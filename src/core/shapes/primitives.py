from typing import Optional
import numpy as np
import trimesh
from .base import Shape, Transform

class Cube(Shape):
    """A cube shape defined by its size."""
    
    def __init__(self, size: float = 1.0, transform: Optional[Transform] = None):
        """
        Initialize a cube.
        
        Args:
            size: The length of each side of the cube
            transform: Optional initial transformation
        """
        super().__init__(transform)
        self.size = size
    
    def _create_mesh(self) -> trimesh.Trimesh:
        """Create a cube mesh."""
        return trimesh.creation.box(extents=[self.size] * 3)

class Sphere(Shape):
    """A sphere shape defined by its radius."""
    
    def __init__(self, radius: float = 1.0, transform: Optional[Transform] = None):
        """
        Initialize a sphere.
        
        Args:
            radius: The radius of the sphere
            transform: Optional initial transformation
        """
        super().__init__(transform)
        self.radius = radius
    
    def _create_mesh(self) -> trimesh.Trimesh:
        """Create a sphere mesh."""
        return trimesh.creation.icosphere(radius=self.radius)

class Cylinder(Shape):
    """A cylinder shape defined by its radius and height."""
    
    def __init__(
        self,
        radius: float = 1.0,
        height: float = 2.0,
        transform: Optional[Transform] = None
    ):
        """
        Initialize a cylinder.
        
        Args:
            radius: The radius of the cylinder
            height: The height of the cylinder
            transform: Optional initial transformation
        """
        super().__init__(transform)
        self.radius = radius
        self.height = height
    
    def _create_mesh(self) -> trimesh.Trimesh:
        """Create a cylinder mesh."""
        return trimesh.creation.cylinder(
            radius=self.radius,
            height=self.height,
            sections=32  # Number of segments for the circular cross-section
        ) 