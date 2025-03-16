"""
Core sketch functionality including geometric entities and constraints.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
import uuid
import numpy as np
from enum import Enum, auto
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import logging

class ConstraintType(Enum):
    """Types of geometric constraints."""
    COINCIDENT = auto()
    PARALLEL = auto()
    PERPENDICULAR = auto()
    HORIZONTAL = auto()
    VERTICAL = auto()
    TANGENT = auto()
    EQUAL = auto()
    FIXED = auto()
    DISTANCE = auto()
    ANGLE = auto()
    CONCENTRIC = auto()

@dataclass
class Point2D:
    """2D point representation."""
    x: float
    y: float
    id: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

    def distance_to(self, other: 'Point2D') -> float:
        """Calculate distance to another point."""
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def move_to(self, x: float, y: float):
        """Move point to new coordinates."""
        self.x = x
        self.y = y

@dataclass
class Line2D:
    """2D line segment representation."""
    start: Point2D
    end: Point2D
    id: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

    def length(self) -> float:
        """Calculate line length."""
        return self.start.distance_to(self.end)

    def direction(self) -> Tuple[float, float]:
        """Get normalized direction vector."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        length = np.sqrt(dx*dx + dy*dy)
        return (dx/length, dy/length) if length > 0 else (0, 0)

@dataclass
class Circle2D:
    """2D circle representation."""
    center: Point2D
    radius: float
    id: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

    def contains_point(self, point: Point2D, tolerance: float = 1e-6) -> bool:
        """Check if point lies on circle circumference."""
        return abs(self.center.distance_to(point) - self.radius) < tolerance

@dataclass
class Arc2D:
    """2D arc representation."""
    center: Point2D
    radius: float
    start_angle: float  # in radians
    end_angle: float    # in radians
    id: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

    def angle_span(self) -> float:
        """Calculate angular span of arc in radians."""
        span = self.end_angle - self.start_angle
        return span if span >= 0 else span + 2*np.pi

@dataclass
class Spline2D:
    """2D spline representation using control points."""
    control_points: List[Point2D]
    degree: int = 3
    id: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

@dataclass
class Constraint:
    """Geometric constraint between entities."""
    type: ConstraintType
    entities: List[str]  # entity IDs
    parameters: Dict = None
    id: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.parameters is None:
            self.parameters = {}

