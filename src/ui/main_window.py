"""
Main application window for the CAD system.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QDockWidget, QToolBar, QMenuBar, QStatusBar,
    QTreeView, QLabel, QMenu, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem
from .sketch_view import SketchView
from ..core.sketch import ConstraintType
import psutil
import time

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Break the Chains - CAD")
        self.resize(1200, 800)
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create sketch view
        self.sketch_view = SketchView()
        self.layout.addWidget(self.sketch_view)
        
        # Create UI components
        self._create_actions()
        self._create_menubar()
        self._create_toolbar()
        self._create_statusbar()
        self._create_dockwidgets()
        
        # Set up feature tree model
        self._setup_feature_tree()
        
        # Set up performance monitoring
        self._setup_performance_monitor()
        
        # Connect signals
        self._connect_signals()

    def _create_actions(self):
        """Create actions for menus and toolbars."""
        # File actions
        self.new_action = QAction("&New", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self._new_file)
        
        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._open_file)
        
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self._save_file)
        
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Alt+F4")
        self.exit_action.triggered.connect(self.close)
        
        # Edit actions
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self._undo)
        
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self._redo)
        
        # View actions
        self.zoom_in_action = QAction("Zoom &In", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.triggered.connect(self._zoom_in)
        
        self.zoom_out_action = QAction("Zoom &Out", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(self._zoom_out)
        
        self.fit_view_action = QAction("&Fit View", self)
        self.fit_view_action.setShortcut("Ctrl+F")
        self.fit_view_action.triggered.connect(self._fit_view)
        
        # Tools actions
        self.select_action = QAction("Select", self)
        self.select_action.setCheckable(True)
        self.select_action.setChecked(True)
        self.select_action.triggered.connect(
            lambda: self.sketch_view.set_tool('select')
        )
        
        self.point_action = QAction("Point", self)
        self.point_action.setCheckable(True)
        self.point_action.triggered.connect(
            lambda: self.sketch_view.set_tool('point')
        )
        
        self.line_action = QAction("Line", self)
        self.line_action.setCheckable(True)
        self.line_action.triggered.connect(
            lambda: self.sketch_view.set_tool('line')
        )
        
        self.circle_action = QAction("Circle", self)
        self.circle_action.setCheckable(True)
        self.circle_action.triggered.connect(
            lambda: self.sketch_view.set_tool('circle')
        )
        
        # Constraint actions
        self.coincident_action = QAction("Coincident", self)
        self.coincident_action.setCheckable(True)
        self.coincident_action.triggered.connect(
            lambda: self.sketch_view.set_tool('coincident')
        )
        
        self.parallel_action = QAction("Parallel", self)
        self.parallel_action.setCheckable(True)
        self.parallel_action.triggered.connect(
            lambda: self.sketch_view.set_tool('parallel')
        )
        
        self.perpendicular_action = QAction("Perpendicular", self)
        self.perpendicular_action.setCheckable(True)
        self.perpendicular_action.triggered.connect(
            lambda: self.sketch_view.set_tool('perpendicular')
        )

        self.tangent_action = QAction("Tangent", self)
        self.tangent_action.setCheckable(True)
        self.tangent_action.triggered.connect(
            lambda: self.sketch_view.set_tool('tangent')
        )

        self.equal_action = QAction("Equal Length/Radius", self)
        self.equal_action.setCheckable(True)
        self.equal_action.triggered.connect(
            lambda: self.sketch_view.set_tool('equal')
        )

        self.horizontal_action = QAction("Horizontal", self)
        self.horizontal_action.setCheckable(True)
        self.horizontal_action.triggered.connect(
            lambda: self.sketch_view.set_tool('horizontal')
        )

        self.vertical_action = QAction("Vertical", self)
        self.vertical_action.setCheckable(True)
        self.vertical_action.triggered.connect(
            lambda: self.sketch_view.set_tool('vertical')
        )

        self.concentric_action = QAction("Concentric", self)
        self.concentric_action.setCheckable(True)
        self.concentric_action.triggered.connect(
            lambda: self.sketch_view.set_tool('concentric')
        )
        
        # Create action groups
        self.tool_actions = [
            self.select_action,
            self.point_action,
            self.line_action,
            self.circle_action
        ]
        
        self.constraint_actions = [
            self.coincident_action,
            self.parallel_action,
            self.perpendicular_action,
            self.tangent_action,
            self.equal_action,
            self.horizontal_action,
            self.vertical_action,
            self.concentric_action
        ]
        
        all_actions = self.tool_actions + self.constraint_actions
        for action in all_actions:
            action.triggered.connect(
                lambda checked, a=action: self._update_tool_actions(a)
            )

    def _create_menubar(self):
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.fit_view_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        # Drawing submenu
        drawing_menu = tools_menu.addMenu("Drawing")
        drawing_menu.addAction(self.select_action)
        drawing_menu.addAction(self.point_action)
        drawing_menu.addAction(self.line_action)
        drawing_menu.addAction(self.circle_action)
        
        # Constraints submenu
        constraints_menu = tools_menu.addMenu("Constraints")
        constraints_menu.addAction(self.coincident_action)
        constraints_menu.addAction(self.parallel_action)
        constraints_menu.addAction(self.perpendicular_action)
        constraints_menu.addAction(self.tangent_action)
        constraints_menu.addAction(self.equal_action)
        constraints_menu.addAction(self.horizontal_action)
        constraints_menu.addAction(self.vertical_action)
        constraints_menu.addAction(self.concentric_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self._show_about)

    def _create_toolbar(self):
        """Create toolbars."""
        # File toolbar
        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(file_toolbar)
        file_toolbar.addAction(self.new_action)
        file_toolbar.addAction(self.open_action)
        file_toolbar.addAction(self.save_action)
        
        # Edit toolbar
        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(edit_toolbar)
        edit_toolbar.addAction(self.undo_action)
        edit_toolbar.addAction(self.redo_action)
        
        # View toolbar
        view_toolbar = QToolBar("View")
        view_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(view_toolbar)
        view_toolbar.addAction(self.zoom_in_action)
        view_toolbar.addAction(self.zoom_out_action)
        view_toolbar.addAction(self.fit_view_action)
        
        # Tools toolbar
        tools_toolbar = QToolBar("Tools")
        tools_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(tools_toolbar)
        
        # Add drawing tools
        tools_toolbar.addAction(self.select_action)
        tools_toolbar.addAction(self.point_action)
        tools_toolbar.addAction(self.line_action)
        tools_toolbar.addAction(self.circle_action)
        tools_toolbar.addSeparator()
        
        # Add constraint tools
        tools_toolbar.addAction(self.coincident_action)
        tools_toolbar.addAction(self.parallel_action)
        tools_toolbar.addAction(self.perpendicular_action)
        tools_toolbar.addAction(self.tangent_action)
        tools_toolbar.addAction(self.equal_action)
        tools_toolbar.addAction(self.horizontal_action)
        tools_toolbar.addAction(self.vertical_action)
        tools_toolbar.addAction(self.concentric_action)

    def _create_statusbar(self):
        """Create status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Add CPU usage label
        self.cpu_label = QLabel("CPU: 0%")
        self.statusbar.addPermanentWidget(self.cpu_label)
        
        # Add memory usage label
        self.memory_label = QLabel("Memory: 0MB")
        self.statusbar.addPermanentWidget(self.memory_label)
        
        # Add solver progress bar
        self.solver_progress = QProgressBar()
        self.solver_progress.setMaximumWidth(100)
        self.solver_progress.hide()
        self.statusbar.addPermanentWidget(self.solver_progress)
        
        self.statusbar.showMessage("Ready")

    def _create_dockwidgets(self):
        """Create dock widgets."""
        # Feature tree dock
        self.feature_dock = QDockWidget("Feature Tree", self)
        self.feature_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.feature_tree = QTreeView()
        self.feature_dock.setWidget(self.feature_tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,
                          self.feature_dock)
        
        # Properties dock
        self.properties_dock = QDockWidget("Properties", self)
        self.properties_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.properties_widget = QWidget()
        self.properties_layout = QVBoxLayout(self.properties_widget)
        self.properties_dock.setWidget(self.properties_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,
                          self.properties_dock)

    def _setup_feature_tree(self):
        """Set up feature tree model."""
        self.feature_model = QStandardItemModel()
        self.feature_model.setHorizontalHeaderLabels(["Features"])
        
        # Create root items
        self.sketch_root = QStandardItem("Sketches")
        self.constraints_root = QStandardItem("Constraints")
        
        self.feature_model.appendRow(self.sketch_root)
        self.feature_model.appendRow(self.constraints_root)
        
        self.feature_tree.setModel(self.feature_model)

    def _setup_performance_monitor(self):
        """Set up performance monitoring."""
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._update_performance_stats)
        self.performance_timer.start(1000)  # Update every second
        
        self.process = psutil.Process()
        self.last_cpu_time = time.time()
        self.last_cpu_percent = self.process.cpu_percent()

    def _update_performance_stats(self):
        """Update performance statistics."""
        # Update CPU usage
        cpu_percent = self.process.cpu_percent()
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        
        # Update memory usage
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        self.memory_label.setText(f"Memory: {memory_mb:.1f}MB")

    def _connect_signals(self):
        """Connect signals from sketch view."""
        self.sketch_view.entity_selected.connect(self._handle_entity_selected)
        self.sketch_view.entity_modified.connect(self._handle_entity_modified)
        self.sketch_view.constraint_added.connect(self._handle_constraint_added)

    def _handle_entity_selected(self, entity_id: str):
        """Handle entity selection."""
        entity = self.sketch_view.sketch_manager.get_entity(entity_id)
        if entity:
            self._update_properties(entity)

    def _handle_entity_modified(self, entity_id: str):
        """Handle entity modification."""
        self.statusbar.showMessage(f"Entity {entity_id} modified")

    def _handle_constraint_added(self, constraint_id: str):
        """Handle new constraint."""
        constraint = self.sketch_view.sketch_manager.constraints[constraint_id]
        constraint_item = QStandardItem(f"{constraint.type.name} Constraint")
        self.constraints_root.appendRow(constraint_item)
        self.statusbar.showMessage(f"Added {constraint.type.name} constraint")

    def _update_tool_actions(self, triggered_action):
        """Update tool action states."""
        # Uncheck all actions except the triggered one
        all_actions = self.tool_actions + self.constraint_actions
        for action in all_actions:
            if action != triggered_action:
                action.setChecked(False)

    def _update_properties(self, entity):
        """Update properties panel with entity data."""
        # Clear previous properties
        while self.properties_layout.count():
            item = self.properties_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add entity properties
        self.properties_layout.addWidget(QLabel(f"Type: {type(entity).__name__}"))
        self.properties_layout.addWidget(QLabel(f"ID: {entity.id}"))
        
        if hasattr(entity, 'x') and hasattr(entity, 'y'):
            self.properties_layout.addWidget(
                QLabel(f"Position: ({entity.x:.2f}, {entity.y:.2f})")
            )
        
        if hasattr(entity, 'radius'):
            self.properties_layout.addWidget(
                QLabel(f"Radius: {entity.radius:.2f}")
            )
        
        # Add spacer
        self.properties_layout.addStretch()

    def _new_file(self):
        """Create new file."""
        # TODO: Implement new file functionality
        self.statusbar.showMessage("New file created")

    def _open_file(self):
        """Open existing file."""
        # TODO: Implement open file functionality
        self.statusbar.showMessage("File opened")

    def _save_file(self):
        """Save current file."""
        # TODO: Implement save file functionality
        self.statusbar.showMessage("File saved")

    def _undo(self):
        """Undo last action."""
        # TODO: Implement undo functionality
        self.statusbar.showMessage("Undo")

    def _redo(self):
        """Redo last undone action."""
        # TODO: Implement redo functionality
        self.statusbar.showMessage("Redo")

    def _zoom_in(self):
        """Zoom in view."""
        self.sketch_view.scale(1.2, 1.2)
        self.statusbar.showMessage("Zoomed in")

    def _zoom_out(self):
        """Zoom out view."""
        self.sketch_view.scale(1/1.2, 1/1.2)
        self.statusbar.showMessage("Zoomed out")

    def _fit_view(self):
        """Fit view to content."""
        # TODO: Implement fit view functionality
        self.statusbar.showMessage("View fitted to content")

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Break the Chains",
            "Break the Chains - Modern CAD System\n\n"
            "Version 1.0.0\n"
            "Copyright © 2024"
        ) 