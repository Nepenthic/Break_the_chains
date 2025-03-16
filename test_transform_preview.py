"""
Unit tests for transform preview functionality in the TransformTab class.

This module contains comprehensive tests for the transform preview system, including:
- Mode switching behavior (absolute/relative)
- Compound transforms across multiple axes
- Transform application and cancellation
- Visual feedback and performance monitoring
- Edge cases and error handling
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
import numpy as np
from transform_tab import TransformTab
from viewport import Viewport, TransformPreviewOverlay
from shapes_3d import Cube, Sphere, Cylinder

@pytest.fixture
def transform_tab(qtbot):
    """Create TransformTab instance for tests."""
    tab = TransformTab()
    qtbot.addWidget(tab)
    return tab

@pytest.fixture
def viewport(qtbot):
    """Create Viewport instance for tests."""
    view = Viewport()
    qtbot.addWidget(view)
    return view

def test_preview_initialization(transform_tab, viewport):
    """Test transform preview initialization."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Verify initial state
    assert not transform_tab.preview_active
    assert not viewport.preview_overlay.active
    
    # Start preview by changing transform value
    transform_tab.translate_x.setValue(1.0)
    
    # Verify preview started
    assert transform_tab.preview_active
    assert viewport.preview_overlay.active
    assert viewport.preview_overlay.transform_type == 'translate'
    assert viewport.preview_overlay.axis == 'x'
    assert viewport.preview_overlay.value == 1.0

def test_preview_update(transform_tab, viewport):
    """Test transform preview updates."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Start preview
    transform_tab.translate_x.setValue(1.0)
    original_position = cube.transform.position.copy()
    
    # Update preview
    transform_tab.translate_x.setValue(2.0)
    
    # Verify preview updated without affecting shape
    assert viewport.preview_overlay.value == 2.0
    assert np.allclose(cube.transform.position, original_position)

def test_preview_cancel(transform_tab, viewport):
    """Test transform preview cancellation."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Start preview
    transform_tab.translate_x.setValue(1.0)
    original_position = cube.transform.position.copy()
    
    # Cancel preview
    transform_tab.cancel_preview()
    
    # Verify preview stopped and shape unchanged
    assert not transform_tab.preview_active
    assert not viewport.preview_overlay.active
    assert np.allclose(cube.transform.position, original_position)

def test_preview_apply(transform_tab, viewport):
    """Test applying previewed transform."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Start preview
    transform_tab.translate_x.setValue(1.0)
    original_position = cube.transform.position.copy()
    
    # Apply transform
    transform_tab.apply_transform()
    
    # Verify preview stopped and transform applied
    assert not transform_tab.preview_active
    assert not viewport.preview_overlay.active
    assert cube.transform.position[0] == original_position[0] + 1.0

def test_preview_with_undo_redo(transform_tab, viewport, main_window):
    """Test transform preview interaction with undo/redo."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Apply first transform
    transform_tab.translate_x.setValue(1.0)
    transform_tab.apply_transform()
    position_1 = cube.transform.position.copy()
    
    # Apply second transform
    transform_tab.translate_y.setValue(2.0)
    transform_tab.apply_transform()
    position_2 = cube.transform.position.copy()
    
    # Undo last transform
    main_window.undoTransform()
    assert np.allclose(cube.transform.position, position_1)
    
    # Start new preview
    transform_tab.translate_z.setValue(3.0)
    
    # Verify preview active but not affecting undo stack
    assert transform_tab.preview_active
    assert np.allclose(cube.transform.position, position_1)
    
    # Redo while preview active
    main_window.redoTransform()
    
    # Verify preview still active and redo applied
    assert transform_tab.preview_active
    assert np.allclose(cube.transform.position, position_2)

def test_preview_multiple_shapes(transform_tab, viewport):
    """Test transform preview with multiple selected shapes."""
    # Create shapes
    cube = Cube(size=1.0)
    sphere = Sphere(radius=0.5)
    sphere.transform.position[0] = 2.0
    
    # Add and select both shapes
    cube_id = viewport.addShape(cube)
    sphere_id = viewport.addShape(sphere)
    viewport.selectShape(cube_id)
    viewport.selectShape(sphere_id, add_to_selection=True)
    
    # Start preview
    transform_tab.scale_x.setValue(2.0)
    
    # Verify preview affects both shapes
    assert viewport.preview_overlay.active
    original_states = viewport.preview_overlay.original_state
    assert len(original_states) == 2
    assert cube_id in original_states
    assert sphere_id in original_states
    
    # Apply transform
    transform_tab.apply_transform()
    
    # Verify transform applied to both shapes
    assert cube.transform.scale[0] == 2.0
    assert sphere.transform.scale[0] == 2.0

