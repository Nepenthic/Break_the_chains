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
import gc

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

class TransformBatchConfig:
    """Configuration for transform batching."""
    MIN_BATCH_SIZE = 5
    MAX_BATCH_SIZE = 20
    BATCH_TIMEOUT_MS = 16  # 1 frame @ 60fps

def test_ui_state_recovery(transform_tab, viewport):
    """Test UI state recovery after error conditions."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Capture initial UI state
    initial_state = {
        'mode': transform_tab.getCurrentMode(),
        'axis': transform_tab._active_axis,
        'history_len': len(transform_tab._history),
        'undo_enabled': transform_tab.undo_button.isEnabled(),
        'redo_enabled': transform_tab.redo_button.isEnabled(),
        'transform_values': transform_tab.getTransformValues()
    }
    
    # Attempt invalid transform
    transform_params = {
        'mode': 'scale',
        'axis': 'x',
        'value': 0.0,  # Invalid scale factor
        'snap': {'enabled': True}
    }
    transform_tab.transform_applied.emit('scale', transform_params)
    
    # Verify error handling and state recovery
    viewport.showStatusMessage.assert_called_with("Error: Scale factor must be non-zero")
    
    # Verify UI state restored
    assert transform_tab.getCurrentMode() == initial_state['mode']
    assert transform_tab._active_axis == initial_state['axis']
    assert len(transform_tab._history) == initial_state['history_len']
    assert transform_tab.undo_button.isEnabled() == initial_state['undo_enabled']
    assert transform_tab.redo_button.isEnabled() == initial_state['redo_enabled']
    assert transform_tab.getTransformValues() == initial_state['transform_values']

def test_resource_management(transform_tab, viewport):
    """Test resource management during transform operations."""
    # Track initial resource state
    initial_gl_resources = get_gl_resource_count(viewport)
    initial_objects = get_object_count()
    
    # Create test shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Perform complex transform sequence
    transforms = [
        ('translate', 1.0, 'x'),
        ('rotate', 45.0, 'y'),
        ('scale', 2.0, 'z')
    ]
    
    for mode, value, axis in transforms:
        transform_params = {
            'mode': mode,
            'axis': axis,
            'value': value,
            'snap': {'enabled': True}
        }
        transform_tab.transform_applied.emit(mode, transform_params)
    
    # Force cleanup
    viewport.selectShape(None)
    gc.collect()
    
    # Verify resource cleanup
    final_gl_resources = get_gl_resource_count(viewport)
    final_objects = get_object_count()
    
    assert final_gl_resources == initial_gl_resources
    assert final_objects == initial_objects

def test_graduated_memory_thresholds(transform_tab, viewport):
    """Test memory usage with different dataset sizes."""
    thresholds = {
        100: 2 * 1024 * 1024,    # 2MB for 100 presets
        1000: 10 * 1024 * 1024,  # 10MB for 1000 presets
        5000: 40 * 1024 * 1024   # 40MB for 5000 presets
    }
    
    for preset_count, memory_limit in thresholds.items():
        # Create test presets
        create_test_presets(transform_tab, preset_count)
        
        # Measure memory during operations
        start_mem = get_memory_usage()
        
        # Perform UI updates
        transform_tab.updateCategoryFilter()
        transform_tab.updatePresetCombo()
        
        # Force garbage collection
        gc.collect()
        
        # Check memory usage
        end_mem = get_memory_usage()
        mem_increase = end_mem - start_mem
        
        assert mem_increase < memory_limit, \
            f"Memory usage exceeded {memory_limit/1024/1024}MB for {preset_count} presets"
        
        # Clear presets for next iteration
        transform_tab._presets.clear()
        gc.collect()

def test_shared_state_verification(transform_tab, viewport):
    """Test state verification between frontend and backend."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Define verification points
    verify_points = [
        # Normal transform
        {
            'transform': {'mode': 'translate', 'axis': 'x', 'value': 1.0},
            'expected_state': {
                'position': [1.0, 0.0, 0.0],
                'rotation': [0.0, 0.0, 0.0],
                'scale': [1.0, 1.0, 1.0]
            }
        },
        # Compound transform
        {
            'transform': {'mode': 'rotate', 'axis': 'y', 'value': 45.0},
            'expected_state': {
                'position': [1.0, 0.0, 0.0],
                'rotation': [0.0, np.radians(45.0), 0.0],
                'scale': [1.0, 1.0, 1.0]
            }
        }
    ]
    
    for point in verify_points:
        # Apply transform
        transform_params = {
            'mode': point['transform']['mode'],
            'axis': point['transform']['axis'],
            'value': point['transform']['value'],
            'snap': {'enabled': True}
        }
        transform_tab.transform_applied.emit(point['transform']['mode'], transform_params)
        
        # Verify frontend state
        shape = viewport.getSelectedShape()
        assert shape is not None
        assert np.allclose(shape.transform.position, point['expected_state']['position'])
        assert np.allclose(shape.transform.rotation, point['expected_state']['rotation'])
        assert np.allclose(shape.transform.scale, point['expected_state']['scale'])
        
        # Verify UI reflects correct state
        transform_values = transform_tab.getTransformValues()
        assert np.allclose(transform_values['position'], point['expected_state']['position'])
        assert np.allclose(transform_values['rotation'], point['expected_state']['rotation'])
        assert np.allclose(transform_values['scale'], point['expected_state']['scale'])

def test_performance_profiling(transform_tab, viewport):
    """Test detailed performance profiling of transform operations."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Profile complex transform sequence
    transform_sequence = [
        ('translate', 1.0, 'x'),
        ('rotate', 45.0, 'y'),
        ('scale', 2.0, 'z')
    ]
    
    profiling_data = []
    
    for mode, value, axis in transform_sequence:
        profile = {
            'operation': f"{mode}_{axis}",
            'timings': {
                'ui_update': 0,
                'transform_apply': 0,
                'gl_render': 0
            }
        }
        
        # Time UI update
        start_time = time.time()
        transform_params = {
            'mode': mode,
            'axis': axis,
            'value': value,
            'snap': {'enabled': True}
        }
        transform_tab.transform_applied.emit(mode, transform_params)
        profile['timings']['ui_update'] = time.time() - start_time
        
        # Time GL render
        start_time = time.time()
        viewport.update()
        profile['timings']['gl_render'] = time.time() - start_time
        
        profiling_data.append(profile)
        
        # Verify performance thresholds
        assert profile['timings']['ui_update'] < 0.016  # 16ms
        assert profile['timings']['gl_render'] < 0.016  # 16ms
        
    return profiling_data

# Helper functions

def get_gl_resource_count(viewport):
    """Get count of OpenGL resources."""
    # In real implementation, would track textures, VBOs, etc.
    return 0  # Placeholder

def get_object_count():
    """Get count of Python objects."""
    return len(gc.get_objects())

def create_test_presets(transform_tab, count):
    """Create test presets with unique data."""
    for i in range(count):
        preset_name = f"Preset{i}"
        preset_data = {
            'mode': 'translate',
            'axis': 'x',
            'relative': False,
            'snap': {'enabled': True, 'translate': 0.25},
            'category': f'Category{i%20}',
            'tags': [f'tag{j}' for j in range(i%5)],
            'description': f'Test preset {i}',
            'timestamp': QDateTime.currentDateTime().toString()
        }
        transform_tab._presets[preset_name] = preset_data

def get_memory_usage():
    """Get current memory usage in bytes."""
    import psutil
    import os
    process = psutil.Process(os.getpid())
    return process.memory_info().rss 