"""
Machine simulation module for real-time toolpath visualization and verification.
"""

from typing import List, Optional, Dict, Union, Tuple, Any
import numpy as np
from scipy import sparse
from dataclasses import dataclass
from enum import Enum
from .toolpath import ToolParameters, CuttingParameters
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import threading
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

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
    min_voxel_size: float = 0.1  # Minimum voxel size for adaptive grid
    max_voxel_size: float = 4.0  # Maximum voxel size for adaptive grid
    refinement_threshold: float = 0.5  # Threshold for voxel refinement (0-1)

class VoxelNode:
    """Represents a node in the adaptive voxel grid."""
    
    def __init__(
        self,
        center: np.ndarray,
        size: float,
        parent: Optional['VoxelNode'] = None,
        level: int = 0
    ):
        """
        Initialize a voxel node.
        
        Args:
            center: Center point of the node (x, y, z)
            size: Size of the node (uniform in all dimensions)
            parent: Parent node in the hierarchy
            level: Level in the octree (0 for root)
        """
        self.center = center
        self.size = size
        self.parent = parent
        self.level = level
        self.children: Optional[List['VoxelNode']] = None
        self.voxel_grid: Optional[sparse.csr_matrix] = None
        self.is_leaf = True
        self.lock = threading.Lock()
        
    def subdivide(self) -> None:
        """Subdivide the node into 8 children."""
        if not self.is_leaf:
            return
            
        half_size = self.size / 2
        quarter_size = half_size / 2
        
        # Create 8 children in octree order
        self.children = []
        for i in range(8):
            # Calculate child center based on octree index
            x = self.center[0] + quarter_size * ((i & 1) * 2 - 1)
            y = self.center[1] + quarter_size * (((i >> 1) & 1) * 2 - 1)
            z = self.center[2] + quarter_size * (((i >> 2) & 1) * 2 - 1)
            
            child = VoxelNode(
                center=np.array([x, y, z]),
                size=half_size,
                parent=self,
                level=self.level + 1
            )
            self.children.append(child)
            
        self.is_leaf = False
        
    def get_child_at_point(self, point: np.ndarray) -> Optional['VoxelNode']:
        """
        Get the child node containing a given point.
        
        Args:
            point: Point to locate (x, y, z)
            
        Returns:
            Child node containing the point, or None if point is outside node
        """
        if self.is_leaf:
            return None
            
        # Check if point is within node bounds
        half_size = self.size / 2
        if not all(abs(p - c) <= half_size for p, c in zip(point, self.center)):
            return None
            
        # Calculate child index based on point position
        child_idx = 0
        for i, (p, c) in enumerate(zip(point, self.center)):
            if p > c:
                child_idx |= (1 << i)
                
        return self.children[child_idx]
        
    def get_voxel_grid(self) -> sparse.csr_matrix:
        """
        Get the voxel grid for this node, creating it if necessary.
        
        Returns:
            Sparse matrix representing the voxel grid
        """
        if self.voxel_grid is None:
            # Calculate grid dimensions
            nx = ny = nz = int(np.ceil(self.size / self.parent.voxel_size))
            
            # Initialize full voxel grid
            self.voxel_grid = sparse.csr_matrix(
                (np.ones(nx * ny * nz),
                 (np.arange(nx * ny * nz),
                  np.zeros(nx * ny * nz))),
                shape=(nx * ny * nz, 1)
            )
            
        return self.voxel_grid