def test_preview_performance(transform_tab, viewport):
    """Test transform preview performance monitoring."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Start preview
    transform_tab.translate_x.setValue(1.0)
    
    # Verify performance metrics
    metrics = transform_tab.feedback.performance_metrics.get_metrics()
    assert 'update_time' in metrics
    assert 'frame_time' in metrics
    
    # Update preview rapidly
    for i in range(10):
        transform_tab.translate_x.setValue(float(i))
    
    # Verify performance monitoring
    metrics = transform_tab.feedback.performance_metrics.get_metrics()
    assert metrics['update_count'] >= 10 

def test_value_text_formatting(transform_tab, viewport):
    """Test value text formatting for different transform types."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Test translation value format
    transform_tab.translate_x.setValue(1.5)
    assert viewport.preview_overlay.get_value_text() == "+1.50"
    
    # Test rotation value format
    transform_tab.setCurrentMode('rotate')
    transform_tab.rotate_x.setValue(45.0)
    assert viewport.preview_overlay.get_value_text() == "+45.0°"
    
    # Test scale value format
    transform_tab.setCurrentMode('scale')
    transform_tab.scale_x.setValue(2.0)
    assert viewport.preview_overlay.get_value_text() == "×2.00"

def test_preview_visual_properties(transform_tab, viewport):
    """Test visual properties of transform preview."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Start preview
    transform_tab.translate_x.setValue(1.0)
    
    # Check color properties
    color = viewport.preview_overlay.get_preview_color()
    assert color[3] == 0.3  # Check alpha value for transparency
    
    # Check line pattern for dashed lines
    assert viewport.preview_overlay.line_pattern == 0x00FF
    
    # Check text offset
    assert viewport.preview_overlay.text_offset > 0

def test_preview_end_position(transform_tab, viewport):
    """Test end position calculation for different transform types."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    center = np.array([0.0, 0.0, 0.0])
    
    # Test translation end position
    transform_tab.translate_x.setValue(2.0)
    end_pos = viewport.preview_overlay.get_preview_end_position(center)
    assert np.allclose(end_pos, [2.0, 0.0, 0.0])
    
    # Test rotation end position
    transform_tab.setCurrentMode('rotate')
    transform_tab.rotate_z.setValue(90.0)
    end_pos = viewport.preview_overlay.get_preview_end_position(center)
    assert np.allclose(end_pos[:2], [0.0, 1.0], atol=1e-5)
    
    # Test scale end position
    transform_tab.setCurrentMode('scale')
    transform_tab.scale_x.setValue(2.0)
    end_pos = viewport.preview_overlay.get_preview_end_position(center)
    assert np.allclose(end_pos, [0.0, 0.0, 0.0])

def test_multiple_shape_preview(transform_tab, viewport):
    """Test preview with multiple selected shapes."""
    # Create shapes at different positions
    cube1 = Cube(size=1.0)
    cube2 = Cube(size=1.0)
    cube2.transform.position = np.array([2.0, 0.0, 0.0])
    
    # Add and select both shapes
    id1 = viewport.addShape(cube1)
    id2 = viewport.addShape(cube2)
    viewport.selectShape(id1)
    viewport.selectShape(id2, add_to_selection=True)
    
    # Start preview
    transform_tab.translate_y.setValue(1.0)
    
    # Check that preview center is between shapes
    center = viewport.preview_overlay.get_preview_center()
    assert np.allclose(center, [1.0, 0.0, 0.0])
    
    # Check that preview affects both shapes
    end_pos = viewport.preview_overlay.get_preview_end_position(center)
    assert np.allclose(end_pos[1], 1.0)

