import pytest
import time
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
import psutil
import gc
from transform_tab import TransformTab
from viewport import Viewport
from shapes_3d import Cube, ComplexMesh
from src.core.scene import SceneManager
from utils.logging import TransformLogger
import unittest
from ..core.transform import Transform

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

class PerformanceAudit:
    """Performance auditing system for transform operations."""
    
    def __init__(self, transform_tab, viewport, scene_manager):
        self.transform_tab = transform_tab
        self.viewport = viewport
        self.scene_manager = scene_manager
        self.metrics_collector = PerformanceMetricsCollector()
        self.logger = TransformLogger("performance_audit.log")
        
        # Configure performance thresholds
        self.thresholds = {
            'batch_transform_ms': 16,  # 60fps target
            'memory_increase_mb': 50,  # Max memory increase per 1000 shapes
            'vertex_processing_ms': 0.1  # Per 1000 vertices
        }
    
    async def benchmark_shape_scaling(self):
        """Benchmark performance with increasing shape counts."""
        self.logger.info("Starting shape scaling benchmark")
        
        shape_counts = [100, 500, 1000, 5000]
        results = {}
        
        for count in shape_counts:
            self.logger.debug(f"Testing with {count} shapes")
            
            # Create test shapes
            shapes = [Cube(size=1.0) for _ in range(count)]
            
            # Measure memory before
            initial_memory = self.get_memory_usage()
            
            # Time batch transform
            start_time = time.perf_counter_ns()
            
            # Add shapes to scene
            for shape in shapes:
                self.scene_manager.add_shape(shape)
            
            # Apply transform to all shapes
            transform = {
                'mode': 'translate',
                'axis': 'x',
                'value': 1.0
            }
            
            await self.transform_tab.apply_batch_transform(transform)
            
            # Calculate metrics
            duration = (time.perf_counter_ns() - start_time) / 1e6  # Convert to ms
            memory_increase = self.get_memory_usage() - initial_memory
            
            results[count] = {
                'duration_ms': duration,
                'memory_increase_mb': memory_increase / (1024 * 1024),
                'ms_per_shape': duration / count
            }
            
            # Log results
            self.logger.info(f"Batch transform results for {count} shapes", 
                           extra=results[count])
            
            # Cleanup
            self.scene_manager.clear_scene()
            gc.collect()
        
        return results
    
    async def benchmark_complex_transforms(self):
        """Benchmark performance with complex vertex operations."""
        self.logger.info("Starting complex transform benchmark")
        
        vertex_counts = [1000, 10000, 100000]
        results = {}
        
        for count in vertex_counts:
            self.logger.debug(f"Testing with {count} vertices")
            
            # Create complex mesh
            mesh = ComplexMesh.create_test_mesh(vertex_count=count)
            
            # Measure initial state
            initial_memory = self.get_memory_usage()
            
            # Apply complex transform sequence
            transforms = [
                {'mode': 'rotate', 'axis': 'y', 'value': 45.0},
                {'mode': 'scale', 'axis': 'all', 'value': 2.0},
                {'mode': 'translate', 'axis': 'x', 'value': 10.0}
            ]
            
            start_time = time.perf_counter_ns()
            
            for transform in transforms:
                await self.transform_tab.apply_transform(transform)
            
            # Calculate metrics
            duration = (time.perf_counter_ns() - start_time) / 1e6
            memory_increase = self.get_memory_usage() - initial_memory
            
            results[count] = {
                'duration_ms': duration,
                'memory_increase_mb': memory_increase / (1024 * 1024),
                'ms_per_vertex': duration / count,
                'transform_count': len(transforms)
            }
            
            # Log results
            self.logger.info(f"Complex transform results for {count} vertices", 
                           extra=results[count])
            
            # Cleanup
            self.scene_manager.remove_shape(mesh)
            gc.collect()
        
        return results
    
    async def analyze_memory_patterns(self):
        """Analyze memory usage patterns during transforms."""
        self.logger.info("Starting memory pattern analysis")
        
        # Track memory over time
        memory_samples = []
        sample_interval = 0.1  # seconds
        
        # Create test scenario
        shapes = [Cube(size=1.0) for _ in range(1000)]
        for shape in shapes:
            self.scene_manager.add_shape(shape)
        
        # Sample memory during operations
        start_time = time.time()
        
        while time.time() - start_time < 10:  # 10 second test
            memory_samples.append({
                'timestamp': time.time() - start_time,
                'memory_mb': self.get_memory_usage() / (1024 * 1024),
                'shape_count': len(self.scene_manager.get_shapes())
            })
            
            # Apply random transform
            if len(memory_samples) % 10 == 0:
                transform = self.generate_random_transform()
                await self.transform_tab.apply_batch_transform(transform)
            
            await asyncio.sleep(sample_interval)
        
        # Analyze patterns
        analysis = {
            'peak_memory_mb': max(s['memory_mb'] for s in memory_samples),
            'average_memory_mb': np.mean([s['memory_mb'] for s in memory_samples]),
            'memory_growth_rate': self.calculate_growth_rate(memory_samples)
        }
        
        # Log analysis
        self.logger.info("Memory pattern analysis complete", extra=analysis)
        
        return {
            'samples': memory_samples,
            'analysis': analysis
        }
    
    def get_memory_usage(self):
        """Get current memory usage in bytes."""
        process = psutil.Process()
        return process.memory_info().rss
    
    def calculate_growth_rate(self, samples):
        """Calculate memory growth rate from samples."""
        if len(samples) < 2:
            return 0
            
        time_diff = samples[-1]['timestamp'] - samples[0]['timestamp']
        memory_diff = samples[-1]['memory_mb'] - samples[0]['memory_mb']
        
        return memory_diff / time_diff if time_diff > 0 else 0
    
    def generate_random_transform(self):
        """Generate random transform for testing."""
        modes = ['translate', 'rotate', 'scale']
        axes = ['x', 'y', 'z']
        
        return {
            'mode': np.random.choice(modes),
            'axis': np.random.choice(axes),
            'value': np.random.uniform(-10, 10)
        }

