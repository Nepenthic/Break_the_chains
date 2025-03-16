import unittest
import json
import os
from datetime import datetime
import numpy as np
import psutil
import platform
import GPUtil
from dataclasses import dataclass
from typing import Dict, List, Optional
from .test_transform_performance import TestTransformPerformance
from ..utils.logging import TransformLogger
from ..utils.visualization import PerformanceVisualizer

@dataclass
class HardwareProfile:
    """Hardware profile information and capabilities."""
    cpu_cores: int
    cpu_threads: int
    ram_total_gb: float
    ram_available_gb: float
    gpu_name: Optional[str]
    gpu_memory_gb: Optional[float]
    platform: str
    
    def calculate_performance_tier(self) -> str:
        """Determine hardware performance tier based on specifications."""
        score = 0
        
        # CPU scoring
        if self.cpu_cores >= 8:
            score += 3
        elif self.cpu_cores >= 4:
            score += 2
        else:
            score += 1
            
        # RAM scoring
        if self.ram_total_gb >= 16:
            score += 3
        elif self.ram_total_gb >= 8:
            score += 2
        else:
            score += 1
            
        # GPU scoring
        if self.gpu_memory_gb:
            if self.gpu_memory_gb >= 8:
                score += 3
            elif self.gpu_memory_gb >= 4:
                score += 2
            else:
                score += 1
        
        # Determine tier
        if score >= 7:
            return "high-end"
        elif score >= 4:
            return "mid-range"
        else:
            return "low-end"
    
    def get_adaptive_thresholds(self) -> Dict[str, float]:
        """Calculate adaptive performance thresholds based on hardware capabilities."""
        tier = self.calculate_performance_tier()
        base_thresholds = {
            'single_transform_ms': 50,  # Base threshold for single transform
            'bulk_transform_ms': 1000,  # Base threshold for 100 shapes
            'complex_mesh_ms': 100,     # Base threshold for 100K vertices
            'ui_frame_ms': 16.7,        # Target 60fps
            'memory_increase_mb': 50,   # Max memory increase per operation
        }
        
        # Adjust thresholds based on tier
        multipliers = {
            'high-end': 0.5,    # Expect better performance
            'mid-range': 1.0,   # Base thresholds
            'low-end': 2.0      # Allow more time
        }
        
        return {k: v * multipliers[tier] for k, v in base_thresholds.items()}

class HardwareProfiler:
    """Detects and manages hardware capabilities for performance testing."""
    
    def __init__(self):
        self.logger = TransformLogger('hardware_profiler.log')
    
    def detect_hardware_profile(self) -> HardwareProfile:
        """Detect current hardware capabilities."""
        try:
            # CPU information
            cpu_cores = psutil.cpu_count(logical=False)
            cpu_threads = psutil.cpu_count(logical=True)
            
            # Memory information
            memory = psutil.virtual_memory()
            ram_total_gb = memory.total / (1024**3)
            ram_available_gb = memory.available / (1024**3)
            
            # GPU information
            gpu_name = None
            gpu_memory_gb = None
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]  # Use primary GPU
                    gpu_name = gpu.name
                    gpu_memory_gb = gpu.memoryTotal / 1024
            except Exception as e:
                self.logger.warning(f"GPU detection failed: {e}")
            
            profile = HardwareProfile(
                cpu_cores=cpu_cores,
                cpu_threads=cpu_threads,
                ram_total_gb=ram_total_gb,
                ram_available_gb=ram_available_gb,
                gpu_name=gpu_name,
                gpu_memory_gb=gpu_memory_gb,
                platform=platform.platform()
            )
            
            self.logger.info(
                "Hardware profile detected",
                extra={
                    'profile': profile.__dict__,
                    'performance_tier': profile.calculate_performance_tier(),
                    'thresholds': profile.get_adaptive_thresholds()
                }
            )
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Hardware detection failed: {e}")
            raise

