from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                           QGroupBox, QFormLayout, QDoubleSpinBox,
                           QRadioButton, QButtonGroup, QLabel,
                           QHBoxLayout, QCheckBox, QGridLayout,
                           QListWidget, QListWidgetItem)
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
        
        # History panel
        history_group = QGroupBox("Transform History")
        history_layout = QVBoxLayout()
        
        # History list widget
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(150)
        self.history_list.setAlternatingRowColors(True)
        self.history_list.itemClicked.connect(self.onHistoryItemClicked)
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
        
        # Axis selection
        axis_group = QGroupBox("Axis")
        axis_layout = QHBoxLayout()
        
        self.axis_group = QButtonGroup()
        axes = [
            ("X (Alt+X)", "x", "Transform along X axis (Alt+X)"),
            ("Y (Alt+Y)", "y", "Transform along Y axis (Alt+Y)"),
            ("Z (Alt+Z)", "z", "Transform along Z axis (Alt+Z)")
        ]
        
        for text, axis, tooltip in axes:
            radio = QRadioButton(text)
            radio.setToolTip(tooltip)
            self.axis_group.addButton(radio)
            axis_layout.addWidget(radio)
            radio.clicked.connect(lambda checked, a=axis: self.onAxisChanged(a))
            
        axis_group.setLayout(axis_layout)
        layout.addWidget(axis_group)
        
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
        """Handle transform mode change"""
        if self._current_mode != mode:
            self._current_mode = mode
            self.transform_mode_changed.emit(self.getTransformMode())
            
    def onAxisChanged(self, axis):
        """Handle axis selection change"""
        if self._active_axis != axis:
            self._active_axis = axis
            self.axis_changed.emit(axis)
            
    def onSnapSettingsChanged(self):
        """Handle snap settings change"""
        self.snap_settings_changed.emit(self.getSnapSettings())
        
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
        """Update the history list widget."""
        self.history_list.clear()
        for i, transform in enumerate(self._history):
            timestamp = transform['timestamp'].toString('hh:mm:ss')
            mode = transform['params']['mode']
            axis = transform['params']['axis']
            value = transform['params'].get('value', 0)
            
            item_text = f"{timestamp} - {mode.capitalize()} {axis.upper()}: {value:.2f}"
            item = QListWidgetItem(item_text)
            
            # Highlight current position in history
            if i == self._history_index:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                
            self.history_list.addItem(item)
            
        # Scroll to current position
        if self._history_index >= 0:
            self.history_list.scrollToItem(
                self.history_list.item(self._history_index)
            )
            
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
            
    def onHistoryItemClicked(self, item):
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
                
    def applyTransform(self):
        """Apply the current transform with parameters"""
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
                params["axis"] = button.text().lower()
                break
        
        # Get the parameter value
        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i * 2).widget()
            spin_box = self.params_layout.itemAt(i * 2 + 1).widget()
            if isinstance(label_item, QLabel) and isinstance(spin_box, QDoubleSpinBox):
                params["value"] = spin_box.value()
                break
        
        # Add snapping settings
        params["snap"] = self.getSnapSettings()
                
        # Add transform to history
        self.addToHistory(params["mode"], params)
        
        # Emit signal with transform parameters
        self.transform_applied.emit(params["mode"], params)
        
    def updateTransformValues(self, transform):
        """Update the UI with current transform values"""
        # Get the current parameter spin box
        for i in range(self.params_layout.rowCount()):
            spin_box = self.params_layout.itemAt(i * 2 + 1).widget()
            if isinstance(spin_box, QDoubleSpinBox):
                # Update value based on transform mode
                current_mode = None
                for button in self.mode_group.buttons():
                    if button.isChecked():
                        current_mode = button.text().split()[0].lower()
                        break
                
                if current_mode == "translate":
                    # Show position for current axis
                    for button in self.axis_group.buttons():
                        if button.isChecked():
                            axis = button.text().lower()
                            if axis == 'x':
                                spin_box.setValue(transform.position[0])
                            elif axis == 'y':
                                spin_box.setValue(transform.position[1])
                            else:  # z
                                spin_box.setValue(transform.position[2])
                            break
                elif current_mode == "rotate":
                    # Show rotation for current axis
                    for button in self.axis_group.buttons():
                        if button.isChecked():
                            axis = button.text().lower()
                            if axis == 'x':
                                spin_box.setValue(transform.rotation[0])
                            elif axis == 'y':
                                spin_box.setValue(transform.rotation[1])
                            else:  # z
                                spin_box.setValue(transform.rotation[2])
                            break
                elif current_mode == "scale":
                    # Show scale for current axis
                    for button in self.axis_group.buttons():
                        if button.isChecked():
                            axis = button.text().lower()
                            if axis == 'x':
                                spin_box.setValue(transform.scale[0])
                            elif axis == 'y':
                                spin_box.setValue(transform.scale[1])
                            else:  # z
                                spin_box.setValue(transform.scale[2])
                            break
                break 