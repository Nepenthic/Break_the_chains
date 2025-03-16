"""
Sketch manager module for handling 2D sketch creation and management.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from .entities import Point2D, Line2D, Arc2D, Circle2D, Spline2D
from .constraints import ConstraintSolver

@dataclass
class SketchPlane:
    """Represents a plane on which sketches can be created."""
    origin: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    normal: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 1.0]))
    x_axis: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0, 0.0]))
    
    def __post_init__(self):
        """Normalize vectors and ensure orthogonality."""
        self.normal = self.normal / np.linalg.norm(self.normal)
        self.x_axis = self.x_axis - np.dot(self.x_axis, self.normal) * self.normal
        self.x_axis = self.x_axis / np.linalg.norm(self.x_axis)
        self.y_axis = np.cross(self.normal, self.x_axis)

class SketchManager:
    """Manages sketch creation, modification, and constraints."""
    
    def __init__(self):
        self.entities: Dict[str, Union[Point2D, Line2D, Arc2D, Circle2D, Spline2D]] = {}
        self.constraint_solver = ConstraintSolver()
        self.active_plane = SketchPlane()
        self._next_id = 1

    def create_sketch_plane(self, origin: np.ndarray, normal: np.ndarray, 
                          x_axis: Optional[np.ndarray] = None) -> SketchPlane:
        """Create a new sketch plane with given parameters."""
        if x_axis is None:
            # Generate a reasonable x-axis based on the normal
            if not np.allclose(normal, [0, 1, 0]):
                x_axis = np.cross([0, 1, 0], normal)
            else:
                x_axis = np.array([1, 0, 0])
        
        plane = SketchPlane(origin=origin, normal=normal, x_axis=x_axis)
        return plane

    def start_sketch(self, plane: Optional[SketchPlane] = None) -> None:
        """Start a new sketch on the specified plane."""
        if plane is not None:
            self.active_plane = plane
        self.entities.clear()
        self.constraint_solver.clear()

    def add_point(self, x: float, y: float) -> str:
        """Add a point to the sketch."""
        point_id = f"P{self._next_id}"
        self._next_id += 1
        self.entities[point_id] = Point2D(x, y)
        return point_id

    def add_line(self, start_x: float, start_y: float, 
                end_x: float, end_y: float) -> str:
        """Add a line to the sketch."""
        line_id = f"L{self._next_id}"
        self._next_id += 1
        self.entities[line_id] = Line2D(
            Point2D(start_x, start_y),
            Point2D(end_x, end_y)
        )
        return line_id

    def add_circle(self, center_x: float, center_y: float, 
                  radius: float) -> str:
        """Add a circle to the sketch."""
        circle_id = f"C{self._next_id}"
        self._next_id += 1
        self.entities[circle_id] = Circle2D(
            Point2D(center_x, center_y),
            radius
        )
        return circle_id

    def add_arc(self, center_x: float, center_y: float,
                radius: float, start_angle: float, end_angle: float) -> str:
        """Add an arc to the sketch."""
        arc_id = f"A{self._next_id}"
        self._next_id += 1
        self.entities[arc_id] = Arc2D(
            Point2D(center_x, center_y),
            radius,
            start_angle,
            end_angle
        )
        return arc_id

    def add_spline(self, control_points: List[Tuple[float, float]]) -> str:
        """Add a spline curve to the sketch."""
        spline_id = f"S{self._next_id}"
        self._next_id += 1
        points = [Point2D(x, y) for x, y in control_points]
        self.entities[spline_id] = Spline2D(points)
        return spline_id

    def add_constraint(self, constraint_type: str, 
                      entity_ids: List[str], 
                      value: Optional[float] = None) -> bool:
        """Add a geometric constraint to the sketch."""
        return self.constraint_solver.add_constraint(
            constraint_type, 
            [self.entities[eid] for eid in entity_ids],
            value
        )

    def solve_constraints(self) -> bool:
        """Solve all constraints in the sketch."""
        return self.constraint_solver.solve()

    def get_entity(self, entity_id: str) -> Optional[Union[Point2D, Line2D, Arc2D, Circle2D, Spline2D]]:
        """Get an entity by its ID."""
        return self.entities.get(entity_id)

    def update_entity(self, entity_id: str, 
                     new_geometry: Union[Point2D, Line2D, Arc2D, Circle2D, Spline2D]) -> bool:
        """Update an entity's geometry."""
        if entity_id in self.entities:
            if isinstance(new_geometry, type(self.entities[entity_id])):
                self.entities[entity_id] = new_geometry
                return True
        return False

    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity from the sketch."""
        if entity_id in self.entities:
            del self.entities[entity_id]
            self.constraint_solver.remove_entity_constraints(entity_id)
            return True
        return False

    def get_sketch_plane_transform(self) -> np.ndarray:
        """Get the transformation matrix for the current sketch plane."""
        rotation = np.column_stack([
            self.active_plane.x_axis,
            self.active_plane.y_axis,
            self.active_plane.normal
        ])
        transform = np.eye(4)
        transform[:3, :3] = rotation
        transform[:3, 3] = self.active_plane.origin
        return transform 