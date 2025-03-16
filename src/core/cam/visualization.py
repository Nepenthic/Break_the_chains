"""
Visualization utilities for CAM toolpath debugging and validation.
"""

from typing import List, Dict, Union, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Polygon
import matplotlib.colors as mcolors

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
        
    def plot_toolpath(
        self,
        toolpath: List[np.ndarray],
        islands: Optional[List[Dict[str, Union[List[np.ndarray], float]]]] = None,
        show_clearance: bool = True,
        show_entry_points: bool = True,
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
            z_filter: Optional Z-level to filter moves (show only moves at this level)
            title: Optional title for the plot
        """
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot toolpath
        if z_filter is not None:
            # Show only moves at specific Z-level
            points = [p for p in toolpath if abs(p[2] - z_filter) < 0.01]
            if points:
                xs, ys, zs = zip(*points)
                ax.plot(xs, ys, zs, 'g-', linewidth=2, label=f'Moves at Z={z_filter}')
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