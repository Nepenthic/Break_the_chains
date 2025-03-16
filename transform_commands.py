from PyQt6.QtCore import pyqtSignal, QObject
import numpy as np

class TransformCommand:
    """Command class for transform operations."""
    
    def __init__(self, shapes, before_states, after_states, transform_params):
        """Initialize with shapes and their states before/after the transform."""
        self.shapes = shapes
        self.before_states = before_states
        self.after_states = after_states
        self.transform_params = transform_params
    
    def undo(self):
        """Revert shapes to their pre-transform states."""
        for shape, state in zip(self.shapes, self.before_states):
            shape.transform.position = np.array(state['position'])
            shape.transform.rotation = np.array(state['rotation'])
            shape.transform.scale = np.array(state['scale'])
            shape.update()
    
    def redo(self):
        """Reapply the transform by restoring post-transform states."""
        for shape, state in zip(self.shapes, self.after_states):
            shape.transform.position = np.array(state['position'])
            shape.transform.rotation = np.array(state['rotation'])
            shape.transform.scale = np.array(state['scale'])
            shape.update()

class UndoRedoManager(QObject):
    """Manages undo/redo operations for transforms."""
    
    undo_stack_changed = pyqtSignal()
    redo_stack_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 100  # Limit stack size to manage memory
        self.logger = None  # Will be set by MainWindow
    
    def add_command(self, command):
        """Add a new transform command to the undo stack."""
        self.undo_stack.append(command)
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)  # Remove oldest command
        self.redo_stack.clear()  # New action invalidates redo stack
        self.undo_stack_changed.emit()
        self.redo_stack_changed.emit()
        
        if self.logger:
            self.log_command_added(command)
    
    def undo(self):
        """Undo the last transform operation."""
        if self.undo_stack:
            command = self.undo_stack.pop()
            command.undo()
            self.redo_stack.append(command)
            self.undo_stack_changed.emit()
            self.redo_stack_changed.emit()
            
            if self.logger:
                self.log_undo(command)
            
            return True
        return False
    
    def redo(self):
        """Redo the last undone transform operation."""
        if self.redo_stack:
            command = self.redo_stack.pop()
            command.redo()
            self.undo_stack.append(command)
            self.undo_stack_changed.emit()
            self.redo_stack_changed.emit()
            
            if self.logger:
                self.log_redo(command)
            
            return True
        return False
    
    def clear(self):
        """Clear both undo and redo stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.undo_stack_changed.emit()
        self.redo_stack_changed.emit()
    
    def can_undo(self):
        """Check if there are operations to undo."""
        return bool(self.undo_stack)
    
    def can_redo(self):
        """Check if there are operations to redo."""
        return bool(self.redo_stack)
    
    def log_command_added(self, command):
        """Log when a new command is added."""
        self.logger.log_ui_change(
            component="UndoRedoManager",
            change_type="command_added",
            details={
                'transform_type': command.transform_params['mode'],
                'shapes_affected': len(command.shapes)
            }
        )
    
    def log_undo(self, command):
        """Log when an undo operation is performed."""
        self.logger.log_ui_change(
            component="UndoRedoManager",
            change_type="undo",
            details={
                'transform_type': command.transform_params['mode'],
                'shapes_affected': len(command.shapes)
            }
        )
    
    def log_redo(self, command):
        """Log when a redo operation is performed."""
        self.logger.log_ui_change(
            component="UndoRedoManager",
            change_type="redo",
            details={
                'transform_type': command.transform_params['mode'],
                'shapes_affected': len(command.shapes)
            }
        ) 