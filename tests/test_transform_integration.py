import sys
import os
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtTest import QTest

# Add the parent directory to the Python path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transform_tab import TransformTab
from scene_manager import SceneManager
from viewport import Viewport
from shape import Shape
from performance_visualizer import PerformanceVisualizer

class TestTransformIntegration(unittest.TestCase):
    """Integration test suite for the transform system."""
    
    @classmethod
    def setUpClass(cls):
        """Create the QApplication instance."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])
            
    def setUp(self):
        """Set up the test environment before each test."""
        self.transform_tab = TransformTab()
        self.scene_manager = SceneManager()
        self.viewport = Viewport()
        
        # Connect signals
        self.transform_tab.transform_applied.connect(self.scene_manager.applyTransform)
        self.transform_tab.preset_applied.connect(self.viewport.onPresetApplied)
        self.scene_manager.shape_transformed.connect(self.viewport.onShapeTransformed)
        
        # Sample preset data for testing
        self.test_preset = {
            'transform': {
                'mode': 'translate',
                'axis': 'x',
                'value': 1.0,
                'param_name': 'Distance',
                'relative_mode': False,
                'snap_settings': {
                    'enabled': True,
                    'translate': 0.25,
                    'rotate': 15.0,
                    'scale': 0.25
                }
            },
            'created': QDateTime.currentDateTime().toString(),
            'last_modified': QDateTime.currentDateTime().toString()
        }
        
    def test_scene_manager_integration(self):
        """Test integration with SceneManager when applying presets."""
        # Create a test shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # Add and apply a test preset
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify shape state
        self.assertEqual(shape.transform.mode, 'translate')
        self.assertEqual(shape.transform.axis, 'x')
        self.assertEqual(shape.transform.value, 1.0)
        self.assertFalse(shape.transform.relative_mode)
        
        # Verify snap settings were applied
        self.assertTrue(shape.transform.snap_enabled)
        self.assertEqual(shape.transform.snap_translate, 0.25)
        self.assertEqual(shape.transform.snap_rotate, 15.0)
        self.assertEqual(shape.transform.snap_scale, 0.25)
        
    def test_viewport_integration(self):
        """Test integration with viewport rendering."""
        # Create and select a shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # Mock viewport's render method
        self.viewport.render = MagicMock()
        
        # Apply preset and verify viewport update
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify viewport was updated
        self.viewport.render.assert_called()
        
        # Verify viewport's transform gizmos reflect preset settings
        self.assertEqual(self.viewport.current_transform_mode, 'translate')
        self.assertEqual(self.viewport.active_axis, 'x')
        self.assertTrue(self.viewport.show_snap_grid)
        
    def test_shape_creation_with_preset(self):
        """Test applying presets during shape creation."""
        # Set up preset
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        self.transform_tab.loadSelectedPreset()
        
        # Create shape with preset settings
        shape = self.scene_manager.create_shape(
            "cube",
            transform_settings=self.test_preset['transform']
        )
        
        # Verify shape was created with preset settings
        self.assertEqual(shape.transform.mode, 'translate')
        self.assertEqual(shape.transform.axis, 'x')
        self.assertEqual(shape.transform.value, 1.0)
        self.assertTrue(shape.transform.snap_enabled)
        
    def test_multiple_shape_transforms(self):
        """Test applying presets to multiple selected shapes."""
        # Create multiple shapes
        shape1 = self.scene_manager.create_shape("cube")
        shape2 = self.scene_manager.create_shape("sphere")
        
        # Select both shapes
        self.scene_manager.select_shape(shape1.id)
        self.scene_manager.select_shape(shape2.id, add_to_selection=True)
        
        # Apply preset to selected shapes
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify both shapes were transformed
        for shape in [shape1, shape2]:
            self.assertEqual(shape.transform.mode, 'translate')
            self.assertEqual(shape.transform.axis, 'x')
            self.assertEqual(shape.transform.value, 1.0)
            
    def test_unsupported_transform_mode(self):
        """Test handling of unsupported transform modes."""
        # Create a shape that doesn't support scaling
        shape = self.scene_manager.create_shape("line")  # Hypothetical non-scalable shape
        self.scene_manager.select_shape(shape.id)
        
        # Create a scale preset
        scale_preset = self.test_preset.copy()
        scale_preset['transform']['mode'] = 'scale'
        scale_preset['transform']['value'] = 2.0
        self.transform_tab._presets['Scale Preset'] = scale_preset
        
        # Try to apply scale preset
        self.transform_tab.preset_combo.setCurrentText('Scale Preset')
        self.transform_tab.loadSelectedPreset()
        
        # Verify shape remains unchanged
        self.assertNotEqual(shape.transform.mode, 'scale')
        self.assertNotEqual(shape.transform.value, 2.0)
        
    def test_invalid_preset_data(self):
        """Test handling of invalid or corrupted preset data."""
        # Create preset with missing fields
        invalid_preset = {
            'transform': {
                'mode': 'translate'
                # Missing other required fields
            }
        }
        
        self.transform_tab._presets['Invalid Preset'] = invalid_preset
        self.transform_tab.preset_combo.setCurrentText('Invalid Preset')
        
        # Create and select a shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # Try to load invalid preset
        with self.assertRaises(KeyError):
            self.transform_tab.loadSelectedPreset()
            
        # Verify shape remains unchanged
        self.assertNotEqual(shape.transform.mode, 'translate')
        
    def test_preset_undo_redo_integration(self):
        """Test undo/redo functionality with SceneManager."""
        # Create and select a shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # Apply first preset
        preset1 = self.test_preset.copy()
        preset1['transform']['value'] = 1.0
        self.transform_tab._presets['Preset1'] = preset1
        self.transform_tab.preset_combo.setCurrentText('Preset1')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Apply second preset
        preset2 = self.test_preset.copy()
        preset2['transform']['value'] = 2.0
        self.transform_tab._presets['Preset2'] = preset2
        self.transform_tab.preset_combo.setCurrentText('Preset2')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Test undo
        self.transform_tab.undoTransform()
        self.assertEqual(shape.transform.value, 1.0)
        
        # Test redo
        self.transform_tab.redoTransform()
        self.assertEqual(shape.transform.value, 2.0)
        
        # Verify viewport updates
        self.viewport.render.assert_called()

    def test_preset_performance_bulk_shapes(self):
        """Test performance when applying presets to many shapes."""
        # Create many shapes
        num_shapes = 100
        shapes = [self.scene_manager.create_shape("cube") for _ in range(num_shapes)]
        
        # Add test preset
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        
        # Time the preset application
        start_time = time.time()
        
        # Select all shapes and apply preset
        for shape in shapes:
            self.scene_manager.select_shape(shape.id)
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        duration = time.time() - start_time
        
        # Should complete within 1 second
        self.assertLess(duration, 1.0)
        
        # Verify all shapes were transformed
        for shape in shapes:
            self.assertEqual(shape.transform.mode, 'translate')
            self.assertEqual(shape.transform.value, 1.0)
            
    def test_preset_performance_complex_shape(self):
        """Test performance when applying presets to a complex shape."""
        # Create a complex shape (e.g., high vertex count)
        shape = self.scene_manager.create_shape("complex_mesh", vertex_count=10000)
        self.scene_manager.select_shape(shape.id)
        
        # Add test preset
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        
        # Time the preset application
        start_time = time.time()
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        duration = time.time() - start_time
        
        # Should complete within 100ms
        self.assertLess(duration, 0.1)
        
    def test_preset_ui_feedback(self):
        """Test UI feedback when applying presets."""
        # Mock viewport status message and progress indicator
        self.viewport.show_status_message = MagicMock()
        self.viewport.show_progress = MagicMock()
        self.viewport.hide_progress = MagicMock()
        
        # Create and select a shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # Apply preset
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify UI feedback
        self.viewport.show_status_message.assert_called_with("Preset 'Test Preset' applied")
        self.viewport.show_progress.assert_called()
        self.viewport.hide_progress.assert_called()
        
    def test_preset_ui_gizmo_update(self):
        """Test that transform gizmos update correctly when applying presets."""
        # Create and select a shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # Mock gizmo update methods
        self.viewport.update_transform_gizmos = MagicMock()
        self.viewport.update_snap_grid = MagicMock()
        
        # Apply preset
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify gizmo updates
        self.viewport.update_transform_gizmos.assert_called_with(
            mode='translate',
            axis='x',
            snap_enabled=True
        )
        self.viewport.update_snap_grid.assert_called_with(
            enabled=True,
            spacing=0.25
        )
        
    def test_extreme_transform_values(self):
        """Test applying presets with extreme transform values."""
        # Create shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # Test very large value
        large_preset = self.test_preset.copy()
        large_preset['transform']['value'] = 1e6
        self.transform_tab._presets['Large Preset'] = large_preset
        self.transform_tab.preset_combo.setCurrentText('Large Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify large transform
        self.assertEqual(shape.transform.value, 1e6)
        
        # Test very small value
        small_preset = self.test_preset.copy()
        small_preset['transform']['value'] = 1e-6
        self.transform_tab._presets['Small Preset'] = small_preset
        self.transform_tab.preset_combo.setCurrentText('Small Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify small transform
        self.assertEqual(shape.transform.value, 1e-6)
        
    def test_invalid_snap_settings(self):
        """Test handling of presets with invalid snap settings."""
        # Create shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # Create preset with invalid snap settings
        invalid_snap_preset = self.test_preset.copy()
        invalid_snap_preset['transform']['snap_settings'] = {
            'enabled': True,
            'translate': -1.0,  # Invalid negative value
            'rotate': 'invalid',  # Invalid type
            'scale': None  # Missing value
        }
        
        self.transform_tab._presets['Invalid Snap'] = invalid_snap_preset
        self.transform_tab.preset_combo.setCurrentText('Invalid Snap')
        
        # Should raise ValueError for invalid snap settings
        with self.assertRaises(ValueError):
            self.transform_tab.loadSelectedPreset()
            
        # Verify shape remains unchanged
        self.assertNotEqual(shape.transform.snap_translate, -1.0)
        
    def test_no_selection_preset(self):
        """Test applying preset with no shape selected."""
        # Add test preset
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        
        # Mock viewport status message
        self.viewport.show_status_message = MagicMock()
        
        # Try to apply preset without selection
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify warning message
        self.viewport.show_status_message.assert_called_with(
            "No shape selected for transform",
            level="warning"
        )
        
    def test_rotated_shape_transform(self):
        """Test applying preset to an already rotated shape."""
        # Create and select a shape
        shape = self.scene_manager.create_shape("cube")
        self.scene_manager.select_shape(shape.id)
        
        # First rotate the shape
        rotate_preset = self.test_preset.copy()
        rotate_preset['transform'].update({
            'mode': 'rotate',
            'axis': 'y',
            'value': 45.0
        })
        
        self.transform_tab._presets['Rotate Preset'] = rotate_preset
        self.transform_tab.preset_combo.setCurrentText('Rotate Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Now apply translation preset
        self.transform_tab._presets['Test Preset'] = self.test_preset
        self.transform_tab.preset_combo.setCurrentText('Test Preset')
        self.transform_tab.loadSelectedPreset()
        self.transform_tab.applyTransform()
        
        # Verify both transforms were applied correctly
        self.assertEqual(shape.transform.rotation.y, 45.0)
        self.assertEqual(shape.transform.translation.x, 1.0)

    def test_performance_visualization_filtering(self):
        """Test filtering capabilities of performance visualizations."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data
        shape_counts = [100, 500, 1000, 2000, 5000]
        durations = [50, 150, 250, 450, 1000]
        
        # Test filtering by range
        filters = {'value_range': (0, 1000)}
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations, 
            test_type='test_filtering',
            filters=filters
        )
        self.assertTrue(os.path.exists(chart_file))
        
        # Test min/max filtering
        filters = {'min_value': 200, 'max_value': 800}
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations, 
            test_type='test_filtering',
            filters=filters
        )
        self.assertTrue(os.path.exists(chart_file))

    def test_performance_comparison(self):
        """Test comparison view functionality."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate current run data
        current_data = {
            'shape_counts': [100, 500, 1000],
            'durations': [50, 150, 250]
        }
        
        # Save current run data
        run_id = visualizer.save_test_data(current_data)
        self.assertIsNotNone(run_id)
        
        # Generate comparison data
        comparison_data = {
            'shape_counts': [100, 500, 1000],
            'durations': [45, 140, 230]  # Slightly better performance
        }
        
        # Create comparison visualization
        chart_file = visualizer.plot_transform_durations(
            current_data['shape_counts'],
            current_data['durations'],
            test_type='comparison_test',
            comparison_data=comparison_data
        )
        self.assertTrue(os.path.exists(chart_file))
        
        # Verify data persistence
        loaded_data = visualizer.load_test_data(run_id)
        self.assertEqual(loaded_data, current_data)
        
        # Verify run listing
        available_runs = visualizer.list_available_runs()
        self.assertIn(run_id, available_runs)

    def test_interactive_controls(self):
        """Test interactive control generation in HTML report."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data
        test_data = {
            'test_results': {
                'tests_run': 10,
                'failures': 0
            },
            'system_info': {
                'cpu_count': 8,
                'memory_total': 16000000000
            },
            'recommendations': []
        }
        
        # Create chart files
        chart_files = [
            visualizer.plot_transform_durations([100, 500], [50, 150], 'test_controls')
        ]
        
        # Generate report
        report_file = visualizer.generate_html_report(test_data, chart_files)
        self.assertTrue(os.path.exists(report_file))
        
        # Verify HTML content
        with open(report_file, 'r') as f:
            content = f.read()
            self.assertIn('filter-controls', content)
            self.assertIn('shape-count-min', content)
            self.assertIn('shape-count-max', content)
            self.assertIn('comparison-toggle', content)
            self.assertIn('chart-type', content)

if __name__ == '__main__':
    unittest.main() 