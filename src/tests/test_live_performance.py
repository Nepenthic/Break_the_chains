import pytest
import time
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from src.utils.hardware_profile import HardwareProfile
from src.utils.state_management import PerformanceMetrics
from src.viewport import Viewport
from src.transform_tab import TransformTab

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LiveTestRunner:
    """Runs comprehensive performance tests across different hardware configurations."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the test runner with optional configuration."""
        self.config = config or {}
        self.hardware_profile = HardwareProfile.detect()
        self.performance_metrics = PerformanceMetrics()
        self.results: Dict = {}
        
        # Test configuration
        self.num_shapes = self.config.get('num_shapes', 100)
        self.num_transforms = self.config.get('num_transforms', 50)
        self.batch_size = self._determine_batch_size()
        self.test_duration = self.config.get('test_duration', 60)  # seconds
        
        # Progress tracking
        self.test_phase = "initialization"
        self.progress = 0.0
        
        # Initialize Qt application
        self.app = QApplication([])
        self.viewport = Viewport()
        self.transform_tab = TransformTab()
        
        # Connect signals
        self.transform_tab.transformApplied.connect(self._on_transform_applied)
        self.viewport.viewportUpdated.connect(self._on_viewport_updated)
        
        # Setup performance monitoring
        self.frame_times: List[float] = []
        self.operation_times: List[float] = []
        self.memory_usage: List[float] = []
        self.error_count = 0
        self.warning_count = 0
        
        # Timer for periodic measurements
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_metrics)
        self.monitor_timer.start(1000)  # Collect metrics every second
        
        # Log initialization
        logger.info("LiveTestRunner initialized", extra={
            'hardware_tier': self.hardware_profile.tier,
            'batch_size': self.batch_size,
            'test_config': self.config
        })
    
    def _update_progress(self, phase: str, progress: float):
        """Update test progress and log status."""
        self.test_phase = phase
        self.progress = progress
        logger.info(f"Test progress: {phase}", extra={
            'phase': phase,
            'progress': f"{progress:.1f}%",
            'error_count': self.error_count,
            'warning_count': self.warning_count
        })
    
    def _determine_batch_size(self) -> int:
        """Determine appropriate batch size based on hardware tier."""
        if self.config.get('batch_size'):
            return self.config['batch_size']
            
        tier = self.hardware_profile.tier
        if tier == 'low-end':
            return 25
        elif tier == 'mid-range':
            return 50
        else:
            return 100
    
    def _collect_metrics(self):
        """Collect current performance metrics with error tracking."""
        try:
            metrics = self.performance_metrics.get_current_metrics()
            self.frame_times.append(metrics['frame_time'])
            self.memory_usage.append(metrics['memory_usage'])
            
            # Check for concerning metrics
            if metrics['frame_time'] > self.hardware_profile.get_performance_thresholds()['frame_time_threshold'] * 1.5:
                self.warning_count += 1
                logger.warning("High frame time detected", extra={
                    'frame_time': metrics['frame_time'],
                    'threshold': self.hardware_profile.get_performance_thresholds()['frame_time_threshold']
                })
            
            if metrics['memory_usage'] > self.hardware_profile.get_performance_thresholds()['memory_threshold_mb'] * 0.9:
                self.warning_count += 1
                logger.warning("Memory usage approaching threshold", extra={
                    'memory_usage': metrics['memory_usage'],
                    'threshold': self.hardware_profile.get_performance_thresholds()['memory_threshold_mb']
                })
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error collecting metrics: {str(e)}", exc_info=True)
    
    def _on_transform_applied(self, mode: str, values: Dict):
        """Handle transform application events."""
        start_time = time.time()
        # Process transform
        self.viewport.update()
        end_time = time.time()
        self.operation_times.append(end_time - start_time)
    
    def _on_viewport_updated(self):
        """Handle viewport update events."""
        self.performance_metrics.record_frame()
    
    def _validate_performance(self) -> Dict:
        """Validate performance metrics against thresholds."""
        thresholds = self.hardware_profile.get_performance_thresholds()
        
        validation = {
            'frame_time': {
                'mean': float(np.mean(self.frame_times)),
                'p95': float(np.percentile(self.frame_times, 95)),
                'threshold': float(thresholds['frame_time_threshold']),
                'passed': True
            },
            'memory': {
                'mean': float(np.mean(self.memory_usage)),
                'peak': float(np.max(self.memory_usage)),
                'p95': float(np.percentile(self.memory_usage, 95)),
                'threshold': float(thresholds['memory_threshold_mb']),
                'passed': True
            },
            'operations': {
                'mean': float(np.mean(self.operation_times)),
                'p95': float(np.percentile(self.operation_times, 95)),
                'threshold': float(thresholds['operation_time_threshold']),
                'passed': True
            }
        }
        
        # Check if metrics are within thresholds
        validation['frame_time']['passed'] = bool(
            validation['frame_time']['p95'] <= thresholds['frame_time_threshold']
        )
        validation['memory']['passed'] = bool(
            validation['memory']['peak'] <= thresholds['memory_threshold_mb']
        )
        validation['operations']['passed'] = bool(
            validation['operations']['p95'] <= thresholds['operation_time_threshold']
        )
        
        return validation
    
    def run_test_sequence(self):
        """Execute the full test sequence with progress tracking."""
        logger.info("Starting live test sequence", extra={
            'hardware_profile': self.hardware_profile.__dict__,
            'test_config': self.config
        })
        
        try:
            # 1. Add shapes in batches
            self._update_progress("adding_shapes", 0.0)
            start_time = time.time()
            shapes_added = 0
            while shapes_added < self.num_shapes:
                batch = min(self.batch_size, self.num_shapes - shapes_added)
                for _ in range(batch):
                    try:
                        self.viewport.add_shape()
                        shapes_added += 1
                    except Exception as e:
                        self.error_count += 1
                        logger.error(f"Error adding shape: {str(e)}", exc_info=True)
                        
                progress = (shapes_added / self.num_shapes) * 30  # 30% of total progress
                self._update_progress("adding_shapes", progress)
                self.app.processEvents()
            
            # 2. Apply transforms
            self._update_progress("applying_transforms", 30.0)
            transforms_applied = 0
            for _ in range(self.num_transforms):
                try:
                    self.transform_tab.apply_transform('rotate', {'angle': 45})
                    transforms_applied += 1
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error applying transform: {str(e)}", exc_info=True)
                
                progress = 30 + (transforms_applied / self.num_transforms) * 30  # 30-60% progress
                self._update_progress("applying_transforms", progress)
                self.app.processEvents()
            
            # 3. Run test loop
            self._update_progress("running_test_loop", 60.0)
            end_time = start_time + self.test_duration
            while time.time() < end_time:
                try:
                    self.app.processEvents()
                    progress = 60 + ((time.time() - start_time) / self.test_duration) * 30  # 60-90% progress
                    self._update_progress("running_test_loop", progress)
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error in test loop: {str(e)}", exc_info=True)
            
            # 4. Validate and collect results
            self._update_progress("validating_results", 90.0)
            validation = self._validate_performance()
            
            # Convert hardware profile info to serializable format
            hardware_info = {
                'tier': str(self.hardware_profile.tier),
                'cpu_info': {k: str(v) for k, v in self.hardware_profile.cpu_info.items()},
                'memory_info': {k: str(v) for k, v in self.hardware_profile.memory_info.items()},
                'os_info': {k: str(v) for k, v in self.hardware_profile.os_info.items()}
            }
            
            self.results = {
                'hardware_profile': hardware_info,
                'test_config': {k: str(v) for k, v in self.config.items()},
                'performance': validation,
                'recommendations': [str(r) for r in self.hardware_profile.get_performance_thresholds()['recommendations']],
                'test_summary': {
                    'error_count': int(self.error_count),
                    'warning_count': int(self.warning_count),
                    'shapes_added': int(shapes_added),
                    'transforms_applied': int(transforms_applied),
                    'test_duration': float(self.test_duration)
                }
            }
            
            # 5. Save results
            self._update_progress("saving_results", 95.0)
            self._save_results()
            
            # 6. Log summary
            self._update_progress("completed", 100.0)
            logger.info("Test sequence completed", extra={
                'validation': validation,
                'passed_all': all(v['passed'] for v in validation.values()),
                'error_count': self.error_count,
                'warning_count': self.warning_count
            })
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Test sequence failed: {str(e)}", exc_info=True)
            raise
        
        finally:
            self.monitor_timer.stop()
            self.app.quit()
    
    def _save_results(self):
        """Save test results to file with error summary."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = Path('test_results')
        results_dir.mkdir(exist_ok=True)
        
        # Save detailed results
        result_file = results_dir / f'live_test_{timestamp}.json'
        with open(result_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save summary for quick reference
        summary_file = results_dir / f'live_test_{timestamp}_summary.txt'
        with open(summary_file, 'w') as f:
            f.write(f"Live Test Summary ({timestamp})\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Hardware Tier: {self.hardware_profile.tier}\n")
            f.write(f"Test Duration: {self.test_duration}s\n")
            f.write(f"Errors: {self.error_count}\n")
            f.write(f"Warnings: {self.warning_count}\n\n")
            
            f.write("Performance Summary:\n")
            for metric, data in self.results['performance'].items():
                f.write(f"{metric}:\n")
                f.write(f"  Mean: {data['mean']:.2f}\n")
                f.write(f"  P95: {data['p95']:.2f}\n")
                f.write(f"  Threshold: {data['threshold']:.2f}\n")
                f.write(f"  Passed: {data['passed']}\n\n")
            
            if self.results['recommendations']:
                f.write("\nRecommendations:\n")
                for rec in self.results['recommendations']:
                    f.write(f"- {rec}\n")
        
        logger.info("Test results saved", extra={
            'result_file': str(result_file),
            'summary_file': str(summary_file)
        })

def main():
    """Main entry point for running live tests."""
    parser = argparse.ArgumentParser(description='Run live performance tests')
    parser.add_argument('--num-shapes', type=int, default=100,
                      help='Number of shapes to create')
    parser.add_argument('--num-transforms', type=int, default=50,
                      help='Number of transforms to apply')
    parser.add_argument('--batch-size', type=int,
                      help='Override automatic batch size')
    parser.add_argument('--test-duration', type=int, default=60,
                      help='Test duration in seconds')
    
    args = parser.parse_args()
    config = vars(args)
    
    runner = LiveTestRunner(config)
    runner.run_test_sequence()

if __name__ == '__main__':
    main()

# Pytest functions for automated testing
def test_live_performance():
    """Run live performance test and validate results."""
    runner = LiveTestRunner()
    runner.run_test_sequence()
    
    # Assert all performance validations passed
    assert all(v['passed'] for v in runner.results['performance'].values()), \
        "Performance validation failed"
    
    # Check specific metrics
    performance = runner.results['performance']
    
    # Frame time validation
    assert performance['frame_time']['p95'] <= runner.hardware_profile.get_performance_thresholds()['frame_time_threshold'], \
        f"Frame time P95 ({performance['frame_time']['p95']:.1f}ms) exceeds threshold"
    
    # Memory validation
    assert performance['memory']['peak'] <= runner.hardware_profile.get_performance_thresholds()['memory_threshold_mb'], \
        f"Peak memory usage ({performance['memory']['peak']:.1f}MB) exceeds threshold"
    
    # Operation time validation
    assert performance['operations']['p95'] <= runner.hardware_profile.get_performance_thresholds()['operation_time_threshold'], \
        f"Operation time P95 ({performance['operations']['p95']:.1f}s) exceeds threshold" 