class PerformanceTestRunner:
    """Runs performance tests and generates reports with hardware-aware thresholds."""
    
    def __init__(self):
        self.logger = TransformLogger('performance_test_runner.log')
        self.visualizer = PerformanceVisualizer()
        self.results = {}
        self.metrics = {}
        self.hardware_profiler = HardwareProfiler()
        
        # Detect hardware profile and set thresholds
        self.hardware_profile = self.hardware_profiler.detect_hardware_profile()
        self.thresholds = self.hardware_profile.get_adaptive_thresholds()
        
        # Ensure reports directory exists
        os.makedirs('reports', exist_ok=True)
        
    def run_tests(self):
        """Run all performance tests with hardware-aware thresholds."""
        self.logger.info(
            "Starting performance test suite",
            extra={
                'hardware_profile': self.hardware_profile.__dict__,
                'thresholds': self.thresholds
            }
        )
        
        # Create test suite with hardware-aware thresholds
        test_loader = unittest.TestLoader()
        suite = test_loader.loadTestsFromTestCase(TestTransformPerformance)
        
        # Inject hardware profile and thresholds into test cases
        for test in suite:
            test.hardware_profile = self.hardware_profile
            test.thresholds = self.thresholds
        
        # Run tests and collect metrics
        runner = unittest.TextTestRunner(verbosity=2)
        test_result = runner.run(suite)
        
        # Process results
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests_run': test_result.testsRun,
            'failures': len(test_result.failures),
            'errors': len(test_result.errors),
            'skipped': len(test_result.skipped),
            'was_successful': test_result.wasSuccessful(),
            'hardware_profile': self.hardware_profile.__dict__,
            'thresholds': self.thresholds
        }
        
        # Collect metrics from test cases
        self._collect_metrics(test_result)
        
        self.logger.info(
            "Test suite completed",
            extra={
                'results': self.results,
                'metrics': self.metrics
            }
        )
        
        return self.results
    
    def _collect_metrics(self, test_result):
        """Collect metrics from test cases."""
        # Extract metrics from test cases
        for test_case in test_result.collectedTests:
            if hasattr(test_case, 'metrics_collector'):
                metrics = test_case.metrics_collector.metrics
                
                # Process batch transform metrics
                batch_metrics = [m for m in metrics if 'batch_transform' in m['operation']]
                if batch_metrics:
                    shape_counts = []
                    durations = []
                    memory_usage = []
                    
                    for metric in batch_metrics:
                        if metric['shape_count']:
                            shape_counts.append(metric['shape_count'])
                            durations.append(metric['duration'] * 1000)  # Convert to ms
                            memory_usage.append(metric['memory_used'] / (1024 * 1024))  # Convert to MB
                    
                    if shape_counts:
                        self.metrics['batch_transform'] = {
                            'shape_counts': shape_counts,
                            'durations': durations,
                            'memory_usage': memory_usage
                        }
                
                # Process complex mesh metrics
                complex_metrics = [m for m in metrics if 'complex_mesh' in m['operation']]
                if complex_metrics:
                    vertex_counts = []
                    durations = []
                    memory_usage = []
                    
                    for metric in complex_metrics:
                        if metric['vertex_count']:
                            vertex_counts.append(metric['vertex_count'])
                            durations.append(metric['duration'] * 1000)  # Convert to ms
                            memory_usage.append(metric['memory_used'] / (1024 * 1024))  # Convert to MB
                    
                    if vertex_counts:
                        self.metrics['complex_mesh'] = {
                            'vertex_counts': vertex_counts,
                            'durations': durations,
                            'memory_usage': memory_usage
                        }
    
    def generate_report(self):
        """Generate a detailed performance report with visualizations."""
        if not self.results:
            self.logger.error("No test results available")
            return
        
        # Create report filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'reports/performance_report_{timestamp}.json'
        
        # Generate visualizations
        image_files = []
        
        # Batch transform visualizations
        if 'batch_transform' in self.metrics:
            metrics = self.metrics['batch_transform']
            
            # Duration line plot
            duration_plot = self.visualizer.plot_transform_durations(
                metrics['shape_counts'],
                metrics['durations'],
                'batch'
            )
            image_files.append(duration_plot)
            
            # Memory usage bar plot
            memory_plot = self.visualizer.plot_memory_usage(
                metrics['shape_counts'],
                metrics['memory_usage'],
                'batch'
            )
            image_files.append(memory_plot)
            
            # Performance scatter plot
            scatter_plot = self.visualizer.plot_performance_scatter(
                metrics['shape_counts'],
                metrics['durations'],
                'Shape Count',
                'Duration (ms)',
                'Transform Performance Scaling'
            )
            image_files.append(scatter_plot)
        
        # Complex mesh visualizations
        if 'complex_mesh' in self.metrics:
            metrics = self.metrics['complex_mesh']
            
            # Duration line plot
            duration_plot = self.visualizer.plot_transform_durations(
                metrics['vertex_counts'],
                metrics['durations'],
                'complex'
            )
            image_files.append(duration_plot)
            
            # Memory usage bar plot
            memory_plot = self.visualizer.plot_memory_usage(
                metrics['vertex_counts'],
                metrics['memory_usage'],
                'complex'
            )
            image_files.append(memory_plot)
        
        # Add performance metrics to report data
        report_data = {
            'test_results': self.results,
            'performance_metrics': self.metrics,
            'system_info': self._get_system_info(),
            'recommendations': self._generate_recommendations()
        }
        
        # Write JSON report
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        # Generate HTML report
        html_file = self.visualizer.generate_html_report(report_data, image_files)
        
        self.logger.info(
            f"Performance report and visualizations generated",
            extra={
                'report_file': report_file,
                'html_file': html_file,
                'image_files': image_files
            }
        )
        
        return report_file, html_file
    
    def _get_system_info(self):
        """Gather system information for the report."""
        import platform
        import psutil
        
        return {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'cpu_count': psutil.cpu_count(),
            'python_version': platform.python_version()
        }
    
    def _generate_recommendations(self):
        """Generate performance improvement recommendations."""
        recommendations = []
        
        # Test failure recommendations
        if self.results.get('failures', 0) > 0:
            recommendations.append({
                'priority': 'high',
                'message': 'Address failed performance tests',
                'details': 'Some performance tests failed to meet their targets'
            })
        
        # Memory usage recommendations
        memory_available = psutil.virtual_memory().available
        if memory_available < 1024 * 1024 * 1024:  # Less than 1GB available
            recommendations.append({
                'priority': 'medium',
                'message': 'Consider memory optimization',
                'details': 'System is running low on available memory'
            })
        
        # Performance scaling recommendations
        if 'batch_transform' in self.metrics:
            durations = self.metrics['batch_transform']['durations']
            shape_counts = self.metrics['batch_transform']['shape_counts']
            
            # Calculate performance scaling factor
            if len(durations) > 1 and len(shape_counts) > 1:
                scaling_factor = np.polyfit(
                    np.log(shape_counts), 
                    np.log(durations), 
                    1
                )[0]
                
                if scaling_factor > 1.2:  # Super-linear scaling
                    recommendations.append({
                        'priority': 'medium',
                        'message': 'Performance scaling needs improvement',
                        'details': f'Transform operations are scaling super-linearly (factor: {scaling_factor:.2f})'
                    })
        
        return recommendations

def main():
    """Main entry point for running performance tests."""
    runner = PerformanceTestRunner()
    
    try:
        # Run tests
        results = runner.run_tests()
        
        # Generate report and visualizations
        report_file, html_file = runner.generate_report()
        
        print(f"\nTest Results:")
        print(f"Tests Run: {results['tests_run']}")
        print(f"Failures: {results['failures']}")
        print(f"Errors: {results['errors']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Success: {results['was_successful']}")
        print(f"\nReports generated:")
        print(f"- JSON: {report_file}")
        print(f"- HTML: {html_file}")
        
    except Exception as e:
        runner.logger.error(
            "Error running performance tests",
            extra={
                'error': str(e)
            }
        )
        raise

if __name__ == '__main__':
    main() 