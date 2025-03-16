from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                           QGroupBox, QFormLayout, QDoubleSpinBox,
                           QRadioButton, QButtonGroup, QLabel,
                           QHBoxLayout, QCheckBox, QGridLayout,
                           QListWidget, QListWidgetItem, QMenu,
                           QLineEdit, QComboBox, QDialog,
                           QInputDialog, QMessageBox, QStatusBar)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
import json
import os
from pathlib import Path

class TransformTab(QWidget):
    # Signals
    transform_applied = pyqtSignal(str, dict)  # (transform_type, parameters)
    transform_mode_changed = pyqtSignal(str)  # Current transform mode
    snap_settings_changed = pyqtSignal(dict)  # Snapping settings
    axis_changed = pyqtSignal(str)  # Active axis
    preset_applied = pyqtSignal(dict)  # Emitted when a preset is applied
    
    def __init__(self):
        super().__init__()
        self._current_mode = None
        self._active_axis = None
        self._relative_mode = False  # Track relative/absolute mode
        self._history = []  # Track transform history
        self._history_index = -1  # Current position in history
        self._grouped_history = []  # Track grouped transforms
        self._presets = {}  # Store transform presets
        self._presets_file = Path("transform_presets.json")
        self.loadPresets()  # Load saved presets
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
        
        # History panel with search and filter
        history_group = QGroupBox("Transform History")
        history_layout = QVBoxLayout()

        # Search and filter controls
        filter_layout = QHBoxLayout()
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search history...")
        self.search_box.textChanged.connect(self.updateHistoryList)
        filter_layout.addWidget(self.search_box)
        
        # Filter by type
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Translate", "Rotate", "Scale"])
        self.type_filter.currentTextChanged.connect(self.updateHistoryList)
        filter_layout.addWidget(self.type_filter)
        
        # Filter by axis
        self.axis_filter = QComboBox()
        self.axis_filter.addItems(["All Axes", "X", "Y", "Z"])
        self.axis_filter.currentTextChanged.connect(self.updateHistoryList)
        filter_layout.addWidget(self.axis_filter)
        
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
        
        # Undo/Redo and group controls
        controls_layout = QHBoxLayout()
        
        self.undo_button = QPushButton("Undo (Ctrl+Z)")
        self.undo_button.setToolTip("Undo last transform")
        self.undo_button.clicked.connect(self.undoTransform)
        self.undo_button.setEnabled(False)
        controls_layout.addWidget(self.undo_button)
        
        self.redo_button = QPushButton("Redo (Ctrl+Y)")
        self.redo_button.setToolTip("Redo last undone transform")
        self.redo_button.clicked.connect(self.redoTransform)
        self.redo_button.setEnabled(False)
        controls_layout.addWidget(self.redo_button)
        
        # Group transforms button
        self.group_button = QPushButton("Group Selected")
        self.group_button.setToolTip("Group selected transforms together")
        self.group_button.clicked.connect(self.groupSelectedTransforms)
        self.group_button.setEnabled(False)
        controls_layout.addWidget(self.group_button)
        
        history_layout.addLayout(controls_layout)
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
        
        # Transform presets
        presets_group = QGroupBox("Transform Presets")
        presets_layout = QVBoxLayout()
        
        # Preset controls
        preset_controls = QHBoxLayout()
        
        # Preset selection combo box
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip("Select a saved transform preset (Ctrl+L to load)")
        self.updatePresetCombo()
        preset_controls.addWidget(self.preset_combo)
        
        # Load preset button
        load_preset_btn = QPushButton("Load (Ctrl+L)")
        load_preset_btn.setToolTip("Load selected preset (Ctrl+L)")
        load_preset_btn.clicked.connect(self.loadSelectedPreset)
        preset_controls.addWidget(load_preset_btn)
        
        # Save preset button
        save_preset_btn = QPushButton("Save (Ctrl+S)")
        save_preset_btn.setToolTip("Save current transform as preset (Ctrl+S)")
        save_preset_btn.clicked.connect(self.savePreset)
        preset_controls.addWidget(save_preset_btn)
        
        # Manage presets button
        manage_presets_btn = QPushButton("Manage (Ctrl+M)")
        manage_presets_btn.setToolTip("Manage saved presets (Ctrl+M)")
        manage_presets_btn.clicked.connect(self.managePresets)
        preset_controls.addWidget(manage_presets_btn)
        
        presets_layout.addLayout(preset_controls)
        
        # Status bar for temporary messages
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        presets_layout.addWidget(self.status_bar)
        
        presets_group.setLayout(presets_layout)
        layout.addWidget(presets_group)
        
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
        
        # Add keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+G"), self, self.groupSelectedTransforms)
        QShortcut(QKeySequence("Ctrl+U"), self, self.ungroupSelectedTransforms)
        
        # Add keyboard shortcuts for transform presets
        # Save preset shortcut (Ctrl+S)
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.savePreset)
        self.save_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        
        # Load preset shortcut (Ctrl+L)
        self.load_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.load_shortcut.activated.connect(self.loadSelectedPreset)
        self.load_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        
        # Manage presets shortcut (Ctrl+M)
        self.manage_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        self.manage_shortcut.activated.connect(self.managePresets)
        self.manage_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        
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
            'timestamp': QDateTime.currentDateTime(),
            'group_id': None  # For transform grouping
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
        
        search_text = self.search_box.text().lower()
        type_filter = self.type_filter.currentText()
        axis_filter = self.axis_filter.currentText()
        
        for i, transform in enumerate(self._history):
            # Apply filters
            if type_filter != "All Types" and transform['params']['mode'].capitalize() != type_filter:
                continue
                
            if axis_filter != "All Axes" and transform['params']['axis'].upper() != axis_filter:
                continue
                
            timestamp = transform['timestamp'].toString('hh:mm:ss')
            mode = transform['params']['mode']
            axis = transform['params']['axis']
            value = transform['params'].get('value', 0)
            relative = "Relative" if transform['params'].get('relative_mode', False) else "Absolute"
            
            item_text = f"{timestamp} - {mode.capitalize()} {axis.upper()}: {value:.2f} ({relative})"
            
            # Apply search filter
            if search_text and search_text not in item_text.lower():
                continue
            
            if transform['group_id'] != current_group:
                # If we have a previous group, add it
                if group_items:
                    self.addGroupToList(group_items)
                    group_items = []
                current_group = transform['group_id']
            
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
            
        # Scroll to current position
        if self._history_index >= 0:
            visible_items = [self.history_list.item(i) for i in range(self.history_list.count())]
            for item in visible_items:
                if isinstance(item.data(Qt.ItemDataRole.UserRole), int) and item.data(Qt.ItemDataRole.UserRole) == self._history_index:
                    self.history_list.scrollToItem(item)
                    break

    def addGroupToList(self, items):
        """Add a group of items to the history list."""
        if not items:
            return
            
        # Create group item
        first = items[0]
        last = items[-1]
        group_text = f"Group: {len(items)} transforms"
        group_item = QListWidgetItem(group_text)
        group_item.setData(Qt.ItemDataRole.UserRole, [item.data(Qt.ItemDataRole.UserRole) for item in items])
        
        # Style group item
        font = group_item.font()
        font.setBold(True)
        group_item.setFont(font)
        group_item.setBackground(Qt.GlobalColor.lightGray)
        
        self.history_list.addItem(group_item)
        
    def showHistoryContextMenu(self, position):
        """Show context menu for history items."""
        menu = QMenu()
        
        # Get item at position
        item = self.history_list.itemAt(position)
        if not item:
            return
            
        # Add menu actions
        restore_action = menu.addAction("Restore This State")
        restore_action.triggered.connect(lambda: self.onHistoryItemDoubleClicked(item))
        
        if len(self.history_list.selectedItems()) > 1:
            group_action = menu.addAction("Group Selected (Ctrl+G)")
            group_action.triggered.connect(self.groupSelectedTransforms)
            
        if isinstance(item.data(Qt.ItemDataRole.UserRole), list):
            ungroup_action = menu.addAction("Ungroup (Ctrl+U)")
            ungroup_action.triggered.connect(lambda: self.ungroupTransforms(item))
            
        menu.exec(self.history_list.mapToGlobal(position))
        
    def onHistoryItemDoubleClicked(self, item):
        """Handle double-clicking on a history item."""
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, list):
            # Group item - restore to last transform in group
            index = index[-1]
            
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
                
    def groupSelectedTransforms(self):
        """Group selected transforms together."""
        selected_items = self.history_list.selectedItems()
        if len(selected_items) < 2:
            return
            
        # Generate new group ID
        group_id = len(self._grouped_history)
        self._grouped_history.append([])
        
        # Update group IDs in history
        for item in selected_items:
            index = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(index, int):
                self._history[index]['group_id'] = group_id
                self._grouped_history[group_id].append(index)
                
        self.updateHistoryList()
        
    def ungroupTransforms(self, group_item):
        """Ungroup a set of transforms."""
        indices = group_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(indices, list):
            return
            
        # Remove group IDs
        for index in indices:
            self._history[index]['group_id'] = None
            
        self.updateHistoryList()
        
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

    def ungroupSelectedTransforms(self):
        """Ungroup selected transforms."""
        selected_items = self.history_list.selectedItems()
        for item in selected_items:
            if isinstance(item.data(Qt.ItemDataRole.UserRole), list):
                self.ungroupTransforms(item)

    def loadPresets(self):
        """Load transform presets from file."""
        try:
            if self._presets_file.exists():
                with open(self._presets_file, 'r') as f:
                    self._presets = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load presets: {str(e)}")
            self._presets = {}

    def savePresetsToFile(self):
        """Save transform presets to file."""
        try:
            with open(self._presets_file, 'w') as f:
                json.dump(self._presets, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save presets: {str(e)}")

    def updatePresetCombo(self):
        """Update the preset combo box with current presets."""
        self.preset_combo.clear()
        self.preset_combo.addItem("Select Preset...")
        for name in sorted(self._presets.keys()):
            self.preset_combo.addItem(name)

    def getCurrentTransform(self):
        """Get current transform settings."""
        transform = {
            'mode': self.getCurrentMode(),
            'axis': self.getCurrentAxis(),
            'relative_mode': self._relative_mode,
            'snap_settings': self.getCurrentSnapSettings()
        }
        
        # Get parameter value based on mode
        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i * 2).widget()
            spin_box = self.params_layout.itemAt(i * 2 + 1).widget()
            if isinstance(label_item, QLabel) and isinstance(spin_box, QDoubleSpinBox):
                transform['value'] = spin_box.value()
                transform['param_name'] = label_item.text()
                break
        
        return transform

    def showStatusMessage(self, message, timeout=2000):
        """Show a temporary status message."""
        self.status_bar.showMessage(message, timeout)

    def savePreset(self):
        """Save current transform settings as a preset."""
        name, ok = QInputDialog.getText(
            self, "Save Preset (Ctrl+S)",
            "Enter preset name:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and name:
            if name in self._presets:
                reply = QMessageBox.question(
                    self, "Overwrite Preset",
                    f"Preset '{name}' already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Save current transform settings
            self._presets[name] = {
                'transform': self.getCurrentTransform(),
                'created': QDateTime.currentDateTime().toString(),
                'last_modified': QDateTime.currentDateTime().toString()
            }
            
            self.savePresetsToFile()
            self.updatePresetCombo()
            self.preset_combo.setCurrentText(name)
            
            self.showStatusMessage(f"Preset '{name}' saved successfully! (Ctrl+S to save presets)")

    def loadSelectedPreset(self):
        """Load the selected preset."""
        preset_name = self.preset_combo.currentText()
        if preset_name == "Select Preset..." or preset_name not in self._presets:
            self.showStatusMessage("No valid preset selected! (Use Ctrl+L to load)")
            return
            
        preset = self._presets[preset_name]['transform']
        
        # Apply transform settings
        self.setCurrentMode(preset['mode'])
        self.setActiveAxis(preset['axis'])
        self.relative_mode.setChecked(preset['relative_mode'])
        
        # Apply snap settings
        snap_settings = preset['snap_settings']
        self.snap_enabled.setChecked(snap_settings['enabled'])
        self.snap_translate.setValue(snap_settings['translate'])
        self.snap_rotate.setValue(snap_settings['rotate'])
        self.snap_scale.setValue(snap_settings['scale'])
        
        # Set parameter value
        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i * 2).widget()
            spin_box = self.params_layout.itemAt(i * 2 + 1).widget()
            if isinstance(label_item, QLabel) and isinstance(spin_box, QDoubleSpinBox):
                if label_item.text() == preset['param_name']:
                    spin_box.setValue(preset['value'])
                    break
        
        # Emit signal that preset was applied
        self.preset_applied.emit(preset)
        self.showStatusMessage(f"Preset '{preset_name}' loaded! (Ctrl+L to load)")

    def managePresets(self):
        """Show dialog to manage presets."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Presets (Ctrl+M)")
        layout = QVBoxLayout(dialog)
        
        # Help text
        help_label = QLabel("Keyboard Shortcuts:\n" +
                          "• Ctrl+S: Save preset\n" +
                          "• Ctrl+L: Load selected preset\n" +
                          "• Ctrl+M: Open this dialog")
        help_label.setStyleSheet("color: gray;")
        layout.addWidget(help_label)
        
        # Preset list
        preset_list = QListWidget()
        preset_list.addItems(sorted(self._presets.keys()))
        layout.addWidget(preset_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        rename_btn = QPushButton("Rename")
        rename_btn.clicked.connect(lambda: self.renamePreset(preset_list))
        button_layout.addWidget(rename_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda: self.deletePreset(preset_list))
        button_layout.addWidget(delete_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.exec()

    def renamePreset(self, preset_list):
        """Rename selected preset."""
        current_item = preset_list.currentItem()
        if not current_item:
            self.showStatusMessage("No preset selected!")
            return
            
        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(
            self, "Rename Preset",
            "Enter new name:",
            QLineEdit.EchoMode.Normal,
            old_name
        )
        
        if ok and new_name and new_name != old_name:
            if new_name in self._presets:
                QMessageBox.warning(
                    self, "Error",
                    f"Preset '{new_name}' already exists!"
                )
                return
                
            self._presets[new_name] = self._presets.pop(old_name)
            self._presets[new_name]['last_modified'] = QDateTime.currentDateTime().toString()
            self.savePresetsToFile()
            self.updatePresetCombo()
            preset_list.currentItem().setText(new_name)
            self.showStatusMessage(f"Preset renamed from '{old_name}' to '{new_name}'")

    def deletePreset(self, preset_list):
        """Delete selected preset."""
        current_item = preset_list.currentItem()
        if not current_item:
            self.showStatusMessage("No preset selected!")
            return
            
        name = current_item.text()
        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Are you sure you want to delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self._presets[name]
            self.savePresetsToFile()
            self.updatePresetCombo()
            preset_list.takeItem(preset_list.row(current_item))
            self.showStatusMessage(f"Preset '{name}' deleted") 