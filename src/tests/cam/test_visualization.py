"""
Tests for CAM toolpath visualization.
"""

import unittest
import numpy as np
from src.core.cam.visualization import ToolpathVisualizer
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

class TestToolpathVisualization(unittest.TestCase):
    """Test cases for toolpath visualization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.visualizer = ToolpathVisualizer(clearance_height=10.0)
        
        # Create a simple toolpath for testing
        self.test_toolpath = [
            np.array([0.0, 0.0, 10.0]),  # Start at clearance height
            np.array([0.0, 0.0, 0.0]),   # Plunge
            np.array([10.0, 0.0, 0.0]),  # Cut
            np.array([10.0, 10.0, 0.0]), # Cut
            np.array([0.0, 10.0, 0.0]),  # Cut
            np.array([0.0, 0.0, 0.0]),   # Cut
            np.array([0.0, 0.0, 10.0])   # Retract
        ]
        
        # Create test islands
        self.test_islands = [
            {  # Full height island
                'points': [
                    np.array([2.0, 2.0]),
                    np.array([4.0, 2.0]),
                    np.array([4.0, 4.0]),
                    np.array([2.0, 4.0]),
                    np.array([2.0, 2.0])
                ],
                'z_min': -5.0,
                'z_max': 0.0
            },
            {  # Partial height island
                'points': [
                    np.array([6.0, 6.0]),
                    np.array([8.0, 6.0]),
                    np.array([7.0, 8.0]),
                    np.array([6.0, 6.0])
                ],
                'z_min': -2.0,
                'z_max': 0.0
            }
        ]
        
    def test_basic_visualization(self):
        """Test basic toolpath visualization without islands."""
        try:
            self.visualizer.plot_toolpath(self.test_toolpath)
        except Exception as e:
            self.fail(f"Basic visualization failed: {str(e)}")
            
    def test_island_visualization(self):
        """Test visualization with islands."""
        try:
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                islands=self.test_islands
            )
        except Exception as e:
            self.fail(f"Island visualization failed: {str(e)}")
            
    def test_z_level_filtering(self):
        """Test Z-level filtering in visualization."""
        try:
            # Test at cutting level (Z=0)
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                islands=self.test_islands,
                z_filter=0.0
            )
            
            # Test at intermediate level (Z=-2.5)
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                islands=self.test_islands,
                z_filter=-2.5
            )
        except Exception as e:
            self.fail(f"Z-level filtering failed: {str(e)}")
            
    def test_visualization_options(self):
        """Test various visualization options."""
        try:
            # Test without clearance moves
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                show_clearance=False
            )
            
            # Test without entry points
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                show_entry_points=False
            )
            
            # Test with custom title
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                title="Test Visualization"
            )
        except Exception as e:
            self.fail(f"Visualization options test failed: {str(e)}")
            
    def test_integration_with_toolpath_generator(self):
        """Test visualization integration with toolpath generator."""
        # Create a simple tool
        tool = ToolParameters(
            tool_type=ToolType.ENDMILL,
            diameter=10.0,
            flutes=4,
            length=50.0,
            shank_diameter=10.0
        )
        
        # Create cutting parameters
        cutting_params = CuttingParameters(
            feedrate=1000.0,
            spindle_speed=10000.0,
            depth_of_cut=2.0,
            width_of_cut=5.0
        )
        
        # Create toolpath parameters with visualization enabled
        params = ToolpathParameters(
            toolpath_type=ToolpathType.POCKET,
            tool=tool,
            cutting_params=cutting_params,
            stock_dimensions=(100.0, 100.0, 20.0),
            islands=self.test_islands,
            debug_visualization=True,
            show_clearance_moves=True,
            show_entry_points=True
        )
        
        # Create toolpath generator
        generator = ToolpathGenerator(
            model=None,  # Mock mesh
            params=params,
            collision_detector=CollisionDetector(
                tool=tool,
                stock_model=None,
                fixtures=[]
            )
        )
        
        try:
            # Generate toolpath (should trigger visualization)
            generator.generate_toolpath()
        except Exception as e:
            self.fail(f"Integration test failed: {str(e)}")
            
    def test_complex_toolpath_visualization(self):
        """Test visualization with a complex toolpath and multiple islands."""
        # Create a more complex toolpath
        complex_toolpath = []
        clearance_z = 10.0
        cutting_z = 0.0
        
        # Add spiral pattern
        center = np.array([50.0, 50.0])
        for t in np.linspace(0, 4*np.pi, 100):
            r = 2 * t
            x = center[0] + r * np.cos(t)
            y = center[1] + r * np.sin(t)
            complex_toolpath.append(np.array([x, y, cutting_z]))
            
        # Add clearance moves between sections
        complex_toolpath.append(np.array([x, y, clearance_z]))
        
        # Add zigzag pattern
        for i in range(10):
            y = i * 5.0
            if i % 2 == 0:
                complex_toolpath.extend([
                    np.array([0.0, y, clearance_z]),
                    np.array([0.0, y, cutting_z]),
                    np.array([100.0, y, cutting_z]),
                    np.array([100.0, y, clearance_z])
                ])
            else:
                complex_toolpath.extend([
                    np.array([100.0, y, clearance_z]),
                    np.array([100.0, y, cutting_z]),
                    np.array([0.0, y, cutting_z]),
                    np.array([0.0, y, clearance_z])
                ])
                
        # Create multiple islands at different heights
        complex_islands = [
            {  # Tall rectangular island
                'points': [
                    np.array([20.0, 20.0]),
                    np.array([30.0, 20.0]),
                    np.array([30.0, 40.0]),
                    np.array([20.0, 40.0]),
                    np.array([20.0, 20.0])
                ],
                'z_min': -8.0,
                'z_max': 0.0
            },
            {  # Medium height circular-like island
                'points': [np.array([60.0 + 5.0*np.cos(t), 30.0 + 5.0*np.sin(t)])
                          for t in np.linspace(0, 2*np.pi, 16)],
                'z_min': -5.0,
                'z_max': 0.0
            },
            {  # Short triangular island
                'points': [
                    np.array([40.0, 60.0]),
                    np.array([50.0, 70.0]),
                    np.array([30.0, 70.0]),
                    np.array([40.0, 60.0])
                ],
                'z_min': -3.0,
                'z_max': 0.0
            }
        ]
        
        try:
            # Test full visualization
            self.visualizer.plot_toolpath(
                complex_toolpath,
                islands=complex_islands,
                title="Complex Toolpath Visualization"
            )
            
            # Test Z-level filtering at different depths
            for z in [0.0, -3.0, -5.0, -8.0]:
                self.visualizer.plot_toolpath(
                    complex_toolpath,
                    islands=complex_islands,
                    z_filter=z,
                    title=f"Z-Level: {z}"
                )
        except Exception as e:
            self.fail(f"Complex visualization test failed: {str(e)}")

    def test_tool_visualization(self):
        """Test tool visualization along toolpath."""
        # Create a simple tool
        tool = ToolParameters(
            tool_type=ToolType.ENDMILL,
            diameter=10.0,
            flutes=4,
            length=50.0,
            shank_diameter=10.0
        )
        
        try:
            # Test basic tool visualization
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                show_tool=True,
                tool_params=tool
            )
            
            # Test tool visualization with Z-level filtering
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                show_tool=True,
                tool_params=tool,
                z_filter=0.0
            )
            
            # Test tool visualization with islands
            self.visualizer.plot_toolpath(
                self.test_toolpath,
                show_tool=True,
                tool_params=tool,
                islands=self.test_islands
            )
        except Exception as e:
            self.fail(f"Tool visualization failed: {str(e)}")
            
    def test_tool_mesh_generation(self):
        """Test tool mesh generation and transformation."""
        # Create a simple tool
        tool = ToolParameters(
            tool_type=ToolType.ENDMILL,
            diameter=10.0,
            flutes=4,
            length=50.0,
            shank_diameter=10.0
        )
        
        # Create tool visualizer
        tool_vis = ToolVisualizer(tool)
        
        # Generate tool mesh
        vertices, faces = tool_vis.generate_tool_mesh()
        
        # Basic validation
        self.assertIsNotNone(vertices)
        self.assertIsNotNone(faces)
        self.assertGreater(len(vertices), 0)
        self.assertGreater(len(faces), 0)
        
        # Test mesh dimensions
        vertex_array = np.array(vertices)
        self.assertEqual(vertex_array.shape[1], 3)  # 3D points
        
        # Check diameter
        xy_coords = vertex_array[:, :2]
        max_radius = np.max(np.linalg.norm(xy_coords, axis=1))
        self.assertAlmostEqual(max_radius, tool.diameter/2, places=2)
        
        # Check length
        z_coords = vertex_array[:, 2]
        self.assertAlmostEqual(np.max(z_coords), tool.length, places=2)
        self.assertAlmostEqual(np.min(z_coords), 0.0, places=2)
        
        # Test mesh transformation
        position = np.array([10.0, 20.0, 30.0])
        direction = np.array([1.0, 1.0, 1.0])
        
        transformed_vertices = tool_vis.transform_tool_mesh(vertices, position, direction)
        
        # Check transformation
        self.assertEqual(transformed_vertices.shape, vertex_array.shape)
        
        # Check position
        center = np.mean(transformed_vertices, axis=0)
        self.assertAlmostEqual(center[0], position[0], places=2)
        self.assertAlmostEqual(center[1], position[1], places=2)
        
    def test_complex_tool_visualization(self):
        """Test tool visualization with complex toolpath and different tool types."""
        # Create different tool types
        tools = [
            ToolParameters(  # Standard endmill
                tool_type=ToolType.ENDMILL,
                diameter=10.0,
                flutes=4,
                length=50.0,
                shank_diameter=10.0
            ),
            ToolParameters(  # Ball endmill
                tool_type=ToolType.BALL_ENDMILL,
                diameter=8.0,
                flutes=2,
                length=40.0,
                shank_diameter=8.0
            ),
            ToolParameters(  # Bull nose endmill
                tool_type=ToolType.BULL_NOSE_ENDMILL,
                diameter=12.0,
                flutes=3,
                length=60.0,
                shank_diameter=12.0
            )
        ]
        
        # Create a complex spiral toolpath
        complex_toolpath = []
        clearance_z = 10.0
        cutting_z = 0.0
        
        # Add spiral pattern
        center = np.array([50.0, 50.0])
        for t in np.linspace(0, 4*np.pi, 100):
            r = 2 * t
            x = center[0] + r * np.cos(t)
            y = center[1] + r * np.sin(t)
            complex_toolpath.append(np.array([x, y, cutting_z]))
        
        try:
            # Test each tool type
            for tool in tools:
                self.visualizer.plot_toolpath(
                    complex_toolpath,
                    show_tool=True,
                    tool_params=tool,
                    title=f"{tool.tool_type.value} Visualization"
                )
                
                # Test with islands
                self.visualizer.plot_toolpath(
                    complex_toolpath,
                    show_tool=True,
                    tool_params=tool,
                    islands=self.test_islands,
                    title=f"{tool.tool_type.value} with Islands"
                )
        except Exception as e:
            self.fail(f"Complex tool visualization failed: {str(e)}")

if __name__ == '__main__':
    unittest.main() 