from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                           QGroupBox, QFormLayout, QDoubleSpinBox,
                           QRadioButton, QButtonGroup, QLabel,
                           QHBoxLayout, QCheckBox, QGridLayout,
                           QListWidget, QListWidgetItem, QMenu,
                           QLineEdit, QComboBox, QDialog, QInputDialog,
                           QDateTimeEdit, QSpinBox, QScrollArea,
                           QFrame, QToolButton)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime
from PyQt6.QtGui import QIcon
import json
import os
from typing import Dict, List, Set

class TransformPresetDialog(QDialog):
    def __init__(self, parent=None, categories: Set[str] = None, tags: Set[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Save Transform Preset")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        
        # Preset name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter preset name...")
        layout.addWidget(QLabel("Preset Name:"))
        layout.addWidget(self.name_input)
        
        # Category selection/creation
        category_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAlphabetically)
        if categories:
            self.category_combo.addItems(sorted(categories))
        self.category_combo.setPlaceholderText("Select or create category...")
        category_layout.addWidget(QLabel("Category:"))
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)
        
        # Tags input
        tags_layout = QVBoxLayout()
        tags_layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("e.g., rotation, precise, custom...")
        if tags:
            tag_completer = QCompleter(sorted(tags))
            tag_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.tags_input.setCompleter(tag_completer)
        tags_layout.addWidget(self.tags_input)
        layout.addLayout(tags_layout)
        
        # Description input
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Enter description (optional)...")
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.desc_input)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
    def getPresetInfo(self):
        return {
            'name': self.name_input.text(),
            'category': self.category_combo.currentText(),
            'tags': [tag.strip() for tag in self.tags_input.text().split(',') if tag.strip()],
            'description': self.desc_input.text()
        }