def test_preview_text_position(transform_tab, viewport):
    """Test text position calculation for value indicators."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Test text position for different axes
    center = np.array([0.0, 0.0, 0.0])
    
    # X-axis
    transform_tab.translate_x.setValue(1.0)
    end_pos = viewport.preview_overlay.get_preview_end_position(center)
    text_pos = viewport.preview_overlay.get_text_position(center, end_pos)
    assert text_pos[0] > end_pos[0]  # Text should be offset in x direction
    
    # Y-axis
    transform_tab.translate_y.setValue(1.0)
    end_pos = viewport.preview_overlay.get_preview_end_position(center)
    text_pos = viewport.preview_overlay.get_text_position(center, end_pos)
    assert text_pos[1] > end_pos[1]  # Text should be offset in y direction
    
    # Z-axis
    transform_tab.translate_z.setValue(1.0)
    end_pos = viewport.preview_overlay.get_preview_end_position(center)
    text_pos = viewport.preview_overlay.get_text_position(center, end_pos)
    assert text_pos[2] > end_pos[2]  # Text should be offset in z direction

def test_preview_visibility(transform_tab, viewport):
    """Test preview visibility states."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Check initial state
    assert not viewport.preview_overlay.active
    
    # Start preview
    transform_tab.translate_x.setValue(1.0)
    assert viewport.preview_overlay.active
    
    # Cancel preview
    transform_tab.cancel_preview()
    assert not viewport.preview_overlay.active
    
    # Apply transform and check preview state
    transform_tab.translate_x.setValue(1.0)
    transform_tab.apply_transform()
    assert not viewport.preview_overlay.active 

def test_compound_transform_initialization(transform_tab, qtbot):
    """Test initialization of compound transform preview."""
    # Set multiple transform values
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
    
    # Check that both axes are active
    assert len(transform_tab._active_axes) == 2
    assert 'x' in transform_tab._active_axes
    assert 'y' in transform_tab._active_axes
    
    # Verify preview state
    assert transform_tab._preview_active
    
def test_compound_transform_values(transform_tab, qtbot):
    """Test that compound transform values are correctly tracked."""
    # Set multiple transform values
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 3):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
        transform_tab.translate_z.setValue(3.0)
    
    # Get current transform values
    values = {a: sb.value() for a, sb in transform_tab._active_axes.items()}
    
    # Verify values
    assert values == {'x': 1.0, 'y': 2.0, 'z': 3.0}
    
def test_compound_transform_signals(transform_tab, qtbot):
    """Test that preview signals contain all active axes."""
    def check_signal(transform_type, values):
        assert transform_type == 'translate'
        assert len(values) == 2
        assert values['x'] == 1.0
        assert values['y'] == 2.0
    
    # Connect signal checker
    transform_tab.transformPreviewRequested.connect(check_signal)
    
    # Set multiple transform values
    transform_tab.translate_x.setValue(1.0)
    transform_tab.translate_y.setValue(2.0)
    
def test_compound_transform_mode_switch(transform_tab, qtbot):
    """Test switching transform modes with compound transforms."""
    # Set translation values
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
    
    # Switch to rotation mode
    transform_tab._set_transform_mode('rotate')
    
    # Verify preview state is reset
    assert not transform_tab._preview_active
    assert len(transform_tab._active_axes) == 0
    
def test_compound_transform_apply(transform_tab, qtbot):
    """Test applying compound transforms."""
    # Set multiple transform values
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
    
    # Apply transform
    with qtbot.waitSignal(transform_tab.transformApplied):
        transform_tab.apply_transform()
    
    # Verify history
    assert len(transform_tab._history) == 1
    last_transform = transform_tab._history[-1]
    assert last_transform['mode'] == 'translate'
    assert last_transform['values'] == {'x': 1.0, 'y': 2.0}
    
def test_compound_transform_cancel(transform_tab, qtbot):
    """Test canceling compound transforms."""
    # Set multiple transform values
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
    
    # Cancel preview
    transform_tab.cancel_preview()
    
    # Verify state is reset
    assert not transform_tab._preview_active
    assert len(transform_tab._active_axes) == 0
    assert transform_tab.translate_x.value() == 0.0
    assert transform_tab.translate_y.value() == 0.0
    
def test_compound_transform_history(transform_tab, qtbot):
    """Test history management for compound transforms."""
    # Apply first compound transform
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
    transform_tab.apply_transform()
    
    # Apply second compound transform
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_y.setValue(3.0)
        transform_tab.translate_z.setValue(4.0)
    transform_tab.apply_transform()
    
    # Verify history
    assert len(transform_tab._history) == 2
    assert transform_tab._history[0]['values'] == {'x': 1.0, 'y': 2.0}
    assert transform_tab._history[1]['values'] == {'y': 3.0, 'z': 4.0}
    
