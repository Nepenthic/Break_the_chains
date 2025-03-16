"""
Unit tests for TransformTab UI enhancements, focusing on accessibility,
performance, and keyboard navigation.
"""

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
import time
from transform_tab import TransformTab

@pytest.fixture
def transform_tab(qtbot):
    """Create TransformTab instance for tests."""
    tab = TransformTab()
    qtbot.addWidget(tab)
    return tab

def test_keyboard_navigation(transform_tab, qtbot):
    """Test keyboard navigation through transform modes."""
    # Focus the mode indicator
    transform_tab.mode_indicator.setFocus()
    assert transform_tab.mode_indicator.hasFocus()
    
    # Test mode cycling with Space
    assert transform_tab.current_transform_mode == 'translate'
    QTest.keyClick(transform_tab.mode_indicator, Qt.Key_Space)
    assert transform_tab.current_transform_mode == 'rotate'
    QTest.keyClick(transform_tab.mode_indicator, Qt.Key_Space)
    assert transform_tab.current_transform_mode == 'scale'
    QTest.keyClick(transform_tab.mode_indicator, Qt.Key_Space)
    assert transform_tab.current_transform_mode == 'translate'
    
    # Test relative mode toggle with R
    assert not transform_tab._relative_mode
    QTest.keyClick(transform_tab.mode_indicator, Qt.Key_R)
    assert transform_tab._relative_mode
    QTest.keyClick(transform_tab.mode_indicator, Qt.Key_R)
    assert not transform_tab._relative_mode

def test_animation_performance(transform_tab, qtbot):
    """Test performance of mode transition animations."""
    # Monitor transition time
    start_time = time.perf_counter_ns()
    
    # Trigger mode change
    with qtbot.waitSignal(transform_tab.mode_transition_completed):
        transform_tab._set_transform_mode('rotate')
    
    # Check transition duration
    duration = (time.perf_counter_ns() - start_time) / 1_000_000  # ms
    assert duration < transform_tab.PERFORMANCE_THRESHOLD
    
    # Test rapid mode switches
    for _ in range(5):
        with qtbot.waitSignal(transform_tab.mode_transition_completed):
            transform_tab._set_transform_mode('scale')
        with qtbot.waitSignal(transform_tab.mode_transition_completed):
            transform_tab._set_transform_mode('translate')
    
    # Verify no performance warnings were emitted
    assert not hasattr(transform_tab, '_last_performance_warning')

def test_tooltip_consistency(transform_tab):
    """Test consistency of tooltips and status messages."""
    # Check mode indicator tooltip format
    assert "Translation Mode:" in transform_tab.mode_indicator.toolTip()
    assert "(Space/Enter to change mode)" in transform_tab.mode_indicator.toolTip()
    
    # Check status message format
    assert "Absolute Mode" in transform_tab.mode_status.text()
    assert "Active Axes" in transform_tab._get_active_axes_text()
    
    # Check status tooltip format
    status_tooltip = transform_tab.mode_status.toolTip()
    assert status_tooltip.startswith("Current Mode:")
    assert "Active Axes:" in transform_tab._get_full_axes_text()

def test_accessibility_labels(transform_tab):
    """Test accessibility labels and descriptions."""
    assert transform_tab.mode_indicator.accessibleName() == "Transform Mode Indicator"
    assert "current transform mode" in transform_tab.mode_indicator.accessibleDescription().lower()
    
    # Test focus handling
    transform_tab.mode_indicator.setFocus()
    assert transform_tab.mode_indicator.hasFocus()
    assert not transform_tab.mode_label.hasFocus()
    assert not transform_tab.mode_status.hasFocus()

def test_status_text_truncation(transform_tab):
    """Test truncation of status text for multiple axes."""
    # Simulate multiple active axes
    transform_tab._active_axes = {
        'x': None, 'y': None, 'z': None, 'w': None
    }
    
    # Check truncation
    status_text = transform_tab._get_active_axes_text()
    assert "..." in status_text
    assert len(status_text.split(",")) <= transform_tab.MAX_STATUS_AXES
    
    # Check full text in tooltip
    full_text = transform_tab._get_full_axes_text()
    assert "..." not in full_text
    assert all(axis in full_text for axis in ['X', 'Y', 'Z', 'W'])

def test_visual_feedback(transform_tab, qtbot):
    """Test visual feedback during interactions."""
    # Test focus visual feedback
    transform_tab.mode_indicator.setFocus()
    style = transform_tab.mode_indicator.styleSheet()
    assert "QFrame:focus" in style
    assert "background-color" in style
    
    # Test mode change visual feedback
    with qtbot.waitSignal(transform_tab.mode_transition_completed):
        transform_tab._set_transform_mode('rotate')
    assert "#4CAF50" in transform_tab.mode_indicator.styleSheet()  # Green for rotate
    
    with qtbot.waitSignal(transform_tab.mode_transition_completed):
        transform_tab._set_transform_mode('scale')
    assert "#FF9800" in transform_tab.mode_indicator.styleSheet()  # Orange for scale

def test_performance_monitoring(transform_tab, qtbot):
    """Test performance monitoring and warnings."""
    # Mock a slow transition
    def slow_transition():
        time.sleep(0.6)  # Longer than PERFORMANCE_THRESHOLD
    
    # Replace animation with slow mock
    transform_tab._animate_mode_transition = slow_transition
    
    # Monitor for performance warning
    with qtbot.waitSignal(transform_tab.performance_warning) as blocker:
        transform_tab._set_transform_mode('rotate')
    
    # Verify warning was emitted
    assert "Slow mode transition" in blocker.args[0]
    assert "ms" in blocker.args[0] 