from PyQt6.QtGui import QVector3D, QMatrix4x4
from OpenGL.GL import *
import numpy as np

class Shape3D:
    """Base class for 3D shapes"""
    def __init__(self):
        self.position = QVector3D(0, 0, 0)
        self.rotation = QVector3D(0, 0, 0)  # Euler angles in degrees
        self.scale = QVector3D(1, 1, 1)
        self.color = (0.7, 0.7, 0.7, 1.0)  # Default light gray
        self.selected = False
        
    def getModelMatrix(self):
        """Calculate and return the model matrix for this shape"""
        matrix = QMatrix4x4()
        matrix.setToIdentity()
        
        # Apply transformations in order: Scale -> Rotate -> Translate
        matrix.translate(self.position)
        matrix.rotate(self.rotation.x(), 1, 0, 0)
        matrix.rotate(self.rotation.y(), 0, 1, 0)
        matrix.rotate(self.rotation.z(), 0, 0, 1)
        matrix.scale(self.scale)
        
        return matrix
    
    def render(self):
        """Base render method to be overridden by subclasses"""
        pass
        
    def setSelected(self, selected):
        """Set the selection state of the shape"""
        self.selected = selected

    def intersectRay(self, ray_origin, ray_direction):
        """
        Test if a ray intersects with this shape.
        
        Args:
            ray_origin (QVector3D): Origin point of the ray in local space
            ray_direction (QVector3D): Direction vector of the ray in local space
            
        Returns:
            tuple: (hit, distance) where hit is a boolean indicating if there was an intersection,
                  and distance is the distance from ray origin to the intersection point
        """
        return False, float('inf')  # Base class returns no intersection

