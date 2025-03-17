"""
Geometric constraint solver for 2D sketches.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum, auto
import numpy as np
from scipy.optimize import minimize
from .entities import Point2D, Line2D, Circle2D, Arc2D

class ConstraintType(Enum):
    """Types of geometric constraints supported by the sketch system."""
    COINCIDENT = auto()
    PARALLEL = auto()
    PERPENDICULAR = auto()
    HORIZONTAL = auto()
    VERTICAL = auto()
    DISTANCE = auto()
    ANGLE = auto()
    EQUAL = auto()
    TANGENT = auto()
    RADIUS = auto()
    CONCENTRIC = auto()

class Constraint:
    """Represents a geometric constraint between sketch entities."""
    
    def __init__(self, constraint_type: ConstraintType, entities: List[Any], value: Optional[float] = None):
        """Initialize a new constraint.
        
        Args:
            constraint_type: Type of geometric constraint
            entities: List of entities involved in the constraint
            value: Optional numeric value for the constraint (e.g. distance, angle)
        """
        self.type = constraint_type
        self.entities = entities
        self.value = value
        self.is_satisfied = False
        
    def __repr__(self) -> str:
        """String representation of the constraint."""
        return f"Constraint({self.type}, entities={len(self.entities)}, value={self.value})"

class ConstraintSolver:
    """Solver for geometric constraints in 2D sketches."""

    def __init__(self):
        self.constraints: List[Dict[str, Any]] = []
        self.tolerance = 1e-6

    def clear(self):
        """Clear all constraints."""
        self.constraints.clear()

    def add_constraint(self, constraint_type: str, 
                      entities: List[Any], 
                      value: Optional[float] = None) -> bool:
        """Add a new geometric constraint."""
        if not self._validate_constraint(constraint_type, entities):
            return False

        constraint = {
            'type': constraint_type,
            'entities': entities,
            'value': value
        }
        self.constraints.append(constraint)
        return True

    def _validate_constraint(self, constraint_type: str, 
                           entities: List[Any]) -> bool:
        """Validate that a constraint is properly formed."""
        valid_constraints = {
            'coincident': (2, [Point2D]),
            'parallel': (2, [Line2D]),
            'perpendicular': (2, [Line2D]),
            'horizontal': (1, [Line2D]),
            'vertical': (1, [Line2D]),
            'distance': (2, [Point2D, Line2D]),
            'angle': (2, [Line2D]),
            'equal': (2, [Line2D, Circle2D, Arc2D]),
            'tangent': (2, [Line2D, Circle2D, Arc2D]),
            'radius': (1, [Circle2D, Arc2D]),
            'concentric': (2, [Circle2D, Arc2D])
        }

        if constraint_type not in valid_constraints:
            return False

        required_count, valid_types = valid_constraints[constraint_type]
        if len(entities) != required_count:
            return False

        # Check if entities are of valid types
        for entity in entities:
            if not any(isinstance(entity, t) for t in valid_types):
                return False

        return True

    def remove_entity_constraints(self, entity_id: str):
        """Remove all constraints involving a specific entity."""
        self.constraints = [c for c in self.constraints 
                          if entity_id not in [e.id for e in c['entities']]]

    def _get_constraint_error(self, constraint: Dict[str, Any], 
                            positions: np.ndarray) -> float:
        """Calculate the error for a single constraint."""
        c_type = constraint['type']
        entities = constraint['entities']
        value = constraint['value']

        if c_type == 'coincident':
            p1, p2 = entities
            return np.linalg.norm(p1.to_array() - p2.to_array())

        elif c_type == 'parallel':
            l1, l2 = entities
            dir1 = l1.direction()
            dir2 = l2.direction()
            return abs(np.dot(dir1, dir2) - 1)

        elif c_type == 'perpendicular':
            l1, l2 = entities
            dir1 = l1.direction()
            dir2 = l2.direction()
            return abs(np.dot(dir1, dir2))

        elif c_type == 'horizontal':
            line = entities[0]
            return abs(line.end.y - line.start.y)

        elif c_type == 'vertical':
            line = entities[0]
            return abs(line.end.x - line.start.x)

        elif c_type == 'distance':
            if isinstance(entities[0], Point2D) and isinstance(entities[1], Point2D):
                dist = entities[0].distance_to(entities[1])
            else:  # Line length
                dist = entities[0].length()
            return abs(dist - value) if value is not None else 0

        elif c_type == 'angle':
            l1, l2 = entities
            dir1 = l1.direction()
            dir2 = l2.direction()
            angle = np.arccos(np.clip(np.dot(dir1, dir2), -1, 1))
            return abs(angle - value) if value is not None else 0

        elif c_type == 'equal':
            if isinstance(entities[0], Line2D):
                len1 = entities[0].length()
                len2 = entities[1].length()
                return abs(len1 - len2)
            else:  # Circle/Arc radius
                r1 = entities[0].radius
                r2 = entities[1].radius
                return abs(r1 - r2)

        elif c_type == 'radius':
            return abs(entities[0].radius - value)

        elif c_type == 'concentric':
            c1, c2 = entities
            return np.linalg.norm(c1.center.to_array() - c2.center.to_array())

        return 0.0

    def _total_constraint_error(self, x: np.ndarray) -> float:
        """Calculate total error for all constraints."""
        total_error = 0.0
        for constraint in self.constraints:
            error = self._get_constraint_error(constraint, x)
            total_error += error * error
        return total_error

    def solve(self) -> bool:
        """Solve all constraints using numerical optimization."""
        if not self.constraints:
            return True

        # Collect all points that need to be optimized
        points = set()
        for constraint in self.constraints:
            for entity in constraint['entities']:
                if isinstance(entity, Point2D):
                    points.add(entity)
                elif isinstance(entity, Line2D):
                    points.add(entity.start)
                    points.add(entity.end)
                elif isinstance(entity, (Circle2D, Arc2D)):
                    points.add(entity.center)

        # Convert points to flat array for optimization
        points = list(points)
        x0 = np.concatenate([p.to_array() for p in points])

        # Optimize
        result = minimize(
            self._total_constraint_error,
            x0,
            method='SLSQP',
            tol=self.tolerance
        )

        if not result.success:
            return False

        # Update point positions with solution
        for i, point in enumerate(points):
            point.x = result.x[i*2]
            point.y = result.x[i*2 + 1]

        return True 