import pytest
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QVector3D
from PyQt6.QtWidgets import QApplication
import numpy as np
from src.core.scene import SceneManager
from transform_tab import TransformTab
from viewport import Viewport
from shapes_3d import Cube, Sphere

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

def test_preset_application_to_new_shape(transform_tab, viewport):
    """Test applying transform preset to newly created shape."""
    # Create a test preset
    preset_name = "Test Preset"
    preset_data = {
        'mode': 'translate',
        'axis': 'x',
        'relative': False,
        'snap': {
            'enabled': True,
            'translate': 0.25,
            'rotate': 15.0,
            'scale': 0.25
        },
        'category': 'Test',
        'tags': ['test'],
        'description': 'Test preset',
        'timestamp': QDateTime.currentDateTime().toString()
    }
    transform_tab._presets[preset_name] = preset_data
    
    # Create and add a shape
    cube = Cube(size=2.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Load and apply preset
    transform_tab.preset_combo.setCurrentText(preset_name)
    transform_tab.loadSelectedPreset()
    
    # Verify shape transform
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert shape.transform.position[0] == 0.25  # Snapped translation
    assert transform_tab._history[-1]['params']['mode'] == 'translate'
    assert transform_tab._history[-1]['params']['axis'] == 'x'

def test_realtime_transform_updates(transform_tab, viewport):
    """Test real-time updates when applying transforms."""
    # Create and select shape
    sphere = Sphere(radius=1.0)
    shape_id = viewport.addShape(sphere)
    viewport.selectShape(shape_id)
    
    # Apply transform
    transform_params = {
        'mode': 'scale',
        'axis': 'y',
        'value': 2.0,
        'snap': {
            'enabled': True,
            'translate': 0.25,
            'rotate': 15.0,
            'scale': 0.25
        }
    }
    transform_tab.transform_applied.emit('scale', transform_params)
    
    # Verify immediate update
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert np.isclose(shape.transform.scale[1], 2.0)
    assert transform_tab._history[-1]['params']['mode'] == 'scale'

def test_transform_error_handling(transform_tab, viewport):
    """Test error handling in transform system."""
    # Test applying transform with no selection
    transform_params = {
        'mode': 'rotate',
        'axis': 'z',
        'value': 45.0,
        'snap': {'enabled': True, 'rotate': 15.0}
    }
    transform_tab.transform_applied.emit('rotate', transform_params)
    assert len(transform_tab._history) == 0  # No transform added to history
    
    # Test invalid transform parameters
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    invalid_params = {
        'mode': 'invalid_mode',
        'axis': 'x',
        'value': 1.0
    }
    with pytest.raises(ValueError):
        viewport.scene_manager.apply_transform(shape_id, 'invalid_mode', invalid_params)

def test_transform_history_sync(transform_tab, viewport):
    """Test synchronization between transform history and shape state."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Apply multiple transforms
    transforms = [
        ('translate', {'x': 1.0, 'y': 0.0, 'z': 0.0}),
        ('rotate', {'x': 0.0, 'y': 45.0, 'z': 0.0}),
        ('scale', {'x': 2.0, 'y': 2.0, 'z': 2.0})
    ]
    
    for mode, params in transforms:
        transform_params = {
            'mode': mode,
            'axis': list(params.keys())[0],
            'value': list(params.values())[0],
            'snap': {'enabled': False}
        }
        transform_tab.transform_applied.emit(mode, transform_params)
    
    # Verify history
    assert len(transform_tab._history) == len(transforms)
    
    # Test undo/redo
    transform_tab.undoTransform()
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert not np.allclose(shape.transform.scale, [2.0, 2.0, 2.0])
    
    transform_tab.redoTransform()
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert np.allclose(shape.transform.scale, [2.0, 2.0, 2.0])

def test_preset_categories_and_tags(transform_tab):
    """Test preset organization with categories and tags."""
    # Add presets with categories and tags
    presets = {
        "Preset1": {
            'mode': 'translate',
            'axis': 'x',
            'relative': False,
            'snap': {'enabled': True, 'translate': 0.5},
            'category': 'Position',
            'tags': ['move', 'precise'],
            'description': 'Move right',
            'timestamp': QDateTime.currentDateTime().toString()
        },
        "Preset2": {
            'mode': 'rotate',
            'axis': 'y',
            'relative': True,
            'snap': {'enabled': True, 'rotate': 45.0},
            'category': 'Rotation',
            'tags': ['spin', 'angle'],
            'description': 'Rotate 45°',
            'timestamp': QDateTime.currentDateTime().toString()
        }
    }
    transform_tab._presets.update(presets)
    transform_tab.updateCategoryFilter()
    
    # Test category filter
    categories = {item.text() for item in [transform_tab.category_filter.itemText(i) 
                 for i in range(transform_tab.category_filter.count())]}
    assert 'Position' in categories
    assert 'Rotation' in categories
    
    # Test preset filtering by category
    transform_tab.category_filter.setCurrentText('Position')
    assert transform_tab.preset_combo.findText("Preset1") >= 0
    assert transform_tab.preset_combo.findText("Preset2") == -1

def test_transform_gizmo_interaction(transform_tab, viewport):
    """Test transform gizmo visualization and interaction."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Set transform mode
    viewport.setTransformMode('translate')
    
    # Verify gizmo creation
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert shape.transform_mode == 'translate'
    
    # Test gizmo scale update
    viewport.camera_distance = 10.0
    viewport.updateGizmoScale()
    shape = viewport.getSelectedShape()
    assert shape.gizmo_scale == pytest.approx(1.5, rel=1e-2)  # 10.0 * 0.15

def test_snap_settings_integration(transform_tab, viewport):
    """Test snapping settings integration between transform tab and viewport."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Update snap settings
    snap_settings = {
        'enabled': True,
        'translate': 0.5,
        'rotate': 30.0,
        'scale': 0.5
    }
    transform_tab.snap_settings_changed.emit(snap_settings)
    
    # Apply transform with snapping
    transform_params = {
        'mode': 'translate',
        'axis': 'x',
        'value': 0.7,  # Should snap to 0.5
        'snap': snap_settings
    }
    transform_tab.transform_applied.emit('translate', transform_params)
    
    # Verify snapped position
    shape = viewport.getSelectedShape()
    assert shape is not None
    assert shape.transform.position[0] == pytest.approx(0.5, rel=1e-6) 