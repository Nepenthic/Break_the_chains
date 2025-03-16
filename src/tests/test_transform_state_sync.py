import pytest
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
import numpy as np
from transform_tab import TransformTab
from viewport import Viewport
from shapes_3d import Cube
from unittest.mock import MagicMock, patch
import time

@pytest.fixture
def app():
    """Create QApplication instance for tests."""
    return QApplication([])

@pytest.fixture
def transform_tab(app):
    """Create TransformTab instance for tests."""
    return TransformTab()

@pytest.fixture
def viewport():
    """Create Viewport instance for tests."""
    viewport = Viewport()
    viewport.update_transform_gizmos = MagicMock()
    viewport.update_snap_grid = MagicMock()
    viewport.showStatusMessage = MagicMock()
    return viewport

def test_transform_state_consistency(transform_tab, viewport):
    """Test state consistency between UI and scene during transforms."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Define transform sequence
    transforms = [
        ('translate', {'x': 1.0, 'y': 0.0, 'z': 0.0}),
        ('rotate', {'x': 0.0, 'y': 45.0, 'z': 0.0}),
        ('scale', {'x': 2.0, 'y': 2.0, 'z': 2.0})
    ]
    
    # Apply transforms and verify state consistency
    for mode, params in transforms:
        # Apply transform
        transform_params = {
            'mode': mode,
            'axis': list(params.keys())[0],
            'value': list(params.values())[0],
            'snap': {'enabled': True}
        }
        transform_tab.transform_applied.emit(mode, transform_params)
        
        # Verify UI state
        assert transform_tab.getCurrentMode() == mode
        assert transform_tab._active_axis == transform_params['axis']
        
        # Verify scene state
        shape = viewport.getSelectedShape()
        assert shape is not None
        
        # Verify transform values
        if mode == 'translate':
            assert np.allclose(shape.transform.position, [1.0, 0.0, 0.0])
        elif mode == 'rotate':
            assert np.allclose(shape.transform.rotation[1], np.radians(45.0))
        elif mode == 'scale':
            assert np.allclose(shape.transform.scale, [2.0, 2.0, 2.0])
        
        # Verify history state
        assert transform_tab._history[-1]['params']['mode'] == mode
        assert transform_tab._history[-1]['params']['value'] == list(params.values())[0]

def test_history_state_sync(transform_tab, viewport):
    """Test history state synchronization between UI and transform system."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Apply multiple transforms
    transform_params = {
        'mode': 'translate',
        'axis': 'x',
        'value': 1.0,
        'snap': {'enabled': True}
    }
    transform_tab.transform_applied.emit('translate', transform_params)
    
    transform_params['value'] = 2.0
    transform_tab.transform_applied.emit('translate', transform_params)
    
    # Verify initial state
    assert len(transform_tab._history) == 2
    assert transform_tab.undo_button.isEnabled()
    assert not transform_tab.redo_button.isEnabled()
    
    # Test undo state sync
    transform_tab.undoTransform()
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert np.allclose(shape.transform.position[0], 1.0)
    assert transform_tab.redo_button.isEnabled()
    
    # Test redo state sync
    transform_tab.redoTransform()
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert np.allclose(shape.transform.position[0], 2.0)
    assert not transform_tab.redo_button.isEnabled()

def test_ui_update_batching(transform_tab, viewport):
    """Test UI update batching during rapid transforms."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Mock UI update methods to track calls
    with patch.object(viewport, 'update') as mock_update:
        # Apply rapid transforms
        for i in range(10):
            transform_params = {
                'mode': 'translate',
                'axis': 'x',
                'value': 0.1 * i,
                'snap': {'enabled': False}
            }
            transform_tab.transform_applied.emit('translate', transform_params)
        
        # Verify batched updates
        assert mock_update.call_count < 10  # Updates should be coalesced

def test_error_handling_coordination(transform_tab, viewport):
    """Test error handling coordination between UI and transform system."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Test invalid transform scenarios
    invalid_transforms = [
        ('rotate', float('inf'), 'y'),  # Invalid rotation
        ('scale', -1.0, 'all'),         # Invalid scale
        ('translate', None, 'x')        # Invalid translation
    ]
    
    for mode, value, axis in invalid_transforms:
        transform_params = {
            'mode': mode,
            'axis': axis,
            'value': value,
            'snap': {'enabled': True}
        }
        
        # Apply invalid transform
        transform_tab.transform_applied.emit(mode, transform_params)
        
        # Verify error handling
        viewport.showStatusMessage.assert_called_with(
            f"Error: Invalid {mode} value"
        )
        
        # Verify no change to transform history
        assert all(t['params']['value'] != value for t in transform_tab._history)

def test_webgl_frame_timing(transform_tab, viewport):
    """Test WebGL frame timing during complex transform sequences."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Define complex transform sequence
    transforms = [
        ('rotate', 45.0, 'y'),
        ('translate', 1.0, 'x'),
        ('scale', 2.0, 'z')
    ]
    
    # Track frame times
    frame_times = []
    
    for mode, value, axis in transforms:
        start_time = time.time()
        
        transform_params = {
            'mode': mode,
            'axis': axis,
            'value': value,
            'snap': {'enabled': True}
        }
        transform_tab.transform_applied.emit(mode, transform_params)
        
        # Wait for frame completion
        viewport.makeCurrent.assert_called()
        viewport.doneCurrent.assert_called()
        
        frame_time = time.time() - start_time
        frame_times.append(frame_time)
        
        # Verify frame time is within acceptable range (16ms for 60fps)
        assert frame_time < 0.016, f"Frame time exceeded 16ms: {frame_time*1000:.2f}ms"
    
    # Verify average frame time
    avg_frame_time = sum(frame_times) / len(frame_times)
    assert avg_frame_time < 0.010, f"Average frame time too high: {avg_frame_time*1000:.2f}ms"

def test_memory_optimization(transform_tab, viewport):
    """Test memory usage during filter operations."""
    # Create large number of presets with various categories and tags
    num_presets = 1000
    categories = [f"Category{i}" for i in range(20)]
    tags = [f"tag{i}" for i in range(50)]
    
    for i in range(num_presets):
        preset_name = f"Preset{i}"
        preset_data = {
            'mode': 'translate',
            'axis': 'x',
            'relative': False,
            'snap': {'enabled': True, 'translate': 0.25},
            'category': categories[i % len(categories)],
            'tags': [tags[j] for j in range(i % 5)],
            'description': f'Test preset {i}',
            'timestamp': QDateTime.currentDateTime().toString()
        }
        transform_tab._presets[preset_name] = preset_data
    
    # Test category filtering
    start_mem = get_memory_usage()
    
    for category in categories:
        transform_tab.category_filter.setCurrentText(category)
        transform_tab.updatePresetCombo()
    
    end_mem = get_memory_usage()
    mem_increase = end_mem - start_mem
    
    # Verify memory usage stays within reasonable bounds (e.g., less than 10MB)
    assert mem_increase < 10 * 1024 * 1024  # 10MB

def get_memory_usage():
    """Helper function to get current memory usage."""
    import psutil
    import os
    process = psutil.Process(os.getpid())
    return process.memory_info().rss 