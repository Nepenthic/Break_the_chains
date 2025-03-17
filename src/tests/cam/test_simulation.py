"""
Tests for material removal simulation.
"""

import unittest
import numpy as np
import time
import psutil
import os
from src.core.cam.simulation import (
    MaterialSimulator,
    StockParameters,
    StockType
)

class TestMaterialSimulation(unittest.TestCase):
    """Test cases for material removal simulation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create rectangular stock
        self.rect_stock_params = StockParameters(
            stock_type=StockType.RECTANGULAR,
            dimensions=(100.0, 50.0, 25.0),  # length, width, height
            voxel_size=1.0
        )
        self.rect_simulator = MaterialSimulator(self.rect_stock_params)
        
        # Create cylindrical stock
        self.cyl_stock_params = StockParameters(
            stock_type=StockType.CYLINDRICAL,
            dimensions=(80.0, 30.0, 0.0),  # diameter, height
            voxel_size=1.0
        )
        self.cyl_simulator = MaterialSimulator(self.cyl_stock_params)
        
        # Create test toolpath
        self.test_toolpath = [
            np.array([10.0, 10.0, 20.0]),  # Start point
            np.array([10.0, 40.0, 20.0]),  # Line cut
            np.array([90.0, 40.0, 20.0]),  # Line cut
            np.array([90.0, 10.0, 20.0]),  # Line cut
            np.array([10.0, 10.0, 20.0])   # Close rectangle
        ]
        
        # Create test islands
        self.test_islands = [
            {  # Square island
                'points': [
                    np.array([40.0, 20.0]),
                    np.array([60.0, 20.0]),
                    np.array([60.0, 30.0]),
                    np.array([40.0, 30.0]),
                    np.array([40.0, 20.0])
                ],
                'z_min': 0.0,
                'z_max': 25.0
            }
        ]
        
        # Create large stock for performance testing
        self.large_stock_params = StockParameters(
            stock_type=StockType.RECTANGULAR,
            dimensions=(1000.0, 1000.0, 100.0),  # Large stock
            voxel_size=1.0
        )
        self.large_simulator = MaterialSimulator(self.large_stock_params)
        
        # Create complex toolpath for performance testing
        self.complex_toolpath = []
        num_points = 1000
        for i in range(num_points):
            t = i / (num_points - 1)
            x = 100 * np.cos(2 * np.pi * t)
            y = 100 * np.sin(2 * np.pi * t)
            z = 50 * (1 - t)
            self.complex_toolpath.append(np.array([x, y, z]))
    
    def test_stock_initialization(self):
        """Test stock initialization for different types."""
        # Test rectangular stock dimensions
        self.assertEqual(self.rect_simulator.nx, 100)
        self.assertEqual(self.rect_simulator.ny, 50)
        self.assertEqual(self.rect_simulator.nz, 25)
        self.assertTrue(np.all(self.rect_simulator.voxel_grid.toarray()))
        
        # Test cylindrical stock dimensions and shape
        radius = self.cyl_stock_params.dimensions[0] / 2
        center = np.array([40, 40])  # Center of the grid
        
        for i in range(self.cyl_simulator.nx):
            for j in range(self.cyl_simulator.ny):
                x = self.cyl_simulator.X[i,j,0]
                y = self.cyl_simulator.Y[i,j,0]
                distance = np.sqrt(x**2 + y**2)
                
                if distance <= radius:
                    self.assertTrue(
                        self.cyl_simulator.voxel_grid[self.cyl_simulator._get_voxel_index(i,j,0)]
                    )
                else:
                    self.assertFalse(
                        self.cyl_simulator.voxel_grid[self.cyl_simulator._get_voxel_index(i,j,0)]
                    )
    
    def test_single_point_removal(self):
        """Test material removal at a single point."""
        # Remove material at center point
        tool_position = np.array([50.0, 25.0, 20.0])
        tool_diameter = 10.0
        
        self.rect_simulator.remove_material(
            tool_position,
            None,
            tool_diameter
        )
        
        # Check that material was removed in a circular pattern
        tool_radius = tool_diameter / 2
        center_voxel = (
            int(tool_position[0] / self.rect_simulator.voxel_size),
            int(tool_position[1] / self.rect_simulator.voxel_size),
            int(tool_position[2] / self.rect_simulator.voxel_size)
        )
        
        # Check voxels within tool radius
        radius_voxels = int(np.ceil(tool_radius / self.rect_simulator.voxel_size))
        for i in range(-radius_voxels, radius_voxels + 1):
            for j in range(-radius_voxels, radius_voxels + 1):
                x = center_voxel[0] + i
                y = center_voxel[1] + j
                z = center_voxel[2]
                
                if x < 0 or x >= self.rect_simulator.nx or \
                   y < 0 or y >= self.rect_simulator.ny or \
                   z < 0 or z >= self.rect_simulator.nz:
                    continue
                    
                distance = np.sqrt(i**2 + j**2)
                if distance <= radius_voxels:
                    self.assertFalse(
                        self.rect_simulator.voxel_grid[self.rect_simulator._get_voxel_index(x,y,z)],
                        f"Material not removed at ({x},{y},{z})"
                    )
    
    def test_toolpath_simulation(self):
        """Test material removal along a toolpath."""
        tool_diameter = 10.0
        
        # Simulate complete toolpath
        self.rect_simulator.simulate_toolpath(
            self.test_toolpath,
            tool_diameter
        )
        
        # Verify material removal along path
        for i in range(len(self.test_toolpath) - 1):
            start = self.test_toolpath[i]
            end = self.test_toolpath[i + 1]
            
            # Check points along the path
            num_points = 10
            for t in np.linspace(0, 1, num_points):
                point = start + t * (end - start)
                vx = int(point[0] / self.rect_simulator.voxel_size)
                vy = int(point[1] / self.rect_simulator.voxel_size)
                vz = int(point[2] / self.rect_simulator.voxel_size)
                
                # Check center point and surrounding area
                radius_voxels = int(np.ceil((tool_diameter/2) / self.rect_simulator.voxel_size))
                for dx in range(-radius_voxels, radius_voxels + 1):
                    for dy in range(-radius_voxels, radius_voxels + 1):
                        x = vx + dx
                        y = vy + dy
                        
                        if x < 0 or x >= self.rect_simulator.nx or \
                           y < 0 or y >= self.rect_simulator.ny:
                            continue
                            
                        distance = np.sqrt(dx**2 + dy**2)
                        if distance <= radius_voxels:
                            self.assertFalse(
                                self.rect_simulator.voxel_grid[self.rect_simulator._get_voxel_index(x,y,vz)],
                                f"Material not removed at ({x},{y},{vz})"
                            )
    
    def test_island_preservation(self):
        """Test that islands are preserved during material removal."""
        tool_diameter = 10.0
        
        # Simulate toolpath with islands
        self.rect_simulator.simulate_toolpath(
            self.test_toolpath,
            tool_diameter,
            self.test_islands
        )
        
        # Check that material within islands is preserved
        for island in self.test_islands:
            points = island['points']
            z_min = int(island['z_min'] / self.rect_simulator.voxel_size)
            z_max = int(island['z_max'] / self.rect_simulator.voxel_size)
            
            # Convert island points to voxel coordinates
            voxel_points = [np.array([
                int(p[0] / self.rect_simulator.voxel_size),
                int(p[1] / self.rect_simulator.voxel_size)
            ]) for p in points]
            
            # Check points within island bounds
            min_x = min(p[0] for p in voxel_points)
            max_x = max(p[0] for p in voxel_points)
            min_y = min(p[1] for p in voxel_points)
            max_y = max(p[1] for p in voxel_points)
            
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    point = np.array([x, y])
                    if self._point_in_polygon(point, voxel_points):
                        for z in range(z_min, z_max + 1):
                            self.assertTrue(
                                self.rect_simulator.voxel_grid[self.rect_simulator._get_voxel_index(x,y,z)],
                                f"Island material removed at ({x},{y},{z})"
                            )
    
    def test_visualization(self):
        """Test visualization functionality."""
        import matplotlib.pyplot as plt
        
        # Create a simple cut
        tool_position = np.array([50.0, 25.0, 20.0])
        tool_diameter = 10.0
        self.rect_simulator.remove_material(tool_position, None, tool_diameter)
        
        try:
            # Test basic visualization
            self.rect_simulator.visualize(alpha=0.5)
            plt.close()
            
            # Test with original stock outline
            self.rect_simulator.visualize(show_original=True)
            plt.close()
            
        except Exception as e:
            self.fail(f"Visualization failed: {str(e)}")
    
    def test_performance_large_stock(self):
        """Test performance with large stock dimensions."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and initialize large stock
        start_time = time.time()
        simulator = MaterialSimulator(self.large_stock_params)
        init_time = time.time() - start_time
        
        # Simulate complex toolpath
        start_time = time.time()
        simulator.simulate_toolpath(
            self.complex_toolpath,
            tool_diameter=10.0
        )
        sim_time = time.time() - start_time
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Log performance metrics
        print(f"\nPerformance Test Results:")
        print(f"Stock Size: {self.large_stock_params.dimensions}")
        print(f"Voxel Size: {self.large_stock_params.voxel_size}")
        print(f"Initialization Time: {init_time:.2f} seconds")
        print(f"Simulation Time: {sim_time:.2f} seconds")
        print(f"Memory Usage: {memory_increase:.2f} MB")
        
        # Assert reasonable performance
        self.assertLess(init_time, 5.0, "Stock initialization took too long")
        self.assertLess(sim_time, 30.0, "Simulation took too long")
        self.assertLess(memory_increase, 1000.0, "Memory usage too high")
    
    def test_performance_memory_efficiency(self):
        """Test memory efficiency of sparse voxel storage."""
        # Create a stock with high resolution
        high_res_params = StockParameters(
            stock_type=StockType.RECTANGULAR,
            dimensions=(100.0, 100.0, 100.0),
            voxel_size=0.1  # 1mm voxels
        )
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create simulator
        simulator = MaterialSimulator(high_res_params)
        creation_memory = process.memory_info().rss / 1024 / 1024 - initial_memory
        
        # Simulate material removal
        simulator.remove_material(
            np.array([50.0, 50.0, 50.0]),
            None,
            tool_diameter=10.0
        )
        final_memory = process.memory_info().rss / 1024 / 1024 - initial_memory
        
        # Log memory metrics
        print(f"\nMemory Efficiency Test Results:")
        print(f"Stock Size: {high_res_params.dimensions}")
        print(f"Voxel Size: {high_res_params.voxel_size}")
        print(f"Creation Memory: {creation_memory:.2f} MB")
        print(f"Final Memory: {final_memory:.2f} MB")
        print(f"Memory Increase: {final_memory - creation_memory:.2f} MB")
        
        # Assert reasonable memory usage
        self.assertLess(creation_memory, 1000.0, "Initial memory usage too high")
        self.assertLess(final_memory - creation_memory, 100.0, "Memory increase too high")
    
    def _point_in_polygon(self, point: np.ndarray, polygon: list) -> bool:
        """Helper method to test if a point is inside a polygon."""
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            if (((polygon[i][1] > point[1]) != (polygon[j][1] > point[1])) and
                (point[0] < (polygon[j][0] - polygon[i][0]) * 
                 (point[1] - polygon[i][1]) / (polygon[j][1] - polygon[i][1]) +
                 polygon[i][0])):
                inside = not inside
            j = i
            
        return inside

if __name__ == '__main__':
    unittest.main() 