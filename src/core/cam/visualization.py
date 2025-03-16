"""
Visualization utilities for CAM toolpath debugging and validation.
"""

from typing import List, Dict, Union, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Polygon, Circle
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

class ToolVisualizer:
    """Handles 3D visualization of cutting tools."""
    
    def __init__(self, tool_params):
        """
        Initialize tool visualizer.
        
        Args:
            tool_params: Tool parameters (diameter, length, etc.)
        """
        self.tool_params = tool_params
        self.resolution = 32  # Number of points for circular cross-sections
        
    def generate_tool_mesh(self) -> Tuple[List[np.ndarray], List[List[int]]]:
        """
        Generate a 3D mesh representation of the tool.
        
        Returns:
            Tuple of (vertices, faces) for the tool mesh
        """
        diameter = self.tool_params.diameter
        length = self.tool_params.length
        shank_diameter = self.tool_params.shank_diameter
        
        # Generate points around the circumference
        theta = np.linspace(0, 2*np.pi, self.resolution)
        
        # Cutting portion vertices
        cutting_r = diameter / 2
        cutting_bottom = np.array([[cutting_r * np.cos(t), cutting_r * np.sin(t), 0] 
                                 for t in theta])
        cutting_top = np.array([[cutting_r * np.cos(t), cutting_r * np.sin(t), length/2] 
                              for t in theta])
        
        # Shank portion vertices
        shank_r = shank_diameter / 2
        shank_bottom = np.array([[shank_r * np.cos(t), shank_r * np.sin(t), length/2] 
                               for t in theta])
        shank_top = np.array([[shank_r * np.cos(t), shank_r * np.sin(t), length] 
                            for t in theta])
        
        # Combine vertices
        vertices = np.vstack([cutting_bottom, cutting_top, shank_bottom, shank_top])
        
        # Generate faces
        faces = []
        n = self.resolution
        
        # Cutting portion faces
        for i in range(n-1):
            # Side faces
            faces.append([i, i+1, i+n+1, i+n])
            # Bottom cap
            faces.append([i, i+1, n-1])
        # Close the cylinder
        faces.append([n-1, 0, n, 2*n-1])
        faces.append([n-1, 0, n-1])
        
        # Shank portion faces (offset by 2*n for the cutting portion)
        offset = 2*n
        for i in range(n-1):
            faces.append([i+offset, i+1+offset, i+n+1+offset, i+n+offset])
        faces.append([offset+n-1, offset, offset+n, offset+2*n-1])
        
        return vertices, faces
        
    def transform_tool_mesh(
        self,
        vertices: List[np.ndarray],
        position: np.ndarray,
        direction: Optional[np.ndarray] = None
    ) -> List[np.ndarray]:
        """
        Transform tool mesh to a specific position and orientation.
        
        Args:
            vertices: List of vertex coordinates
            position: Target position (x, y, z)
            direction: Optional tool direction vector
            
        Returns:
            Transformed vertex coordinates
        """
        # Create transformation matrix
        transform = np.eye(4)
        
        # Set translation
        transform[:3, 3] = position
        
        # Set rotation if direction is provided
        if direction is not None:
            direction = direction / np.linalg.norm(direction)
            z_axis = np.array([0, 0, 1])
            
            # Calculate rotation axis and angle
            rotation_axis = np.cross(z_axis, direction)
            if np.any(rotation_axis):
                rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
                cos_angle = np.dot(z_axis, direction)
                angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
                
                # Create rotation matrix using Rodrigues' formula
                K = np.array([
                    [0, -rotation_axis[2], rotation_axis[1]],
                    [rotation_axis[2], 0, -rotation_axis[0]],
                    [-rotation_axis[1], rotation_axis[0], 0]
                ])
                R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * K @ K
                transform[:3, :3] = R
        
        # Apply transformation to vertices
        vertices_homogeneous = np.hstack([vertices, np.ones((len(vertices), 1))])
        transformed_vertices = (transform @ vertices_homogeneous.T).T
        return transformed_vertices[:, :3]

