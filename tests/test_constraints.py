"""
Unit tests for geometric constraints in the sketch system.
"""

import unittest
import numpy as np
from src.core.sketch import (
    SketchManager, Point2D, Line2D, Circle2D, Arc2D,
    ConstraintType, Constraint
)

class TestGeometricConstraints(unittest.TestCase):
    """Test cases for geometric constraints."""

    def setUp(self):
        """Set up test environment before each test."""
        self.sketch_manager = SketchManager()
        self.tolerance = 1e-6

    def test_concentric_circles(self):
        """Test concentric constraint between two circles."""
        # Create two circles with different centers
        c1_id = self.sketch_manager.add_circle(0, 0, 5)
        c2_id = self.sketch_manager.add_circle(2, 2, 3)
        
        # Add concentric constraint
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.CONCENTRIC,
            [c1_id, c2_id]
        )
        
        # Solve constraints
        self.assertTrue(self.sketch_manager.solve_constraints())
        
        # Get updated circles
        c1 = self.sketch_manager.circles[c1_id]
        c2 = self.sketch_manager.circles[c2_id]
        
        # Centers should be at the same point (1, 1)
        self.assertAlmostEqual(c1.center.x, c2.center.x, delta=self.tolerance)
        self.assertAlmostEqual(c1.center.y, c2.center.y, delta=self.tolerance)
        
        # Radii should remain unchanged
        self.assertAlmostEqual(c1.radius, 5, delta=self.tolerance)
        self.assertAlmostEqual(c2.radius, 3, delta=self.tolerance)

    def test_concentric_circle_arc(self):
        """Test concentric constraint between circle and arc."""
        # Create circle and arc with different centers
        circle_id = self.sketch_manager.add_circle(0, 0, 5)
        arc_id = self.sketch_manager.add_arc(3, 3, 2, 0, np.pi/2)
        
        # Add concentric constraint
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.CONCENTRIC,
            [circle_id, arc_id]
        )
        
        # Solve constraints
        self.assertTrue(self.sketch_manager.solve_constraints())
        
        # Get updated entities
        circle = self.sketch_manager.circles[circle_id]
        arc = self.sketch_manager.arcs[arc_id]
        
        # Centers should be at the same point (1.5, 1.5)
        self.assertAlmostEqual(circle.center.x, arc.center.x, delta=self.tolerance)
        self.assertAlmostEqual(circle.center.y, arc.center.y, delta=self.tolerance)
        
        # Radii and arc angles should remain unchanged
        self.assertAlmostEqual(circle.radius, 5, delta=self.tolerance)
        self.assertAlmostEqual(arc.radius, 2, delta=self.tolerance)
        self.assertAlmostEqual(arc.start_angle, 0, delta=self.tolerance)
        self.assertAlmostEqual(arc.end_angle, np.pi/2, delta=self.tolerance)

    def test_horizontal_line(self):
        """Test horizontal constraint on a line."""
        # Create diagonal line
        line_id = self.sketch_manager.add_line(0, 0, 3, 4)
        
        # Add horizontal constraint
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.HORIZONTAL,
            [line_id]
        )
        
        # Solve constraints
        self.assertTrue(self.sketch_manager.solve_constraints())
        
        # Get updated line
        line = self.sketch_manager.lines[line_id]
        
        # Line should be horizontal (same Y coordinate for both endpoints)
        self.assertAlmostEqual(line.start.y, line.end.y, delta=self.tolerance)
        
        # Length should be preserved (5)
        original_length = np.sqrt(3**2 + 4**2)
        new_length = line.length()
        self.assertAlmostEqual(new_length, original_length, delta=self.tolerance)

    def test_vertical_line(self):
        """Test vertical constraint on a line."""
        # Create diagonal line
        line_id = self.sketch_manager.add_line(0, 0, 4, 3)
        
        # Add vertical constraint
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.VERTICAL,
            [line_id]
        )
        
        # Solve constraints
        self.assertTrue(self.sketch_manager.solve_constraints())
        
        # Get updated line
        line = self.sketch_manager.lines[line_id]
        
        # Line should be vertical (same X coordinate for both endpoints)
        self.assertAlmostEqual(line.start.x, line.end.x, delta=self.tolerance)
        
        # Length should be preserved (5)
        original_length = np.sqrt(4**2 + 3**2)
        new_length = line.length()
        self.assertAlmostEqual(new_length, original_length, delta=self.tolerance)

    def test_already_horizontal_line(self):
        """Test horizontal constraint on already horizontal line."""
        # Create horizontal line
        line_id = self.sketch_manager.add_line(0, 5, 4, 5)
        
        # Add horizontal constraint
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.HORIZONTAL,
            [line_id]
        )
        
        # Solve constraints
        self.assertTrue(self.sketch_manager.solve_constraints())
        
        # Get updated line
        line = self.sketch_manager.lines[line_id]
        
        # Line should remain unchanged
        self.assertAlmostEqual(line.start.x, 0, delta=self.tolerance)
        self.assertAlmostEqual(line.start.y, 5, delta=self.tolerance)
        self.assertAlmostEqual(line.end.x, 4, delta=self.tolerance)
        self.assertAlmostEqual(line.end.y, 5, delta=self.tolerance)

    def test_already_vertical_line(self):
        """Test vertical constraint on already vertical line."""
        # Create vertical line
        line_id = self.sketch_manager.add_line(3, 0, 3, 4)
        
        # Add vertical constraint
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.VERTICAL,
            [line_id]
        )
        
        # Solve constraints
        self.assertTrue(self.sketch_manager.solve_constraints())
        
        # Get updated line
        line = self.sketch_manager.lines[line_id]
        
        # Line should remain unchanged
        self.assertAlmostEqual(line.start.x, 3, delta=self.tolerance)
        self.assertAlmostEqual(line.start.y, 0, delta=self.tolerance)
        self.assertAlmostEqual(line.end.x, 3, delta=self.tolerance)
        self.assertAlmostEqual(line.end.y, 4, delta=self.tolerance)

    def test_multiple_constraints(self):
        """Test multiple constraints working together."""
        # Create two circles and a line
        c1_id = self.sketch_manager.add_circle(0, 0, 2)
        c2_id = self.sketch_manager.add_circle(3, 4, 3)
        line_id = self.sketch_manager.add_line(1, 1, 5, 6)
        
        # Add concentric constraint between circles
        self.sketch_manager.add_constraint(
            ConstraintType.CONCENTRIC,
            [c1_id, c2_id]
        )
        
        # Add horizontal constraint to line
        self.sketch_manager.add_constraint(
            ConstraintType.HORIZONTAL,
            [line_id]
        )
        
        # Solve all constraints
        self.assertTrue(self.sketch_manager.solve_constraints())
        
        # Get updated entities
        c1 = self.sketch_manager.circles[c1_id]
        c2 = self.sketch_manager.circles[c2_id]
        line = self.sketch_manager.lines[line_id]
        
        # Verify circles are concentric
        self.assertAlmostEqual(c1.center.x, c2.center.x, delta=self.tolerance)
        self.assertAlmostEqual(c1.center.y, c2.center.y, delta=self.tolerance)
        
        # Verify line is horizontal
        self.assertAlmostEqual(line.start.y, line.end.y, delta=self.tolerance)

    def test_invalid_concentric_constraint(self):
        """Test concentric constraint with invalid entities."""
        # Create circle and line
        circle_id = self.sketch_manager.add_circle(0, 0, 2)
        line_id = self.sketch_manager.add_line(1, 1, 3, 3)
        
        # Try to add concentric constraint between circle and line
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.CONCENTRIC,
            [circle_id, line_id]
        )
        
        # Constraint solving should fail
        self.assertFalse(self.sketch_manager.solve_constraints())

    def test_invalid_horizontal_constraint(self):
        """Test horizontal constraint with invalid entity."""
        # Create circle
        circle_id = self.sketch_manager.add_circle(0, 0, 2)
        
        # Try to add horizontal constraint to circle
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.HORIZONTAL,
            [circle_id]
        )
        
        # Constraint solving should fail
        self.assertFalse(self.sketch_manager.solve_constraints())

    def test_invalid_vertical_constraint(self):
        """Test vertical constraint with invalid entity."""
        # Create circle
        circle_id = self.sketch_manager.add_circle(0, 0, 2)
        
        # Try to add vertical constraint to circle
        constraint_id = self.sketch_manager.add_constraint(
            ConstraintType.VERTICAL,
            [circle_id]
        )
        
        # Constraint solving should fail
        self.assertFalse(self.sketch_manager.solve_constraints())

if __name__ == '__main__':
    unittest.main() 