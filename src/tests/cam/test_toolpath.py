"""
Tests for CAM toolpath generation.
"""

import unittest
import numpy as np
from src.core.cam.toolpath import (
    ToolType,
    ToolParameters,
    CuttingParameters,
    ToolpathType,
    ToolpathParameters,
    ToolpathGenerator,
    CollisionDetector,
    PocketStrategy
)
from src.core.cam.geometry import (
    OffsetDirection,
    offset_contour,
    check_point_in_polygon,
    generate_parallel_paths
)

class TestToolpathGeneration(unittest.TestCase):
    """Test cases for toolpath generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a simple tool
        self.tool = ToolParameters(
            tool_type=ToolType.ENDMILL,
            diameter=10.0,  # 10mm endmill
            flutes=4,
            length=50.0,
            shank_diameter=10.0,
            max_doc=5.0,
            max_woc=8.0,
            max_feedrate=1000.0,
            max_spindle_speed=12000.0
        )
        
        # Create cutting parameters
        self.cutting_params = CuttingParameters(
            feedrate=800.0,
            spindle_speed=10000.0,
            depth_of_cut=2.0,
            width_of_cut=5.0
        )
        
        # Create toolpath parameters for pocket operations
        self.pocket_params = ToolpathParameters(
            toolpath_type=ToolpathType.POCKET,
            tool=self.tool,
            cutting_params=self.cutting_params,
            stock_dimensions=(100.0, 100.0, 20.0),
            stepover=0.5,
            pocket_strategy=PocketStrategy.HYBRID,
            pocket_angle=0.0
        )
        
        # Create a mock collision detector
        self.collision_detector = CollisionDetector(
            tool=self.tool,
            stock_model=None,  # Mock mesh
            fixtures=[]
        )
        
        # Create the toolpath generator
        self.generator = ToolpathGenerator(
            model=None,  # Mock mesh
            params=self.pocket_params,
            collision_detector=self.collision_detector
        )
        
        # Test pocket boundary (simple rectangle)
        self.test_pocket = [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 30.0]),
            np.array([0.0, 30.0]),
            np.array([0.0, 0.0])
        ]
        
    def test_contour_path_generation(self):
        """Test basic contour toolpath generation."""
        # Generate toolpath
        toolpath = self.generator._generate_contour_path()
        
        # Basic validation
        self.assertIsNotNone(toolpath)
        self.assertGreater(len(toolpath), 0)
        
        # Check that all points are 3D
        for point in toolpath:
            self.assertEqual(len(point), 3)
            
        # Check clearance height moves
        clearance_moves = [p for p in toolpath if p[2] == self.generator.clearance_height]
        self.assertGreater(len(clearance_moves), 0)
        
        # Check cutting moves
        cutting_moves = [p for p in toolpath if p[2] == 0.0]  # TODO: Update when Z depth is implemented
        self.assertGreater(len(cutting_moves), 0)
        
    def test_offset_contour(self):
        """Test contour offsetting."""
        # Create a simple square contour
        contour = [
            np.array([0.0, 0.0]),
            np.array([10.0, 0.0]),
            np.array([10.0, 10.0]),
            np.array([0.0, 10.0]),
            np.array([0.0, 0.0])
        ]
        
        # Test outside offset
        offset = 1.0
        outside_offset = offset_contour(contour, offset, OffsetDirection.OUTSIDE)
        
        self.assertIsNotNone(outside_offset)
        self.assertEqual(len(outside_offset), len(contour))
        
        # Check that offset points are further from origin
        original_distance = np.linalg.norm(contour[1])  # Check first non-zero point
        offset_distance = np.linalg.norm(outside_offset[1])
        self.assertGreater(offset_distance, original_distance)
        
        # Test inside offset
        inside_offset = offset_contour(contour, offset, OffsetDirection.INSIDE)
        
        self.assertIsNotNone(inside_offset)
        self.assertEqual(len(inside_offset), len(contour))
        
        # Check that offset points are closer to origin
        offset_distance = np.linalg.norm(inside_offset[1])
        self.assertLess(offset_distance, original_distance)
        
    def test_point_in_polygon(self):
        """Test point in polygon checking."""
        # Create a simple square
        polygon = [
            np.array([0.0, 0.0]),
            np.array([10.0, 0.0]),
            np.array([10.0, 10.0]),
            np.array([0.0, 10.0])
        ]
        
        # Test points
        inside_point = np.array([5.0, 5.0])
        outside_point = np.array([15.0, 15.0])
        edge_point = np.array([10.0, 5.0])
        
        self.assertTrue(check_point_in_polygon(inside_point, polygon))
        self.assertFalse(check_point_in_polygon(outside_point, polygon))
        # Edge points may be implementation dependent
        
    def test_toolpath_safety(self):
        """Test that toolpath includes proper safety moves."""
        toolpath = self.generator._generate_contour_path()
        
        # First move should be to clearance height
        self.assertEqual(toolpath[0][2], self.generator.clearance_height)
        
        # Last move should be to clearance height
        self.assertEqual(toolpath[-1][2], self.generator.clearance_height)
        
        # Check for proper sequence: clearance -> plunge -> cut -> retract
        for i in range(len(toolpath) - 3):
            if toolpath[i][2] == self.generator.clearance_height:
                # Next should be at same XY but clearance height
                self.assertEqual(toolpath[i+1][2], self.generator.clearance_height)
                self.assertEqual(toolpath[i+1][0], toolpath[i+2][0])
                self.assertEqual(toolpath[i+1][1], toolpath[i+2][1])
                # Then should plunge
                self.assertEqual(toolpath[i+2][2], 0.0)  # TODO: Update when Z depth is implemented
                
    def test_pocket_boundary_paths(self):
        """Test generation of pocket boundary following paths."""
        # Generate boundary paths
        boundary_paths = self.generator._generate_pocket_boundary_paths(
            self.test_pocket,
            tool_radius=5.0,
            stepover=5.0
        )
        
        # Basic validation
        self.assertIsNotNone(boundary_paths)
        self.assertGreater(len(boundary_paths), 0)
        
        # Check that paths are properly offset inward
        for i in range(len(boundary_paths)):
            path = boundary_paths[i]
            # Each path should have same number of points as original
            self.assertEqual(len(path), len(self.test_pocket))
            
            # Check that points are inside the original boundary
            for point in path[:-1]:  # Exclude last point (same as first)
                self.assertTrue(check_point_in_polygon(point, self.test_pocket))
                
            if i > 0:
                # Check stepover distance approximately
                prev_path = boundary_paths[i-1]
                dist = np.linalg.norm(path[0] - prev_path[0])
                self.assertAlmostEqual(dist, 5.0, delta=0.1)
    
    def test_pocket_zigzag_paths(self):
        """Test generation of pocket zigzag paths."""
        # Generate zigzag paths
        zigzag_paths = self.generator._generate_pocket_zigzag_paths(
            self.test_pocket,
            stepover=5.0,
            angle=0.0
        )
        
        # Basic validation
        self.assertIsNotNone(zigzag_paths)
        self.assertGreater(len(zigzag_paths), 0)
        
        # Check that paths are within boundary
        for path in zigzag_paths:
            for point in path:
                self.assertTrue(check_point_in_polygon(point, self.test_pocket))
        
        # Check stepover distance between adjacent paths
        if len(zigzag_paths) > 1:
            for i in range(len(zigzag_paths) - 1):
                path = zigzag_paths[i]
                next_path = zigzag_paths[i + 1]
                if len(path) > 0 and len(next_path) > 0:
                    dist = abs(path[0][1] - next_path[0][1])  # For horizontal paths
                    self.assertAlmostEqual(dist, 5.0, delta=0.1)
    
    def test_pocket_path_generation(self):
        """Test complete pocket toolpath generation."""
        # Generate toolpath
        toolpath = self.generator._generate_pocket_path()
        
        # Basic validation
        self.assertIsNotNone(toolpath)
        self.assertGreater(len(toolpath), 0)
        
        # Check that all points are 3D
        for point in toolpath:
            self.assertEqual(len(point), 3)
        
        # Validate safety moves
        clearance_moves = [p for p in toolpath if p[2] == self.generator.clearance_height]
        cutting_moves = [p for p in toolpath if p[2] == 0.0]
        
        self.assertGreater(len(clearance_moves), 0)
        self.assertGreater(len(cutting_moves), 0)
        
        # Check proper move sequencing
        for i in range(len(toolpath) - 3):
            if toolpath[i][2] == self.generator.clearance_height:
                # Next move should be at clearance height
                self.assertEqual(toolpath[i+1][2], self.generator.clearance_height)
                # Then plunge
                self.assertEqual(toolpath[i+2][2], 0.0)
    
    def test_pocket_strategies(self):
        """Test different pocket machining strategies."""
        # Test zigzag strategy
        self.generator.params.pocket_strategy = PocketStrategy.ZIGZAG
        zigzag_path = self.generator._generate_pocket_path()
        self.assertIsNotNone(zigzag_path)
        
        # Test spiral strategy
        self.generator.params.pocket_strategy = PocketStrategy.SPIRAL
        spiral_path = self.generator._generate_pocket_path()
        self.assertIsNotNone(spiral_path)
        
        # Test hybrid strategy
        self.generator.params.pocket_strategy = PocketStrategy.HYBRID
        hybrid_path = self.generator._generate_pocket_path()
        self.assertIsNotNone(hybrid_path)
        
        # Hybrid should have more points (combines both strategies)
        self.assertGreater(len(hybrid_path), len(zigzag_path))
        self.assertGreater(len(hybrid_path), len(spiral_path))
    
    def test_pocket_angle(self):
        """Test pocket toolpath generation with different angles."""
        angles = [0.0, np.pi/4, np.pi/2]  # 0, 45, 90 degrees
        
        for angle in angles:
            self.generator.params.pocket_angle = angle
            toolpath = self.generator._generate_pocket_path()
            
            # Basic validation
            self.assertIsNotNone(toolpath)
            self.assertGreater(len(toolpath), 0)
            
            # TODO: Add validation for path orientation
            # This would require analyzing the direction of zigzag paths

    def test_zigzag_clipping(self):
        """Test line clipping for zigzag paths."""
        # Create a non-convex test boundary (L-shape)
        boundary = [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 20.0]),
            np.array([20.0, 20.0]),
            np.array([20.0, 50.0]),
            np.array([0.0, 50.0]),
            np.array([0.0, 0.0])
        ]
        
        # Test horizontal zigzag (0 degrees)
        zigzag_paths = self.generator._generate_pocket_zigzag_paths(
            boundary,
            stepover=5.0,
            angle=0.0
        )
        
        # Validate clipped paths
        for path in zigzag_paths:
            # Check that path has exactly two points (start and end)
            self.assertEqual(len(path), 2)
            
            # Check that both points are inside boundary
            for point in path:
                self.assertTrue(check_point_in_polygon(point, boundary))
            
            # Check that path is horizontal (y coordinates match)
            self.assertAlmostEqual(path[0][1], path[1][1], delta=0.001)
        
        # Test diagonal zigzag (45 degrees)
        diagonal_paths = self.generator._generate_pocket_zigzag_paths(
            boundary,
            stepover=5.0,
            angle=np.pi/4
        )
        
        # Validate diagonal paths
        for path in diagonal_paths:
            self.assertEqual(len(path), 2)
            for point in path:
                self.assertTrue(check_point_in_polygon(point, boundary))
            
            # Check 45-degree angle
            dx = path[1][0] - path[0][0]
            dy = path[1][1] - path[0][1]
            if not np.isclose(dx, 0):  # Avoid division by zero
                angle = abs(np.arctan(dy/dx))
                self.assertAlmostEqual(angle, np.pi/4, delta=0.1)
        
        # Test vertical zigzag (90 degrees)
        vertical_paths = self.generator._generate_pocket_zigzag_paths(
            boundary,
            stepover=5.0,
            angle=np.pi/2
        )
        
        # Validate vertical paths
        for path in vertical_paths:
            self.assertEqual(len(path), 2)
            for point in path:
                self.assertTrue(check_point_in_polygon(point, boundary))
            
            # Check that path is vertical (x coordinates match)
            self.assertAlmostEqual(path[0][0], path[1][0], delta=0.001)
        
        # Test path spacing
        def check_path_spacing(paths, stepover):
            for i in range(len(paths) - 1):
                path1 = paths[i]
                path2 = paths[i + 1]
                # Calculate minimum distance between paths
                dist = min(
                    np.linalg.norm(path1[0] - path2[0]),
                    np.linalg.norm(path1[0] - path2[1]),
                    np.linalg.norm(path1[1] - path2[0]),
                    np.linalg.norm(path1[1] - path2[1])
                )
                self.assertGreaterEqual(dist, stepover * 0.9)  # Allow 10% tolerance
                self.assertLessEqual(dist, stepover * 1.1)
        
        check_path_spacing(zigzag_paths, 5.0)
        check_path_spacing(diagonal_paths, 5.0)
        check_path_spacing(vertical_paths, 5.0)
        
    def test_complex_boundary_clipping(self):
        """Test line clipping with complex boundaries."""
        # Create a boundary with an internal island
        outer_boundary = [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 50.0]),
            np.array([0.0, 50.0]),
            np.array([0.0, 0.0])
        ]
        
        island = [
            np.array([20.0, 20.0]),
            np.array([30.0, 20.0]),
            np.array([30.0, 30.0]),
            np.array([20.0, 30.0]),
            np.array([20.0, 20.0])
        ]
        
        # Test zigzag paths with island
        zigzag_paths = self.generator._generate_pocket_zigzag_paths(
            outer_boundary,  # TODO: Add support for islands
            stepover=5.0,
            angle=0.0
        )
        
        # Validate paths
        for path in zigzag_paths:
            # Check that path endpoints are valid
            self.assertEqual(len(path), 2)
            for point in path:
                # Point should be inside outer boundary
                self.assertTrue(check_point_in_polygon(point, outer_boundary))
                # TODO: Point should be outside island
                # self.assertFalse(check_point_in_polygon(point, island))
            
        # Test path continuity
        for i in range(len(zigzag_paths) - 1):
            path1 = zigzag_paths[i]
            path2 = zigzag_paths[i + 1]
            # End of path1 should be close to start of path2
            dist = np.linalg.norm(path1[1] - path2[0])
            self.assertLessEqual(dist, 5.0 * 1.5)  # Allow some tolerance for path connections

    def test_zigzag_with_islands(self):
        """Test zigzag path generation with islands."""
        # Create test boundary and island
        boundary = [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 50.0]),
            np.array([0.0, 50.0]),
            np.array([0.0, 0.0])
        ]
        
        island = [
            np.array([20.0, 20.0]),
            np.array([30.0, 20.0]),
            np.array([30.0, 30.0]),
            np.array([20.0, 30.0]),
            np.array([20.0, 20.0])
        ]
        
        # Generate zigzag paths with island
        zigzag_paths = self.generator._generate_pocket_zigzag_paths(
            boundary,
            stepover=5.0,
            angle=0.0,
            islands=[island]
        )
        
        # Basic validation
        self.assertIsNotNone(zigzag_paths)
        self.assertGreater(len(zigzag_paths), 0)
        
        # Check that paths avoid island
        for path in zigzag_paths:
            # Check path endpoints
            self.assertEqual(len(path), 2)
            for point in path:
                # Point should be inside boundary
                self.assertTrue(check_point_in_polygon(point, boundary))
                # Point should be outside island
                self.assertFalse(check_point_in_polygon(point, island))
            
            # Check that path doesn't intersect island
            start, end = path
            # Sample points along the path
            for t in np.linspace(0, 1, 10):
                point = start + t * (end - start)
                self.assertFalse(check_point_in_polygon(point, island))
                
    def test_pocket_with_multiple_islands(self):
        """Test pocket toolpath generation with multiple islands."""
        # Create test boundary and islands
        boundary = [
            np.array([0.0, 0.0]),
            np.array([100.0, 0.0]),
            np.array([100.0, 100.0]),
            np.array([0.0, 100.0]),
            np.array([0.0, 0.0])
        ]
        
        islands = [
            # First island (square)
            [
                np.array([20.0, 20.0]),
                np.array([30.0, 20.0]),
                np.array([30.0, 30.0]),
                np.array([20.0, 30.0]),
                np.array([20.0, 20.0])
            ],
            # Second island (triangle)
            [
                np.array([60.0, 60.0]),
                np.array([80.0, 60.0]),
                np.array([70.0, 80.0]),
                np.array([60.0, 60.0])
            ]
        ]
        
        # Update generator parameters
        self.generator.params.islands = islands
        
        # Generate pocket toolpath
        toolpath = self.generator._generate_pocket_path()
        
        # Basic validation
        self.assertIsNotNone(toolpath)
        self.assertGreater(len(toolpath), 0)
        
        # Extract cutting moves (Z = 0)
        cutting_moves = [p for p in toolpath if p[2] == 0.0]
        
        # Check that cutting moves avoid islands
        for point in cutting_moves:
            xy_point = point[:2]  # Get XY coordinates
            # Point should be inside boundary
            self.assertTrue(check_point_in_polygon(xy_point, boundary))
            # Point should be outside all islands
            for island in islands:
                self.assertFalse(check_point_in_polygon(xy_point, island))
                
    def test_boundary_paths_with_islands(self):
        """Test boundary following paths with islands."""
        # Create test boundary and island
        boundary = [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 50.0]),
            np.array([0.0, 50.0]),
            np.array([0.0, 0.0])
        ]
        
        island = [
            np.array([20.0, 20.0]),
            np.array([30.0, 20.0]),
            np.array([30.0, 30.0]),
            np.array([20.0, 30.0]),
            np.array([20.0, 20.0])
        ]
        
        # Generate boundary paths with island
        boundary_paths = self.generator._generate_pocket_boundary_paths(
            boundary,
            tool_radius=5.0,
            stepover=5.0,
            islands=[island]
        )
        
        # Basic validation
        self.assertIsNotNone(boundary_paths)
        self.assertGreater(len(boundary_paths), 0)
        
        # Check that paths maintain proper offset and avoid island
        for path in boundary_paths:
            # Check that points are inside boundary
            for point in path:
                self.assertTrue(check_point_in_polygon(point, boundary))
                # Point should be outside island with tool radius clearance
                offset_island = offset_contour(
                    island,
                    5.0,  # Tool radius
                    OffsetDirection.OUTSIDE
                )
                self.assertFalse(check_point_in_polygon(point, offset_island))
                
    def test_complex_pocket_with_islands(self):
        """Test pocket machining with complex boundary and islands."""
        # Create L-shaped boundary
        boundary = [
            np.array([0.0, 0.0]),
            np.array([100.0, 0.0]),
            np.array([100.0, 30.0]),
            np.array([30.0, 30.0]),
            np.array([30.0, 100.0]),
            np.array([0.0, 100.0]),
            np.array([0.0, 0.0])
        ]
        
        # Create circular-like island (approximated with polygon)
        n_points = 16
        radius = 10.0
        center = np.array([50.0, 15.0])
        island = []
        for i in range(n_points):
            angle = 2 * np.pi * i / n_points
            point = center + radius * np.array([np.cos(angle), np.sin(angle)])
            island.append(point)
        island.append(island[0])  # Close the polygon
        
        # Test different strategies
        strategies = [
            PocketStrategy.ZIGZAG,
            PocketStrategy.SPIRAL,
            PocketStrategy.HYBRID
        ]
        
        for strategy in strategies:
            # Update generator parameters
            self.generator.params.pocket_strategy = strategy
            self.generator.params.islands = [island]
            
            # Generate toolpath
            toolpath = self.generator._generate_pocket_path()
            
            # Basic validation
            self.assertIsNotNone(toolpath)
            self.assertGreater(len(toolpath), 0)
            
            # Check cutting moves
            cutting_moves = [p for p in toolpath if p[2] == 0.0]
            for point in cutting_moves:
                xy_point = point[:2]
                # Point should be inside boundary
                self.assertTrue(check_point_in_polygon(xy_point, boundary))
                # Point should be outside island with tool radius clearance
                offset_island = offset_contour(
                    island,
                    self.generator.params.tool.diameter / 2.0,
                    OffsetDirection.OUTSIDE
                )
                self.assertFalse(check_point_in_polygon(xy_point, offset_island))
                
            # Strategy-specific checks
            if strategy == PocketStrategy.ZIGZAG:
                # Check for parallel segments
                self._check_parallel_segments(cutting_moves)
            elif strategy == PocketStrategy.SPIRAL:
                # Check for continuous boundary following
                self._check_boundary_following(cutting_moves)
                
    def _check_parallel_segments(self, points):
        """Helper to check for parallel toolpath segments."""
        # Group points into segments
        segments = []
        for i in range(0, len(points) - 1, 2):
            if i + 1 < len(points):
                segments.append((points[i], points[i + 1]))
        
        # Check parallel segments
        if len(segments) > 1:
            for i in range(len(segments) - 1):
                v1 = segments[i][1] - segments[i][0]
                v2 = segments[i + 1][1] - segments[i + 1][0]
                # Normalize vectors
                v1 = v1 / np.linalg.norm(v1)
                v2 = v2 / np.linalg.norm(v2)
                # Check if parallel or anti-parallel
                dot_product = abs(np.dot(v1[:2], v2[:2]))  # Use only XY components
                self.assertGreater(dot_product, 0.9)  # Allow some deviation
                
    def _check_boundary_following(self, points):
        """Helper to check for boundary following behavior."""
        # Check that consecutive points maintain similar distance to boundary
        if len(points) > 1:
            distances = []
            for point in points:
                # Calculate minimum distance to boundary
                # This is a simplified check - in practice, you'd want to
                # calculate actual distance to boundary
                distances.append(point[0] + point[1])  # Simple metric
            
            # Check that distances change gradually
            for i in range(len(distances) - 1):
                diff = abs(distances[i + 1] - distances[i])
                self.assertLess(diff, 5.0)  # Allow gradual changes

    def test_near_boundary_island(self):
        """Test pocket machining with an island very close to the boundary."""
        # Create boundary
        boundary = [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 50.0]),
            np.array([0.0, 50.0]),
            np.array([0.0, 0.0])
        ]
        
        # Create island very close to boundary (within one tool diameter)
        tool_diameter = self.generator.params.tool.diameter
        island = [
            np.array([45.0, 20.0]),  # Close to right boundary
            np.array([48.0, 20.0]),
            np.array([48.0, 30.0]),
            np.array([45.0, 30.0]),
            np.array([45.0, 20.0])
        ]
        
        # Generate toolpath with near-boundary island
        self.generator.params.islands = [island]
        toolpath = self.generator._generate_pocket_path()
        
        # Basic validation
        self.assertIsNotNone(toolpath)
        self.assertGreater(len(toolpath), 0)
        
        # Check cutting moves
        cutting_moves = [p for p in toolpath if p[2] == 0.0]
        for point in cutting_moves:
            xy_point = point[:2]
            # Point should be inside boundary
            self.assertTrue(check_point_in_polygon(xy_point, boundary))
            
            # Point should maintain proper clearance from both boundary and island
            offset_island = offset_contour(
                island,
                tool_diameter / 2.0,
                OffsetDirection.OUTSIDE
            )
            self.assertFalse(check_point_in_polygon(xy_point, offset_island))
            
            # Check clearance from boundary
            min_dist_to_boundary = min(
                abs(xy_point[0] - 50.0),  # Distance to right boundary
                abs(xy_point[0] - 0.0),   # Distance to left boundary
                abs(xy_point[1] - 50.0),  # Distance to top boundary
                abs(xy_point[1] - 0.0)    # Distance to bottom boundary
            )
            self.assertGreaterEqual(min_dist_to_boundary, tool_diameter / 2.0)
            
    def test_non_convex_island(self):
        """Test pocket machining with a non-convex (concave) island."""
        # Create boundary
        boundary = [
            np.array([0.0, 0.0]),
            np.array([60.0, 0.0]),
            np.array([60.0, 60.0]),
            np.array([0.0, 60.0]),
            np.array([0.0, 0.0])
        ]
        
        # Create U-shaped (non-convex) island
        island = [
            np.array([20.0, 20.0]),  # Start at bottom-left
            np.array([40.0, 20.0]),  # Bottom edge
            np.array([40.0, 35.0]),  # Right up
            np.array([35.0, 35.0]),  # Left indent
            np.array([35.0, 25.0]),  # Down
            np.array([25.0, 25.0]),  # Left
            np.array([25.0, 35.0]),  # Up
            np.array([20.0, 35.0]),  # Left to start
            np.array([20.0, 20.0])   # Close polygon
        ]
        
        # Generate toolpath with non-convex island
        self.generator.params.islands = [island]
        
        # Test with different strategies
        for strategy in [PocketStrategy.ZIGZAG, PocketStrategy.SPIRAL]:
            self.generator.params.pocket_strategy = strategy
            toolpath = self.generator._generate_pocket_path()
            
            # Basic validation
            self.assertIsNotNone(toolpath)
            self.assertGreater(len(toolpath), 0)
            
            # Check cutting moves
            cutting_moves = [p for p in toolpath if p[2] == 0.0]
            for point in cutting_moves:
                xy_point = point[:2]
                # Point should be inside boundary
                self.assertTrue(check_point_in_polygon(xy_point, boundary))
                
                # Point should be outside offset island
                offset_island = offset_contour(
                    island,
                    self.generator.params.tool.diameter / 2.0,
                    OffsetDirection.OUTSIDE
                )
                self.assertFalse(check_point_in_polygon(xy_point, offset_island))
            
            if strategy == PocketStrategy.ZIGZAG:
                # For zigzag, verify handling of multiple intersections
                # Sample points along each path to ensure no intersection
                for i in range(len(cutting_moves) - 1):
                    start = cutting_moves[i][:2]
                    end = cutting_moves[i + 1][:2]
                    # Sample points along the line
                    for t in np.linspace(0, 1, 20):
                        point = start + t * (end - start)
                        self.assertFalse(check_point_in_polygon(point, island))
                        
            elif strategy == PocketStrategy.SPIRAL:
                # For spiral, verify continuous boundary following
                self._check_boundary_following(cutting_moves)
                
                # Check that paths handle concave regions properly
                # This is a simplified check - we verify that points don't
                # jump across the concave region
                for i in range(len(cutting_moves) - 1):
                    p1 = cutting_moves[i][:2]
                    p2 = cutting_moves[i + 1][:2]
                    dist = np.linalg.norm(p2 - p1)
                    # Points shouldn't be too far apart (no jumping across void)
                    self.assertLess(dist, self.generator.params.tool.diameter * 2.0)

    def test_variable_z_depth(self):
        """Test pocket toolpath generation with multiple Z-levels."""
        # Set Z-depth parameters
        self.generator.params.start_z = 0.0
        self.generator.params.pocket_depth = 6.0
        self.generator.params.step_down = 2.0
        self.generator.params.final_pass_depth = 0.5
        
        # Generate toolpath
        toolpath = self.generator._generate_pocket_path()
        
        # Basic validation
        self.assertIsNotNone(toolpath)
        self.assertGreater(len(toolpath), 0)
        
        # Extract unique Z-levels from cutting moves
        z_levels = sorted(set(p[2] for p in toolpath if p[2] < self.generator.clearance_height))
        expected_z = [0.0, -2.0, -4.0, -6.0]  # Including final pass
        
        # Check Z-levels
        self.assertEqual(len(z_levels), len(expected_z))
        for actual, expected in zip(z_levels, expected_z):
            self.assertAlmostEqual(actual, expected, delta=0.001)
            
        # Check that each level has cutting moves
        for z_level in z_levels:
            level_moves = [p for p in toolpath if p[2] == z_level]
            self.assertGreater(len(level_moves), 0)
            
        # Verify safe transitions between levels
        for i in range(len(toolpath) - 1):
            p1 = toolpath[i]
            p2 = toolpath[i + 1]
            
            # If changing Z-level significantly, should go through clearance height
            if abs(p2[2] - p1[2]) > self.generator.params.step_down:
                # Find points between p1 and p2 that are at clearance height
                between_points = toolpath[i:i+3]  # Look at small window
                clearance_moves = [p for p in between_points if p[2] == self.generator.clearance_height]
                self.assertGreater(len(clearance_moves), 0)
                
    def test_entry_moves(self):
        """Test different types of Z-level entry moves."""
        # Test plunge entry
        self.generator.params.entry_type = "plunge"
        plunge_path = self.generator._generate_pocket_path()
        
        # Verify direct plunge moves
        for i in range(len(plunge_path) - 1):
            p1 = plunge_path[i]
            p2 = plunge_path[i + 1]
            if p1[2] == self.generator.clearance_height and p2[2] < self.generator.clearance_height:
                # Should be vertical plunge (same XY)
                self.assertAlmostEqual(p1[0], p2[0], delta=0.001)
                self.assertAlmostEqual(p1[1], p2[1], delta=0.001)
        
        # Test ramp entry
        self.generator.params.entry_type = "ramp"
        self.generator.params.ramp_angle = 3.0  # 3 degree ramp
        ramp_path = self.generator._generate_pocket_path()
        
        # Verify ramping moves
        for i in range(len(ramp_path) - 1):
            p1 = ramp_path[i]
            p2 = ramp_path[i + 1]
            if p1[2] == self.generator.clearance_height and p2[2] < self.generator.clearance_height:
                # Find the ramp sequence
                ramp_points = []
                j = i + 1
                while j < len(ramp_path) and ramp_path[j][2] > ramp_path[j-1][2]:
                    ramp_points.append(ramp_path[j])
                    j += 1
                
                # Check ramp angle
                if len(ramp_points) > 1:
                    z_diff = abs(ramp_points[-1][2] - ramp_points[0][2])
                    xy_diff = np.linalg.norm(ramp_points[-1][:2] - ramp_points[0][:2])
                    if xy_diff > 0:  # Avoid division by zero
                        angle = np.degrees(np.arctan(z_diff / xy_diff))
                        self.assertAlmostEqual(angle, self.generator.params.ramp_angle, delta=0.5)
                        
    def test_final_pass_depth(self):
        """Test final finishing pass at bottom of pocket."""
        # Set up test parameters
        self.generator.params.start_z = 0.0
        self.generator.params.pocket_depth = 10.0
        self.generator.params.step_down = 4.0
        self.generator.params.final_pass_depth = 1.0
        
        # Generate toolpath
        toolpath = self.generator._generate_pocket_path()
        
        # Get cutting moves at each Z-level
        z_levels = sorted(set(p[2] for p in toolpath if p[2] < self.generator.clearance_height))
        
        # Check that we have the correct number of levels
        expected_levels = [0.0, -4.0, -8.0, -10.0]  # Including final pass
        self.assertEqual(len(z_levels), len(expected_levels))
        
        # Verify final pass depth
        self.assertAlmostEqual(z_levels[-1], -self.generator.params.pocket_depth, delta=0.001)
        
        # Check that the step to final pass is equal to or less than final_pass_depth
        final_step = abs(z_levels[-1] - z_levels[-2])
        self.assertLessEqual(final_step, self.generator.params.final_pass_depth)
        
    def test_z_depth_with_islands(self):
        """Test variable Z-depth pocket machining with islands."""
        # Create test boundary and island
        boundary = [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 50.0]),
            np.array([0.0, 50.0]),
            np.array([0.0, 0.0])
        ]
        
        island = [
            np.array([20.0, 20.0]),
            np.array([30.0, 20.0]),
            np.array([30.0, 30.0]),
            np.array([20.0, 30.0]),
            np.array([20.0, 20.0])
        ]
        
        # Set up Z-depth parameters
        self.generator.params.islands = [island]
        self.generator.params.start_z = 0.0
        self.generator.params.pocket_depth = 5.0
        self.generator.params.step_down = 2.5
        
        # Generate toolpath
        toolpath = self.generator._generate_pocket_path()
        
        # Check Z-levels
        z_levels = sorted(set(p[2] for p in toolpath if p[2] < self.generator.clearance_height))
        expected_z = [0.0, -2.5, -5.0]
        
        self.assertEqual(len(z_levels), len(expected_z))
        for actual, expected in zip(z_levels, expected_z):
            self.assertAlmostEqual(actual, expected, delta=0.001)
        
        # Verify island avoidance at each Z-level
        for z_level in z_levels:
            level_moves = [p for p in toolpath if p[2] == z_level]
            for point in level_moves:
                # Point should be inside boundary
                self.assertTrue(check_point_in_polygon(point[:2], boundary))
                # Point should be outside island
                self.assertFalse(check_point_in_polygon(point[:2], island))
                
        # Check proper transitions near island
        for i in range(len(toolpath) - 1):
            p1 = toolpath[i]
            p2 = toolpath[i + 1]
            
            # If points are at same Z-level and not at clearance height
            if p1[2] == p2[2] and p1[2] < self.generator.clearance_height:
                # Create line segment between points
                for t in np.linspace(0, 1, 10):
                    point = p1[:2] + t * (p2[:2] - p1[:2])
                    # Check that interpolated point doesn't intersect island
                    self.assertFalse(check_point_in_polygon(point, island))

    def test_helix_entry(self):
        """Test helix entry moves in pocket machining."""
        # Set up test parameters
        self.generator.params.entry_type = "helix"
        self.generator.params.helix_diameter = 0.8  # 80% of tool diameter
        self.generator.params.helix_angle = 5.0  # 5 degrees
        self.generator.params.start_z = 0.0
        self.generator.params.pocket_depth = 10.0
        self.generator.params.step_down = 5.0
        
        # Generate toolpath
        toolpath = self.generator._generate_pocket_path()
        
        # Basic validation
        self.assertIsNotNone(toolpath)
        self.assertGreater(len(toolpath), 0)
        
        # Find helix entry moves
        helix_entries = []
        current_entry = []
        
        for i in range(len(toolpath) - 1):
            p1 = toolpath[i]
            p2 = toolpath[i + 1]
            
            # Check for start of helix (transition from clearance to cutting height)
            if p1[2] == self.generator.clearance_height and p2[2] < self.generator.clearance_height:
                current_entry = [p1, p2]
            # Continue collecting helix points
            elif len(current_entry) > 0 and p2[2] < self.generator.clearance_height:
                current_entry.append(p2)
                # Check if helix is complete (reached target Z)
                if abs(p2[2] - (-5.0)) < 0.01 or abs(p2[2] - (-10.0)) < 0.01:
                    helix_entries.append(current_entry)
                    current_entry = []
        
        # Should have at least one helix entry
        self.assertGreater(len(helix_entries), 0)
        
        # Validate each helix entry
        for entry in helix_entries:
            # Check number of points
            self.assertGreater(len(entry), 16)  # At least 16 points per revolution
            
            # Check helix properties
            tool_radius = self.generator.params.tool.diameter / 2.0
            expected_radius = tool_radius * self.generator.params.helix_diameter / 2.0
            
            # Get helix center (first point XY)
            center = entry[0][:2]
            
            # Check points form a helix
            for i in range(1, len(entry)):
                point = entry[i]
                # Calculate radius from center
                radius = np.linalg.norm(point[:2] - center)
                self.assertAlmostEqual(radius, expected_radius, delta=0.1)
                
                if i > 1:
                    # Check Z decreases monotonically
                    self.assertLess(point[2], entry[i-1][2])
                    
                    # Check angle between consecutive points
                    v1 = entry[i-1][:2] - center
                    v2 = point[:2] - center
                    angle = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
                    # Angle should be small for smooth helix
                    self.assertLess(angle, np.pi/4)
                    
    def test_helix_with_islands(self):
        """Test helix entry moves with islands present."""
        # Create test boundary and island
        boundary = [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 50.0]),
            np.array([0.0, 50.0]),
            np.array([0.0, 0.0])
        ]
        
        island = [
            np.array([20.0, 20.0]),
            np.array([30.0, 20.0]),
            np.array([30.0, 30.0]),
            np.array([20.0, 30.0]),
            np.array([20.0, 20.0])
        ]
        
        # Set up test parameters
        self.generator.params.islands = [island]
        self.generator.params.entry_type = "helix"
        self.generator.params.helix_diameter = 0.8
        self.generator.params.helix_angle = 5.0
        self.generator.params.start_z = 0.0
        self.generator.params.pocket_depth = 10.0
        self.generator.params.step_down = 5.0
        
        # Generate toolpath
        toolpath = self.generator._generate_pocket_path()
        
        # Basic validation
        self.assertIsNotNone(toolpath)
        self.assertGreater(len(toolpath), 0)
        
        # Find helix entry points
        helix_points = []
        for i in range(len(toolpath) - 1):
            p1 = toolpath[i]
            p2 = toolpath[i + 1]
            if p1[2] == self.generator.clearance_height and p2[2] < self.generator.clearance_height:
                # Found start of helix
                while i + 1 < len(toolpath) and toolpath[i + 1][2] < self.generator.clearance_height:
                    helix_points.append(toolpath[i + 1][:2])
                    i += 1
                break
        
        # Check that helix points don't intersect with island
        offset_island = offset_contour(
            island,
            self.generator.params.tool.diameter / 2.0,
            OffsetDirection.OUTSIDE
        )
        
        for point in helix_points:
            # Point should be inside boundary
            self.assertTrue(check_point_in_polygon(point, boundary))
            # Point should be outside offset island
            self.assertFalse(check_point_in_polygon(point, offset_island))
            
    def test_helix_parameters(self):
        """Test different helix parameter combinations."""
        test_params = [
            # (diameter, angle, revolutions)
            (0.6, 3.0, None),  # Smaller diameter, shallow angle
            (1.0, 10.0, None),  # Larger diameter, steeper angle
            (0.8, 5.0, 2.0),   # Fixed number of revolutions
        ]
        
        for diameter, angle, revolutions in test_params:
            # Set parameters
            self.generator.params.entry_type = "helix"
            self.generator.params.helix_diameter = diameter
            self.generator.params.helix_angle = angle
            self.generator.params.helix_revolutions = revolutions
            self.generator.params.start_z = 0.0
            self.generator.params.pocket_depth = 10.0
            self.generator.params.step_down = 10.0  # Single pass for easier testing
            
            # Generate toolpath
            toolpath = self.generator._generate_pocket_path()
            
            # Find helix points
            helix_points = []
            for i in range(len(toolpath) - 1):
                p1 = toolpath[i]
                p2 = toolpath[i + 1]
                if p1[2] == self.generator.clearance_height and p2[2] < self.generator.clearance_height:
                    while i + 1 < len(toolpath) and toolpath[i + 1][2] < self.generator.clearance_height:
                        helix_points.append(toolpath[i + 1])
                        i += 1
                    break
            
            # Validate helix properties
            tool_radius = self.generator.params.tool.diameter / 2.0
            expected_radius = tool_radius * diameter / 2.0
            
            # Get helix center
            center = helix_points[0][:2]
            
            # Check radius
            for point in helix_points:
                radius = np.linalg.norm(point[:2] - center)
                self.assertAlmostEqual(radius, expected_radius, delta=0.1)
            
            # Check total angle traversed
            if revolutions is not None:
                # Calculate total angle traversed
                total_angle = 0.0
                for i in range(1, len(helix_points)):
                    v1 = helix_points[i-1][:2] - center
                    v2 = helix_points[i][:2] - center
                    angle = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
                    total_angle += angle
                
                expected_angle = revolutions * 2 * np.pi
                self.assertAlmostEqual(total_angle, expected_angle, delta=0.5)
            
            # Check Z-depth distribution
            z_values = [p[2] for p in helix_points]
            self.assertAlmostEqual(min(z_values), -10.0, delta=0.1)  # Should reach target depth
            # Z should decrease approximately linearly
            z_diffs = np.diff(z_values)
            avg_diff = np.mean(z_diffs)
            max_deviation = np.max(np.abs(z_diffs - avg_diff))
            self.assertLess(max_deviation, 0.1)  # Z steps should be fairly uniform

if __name__ == '__main__':
    unittest.main() 