import unittest
import json
import os
from datetime import datetime
from .test_transform_performance import TestTransformPerformance
from ..utils.logging import TransformLogger

class PerformanceTestRunner:
    """Runs performance tests and generates reports."""
    
    def __init__(self):
        self.logger = TransformLogger('performance_test_runner.log')
        self.results = {}
        
        # Ensure reports directory exists
        os.makedirs('reports', exist_ok=True)
    
    def run_tests(self):
        """Run all performance tests."""
        self.logger.info("Starting performance test suite")
        
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTransformPerformance)
        
        # Run tests
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
        
        self.logger.info(
            "Test suite completed",
            extra={
                'results': self.results
            }
        )
        
        return self.results
    
    def generate_report(self):
        """Generate a detailed performance report."""
        if not self.results:
            self.logger.error("No test results available")
            return
        
        # Create report filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'reports/performance_report_{timestamp}.json'
        
        # Add performance metrics from test runs
        report_data = {
            'test_results': self.results,
            'system_info': self._get_system_info(),
            'recommendations': self._generate_recommendations()
        }
        
        # Write report to file
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(
            f"Performance report generated",
            extra={
                'report_file': report_file
            }
        )
        
        return report_file
    
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
        
        if self.results.get('failures', 0) > 0:
            recommendations.append({
                'priority': 'high',
                'message': 'Address failed performance tests',
                'details': 'Some performance tests failed to meet their targets'
            })
        
        # Add memory usage recommendations
        memory_available = psutil.virtual_memory().available
        if memory_available < 1024 * 1024 * 1024:  # Less than 1GB available
            recommendations.append({
                'priority': 'medium',
                'message': 'Consider memory optimization',
                'details': 'System is running low on available memory'
            })
        
        return recommendations

def main():
    """Main entry point for running performance tests."""
    runner = PerformanceTestRunner()
    
    try:
        # Run tests
        results = runner.run_tests()
        
        # Generate report
        report_file = runner.generate_report()
        
        print(f"\nTest Results:")
        print(f"Tests Run: {results['tests_run']}")
        print(f"Failures: {results['failures']}")
        print(f"Errors: {results['errors']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Success: {results['was_successful']}")
        print(f"\nReport generated: {report_file}")
        
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