class ToolpathVisualizer:
    """Visualizes toolpaths and islands for debugging and validation."""
    
    def __init__(self, clearance_height: float = 10.0):
        """
        Initialize the visualizer.
        
        Args:
            clearance_height: Z-level for clearance moves
        """
        self.clearance_height = clearance_height
        self.colors = list(mcolors.TABLEAU_COLORS)
        self.tool_visualizer = None
        
    def plot_toolpath(
        self,
        toolpath: List[np.ndarray],
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None,
        show_clearance: bool = True,
        show_entry_points: bool = True,
        show_tool: bool = False,
        tool_params = None,
        z_filter: Optional[float] = None,
        title: Optional[str] = None
    ) -> None:
        """
        Create a 3D visualization of the toolpath and islands.
        
        Args:
            toolpath: List of 3D points defining the toolpath
            islands: Optional list of islands with Z-depth information
            show_clearance: Whether to show clearance moves
            show_entry_points: Whether to highlight entry points
            show_tool: Whether to show tool representation
            tool_params: Tool parameters for visualization
            z_filter: Optional Z-level to filter moves
            title: Optional title for the plot
        """
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Initialize tool visualizer if needed
        if show_tool and tool_params:
            self.tool_visualizer = ToolVisualizer(tool_params)
            tool_vertices, tool_faces = self.tool_visualizer.generate_tool_mesh()
        
        # Plot toolpath
        if z_filter is not None:
            # Show only moves at specific Z-level
            points = [p for p in toolpath if abs(p[2] - z_filter) < 0.01]
            if points:
                xs, ys, zs = zip(*points)
                ax.plot(xs, ys, zs, 'g-', linewidth=2, label=f'Moves at Z={z_filter}')
                
                # Show tool at filtered level if enabled
                if show_tool and tool_params:
                    self._plot_tool_at_points(ax, points, tool_vertices, tool_faces)
        else:
            # Separate moves by type
            cutting_moves = []
            clearance_moves = []
            current_move = []
            
            for point in toolpath:
                if abs(point[2] - self.clearance_height) < 0.01:
                    if current_move:
                        if abs(current_move[0][2] - self.clearance_height) < 0.01:
                            clearance_moves.append(current_move)
                        else:
                            cutting_moves.append(current_move)
                        current_move = []
                current_move.append(point)
                
            if current_move:
                if abs(current_move[0][2] - self.clearance_height) < 0.01:
                    clearance_moves.append(current_move)
                else:
                    cutting_moves.append(current_move)
            
            # Plot cutting moves
            for move in cutting_moves:
                xs, ys, zs = zip(*move)
                ax.plot(xs, ys, zs, 'b-', linewidth=2, label='Cutting moves')
                
                # Show tool along cutting moves if enabled
                if show_tool and tool_params:
                    self._plot_tool_at_points(ax, move, tool_vertices, tool_faces)
            
            # Plot clearance moves if enabled
            if show_clearance:
                for move in clearance_moves:
                    xs, ys, zs = zip(*move)
                    ax.plot(xs, ys, zs, 'r--', alpha=0.5, label='Clearance moves')
            
            # Highlight entry points if enabled
            if show_entry_points:
                entry_points = []
                for i in range(len(toolpath) - 1):
                    if (abs(toolpath[i][2] - self.clearance_height) < 0.01 and
                        toolpath[i+1][2] < self.clearance_height):
                        entry_points.append(toolpath[i+1])
                
                if entry_points:
                    xs, ys, zs = zip(*entry_points)
                    ax.scatter(xs, ys, zs, c='g', marker='o', s=100, label='Entry points')
        
        # Plot islands if provided
        if islands:
            self._plot_islands(ax, islands, z_filter)
        
        # Set labels and title
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        if title:
            ax.set_title(title)
        
        # Remove duplicate labels
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys())
        
        # Show the plot
        plt.show()
        
    def _plot_tool_at_points(
        self,
        ax: Axes3D,
        points: List[np.ndarray],
        tool_vertices: List[np.ndarray],
        tool_faces: List[List[int]],
        sample_rate: int = 10
    ) -> None:
        """
        Plot tool representation at specified points along the toolpath.
        
        Args:
            ax: The 3D axes to plot on
            points: List of points to show the tool at
            tool_vertices: Base tool mesh vertices
            tool_faces: Tool mesh face indices
            sample_rate: Plot tool every N points
        """
        for i in range(0, len(points), sample_rate):
            point = points[i]
            
            # Calculate tool direction if not at the end
            direction = None
            if i < len(points) - 1:
                direction = points[i+1] - point
            
            # Transform tool mesh to current position
            transformed_vertices = self.tool_visualizer.transform_tool_mesh(
                tool_vertices, point, direction
            )
            
            # Create tool mesh
            tool_poly = Poly3DCollection([transformed_vertices[face] for face in tool_faces])
            tool_poly.set_alpha(0.3)
            tool_poly.set_facecolor('gray')
            ax.add_collection3d(tool_poly)
        
    def _plot_islands(
        self,
        ax: Axes3D,
        islands: List[Dict[str, Union[List[np.ndarray], float]]],
        z_filter: Optional[float] = None
    ) -> None:
        """
        Plot islands on the 3D axes.
        
        Args:
            ax: The 3D axes to plot on
            islands: List of islands with Z-depth information
            z_filter: Optional Z-level to filter islands
        """
        for i, island in enumerate(islands):
            color = self.colors[i % len(self.colors)]
            points = island['points']
            z_min = island['z_min']
            z_max = island['z_max']
            
            if z_filter is not None:
                # Only show islands active at this Z-level
                if not (z_min <= z_filter <= z_max):
                    continue
                z_levels = [z_filter]
            else:
                # Show islands at multiple Z-levels
                z_levels = np.linspace(z_min, z_max, 5)
            
            # Plot island boundaries at each Z-level
            for z_level in z_levels:
                xs, ys = zip(*points)
                zs = [z_level] * len(xs)
                
                # Plot boundary
                ax.plot(xs, ys, zs, '-', color=color, alpha=0.5,
                       label=f'Island {i+1} (Z={z_level:.1f})')
                
                # Fill polygon at this level
                verts = [(x, y, z_level) for x, y in zip(xs, ys)]
                poly = Polygon([(x, y) for x, y in zip(xs, ys)],
                             facecolor=color, alpha=0.2)
                ax.add_collection3d(poly, zs=z_level)
                
            # Add vertical lines at corners to show height
            if z_filter is None:
                for x, y in points[:-1]:  # Exclude last point (same as first)
                    ax.plot([x, x], [y, y], [z_min, z_max],
                           '--', color=color, alpha=0.3)
                    
    def create_animation(
        self,
        toolpath: List[np.ndarray],
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None,
        output_file: Optional[str] = None
    ) -> None:
        """
        Create an animated visualization of the toolpath generation.
        
        Args:
            toolpath: List of 3D points defining the toolpath
            islands: Optional list of islands with Z-depth information
            output_file: Optional file path to save the animation
        """
        # TODO: Implement animation using matplotlib.animation
        pass 