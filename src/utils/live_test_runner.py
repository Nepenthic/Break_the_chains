import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np

from .live_test_monitor import LiveTestMonitor
from .performance_visualizer import PerformanceVisualizer

class LiveTestRunner:
    """Runner for executing and monitoring the live test."""

    def __init__(self):
        """Initialize the test runner with monitoring."""
        self.monitor = LiveTestMonitor()
        self.visualizer = PerformanceVisualizer()
        self.test_data = self._generate_test_data()
        
    def _generate_test_data(self) -> Dict[str, np.ndarray]:
        """Generate test datasets of various sizes."""
        return {
            'tiny': np.random.rand(3, 2),
            'small': np.random.rand(100, 2),
            'medium': np.random.rand(10000, 2),
            'large': np.random.rand(100000, 2),
            'extreme': np.random.rand(1000000, 2),
            'sparse': np.array([[0, 0], [1000, 1000], [-1000, -1000]])
        }
        
    def run_safari_tests(self) -> None:
        """Run Safari-specific tests with monitoring."""
        self.monitor.loggers['browser_compatibility'].info(
            "Starting Safari WebGL compatibility tests"
        )
        
        try:
            for dataset_name, data in self.test_data.items():
                # Test WebGL rendering
                start_time = time.time()
                self.visualizer.render(data)
                render_time = time.time() - start_time
                
                # Log metrics
                self.monitor.log_render_time(render_time, len(data))
                
                # Test export functionality
                self._test_export(dataset_name, data)
                
        except Exception as e:
            self.monitor.log_error(
                f"Safari test failed: {str(e)}",
                exc_info=e
            )
            
    def run_edge_tests(self) -> None:
        """Run Edge-specific tests with monitoring."""
        self.monitor.loggers['browser_compatibility'].info(
            "Starting Edge touch event tests"
        )
        
        try:
            # Test touch events
            touch_events = [
                {'type': 'touchstart', 'x': 100, 'y': 100},
                {'type': 'touchmove', 'x': 150, 'y': 150},
                {'type': 'touchend', 'x': 200, 'y': 200}
            ]
            
            for event in touch_events:
                start_time = time.time()
                self.visualizer.handle_touch_event(event)
                interaction_time = time.time() - start_time
                self.monitor.log_interaction_time(event['type'], interaction_time)
                
            # Test gesture events
            gesture_events = [
                {'type': 'gesturestart', 'scale': 1.0},
                {'type': 'gesturechange', 'scale': 1.5},
                {'type': 'gestureend', 'scale': 2.0}
            ]
            
            for event in gesture_events:
                start_time = time.time()
                self.visualizer.handle_gesture_event(event)
                interaction_time = time.time() - start_time
                self.monitor.log_interaction_time(event['type'], interaction_time)
                
        except Exception as e:
            self.monitor.log_error(
                f"Edge test failed: {str(e)}",
                exc_info=e
            )
            
    def _test_export(self, dataset_name: str, data: np.ndarray) -> None:
        """Test export functionality with monitoring."""
        try:
            filename = f"test_export_{dataset_name}.json"
            start_time = time.time()
            self.visualizer.export_data(data, filename)
            export_time = time.time() - start_time
            
            self.monitor.loggers['performance_metrics'].info(
                f"Export time for {dataset_name}: {export_time:.3f}s"
            )
            
        except Exception as e:
            self.monitor.log_error(
                f"Export failed for {dataset_name}: {str(e)}",
                exc_info=e
            )
            
    def run_all_tests(self) -> None:
        """Run all tests with monitoring."""
        self.monitor.start_monitoring()
        
        try:
            # Run Safari tests
            self.run_safari_tests()
            
            # Run Edge tests
            self.run_edge_tests()
            
        finally:
            self.monitor.stop_monitoring()
            
def main():
    """Main entry point for running live tests."""
    runner = LiveTestRunner()
    
    try:
        runner.run_all_tests()
        
    except Exception as e:
        print(f"Live test failed: {str(e)}", file=sys.stderr)
        sys.exit(1)
        
if __name__ == '__main__':
    main() 