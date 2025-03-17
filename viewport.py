from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import QMatrix4x4, QVector3D, QVector4D, QPainter, QColor
from OpenGL.GL import *
import numpy as np
from shapes_3d import SceneManager, Cube
from src.core.utils import (
    qvector3d_to_numpy,
    qvector4d_to_numpy,
    numpy_to_qvector3d,
    qmatrix4x4_to_numpy
)
import math
import logging

class TransformPreviewOverlay:
    """Manages transform preview visualization in the viewport."""
    
    def __init__(self, viewport):
        self.viewport = viewport
        self.active = False
        self.transform_type = None
        self.transform_mode = 'absolute'  # Default to absolute mode
        self.axes_values = {}  # Dictionary to store values for each active axis
        self.original_state = None
        self.preview_color = {
            'x': (1.0, 0.0, 0.0, 0.3),  # Red with reduced alpha
            'y': (0.0, 1.0, 0.0, 0.3),  # Green with reduced alpha
            'z': (0.0, 0.0, 1.0, 0.3)   # Blue with reduced alpha
        }
        # Text offset from preview indicators
        self.text_offset = 0.2
        # Line pattern for dashed lines (stipple pattern)
        self.line_pattern = 0x00FF
    
    def start_preview(self, transform_type, axes_values, transform_mode='absolute'):
        """Start transform preview with multiple axes and specified mode."""
        self.active = True
        self.transform_type = transform_type
        self.transform_mode = transform_mode
        self.axes_values = axes_values.copy()  # e.g., {'x': 1.0, 'y': 2.0}
        self.original_state = self.capture_current_state()
        self.viewport.update()
    
    def update_preview(self, axes_values, transform_mode=None):
        """Update preview with new values for multiple axes."""
        if not self.active:
            return
        self.axes_values.update(axes_values)  # Update only provided axes
        if transform_mode is not None:
            self.transform_mode = transform_mode
        self.viewport.update()
    
    def stop_preview(self):
        """Stop transform preview and restore original state."""
        if not self.active:
            return
        self.active = False
        self.restore_original_state()
        self.transform_type = None
        self.axes_values.clear()
        self.original_state = None
        self.viewport.update()
    
    def capture_current_state(self):
        """Capture current state of selected shapes."""
        selected_shapes = self.viewport.scene_manager.get_selected_shapes()
        if not selected_shapes:
            return None
            
        return {
            shape.id: {
                'position': shape.transform.position.copy(),
                'rotation': shape.transform.rotation.copy(),
                'scale': shape.transform.scale.copy()
            }
            for shape in selected_shapes
        }
    
    def restore_original_state(self):
        """Restore shapes to their original state."""
        if not self.original_state:
            return
            
        for shape_id, state in self.original_state.items():
            shape = self.viewport.scene_manager.get_shape(shape_id)
            if shape:
                shape.transform.position = state['position'].copy()
                shape.transform.rotation = state['rotation'].copy()
                shape.transform.scale = state['scale'].copy()
                shape.update()
    
    def get_value_text(self, axis):
        """Get formatted value text for a specific axis."""
        if not self.active or axis not in self.axes_values:
            return ""
            
        value = self.axes_values[axis]
        prefix = "Δ" if self.transform_mode == 'relative' else ""
        
        if self.transform_type == 'translate':
            return f"{prefix}{value:+.2f}"
        elif self.transform_type == 'rotate':
            return f"{prefix}{value:+.1f}°"
        elif self.transform_type == 'scale':
            if self.transform_mode == 'relative':
                return f"{prefix}×{value:+.2f}"
            else:
                return f"×{value:.2f}"
        return ""
        
    def get_text_position(self, center, end_pos, axis):
        """Calculate position for value text display for a specific axis."""
        offset = np.array([
            self.text_offset if axis == 'x' else 0,
            self.text_offset if axis == 'y' else 0,
            self.text_offset if axis == 'z' else 0
        ])
        return end_pos + offset
    
    def get_preview_color(self, axis):
        """Get color for specific axis with alpha for preview."""
        return self.preview_color.get(axis, (0.7, 0.7, 0.7, 0.3))  # Default to gray
    
    def get_preview_end_position(self, center, axis):
        """Calculate end position for preview indicator based on mode."""
        if not self.active or axis not in self.axes_values:
            return center
            
        value = self.axes_values[axis]
        end_pos = np.array(center)
        
        if self.transform_type == 'translate':
            if self.transform_mode == 'absolute':
                # Set position directly
                if axis == 'x':
                    end_pos[0] = value
                elif axis == 'y':
                    end_pos[1] = value
                else:  # z
                    end_pos[2] = value
            else:  # relative
                # Add delta to current position
                if axis == 'x':
                    end_pos[0] += value
                elif axis == 'y':
                    end_pos[1] += value
                else:  # z
                    end_pos[2] += value
        elif self.transform_type == 'rotate':
            # Rotation is always relative
            radius = 1.0
            angle = np.radians(value)
            if axis == 'x':
                end_pos[1] += radius * np.cos(angle)
                end_pos[2] += radius * np.sin(angle)
            elif axis == 'y':
                end_pos[0] += radius * np.cos(angle)
                end_pos[2] += radius * np.sin(angle)
            else:  # z
                end_pos[0] += radius * np.cos(angle)
                end_pos[1] += radius * np.sin(angle)
        elif self.transform_type == 'scale':
            if self.transform_mode == 'absolute':
                # Set scale directly
                if axis == 'x':
                    end_pos[0] = center[0] * value
                elif axis == 'y':
                    end_pos[1] = center[1] * value
                else:  # z
                    end_pos[2] = center[2] * value
            else:  # relative
                # Multiply current scale
                if axis == 'x':
                    end_pos[0] *= (1.0 + value)
                elif axis == 'y':
                    end_pos[1] *= (1.0 + value)
                else:  # z
                    end_pos[2] *= (1.0 + value)
                
        return end_pos

    def get_preview_center(self):
        """Get center point for preview visualization."""
        selected_shapes = self.viewport.scene_manager.get_selected_shapes()
        if not selected_shapes:
            return np.array([0.0, 0.0, 0.0])
            
        # Calculate average position of selected shapes
        positions = [shape.transform.position for shape in selected_shapes]
        return sum(positions) / len(positions)

