import unittest
import json
import os
from datetime import datetime
import numpy as np
from .test_transform_performance import TestTransformPerformance
from ..utils.logging import TransformLogger
from ..utils.visualization import PerformanceVisualizer

class PerformanceTestRunner:
    """Runs performance tests and generates reports."""
    
    def __init__(self):
        self.logger = TransformLogger('performance_test_runner.log')
        self.visualizer = PerformanceVisualizer()
        self.results = {}
        self.metrics = {}
        
        # Ensure reports directory exists
        os.makedirs('reports', exist_ok=True)
    
    def run_tests(self):
        """Run all performance tests."""
        self.logger.info("Starting performance test suite")
        
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTransformPerformance)
        
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
            'was_successful': test_result.wasSuccessful()
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