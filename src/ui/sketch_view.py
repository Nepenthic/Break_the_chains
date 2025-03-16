"""
Sketch view for 2D drawing and constraint creation.
"""

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QRubberBand,
    QMenu, QGraphicsItem, QMessageBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSizeF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QTransform, QFont
)
from typing import Optional, List, Tuple, Dict, Set
from ..core.sketch import (
    SketchManager, Point2D, Line2D, Circle2D,
    Arc2D, Spline2D, ConstraintType, Constraint
)
import time
import logging

class SketchItem(QGraphicsItem):
    """Base class for sketch entities in the view."""
    
    def __init__(self, entity_id: str):
        super().__init__()
        self.entity_id = entity_id
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self.hover_points: Set[QPointF] = set()
        self.constraint_points: Set[QPointF] = set()
        self.preview_items: List[QGraphicsItem] = []
        self.is_preview_source = False

    def add_hover_point(self, point: QPointF):
        """Add a hover point for constraint snapping."""
        self.hover_points.add(point)
        self.update()

    def clear_hover_points(self):
        """Clear all hover points."""
        self.hover_points.clear()
        self.update()

    def add_constraint_point(self, point: QPointF):
        """Add a constraint point."""
        self.constraint_points.add(point)
        self.update()

    def clear_constraint_points(self):
        """Clear all constraint points."""
        self.constraint_points.clear()
        self.update()

    def start_preview(self):
        """Mark this item as the source of a constraint preview."""
        self.is_preview_source = True
        self.update()

    def end_preview(self):
        """End preview mode for this item."""
        self.is_preview_source = False
        self.clear_preview_items()
        self.update()

    def clear_preview_items(self):
        """Clear all preview items."""
        for item in self.preview_items:
            if item.scene():
                item.scene().removeItem(item)
        self.preview_items.clear()

class PointItem(SketchItem):
    """Visual representation of a point in the sketch."""
    
    def __init__(self, entity_id: str, x: float, y: float):
        super().__init__(entity_id)
        self.setPos(x, y)
        self.radius = 3.0

    def boundingRect(self) -> QRectF:
        """Get item's bounding rectangle."""
        return QRectF(-self.radius, -self.radius,
                     2 * self.radius, 2 * self.radius)

    def paint(self, painter: QPainter,
             option: 'QStyleOptionGraphicsItem',
             widget: Optional['QWidget'] = None) -> None:
        """Paint the point."""
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        if self.isSelected():
            painter.setBrush(QBrush(Qt.GlobalColor.blue))
        else:
            painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.drawEllipse(self.boundingRect())
        
        # Draw hover points
        painter.setPen(QPen(Qt.GlobalColor.green, 1, Qt.PenStyle.DashLine))
        for point in self.hover_points:
            painter.drawEllipse(point, 5, 5)
        
        # Draw constraint points
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        for point in self.constraint_points:
            painter.drawEllipse(point, 3, 3)

class LineItem(SketchItem):
    """Visual representation of a line in the sketch."""
    
    def __init__(self, entity_id: str, x1: float, y1: float,
                 x2: float, y2: float):
        super().__init__(entity_id)
        self.start = QPointF(x1, y1)
        self.end = QPointF(x2, y2)
        self.update_position()

    def update_position(self):
        """Update item position to match line endpoints."""
        self.setPos(self.start)
        self.line = QPointF(self.end.x() - self.start.x(),
                          self.end.y() - self.start.y())

    def boundingRect(self) -> QRectF:
        """Get item's bounding rectangle."""
        return QRectF(0, 0, self.line.x(), self.line.y())

    def paint(self, painter: QPainter,
             option: 'QStyleOptionGraphicsItem',
             widget: Optional['QWidget'] = None) -> None:
        """Paint the line."""
        pen = QPen(Qt.GlobalColor.black, 1)
        if self.isSelected():
            pen.setColor(Qt.GlobalColor.blue)
        painter.setPen(pen)
        painter.drawLine(QPointF(0, 0), self.line)
        
        # Draw hover points
        painter.setPen(QPen(Qt.GlobalColor.green, 1, Qt.PenStyle.DashLine))
        for point in self.hover_points:
            painter.drawEllipse(point, 5, 5)
        
        # Draw constraint points
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        for point in self.constraint_points:
            painter.drawEllipse(point, 3, 3)

