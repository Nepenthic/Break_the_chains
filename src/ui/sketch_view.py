"""
Sketch view for 2D drawing and constraint creation.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF, QLineF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QTransform, QFont
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QStyleOptionGraphicsItem, QWidget, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsSimpleTextItem, QRubberBand,
    QMenu, QMessageBox
)
from typing import Optional, List, Tuple, Dict, Set
from ..core.sketch import (
    SketchManager, Point2D, Line2D, Circle2D,
    Arc2D, Spline2D, ConstraintType, Constraint
)
import time
import logging
import math

class PreviewEllipseItem(QGraphicsEllipseItem):
    """Preview item for circles and ellipses."""
    Type = QGraphicsItem.UserType + 1
    EllipseItem = Type

    def type(self) -> int:
        return self.Type

class PreviewLineItem(QGraphicsLineItem):
    """Preview line item for showing temporary lines."""
    LineItem = QGraphicsItem.UserType + 2

    def __init__(self, start, end, parent=None):
        """Initialize preview line item.
        
        Args:
            start: Starting point (QPointF or tuple of x,y coordinates)
            end: Ending point (QPointF or tuple of x,y coordinates)
            parent: Optional parent item
        """
        if isinstance(start, QPointF):
            super().__init__(start.x(), start.y(), end.x(), end.y(), parent)
        else:
            super().__init__(start[0], start[1], end[0], end[1], parent)
        self.setPen(QPen(Qt.GlobalColor.blue, 2))

    def type(self):
        """Return the type of the item."""
        return self.LineItem

class PreviewTextItem(QGraphicsSimpleTextItem):
    """Preview item for text labels."""
    Type = QGraphicsItem.UserType + 3
    SimpleTextItem = Type

    def type(self) -> int:
        return self.Type

class SketchItem(QGraphicsItem):
    """Base class for sketch items."""
    def __init__(self, entity_id: int):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.entity_id = entity_id
        self.preview_items = []
        self.is_previewing = False

    def start_preview(self):
        """Mark item as preview source."""
        self.is_previewing = True

    def end_preview(self):
        """End preview and clean up preview items."""
        self.is_previewing = False
        self.clear_preview_items()

    def clear_preview_items(self):
        """Remove all preview items from the scene."""
        for item in self.preview_items[:]:  # Create a copy of the list to avoid modification during iteration
            if item.scene() is not None:
                item.scene().removeItem(item)
            self.preview_items.remove(item)
            del item  # Explicitly delete the item

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the item."""
        return QRectF()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """Paint the item."""
        pass

class PointItem(SketchItem):
    """A point in the sketch."""
    def __init__(self, x: float, y: float, entity_id=None):
        super().__init__(entity_id)
        self.x = x
        self.y = y
        self.setPos(x, y)

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the point."""
        return QRectF(-5, -5, 10, 10)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """Paint the point."""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawEllipse(QRectF(-3, -3, 6, 6))

class LineItem(QGraphicsLineItem, SketchItem):
    """Line item for the sketch."""
    def __init__(self, start_pos, end_pos, entity_id=None, parent=None):
        """Initialize line item.
        
        Args:
            start_pos: Starting point (QPointF)
            end_pos: Ending point (QPointF)
            entity_id: Optional entity ID for the line
            parent: Optional parent item (QGraphicsItem)
        """
        QGraphicsLineItem.__init__(self, start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y(), parent)
        SketchItem.__init__(self, entity_id)
        self.start = start_pos
        self.end = end_pos
        self.preview_items = []  # Explicitly initialize preview_items

    def length(self):
        """Calculate the length of the line."""
        dx = self.end.x() - self.start.x()
        dy = self.end.y() - self.start.y()
        return math.sqrt(dx * dx + dy * dy)

    def direction_vector(self):
        """Get the normalized direction vector of the line."""
        dx = self.end.x() - self.start.x()
        dy = self.end.y() - self.start.y()
        length = self.length()
        if length < 1e-6:  # Avoid division by zero
            return QPointF(0, 0)
        return QPointF(dx / length, dy / length)

    def perpendicular_vector(self, length=1.0):
        """Get a perpendicular vector of the specified length.
        
        Args:
            length: Length of the perpendicular vector (default: 1.0)
        
        Returns:
            QPointF: Perpendicular vector
        """
        dir_vec = self.direction_vector()
        if dir_vec.manhattanLength() == 0:
            return QPointF(0, 0)
        return QPointF(-dir_vec.y() * length, dir_vec.x() * length)

    def closest_point(self, point: QPointF) -> QPointF:
        """Find the closest point on the line to the given point.
        
        Args:
            point: Point to find closest point to
        
        Returns:
            QPointF: Closest point on the line
        """
        # Convert point to local coordinates
        dir_vec = self.direction_vector()
        if dir_vec.manhattanLength() == 0:
            return self.start

        # Project point onto line
        v = QPointF(point.x() - self.start.x(), point.y() - self.start.y())
        t = QPointF.dotProduct(v, dir_vec)
        length = self.length()

        # Clamp t to line segment
        t = max(0, min(length, t))

        # Return point on line
        return QPointF(
            self.start.x() + dir_vec.x() * t,
            self.start.y() + dir_vec.y() * t
        )

    def midpoint(self):
        """Get the midpoint of the line."""
        return QPointF(
            (self.start.x() + self.end.x()) / 2,
            (self.start.y() + self.end.y()) / 2
        )

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the line."""
        return QRectF(
            min(self.start.x(), self.end.x()) - 5,
            min(self.start.y(), self.end.y()) - 5,
            abs(self.end.x() - self.start.x()) + 10,
            abs(self.end.y() - self.start.y()) + 10
        )

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """Paint the line."""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(self.start, self.end)

