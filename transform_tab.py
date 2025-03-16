from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                           QGroupBox, QFormLayout, QDoubleSpinBox,
                           QRadioButton, QButtonGroup, QLabel,
                           QHBoxLayout, QCheckBox, QGridLayout,
                           QListWidget, QListWidgetItem, QMenu,
                           QLineEdit, QComboBox, QDialog, QInputDialog,
                           QDateTimeEdit, QSpinBox, QScrollArea,
                           QFrame, QToolButton, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QTimer, QPropertyAnimation, QSequentialAnimationGroup, QAbstractAnimation
from PyQt6.QtGui import QIcon
import json
import os
from typing import Dict, List, Set
import numpy as np
import time

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

class TransformFeedback:
    """Manages real-time visual feedback for transform operations."""
    
    def __init__(self):
        self.active = False
        self.current_transform = None
        self.preview_overlay = None
        self.performance_metrics = UIPerformanceMonitor()
    
    def start_transform_preview(self, transform_type, initial_value):
        """Initialize transform preview overlay."""
        self.active = True
        self.current_transform = {
            'type': transform_type,
            'start_value': initial_value,
            'start_time': time.perf_counter_ns()
        }
        
class TransformTab(QWidget):
    """Widget for controlling object transformations with compound transform support."""
    
    # Constants for configuration and performance
    TRANSITION_DURATION = 200  # Reduced from 300ms for better responsiveness
    PERFORMANCE_THRESHOLD = 500  # milliseconds for slow operation warning
    MAX_STATUS_AXES = 3  # Maximum number of axes to show in status before truncating
    ANIMATION_BATCH_SIZE = 5  # Number of UI updates to batch during transitions
    
    # Update signal to support multiple axes
    transformPreviewRequested = Signal(str, dict)  # (transform_type, {axis: value})
    transformApplied = Signal()
    
    # Add new signals for enhanced feedback
    mode_transition_started = Signal(str, str)  # old_mode, new_mode
    mode_transition_completed = Signal(str)  # new_mode
    transform_state_changed = Signal(dict)  # transform_state
    performance_warning = Signal(str)  # warning message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_transform_mode = 'translate'
        self._preview_active = False
        self._history = []
        self._active_axes = {}  # {axis: spinbox} for active transforms
        self._mode_transition_timer = QTimer()
        self._mode_transition_timer.setSingleShot(True)
        self._mode_transition_timer.timeout.connect(self._complete_mode_transition)
        self._last_mode_switch_time = 0
        
        self._setup_ui()
        self.connect_signals()
        self._setup_mode_indicators()

    def _setup_mode_indicators(self):
        """Setup visual indicators for transform modes with accessibility support."""
        # Create mode indicator widget with high contrast colors
        self.mode_indicator = QFrame(self)
        self.mode_indicator.setFrameShape(QFrame.Box)
        self.mode_indicator.setFocusPolicy(Qt.StrongFocus)  # Enable keyboard focus
        self.mode_indicator.setStyleSheet("""
            QFrame {
                border: 2px solid #2196F3;
                border-radius: 4px;
                background-color: rgba(33, 150, 243, 0.15);
                margin: 4px;
                padding: 2px;
            }
            QFrame:focus {
                border-color: #1565C0;
                background-color: rgba(33, 150, 243, 0.25);
            }
        """)
        self.mode_indicator.setAccessibleName("Transform Mode Indicator")
        self.mode_indicator.setAccessibleDescription("Shows current transform mode and state")
        
        # Mode label with icon and high contrast
        self.mode_label = QLabel(self.mode_indicator)
        self.mode_label.setAlignment(Qt.AlignCenter)
        self.mode_label.setFocusPolicy(Qt.NoFocus)  # Parent frame handles focus
        self.mode_label.setStyleSheet("""
            QLabel {
                color: #000000;
                font-weight: bold;
                padding: 4px;
                font-size: 12pt;
            }
        """)
        
        # Status message with improved contrast
        self.mode_status = QLabel(self.mode_indicator)
        self.mode_status.setAlignment(Qt.AlignCenter)
        self.mode_status.setFocusPolicy(Qt.NoFocus)  # Parent frame handles focus
        self.mode_status.setStyleSheet("""
            QLabel {
                color: #424242;
                font-size: 10pt;
                padding: 2px;
            }
        """)
        
        # Layout for mode indicator
        indicator_layout = QVBoxLayout(self.mode_indicator)
        indicator_layout.addWidget(self.mode_label)
        indicator_layout.addWidget(self.mode_status)
        indicator_layout.setContentsMargins(8, 8, 8, 8)
        
        # Add to main layout
        self.layout().insertWidget(0, self.mode_indicator)
        
        # Initialize mode display
        self._update_mode_indicator('translate')
        
        # Setup keyboard navigation
        self.mode_indicator.keyPressEvent = self._handle_mode_indicator_key_press

    def _handle_mode_indicator_key_press(self, event):
        """Handle keyboard navigation for mode indicator."""
        if event.key() == Qt.Key_Space or event.key() == Qt.Key_Return:
            # Toggle through modes: translate -> rotate -> scale -> translate
            current_modes = ['translate', 'rotate', 'scale']
            current_index = current_modes.index(self.current_transform_mode)
            next_mode = current_modes[(current_index + 1) % len(current_modes)]
            self._set_transform_mode(next_mode)
        elif event.key() == Qt.Key_R:
            # Toggle relative mode with 'R' key
            self.relative_mode.setChecked(not self.relative_mode.isChecked())
        else:
            super().keyPressEvent(event)

    def _animate_mode_transition(self, old_mode, new_mode):
        """Animate the mode transition with optimized performance."""
        start_time = time.perf_counter_ns()
        
        # Create fade out animation with batched updates
        fade_out = QPropertyAnimation(self.mode_indicator, b"windowOpacity")
        fade_out.setDuration(self.TRANSITION_DURATION // 2)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setUpdateInterval(self.TRANSITION_DURATION // self.ANIMATION_BATCH_SIZE)
        
        # Create fade in animation with batched updates
        fade_in = QPropertyAnimation(self.mode_indicator, b"windowOpacity")
        fade_in.setDuration(self.TRANSITION_DURATION // 2)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setUpdateInterval(self.TRANSITION_DURATION // self.ANIMATION_BATCH_SIZE)
        
        # Sequential animation group
        transition = QSequentialAnimationGroup()
        transition.addAnimation(fade_out)
        transition.addAnimation(fade_in)
        
        # Connect to update indicator between animations
        fade_out.finished.connect(lambda: self._update_mode_indicator(new_mode))
        
        # Monitor performance
        transition.finished.connect(lambda: self._check_transition_performance(start_time))
        
        # Start animation
        transition.start(QAbstractAnimation.DeleteWhenStopped)

    def _check_transition_performance(self, start_time):
        """Monitor transition performance and emit warnings if needed."""
        duration = (time.perf_counter_ns() - start_time) / 1_000_000  # Convert to ms
        if duration > self.PERFORMANCE_THRESHOLD:
            warning = f"Slow mode transition detected: {duration:.1f}ms"
            self.performance_warning.emit(warning)
            print(f"Performance warning: {warning}")

    def _update_mode_indicator(self, mode):
        """Update the mode indicator display with accessibility support."""
        mode_info = {
            'translate': {
                'icon': '⬌',
                'color': '#2196F3',  # Blue
                'text': 'Translation Mode',
                'contrast_color': '#0D47A1',  # Darker blue for contrast
                'tooltip': 'Translation Mode: Move objects along axes (Space/Enter to change mode)'
            },
            'rotate': {
                'icon': '⟲',
                'color': '#4CAF50',  # Green
                'text': 'Rotation Mode',
                'contrast_color': '#1B5E20',  # Darker green for contrast
                'tooltip': 'Rotation Mode: Rotate objects around axes (Space/Enter to change mode)'
            },
            'scale': {
                'icon': '⤧',
                'color': '#FF9800',  # Orange
                'text': 'Scale Mode',
                'contrast_color': '#E65100',  # Darker orange for contrast
                'tooltip': 'Scale Mode: Scale objects along axes (Space/Enter to change mode)'
            }
        }
        
        info = mode_info.get(mode, mode_info['translate'])
        
        # Update indicator style with high contrast and focus states
        self.mode_indicator.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {info['contrast_color']};
                border-radius: 4px;
                background-color: {info['color']}22;
            }}
            QFrame:hover {{
                background-color: {info['color']}33;
            }}
            QFrame:focus {{
                border-color: {info['contrast_color']};
                background-color: {info['color']}44;
                outline: none;
            }}
        """)
        
        # Update labels with accessibility
        mode_text = f"{info['icon']} {info['text']}"
        self.mode_label.setText(mode_text)
        self.mode_label.setStyleSheet(f"""
            QLabel {{
                color: {info['contrast_color']};
                font-weight: bold;
                padding: 4px;
            }}
        """)
        
        # Update tooltips with consistent capitalization and keyboard shortcuts
        self.mode_indicator.setToolTip(info['tooltip'])
        
        # Update status with consistent capitalization
        relative_text = "Relative Mode" if self._relative_mode else "Absolute Mode"
        axes_text = self._get_active_axes_text()
        status_text = f"{relative_text} • {axes_text}"
        self.mode_status.setText(status_text)
        self.mode_status.setToolTip(f"Current Mode: {relative_text}\n{self._get_full_axes_text()}")

    def _get_active_axes_text(self):
        """Get truncated text representation of active axes."""
        if not self._active_axes:
            return "No Active Axes"
        
        axes = list(self._active_axes.keys())
        if len(axes) <= self.MAX_STATUS_AXES:
            return f"Active Axes: {', '.join(axes).upper()}"
        return f"Active Axes: {', '.join(axes[:self.MAX_STATUS_AXES]).upper()}..."

    def _get_full_axes_text(self):
        """Get complete text representation of active axes for tooltip."""
        if not self._active_axes:
            return "No Active Axes"
        return f"Active Axes: {', '.join(self._active_axes.keys()).upper()}"

    def _set_transform_mode(self, mode):
        """Set the current transform mode with visual transition and performance monitoring."""
        if self.current_transform_mode != mode:
            start_time = time.perf_counter_ns()
            
            # Start transition
            old_mode = self.current_transform_mode
            self.mode_transition_started.emit(old_mode, mode)
            
            # Cancel any active preview
            self.cancel_preview()
            
            # Update mode
            self.current_transform_mode = mode
            
            # Start transition animation
            self._animate_mode_transition(old_mode, mode)
            
            # Update UI
            self._update_ui_for_mode()
            
            # Start transition timer
            self._mode_transition_timer.start(self.TRANSITION_DURATION)
            
            # Monitor performance
            duration = (time.perf_counter_ns() - start_time) / 1_000_000  # Convert to ms
            if duration > self.PERFORMANCE_THRESHOLD:
                warning = f"Slow mode switch detected: {duration:.1f}ms"
                self.performance_warning.emit(warning)
                print(f"Performance warning: {warning}")

    def _complete_mode_transition(self):
        """Complete the mode transition."""
        self.mode_transition_completed.emit(self.current_transform_mode)
        self._update_transform_state()

    def _update_transform_state(self):
        """Update and emit the current transform state."""
        state = {
            'mode': self.current_transform_mode,
            'relative': self._relative_mode,
            'active_axes': list(self._active_axes.keys()),
            'preview_active': self._preview_active,
            'snap_enabled': self.snap_enabled.isChecked(),
            'history_size': len(self._history)
        }
        self.transform_state_changed.emit(state)

    def _update_ui_for_mode(self):
        """Update UI elements for the current transform mode."""
        # Update button states
        self.translate_button.setChecked(self.current_transform_mode == 'translate')
        self.rotate_button.setChecked(self.current_transform_mode == 'rotate')
        self.scale_button.setChecked(self.current_transform_mode == 'scale')
        
        # Show/hide appropriate spinboxes
        self.translate_group.setVisible(self.current_transform_mode == 'translate')
        self.rotate_group.setVisible(self.current_transform_mode == 'rotate')
        self.scale_group.setVisible(self.current_transform_mode == 'scale')
        
    def apply_transform(self):
        """Apply the current compound transform."""
        if not self._preview_active:
            return
            
        # Get final transform values
        transform_values = {a: sb.value() for a, sb in self._active_axes.items()}
        
        # Add to history
        self._history.append({
            'mode': self.current_transform_mode,
            'values': transform_values.copy()
        })
        
        # Reset preview state
        self._preview_active = False
        self._active_axes.clear()
        
        # Emit signals
        self.transformApplied.emit()
        self._log_transform_applied(transform_values)
        
    def cancel_preview(self):
        """Cancel the current transform preview."""
        if not self._preview_active:
            return
            
        # Reset values to last applied state
        if self._history:
            last_transform = self._history[-1]
            if last_transform['mode'] == self.current_transform_mode:
                for axis, value in last_transform['values'].items():
                    spinbox = self._get_spinbox_for_axis(axis)
                    spinbox.setValue(value)
        else:
            # Reset to default values
            for axis in 'xyz':
                spinbox = self._get_spinbox_for_axis(axis)
                spinbox.setValue(0.0 if self.current_transform_mode != 'scale' else 1.0)
                
        # Reset preview state
        self._preview_active = False
        self._active_axes.clear()
        
    def reset_transform_values(self):
        """Reset all transform values to defaults."""
        self.cancel_preview()
        self._history.clear()
        
        # Reset all spinboxes to default values
        for axis in 'xyz':
            self.translate_x.setValue(0.0)
            self.translate_y.setValue(0.0)
            self.translate_z.setValue(0.0)
            self.rotate_x.setValue(0.0)
            self.rotate_y.setValue(0.0)
            self.rotate_z.setValue(0.0)
            self.scale_x.setValue(1.0)
            self.scale_y.setValue(1.0)
            self.scale_z.setValue(1.0)
            
    def _log_preview_update(self, values):
        """Log preview updates for debugging."""
        print(f"Preview update - Mode: {self.current_transform_mode}, Values: {values}")
        
    def _log_transform_applied(self, values):
        """Log applied transforms for debugging."""
        print(f"Transform applied - Mode: {self.current_transform_mode}, Values: {values}")

    def setup_ui(self):
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
        
        # Add visual feedback indicators
        self.status_label = QLabel()
        self.status_label.setStyleSheet("QLabel { color: #2196F3; }")
        self.layout().addWidget(self.status_label)
        
        # Add performance monitor widget
        self.performance_widget = QWidget()
        self.performance_layout = QVBoxLayout(self.performance_widget)
        self.performance_indicator = QProgressBar()
        self.performance_layout.addWidget(self.performance_indicator)
        self.layout().addWidget(self.performance_widget)
        
        # Connect signals
        self.transform_preview.connect(self.update_preview_overlay)
        self.performance_alert.connect(self.show_performance_warning)
        
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
        """Handle relative mode toggle with visual feedback."""
        self._relative_mode = bool(state)
        mode = "relative" if self._relative_mode else "absolute"
        
        # Update mode indicator
        self._update_mode_indicator(self.current_transform_mode)
        
        # Emit mode change signal
        self.transform_mode_changed.emit(f"{self.current_transform_mode}_{mode}")
        
        # Update transform state
        self._update_transform_state()
        
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
        # Add new transform to history
        transform_info = {
            'type': transform_type,
            'params': parameters.copy(),
            'timestamp': QDateTime.currentDateTime()
        }
        self._history.append(transform_info)
        self._history_index = len(self._history) - 1
        
        # Update history list
        self.updateHistoryList()
        
    def updateHistoryList(self):
        """Update the history list widget with filtering."""
        self.history_list.clear()
        
        for i, transform in enumerate(self._history):
            # Check if transform should be shown
            if not self.shouldShowTransform(transform):
                continue
                
            timestamp = transform['timestamp'].toString('hh:mm:ss')
            mode = transform['params']['mode']
            axis = transform['params']['axis']
            value = transform['params'].get('value', 0)
            relative = "Relative" if transform['params'].get('relative_mode', False) else "Absolute"
            
            item_text = f"{timestamp} - {mode.capitalize()} {axis.upper()}: {value:.2f} ({relative})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # Store history index
            
            # Highlight current position in history
            if i == self._history_index:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.history_list.addItem(item)
            
        # Scroll to current position
        if self._history_index >= 0:
            self.history_list.scrollToItem(self.history_list.item(self._history_index))
        
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
        # This is now handled by MainWindow's UndoRedoManager
        self.transformApplied.emit("undo", {})
            
    def redoTransform(self):
        """Redo the last undone transform operation."""
        # This is now handled by MainWindow's UndoRedoManager
        self.transformApplied.emit("redo", {})

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
        
        # Create transform parameters
        transform_params = {
            'mode': preset['mode'],
            'axis': preset['axis'],
            'relative_mode': preset['relative'],
            'snap': snap,
            'value': 1.0  # Default value, will be adjusted based on mode
        }
        
        # Adjust value based on transform mode
        if preset['mode'] == 'rotate':
            transform_params['value'] = 45.0  # Default rotation angle
        elif preset['mode'] == 'scale':
            transform_params['value'] = 1.0  # Default scale factor
        else:  # translate
            transform_params['value'] = snap['translate']  # Use grid size as default
            
        # Add to history and emit transform signal
        self.addToHistory(preset['mode'], transform_params)
        self.transform_applied.emit(preset['mode'], transform_params)

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

    def updateTransformValues(self, transform):
        """Update UI to reflect current transform values."""
        # Update mode and axis if needed
        if self._current_mode == 'translate':
            self.translate_x.setValue(transform.position[0])
            self.translate_y.setValue(transform.position[1])
            self.translate_z.setValue(transform.position[2])
        elif self._current_mode == 'rotate':
            self.rotate_x.setValue(np.degrees(transform.rotation[0]))
            self.rotate_y.setValue(np.degrees(transform.rotation[1]))
            self.rotate_z.setValue(np.degrees(transform.rotation[2]))
        elif self._current_mode == 'scale':
            self.scale_x.setValue(transform.scale[0])
            self.scale_y.setValue(transform.scale[1])
            self.scale_z.setValue(transform.scale[2])
            
        # Update history list
        self.updateHistoryList() 

    def on_transform_value_changed(self, value):
        """Handle transform value changes with real-time feedback."""
        try:
            with self.performance_monitor.measure('transform_update'):
                # Get current transform parameters
                transform_params = self.get_current_transform_params()
                
                # Update preview
                self.transform_preview.emit(self.current_mode, {
                    'value': value,
                    'axis': self._active_axis,
                    'preview': True
                })
                
                # Log the change
                self.log_transform_update(transform_params)
                
                # Check performance
                if self.performance_monitor.should_alert():
                    self.performance_alert.emit('transform_latency', {
                        'duration': self.performance_monitor.last_duration,
                        'threshold': self.performance_monitor.thresholds['transform_update']
                    })
        
        except Exception as e:
            self.log_error(f"Transform update error: {str(e)}")
            self.status_label.setText("Error updating transform")
    
    def update_preview_overlay(self, transform_type, params):
        """Update transform preview overlay."""
        try:
            if not self.feedback.active:
                self.feedback.start_transform_preview(transform_type, params['value'])
            
            # Update overlay
            self.viewport().update_transform_preview(
                transform_type,
                params['value'],
                params['axis']
            )
            
            # Update status
            self.status_label.setText(
                f"Previewing {transform_type} on {params['axis']} axis: {params['value']:.2f}"
            )
            
        except Exception as e:
            self.log_error(f"Preview update error: {str(e)}")
    
    def show_performance_warning(self, metric_type, data):
        """Show performance warning to user."""
        if metric_type == 'transform_latency':
            message = (
                f"Transform operation taking longer than expected "
                f"({data['duration']:.1f}ms > {data['threshold']:.1f}ms)"
            )
            self.status_label.setText(message)
            self.status_label.setStyleSheet("QLabel { color: #FFA000; }")
    
    def log_transform_update(self, params):
        """Log transform updates with performance metrics."""
        self.ui_logger.log_ui_change(
            component="TransformTab",
            change_type="transform_update",
            details={
                'mode': self.current_mode,
                'params': params,
                'performance': self.performance_monitor.get_metrics()
            }
        )
    
    def setup_logging(self):
        """Initialize UI change logging."""
        self.ui_logger = UIChangeLogger()
        self.ui_logger.set_log_level('INFO')
        
    def log_error(self, message):
        """Log error messages."""
        self.ui_logger.log_ui_change(
            component="TransformTab",
            change_type="error",
            details={'message': message}
        ) 