class CircleItem(SketchItem):
    """Visual representation of a circle in the sketch."""
    
    def __init__(self, entity_id: str, center_x: float,
                 center_y: float, radius: float):
        super().__init__(entity_id)
        self.setPos(center_x - radius, center_y - radius)
        self.radius = radius
        self.center = QPointF(center_x, center_y)

    def boundingRect(self) -> QRectF:
        """Get item's bounding rectangle."""
        return QRectF(0, 0, 2 * self.radius, 2 * self.radius)

    def paint(self, painter: QPainter,
             option: 'QStyleOptionGraphicsItem',
             widget: Optional['QWidget'] = None) -> None:
        """Paint the circle."""
        pen = QPen(Qt.GlobalColor.black, 1)
        if self.isSelected() or self.is_preview_source:
            pen.setColor(Qt.GlobalColor.blue)
        painter.setPen(pen)
        painter.drawEllipse(self.boundingRect())
        
        # Draw center point if selected or preview source
        if self.isSelected() or self.is_preview_source:
            painter.setPen(QPen(Qt.GlobalColor.blue, 2))
            center_local = QPointF(self.radius, self.radius)
            painter.drawEllipse(center_local, 3, 3)
        
        # Draw hover points
        painter.setPen(QPen(Qt.GlobalColor.green, 1, Qt.PenStyle.DashLine))
        for point in self.hover_points:
            painter.drawEllipse(point, 5, 5)
        
        # Draw constraint points
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        for point in self.constraint_points:
            painter.drawEllipse(point, 3, 3)

