"""
Module for creating 3D shapes by extruding 2D profiles.
"""

from typing import List, Optional, Union
import numpy as np
import trimesh
from .base import Shape, Transform

class ExtrudedShape(Shape):
    """A 3D shape created by extruding a 2D profile along a path."""
    
    def __init__(
        self,
        profile_points: List[List[float]],
        height: float = 1.0,
        transform: Optional[Transform] = None,
        center: bool = True
    ):
        """
        Initialize an extruded shape.
        
        Args:
            profile_points: List of [x, y] coordinates defining the 2D profile
            height: Height of the extrusion
            transform: Optional initial transformation
            center: If True, center the shape at origin
        """
        super().__init__(transform)
        # Convert profile points to numpy array
        self.profile = np.array(profile_points)
        if self.profile.shape[1] != 2:
            raise ValueError("Profile points must be 2D coordinates [x, y]")
        
        self.height = height
        self.center = center
    
    def _create_mesh(self) -> trimesh.Trimesh:
        """Create a mesh by extruding the 2D profile."""
        # Ensure the profile is closed (first and last points match)
        if not np.allclose(self.profile[0], self.profile[-1]):
            self.profile = np.vstack([self.profile, self.profile[0]])
        
        # Create vertices for the top and bottom faces
        bottom_vertices = np.column_stack([self.profile, np.zeros(len(self.profile))])
        top_vertices = np.column_stack([self.profile, np.full(len(self.profile), self.height)])
        
        # Combine vertices
        vertices = np.vstack([bottom_vertices, top_vertices])
        
        # Create faces
        num_points = len(self.profile)
        
        # Bottom face triangulation
        bottom_faces = []
        for i in range(1, num_points - 1):
            bottom_faces.append([0, i, i + 1])
        bottom_faces = np.array(bottom_faces)
        
        # Top face triangulation (reversed winding)
        top_offset = num_points  # Index offset for top vertices
        top_faces = []
        for i in range(1, num_points - 1):
            top_faces.append([
                top_offset + 0,
                top_offset + i + 1,
                top_offset + i
            ])
        top_faces = np.array(top_faces)
        
        # Side faces (quads split into triangles)
        side_faces = []
        for i in range(num_points - 1):
            # First triangle of quad
            side_faces.append([
                i,
                i + 1,
                i + top_offset
            ])
            # Second triangle of quad
            side_faces.append([
                i + 1,
                i + 1 + top_offset,
                i + top_offset
            ])
        side_faces = np.array(side_faces)
        
        # Combine all faces
        faces = np.vstack([bottom_faces, top_faces, side_faces])
        
        # Create the mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # Center the mesh if requested
        if self.center:
            mesh.vertices -= mesh.centroid
        
        return mesh
    
    @classmethod
    def create_rectangle(
        cls,
        width: float = 1.0,
        length: float = 1.0,
        height: float = 1.0,
        transform: Optional[Transform] = None,
        center: bool = True
    ) -> 'ExtrudedShape':
        """
        Create a rectangular extrusion.
        
        Args:
            width: Width of the rectangle (X dimension)
            length: Length of the rectangle (Y dimension)
            height: Height of the extrusion (Z dimension)
            transform: Optional initial transformation
            center: If True, center the shape at origin
        
        Returns:
            An ExtrudedShape instance with a rectangular profile
        """
        profile_points = [
            [-width/2, -length/2],
            [width/2, -length/2],
            [width/2, length/2],
            [-width/2, length/2]
        ]
        return cls(profile_points, height, transform, center)
    
    @classmethod
    def create_polygon(
        cls,
        num_sides: int,
        radius: float = 1.0,
        height: float = 1.0,
        transform: Optional[Transform] = None,
        center: bool = True
    ) -> 'ExtrudedShape':
        """
        Create a regular polygon extrusion.
        
        Args:
            num_sides: Number of sides in the polygon
            radius: Radius of the circumscribed circle
            height: Height of the extrusion
            transform: Optional initial transformation
            center: If True, center the shape at origin
        
        Returns:
            An ExtrudedShape instance with a regular polygon profile
        """
        if num_sides < 3:
            raise ValueError("Number of sides must be at least 3")
        
        # Generate points around a circle
        angles = np.linspace(0, 2*np.pi, num_sides, endpoint=False)
        x = radius * np.cos(angles)
        y = radius * np.sin(angles)
        profile_points = np.column_stack([x, y]).tolist()
        
        return cls(profile_points, height, transform, center) 