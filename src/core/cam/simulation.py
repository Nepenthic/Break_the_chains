"""
Machine simulation module for real-time toolpath visualization and verification.
"""

from typing import List, Optional, Dict, Union, Tuple
import numpy as np
from scipy import sparse
from dataclasses import dataclass
from enum import Enum
from .toolpath import ToolParameters, CuttingParameters
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

class SimulationType(Enum):
    """Types of simulation available."""
    WIREFRAME = "wireframe"  # Fast, basic simulation
    SOLID = "solid"         # Full material removal simulation
    VERIFY = "verify"       # Detailed verification with measurements

class StockType(Enum):
    """Types of stock material."""
    RECTANGULAR = "rectangular"
    CYLINDRICAL = "cylindrical"

@dataclass
class SimulationParameters:
    """Parameters for controlling the simulation."""
    simulation_type: SimulationType
    show_tool: bool = True
    show_stock: bool = True
    show_fixtures: bool = True
    show_collisions: bool = True
    update_rate: float = 30.0  # Hz
    
@dataclass
class StockParameters:
    """Parameters for stock material."""
    stock_type: StockType
    dimensions: Tuple[float, float, float]  # (length, width, height) or (diameter, height)
    voxel_size: float = 1.0  # Size of each voxel in mm
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # Stock origin point

class MaterialRemovalSimulation:
    """Simulates material removal during machining."""
    
    def __init__(self,
                 stock_model: 'Mesh',
                 tool: ToolParameters,
                 cutting_params: CuttingParameters):
        self.stock = stock_model
        self.tool = tool
        self.cutting_params = cutting_params
        self.removed_volume = 0.0
        self.current_position = np.zeros(3)
        
    def update(self, new_position: np.ndarray) -> None:
        """
        Update the simulation for a new tool position.
        
        Args:
            new_position: New tool position (x, y, z)
        """
        # Calculate material removal between current and new position
        self._simulate_material_removal(self.current_position, new_position)
        self.current_position = new_position
        
    def _simulate_material_removal(self, 
                                 start_pos: np.ndarray,
                                 end_pos: np.ndarray) -> None:
        """
        Simulate material removal between two positions.
        
        Args:
            start_pos: Starting tool position
            end_pos: Ending tool position
        """
        # TODO: Implement material removal simulation
        # - Calculate intersection volume
        # - Update stock model
        # - Track removed material
        pass

class CollisionMonitor:
    """Monitors and reports potential collisions during simulation."""
    
    def __init__(self,
                 tool: ToolParameters,
                 stock: 'Mesh',
                 fixtures: List['Mesh']):
        self.tool = tool
        self.stock = stock
        self.fixtures = fixtures
        self.collision_points: List[np.ndarray] = []
        
    def check_movement(self, 
                      start_pos: np.ndarray,
                      end_pos: np.ndarray) -> bool:
        """
        Check for collisions along a movement path.
        
        Args:
            start_pos: Starting position
            end_pos: Ending position
            
        Returns:
            bool: True if collision detected
        """
        # TODO: Implement collision checking
        # - Check tool against fixtures
        # - Check tool holder against stock
        # - Check rapid movements
        pass

class MachineSimulator:
    """Main simulation controller for machining operations."""
    
    def __init__(self,
                 params: SimulationParameters,
                 stock_model: 'Mesh',
                 tool: ToolParameters,
                 cutting_params: CuttingParameters,
                 fixtures: List['Mesh']):
        self.params = params
        self.material_sim = MaterialRemovalSimulation(stock_model, tool, cutting_params)
        self.collision_monitor = CollisionMonitor(tool, stock_model, fixtures)
        self.toolpath: List[np.ndarray] = []
        self.current_index = 0
        self.is_running = False
        self.metrics: Dict[str, float] = {
            'removed_volume': 0.0,
            'machining_time': 0.0,
            'distance_traveled': 0.0
        }
        
    def load_toolpath(self, toolpath: List[np.ndarray]) -> None:
        """
        Load a toolpath for simulation.
        
        Args:
            toolpath: List of points defining the toolpath
        """
        self.toolpath = toolpath
        self.current_index = 0
        self.reset_metrics()
        
    def step(self) -> bool:
        """
        Advance simulation by one step.
        
        Returns:
            bool: False if simulation is complete
        """
        if self.current_index >= len(self.toolpath) - 1:
            self.is_running = False
            return False
            
        current_pos = self.toolpath[self.current_index]
        next_pos = self.toolpath[self.current_index + 1]
        
        # Check for collisions
        if self.params.show_collisions:
            if self.collision_monitor.check_movement(current_pos, next_pos):
                self.is_running = False
                return False
        
        # Update material removal simulation
        if self.params.simulation_type == SimulationType.SOLID:
            self.material_sim.update(next_pos)
        
        # Update metrics
        self._update_metrics(current_pos, next_pos)
        
        self.current_index += 1
        return True
        
    def reset_metrics(self) -> None:
        """Reset simulation metrics."""
        self.metrics = {
            'removed_volume': 0.0,
            'machining_time': 0.0,
            'distance_traveled': 0.0
        }
        
    def _update_metrics(self,
                       current_pos: np.ndarray,
                       next_pos: np.ndarray) -> None:
        """
        Update simulation metrics.
        
        Args:
            current_pos: Current position
            next_pos: Next position
        """
        # Update distance traveled
        distance = np.linalg.norm(next_pos - current_pos)
        self.metrics['distance_traveled'] += distance
        
        # Update machining time based on feedrate
        # TODO: Consider acceleration/deceleration
        time = distance / self.material_sim.cutting_params.feedrate
        self.metrics['machining_time'] += time
        
        # Update removed volume from material simulation
        self.metrics['removed_volume'] = self.material_sim.removed_volume 

