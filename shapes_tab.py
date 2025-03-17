from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                           QGroupBox, QFormLayout, QDoubleSpinBox,
                           QComboBox, QLabel, QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal

class ShapesTab(QWidget):
    # Signals to communicate with backend
    shape_created = pyqtSignal(str, dict)  # (shape_type, parameters)
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Shape type selection
        shape_type_group = QGroupBox("Shape Type")
        shape_type_layout = QVBoxLayout()
        
        self.shape_type = QComboBox()
        self.shape_type.addItems(["Cube", "Sphere", "Cylinder", "Cone", "Extrusion"])
        self.shape_type.currentTextChanged.connect(self.onShapeTypeChanged)
        
        shape_type_layout.addWidget(self.shape_type)
        shape_type_group.setLayout(shape_type_layout)
        layout.addWidget(shape_type_group)
        
        # Parameters group
        self.params_group = QGroupBox("Parameters")
        self.params_layout = QFormLayout()
        self.params_group.setLayout(self.params_layout)
        layout.addWidget(self.params_group)
        
        # Create button
        create_button = QPushButton("Create Shape")
        create_button.clicked.connect(self.createShape)
        layout.addWidget(create_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Initialize parameters for default shape (Cube)
        self.setupCubeParams()
        
    def setupCubeParams(self):
        self.clearParams()
        self.addParameter("Width", 1.0)
        self.addParameter("Height", 1.0)
        self.addParameter("Depth", 1.0)
        
    def setupSphereParams(self):
        self.clearParams()
        self.addParameter("Radius", 1.0)
        self.addParameter("Segments", 32.0)
        
    def setupCylinderParams(self):
        self.clearParams()
        self.addParameter("Radius", 1.0)
        self.addParameter("Height", 2.0)
        self.addParameter("Segments", 32.0)
        
    def setupConeParams(self):
        self.clearParams()
        self.addParameter("Base Radius", 1.0)
        self.addParameter("Height", 2.0)
        self.addParameter("Segments", 32.0)
        
    def setupExtrusionParams(self):
        self.clearParams()
        # Add integer spinbox for number of sides
        sides_spin = QSpinBox()
        sides_spin.setRange(3, 100)
        sides_spin.setValue(6)
        sides_spin.setSingleStep(1)
        self.params_layout.addRow("Sides", sides_spin)
        
        # Add double spinboxes for radius and height
        self.addParameter("Radius", 1.0)
        self.addParameter("Height", 2.0)
        
    def clearParams(self):
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def addParameter(self, name, default_value):
        spin_box = QDoubleSpinBox()
        spin_box.setRange(0.1, 1000.0)
        spin_box.setValue(default_value)
        spin_box.setSingleStep(0.1)
        self.params_layout.addRow(name, spin_box)
        
    def onShapeTypeChanged(self, shape_type):
        if shape_type == "Cube":
            self.setupCubeParams()
        elif shape_type == "Sphere":
            self.setupSphereParams()
        elif shape_type == "Cylinder":
            self.setupCylinderParams()
        elif shape_type == "Cone":
            self.setupConeParams()
        elif shape_type == "Extrusion":
            self.setupExtrusionParams()
            
    def createShape(self):
        # Collect parameters
        params = {}
        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i * 2).widget()
            value_widget = self.params_layout.itemAt(i * 2 + 1).widget()
            if isinstance(label_item, QLabel):
                if isinstance(value_widget, QDoubleSpinBox):
                    params[label_item.text()] = value_widget.value()
                elif isinstance(value_widget, QSpinBox):
                    params[label_item.text()] = value_widget.value()
                
        # Emit signal with shape type and parameters
        self.shape_created.emit(self.shape_type.currentText(), params) 