def test_compound_transform_reset(transform_tab, qtbot):
    """Test resetting all transform values."""
    # Set and apply compound transform
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 3):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
        transform_tab.translate_z.setValue(3.0)
    transform_tab.apply_transform()
    
    # Reset values
    transform_tab.reset_transform_values()
    
    # Verify all values are reset
    assert transform_tab.translate_x.value() == 0.0
    assert transform_tab.translate_y.value() == 0.0
    assert transform_tab.translate_z.value() == 0.0
    assert len(transform_tab._history) == 0
    
def test_compound_transform_visual_feedback(viewport, qtbot):
    """Test visual feedback for compound transforms."""
    # Create preview overlay
    overlay = TransformPreviewOverlay()
    
    # Start preview with multiple axes
    overlay.start_preview('translate', {'x': 1.0, 'y': 2.0})
    
    # Verify preview parameters
    assert len(overlay.axes_values) == 2
    assert overlay.axes_values['x'] == 1.0
    assert overlay.axes_values['y'] == 2.0
    
    # Update preview with additional axis
    overlay.update_preview({'x': 1.0, 'y': 2.0, 'z': 3.0})
    assert len(overlay.axes_values) == 3
    
    # Stop preview
    overlay.stop_preview()
    assert not overlay.active
    assert len(overlay.axes_values) == 0 

def test_transform_mode_initialization(transform_tab):
    """Test initial transform mode state."""
    assert transform_tab._transform_mode == 'absolute'
    assert transform_tab.absolute_mode.isChecked()
    assert not transform_tab.relative_mode.isChecked()

def test_transform_mode_switch(transform_tab, qtbot):
    """Test switching between absolute and relative modes."""
    # Switch to relative mode
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.relative_mode.setChecked(True)
    
    assert transform_tab._transform_mode == 'relative'
    assert not transform_tab.absolute_mode.isChecked()
    
    # Switch back to absolute mode
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.absolute_mode.setChecked(True)
    
    assert transform_tab._transform_mode == 'absolute'
    assert not transform_tab.relative_mode.isChecked()

def test_spinbox_ranges_in_absolute_mode(transform_tab):
    """Test spinbox ranges in absolute mode."""
    transform_tab.absolute_mode.setChecked(True)
    
    # Check translation ranges
    assert transform_tab.translate_x.minimum() == -1000
    assert transform_tab.translate_x.maximum() == 1000
    assert transform_tab.translate_x.value() == 0.0
    
    # Check rotation ranges
    assert transform_tab.rotate_x.minimum() == 0
    assert transform_tab.rotate_x.maximum() == 360
    assert transform_tab.rotate_x.value() == 0.0
    
    # Check scale ranges
    assert transform_tab.scale_x.minimum() == 0.01
    assert transform_tab.scale_x.maximum() == 100.0
    assert transform_tab.scale_x.value() == 1.0

def test_spinbox_ranges_in_relative_mode(transform_tab):
    """Test spinbox ranges in relative mode."""
    transform_tab.relative_mode.setChecked(True)
    
    # Check translation ranges
    assert transform_tab.translate_x.minimum() == -1000
    assert transform_tab.translate_x.maximum() == 1000
    assert transform_tab.translate_x.value() == 0.0
    
    # Check rotation ranges
    assert transform_tab.rotate_x.minimum() == -360
    assert transform_tab.rotate_x.maximum() == 360
    assert transform_tab.rotate_x.value() == 0.0
    
    # Check scale ranges
    assert transform_tab.scale_x.minimum() == -0.99
    assert transform_tab.scale_x.maximum() == 10.0
    assert transform_tab.scale_x.value() == 0.0

def test_absolute_transform_preview(transform_tab, viewport, qtbot):
    """Test transform preview in absolute mode."""
    transform_tab.absolute_mode.setChecked(True)
    
    # Set translation values
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.translate_x.setValue(5.0)
    
    # Check signal arguments
    assert blocker.args[0] == 'translate'  # transform_type
    assert blocker.args[1] == {'x': 5.0}   # transform_values
    assert blocker.args[2] == 'absolute'    # transform_mode
    
    # Check preview overlay
    assert viewport.preview_overlay.transform_mode == 'absolute'
    assert viewport.preview_overlay.axes_values['x'] == 5.0

