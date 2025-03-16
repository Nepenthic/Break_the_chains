from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
import trimesh

@dataclass
class Transform:
    """Represents a 3D transformation with position, rotation, and scale."""
    position: np.ndarray = np.array([0.0, 0.0, 0.0])
    rotation: np.ndarray = np.array([0.0, 0.0, 0.0])  # Euler angles in radians
    scale: np.ndarray = np.array([1.0, 1.0, 1.0])

class Shape:
    """Base class for all 3D shapes in the CAD/CAM program."""
    
    def __init__(self, transform: Optional[Transform] = None):
        """Initialize a shape with an optional transform."""
        self.transform = transform or Transform()
        self._mesh: Optional[trimesh.Trimesh] = None
        self._selected: bool = False
        self._hovered: bool = False
        self._transform_mode: Optional[str] = None
        self._active_axis: Optional[str] = None
        self._gizmo_scale: float = 1.0  # Scale factor for transform gizmos
        
        # Snapping configuration
        self._snap_enabled: bool = True
        self._snap_translate: float = 0.25  # Grid size for translation (units)
        self._snap_rotate: float = 15.0  # Angle snap increment (degrees)
        self._snap_scale: float = 0.25  # Scale snap increment
    
    @property
    def selected(self) -> bool:
        """Get the selection state of the shape."""
        return self._selected
    
    @selected.setter
    def selected(self, value: bool) -> None:
        """Set the selection state of the shape."""
        self._selected = value
        if not value:
            # Clear transform mode when deselected
            self._transform_mode = None
            self._active_axis = None
    
    @property
    def hovered(self) -> bool:
        """Get the hover state of the shape."""
        return self._hovered
    
    @hovered.setter
    def hovered(self, value: bool) -> None:
        """Set the hover state of the shape."""
        self._hovered = value
    
    @property
    def transform_mode(self) -> Optional[str]:
        """Get the current transform mode."""
        return self._transform_mode
    
    @transform_mode.setter
    def transform_mode(self, value: Optional[str]) -> None:
        """Set the current transform mode."""
        self._transform_mode = value
        if not value:
            self._active_axis = None
    
    @property
    def active_axis(self) -> Optional[str]:
        """Get the currently active transform axis."""
        return self._active_axis
    
    @active_axis.setter
    def active_axis(self, value: Optional[str]) -> None:
        """Set the currently active transform axis."""
        self._active_axis = value
    
    @property
    def gizmo_scale(self) -> float:
        """Get the scale factor for transform gizmos."""
        return self._gizmo_scale
    
    @gizmo_scale.setter
    def gizmo_scale(self, value: float) -> None:
        """Set the scale factor for transform gizmos."""
        self._gizmo_scale = max(0.1, value)  # Ensure minimum scale
    
    @property
    def snap_enabled(self) -> bool:
        """Get whether snapping is enabled."""
        return self._snap_enabled
    
    @snap_enabled.setter
    def snap_enabled(self, value: bool) -> None:
        """Set whether snapping is enabled."""
        self._snap_enabled = value
    
    def set_snap_values(self, translate: float = 0.25, rotate: float = 15.0, scale: float = 0.25) -> None:
        """Set snapping increment values."""
        self._snap_translate = max(0.001, translate)
        self._snap_rotate = max(0.001, rotate)
        self._snap_scale = max(0.001, scale)
    
    def _snap_value(self, value: float, increment: float) -> float:
        """Snap a value to the nearest increment."""
        if not self._snap_enabled or increment <= 0:
            return value
        return round(value / increment) * increment
    
    def get_transform_color(self) -> Tuple[float, float, float, float]:
        """Get the color to use for rendering based on current state."""
        if self._selected:
            if self._transform_mode:
                # Show transform-specific colors
                if self._transform_mode == "translate":
                    return (0.2, 0.6, 1.0, 1.0)  # Blue for translation
                elif self._transform_mode == "rotate":
                    return (0.2, 1.0, 0.2, 1.0)  # Green for rotation
                elif self._transform_mode == "scale":
                    return (1.0, 0.6, 0.2, 1.0)  # Orange for scale
            return (1.0, 1.0, 0.0, 1.0)  # Yellow for selection
        elif self._hovered:
            return (0.8, 0.8, 0.8, 1.0)  # Light gray for hover
        return (0.7, 0.7, 0.7, 1.0)  # Default gray
    
    def get_axis_color(self, axis: str) -> Tuple[float, float, float, float]:
        """Get the color for a transform axis."""
        if self._active_axis == axis:
            return (1.0, 1.0, 1.0, 1.0)  # White for active axis
        if axis == 'x':
            return (1.0, 0.2, 0.2, 1.0)  # Red for X
        elif axis == 'y':
            return (0.2, 1.0, 0.2, 1.0)  # Green for Y
        else:  # z
            return (0.2, 0.2, 1.0, 1.0)  # Blue for Z
    
    def get_mesh(self) -> trimesh.Trimesh:
        """Get the trimesh representation of the shape."""
        if self._mesh is None:
            self._mesh = self._create_mesh()
        return self._apply_transform(self._mesh)
    
    def _create_mesh(self) -> trimesh.Trimesh:
        """Create the base mesh for the shape. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _create_mesh()")
    
    def _apply_transform(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Apply the current transformation to the mesh."""
        # Create a copy to avoid modifying the original
        transformed = mesh.copy()
        
        # Apply scale
        transformed.apply_scale(self.transform.scale)
        
        # Apply rotation (Euler angles)
        rotation_matrix = trimesh.transformations.euler_matrix(
            *self.transform.rotation, axes='rxyz'
        )
        transformed.apply_transform(rotation_matrix)
        
        # Apply translation
        transformed.apply_translation(self.transform.position)
        
        return transformed
    
    def translate(self, x: float, y: float, z: float) -> None:
        """Translate the shape by the given amounts."""
        if self._snap_enabled:
            x = self._snap_value(x, self._snap_translate)
            y = self._snap_value(y, self._snap_translate)
            z = self._snap_value(z, self._snap_translate)
        self.transform.position += np.array([x, y, z])
    
    def rotate(self, x: float, y: float, z: float) -> None:
        """Rotate the shape by the given angles (in radians)."""
        if self._snap_enabled:
            # Convert to degrees for snapping
            snap_increment = np.radians(self._snap_rotate)
            x = self._snap_value(x, snap_increment)
            y = self._snap_value(y, snap_increment)
            z = self._snap_value(z, snap_increment)
        self.transform.rotation += np.array([x, y, z])
    
    def scale(self, x: float, y: float, z: float) -> None:
        """Scale the shape by the given factors."""
        if self._snap_enabled:
            x = self._snap_value(x, self._snap_scale)
            y = self._snap_value(y, self._snap_scale)
            z = self._snap_value(z, self._snap_scale)
        self.transform.scale *= np.array([x, y, z])
    
    def export_stl(self, filepath: str) -> None:
        """Export the shape to an STL file."""
        mesh = self.get_mesh()
        mesh.export(filepath)
    
    def intersect_ray(self, ray_origin: np.ndarray, ray_direction: np.ndarray) -> Tuple[bool, float]:
        """
        Test if a ray intersects with this shape.
        
        Args:
            ray_origin: Origin point of the ray in world space (3D vector)
            ray_direction: Direction vector of the ray in world space (3D vector)
            
        Returns:
            tuple: (hit, distance) where hit is a boolean indicating if there was an intersection,
                  and distance is the distance from ray origin to the intersection point
        """
        # Get the mesh and test intersection
        mesh = self.get_mesh()
        locations, index_ray, index_tri = mesh.ray.intersects_location(
            ray_origins=[ray_origin],
            ray_directions=[ray_direction]
        )
        
        if len(locations) > 0:
            # Calculate distance to closest intersection
            distances = np.linalg.norm(locations - ray_origin, axis=1)
            return True, np.min(distances)
        
        return False, float('inf')
    
    def get_gizmo_transform(self) -> Transform:
        """Get the transform for gizmo rendering."""
        gizmo_transform = Transform()
        gizmo_transform.position = self.transform.position.copy()
        gizmo_transform.rotation = self.transform.rotation.copy()
        gizmo_transform.scale = np.array([self._gizmo_scale] * 3)
        return gizmo_transform
    
    def create_axis_gizmo(self, axis: str) -> trimesh.Trimesh:
        """Create a gizmo mesh for the specified axis."""
        if self._transform_mode == "translate":
            return self._create_translate_gizmo(axis)
        elif self._transform_mode == "rotate":
            return self._create_rotate_gizmo(axis)
        elif self._transform_mode == "scale":
            return self._create_scale_gizmo(axis)
        return None
    
    def _create_translate_gizmo(self, axis: str) -> trimesh.Trimesh:
        """Create a translation gizmo for the specified axis."""
        # Create arrow mesh
        arrow_length = 1.0 * self._gizmo_scale
        arrow_radius = 0.02 * self._gizmo_scale
        head_radius = 0.05 * self._gizmo_scale
        head_length = 0.2 * self._gizmo_scale
        
        # Create arrow shaft
        shaft = trimesh.creation.cylinder(
            radius=arrow_radius,
            height=arrow_length - head_length,
            sections=12
        )
        
        # Create arrow head
        head = trimesh.creation.cone(
            radius=head_radius,
            height=head_length,
            sections=12
        )
        
        # Position head at end of shaft
        head.apply_translation([0, 0, (arrow_length - head_length) / 2])
        
        # Combine shaft and head
        arrow = trimesh.util.concatenate([shaft, head])
        
        # Rotate to align with axis
        if axis == 'x':
            arrow.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
        elif axis == 'y':
            arrow.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0]))
        
        return arrow
    
    def _create_rotate_gizmo(self, axis: str) -> trimesh.Trimesh:
        """Create a rotation gizmo for the specified axis."""
        # Create ring mesh
        ring_radius = 1.0 * self._gizmo_scale
        tube_radius = 0.02 * self._gizmo_scale
        
        # Create torus
        ring = trimesh.creation.annulus(
            r_min=ring_radius - tube_radius,
            r_max=ring_radius + tube_radius,
            height=tube_radius * 2,
            sections=32
        )
        
        # Rotate to align with axis
        if axis == 'x':
            ring.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
        elif axis == 'y':
            ring.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
        
        return ring
    
    def _create_scale_gizmo(self, axis: str) -> trimesh.Trimesh:
        """Create a scale gizmo for the specified axis."""
        # Create cube handle mesh
        handle_size = 0.1 * self._gizmo_scale
        line_length = 1.0 * self._gizmo_scale
        line_radius = 0.01 * self._gizmo_scale
        
        # Create handle cube
        handle = trimesh.creation.box(extents=[handle_size] * 3)
        
        # Create line
        line = trimesh.creation.cylinder(
            radius=line_radius,
            height=line_length,
            sections=12
        )
        
        # Position handle at end of line
        handle.apply_translation([0, 0, line_length/2])
        
        # Combine line and handle
        gizmo = trimesh.util.concatenate([line, handle])
        
        # Rotate to align with axis
        if axis == 'x':
            gizmo.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
        elif axis == 'y':
            gizmo.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0]))
        
        return gizmo
    
    def get_gizmo_meshes(self) -> List[Tuple[trimesh.Trimesh, Tuple[float, float, float, float]]]:
        """Get a list of (mesh, color) tuples for transform gizmos."""
        if not self._selected or not self._transform_mode:
            return []
        
        gizmos = []
        for axis in ['x', 'y', 'z']:
            gizmo_mesh = self.create_axis_gizmo(axis)
            if gizmo_mesh is not None:
                # Apply gizmo transform
                gizmo_transform = self.get_gizmo_transform()
                gizmo_mesh = self._apply_transform(gizmo_mesh)
                gizmos.append((gizmo_mesh, self.get_axis_color(axis)))
        
        return gizmos 