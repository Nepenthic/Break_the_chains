from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal

class TestViewport(QWidget):
    """Minimal viewport implementation for testing."""
    
    # Signals
    shapeSelected = pyqtSignal(str)  # shape_id
    selectionCleared = pyqtSignal()
    viewportUpdated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.shapes = {}
        self.selected_shapes = set()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def addShape(self, shape):
        """Add a shape to the viewport."""
        shape_id = str(len(self.shapes))
        self.shapes[shape_id] = shape
        self.update()
        return shape_id
    
    def selectShape(self, shape_id):
        """Select a shape by ID."""
        if shape_id in self.shapes:
            self.selected_shapes.add(shape_id)
            self.shapeSelected.emit(shape_id)
            self.update()
    
    def clearSelection(self):
        """Clear all shape selections."""
        self.selected_shapes.clear()
        self.selectionCleared.emit()
        self.update()
    
    def getSelectedShape(self):
        """Get the currently selected shape."""
        if self.selected_shapes:
            shape_id = next(iter(self.selected_shapes))
            return self.shapes[shape_id]
        return None
    
    def getShape(self, shape_id):
        """Get a shape by ID."""
        return self.shapes.get(shape_id)
    
    def clear(self):
        """Clear all shapes from the viewport."""
        self.shapes.clear()
        self.selected_shapes.clear()
        self.update()
    
    def update(self):
        """Update the viewport display."""
        super().update()
        self.viewportUpdated.emit() 