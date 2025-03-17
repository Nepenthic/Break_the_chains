import sys
import logging
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTabWidget, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector3D
from shapes_tab import ShapesTab
from transform_tab import TransformTab
from viewport import Viewport
from shapes_3d import Cube, Sphere, Cylinder, ExtrudedShape
from PyQt6.QtWidgets import QShortcut
from PyQt6.QtGui import QKeySequence
from transform_commands import UndoRedoManager, TransformCommand

# Performance monitoring constants
PERF_WARNING_THRESHOLD = 100.0  # ms
PERF_ERROR_THRESHOLD = 500.0    # ms

# Shape validation constants
MAX_DIMENSION = 1000.0  # Maximum size in units
MAX_SEGMENTS = 128     # Maximum segments for spheres, cylinders
MAX_SIDES = 100        # Maximum sides for extrusions
MIN_DIMENSION = 0.001  # Minimum size in units
MIN_SEGMENTS = 8       # Minimum segments for spheres, cylinders
MIN_SIDES = 3          # Minimum sides for extrusions

# Additional validation constants
SCENE_MAX = 1000.0     # Maximum scene bounds
MIN_ANGLE = 15.0       # Minimum angle between edges (degrees)
MAX_ANGLE = 165.0      # Maximum angle between edges (degrees)
MIN_SCALE_STEP = 0.01  # Minimum scale step size

class CADCAMMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Add file handler if not already added
        if not self.logger.handlers:
            fh = logging.FileHandler('cadcam.log')
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
        
        # Initialize performance metrics
        self.operation_times = {
            'shape_creation': [],
            'transform_apply': [],
            'shape_deletion': [],
            'undo_redo': []
        }
        
        # Log validation constants
        self.logger.info("Initializing with validation limits:")
        self.logger.info(f"MAX_DIMENSION: {MAX_DIMENSION}")
        self.logger.info(f"MAX_SEGMENTS: {MAX_SEGMENTS}")
        self.logger.info(f"MAX_SIDES: {MAX_SIDES}")
        self.logger.info(f"SCENE_MAX: {SCENE_MAX}")
        self.logger.info(f"MIN_ANGLE: {MIN_ANGLE}")
        self.logger.info(f"MAX_ANGLE: {MAX_ANGLE}")
        self.logger.info(f"MIN_SCALE_STEP: {MIN_SCALE_STEP}")
        
        # Log performance thresholds
        self.logger.info("Performance monitoring thresholds:")
        self.logger.info(f"Warning threshold: {PERF_WARNING_THRESHOLD}ms")
        self.logger.info(f"Error threshold: {PERF_ERROR_THRESHOLD}ms")
        
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
        
        # Create placeholder tabs
        boolean_tab = QWidget()
        boolean_layout = QVBoxLayout(boolean_tab)
        boolean_layout.addWidget(QLabel("Boolean Operations"))
        boolean_layout.addStretch()
        
        cam_tab = QWidget()
        cam_layout = QVBoxLayout(cam_tab)
        cam_layout.addWidget(QLabel("CAM Operations"))
        cam_layout.addStretch()
        
        constraints_tab = QWidget()
        constraints_layout = QVBoxLayout(constraints_tab)
        constraints_layout.addWidget(QLabel("Constraints"))
        constraints_layout.addStretch()
        
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
        """Handle shape creation request from the Shapes tab."""
        start_time = time.time()
        try:
            self.logger.info(f"Creating {shape_type} with parameters: {parameters}")
            
            # Validate parameters
            if not parameters:
                raise ValueError("No parameters provided for shape creation")
                
            shape = None
            
            if shape_type == "Cube":
                # Validate cube parameters
                width = float(parameters.get("Width", 1.0))
                height = float(parameters.get("Height", 1.0))
                
                if width <= 0 or height <= 0:
                    raise ValueError("Cube dimensions must be positive")
                if width > MAX_DIMENSION or height > MAX_DIMENSION:
                    raise ValueError(f"Dimensions must be less than {MAX_DIMENSION}")
                if width < MIN_DIMENSION or height < MIN_DIMENSION:
                    raise ValueError(f"Dimensions must be greater than {MIN_DIMENSION}")
                    
                shape = Cube(size=width)
                shape.position = QVector3D(0, 0, height / 2)
                
            elif shape_type == "Sphere":
                # Validate sphere parameters
                radius = float(parameters.get("Radius", 1.0))
                segments = int(parameters.get("Segments", 32))
                
                if radius <= 0:
                    raise ValueError("Sphere radius must be positive")
                if radius > MAX_DIMENSION:
                    raise ValueError(f"Radius must be less than {MAX_DIMENSION}")
                if radius < MIN_DIMENSION:
                    raise ValueError(f"Radius must be greater than {MIN_DIMENSION}")
                if segments < MIN_SEGMENTS:
                    raise ValueError(f"Segments must be at least {MIN_SEGMENTS}")
                if segments > MAX_SEGMENTS:
                    raise ValueError(f"Segments must be {MAX_SEGMENTS} or fewer")
                    
                shape = Sphere(radius=radius, segments=segments)
                shape.position = QVector3D(0, 0, radius)
                
            elif shape_type == "Cylinder":
                # Validate cylinder parameters
                radius = float(parameters.get("Radius", 1.0))
                height = float(parameters.get("Height", 2.0))
                segments = int(parameters.get("Segments", 32))
                
                if radius <= 0 or height <= 0:
                    raise ValueError("Cylinder dimensions must be positive")
                if radius > MAX_DIMENSION or height > MAX_DIMENSION:
                    raise ValueError(f"Dimensions must be less than {MAX_DIMENSION}")
                if radius < MIN_DIMENSION or height < MIN_DIMENSION:
                    raise ValueError(f"Dimensions must be greater than {MIN_DIMENSION}")
                if segments < MIN_SEGMENTS:
                    raise ValueError(f"Segments must be at least {MIN_SEGMENTS}")
                if segments > MAX_SEGMENTS:
                    raise ValueError(f"Segments must be {MAX_SEGMENTS} or fewer")
                    
                shape = Cylinder(radius=radius, height=height, segments=segments)
                shape.position = QVector3D(0, 0, height / 2)
                
            elif shape_type == "Extrusion":
                # Validate extrusion parameters
                num_sides = int(parameters.get("Sides", 6))
                radius = float(parameters.get("Radius", 1.0))
                height = float(parameters.get("Height", 2.0))
                
                if num_sides < MIN_SIDES:
                    raise ValueError(f"Extrusion must have at least {MIN_SIDES} sides")
                if num_sides > MAX_SIDES:
                    raise ValueError(f"Extrusion cannot have more than {MAX_SIDES} sides")
                if radius <= 0 or height <= 0:
                    raise ValueError("Extrusion dimensions must be positive")
                if radius > MAX_DIMENSION or height > MAX_DIMENSION:
                    raise ValueError(f"Dimensions must be less than {MAX_DIMENSION}")
                if radius < MIN_DIMENSION or height < MIN_DIMENSION:
                    raise ValueError(f"Dimensions must be greater than {MIN_DIMENSION}")
                    
                # Create shape and validate angles
                shape = ExtrudedShape(num_sides=num_sides, radius=radius, height=height)
                
                # Calculate and validate angles between edges
                angles = shape._calculate_edge_angles()
                min_angle = min(angles)
                max_angle = max(angles)
                
                if min_angle < MIN_ANGLE:
                    raise ValueError(f"Extrusion has sharp angles (min: {min_angle:.1f}°)")
                if max_angle > MAX_ANGLE:
                    raise ValueError(f"Extrusion has obtuse angles (max: {max_angle:.1f}°)")
                    
                shape.position = QVector3D(0, 0, height / 2)
            else:
                raise ValueError(f"Unknown shape type: {shape_type}")
            
            if shape:
                # Add shape to viewport
                shape_id = self.viewport.addShape(shape)
                if shape_id:
                    self.viewport.selectShape(shape_id)
                    self.logger.info(f"Successfully created {shape_type} with ID: {shape_id}")
                    self.viewport.showStatusMessage(f"Created {shape_type}")
                else:
                    raise RuntimeError("Failed to add shape to viewport")
                    
        except ValueError as e:
            self.logger.error(f"Invalid parameters for {shape_type}: {str(e)}")
            self.viewport.showStatusMessage(f"Error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to create {shape_type}: {str(e)}", exc_info=True)
            self.viewport.showStatusMessage(f"Failed to create {shape_type}")
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            self.log_performance('shape_creation', elapsed_ms)
        
    def onTransformApplied(self, transform_type, parameters):
        """Handle transform application request from the Transform tab"""
        start_time = time.time()
        try:
            self.logger.info(f"Applying {transform_type} transform with parameters: {parameters}")
            
            # Validate parameters
            if not parameters:
                raise ValueError("No parameters provided for transform")
                
            # Get the selected shape
            selected = self.viewport.scene_manager.get_selected_shape()
            if not selected:
                raise ValueError("No shape selected")
                
            shape_id, shape = selected
            
            # Validate transform mode
            if 'mode' not in parameters:
                raise ValueError("Transform mode not specified")
                
            mode = parameters['mode']
            if mode not in ['translate', 'rotate', 'scale']:
                raise ValueError(f"Invalid transform mode: {mode}")
                
            # Set transform mode if not already set
            if self.viewport.scene_manager.get_transform_mode() != mode:
                self.viewport.setTransformMode(mode)
                
            # Validate and set active axis
            if 'axis' not in parameters:
                raise ValueError("Transform axis not specified")
                
            axis = parameters['axis']
            if axis not in ['x', 'y', 'z']:
                raise ValueError(f"Invalid transform axis: {axis}")
                
            self.viewport.scene_manager.set_active_axis(axis)
            
            # Validate transform value
            if 'value' in parameters:
                value = float(parameters['value'])
                if mode == 'scale':
                    # Check scale limits
                    if value <= 0:
                        raise ValueError("Scale factor must be positive")
                    if value > 100:
                        raise ValueError("Scale factor must be less than 100")
                    if value < 0.01:
                        raise ValueError("Scale factor must be greater than 0.01")
                        
                    # Check scale step size
                    current_scale = shape.transform.scale
                    new_scale = current_scale * value
                    scale_change = abs(new_scale - current_scale)
                    if scale_change < MIN_SCALE_STEP:
                        raise ValueError(f"Scale change too small (min: {MIN_SCALE_STEP})")
                        
                    # Check resulting dimensions
                    if (new_scale.x() > MAX_DIMENSION or 
                        new_scale.y() > MAX_DIMENSION or 
                        new_scale.z() > MAX_DIMENSION):
                        raise ValueError(f"Resulting dimensions would exceed {MAX_DIMENSION}")
                    if (new_scale.x() < MIN_DIMENSION or 
                        new_scale.y() < MIN_DIMENSION or 
                        new_scale.z() < MIN_DIMENSION):
                        raise ValueError(f"Resulting dimensions would be less than {MIN_DIMENSION}")
                        
                elif mode == 'translate':
                    # Check translation limits
                    if abs(value) > MAX_DIMENSION:
                        raise ValueError(f"Translation distance must be less than {MAX_DIMENSION}")
                        
                    # Check resulting position
                    current_pos = shape.transform.position
                    new_pos = current_pos.copy()
                    if axis == 'x':
                        new_pos.setX(current_pos.x() + value)
                    elif axis == 'y':
                        new_pos.setY(current_pos.y() + value)
                    else:  # z
                        new_pos.setZ(current_pos.z() + value)
                        
                    # Validate position bounds
                    if (abs(new_pos.x()) > SCENE_MAX or 
                        abs(new_pos.y()) > SCENE_MAX or 
                        abs(new_pos.z()) > SCENE_MAX):
                        raise ValueError(f"Shape would move out of scene bounds (±{SCENE_MAX})")
                        
                elif mode == 'rotate':
                    # Normalize rotation to [0, 360)
                    parameters['value'] = value % 360
            
            # Capture states before transform
            selected_shapes = [shape]
            before_states = [{
                'position': shape.transform.position.copy(),
                'rotation': shape.transform.rotation.copy(),
                'scale': shape.transform.scale.copy()
            } for shape in selected_shapes]
                
            # Apply the transformation through the scene manager
            self.viewport.scene_manager.apply_transform(
                shape_id,
                mode,
                parameters  # Now includes snapping settings
            )
            
            # Validate resulting state
            shape = self.viewport.scene_manager.get_shape(shape_id)
            if not shape:
                raise RuntimeError("Shape not found after transform")
                
            # Check final dimensions
            scale = shape.transform.scale
            if (scale.x() > MAX_DIMENSION or 
                scale.y() > MAX_DIMENSION or 
                scale.z() > MAX_DIMENSION):
                raise ValueError(f"Transform would result in dimensions exceeding {MAX_DIMENSION}")
            if (scale.x() < MIN_DIMENSION or 
                scale.y() < MIN_DIMENSION or 
                scale.z() < MIN_DIMENSION):
                raise ValueError(f"Transform would result in dimensions less than {MIN_DIMENSION}")
                
            # Check final position
            position = shape.transform.position
            if (abs(position.x()) > SCENE_MAX or 
                abs(position.y()) > SCENE_MAX or 
                abs(position.z()) > SCENE_MAX):
                raise ValueError(f"Shape moved out of scene bounds (±{SCENE_MAX})")
            
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
            mode_str = mode.capitalize()
            axis_str = axis.upper()
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
            
            self.logger.info(f"Successfully applied {mode_str} transform on axis {axis_str}")
            
        except ValueError as e:
            self.logger.error(f"Invalid transform parameters: {str(e)}")
            self.viewport.showStatusMessage(f"Error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to apply transform: {str(e)}", exc_info=True)
            self.viewport.showStatusMessage(f"Failed to apply transform")
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            self.log_performance('transform_apply', elapsed_ms)
            
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

    def onShapeDeleted(self, shape_id):
        """Handle shape deletion request."""
        start_time = time.time()
        try:
            self.logger.info(f"Attempting to delete shape {shape_id}")
            
            # Validate shape exists
            if not self.viewport.scene_manager.shape_exists(shape_id):
                raise ValueError(f"Shape {shape_id} does not exist")
                
            # Get shape and validate it's not locked
            shape = self.viewport.scene_manager.get_shape(shape_id)
            if hasattr(shape, 'is_locked') and shape.is_locked:
                raise ValueError(f"Cannot delete locked shape {shape_id}")
                
            # Check if shape is selected
            selected = self.viewport.scene_manager.get_selected_shape()
            if selected and selected[0] == shape_id:
                # Deselect before deletion
                self.viewport.scene_manager.deselect_shape()
                
            # Remove shape from viewport
            if self.viewport.removeShape(shape_id):
                self.logger.info(f"Successfully deleted shape {shape_id}")
                self.viewport.showStatusMessage("Shape deleted")
            else:
                raise RuntimeError(f"Failed to remove shape {shape_id} from viewport")
                
        except ValueError as e:
            self.logger.error(f"Deletion error: {str(e)}")
            self.viewport.showStatusMessage(f"Error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during shape deletion: {str(e)}", exc_info=True)
            self.viewport.showStatusMessage("Failed to delete shape")
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            self.log_performance('shape_deletion', elapsed_ms)
            
        # Update viewport
        self.viewport.update()

    def onTransformUndo(self):
        """Handle transform undo operation."""
        start_time = time.time()
        try:
            self.logger.info("Attempting to undo last transform")
            
            # Check if undo is available
            if not self.undo_redo_manager.can_undo():
                raise ValueError("Nothing to undo")
                
            # Get the command to undo
            command = self.undo_redo_manager.peek_undo()
            if not command:
                raise RuntimeError("No transform command found in undo stack")
                
            # Validate command states
            if not command.validate_states():
                raise ValueError("Invalid transform states in undo stack")
                
            # Perform undo
            if self.undo_redo_manager.undo():
                self.logger.info("Successfully undid last transform")
                self.viewport.showStatusMessage("Transform undone")
                self.viewport.update()
            else:
                raise RuntimeError("Failed to undo transform")
                
        except ValueError as e:
            self.logger.error(f"Undo error: {str(e)}")
            self.viewport.showStatusMessage(f"Error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during undo: {str(e)}", exc_info=True)
            self.viewport.showStatusMessage("Failed to undo transform")
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            self.log_performance('undo_redo', elapsed_ms)
            
    def onTransformRedo(self):
        """Handle transform redo operation."""
        start_time = time.time()
        try:
            self.logger.info("Attempting to redo last undone transform")
            
            # Check if redo is available
            if not self.undo_redo_manager.can_redo():
                raise ValueError("Nothing to redo")
                
            # Get the command to redo
            command = self.undo_redo_manager.peek_redo()
            if not command:
                raise RuntimeError("No transform command found in redo stack")
                
            # Validate command states
            if not command.validate_states():
                raise ValueError("Invalid transform states in redo stack")
                
            # Perform redo
            if self.undo_redo_manager.redo():
                self.logger.info("Successfully redid last transform")
                self.viewport.showStatusMessage("Transform redone")
                self.viewport.update()
            else:
                raise RuntimeError("Failed to redo transform")
                
        except ValueError as e:
            self.logger.error(f"Redo error: {str(e)}")
            self.viewport.showStatusMessage(f"Error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during redo: {str(e)}", exc_info=True)
            self.viewport.showStatusMessage("Failed to redo transform")
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            self.log_performance('undo_redo', elapsed_ms)

    def log_performance(self, operation, elapsed_ms):
        """Log performance metrics for an operation."""
        self.operation_times[operation].append(elapsed_ms)
        
        # Keep only last 100 measurements
        if len(self.operation_times[operation]) > 100:
            self.operation_times[operation] = self.operation_times[operation][-100:]
            
        # Calculate statistics
        avg_time = sum(self.operation_times[operation]) / len(self.operation_times[operation])
        max_time = max(self.operation_times[operation])
        
        # Log performance data
        self.logger.info(f"Performance - {operation}:")
        self.logger.info(f"  Last operation: {elapsed_ms:.2f}ms")
        self.logger.info(f"  Average time: {avg_time:.2f}ms")
        self.logger.info(f"  Maximum time: {max_time:.2f}ms")
        
        # Log warnings for slow operations
        if elapsed_ms > PERF_ERROR_THRESHOLD:
            self.logger.error(f"Operation {operation} took {elapsed_ms:.2f}ms (exceeded error threshold)")
        elif elapsed_ms > PERF_WARNING_THRESHOLD:
            self.logger.warning(f"Operation {operation} took {elapsed_ms:.2f}ms (exceeded warning threshold)")

def main():
    app = QApplication(sys.argv)
    window = CADCAMMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 