class ConstraintSolver:
    """Solves geometric constraints in parallel."""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or max(2, cpu_count() - 1)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.update_queue = Queue()
        self._start_update_worker()

    def _start_update_worker(self):
        """Start background worker for processing updates."""
        def update_worker():
            while True:
                update_func, args = self.update_queue.get()
                try:
                    update_func(*args)
                except Exception as e:
                    logging.error(f"Error in update worker: {e}")
                self.update_queue.task_done()
        
        self.update_thread = threading.Thread(
            target=update_worker, daemon=True
        )
        self.update_thread.start()

    def solve_constraint(self, constraint: 'Constraint',
                        entities: Dict[str, Any]) -> bool:
        """Solve a single constraint."""
        try:
            if constraint.type == ConstraintType.COINCIDENT:
                return self._solve_coincident(constraint, entities)
            elif constraint.type == ConstraintType.PARALLEL:
                return self._solve_parallel(constraint, entities)
            elif constraint.type == ConstraintType.PERPENDICULAR:
                return self._solve_perpendicular(constraint, entities)
            elif constraint.type == ConstraintType.TANGENT:
                return self._solve_tangent(constraint, entities)
            elif constraint.type == ConstraintType.EQUAL:
                return self._solve_equal(constraint, entities)
            elif constraint.type == ConstraintType.HORIZONTAL:
                return self._solve_horizontal(constraint, entities)
            elif constraint.type == ConstraintType.VERTICAL:
                return self._solve_vertical(constraint, entities)
            elif constraint.type == ConstraintType.CONCENTRIC:
                return self._solve_concentric(constraint, entities)
            return True
        except Exception as e:
            logging.error(f"Error solving constraint {constraint.id}: {e}")
            return False

    def _solve_coincident(self, constraint: 'Constraint',
                         entities: Dict[str, Any]) -> bool:
        """Solve coincident constraint between points."""
        if len(constraint.entities) != 2:
            return False
        
        p1_id, p2_id = constraint.entities
        p1 = entities.get(p1_id)
        p2 = entities.get(p2_id)
        
        if not (isinstance(p1, Point2D) and isinstance(p2, Point2D)):
            return False
        
        # Calculate midpoint
        mid_x = (p1.x + p2.x) / 2
        mid_y = (p1.y + p2.y) / 2
        
        # Move both points to midpoint
        p1.move_to(mid_x, mid_y)
        p2.move_to(mid_x, mid_y)
        return True

    def _solve_parallel(self, constraint: 'Constraint',
                       entities: Dict[str, Any]) -> bool:
        """Solve parallel constraint between lines."""
        if len(constraint.entities) != 2:
            return False
        
        l1_id, l2_id = constraint.entities
        l1 = entities.get(l1_id)
        l2 = entities.get(l2_id)
        
        if not (isinstance(l1, Line2D) and isinstance(l2, Line2D)):
            return False
        
        # Get direction vectors
        dir1_x, dir1_y = l1.direction()
        dir2_x, dir2_y = l2.direction()
        
        # Calculate angle between lines
        dot_product = dir1_x * dir2_x + dir1_y * dir2_y
        if abs(abs(dot_product) - 1) < 1e-6:
            return True  # Already parallel
        
        # Rotate second line to be parallel
        length = l2.length()
        if length > 0:
            l2.end.x = l2.start.x + dir1_x * length
            l2.end.y = l2.start.y + dir1_y * length
        return True

    def _solve_perpendicular(self, constraint: 'Constraint',
                           entities: Dict[str, Any]) -> bool:
        """Solve perpendicular constraint between lines."""
        if len(constraint.entities) != 2:
            return False
        
        l1_id, l2_id = constraint.entities
        l1 = entities.get(l1_id)
        l2 = entities.get(l2_id)
        
        if not (isinstance(l1, Line2D) and isinstance(l2, Line2D)):
            return False
        
        # Get direction vectors
        dir1_x, dir1_y = l1.direction()
        
        # Calculate perpendicular direction
        perp_x = -dir1_y
        perp_y = dir1_x
        
        # Rotate second line to be perpendicular
        length = l2.length()
        if length > 0:
            l2.end.x = l2.start.x + perp_x * length
            l2.end.y = l2.start.y + perp_y * length
        return True

    def _solve_tangent(self, constraint: 'Constraint',
                      entities: Dict[str, Any]) -> bool:
        """Solve tangent constraint between line-circle or circle-circle."""
        if len(constraint.entities) != 2:
            return False
        
        e1_id, e2_id = constraint.entities
        e1 = entities.get(e1_id)
        e2 = entities.get(e2_id)
        
        # Line-Circle tangency
        if isinstance(e1, Line2D) and isinstance(e2, Circle2D):
            return self._solve_line_circle_tangent(e1, e2)
        elif isinstance(e1, Circle2D) and isinstance(e2, Line2D):
            return self._solve_line_circle_tangent(e2, e1)
        # Circle-Circle tangency
        elif isinstance(e1, Circle2D) and isinstance(e2, Circle2D):
            return self._solve_circle_circle_tangent(e1, e2)
        
        return False

    def _solve_line_circle_tangent(self, line: Line2D,
                                 circle: Circle2D) -> bool:
        """Solve tangency between a line and circle."""
        # Get line direction and normalize
        dir_x, dir_y = line.direction()
        
        # Get vector from line start to circle center
        to_center_x = circle.center.x - line.start.x
        to_center_y = circle.center.y - line.start.y
        
        # Project center onto line
        proj = (to_center_x * dir_x + to_center_y * dir_y)
        proj_x = line.start.x + proj * dir_x
        proj_y = line.start.y + proj * dir_y
        
        # Calculate distance from center to line
        dist = np.sqrt((circle.center.x - proj_x)**2 +
                      (circle.center.y - proj_y)**2)
        
        if abs(dist - circle.radius) < 1e-6:
            return True  # Already tangent
        
        # Move line to be tangent
        offset = circle.radius - dist
        perp_x = -dir_y  # Perpendicular direction
        perp_y = dir_x
        
        # Move line parallel to itself
        line.start.move_to(
            line.start.x + offset * perp_x,
            line.start.y + offset * perp_y
        )
        line.end.move_to(
            line.end.x + offset * perp_x,
            line.end.y + offset * perp_y
        )
        return True

    def _solve_circle_circle_tangent(self, c1: Circle2D,
                                   c2: Circle2D) -> bool:
        """Solve tangency between two circles."""
        # Calculate distance between centers
        dx = c2.center.x - c1.center.x
        dy = c2.center.y - c1.center.y
        dist = np.sqrt(dx*dx + dy*dy)
        
        if abs(dist - (c1.radius + c2.radius)) < 1e-6:
            return True  # Already tangent
        
        # Calculate unit vector between centers
        if dist > 0:
            unit_x = dx / dist
            unit_y = dy / dist
            
            # Move second circle to be tangent
            target_dist = c1.radius + c2.radius
            c2.center.move_to(
                c1.center.x + unit_x * target_dist,
                c1.center.y + unit_y * target_dist
            )
        return True

    def _solve_equal(self, constraint: 'Constraint',
                    entities: Dict[str, Any]) -> bool:
        """Solve equal length/radius constraint."""
        if len(constraint.entities) != 2:
            return False
        
        e1_id, e2_id = constraint.entities
        e1 = entities.get(e1_id)
        e2 = entities.get(e2_id)
        
        # Equal length for lines
        if isinstance(e1, Line2D) and isinstance(e2, Line2D):
            return self._solve_equal_length(e1, e2)
        # Equal radius for circles
        elif isinstance(e1, Circle2D) and isinstance(e2, Circle2D):
            return self._solve_equal_radius(e1, e2)
        
        return False

    def _solve_equal_length(self, l1: Line2D, l2: Line2D) -> bool:
        """Make two lines equal in length."""
        len1 = l1.length()
        len2 = l2.length()
        
        if abs(len1 - len2) < 1e-6:
            return True  # Already equal
        
        # Calculate average length
        target_len = (len1 + len2) / 2
        
        # Adjust both lines to target length
        dir1_x, dir1_y = l1.direction()
        l1.end.move_to(
            l1.start.x + dir1_x * target_len,
            l1.start.y + dir1_y * target_len
        )
        
        dir2_x, dir2_y = l2.direction()
        l2.end.move_to(
            l2.start.x + dir2_x * target_len,
            l2.start.y + dir2_y * target_len
        )
        return True

    def _solve_equal_radius(self, c1: Circle2D, c2: Circle2D) -> bool:
        """Make two circles equal in radius."""
        if abs(c1.radius - c2.radius) < 1e-6:
            return True  # Already equal
        
        # Set both radii to average
        target_radius = (c1.radius + c2.radius) / 2
        c1.radius = target_radius
        c2.radius = target_radius
        return True

    def _solve_concentric(self, constraint: 'Constraint',
                         entities: Dict[str, Any]) -> bool:
        """
        Solve concentric constraint between two circles or arcs.
        
        This constraint ensures that two circles or arcs share the same center point.
        The centers are moved to their midpoint to maintain stability.
        
        Args:
            constraint: The constraint to solve
            entities: Dictionary of all entities in the sketch
        
        Returns:
            bool: True if the constraint was satisfied, False otherwise
        """
        if len(constraint.entities) != 2:
            return False
        
        e1_id, e2_id = constraint.entities
        e1 = entities.get(e1_id)
        e2 = entities.get(e2_id)
        
        # Validate entity types (circles or arcs)
        if not (isinstance(e1, (Circle2D, Arc2D)) and 
                isinstance(e2, (Circle2D, Arc2D))):
            return False
        
        # Calculate midpoint between centers
        mid_x = (e1.center.x + e2.center.x) / 2
        mid_y = (e1.center.y + e2.center.y) / 2
        
        # Move both centers to midpoint
        e1.center.move_to(mid_x, mid_y)
        e2.center.move_to(mid_x, mid_y)
        
        return True

    def _solve_horizontal(self, constraint: 'Constraint',
                         entities: Dict[str, Any]) -> bool:
        """
        Solve horizontal constraint for a line.
        
        Makes a line parallel to the X-axis by setting both endpoints
        to the same Y-coordinate (average of current Y values).
        
        Args:
            constraint: The constraint to solve
            entities: Dictionary of all entities in the sketch
        
        Returns:
            bool: True if the constraint was satisfied, False otherwise
        """
        if len(constraint.entities) != 1:
            return False
        
        line_id = constraint.entities[0]
        line = entities.get(line_id)
        
        if not isinstance(line, Line2D):
            return False
        
        # Calculate average Y coordinate
        avg_y = (line.start.y + line.end.y) / 2
        
        # Set both endpoints to average Y
        line.start.y = avg_y
        line.end.y = avg_y
        
        return True

    def _solve_vertical(self, constraint: 'Constraint',
                       entities: Dict[str, Any]) -> bool:
        """
        Solve vertical constraint for a line.
        
        Makes a line parallel to the Y-axis by setting both endpoints
        to the same X-coordinate (average of current X values).
        
        Args:
            constraint: The constraint to solve
            entities: Dictionary of all entities in the sketch
        
        Returns:
            bool: True if the constraint was satisfied, False otherwise
        """
        if len(constraint.entities) != 1:
            return False
        
        line_id = constraint.entities[0]
        line = entities.get(line_id)
        
        if not isinstance(line, Line2D):
            return False
        
        # Calculate average X coordinate
        avg_x = (line.start.x + line.end.x) / 2
        
        # Set both endpoints to average X
        line.start.x = avg_x
        line.end.x = avg_x
        
        return True