def test_relative_transform_preview(transform_tab, viewport, qtbot):
    """Test transform preview in relative mode."""
    transform_tab.relative_mode.setChecked(True)
    
    # Set translation values
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.translate_x.setValue(2.0)
    
    # Check signal arguments
    assert blocker.args[0] == 'translate'  # transform_type
    assert blocker.args[1] == {'x': 2.0}   # transform_values
    assert blocker.args[2] == 'relative'    # transform_mode
    
    # Check preview overlay
    assert viewport.preview_overlay.transform_mode == 'relative'
    assert viewport.preview_overlay.axes_values['x'] == 2.0

def test_compound_transform_with_modes(transform_tab, viewport, qtbot):
    """Test compound transforms with different modes."""
    # Start with absolute mode
    transform_tab.absolute_mode.setChecked(True)
    
    # Set multiple transform values
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2) as blockers:
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
    
    # Check last signal
    assert blockers[-1].args[0] == 'translate'  # transform_type
    assert blockers[-1].args[1] == {'x': 1.0, 'y': 2.0}  # transform_values
    assert blockers[-1].args[2] == 'absolute'  # transform_mode
    
    # Switch to relative mode
    transform_tab.relative_mode.setChecked(True)
    
    # Set additional transform value
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.translate_z.setValue(3.0)
    
    # Check signal
    assert blocker.args[0] == 'translate'
    assert blocker.args[1] == {'x': 0.0, 'y': 0.0, 'z': 3.0}  # Values reset for relative mode
    assert blocker.args[2] == 'relative'

def test_preview_text_formatting_with_modes(viewport):
    """Test value text formatting for different modes."""
    overlay = viewport.preview_overlay
    
    # Test absolute mode
    overlay.transform_mode = 'absolute'
    overlay.transform_type = 'translate'
    overlay.axes_values = {'x': 5.0}
    assert overlay.get_value_text('x') == "+5.00"
    
    overlay.transform_type = 'rotate'
    overlay.axes_values = {'y': 45.0}
    assert overlay.get_value_text('y') == "+45.0°"
    
    overlay.transform_type = 'scale'
    overlay.axes_values = {'z': 2.0}
    assert overlay.get_value_text('z') == "×2.00"
    
    # Test relative mode
    overlay.transform_mode = 'relative'
    overlay.transform_type = 'translate'
    overlay.axes_values = {'x': 1.0}
    assert overlay.get_value_text('x') == "Δ+1.00"
    
    overlay.transform_type = 'rotate'
    overlay.axes_values = {'y': 90.0}
    assert overlay.get_value_text('y') == "Δ+90.0°"
    
    overlay.transform_type = 'scale'
    overlay.axes_values = {'z': 0.5}
    assert overlay.get_value_text('z') == "Δ×+0.50"

def test_preview_end_position_with_modes(viewport):
    """Test end position calculation for different modes."""
    overlay = viewport.preview_overlay
    center = np.array([0.0, 0.0, 0.0])
    
    # Test absolute translation
    overlay.transform_mode = 'absolute'
    overlay.transform_type = 'translate'
    overlay.axes_values = {'x': 5.0}
    end_pos = overlay.get_preview_end_position(center, 'x')
    assert np.allclose(end_pos, [5.0, 0.0, 0.0])
    
    # Test relative translation
    overlay.transform_mode = 'relative'
    overlay.transform_type = 'translate'
    overlay.axes_values = {'x': 2.0}
    end_pos = overlay.get_preview_end_position(center, 'x')
    assert np.allclose(end_pos, [2.0, 0.0, 0.0])
    
    # Test absolute scale
    overlay.transform_mode = 'absolute'
    overlay.transform_type = 'scale'
    overlay.axes_values = {'x': 2.0}
    end_pos = overlay.get_preview_end_position(np.array([1.0, 1.0, 1.0]), 'x')
    assert np.allclose(end_pos, [2.0, 1.0, 1.0])
    
    # Test relative scale
    overlay.transform_mode = 'relative'
    overlay.transform_type = 'scale'
    overlay.axes_values = {'x': 0.5}
    end_pos = overlay.get_preview_end_position(np.array([1.0, 1.0, 1.0]), 'x')
    assert np.allclose(end_pos, [1.5, 1.0, 1.0]) 