class Viewport(QWidget):
    """Widget for 3D viewport display."""
    
    # Signals
    shapeSelected = pyqtSignal(str)  # shape_id
    selectionCleared = pyqtSignal()
    viewportUpdated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.shapes = {}
        self.selected_shapes = set()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.initializeCamera()
        self.last_pos = QPoint()
        self.setCursor(Qt.CursorShape.CrossCursor)  # Set default cursor for better precision
        
        # Initialize scene manager
        self.scene_manager = SceneManager()
        
        # Transform mode
        self.transform_mode = None
        
        # Status message
        self.status_message = ""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.clearStatusMessage)
        self.status_timer.setSingleShot(True)
        
        # Add a test cube
        test_cube = Cube(size=2.0)
        test_cube.position = QVector3D(0, 0, 1)  # Lift slightly above the grid
        self.scene_manager.addShape(test_cube)
        
        self.preview_overlay = TransformPreviewOverlay(self)
        self.setup_logging()
        
    def initializeCamera(self):
        # Camera parameters
        self.camera_distance = 10.0
        self.camera_azimuth = 45.0  # Horizontal angle in degrees
        self.camera_elevation = 30.0  # Vertical angle in degrees
        self.camera_target = QVector3D(0, 0, 0)
        
        # View matrix
        self.view_matrix = QMatrix4x4()
        self.updateViewMatrix()
        
        # Projection matrix
        self.projection_matrix = QMatrix4x4()
        
    def updateViewMatrix(self):
        """Update the view matrix based on camera parameters"""
        self.view_matrix.setToIdentity()
        
        # Convert spherical coordinates to Cartesian
        phi = np.radians(self.camera_azimuth)
        theta = np.radians(self.camera_elevation)
        
        camera_x = self.camera_distance * np.cos(phi) * np.cos(theta)
        camera_y = self.camera_distance * np.sin(phi) * np.cos(theta)
        camera_z = self.camera_distance * np.sin(theta)
        
        camera_pos = QVector3D(camera_x, camera_y, camera_z)
        
        # Look at the target point
        self.view_matrix.lookAt(
            camera_pos,
            self.camera_target,
            QVector3D(0, 0, 1)  # Up vector
        )
        
        self.update()  # Request a redraw
        
    def addShape(self, shape):
        """Add a shape to the viewport."""
        shape_id = str(len(self.shapes))
        self.shapes[shape_id] = shape
        self.update()
        return shape_id
    
    def selectShape(self, shape_id):
        """Select a shape by ID."""
        if shape_id in self.shapes:
            self.selected_shapes.add(shape_id)
            self.shapeSelected.emit(shape_id)
            self.update()
    
    def clearSelection(self):
        """Clear all shape selections."""
        self.selected_shapes.clear()
        self.selectionCleared.emit()
        self.update()
    
    def getSelectedShape(self):
        """Get the currently selected shape."""
        if self.selected_shapes:
            shape_id = next(iter(self.selected_shapes))
            return self.shapes[shape_id]
        return None
    
    def getShape(self, shape_id):
        """Get a shape by ID."""
        return self.shapes.get(shape_id)
    
    def clear(self):
        """Clear all shapes from the viewport."""
        self.shapes.clear()
        self.selected_shapes.clear()
        self.update()
    
    def update(self):
        """Update the viewport display."""
        super().update()
        self.viewportUpdated.emit()

    def drawAxes(self):
        """Draw coordinate axes with enhanced visual feedback"""
        glDisable(GL_LIGHTING)
        
        # Get active axis for highlighting
        active_axis = self.scene_manager.get_active_axis()
        
        # Draw main axes
        glLineWidth(2.0)  # Thicker lines for better visibility
        glBegin(GL_LINES)
        
        # X axis (red)
        if active_axis == 'x':
            glColor3f(1.0, 0.8, 0.8)  # Lighter red when active
        else:
            glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(5, 0, 0)
        
        # Y axis (green)
        if active_axis == 'y':
            glColor3f(0.8, 1.0, 0.8)  # Lighter green when active
        else:
            glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 5, 0)
        
        # Z axis (blue)
        if active_axis == 'z':
            glColor3f(0.8, 0.8, 1.0)  # Lighter blue when active
        else:
            glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 5)
        
        glEnd()
        
        # Draw axis labels
        self.renderAxisLabel("X", QVector3D(5.2, 0, 0), active_axis == 'x')
        self.renderAxisLabel("Y", QVector3D(0, 5.2, 0), active_axis == 'y')
        self.renderAxisLabel("Z", QVector3D(0, 0, 5.2), active_axis == 'z')
        
        glEnable(GL_LIGHTING)
        
    def renderAxisLabel(self, text, position, is_active):
        """Render an axis label at the given position"""
        # Save matrices
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        
        # Convert 3D position to screen coordinates
        viewport = glGetIntegerv(GL_VIEWPORT)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        x, y, z = gluProject(position.x(), position.y(), position.z(),
                           modelview, projection, viewport)
        
        # Switch to 2D rendering
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.width(), 0, self.height(), -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Draw text using QPainter
        painter = QPainter(self)
        if is_active:
            painter.setPen(Qt.GlobalColor.white)  # White when active
        else:
            painter.setPen(Qt.GlobalColor.lightGray)  # Light gray otherwise
        painter.setFont(self.font())
        painter.drawText(int(x), int(self.height() - y), text)
        painter.end()
        
        # Restore matrices
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def drawGrid(self):
        """Draw a reference grid with snapping visualization"""
        glDisable(GL_LIGHTING)
        
        # Draw main grid
        glColor3f(0.3, 0.3, 0.3)  # Gray color for main grid
        glBegin(GL_LINES)
        
        grid_size = 10
        step = 1
        
        for i in range(-grid_size, grid_size + 1, step):
            # Lines parallel to X axis
            glVertex3f(i, -grid_size, 0)
            glVertex3f(i, grid_size, 0)
            
            # Lines parallel to Y axis
            glVertex3f(-grid_size, i, 0)
            glVertex3f(grid_size, i, 0)
            
        glEnd()
        
        # Draw snap grid if snapping is enabled
        selected = self.scene_manager.get_selected_shape()
        if selected:
            shape_id, shape = selected
            if shape.snap_enabled:
                # Get snap settings
                snap_settings = shape.getSnapSettings()
                
                # Draw snap grid based on transform mode
                if self.transform_mode == "translate":
                    self.drawSnapGrid(snap_settings['translate'])
                elif self.transform_mode == "rotate":
                    self.drawRotationGuides(snap_settings['rotate'])
                elif self.transform_mode == "scale":
                    self.drawScaleGuides(snap_settings['scale'])
        
        glEnable(GL_LIGHTING)
        
    def drawSnapGrid(self, grid_size):
        """Draw the snap grid with the specified size"""
        glColor3f(0.4, 0.4, 0.4)  # Slightly brighter for snap grid
        glLineWidth(1.0)  # Thinner lines for snap grid
        glBegin(GL_LINES)
        
        grid_extent = 10
        
        for i in range(int(-grid_extent/grid_size), int(grid_extent/grid_size) + 1):
            pos = i * grid_size
            # Lines parallel to X axis
            glVertex3f(pos, -grid_extent, 0)
            glVertex3f(pos, grid_extent, 0)
            
            # Lines parallel to Y axis
            glVertex3f(-grid_extent, pos, 0)
            glVertex3f(grid_extent, pos, 0)
            
        glEnd()
        glLineWidth(1.0)  # Reset line width
        
    def drawRotationGuides(self, angle_snap):
        """Draw rotation snap guides"""
        glColor3f(0.4, 0.4, 0.4)  # Slightly brighter for guides
        
        # Get active axis
        active_axis = self.scene_manager.get_active_axis()
        if not active_axis:
            return
            
        # Draw rotation circle
        radius = 5.0
        segments = int(360 / min(angle_snap, 15))  # At least 24 segments
        
        glBegin(GL_LINE_LOOP)
        for i in range(segments):
            angle = np.radians(i * 360 / segments)
            if active_axis == 'x':
                glVertex3f(0, radius * np.cos(angle), radius * np.sin(angle))
            elif active_axis == 'y':
                glVertex3f(radius * np.cos(angle), 0, radius * np.sin(angle))
            else:  # z
                glVertex3f(radius * np.cos(angle), radius * np.sin(angle), 0)
        glEnd()
        
        # Draw snap angles
        glBegin(GL_LINES)
        for angle in range(0, 360, int(angle_snap)):
            rad = np.radians(angle)
            cos = radius * np.cos(rad)
            sin = radius * np.sin(rad)
            
            if active_axis == 'x':
                glVertex3f(0, cos, sin)
                glVertex3f(0, cos * 0.9, sin * 0.9)
            elif active_axis == 'y':
                glVertex3f(cos, 0, sin)
                glVertex3f(cos * 0.9, 0, sin * 0.9)
            else:  # z
                glVertex3f(cos, sin, 0)
                glVertex3f(cos * 0.9, sin * 0.9, 0)
        glEnd()
        
    def drawScaleGuides(self, scale_snap):
        """Draw scale snap guides"""
        glColor3f(0.4, 0.4, 0.4)  # Slightly brighter for guides
        
        # Get active axis
        active_axis = self.scene_manager.get_active_axis()
        if not active_axis:
            return
            
        # Draw scale markers
        glBegin(GL_LINES)
        for i in range(1, int(10/scale_snap) + 1):
            pos = i * scale_snap
            
            if active_axis == 'x':
                glVertex3f(pos, -0.1, 0)
                glVertex3f(pos, 0.1, 0)
            elif active_axis == 'y':
                glVertex3f(-0.1, pos, 0)
                glVertex3f(0.1, pos, 0)
            else:  # z
                glVertex3f(-0.1, 0, pos)
                glVertex3f(0.1, 0, pos)
        glEnd()

    def createRayFromMouseClick(self, mouse_pos):
        """Convert mouse coordinates to a ray in world space"""
        # Get viewport dimensions
        viewport_width = self.width()
        viewport_height = self.height()
        
        # Convert mouse coordinates to normalized device coordinates (-1 to 1)
        x = (2.0 * mouse_pos.x()) / viewport_width - 1.0
        y = 1.0 - (2.0 * mouse_pos.y()) / viewport_height
        
        # Create near and far points in clip space
        near_point = QVector4D(x, y, -1.0, 1.0)
        far_point = QVector4D(x, y, 1.0, 1.0)
        
        # Get the inverse of projection * view matrix
        inv_projection = QMatrix4x4(self.projection_matrix)
        inv_view = QMatrix4x4(self.view_matrix)
        
        # Check if matrices can be inverted
        inv_projection_success, inv_projection = inv_projection.inverted()
        inv_view_success, inv_view = inv_view.inverted()
        
        if not (inv_projection_success and inv_view_success):
            return None, None
            
        inv_transform = inv_view * inv_projection
        
        # Transform to world space
        near_world = inv_transform * near_point
        far_world = inv_transform * far_point
        
        # Divide by w to get actual positions
        if near_world.w() != 0:
            near_world /= near_world.w()
        if far_world.w() != 0:
            far_world /= far_world.w()
        
        # Create ray direction
        ray_origin = QVector3D(near_world.x(), near_world.y(), near_world.z())
        ray_direction = QVector3D(
            far_world.x() - near_world.x(),
            far_world.y() - near_world.y(),
            far_world.z() - near_world.z()
        ).normalized()
        
        # Convert to numpy arrays for backend
        ray_origin_np = qvector3d_to_numpy(ray_origin)
        ray_direction_np = qvector3d_to_numpy(ray_direction)
        
        return ray_origin_np, ray_direction_np

    def findShapeUnderMouse(self, mouse_pos):
        """Find the shape under the mouse cursor using ray casting"""
        ray_origin, ray_direction = self.createRayFromMouseClick(mouse_pos)
        
        if ray_origin is None or ray_direction is None:
            return None
            
        # Use backend's ray casting system
        shape_id = self.scene_manager.find_shape_under_ray(ray_origin, ray_direction)
        if shape_id:
            return self.scene_manager.get_shape(shape_id)
        return None

    def setTransformMode(self, mode):
        """Set the current transform mode and update cursor"""
        self.transform_mode = mode
        # Update backend transform mode
        self.scene_manager.set_transform_mode(mode)
        self.updateCursor()
        
        # Show status message with mode and keyboard shortcuts
        if mode:
            shortcuts = {
                'translate': '(T)',
                'rotate': '(R)',
                'scale': '(S)'
            }
            relative = "Relative" if self.scene_manager.get_selected_shape() and \
                      self.scene_manager.get_selected_shape()[1].relative_mode else "Absolute"
            self.showStatusMessage(
                f"Transform Mode: {mode.capitalize()} {shortcuts.get(mode, '')} - {relative} Mode"
            )
        else:
            self.showStatusMessage("Transform Mode: None")
            
        self.update()  # Request redraw for visual feedback

    def updateCursor(self):
        """Update cursor based on transform mode and hover state"""
        if self.transform_mode:
            # Show transform-specific cursor
            if self.transform_mode == "translate":
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            elif self.transform_mode == "rotate":
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif self.transform_mode == "scale":
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            # Show selection cursor
            hovered = self.scene_manager.get_hovered_shape()
            self.setCursor(Qt.CursorShape.PointingHandCursor if hovered else Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, event):
        """Handle mouse press events for camera control and shape selection"""
        self.last_pos = event.pos()
        
        if event.button() == Qt.MouseButton.LeftButton and not event.modifiers():
            # Left click without modifiers - select shape
            ray_origin, ray_direction = self.createRayFromMouseClick(event.pos())
            if ray_origin is not None and ray_direction is not None:
                shape_id = self.scene_manager.find_shape_under_ray(ray_origin, ray_direction)
                if self.scene_manager.select_shape(shape_id):
                    # Clear hover state when selection changes
                    self.scene_manager.set_hovered_shape(None)
                    self.updateCursor()
                    self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for camera control and hover effects"""
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()
        
        if event.buttons() & Qt.MouseButton.LeftButton and event.modifiers():
            # Orbit camera only when modifier key is pressed
            self.camera_azimuth += dx * 0.5
            self.camera_elevation = max(-89.0, min(89.0, self.camera_elevation + dy * 0.5))
            self.updateViewMatrix()
        elif event.buttons() & Qt.MouseButton.RightButton:
            # Pan camera
            scale = 0.01 * self.camera_distance
            right = QVector3D.crossProduct(
                QVector3D(0, 0, 1),
                QVector3D(self.view_matrix.column(2))
            ).normalized()
            up = QVector3D(0, 0, 1)
            
            self.camera_target -= right * (dx * scale)
            self.camera_target += up * (dy * scale)
            self.updateViewMatrix()
        elif event.buttons() & Qt.MouseButton.LeftButton and self.transform_mode:
            # Handle transform operations
            selected = self.scene_manager.get_selected_shape()
            if selected:
                shape_id, shape = selected
                
                # Calculate transform value based on mode
                if self.transform_mode == "rotate":
                    transform_value = dx * 0.5  # Degrees for rotation
                else:
                    # Scale transform value based on camera distance for better control
                    transform_value = dx * 0.01 * (self.camera_distance / 10.0)
                
                # Set active axis based on modifiers or gizmo intersection
                active_axis = None
                if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                    active_axis = 'x'
                elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    active_axis = 'y'
                elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    active_axis = 'z'
                else:
                    # Try to find intersected gizmo axis
                    ray_origin, ray_direction = self.createRayFromMouseClick(event.pos())
                    if ray_origin is not None and ray_direction is not None:
                        active_axis = shape.find_intersected_gizmo_axis(
                            ray_origin,
                            ray_direction,
                            self.transform_mode
                        )
                
                if active_axis:
                    self.scene_manager.set_active_axis(active_axis)
                    
                    # Apply transform based on mode and active axis
                    transform_params = {
                        'x': transform_value if active_axis == 'x' else 0,
                        'y': transform_value if active_axis == 'y' else 0,
                        'z': transform_value if active_axis == 'z' else 0,
                        'snap': {
                            'enabled': True,  # Always enable snapping for direct manipulation
                            'translate': 0.25,  # Default grid size
                            'rotate': 15.0,    # Default angle snap
                            'scale': 0.25      # Default scale snap
                        }
                    }
                    
                    self.scene_manager.apply_transform(
                        shape_id,
                        self.transform_mode,
                        transform_params
                    )
                    self.update()
        else:
            # Update hover state for shapes and gizmos
            ray_origin, ray_direction = self.createRayFromMouseClick(event.pos())
            if ray_origin is not None and ray_direction is not None:
                # First check for gizmo intersection
                selected = self.scene_manager.get_selected_shape()
                if selected and self.transform_mode:
                    shape_id, shape = selected
                    intersected_axis = shape.find_intersected_gizmo_axis(
                        ray_origin,
                        ray_direction,
                        self.transform_mode
                    )
                    if intersected_axis:
                        self.scene_manager.set_active_axis(intersected_axis)
                        self.updateCursor()
                        self.update()
                        self.last_pos = event.pos()
                        return
                
                # If no gizmo intersection, check for shape intersection
                shape_id = self.scene_manager.find_shape_under_ray(ray_origin, ray_direction)
                if self.scene_manager.set_hovered_shape(shape_id):
                    self.updateCursor()
                    self.update()
        
        self.last_pos = event.pos()

    def leaveEvent(self, event):
        """Handle mouse leave events"""
        # Clear hover state and active axis when mouse leaves widget
        self.scene_manager.set_hovered_shape(None)
        self.scene_manager.set_active_axis(None)
        self.updateCursor()
        self.update()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        """Handle mouse wheel events for camera zoom"""
        delta = event.angleDelta().y()
        zoom_factor = 0.0015
        
        self.camera_distance *= (1.0 - delta * zoom_factor)
        self.camera_distance = max(1.0, min(100.0, self.camera_distance))
        
        self.updateViewMatrix()
        
    def removeShape(self, shape_id):
        """Remove a shape from the scene"""
        self.scene_manager.remove_shape(shape_id)
        self.update()
        
    def _get_shape_parameters(self, shape):
        """Extract parameters from a frontend shape for backend creation"""
        params = {}
        if hasattr(shape, 'size'):
            params['size'] = shape.size
        if hasattr(shape, 'radius'):
            params['radius'] = shape.radius
        if hasattr(shape, 'height'):
            params['height'] = shape.height
        if hasattr(shape, 'segments'):
            params['segments'] = shape.segments
        return params
        
    def _get_shape_transform(self, shape):
        """Extract transform from a frontend shape for backend creation"""
        return {
            'position': qvector3d_to_numpy(shape.position).tolist(),
            'rotation': qvector3d_to_numpy(shape.rotation).tolist(),
            'scale': qvector3d_to_numpy(shape.scale).tolist()
        }

    def renderMesh(self, mesh):
        """Render a trimesh mesh using OpenGL."""
        glBegin(GL_TRIANGLES)
        for face in mesh.faces:
            for vertex_index in face:
                vertex = mesh.vertices[vertex_index]
                if mesh.vertex_normals is not None:
                    normal = mesh.vertex_normals[vertex_index]
                    glNormal3fv(normal)
                glVertex3fv(vertex)
        glEnd()

    def renderGizmos(self, shape):
        """Render transform gizmos for a shape."""
        glDisable(GL_LIGHTING)  # Disable lighting for gizmos
        glDepthFunc(GL_ALWAYS)  # Always draw gizmos on top
        
        # Get and render all gizmo meshes
        for gizmo_mesh, color in shape.get_gizmo_meshes():
            glColor4f(*color)
            self.renderMesh(gizmo_mesh)
        
        glDepthFunc(GL_LESS)  # Restore depth testing
        glEnable(GL_LIGHTING)  # Restore lighting

    def updateGizmoScale(self):
        """Update gizmo scale based on camera distance."""
        selected = self.scene_manager.get_selected_shape()
        if selected:
            shape_id, shape = selected
            # Calculate distance from camera to shape
            shape_pos = shape.transform.position
            camera_pos = self.getCameraPosition()
            distance = np.linalg.norm(shape_pos - camera_pos)
            # Scale gizmos based on distance (adjust multiplier as needed)
            shape.gizmo_scale = distance * 0.15

    def getCameraPosition(self) -> np.ndarray:
        """Get the current camera position in world space."""
        # Convert spherical coordinates to Cartesian
        phi = np.radians(self.camera_azimuth)
        theta = np.radians(self.camera_elevation)
        
        x = self.camera_distance * np.cos(phi) * np.cos(theta)
        y = self.camera_distance * np.sin(phi) * np.cos(theta)
        z = self.camera_distance * np.sin(theta)
        
        return np.array([x, y, z]) + qvector3d_to_numpy(self.camera_target)

    def showStatusMessage(self, message: str, duration: int = 3000):
        """Show a status message in the viewport."""
        self.status_message = message
        self.status_timer.start(duration)
        self.update()
        
    def clearStatusMessage(self):
        """Clear the current status message."""
        self.status_message = ""
        self.update()
        
    def drawStatusMessage(self):
        """Draw the current status message."""
        if not self.status_message:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Set up font and colors
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        
        # Draw text background
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(self.status_message)
        text_height = metrics.height()
        padding = 10
        
        bg_rect = QRect(
            10,  # Left margin
            self.height() - text_height - 2 * padding,  # Bottom margin
            text_width + 2 * padding,
            text_height + 2 * padding
        )
        
        painter.fillRect(bg_rect, QColor(0, 0, 0, 128))
        
        # Draw text
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(
            bg_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.status_message
        )
        
        painter.end()

    def updateSnapState(self, enabled):
        """Update snapping state and show feedback."""
        self.showStatusMessage(f"Snapping: {'Enabled' if enabled else 'Disabled'}")

    def update_transform_preview(self, transform_type, value, axis):
        """Update transform preview overlay."""
        try:
            if not self.preview_overlay.active:
                self.preview_overlay.start_preview(transform_type, {axis: value})
            
            self.preview_overlay.update_preview({axis: value})
            
            # Log preview update
            self.log_viewport_update({
                'type': 'preview_update',
                'transform_type': transform_type,
                'axis': axis,
                'value': value
            })
            
        except Exception as e:
            self.log_error(f"Preview update error: {str(e)}")

    def draw_transform_preview(self):
        """Draw transform preview with enhanced visual feedback for multiple axes."""
        if not self.preview_overlay.active:
            return
            
        gl = self.context().functions()
        
        # Set up preview rendering state
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glLineWidth(2.0)
        
        # Get preview center
        center = self.preview_overlay.get_preview_center()
        
        # Enable line stipple for dashed lines
        gl.glEnable(gl.GL_LINE_STIPPLE)
        gl.glLineStipple(1, self.preview_overlay.line_pattern)
        
        # Draw preview for each active axis
        for axis in self.preview_overlay.axes_values:
            # Get preview parameters for this axis
            color = self.preview_overlay.get_preview_color(axis)
            end_pos = self.preview_overlay.get_preview_end_position(center, axis)
            
            # Draw preview based on transform type
            if self.preview_overlay.transform_type == 'translate':
                self.draw_translation_preview(gl, center, end_pos, color)
            elif self.preview_overlay.transform_type == 'rotate':
                self.draw_rotation_preview(gl, center, end_pos, color, axis)
            else:  # scale
                self.draw_scale_preview(gl, center, end_pos, color)
                
            # Draw value indicator and axis label for this axis
            text_pos = self.preview_overlay.get_text_position(center, end_pos, axis)
            value_text = self.preview_overlay.get_value_text(axis)
            axis_label = axis.upper()
            
            # Convert 3D position to screen coordinates for text
            viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
            modelview = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)
            projection = gl.glGetDoublev(gl.GL_PROJECTION_MATRIX)
            win_x, win_y, win_z = gluProject(text_pos[0], text_pos[1], text_pos[2],
                                           modelview, projection, viewport)
            
            # Save matrices for text rendering
            gl.glMatrixMode(gl.GL_PROJECTION)
            gl.glPushMatrix()
            gl.glMatrixMode(gl.GL_MODELVIEW)
            gl.glPushMatrix()
            
            # Switch to 2D rendering for text
            gl.glMatrixMode(gl.GL_PROJECTION)
            gl.glLoadIdentity()
            gl.glOrtho(0, self.width(), 0, self.height(), -1, 1)
            gl.glMatrixMode(gl.GL_MODELVIEW)
            gl.glLoadIdentity()
            
            # Draw text using QPainter
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            # Set up font for value text
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            
            # Calculate vertical offset for stacked text
            axis_index = {'x': 0, 'y': 1, 'z': 2}[axis]
            vertical_offset = axis_index * 24  # Offset each axis text by 24 pixels
            
            # Draw value text with background
            text_rect = painter.fontMetrics().boundingRect(value_text)
            bg_rect = QRect(int(win_x), int(self.height() - win_y) + vertical_offset,
                           text_rect.width() + 6, text_rect.height() + 4)
            painter.fillRect(bg_rect, QColor(0, 0, 0, 128))
            painter.setPen(QColor(*[int(c * 255) for c in color[:3]], 255))
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, value_text)
            
            # Draw axis label
            label_rect = QRect(bg_rect.x(), bg_rect.y() - 20,
                             20, 20)
            painter.fillRect(label_rect, QColor(0, 0, 0, 128))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, axis_label)
            
            painter.end()
            
            # Restore matrices
            gl.glMatrixMode(gl.GL_PROJECTION)
            gl.glPopMatrix()
            gl.glMatrixMode(gl.GL_MODELVIEW)
            gl.glPopMatrix()
        
        # Disable line stipple
        gl.glDisable(gl.GL_LINE_STIPPLE)
        
        # Restore GL state
        gl.glEnable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_BLEND)
        gl.glLineWidth(1.0)
        
    def draw_translation_preview(self, gl, center, end_pos, color):
        """Draw translation preview with enhanced visual feedback."""
        gl.glColor4f(*color)
        
        # Draw main line
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3f(center[0], center[1], center[2])
        gl.glVertex3f(end_pos[0], end_pos[1], end_pos[2])
        gl.glEnd()
        
        # Draw arrow head
        arrow_size = 0.15
        direction = end_pos - center
        length = np.linalg.norm(direction)
        if length > 0:
            direction = direction / length
            
            # Calculate perpendicular vectors for arrow head
            if abs(direction[1]) < 0.9:
                up = np.cross(direction, [0, 1, 0])
            else:
                up = np.cross(direction, [1, 0, 0])
            up = up / np.linalg.norm(up)
            right = np.cross(direction, up)
            
            # Draw arrow head
            gl.glBegin(gl.GL_TRIANGLES)
            tip = end_pos
            base1 = end_pos - direction * arrow_size + up * arrow_size * 0.5
            base2 = end_pos - direction * arrow_size - up * arrow_size * 0.5
            
            gl.glVertex3f(*tip)
            gl.glVertex3f(*base1)
            gl.glVertex3f(*base2)
            gl.glEnd()
            
    def draw_rotation_preview(self, gl, center, end_pos, color, axis):
        """Draw rotation preview with enhanced visual feedback."""
        gl.glColor4f(*color)
        
        # Draw rotation arc
        segments = 32
        radius = 1.0
        angle = np.radians(self.preview_overlay.axes_values[axis])
        
        gl.glBegin(gl.GL_LINE_STRIP)
        for i in range(segments + 1):
            t = (i / segments) * angle
            if axis == 'x':
                gl.glVertex3f(center[0],
                            center[1] + radius * np.cos(t),
                            center[2] + radius * np.sin(t))
            elif axis == 'y':
                gl.glVertex3f(center[0] + radius * np.cos(t),
                            center[1],
                            center[2] + radius * np.sin(t))
            else:  # z
                gl.glVertex3f(center[0] + radius * np.cos(t),
                            center[1] + radius * np.sin(t),
                            center[2])
        gl.glEnd()
        
        # Draw rotation axis
        gl.glBegin(GL_LINES)
        if axis == 'x':
            gl.glVertex3f(center[0] - 1.5, center[1], center[2])
            gl.glVertex3f(center[0] + 1.5, center[1], center[2])
        elif axis == 'y':
            gl.glVertex3f(center[0], center[1] - 1.5, center[2])
            gl.glVertex3f(center[0], center[1] + 1.5, center[2])
        else:
            gl.glVertex3f(center[0], center[1], center[2] - 1.5)
            gl.glVertex3f(center[0], center[1], center[2] + 1.5)
        gl.glEnd()
        
    def draw_scale_preview(self, gl, center, end_pos, color):
        """Draw scale preview with enhanced visual feedback."""
        gl.glColor4f(*color)
        
        # Draw main axis line
        gl.glBegin(GL_LINES)
        gl.glVertex3f(center[0], center[1], center[2])
        gl.glVertex3f(end_pos[0], end_pos[1], end_pos[2])
        gl.glEnd()
        
        # Draw scale handles
        handle_size = 0.1
        self.draw_scale_handle(gl, center, handle_size)
        self.draw_scale_handle(gl, end_pos, handle_size * self.preview_overlay.axes_values[self.scene_manager.get_active_axis()])
    
    def draw_scale_handle(self, gl, center, size):
        """Draw a cube handle for scale preview."""
        half = size / 2
        
        # Draw top face
        gl.glVertex3f(center[0] - half, center[1] - half, center[2] + half)
        gl.glVertex3f(center[0] + half, center[1] - half, center[2] + half)
        
        gl.glVertex3f(center[0] + half, center[1] - half, center[2] + half)
        gl.glVertex3f(center[0] + half, center[1] + half, center[2] + half)
        
        gl.glVertex3f(center[0] + half, center[1] + half, center[2] + half)
        gl.glVertex3f(center[0] - half, center[1] + half, center[2] + half)
        
        gl.glVertex3f(center[0] - half, center[1] + half, center[2] + half)
        gl.glVertex3f(center[0] - half, center[1] - half, center[2] + half)
        
        # Draw bottom face
        gl.glVertex3f(center[0] - half, center[1] - half, center[2] - half)
        gl.glVertex3f(center[0] + half, center[1] - half, center[2] - half)
        
        gl.glVertex3f(center[0] + half, center[1] - half, center[2] - half)
        gl.glVertex3f(center[0] + half, center[1] + half, center[2] - half)
        
        gl.glVertex3f(center[0] + half, center[1] + half, center[2] - half)
        gl.glVertex3f(center[0] - half, center[1] + half, center[2] - half)
        
        gl.glVertex3f(center[0] - half, center[1] + half, center[2] - half)
        gl.glVertex3f(center[0] - half, center[1] - half, center[2] - half)
        
        # Draw connecting lines
        gl.glVertex3f(center[0] - half, center[1] - half, center[2] - half)
        gl.glVertex3f(center[0] - half, center[1] - half, center[2] + half)
        
        gl.glVertex3f(center[0] + half, center[1] - half, center[2] - half)
        gl.glVertex3f(center[0] + half, center[1] - half, center[2] + half)
        
        gl.glVertex3f(center[0] + half, center[1] + half, center[2] - half)
        gl.glVertex3f(center[0] + half, center[1] + half, center[2] + half)
        
        gl.glVertex3f(center[0] - half, center[1] + half, center[2] - half)
        gl.glVertex3f(center[0] - half, center[1] + half, center[2] + half)

    def setup_logging(self):
        """Initialize viewport logging."""
        self.viewport_logger = UIChangeLogger()
        self.viewport_logger.set_log_level('INFO')
    
    def log_viewport_update(self, details):
        """Log viewport updates."""
        self.viewport_logger.log_ui_change(
            component="Viewport",
            change_type="viewport_update",
            details=details
        )
    
    def log_error(self, message):
        """Log viewport errors."""
        self.viewport_logger.log_ui_change(
            component="Viewport",
            change_type="error",
            details={'message': message}
        ) 