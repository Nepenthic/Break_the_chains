"""
Scene management and UI integration module.
"""

from typing import Dict, List, Optional, Any
import uuid
import numpy as np
from .shapes import Shape, ShapeFactory

class SceneManager:
    """Manages the scene graph and handles UI interactions."""
    
    def __init__(self):
        """Initialize an empty scene."""
        self._shapes: Dict[str, Shape] = {}  # Map of shape_id to Shape
        self._selected_shape_id: Optional[str] = None
    
    def create_shape(
        self,
        shape_type: str,
        parameters: Dict[str, Any],
        transform: Optional[Dict[str, List[float]]] = None
    ) -> str:
        """
        Create a new shape and add it to the scene.
        
        Args:
            shape_type: Type of shape to create
            parameters: Shape-specific parameters
            transform: Optional initial transform
        
        Returns:
            shape_id: Unique identifier for the created shape
        """
        # Create shape using factory
        shape = ShapeFactory.create_shape(shape_type, parameters, transform)
        
        # Generate unique ID and store shape
        shape_id = str(uuid.uuid4())
        self._shapes[shape_id] = shape
        
        return shape_id
    
    def apply_transform(
        self,
        shape_id: str,
        transform_type: str,
        parameters: Dict[str, float]
    ) -> None:
        """
        Apply a transformation to a shape in the scene.
        
        Args:
            shape_id: ID of the shape to transform
            transform_type: Type of transformation
            parameters: Transform parameters
        
        Raises:
            KeyError: If shape_id is not found
        """
        shape = self._shapes.get(shape_id)
        if shape is None:
            raise KeyError(f"Shape with ID {shape_id} not found")
        
        ShapeFactory.apply_transform(shape, transform_type, parameters)
    
    def get_shape(self, shape_id: str) -> Optional[Shape]:
        """Get a shape by its ID."""
        return self._shapes.get(shape_id)
    
    def get_all_shapes(self) -> List[tuple[str, Shape]]:
        """Get all shapes in the scene with their IDs."""
        return list(self._shapes.items())
    
    def remove_shape(self, shape_id: str) -> bool:
        """
        Remove a shape from the scene.
        
        Returns:
            bool: True if shape was removed, False if not found
        """
        if shape_id in self._shapes:
            del self._shapes[shape_id]
            if self._selected_shape_id == shape_id:
                self._selected_shape_id = None
            return True
        return False
    
    def select_shape(self, shape_id: Optional[str]) -> bool:
        """
        Set the currently selected shape.
        
        Args:
            shape_id: ID of shape to select, or None to clear selection
        
        Returns:
            bool: True if selection changed, False otherwise
        """
        if shape_id is None:
            if self._selected_shape_id is not None:
                self._selected_shape_id = None
                return True
            return False
        
        if shape_id not in self._shapes:
            return False
        
        if shape_id != self._selected_shape_id:
            self._selected_shape_id = shape_id
            return True
        return False
    
    def get_selected_shape(self) -> Optional[tuple[str, Shape]]:
        """Get the currently selected shape and its ID."""
        if self._selected_shape_id is None:
            return None
        shape = self._shapes.get(self._selected_shape_id)
        if shape is None:
            self._selected_shape_id = None
            return None
        return (self._selected_shape_id, shape)
    
    def export_shape_stl(self, shape_id: str, filepath: str) -> bool:
        """
        Export a shape to STL file.
        
        Args:
            shape_id: ID of the shape to export
            filepath: Path to save the STL file
        
        Returns:
            bool: True if export successful, False otherwise
        """
        shape = self._shapes.get(shape_id)
        if shape is None:
            return False
        
        try:
            shape.export_stl(filepath)
            return True
        except Exception:
            return False

# Example usage from frontend:
"""
# Initialize scene
scene = SceneManager()

# Create shapes
cube_id = scene.create_shape('cube', {'size': 2.0})
sphere_id = scene.create_shape('sphere', {'radius': 1.0})

# Handle UI shape selection
def on_shape_selected(shape_id: str):
    scene.select_shape(shape_id)
    selected = scene.get_selected_shape()
    if selected:
        # Update UI to show shape properties
        shape_id, shape = selected
        # ...

# Handle transform from UI
def on_transform_applied(transform_type: str, x: float, y: float, z: float):
    selected = scene.get_selected_shape()
    if selected:
        shape_id, _ = selected
        scene.apply_transform(
            shape_id,
            transform_type,
            {'x': x, 'y': y, 'z': z}
        )

# Handle shape creation from UI
def on_shape_created(shape_type: str, parameters: dict):
    shape_id = scene.create_shape(shape_type, parameters)
    # Update UI with new shape
    # ...

# Handle shape export
def on_export_requested(shape_id: str, filepath: str):
    success = scene.export_shape_stl(shape_id, filepath)
    if success:
        print(f"Shape exported to {filepath}")
    else:
        print("Export failed")
""" 