class SketchManager:
    """Manages 2D sketch entities and constraints."""
    
    def __init__(self):
        self.points: Dict[str, Point2D] = {}
        self.lines: Dict[str, Line2D] = {}
        self.circles: Dict[str, Circle2D] = {}
        self.arcs: Dict[str, Arc2D] = {}
        self.splines: Dict[str, Spline2D] = {}
        self.constraints: Dict[str, Constraint] = {}
        
        # Initialize constraint solver
        self.solver = ConstraintSolver()
        
        # Set up update callbacks
        self.update_callbacks = []

    def register_update_callback(self, callback):
        """Register a callback for entity updates."""
        self.update_callbacks.append(callback)

    def _notify_update(self, entity_id: str):
        """Notify listeners of entity updates."""
        for callback in self.update_callbacks:
            self.solver.update_queue.put((callback, (entity_id,)))

    def solve_constraints(self) -> bool:
        """Solve all constraints in parallel."""
        entities = {
            **self.points,
            **self.lines,
            **self.circles,
            **self.arcs,
            **self.splines
        }
        
        # Create tasks for parallel solving
        tasks = [
            (constraint, entities)
            for constraint in self.constraints.values()
        ]
        
        # Solve constraints in parallel using thread pool
        results = list(
            self.solver.thread_pool.map(
                lambda args: self.solver.solve_constraint(*args),
                tasks
            )
        )
        
        # Check if all constraints were satisfied
        success = all(results)
        
        # Notify updates
        if success:
            for entity_id in entities:
                self._notify_update(entity_id)
        
        return success

    def add_point(self, x: float, y: float) -> str:
        """Add a point to the sketch."""
        point = Point2D(x, y)
        self.points[point.id] = point
        return point.id

    def add_line(self, x1: float, y1: float, x2: float, y2: float) -> str:
        """Add a line to the sketch."""
        start = Point2D(x1, y1)
        end = Point2D(x2, y2)
        line = Line2D(start, end)
        self.points[start.id] = start
        self.points[end.id] = end
        self.lines[line.id] = line
        return line.id

    def add_circle(self, center_x: float, center_y: float,
                  radius: float) -> str:
        """Add a circle to the sketch."""
        center = Point2D(center_x, center_y)
        circle = Circle2D(center, radius)
        self.points[center.id] = center
        self.circles[circle.id] = circle
        return circle.id

    def add_arc(self, center_x: float, center_y: float,
                radius: float, start_angle: float,
                end_angle: float) -> str:
        """Add an arc to the sketch."""
        center = Point2D(center_x, center_y)
        arc = Arc2D(center, radius, start_angle, end_angle)
        self.points[center.id] = center
        self.arcs[arc.id] = arc
        return arc.id

    def add_spline(self, control_points: List[Tuple[float, float]],
                  degree: int = 3) -> str:
        """Add a spline to the sketch."""
        points = [Point2D(x, y) for x, y in control_points]
        spline = Spline2D(points, degree)
        for point in points:
            self.points[point.id] = point
        self.splines[spline.id] = spline
        return spline.id

    def add_constraint(self, constraint_type: ConstraintType,
                      entities: List[str],
                      parameters: Dict = None) -> str:
        """Add a constraint between entities."""
        constraint = Constraint(constraint_type, entities, parameters)
        self.constraints[constraint.id] = constraint
        return constraint.id

    def remove_entity(self, entity_id: str):
        """Remove an entity and its associated constraints."""
        # Remove entity from appropriate collection
        if entity_id in self.points:
            del self.points[entity_id]
        elif entity_id in self.lines:
            line = self.lines[entity_id]
            del self.points[line.start.id]
            del self.points[line.end.id]
            del self.lines[entity_id]
        elif entity_id in self.circles:
            circle = self.circles[entity_id]
            del self.points[circle.center.id]
            del self.circles[entity_id]
        elif entity_id in self.arcs:
            arc = self.arcs[entity_id]
            del self.points[arc.center.id]
            del self.arcs[entity_id]
        elif entity_id in self.splines:
            spline = self.splines[entity_id]
            for point in spline.control_points:
                del self.points[point.id]
            del self.splines[entity_id]

        # Remove associated constraints
        constraints_to_remove = []
        for c_id, constraint in self.constraints.items():
            if entity_id in constraint.entities:
                constraints_to_remove.append(c_id)
        for c_id in constraints_to_remove:
            del self.constraints[c_id]

    def get_entity(self, entity_id: str) -> Optional[object]:
        """Get entity by ID."""
        if entity_id in self.points:
            return self.points[entity_id]
        elif entity_id in self.lines:
            return self.lines[entity_id]
        elif entity_id in self.circles:
            return self.circles[entity_id]
        elif entity_id in self.arcs:
            return self.arcs[entity_id]
        elif entity_id in self.splines:
            return self.splines[entity_id]
        return None

    def move_point(self, point_id: str, x: float, y: float):
        """Move a point to new coordinates."""
        if point_id in self.points:
            self.points[point_id].move_to(x, y)
            self._notify_update(point_id)
            # Solve constraints after point movement
            self.solve_constraints()

    def get_connected_entities(self, entity_id: str) -> List[str]:
        """Get IDs of entities connected via constraints."""
        connected = set()
        for constraint in self.constraints.values():
            if entity_id in constraint.entities:
                connected.update(constraint.entities)
        connected.discard(entity_id)
        return list(connected)

    def validate_constraint(self, constraint: Constraint) -> bool:
        """Validate if a constraint can be satisfied."""
        entities = {
            **self.points,
            **self.lines,
            **self.circles,
            **self.arcs,
            **self.splines
        }
        return self.solver.solve_constraint(constraint, entities) 