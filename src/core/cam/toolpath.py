"""
Core module for CAM toolpath generation and optimization.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Union
import numpy as np
from enum import Enum
from .geometry import (
    OffsetDirection,
    offset_contour,
    generate_parallel_paths,
    check_point_in_polygon,
    calculate_path_length,
    optimize_path_connections,
    clip_line_to_polygon
)

class ToolType(Enum):
    """Supported cutting tool types."""
    ENDMILL = "endmill"
    BALLMILL = "ballmill"
    FACEMILL = "facemill"
    DRILL = "drill"
    CHAMFER = "chamfer"
    THREAD = "thread"

@dataclass
class ToolParameters:
    """Cutting tool parameters."""
    tool_type: ToolType
    diameter: float
    flutes: int
    length: float
    shank_diameter: float
    coating: Optional[str] = None
    max_doc: Optional[float] = None  # Maximum depth of cut
    max_woc: Optional[float] = None  # Maximum width of cut
    max_feedrate: Optional[float] = None
    max_spindle_speed: Optional[float] = None

@dataclass
class CuttingParameters:
    """Cutting operation parameters."""
    feedrate: float  # mm/min
    spindle_speed: float  # RPM
    depth_of_cut: float  # mm
    width_of_cut: float  # mm
    coolant: bool = True
    
class ToolpathType(Enum):
    """Supported toolpath strategies."""
    CONTOUR = "contour"
    POCKET = "pocket"
    DRILL = "drill"
    SURFACE = "surface"
    THREAD = "thread"
    CHAMFER = "chamfer"

class PocketStrategy(Enum):
    """Pocket machining strategy."""
    ZIGZAG = "zigzag"
    SPIRAL = "spiral"
    HYBRID = "hybrid"  # Boundary following + zigzag

@dataclass
class ToolpathParameters:
    """Toolpath generation parameters."""
    toolpath_type: ToolpathType
    tool: ToolParameters
    cutting_params: CuttingParameters
    stock_dimensions: Tuple[float, float, float]
    tolerance: float = 0.01
    stepover: float = 0.5  # As percentage of tool diameter
    pocket_strategy: PocketStrategy = PocketStrategy.HYBRID
    pocket_angle: float = 0.0  # Angle for zigzag paths in radians
    islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None  # List of islands with Z-depths
    start_z: float = 0.0  # Starting Z-level (top of stock)
    pocket_depth: float = 10.0  # Total depth of the pocket
    step_down: float = 2.0  # Depth per pass
    final_pass_depth: float = 0.5  # Depth for final finishing pass
    entry_type: str = "plunge"  # Type of Z entry ("plunge", "ramp", "helix")
    ramp_angle: float = 3.0  # Angle for ramping entry in degrees
    helix_diameter: float = 0.8  # Diameter of helix as fraction of tool diameter
    helix_angle: float = 5.0  # Angle of helix descent in degrees
    helix_revolutions: Optional[float] = None  # Number of revolutions (if None, calculated from angles)

class CollisionDetector:
    """Handles collision detection during toolpath generation."""
    
    def __init__(self, 
                 tool: ToolParameters,
                 stock_model: 'Mesh',
                 fixtures: List['Mesh']):
        self.tool = tool
        self.stock = stock_model
        self.fixtures = fixtures
        self.clearance_height = 10.0  # mm above stock
        
    def check_collision(self, 
                       position: np.ndarray, 
                       vector: np.ndarray) -> bool:
        """
        Check for collisions along a tool movement vector.
        
        Args:
            position: Current tool position (x, y, z)
            vector: Movement vector
            
        Returns:
            bool: True if collision detected
        """
        # TODO: Implement collision detection algorithm
        pass

class ToolpathGenerator:
    """Generates optimized toolpaths for machining operations."""
    
    def __init__(self, 
                 model: 'Mesh',
                 params: ToolpathParameters,
                 collision_detector: CollisionDetector):
        self.model = model
        self.params = params
        self.collision_detector = collision_detector
        self.toolpath: List[np.ndarray] = []
        self.clearance_height = 10.0  # mm above stock
        
    def generate_toolpath(self) -> List[np.ndarray]:
        """
        Generate optimized toolpath based on parameters.
        
        Returns:
            List of points defining the toolpath
        """
        if self.params.toolpath_type == ToolpathType.CONTOUR:
            return self._generate_contour_path()
        elif self.params.toolpath_type == ToolpathType.POCKET:
            return self._generate_pocket_path()
        elif self.params.toolpath_type == ToolpathType.SURFACE:
            return self._generate_surface_path()
        # Add other toolpath strategies
        
    def _generate_contour_path(self) -> List[np.ndarray]:
        """
        Generate contour toolpath.
        
        Returns:
            List of 3D points defining the toolpath
        """
        # Extract contour from model at current Z level
        # TODO: Get this from the model intersection with XY plane
        contour_2d = self._extract_contour_at_z(0.0)
        
        # Calculate tool radius offset
        tool_radius = self.params.tool.diameter / 2.0
        offset_distance = tool_radius
        
        # Generate offset paths
        paths_2d = []
        current_offset = offset_distance
        max_offsets = 10  # Prevent infinite loops
        
        for i in range(max_offsets):
            # Generate offset contour
            offset_path = offset_contour(
                contour_2d,
                current_offset,
                OffsetDirection.OUTSIDE  # TODO: Make this configurable
            )
            
            # Check if path is valid
            if not offset_path or len(offset_path) < 3:
                break
                
            paths_2d.append(offset_path)
            current_offset += offset_distance * self.params.stepover
        
        # Optimize path connections
        optimized_2d = optimize_path_connections(paths_2d)
        
        # Convert 2D paths to 3D toolpath
        toolpath = []
        current_z = self.clearance_height
        
        # Add initial move to clearance height
        if optimized_2d and optimized_2d[0]:
            start_point = optimized_2d[0][0]
            toolpath.append(np.array([start_point[0], start_point[1], self.clearance_height]))
        
        # Process each path
        for path_2d in optimized_2d:
            # Move to start point at clearance height
            start_point = path_2d[0]
            toolpath.append(np.array([start_point[0], start_point[1], self.clearance_height]))
            
            # Plunge to cutting depth
            toolpath.append(np.array([start_point[0], start_point[1], 0.0]))  # TODO: Use actual Z depth
            
            # Add cutting moves
            for point in path_2d[1:]:
                toolpath.append(np.array([point[0], point[1], 0.0]))  # TODO: Use actual Z depth
            
            # Retract to clearance height
            end_point = path_2d[-1]
            toolpath.append(np.array([end_point[0], end_point[1], self.clearance_height]))
        
        return toolpath
        
    def _generate_helix_points(
        self,
        center_x: float,
        center_y: float,
        start_z: float,
        end_z: float
    ) -> List[np.ndarray]:
        """
        Generate points for a helical entry move.
        
        Args:
            center_x: X coordinate of helix center
            center_y: Y coordinate of helix center
            start_z: Starting Z height
            end_z: Target Z height
            
        Returns:
            List of 3D points defining the helical path
        """
        # Calculate helix parameters
        tool_radius = self.params.tool.diameter / 2.0
        helix_radius = tool_radius * self.params.helix_diameter / 2.0
        helix_angle_rad = np.radians(self.params.helix_angle)
        
        # Calculate number of revolutions if not specified
        if self.params.helix_revolutions is None:
            z_diff = abs(end_z - start_z)
            pitch = z_diff * np.tan(helix_angle_rad)
            revolutions = z_diff / pitch
        else:
            revolutions = self.params.helix_revolutions
            
        # Generate points along helix
        points = []
        num_points = max(20, int(revolutions * 16))  # At least 16 points per revolution
        
        for i in range(num_points + 1):
            t = i / num_points
            theta = t * revolutions * 2 * np.pi
            x = center_x + helix_radius * np.cos(theta)
            y = center_y + helix_radius * np.sin(theta)
            z = start_z + t * (end_z - start_z)
            points.append(np.array([x, y, z]))
            
        return points

    def _generate_pocket_path(self) -> List[np.ndarray]:
        """
        Generate pocket toolpath using specified strategy at multiple Z-levels.
        
        The method generates toolpaths at each Z-level, working from top to bottom:
        1. Calculate Z-levels based on step_down and pocket_depth
        2. Filter active islands at each Z-level based on their Z-depth range
        3. Generate 2D toolpaths considering only active islands
        4. Add safe transitions between levels
        5. Include proper entry moves (plunge, ramp, or helix)
        
        Returns:
            List of 3D points defining the toolpath
        """
        # Extract boundary at current Z level
        boundary_2d = self._extract_contour_at_z(0.0)  # Boundary is same at all levels
        
        # Calculate Z-levels
        z_levels = []
        current_z = self.params.start_z
        while current_z > self.params.start_z - self.params.pocket_depth + self.params.final_pass_depth:
            z_levels.append(current_z)
            current_z -= self.params.step_down
        # Add final pass
        z_levels.append(self.params.start_z - self.params.pocket_depth)
        
        # Calculate tool and path parameters
        tool_radius = self.params.tool.diameter / 2.0
        stepover = tool_radius * self.params.stepover
        strategy = self.params.pocket_strategy
        
        complete_toolpath = []
        last_point = None
        
        # Process each Z-level
        for z_level in z_levels:
            # Filter active islands at this Z-level
            active_islands = None
            if self.params.islands:
                active_islands = []
                for island in self.params.islands:
                    if island['z_max'] >= z_level >= island['z_min']:
                        active_islands.append({
                            'points': island['points'],
                            'z_min': island['z_min'],
                            'z_max': island['z_max']
                        })
                if not active_islands:
                    active_islands = None
            
            # Generate 2D paths at this level
            paths_2d = []
            
            # Generate boundary following paths
            offset_paths = self._generate_pocket_boundary_paths(
                boundary_2d,
                tool_radius,
                stepover,
                active_islands
            )
            
            # Generate zigzag paths if using ZIGZAG or HYBRID strategy
            zigzag_paths = []
            if strategy in [PocketStrategy.ZIGZAG, PocketStrategy.HYBRID]:
                zigzag_paths = self._generate_pocket_zigzag_paths(
                    boundary_2d,
                    stepover,
                    self.params.pocket_angle,
                    active_islands
                )
            
            # Combine paths based on strategy
            if strategy == PocketStrategy.ZIGZAG:
                paths_2d = zigzag_paths
            elif strategy == PocketStrategy.SPIRAL:
                paths_2d = offset_paths
            else:  # HYBRID
                paths_2d = offset_paths + zigzag_paths
            
            # Optimize path connections
            optimized_2d = optimize_path_connections(paths_2d)
            
            # Add Z-level paths to complete toolpath
            if not complete_toolpath:
                # First Z-level - start with move to clearance height
                if optimized_2d and optimized_2d[0]:
                    start_point = optimized_2d[0][0]
                    complete_toolpath.append(np.array([
                        start_point[0],
                        start_point[1],
                        self.clearance_height
                    ]))
                    last_point = complete_toolpath[-1]
            
            # Process each path at this Z-level
            for path_2d in optimized_2d:
                if not path_2d:
                    continue
                
                # Move to path start point
                start_point = path_2d[0]
                if last_point is None or not np.array_equal(last_point[:2], start_point):
                    # Move to clearance height if needed
                    complete_toolpath.append(np.array([
                        last_point[0],
                        last_point[1],
                        self.clearance_height
                    ]))
                    # Move to start XY
                    complete_toolpath.append(np.array([
                        start_point[0],
                        start_point[1],
                        self.clearance_height
                    ]))
                
                # Add entry move based on entry_type
                if self.params.entry_type == "plunge":
                    # Direct plunge to Z-level
                    complete_toolpath.append(np.array([
                        start_point[0],
                        start_point[1],
                        z_level
                    ]))
                elif self.params.entry_type == "ramp":
                    # Calculate ramp points
                    ramp_angle_rad = np.radians(self.params.ramp_angle)
                    z_diff = last_point[2] - z_level
                    ramp_length = abs(z_diff / np.tan(ramp_angle_rad))
                    
                    # Create ramp points
                    num_points = max(2, int(ramp_length / (tool_radius * 0.1)))
                    for i in range(num_points):
                        t = i / (num_points - 1)
                        ramp_z = last_point[2] + t * (z_level - last_point[2])
                        complete_toolpath.append(np.array([
                            start_point[0],
                            start_point[1],
                            ramp_z
                        ]))
                elif self.params.entry_type == "helix":
                    # Generate helix points
                    helix_points = self._generate_helix_points(
                        start_point[0],
                        start_point[1],
                        last_point[2],
                        z_level
                    )
                    complete_toolpath.extend(helix_points)
                
                # Add cutting moves at this Z-level
                for point in path_2d[1:]:
                    complete_toolpath.append(np.array([point[0], point[1], z_level]))
                
                last_point = complete_toolpath[-1]
            
            # Retract to clearance height at end of level
            if last_point[2] != self.clearance_height:
                complete_toolpath.append(np.array([
                    last_point[0],
                    last_point[1],
                    self.clearance_height
                ]))
        
        return complete_toolpath
    
    def _generate_pocket_boundary_paths(
        self,
        boundary: List[np.ndarray],
        tool_radius: float,
        stepover: float,
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None
    ) -> List[List[np.ndarray]]:
        """
        Generate boundary following paths for pocket machining.
        
        Args:
            boundary: List of 2D points defining the pocket boundary
            tool_radius: Radius of the cutting tool
            stepover: Distance between consecutive paths
            islands: Optional list of islands to avoid
            
        Returns:
            List of 2D paths following the boundary
        """
        offset_paths = []
        current_offset = tool_radius  # Start at tool radius from boundary
        max_offsets = 100  # Prevent infinite loops
        
        # Offset islands outward by tool radius to ensure proper clearance
        offset_islands = None
        if islands:
            offset_islands = []
            for island_info in islands:
                island = island_info['island']
                if island is not None:
                    offset_island = offset_contour(
                        island,
                        tool_radius,
                        OffsetDirection.OUTSIDE
                    )
                    if offset_island:
                        offset_islands.append(offset_island)
        
        for i in range(max_offsets):
            # Generate offset contour
            offset_path = offset_contour(
                boundary,
                current_offset,
                OffsetDirection.INSIDE
            )
            
            # Check if path is valid
            if not offset_path or len(offset_path) < 3:
                break
                
            # Check if path intersects any offset islands
            if offset_islands:
                valid_segments = []
                # Convert offset path to line segments
                for j in range(len(offset_path) - 1):
                    start = offset_path[j]
                    end = offset_path[j + 1]
                    # Clip against all islands
                    clipped_segments = clip_line_to_polygon(
                        start, end, boundary, offset_islands
                    )
                    valid_segments.extend(clipped_segments)
                
                # Convert segments back to continuous paths
                if valid_segments:
                    # TODO: Implement path reconnection for split segments
                    # For now, just use the segments as separate paths
                    for segment in valid_segments:
                        offset_paths.append([segment.start, segment.end])
            else:
                offset_paths.append(offset_path)
                
            current_offset += stepover
            
        return offset_paths
    
    def _generate_pocket_zigzag_paths(
        self,
        boundary: List[np.ndarray],
        stepover: float,
        angle: float,
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None
    ) -> List[List[np.ndarray]]:
        """
        Generate zigzag paths for pocket machining.
        
        Uses line clipping to ensure paths stay within the boundary
        and avoid islands. Supports arbitrary angles for the zigzag pattern.
        
        Args:
            boundary: List of 2D points defining the pocket boundary
            stepover: Distance between parallel paths
            angle: Angle of zigzag paths in radians
            islands: Optional list of islands to avoid
            
        Returns:
            List of 2D zigzag paths clipped to boundary and avoiding islands
        """
        # Generate parallel lines
        parallel_paths = generate_parallel_paths(boundary, stepover, angle)
        
        # Offset islands outward by tool radius to ensure proper clearance
        offset_islands = None
        if islands:
            offset_islands = []
            for island_info in islands:
                island = island_info['island']
                if island is not None:
                    offset_island = offset_contour(
                        island,
                        self.params.tool.diameter / 2.0,
                        OffsetDirection.OUTSIDE
                    )
                    if offset_island:
                        offset_islands.append(offset_island)
        
        # Clip paths to boundary and avoid islands
        clipped_paths = []
        for path in parallel_paths:
            # Clip line against polygon and islands
            clipped_segments = clip_line_to_polygon(
                path[0], path[1], boundary, offset_islands
            )
            
            # Add valid segments, alternating direction for better machining
            for i, segment in enumerate(clipped_segments):
                if len(clipped_paths) % 2 == 1:
                    clipped_paths.append([segment.end, segment.start])
                else:
                    clipped_paths.append([segment.start, segment.end])
                
        return clipped_paths
    
    def _convert_2d_paths_to_3d_toolpath(
        self,
        paths_2d: List[List[np.ndarray]]
    ) -> List[np.ndarray]:
        """
        Convert 2D paths to 3D toolpath with safety moves.
        
        Args:
            paths_2d: List of 2D paths to convert
            
        Returns:
            List of 3D points with safety moves
        """
        toolpath = []
        z_cut = 0.0  # TODO: Use actual cutting depth
        
        # Add initial move to clearance height if paths exist
        if paths_2d and paths_2d[0]:
            start_point = paths_2d[0][0]
            toolpath.append(np.array([
                start_point[0],
                start_point[1],
                self.clearance_height
            ]))
        
        # Process each path
        for path_2d in paths_2d:
            if not path_2d:
                continue
                
            # Move to start point at clearance height
            start_point = path_2d[0]
            toolpath.append(np.array([
                start_point[0],
                start_point[1],
                self.clearance_height
            ]))
            
            # Plunge to cutting depth
            toolpath.append(np.array([
                start_point[0],
                start_point[1],
                z_cut
            ]))
            
            # Add cutting moves
            for point in path_2d[1:]:
                toolpath.append(np.array([point[0], point[1], z_cut]))
            
            # Retract to clearance height
            end_point = path_2d[-1]
            toolpath.append(np.array([
                end_point[0],
                end_point[1],
                self.clearance_height
            ]))
        
        return toolpath
        
    def _generate_surface_path(self) -> List[np.ndarray]:
        """Generate surface toolpath."""
        # TODO: Implement surface path generation
        pass
        
    def _extract_contour_at_z(self, z: float) -> List[np.ndarray]:
        """
        Extract a 2D contour from the model at given Z height.
        
        Args:
            z: Z height to extract contour
            
        Returns:
            List of 2D points defining the contour
        """
        # TODO: Implement actual contour extraction from model
        # For testing, return a simple rectangle
        return [
            np.array([0.0, 0.0]),
            np.array([50.0, 0.0]),
            np.array([50.0, 30.0]),
            np.array([0.0, 30.0]),
            np.array([0.0, 0.0])
        ]
        
    def optimize_path(self) -> None:
        """Optimize the generated toolpath."""
        if not self.toolpath:
            return
            
        # Split paths at clearance height moves
        paths = []
        current_path = []
        
        for point in self.toolpath:
            if point[2] == self.clearance_height and current_path:
                if len(current_path) > 1:
                    paths.append(current_path)
                current_path = []
            current_path.append(point)
            
        if current_path and len(current_path) > 1:
            paths.append(current_path)
            
        # Optimize connections between paths
        if paths:
            optimized = optimize_path_connections(paths)
            self.toolpath = [point for path in optimized for point in path] 