class PresetManagerDialog(QDialog):
    def __init__(self, parent=None, presets: Dict = None):
        super().__init__(parent)
        self.setWindowTitle("Manage Transform Presets")
        self.setMinimumSize(600, 400)
        self.presets = presets or {}
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Search and filter
        filter_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search presets...")
        self.search_box.textChanged.connect(self.filterPresets)
        filter_layout.addWidget(self.search_box)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.addItems(sorted(self.getCategories()))
        self.category_filter.currentTextChanged.connect(self.filterPresets)
        filter_layout.addWidget(self.category_filter)
        
        layout.addLayout(filter_layout)
        
        # Presets list
        self.presets_list = QListWidget()
        self.presets_list.setAlternatingRowColors(True)
        self.presets_list.itemDoubleClicked.connect(self.editPreset)
        self.presets_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.presets_list.customContextMenuRequested.connect(self.showPresetContextMenu)
        layout.addWidget(self.presets_list)
        
        # Buttons
        buttons = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)
        
        self.updatePresetsList()
        
    def getCategories(self) -> Set[str]:
        return {preset.get('category', 'Uncategorized') 
                for preset in self.presets.values()}
                
    def getTags(self) -> Set[str]:
        tags = set()
        for preset in self.presets.values():
            tags.update(preset.get('tags', []))
        return tags
        
    def filterPresets(self):
        search_text = self.search_box.text().lower()
        category = self.category_filter.currentText()
        
        self.presets_list.clear()
        for name, preset in self.presets.items():
            # Check category filter
            if category != "All Categories" and preset.get('category') != category:
                continue
                
            # Check search text
            if search_text:
                search_target = f"{name} {preset.get('category', '')} {' '.join(preset.get('tags', []))} {preset.get('description', '')}"
                if search_text not in search_target.lower():
                    continue
                    
            item = QListWidgetItem(f"{name} ({preset.get('category', 'Uncategorized')})")
            item.setToolTip(f"Tags: {', '.join(preset.get('tags', []))}\nDescription: {preset.get('description', 'No description')}")
            self.presets_list.addItem(item)
            
    def showPresetContextMenu(self, position):
        menu = QMenu()
        item = self.presets_list.itemAt(position)
        if item:
            preset_name = item.text().split(" (")[0]
            
            edit_action = menu.addAction("Edit")
            edit_action.triggered.connect(lambda: self.editPreset(item))
            
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self.deletePreset(preset_name))
            
            menu.exec(self.presets_list.mapToGlobal(position))
            
    def editPreset(self, item):
        preset_name = item.text().split(" (")[0]
        preset = self.presets.get(preset_name)
        if not preset:
            return
            
        dialog = TransformPresetDialog(self, self.getCategories(), self.getTags())
        dialog.name_input.setText(preset_name)
        dialog.category_combo.setCurrentText(preset.get('category', ''))
        dialog.tags_input.setText(', '.join(preset.get('tags', [])))
        dialog.desc_input.setText(preset.get('description', ''))
        
        if dialog.exec():
            info = dialog.getPresetInfo()
            new_name = info['name']
            
            # Update or rename preset
            if new_name != preset_name:
                del self.presets[preset_name]
                
            self.presets[new_name] = {
                **preset,
                'category': info['category'],
                'tags': info['tags'],
                'description': info['description']
            }
            
            self.updatePresetsList()
            
    def deletePreset(self, preset_name):
        if preset_name in self.presets:
            del self.presets[preset_name]
            self.updatePresetsList()
            
    def updatePresetsList(self):
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        self.category_filter.addItems(sorted(self.getCategories()))
        self.filterPresets()

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
        self._filter_date_start = None
        self._filter_date_end = None
        self._filter_value_min = None
        self._filter_value_max = None
        self._presets = self.loadPresets()
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
        
        # History panel with enhanced search and filters
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
        
        # Date range filter
        date_label = QLabel("Date Range:")
        filter_layout.addWidget(date_label, 3, 0)
        date_layout = QHBoxLayout()
        
        self.date_start = QDateTimeEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.date_start.dateTimeChanged.connect(lambda: self.onFilterChanged("date"))
        
        self.date_end = QDateTimeEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.date_end.setDateTime(QDateTime.currentDateTime())
        self.date_end.dateTimeChanged.connect(lambda: self.onFilterChanged("date"))
        
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("to"))
        date_layout.addWidget(self.date_end)
        filter_layout.addLayout(date_layout, 3, 1)
        
        # Value range filter
        value_label = QLabel("Value Range:")
        filter_layout.addWidget(value_label, 4, 0)
        value_layout = QHBoxLayout()
        
        self.value_min = QDoubleSpinBox()
        self.value_min.setRange(-1000, 1000)
        self.value_min.valueChanged.connect(lambda: self.onFilterChanged("value"))
        
        self.value_max = QDoubleSpinBox()
        self.value_max.setRange(-1000, 1000)
        self.value_max.setValue(1000)
        self.value_max.valueChanged.connect(lambda: self.onFilterChanged("value"))
        
        value_layout.addWidget(self.value_min)
        value_layout.addWidget(QLabel("to"))
        value_layout.addWidget(self.value_max)
        filter_layout.addLayout(value_layout, 4, 1)
        
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
        
        # Presets controls with categories
        presets_group = QGroupBox("Transform Presets")
        presets_layout = QVBoxLayout()
        
        # Category and preset selection
        selection_layout = QGridLayout()
        
        # Category filter
        category_label = QLabel("Category:")
        self.category_filter = QComboBox()
        self.updateCategoryFilter()
        self.category_filter.currentTextChanged.connect(self.onCategoryChanged)
        selection_layout.addWidget(category_label, 0, 0)
        selection_layout.addWidget(self.category_filter, 0, 1)
        
        # Preset selection
        preset_label = QLabel("Preset:")
        self.preset_combo = QComboBox()
        self.updatePresetCombo()
        self.preset_combo.setToolTip("Select a saved transform preset")
        selection_layout.addWidget(preset_label, 1, 0)
        selection_layout.addWidget(self.preset_combo, 1, 1)
        
        presets_layout.addLayout(selection_layout)
        
        # Preset actions
        actions_layout = QHBoxLayout()
        
        load_preset_btn = QPushButton("Load (Ctrl+L)")
        load_preset_btn.setToolTip("Load selected transform preset")
        load_preset_btn.clicked.connect(self.loadSelectedPreset)
        actions_layout.addWidget(load_preset_btn)
        
        save_preset_btn = QPushButton("Save (Ctrl+S)")
        save_preset_btn.setToolTip("Save current transform as preset")
        save_preset_btn.clicked.connect(self.saveCurrentAsPreset)
        actions_layout.addWidget(save_preset_btn)
        
        manage_presets_btn = QPushButton("Manage...")
        manage_presets_btn.setToolTip("Manage transform presets")
        manage_presets_btn.clicked.connect(self.showPresetManager)
        actions_layout.addWidget(manage_presets_btn)
        
        presets_layout.addLayout(actions_layout)
        presets_group.setLayout(presets_layout)
        layout.addWidget(presets_group)
        
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
            
        # Date range filter
        if self._filter_date_start and self._filter_date_end:
            transform_date = transform['timestamp']
            if not (self._filter_date_start <= transform_date <= self._filter_date_end):
                return False
                
        # Value range filter
        if self._filter_value_min is not None and self._filter_value_max is not None:
            value = transform['params'].get('value', 0)
            if not (self._filter_value_min <= value <= self._filter_value_max):
                return False
                
        return True
        
    def onSearchTextChanged(self, text):
        """Handle search text changes."""
        self._filter_text = text.lower()
        self.updateHistoryList()
        
    def onFilterChanged(self, source=None):
        """Handle filter changes."""
        if source == "date":
            self._filter_date_start = self.date_start.dateTime()
            self._filter_date_end = self.date_end.dateTime()
        elif source == "value":
            self._filter_value_min = self.value_min.value()
            self._filter_value_max = self.value_max.value()
        else:
            if self.sender() == self.type_filter:
                self._filter_type = self.type_filter.currentText().lower()
            elif self.sender() == self.axis_filter:
                self._filter_axis = self.axis_filter.currentText().lower()
        self.updateHistoryList()
        
    def clearFilters(self):
        """Clear all filters and search text."""
        self.search_box.clear()
        self.type_filter.setCurrentText("All")
        self.axis_filter.setCurrentText("All")
        self._filter_text = ""
        self._filter_type = "all"
        self._filter_axis = "all"
        self._filter_date_start = None
        self._filter_date_end = None
        self._filter_value_min = None
        self._filter_value_max = None
        self.updateHistoryList()
        
    def showHistoryContextMenu(self, position):
        """Show context menu for history items."""
        menu = QMenu()
        
        # Get item at position
        item = self.history_list.itemAt(position)
        
        # Add filter-related actions
        clear_filters = menu.addAction("Clear Filters")
        clear_filters.triggered.connect(self.clearFilters)
        
        # Add preset-related actions
        menu.addSeparator()
        if item:
            save_as_preset = menu.addAction("Save as Preset")
            save_as_preset.triggered.connect(lambda: self.saveTransformAsPreset(item))
            
        load_preset = menu.addAction("Load Preset")
        load_preset.triggered.connect(self.loadSelectedPreset)
        
        menu.addSeparator()
        
        # Add existing item-specific actions
        if item:
            restore_action = menu.addAction("Restore This State")
            restore_action.triggered.connect(lambda: self.onHistoryItemDoubleClicked(item))
            
            if len(self.history_list.selectedItems()) > 1:
                group_action = menu.addAction("Group Selected (Ctrl+Shift+G)")
                group_action.triggered.connect(self.groupSelectedTransforms)
                
            if isinstance(item.data(Qt.ItemDataRole.UserRole), list):
                ungroup_action = menu.addAction("Ungroup (Ctrl+Shift+U)")
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

    def loadPresets(self):
        """Load transform presets from file."""
        presets_file = os.path.join(os.path.dirname(__file__), "transform_presets.json")
        if os.path.exists(presets_file):
            try:
                with open(presets_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def savePresets(self):
        """Save transform presets to file."""
        presets_file = os.path.join(os.path.dirname(__file__), "transform_presets.json")
        with open(presets_file, 'w') as f:
            json.dump(self._presets, f, indent=2)
            
    def updatePresetCombo(self):
        """Update the presets combo box."""
        self.preset_combo.clear()
        self.preset_combo.addItems(self._presets.keys())
        
    def saveCurrentAsPreset(self):
        """Save current transform settings as a preset."""
        dialog = TransformPresetDialog(
            self,
            categories={p.get('category', 'Uncategorized') for p in self._presets.values()},
            tags={tag for p in self._presets.values() for tag in p.get('tags', [])}
        )
        
        if dialog.exec():
            info = dialog.getPresetInfo()
            name = info['name']
            if not name:
                return
                
            # Get current transform settings
            preset = {
                'mode': self._current_mode,
                'axis': self._active_axis,
                'relative': self._relative_mode,
                'snap': self.getSnapSettings(),
                'category': info['category'],
                'tags': info['tags'],
                'description': info['description'],
                'timestamp': QDateTime.currentDateTime().toString()
            }
            
            self._presets[name] = preset
            self.savePresets()
            self.updateCategoryFilter()
            self.updatePresetCombo()
            
    def loadSelectedPreset(self):
        """Load the selected preset."""
        name = self.preset_combo.currentText()
        if not name or name not in self._presets:
            return
            
        preset = self._presets[name]
        
        # Apply preset settings
        if preset['mode']:
            self.setCurrentMode(preset['mode'])
        if preset['axis']:
            self.setActiveAxis(preset['axis'])
            
        self.relative_mode.setChecked(preset['relative'])
        
        snap = preset['snap']
        self.snap_enabled.setChecked(snap['enabled'])
        self.snap_translate.setValue(snap['translate'])
        self.snap_rotate.setValue(snap['rotate'])
        self.snap_scale.setValue(snap['scale'])
        
    def saveTransformAsPreset(self, item):
        """Save a specific transform as a preset."""
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, int) and 0 <= index < len(self._history):
            transform = self._history[index]
            
            dialog = TransformPresetDialog(
                self,
                categories={p.get('category', 'Uncategorized') for p in self._presets.values()},
                tags={tag for p in self._presets.values() for tag in p.get('tags', [])}
            )
            
            if dialog.exec():
                info = dialog.getPresetInfo()
                name = info['name']
                if not name:
                    return
                    
                preset = {
                    'mode': transform['params']['mode'],
                    'axis': transform['params']['axis'],
                    'relative': transform['params'].get('relative_mode', False),
                    'snap': transform['params'].get('snap', self.getSnapSettings()),
                    'category': info['category'],
                    'tags': info['tags'],
                    'description': info['description'],
                    'timestamp': transform['timestamp'].toString()
                }
                
                self._presets[name] = preset
                self.savePresets()
                self.updateCategoryFilter()
                self.updatePresetCombo()

    def updateCategoryFilter(self):
        """Update the category filter combo box."""
        current = self.category_filter.currentText()
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        categories = {preset.get('category', 'Uncategorized') 
                     for preset in self._presets.values()}
        self.category_filter.addItems(sorted(categories))
        
        # Restore previous selection if valid
        index = self.category_filter.findText(current)
        if index >= 0:
            self.category_filter.setCurrentIndex(index)
            
    def onCategoryChanged(self, category: str):
        """Handle category filter changes."""
        self.updatePresetCombo(category)
        
    def updatePresetCombo(self, category: str = None):
        """Update the presets combo box with optional category filter."""
        self.preset_combo.clear()
        
        for name, preset in self._presets.items():
            preset_category = preset.get('category', 'Uncategorized')
            if category in (None, "All Categories") or preset_category == category:
                self.preset_combo.addItem(name)
                
    def showPresetManager(self):
        """Show the preset manager dialog."""
        dialog = PresetManagerDialog(self, self._presets)
        if dialog.exec():
            self.savePresets()
            self.updateCategoryFilter()
            self.updatePresetCombo()
            
    def onCategoryChanged(self, category: str):
        """Handle category filter changes."""
        self.updatePresetCombo(category)
        
    def updatePresetCombo(self, category: str = None):
        """Update the presets combo box with optional category filter."""
        self.preset_combo.clear()
        
        for name, preset in self._presets.items():
            preset_category = preset.get('category', 'Uncategorized')
            if category in (None, "All Categories") or preset_category == category:
                self.preset_combo.addItem(name)
                
    def showPresetManager(self):
        """Show the preset manager dialog."""
        dialog = PresetManagerDialog(self, self._presets)
        if dialog.exec():
            self.savePresets()
            self.updateCategoryFilter()
            self.updatePresetCombo() 