class MaterialSimulator:
    """Simulates material removal during machining operations."""
    
    def __init__(self, stock_params: StockParameters):
        """
        Initialize material simulator.
        
        Args:
            stock_params: Parameters defining the stock material
        """
        self.stock_params = stock_params
        self.voxel_size = stock_params.voxel_size
        
        # Calculate grid dimensions
        if stock_params.stock_type == StockType.RECTANGULAR:
            length, width, height = stock_params.dimensions
            self.nx = int(np.ceil(length / self.voxel_size))
            self.ny = int(np.ceil(width / self.voxel_size))
            self.nz = int(np.ceil(height / self.voxel_size))
        else:  # CYLINDRICAL
            diameter, height = stock_params.dimensions[:2]
            self.nx = int(np.ceil(diameter / self.voxel_size))
            self.ny = int(np.ceil(diameter / self.voxel_size))
            self.nz = int(np.ceil(height / self.voxel_size))
        
        # Initialize sparse voxel grid (1 = material present, 0 = material removed)
        # Use COO format for efficient construction, then convert to CSR for fast operations
        self.voxel_grid = sparse.csr_matrix(
            (np.ones(self.nx * self.ny * self.nz),
             (np.arange(self.nx * self.ny * self.nz),
              np.zeros(self.nx * self.ny * self.nz))),
            shape=(self.nx * self.ny * self.nz, 1)
        )
        
        # Set up coordinate grids for faster operations
        x = np.linspace(0, length, self.nx) if stock_params.stock_type == StockType.RECTANGULAR else \
            np.linspace(-diameter/2, diameter/2, self.nx)
        y = np.linspace(0, width, self.ny) if stock_params.stock_type == StockType.RECTANGULAR else \
            np.linspace(-diameter/2, diameter/2, self.ny)
        z = np.linspace(0, height, self.nz)
        self.X, self.Y, self.Z = np.meshgrid(x, y, z, indexing='ij')
        
        # Initialize cylindrical stock if needed
        if stock_params.stock_type == StockType.CYLINDRICAL:
            radius = diameter / 2
            mask = (self.X**2 + self.Y**2) <= radius**2
            self.voxel_grid = sparse.csr_matrix(
                (mask.flatten(),
                 (np.arange(self.nx * self.ny * self.nz),
                  np.zeros(self.nx * self.ny * self.nz))),
                shape=(self.nx * self.ny * self.nz, 1)
            )
        
        # Store original stock for visualization
        self.original_stock = self.voxel_grid.copy()
        
    def _get_voxel_index(self, x: int, y: int, z: int) -> int:
        """Convert 3D voxel coordinates to 1D index."""
        return x + self.nx * (y + self.ny * z)
        
    def _get_voxel_coords(self, index: int) -> Tuple[int, int, int]:
        """Convert 1D index to 3D voxel coordinates."""
        z = index // (self.nx * self.ny)
        y = (index % (self.nx * self.ny)) // self.nx
        x = index % self.nx
        return x, y, z
        
    def remove_material(
        self,
        tool_position: np.ndarray,
        tool_direction: Optional[np.ndarray],
        tool_diameter: float,
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None
    ) -> None:
        """
        Remove material at the specified tool position.
        
        Args:
            tool_position: (x, y, z) position of tool tip
            tool_direction: Optional direction vector for non-vertical cuts
            tool_diameter: Diameter of the cutting tool
            islands: Optional list of islands to preserve
        """
        # Convert tool position to voxel coordinates
        vx = int(tool_position[0] / self.voxel_size)
        vy = int(tool_position[1] / self.voxel_size)
        vz = int(tool_position[2] / self.voxel_size)
        
        # Calculate tool radius in voxels
        tool_radius_voxels = int(np.ceil((tool_diameter / 2) / self.voxel_size))
        
        # Calculate affected voxel ranges
        x_min = max(0, vx - tool_radius_voxels)
        x_max = min(self.nx, vx + tool_radius_voxels + 1)
        y_min = max(0, vy - tool_radius_voxels)
        y_max = min(self.ny, vy + tool_radius_voxels + 1)
        z_min = max(0, vz)
        z_max = min(self.nz, vz + 1)
        
        # Create a mask for the tool's circular cross-section
        y, x = np.ogrid[-tool_radius_voxels:tool_radius_voxels+1, 
                        -tool_radius_voxels:tool_radius_voxels+1]
        tool_mask = x*x + y*y <= tool_radius_voxels*tool_radius_voxels
        
        # Check for islands before removing material
        if islands:
            # Create a mask for protected areas (islands)
            protected_indices = []
            for island in islands:
                if island['z_min'] <= tool_position[2] <= island['z_max']:
                    # Convert island points to voxel coordinates
                    island_points = np.array(island['points']) / self.voxel_size
                    
                    # Create a polygon mask for this island
                    y_coords = np.arange(y_min, y_max)
                    x_coords = np.arange(x_min, x_max)
                    XX, YY = np.meshgrid(x_coords, y_coords)
                    points = np.column_stack((XX.flatten(), YY.flatten()))
                    
                    # Use points_in_polygon to create island mask
                    mask = self._points_in_polygon(points, island_points)
                    mask = mask.reshape(XX.shape)
                    
                    # Add protected indices
                    for i in range(x_min, x_max):
                        for j in range(y_min, y_max):
                            if mask[i-x_min, j-y_min]:
                                for z in range(z_min, z_max):
                                    protected_indices.append(self._get_voxel_index(i, j, z))
            
            # Convert protected indices to sparse matrix
            protected = sparse.csr_matrix(
                (np.ones(len(protected_indices)),
                 (protected_indices, np.zeros(len(protected_indices)))),
                shape=(self.nx * self.ny * self.nz, 1)
            )
            
            # Remove material only in unprotected areas
            self.voxel_grid = self.voxel_grid.multiply(
                ~(protected.astype(bool))
            )
        else:
            # Remove material where the tool intersects
            indices_to_remove = []
            for i in range(x_min, x_max):
                for j in range(y_min, y_max):
                    dx = i - vx
                    dy = j - vy
                    if dx*dx + dy*dy <= tool_radius_voxels*tool_radius_voxels:
                        for z in range(z_min, z_max):
                            indices_to_remove.append(self._get_voxel_index(i, j, z))
            
            # Convert indices to sparse matrix and remove material
            remove_mask = sparse.csr_matrix(
                (np.ones(len(indices_to_remove)),
                 (indices_to_remove, np.zeros(len(indices_to_remove)))),
                shape=(self.nx * self.ny * self.nz, 1)
            )
            self.voxel_grid = self.voxel_grid.multiply(
                ~(remove_mask.astype(bool))
            )
    
    def simulate_toolpath(
        self,
        toolpath: List[np.ndarray],
        tool_diameter: float,
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None,
        update_callback: Optional[callable] = None
    ) -> None:
        """
        Simulate material removal along a complete toolpath.
        
        Args:
            toolpath: List of tool positions
            tool_diameter: Diameter of the cutting tool
            islands: Optional list of islands to preserve
            update_callback: Optional callback function for visualization updates
        """
        for i in range(len(toolpath) - 1):
            current_pos = toolpath[i]
            next_pos = toolpath[i + 1]
            
            # Calculate direction vector
            direction = next_pos - current_pos
            
            # Interpolate positions along the path
            num_steps = max(1, int(np.ceil(np.linalg.norm(direction) / self.voxel_size)))
            for t in np.linspace(0, 1, num_steps):
                pos = current_pos + t * direction
                self.remove_material(pos, direction, tool_diameter, islands)
            
            # Call update callback if provided
            if update_callback and i % 10 == 0:  # Update every 10 moves
                update_callback(self.voxel_grid)
    
    def visualize(
        self,
        ax: Optional[Axes3D] = None,
        alpha: float = 0.3,
        show_original: bool = False
    ) -> None:
        """
        Visualize the current state of the stock material.
        
        Args:
            ax: Optional matplotlib 3D axes
            alpha: Transparency level for visualization
            show_original: Whether to show the original stock outline
        """
        if ax is None:
            fig = plt.figure(figsize=(10, 10))
            ax = fig.add_subplot(111, projection='3d')
        
        # Create vertices and faces for remaining material
        vertices = []
        faces = []
        
        # Function to add a face
        def add_face(v1, v2, v3, v4):
            face_idx = len(vertices)
            vertices.extend([v1, v2, v3, v4])
            faces.append([face_idx, face_idx+1, face_idx+2, face_idx+3])
        
        # Get non-zero indices from sparse matrix
        remaining_indices = self.voxel_grid.nonzero()[0]
        
        # Create mesh for remaining material
        for idx in remaining_indices:
            i, j, k = self._get_voxel_coords(idx)
            
            # Add cube vertices and faces
            v000 = np.array([self.X[i,j,k], self.Y[i,j,k], self.Z[i,j,k]])
            v001 = np.array([self.X[i,j,k+1], self.Y[i,j,k+1], self.Z[i,j,k+1]])
            v010 = np.array([self.X[i,j+1,k], self.Y[i,j+1,k], self.Z[i,j+1,k]])
            v011 = np.array([self.X[i,j+1,k+1], self.Y[i,j+1,k+1], self.Z[i,j+1,k+1]])
            v100 = np.array([self.X[i+1,j,k], self.Y[i+1,j,k], self.Z[i+1,j,k]])
            v101 = np.array([self.X[i+1,j,k+1], self.Y[i+1,j,k+1], self.Z[i+1,j,k+1]])
            v110 = np.array([self.X[i+1,j+1,k], self.Y[i+1,j+1,k], self.Z[i+1,j+1,k]])
            v111 = np.array([self.X[i+1,j+1,k+1], self.Y[i+1,j+1,k+1], self.Z[i+1,j+1,k+1]])
            
            # Check neighbors to determine which faces to add
            if i == 0 or not self.voxel_grid[self._get_voxel_index(i-1,j,k)]:
                add_face(v000, v001, v011, v010)
            if i == self.nx-2 or not self.voxel_grid[self._get_voxel_index(i+1,j,k)]:
                add_face(v100, v101, v111, v110)
            if j == 0 or not self.voxel_grid[self._get_voxel_index(i,j-1,k)]:
                add_face(v000, v001, v101, v100)
            if j == self.ny-2 or not self.voxel_grid[self._get_voxel_index(i,j+1,k)]:
                add_face(v010, v011, v111, v110)
            if k == 0 or not self.voxel_grid[self._get_voxel_index(i,j,k-1)]:
                add_face(v000, v010, v110, v100)
            if k == self.nz-2 or not self.voxel_grid[self._get_voxel_index(i,j,k+1)]:
                add_face(v001, v011, v111, v101)
        
        # Create mesh collection
        poly = Poly3DCollection(faces)
        poly.set_alpha(alpha)
        poly.set_facecolor('blue')
        ax.add_collection3d(poly)
        
        # Show original stock outline if requested
        if show_original:
            vertices_orig = []
            faces_orig = []
            # Add outline faces similar to above, but for original stock
            # ... (similar code for original stock)
            
            poly_orig = Poly3DCollection(faces_orig)
            poly_orig.set_alpha(0.1)
            poly_orig.set_facecolor('gray')
            ax.add_collection3d(poly_orig)
        
        # Set axis labels and limits
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        
        # Set axis limits based on stock dimensions
        if self.stock_params.stock_type == StockType.RECTANGULAR:
            length, width, height = self.stock_params.dimensions
            ax.set_xlim(0, length)
            ax.set_ylim(0, width)
            ax.set_zlim(0, height)
        else:
            diameter, height = self.stock_params.dimensions[:2]
            ax.set_xlim(-diameter/2, diameter/2)
            ax.set_ylim(-diameter/2, diameter/2)
            ax.set_zlim(0, height)
    
    def _points_in_polygon(self, points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
        """
        Test whether points are inside a polygon.
        
        Args:
            points: Array of points to test (N x 2)
            polygon: Array of polygon vertices (M x 2)
            
        Returns:
            Boolean array indicating which points are inside the polygon
        """
        path = plt.Path(polygon)
        return path.contains_points(points) 