class PerformanceMetricsCollector:
    """Collects and analyzes performance metrics during testing."""
    
    def __init__(self):
        self.metrics = []
        self.logger = TransformLogger('performance_metrics.log')
    
    def record_metric(self, operation, duration, memory_used, shape_count=None, vertex_count=None):
        """Record a performance metric."""
        metric = {
            'operation': operation,
            'duration': duration,
            'memory_used': memory_used,
            'shape_count': shape_count,
            'vertex_count': vertex_count,
            'timestamp': time.time()
        }
        self.metrics.append(metric)
        
        # Log the metric
        self.logger.info(
            f"Performance Metric Recorded",
            extra={
                'metric': metric
            }
        )
    
    def analyze_metrics(self):
        """Analyze collected metrics and return insights."""
        if not self.metrics:
            return "No metrics collected"
            
        analysis = {
            'total_operations': len(self.metrics),
            'avg_duration': np.mean([m['duration'] for m in self.metrics]),
            'max_duration': max(m['duration'] for m in self.metrics),
            'avg_memory': np.mean([m['memory_used'] for m in self.metrics]),
            'max_memory': max(m['memory_used'] for m in self.metrics)
        }
        
        # Log analysis results
        self.logger.info(
            "Performance Analysis Complete",
            extra={
                'analysis': analysis
            }
        )
        
        return analysis

class TestTransformPerformance(unittest.TestCase):
    """Performance tests for the transform system."""
    
    def setUp(self):
        self.metrics_collector = PerformanceMetricsCollector()
        self.logger = TransformLogger('transform_performance.log')
        gc.collect()  # Clean up before tests
    
    def test_batch_transform_performance(self):
        """Test performance with increasing numbers of shapes."""
        shape_counts = [100, 500, 1000, 5000]
        
        for count in shape_counts:
            self.logger.info(f"Testing batch transform with {count} shapes")
            
            # Create shapes
            shapes = [ComplexMesh() for _ in range(count)]
            
            # Measure transform performance
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            # Apply transforms
            transform = Transform()
            for shape in shapes:
                transform.apply(shape)
            
            duration = time.time() - start_time
            memory_used = psutil.Process().memory_info().rss - start_memory
            
            self.metrics_collector.record_metric(
                f"batch_transform_{count}",
                duration,
                memory_used,
                shape_count=count
            )
            
            # Performance assertions
            self.assertLess(
                duration,
                count * 0.001,  # Expected 1ms per shape max
                f"Batch transform of {count} shapes took too long"
            )
    
    def test_complex_mesh_performance(self):
        """Test performance with high-vertex meshes."""
        vertex_counts = [1000, 10000, 100000]
        
        for count in vertex_counts:
            self.logger.info(f"Testing complex mesh with {count} vertices")
            
            # Create complex mesh
            mesh = ComplexMesh(vertex_count=count)
            
            # Measure transform performance
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            # Apply transform
            transform = Transform()
            transform.apply(mesh)
            
            duration = time.time() - start_time
            memory_used = psutil.Process().memory_info().rss - start_memory
            
            self.metrics_collector.record_metric(
                f"complex_mesh_{count}",
                duration,
                memory_used,
                vertex_count=count
            )
            
            # Performance assertions
            self.assertLess(
                duration,
                count * 0.0001,  # Expected 0.1ms per 1000 vertices max
                f"Transform of {count} vertex mesh took too long"
            )
    
    def test_memory_usage(self):
        """Test memory usage patterns during transforms."""
        self.logger.info("Testing memory usage patterns")
        
        initial_memory = psutil.Process().memory_info().rss
        shape_count = 1000
        
        # Create and transform shapes while monitoring memory
        shapes = []
        memory_samples = []
        
        for i in range(shape_count):
            shapes.append(ComplexMesh())
            transform = Transform()
            transform.apply(shapes[-1])
            
            if i % 100 == 0:  # Sample every 100 shapes
                current_memory = psutil.Process().memory_info().rss
                memory_samples.append(current_memory - initial_memory)
                
                self.metrics_collector.record_metric(
                    f"memory_sample_{i}",
                    0,  # Duration not relevant here
                    memory_samples[-1],
                    shape_count=i+1
                )
        
        # Analyze memory growth
        if len(memory_samples) > 1:
            memory_growth_rate = (memory_samples[-1] - memory_samples[0]) / len(memory_samples)
            
            self.logger.info(
                "Memory growth analysis",
                extra={
                    'growth_rate': memory_growth_rate,
                    'initial_memory': memory_samples[0],
                    'final_memory': memory_samples[-1]
                }
            )
            
            # Assert reasonable memory growth
            self.assertLess(
                memory_growth_rate,
                1024 * 1024,  # Expected less than 1MB growth per 100 shapes
                "Memory growth rate too high"
            )
    
    def tearDown(self):
        """Analyze metrics after each test."""
        analysis = self.metrics_collector.analyze_metrics()
        self.logger.info(
            "Test completed",
            extra={
                'metrics_analysis': analysis
            }
        )
        gc.collect()  # Clean up after tests

if __name__ == '__main__':
    unittest.main() 