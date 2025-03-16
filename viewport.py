from PyQt6.QtWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QMatrix4x4, QVector3D, QPainter
from OpenGL.GL import *
import numpy as np
from shapes_3d import SceneManager, Cube

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
        
    def mousePressEvent(self, event):
        """Handle mouse press events for camera control"""
        self.last_pos = event.pos()
        
    def mouseMoveEvent(self, event):
        """Handle mouse move events for camera control"""
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()
        
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Orbit camera
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
            
        self.last_pos = event.pos()
        
    def wheelEvent(self, event):
        """Handle mouse wheel events for camera zoom"""
        delta = event.angleDelta().y()
        zoom_factor = 0.0015
        
        self.camera_distance *= (1.0 - delta * zoom_factor)
        self.camera_distance = max(1.0, min(100.0, self.camera_distance))
        
        self.updateViewMatrix()
        
    def addShape(self, shape):
        """Add a shape to the scene"""
        self.scene_manager.addShape(shape)
        self.update()
        
    def removeShape(self, shape):
        """Remove a shape from the scene"""
        self.scene_manager.removeShape(shape)
        self.update()
        
    def selectShape(self, shape):
        """Select a shape in the scene"""
        self.scene_manager.selectShape(shape)
        self.update()
        
    def getSelectedShape(self):
        """Get the currently selected shape"""
        return self.scene_manager.getSelectedShape()
    
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
            
        # Save current matrices
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Disable lighting and depth test
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        
        # Set text color
        glColor3f(1.0, 1.0, 1.0)  # White text
        
        # Position text in bottom-left corner
        self.renderText(-0.95, -0.95, self.status_message)
        
        # Restore state
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def setTransformMode(self, mode):
        """Set the current transform mode."""
        self.transform_mode = mode
        self.scene_manager.set_transform_mode(mode)
        
        # Show status message for transform mode
        if mode:
            self.showStatusMessage(f"Transform Mode: {mode.capitalize()}")
        else:
            self.showStatusMessage("Transform Mode: None")
            
    def updateSnapState(self, enabled):
        """Update snapping state and show feedback."""
        self.showStatusMessage(f"Snapping: {'Enabled' if enabled else 'Disabled'}") 