import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QFrame, QFileDialog, QCheckBox
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QRect, QPoint
import numpy as np
import xml.etree.ElementTree as ET
import html



PIXEL_TO_MICRON = 1/50


# -------------------------------------------------
# Drawable Image Widget
# -------------------------------------------------

class DrawableImage(QLabel):
    def __init__(self, image_path):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(1,1)

        self.original_pixmap = QPixmap(image_path)
        self.scaled_pixmap = None
        self.offset_x = 0
        self.offset_y = 0

        self.start_point = None
        self.preview_rect_img = None      # red in widget coords
        self.active_rect_img = None   # green in **image coordinates**

        # polygon editor
        self.polygons_img = [] # list[{"id": int, "points": list[QPoint]}]
        self.drag_start_img = None
        self.start_point_img = None
        self.is_dragging_shapes = False
        self.is_drawing_rect = False
        self.shapes_dirty = False
        self.shapes_changed_callback = None


    def resizeEvent(self, event):
        if not self.original_pixmap.isNull():
            self.scaled_pixmap = self.original_pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            # Compute top-left offset to center the image
            self.offset_x = (self.width() - self.scaled_pixmap.width()) // 2
            self.offset_y = (self.height() - self.scaled_pixmap.height()) // 2
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 10))

        # Draw scaled image
        if self.scaled_pixmap:
            painter.drawPixmap(self.offset_x, self.offset_y, self.scaled_pixmap)

        # Draw preview rectangle (red)
        if self.preview_rect_img:
            rect_widget = self._image_rect_to_widget(self.preview_rect_img)
            self._draw_rect_with_measurements_widget(painter, rect_widget, Qt.red)

        # Draw active rectangle (green)
        if self.active_rect_img:
            rect_widget = self._image_rect_to_widget(self.active_rect_img)
            self._draw_rect_with_measurements_widget(painter, rect_widget, Qt.green)
    
        if self.polygons_img:
            pen = QPen(Qt.yellow, 2)
            painter.setPen(pen)
            brush = QBrush(QColor(255, 255, 0, 50))
            painter.setBrush(brush)
            for poly in self.polygons_img:
                painter.drawPolygon(
                    *[self._image_point_to_widget(p) for p in poly["points"]]
                )

    def load_shapes(self, shapes):
        self.polygons_img = [
            {
                "id": sid,
                "points": [QPoint(x, y) for x, y in pattern.coords]
            }
            for sid, pattern in shapes.items()
        ]
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

    # -------------------------------
    # Mouse interactions
    # -------------------------------

    def mousePressEvent(self, event):
        if not self.scaled_pixmap:
            return

        img_point = self._widget_to_image_point(event.pos())

        if event.button() == Qt.LeftButton:
            if self.polygons_img and self._point_in_any_polygon(img_point):
                self.drag_start_img = img_point
                self.is_dragging_shapes = True
            else:
                self.is_dragging_shapes = False

        elif event.button() == Qt.RightButton:
            self.start_point_img = img_point
            self.preview_rect_img = None
            self.is_drawing_rect = True

        self.update()

    def mouseMoveEvent(self, event):
        if not self.scaled_pixmap:
            return

        if self.is_dragging_shapes and self.drag_start_img:
            current_img = self._widget_to_image_point(event.pos())
            dx = current_img.x() - self.drag_start_img.x()
            dy = current_img.y() - self.drag_start_img.y()

            for poly in self.polygons_img:
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
            self.preview_rect_img = QRect(
                self.start_point_img, current_img
            ).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_dragging_shapes and self.shapes_dirty:
                if self.shapes_changed_callback:
                    self.shapes_changed_callback(self.get_shapes())

            self.is_dragging_shapes = False
            self.drag_start_img = None
            self.shapes_dirty = False

        elif event.button() == Qt.RightButton:
            self.is_drawing_rect = False
            self.start_point_img = None

        self.update()

    def load_image(self, filename):
        pixmap = QPixmap(filename)
        if pixmap.isNull():
            print(f"Failed to load image: {filename}")
            return
        self.original_pixmap = pixmap
        self.scaled_pixmap = None
        self.preview_rect_img = None
        self.active_rect_img = None
        self.start_point_img = None
        self.polygons_img = []
        self.is_dragging_shapes = False
        self.shapes_dirty = False

        # Force scaled pixmap update
        self.scaled_pixmap = self.original_pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.offset_x = (self.width() - self.scaled_pixmap.width()) // 2
        self.offset_y = (self.height() - self.scaled_pixmap.height()) // 2

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

    # -------------------------------
    # Draw rectangle + measurements
    # -------------------------------
    def _draw_rect_with_measurements_widget(self, painter, rect, color):
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.drawRect(rect)

        # width and height in µm using image coordinates
        width_um = rect.width() / self.scaled_pixmap.width() * self.original_pixmap.width() * PIXEL_TO_MICRON
        height_um = rect.height() / self.scaled_pixmap.height() * self.original_pixmap.height() * PIXEL_TO_MICRON

        # Width text
        width_text = f"{width_um:.1f} µm"
        painter.drawText(rect.center().x() - 30, rect.top() - 5, width_text)

        # Height text (rotated)
        height_text = f"{height_um:.1f} µm"
        painter.save()
        painter.translate(rect.left() - 10, rect.center().y() + 30)
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Protocol Editor")
        #self.showFullScreen()

        self.positions = {}

        # Layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left panel
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)

        self.position_list = PositionList()
        self.position_list.model().rowsMoved.connect(self.rebuild_positions)
        self.position_list.itemClicked.connect(self.on_item_clicked)

        add_position_btn = QPushButton("Add Position")
        add_position_btn.clicked.connect(self.add_position)

        add_protocol_btn = QPushButton("Add Protocol")
        add_protocol_btn.clicked.connect(self.add_protocol)

        self.auto_add_checkbox = QCheckBox("Auto add")

        left_layout.addWidget(self.position_list, stretch=3)
        left_layout.addWidget(add_position_btn)
        left_layout.addWidget(add_protocol_btn)
        left_layout.addWidget(self.auto_add_checkbox)
        left_layout.addStretch(1)

        # Image panel
        self.image_widget = DrawableImage("logo.png")

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)

        # Assemble
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(separator)
        main_layout.addWidget(self.image_widget, 4)

        self.last_loaded_patterns = None

    # -------------------------------
    # Logic
    # -------------------------------

    def add_position(self):
        index = self.position_list.count()
        coords = (index * 1.0, index * 2.0, index * 3.0)
        # Choose image filename. Later: take image
        image_filename = os.path.join("images",np.random.choice([f for f in os.listdir("images") if ".png" in f]))
        item = QListWidgetItem()
        data = {
            "coords": coords,
            "rect": None,
            "image": image_filename,
            "patterns": {}
        }
        # AUTO ADD LOGIC
        if (self.auto_add_checkbox.isChecked()
            and self.last_loaded_patterns is not None):
            # deep copy so positions are independent
            data["patterns"] = {
                pid: pattern.clone()
                for pid, pattern in self.last_loaded_patterns.items()
            }

        item.setData(Qt.UserRole, data)
        self.position_list.addItem(item)
        self.position_list.setCurrentItem(item)
        self.rebuild_positions()
        # Load the image immediately into the DrawableImage widget
        self.image_widget.load_image(image_filename)
        self.image_widget.load_shapes(data.get("patterns", {}))
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
        pattern_dict = parse_ptf(file_path)

        item = self.position_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            # Load image so we know its size
            pixmap = QPixmap(data["image"])
            img_w, img_h = pixmap.width(), pixmap.height()
            pattern_dict = center_shapes(pattern_dict, offset_x=img_w//2, offset_y=img_h//2, flip_y_around=img_h)
            data["patterns"] = {
                pid: pattern.clone()
                for pid, pattern in pattern_dict.items()
            }
            item.setData(Qt.UserRole, data)
            self.rebuild_positions()
            self.image_widget.load_shapes(pattern_dict)
            self.image_widget.shapes_changed_callback = self.on_shapes_changed
            # Remember this pattern as the last loaded pattern
            self.last_loaded_patterns = {
                pid: pattern.clone()
                for pid, pattern in data["patterns"].items()
            }

    def on_item_clicked(self, item):
        data = item.data(Qt.UserRole)

        self.image_widget.load_image(data["image"])
        self.image_widget.load_rectangle(data["rect"])
        self.image_widget.load_shapes(data.get("patterns", {}))

        self.image_widget.shapes_changed_callback = (
            lambda shapes, item=item: self.update_shapes(item, shapes)
        )
        self.image_widget.shapes_changed_callback = self.on_shapes_changed

    def on_shapes_changed(self,updated_shapes):
        item = self.position_list.currentItem()
        if not item:
            return

        data = item.data(Qt.UserRole)
        patterns = data.get("patterns", {})

        for pid, coords in updated_shapes.items():
            if pid in patterns:
                patterns[pid].coords = coords

        data["patterns"] = patterns
        item.setData(Qt.UserRole, data)
        self.rebuild_positions()

    def update_shapes(self, item, shapes):
        data = item.data(Qt.UserRole)
        data["shapes"] = shapes
        item.setData(Qt.UserRole, data)
        self.rebuild_positions()

    def rebuild_positions(self):
        self.positions.clear()

        for i in range(self.position_list.count()):
            item = self.position_list.item(i)
            data = item.data(Qt.UserRole)

            self.positions[i] = data

            text = f"Position {i}: {data['coords']}"
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

    def random_polygon(self, img_w, img_h):
        cx = np.random.randint(img_w // 4, 3 * img_w // 4)
        cy = np.random.randint(img_h // 4, 3 * img_h // 4)
        size = min(img_w, img_h) // 10

        return [
            (cx - size, cy - size),
            (cx + size, cy - size),
            (cx + size, cy + size),
            (cx - size, cy + size),
        ]
    
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
