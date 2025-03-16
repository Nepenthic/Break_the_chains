from PyQt6.QtWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QMatrix4x4, QVector3D, QVector4D, QPainter
from OpenGL.GL import *
import numpy as np
from shapes_3d import SceneManager, Cube
from src.core.utils import (
    qvector3d_to_numpy,
    qvector4d_to_numpy,
    numpy_to_qvector3d,
    qmatrix4x4_to_numpy
)

class Viewport(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initializeCamera()
        self.last_pos = QPoint()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Enable key events
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
        
    def initializeGL(self):
        """Initialize OpenGL settings"""
        glClearColor(0.15, 0.15, 0.15, 1.0)  # Dark gray background
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        
        # Enable basic lighting
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        
        # Set up light position and properties
        glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        
    def resizeGL(self, width, height):
        """Handle window resize events"""
        glViewport(0, 0, width, height)
        
        # Update projection matrix
        self.projection_matrix.setToIdentity()
        aspect = width / height if height > 0 else 1.0
        self.projection_matrix.perspective(45.0, aspect, 0.1, 1000.0)
        
    def paintGL(self):
        """Render the scene"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Set up matrices
        glMatrixMode(GL_PROJECTION)
        glLoadMatrixf(self.projection_matrix.data())
        
        glMatrixMode(GL_MODELVIEW)
        glLoadMatrixf(self.view_matrix.data())
        
        # Draw coordinate axes
        self.drawAxes()
        
        # Draw grid
        self.drawGrid()
        
        # Render all shapes in the scene
        for shape_id, shape in self.scene_manager.get_all_shapes():
            # Draw shape
            glPushMatrix()
            color = shape.get_transform_color()
            glColor4f(*color)
            mesh = shape.get_mesh()
            self.renderMesh(mesh)
            glPopMatrix()
            
            # Draw transform gizmos if shape is selected
            if shape.selected and shape.transform_mode:
                self.renderGizmos(shape)
                
        # Update gizmo scale based on camera distance
        self.updateGizmoScale()
        
        # Draw status message
        if self.status_message:
            self.drawStatusMessage()
        
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
        
        # Show status message
        if mode:
            self.showStatusMessage(f"Transform Mode: {mode.capitalize()}")
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
        
    def addShape(self, shape):
        """Add a shape to the scene"""
        # Convert frontend shape to backend shape if necessary
        shape_id = self.scene_manager.create_shape(
            shape.__class__.__name__.lower(),
            self._get_shape_parameters(shape),
            self._get_shape_transform(shape)
        )
        self.update()
        return shape_id
        
    def removeShape(self, shape_id):
        """Remove a shape from the scene"""
        self.scene_manager.remove_shape(shape_id)
        self.update()
        
    def selectShape(self, shape_id):
        """Select a shape in the scene"""
        self.scene_manager.select_shape(shape_id)
        self.update()
        
    def getSelectedShape(self):
        """Get the currently selected shape"""
        result = self.scene_manager.get_selected_shape()
        if result:
            shape_id, shape = result
            return shape
        return None
        
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

    def showStatusMessage(self, message, duration=2000):
        """Show a status message for the specified duration (ms)."""
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
            
        # Switch to 2D rendering mode
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width(), 0, self.height(), -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Disable lighting and depth test
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        
        # Draw text using QPainter
        painter = QPainter(self)
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(self.font())
        painter.drawText(10, self.height() - 10, self.status_message)
        painter.end()
        
        # Restore state
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def updateSnapState(self, enabled):
        """Update snapping state and show feedback."""
        self.showStatusMessage(f"Snapping: {'Enabled' if enabled else 'Disabled'}") 