class Cube(Shape3D):
    """A basic cube shape centered at the origin"""
    def __init__(self, size=1.0):
        super().__init__()
        self.size = size
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        
    def _generateVertices(self):
        """Generate vertices for a unit cube"""
        s = self.size / 2
        return [
            # Front face
            [-s, -s,  s],
            [ s, -s,  s],
            [ s,  s,  s],
            [-s,  s,  s],
            # Back face
            [-s, -s, -s],
            [-s,  s, -s],
            [ s,  s, -s],
            [ s, -s, -s],
            # Top face
            [-s,  s, -s],
            [-s,  s,  s],
            [ s,  s,  s],
            [ s,  s, -s],
            # Bottom face
            [-s, -s, -s],
            [ s, -s, -s],
            [ s, -s,  s],
            [-s, -s,  s],
            # Right face
            [ s, -s, -s],
            [ s,  s, -s],
            [ s,  s,  s],
            [ s, -s,  s],
            # Left face
            [-s, -s, -s],
            [-s, -s,  s],
            [-s,  s,  s],
            [-s,  s, -s],
        ]
        
    def _generateNormals(self):
        """Generate normals for each vertex"""
        return [
            # Front face
            [0, 0, 1] * 4,
            # Back face
            [0, 0, -1] * 4,
            # Top face
            [0, 1, 0] * 4,
            # Bottom face
            [0, -1, 0] * 4,
            # Right face
            [1, 0, 0] * 4,
            # Left face
            [-1, 0, 0] * 4
        ]
        
    def render(self):
        """Render the cube using OpenGL"""
        model_matrix = self.getModelMatrix()
        glPushMatrix()
        glMultMatrixf(model_matrix.data())
        
        if self.selected:
            # Draw highlighted when selected
            glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow highlight
        else:
            glColor4f(*self.color)
        
        glBegin(GL_QUADS)
        for i, (vertex, normal) in enumerate(zip(self.vertices, [n for face in self.normals for n in face])):
            glNormal3fv(normal)
            glVertex3fv(vertex)
        glEnd()
        
        if self.selected:
            # Draw wireframe overlay when selected
            glDisable(GL_LIGHTING)
            glColor4f(1.0, 1.0, 0.0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glLineWidth(2.0)
            
            glBegin(GL_QUADS)
            for vertex in self.vertices:
                glVertex3fv(vertex)
            glEnd()
            
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glEnable(GL_LIGHTING)
            glLineWidth(1.0)
            
        glPopMatrix()

    def intersectRay(self, ray_origin, ray_direction):
        """
        Test if a ray intersects with the cube using slab method.
        The cube is centered at origin with size determined by self.size.
        """
        half_size = self.size / 2
        bounds_min = QVector3D(-half_size, -half_size, -half_size)
        bounds_max = QVector3D(half_size, half_size, half_size)
        
        # Initialize parameters for intersection
        t_min = float('-inf')
        t_max = float('inf')
        
        # Test intersection with each pair of planes
        for i in range(3):
            if abs(ray_direction[i]) < 1e-8:
                # Ray is parallel to slab, check if origin is within slab
                if ray_origin[i] < bounds_min[i] or ray_origin[i] > bounds_max[i]:
                    return False, float('inf')
            else:
                # Calculate intersection distances
                t1 = (bounds_min[i] - ray_origin[i]) / ray_direction[i]
                t2 = (bounds_max[i] - ray_origin[i]) / ray_direction[i]
                
                # Ensure t1 is the smaller value
                if t1 > t2:
                    t1, t2 = t2, t1
                
                # Update intersection interval
                t_min = max(t_min, t1)
                t_max = min(t_max, t2)
                
                if t_min > t_max:
                    return False, float('inf')
        
        # If we get here, the ray intersects the cube
        return True, max(0, t_min)

class Sphere(Shape3D):
    """A sphere shape centered at the origin"""
    def __init__(self, radius=1.0, segments=32):
        super().__init__()
        self.radius = radius
        self.segments = segments
        self.vertices, self.normals, self.indices = self._generateGeometry()
        
    def _generateGeometry(self):
        """Generate vertices, normals, and indices for a UV sphere"""
        vertices = []
        normals = []
        indices = []
        
        # Generate vertices and normals
        for phi in range(self.segments + 1):
            phi_angle = np.pi * phi / self.segments
            sin_phi = np.sin(phi_angle)
            cos_phi = np.cos(phi_angle)
            
            for theta in range(self.segments * 2 + 1):
                theta_angle = 2.0 * np.pi * theta / (self.segments * 2)
                sin_theta = np.sin(theta_angle)
                cos_theta = np.cos(theta_angle)
                
                # Calculate vertex position
                x = cos_theta * sin_phi
                y = sin_theta * sin_phi
                z = cos_phi
                
                # Add vertex (scaled by radius)
                vertices.append([x * self.radius, y * self.radius, z * self.radius])
                
                # Add normal (normalized position for a sphere)
                normals.append([x, y, z])
        
        # Generate indices for triangle strips
        for phi in range(self.segments):
            for theta in range(self.segments * 2):
                first = phi * (self.segments * 2 + 1) + theta
                second = first + self.segments * 2 + 1
                
                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])
        
        return vertices, normals, indices
        
    def render(self):
        """Render the sphere using OpenGL"""
        model_matrix = self.getModelMatrix()
        glPushMatrix()
        glMultMatrixf(model_matrix.data())
        
        if self.selected:
            # Draw highlighted when selected
            glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow highlight
        else:
            glColor4f(*self.color)
        
        # Draw the sphere using triangle strips
        glBegin(GL_TRIANGLES)
        for i in range(0, len(self.indices), 3):
            idx1, idx2, idx3 = self.indices[i:i+3]
            
            # First vertex
            glNormal3fv(self.normals[idx1])
            glVertex3fv(self.vertices[idx1])
            
            # Second vertex
            glNormal3fv(self.normals[idx2])
            glVertex3fv(self.vertices[idx2])
            
            # Third vertex
            glNormal3fv(self.normals[idx3])
            glVertex3fv(self.vertices[idx3])
        glEnd()
        
        if self.selected:
            # Draw wireframe overlay when selected
            glDisable(GL_LIGHTING)
            glColor4f(1.0, 1.0, 0.0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glLineWidth(2.0)
            
            glBegin(GL_TRIANGLES)
            for i in range(0, len(self.indices), 3):
                idx1, idx2, idx3 = self.indices[i:i+3]
                glVertex3fv(self.vertices[idx1])
                glVertex3fv(self.vertices[idx2])
                glVertex3fv(self.vertices[idx3])
            glEnd()
            
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glEnable(GL_LIGHTING)
            glLineWidth(1.0)
            
        glPopMatrix()

    def intersectRay(self, ray_origin, ray_direction):
        """
        Test if a ray intersects with the sphere using quadratic equation.
        The sphere is centered at origin with radius determined by self.radius.
        """
        # Calculate quadratic equation coefficients
        a = ray_direction.lengthSquared()
        b = 2.0 * QVector3D.dotProduct(ray_direction, ray_origin)
        c = ray_origin.lengthSquared() - (self.radius * self.radius)
        
        # Calculate discriminant
        discriminant = b * b - 4.0 * a * c
        
        if discriminant < 0:
            return False, float('inf')  # No intersection
            
        # Calculate intersection distances
        sqrt_discriminant = np.sqrt(discriminant)
        t1 = (-b - sqrt_discriminant) / (2.0 * a)
        t2 = (-b + sqrt_discriminant) / (2.0 * a)
        
        # Return closest positive intersection
        if t1 > 0:
            return True, t1
        elif t2 > 0:
            return True, t2
        else:
            return False, float('inf')

class Cylinder(Shape3D):
    """A cylinder shape centered at the origin"""
    def __init__(self, radius=1.0, height=2.0, segments=32):
        super().__init__()
        self.radius = radius
        self.height = height
        self.segments = segments
        self.vertices, self.normals, self.indices = self._generateGeometry()
        
    def _generateGeometry(self):
        """Generate vertices, normals, and indices for a cylinder"""
        vertices = []
        normals = []
        indices = []
        
        half_height = self.height / 2
        
        # Generate vertices and normals for the side of the cylinder
        for i in range(self.segments + 1):
            angle = 2.0 * np.pi * i / self.segments
            cos_angle = np.cos(angle)
            sin_angle = np.sin(angle)
            
            # Top vertex
            vertices.append([self.radius * cos_angle, self.radius * sin_angle, half_height])
            normals.append([cos_angle, sin_angle, 0.0])
            
            # Bottom vertex
            vertices.append([self.radius * cos_angle, self.radius * sin_angle, -half_height])
            normals.append([cos_angle, sin_angle, 0.0])
        
        # Generate indices for the side triangles
        for i in range(self.segments):
            base = i * 2
            next_base = ((i + 1) % self.segments) * 2
            
            # First triangle
            indices.extend([base, base + 1, next_base])
            # Second triangle
            indices.extend([next_base, base + 1, next_base + 1])
            
        # Generate vertices and normals for the top cap
        center_top_idx = len(vertices)
        vertices.append([0, 0, half_height])  # Center point
        normals.append([0, 0, 1])  # Up normal
        
        for i in range(self.segments):
            angle = 2.0 * np.pi * i / self.segments
            cos_angle = np.cos(angle)
            sin_angle = np.sin(angle)
            
            vertices.append([self.radius * cos_angle, self.radius * sin_angle, half_height])
            normals.append([0, 0, 1])  # Up normal
            
            if i > 0:
                # Add triangle for this segment of the cap
                indices.extend([center_top_idx, center_top_idx + i, center_top_idx + i + 1])
        # Close the last triangle of the top cap
        indices.extend([center_top_idx, center_top_idx + self.segments, center_top_idx + 1])
        
        # Generate vertices and normals for the bottom cap
        center_bottom_idx = len(vertices)
        vertices.append([0, 0, -half_height])  # Center point
        normals.append([0, 0, -1])  # Down normal
        
        for i in range(self.segments):
            angle = 2.0 * np.pi * i / self.segments
            cos_angle = np.cos(angle)
            sin_angle = np.sin(angle)
            
            vertices.append([self.radius * cos_angle, self.radius * sin_angle, -half_height])
            normals.append([0, 0, -1])  # Down normal
            
            if i > 0:
                # Add triangle for this segment of the cap (note winding order is reversed)
                indices.extend([center_bottom_idx, center_bottom_idx + i + 1, center_bottom_idx + i])
        # Close the last triangle of the bottom cap
        indices.extend([center_bottom_idx, center_bottom_idx + 1, center_bottom_idx + self.segments])
        
        return vertices, normals, indices
        
    def render(self):
        """Render the cylinder using OpenGL"""
        model_matrix = self.getModelMatrix()
        glPushMatrix()
        glMultMatrixf(model_matrix.data())
        
        if self.selected:
            # Draw highlighted when selected
            glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow highlight
        else:
            glColor4f(*self.color)
        
        # Draw the cylinder using triangles
        glBegin(GL_TRIANGLES)
        for i in range(0, len(self.indices), 3):
            idx1, idx2, idx3 = self.indices[i:i+3]
            
            # First vertex
            glNormal3fv(self.normals[idx1])
            glVertex3fv(self.vertices[idx1])
            
            # Second vertex
            glNormal3fv(self.normals[idx2])
            glVertex3fv(self.vertices[idx2])
            
            # Third vertex
            glNormal3fv(self.normals[idx3])
            glVertex3fv(self.vertices[idx3])
        glEnd()
        
        if self.selected:
            # Draw wireframe overlay when selected
            glDisable(GL_LIGHTING)
            glColor4f(1.0, 1.0, 0.0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glLineWidth(2.0)
            
            glBegin(GL_TRIANGLES)
            for i in range(0, len(self.indices), 3):
                idx1, idx2, idx3 = self.indices[i:i+3]
                glVertex3fv(self.vertices[idx1])
                glVertex3fv(self.vertices[idx2])
                glVertex3fv(self.vertices[idx3])
            glEnd()
            
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glEnable(GL_LIGHTING)
            glLineWidth(1.0)
            
        glPopMatrix()

    def intersectRay(self, ray_origin, ray_direction):
        """
        Test if a ray intersects with the cylinder.
        The cylinder is centered at origin with radius and height determined by self.radius and self.height.
        """
        half_height = self.height / 2
        
        # Test intersection with infinite cylinder
        a = ray_direction.x() * ray_direction.x() + ray_direction.y() * ray_direction.y()
        b = 2.0 * (ray_origin.x() * ray_direction.x() + ray_origin.y() * ray_direction.y())
        c = ray_origin.x() * ray_origin.x() + ray_origin.y() * ray_origin.y() - self.radius * self.radius
        
        discriminant = b * b - 4.0 * a * c
        
        if discriminant < 0:
            return False, float('inf')
            
        # Calculate cylinder intersection points
        sqrt_discriminant = np.sqrt(discriminant)
        t1 = (-b - sqrt_discriminant) / (2.0 * a)
        t2 = (-b + sqrt_discriminant) / (2.0 * a)
        
        # Calculate z coordinates of intersection points
        z1 = ray_origin.z() + t1 * ray_direction.z()
        z2 = ray_origin.z() + t2 * ray_direction.z()
        
        # Check if intersection points are within cylinder height
        t1_valid = t1 > 0 and -half_height <= z1 <= half_height
        t2_valid = t2 > 0 and -half_height <= z2 <= half_height
        
        # Test intersection with caps
        if ray_direction.z() != 0:
            t_top = (half_height - ray_origin.z()) / ray_direction.z()
            t_bottom = (-half_height - ray_origin.z()) / ray_direction.z()
            
            # Check if cap intersections are within radius
            if t_top > 0:
                p = ray_origin + ray_direction * t_top
                if p.x() * p.x() + p.y() * p.y() <= self.radius * self.radius:
                    if not t1_valid or t_top < t1:
                        t1 = t_top
                        t1_valid = True
                        
            if t_bottom > 0:
                p = ray_origin + ray_direction * t_bottom
                if p.x() * p.x() + p.y() * p.y() <= self.radius * self.radius:
                    if not t1_valid or t_bottom < t1:
                        t1 = t_bottom
                        t1_valid = True
        
        if t1_valid:
            return True, t1
        elif t2_valid:
            return True, t2
        else:
            return False, float('inf')

class SceneManager:
    """Manages all shapes in the 3D scene"""
    def __init__(self):
        self.shapes = []
        self.selected_shape = None
        
    def addShape(self, shape):
        """Add a shape to the scene"""
        self.shapes.append(shape)
        
    def removeShape(self, shape):
        """Remove a shape from the scene"""
        if shape in self.shapes:
            self.shapes.remove(shape)
            if self.selected_shape == shape:
                self.selected_shape = None
                
    def renderScene(self):
        """Render all shapes in the scene"""
        for shape in self.shapes:
            shape.render()
            
    def selectShape(self, shape):
        """Select a shape and deselect others"""
        # Deselect current shape if any
        if self.selected_shape:
            self.selected_shape.setSelected(False)
            
        # Select new shape if provided
        self.selected_shape = shape
        if shape:
            shape.setSelected(True)
            
    def getSelectedShape(self):
        """Return the currently selected shape"""
        return self.selected_shape 