class SketchView(QGraphicsView):
    """Graphics view for sketch creation and editing."""
    
    # Signals
    entity_selected = pyqtSignal(str)  # Emits entity_id
    entity_modified = pyqtSignal(str)  # Emits entity_id
    constraint_added = pyqtSignal(str)  # Emits constraint_id
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Initialize sketch manager
        self.sketch_manager = SketchManager()
        self.sketch_manager.register_update_callback(self._handle_entity_update)
        
        # Drawing state
        self.current_tool = None
        self.drawing = False
        self.start_pos = None
        self.temp_item = None
        self.rubber_band = None
        self.last_hover_item = None
        self.constraint_mode = False
        self.constraint_type = None
        self.constraint_entities = []
        
        # Performance settings
        self.update_interval = 1/60  # 60 FPS
        self.last_update = 0
        
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
            self.entity_modified.emit(entity_id)

    def _find_item_by_entity_id(self, entity_id: str) -> Optional[SketchItem]:
        """Find a graphics item by its entity ID."""
        for item in self.scene.items():
            if isinstance(item, SketchItem) and item.entity_id == entity_id:
                return item
        return None

    def _start_constraint(self, constraint_type: ConstraintType):
        """Start creating a constraint."""
        # Clear any existing previews
        for item in self.scene.items():
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
        for item in self.scene.items():
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
                item = self.scene.itemAt(
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
        if current_time - self.last_update < self.update_interval:
            return  # Skip update if too soon
        
        scene_pos = self.mapToScene(event.pos())
        
        # Clear previous hover points
        if self.last_hover_item:
            self.last_hover_item.clear_hover_points()
        
        # Update hover points and constraint previews
        item = self.scene.itemAt(scene_pos, QTransform())
        if isinstance(item, SketchItem):
            item.add_hover_point(scene_pos)
            self.last_hover_item = item
            
            # Handle constraint previews
            if self.constraint_mode and self.constraint_entities:
                self._update_constraint_preview(item, scene_pos)
        
        if self.drawing and self.start_pos:
            if self.current_tool == 'line':
                if self.temp_item:
                    self.scene.removeItem(self.temp_item)
                self.temp_item = self.scene.addLine(
                    self.start_pos.x(), self.start_pos.y(),
                    scene_pos.x(), scene_pos.y(),
                    QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.DashLine)
                )
            elif self.current_tool == 'circle':
                if self.temp_item:
                    self.scene.removeItem(self.temp_item)
                radius = ((scene_pos.x() - self.start_pos.x())**2 +
                         (scene_pos.y() - self.start_pos.y())**2)**0.5
                self.temp_item = self.scene.addEllipse(
                    self.start_pos.x() - radius,
                    self.start_pos.y() - radius,
                    2 * radius, 2 * radius,
                    QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.DashLine)
                )
        
        self.last_update = current_time
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
                self.scene.removeItem(self.temp_item)
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
        point_item = PointItem(entity_id, pos.x(), pos.y())
        self.scene.addItem(point_item)

    def _line_tool(self, event, pos):
        """Handle line tool."""
        if not self.drawing:
            self.drawing = True
            self.start_pos = pos
        else:
            self._finish_line(pos)

    def _finish_line(self, end_pos):
        """Finish creating a line."""
        if self.start_pos:
            entity_id = self.sketch_manager.add_line(
                self.start_pos.x(), self.start_pos.y(),
                end_pos.x(), end_pos.y()
            )
            line_item = LineItem(
                entity_id,
                self.start_pos.x(), self.start_pos.y(),
                end_pos.x(), end_pos.y()
            )
            self.scene.addItem(line_item)

    def _circle_tool(self, event, pos):
        """Handle circle tool."""
        if not self.drawing:
            self.drawing = True
            self.start_pos = pos
        else:
            self._finish_circle(pos)

    def _finish_circle(self, end_pos):
        """Finish creating a circle."""
        if self.start_pos:
            radius = ((end_pos.x() - self.start_pos.x())**2 +
                     (end_pos.y() - self.start_pos.y())**2)**0.5
            entity_id = self.sketch_manager.add_circle(
                self.start_pos.x(), self.start_pos.y(), radius
            )
            circle_item = CircleItem(
                entity_id,
                self.start_pos.x(), self.start_pos.y(),
                radius
            )
            self.scene.addItem(circle_item)

    def _update_constraint_preview(self, hover_item: SketchItem, scene_pos: QPointF):
        """Update constraint preview based on current constraint type.
        
        This method provides real-time visual feedback for constraint creation:
        - Coincident: Shows connection between points with snap indicators
        - Equal: Shows current and target measurements with directional hints
        - Parallel/Perpendicular: Shows alignment guides and angle indicators
        
        Args:
            hover_item: The SketchItem currently under the mouse cursor
            scene_pos: Current mouse position in scene coordinates
        """
        # Clear any existing preview items when hovering over a new item
        if self.last_hover_item and self.last_hover_item != hover_item:
            self.last_hover_item.end_preview()
        
        first_item = self._find_item_by_entity_id(self.constraint_entities[0])
        if not first_item:
            return

        # Font settings for better visibility
        label_font = QFont("Arial", 10)
        label_color = Qt.GlobalColor.blue

        if self.constraint_type == ConstraintType.COINCIDENT:
            # Only show preview for point-to-point coincidence
            if isinstance(first_item, PointItem):
                # Clear previous preview and mark as source
                first_item.clear_preview_items()
                first_item.start_preview()
                
                # Draw highlight circle around first point for emphasis
                highlight = self.scene.addEllipse(
                    first_item.pos().x() - 5, first_item.pos().y() - 5,
                    10, 10,
                    QPen(label_color, 1, Qt.PenStyle.DashLine)
                )
                first_item.preview_items.append(highlight)
                
                if isinstance(hover_item, PointItem):
                    # Draw dashed guide line between points to show connection
                    preview_line = self.scene.addLine(
                        first_item.pos().x(), first_item.pos().y(),
                        hover_item.pos().x(), hover_item.pos().y(),
                        QPen(label_color, 1, Qt.PenStyle.DashLine)
                    )
                    first_item.preview_items.append(preview_line)
                    
                    # Draw filled dot to indicate snap target
                    snap_preview = self.scene.addEllipse(
                        hover_item.pos().x() - 3, hover_item.pos().y() - 3,
                        6, 6,
                        QPen(label_color, 2),
                        QBrush(label_color)
                    )
                    first_item.preview_items.append(snap_preview)
                else:
                    # Show red X to indicate invalid selection
                    size = 6
                    x, y = scene_pos.x(), scene_pos.y()
                    for start, end in [(-size, -size, size, size),
                                     (-size, size, size, -size)]:
                        invalid_mark = self.scene.addLine(
                            x + start, y + start,
                            x + end, y + end,
                            QPen(Qt.GlobalColor.red, 2)
                        )
                        first_item.preview_items.append(invalid_mark)

        elif self.constraint_type == ConstraintType.EQUAL:
            if isinstance(first_item, LineItem) and isinstance(hover_item, LineItem):
                # Clear previous preview and mark as source
                first_item.clear_preview_items()
                first_item.start_preview()
                
                # Calculate current lengths and target (average) length
                len1 = ((first_item.end.x() - first_item.start.x()) ** 2 +
                       (first_item.end.y() - first_item.start.y()) ** 2) ** 0.5
                len2 = ((hover_item.end.x() - hover_item.start.x()) ** 2 +
                       (hover_item.end.y() - hover_item.start.y()) ** 2) ** 0.5
                avg_len = (len1 + len2) / 2
                
                # Draw length indicators and labels for both lines
                for line, length in [(first_item, len1), (hover_item, len2)]:
                    mid_x = (line.start.x() + line.end.x()) / 2
                    mid_y = (line.start.y() + line.end.y()) / 2
                    
                    # Calculate perpendicular direction for indicator placement
                    dx = line.end.x() - line.start.x()
                    dy = line.end.y() - line.start.y()
                    if dx * dx + dy * dy > 0:
                        # Normalize vector and rotate 90 degrees for perpendicular indicator
                        length = (dx * dx + dy * dy) ** 0.5
                        dx, dy = dx / length, dy / length
                        perp_x, perp_y = -dy * 10, dx * 10
                        
                        # Draw perpendicular indicator at midpoint
                        indicator = self.scene.addLine(
                            mid_x - perp_x, mid_y - perp_y,
                            mid_x + perp_x, mid_y + perp_y,
                            QPen(label_color, 1)
                        )
                        first_item.preview_items.append(indicator)
                    
                    # Add length label with background for better visibility
                    text = self.scene.addSimpleText(
                        f"{length:.1f}",
                        font=label_font
                    )
                    text.setBrush(QBrush(label_color))
                    # Position label above the line using perpendicular offset
                    text.setPos(mid_x + perp_x, mid_y + perp_y)
                    first_item.preview_items.append(text)
                
                # Show target length above current mouse position
                text = self.scene.addSimpleText(
                    f"Target: {avg_len:.1f}",
                    font=label_font
                )
                text.setBrush(QBrush(label_color))
                text.setPos(scene_pos.x(), scene_pos.y() - 20)
                first_item.preview_items.append(text)
                
            elif isinstance(first_item, CircleItem) and isinstance(hover_item, CircleItem):
                # Clear previous preview and mark as source
                first_item.clear_preview_items()
                first_item.start_preview()
                
                # Calculate target (average) radius
                avg_radius = (first_item.radius + hover_item.radius) / 2
                
                # Draw preview elements for both circles
                for circle in [first_item, hover_item]:
                    # Show dashed preview of target radius
                    preview_circle = self.scene.addEllipse(
                        circle.center.x() - avg_radius,
                        circle.center.y() - avg_radius,
                        2 * avg_radius,
                        2 * avg_radius,
                        QPen(label_color, 1, Qt.PenStyle.DashLine)
                    )
                    first_item.preview_items.append(preview_circle)
                    
                    # Draw radius line for measurement reference
                    radius_line = self.scene.addLine(
                        circle.center.x(), circle.center.y(),
                        circle.center.x() + circle.radius, circle.center.y(),
                        QPen(label_color, 1, Qt.PenStyle.DashLine)
                    )
                    first_item.preview_items.append(radius_line)
                    
                    # Add current radius label
                    text = self.scene.addSimpleText(
                        f"R: {circle.radius:.1f}",
                        font=label_font
                    )
                    text.setBrush(QBrush(label_color))
                    # Position label above radius line
                    text.setPos(
                        circle.center.x() + circle.radius / 2,
                        circle.center.y() - 15
                    )
                    first_item.preview_items.append(text)
                    
                    # Draw arrow indicating radius change direction
                    arrow_size = 10
                    if circle.radius < avg_radius:
                        # Draw expansion arrow (pointing outward)
                        arrow = self.scene.addLine(
                            circle.center.x() + circle.radius, circle.center.y(),
                            circle.center.x() + circle.radius + arrow_size, circle.center.y(),
                            QPen(label_color, 2)
                        )
                    else:
                        # Draw contraction arrow (pointing inward)
                        arrow = self.scene.addLine(
                            circle.center.x() + circle.radius, circle.center.y(),
                            circle.center.x() + circle.radius - arrow_size, circle.center.y(),
                            QPen(label_color, 2)
                        )
                    first_item.preview_items.append(arrow)
                
                # Show target radius above current mouse position
                text = self.scene.addSimpleText(
                    f"Target R: {avg_radius:.1f}",
                    font=label_font
                )
                text.setBrush(QBrush(label_color))
                text.setPos(scene_pos.x(), scene_pos.y() - 20)
                first_item.preview_items.append(text)

        elif self.constraint_type == ConstraintType.PARALLEL:
            if (isinstance(first_item, LineItem) and 
                isinstance(hover_item, LineItem)):
                # Clear previous preview
                first_item.clear_preview_items()
                
                # Mark first item as preview source
                first_item.start_preview()
                
                # Get line vectors
                line1_start, line1_end = first_item.start, first_item.end
                line2_start, line2_end = hover_item.start, hover_item.end
                
                # Calculate direction vectors
                dx1 = line1_end.x() - line1_start.x()
                dy1 = line1_end.y() - line1_start.y()
                len1 = (dx1 * dx1 + dy1 * dy1) ** 0.5
                
                if len1 > 0:
                    # Normalize first line direction
                    dx1, dy1 = dx1 / len1, dy1 / len1
                    
                    # Create extension lines in both directions
                    extension_length = 50  # pixels
                    
                    # Draw extension lines for first line
                    for point, direction in [(line1_start, -1), (line1_end, 1)]:
                        ext_line = self.scene.addLine(
                            point.x(), point.y(),
                            point.x() + dx1 * extension_length * direction,
                            point.y() + dy1 * extension_length * direction,
                            QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine)
                        )
                        first_item.preview_items.append(ext_line)
                    
                    # Draw extension lines for second line
                    for point in [line2_start, line2_end]:
                        ext_line = self.scene.addLine(
                            point.x(), point.y(),
                            point.x() + dx1 * extension_length,
                            point.y() + dy1 * extension_length,
                            QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine)
                        )
                        first_item.preview_items.append(ext_line)
                    
                    # Draw parallel indicators (small arrows)
                    arrow_size = 10
                    mid1_x = (line1_start.x() + line1_end.x()) / 2
                    mid1_y = (line1_start.y() + line1_end.y()) / 2
                    mid2_x = (line2_start.x() + line2_end.x()) / 2
                    mid2_y = (line2_start.y() + line2_end.y()) / 2
                    
                    # Draw arrows perpendicular to lines
                    for mid_x, mid_y in [(mid1_x, mid1_y), (mid2_x, mid2_y)]:
                        # Create perpendicular vector for arrows
                        arrow1 = self.scene.addLine(
                            mid_x - dy1 * arrow_size, mid_y + dx1 * arrow_size,
                            mid_x + dy1 * arrow_size, mid_y - dx1 * arrow_size,
                            QPen(Qt.GlobalColor.blue, 2)
                        )
                        first_item.preview_items.append(arrow1)

        elif self.constraint_type == ConstraintType.PERPENDICULAR:
            if (isinstance(first_item, LineItem) and 
                isinstance(hover_item, LineItem)):
                # Clear previous preview
                first_item.clear_preview_items()
                
                # Mark first item as preview source
                first_item.start_preview()
                
                # Get line vectors
                line1_start, line1_end = first_item.start, first_item.end
                line2_start, line2_end = hover_item.start, hover_item.end
                
                # Calculate direction vectors
                dx1 = line1_end.x() - line1_start.x()
                dy1 = line1_end.y() - line1_start.y()
                len1 = (dx1 * dx1 + dy1 * dy1) ** 0.5
                
                if len1 > 0:
                    # Normalize first line direction
                    dx1, dy1 = dx1 / len1, dy1 / len1
                    
                    # Calculate perpendicular vector (rotate 90 degrees)
                    perp_dx, perp_dy = -dy1, dx1
                    
                    # Calculate intersection point (if lines intersect)
                    dx2 = line2_end.x() - line2_start.x()
                    dy2 = line2_end.y() - line2_start.y()
                    
                    # Draw preview of perpendicular line
                    mid2_x = (line2_start.x() + line2_end.x()) / 2
                    mid2_y = (line2_start.y() + line2_end.y()) / 2
                    preview_length = ((dx2 * dx2 + dy2 * dy2) ** 0.5) / 2
                    
                    preview_line = self.scene.addLine(
                        mid2_x - perp_dx * preview_length,
                        mid2_y - perp_dy * preview_length,
                        mid2_x + perp_dx * preview_length,
                        mid2_y + perp_dy * preview_length,
                        QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine)
                    )
                    first_item.preview_items.append(preview_line)
                    
                    # Draw right angle indicator
                    indicator_size = 10
                    # Find closest point on first line to second line's midpoint
                    t = ((mid2_x - line1_start.x()) * dx1 +
                         (mid2_y - line1_start.y()) * dy1)
                    closest_x = line1_start.x() + dx1 * t
                    closest_y = line1_start.y() + dy1 * t
                    
                    # Draw right angle symbol
                    path = QPainterPath()
                    path.moveTo(closest_x, closest_y)
                    path.lineTo(closest_x + dx1 * indicator_size,
                              closest_y + dy1 * indicator_size)
                    path.lineTo(closest_x + dx1 * indicator_size - perp_dx * indicator_size,
                              closest_y + dy1 * indicator_size - perp_dy * indicator_size)
                    
                    indicator = self.scene.addPath(
                        path,
                        QPen(Qt.GlobalColor.blue, 2)
                    )
                    first_item.preview_items.append(indicator)

    def contextMenuEvent(self, event):
        """Show context menu."""
        menu = QMenu()
        menu.addAction("Select", lambda: self.set_tool('select'))
        menu.addAction("Point", lambda: self.set_tool('point'))
        menu.addAction("Line", lambda: self.set_tool('line'))
        menu.addAction("Circle", lambda: self.set_tool('circle'))
        menu.exec(event.globalPos()) 