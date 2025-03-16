import pytest
from PyQt6.QtWidgets import QApplication
import sys
import numpy as np
from src.core.shapes_3d import Shape
from src.utils.hardware_profile import HardwareProfile
from src.utils.state_management import PerformanceMetrics

class MockShape(Shape):
    def __init__(self, shape_id="test_shape"):
        super().__init__()
        self.id = shape_id

@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    app.quit()

@pytest.fixture
def viewport(app):
    from src.tests.test_viewport import TestViewport
    return TestViewport()

@pytest.fixture
def performance_metrics(viewport):
    return PerformanceMetrics(viewport)

def test_performance_thresholds(viewport, performance_metrics):
    """Test hardware-specific performance thresholds."""
    # Add a test shape
    shape = MockShape()
    viewport.addShape(shape)
    
    # Get hardware profile
    profile = HardwareProfile.detect()
    thresholds = profile.get_performance_thresholds()
    
    # Test frame time tracking
    for _ in range(10):
        performance_metrics.update_frame_time(16.7)  # 60 FPS
    
    metrics = performance_metrics.get_metrics()
    assert 'frame_time_avg' in metrics
    assert metrics['frame_time_avg'] <= thresholds['frame_time_threshold']
    
    # Test memory usage tracking
    performance_metrics.update_memory_usage(500)  # 500MB
    metrics = performance_metrics.get_metrics()
    assert 'memory_usage_mb' in metrics
    assert metrics['memory_usage_mb'] <= thresholds['memory_threshold_mb']
    
    # Test operation time tracking
    performance_metrics.record_operation_time('transform', 0.05)
    metrics = performance_metrics.get_metrics()
    assert 'operation_times' in metrics
    assert 'transform' in metrics['operation_times']
    assert metrics['operation_times']['transform'] <= thresholds['operation_time_threshold']