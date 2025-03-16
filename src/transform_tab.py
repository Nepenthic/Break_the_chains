from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from typing import Dict

class TransformTab(QWidget):
    """Minimal transform tab implementation for testing."""
    
    # Signals
    transformApplied = pyqtSignal(str, dict)  # mode, values
    transformPreviewRequested = pyqtSignal(str, dict)  # mode, values
    transformPreviewCanceled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_transform_mode = None
        self.transform_values = {}
    
    def apply_transform(self, mode: str, values: Dict):
        """Apply a transform with the given mode and values."""
        self.current_transform_mode = mode
        self.transform_values = values.copy()
        self.transformApplied.emit(mode, values)
    
    def preview_transform(self, mode: str, values: Dict):
        """Preview a transform with the given mode and values."""
        self.transformPreviewRequested.emit(mode, values)
    
    def cancel_preview(self):
        """Cancel the current transform preview."""
        self.transformPreviewCanceled.emit() 