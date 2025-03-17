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

class ExtrudedShape(Shape3D):
    """A shape created by extruding a 2D profile along the Z-axis"""
    
    # Preset profiles for common shapes (normalized to unit size)
    PRESETS = {
        'triangle': [(1, 0), (-0.5, 0.866), (-0.5, -0.866), (1, 0)],
        'square': [(1, 1), (-1, 1), (-1, -1), (1, -1), (1, 1)],
        'pentagon': [(0.951, 0.309), (0, 1), (-0.951, 0.309), (-0.588, -0.809), (0.588, -0.809), (0.951, 0.309)],
        'hexagon': [(1, 0), (0.5, 0.866), (-0.5, 0.866), (-1, 0), (-0.5, -0.866), (0.5, -0.866), (1, 0)],
        'octagon': [(0.924, 0.383), (0.383, 0.924), (-0.383, 0.924), (-0.924, 0.383),
                    (-0.924, -0.383), (-0.383, -0.924), (0.383, -0.924), (0.924, -0.383), (0.924, 0.383)],
        'star': [(1, 0), (0.309, 0.309), (0, 1), (-0.309, 0.309), (-1, 0),
                (-0.309, -0.309), (0, -1), (0.309, -0.309), (1, 0)],
        'circle': [(np.cos(a), np.sin(a)) for a in np.linspace(0, 2 * np.pi, 32, endpoint=True)],
        'rectangle': [(1, 0.5), (-1, 0.5), (-1, -0.5), (1, -0.5), (1, 0.5)],
        'rounded_rectangle': [(1 - min(0.2, abs(t - 0.5)), 0.5 * np.sign(np.sin(2 * np.pi * t))) 
                            for t in np.linspace(0, 1, 40, endpoint=True)],
        'gear': [(np.cos(a) * (1 + 0.2 * np.sin(5 * a)), np.sin(a) * (1 + 0.2 * np.sin(5 * a))) 
                for a in np.linspace(0, 2 * np.pi, 50, endpoint=True)]
    }
    
    def __init__(self, num_sides=6, radius_x=1.0, radius_y=None, height=2.0, preset_profile=None, 
                 custom_profile=None, smooth_profile=False, smooth_segments=32):
        """
        Initialize an extruded shape.
        
        Args:
            num_sides (int): Number of sides for regular polygon
            radius_x (float): X radius (width/2)
            radius_y (float): Y radius (depth/2). If None, uses radius_x for uniform scaling
            height (float): Height of extrusion
            preset_profile (str): Name of preset profile to use
            custom_profile (list): List of (x,y) points defining a custom profile
            smooth_profile (bool): Whether to apply Catmull-Rom smoothing
            smooth_segments (int): Number of segments per edge when smoothing
        """
        super().__init__()
        self.num_sides = num_sides
        self.radius_x = radius_x
        self.radius_y = radius_y if radius_y is not None else radius_x
        self.height = height
        
        if custom_profile is not None:
            self._validate_profile(custom_profile)
            points = custom_profile
        elif preset_profile is not None:
            if preset_profile not in self.PRESETS:
                raise ValueError(f"Unknown preset profile: {preset_profile}. Available presets: {list(self.PRESETS.keys())}")
            points = self.PRESETS[preset_profile]
        else:
            angles = np.linspace(0, 2 * np.pi, self.num_sides, endpoint=True)
            points = [(np.cos(angle), np.sin(angle)) for angle in angles]
        
        # Apply smoothing if requested
        if smooth_profile:
            points = self._smooth_profile(points, smooth_segments)
            
        # Scale points
        self.polygon_points = [(x * self.radius_x, y * self.radius_y) for x, y in points]
        
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        self.indices = self._generateIndices()
    
    def _smooth_profile(self, points, segments_per_edge):
        """
        Apply Catmull-Rom spline smoothing to profile points.
        
        Args:
            points (list): List of (x,y) points to smooth
            segments_per_edge (int): Number of segments to generate between each pair of points
            
        Returns:
            list: Smoothed profile points
        """
        def catmull_rom(p0, p1, p2, p3, t):
            t2 = t * t
            t3 = t2 * t
            return (
                0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3,
                       (2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            )
        
        # Ensure profile is closed
        if points[0] != points[-1]:
            points = points + [points[0]]
            
        smoothed = []
        n = len(points)
        for i in range(n - 1):
            p0 = points[(i - 1) % (n - 1)]  # Use modulo to wrap around for first point
            p1 = points[i]
            p2 = points[(i + 1) % (n - 1)]
            p3 = points[(i + 2) % (n - 1)]
            
            for t in np.linspace(0, 1, segments_per_edge, endpoint=(i == n-2)):
                smoothed.append(catmull_rom(p0, p1, p2, p3, t))
                
        return smoothed
    
    def rotate_profile(self, angle_degrees):
        """
        Rotate the profile around its center by the specified angle.
        
        Args:
            angle_degrees (float): Rotation angle in degrees
        """
        angle_rad = np.radians(angle_degrees)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        
        self.polygon_points = [
            (x * cos_a - y * sin_a, x * sin_a + y * cos_a)
            for x, y in self.polygon_points
        ]
        
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        self.indices = self._generateIndices()
    
    def mirror_profile(self, axis='x'):
        """
        Mirror the profile across the specified axis.
        
        Args:
            axis (str): 'x' or 'y' axis to mirror across
        """
        if axis.lower() not in {'x', 'y'}:
            raise ValueError("Axis must be 'x' or 'y'")
            
        if axis.lower() == 'x':
            self.polygon_points = [(x, -y) for x, y in self.polygon_points]
        else:
            self.polygon_points = [(-x, y) for x, y in self.polygon_points]
            
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        self.indices = self._generateIndices()
    
    def scale_profile(self, scale_x, scale_y=None):
        """
        Scale the profile by the specified factors.
        
        Args:
            scale_x (float): X scaling factor
            scale_y (float): Y scaling factor. If None, uses scale_x
        """
        scale_y = scale_y if scale_y is not None else scale_x
        self.radius_x *= scale_x
        self.radius_y *= scale_y
        
        self.polygon_points = [(x * scale_x, y * scale_y) 
                             for x, y in self.polygon_points]
        
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        self.indices = self._generateIndices()

    def _validate_profile(self, profile, min_angle_threshold=15):
        """
        Validate a custom profile for correctness.
        
        Args:
            profile (list): List of (x,y) points defining the profile
            min_angle_threshold (float): Minimum allowed angle between edges in degrees
            
        Raises:
            ValueError: If the profile is invalid
        """
        if len(profile) < 4:  # Need at least 3 points plus closure
            raise ValueError("Profile must have at least 3 points plus closure point.")
            
        # Check if profile is closed
        if not np.allclose(profile[0], profile[-1]):
            raise ValueError("Profile must be closed (first and last points must be the same).")
            
        # Check for self-intersections
        if self._is_self_intersecting(profile):
            raise ValueError("Profile has self-intersecting edges.")
            
        # Check for degenerate edges (zero length)
        for i in range(len(profile) - 1):
            p1, p2 = profile[i], profile[i + 1]
            if np.allclose(p1, p2):
                raise ValueError(f"Profile has degenerate edge at points {i}-{i+1}.")
                
        # Check for minimum area
        if self._calculate_area(profile) < 1e-6:
            raise ValueError("Profile has zero or negative area.")
            
        # Check for minimum angle between edges
        min_angle = self._calculate_min_angle(profile)
        if min_angle < min_angle_threshold:
            raise ValueError(f"Profile has sharp angles (minimum angle: {min_angle:.1f} degrees).")
            
        # Check for convexity
        if not self._is_convex(profile):
            raise ValueError("Profile must be convex.")

    def _calculate_min_angle(self, profile):
        """
        Calculate the minimum angle between consecutive edges.
        
        Args:
            profile (list): List of (x,y) points defining the profile
            
        Returns:
            float: Minimum angle in degrees
        """
        min_angle = float('inf')
        n = len(profile) - 1  # Don't check the closure point
        
        for i in range(n):
            p1 = profile[i]
            p2 = profile[i + 1]
            p3 = profile[(i + 2) % n]
            
            # Calculate vectors
            v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
            v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
            
            # Calculate angle
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Handle numerical errors
            angle = np.degrees(np.arccos(cos_angle))
            
            min_angle = min(min_angle, angle)
            
        return min_angle
    
    def _is_convex(self, profile):
        """
        Check if a profile is convex.
        
        Args:
            profile (list): List of (x,y) points defining the profile
            
        Returns:
            bool: True if profile is convex
        """
        n = len(profile) - 1  # Don't check the closure point
        if n < 3:
            return True  # Triangles are always convex
            
        # Calculate cross products to determine winding order
        def cross_product(p1, p2, p3):
            return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
            
        # Check if all cross products have the same sign
        sign = None
        for i in range(n):
            p1 = profile[i]
            p2 = profile[i + 1]
            p3 = profile[(i + 2) % n]
            
            cross = cross_product(p1, p2, p3)
            if abs(cross) < 1e-6:  # Handle collinear points
                continue
                
            if sign is None:
                sign = np.sign(cross)
            elif np.sign(cross) != sign:
                return False
                
        return True
    
    def _find_features(self, profile, method='angle', angle_threshold=45, curvature_threshold=0.1, 
                      edge_length_threshold=0.1):
        """
        Find significant features in a profile using specified method.
        
        Args:
            profile (list): List of (x,y) points defining the profile
            method (str): 'angle', 'curvature', or 'edge_length' for feature detection
            angle_threshold (float): Angle threshold in degrees for angle-based detection
            curvature_threshold (float): Curvature threshold for curvature-based detection
            edge_length_threshold (float): Relative length threshold for edge-based detection
            
        Returns:
            list: Indices of feature points
        """
        features = []
        n = len(profile) - 1  # Don't check the closure point
        
        if method == 'angle':
            for i in range(n):
                p1 = profile[i]
                p2 = profile[i + 1]
                p3 = profile[(i + 2) % n]
                
                # Calculate vectors
                v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
                v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
                
                # Calculate angle
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                angle = np.degrees(np.arccos(cos_angle))
                
                # Add point if angle is significant
                if angle > angle_threshold:
                    features.append(i + 1)  # Add the vertex point
                    
        elif method == 'curvature':
            for i in range(1, n-1):  # Skip first and last points
                curvature = self._curvature_at_point(profile[i-1], profile[i], profile[i+1])
                if curvature > curvature_threshold:
                    features.append(i)
                    
        elif method == 'edge_length':
            # Calculate average edge length
            edge_lengths = []
            for i in range(n):
                p1 = profile[i]
                p2 = profile[i + 1]
                edge_lengths.append(np.linalg.norm(np.array(p2) - np.array(p1)))
            avg_length = np.mean(edge_lengths)
            
            # Find edges significantly longer than average
            for i in range(n):
                if edge_lengths[i] > avg_length * (1 + edge_length_threshold):
                    features.append(i + 1)  # Add the vertex point
                    
        return features

    def _curvature_at_point(self, p0, p1, p2):
        """
        Calculate discrete curvature at a point using its neighbors.
        
        Args:
            p0 (tuple): Previous point (x,y)
            p1 (tuple): Current point (x,y)
            p2 (tuple): Next point (x,y)
            
        Returns:
            float: Curvature value at p1
        """
        v1 = np.array(p0) - np.array(p1)
        v2 = np.array(p2) - np.array(p1)
        
        # Calculate angle between vectors
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle)
        
        # Calculate curvature as angle divided by average edge length
        return angle / (np.linalg.norm(v1) + np.linalg.norm(v2))

    def morph_profile_with_features(self, target_profile, t, num_points=None, correspondences=None, 
                                  feature_method='angle', mapping_method='position',
                                  angle_threshold=45, curvature_threshold=0.1, 
                                  edge_length_threshold=0.1):
        """
        Morph between profiles using feature-based interpolation with optional user-defined correspondences.
        
        Args:
            target_profile (list): List of (x,y) points defining target profile
            t (float): Interpolation factor (0 to 1)
            num_points (int): Number of points in result. If None, uses max of both profiles
            correspondences (dict): Optional mapping from source indices to target indices
            feature_method (str): 'angle', 'curvature', or 'edge_length' for feature detection
            mapping_method (str): 'position' or 'angle' for feature mapping strategy
            angle_threshold (float): Angle threshold in degrees for angle-based detection
            curvature_threshold (float): Curvature threshold for curvature-based detection
            edge_length_threshold (float): Relative length threshold for edge-based detection
            
        Raises:
            ValueError: If either profile is invalid or correspondences are invalid
        """
        # Validate both profiles
        self._validate_profile(self.polygon_points)
        self._validate_profile(target_profile)
        
        # Find features in both profiles
        source_features = self._find_features(self.polygon_points, method=feature_method,
                                            angle_threshold=angle_threshold,
                                            curvature_threshold=curvature_threshold,
                                            edge_length_threshold=edge_length_threshold)
        target_features = self._find_features(target_profile, method=feature_method,
                                            angle_threshold=angle_threshold,
                                            curvature_threshold=curvature_threshold,
                                            edge_length_threshold=edge_length_threshold)
        
        # Validate correspondences if provided
        if correspondences is not None:
            for src_idx, tgt_idx in correspondences.items():
                if src_idx >= len(self.polygon_points) or tgt_idx >= len(target_profile):
                    raise ValueError("Invalid correspondence indices")
                if src_idx not in source_features:
                    raise ValueError(f"Source index {src_idx} is not a feature point")
                if tgt_idx not in target_features:
                    raise ValueError(f"Target index {tgt_idx} is not a feature point")
        
        # Resample profiles to have the same number of points
        if num_points is None:
            num_points = max(len(self.polygon_points), len(target_profile))
            
        source = self._resample_profile(self.polygon_points, num_points)
        target = self._resample_profile(target_profile, num_points)
        
        # Use user-defined correspondences if provided, else use automatic mapping
        if correspondences is not None:
            feature_map = correspondences
        else:
            feature_map = self._map_features(source, target, source_features, target_features, 
                                           method=mapping_method)
        
        # Interpolate between profiles, giving more weight to feature points
        self.polygon_points = []
        for i in range(num_points):
            if i in feature_map:
                # Feature point - interpolate directly
                j = feature_map[i]
                x1, y1 = source[i]
                x2, y2 = target[j]
                self.polygon_points.append((
                    x1 + (x2 - x1) * t,
                    y1 + (y2 - y1) * t
                ))
            else:
                # Non-feature point - interpolate with feature influence
                x1, y1 = source[i]
                x2, y2 = target[i]
                # Find nearest features
                dist1, feat1 = self._find_nearest_feature(i, source_features)
                dist2, feat2 = self._find_nearest_feature(i, target_features)
                # Weight interpolation based on feature distances
                w1 = 1.0 / (dist1 + 1e-6)
                w2 = 1.0 / (dist2 + 1e-6)
                w = w1 / (w1 + w2)
                self.polygon_points.append((
                    x1 + (x2 - x1) * (t * w + (1 - w) * 0.5),
                    y1 + (y2 - y1) * (t * w + (1 - w) * 0.5)
                ))
        
        # Update geometry
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        self.indices = self._generateIndices()

    def _map_features(self, source, target, source_features, target_features, method='position'):
        """
        Map feature points between source and target profiles.
        
        Args:
            source (list): Source profile points
            target (list): Target profile points
            source_features (list): Indices of source feature points
            target_features (list): Indices of target feature points
            method (str): 'position' or 'angle' for mapping strategy
            
        Returns:
            dict: Mapping from source indices to target indices
        """
        mapping = {}
        
        if method == 'position':
            # Map based on relative position along profile
            for i, src_idx in enumerate(source_features):
                tgt_idx = target_features[int(i * len(target_features) / len(source_features))]
                mapping[src_idx] = tgt_idx
                
        elif method == 'angle':
            # Map based on similar angles at features
            src_angles = []
            tgt_angles = []
            
            # Calculate angles at features for both profiles
            for idx in source_features:
                p1 = source[idx]
                p2 = source[(idx + 1) % len(source)]
                p3 = source[(idx + 2) % len(source)]
                angle = self._calculate_angle(p1, p2, p3)
                src_angles.append(angle)
                
            for idx in target_features:
                p1 = target[idx]
                p2 = target[(idx + 1) % len(target)]
                p3 = target[(idx + 2) % len(target)]
                angle = self._calculate_angle(p1, p2, p3)
                tgt_angles.append(angle)
            
            # Map features with similar angles
            for i, src_idx in enumerate(source_features):
                src_angle = src_angles[i]
                # Find target feature with closest angle
                closest_idx = min(range(len(target_features)), 
                                key=lambda j: abs(tgt_angles[j] - src_angle))
                mapping[src_idx] = target_features[closest_idx]
                
        return mapping
    
    def _calculate_angle(self, p1, p2, p3):
        """Calculate angle between three points in degrees."""
        v1 = np.array(p2) - np.array(p1)
        v2 = np.array(p3) - np.array(p2)
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        return np.degrees(np.arccos(cos_angle))

    def _find_nearest_feature(self, point_idx, features):
        """
        Find the nearest feature point to a given point.
        
        Args:
            point_idx (int): Index of the point
            features (list): List of feature point indices
            
        Returns:
            tuple: (distance, feature_index)
        """
        min_dist = float('inf')
        nearest_feature = None
        
        for feat_idx in features:
            dist = abs(feat_idx - point_idx)
            if dist < min_dist:
                min_dist = dist
                nearest_feature = feat_idx
                
        return min_dist, nearest_feature

    def _generateVertices(self):
        """Generate vertices for the extruded shape"""
        vertices = []
        half_height = self.height / 2
        
        # Use precomputed polygon points for vertices
        # Top face vertices
        for x, y in self.polygon_points:
            vertices.append([x, y, half_height])
            
        # Bottom face vertices
        for x, y in self.polygon_points:
            vertices.append([x, y, -half_height])
            
        return vertices
        
    def _generateNormals(self):
        """Generate normals for each vertex"""
        normals = []
        
        # Top face normals
        for _ in range(len(self.polygon_points)):
            normals.append([0, 0, 1])
            
        # Bottom face normals
        for _ in range(len(self.polygon_points)):
            normals.append([0, 0, -1])
            
        # Side face normals - calculate from adjacent points
        num_points = len(self.polygon_points)
        for i in range(num_points):
            p1 = self.polygon_points[i]
            p2 = self.polygon_points[(i + 1) % num_points]
            # Calculate normal as perpendicular to edge
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = np.sqrt(dx * dx + dy * dy)
            normal = [dy / length, -dx / length, 0] if length > 0 else [1, 0, 0]
            normals.extend([normal, normal])  # Same normal for top and bottom vertices of each side
            
        return normals
        
    def _generateIndices(self):
        """Generate indices for triangles"""
        indices = []
        
        # Top face triangles
        for i in range(self.num_sides - 2):
            indices.extend([0, i + 1, i + 2])
            
        # Bottom face triangles
        base = self.num_sides
        for i in range(self.num_sides - 2):
            indices.extend([base, base + i + 2, base + i + 1])
            
        # Side faces (quads split into triangles)
        for i in range(self.num_sides):
            next_i = (i + 1) % self.num_sides
            top1, top2 = i, next_i
            bottom1, bottom2 = top1 + self.num_sides, top2 + self.num_sides
            
            # First triangle of quad
            indices.extend([top1, bottom1, top2])
            # Second triangle of quad
            indices.extend([bottom1, bottom2, top2])
            
        return indices
        
    def render(self):
        """Render the extruded shape using OpenGL"""
        model_matrix = self.getModelMatrix()
        glPushMatrix()
        glMultMatrixf(model_matrix.data())
        
        if self.selected:
            glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow highlight
        else:
            glColor4f(*self.color)
        
        # Draw the shape
        glBegin(GL_TRIANGLES)
        for i in range(0, len(self.indices), 3):
            for j in range(3):
                idx = self.indices[i + j]
                glNormal3fv(self.normals[idx])
                glVertex3fv(self.vertices[idx])
        glEnd()
        
        if self.selected:
            # Draw wireframe overlay when selected
            glDisable(GL_LIGHTING)
            glColor4f(1.0, 1.0, 0.0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glLineWidth(2.0)
            
            glBegin(GL_TRIANGLES)
            for i in range(0, len(self.indices), 3):
                for j in range(3):
                    idx = self.indices[i + j]
                    glVertex3fv(self.vertices[idx])
            glEnd()
            
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glEnable(GL_LIGHTING)
            glLineWidth(1.0)
            
        glPopMatrix()

    def intersectRay(self, ray_origin, ray_direction):
        """
        Test if a ray intersects with the extruded shape.
        Uses a combination of cylinder intersection test for sides and exact polygon test for caps.
        """
        half_height = self.height / 2
        min_t = float('inf')
        hit = False
        
        # Test intersection with infinite cylinder (for side faces)
        a = ray_direction.x() * ray_direction.x() + ray_direction.y() * ray_direction.y()
        b = 2.0 * (ray_origin.x() * ray_direction.x() + ray_origin.y() * ray_direction.y())
        c = ray_origin.x() * ray_origin.x() + ray_origin.y() * ray_origin.y() - self.radius_x * self.radius_x
        
        discriminant = b * b - 4.0 * a * c
        
        if discriminant >= 0:
            # Calculate cylinder intersection points
            sqrt_discriminant = np.sqrt(discriminant)
            t1 = (-b - sqrt_discriminant) / (2.0 * a)
            t2 = (-b + sqrt_discriminant) / (2.0 * a)
            
            # Check if intersection points are within height bounds
            for t in [t1, t2]:
                if t > 0:
                    z = ray_origin.z() + t * ray_direction.z()
                    if -half_height <= z <= half_height:
                        hit = True
                        min_t = min(min_t, t)
        
        # Test intersection with top and bottom caps using exact polygon test
        if ray_direction.z() != 0:
            # Test top cap
            t_top = (half_height - ray_origin.z()) / ray_direction.z()
            if t_top > 0:
                x = ray_origin.x() + t_top * ray_direction.x()
                y = ray_origin.y() + t_top * ray_direction.y()
                # Quick bounding circle test before detailed polygon test
                if x * x + y * y <= self.radius_x * self.radius_x and self._point_in_polygon(x, y, self.polygon_points):
                    hit = True
                    min_t = min(min_t, t_top)
            
            # Test bottom cap
            t_bottom = (-half_height - ray_origin.z()) / ray_direction.z()
            if t_bottom > 0:
                x = ray_origin.x() + t_bottom * ray_direction.x()
                y = ray_origin.y() + t_bottom * ray_direction.y()
                # Quick bounding circle test before detailed polygon test
                if x * x + y * y <= self.radius_x * self.radius_x and self._point_in_polygon(x, y, self.polygon_points):
                    hit = True
                    min_t = min(min_t, t_bottom)
        
        return hit, min_t

    def _point_in_polygon(self, x, y, polygon_points):
        """
        Test if a point (x,y) lies inside a polygon defined by polygon_points.
        Uses the ray casting algorithm (even-odd rule).
        """
        inside = False
        j = len(polygon_points) - 1
        
        for i in range(len(polygon_points)):
            xi, yi = polygon_points[i]
            xj, yj = polygon_points[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside

    def shear_profile(self, shear_x=0, shear_y=0):
        """
        Apply shear transformation to the profile.
        
        Args:
            shear_x (float): Shear factor in X direction (shears Y coordinates)
            shear_y (float): Shear factor in Y direction (shears X coordinates)
        """
        # Calculate centroid for shear around center
        cx = sum(x for x, y in self.polygon_points) / len(self.polygon_points)
        cy = sum(y for x, y in self.polygon_points) / len(self.polygon_points)
        
        # Apply shear transformation
        self.polygon_points = [
            (x + (y - cy) * shear_x, y + (x - cx) * shear_y)
            for x, y in self.polygon_points
        ]
        
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        self.indices = self._generateIndices()
    
    def translate_profile(self, dx=0, dy=0):
        """
        Translate the profile by the specified offsets.
        
        Args:
            dx (float): Translation in X direction
            dy (float): Translation in Y direction
        """
        self.polygon_points = [(x + dx, y + dy) for x, y in self.polygon_points]
        
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        self.indices = self._generateIndices()
    
    def interpolate_profile(self, target_profile, t):
        """
        Interpolate between current profile and target profile.
        
        Args:
            target_profile (list): List of (x,y) points defining target profile
            t (float): Interpolation factor (0 to 1)
            
        Raises:
            ValueError: If profiles have different number of points
        """
        if len(target_profile) != len(self.polygon_points):
            raise ValueError("Profiles must have the same number of points")
            
        # Ensure target profile is closed
        if target_profile[0] != target_profile[-1]:
            target_profile = target_profile + [target_profile[0]]
            
        # Interpolate between points
        self.polygon_points = [
            (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
            for (x1, y1), (x2, y2) in zip(self.polygon_points, target_profile)
        ]
        
        self.vertices = self._generateVertices()
        self.normals = self._generateNormals()
        self.indices = self._generateIndices()

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