"""
Interface module for communication between frontend and shape classes.
"""

from typing import Dict, List, Optional, Union, Any
import numpy as np
from .base import Shape, Transform
from .primitives import Cube, Sphere, Cylinder
from .extrusion import ExtrudedShape

class ShapeFactory:
    """Factory class for creating and managing shapes based on UI input."""
    
    @staticmethod
    def create_shape(
        shape_type: str,
        parameters: Dict[str, Any],
        transform: Optional[Dict[str, List[float]]] = None
    ) -> Shape:
        """
        Create a shape based on UI input.
        
        Args:
            shape_type: Type of shape to create ('cube', 'sphere', 'cylinder', 'extrusion')
            parameters: Shape-specific parameters (e.g., size, radius, profile points)
            transform: Optional initial transform as dictionary with 'position',
                     'rotation', and 'scale' keys
        
        Returns:
            Created shape instance
        """
        # Convert transform dict to Transform object if provided
        transform_obj = None
        if transform:
            transform_obj = Transform(
                position=np.array(transform.get('position', [0.0, 0.0, 0.0])),
                rotation=np.array(transform.get('rotation', [0.0, 0.0, 0.0])),
                scale=np.array(transform.get('scale', [1.0, 1.0, 1.0]))
            )
        
        # Create shape based on type
        if shape_type == 'cube':
            return Cube(
                size=parameters.get('size', 1.0),
                transform=transform_obj
            )
        elif shape_type == 'sphere':
            return Sphere(
                radius=parameters.get('radius', 1.0),
                transform=transform_obj
            )
        elif shape_type == 'cylinder':
            return Cylinder(
                radius=parameters.get('radius', 1.0),
                height=parameters.get('height', 2.0),
                transform=transform_obj
            )
        elif shape_type == 'extrusion':
            # Handle different types of extrusions
            extrusion_type = parameters.get('extrusion_type', 'custom')
            if extrusion_type == 'rectangle':
                return ExtrudedShape.create_rectangle(
                    width=parameters.get('width', 1.0),
                    length=parameters.get('length', 1.0),
                    height=parameters.get('height', 1.0),
                    transform=transform_obj
                )
            elif extrusion_type == 'polygon':
                return ExtrudedShape.create_polygon(
                    num_sides=parameters.get('num_sides', 6),
                    radius=parameters.get('radius', 1.0),
                    height=parameters.get('height', 1.0),
                    transform=transform_obj
                )
            else:  # custom profile
                return ExtrudedShape(
                    profile_points=parameters['profile_points'],
                    height=parameters.get('height', 1.0),
                    transform=transform_obj
                )
        else:
            raise ValueError(f"Unknown shape type: {shape_type}")
    
    @staticmethod
    def apply_transform(
        shape: Shape,
        transform_type: str,
        parameters: Dict[str, float]
    ) -> None:
        """
        Apply a transformation to a shape based on UI input.
        
        Args:
            shape: Shape to transform
            transform_type: Type of transformation ('translate', 'rotate', 'scale')
            parameters: Transform parameters (x, y, z values)
        """
        x = parameters.get('x', 0.0)
        y = parameters.get('y', 0.0)
        z = parameters.get('z', 0.0)
        
        if transform_type == 'translate':
            shape.translate(x, y, z)
        elif transform_type == 'rotate':
            shape.rotate(x, y, z)
        elif transform_type == 'scale':
            shape.scale(x, y, z)
        else:
            raise ValueError(f"Unknown transform type: {transform_type}")

# Example usage from frontend:
"""
# Creating a shape
shape_params = {
    'size': 2.0,
    'transform': {
        'position': [1.0, 0.0, 0.0],
        'rotation': [0.0, np.pi/4, 0.0],
        'scale': [1.0, 1.0, 1.0]
    }
}
cube = ShapeFactory.create_shape('cube', shape_params)

# Creating an extrusion
extrusion_params = {
    'extrusion_type': 'custom',
    'profile_points': [[0,0], [1,0], [1,1], [0,1]],
    'height': 2.0
}
extrusion = ShapeFactory.create_shape('extrusion', extrusion_params)

# Applying a transformation
transform_params = {'x': 1.0, 'y': 2.0, 'z': 3.0}
ShapeFactory.apply_transform(cube, 'translate', transform_params)
""" 