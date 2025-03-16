import pytest
import time
import numpy as np
from PyQt6.QtWidgets import QApplication
from transform_tab import TransformTab
from viewport import Viewport
from shapes_3d import Cube
from src.core.scene import SceneManager

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
    return Viewport()

def test_bulk_transform_performance(transform_tab, viewport):
    """Test performance of bulk transform operations."""
    # Create 100 shapes
    shapes = []
    for i in range(100):
        cube = Cube(size=1.0)
        shape_id = viewport.addShape(cube)
        shapes.append(shape_id)
        
    # Time bulk transform operations
    start_time = time.time()
    
    for shape_id in shapes:
        viewport.selectShape(shape_id)
        transform_params = {
            'mode': 'translate',
            'axis': 'x',
            'value': 1.0,
            'snap': {'enabled': True, 'translate': 0.25}
        }
        transform_tab.transform_applied.emit('translate', transform_params)
        
    end_time = time.time()
    total_time = end_time - start_time
    
    # Verify performance (should be under 1 second for 100 shapes)
    assert total_time < 1.0, f"Bulk transform took {total_time:.2f} seconds"
    
    # Verify all shapes were transformed
    for shape_id in shapes:
        viewport.selectShape(shape_id)
        shape = viewport.getSelectedShape()
        assert shape is not None
        assert shape.transform.position[0] == 1.0

def test_complex_shape_transform_performance(transform_tab, viewport):
    """Test performance with complex shapes (high vertex count)."""
    # Create a complex shape (cube with many segments)
    cube = Cube(size=2.0)  # In real implementation, this would be a high-poly shape
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Time transform operation
    start_time = time.time()
    
    transform_params = {
        'mode': 'rotate',
        'axis': 'y',
        'value': 45.0,
        'snap': {'enabled': True, 'rotate': 15.0}
    }
    transform_tab.transform_applied.emit('rotate', transform_params)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Verify performance (should be under 100ms)
    assert total_time < 0.1, f"Complex shape transform took {total_time*1000:.2f}ms"
    
    # Verify transform was applied correctly
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert np.isclose(shape.transform.rotation[1], np.radians(45.0))

def test_preset_application_performance(transform_tab, viewport):
    """Test performance of preset application."""
    # Create test presets
    num_presets = 50
    for i in range(num_presets):
        preset_name = f"Preset{i}"
        preset_data = {
            'mode': 'translate',
            'axis': 'x',
            'relative': False,
            'snap': {'enabled': True, 'translate': 0.25},
            'category': f'Category{i%5}',
            'tags': [f'tag{i}'],
            'description': f'Test preset {i}',
            'timestamp': QDateTime.currentDateTime().toString()
        }
        transform_tab._presets[preset_name] = preset_data
    
    # Create shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Time preset loading and application
    start_time = time.time()
    
    for preset_name in transform_tab._presets:
        transform_tab.preset_combo.setCurrentText(preset_name)
        transform_tab.loadSelectedPreset()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Verify performance (should be under 500ms for 50 presets)
    assert total_time < 0.5, f"Preset application took {total_time*1000:.2f}ms"

def test_transform_history_performance(transform_tab, viewport):
    """Test performance of transform history operations."""
    # Create shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Add many transforms to history
    num_transforms = 1000
    start_time = time.time()
    
    for i in range(num_transforms):
        transform_params = {
            'mode': 'translate',
            'axis': 'x',
            'value': 0.1,
            'snap': {'enabled': False}
        }
        transform_tab.transform_applied.emit('translate', transform_params)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Verify performance (should be under 2 seconds for 1000 transforms)
    assert total_time < 2.0, f"History recording took {total_time:.2f} seconds"
    
    # Test undo/redo performance
    start_time = time.time()
    
    for _ in range(100):  # Test 100 undo operations
        transform_tab.undoTransform()
    
    for _ in range(100):  # Test 100 redo operations
        transform_tab.redoTransform()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Verify undo/redo performance (should be under 500ms for 200 operations)
    assert total_time < 0.5, f"Undo/redo operations took {total_time*1000:.2f}ms" 