import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLineEdit, QComboBox, QGroupBox, QScrollArea, QFormLayout, QFrame,
    QTabWidget, QSpinBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from src.CustomPatterns import RectanglePattern, PolygonPattern, DisplayablePattern, PatternGroup


class ProtocolEditor(QWidget):
    """Widget for creating block preparation and polishing patterns."""
    
    # Which pattern indices belong to which current group (for block prep)
    ENABLE_PATTERNS = {
        'coarse': [0, 8],
        'medium': [0, 4, 5, 7, 9, 14, 11, 12, 13],
        'fine': [0, 1, 2, 3, 6, 10]
    }
    
    # Default currents in Amperes for dev mode
    DEV_MODE_CURRENTS = [0.1e-9, 15e-9, 50e-9, 65e-9]  # 0.1nA, 15nA, 50nA, 65nA
    
    # Default current selections (in Amperes)
    DEFAULT_COARSE_CURRENT = 65e-9   # 65 nA
    DEFAULT_MEDIUM_CURRENT = 50e-9   # 50 nA
    DEFAULT_FINE_CURRENT = 15e-9     # 15 nA
    DEFAULT_POLISH_CURRENT = 0.1e-9  # 0.1 nA for polishing
    
    # Hard-coded pattern properties from reference PTF file
    # Pattern index -> (scan_direction, enabled)
    # All patterns share: dwell_time=1e-6, scan_type="Serpentine", application_file="Si"
    PATTERN_PROPERTIES = {
        0:  {'scan_direction': 'DynamicAllDirections', 'enabled': False},  # Block (reference, disabled)
        1:  {'scan_direction': 'BottomToTop', 'enabled': True},            # inner bottom
        2:  {'scan_direction': 'LeftToRight', 'enabled': True},            # inner left top
        3:  {'scan_direction': 'RightToLeft', 'enabled': True},            # inner right
        4:  {'scan_direction': 'RightToLeft', 'enabled': True},            # outer right
        5:  {'scan_direction': 'BottomToTop', 'enabled': True},            # outer bottom
        6:  {'scan_direction': 'TopToBottom', 'enabled': True},            # inner top
        7:  {'scan_direction': 'LeftToRight', 'enabled': True},            # outer left top
        8:  {'scan_direction': 'TopToBottom', 'enabled': True},            # trench top
        9:  {'scan_direction': 'LeftToRight', 'enabled': True},            # outer left bottom
        10: {'scan_direction': 'LeftToRight', 'enabled': True},            # inner left bottom
        11: {'scan_direction': 'LeftToRight', 'enabled': True},            # needle gap right top
        12: {'scan_direction': 'RightToLeft', 'enabled': True},            # outer left trench
        13: {'scan_direction': 'LeftToRight', 'enabled': True},            # needle gap
        14: {'scan_direction': 'TopToBottom', 'enabled': True},            # outer top
    }
    
    def __init__(self, parent=None, mode="dev", scope=None):
        super().__init__(parent)
        self.main_window = parent
        self.mode = mode
        self.scope = scope
        self.available_currents = self._get_available_currents()
        self.setup_ui_with_tabs()
    
    def _get_available_currents(self):
        """Get available milling currents based on mode."""
        if self.mode == "scope" and self.scope is not None:
            try:
                # Get from microscope - values are in Amperes
                values = self.scope.beams.ion_beam.beam_current.available_values
                return sorted(values)
            except Exception as e:
                print(f"Warning: Could not get beam currents from scope: {e}")
                return self.DEV_MODE_CURRENTS
        else:
            return self.DEV_MODE_CURRENTS
    
    def _current_to_nA_str(self, current_A):
        """Convert current in Amperes to nA string for display."""
        nA = current_A * 1e9
        if nA < 1:
            return f"{nA:.1f} nA"
        else:
            return f"{nA:.0f} nA"
    
    def _nA_str_to_current(self, nA_str):
        """Convert nA string back to Amperes."""
        # Parse "X nA" or "X.X nA" format
        value = float(nA_str.replace(" nA", "").strip())
        return value * 1e-9
    
    def setup_ui_with_tabs(self):
        """Setup UI with tabs for Block Preparation and Polishing."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Protocol Editor")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget, stretch=1)
        
        # Add Block Preparation tab
        block_prep_tab = self._create_block_prep_tab()
        self.tab_widget.addTab(block_prep_tab, "Block Preparation")
        
        # Add Polishing tab
        polishing_tab = self._create_polishing_tab()
        self.tab_widget.addTab(polishing_tab, "Polishing")
    
    def _create_block_prep_tab(self):
        """Create the Block Preparation tab content."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Scroll area for parameters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # GROUP 1: Block parameters
        block_group = QGroupBox("Block parameters")
        block_layout = QFormLayout(block_group)
        self.block_width_um = QLineEdit("40")
        self.block_height_um = QLineEdit("35")
        self.block_depth_um = QLineEdit("30")
        block_layout.addRow("Block width (μm):", self.block_width_um)
        block_layout.addRow("Block height (μm):", self.block_height_um)
        block_layout.addRow("Block depth (μm):", self.block_depth_um)
        
        # Liftout mode dropdown
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["TopDown", "Planar"])
        block_layout.addRow("Liftout mode:", self.mode_combo)
        scroll_layout.addWidget(block_group)
        
        # GROUP 2: Outer & Inner pattern
        pattern_group = QGroupBox("Outer & Inner pattern")
        pattern_layout = QFormLayout(pattern_group)
        self.outer_pattern_size_um = QLineEdit("10")
        self.outer_margin_um = QLineEdit("5")
        self.inner_pattern_size_um = QLineEdit("8")
        self.inner_margin_um = QLineEdit("0.5")
        pattern_layout.addRow("Outer pattern size (μm):", self.outer_pattern_size_um)
        pattern_layout.addRow("Outer margin (μm):", self.outer_margin_um)
        pattern_layout.addRow("Inner pattern size (μm):", self.inner_pattern_size_um)
        pattern_layout.addRow("Inner margin (μm):", self.inner_margin_um)
        scroll_layout.addWidget(pattern_group)
        
        # GROUP 3: Milling currents
        current_group = QGroupBox("Milling currents")
        current_layout = QFormLayout(current_group)
        
        # Build current options list
        current_options = [self._current_to_nA_str(c) for c in self.available_currents]
        
        # Coarse current (65nA default)
        self.do_coarse = QCheckBox()
        self.do_coarse.setChecked(True)
        self.coarse_current_combo = QComboBox()
        self.coarse_current_combo.addItems(current_options)
        self._set_combo_to_current(self.coarse_current_combo, self.DEFAULT_COARSE_CURRENT)
        self.coarse_seq_group = QSpinBox()
        self.coarse_seq_group.setMinimum(0)
        self.coarse_seq_group.setMaximum(999)
        self.coarse_seq_group.setValue(0)
        self.coarse_seq_group.setFixedWidth(50)
        coarse_row = QHBoxLayout()
        coarse_row.addWidget(self.do_coarse)
        coarse_row.addWidget(self.coarse_current_combo)
        coarse_row.addWidget(QLabel("Seq:"))
        coarse_row.addWidget(self.coarse_seq_group)
        coarse_row.addStretch()
        current_layout.addRow("Coarse:", coarse_row)
        
        # Medium current (50nA default)
        self.do_medium = QCheckBox()
        self.do_medium.setChecked(True)
        self.medium_current_combo = QComboBox()
        self.medium_current_combo.addItems(current_options)
        self._set_combo_to_current(self.medium_current_combo, self.DEFAULT_MEDIUM_CURRENT)
        self.medium_seq_group = QSpinBox()
        self.medium_seq_group.setMinimum(0)
        self.medium_seq_group.setMaximum(999)
        self.medium_seq_group.setValue(0)
        self.medium_seq_group.setFixedWidth(50)
        medium_row = QHBoxLayout()
        medium_row.addWidget(self.do_medium)
        medium_row.addWidget(self.medium_current_combo)
        medium_row.addWidget(QLabel("Seq:"))
        medium_row.addWidget(self.medium_seq_group)
        medium_row.addStretch()
        current_layout.addRow("Medium:", medium_row)
        
        # Fine current (15nA default)
        self.do_fine = QCheckBox()
        self.do_fine.setChecked(True)
        self.fine_current_combo = QComboBox()
        self.fine_current_combo.addItems(current_options)
        self._set_combo_to_current(self.fine_current_combo, self.DEFAULT_FINE_CURRENT)
        self.fine_seq_group = QSpinBox()
        self.fine_seq_group.setMinimum(0)
        self.fine_seq_group.setMaximum(999)
        self.fine_seq_group.setValue(1)
        self.fine_seq_group.setFixedWidth(50)
        fine_row = QHBoxLayout()
        fine_row.addWidget(self.do_fine)
        fine_row.addWidget(self.fine_current_combo)
        fine_row.addWidget(QLabel("Seq:"))
        fine_row.addWidget(self.fine_seq_group)
        fine_row.addStretch()
        current_layout.addRow("Fine:", fine_row)
        
        scroll_layout.addWidget(current_group)
        
        # GROUP 4: Extra parameters
        extra_group = QGroupBox("Extra parameters")
        extra_layout = QFormLayout(extra_group)
        self.milling_angle = QLineEdit("10")
        self.pattern_overlap_X = QLineEdit("100")
        self.pattern_overlap_Y = QLineEdit("100")
        self.bridge_width_um = QLineEdit("15")
        self.needle_gap_width_um = QLineEdit("25")
        self.needle_gap_height_um = QLineEdit("65")
        extra_layout.addRow("Milling angle:", self.milling_angle)
        extra_layout.addRow("Pattern overlap X (%):", self.pattern_overlap_X)
        extra_layout.addRow("Pattern overlap Y (%):", self.pattern_overlap_Y)
        extra_layout.addRow("Bridge thickness (μm):", self.bridge_width_um)
        extra_layout.addRow("Needle gap width (μm):", self.needle_gap_width_um)
        extra_layout.addRow("Needle gap height (μm):", self.needle_gap_height_um)
        scroll_layout.addWidget(extra_group)
        
        # Create pattern button (inside scroll area, right after parameters)
        create_btn = QPushButton("Create pattern")
        create_btn.clicked.connect(self.create_block_prep_patterns)
        scroll_layout.addWidget(create_btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)
        
        return tab
    
    def _create_polishing_tab(self):
        """Create the Polishing tab content."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Scroll area for parameters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # GROUP 1: Lamella parameters
        lamella_group = QGroupBox("Lamella parameters")
        lamella_layout = QFormLayout(lamella_group)
        self.lamella_thickness_nm = QLineEdit("200")
        self.pattern_width_um = QLineEdit("20")
        self.pattern_height_nm = QLineEdit("300")
        self.depth_um = QLineEdit("3")
        lamella_layout.addRow("Lamella thickness (nm):", self.lamella_thickness_nm)
        lamella_layout.addRow("Pattern width (μm):", self.pattern_width_um)
        lamella_layout.addRow("Pattern height (nm):", self.pattern_height_nm)
        lamella_layout.addRow("Depth (μm):", self.depth_um)
        scroll_layout.addWidget(lamella_group)
        
        # GROUP 2: Arc parameters
        arc_group = QGroupBox("Arc parameters")
        arc_layout = QFormLayout(arc_group)
        self.radius = QLineEdit("1.2")
        self.num_points = QLineEdit("10")
        arc_layout.addRow("Radius (≥1, 1=circle):", self.radius)
        arc_layout.addRow("Number of points:", self.num_points)
        scroll_layout.addWidget(arc_group)
        
        # GROUP 3: Milling current
        current_group = QGroupBox("Milling current")
        current_layout = QFormLayout(current_group)
        current_options = [self._current_to_nA_str(c) for c in self.available_currents]
        self.polish_current_combo = QComboBox()
        self.polish_current_combo.addItems(current_options)
        self._set_combo_to_current(self.polish_current_combo, self.DEFAULT_POLISH_CURRENT)
        current_layout.addRow("Current:", self.polish_current_combo)
        scroll_layout.addWidget(current_group)
        
        # Create pattern button
        create_btn = QPushButton("Create pattern")
        create_btn.clicked.connect(self.create_polishing_patterns)
        scroll_layout.addWidget(create_btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)
        
        return tab
        
    def setup_ui(self):
        """Legacy setup_ui method - redirects to tabbed version."""
        self.setup_ui_with_tabs()
    
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
        
    def get_parameters(self):
        """Return all block preparation parameters."""
        return {
            'block_width': float(self.block_width_um.text()) * 1e-6,
            'block_height': float(self.block_height_um.text()) * 1e-6,
            'block_depth': float(self.block_depth_um.text()) * 1e-6,
            'inner_pattern_size': float(self.inner_pattern_size_um.text()) * 1e-6,
            'inner_margin': float(self.inner_margin_um.text()) * 1e-6,
            'outer_pattern_size': float(self.outer_pattern_size_um.text()) * 1e-6,
            'outer_margin': float(self.outer_margin_um.text()) * 1e-6,
            'do_coarse': self.do_coarse.isChecked(),
            'do_medium': self.do_medium.isChecked(),
            'do_fine': self.do_fine.isChecked(),
            'coarse_current': self._nA_str_to_current(self.coarse_current_combo.currentText()),
            'medium_current': self._nA_str_to_current(self.medium_current_combo.currentText()),
            'fine_current': self._nA_str_to_current(self.fine_current_combo.currentText()),
            'milling_angle': float(self.milling_angle.text()),
            'pattern_overlap_X': float(self.pattern_overlap_X.text()) / 100,
            'pattern_overlap_Y': float(self.pattern_overlap_Y.text()) / 100,
            'bridge_width': float(self.bridge_width_um.text()) * 1e-6,
            'needle_gap_width': float(self.needle_gap_width_um.text()) * 1e-6,
            'needle_gap_height': float(self.needle_gap_height_um.text()) * 1e-6,
            'needle_gap_overlap': 2 * 1e-6,
            'trench_safety_margin': 25 * 1e-6,
            'mode': self.mode_combo.currentText(),
        }
    
    def get_polishing_parameters(self):
        """Return all polishing parameters."""
        return {
            'lamella_thickness': float(self.lamella_thickness_nm.text()) * 1e-9,
            'pattern_width': float(self.pattern_width_um.text()) * 1e-6,
            'pattern_height': float(self.pattern_height_nm.text()) * 1e-9,
            'depth': float(self.depth_um.text()) * 1e-6,
            'radius': float(self.radius.text()),
            'num_points': int(self.num_points.text()),
            'polish_current': self._nA_str_to_current(self.polish_current_combo.currentText()),
        }
    
    def rectangle_vertices(self, centerX, centerY, w, l):
        """Returns an 4x2 array with X,Y coordinates of rectangle vertices (anticlockwise)."""
        return np.array([
            [centerX - w/2, centerY + l/2],
            [centerX - w/2, centerY - l/2],
            [centerX + w/2, centerY - l/2],
            [centerX + w/2, centerY + l/2]
        ])
    
    def rectangle_properties(self, vertices):
        """Returns (X, Y, w, l) of rectangle from 4 vertices."""
        w = vertices[3, 0] - vertices[0, 0]
        l = vertices[0, 1] - vertices[1, 1]
        centerX = vertices[1, 0] + w / 2
        centerY = vertices[1, 1] + l / 2
        return (centerX, centerY, w, l)
    
    def create_block_prep_patterns(self):
        """Generate block preparation patterns and display them."""
        params = self.get_parameters()
        
        # Get parameters
        block_width = params['block_width']
        block_height = params['block_height']
        block_depth = params['block_depth']
        inner_margin = params['inner_margin']
        outer_margin = params['outer_margin']
        inner_pattern_size = params['inner_pattern_size']
        outer_pattern_size = params['outer_pattern_size']
        milling_angle = params['milling_angle']
        pattern_overlap_X = params['pattern_overlap_X']
        pattern_overlap_Y = params['pattern_overlap_Y']
        bridge_width = params['bridge_width']
        needle_gap_width = params['needle_gap_width']
        needle_gap_height = params['needle_gap_height']
        needle_gap_overlap = params['needle_gap_overlap']
        trench_safety_margin = params['trench_safety_margin']
        mode = params['mode']
        do_coarse = params['do_coarse']
        do_medium = params['do_medium']
        do_fine = params['do_fine']
        coarse_current = params['coarse_current']
        medium_current = params['medium_current']
        fine_current = params['fine_current']
        
        # Define trench height using THALES theorem
        trench_height = block_depth / np.tan(np.deg2rad(milling_angle)) + trench_safety_margin
        
        # Build all pattern vertices
        new_verts = {}
        # Pattern 0 is the block itself (reference)
        new_verts[0] = self.rectangle_vertices(0, 0, block_width, block_height)
        
        # Pattern 1: inner bottom
        new_verts[1] = np.array([
            [new_verts[0][1,0] - inner_margin - pattern_overlap_X*inner_pattern_size, new_verts[0][1,1] - inner_margin],
            [new_verts[0][1,0] - inner_margin - pattern_overlap_X*inner_pattern_size, new_verts[0][1,1] - inner_margin - inner_pattern_size],
            [new_verts[0][2,0] + inner_margin + pattern_overlap_X*inner_pattern_size, new_verts[0][2,1] - inner_margin - inner_pattern_size],
            [new_verts[0][2,0] + inner_margin + pattern_overlap_X*inner_pattern_size, new_verts[0][2,1] - inner_margin]
        ])
        
        # Pattern 2: inner left top
        new_verts[2] = np.array([
            [new_verts[0][0,0] - inner_margin - inner_pattern_size, new_verts[0][0,1] + inner_margin + pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][0,0] - inner_margin - inner_pattern_size, bridge_width/2],
            [new_verts[0][0,0] - inner_margin, bridge_width/2],
            [new_verts[0][0,0] - inner_margin, new_verts[0][0,1] + inner_margin + pattern_overlap_Y*inner_pattern_size]
        ])
        
        # Pattern 3: inner right
        new_verts[3] = np.array([
            [new_verts[0][3,0] + inner_margin, new_verts[0][3,1] + inner_margin + pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][3,0] + inner_margin, new_verts[0][2,1] - inner_margin - pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][3,0] + inner_margin + inner_pattern_size, new_verts[0][2,1] - inner_margin - pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][3,0] + inner_margin + inner_pattern_size, new_verts[0][3,1] + inner_margin + pattern_overlap_Y*inner_pattern_size]
        ])
        
        # Pattern 4: outer right
        new_verts[4] = np.array([
            [new_verts[0][3,0] + outer_margin, new_verts[0][3,1] + outer_margin + pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin, new_verts[0][2,1] - outer_margin - pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][2,1] - outer_margin - pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][3,1] + outer_margin + pattern_overlap_Y*outer_pattern_size]
        ])
        
        # Pattern 5: outer bottom
        new_verts[5] = np.array([
            [new_verts[0][1,0] - outer_margin - pattern_overlap_X*outer_pattern_size, new_verts[0][1,1] - outer_margin],
            [new_verts[0][1,0] - outer_margin - pattern_overlap_X*outer_pattern_size, new_verts[0][1,1] - outer_margin - outer_pattern_size],
            [new_verts[0][2,0] + outer_margin + pattern_overlap_X*outer_pattern_size, new_verts[0][1,1] - outer_margin - outer_pattern_size],
            [new_verts[0][2,0] + outer_margin + pattern_overlap_X*outer_pattern_size, new_verts[0][1,1] - outer_margin]
        ])
        
        # Pattern 6: inner top
        new_verts[6] = np.array([
            [new_verts[0][0,0] - inner_margin - pattern_overlap_X*inner_pattern_size, new_verts[0][0,1] + inner_margin + inner_pattern_size],
            [new_verts[0][0,0] - inner_margin - pattern_overlap_X*inner_pattern_size, new_verts[0][0,1] + inner_margin],
            [new_verts[0][3,0] + inner_margin + pattern_overlap_X*inner_pattern_size, new_verts[0][3,1] + inner_margin],
            [new_verts[0][3,0] + inner_margin + pattern_overlap_X*inner_pattern_size, new_verts[0][3,1] + inner_margin + inner_pattern_size]
        ])
        
        # Pattern 7: outer left top
        new_verts[7] = np.array([
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, bridge_width/2],
            [new_verts[0][0,0] - outer_margin, bridge_width/2],
            [new_verts[0][0,0] - outer_margin, new_verts[0][0,1] + outer_margin + pattern_overlap_Y*outer_pattern_size]
        ])
        
        # Pattern 8: trench top
        new_verts[8] = np.array([
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height],
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size + trench_height]
        ])
        
        # Pattern 9: outer left bottom
        new_verts[9] = np.array([
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, -bridge_width/2],
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][1,1] - outer_margin - pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin, new_verts[0][1,1] - outer_margin - pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin, -bridge_width/2]
        ])
        
        # Pattern 10: inner left bottom
        new_verts[10] = np.array([
            [new_verts[0][0,0] - inner_margin - inner_pattern_size, -bridge_width/2],
            [new_verts[0][0,0] - inner_margin - inner_pattern_size, new_verts[0][1,1] - inner_margin - pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][0,0] - inner_margin, new_verts[0][1,1] - inner_margin - pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][0,0] - inner_margin, -bridge_width/2]
        ])
        
        # Pattern 11: needle gap right top
        new_verts[11] = np.array([
            [new_verts[0][3,0] + outer_margin, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height],
            [new_verts[0][3,0] + outer_margin, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + needle_gap_height - needle_gap_overlap],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + needle_gap_height - needle_gap_overlap],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height]
        ])
        
        # Pattern 12: outer left trench
        new_verts[12] = np.array([
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height],
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height]
        ])
        
        # Pattern 13: needle gap
        new_verts[13] = np.array([
            [new_verts[0][3,0] + outer_margin, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size + needle_gap_height],
            [new_verts[0][3,0] + outer_margin, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + needle_gap_width, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + needle_gap_width, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size + needle_gap_height]
        ])
        
        # Pattern 14: outer top
        new_verts[14] = np.array([
            [new_verts[0][1,0] - outer_margin - pattern_overlap_X*outer_pattern_size, new_verts[0][0,1] + outer_margin + outer_pattern_size],
            [new_verts[0][1,0] - outer_margin - pattern_overlap_X*outer_pattern_size, new_verts[0][0,1] + outer_margin],
            [new_verts[0][2,0] + outer_margin + pattern_overlap_X*outer_pattern_size, new_verts[0][3,1] + outer_margin],
            [new_verts[0][2,0] + outer_margin + pattern_overlap_X*outer_pattern_size, new_verts[0][3,1] + outer_margin + outer_pattern_size]
        ])
        
        # Handle Planar mode (flip X coordinates)
        if mode == 'Planar':
            new_verts[2][:, 0] = new_verts[2][:, 0] + 2*inner_margin + block_width + inner_pattern_size
            new_verts[10][:, 0] = new_verts[10][:, 0] + 2*inner_margin + block_width + inner_pattern_size
            new_verts[7][:, 0] = new_verts[7][:, 0] + 2*outer_margin + block_width + outer_pattern_size
            new_verts[9][:, 0] = new_verts[9][:, 0] + 2*outer_margin + block_width + outer_pattern_size
            new_verts[3][:, 0] = new_verts[3][:, 0] - 2*inner_margin - block_width - inner_pattern_size
            new_verts[4][:, 0] = new_verts[4][:, 0] - 2*outer_margin - block_width - outer_pattern_size
            new_verts[11][:, 1:3] = new_verts[12][:, 1:3]
            # Remove needle gap pattern in Planar mode
            del new_verts[13]
        
        # Build pattern dictionaries for each milling current group
        # Map group name to (enabled, current in Amperes)
        current_groups = {}
        seq_groups = {}
        if do_coarse:
            current_groups['coarse'] = coarse_current
            seq_groups['coarse'] = self.coarse_seq_group.value()
        if do_medium:
            current_groups['medium'] = medium_current
            seq_groups['medium'] = self.medium_seq_group.value()
        if do_fine:
            current_groups['fine'] = fine_current
            seq_groups['fine'] = self.fine_seq_group.value()
        
        # Store current_groups and seq_groups for use in store_and_display_patterns
        self.current_groups = current_groups
        self.seq_groups = seq_groups
        
        # Store generated patterns grouped by current group
        self.generated_patterns = {group: {} for group in current_groups.keys()}
        
        pattern_id = 0
        for group, current_A in current_groups.items():
            for i, verts in new_verts.items():
                if i == 0:  # Skip the block pattern (index 0)
                    continue
                if i in self.ENABLE_PATTERNS[group]:
                    # Get hard-coded properties for this pattern index
                    props = self.PATTERN_PROPERTIES.get(i, {})
                    scan_dir = props.get('scan_direction', 'TopToBottom')
                    
                    # Create RectanglePattern with all properties
                    centerX, centerY, w, l = self.rectangle_properties(verts)
                    pattern = RectanglePattern(
                        center_x=centerX,
                        center_y=centerY,
                        width=w,
                        height=l,
                        dwell_time=1e-6,
                        scan_direction=scan_dir,
                        scan_type='Serpentine',
                        application_file='Si',
                        enabled=True
                    )
                    # Convert to pixel coordinates for display
                    coords = [(verts[j, 0], verts[j, 1]) for j in range(4)]
                    displayable = DisplayablePattern(pattern=pattern, coords=coords)
                    self.generated_patterns[group][f"{group}_{i}"] = displayable
                    pattern_id += 1
        
        # Store patterns in position data and display
        self.store_and_display_patterns()
        
    def store_and_display_patterns(self):
        """Convert patterns to pixels, store in position data, and display via load_shapes."""
        if not hasattr(self, 'generated_patterns') or self.main_window is None:
            return
            
        # Get current position data to get image dimensions and FOV
        item = self.main_window.position_list.currentItem()
        if not item:
            print("Warning: No position selected. Patterns generated but not displayed.")
            return
            
        data = item.data(Qt.UserRole)
        if data.get("image") is None:
            print("Warning: No image loaded. Patterns generated but not displayed.")
            return
        
        img_w = data["image_width"]
        img_h = data["image_height"]
        pixel_to_um = data["pixel_to_um"]
        
        # Calculate meters per pixel
        m_per_px = pixel_to_um * 1e-6
        
        # Image center in pixels
        center_px_x = img_w / 2
        center_px_y = img_h / 2
        
        # Convert patterns to pixel coords and store as list of PatternGroups
        # Order: coarse, medium, fine (matching predefined colors)
        patterns_list = []
        group_index = 0
        for group in ['coarse', 'medium', 'fine']:
            if group in self.generated_patterns:
                converted = {}
                for pid, dp in self.generated_patterns[group].items():
                    pixel_coords = []
                    for x_m, y_m in dp.coords:
                        x_px = int(center_px_x + x_m / m_per_px)
                        y_px = int(center_px_y - y_m / m_per_px)  # Flip Y
                        pixel_coords.append((x_px, y_px))
                    new_dp = DisplayablePattern(pattern=dp.pattern, coords=pixel_coords)
                    converted[pid] = new_dp
                
                # Create PatternGroup with color based on index
                milling_current = self.current_groups.get(group, 0.0)
                sequential_group = self.seq_groups.get(group, 0)
                pattern_group = PatternGroup.create_with_index(
                    patterns=converted,
                    milling_current=milling_current,
                    index=group_index,
                    sequential_group=sequential_group
                )
                patterns_list.append(pattern_group)
                group_index += 1
        
        # Store in position data
        data["patterns"] = patterns_list
        item.setData(Qt.UserRole, data)
        
        # Display via main window's load_shapes (handles list of PatternGroups)
        self.main_window.image_widget.load_shapes(patterns_list, locked=False)
        
        # Store as last loaded patterns for auto-add functionality
        self.main_window.set_last_loaded_patterns(patterns_list)
    
    def _define_arc(self, pattern_height, radius=1.2, num_points=10):
        """
        Create two arrays of point coordinates (x_coords and y_coords) which define an arc.
        This is used for the curved top/bottom edges of polishing patterns.
        
        Args:
            pattern_height: Height of the pattern (defines arc size)
            radius: Ratio of circle radius to height (>=1, 1=semicircle)
            num_points: Number of points along the arc
            
        Returns:
            x_coords, y_coords: Arrays of coordinates defining the arc
        """
        h = pattern_height
        circle_radius = h * radius
        xT = np.sqrt(circle_radius**2 - (circle_radius - h)**2)
        theta0 = -np.pi / 2
        theta1 = np.arctan2(h - circle_radius, xT)
        x_coords, y_coords = self._define_points_on_circle(0, circle_radius, circle_radius, theta0, theta1, num_points)
        return x_coords, y_coords
    
    def _define_points_on_circle(self, xM, yM, R, theta0, theta1, num_points=10):
        """
        Create two arrays of point coordinates which define a part of a circle between theta0 and theta1.
        
        Args:
            xM, yM: Center of circle
            R: Radius of circle
            theta0, theta1: Start and end angles (radians)
            num_points: Number of points
            
        Returns:
            x_coords, y_coords: Arrays of coordinates
        """
        theta_min = np.min([theta0, theta1])
        theta_max = np.max([theta0, theta1])
        theta_array = np.linspace(theta_min, theta_max, num_points)
        x_coords = R * np.cos(theta_array) + xM
        y_coords = R * np.sin(theta_array) + yM
        return x_coords, y_coords
    
    def create_polishing_patterns(self):
        """Generate polishing patterns and display them."""
        params = self.get_polishing_parameters()
        
        # Get parameters
        pattern_height = params['pattern_height']
        pattern_width = params['pattern_width']
        lamella_thickness = params['lamella_thickness']
        num_points = params['num_points']
        radius = params['radius']
        depth = params['depth']
        polish_current = params['polish_current']
        
        # Define arc for curved pattern edges
        x_coords, y_coords = self._define_arc(pattern_height, radius=radius, num_points=num_points)
        w = pattern_width / 2
        
        # Build top pattern coordinates
        # Right-hand side
        x_rhs = x_coords + w
        y_rhs = y_coords + lamella_thickness / 2
        # Left-hand side (mirrored)
        x_lhs = -x_coords - w
        y_lhs = y_coords + lamella_thickness / 2
        # Combine to form closed polygon (right side, then flipped left side)
        x1 = np.concatenate([x_rhs, np.flipud(x_lhs)])
        y1 = np.concatenate([y_rhs, np.flipud(y_lhs)])
        
        # Build bottom pattern coordinates (mirror of top)
        x2 = x1.copy()
        y2 = -y1.copy()
        
        # Convert to coordinate tuples for display
        top_coords = [(x1[i], y1[i]) for i in range(len(x1))]
        bottom_coords = [(x2[i], y2[i]) for i in range(len(x2))]
        
        # Create PolygonPattern objects for the patterns
        # Calculate center for the patterns
        top_center_x = np.mean(x1)
        top_center_y = np.mean(y1)
        bottom_center_x = np.mean(x2)
        bottom_center_y = np.mean(y2)
        
        # Top pattern - uses BottomToTop scan direction (matches reference PTF)
        top_pattern = PolygonPattern(
            center_x=top_center_x,
            center_y=top_center_y,
            vertices=top_coords,
            depth=depth,
            dwell_time=1e-6,
            scan_direction='BottomToTop',
            scan_type='Serpentine',
            application_file='Si',
            enabled=True,
            overlap_x=0.5,
            overlap_y=0.5
        )
        
        # Bottom pattern - uses BottomToTop scan direction (matches reference PTF)
        bottom_pattern = PolygonPattern(
            center_x=bottom_center_x,
            center_y=bottom_center_y,
            vertices=bottom_coords,
            depth=depth,
            dwell_time=1e-6,
            scan_direction='BottomToTop',
            scan_type='Serpentine',
            application_file='Si',
            enabled=True,
            overlap_x=0.5,
            overlap_y=0.5
        )
        
        # Create displayable patterns
        top_displayable = DisplayablePattern(pattern=top_pattern, coords=top_coords)
        bottom_displayable = DisplayablePattern(pattern=bottom_pattern, coords=bottom_coords)
        
        # Store polish current for use in store_and_display_polishing_patterns
        self.polish_current = polish_current
        
        # Store in generated_patterns structure (use 'polish' as the group)
        self.generated_patterns = {
            'polish': {
                'polish_top': top_displayable,
                'polish_bottom': bottom_displayable
            }
        }
        
        # Store and display
        self.store_and_display_polishing_patterns()
    
    def store_and_display_polishing_patterns(self):
        """Convert polishing patterns to pixels, store in position data, and display via load_shapes."""
        if not hasattr(self, 'generated_patterns') or self.main_window is None:
            return
            
        # Get current position data to get image dimensions and FOV
        item = self.main_window.position_list.currentItem()
        if not item:
            print("Warning: No position selected. Patterns generated but not displayed.")
            return
            
        data = item.data(Qt.UserRole)
        if data.get("image") is None:
            print("Warning: No image loaded. Patterns generated but not displayed.")
            return
        
        img_w = data["image_width"]
        img_h = data["image_height"]
        pixel_to_um = data["pixel_to_um"]
        
        # Calculate meters per pixel
        m_per_px = pixel_to_um * 1e-6
        
        # Image center in pixels
        center_px_x = img_w / 2
        center_px_y = img_h / 2
        
        # Convert polish patterns to pixel coords and create PatternGroup
        patterns_list = []
        if 'polish' in self.generated_patterns:
            converted = {}
            for pid, dp in self.generated_patterns['polish'].items():
                pixel_coords = []
                for x_m, y_m in dp.coords:
                    x_px = int(center_px_x + x_m / m_per_px)
                    y_px = int(center_px_y - y_m / m_per_px)  # Flip Y
                    pixel_coords.append((x_px, y_px))
                new_dp = DisplayablePattern(pattern=dp.pattern, coords=pixel_coords)
                converted[pid] = new_dp
            
            # Create PatternGroup with index 0 (first/yellow color)
            milling_current = getattr(self, 'polish_current', 0.0)
            pattern_group = PatternGroup.create_with_index(
                patterns=converted,
                milling_current=milling_current,
                index=0
            )
            patterns_list.append(pattern_group)
        
        # Store in position data
        data["patterns"] = patterns_list
        item.setData(Qt.UserRole, data)
        
        # Display via main window's load_shapes (handles list of PatternGroups)
        self.main_window.image_widget.load_shapes(patterns_list, locked=False)
        
        # Store as last loaded patterns for auto-add functionality
        self.main_window.set_last_loaded_patterns(patterns_list)
