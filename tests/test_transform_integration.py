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

    def test_export_functionality(self):
        """Test export functionality in the HTML report."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        
        # Test single dataset export
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations, 
            test_type='export_test'
        )
        
        # Generate report
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            }, 
            [chart_file]
        )
        
        # Verify export controls and functionality
        with open(report_file, 'r') as f:
            content = f.read()
            # Check for export controls
            self.assertIn('export-controls', content)
            self.assertIn('exportData', content)
            self.assertIn('exportComparisonData', content)
            # Check for export buttons
            self.assertIn('Export Data', content)
            self.assertIn('onclick="exportData(\'csv\')"', content)
            self.assertIn('onclick="exportData(\'json\')"', content)
            self.assertIn('onclick="exportData(\'excel\')"', content)
            # Check for data embedding
            self.assertIn('window.currentData', content)
            self.assertIn('"shape_counts":', content)
            self.assertIn('"durations":', content)
        
        # Test comparison dataset export
        comparison_data = {
            'shape_counts': [100, 500, 1000],
            'durations': [45, 140, 230]
        }
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='export_test_comparison',
            comparison_data=comparison_data
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify comparison export functionality
        with open(report_file, 'r') as f:
            content = f.read()
            # Check for comparison data embedding
            self.assertIn('window.comparisonData', content)
            self.assertIn('"current":', content)
            self.assertIn('"comparison":', content)
            # Check for comparison export buttons
            self.assertIn('onclick="exportComparisonData(\'csv\')"', content)
            self.assertIn('onclick="exportComparisonData(\'json\')"', content)
            self.assertIn('onclick="exportComparisonData(\'excel\')"', content)

    def test_export_directory_creation(self):
        """Test that export directory is created correctly."""
        output_dir = 'test_reports_export'
        visualizer = PerformanceVisualizer(output_dir=output_dir)
        
        # Verify directories were created
        self.assertTrue(os.path.exists(output_dir))
        self.assertTrue(os.path.exists(os.path.join(output_dir, 'data')))
        self.assertTrue(os.path.exists(os.path.join(output_dir, 'exports')))
        
        # Clean up test directory
        import shutil
        shutil.rmtree(output_dir)

    def test_export_with_invalid_data(self):
        """Test export functionality with invalid data."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with NaN and infinite values
        shape_counts = [100, 500, 1000, 2000]
        durations = [50, float('nan'), float('inf'), 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='invalid_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify data validation and sanitization
        with open(report_file, 'r') as f:
            content = f.read()
            # Check for sanitization functions
            self.assertIn('sanitizeNumber', content)
            self.assertIn('validateDataArrays', content)
            self.assertIn('sanitizeDataForExport', content)
            # Check for error handling
            self.assertIn('showExportError', content)
            self.assertIn('export-error', content)
            # Check for data embedding with sanitized values
            self.assertIn('"durations":', content)
            self.assertIn('N/A', content)  # NaN should be replaced with N/A

    def test_export_with_mismatched_arrays(self):
        """Test export functionality with mismatched array lengths."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with different array lengths
        shape_counts = [100, 500, 1000]
        durations = [50, 150]  # Missing one value
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='mismatch_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error handling for mismatched arrays
        with open(report_file, 'r') as f:
            content = f.read()
            self.assertIn('array length mismatch', content)

    def test_export_with_invalid_comparison(self):
        """Test export functionality with invalid comparison data."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with different shape counts in comparison
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        comparison_data = {
            'shape_counts': [200, 600, 1200],  # Different shape counts
            'durations': [45, 140, 230]
        }
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='invalid_comparison',
            comparison_data=comparison_data
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error handling for invalid comparison data
        with open(report_file, 'r') as f:
            content = f.read()
            self.assertIn('Shape counts in comparison data do not match', content)

    def test_export_with_decimal_precision(self):
        """Test export functionality with decimal precision handling."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with many decimal places
        shape_counts = [100, 500, 1000]
        durations = [50.123456, 150.987654, 250.543210]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='precision_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify decimal precision in exported data
        with open(report_file, 'r') as f:
            content = f.read()
            # Check that numbers are rounded to 2 decimal places
            self.assertIn('50.12', content)
            self.assertIn('150.99', content)
            self.assertIn('250.54', content)
            # Ensure original precision is not present
            self.assertNotIn('50.123456', content)

    def test_detailed_error_messages(self):
        """Test enhanced error messages with detailed diagnostics."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with various validation issues
        shape_counts = [100, float('nan'), 1000]
        durations = [50, 150]  # Mismatched length
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='error_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error message content
        with open(report_file, 'r') as f:
            content = f.read()
            # Check for array length mismatch message
            self.assertIn("Array length mismatch: 'durations' has 2 elements, expected 3", content)
            # Check for invalid value message
            self.assertIn("Found 1 invalid shape count(s):", content)
            self.assertIn("Index 1:", content)
            self.assertIn("replaced with N/A", content)

    def test_comparison_data_error_messages(self):
        """Test detailed error messages for comparison data validation."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with mismatched shape counts
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        comparison_data = {
            'shape_counts': [200, 600, 1200],
            'durations': [45, 140, 230]
        }
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='comparison_error_test',
            comparison_data=comparison_data
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify comparison error message content
        with open(report_file, 'r') as f:
            content = f.read()
            # Check for shape count mismatch details
            self.assertIn("Shape counts in comparison data do not match:", content)
            self.assertIn("Index 0: current=100, comparison=200", content)
            self.assertIn("Index 1: current=500, comparison=600", content)
            self.assertIn("Index 2: current=1000, comparison=1200", content)

    def test_export_error_styling(self):
        """Test that error messages are properly styled in the HTML report."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data with validation issues
        shape_counts = [100, float('inf'), 1000]
        durations = [50, float('nan'), 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='style_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error styling
        with open(report_file, 'r') as f:
            content = f.read()
            # Check for styled error elements
            self.assertIn("error-title", content)
            self.assertIn("error-content", content)
            self.assertIn("error-header", content)
            self.assertIn("error-detail", content)
            # Check for error message formatting
            self.assertIn("Found 1 invalid shape count(s):", content)
            self.assertIn("Found 1 invalid duration(s):", content)

    def test_json_export_diagnostics(self):
        """Test that diagnostics are included in JSON exports."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data with validation issues
        shape_counts = [100, float('nan'), 1000]
        durations = [50, float('inf'), 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='json_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify JSON export content
        with open(report_file, 'r') as f:
            content = f.read()
            # Check for diagnostics in JSON structure
            self.assertIn('"diagnostics":', content)
            self.assertIn('"data":', content)
            self.assertIn('"shape_counts":', content)
            self.assertIn('"durations":', content)
            # Check for specific diagnostic messages
            self.assertIn("Found 1 invalid shape count(s):", content)
            self.assertIn("Found 1 invalid duration(s):", content)

    def test_empty_array_error(self):
        """Test error handling for empty arrays."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test with empty shape_counts array
        shape_counts = []
        durations = [50, 150]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='empty_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error message content
        with open(report_file, 'r') as f:
            content = f.read()
            self.assertIn("Array 'shape_counts' is empty", content)
            self.assertIn("Please provide at least one data point", content)

    def test_non_numeric_error(self):
        """Test error handling for non-numeric values."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test with various non-numeric values
        shape_counts = [100, 'abc', 1000]
        durations = [50, {'value': 150}, 250]  # Object in durations
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='non_numeric_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error message content
        with open(report_file, 'r') as f:
            content = f.read()
            # Check string value error
            self.assertIn("Invalid value type: expected number, got string ('abc')", content)
            # Check object value error
            self.assertIn("Invalid value type: expected number, got object", content)

    def test_validation_summary(self):
        """Test validation summary in export data."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with various validation issues
        shape_counts = [100, float('nan'), 'invalid', 1000]
        durations = [50, float('inf'), 'abc', 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='summary_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify validation summary
        with open(report_file, 'r') as f:
            content = f.read()
            self.assertIn('"validation_summary":', content)
            self.assertIn('"total_values": 8', content)
            self.assertIn('"invalid_values": 4', content)
            self.assertIn('"shape_count_errors": 2', content)
            self.assertIn('"duration_errors": 2', content)

    def test_comparison_validation_summary(self):
        """Test validation summary in comparison export data."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with validation issues in both current and comparison
        shape_counts = [100, float('nan'), 1000]
        durations = [50, 150, 250]
        comparison_data = {
            'shape_counts': [100, 'invalid', 1000],
            'durations': [45, float('inf'), 230]
        }
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='comparison_summary_test',
            comparison_data=comparison_data
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify comparison validation summary
        with open(report_file, 'r') as f:
            content = f.read()
            self.assertIn('"validation_summary":', content)
            self.assertIn('"total_values":', content)
            self.assertIn('"invalid_values":', content)
            self.assertIn('"current_errors":', content)
            self.assertIn('"comparison_errors":', content)
            # Check specific error messages
            self.assertIn('Invalid numeric value: NaN', content)
            self.assertIn('Invalid value type: expected number, got string', content)
            self.assertIn('Invalid numeric value: Infinity', content)

    def test_invalid_data_structure(self):
        """Test error handling for invalid data structures."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test with null data
        shape_counts = None
        durations = [50, 150]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='invalid_structure_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error message content
        with open(report_file, 'r') as f:
            content = f.read()
            self.assertIn('Invalid input: expected array, got null', content)

    def test_detailed_type_errors(self):
        """Test detailed error messages for type mismatches."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test with various invalid types
        shape_counts = [100, [], {'count': 500}, 1000]  # Array and object in shape_counts
        durations = [50, None, 250]  # Null in durations
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='type_error_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error message content
        with open(report_file, 'r') as f:
            content = f.read()
            # Check array value error
            self.assertIn('Invalid value type: expected number, got array', content)
            # Check object value error
            self.assertIn('Invalid value type: expected number, got object', content)
            # Check null value error
            self.assertIn('Invalid value type: expected number, got null', content)

    def test_csv_export_format(self):
        """Test CSV export format integrity and data accuracy."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with various numeric formats
        shape_counts = [100, 500.5, 1000]
        durations = [50.123, 150.456, 250.789]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='csv_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify CSV export functionality
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check CSV structure
            self.assertIn('Shape Count,Duration (ms)', content)
            
            # Verify decimal precision
            self.assertIn('500.50', content)
            self.assertIn('50.12', content)
            
            # Check newline handling
            self.assertIn('\\n', content)  # Proper line endings
            
            # Verify export function call
            self.assertIn('exportData(\'csv\')', content)

    def test_json_export_structure(self):
        """Test JSON export structure and metadata inclusion."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with metadata
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='json_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify JSON export functionality
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check JSON structure
            self.assertIn('"data": {', content)
            self.assertIn('"shape_counts":', content)
            self.assertIn('"durations":', content)
            
            # Verify metadata inclusion
            self.assertIn('"validation_summary":', content)
            
            # Check array formatting
            self.assertIn('[100,', content)
            
            # Verify export function call
            self.assertIn('exportData(\'json\')', content)

    def test_excel_export_format(self):
        """Test Excel export format and cell formatting."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with various numeric types
        shape_counts = [100, 500.5, 1000]
        durations = [50.123, 150.456, 250.789]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='excel_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify Excel export functionality
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check Excel structure
            self.assertIn('Shape Count\\tDuration (ms)', content)
            
            # Verify number formatting
            self.assertIn('500.50', content)
            self.assertIn('50.12', content)
            
            # Check tab delimiter
            self.assertIn('\\t', content)
            
            # Verify export function call
            self.assertIn('exportData(\'excel\')', content)

    def test_comparison_export_formats(self):
        """Test export formats for comparison data."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Test data with comparison
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        comparison_data = {
            'shape_counts': [100, 500, 1000],
            'durations': [45, 140, 230]
        }
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='comparison_export_test',
            comparison_data=comparison_data
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify comparison export formats
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check CSV format
            self.assertIn('Shape Count,Current Duration (ms),Comparison Duration (ms)', content)
            
            # Check JSON structure
            self.assertIn('"current": {', content)
            self.assertIn('"comparison": {', content)
            
            # Check Excel format
            self.assertIn('Shape Count\\tCurrent Duration (ms)\\tComparison Duration (ms)', content)
            
            # Verify export function calls
            self.assertIn('exportComparisonData(\'csv\')', content)
            self.assertIn('exportComparisonData(\'json\')', content)
            self.assertIn('exportComparisonData(\'excel\')', content)

    def test_export_filename_generation(self):
        """Test export filename generation and timestamp formatting."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='filename_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify filename generation
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check timestamp inclusion
            self.assertIn('new Date().toISOString().slice(0,19)', content)
            
            # Check file extensions
            self.assertIn('.csv', content)
            self.assertIn('.json', content)
            self.assertIn('.xls', content)
            
            # Verify filename patterns
            self.assertIn('performance_data_', content)
            self.assertIn('comparison_data_', content)

    def test_export_mime_types(self):
        """Test MIME type handling for different export formats."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='mime_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify MIME type handling
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check MIME types
            self.assertIn('text/csv', content)
            self.assertIn('application/json', content)
            self.assertIn('application/vnd.ms-excel', content)

    def test_export_progress_indicator(self):
        """Test that progress indicator is properly implemented in the HTML report."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='progress_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify progress indicator elements and functionality
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check progress container and bar
            self.assertIn('class="progress-container"', content)
            self.assertIn('class="progress-bar"', content)
            
            # Check progress functions
            self.assertIn('function showProgress', content)
            self.assertIn('function updateProgress', content)
            
            # Check progress updates in export functions
            self.assertIn('updateProgress(20)', content)
            self.assertIn('updateProgress(40)', content)
            self.assertIn('updateProgress(60)', content)
            self.assertIn('updateProgress(80)', content)
            self.assertIn('updateProgress(100)', content)

    def test_export_status_messages(self):
        """Test that status messages are properly implemented in the HTML report."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='status_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify status message elements and functionality
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check status message container
            self.assertIn('class="status-message"', content)
            
            # Check status message styles
            self.assertIn('status-success', content)
            self.assertIn('status-error', content)
            self.assertIn('status-warning', content)
            self.assertIn('status-info', content)
            
            # Check status message function
            self.assertIn('function showStatus', content)
            
            # Check status messages in export functions
            self.assertIn('Preparing data for export', content)
            self.assertIn('Data exported successfully', content)
            self.assertIn('Preparing comparison data for export', content)
            self.assertIn('Comparison data exported successfully', content)

    def test_export_ui_interaction(self):
        """Test that export UI elements are properly implemented and interactive."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data with comparison
        shape_counts = [100, 500, 1000]
        durations = [50, 150, 250]
        comparison_data = {
            'shape_counts': [100, 500, 1000],
            'durations': [45, 140, 230]
        }
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='ui_test',
            comparison_data=comparison_data
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify UI elements and interaction
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check export buttons
            self.assertIn('onclick="exportData(\'csv\')"', content)
            self.assertIn('onclick="exportData(\'json\')"', content)
            self.assertIn('onclick="exportData(\'excel\')"', content)
            
            # Check comparison export buttons
            self.assertIn('onclick="exportComparisonData(\'csv\')"', content)
            self.assertIn('onclick="exportComparisonData(\'json\')"', content)
            self.assertIn('onclick="exportComparisonData(\'excel\')"', content)
            
            # Check button styling
            self.assertIn('class="btn btn-primary"', content)
            self.assertIn('class="btn btn-secondary"', content)
            
            # Check export controls container
            self.assertIn('class="export-controls mb-4"', content)
            self.assertIn('class="button-group"', content)

    def test_export_error_handling_ui(self):
        """Test that export error handling is properly implemented in the UI."""
        visualizer = PerformanceVisualizer(output_dir='test_reports')
        
        # Generate test data with invalid values
        shape_counts = [100, float('nan'), 1000]
        durations = [50, float('inf'), 250]
        
        chart_file = visualizer.plot_transform_durations(
            shape_counts, durations,
            test_type='error_ui_test'
        )
        
        report_file = visualizer.generate_html_report(
            {
                'test_results': {
                    'tests_run': 10,
                    'failures': 0
                },
                'system_info': {},
                'recommendations': []
            },
            [chart_file]
        )
        
        # Verify error handling in UI
        with open(report_file, 'r') as f:
            content = f.read()
            
            # Check error handling in export functions
            self.assertIn('catch (error)', content)
            self.assertIn('showStatus(error.message, \'error\')', content)
            
            # Check error message styling
            self.assertIn('background-color: #FFEBEE', content)
            self.assertIn('color: #C62828', content)
            
            # Check error cleanup
            self.assertIn('showProgress(false)', content)
            self.assertIn('updateProgress(0)', content)

if __name__ == '__main__':
    unittest.main() 