def test_edge_case_max_values_absolute(transform_tab, viewport, qtbot):
    """Test setting maximum values in absolute mode."""
    transform_tab.absolute_mode.setChecked(True)
    
    # Test translation max value
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.translate_x.setValue(1000.0)
    
    assert blocker.args[0] == 'translate'
    assert blocker.args[1] == {'x': 1000.0}
    assert blocker.args[2] == 'absolute'
    assert viewport.preview_overlay.axes_values['x'] == 1000.0
    
    # Test rotation max value
    transform_tab._set_transform_mode('rotate')
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.rotate_y.setValue(360.0)
    
    assert blocker.args[0] == 'rotate'
    assert blocker.args[1] == {'y': 360.0}
    assert blocker.args[2] == 'absolute'
    
    # Test scale max value
    transform_tab._set_transform_mode('scale')
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.scale_z.setValue(100.0)
    
    assert blocker.args[0] == 'scale'
    assert blocker.args[1] == {'z': 100.0}
    assert blocker.args[2] == 'absolute'

def test_edge_case_min_values_relative(transform_tab, viewport, qtbot):
    """Test setting minimum values in relative mode."""
    transform_tab.relative_mode.setChecked(True)
    
    # Test translation min value
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.translate_x.setValue(-1000.0)
    
    assert blocker.args[0] == 'translate'
    assert blocker.args[1] == {'x': -1000.0}
    assert blocker.args[2] == 'relative'
    assert viewport.preview_overlay.axes_values['x'] == -1000.0
    
    # Test rotation min value
    transform_tab._set_transform_mode('rotate')
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.rotate_y.setValue(-360.0)
    
    assert blocker.args[0] == 'rotate'
    assert blocker.args[1] == {'y': -360.0}
    assert blocker.args[2] == 'relative'
    
    # Test scale min value
    transform_tab._set_transform_mode('scale')
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.scale_z.setValue(-0.99)
    
    assert blocker.args[0] == 'scale'
    assert blocker.args[1] == {'z': -0.99}
    assert blocker.args[2] == 'relative'

def test_mode_switch_during_preview(transform_tab, viewport, qtbot):
    """Test switching modes while preview is active with multiple axes."""
    # Set values in absolute mode
    transform_tab.absolute_mode.setChecked(True)
    transform_tab.translate_x.setValue(5.0)
    transform_tab.translate_y.setValue(3.0)
    
    # Verify initial preview state
    assert viewport.preview_overlay.transform_mode == 'absolute'
    assert viewport.preview_overlay.axes_values == {'x': 5.0, 'y': 3.0}
    
    # Switch to relative mode
    with qtbot.waitSignal(transform_tab.transformPreviewRequested) as blocker:
        transform_tab.relative_mode.setChecked(True)
    
    # Verify preview updates
    assert viewport.preview_overlay.transform_mode == 'relative'
    assert all(val == 0.0 for val in viewport.preview_overlay.axes_values.values())
    
    # Set new values in relative mode
    transform_tab.translate_x.setValue(2.0)
    end_pos = viewport.preview_overlay.get_preview_end_position(np.array([0.0, 0.0, 0.0]), 'x')
    assert np.allclose(end_pos, [2.0, 0.0, 0.0])

def test_zero_values_behavior(transform_tab, viewport, qtbot):
    """Test behavior with zero values in both modes."""
    # Test absolute mode
    transform_tab.absolute_mode.setChecked(True)
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.translate_x.setValue(0.0)
    
    center = np.array([1.0, 1.0, 1.0])
    end_pos = viewport.preview_overlay.get_preview_end_position(center, 'x')
    assert np.allclose(end_pos, [0.0, 1.0, 1.0])  # X should be set to 0
    
    # Test relative mode
    transform_tab.relative_mode.setChecked(True)
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.translate_x.setValue(0.0)
    
    end_pos = viewport.preview_overlay.get_preview_end_position(center, 'x')
    assert np.allclose(end_pos, center)  # Should remain unchanged

