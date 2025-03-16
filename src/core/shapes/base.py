from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
import trimesh

@dataclass
class Transform:
    """Represents a 3D transformation with position, rotation, and scale."""
    position: np.ndarray = np.array([0.0, 0.0, 0.0])
    rotation: np.ndarray = np.array([0.0, 0.0, 0.0])  # Euler angles in radians
    scale: np.ndarray = np.array([1.0, 1.0, 1.0])

class Shape:
    """Base class for all 3D shapes in the CAD/CAM program."""
    
    def __init__(self, transform: Optional[Transform] = None):
        """Initialize a shape with an optional transform."""
        self.transform = transform or Transform()
        self._mesh: Optional[trimesh.Trimesh] = None
    
    def get_mesh(self) -> trimesh.Trimesh:
        """Get the trimesh representation of the shape."""
        if self._mesh is None:
            self._mesh = self._create_mesh()
        return self._apply_transform(self._mesh)
    
    def _create_mesh(self) -> trimesh.Trimesh:
        """Create the base mesh for the shape. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _create_mesh()")
    
    def _apply_transform(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Apply the current transformation to the mesh."""
        # Create a copy to avoid modifying the original
        transformed = mesh.copy()
        
        # Apply scale
        transformed.apply_scale(self.transform.scale)
        
        # Apply rotation (Euler angles)
        rotation_matrix = trimesh.transformations.euler_matrix(
            *self.transform.rotation, axes='rxyz'
        )
        transformed.apply_transform(rotation_matrix)
        
        # Apply translation
        transformed.apply_translation(self.transform.position)
        
        return transformed
    
    def translate(self, x: float, y: float, z: float) -> None:
        """Translate the shape by the given amounts."""
        self.transform.position += np.array([x, y, z])
    
    def rotate(self, x: float, y: float, z: float) -> None:
        """Rotate the shape by the given angles (in radians)."""
        self.transform.rotation += np.array([x, y, z])
    
    def scale(self, x: float, y: float, z: float) -> None:
        """Scale the shape by the given factors."""
        self.transform.scale *= np.array([x, y, z])
    
    def export_stl(self, filepath: str) -> None:
        """Export the shape to an STL file."""
        mesh = self.get_mesh()
        mesh.export(filepath) 