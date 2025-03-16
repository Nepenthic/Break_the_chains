import numpy as np
from PyQt6.QtGui import QVector3D

class Transform:
    def __init__(self):
        self.position = np.array([0.0, 0.0, 0.0])
        self.rotation = np.array([0.0, 0.0, 0.0])
        self.scale = np.array([1.0, 1.0, 1.0])

class Shape:
    def __init__(self):
        self.id = str(id(self))
        self.transform = Transform()
        self.vertices = np.array([])
        self.indices = np.array([])
        
    def update(self):
        """Update shape state."""
        pass

class Cube(Shape):
    def __init__(self, size=1.0):
        super().__init__()
        self.size = size
        self._create_geometry()
        
    def _create_geometry(self):
        """Create cube geometry."""
        s = self.size / 2
        self.vertices = np.array([
            # Front face
            [-s, -s,  s],
            [ s, -s,  s],
            [ s,  s,  s],
            [-s,  s,  s],
            # Back face
            [-s, -s, -s],
            [ s, -s, -s],
            [ s,  s, -s],
            [-s,  s, -s],
        ])
        
        self.indices = np.array([
            # Front
            0, 1, 2,
            2, 3, 0,
            # Right
            1, 5, 6,
            6, 2, 1,
            # Back
            7, 6, 5,
            5, 4, 7,
            # Left
            4, 0, 3,
            3, 7, 4,
            # Bottom
            4, 5, 1,
            1, 0, 4,
            # Top
            3, 2, 6,
            6, 7, 3,
        ])

class SceneManager:
    def __init__(self):
        self.shapes = {}
        self.selected_shapes = set()
        
    def addShape(self, shape):
        """Add a shape to the scene."""
        self.shapes[shape.id] = shape
        return shape.id
        
    def removeShape(self, shape_id):
        """Remove a shape from the scene."""
        if shape_id in self.shapes:
            del self.shapes[shape_id]
            self.selected_shapes.discard(shape_id)
            
    def selectShape(self, shape_id):
        """Select a shape."""
        if shape_id in self.shapes:
            self.selected_shapes.add(shape_id)
            
    def clearSelection(self):
        """Clear shape selection."""
        self.selected_shapes.clear()
        
    def getShape(self, shape_id):
        """Get a shape by ID."""
        return self.shapes.get(shape_id)
        
    def get_selected_shapes(self):
        """Get list of selected shapes."""
        return [self.shapes[shape_id] for shape_id in self.selected_shapes] 