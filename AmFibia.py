import sys
import os
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QFrame, QFileDialog, QCheckBox,
    QLineEdit, QComboBox, QGroupBox, QScrollArea, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSpinBox
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QFont, QColor, QBrush, QImage, QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt, QRect, QPoint
import numpy as np
import xml.etree.ElementTree as ET
import html
import cv2

PIXEL_TO_MICRON = 1/2
MAX_DELAY_NO_HOME = 300  # seconds
MODE = "dev" # "scope" or "dev"

from src.ProtocolEditor import ProtocolEditor

if MODE == "scope":
    from src.AutoscriptHelpers import fibsem
    from src.CustomPatterns import DisplayablePattern, convert_xT_patterns_to_displayable, RectanglePattern, PatternGroup
    ### INITIALIZE MICROSCOPE FROM DRIVER
    scope = fibsem()
elif MODE == "dev":
    from src.CustomPatterns import parse_pattern_file, load_patterns_for_display, DisplayablePattern, RectanglePattern, PatternGroup


# -------------------------------------------------
# Drawable Image Widget
# -------------------------------------------------

class DrawableImage(QLabel):
    def __init__(self, pixmap):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(1,1)
        self.setFocusPolicy(Qt.StrongFocus)  # Enable keyboard focus for spacebar

        self.original_pixmap = pixmap
        self.scaled_pixmap = None
        self.offset_x = 0
        self.offset_y = 0

        # Zoom and pan state
        self.zoom_factor = 1.0
        self.pan_offset_x = 0.0  # Pan offset in image coordinates
        self.pan_offset_y = 0.0
        self.is_panning = False
        self.pan_start_pos = None
        self.spacebar_held = False

        self.start_point = None
        self.preview_rect_img = None      # red in widget coords
        self.active_rect_img = None   # green in **image coordinates**
        self.pixel_to_um = PIXEL_TO_MICRON  # Default, can be overridden per image
        
        # Tracking area (green rectangle with transparency)
        self.tracking_area_img = None  # Stored in image coordinates
        self.tracking_area_preview_img = None  # Preview while drawing
        self.right_mouse_mode = "measure"  # "measure" or "tracking_area"
        self.tracking_area_callback = None  # Callback when tracking area is set
        
        # Rectangle selection and manipulation
        self.selected_rect = None  # "measure" or "tracking_area" or None
        self.rect_drag_start_img = None  # Start point for dragging rectangle
        self.rect_resize_handle = None  # Which handle is being dragged (0-7 for corners/edges)
        self.is_dragging_rect = False
        self.is_resizing_rect = False
        self.HANDLE_SIZE = 8  # Size of resize handles in pixels (widget coords)
        self.rect_selected_callback = None  # Callback when rectangle is selected/deselected

        # polygon editor
        self.polygons_img = [] # list[{"id": int, "points": list[QPoint], "pattern": DisplayablePattern}]
        self.drag_start_img = None
        self.start_point_img = None
        self.is_dragging_shapes = False
        self.is_drawing_rect = False
        self.shapes_dirty = False
        self.shapes_changed_callback = None
        self.pattern_selected_callback = None  # Callback when patterns are clicked
        self.selected_polygon_ids = set()  # Currently selected polygon ids (supports multi-select)
        self.selection_rect_img = None  # White selection rectangle for drag-select
        self.is_drawing_selection = False  # Flag for selection rectangle drawing
        self.selection_start_img = None  # Start point for selection rectangle

        # Reset zoom button
        self._setup_reset_zoom_button()

    def _setup_reset_zoom_button(self):
        """Create the reset zoom button overlay."""
        from PyQt5.QtWidgets import QPushButton
        self.reset_zoom_btn = QPushButton("⬜", self)
        self.reset_zoom_btn.setFixedSize(30, 30)
        self.reset_zoom_btn.setToolTip("Reset zoom (fit to window)")
        self.reset_zoom_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(50, 50, 50, 180);
                color: white;
                border: 1px solid #666;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 200);
            }
        """)
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        self.reset_zoom_btn.hide()  # Hidden when zoom is 1.0

    def reset_zoom(self):
        """Reset zoom to fit image in widget."""
        self.zoom_factor = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.reset_zoom_btn.hide()
        self._update_scaled_pixmap()
        self.update()

    def _update_scaled_pixmap(self):
        """Update scaled pixmap based on current zoom level."""
        if self.original_pixmap.isNull():
            return
        
        # Base size that fits the widget
        base_scaled = self.original_pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Apply zoom factor
        zoomed_width = int(base_scaled.width() * self.zoom_factor)
        zoomed_height = int(base_scaled.height() * self.zoom_factor)
        
        self.scaled_pixmap = self.original_pixmap.scaled(
            zoomed_width, zoomed_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Compute offset to center the zoomed image, then apply pan
        self.offset_x = (self.width() - self.scaled_pixmap.width()) // 2 + int(self.pan_offset_x * self.zoom_factor)
        self.offset_y = (self.height() - self.scaled_pixmap.height()) // 2 + int(self.pan_offset_y * self.zoom_factor)

    def resizeEvent(self, event):
        if not self.original_pixmap.isNull():
            self._update_scaled_pixmap()
            # Position reset button at bottom-left
            self.reset_zoom_btn.move(10, self.height() - 40)
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 10))

        # Draw scaled image
        if self.scaled_pixmap:
            painter.drawPixmap(self.offset_x, self.offset_y, self.scaled_pixmap)

        # Draw preview rectangle (red) - measure mode
        if self.preview_rect_img:
            rect_widget = self._image_rect_to_widget(self.preview_rect_img)
            self._draw_rect_with_measurements_widget(painter, rect_widget, self.preview_rect_img, Qt.red)

        # Draw active rectangle (green) - measure mode
        if self.active_rect_img:
            rect_widget = self._image_rect_to_widget(self.active_rect_img)
            self._draw_rect_with_measurements_widget(painter, rect_widget, self.active_rect_img, Qt.green)
        
        # Draw tracking area preview (green with 20% transparency)
        if self.tracking_area_preview_img:
            rect_widget = self._image_rect_to_widget(self.tracking_area_preview_img)
            self._draw_tracking_area_rect(painter, rect_widget, preview=True)
        
        # Draw committed tracking area (green with 20% transparency)
        if self.tracking_area_img:
            rect_widget = self._image_rect_to_widget(self.tracking_area_img)
            self._draw_tracking_area_rect(painter, rect_widget, preview=False)
            # Draw handles if selected
            if self.selected_rect == "tracking_area":
                self._draw_rect_handles(painter, self.tracking_area_img)
        
        # Draw handles on selected measure rectangle
        if self.active_rect_img and self.selected_rect == "measure":
            self._draw_rect_handles(painter, self.active_rect_img)
    
        if self.polygons_img:
            for poly in self.polygons_img:
                # Use per-polygon color if available, otherwise default to yellow
                color = poly.get("color", QColor(255, 255, 0))
                pen = QPen(color, 2)
                painter.setPen(pen)
                # Use 60% opacity (153/255) for selected polygon, 50 for others
                is_selected = poly.get("id") in self.selected_polygon_ids
                alpha = 153 if is_selected else 50
                brush_color = QColor(color.red(), color.green(), color.blue(), alpha)
                brush = QBrush(brush_color)
                painter.setBrush(brush)
                painter.drawPolygon(
                    *[self._image_point_to_widget(p) for p in poly["points"]]
                )
        
        # Draw selection rectangle (white)
        if self.selection_rect_img:
            rect_widget = self._image_rect_to_widget(self.selection_rect_img)
            pen = QPen(Qt.white, 1, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect_widget)

    def _draw_tracking_area_rect(self, painter, rect, preview=False):
        """Draw a tracking area rectangle with 20% green transparency."""
        # Green with 20% opacity (51/255)
        fill_color = QColor(0, 255, 0, 51)
        border_color = QColor(0, 255, 0) if not preview else QColor(0, 200, 0)
        
        pen = QPen(border_color, 2)
        if preview:
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill_color))
        painter.drawRect(rect)
    
    def _get_rect_handles(self, rect_img):
        """Get the 8 handle positions for a rectangle (in image coordinates).
        Returns list of (x, y) tuples for: TL, T, TR, R, BR, B, BL, L
        """
        if not rect_img:
            return []
        r = rect_img
        cx = (r.left() + r.right()) / 2
        cy = (r.top() + r.bottom()) / 2
        return [
            (r.left(), r.top()),      # 0: top-left
            (cx, r.top()),             # 1: top-center
            (r.right(), r.top()),      # 2: top-right
            (r.right(), cy),           # 3: right-center
            (r.right(), r.bottom()),   # 4: bottom-right
            (cx, r.bottom()),          # 5: bottom-center
            (r.left(), r.bottom()),    # 6: bottom-left
            (r.left(), cy),            # 7: left-center
        ]
    
    def _draw_rect_handles(self, painter, rect_img):
        """Draw resize handles on a rectangle."""
        handles = self._get_rect_handles(rect_img)
        painter.setPen(QPen(Qt.white, 1))
        painter.setBrush(QBrush(Qt.white))
        
        hs = self.HANDLE_SIZE
        for hx, hy in handles:
            widget_pt = self._image_point_to_widget(QPoint(int(hx), int(hy)))
            painter.drawRect(widget_pt.x() - hs//2, widget_pt.y() - hs//2, hs, hs)
    
    def _get_handle_at_point(self, img_point, rect_img):
        """Check if img_point is on a handle. Returns handle index (0-7) or -1."""
        if not rect_img:
            return -1
        
        handles = self._get_rect_handles(rect_img)
        # Convert handle size to image coordinates
        scale = self.original_pixmap.width() / self.scaled_pixmap.width() if self.scaled_pixmap else 1
        tolerance = self.HANDLE_SIZE * scale
        
        for i, (hx, hy) in enumerate(handles):
            if abs(img_point.x() - hx) <= tolerance and abs(img_point.y() - hy) <= tolerance:
                return i
        return -1
    
    def _point_in_rect(self, img_point, rect_img):
        """Check if point is inside rectangle (but not on handles)."""
        if not rect_img:
            return False
        return rect_img.contains(img_point)
    
    def _resize_rect_by_handle(self, rect_img, handle_idx, new_img_point):
        """Resize rectangle by moving a handle. Returns new QRect."""
        if not rect_img:
            return rect_img
        
        left = rect_img.left()
        top = rect_img.top()
        right = rect_img.right()
        bottom = rect_img.bottom()
        
        nx, ny = new_img_point.x(), new_img_point.y()
        
        # Handle indices: 0=TL, 1=T, 2=TR, 3=R, 4=BR, 5=B, 6=BL, 7=L
        if handle_idx == 0:  # top-left
            left, top = nx, ny
        elif handle_idx == 1:  # top-center
            top = ny
        elif handle_idx == 2:  # top-right
            right, top = nx, ny
        elif handle_idx == 3:  # right-center
            right = nx
        elif handle_idx == 4:  # bottom-right
            right, bottom = nx, ny
        elif handle_idx == 5:  # bottom-center
            bottom = ny
        elif handle_idx == 6:  # bottom-left
            left, bottom = nx, ny
        elif handle_idx == 7:  # left-center
            left = nx
        
        return QRect(QPoint(int(left), int(top)), QPoint(int(right), int(bottom))).normalized()

    def load_shapes(self, shapes, locked=False, color=None):
        """Load shapes for display. If locked=True, shapes cannot be dragged.
        
        shapes should be a list of PatternGroup objects.
        Each PatternGroup contains its own color attribute.
        
        For backwards compatibility, also supports list of dicts [{id: pattern}, ...]
        with predefined colors (Yellow, Red, Blue, Orange, Green).
        """
        import random
        
        # Predefined colors for backwards compatibility with dict format
        PREDEFINED_COLORS = [
            QColor(255, 255, 0),   # Yellow
            QColor(255, 0, 0),     # Red
            QColor(0, 100, 255),   # Blue
            QColor(255, 165, 0),   # Orange
            QColor(0, 200, 0),     # Green
        ]
        
        self.polygons_img = []
        
        # Handle both list and dict for backwards compatibility
        if not isinstance(shapes, list):
            shapes = [shapes] if shapes else []
        
        for i, item in enumerate(shapes):
            # Check if item is a PatternGroup (has 'patterns' and 'color' attributes)
            if hasattr(item, 'patterns') and hasattr(item, 'color'):
                # PatternGroup object
                pattern_group = item
                c = QColor(*pattern_group.color)  # Convert RGB tuple to QColor
                pattern_dict = pattern_group.patterns
            else:
                # Legacy dict format - use predefined colors and create temporary PatternGroup
                pattern_dict = item
                pattern_group = None  # No PatternGroup for legacy format
                if i < len(PREDEFINED_COLORS):
                    c = PREDEFINED_COLORS[i]
                else:
                    c = QColor(random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
            
            for sid, pattern in pattern_dict.items():
                self.polygons_img.append({
                    "id": sid,
                    "points": [QPoint(x, y) for x, y in pattern.coords],
                    "locked": locked,
                    "color": c,
                    "displayable_pattern": pattern,  # Store reference for property display
                    "pattern_group": pattern_group   # Store reference to PatternGroup
                })
        
        self.selected_polygon_ids = set()  # Clear selection when loading new shapes
        self.update()

    def add_shapes(self, shapes, locked=False, color=None):
        """Add shapes to existing shapes (without clearing). 
        color can be a QColor or None for default yellow."""
        for sid, pattern in shapes.items():
            self.polygons_img.append({
                "id": sid,
                "points": [QPoint(x, y) for x, y in pattern.coords],
                "locked": locked,
                "color": color if color else QColor(255, 255, 0),
                "displayable_pattern": pattern  # Store reference for property display
            })
        self.update()

    def clear_shapes(self):
        """Clear all shapes."""
        self.polygons_img = []
        self.selected_polygon_ids = set()
        self.update()


    def get_shapes(self):
        return {
            poly["id"]: [(p.x(), p.y()) for p in poly["points"]]
            for poly in self.polygons_img
        }


    def _point_in_polygon(self, point, poly):
        """
        Ray casting algorithm
        point: QPoint
        polygon: list[QPoint]
        """
        polygon = poly["points"]
        x, y = point.x(), point.y()
        inside = False
        n = len(polygon)

        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]

            if ((p1.y() > y) != (p2.y() > y)):
                x_intersect = (y - p1.y()) * (p2.x() - p1.x()) / (p2.y() - p1.y()) + p1.x()
                if x < x_intersect:
                    inside = not inside

        return inside
    
    def _point_in_any_polygon(self, point):
        for poly in self.polygons_img:
            if self._point_in_polygon(point, poly):
                return True
        return False

    def _point_in_any_unlocked_polygon(self, point):
        """Check if point is inside any unlocked (draggable) polygon."""
        for poly in self.polygons_img:
            if not poly.get("locked", False) and self._point_in_polygon(point, poly):
                return True
        return False

    def _get_polygon_at_point(self, point):
        """Return the polygon at the given point, or None."""
        for poly in self.polygons_img:
            if self._point_in_polygon(point, poly):
                return poly
        return None

    def _get_selected_displayable_patterns(self):
        """Return list of DisplayablePatterns for all selected polygons."""
        patterns = []
        for poly in self.polygons_img:
            if poly.get("id") in self.selected_polygon_ids:
                dp = poly.get("displayable_pattern")
                if dp:
                    patterns.append(dp)
        return patterns
    
    def _get_selected_pattern_groups(self):
        """Return list of unique PatternGroups for all selected polygons."""
        groups = []
        seen_ids = set()
        for poly in self.polygons_img:
            if poly.get("id") in self.selected_polygon_ids:
                pg = poly.get("pattern_group")
                if pg and id(pg) not in seen_ids:
                    groups.append(pg)
                    seen_ids.add(id(pg))
        return groups

    def _polygon_intersects_rect(self, poly, rect):
        """Check if a polygon intersects or is inside a rectangle.
        
        Uses bounding box check first, then checks if any polygon edge
        intersects the rectangle or if polygon is fully inside rect.
        """
        points = poly["points"]
        if not points:
            return False
        
        # Get polygon bounding box
        min_x = min(p.x() for p in points)
        max_x = max(p.x() for p in points)
        min_y = min(p.y() for p in points)
        max_y = max(p.y() for p in points)
        
        # Quick bounding box check
        if (max_x < rect.left() or min_x > rect.right() or
            max_y < rect.top() or min_y > rect.bottom()):
            return False
        
        # Check if any polygon vertex is inside rect
        for p in points:
            if rect.contains(p):
                return True
        
        # Check if any rect corner is inside polygon
        rect_corners = [
            QPoint(rect.left(), rect.top()),
            QPoint(rect.right(), rect.top()),
            QPoint(rect.right(), rect.bottom()),
            QPoint(rect.left(), rect.bottom())
        ]
        for corner in rect_corners:
            if self._point_in_polygon(corner, poly):
                return True
        
        # If bounding boxes overlap but no points inside, they likely intersect
        # This is a simplification - for more accuracy would need edge intersection tests
        return True

    # -------------------------------
    # Zoom and Pan
    # -------------------------------

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming towards mouse position."""
        if self.original_pixmap.isNull() or not self.scaled_pixmap:
            return
        
        # Get mouse position in widget coordinates
        mouse_pos = event.pos()
        
        # Convert mouse position to image coordinates BEFORE zoom change
        img_x_before = (mouse_pos.x() - self.offset_x) * self.original_pixmap.width() / self.scaled_pixmap.width()
        img_y_before = (mouse_pos.y() - self.offset_y) * self.original_pixmap.height() / self.scaled_pixmap.height()
        
        # Calculate zoom delta
        delta = event.angleDelta().y()
        zoom_in = delta > 0
        
        # Zoom factor change
        old_zoom = self.zoom_factor
        if zoom_in:
            new_zoom = min(self.zoom_factor * 1.15, 10.0)  # Max 10x zoom
        else:
            new_zoom = max(self.zoom_factor / 1.15, 1.0)  # Min 1x (fit to window)
        
        if new_zoom == old_zoom:
            return
        
        self.zoom_factor = new_zoom
        
        # Calculate new scaled pixmap dimensions
        base_scaled = self.original_pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        new_scaled_width = base_scaled.width() * self.zoom_factor
        new_scaled_height = base_scaled.height() * self.zoom_factor
        
        # Calculate where the same image point would be in widget coords after zoom (without pan adjustment)
        new_widget_x = img_x_before * new_scaled_width / self.original_pixmap.width()
        new_widget_y = img_y_before * new_scaled_height / self.original_pixmap.height()
        
        # Calculate new center offset (before pan)
        new_center_offset_x = (self.width() - new_scaled_width) / 2
        new_center_offset_y = (self.height() - new_scaled_height) / 2
        
        # The point under mouse should stay at mouse_pos
        # mouse_pos.x() = new_center_offset_x + pan_offset_x * zoom + new_widget_x
        # Solve for pan_offset_x:
        # pan_offset_x = (mouse_pos.x() - new_center_offset_x - new_widget_x) / zoom
        self.pan_offset_x = (mouse_pos.x() - new_center_offset_x - new_widget_x) / self.zoom_factor
        self.pan_offset_y = (mouse_pos.y() - new_center_offset_y - new_widget_y) / self.zoom_factor
        
        # When zooming out to 1.0, reset pan
        if self.zoom_factor == 1.0:
            self.pan_offset_x = 0.0
            self.pan_offset_y = 0.0
        
        # Clamp pan to reasonable bounds
        self._clamp_pan()
        
        self._update_scaled_pixmap()
        
        # Show/hide reset button based on zoom level
        if self.zoom_factor > 1.0:
            self.reset_zoom_btn.show()
        else:
            self.reset_zoom_btn.hide()
        
        self.update()

    def _clamp_pan(self):
        """Clamp pan offset to keep image visible."""
        if self.original_pixmap.isNull():
            return
        
        # Allow panning up to half the image size beyond edges
        max_pan_x = self.original_pixmap.width() * 0.5
        max_pan_y = self.original_pixmap.height() * 0.5
        
        self.pan_offset_x = max(-max_pan_x, min(max_pan_x, self.pan_offset_x))
        self.pan_offset_y = max(-max_pan_y, min(max_pan_y, self.pan_offset_y))

    def keyPressEvent(self, event):
        """Handle key press for spacebar panning and arrow keys for pattern/rectangle movement."""
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.spacebar_held = True
            self.setCursor(Qt.OpenHandCursor)
        elif event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            # Determine movement delta (1 pixel, or 10 with Shift held)
            step = 10 if event.modifiers() & Qt.ShiftModifier else 1
            dx, dy = 0, 0
            if event.key() == Qt.Key_Left:
                dx = -step
            elif event.key() == Qt.Key_Right:
                dx = step
            elif event.key() == Qt.Key_Up:
                dy = -step
            elif event.key() == Qt.Key_Down:
                dy = step
            
            # Check if a rectangle is selected - move it
            if self.selected_rect:
                if self.selected_rect == "measure" and self.active_rect_img:
                    self.active_rect_img.translate(dx, dy)
                    self.update()
                    # Notify callback
                    if self.rect_selected_callback:
                        self.rect_selected_callback(self.selected_rect, self._get_rect_dimensions_um(self.selected_rect))
                elif self.selected_rect == "tracking_area" and self.tracking_area_img:
                    self.tracking_area_img.translate(dx, dy)
                    self.update()
                    # Notify callbacks
                    if self.tracking_area_callback:
                        self.tracking_area_callback(self._get_tracking_area_um())
                    if self.rect_selected_callback:
                        self.rect_selected_callback(self.selected_rect, self._get_rect_dimensions_um(self.selected_rect))
            # If any pattern is selected, move ALL unlocked patterns
            elif self.selected_polygon_ids:
                moved = False
                for poly in self.polygons_img:
                    if not poly.get("locked", False):
                        for p in poly["points"]:
                            p.setX(p.x() + dx)
                            p.setY(p.y() + dy)
                        moved = True
                
                if moved:
                    self.update()
                    # Notify callback about shape changes
                    if self.shapes_changed_callback:
                        self.shapes_changed_callback(self.get_shapes())
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Handle key release for spacebar panning."""
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.spacebar_held = False
            self.is_panning = False
            self.pan_start_pos = None
            self.setCursor(Qt.ArrowCursor)
        else:
            super().keyReleaseEvent(event)

    def enterEvent(self, event):
        """Grab focus when mouse enters the widget for keyboard events."""
        self.setFocus()
        super().enterEvent(event)

    # -------------------------------
    # Mouse interactions
    # -------------------------------

    def mousePressEvent(self, event):
        if not self.scaled_pixmap:
            return
        
        # Ensure we have focus for keyboard events
        self.setFocus()

        # Handle spacebar + click for panning
        if self.spacebar_held and event.button() == Qt.LeftButton:
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        img_point = self._widget_to_image_point(event.pos())

        if event.button() == Qt.LeftButton:
            # First check if clicking on rectangle handles (for resizing)
            handle_measure = self._get_handle_at_point(img_point, self.active_rect_img) if self.selected_rect == "measure" else -1
            handle_tracking = self._get_handle_at_point(img_point, self.tracking_area_img) if self.selected_rect == "tracking_area" else -1
            
            if handle_measure >= 0:
                # Start resizing measure rectangle
                self.is_resizing_rect = True
                self.rect_resize_handle = handle_measure
                self.update()
                return
            elif handle_tracking >= 0:
                # Start resizing tracking area
                self.is_resizing_rect = True
                self.rect_resize_handle = handle_tracking
                self.update()
                return
            
            # Check if clicking inside a rectangle (for moving or selecting)
            in_measure = self._point_in_rect(img_point, self.active_rect_img)
            in_tracking = self._point_in_rect(img_point, self.tracking_area_img)
            
            if in_measure or in_tracking:
                # Select the rectangle and start dragging
                if in_measure:
                    self.selected_rect = "measure"
                else:
                    self.selected_rect = "tracking_area"
                self.is_dragging_rect = True
                self.rect_drag_start_img = self._widget_to_image_point_unclamped(event.pos())
                # Notify callback about rectangle selection
                if self.rect_selected_callback:
                    self.rect_selected_callback(self.selected_rect, self._get_rect_dimensions_um(self.selected_rect))
                self.update()
                return
            else:
                # Clicked outside rectangles - deselect
                if self.selected_rect:
                    self.selected_rect = None
                    # Notify callback about deselection
                    if self.rect_selected_callback:
                        self.rect_selected_callback(None, None)
                    self.update()
            
            # Check if clicking on any polygon (for selection)
            clicked_poly = self._get_polygon_at_point(img_point)
            shift_held = event.modifiers() & Qt.ShiftModifier
            
            if clicked_poly:
                poly_id = clicked_poly.get("id")
                if shift_held:
                    # Toggle selection with Shift
                    if poly_id in self.selected_polygon_ids:
                        self.selected_polygon_ids.discard(poly_id)
                    else:
                        self.selected_polygon_ids.add(poly_id)
                else:
                    # Replace selection without Shift
                    self.selected_polygon_ids = {poly_id}
                
                # Notify callback about pattern selection (pass list of selected patterns)
                if self.pattern_selected_callback:
                    selected_patterns = self._get_selected_displayable_patterns()
                    self.pattern_selected_callback(selected_patterns)
                self.update()
            else:
                # Clicked outside a polygon - start selection rectangle
                self.selection_start_img = img_point
                self.selection_rect_img = None
                self.is_drawing_selection = True
                
                # Clear selection immediately only if Shift not held
                if not shift_held and self.selected_polygon_ids:
                    self.selected_polygon_ids.clear()
                    if self.pattern_selected_callback:
                        self.pattern_selected_callback([])
                    self.update()
            
            # Only allow dragging unlocked shapes
            if self.polygons_img and self._point_in_any_unlocked_polygon(img_point):
                self.drag_start_img = img_point
                self.is_dragging_shapes = True
            else:
                self.is_dragging_shapes = False

        elif event.button() == Qt.RightButton:
            self.start_point_img = img_point
            if self.right_mouse_mode == "measure":
                self.preview_rect_img = None
            else:  # tracking_area mode
                self.tracking_area_preview_img = None
            self.is_drawing_rect = True

        self.update()

    def mouseMoveEvent(self, event):
        if not self.scaled_pixmap:
            return

        # Handle panning when spacebar is held
        if self.is_panning and self.pan_start_pos:
            delta = event.pos() - self.pan_start_pos
            # Convert widget delta to image coordinate delta
            scale = self.original_pixmap.width() / self.scaled_pixmap.width()
            self.pan_offset_x += delta.x() * scale
            self.pan_offset_y += delta.y() * scale
            self._clamp_pan()
            self._update_scaled_pixmap()
            self.pan_start_pos = event.pos()
            self.update()
            return
        
        # Handle rectangle resizing
        if self.is_resizing_rect and self.rect_resize_handle >= 0:
            current_img = self._widget_to_image_point(event.pos())
            if self.selected_rect == "measure" and self.active_rect_img:
                self.active_rect_img = self._resize_rect_by_handle(
                    self.active_rect_img, self.rect_resize_handle, current_img
                )
            elif self.selected_rect == "tracking_area" and self.tracking_area_img:
                self.tracking_area_img = self._resize_rect_by_handle(
                    self.tracking_area_img, self.rect_resize_handle, current_img
                )
            self.update()
            return
        
        # Handle rectangle dragging (moving)
        if self.is_dragging_rect and self.rect_drag_start_img:
            current_img = self._widget_to_image_point_unclamped(event.pos())
            dx = current_img.x() - self.rect_drag_start_img.x()
            dy = current_img.y() - self.rect_drag_start_img.y()
            
            if self.selected_rect == "measure" and self.active_rect_img:
                self.active_rect_img.translate(dx, dy)
            elif self.selected_rect == "tracking_area" and self.tracking_area_img:
                self.tracking_area_img.translate(dx, dy)
            
            self.rect_drag_start_img = current_img
            self.update()
            return

        if self.is_drawing_selection and self.selection_start_img:
            # Drawing selection rectangle
            current_img = self._widget_to_image_point(event.pos())
            self.selection_rect_img = QRect(
                self.selection_start_img, current_img
            ).normalized()
            self.update()

        elif self.is_dragging_shapes and self.drag_start_img:
            current_img = self._widget_to_image_point(event.pos())
            dx = current_img.x() - self.drag_start_img.x()
            dy = current_img.y() - self.drag_start_img.y()

            for poly in self.polygons_img:
                # Only move unlocked shapes
                if poly.get("locked", False):
                    continue
                for p in poly["points"]:
                    p.setX(p.x() + dx)
                    p.setY(p.y() + dy)

            self.drag_start_img = current_img
            self.shapes_dirty = True
            self.update()

            # if self.shapes_changed_callback:
            #     self.shapes_changed_callback(self.get_shapes())

        elif self.is_drawing_rect and self.start_point_img:
            current_img = self._widget_to_image_point(event.pos())
            rect = QRect(self.start_point_img, current_img).normalized()
            if self.right_mouse_mode == "measure":
                self.preview_rect_img = rect
            else:  # tracking_area mode
                self.tracking_area_preview_img = rect
            self.update()

    def mouseReleaseEvent(self, event):
        # Handle panning release
        if self.is_panning and event.button() == Qt.LeftButton:
            self.is_panning = False
            self.pan_start_pos = None
            if self.spacebar_held:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            return

        if event.button() == Qt.LeftButton:
            # Handle rectangle resize/drag completion
            if self.is_resizing_rect or self.is_dragging_rect:
                if self.selected_rect == "tracking_area" and self.tracking_area_callback:
                    self.tracking_area_callback(self._get_tracking_area_um())
                # Notify about updated dimensions
                if self.rect_selected_callback and self.selected_rect:
                    self.rect_selected_callback(self.selected_rect, self._get_rect_dimensions_um(self.selected_rect))
                self.is_resizing_rect = False
                self.is_dragging_rect = False
                self.rect_resize_handle = -1
                self.rect_drag_start_img = None
                self.update()
                return
            
            if self.is_drawing_selection:
                if self.selection_rect_img:
                    # Find all polygons touching the selection rectangle
                    shift_held = event.modifiers() & Qt.ShiftModifier
                    newly_selected = set()
                    
                    for poly in self.polygons_img:
                        if self._polygon_intersects_rect(poly, self.selection_rect_img):
                            newly_selected.add(poly.get("id"))
                    
                    if shift_held:
                        # Add to existing selection
                        self.selected_polygon_ids.update(newly_selected)
                    else:
                        # Replace selection
                        self.selected_polygon_ids = newly_selected
                    
                    # Notify callback
                    if self.pattern_selected_callback:
                        selected_patterns = self._get_selected_displayable_patterns()
                        self.pattern_selected_callback(selected_patterns)
                
                # Always clear selection rectangle state on left button release
                self.selection_rect_img = None
                self.selection_start_img = None
                self.is_drawing_selection = False
            
            if self.is_dragging_shapes and self.shapes_dirty:
                if self.shapes_changed_callback:
                    self.shapes_changed_callback(self.get_shapes())

            self.is_dragging_shapes = False
            self.drag_start_img = None
            self.shapes_dirty = False

        elif event.button() == Qt.RightButton:
            if self.is_drawing_rect:
                if self.right_mouse_mode == "measure":
                    # Commit measure preview to active rectangle
                    if self.preview_rect_img:
                        self.active_rect_img = self.preview_rect_img
                        self.preview_rect_img = None
                elif self.right_mouse_mode == "tracking_area":
                    # Commit tracking area preview
                    if self.tracking_area_preview_img:
                        self.tracking_area_img = self.tracking_area_preview_img
                        self.tracking_area_preview_img = None
                        # Notify callback with coordinates in µm
                        if self.tracking_area_callback:
                            self.tracking_area_callback(self._get_tracking_area_um())
            self.is_drawing_rect = False
            self.start_point_img = None

        self.update()

    def load_image(self, pixmap, pixel_to_um=None):
        if pixmap is None or pixmap.isNull():
            self.clear()
            return
        self.original_pixmap = pixmap
        self.scaled_pixmap = None
        self.preview_rect_img = None
        self.active_rect_img = None
        self.start_point_img = None
        self.polygons_img = []
        self.is_dragging_shapes = False
        self.shapes_dirty = False
        self.selected_polygon_ids = set()
        self.selection_rect_img = None
        self.selection_start_img = None
        self.is_drawing_selection = False
        self.tracking_area_img = None
        self.tracking_area_preview_img = None
        # Reset rectangle selection state
        self.selected_rect = None
        self.is_dragging_rect = False
        self.is_resizing_rect = False
        self.rect_resize_handle = -1
        self.rect_drag_start_img = None
        
        # Set pixel to micron conversion factor
        self.pixel_to_um = pixel_to_um if pixel_to_um is not None else PIXEL_TO_MICRON
        
        # Reset zoom and pan
        self.zoom_factor = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.reset_zoom_btn.hide()

        # Force scaled pixmap update
        self._update_scaled_pixmap()

        self.update()

    def clear(self):
        """Clear the image widget to show nothing."""
        self.original_pixmap = QPixmap()
        self.scaled_pixmap = None
        self.preview_rect_img = None
        self.active_rect_img = None
        self.start_point_img = None
        self.polygons_img = []
        self.is_dragging_shapes = False
        self.shapes_dirty = False
        self.selected_polygon_ids = set()
        self.selection_rect_img = None
        self.selection_start_img = None
        self.is_drawing_selection = False
        self.tracking_area_img = None
        self.tracking_area_preview_img = None
        # Reset rectangle selection state
        self.selected_rect = None
        self.is_dragging_rect = False
        self.is_resizing_rect = False
        self.rect_resize_handle = -1
        self.rect_drag_start_img = None
        # Reset zoom and pan
        self.zoom_factor = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.reset_zoom_btn.hide()
        self.update()

    # -------------------------------
    # Conversions
    # -------------------------------
    def _image_rect_to_widget(self, rect_img):
        """Convert rect from image coordinates to widget coordinates"""
        scale_x = self.scaled_pixmap.width() / self.original_pixmap.width()
        scale_y = self.scaled_pixmap.height() / self.original_pixmap.height()
        x1 = int(rect_img.left() * scale_x + self.offset_x)
        y1 = int(rect_img.top() * scale_y + self.offset_y)
        x2 = int(rect_img.right() * scale_x + self.offset_x)
        y2 = int(rect_img.bottom() * scale_y + self.offset_y)
        return QRect(x1, y1, x2 - x1, y2 - y1)
    
    def _image_point_to_widget(self, p):
        """Convert a QPoint from image coordinates to widget coordinates"""
        scale_x = self.scaled_pixmap.width() / self.original_pixmap.width()
        scale_y = self.scaled_pixmap.height() / self.original_pixmap.height()
        x = int(p.x() * scale_x + self.offset_x)
        y = int(p.y() * scale_y + self.offset_y)
        return QPoint(x, y)


    def _widget_rect_to_image(self, rect_widget):
        """Convert rectangle from widget coordinates to original image coordinates"""
        scale_x = self.scaled_pixmap.width() / self.original_pixmap.width()
        scale_y = self.scaled_pixmap.height() / self.original_pixmap.height()
        x1 = int((rect_widget.left() - self.offset_x) / scale_x)
        y1 = int((rect_widget.top() - self.offset_y) / scale_y)
        x2 = int((rect_widget.right() - self.offset_x) / scale_x)
        y2 = int((rect_widget.bottom() - self.offset_y) / scale_y)
        # Clamp values inside original image
        x1 = max(0, min(x1, self.original_pixmap.width()-1))
        x2 = max(0, min(x2, self.original_pixmap.width()-1))
        y1 = max(0, min(y1, self.original_pixmap.height()-1))
        y2 = max(0, min(y2, self.original_pixmap.height()-1))
        return (x1, y1, x2, y2)
    
    def _widget_to_image_point(self, pos):
        # Ensure inside image
        x = (pos.x() - self.offset_x) * self.original_pixmap.width() / self.scaled_pixmap.width()
        y = (pos.y() - self.offset_y) * self.original_pixmap.height() / self.scaled_pixmap.height()
        x = max(0, min(int(x), self.original_pixmap.width()-1))
        y = max(0, min(int(y), self.original_pixmap.height()-1))
        return QPoint(x, y)
    
    def _widget_to_image_point_unclamped(self, pos):
        """Convert widget coordinates to image coordinates without clamping.
        Used for drag operations where we need accurate deltas."""
        x = (pos.x() - self.offset_x) * self.original_pixmap.width() / self.scaled_pixmap.width()
        y = (pos.y() - self.offset_y) * self.original_pixmap.height() / self.scaled_pixmap.height()
        return QPoint(int(x), int(y))

    # -------------------------------
    # Commit / load rectangle
    # -------------------------------
    def commit_preview(self):
        if self.preview_rect_img:
            self.active_rect_img = self.preview_rect_img
            self.preview_rect_img = None
            self.update()


    def load_rectangle(self, rect_img):
        self.active_rect_img = rect_img
        self.preview_rect_img = None
        self.update()

    def get_active_rectangle(self):
        return self.active_rect_img
    
    def _get_tracking_area_um(self):
        """Get tracking area coordinates in µm relative to image center."""
        if not self.tracking_area_img or self.original_pixmap.isNull():
            return None
        
        rect = self.tracking_area_img
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()
        center_x = img_w / 2
        center_y = img_h / 2
        
        # Convert pixel coordinates to µm relative to center
        # Note: Y is flipped (image Y increases downward, stage Y increases upward)
        left_um = (rect.left() - center_x) * self.pixel_to_um
        right_um = (rect.right() - center_x) * self.pixel_to_um
        top_um = (center_y - rect.top()) * self.pixel_to_um  # Flip Y
        bottom_um = (center_y - rect.bottom()) * self.pixel_to_um  # Flip Y
        
        return {
            "left": left_um,
            "right": right_um,
            "top": top_um,
            "bottom": bottom_um,
            "width": abs(right_um - left_um),
            "height": abs(top_um - bottom_um),
            "center_x": (left_um + right_um) / 2,
            "center_y": (top_um + bottom_um) / 2
        }
    
    def load_tracking_area(self, tracking_area_um):
        """Load tracking area from µm coordinates."""
        if not tracking_area_um or self.original_pixmap.isNull():
            self.tracking_area_img = None
            return
        
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()
        center_x = img_w / 2
        center_y = img_h / 2
        
        # Convert µm coordinates back to pixels
        left_px = tracking_area_um["left"] / self.pixel_to_um + center_x
        right_px = tracking_area_um["right"] / self.pixel_to_um + center_x
        top_px = center_y - tracking_area_um["top"] / self.pixel_to_um  # Flip Y
        bottom_px = center_y - tracking_area_um["bottom"] / self.pixel_to_um  # Flip Y
        
        self.tracking_area_img = QRect(
            int(min(left_px, right_px)),
            int(min(top_px, bottom_px)),
            int(abs(right_px - left_px)),
            int(abs(bottom_px - top_px))
        )
        self.update()
    
    def clear_tracking_area(self):
        """Clear the tracking area."""
        self.tracking_area_img = None
        self.tracking_area_preview_img = None
        self.update()
    
    def _get_rect_dimensions_um(self, rect_type):
        """Get rectangle dimensions in µm."""
        if rect_type == "measure":
            rect = self.active_rect_img
        elif rect_type == "tracking_area":
            rect = self.tracking_area_img
        else:
            return None
        
        if not rect:
            return None
        
        width_um = rect.width() * self.pixel_to_um
        height_um = rect.height() * self.pixel_to_um
        return {"width": width_um, "height": height_um}
    
    def set_rect_dimensions_um(self, rect_type, width_um, height_um):
        """Set rectangle dimensions in µm, keeping center fixed."""
        if rect_type == "measure":
            rect = self.active_rect_img
        elif rect_type == "tracking_area":
            rect = self.tracking_area_img
        else:
            return
        
        if not rect:
            return
        
        # Get current center using floating point to avoid drift
        # QRect.center() uses integer division which can cause 1px shifts
        center_x = rect.left() + rect.width() / 2.0
        center_y = rect.top() + rect.height() / 2.0
        
        # Convert µm to pixels
        new_width_px = int(round(width_um / self.pixel_to_um))
        new_height_px = int(round(height_um / self.pixel_to_um))
        
        # Create new rect centered on same point
        new_left = int(round(center_x - new_width_px / 2.0))
        new_top = int(round(center_y - new_height_px / 2.0))
        
        new_rect = QRect(new_left, new_top, new_width_px, new_height_px)
        
        if rect_type == "measure":
            self.active_rect_img = new_rect
        elif rect_type == "tracking_area":
            self.tracking_area_img = new_rect
            # Notify tracking area callback
            if self.tracking_area_callback:
                self.tracking_area_callback(self._get_tracking_area_um())
        
        self.update()

    # -------------------------------
    # Draw rectangle + measurements
    # -------------------------------
    def _draw_rect_with_measurements_widget(self, painter, rect_widget, rect_img, color):
        """Draw rectangle with measurements.
        
        rect_widget: QRect in widget coordinates (for drawing)
        rect_img: QRect in image coordinates (for measurements)
        """
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.drawRect(rect_widget)

        # width and height in µm using image coordinates directly
        width_um = rect_img.width() * self.pixel_to_um
        height_um = rect_img.height() * self.pixel_to_um

        # Width text
        width_text = f"{width_um:.1f} µm"
        painter.drawText(rect_widget.center().x() - 30, rect_widget.top() - 5, width_text)

        # Height text (rotated)
        height_text = f"{height_um:.1f} µm"
        painter.save()
        painter.translate(rect_widget.left() - 10, rect_widget.center().y() + 30)
        painter.rotate(-90)
        painter.drawText(0, 0, height_text)
        painter.restore()


# -------------------------------------------------
# Position List
# -------------------------------------------------

class PositionList(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QListWidget.SingleSelection)



# -------------------------------------------------
# Main Window
# -------------------------------------------------

class MainWindow(QWidget):
    # Default currents in Amperes for dev mode
    DEV_MODE_CURRENTS = [0.0, 0.1e-9, 15e-9, 50e-9, 65e-9]  # Not set, 0.1nA, 15nA, 50nA, 65nA
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Protocol Editor")
        self.showFullScreen()

        self.positions = {}
        self.selected_displayable_patterns = []  # Track currently selected patterns (list)
        self.selected_pattern_groups = []  # Track PatternGroups for selected patterns
        self.available_currents = self._get_available_currents()

        # Layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left panel
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Protocol Editor toggle button at top
        self.protocol_editor_btn = QPushButton("Protocol Editor ▶")
        self.protocol_editor_btn.clicked.connect(self.toggle_protocol_editor)

        self.position_list = PositionList()
        self.position_list.model().rowsMoved.connect(self.rebuild_positions)
        self.position_list.itemClicked.connect(self.on_item_clicked)

        add_position_btn = QPushButton("Add Position")
        add_position_btn.clicked.connect(self.add_position)

        # Take IB image button with auto checkbox
        take_ib_layout = QHBoxLayout()
        take_ib_layout.setSpacing(5)
        take_ion_beam_image_btn = QPushButton("Take IB image")
        take_ion_beam_image_btn.clicked.connect(self.take_ion_beam_image)
        self.auto_take_image_checkbox = QCheckBox("auto")
        take_ib_layout.addWidget(take_ion_beam_image_btn, stretch=1)
        take_ib_layout.addWidget(self.auto_take_image_checkbox, stretch=0)

        # Attach pattern button with auto checkbox
        attach_pattern_layout = QHBoxLayout()
        attach_pattern_layout.setSpacing(5)
        attach_pattern_btn = QPushButton("Attach pattern from xT")
        attach_pattern_btn.clicked.connect(self.attach_xT_pattern)
        self.auto_attach_pattern_checkbox = QCheckBox("auto")
        attach_pattern_layout.addWidget(attach_pattern_btn, stretch=1)
        attach_pattern_layout.addWidget(self.auto_attach_pattern_checkbox, stretch=0)

        # Right mouse mode dropdown
        right_mouse_layout = QHBoxLayout()
        right_mouse_layout.setSpacing(5)
        right_mouse_label = QLabel("Right mouse:")
        self.right_mouse_combo = QComboBox()
        self.right_mouse_combo.addItems(["Measure", "Tracking area"])
        self.right_mouse_combo.currentIndexChanged.connect(self._on_right_mouse_mode_changed)
        right_mouse_layout.addWidget(right_mouse_label)
        right_mouse_layout.addWidget(self.right_mouse_combo, stretch=1)

        # PatternGroup properties table (milling current, color, sequential group)
        self.group_properties_label = QLabel("Group Properties")
        self.group_properties_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.group_properties_table = QTableWidget()
        self.group_properties_table.setColumnCount(2)
        self.group_properties_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.group_properties_table.horizontalHeader().setStretchLastSection(True)
        self.group_properties_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.group_properties_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.group_properties_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.group_properties_table.verticalHeader().setVisible(False)
        self.group_properties_table.setMaximumHeight(145)  # Keep it compact

        # Pattern properties table
        self.pattern_properties_label = QLabel("Pattern Properties")
        self.pattern_properties_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.pattern_properties_table = QTableWidget()
        self.pattern_properties_table.setColumnCount(2)
        self.pattern_properties_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.pattern_properties_table.horizontalHeader().setStretchLastSection(True)
        self.pattern_properties_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.pattern_properties_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pattern_properties_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.pattern_properties_table.verticalHeader().setVisible(False)

        left_layout.addWidget(self.protocol_editor_btn)
        left_layout.addWidget(self.position_list, stretch=1)  # 50% for position list
        left_layout.addWidget(add_position_btn)
        left_layout.addLayout(take_ib_layout)
        left_layout.addLayout(attach_pattern_layout)
        left_layout.addLayout(right_mouse_layout)
        left_layout.addWidget(self.group_properties_label)
        left_layout.addWidget(self.group_properties_table)
        left_layout.addWidget(self.pattern_properties_label)
        left_layout.addWidget(self.pattern_properties_table, stretch=1)  # Remaining space for pattern properties

        # Run button
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run)
        left_layout.addWidget(run_btn)

        # Image panel
        pixmap = QPixmap("logo.png")
        self.image_widget = DrawableImage(pixmap)
        self.image_widget.pattern_selected_callback = self.on_pattern_selected
        self.image_widget.tracking_area_callback = self.on_tracking_area_changed
        self.image_widget.rect_selected_callback = self.on_rect_selected
        
        # Track currently selected rectangle type
        self.selected_rect_type = None

        # Protocol Editor panel (initially hidden)
        # Pass mode and scope for current dropdown population
        scope_ref = scope if MODE == "scope" else None
        self.protocol_editor = ProtocolEditor(self, mode=MODE, scope=scope_ref)
        self.protocol_editor.setVisible(False)
        self.protocol_editor.setFixedWidth(350)

        # Separators
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)

        self.separator2 = QFrame()
        self.separator2.setFrameShape(QFrame.VLine)
        self.separator2.setFrameShadow(QFrame.Sunken)
        self.separator2.setVisible(False)

        # Assemble
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(separator1)
        main_layout.addWidget(self.protocol_editor, 0)
        main_layout.addWidget(self.separator2)
        main_layout.addWidget(self.image_widget, 4)

        self.last_loaded_patterns = None
        self.last_loaded_pattern_file = None  # Store file path for auto-add with re-conversion

    # -------------------------------
    # Current helpers
    # -------------------------------
    
    def _get_available_currents(self):
        """Get available milling currents based on mode."""
        if MODE == "scope":
            try:
                # Get from microscope - values are in Amperes
                values = scope.get_available_ion_beam_currents()
                return [0.0] + sorted(values)  # Add "Not set" option
            except Exception as e:
                print(f"Warning: Could not get beam currents from scope: {e}")
                return self.DEV_MODE_CURRENTS
        else:
            return self.DEV_MODE_CURRENTS
    
    def _current_to_nA_str(self, current_A):
        """Convert current in Amperes to nA string for display."""
        if current_A == 0:
            return "Not set"
        nA = current_A * 1e9
        if nA < 1:
            return f"{nA:.1f} nA"
        else:
            return f"{nA:.0f} nA"
    
    def _on_right_mouse_mode_changed(self, index):
        """Handle right mouse mode dropdown change."""
        mode = "measure" if index == 0 else "tracking_area"
        self.image_widget.right_mouse_mode = mode
    
    def on_tracking_area_changed(self, tracking_area_um):
        """Handle tracking area change - save to position data."""
        item = self.position_list.currentItem()
        if not item:
            return
        
        data = item.data(Qt.UserRole)
        data["tracking_area"] = tracking_area_um
        item.setData(Qt.UserRole, data)
        
        if tracking_area_um:
            print(f"Tracking area set: center=({tracking_area_um['center_x']:.1f}, {tracking_area_um['center_y']:.1f}) µm, "
                  f"size={tracking_area_um['width']:.1f}x{tracking_area_um['height']:.1f} µm")
    
    def on_rect_selected(self, rect_type, dimensions):
        """Handle rectangle selection - display properties in pattern_properties_table.
        
        rect_type: "measure", "tracking_area", or None (deselected)
        dimensions: dict with "width" and "height" in µm, or None
        """
        self.selected_rect_type = rect_type
        
        # Clear both tables when a rectangle is selected (not a pattern)
        self.group_properties_table.setRowCount(0)
        self.pattern_properties_table.setRowCount(0)
        self.selected_displayable_patterns = []
        self.selected_pattern_groups = []
        
        if rect_type is None or dimensions is None:
            return
        
        # Display rectangle properties
        rect_label = "Measurement" if rect_type == "measure" else "Tracking Area"
        
        # Set up 3 rows: Type, Width, Height
        self.pattern_properties_table.setRowCount(3)
        
        # Row 0: Type (display only)
        self.pattern_properties_table.setItem(0, 0, QTableWidgetItem("Type"))
        self.pattern_properties_table.setItem(0, 1, QTableWidgetItem(rect_label))
        
        # Row 1: Width with editable QLineEdit
        self.pattern_properties_table.setItem(1, 0, QTableWidgetItem("Width (µm)"))
        width_edit = QLineEdit()
        width_edit.setText(f"{dimensions['width']:.3f}")
        width_edit.setValidator(QDoubleValidator(0.001, 10000, 3))
        width_edit.editingFinished.connect(self._on_rect_dimension_changed)
        width_edit.setProperty("dimension", "width")
        self.pattern_properties_table.setCellWidget(1, 1, width_edit)
        
        # Row 2: Height with editable QLineEdit
        self.pattern_properties_table.setItem(2, 0, QTableWidgetItem("Height (µm)"))
        height_edit = QLineEdit()
        height_edit.setText(f"{dimensions['height']:.3f}")
        height_edit.setValidator(QDoubleValidator(0.001, 10000, 3))
        height_edit.editingFinished.connect(self._on_rect_dimension_changed)
        height_edit.setProperty("dimension", "height")
        self.pattern_properties_table.setCellWidget(2, 1, height_edit)
    
    def _on_rect_dimension_changed(self):
        """Handle rectangle dimension edit - update the rectangle size."""
        if not self.selected_rect_type:
            return
        
        # Get width and height from QLineEdit widgets
        width_widget = self.pattern_properties_table.cellWidget(1, 1)
        height_widget = self.pattern_properties_table.cellWidget(2, 1)
        
        if not width_widget or not height_widget:
            return
        
        try:
            new_width = float(width_widget.text())
            new_height = float(height_widget.text())
        except ValueError:
            return
        
        # Ensure positive values
        if new_width <= 0 or new_height <= 0:
            return
        
        # Update the rectangle
        self.image_widget.set_rect_dimensions_um(self.selected_rect_type, new_width, new_height)
    
    def _set_combo_to_current(self, combo, target_current_A):
        """Set combo box to the closest available current value."""
        # Find closest available current
        closest_idx = 0
        min_diff = float('inf')
        for i, curr in enumerate(self.available_currents):
            diff = abs(curr - target_current_A)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        combo.setCurrentIndex(closest_idx)
    
    def _on_milling_current_changed(self, index):
        """Handle milling current dropdown change - updates all selected PatternGroups."""
        if not self.selected_pattern_groups:
            return
        
        # Get the combo box to check if "(mixed)" option exists
        combo = self.pattern_properties_table.cellWidget(0, 1)
        if combo and combo.itemText(0) == "(mixed)":
            if index == 0:
                # User selected "(mixed)" - don't change anything
                return
            # Adjust index since "(mixed)" is at position 0
            adjusted_index = index - 1
        else:
            adjusted_index = index
        
        # Get the new current value
        new_current = self.available_currents[adjusted_index]
        
        # Update all selected PatternGroups
        for pg in self.selected_pattern_groups:
            pg.milling_current = new_current
        
        # Update the stored data in position list
        item = self.position_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            # The patterns are already updated by reference, but ensure data is saved
            item.setData(Qt.UserRole, data)
    
    def _on_sequential_group_changed(self, value):
        """Handle sequential group spinbox change - updates all selected PatternGroups."""
        if not self.selected_pattern_groups:
            return
        
        # Update all selected PatternGroups
        for pg in self.selected_pattern_groups:
            pg.sequential_group = value
        
        # Update the stored data in position list
        item = self.position_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            # The patterns are already updated by reference, but ensure data is saved
            item.setData(Qt.UserRole, data)
    
    def _on_delay_changed(self):
        """Handle delay edit change - updates all selected PatternGroups."""
        if not self.selected_pattern_groups:
            return
        
        # Get the delay edit widget
        delay_edit = self.group_properties_table.cellWidget(3, 1)
        if not delay_edit:
            return
        
        text = delay_edit.text().strip()
        if not text:
            return
        
        try:
            new_delay = int(text)
        except ValueError:
            return
        
        # Ensure non-negative
        if new_delay < 0:
            new_delay = 0
            delay_edit.setText(str(new_delay))
        
        # Update all selected PatternGroups
        for pg in self.selected_pattern_groups:
            pg.delay = new_delay
        
        # Update the stored data in position list
        item = self.position_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            # The patterns are already updated by reference, but ensure data is saved
            item.setData(Qt.UserRole, data)

    # -------------------------------
    # Logic
    # -------------------------------

    def toggle_protocol_editor(self):
        """Toggle visibility of the Protocol Editor panel."""
        is_visible = self.protocol_editor.isVisible()
        self.protocol_editor.setVisible(not is_visible)
        self.separator2.setVisible(not is_visible)
        if is_visible:
            self.protocol_editor_btn.setText("Protocol Editor ▶")
        else:
            self.protocol_editor_btn.setText("Protocol Editor ◀")

    def add_position(self):
        index = self.position_list.count()
        
        # Get current stage coordinates
        if MODE == "scope":
            # Returns dict with keys: x, y, z, r, t (all in meters/radians)
            coords = scope.get_stage_position()
        else:
            # Dummy coordinates for dev mode
            coords = {'x': index * 1.0, 'y': index * 2.0, 'z': index * 3.0, 'r': 0.0, 't': 0.0}

        item = QListWidgetItem()
        data = {
            "coords": coords,
            "rect": None,
            "image": None,
            "image_data": None,
            "image_metadata": None,
            "image_width": None,
            "image_height": None,
            "pixel_to_um": None,
            "patterns": [],  # List of pattern dicts
            "tracking_area": None  # Tracking area in µm coordinates
        }

        item.setData(Qt.UserRole, data)
        self.position_list.addItem(item)
        self.position_list.setCurrentItem(item)
        self.rebuild_positions()
        # Clear the image widget since no image has been taken yet
        self.image_widget.clear()

        # Auto take image if checkbox is checked
        if self.auto_take_image_checkbox.isChecked():
            self.take_ion_beam_image()

        # Auto-attach patterns if checkbox is checked
        if self.auto_attach_pattern_checkbox.isChecked():
            self.attach_xT_pattern()      

    def take_ion_beam_image(self):
        item = self.position_list.currentItem()
        if not item:
            return

        data = item.data(Qt.UserRole)
        index = self.position_list.count()

        # Obtain coordinates
        # Get current stage coordinates
        if MODE == "scope":
            # Returns dict with keys: x, y, z, r, t (all in meters/radians)
            coords = scope.get_stage_position()
        else:
            # Dummy coordinates for dev mode
            coords = {'x': index * 1.0, 'y': index * 2.0, 'z': index * 3.0, 'r': 0.0, 't': 0.0}

        # Take image
        if MODE == "scope":
            adorned_img = scope.take_image_IB()
            img = adorned_img.data
            img_metadata = adorned_img.metadata
            width = adorned_img.width
            height = adorned_img.height
            pixel_to_um = 1e6 * adorned_img.metadata.optics.scan_field_of_view.width / width
            pixel_to_um_h = 1e6 * adorned_img.metadata.optics.scan_field_of_view.height / height
            if abs(pixel_to_um - pixel_to_um_h) > 1e-6:
                print("Warning: non-square pixels detected!")
            pixmap = QPixmap.fromImage(
                QImage(
                    img, width, height, QImage.Format_Grayscale8
                )
            )
        else:
            image_filename = os.path.join("images", np.random.choice([f for f in os.listdir("images") if ".png" in f]))
            pixmap = QPixmap(image_filename)
            img = cv2.imread(image_filename, cv2.IMREAD_GRAYSCALE)
            img_metadata = image_filename
            height, width = img.shape[:2]
            pixel_to_um = PIXEL_TO_MICRON

        # Update data
        data["coords"] = coords # Update coordinates in case they changed since the position was added
        data["image"] = pixmap
        data["image_data"] = img
        data["image_metadata"] = img_metadata
        data["image_width"] = width
        data["image_height"] = height
        data["pixel_to_um"] = pixel_to_um

        item.setData(Qt.UserRole, data)
        self.rebuild_positions()

        # Load the image into the DrawableImage widget
        self.image_widget.load_image(pixmap, pixel_to_um=pixel_to_um)
        self.image_widget.load_shapes(data.get("patterns", []), locked=False)
        self.image_widget.shapes_changed_callback = self.on_shapes_changed

    def attach_xT_pattern(self):
        item = self.position_list.currentItem()
        if not item:
            print("Warning: No position selected.")
            return
        
        if MODE == "dev":
            # In dev mode with auto checkbox checked, use last loaded patterns
            if self.auto_attach_pattern_checkbox.isChecked():
                if self.last_loaded_pattern_file is not None:
                    # Reload from file (re-converts coordinates for current image)
                    self._load_pattern_file(self.last_loaded_pattern_file)
                elif self.last_loaded_patterns is not None:
                    # Use stored patterns from Protocol Editor
                    self._apply_stored_patterns()
                else:
                    self.add_protocol()
            else:
                self.add_protocol()

        elif MODE == "scope":
            data = item.data(Qt.UserRole)
            # Check if we have an image loaded
            pixmap = data.get("image")
            if pixmap is None or pixmap.isNull():
                print("Warning: No image loaded for this position. Please update position first.")
                return
            
            # Read all patterns from the active view
            all_patterns = scope.retreive_xT_patterns()
            
            # Get image dimensions and FOV for coordinate conversion
            img_w = data["image_width"]
            img_h = data["image_height"]
            pixel_to_um = data["pixel_to_um"]
            
            # Calculate field of view in meters
            fov_width_m = img_w * pixel_to_um * 1e-6
            fov_height_m = img_h * pixel_to_um * 1e-6
            
            # Convert xT patterns to PatternGroup
            pattern_group = convert_xT_patterns_to_displayable(
                all_patterns,
                img_w, img_h,
                fov_width_m, fov_height_m
            )
            
            data["patterns"] = [pattern_group]  # Store as list with one PatternGroup
            item.setData(Qt.UserRole, data)
            self.rebuild_positions()
            self.image_widget.load_shapes(data["patterns"], locked=False)
            self.image_widget.shapes_changed_callback = self.on_shapes_changed

    def add_protocol(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select protocol file",
            "",
            "Pattern files (*.ptf);;All files (*)"
        )

        if not file_path:
            return  # user cancelled

        print("Selected file:", file_path)
        self._load_pattern_file(file_path)

    def _load_pattern_file(self, file_path):
        """Load patterns from a .ptf file and attach to current position."""
        item = self.position_list.currentItem()
        if not item:
            return
            
        data = item.data(Qt.UserRole)
        
        # Check if we have an image loaded
        pixmap = data.get("image")
        if pixmap is None or pixmap.isNull():
            print("Warning: No image loaded for this position. Please update position first.")
            return
        
        img_w = data["image_width"]
        img_h = data["image_height"]
        pixel_to_um = data["pixel_to_um"]
        
        # Calculate field of view in meters
        # pixel_to_um is µm/pixel, so FOV = pixels * µm/pixel * 1e-6 = meters
        fov_width_m = img_w * pixel_to_um * 1e-6
        fov_height_m = img_h * pixel_to_um * 1e-6
        
        print(f"Image size: {img_w} x {img_h} pixels")
        print(f"FOV: {fov_width_m*1e6:.1f} x {fov_height_m*1e6:.1f} µm")
        
        # Load patterns and convert to PatternGroup
        pattern_group = load_patterns_for_display(
            file_path,
            img_w, img_h,
            fov_width_m, fov_height_m
        )
        
        data["patterns"] = [pattern_group]  # Store as list with one PatternGroup
        item.setData(Qt.UserRole, data)
        self.rebuild_positions()
        self.image_widget.load_shapes(data["patterns"], locked=False)
        self.image_widget.shapes_changed_callback = self.on_shapes_changed
        
        # Remember this pattern file for auto-add (clear stored patterns since we use file)
        self.last_loaded_pattern_file = file_path
        self.last_loaded_patterns = None
    
    def set_last_loaded_patterns(self, patterns_list):
        """Store patterns from Protocol Editor for auto-add functionality.
        
        patterns_list is now a list of PatternGroup objects.
        """
        # Clone the PatternGroups to avoid reference issues
        self.last_loaded_patterns = [pg.clone() for pg in patterns_list]
        # Clear file path since these patterns are from Protocol Editor
        self.last_loaded_pattern_file = None
    
    def _apply_stored_patterns(self):
        """Apply stored patterns (from Protocol Editor) to current position."""
        item = self.position_list.currentItem()
        if not item or not self.last_loaded_patterns:
            return
        
        data = item.data(Qt.UserRole)
        
        # Clone the stored PatternGroups for this position
        patterns_list = [pg.clone() for pg in self.last_loaded_patterns]
        
        # Store patterns in position data (even without image)
        data["patterns"] = patterns_list
        item.setData(Qt.UserRole, data)
        self.rebuild_positions()
        
        # Only display if we have an image loaded
        pixmap = data.get("image")
        if pixmap is not None and not pixmap.isNull():
            self.image_widget.load_shapes(data["patterns"], locked=False)
            self.image_widget.shapes_changed_callback = self.on_shapes_changed

    def on_item_clicked(self, item):
        data = item.data(Qt.UserRole)

        if data["image"] is not None:
            self.image_widget.load_image(data["image"], pixel_to_um=data.get("pixel_to_um"))
            self.image_widget.load_rectangle(data["rect"])
            self.image_widget.load_shapes(data.get("patterns", []), locked=False)
            # Load tracking area if it exists
            if data.get("tracking_area"):
                self.image_widget.load_tracking_area(data["tracking_area"])
        else:
            self.image_widget.clear()

        self.image_widget.shapes_changed_callback = self.on_shapes_changed
        # Clear property table when switching positions
        self.pattern_properties_table.setRowCount(0)

    def on_pattern_selected(self, displayable_patterns):
        """Handle pattern selection - display properties in tables.
        
        displayable_patterns is now a list of selected patterns.
        Shows shared values, blank for different values.
        Group properties (milling current, color, sequential group) shown in group table.
        Pattern properties shown in pattern table.
        """
        self.group_properties_table.setRowCount(0)
        self.pattern_properties_table.setRowCount(0)
        self.selected_displayable_patterns = displayable_patterns  # Store reference
        self.selected_rect_type = None  # Clear rectangle selection when patterns are selected
        
        # Get the PatternGroups for the selected patterns
        self.selected_pattern_groups = self.image_widget._get_selected_pattern_groups()
        
        if not displayable_patterns:
            return
        
        # Helper to format values
        def format_value(value):
            if isinstance(value, float):
                if abs(value) < 1e-3 and value != 0:
                    return f"{value:.2e}"
                elif abs(value) < 1:
                    return f"{value:.4f}"
                else:
                    return f"{value:.2f}"
            return str(value)
        
        # =====================
        # Populate Group Properties Table
        # =====================
        if self.selected_pattern_groups:
            # Get values from PatternGroups
            milling_currents = [pg.milling_current for pg in self.selected_pattern_groups]
            colors = [pg.color for pg in self.selected_pattern_groups]
            sequential_groups = [pg.sequential_group for pg in self.selected_pattern_groups]
            delays = [pg.delay for pg in self.selected_pattern_groups]
            
            all_same_current = len(set(milling_currents)) == 1
            all_same_color = len(set(colors)) == 1
            all_same_seq_group = len(set(sequential_groups)) == 1
            all_same_delay = len(set(delays)) == 1
            
            # 4 rows: Milling Current, Color, Sequential Group, Delay
            self.group_properties_table.setRowCount(4)
            
            # Row 0: Milling current with dropdown
            self.group_properties_table.setItem(0, 0, QTableWidgetItem("Milling Current"))
            current_combo = QComboBox()
            current_options = [self._current_to_nA_str(c) for c in self.available_currents]
            current_combo.addItems(current_options)
            
            if all_same_current:
                self._set_combo_to_current(current_combo, milling_currents[0])
            else:
                current_combo.insertItem(0, "(mixed)")
                current_combo.setCurrentIndex(0)
            
            current_combo.currentIndexChanged.connect(self._on_milling_current_changed)
            self.group_properties_table.setCellWidget(0, 1, current_combo)
            
            # Row 1: Color (display only)
            self.group_properties_table.setItem(1, 0, QTableWidgetItem("Color"))
            if all_same_color:
                r, g, b = colors[0]
                color_item = QTableWidgetItem(f"RGB({r}, {g}, {b})")
                color_item.setBackground(QColor(r, g, b))
                # Set text color for contrast
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                color_item.setForeground(QColor(0, 0, 0) if brightness > 128 else QColor(255, 255, 255))
                self.group_properties_table.setItem(1, 1, color_item)
            else:
                self.group_properties_table.setItem(1, 1, QTableWidgetItem("(mixed)"))
            
            # Row 2: Sequential Group with editable spinbox
            self.group_properties_table.setItem(2, 0, QTableWidgetItem("Sequential Group"))
            seq_spinbox = QSpinBox()
            seq_spinbox.setMinimum(0)
            seq_spinbox.setMaximum(999)
            if all_same_seq_group:
                seq_spinbox.setValue(sequential_groups[0])
            else:
                seq_spinbox.setSpecialValueText("(mixed)")
                seq_spinbox.setValue(0)
            seq_spinbox.valueChanged.connect(self._on_sequential_group_changed)
            self.group_properties_table.setCellWidget(2, 1, seq_spinbox)
            
            # Row 3: Delay with editable QLineEdit (no arrows)
            self.group_properties_table.setItem(3, 0, QTableWidgetItem("Delay (s)"))
            delay_edit = QLineEdit()
            delay_edit.setValidator(QIntValidator(0, 999999))
            if all_same_delay:
                delay_edit.setText(str(delays[0]))
            else:
                delay_edit.setPlaceholderText("(mixed)")
            delay_edit.editingFinished.connect(self._on_delay_changed)
            self.group_properties_table.setCellWidget(3, 1, delay_edit)
        
        # =====================
        # Populate Pattern Properties Table
        # =====================
        # Properties to exclude from display
        exclude_props = {'coords', '_id'}
        
        # Build property list - collect values from all patterns
        first_pattern = displayable_patterns[0].pattern
        if not first_pattern:
            return
        
        from dataclasses import fields
        properties = []
        for f in fields(first_pattern):
            name = f.name
            if name in exclude_props or name.startswith('_'):
                continue
            
            # Collect values from all selected patterns
            values = []
            for dp in displayable_patterns:
                if dp.pattern:
                    values.append(getattr(dp.pattern, name))
            
            # Check if all values are the same
            if len(set(str(v) for v in values)) == 1:
                value_str = format_value(values[0])
            else:
                value_str = "(mixed)"
            
            properties.append((name.replace('_', ' ').title(), value_str))
        
        # Populate the pattern properties table
        self.pattern_properties_table.setRowCount(len(properties))
        
        for row, (prop_name, prop_value) in enumerate(properties):
            self.pattern_properties_table.setItem(row, 0, QTableWidgetItem(prop_name))
            self.pattern_properties_table.setItem(row, 1, QTableWidgetItem(prop_value))

    def on_shapes_changed(self, updated_shapes):
        """Handle shape changes - updates patterns in position data."""
        item = self.position_list.currentItem()
        if not item:
            return

        data = item.data(Qt.UserRole)
        patterns_list = data.get("patterns", [])
        
        # Get image dimensions and pixel_to_um for coordinate conversion
        img_w = data.get("image_width")
        img_h = data.get("image_height")
        pixel_to_um = data.get("pixel_to_um")
        
        # Calculate meters per pixel and image center
        if pixel_to_um is not None and img_w is not None and img_h is not None:
            m_per_px = pixel_to_um * 1e-6
            center_px_x = img_w / 2
            center_px_y = img_h / 2
        else:
            m_per_px = None

        # Update coords in all PatternGroups in the list
        for item_pg in patterns_list:
            # Handle both PatternGroup objects and legacy dict format
            if hasattr(item_pg, 'patterns'):
                pattern_dict = item_pg.patterns
            else:
                pattern_dict = item_pg
                
            for pid, coords in updated_shapes.items():
                if pid in pattern_dict:
                    dp = pattern_dict[pid]
                    # Update pixel coords
                    dp.coords = coords
                    
                    # Also update the pattern's meter coordinates if we have the conversion factor
                    if m_per_px is not None and len(coords) > 0:
                        # Convert pixel coords to meters
                        meter_coords = []
                        for x_px, y_px in coords:
                            x_m = (x_px - center_px_x) * m_per_px
                            y_m = (center_px_y - y_px) * m_per_px  # Flip Y
                            meter_coords.append((x_m, y_m))
                        
                        pattern = dp.pattern
                        # Update pattern center (average of all vertices)
                        avg_x = sum(c[0] for c in meter_coords) / len(meter_coords)
                        avg_y = sum(c[1] for c in meter_coords) / len(meter_coords)
                        
                        if hasattr(pattern, 'center_x'):
                            pattern.center_x = avg_x
                        if hasattr(pattern, 'center_y'):
                            pattern.center_y = avg_y
                        
                        # Handle different pattern types
                        # PolygonPattern: update vertices
                        if hasattr(pattern, 'vertices'):
                            pattern.vertices = meter_coords
                        
                        # LinePattern: update start/end points and length
                        if hasattr(pattern, 'start_x') and hasattr(pattern, 'end_x') and len(meter_coords) >= 2:
                            pattern.start_x = meter_coords[0][0]
                            pattern.start_y = meter_coords[0][1]
                            pattern.end_x = meter_coords[1][0]
                            pattern.end_y = meter_coords[1][1]
                            # Recalculate length
                            import math
                            pattern.length = math.sqrt(
                                (pattern.end_x - pattern.start_x)**2 + 
                                (pattern.end_y - pattern.start_y)**2
                            )

        data["patterns"] = patterns_list
        item.setData(Qt.UserRole, data)
        self.rebuild_positions()
        
        # Refresh the pattern properties table if patterns are selected
        if self.selected_displayable_patterns:
            self.on_pattern_selected(self.selected_displayable_patterns)

    def rebuild_positions(self):
        self.positions.clear()

        for i in range(self.position_list.count()):
            item = self.position_list.item(i)
            data = item.data(Qt.UserRole)

            self.positions[i] = data

            coords = data['coords']
            if isinstance(coords, dict):
                coord_str = f"x={coords['x']*1e6:.1f}, y={coords['y']*1e6:.1f}, z={coords['z']*1e6:.1f} µm"
            else:
                coord_str = str(coords)
            
            text = f"Position {i}: {coord_str}"
            if data["rect"]:
                text += f" | Rect: {data['rect']}"

            item.setText(text)

        # Debug
        print("\nUpdated positions dictionary:")
        for k, v in self.positions.items():
            print(k, v)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def build_task_list(self):
        # Find the macimum sequential group number
        max_sequential_group = 0
        for i in range(self.position_list.count()):
            item = self.position_list.item(i)
            data = item.data(Qt.UserRole)
            for pg in data.get("patterns", []):
                if pg.sequential_group > max_sequential_group:
                    max_sequential_group = pg.sequential_group
        
        # Loop through sequential groups and the patterngroups within them
        task_list = []
        for sg in range(max_sequential_group + 1):
            for i in range(self.position_list.count()):
                item = self.position_list.item(i)
                data = item.data(Qt.UserRole)
                image_width = data.get("image_width", None)
                image_height = data.get("image_height", None)
                for pg in data.get("patterns", []):
                    # If this pattern group  is not in the current sequential group, skip and add it later
                    if pg.sequential_group != sg:
                        continue
                    # Otherwise, create a task for this pattern group
                    task = Task()
                    task.patterns = pg.patterns
                    task.milling_current = pg.milling_current
                    task.delay = pg.delay
                    task.coords = data.get("coords", {})
                    task.tracking_area = relative_coords(data.get("tracking_area", None), image_width, image_height)
                    task.ref_image = data["image_data"]
                    task_list.append(task)

        return task_list

    def run(self):
        # Run the milling tasks
        task_list = self.build_task_list()
        print(f"Made a task list with {len(task_list)} tasks.")

        for task_idx, task in enumerate(task_list):
            print(f"Running task {task_idx+1}/{len(task_list)} with {len(task.patterns)} patterns, "
                  f"current={task.milling_current*1e9:.1f} nA, delay={task.delay} s")
            if MODE == "dev":
                print("  (dev mode - not actually milling)")
                continue
            elif MODE == "scope":
                if task.delay > 0:
                    print(f"  Waiting for {task.delay} seconds before starting...")
                    if task.delay > MAX_DELAY_NO_HOME:
                        print(f"The delay is more than {MAX_DELAY_NO_HOME} seconds. Going in sleep mode.")
                        # GO IN SLEEP MODE
                        scope.enter_sleep_mode()
                    time.sleep(task.delay)

                scope.ion_on()
                scope.move_stage_absolute(task.coords)
                # TO DO NEXT:
                # 1. Image alignment at low current
                # 2. Change current to milling current and align using:
                    # Define a sub-area using Rectangle(left, top, width, height)
                    # All values are normalized (0.0 to 1.0, relative to full frame)
                    # settings = GrabFrameSettings(reduced_area=Rectangle(0.6, 0.6, 0.3, 0.3))
                    # image = microscope.imaging.grab_frame(settings)
                # Send patterns to scope and mill

# -------------------------------------------------    
class Pattern():
    def __init__(self):
        self.coords = []
        self.type = None
        self.depth = 0
        self.scan_direction = None
        self.scan_type = None
        self.dwell_time = 0
        self.enable = True

    def clone(self):
        p = Pattern()
        p.coords = [(x, y) for x, y in self.coords]
        p.type = self.type
        p.depth = self.depth
        p.scan_direction = self.scan_direction
        p.scan_type = self.scan_type
        p.dwell_time = self.dwell_time
        p.enable = self.enable
        return p
    
class Task(): 
    def __init__(self):
        self.patterns = []
        self.milling_current = 0.0  # in Amperes
        self.delay = 0
        self.coords = None  # position coordinates for this task
        self.tracking_area = None  # dict with relative coords
        self.ref_image = None  # Numpy array of reference image

def relative_coords(tracking_area, image_width, image_height):
    """Convert absolute tracking area coords to relative (0-1) based on image size."""
    rel_tracking_area = {}
    rel_tracking_area["width"] = tracking_area["width"] / image_width
    rel_tracking_area["height"] = tracking_area["height"] / image_height
    rel_tracking_area["left"] = tracking_area["left"] / image_width
    rel_tracking_area["top"] = tracking_area["top"] / image_height
    return rel_tracking_area
        
def parse_ptf(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    valid_tags = ['PatternRectangle','PatternPolygon']
    pattern_dict = {}
    pattern_id = -1
    for element in root:
        if element.tag in valid_tags:
            pattern_id += 1
            p = Pattern()
            p.type = 'Rectangle'
            p.depth = float(element.find('Depth').text)
            p.dwell_time = float(element.find('DwellTime').text)
            p.scan_direction = str(element.find('ScanDirection').text)
            p.scan_type = str(element.find('ScanType').text)
        if element.tag == 'PatternRectangle':
            cx = float(element.find('CenterX').text)*1e6 / PIXEL_TO_MICRON
            cy = float(element.find('CenterY').text)*1e6 / PIXEL_TO_MICRON
            height = float(element.find('Length').text)*1e6 / PIXEL_TO_MICRON
            width = float(element.find('Width').text)*1e6 / PIXEL_TO_MICRON
            p.coords = [
                (cx - width/2, cy - height/2),
                (cx + width/2, cy - height/2),
                (cx + width/2, cy + height/2),
                (cx - width/2, cy + height/2),
            ]
            pattern_dict[pattern_id] = p
        elif element.tag == 'PatternPolygon':
            cx = float(element.find('CenterX').text)*1e6 / PIXEL_TO_MICRON
            cy = float(element.find('CenterY').text)*1e6 / PIXEL_TO_MICRON
            print(f"coordinates: {cx}, {cy}")
            points_elem = element.find('Points')
            # Unescape &lt; &gt; etc.
            points_xml_str = html.unescape(points_elem.text.strip())
            # Parse the inner XML
            points_root = ET.fromstring(points_xml_str)
            coords = []
            for point in points_root.findall("Point"):
                x = float(point.find("PositionX").text)*1e6 / PIXEL_TO_MICRON 
                y = float(point.find("PositionY").text)*1e6 / PIXEL_TO_MICRON 
                coords.append((x, y))
            p.coords = coords
            pattern_dict[pattern_id] = p

    return pattern_dict

def center_shapes(pattern_dict,offset_x=0,offset_y=0,flip_y_around=None):
    
    for id,shape in pattern_dict.items():
        if flip_y_around is not None:
            shape.coords = [
                (int(p[0]+offset_x), int(flip_y_around - (p[1]+offset_y))) for p in shape.coords
            ]
        else:
            shape.coords = [
                (int(p[0]+offset_x), int(p[1]+offset_y)) for p in shape.coords
            ]
        pattern_dict[id] = shape
    return pattern_dict

# -------------------------------------------------
# Entry Point
# -------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
