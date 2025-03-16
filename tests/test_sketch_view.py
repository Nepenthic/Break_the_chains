"""
Integration tests for sketch view UI interactions.
"""

import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox
import sys

from src.ui.sketch_view import SketchView
from src.core.sketch import ConstraintType

# Create QApplication instance for tests
app = QApplication(sys.argv)

class TestSketchViewConstraints(unittest.TestCase):
    """Test cases for sketch view constraint interactions."""

    def setUp(self):
        """Set up test environment before each test."""
        self.view = SketchView()
        self.view.show()  # Must show widget for some Qt operations
        
        # Mock QMessageBox to avoid actual dialogs
        self.message_patcher = patch.object(QMessageBox, 'information')
        self.mock_message = self.message_patcher.start()
        
        # Mock warning dialog
        self.warning_patcher = patch.object(QMessageBox, 'warning')
        self.mock_warning = self.warning_patcher.start()

    def tearDown(self):
        """Clean up after each test."""
        self.message_patcher.stop()
        self.warning_patcher.stop()
        self.view.close()

    def test_concentric_constraint_ui(self):
        """Test creating concentric constraint through UI."""
        # Create two circles
        self.view.set_tool('circle')
        
        # First circle
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(0, 0))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(2, 0))
        
        # Second circle
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(3, 3))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(4, 3))
        
        # Switch to concentric constraint tool
        self.view.set_tool('concentric')
        
        # Select first circle
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(0, 0))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        
        # Select second circle
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(3, 3))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        
        # Verify constraint was added
        self.assertEqual(len(self.view.sketch_manager.constraints), 1)
        constraint = next(iter(self.view.sketch_manager.constraints.values()))
        self.assertEqual(constraint.type, ConstraintType.CONCENTRIC)

    def test_horizontal_constraint_ui(self):
        """Test creating horizontal constraint through UI."""
        # Create a line
        self.view.set_tool('line')
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(0, 0))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(3, 4))
        
        # Switch to horizontal constraint tool
        self.view.set_tool('horizontal')
        
        # Select the line
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(1, 2))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        
        # Verify constraint was added
        self.assertEqual(len(self.view.sketch_manager.constraints), 1)
        constraint = next(iter(self.view.sketch_manager.constraints.values()))
        self.assertEqual(constraint.type, ConstraintType.HORIZONTAL)
        
        # Verify line is horizontal
        line = next(iter(self.view.sketch_manager.lines.values()))
        self.assertAlmostEqual(line.start.y, line.end.y, places=6)

    def test_vertical_constraint_ui(self):
        """Test creating vertical constraint through UI."""
        # Create a line
        self.view.set_tool('line')
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(0, 0))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(3, 4))
        
        # Switch to vertical constraint tool
        self.view.set_tool('vertical')
        
        # Select the line
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(1, 2))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        
        # Verify constraint was added
        self.assertEqual(len(self.view.sketch_manager.constraints), 1)
        constraint = next(iter(self.view.sketch_manager.constraints.values()))
        self.assertEqual(constraint.type, ConstraintType.VERTICAL)
        
        # Verify line is vertical
        line = next(iter(self.view.sketch_manager.lines.values()))
        self.assertAlmostEqual(line.start.x, line.end.x, places=6)

    def test_invalid_concentric_selection(self):
        """Test attempting to create concentric constraint with invalid selection."""
        # Create a circle and a line
        self.view.set_tool('circle')
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(0, 0))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(2, 0))
        
        self.view.set_tool('line')
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(3, 3))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(5, 5))
        
        # Switch to concentric constraint tool
        self.view.set_tool('concentric')
        
        # Try to constrain circle and line
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(0, 0))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(4, 4))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        
        # Verify warning was shown
        self.mock_warning.assert_called_once()
        
        # Verify no constraint was added
        self.assertEqual(len(self.view.sketch_manager.constraints), 0)

    def test_multiple_constraints_ui(self):
        """Test creating multiple constraints through UI."""
        # Create two circles and a line
        self.view.set_tool('circle')
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(0, 0))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(2, 0))
        
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(3, 3))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(4, 3))
        
        self.view.set_tool('line')
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(1, 1))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton,
                          pos=self.view.mapFromScene(5, 5))
        
        # Add concentric constraint
        self.view.set_tool('concentric')
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(0, 0))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(3, 3))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        
        # Add horizontal constraint
        self.view.set_tool('horizontal')
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton,
                        pos=self.view.mapFromScene(3, 3))
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton)
        
        # Verify both constraints were added
        self.assertEqual(len(self.view.sketch_manager.constraints), 2)
        constraints = list(self.view.sketch_manager.constraints.values())
        constraint_types = {c.type for c in constraints}
        self.assertEqual(
            constraint_types,
            {ConstraintType.CONCENTRIC, ConstraintType.HORIZONTAL}
        )

if __name__ == '__main__':
    unittest.main() 