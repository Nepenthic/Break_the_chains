import pytest
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
import numpy as np
from transform_tab import TransformTab
from viewport import Viewport
from shapes_3d import Cube
from unittest.mock import MagicMock
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
    # Mock the update methods for verification
    viewport.update_transform_gizmos = MagicMock()
    viewport.update_snap_grid = MagicMock()
    viewport.showStatusMessage = MagicMock()
    return viewport

def test_preset_ui_feedback(transform_tab, viewport):
    """Test UI feedback when applying presets."""
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
    
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Apply preset
    transform_tab.preset_combo.setCurrentText(preset_name)
    transform_tab.loadSelectedPreset()
    
    # Verify UI updates
    viewport.update_transform_gizmos.assert_called_with(
        mode='translate',
        axis='x',
        snap_enabled=True
    )
    viewport.update_snap_grid.assert_called_with(
        enabled=True,
        spacing=0.25
    )
    viewport.showStatusMessage.assert_called_with(
        "Preset 'Test Preset' applied"
    )

def test_ui_interaction_patterns(transform_tab, viewport):
    """Test common UI interaction patterns."""
    # Test preset combo interaction
    QTest.mouseClick(transform_tab.preset_combo, Qt.MouseButton.LeftButton)
    QTest.keyClicks(transform_tab.preset_combo, "Test")
    
    # Test category filter
    QTest.mouseClick(transform_tab.category_filter, Qt.MouseButton.LeftButton)
    QTest.keyClicks(transform_tab.category_filter, "Position")
    
    # Test snap settings interaction
    QTest.mouseClick(transform_tab.snap_enabled, Qt.MouseButton.LeftButton)
    assert transform_tab.snap_enabled.isChecked()
    
    # Test transform mode buttons
    for button in transform_tab.mode_group.buttons():
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert button.isChecked()
        
    # Test axis selection
    for button in transform_tab.axis_group.buttons():
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert button.isChecked()

def test_memory_intensive_ui(transform_tab, viewport):
    """Test UI performance with memory-intensive operations."""
    # Create many presets with unique categories and tags
    num_presets = 1000
    for i in range(num_presets):
        preset_name = f"Preset{i}"
        preset_data = {
            'mode': 'translate',
            'axis': 'x',
            'relative': False,
            'snap': {'enabled': True, 'translate': 0.25},
            'category': f'Category{i%20}',  # 20 different categories
            'tags': [f'tag{j}' for j in range(i%10)],  # Up to 10 tags per preset
            'description': f'Test preset {i}',
            'timestamp': QDateTime.currentDateTime().toString()
        }
        transform_tab._presets[preset_name] = preset_data
    
    # Update UI and measure performance
    start_time = time.time()
    transform_tab.updateCategoryFilter()
    transform_tab.updatePresetCombo()
    end_time = time.time()
    
    # Verify UI responsiveness (should update within 100ms)
    assert (end_time - start_time) < 0.1
    
    # Verify memory usage (categories and presets properly filtered)
    assert transform_tab.category_filter.count() <= 21  # All Categories + 20 categories
    assert transform_tab.preset_combo.count() == num_presets

def test_edge_case_ui_interactions(transform_tab, viewport):
    """Test edge cases in UI interactions."""
    # Test rapid mode switching
    modes = ['translate', 'rotate', 'scale']
    for _ in range(10):  # Rapidly switch 10 times
        for mode in modes:
            for button in transform_tab.mode_group.buttons():
                if button.text().lower().startswith(mode):
                    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                    break
    
    # Test concurrent operations
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Simulate rapid transform changes while changing modes
    for i in range(10):
        # Change mode
        mode = modes[i % 3]
        for button in transform_tab.mode_group.buttons():
            if button.text().lower().startswith(mode):
                QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                break
        
        # Apply transform immediately
        transform_params = {
            'mode': mode,
            'axis': 'x',
            'value': 1.0,
            'snap': {'enabled': True}
        }
        transform_tab.transform_applied.emit(mode, transform_params)
    
    # Verify history integrity
    assert len(transform_tab._history) == 10
    
    # Test UI state after rapid operations
    assert transform_tab.undo_button.isEnabled()
    assert not transform_tab.redo_button.isEnabled()

def test_webgl_rendering_sync(transform_tab, viewport):
    """Test synchronization between transforms and WebGL rendering."""
    # Create and select shape
    cube = Cube(size=1.0)
    shape_id = viewport.addShape(cube)
    viewport.selectShape(shape_id)
    
    # Mock the OpenGL context
    viewport.makeCurrent = MagicMock()
    viewport.doneCurrent = MagicMock()
    
    # Apply transform that requires render update
    transform_params = {
        'mode': 'rotate',
        'axis': 'y',
        'value': 45.0,
        'snap': {'enabled': True}
    }
    transform_tab.transform_applied.emit('rotate', transform_params)
    
    # Verify render update sequence
    viewport.makeCurrent.assert_called()
    viewport.doneCurrent.assert_called()
    
    # Verify transform gizmo update
    viewport.update_transform_gizmos.assert_called_with(
        mode='rotate',
        axis='y',
        snap_enabled=True
    ) 