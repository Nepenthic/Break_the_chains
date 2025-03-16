from PyQt6.QtWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMatrix4x4, QVector3D
from OpenGL.GL import *
import numpy as np
from shapes_3d import SceneManager, Cube

class Viewport(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initializeCamera()
        self.last_pos = QPoint()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Enable key events
        
        # Initialize scene manager
        self.scene_manager = SceneManager()
        
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
        self.scene_manager.renderScene()
        
    def drawAxes(self):
        """Draw coordinate axes"""
        glDisable(GL_LIGHTING)
        glBegin(GL_LINES)
        
        # X axis (red)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(5, 0, 0)
        
        # Y axis (green)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 5, 0)
        
        # Z axis (blue)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 5)
        
        glEnd()
        glEnable(GL_LIGHTING)
        
    def drawGrid(self):
        """Draw a reference grid"""
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.3)  # Gray color
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
        glEnable(GL_LIGHTING)
        
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