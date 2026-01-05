"""
Settings Panel for AmFIBia application.
Contains image acquisition settings like scanning resolution.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QFormLayout, QLineEdit, QPushButton, QFileDialog
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal


class SettingsPanel(QWidget):
    """Panel for application settings like image resolution."""
    
    # Signal emitted when working directory changes
    working_dir_changed = pyqtSignal(str)
    
    # Signal emitted when scanning resolution changes (emits preset name like "PRESET_1536X1024")
    resolution_changed = pyqtSignal(str)
    
    # Signal emitted when dwell time changes (emits value in µs)
    dwell_time_changed = pyqtSignal(float)
    
    # Signal emitted when user wants to load a state file
    load_state_requested = pyqtSignal()
    
    # ScanningResolution presets from Autoscript (ordered by size)
    RESOLUTION_PRESETS = [
        ("512x442", "PRESET_512X442"),
        ("768x512", "PRESET_768X512"),
        ("1024x884", "PRESET_1024X884"),
        ("1536x1024", "PRESET_1536X1024"),
        ("2048x1768", "PRESET_2048X1768"),
        ("3072x2048", "PRESET_3072X2048"),
        ("4096x3536", "PRESET_4096X3536"),
        ("6144x4096", "PRESET_6144X4096"),
    ]
    
    DEFAULT_RESOLUTION = "1536x1024"
    
    def __init__(self, parent=None, mode="dev", scope=None):
        super().__init__(parent)
        self.mode = mode
        self.scope = scope
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the settings panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # Image Acquisition Settings Group
        acquisition_group = QGroupBox("Image Acquisition")
        acquisition_layout = QFormLayout(acquisition_group)
        
        # Scanning Resolution dropdown
        self.resolution_combo = QComboBox()
        for display_text, preset_name in self.RESOLUTION_PRESETS:
            self.resolution_combo.addItem(display_text, preset_name)
        
        # Set default resolution
        default_index = self.resolution_combo.findText(self.DEFAULT_RESOLUTION)
        if default_index >= 0:
            self.resolution_combo.setCurrentIndex(default_index)
        
        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        
        acquisition_layout.addRow("Scanning Resolution:", self.resolution_combo)
        
        # Dwell Time input (in µs, stored in seconds)
        self.dwell_time_edit = QLineEdit()
        self.dwell_time_edit.setText("3")  # Default 3 µs
        self.dwell_time_edit.setToolTip("Dwell time in microseconds")
        self.dwell_time_edit.editingFinished.connect(self._on_dwell_time_changed)
        
        acquisition_layout.addRow("Dwell Time (µs):", self.dwell_time_edit)
        
        layout.addWidget(acquisition_group)
        
        # Working Directory Group
        workdir_group = QGroupBox("Working Directory")
        workdir_layout = QVBoxLayout(workdir_group)
        
        # Directory path display and browse button
        dir_row_layout = QHBoxLayout()
        self.workdir_edit = QLineEdit()
        self.workdir_edit.setReadOnly(True)
        self.workdir_edit.setPlaceholderText("No directory selected")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_directory)
        dir_row_layout.addWidget(self.workdir_edit, stretch=1)
        dir_row_layout.addWidget(browse_btn)
        workdir_layout.addLayout(dir_row_layout)
        
        # Load State button
        self.load_state_btn = QPushButton("Load State")
        self.load_state_btn.clicked.connect(self._on_load_state_clicked)
        self.load_state_btn.setToolTip("Load a previously saved application state")
        workdir_layout.addWidget(self.load_state_btn)
        
        layout.addWidget(workdir_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def _on_resolution_changed(self, index):
        """Handle resolution dropdown change."""
        preset_name = self.resolution_combo.currentData()
        resolution_text = self.resolution_combo.currentText()
        print(f"Resolution changed to: {resolution_text} ({preset_name})")
        self.resolution_changed.emit(resolution_text)
    
    def _on_dwell_time_changed(self):
        """Handle dwell time input change."""
        try:
            dwell_time_us = float(self.dwell_time_edit.text())
            if dwell_time_us > 0:
                print(f"Dwell time changed to: {dwell_time_us} µs")
                self.dwell_time_changed.emit(dwell_time_us)
            else:
                # Reset to default if invalid
                self.dwell_time_edit.setText("3")
        except ValueError:
            # Reset to default if not a valid number
            self.dwell_time_edit.setText("3")
    
    def get_scanning_resolution(self):
        """Get the currently selected scanning resolution preset name."""
        return self.resolution_combo.currentData()
    
    def get_scanning_resolution_text(self):
        """Get the currently selected scanning resolution as display text (e.g., '1536x1024')."""
        return self.resolution_combo.currentText()
    
    def set_scanning_resolution(self, resolution_text):
        """Set the scanning resolution dropdown to the given resolution text (e.g., '1536x1024')."""
        index = self.resolution_combo.findText(resolution_text)
        if index >= 0:
            self.resolution_combo.setCurrentIndex(index)
    
    def get_scanning_resolution_tuple(self):
        """Get the currently selected scanning resolution as (width, height) tuple."""
        text = self.resolution_combo.currentText()
        width, height = text.split('x')
        return (int(width), int(height))
    
    def set_dwell_time(self, dwell_time_us):
        """Set the dwell time input field (value in microseconds)."""
        self.dwell_time_edit.setText(str(dwell_time_us))
    
    def _browse_directory(self):
        """Open directory chooser dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Working Directory",
            self.workdir_edit.text() or "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if directory:
            self.set_working_directory(directory)
    
    def set_working_directory(self, directory):
        """Set the working directory and update scope if available."""
        self.workdir_edit.setText(directory)
        if self.scope is not None:
            self.scope.working_dir = directory
        self.working_dir_changed.emit(directory)
    
    def get_working_directory(self):
        """Get the current working directory, or None if not set."""
        text = self.workdir_edit.text()
        return text if text else None
    
    def has_working_directory(self):
        """Check if a working directory has been set."""
        return bool(self.workdir_edit.text())
    
    def _on_load_state_clicked(self):
        """Handle load state button click."""
        self.load_state_requested.emit()