def test_compound_transform_consistency(transform_tab, viewport, qtbot):
    """Test consistency of compound transforms across multiple axes."""
    transform_tab.absolute_mode.setChecked(True)
    center = np.array([0.0, 0.0, 0.0])
    
    # Set values for all axes
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 3):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
        transform_tab.translate_z.setValue(3.0)
    
    # Check end position for each axis
    end_pos_x = viewport.preview_overlay.get_preview_end_position(center, 'x')
    end_pos_y = viewport.preview_overlay.get_preview_end_position(center, 'y')
    end_pos_z = viewport.preview_overlay.get_preview_end_position(center, 'z')
    
    assert np.allclose(end_pos_x, [1.0, 0.0, 0.0])
    assert np.allclose(end_pos_y, [0.0, 2.0, 0.0])
    assert np.allclose(end_pos_z, [0.0, 0.0, 3.0])
    
    # Switch to relative mode and verify
    transform_tab.relative_mode.setChecked(True)
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 3):
        transform_tab.translate_x.setValue(0.5)
        transform_tab.translate_y.setValue(1.0)
        transform_tab.translate_z.setValue(1.5)
    
    end_pos_x = viewport.preview_overlay.get_preview_end_position(center, 'x')
    end_pos_y = viewport.preview_overlay.get_preview_end_position(center, 'y')
    end_pos_z = viewport.preview_overlay.get_preview_end_position(center, 'z')
    
    assert np.allclose(end_pos_x, [0.5, 0.0, 0.0])
    assert np.allclose(end_pos_y, [0.0, 1.0, 0.0])
    assert np.allclose(end_pos_z, [0.0, 0.0, 1.5])

def test_preview_reflection_accuracy(transform_tab, viewport, qtbot):
    """Test accuracy of preview reflection for compound transforms."""
    transform_tab.relative_mode.setChecked(True)
    transform_tab._set_transform_mode('scale')
    
    # Set scale values
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.scale_x.setValue(0.5)  # 50% increase
        transform_tab.scale_y.setValue(1.0)  # 100% increase
    
    center = np.array([1.0, 1.0, 1.0])
    
    # Check end positions reflect relative scaling
    end_pos_x = viewport.preview_overlay.get_preview_end_position(center, 'x')
    end_pos_y = viewport.preview_overlay.get_preview_end_position(center, 'y')
    
    assert np.allclose(end_pos_x, [1.5, 1.0, 1.0])  # 1.0 + 50%
    assert np.allclose(end_pos_y, [1.0, 2.0, 1.0])  # 1.0 + 100%

def test_preview_update_performance(transform_tab, viewport, qtbot):
    """Test performance of preview updates with multiple axes."""
    import time
    
    transform_tab.absolute_mode.setChecked(True)
    update_count = 100
    start_time = time.time()
    
    # Simulate rapid updates
    for i in range(update_count):
        transform_tab.translate_x.setValue(float(i % 10))
        transform_tab.translate_y.setValue(float((i + 1) % 10))
        transform_tab.translate_z.setValue(float((i + 2) % 10))
        
        # Process events to ensure updates are handled
        qtbot.wait(1)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Check performance metrics
    assert duration < 2.0  # Should complete within 2 seconds
    assert viewport.preview_overlay.active  # Preview should remain active
    assert len(viewport.preview_overlay.axes_values) == 3  # All axes should be tracked

def test_compound_transform_with_modes_enhanced(transform_tab, viewport, qtbot):
    """Enhanced test for compound transforms with mode switching, including end position checks."""
    # Start with absolute mode
    transform_tab.absolute_mode.setChecked(True)
    center = np.array([0.0, 0.0, 0.0])
    
    # Set multiple transform values
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(1.0)
        transform_tab.translate_y.setValue(2.0)
    
    # Check end positions in absolute mode
    end_pos_x = viewport.preview_overlay.get_preview_end_position(center, 'x')
    end_pos_y = viewport.preview_overlay.get_preview_end_position(center, 'y')
    assert np.allclose(end_pos_x, [1.0, 0.0, 0.0])
    assert np.allclose(end_pos_y, [0.0, 2.0, 0.0])
    
    # Switch to relative mode
    transform_tab.relative_mode.setChecked(True)
    
    # Set new value in relative mode
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.translate_z.setValue(3.0)
    
    # Check end position in relative mode
    end_pos_z = viewport.preview_overlay.get_preview_end_position(center, 'z')
    assert np.allclose(end_pos_z, [0.0, 0.0, 3.0])
    
    # Verify all axes are tracked correctly
    assert viewport.preview_overlay.transform_mode == 'relative'
    assert len(viewport.preview_overlay.axes_values) == 3
    assert all(axis in viewport.preview_overlay.axes_values for axis in ['x', 'y', 'z']) 

