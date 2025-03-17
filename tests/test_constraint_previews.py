"""
Tests for the constraint preview system in the sketch view.
"""

import sys
import pytest
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from src.ui.sketch_view import SketchView
from src.core.sketch import ConstraintType

# Create QApplication instance for tests
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestConstraintPreviews:
    """Test suite for constraint preview functionality."""
    
    @pytest.fixture
    def sketch_view(self):
        """Create a fresh SketchView instance for each test."""
        view = SketchView()
        # Add some basic entities for testing
        view._point_tool(None, QPointF(100, 100))  # point1
        view._point_tool(None, QPointF(200, 200))  # point2
        view._line_tool(None, QPointF(300, 100))   # Start line1
        view.start_pos = QPointF(300, 100)
        view._finish_line(QPointF(400, 100))       # End line1
        view._line_tool(None, QPointF(300, 200))   # Start line2
        view.start_pos = QPointF(300, 200)
        view._finish_line(QPointF(400, 200))       # End line2
        view._circle_tool(None, QPointF(500, 150)) # Start circle1
        view.start_pos = QPointF(500, 150)
        view._finish_circle(QPointF(550, 150))     # End circle1
        view._circle_tool(None, QPointF(600, 150)) # Start circle2
        view.start_pos = QPointF(600, 150)
        view._finish_circle(QPointF(650, 150))     # End circle2
        return view

    def test_coincident_preview_valid_points(self, sketch_view):
        """Test coincident constraint preview between two points."""
        # Get the first two points from the scene
        points = [item for item in sketch_view.scene.items() 
                 if isinstance(item, sketch_view.PointItem)]
        assert len(points) >= 2
        
        # Start coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [points[0].entity_id]
        
        # Simulate hovering over second point
        sketch_view._update_constraint_preview(points[1], points[1].pos())
        
        # Verify preview elements
        preview_items = points[0].preview_items
        assert len(preview_items) >= 2  # Should have highlight circle and guide line
        
        # Check that preview items are of correct type and style
        has_highlight = any(item.type() == item.Type.EllipseItem for item in preview_items)
        has_guide_line = any(item.type() == item.Type.LineItem for item in preview_items)
        assert has_highlight and has_guide_line

    def test_coincident_preview_invalid_target(self, sketch_view):
        """Test coincident constraint preview with invalid target (line)."""
        # Get a point and a line
        point = next(item for item in sketch_view.scene.items() 
                    if isinstance(item, sketch_view.PointItem))
        line = next(item for item in sketch_view.scene.items() 
                   if isinstance(item, sketch_view.LineItem))
        
        # Start coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [point.entity_id]
        
        # Simulate hovering over line (invalid target)
        sketch_view._update_constraint_preview(line, line.pos())
        
        # Verify that red X indicator is shown
        preview_items = point.preview_items
        assert len(preview_items) >= 2  # Should have two lines forming X
        
        # Check that preview items use red color
        for item in preview_items:
            if item.type() == item.Type.LineItem:
                assert item.pen().color() == Qt.GlobalColor.red

    def test_equal_preview_lines(self, sketch_view):
        """Test equal constraint preview between two lines."""
        # Get two lines from the scene
        lines = [item for item in sketch_view.scene.items() 
                if isinstance(item, sketch_view.LineItem)]
        assert len(lines) >= 2
        
        # Start equal constraint
        sketch_view._start_constraint(ConstraintType.EQUAL)
        sketch_view.constraint_entities = [lines[0].entity_id]
        
        # Simulate hovering over second line
        sketch_view._update_constraint_preview(lines[1], lines[1].pos())
        
        # Verify preview elements
        preview_items = lines[0].preview_items
        assert len(preview_items) >= 3  # Should have indicators and labels
        
        # Check for length labels
        text_items = [item for item in preview_items 
                     if item.type() == item.Type.SimpleTextItem]
        assert len(text_items) >= 2  # Should have current and target length labels

    def test_equal_preview_circles(self, sketch_view):
        """Test equal constraint preview between two circles."""
        # Get two circles from the scene
        circles = [item for item in sketch_view.scene.items() 
                  if isinstance(item, sketch_view.CircleItem)]
        assert len(circles) >= 2
        
        # Start equal constraint
        sketch_view._start_constraint(ConstraintType.EQUAL)
        sketch_view.constraint_entities = [circles[0].entity_id]
        
        # Simulate hovering over second circle
        sketch_view._update_constraint_preview(circles[1], circles[1].pos())
        
        # Verify preview elements
        preview_items = circles[0].preview_items
        assert len(preview_items) >= 4  # Should have preview circles, radius lines, and labels
        
        # Check for radius labels and arrows
        text_items = [item for item in preview_items 
                     if item.type() == item.Type.SimpleTextItem]
        assert len(text_items) >= 2  # Should have current and target radius labels
        
        # Check for expansion/contraction arrows
        line_items = [item for item in preview_items 
                     if item.type() == item.Type.LineItem]
        assert any(item.pen().width() == 2 for item in line_items)  # Arrows use thicker pen

    def test_preview_cleanup(self, sketch_view):
        """Test that preview items are properly cleaned up."""
        # Get two points from the scene
        points = [item for item in sketch_view.scene.items() 
                 if isinstance(item, sketch_view.PointItem)]
        assert len(points) >= 2
        
        # Start coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [points[0].entity_id]
        
        # Show preview
        sketch_view._update_constraint_preview(points[1], points[1].pos())
        assert len(points[0].preview_items) > 0
        
        # End preview
        points[0].end_preview()
        assert len(points[0].preview_items) == 0
        
        # Verify items are removed from scene
        preview_count = sum(1 for item in sketch_view.scene.items() 
                          if item not in [points[0], points[1]])
        assert preview_count == 0

    def test_multiple_constraint_interaction(self, sketch_view):
        """Test interaction between different constraint previews."""
        # Get points and lines
        points = [item for item in sketch_view.scene.items() 
                 if isinstance(item, sketch_view.PointItem)]
        lines = [item for item in sketch_view.scene.items() 
                if isinstance(item, sketch_view.LineItem)]
        assert len(points) >= 2 and len(lines) >= 2
        
        # Start with coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [points[0].entity_id]
        sketch_view._update_constraint_preview(points[1], points[1].pos())
        
        # Switch to equal constraint
        sketch_view._start_constraint(ConstraintType.EQUAL)
        sketch_view.constraint_entities = [lines[0].entity_id]
        sketch_view._update_constraint_preview(lines[1], lines[1].pos())
        
        # Verify previous previews are cleaned up
        assert len(points[0].preview_items) == 0
        assert len(lines[0].preview_items) > 0

    def test_preview_performance(self, sketch_view):
        """Test performance of preview updates."""
        import time
        
        # Get two circles
        circles = [item for item in sketch_view.scene.items() 
                  if isinstance(item, sketch_view.CircleItem)]
        assert len(circles) >= 2
        
        # Start equal constraint
        sketch_view._start_constraint(ConstraintType.EQUAL)
        sketch_view.constraint_entities = [circles[0].entity_id]
        
        # Measure time for multiple preview updates
        start_time = time.time()
        for i in range(100):
            pos = QPointF(600 + i, 150)
            sketch_view._update_constraint_preview(circles[1], pos)
        end_time = time.time()
        
        # Average time per update should be reasonable
        avg_time = (end_time - start_time) / 100
        assert avg_time < 0.01  # Less than 10ms per update

    def test_preview_with_view_transform(self, sketch_view):
        """Test that previews work correctly with view transformations."""
        # Apply zoom and translation to view
        sketch_view.scale(2.0, 2.0)
        sketch_view.translate(100, 100)
        
        # Get two points
        points = [item for item in sketch_view.scene.items() 
                 if isinstance(item, sketch_view.PointItem)]
        assert len(points) >= 2
        
        # Start coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [points[0].entity_id]
        
        # Test preview with transformed coordinates
        scene_pos = sketch_view.mapToScene(
            sketch_view.mapFromScene(points[1].pos())
        )
        sketch_view._update_constraint_preview(points[1], scene_pos)
        
        # Verify preview elements are correctly positioned
        preview_items = points[0].preview_items
        assert len(preview_items) > 0
        
        # Check that preview items use scene coordinates (not view coordinates)
        for item in preview_items:
            if item.type() == item.Type.LineItem:
                line = item
                assert (line.line().p1() - points[0].pos()).manhattanLength() < 1
                assert (line.line().p2() - points[1].pos()).manhattanLength() < 1

    def test_parallel_preview_lines(self, sketch_view):
        """Test parallel constraint preview between two lines."""
        # Get two lines from the scene
        lines = [item for item in sketch_view.scene.items() 
                if isinstance(item, sketch_view.LineItem)]
        assert len(lines) >= 2
        
        # Start parallel constraint
        sketch_view._start_constraint(ConstraintType.PARALLEL)
        sketch_view.constraint_entities = [lines[0].entity_id]
        
        # Simulate hovering over second line
        sketch_view._update_constraint_preview(lines[1], lines[1].pos())
        
        # Verify preview elements
        preview_items = lines[0].preview_items
        assert len(preview_items) >= 4  # Should have extension lines and arrows
        
        # Check for extension lines (dashed)
        dashed_lines = [item for item in preview_items 
                       if (item.type() == item.Type.LineItem and 
                           item.pen().style() == Qt.PenStyle.DashLine)]
        assert len(dashed_lines) >= 2  # Should have at least two extension lines
        
        # Check for parallel indicators (arrows)
        arrows = [item for item in preview_items 
                 if (item.type() == item.Type.LineItem and 
                     item.pen().width() == 2)]  # Arrows use thicker pen
        assert len(arrows) >= 2  # Should have two arrow indicators

    def test_perpendicular_preview_lines(self, sketch_view):
        """Test perpendicular constraint preview between two lines."""
        # Get two lines from the scene
        lines = [item for item in sketch_view.scene.items() 
                if isinstance(item, sketch_view.LineItem)]
        assert len(lines) >= 2
        
        # Start perpendicular constraint
        sketch_view._start_constraint(ConstraintType.PERPENDICULAR)
        sketch_view.constraint_entities = [lines[0].entity_id]
        
        # Simulate hovering over second line
        sketch_view._update_constraint_preview(lines[1], lines[1].pos())
        
        # Verify preview elements
        preview_items = lines[0].preview_items
        assert len(preview_items) >= 2  # Should have preview line and right angle indicator
        
        # Check for preview line (dashed)
        preview_lines = [item for item in preview_items 
                        if (item.type() == item.Type.LineItem and 
                            item.pen().style() == Qt.PenStyle.DashLine)]
        assert len(preview_lines) >= 1
        
        # Check for right angle indicator (path)
        right_angle = next((item for item in preview_items 
                           if item.type() == item.Type.PathItem), None)
        assert right_angle is not None

    def test_edge_case_zero_length_line(self, sketch_view):
        """Test preview behavior with zero-length line."""
        # Create a zero-length line
        sketch_view._line_tool(None, QPointF(100, 100))
        sketch_view.start_pos = QPointF(100, 100)
        sketch_view._finish_line(QPointF(100, 100))
        
        # Get the zero-length line
        zero_line = next(item for item in sketch_view.scene.items() 
                        if (isinstance(item, sketch_view.LineItem) and 
                            item.start == item.end))
        
        # Try to start equal constraint with zero-length line
        sketch_view._start_constraint(ConstraintType.EQUAL)
        sketch_view.constraint_entities = [zero_line.entity_id]
        
        # Get a normal line for comparison
        normal_line = next(item for item in sketch_view.scene.items() 
                         if (isinstance(item, sketch_view.LineItem) and 
                             item.start != item.end))
        
        # Simulate hovering over normal line
        sketch_view._update_constraint_preview(normal_line, normal_line.pos())
        
        # Verify error indicator is shown
        preview_items = zero_line.preview_items
        assert any(item.pen().color() == Qt.GlobalColor.red 
                  for item in preview_items)

    def test_edge_case_overlapping_points(self, sketch_view):
        """Test preview behavior with overlapping points."""
        # Create two points at the same location
        pos = QPointF(150, 150)
        sketch_view._point_tool(None, pos)
        sketch_view._point_tool(None, pos)
        
        # Get the overlapping points
        points = [item for item in sketch_view.scene.items() 
                 if isinstance(item, sketch_view.PointItem)]
        overlapping_points = [p for p in points if p.pos() == pos]
        assert len(overlapping_points) >= 2
        
        # Start coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [overlapping_points[0].entity_id]
        
        # Simulate hovering over second point
        sketch_view._update_constraint_preview(overlapping_points[1], pos)
        
        # Verify special indicator for already-coincident points
        preview_items = overlapping_points[0].preview_items
        assert any(item.pen().color() == Qt.GlobalColor.green 
                  for item in preview_items)

    def test_solver_integration_coincident(self, sketch_view):
        """Test that preview aligns with solver output for coincident constraint."""
        # Get two points
        points = [item for item in sketch_view.scene.items() 
                 if isinstance(item, sketch_view.PointItem)][:2]
        assert len(points) >= 2
        
        # Record initial positions
        pos1 = points[0].pos()
        pos2 = points[1].pos()
        
        # Start coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [points[0].entity_id]
        
        # Update preview
        sketch_view._update_constraint_preview(points[1], points[1].pos())
        
        # Get preview endpoint (where points will meet)
        preview_line = next(item for item in points[0].preview_items 
                          if item.type() == item.Type.LineItem)
        preview_end = preview_line.line().p2()
        
        # Add constraint
        sketch_view._add_constraint()
        
        # Verify that points moved to preview position
        assert (points[0].pos() - preview_end).manhattanLength() < 1 or \
               (points[1].pos() - preview_end).manhattanLength() < 1

    def test_solver_integration_parallel(self, sketch_view):
        """Test that preview aligns with solver output for parallel constraint."""
        # Get two lines
        lines = [item for item in sketch_view.scene.items() 
                if isinstance(item, sketch_view.LineItem)][:2]
        assert len(lines) >= 2
        
        # Record initial angles
        def line_angle(line):
            dx = line.end.x() - line.start.x()
            dy = line.end.y() - line.start.y()
            return abs(dy / dx) if dx != 0 else float('inf')
        
        angle1 = line_angle(lines[0])
        
        # Start parallel constraint
        sketch_view._start_constraint(ConstraintType.PARALLEL)
        sketch_view.constraint_entities = [lines[0].entity_id]
        
        # Update preview
        sketch_view._update_constraint_preview(lines[1], lines[1].pos())
        
        # Add constraint
        sketch_view._add_constraint()
        
        # Verify that lines are parallel (same angle)
        angle2 = line_angle(lines[1])
        assert abs(angle1 - angle2) < 0.001

    def test_preview_update_frequency(self, sketch_view):
        """Test that preview updates respect the minimum update interval."""
        import time
        
        # Get two points
        points = [item for item in sketch_view.scene.items() 
                 if isinstance(item, sketch_view.PointItem)][:2]
        assert len(points) >= 2
        
        # Start coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [points[0].entity_id]
        
        # Try rapid updates
        last_update = 0
        min_interval = sketch_view.update_interval
        
        for i in range(10):
            current_time = time.time()
            sketch_view._update_constraint_preview(points[1], 
                                                QPointF(200 + i, 200))
            
            if i > 0:
                # Verify minimum interval between updates
                assert current_time - last_update >= min_interval
            
            last_update = current_time
            time.sleep(0.01)  # Small delay to simulate rapid mouse movement

    def test_preview_memory_management(self, sketch_view):
        """Test that preview items are properly managed in memory."""
        import gc
        
        # Get two points
        points = [item for item in sketch_view.scene.items() 
                 if isinstance(item, sketch_view.PointItem)][:2]
        assert len(points) >= 2
        
        # Start coincident constraint
        sketch_view._start_constraint(ConstraintType.COINCIDENT)
        sketch_view.constraint_entities = [points[0].entity_id]
        
        # Create and clear many previews
        preview_refs = []
        for i in range(100):
            sketch_view._update_constraint_preview(points[1], 
                                                QPointF(200 + i, 200))
            preview_refs.extend(points[0].preview_items)
            points[0].clear_preview_items()
        
        # Force garbage collection
        gc.collect()
        
        # Verify that old preview items are cleaned up
        for ref in preview_refs:
            assert ref.scene() is None  # Items should be removed from scene 