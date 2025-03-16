from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                           QGroupBox, QFormLayout, QDoubleSpinBox,
                           QRadioButton, QButtonGroup, QLabel,
                           QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal

class TransformTab(QWidget):
    # Signals to communicate with backend
    transform_applied = pyqtSignal(str, dict)  # (transform_type, parameters)
    transform_mode_changed = pyqtSignal(str)  # Current transform mode
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Transform mode selection
        mode_group = QGroupBox("Transform Mode")
        mode_layout = QVBoxLayout()
        
        # Create radio buttons for transform modes
        self.mode_group = QButtonGroup()
        modes = [
            ("Translate (T)", "translate"),
            ("Rotate (R)", "rotate"),
            ("Scale (S)", "scale")
        ]
        
        for text, mode in modes:
            radio = QRadioButton(text)
            self.mode_group.addButton(radio)
            mode_layout.addWidget(radio)
            radio.clicked.connect(lambda checked, m=mode: self.onModeChanged(m))
            
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Transform parameters
        self.params_group = QGroupBox("Parameters")
        self.params_layout = QFormLayout()
        self.params_group.setLayout(self.params_layout)
        layout.addWidget(self.params_group)
        
        # Axis selection
        axis_group = QGroupBox("Axis")
        axis_layout = QHBoxLayout()
        
        self.axis_group = QButtonGroup()
        axes = [("X", "x"), ("Y", "y"), ("Z", "z")]
        
        for text, axis in axes:
            radio = QRadioButton(text)
            self.axis_group.addButton(radio)
            axis_layout.addWidget(radio)
            
        axis_group.setLayout(axis_layout)
        layout.addWidget(axis_group)
        
        # Apply button
        apply_button = QPushButton("Apply Transform")
        apply_button.clicked.connect(self.applyTransform)
        layout.addWidget(apply_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Select translate mode by default
        self.mode_group.buttons()[0].setChecked(True)
        self.axis_group.buttons()[0].setChecked(True)
        self.setupTranslateParams()
        
    def setupTranslateParams(self):
        self.clearParams()
        self.addParameter("Distance", 0.0, -1000.0, 1000.0, 0.1)
        
    def setupRotateParams(self):
        self.clearParams()
        self.addParameter("Angle (degrees)", 0.0, -360.0, 360.0, 1.0)
        
    def setupScaleParams(self):
        self.clearParams()
        self.addParameter("Scale Factor", 1.0, 0.01, 100.0, 0.1)
        
    def clearParams(self):
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def addParameter(self, name, default_value, min_val, max_val, step):
        spin_box = QDoubleSpinBox()
        spin_box.setRange(min_val, max_val)
        spin_box.setValue(default_value)
        spin_box.setSingleStep(step)
        self.params_layout.addRow(name, spin_box)
        
    def onModeChanged(self, mode):
        self.transform_mode_changed.emit(mode)
        if mode == "translate":
            self.setupTranslateParams()
        elif mode == "rotate":
            self.setupRotateParams()
        elif mode == "scale":
            self.setupScaleParams()
            
    def applyTransform(self):
        # Collect parameters
        params = {}
        
        # Get the current mode
        for button in self.mode_group.buttons():
            if button.isChecked():
                params["mode"] = button.text().split()[0].lower()
                break
                
        # Get the selected axis
        for button in self.axis_group.buttons():
            if button.isChecked():
                params["axis"] = button.text().lower()
                break
        
        # Get the parameter value
        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i * 2).widget()
            spin_box = self.params_layout.itemAt(i * 2 + 1).widget()
            if isinstance(label_item, QLabel) and isinstance(spin_box, QDoubleSpinBox):
                params["value"] = spin_box.value()
                break
                
        # Emit signal with transform parameters
        self.transform_applied.emit(params["mode"], params) 