def test_mode_switch_during_preview_enhanced(transform_tab, viewport, qtbot):
    """Test enhanced mode switching behavior during active preview with multiple axes."""
    # Set initial values in absolute mode
    transform_tab.absolute_mode.setChecked(True)
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(5.0)
        transform_tab.translate_y.setValue(3.0)
    
    # Verify initial preview state
    center = np.array([0.0, 0.0, 0.0])
    end_pos_x = viewport.preview_overlay.get_preview_end_position(center, 'x')
    end_pos_y = viewport.preview_overlay.get_preview_end_position(center, 'y')
    assert np.allclose(end_pos_x, [5.0, 0.0, 0.0])
    assert np.allclose(end_pos_y, [0.0, 3.0, 0.0])
    
    # Switch to relative mode mid-preview
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.relative_mode.setChecked(True)
    
    # Set new values in relative mode
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(2.0)
        transform_tab.translate_y.setValue(1.0)
    
    # Verify preview reflects relative changes from zero
    end_pos_x = viewport.preview_overlay.get_preview_end_position(center, 'x')
    end_pos_y = viewport.preview_overlay.get_preview_end_position(center, 'y')
    assert np.allclose(end_pos_x, [2.0, 0.0, 0.0])
    assert np.allclose(end_pos_y, [0.0, 1.0, 0.0])
    
    # Add a third axis in relative mode
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.translate_z.setValue(1.5)
    
    # Verify all axes maintain correct values
    end_pos_z = viewport.preview_overlay.get_preview_end_position(center, 'z')
    assert np.allclose(end_pos_z, [0.0, 0.0, 1.5])
    assert viewport.preview_overlay.transform_mode == 'relative'
    assert len(viewport.preview_overlay.axes_values) == 3

def test_apply_transform_after_mode_switch(transform_tab, viewport, qtbot):
    """Test applying transforms after switching modes."""
    # Create and select a test shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    original_position = cube.transform.position.copy()
    
    # Set value in absolute mode
    transform_tab.absolute_mode.setChecked(True)
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.translate_x.setValue(10.0)
    
    # Switch to relative mode and set new values
    transform_tab.relative_mode.setChecked(True)
    with qtbot.waitSignals([transform_tab.transformPreviewRequested] * 2):
        transform_tab.translate_x.setValue(2.0)
        transform_tab.translate_y.setValue(3.0)
    
    # Apply the transform
    with qtbot.waitSignal(transform_tab.transformApplied):
        transform_tab.apply_transform()
    
    # Verify transform was applied in relative mode
    assert np.allclose(cube.transform.position, 
                      original_position + np.array([2.0, 3.0, 0.0]))
    
    # Switch back to absolute mode and apply another transform
    transform_tab.absolute_mode.setChecked(True)
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.translate_x.setValue(5.0)
    
    with qtbot.waitSignal(transform_tab.transformApplied):
        transform_tab.apply_transform()
    
    # Verify absolute transform was applied correctly
    assert np.allclose(cube.transform.position[0], 5.0)
    
    # Verify transform history
    assert len(transform_tab._history) == 2
    assert transform_tab._history[0]['mode'] == 'relative'
    assert transform_tab._history[1]['mode'] == 'absolute'

def test_mode_switch_with_rotation_and_scale(transform_tab, viewport, qtbot):
    """Test mode switching with rotation and scale transforms."""
    # Start with absolute mode rotation
    transform_tab.absolute_mode.setChecked(True)
    transform_tab._set_transform_mode('rotate')
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.rotate_x.setValue(90.0)
    
    # Switch to relative mode
    transform_tab.relative_mode.setChecked(True)
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.rotate_x.setValue(45.0)
    
    # Verify rotation preview in relative mode
    center = np.array([0.0, 0.0, 0.0])
    end_pos = viewport.preview_overlay.get_preview_end_position(center, 'x')
    assert viewport.preview_overlay.transform_mode == 'relative'
    assert viewport.preview_overlay.transform_type == 'rotate'
    assert viewport.preview_overlay.axes_values['x'] == 45.0  # Rotation affects orientation, not position
    
    # Switch to scale in absolute mode
    transform_tab.absolute_mode.setChecked(True)
    transform_tab._set_transform_mode('scale')
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.scale_x.setValue(2.0)
    
    # Switch to relative mode for scale
    transform_tab.relative_mode.setChecked(True)
    with qtbot.waitSignal(transform_tab.transformPreviewRequested):
        transform_tab.scale_x.setValue(0.5)
    
    # Verify scale preview in relative mode
    end_pos = viewport.preview_overlay.get_preview_end_position(np.array([1.0, 1.0, 1.0]), 'x')
    assert np.allclose(end_pos, [1.5, 1.0, 1.0])  # 50% increase from 1.0