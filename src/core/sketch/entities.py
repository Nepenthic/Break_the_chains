"""
Basic geometric entities for 2D sketching.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from scipy.interpolate import BSpline

@dataclass
class Point2D:
    """Represents a 2D point in sketch space."""
    x: float
    y: float

    def distance_to(self, other: 'Point2D') -> float:
        """Calculate distance to another point."""
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def to_array(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array([self.x, self.y])

@dataclass
class Line2D:
    """Represents a line segment in 2D space."""
    start: Point2D
    end: Point2D

    def length(self) -> float:
        """Calculate length of the line segment."""
        return self.start.distance_to(self.end)

    def direction(self) -> np.ndarray:
        """Get normalized direction vector."""
        vec = np.array([self.end.x - self.start.x, self.end.y - self.start.y])
        return vec / np.linalg.norm(vec)

    def point_at_parameter(self, t: float) -> Point2D:
        """Get point along line at parameter t (0 <= t <= 1)."""
        t = max(0.0, min(1.0, t))
        x = self.start.x + t * (self.end.x - self.start.x)
        y = self.start.y + t * (self.end.y - self.start.y)
        return Point2D(x, y)

@dataclass
class Circle2D:
    """Represents a circle in 2D space."""
    center: Point2D
    radius: float

    def point_at_angle(self, angle: float) -> Point2D:
        """Get point on circle at given angle (in radians)."""
        x = self.center.x + self.radius * np.cos(angle)
        y = self.center.y + self.radius * np.sin(angle)
        return Point2D(x, y)

    def circumference(self) -> float:
        """Calculate circle circumference."""
        return 2 * np.pi * self.radius

@dataclass
class Arc2D:
    """Represents an arc in 2D space."""
    center: Point2D
    radius: float
    start_angle: float  # in radians
    end_angle: float    # in radians

    def length(self) -> float:
        """Calculate arc length."""
        angle_diff = self.end_angle - self.start_angle
        if angle_diff < 0:
            angle_diff += 2 * np.pi
        return self.radius * angle_diff

    def point_at_parameter(self, t: float) -> Point2D:
        """Get point along arc at parameter t (0 <= t <= 1)."""
        t = max(0.0, min(1.0, t))
        angle = self.start_angle + t * (self.end_angle - self.start_angle)
        return self.point_at_angle(angle)

    def point_at_angle(self, angle: float) -> Point2D:
        """Get point on arc at given angle (in radians)."""
        x = self.center.x + self.radius * np.cos(angle)
        y = self.center.y + self.radius * np.sin(angle)
        return Point2D(x, y)

@dataclass
class Spline2D:
    """Represents a B-spline curve in 2D space."""
    control_points: List[Point2D]
    degree: int = 3
    _spline: Optional[BSpline] = None

    def __post_init__(self):
        """Initialize B-spline after creation."""
        if len(self.control_points) < self.degree + 1:
            raise ValueError(f"Need at least {self.degree + 1} control points for degree {self.degree} spline")
        
        # Convert control points to numpy array
        points = np.array([[p.x, p.y] for p in self.control_points])
        
        # Generate knot vector
        n = len(self.control_points)
        knots = np.zeros(n + self.degree + 1)
        knots[self.degree:-self.degree] = np.linspace(0, 1, n - self.degree + 1)
        knots[-self.degree:] = 1
        
        # Create B-spline
        self._spline = BSpline(knots, points, self.degree)

    def point_at_parameter(self, t: float) -> Point2D:
        """Get point along spline at parameter t (0 <= t <= 1)."""
        if self._spline is None:
            raise RuntimeError("Spline not properly initialized")
        
        t = max(0.0, min(1.0, t))
        point = self._spline(t)
        return Point2D(point[0], point[1])

    def get_points(self, num_points: int = 100) -> List[Point2D]:
        """Get a discrete representation of the spline."""
        if self._spline is None:
            raise RuntimeError("Spline not properly initialized")
        
        t = np.linspace(0, 1, num_points)
        points = self._spline(t)
        return [Point2D(x, y) for x, y in points] 