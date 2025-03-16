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
        self._hovered_shape_id: Optional[str] = None
        self._transform_mode: Optional[str] = None
        self._active_axis: Optional[str] = None
        
        # Default snapping settings
        self._snap_enabled: bool = True
        self._snap_translate: float = 0.25
        self._snap_rotate: float = 15.0
        self._snap_scale: float = 0.25
    
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
        parameters: Dict[str, Any]
    ) -> None:
        """
        Apply a transformation to a shape in the scene.
        
        Args:
            shape_id: ID of the shape to transform
            transform_type: Type of transformation
            parameters: Transform parameters including snapping settings
        
        Raises:
            KeyError: If shape_id is not found
        """
        shape = self._shapes.get(shape_id)
        if shape is None:
            raise KeyError(f"Shape with ID {shape_id} not found")
        
        # Update snapping settings if provided
        if 'snap' in parameters:
            snap_settings = parameters['snap']
            shape.snap_enabled = snap_settings.get('enabled', True)
            shape.set_snap_values(
                translate=snap_settings.get('translate', 0.25),
                rotate=snap_settings.get('rotate', 15.0),
                scale=snap_settings.get('scale', 0.25)
            )
        
        # Apply the transformation
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
    
    def set_transform_mode(self, mode: Optional[str]) -> None:
        """
        Set the current transform mode.
        
        Args:
            mode: Transform mode ('translate', 'rotate', 'scale') or None
        """
        self._transform_mode = mode
        if self._selected_shape_id:
            shape = self._shapes[self._selected_shape_id]
            shape.transform_mode = mode
    
    def get_transform_mode(self) -> Optional[str]:
        """Get the current transform mode."""
        return self._transform_mode
    
    def set_active_axis(self, axis: Optional[str]) -> None:
        """
        Set the currently active transform axis.
        
        Args:
            axis: Active axis ('x', 'y', 'z') or None
        """
        self._active_axis = axis
        if self._selected_shape_id:
            shape = self._shapes[self._selected_shape_id]
            shape.active_axis = axis
    
    def get_active_axis(self) -> Optional[str]:
        """Get the currently active transform axis."""
        return self._active_axis
    
    def select_shape(self, shape_id: Optional[str]) -> bool:
        """
        Set the currently selected shape.
        
        Args:
            shape_id: ID of shape to select, or None to clear selection
        
        Returns:
            bool: True if selection changed, False otherwise
        """
        # Clear transform mode and axis when selection changes
        if shape_id != self._selected_shape_id:
            self._transform_mode = None
            self._active_axis = None
        
        if shape_id is None:
            if self._selected_shape_id is not None:
                # Clear transform mode on previous selection
                if self._selected_shape_id in self._shapes:
                    self._shapes[self._selected_shape_id].transform_mode = None
                self._selected_shape_id = None
                return True
            return False
        
        if shape_id not in self._shapes:
            return False
        
        if shape_id != self._selected_shape_id:
            # Clear transform mode on previous selection
            if self._selected_shape_id in self._shapes:
                self._shapes[self._selected_shape_id].transform_mode = None
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
    
    def find_shape_under_ray(self, ray_origin: np.ndarray, ray_direction: np.ndarray) -> Optional[str]:
        """
        Find the shape intersected by a ray and return its ID.
        
        Args:
            ray_origin: Origin point of the ray in world space (3D vector)
            ray_direction: Direction vector of the ray in world space (3D vector)
            
        Returns:
            Optional[str]: ID of the intersected shape, or None if no intersection
        """
        closest_shape_id = None
        closest_distance = float('inf')
        
        for shape_id, shape in self._shapes.items():
            hit, distance = shape.intersect_ray(ray_origin, ray_direction)
            if hit and distance < closest_distance:
                closest_shape_id = shape_id
                closest_distance = distance
        
        return closest_shape_id
    
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
    
    def set_hovered_shape(self, shape_id: Optional[str]) -> bool:
        """
        Set the currently hovered shape.
        
        Args:
            shape_id: ID of shape being hovered, or None to clear hover state
            
        Returns:
            bool: True if hover state changed, False otherwise
        """
        if shape_id == self._hovered_shape_id:
            return False
            
        self._hovered_shape_id = shape_id
        return True
    
    def get_hovered_shape(self) -> Optional[tuple[str, Shape]]:
        """Get the currently hovered shape and its ID."""
        if self._hovered_shape_id is None:
            return None
        shape = self._shapes.get(self._hovered_shape_id)
        if shape is None:
            self._hovered_shape_id = None
            return None
        return (self._hovered_shape_id, shape)
    
    def set_snap_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update snapping settings.
        
        Args:
            settings: Dictionary containing snapping settings
                     {'enabled': bool, 'translate': float, 'rotate': float, 'scale': float}
        """
        self._snap_enabled = settings.get('enabled', True)
        self._snap_translate = settings.get('translate', 0.25)
        self._snap_rotate = settings.get('rotate', 15.0)
        self._snap_scale = settings.get('scale', 0.25)
        
        # Update selected shape's snapping settings
        if self._selected_shape_id:
            shape = self._shapes[self._selected_shape_id]
            shape.snap_enabled = self._snap_enabled
            shape.set_snap_values(
                translate=self._snap_translate,
                rotate=self._snap_rotate,
                scale=self._snap_scale
            )

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