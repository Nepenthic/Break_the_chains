import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTabWidget, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector3D
from shapes_tab import ShapesTab
from transform_tab import TransformTab
from viewport import Viewport
from shapes_3d import Cube, Sphere, Cylinder

class CADCAMMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD/CAM Program")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create OpenGL viewport
        self.viewport = Viewport()
        main_layout.addWidget(self.viewport, stretch=2)
        
        # Create right panel with tabs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        tab_widget = QTabWidget()
        
        # Create and initialize tabs
        self.shapes_tab = ShapesTab()
        self.shapes_tab.shape_created.connect(self.onShapeCreated)
        
        self.transform_tab = TransformTab()
        self.transform_tab.transform_applied.connect(self.onTransformApplied)
        self.transform_tab.transform_mode_changed.connect(self.onTransformModeChanged)
        
        boolean_tab = QWidget()
        cam_tab = QWidget()
        constraints_tab = QWidget()
        
        # Add tabs to tab widget
        tab_widget.addTab(self.shapes_tab, "Shapes")
        tab_widget.addTab(self.transform_tab, "Transform")
        tab_widget.addTab(boolean_tab, "Boolean")
        tab_widget.addTab(cam_tab, "CAM")
        tab_widget.addTab(constraints_tab, "Constraints")
        
        right_layout.addWidget(tab_widget)
        main_layout.addWidget(right_panel, stretch=1)
        
    def onShapeCreated(self, shape_type, parameters):
        """Handle shape creation request from the Shapes tab"""
        print(f"Creating {shape_type} with parameters: {parameters}")
        
        shape = None
        
        if shape_type == "Cube":
            # Create a cube with the specified parameters
            shape = Cube(size=parameters.get("Width", 1.0))
            # Position it slightly above the grid
            shape.position = QVector3D(0, 0, parameters.get("Height", 1.0) / 2)
            
        elif shape_type == "Sphere":
            # Create a sphere with the specified parameters
            shape = Sphere(
                radius=parameters.get("Radius", 1.0),
                segments=int(parameters.get("Segments", 32))
            )
            # Position it slightly above the grid
            shape.position = QVector3D(0, 0, parameters.get("Radius", 1.0))
            
        elif shape_type == "Cylinder":
            # Create a cylinder with the specified parameters
            shape = Cylinder(
                radius=parameters.get("Radius", 1.0),
                height=parameters.get("Height", 2.0),
                segments=int(parameters.get("Segments", 32))
            )
            # Position it slightly above the grid
            shape.position = QVector3D(0, 0, parameters.get("Height", 2.0) / 2)
            
        if shape:
            # Add the shape to the viewport
            self.viewport.addShape(shape)
            # Select the new shape
            self.viewport.selectShape(shape)
        
    def onTransformApplied(self, transform_type, parameters):
        """Handle transform application request from the Transform tab"""
        print(f"Applying {transform_type} transform with parameters: {parameters}")
        
        # Get the selected shape
        shape = self.viewport.getSelectedShape()
        if not shape:
            return
            
        # Apply the transformation
        if parameters["mode"] == "translate":
            axis = parameters["axis"]
            value = parameters["value"]
            current_pos = shape.position
            if axis == "x":
                shape.position = QVector3D(current_pos.x() + value, current_pos.y(), current_pos.z())
            elif axis == "y":
                shape.position = QVector3D(current_pos.x(), current_pos.y() + value, current_pos.z())
            elif axis == "z":
                shape.position = QVector3D(current_pos.x(), current_pos.y(), current_pos.z() + value)
                
        elif parameters["mode"] == "rotate":
            axis = parameters["axis"]
            value = parameters["value"]
            current_rot = shape.rotation
            if axis == "x":
                shape.rotation = QVector3D(current_rot.x() + value, current_rot.y(), current_rot.z())
            elif axis == "y":
                shape.rotation = QVector3D(current_rot.x(), current_rot.y() + value, current_rot.z())
            elif axis == "z":
                shape.rotation = QVector3D(current_rot.x(), current_rot.y(), current_rot.z() + value)
                
        elif parameters["mode"] == "scale":
            axis = parameters["axis"]
            value = parameters["value"]
            current_scale = shape.scale
            if axis == "x":
                shape.scale = QVector3D(value, current_scale.y(), current_scale.z())
            elif axis == "y":
                shape.scale = QVector3D(current_scale.x(), value, current_scale.z())
            elif axis == "z":
                shape.scale = QVector3D(current_scale.x(), current_scale.y(), value)
                
        # Update the viewport
        self.viewport.update()
        
    def onTransformModeChanged(self, mode):
        """Handle transform mode changes for updating UI feedback"""
        print(f"Transform mode changed to: {mode}")
        # This will be used to update cursor and UI feedback later

def main():
    app = QApplication(sys.argv)
    window = CADCAMMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 