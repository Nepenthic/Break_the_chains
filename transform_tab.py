from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                           QGroupBox, QFormLayout, QDoubleSpinBox,
                           QRadioButton, QButtonGroup, QLabel,
                           QHBoxLayout, QCheckBox, QGridLayout,
                           QListWidget, QListWidgetItem, QMenu,
                           QLineEdit, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime

class TransformTab(QWidget):
    # Signals
    transform_applied = pyqtSignal(str, dict)  # (transform_type, parameters)
    transform_mode_changed = pyqtSignal(str)  # Current transform mode
    snap_settings_changed = pyqtSignal(dict)  # Snapping settings
    axis_changed = pyqtSignal(str)  # Active axis
    
    def __init__(self):
        super().__init__()
        self._current_mode = None
        self._active_axis = None
        self._relative_mode = False  # Track relative/absolute mode
        self._history = []  # Track transform history
        self._history_index = -1  # Current position in history
        self._grouped_history = []  # Track grouped transforms
        self._filter_text = ""  # Track search filter
        self._filter_type = "all"  # Track type filter
        self._filter_axis = "all"  # Track axis filter
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Transform mode selection
        mode_group = QGroupBox("Transform Mode")
        mode_layout = QVBoxLayout()
        
        # Create radio buttons for transform modes with shortcuts and tooltips
        self.mode_group = QButtonGroup()
        modes = [
            ("Translate (T)", "translate", "Move objects along axes (T)"),
            ("Rotate (R)", "rotate", "Rotate objects around axes (R)"),
            ("Scale (S)", "scale", "Scale objects along axes (S)")
        ]
        
        for text, mode, tooltip in modes:
            radio = QRadioButton(text)
            radio.setToolTip(tooltip)
            self.mode_group.addButton(radio)
            mode_layout.addWidget(radio)
            radio.clicked.connect(lambda checked, m=mode: self.onModeChanged(m))
            
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # History panel with search and filters
        history_group = QGroupBox("Transform History")
        history_layout = QVBoxLayout()
        
        # Search and filter controls
        filter_layout = QGridLayout()
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search history...")
        self.search_box.textChanged.connect(self.onSearchTextChanged)
        self.search_box.setToolTip("Search by transform type, axis, or value")
        filter_layout.addWidget(self.search_box, 0, 0, 1, 2)
        
        # Transform type filter
        type_label = QLabel("Type:")
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Translate", "Rotate", "Scale"])
        self.type_filter.currentTextChanged.connect(self.onFilterChanged)
        self.type_filter.setToolTip("Filter by transform type")
        filter_layout.addWidget(type_label, 1, 0)
        filter_layout.addWidget(self.type_filter, 1, 1)
        
        # Axis filter
        axis_label = QLabel("Axis:")
        self.axis_filter = QComboBox()
        self.axis_filter.addItems(["All", "X", "Y", "Z"])
        self.axis_filter.currentTextChanged.connect(self.onFilterChanged)
        self.axis_filter.setToolTip("Filter by axis")
        filter_layout.addWidget(axis_label, 2, 0)
        filter_layout.addWidget(self.axis_filter, 2, 1)
        
        history_layout.addLayout(filter_layout)
        
        # History list widget with enhanced functionality
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(150)
        self.history_list.setAlternatingRowColors(True)
        self.history_list.itemDoubleClicked.connect(self.onHistoryItemDoubleClicked)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.showHistoryContextMenu)
        self.history_list.setToolTip("Double-click to restore a transform state\nRight-click for more options")
        history_layout.addWidget(self.history_list)
        
        # Undo/Redo buttons with tooltips
        undo_redo_layout = QHBoxLayout()
        
        self.undo_button = QPushButton("Undo (Ctrl+Z)")
        self.undo_button.setToolTip("Undo last transform")
        self.undo_button.clicked.connect(self.undoTransform)
        self.undo_button.setEnabled(False)
        undo_redo_layout.addWidget(self.undo_button)
        
        self.redo_button = QPushButton("Redo (Ctrl+Y)")
        self.redo_button.setToolTip("Redo last undone transform")
        self.redo_button.clicked.connect(self.redoTransform)
        self.redo_button.setEnabled(False)
        undo_redo_layout.addWidget(self.redo_button)
        
        history_layout.addLayout(undo_redo_layout)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        # Transform mode options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        # Relative/Absolute mode toggle
        self.relative_mode = QCheckBox("Relative Mode (Alt+R)")
        self.relative_mode.setToolTip("Toggle between relative and absolute transformations")
        self.relative_mode.stateChanged.connect(self.onRelativeModeChanged)
        options_layout.addWidget(self.relative_mode)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Snapping controls with enhanced layout
        snap_group = QGroupBox("Snapping")
        snap_layout = QGridLayout()
        
        # Enable/disable snapping with shortcut
        self.snap_enabled = QCheckBox("Enable Snapping (Ctrl+G)")
        self.snap_enabled.setToolTip("Toggle grid snapping (Ctrl+G)")
        self.snap_enabled.setChecked(True)
        self.snap_enabled.stateChanged.connect(self.onSnapSettingsChanged)
        snap_layout.addWidget(self.snap_enabled, 0, 0, 1, 2)
        
        # Snapping increments with labels and tooltips
        snap_layout.addWidget(QLabel("Grid Size:"), 1, 0)
        self.snap_translate = QDoubleSpinBox()
        self.snap_translate.setRange(0.001, 100.0)
        self.snap_translate.setValue(0.25)
        self.snap_translate.setSingleStep(0.25)
        self.snap_translate.setToolTip("Set grid size for translation snapping")
        self.snap_translate.valueChanged.connect(self.onSnapSettingsChanged)
        snap_layout.addWidget(self.snap_translate, 1, 1)
        
        snap_layout.addWidget(QLabel("Angle (degrees):"), 2, 0)
        self.snap_rotate = QDoubleSpinBox()
        self.snap_rotate.setRange(0.001, 90.0)
        self.snap_rotate.setValue(15.0)
        self.snap_rotate.setSingleStep(5.0)
        self.snap_rotate.setToolTip("Set angle increment for rotation snapping")
        self.snap_rotate.valueChanged.connect(self.onSnapSettingsChanged)
        snap_layout.addWidget(self.snap_rotate, 2, 1)
        
        snap_layout.addWidget(QLabel("Scale Increment:"), 3, 0)
        self.snap_scale = QDoubleSpinBox()
        self.snap_scale.setRange(0.001, 10.0)
        self.snap_scale.setValue(0.25)
        self.snap_scale.setSingleStep(0.25)
        self.snap_scale.setToolTip("Set scale increment for scaling snapping")
        self.snap_scale.valueChanged.connect(self.onSnapSettingsChanged)
        snap_layout.addWidget(self.snap_scale, 3, 1)
        
        snap_group.setLayout(snap_layout)
        layout.addWidget(snap_group)
        
        # Apply button with tooltip
        apply_button = QPushButton("Apply Transform (Enter)")
        apply_button.setToolTip("Apply the current transformation (Enter)")
        apply_button.clicked.connect(self.applyTransform)
        layout.addWidget(apply_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Select translate mode by default
        self.mode_group.buttons()[0].setChecked(True)
        self.axis_group.buttons()[0].setChecked(True)
        
        # Emit initial settings
        self.onSnapSettingsChanged()
        
    def setActiveAxis(self, axis):
        """Set the active axis."""
        for button in self.axis_group.buttons():
            if button.text().split()[0].lower() == axis:
                button.setChecked(True)
                self.onAxisChanged(axis)
                break
                
    def onAxisChanged(self, axis):
        """Handle axis selection change."""
        self._active_axis = axis
        self.axis_changed.emit(axis)
        
    def toggleSnapping(self):
        """Toggle snapping on/off."""
        self.snap_enabled.setChecked(not self.snap_enabled.isChecked())
        
    def onRelativeModeChanged(self, state):
        """Handle relative mode toggle."""
        self._relative_mode = bool(state)
        mode = "relative" if self._relative_mode else "absolute"
        self.transform_mode_changed.emit(f"{self._current_mode}_{mode}")
        
    def getTransformMode(self):
        """Get the current transform mode with relative/absolute state."""
        if not self._current_mode:
            return None
        mode = "relative" if self._relative_mode else "absolute"
        return f"{self._current_mode}_{mode}"
        
    def getSnapSettings(self):
        """Get current snapping settings."""
        return {
            'enabled': self.snap_enabled.isChecked(),
            'translate': self.snap_translate.value(),
            'rotate': self.snap_rotate.value(),
            'scale': self.snap_scale.value(),
            'relative_mode': self._relative_mode
        }
        
    def onModeChanged(self, mode):
        """Handle transform mode change."""
        self._current_mode = mode
        self.transform_mode_changed.emit(mode)
        
    def onSnapSettingsChanged(self):
        """Emit signal when snapping settings change."""
        settings = self.getSnapSettings()
        self.snap_settings_changed.emit(settings)
        
    def setCurrentMode(self, mode):
        """Set the current transform mode."""
        for button in self.mode_group.buttons():
            if button.text().split()[0].lower() == mode:
                button.setChecked(True)
                self.onModeChanged(mode)
                break
        
    def setupTranslateParams(self):
        self.clearParams()
        self.addParameter("Distance", 0.0, -1000.0, 1000.0, 0.1)
        
    def setupRotateParams(self):
        self.clearParams()
        self.addParameter("Angle (degrees)", 0.0, -360.0, 360.0, 1.0)
        
    def setupScaleParams(self):
        self.clearParams()
        self.addParameter("Scale Factor", 1.0, 0.01, 100.0, 0.1)
        
    def clearParams(self):
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def addParameter(self, name, default_value, min_val, max_val, step):
        spin_box = QDoubleSpinBox()
        spin_box.setRange(min_val, max_val)
        spin_box.setValue(default_value)
        spin_box.setSingleStep(step)
        self.params_layout.addRow(name, spin_box)
        
    def applyTransform(self):
        # Collect parameters
        params = {}
        
        # Get the current mode
        for button in self.mode_group.buttons():
            if button.isChecked():
                params["mode"] = button.text().split()[0].lower()
                break
                
        # Get the selected axis
        for button in self.axis_group.buttons():
            if button.isChecked():
                params["axis"] = button.text().split()[0].lower()
                break
        
        # Get the parameter value
        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i * 2).widget()
            spin_box = self.params_layout.itemAt(i * 2 + 1).widget()
            if isinstance(label_item, QLabel) and isinstance(spin_box, QDoubleSpinBox):
                params["value"] = spin_box.value()
                break
        
        # Add snapping settings
        params["snap"] = {
            'enabled': self.snap_enabled.isChecked(),
            'translate': self.snap_translate.value(),
            'rotate': self.snap_rotate.value(),
            'scale': self.snap_scale.value()
        }
                
        # Emit signal with transform parameters
        self.transform_applied.emit(params["mode"], params)
        
    def getCurrentMode(self):
        """Get the current transform mode."""
        for button in self.mode_group.buttons():
            if button.isChecked():
                return button.text().split()[0].lower()
        return None

    def getCurrentAxis(self):
        """Get the current active axis."""
        for button in self.axis_group.buttons():
            if button.isChecked():
                return button.text().split()[0].lower()
        return None

    def getCurrentSnapSettings(self):
        """Get the current snapping settings."""
        return self.getSnapSettings()

    def addToHistory(self, transform_type, parameters):
        """Add a transform operation to the history."""
        # Remove any redo history if we're not at the end
        while len(self._history) > self._history_index + 1:
            self._history.pop()
            
        # Add new transform to history
        transform_info = {
            'type': transform_type,
            'params': parameters.copy(),
            'timestamp': QDateTime.currentDateTime()
        }
        self._history.append(transform_info)
        self._history_index += 1
        
        # Update history list
        self.updateHistoryList()
        
        # Enable/disable undo/redo buttons
        self.updateUndoRedoState()
        
    def updateHistoryList(self):
        """Update the history list widget with filtering."""
        self.history_list.clear()
        current_group = None
        group_items = []
        visible_indices = []  # Track which items are visible
        
        for i, transform in enumerate(self._history):
            # Check if transform should be shown
            if not self.shouldShowTransform(transform):
                continue
                
            visible_indices.append(i)
            timestamp = transform['timestamp'].toString('hh:mm:ss')
            mode = transform['params']['mode']
            axis = transform['params']['axis']
            value = transform['params'].get('value', 0)
            relative = "Relative" if transform['params'].get('relative_mode', False) else "Absolute"
            
            if transform['group_id'] != current_group:
                # If we have a previous group, add it
                if group_items:
                    self.addGroupToList(group_items)
                    group_items = []
                current_group = transform['group_id']
            
            item_text = f"{timestamp} - {mode.capitalize()} {axis.upper()}: {value:.2f} ({relative})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # Store history index
            
            if transform['group_id'] is not None:
                group_items.append(item)
            else:
                # Highlight current position in history
                if i == self._history_index:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.history_list.addItem(item)
        
        # Add any remaining group
        if group_items:
            self.addGroupToList(group_items)
            
        # Update group button state
        self.group_button.setEnabled(len(self.history_list.selectedItems()) > 1)
            
        # Scroll to current position if visible
        if self._history_index in visible_indices:
            for i in range(self.history_list.count()):
                item = self.history_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self._history_index:
                    self.history_list.scrollToItem(item)
                    break
                    
    def shouldShowTransform(self, transform):
        """Check if a transform should be shown based on current filters."""
        # Check text filter
        if self._filter_text:
            text = f"{transform['params']['mode']} {transform['params']['axis']} {transform['params'].get('value', 0)}"
            if self._filter_text not in text.lower():
                return False
                
        # Check type filter
        if self._filter_type != "all" and transform['params']['mode'] != self._filter_type:
            return False
            
        # Check axis filter
        if self._filter_axis != "all" and transform['params']['axis'] != self._filter_axis.lower():
            return False
            
        return True
        
    def onSearchTextChanged(self, text):
        """Handle search text changes."""
        self._filter_text = text.lower()
        self.updateHistoryList()
        
    def onFilterChanged(self, value):
        """Handle filter changes."""
        if self.sender() == self.type_filter:
            self._filter_type = value.lower()
        elif self.sender() == self.axis_filter:
            self._filter_axis = value.lower()
        self.updateHistoryList()
        
    def clearFilters(self):
        """Clear all filters and search text."""
        self.search_box.clear()
        self.type_filter.setCurrentText("All")
        self.axis_filter.setCurrentText("All")
        self._filter_text = ""
        self._filter_type = "all"
        self._filter_axis = "all"
        self.updateHistoryList()
        
    def showHistoryContextMenu(self, position):
        """Show context menu for history items."""
        menu = QMenu()
        
        # Get item at position
        item = self.history_list.itemAt(position)
        
        # Add filter-related actions
        clear_filters = menu.addAction("Clear Filters")
        clear_filters.triggered.connect(self.clearFilters)
        menu.addSeparator()
        
        if item:
            # Add item-specific actions
            restore_action = menu.addAction("Restore This State")
            restore_action.triggered.connect(lambda: self.onHistoryItemDoubleClicked(item))
            
            if len(self.history_list.selectedItems()) > 1:
                group_action = menu.addAction("Group Selected")
                group_action.triggered.connect(self.groupSelectedTransforms)
                
            if isinstance(item.data(Qt.ItemDataRole.UserRole), list):
                ungroup_action = menu.addAction("Ungroup")
                ungroup_action.triggered.connect(lambda: self.ungroupTransforms(item))
                
        menu.exec(self.history_list.mapToGlobal(position))
        
    def updateUndoRedoState(self):
        """Update the enabled state of undo/redo buttons."""
        self.undo_button.setEnabled(self._history_index >= 0)
        self.redo_button.setEnabled(self._history_index < len(self._history) - 1)
        
    def undoTransform(self):
        """Undo the last transform operation."""
        if self._history_index >= 0:
            self._history_index -= 1
            self.updateHistoryList()
            self.updateUndoRedoState()
            # Emit signal to main window
            self.transform_applied.emit("undo", {})
            
    def redoTransform(self):
        """Redo the last undone transform operation."""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            transform = self._history[self._history_index]
            self.updateHistoryList()
            self.updateUndoRedoState()
            # Emit signal to main window
            self.transform_applied.emit("redo", transform['params'])
            
    def onHistoryItemDoubleClicked(self, item):
        """Handle clicking on a history item."""
        index = self.history_list.row(item)
        if index == self._history_index:
            return
            
        # Determine if we're undoing or redoing
        if index < self._history_index:
            # Undo operations until we reach the clicked index
            while self._history_index > index:
                self.undoTransform()
        else:
            # Redo operations until we reach the clicked index
            while self._history_index < index:
                self.redoTransform() 