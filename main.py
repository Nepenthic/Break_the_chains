import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTabWidget, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector3D
from shapes_tab import ShapesTab
from transform_tab import TransformTab
from viewport import Viewport
from shapes_3d import Cube, Sphere, Cylinder
from PyQt6.QtWidgets import QShortcut
from PyQt6.QtGui import QKeySequence
from transform_commands import UndoRedoManager, TransformCommand

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
        
        # Initialize undo/redo manager
        self.undo_redo_manager = UndoRedoManager()
        self.undo_redo_manager.logger = self.logger  # Set logger for undo/redo operations
        
        # Create and initialize tabs
        self.shapes_tab = ShapesTab()
        self.shapes_tab.shape_created.connect(self.onShapeCreated)
        
        self.transform_tab = TransformTab()
        self.transform_tab.transform_applied.connect(self.onTransformApplied)
        self.transform_tab.transform_mode_changed.connect(self.onTransformModeChanged)
        self.transform_tab.snap_settings_changed.connect(self.onSnapSettingsChanged)
        self.transform_tab.axis_changed.connect(self.onAxisChanged)
        
        # Connect undo/redo signals
        self.undo_redo_manager.undo_stack_changed.connect(self.updateUndoRedoButtons)
        self.undo_redo_manager.redo_stack_changed.connect(self.updateUndoRedoButtons)
        
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
        
        # Store shape IDs for reference
        self.shape_ids = {}
        
        # Set up keyboard shortcuts
        self.setupShortcuts()
        
        # Connect transform-related signals
        self.transform_tab.transformPreviewRequested.connect(self.on_transform_preview)
        self.transform_tab.transformApplied.connect(self.on_transform_applied)
        
    def setupShortcuts(self):
        """Set up keyboard shortcuts."""
        # Transform mode shortcuts
        QShortcut(QKeySequence("T"), self).activated.connect(
            lambda: self.onTransformModeChanged("translate"))
        QShortcut(QKeySequence("R"), self).activated.connect(
            lambda: self.onTransformModeChanged("rotate"))
        QShortcut(QKeySequence("S"), self).activated.connect(
            lambda: self.onTransformModeChanged("scale"))
        
        # Axis selection shortcuts
        QShortcut(QKeySequence("Alt+X"), self).activated.connect(
            lambda: self.onAxisSelected("x"))
        QShortcut(QKeySequence("Alt+Y"), self).activated.connect(
            lambda: self.onAxisSelected("y"))
        QShortcut(QKeySequence("Alt+Z"), self).activated.connect(
            lambda: self.onAxisSelected("z"))
        
        # Snapping shortcut
        QShortcut(QKeySequence("Ctrl+G"), self).activated.connect(
            self.toggleSnapping)
        
        # Cancel transform mode
        QShortcut(QKeySequence("Esc"), self).activated.connect(
            self.cancelTransform)
            
        # Apply transform
        QShortcut(QKeySequence("Return"), self).activated.connect(
            self.applyCurrentTransform)
            
        # Toggle relative mode
        QShortcut(QKeySequence("Alt+R"), self).activated.connect(
            self.toggleRelativeMode)
            
        # Undo/Redo
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(
            self.undoTransform)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(
            self.redoTransform)
            
    def applyCurrentTransform(self):
        """Apply the current transform using the Enter key."""
        if self.viewport.transform_mode:
            self.transform_tab.applyTransform()
            
    def toggleRelativeMode(self):
        """Toggle between relative and absolute transform modes."""
        self.transform_tab.relative_mode.setChecked(
            not self.transform_tab.relative_mode.isChecked())
            
    def undoTransform(self):
        """Undo the last transform operation."""
        if self.undo_redo_manager.undo():
            self.viewport.showStatusMessage("Transform Undone")
            self.viewport.update()
            
    def redoTransform(self):
        """Redo the last undone transform operation."""
        if self.undo_redo_manager.redo():
            self.viewport.showStatusMessage("Transform Redone")
            self.viewport.update()
            
    def onAxisSelected(self, axis):
        """Handle axis selection."""
        # Only process if we're in a transform mode
        if self.viewport.transform_mode:
            self.transform_tab.setActiveAxis(axis)
            self.viewport.scene_manager.set_active_axis(axis)
            mode = self.transform_tab.getTransformMode()
            self.viewport.showStatusMessage(f"Active Axis: {axis.upper()} ({mode})")
            self.viewport.update()
            
    def cancelTransform(self):
        """Cancel current transform mode."""
        self.onTransformModeChanged(None)
        self.viewport.showStatusMessage("Transform Cancelled")
        
    def toggleSnapping(self):
        """Toggle snapping on/off."""
        self.transform_tab.toggleSnapping()
        snap_enabled = self.transform_tab.getSnapSettings()['enabled']
        self.viewport.showStatusMessage(f"Snapping {'enabled' if snap_enabled else 'disabled'}")
        self.viewport.update()
        
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
        selected = self.viewport.scene_manager.get_selected_shape()
        if not selected:
            self.viewport.showStatusMessage("No shape selected")
            return
            
        shape_id, shape = selected
        
        # Set transform mode if not already set
        if self.viewport.scene_manager.get_transform_mode() != parameters["mode"]:
            self.viewport.setTransformMode(parameters["mode"])
            
        # Set active axis based on parameter
        self.viewport.scene_manager.set_active_axis(parameters["axis"])
        
        # Capture states before transform
        selected_shapes = [shape]
        before_states = [{
            'position': shape.transform.position.copy(),
            'rotation': shape.transform.rotation.copy(),
            'scale': shape.transform.scale.copy()
        } for shape in selected_shapes]
            
        # Apply the transformation through the scene manager
        try:
            self.viewport.scene_manager.apply_transform(
                shape_id,
                parameters["mode"],
                parameters  # Now includes snapping settings
            )
            
            # Capture states after transform
            after_states = [{
                'position': shape.transform.position.copy(),
                'rotation': shape.transform.rotation.copy(),
                'scale': shape.transform.scale.copy()
            } for shape in selected_shapes]
            
            # Create and add command to undo stack
            command = TransformCommand(selected_shapes, before_states, after_states, parameters)
            self.undo_redo_manager.add_command(command)
            
            # Show success message
            mode_str = parameters["mode"].capitalize()
            axis_str = parameters["axis"].upper()
            value_str = f"{parameters.get('value', 0):.2f}"
            relative_str = "Relative" if parameters.get('relative_mode', False) else "Absolute"
            
            if transform_type == "undo":
                self.viewport.showStatusMessage("Undo: Previous transform reversed")
            elif transform_type == "redo":
                self.viewport.showStatusMessage("Redo: Transform reapplied")
            else:
                self.viewport.showStatusMessage(
                    f"{mode_str} {axis_str}: {value_str} ({relative_str})"
                )
                
            # Update transform tab with current transform
            self.transform_tab.updateTransformValues(shape.transform)
            
        except Exception as e:
            self.viewport.showStatusMessage(f"Error: {str(e)}")
            
        # Update the viewport
        self.viewport.update()
        
    def onTransformModeChanged(self, mode):
        """Handle transform mode changes."""
        print(f"Transform mode changed to: {mode}")
        
        # Update transform tab
        self.transform_tab.setCurrentMode(mode)
        
        # Update viewport
        self.viewport.setTransformMode(mode)
        
        # Clear active axis when changing modes
        self.viewport.scene_manager.set_active_axis(None)
        
        # Show status message
        if mode:
            relative = "Relative" if self.transform_tab.relative_mode.isChecked() else "Absolute"
            self.viewport.showStatusMessage(f"Transform Mode: {mode.capitalize()} ({relative})")
        else:
            self.viewport.showStatusMessage("Transform Mode: None")
            
        # Update viewport
        self.viewport.update()
        
    def onSnapSettingsChanged(self, settings):
        """Handle changes to snapping settings."""
        print(f"Updating snapping settings: {settings}")
        self.viewport.scene_manager.set_snap_settings(settings)
        self.viewport.update()  # Refresh viewport to show updated grid

    def onAxisChanged(self, axis):
        """Handle axis selection changes."""
        if self.viewport.transform_mode:
            self.viewport.scene_manager.set_active_axis(axis)
            self.viewport.showStatusMessage(f"Active Axis: {axis.upper()}")
            self.viewport.update()

    def on_transform_preview(self, transform_type, value, axis):
        """Handle transform preview requests."""
        try:
            if transform_type == 'cancel':
                self.viewport.preview_overlay.stop_preview()
                return
                
            # Update viewport preview
            self.viewport.update_transform_preview(transform_type, value, axis)
            
            # Show transform info in status bar
            self.show_transform_status(transform_type, value, axis)
            
        except Exception as e:
            self.log_error(f"Transform preview error: {str(e)}")
    
    def on_transform_applied(self, transform_params):
        """Handle transform application."""
        try:
            # Apply the transform to selected shapes
            selected_shapes = self.viewport.get_selected_shapes()
            if not selected_shapes:
                self.show_status_message("No shapes selected")
                return
            
            # Apply transform based on mode
            mode = transform_params['mode']
            if mode == 'translate':
                values = transform_params['translate']
                for shape in selected_shapes:
                    shape.translate(values[0], values[1], values[2])
            elif mode == 'rotate':
                values = transform_params['rotate']
                for shape in selected_shapes:
                    shape.rotate(values[0], values[1], values[2])
            else:  # scale
                values = transform_params['scale']
                for shape in selected_shapes:
                    shape.scale(values[0], values[1], values[2])
            
            # Stop preview and update viewport
            self.viewport.preview_overlay.stop_preview()
            self.viewport.update()
            
            # Show success message
            self.show_status_message(f"Applied {mode} transform")
            
            # Log the transform
            self.log_transform_applied(transform_params)
            
        except Exception as e:
            self.show_status_message(f"Error applying transform: {str(e)}")
            self.log_error(f"Transform application error: {str(e)}")
    
    def show_transform_status(self, transform_type, value, axis):
        """Show transform status in status bar."""
        status_text = f"{transform_type.capitalize()} {axis.upper()}: {value:.2f}"
        if transform_type == 'rotate':
            status_text += "°"
        self.statusBar().showMessage(status_text, 2000)
    
    def setup_transform_shortcuts(self):
        """Setup keyboard shortcuts for transform operations."""
        # Transform mode shortcuts
        QShortcut(QKeySequence("G"), self, lambda: self.set_transform_mode('translate'))
        QShortcut(QKeySequence("R"), self, lambda: self.set_transform_mode('rotate'))
        QShortcut(QKeySequence("S"), self, lambda: self.set_transform_mode('scale'))
        
        # Axis shortcuts
        QShortcut(QKeySequence("X"), self, lambda: self.set_transform_axis('x'))
        QShortcut(QKeySequence("Y"), self, lambda: self.set_transform_axis('y'))
        QShortcut(QKeySequence("Z"), self, lambda: self.set_transform_axis('z'))
        
        # Transform control shortcuts
        QShortcut(QKeySequence("Return"), self, self.apply_current_transform)
        QShortcut(QKeySequence("Escape"), self, self.cancel_current_transform)
    
    def set_transform_mode(self, mode):
        """Set the current transform mode."""
        self.transform_tab.current_transform_mode = mode
        self.viewport.setTransformMode(mode)
        self.show_status_message(f"Transform mode: {mode}")
    
    def set_transform_axis(self, axis):
        """Set the current transform axis."""
        self.transform_tab.current_axis = axis
        self.viewport.setActiveAxis(axis)
        self.show_status_message(f"Active axis: {axis.upper()}")
    
    def apply_current_transform(self):
        """Apply the current transform."""
        self.transform_tab.apply_transform()
    
    def cancel_current_transform(self):
        """Cancel the current transform."""
        self.transform_tab.cancel_preview()
    
    def show_status_message(self, message, timeout=2000):
        """Show a message in the status bar."""
        self.statusBar().showMessage(message, timeout)
    
    def log_transform_applied(self, transform_params):
        """Log applied transform."""
        self.logger.log_ui_change(
            component="MainWindow",
            change_type="transform_applied",
            details=transform_params
        )
    
    def log_error(self, message):
        """Log error message."""
        self.logger.log_ui_change(
            component="MainWindow",
            change_type="error",
            details={'message': message}
        )

    def updateUndoRedoButtons(self):
        """Update the enabled state of undo/redo buttons."""
        self.transform_tab.undo_button.setEnabled(self.undo_redo_manager.can_undo())
        self.transform_tab.redo_button.setEnabled(self.undo_redo_manager.can_redo())

def main():
    app = QApplication(sys.argv)
    window = CADCAMMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 