class CircleItem(QGraphicsEllipseItem, SketchItem):
    """Circle item for the sketch."""
    def __init__(self, center_pos, radius, entity_id=None, parent=None):
        """Initialize circle item.
        
        Args:
            center_pos: Center point (QPointF)
            radius: Radius of the circle
            entity_id: Optional entity ID for the circle
            parent: Optional parent item (QGraphicsItem)
        """
        QGraphicsEllipseItem.__init__(self, center_pos.x() - radius, center_pos.y() - radius, 
                                     2 * radius, 2 * radius, parent)
        SketchItem.__init__(self, entity_id)
        self._center = center_pos
        self._radius = radius
        self.preview_items = []  # Explicitly initialize preview_items
        self.setPen(QPen(QColor.fromRgb(0, 0, 255), 2))

    @property
    def radius(self):
        """Get the radius of the circle."""
        return self._radius

    @radius.setter
    def radius(self, value):
        """Set the radius of the circle."""
        self._radius = value
        self.setRect(self._center.x() - value, self._center.y() - value, 
                    2 * value, 2 * value)

    def center(self):
        """Get the center point of the circle."""
        return self._center

    def closest_point(self, point: QPointF) -> QPointF:
        """Find the closest point on the circle to the given point.
        
        Args:
            point: Point to find closest point to
        
        Returns:
            QPointF: Closest point on the circle
        """
        # Vector from center to point
        dx = point.x() - self._center.x()
        dy = point.y() - self._center.y()
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist < 1e-6:  # Point is at center
            return QPointF(self._center.x() + self._radius, self._center.y())
            
        # Scale vector to radius length
        scale = self._radius / dist
        return QPointF(
            self._center.x() + dx * scale,
            self._center.y() + dy * scale
        )

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the circle."""
        return QRectF(
            self._center.x() - self._radius - 5,
            self._center.y() - self._radius - 5,
            2 * self._radius + 10,
            2 * self._radius + 10
        )

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """Paint the circle."""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawEllipse(self._center, self._radius, self._radius)

class SketchView(QGraphicsView):
    """Graphics view for sketch creation and editing."""
    
    # Item types
    PointItem = PointItem
    LineItem = LineItem
    CircleItem = CircleItem

    # Preview item types
    PreviewEllipseItem = PreviewEllipseItem
    PreviewLineItem = PreviewLineItem
    PreviewTextItem = PreviewTextItem

    # Signals
    entity_selected = pyqtSignal(str)  # Emits entity_id
    entity_updated = pyqtSignal(str)   # Emits entity_id
    entity_deleted = pyqtSignal(str)   # Emits entity_id
    constraint_added = pyqtSignal(str)  # Emits constraint_id
    
    @property
    def scene(self):
        """Get the graphics scene."""
        return self._scene
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.scale(1, -1)  # Flip Y-axis to match mathematical coordinates
        self.start_pos = None
        self.current_item = None
        self.update_callbacks = []  # Initialize the update_callbacks list
        
        # Initialize sketch manager
        self.sketch_manager = SketchManager()
        self.sketch_manager.register_update_callback(self._handle_entity_update)
        
        # Drawing state
        self.current_tool = None
        self.drawing = False
        self.temp_item = None
        self.rubber_band = None
        self.last_hover_item = None
        self.constraint_mode = False
        self.constraint_type = None
        self.constraint_entities = []
        
        # Performance settings
        self.last_update_time = 0
        self.update_interval = 0.016666667  # 60 FPS target (1/60 seconds)
        
        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        
        # Initialize preview-related attributes
        self.preview_items = []
        
        # Initialize tools
        self._setup_tools()

    def _setup_tools(self):
        """Set up drawing tools."""
        self.tools = {
            'select': self._select_tool,
            'point': self._point_tool,
            'line': self._line_tool,
            'circle': self._circle_tool,
            'coincident': lambda e, p: self._start_constraint(
                ConstraintType.COINCIDENT
            ),
            'parallel': lambda e, p: self._start_constraint(
                ConstraintType.PARALLEL
            ),
            'perpendicular': lambda e, p: self._start_constraint(
                ConstraintType.PERPENDICULAR
            ),
            'tangent': lambda e, p: self._start_constraint(
                ConstraintType.TANGENT
            ),
            'equal': lambda e, p: self._start_constraint(
                ConstraintType.EQUAL
            ),
            'horizontal': lambda e, p: self._start_constraint(
                ConstraintType.HORIZONTAL
            ),
            'vertical': lambda e, p: self._start_constraint(
                ConstraintType.VERTICAL
            ),
            'concentric': lambda e, p: self._start_constraint(
                ConstraintType.CONCENTRIC
            )
        }
        self.current_tool = 'select'

    def _handle_entity_update(self, entity_id: str):
        """Handle entity updates from the sketch manager."""
        item = self._find_item_by_entity_id(entity_id)
        if item:
            item.update()
            self.entity_updated.emit(entity_id)

    def _find_item_by_entity_id(self, entity_id: str) -> Optional[SketchItem]:
        """Find a graphics item by its entity ID."""
        for item in self._scene.items():
            if hasattr(item, 'entity_id') and item.entity_id == entity_id:
                return item
        return None

    def _start_constraint(self, constraint_type: ConstraintType):
        """Start creating a constraint."""
        # Clear any existing previews
        for item in self._scene.items():
            if isinstance(item, SketchItem):
                item.end_preview()
        
        self.constraint_mode = True
        self.constraint_type = constraint_type
        self.constraint_entities = []
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Show message to guide user
        message = {
            ConstraintType.COINCIDENT: "Select two points to make coincident",
            ConstraintType.PARALLEL: "Select two lines to make parallel",
            ConstraintType.PERPENDICULAR: "Select two lines to make perpendicular",
            ConstraintType.TANGENT: "Select line/circle or circle/circle to make tangent",
            ConstraintType.EQUAL: "Select two lines or circles to make equal",
            ConstraintType.HORIZONTAL: "Select a line to make horizontal",
            ConstraintType.VERTICAL: "Select a line to make vertical",
            ConstraintType.CONCENTRIC: "Select two circles or arcs to make concentric"
        }.get(constraint_type, "Select entities to create constraint")
        
        QMessageBox.information(
            self,
            "Create Constraint",
            message
        )

    def _add_constraint(self):
        """Add constraint between selected entities."""
        # Clear any existing previews
        for item in self._scene.items():
            if isinstance(item, SketchItem):
                item.end_preview()
        
        if ((self.constraint_type in [ConstraintType.HORIZONTAL, 
                                    ConstraintType.VERTICAL] and 
             len(self.constraint_entities) != 1) or
            (self.constraint_type not in [ConstraintType.HORIZONTAL,
                                        ConstraintType.VERTICAL] and 
             len(self.constraint_entities) < 2)):
            return
        
        try:
            # Validate entity types for constraints
            e1 = self.sketch_manager.get_entity(self.constraint_entities[0])
            e2 = None
            if len(self.constraint_entities) > 1:
                e2 = self.sketch_manager.get_entity(self.constraint_entities[1])
            
            valid = False
            if self.constraint_type == ConstraintType.TANGENT:
                valid = (
                    (isinstance(e1, Line2D) and isinstance(e2, Circle2D)) or
                    (isinstance(e1, Circle2D) and isinstance(e2, Line2D)) or
                    (isinstance(e1, Circle2D) and isinstance(e2, Circle2D))
                )
            elif self.constraint_type == ConstraintType.EQUAL:
                valid = (
                    (isinstance(e1, Line2D) and isinstance(e2, Line2D)) or
                    (isinstance(e1, Circle2D) and isinstance(e2, Circle2D))
                )
            elif self.constraint_type == ConstraintType.HORIZONTAL:
                valid = isinstance(e1, Line2D)
            elif self.constraint_type == ConstraintType.VERTICAL:
                valid = isinstance(e1, Line2D)
            elif self.constraint_type == ConstraintType.CONCENTRIC:
                valid = (
                    isinstance(e1, (Circle2D, Arc2D)) and
                    isinstance(e2, (Circle2D, Arc2D))
                )
            else:
                valid = True  # Other constraints are already validated
            
            if not valid:
                QMessageBox.warning(
                    self,
                    "Invalid Constraint",
                    "Selected entities cannot be constrained this way"
                )
                return
            
            constraint_id = self.sketch_manager.add_constraint(
                self.constraint_type,
                self.constraint_entities
            )
            
            # Solve constraints
            if self.sketch_manager.solve_constraints():
                self.constraint_added.emit(constraint_id)
            else:
                QMessageBox.warning(
                    self,
                    "Constraint Error",
                    "Could not satisfy all constraints"
                )
                self.sketch_manager.remove_entity(constraint_id)
        
        except Exception as e:
            logging.error(f"Error adding constraint: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to add constraint: {str(e)}"
            )
        
        finally:
            # Reset constraint mode
            self.constraint_mode = False
            self.constraint_type = None
            self.constraint_entities = []
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        scene_pos = self.mapToScene(event.pos())
        
        if event.button() == Qt.MouseButton.LeftButton:
            if self.constraint_mode:
                # Handle constraint creation
                item = self._scene.itemAt(
                    self.mapToScene(event.pos()),
                    QTransform()
                )
                if isinstance(item, SketchItem):
                    self.constraint_entities.append(item.entity_id)
                    if len(self.constraint_entities) == 2:
                        self._add_constraint()
            else:
                # Handle normal tool operations
                tool_handler = self.tools.get(self.current_tool)
                if tool_handler:
                    tool_handler(event, scene_pos)
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return  # Skip update if too soon
        
        scene_pos = self.mapToScene(event.pos())
        
        # Clear previous hover points
        if self.last_hover_item:
            self.last_hover_item.clear_hover_points()
        
        # Update hover points and constraint previews
        item = self._scene.itemAt(scene_pos, QTransform())
        if isinstance(item, SketchItem):
            item.add_hover_point(scene_pos)
            self.last_hover_item = item
            
            # Handle constraint previews
            if self.constraint_mode and self.constraint_entities:
                self._update_constraint_preview(item, scene_pos)
        
        if self.drawing and self.start_pos:
            if self.current_tool == 'line':
                if self.temp_item:
                    self._scene.removeItem(self.temp_item)
                self.temp_item = self._scene.addLine(
                    self.start_pos.x(), self.start_pos.y(),
                    scene_pos.x(), scene_pos.y(),
                    QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.DashLine)
                )
            elif self.current_tool == 'circle':
                if self.temp_item:
                    self._scene.removeItem(self.temp_item)
                radius = ((scene_pos.x() - self.start_pos.x())**2 +
                         (scene_pos.y() - self.start_pos.y())**2)**0.5
                self.temp_item = self._scene.addEllipse(
                    self.start_pos.x() - radius,
                    self.start_pos.y() - radius,
                    2 * radius, 2 * radius,
                    QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.DashLine)
                )
        
        self.last_update_time = current_time
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            scene_pos = self.mapToScene(event.pos())
            if self.current_tool == 'line':
                self._finish_line(scene_pos)
            elif self.current_tool == 'circle':
                self._finish_circle(scene_pos)
            
            if self.temp_item:
                self._scene.removeItem(self.temp_item)
                self.temp_item = None
            
            self.drawing = False
            self.start_pos = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.2
            if event.angleDelta().y() < 0:
                factor = 1.0 / factor
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def _select_tool(self, event, pos):
        """Handle selection tool."""
        self.drawing = False
        # Default selection behavior is handled by QGraphicsView

    def _point_tool(self, event, pos):
        """Handle point tool."""
        entity_id = self.sketch_manager.add_point(pos.x(), pos.y())
        point_item = PointItem(pos.x(), pos.y(), entity_id)
        self._scene.addItem(point_item)
        self._notify_update(point_item)

    def _line_tool(self, event, pos):
        """Handle line tool events."""
        if event is None:  # First click
            entity_id = self.sketch_manager.add_line(pos.x(), pos.y(), pos.x(), pos.y())
            self.current_item = LineItem(pos, pos, entity_id)
            self.scene.addItem(self.current_item)
            self.start_pos = pos
        else:  # Mouse move or second click
            if self.current_item:
                self.current_item.end = pos
                self.current_item.setLine(
                    self.start_pos.x(), self.start_pos.y(),
                    pos.x(), pos.y()
                )
                if event is not None and event.type() == QEvent.Type.MouseButtonPress:
                    self._finish_line(pos)

    def _finish_line(self, end_pos):
        """Finish creating a line."""
        if self.current_item and isinstance(self.current_item, LineItem):
            self.current_item.end = end_pos
            self.current_item.setLine(
                self.start_pos.x(), self.start_pos.y(),
                end_pos.x(), end_pos.y()
            )
            self._notify_update(self.current_item)
            self.current_item = None
        self.start_pos = None

    def _circle_tool(self, event, pos=None):
        """Handle circle tool events.

        Args:
            event: Mouse event
            pos: Optional position override
        """
        if event is None:
            # First click - start circle
            entity_id = self.sketch_manager.add_circle(pos.x(), pos.y(), 0)
            self.current_item = CircleItem(pos, 0, entity_id)
            self._scene.addItem(self.current_item)
            self.start_pos = pos
        else:
            # Mouse move or second click - update circle
            if self.current_item and self.start_pos:
                radius = (pos - self.start_pos).manhattanLength()
                self.current_item.radius = radius
                rect = QRectF(self.start_pos.x() - radius, self.start_pos.y() - radius,
                             radius * 2, radius * 2)
                self.current_item.setRect(rect)

    def _finish_circle(self, end_pos):
        """Finish creating a circle."""
        if self.current_item and isinstance(self.current_item, CircleItem):
            radius = QLineF(self.start_pos, end_pos).length()
            self.current_item.radius = radius
            self._notify_update(self.current_item)
            self.current_item = None
        self.start_pos = None

    def _create_adjustment_arrow(self, from_item, to_item):
        """Create an arrow indicating adjustment direction.

        Args:
            from_item: Source item (shorter/smaller)
            to_item: Target item (longer/larger)

        Returns:
            QGraphicsItem: Arrow indicating adjustment direction
        """
        # Calculate arrow direction based on item centers
        from_center = from_item.pos()
        to_center = to_item.pos()

        # Create arrow path
        arrow_size = 10
        arrow_angle = 30  # degrees

        # Calculate direction vector
        dx = to_center.x() - from_center.x()
        dy = to_center.y() - from_center.y()
        length = (dx * dx + dy * dy) ** 0.5

        if length < 1e-6:
            # If items are at same position, use default direction
            dx, dy = 1, 0
        else:
            dx /= length
            dy /= length

        # Create arrow head points
        import math
        angle = math.atan2(dy, dx)
        angle_rad = math.pi / 180 * arrow_angle

        # Main arrow line
        arrow = PreviewLineItem(
            (from_center.x(), from_center.y()),
            (to_center.x(), to_center.y())
        )
        arrow.setPen(QPen(Qt.GlobalColor.blue, 2, Qt.PenStyle.DashLine))
        return arrow

    def _update_constraint_preview(self, target_item, pos):
        """Update the constraint preview based on the current target item and position."""
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return

        self.last_update_time = current_time
        self.clear_preview_items()

        if not self.constraint_entities or not target_item:
            return

        source_item = self._find_item_by_entity_id(self.constraint_entities[0])
        if not source_item:
            return

        # Cache commonly used values
        source_pos = source_item.pos()
        target_pos = target_item.pos()
        
        # Create preview items based on constraint type
        if self.constraint_type == ConstraintType.COINCIDENT:
            if isinstance(target_item, PointItem):
                # Check if points are already coincident
                if (abs(source_pos.x() - target_pos.x()) < 1e-6 and
                    abs(source_pos.y() - target_pos.y()) < 1e-6):
                    # Show green indicator for already-coincident points
                    coincident = PreviewEllipseItem(
                        source_pos.x() - 4, source_pos.y() - 4,
                        8, 8
                    )
                    coincident.setPen(QPen(Qt.GlobalColor.green, 2))
                    coincident.setBrush(QBrush(Qt.GlobalColor.green))
                    self._scene.addItem(coincident)
                    source_item.preview_items.append(coincident)
                else:
                    # Create highlight circle
                    highlight = PreviewEllipseItem(source_pos.x() - 5, source_pos.y() - 5, 10, 10)
                    highlight.setPen(QPen(Qt.GlobalColor.blue))
                    self._scene.addItem(highlight)
                    source_item.preview_items.append(highlight)

                    # Create guide line
                    guide = PreviewLineItem(source_pos, target_pos)
                    guide.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
                    self._scene.addItem(guide)
                    source_item.preview_items.append(guide)
            else:
                # Show invalid selection indicator
                self._show_invalid_selection(source_item, source_pos)

        elif self.constraint_type == ConstraintType.EQUAL:
            if isinstance(target_item, LineItem) and isinstance(source_item, LineItem):
                self._show_equal_lines_preview(source_item, target_item)
            elif isinstance(target_item, CircleItem) and isinstance(source_item, CircleItem):
                self._show_equal_circles_preview(source_item, target_item)
            else:
                self._show_invalid_selection(source_item, source_pos)

        elif self.constraint_type in (ConstraintType.PARALLEL, ConstraintType.PERPENDICULAR):
            if isinstance(target_item, LineItem) and isinstance(source_item, LineItem):
                if self.constraint_type == ConstraintType.PARALLEL:
                    self._show_parallel_preview(source_item, target_item)
                else:
                    self._show_perpendicular_preview(source_item, target_item)
            else:
                self._show_invalid_selection(source_item, source_pos)

    def _show_invalid_selection(self, source_item: SketchItem, pos: QPointF):
        """Show red X to indicate invalid selection."""
        size = 6
        x, y = pos.x(), pos.y()
        invalid_lines = [
            (QPointF(x - size, y - size), QPointF(x + size, y + size)),
            (QPointF(x - size, y + size), QPointF(x + size, y - size))
        ]
        for start, end in invalid_lines:
            invalid_mark = PreviewLineItem(start, end)
            invalid_mark.setPen(QPen(Qt.GlobalColor.red, 2))
            self._scene.addItem(invalid_mark)
            source_item.preview_items.append(invalid_mark)

    def _show_equal_lines_preview(self, source: LineItem, target: LineItem):
        """Show preview for equal length constraint between lines."""
        # Calculate lengths
        len1 = source.length()
        len2 = target.length()
        
        # Draw length indicators and labels
        for line, length in [(source, len1), (target, len2)]:
            mid_point = line.midpoint()
            perp = line.perpendicular_vector(10)  # Get perpendicular vector of length 10
            
            # Draw perpendicular indicator at midpoint
            indicator = PreviewLineItem(
                mid_point - perp,
                mid_point + perp
            )
            indicator.setPen(QPen(Qt.GlobalColor.blue))
            self._scene.addItem(indicator)
            source.preview_items.append(indicator)
            
            # Add length label
            text = PreviewTextItem(f"{length:.1f}")
            text.setFont(QFont("Arial", 10))
            text.setBrush(QBrush(Qt.GlobalColor.blue))
            text.setPos(mid_point + perp)
            self._scene.addItem(text)
            source.preview_items.append(text)
        
        # Draw arrow if lengths differ
        if abs(len1 - len2) > 1e-6:
            shorter = source if len1 < len2 else target
            longer = target if len1 < len2 else source
            arrow = self._create_adjustment_arrow(shorter, longer)
            self._scene.addItem(arrow)
            source.preview_items.append(arrow)

    def _show_equal_circles_preview(self, source: CircleItem, target: CircleItem):
        """Show preview for equal radius constraint between circles."""
        # Draw radius indicators and labels
        for circle in [source, target]:
            # Draw radius line
            radius_line = PreviewLineItem(
                circle.center(),
                QPointF(circle.center().x() + circle.radius, circle.center().y())
            )
            radius_line.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
            self._scene.addItem(radius_line)
            source.preview_items.append(radius_line)
            
            # Add radius label
            text = PreviewTextItem(f"R={circle.radius:.1f}")
            text.setFont(QFont("Arial", 10))
            text.setBrush(QBrush(Qt.GlobalColor.blue))
            text.setPos(
                circle.center().x() + circle.radius / 2,
                circle.center().y() + 10
            )
            self._scene.addItem(text)
            source.preview_items.append(text)
        
        # Draw arrow if radii differ
        if abs(source.radius - target.radius) > 1e-6:
            shorter = source if source.radius < target.radius else target
            longer = target if source.radius < target.radius else source
            arrow = self._create_adjustment_arrow(shorter, longer)
            self._scene.addItem(arrow)
            source.preview_items.append(arrow)

    def _show_parallel_preview(self, source: LineItem, target: LineItem):
        """Show preview for parallel constraint between lines."""
        # Get line vectors
        source_vec = source.direction_vector()
        if source_vec.manhattanLength() == 0:
            return
        
        # Create extension lines
        extension_length = 50
        for line in [source, target]:
            for point in [line.start, line.end]:
                ext_line = PreviewLineItem(
                    point,
                    point + source_vec * extension_length
                )
                ext_line.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
                self._scene.addItem(ext_line)
                source.preview_items.append(ext_line)
        
        # Draw parallel indicators (arrows)
        arrow_size = 10
        for line in [source, target]:
            mid_point = line.midpoint()
            perp = line.perpendicular_vector(arrow_size)
            arrow = PreviewLineItem(
                mid_point - perp,
                mid_point + perp
            )
            arrow.setPen(QPen(Qt.GlobalColor.blue, 2))
            self._scene.addItem(arrow)
            source.preview_items.append(arrow)

    def _show_perpendicular_preview(self, source: LineItem, target: LineItem):
        """Show preview for perpendicular constraint between lines."""
        source_vec = source.direction_vector()
        if source_vec.manhattanLength() == 0:
            return
        
        # Calculate perpendicular vector
        perp_vec = QPointF(-source_vec.y(), source_vec.x())
        
        # Draw preview of perpendicular line
        target_mid = target.midpoint()
        preview_length = target.length() / 2
        
        preview_line = PreviewLineItem(
            target_mid - perp_vec * preview_length,
            target_mid + perp_vec * preview_length
        )
        preview_line.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
        self._scene.addItem(preview_line)
        source.preview_items.append(preview_line)
        
        # Draw right angle indicator
        indicator_size = 10
        closest_point = source.closest_point(target_mid)
        
        path = QPainterPath()
        path.moveTo(closest_point)
        path.lineTo(closest_point + source_vec * indicator_size)
        path.lineTo(closest_point + source_vec * indicator_size + perp_vec * indicator_size)
        
        indicator = self._scene.addPath(
            path,
            QPen(Qt.GlobalColor.blue, 2)
        )
        source.preview_items.append(indicator)

    def contextMenuEvent(self, event):
        """Show context menu."""
        menu = QMenu()
        menu.addAction("Select", lambda: self.set_tool('select'))
        menu.addAction("Point", lambda: self.set_tool('point'))
        menu.addAction("Line", lambda: self.set_tool('line'))
        menu.addAction("Circle", lambda: self.set_tool('circle'))
        menu.exec(event.globalPos())

    def _notify_update(self, entity):
        for callback in self.update_callbacks:
            callback(entity)

    def clear_preview_items(self):
        """Remove all preview items from the scene."""
        for item in self.preview_items[:]:  # Create a copy of the list to avoid modification during iteration
            if item.scene() is not None:
                self._scene.removeItem(item)
            self.preview_items.remove(item)
            del item  # Explicitly delete the item 