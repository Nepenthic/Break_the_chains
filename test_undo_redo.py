import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
import numpy as np
from transform_commands import TransformCommand, UndoRedoManager
from shapes_3d import Cube

def test_transform_command():
    """Test TransformCommand functionality."""
    # Create test shape
    cube = Cube(size=1.0)
    
    # Create test states
    before_state = {
        'position': np.array([0.0, 0.0, 0.0]),
        'rotation': np.array([0.0, 0.0, 0.0]),
        'scale': np.array([1.0, 1.0, 1.0])
    }
    
    after_state = {
        'position': np.array([1.0, 0.0, 0.0]),
        'rotation': np.array([0.0, 45.0, 0.0]),
        'scale': np.array([2.0, 2.0, 2.0])
    }
    
    transform_params = {
        'mode': 'translate',
        'axis': 'x',
        'value': 1.0
    }
    
    # Create command
    command = TransformCommand([cube], [before_state], [after_state], transform_params)
    
    # Test undo
    command.undo()
    assert np.allclose(cube.transform.position, before_state['position'])
    assert np.allclose(cube.transform.rotation, before_state['rotation'])
    assert np.allclose(cube.transform.scale, before_state['scale'])
    
    # Test redo
    command.redo()
    assert np.allclose(cube.transform.position, after_state['position'])
    assert np.allclose(cube.transform.rotation, after_state['rotation'])
    assert np.allclose(cube.transform.scale, after_state['scale'])

def test_undo_redo_manager():
    """Test UndoRedoManager functionality."""
    manager = UndoRedoManager()
    
    # Create test shape and states
    cube = Cube(size=1.0)
    states = [
        {
            'position': np.array([0.0, 0.0, 0.0]),
            'rotation': np.array([0.0, 0.0, 0.0]),
            'scale': np.array([1.0, 1.0, 1.0])
        },
        {
            'position': np.array([1.0, 0.0, 0.0]),
            'rotation': np.array([0.0, 0.0, 0.0]),
            'scale': np.array([1.0, 1.0, 1.0])
        },
        {
            'position': np.array([1.0, 1.0, 0.0]),
            'rotation': np.array([0.0, 0.0, 0.0]),
            'scale': np.array([1.0, 1.0, 1.0])
        }
    ]
    
    # Create and add commands
    for i in range(2):
        command = TransformCommand(
            [cube],
            [states[i]],
            [states[i+1]],
            {'mode': 'translate', 'axis': 'x' if i == 0 else 'y', 'value': 1.0}
        )
        manager.add_command(command)
    
    # Test initial state
    assert manager.can_undo()
    assert not manager.can_redo()
    assert len(manager.undo_stack) == 2
    assert len(manager.redo_stack) == 0
    
    # Test undo
    assert manager.undo()
    assert np.allclose(cube.transform.position, states[1]['position'])
    assert len(manager.undo_stack) == 1
    assert len(manager.redo_stack) == 1
    
    # Test redo
    assert manager.redo()
    assert np.allclose(cube.transform.position, states[2]['position'])
    assert len(manager.undo_stack) == 2
    assert len(manager.redo_stack) == 0
    
    # Test clear
    manager.clear()
    assert not manager.can_undo()
    assert not manager.can_redo()
    assert len(manager.undo_stack) == 0
    assert len(manager.redo_stack) == 0

def test_max_history_limit():
    """Test that undo stack respects max history limit."""
    manager = UndoRedoManager()
    manager.max_history = 3
    
    # Create test shape and commands
    cube = Cube(size=1.0)
    base_state = {
        'position': np.array([0.0, 0.0, 0.0]),
        'rotation': np.array([0.0, 0.0, 0.0]),
        'scale': np.array([1.0, 1.0, 1.0])
    }
    
    # Add more commands than max_history
    for i in range(5):
        next_state = base_state.copy()
        next_state['position'] = np.array([float(i+1), 0.0, 0.0])
        command = TransformCommand(
            [cube],
            [base_state],
            [next_state],
            {'mode': 'translate', 'axis': 'x', 'value': 1.0}
        )
        manager.add_command(command)
        base_state = next_state
    
    # Verify only max_history commands are kept
    assert len(manager.undo_stack) == manager.max_history
    assert manager.undo_stack[0].after_states[0]['position'][0] == 3.0  # First command should be third transform

def test_undo_redo_integration(qtbot, main_window):
    """Test integration of undo/redo system with main window."""
    # Create and select a shape
    cube = Cube(size=1.0)
    shape_id = main_window.viewport.addShape(cube)
    main_window.viewport.selectShape(shape_id)
    
    # Apply a transform
    transform_params = {
        'mode': 'translate',
        'axis': 'x',
        'value': 1.0,
        'snap': {'enabled': False}
    }
    main_window.transform_tab.transformApplied.emit('translate', transform_params)
    
    # Verify transform was applied
    shape = main_window.viewport.getSelectedShape()
    assert np.allclose(shape.transform.position, [1.0, 0.0, 0.0])
    
    # Test undo
    qtbot.mouseClick(main_window.transform_tab.undo_button, Qt.MouseButton.LeftButton)
    shape = main_window.viewport.getSelectedShape()
    assert np.allclose(shape.transform.position, [0.0, 0.0, 0.0])
    
    # Test redo
    qtbot.mouseClick(main_window.transform_tab.redo_button, Qt.MouseButton.LeftButton)
    shape = main_window.viewport.getSelectedShape()
    assert np.allclose(shape.transform.position, [1.0, 0.0, 0.0])
    
    # Test keyboard shortcuts
    qtbot.keyClick(main_window, 'Z', Qt.KeyboardModifier.ControlModifier)  # Ctrl+Z
    shape = main_window.viewport.getSelectedShape()
    assert np.allclose(shape.transform.position, [0.0, 0.0, 0.0])
    
    qtbot.keyClick(main_window, 'Y', Qt.KeyboardModifier.ControlModifier)  # Ctrl+Y
    shape = main_window.viewport.getSelectedShape()
    assert np.allclose(shape.transform.position, [1.0, 0.0, 0.0]) 