class AdaptiveVoxelGrid:
    """Manages an adaptive voxel grid for material simulation."""
    
    def __init__(
        self,
        dimensions: Tuple[float, float, float],
        min_voxel_size: float,
        max_voxel_size: float,
        refinement_threshold: float = 0.5
    ):
        """
        Initialize adaptive voxel grid.
        
        Args:
            dimensions: Stock dimensions (length, width, height)
            min_voxel_size: Minimum voxel size for refinement
            max_voxel_size: Maximum voxel size for coarsening
            refinement_threshold: Threshold for voxel refinement (0-1)
        """
        self.dimensions = dimensions
        self.min_voxel_size = min_voxel_size
        self.max_voxel_size = max_voxel_size
        self.refinement_threshold = refinement_threshold
        
        # Create root node
        self.root = VoxelNode(
            center=np.array([dimensions[0]/2, dimensions[1]/2, dimensions[2]/2]),
            size=max(dimensions),
            level=0
        )
        self.root.voxel_size = max_voxel_size
        
        # Initialize thread safety
        self.grid_lock = threading.Lock()
        
    def get_node_at_point(self, point: np.ndarray) -> VoxelNode:
        """
        Get the leaf node containing a given point.
        
        Args:
            point: Point to locate (x, y, z)
            
        Returns:
            Leaf node containing the point
        """
        current = self.root
        while not current.is_leaf:
            child = current.get_child_at_point(point)
            if child is None:
                break
            current = child
        return current
        
    def refine_node(self, node: VoxelNode) -> None:
        """
        Refine a node by subdividing it and distributing its voxel grid.
        
        Args:
            node: Node to refine
        """
        if node.size <= self.min_voxel_size:
            return
            
        with node.lock:
            if not node.is_leaf:
                return
                
            # Store current voxel grid
            old_grid = node.voxel_grid
            if old_grid is None:
                return
                
            # Subdivide node
            node.subdivide()
            
            # Distribute voxels to children
            nx = ny = nz = int(np.ceil(node.size / node.voxel_size))
            for i in range(nx):
                for j in range(ny):
                    for k in range(nz):
                        idx = i + nx * (j + ny * k)
                        if old_grid[idx]:
                            # Convert to world coordinates
                            x = node.center[0] - node.size/2 + i * node.voxel_size
                            y = node.center[1] - node.size/2 + j * node.voxel_size
                            z = node.center[2] - node.size/2 + k * node.voxel_size
                            
                            # Find child containing this point
                            child = node.get_child_at_point(np.array([x, y, z]))
                            if child:
                                child.get_voxel_grid()
                                
    def coarsen_node(self, node: VoxelNode) -> None:
        """
        Coarsen a node by merging its children's voxel grids.
        
        Args:
            node: Node to coarsen
        """
        if node.size >= self.max_voxel_size:
            return
            
        with node.lock:
            if node.is_leaf or not all(child.is_leaf for child in node.children):
                return
                
            # Merge children's voxel grids
            nx = ny = nz = int(np.ceil(node.size / node.voxel_size))
            merged_grid = sparse.csr_matrix(
                (np.ones(nx * ny * nz),
                 (np.arange(nx * ny * nz),
                  np.zeros(nx * ny * nz))),
                shape=(nx * ny * nz, 1)
            )
            
            # Combine children's voxels
            for child in node.children:
                if child.voxel_grid is not None:
                    # Convert child's voxels to parent's coordinate system
                    # and merge them
                    # ... (implementation details for coordinate conversion)
                    pass
                    
            node.voxel_grid = merged_grid
            node.children = None
            node.is_leaf = True
            
    def remove_material(
        self,
        tool_position: np.ndarray,
        tool_diameter: float,
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None
    ) -> None:
        """
        Remove material at the specified tool position.
        
        Args:
            tool_position: (x, y, z) position of tool tip
            tool_diameter: Diameter of the cutting tool
            islands: Optional list of islands to preserve
        """
        with self.grid_lock:
            # Get node containing tool position
            node = self.get_node_at_point(tool_position)
            
            # Check if refinement is needed
            if tool_diameter < node.size * self.refinement_threshold:
                self.refine_node(node)
                node = self.get_node_at_point(tool_position)
                
            # Remove material from the node's voxel grid
            with node.lock:
                # Convert tool position to node's local coordinates
                local_pos = tool_position - (node.center - node.size/2)
                
                # Calculate affected voxel ranges
                tool_radius = tool_diameter / 2
                vx = int(local_pos[0] / node.voxel_size)
                vy = int(local_pos[1] / node.voxel_size)
                vz = int(local_pos[2] / node.voxel_size)
                
                # Create removal mask
                nx = ny = nz = int(np.ceil(node.size / node.voxel_size))
                radius_voxels = int(np.ceil(tool_radius / node.voxel_size))
                
                indices_to_remove = []
                for i in range(max(0, vx - radius_voxels),
                             min(nx, vx + radius_voxels + 1)):
                    for j in range(max(0, vy - radius_voxels),
                                 min(ny, vy + radius_voxels + 1)):
                        dx = i - vx
                        dy = j - vy
                        if dx*dx + dy*dy <= radius_voxels*radius_voxels:
                            for k in range(max(0, vz),
                                         min(nz, vz + 1)):
                                idx = i + nx * (j + ny * k)
                                indices_to_remove.append(idx)
                                
                # Remove material
                if indices_to_remove:
                    remove_mask = sparse.csr_matrix(
                        (np.ones(len(indices_to_remove)),
                         (indices_to_remove, np.zeros(len(indices_to_remove)))),
                        shape=(nx * ny * nz, 1)
                    )
                    node.voxel_grid = node.voxel_grid.multiply(
                        ~(remove_mask.astype(bool))
                    )
                    
            # Check if coarsening is possible
            if node.parent and node.parent.size < self.max_voxel_size:
                self.coarsen_node(node.parent)

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
        
        # Initialize adaptive voxel grid
        self.voxel_grid = AdaptiveVoxelGrid(
            dimensions=stock_params.dimensions,
            min_voxel_size=stock_params.min_voxel_size,
            max_voxel_size=stock_params.max_voxel_size,
            refinement_threshold=stock_params.refinement_threshold
        )
        
        # Set up coordinate grids for visualization
        if stock_params.stock_type == StockType.RECTANGULAR:
            length, width, height = stock_params.dimensions
            x = np.linspace(0, length, int(np.ceil(length / stock_params.voxel_size)))
            y = np.linspace(0, width, int(np.ceil(width / stock_params.voxel_size)))
            z = np.linspace(0, height, int(np.ceil(height / stock_params.voxel_size)))
        else:  # CYLINDRICAL
            diameter, height = stock_params.dimensions[:2]
            x = np.linspace(-diameter/2, diameter/2, int(np.ceil(diameter / stock_params.voxel_size)))
            y = np.linspace(-diameter/2, diameter/2, int(np.ceil(diameter / stock_params.voxel_size)))
            z = np.linspace(0, height, int(np.ceil(height / stock_params.voxel_size)))
            
        self.X, self.Y, self.Z = np.meshgrid(x, y, z, indexing='ij')
        
        # Initialize cylindrical stock if needed
        if stock_params.stock_type == StockType.CYLINDRICAL:
            radius = diameter / 2
            mask = (self.X**2 + self.Y**2) <= radius**2
            # Initialize root node with cylindrical mask
            self.voxel_grid.root.voxel_grid = sparse.csr_matrix(
                (mask.flatten(),
                 (np.arange(mask.size),
                  np.zeros(mask.size))),
                shape=(mask.size, 1)
            )
        
        # Store original stock for visualization
        self.original_stock = self.voxel_grid.root.voxel_grid.copy()
        
        # Initialize thread safety
        self.voxel_lock = threading.Lock()
        self.num_workers = max(1, multiprocessing.cpu_count() - 1)  # Leave one core free
        
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
        with self.voxel_lock:
            # Remove material using adaptive grid
            self.voxel_grid.remove_material(tool_position, tool_diameter, islands)
    
    def _process_segment(
        self,
        segment: List[np.ndarray],
        tool_diameter: float,
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None
    ) -> None:
        """
        Process a segment of the toolpath.
        
        Args:
            segment: List of tool positions in the segment
            tool_diameter: Diameter of the cutting tool
            islands: Optional list of islands to preserve
        """
        for i in range(len(segment) - 1):
            current_pos = segment[i]
            next_pos = segment[i + 1]
            
            # Calculate direction vector
            direction = next_pos - current_pos
            
            # Interpolate positions along the path
            num_steps = max(1, int(np.ceil(np.linalg.norm(direction) / self.stock_params.voxel_size)))
            for t in np.linspace(0, 1, num_steps):
                pos = current_pos + t * direction
                self.remove_material(pos, direction, tool_diameter, islands)
    
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
        # Split toolpath into segments for parallel processing
        segment_size = max(1, len(toolpath) // (self.num_workers * 4))  # Ensure enough segments for parallelization
        segments = [toolpath[i:i + segment_size] for i in range(0, len(toolpath), segment_size)]
        
        # Process segments in parallel
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(self._process_segment, segment, tool_diameter, islands)
                for segment in segments
            ]
            
            # Wait for all segments to complete and update visualization if needed
            for i, future in enumerate(futures):
                future.result()
                if update_callback and i % 10 == 0:  # Update every 10 segments
                    update_callback(self.voxel_grid.root.voxel_grid)
    
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
        remaining_indices = self.voxel_grid.root.voxel_grid.nonzero()[0]
        
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
            if i == 0 or not self.voxel_grid.root.voxel_grid[self._get_voxel_index(i-1,j,k)]:
                add_face(v000, v001, v011, v010)
            if i == self.X.shape[0]-2 or not self.voxel_grid.root.voxel_grid[self._get_voxel_index(i+1,j,k)]:
                add_face(v100, v101, v111, v110)
            if j == 0 or not self.voxel_grid.root.voxel_grid[self._get_voxel_index(i,j-1,k)]:
                add_face(v000, v001, v101, v100)
            if j == self.Y.shape[1]-2 or not self.voxel_grid.root.voxel_grid[self._get_voxel_index(i,j+1,k)]:
                add_face(v010, v011, v111, v110)
            if k == 0 or not self.voxel_grid.root.voxel_grid[self._get_voxel_index(i,j,k-1)]:
                add_face(v000, v010, v110, v100)
            if k == self.Z.shape[2]-2 or not self.voxel_grid.root.voxel_grid[self._get_voxel_index(i,j,k+1)]:
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
    
    def _get_voxel_index(self, x: int, y: int, z: int) -> int:
        """Convert 3D voxel coordinates to 1D index."""
        nx = self.X.shape[0]
        ny = self.Y.shape[1]
        return x + nx * (y + ny * z)
        
    def _get_voxel_coords(self, index: int) -> Tuple[int, int, int]:
        """Convert 1D index to 3D voxel coordinates."""
        nx = self.X.shape[0]
        ny = self.Y.shape[1]
        z = index // (nx * ny)
        y = (index % (nx * ny)) // nx
        x = index % nx
        return x, y, z 