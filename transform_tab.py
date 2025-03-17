from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                           QGroupBox, QFormLayout, QDoubleSpinBox,
                           QRadioButton, QButtonGroup, QLabel,
                           QHBoxLayout, QCheckBox, QGridLayout,
                           QListWidget, QListWidgetItem, QMenu,
                           QLineEdit, QComboBox, QDialog, QInputDialog,
                           QDateTimeEdit, QSpinBox, QScrollArea,
                           QFrame, QToolButton, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QTimer, QPropertyAnimation, QSequentialAnimationGroup, QAbstractAnimation, QPointF
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence, QPainterPath, QPen, QColor, QRectF, QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem
import json
import os
from typing import Dict, List, Set, Any, Optional
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
    HANDLE_SIZE = 10  # Size of draggable handles in pixels
    SCALE_SENSITIVITY = 0.01  # Sensitivity factor for scale dragging
    
    # Signals
    transformApplied = pyqtSignal(str, dict)  # (transform_type, transform_params)
    transformPreviewRequested = pyqtSignal(str, dict)  # (transform_type, {axis: value})
    transformPreviewCanceled = pyqtSignal()
    transformHistoryChanged = pyqtSignal()
    modeChanged = pyqtSignal(str)
    presetSelected = pyqtSignal(str)
    presetSaved = pyqtSignal(str, dict)
    presetDeleted = pyqtSignal(str)
    
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
        
        # Dragging state
        self._dragging = False
        self._drag_handle = None
        self._drag_start = None
        self._rotation_handle = None
        self._scale_handles = []
        self._rotation_center = None
        
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
        self.transformApplied.emit(self.current_transform_mode, transform_values)
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
        
        # Transform mode selection with enhanced visual feedback
        mode_group = QGroupBox("Transform Mode")
        mode_layout = QVBoxLayout()
        
        # Create radio buttons for transform modes with shortcuts and tooltips
        self.mode_group = QButtonGroup()
        modes = [
            ("Translate (T)", "translate", "Move objects along axes (T)\nUse arrow keys or drag to move"),
            ("Rotate (R)", "rotate", "Rotate objects around axes (R)\nHold Shift for precise rotation"),
            ("Scale (S)", "scale", "Scale objects along axes (S)\nHold Shift for uniform scaling")
        ]
        
        for text, mode, tooltip in modes:
            radio = QRadioButton(text)
            radio.setToolTip(tooltip)
            radio.setStyleSheet("""
                QRadioButton {
                    padding: 8px;
                    border-radius: 4px;
                    margin: 2px;
                }
                QRadioButton:hover {
                    background-color: rgba(33, 150, 243, 0.1);
                }
                QRadioButton:checked {
                    background-color: #E3F2FD;
                    border: 1px solid #2196F3;
                }
            """)
            self.mode_group.addButton(radio)
            mode_layout.addWidget(radio)
            radio.clicked.connect(lambda checked, m=mode: self.onModeChanged(m))
            
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Quick transform buttons with tooltips and visual feedback
        quick_transform_group = QGroupBox("Quick Transforms")
        quick_transform_layout = QHBoxLayout()
        
        # Common button style
        button_style = """
            QPushButton {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.2);
            }
        """
        
        # Flip horizontal
        self.flip_h_button = QPushButton("Flip H")
        self.flip_h_button.setToolTip("Flip horizontally (Ctrl+H)\nMirrors the object along the X axis")
        self.flip_h_button.setStyleSheet(button_style)
        self.flip_h_button.clicked.connect(lambda: self.quickTransform("flip_h"))
        quick_transform_layout.addWidget(self.flip_h_button)
        
        # Flip vertical
        self.flip_v_button = QPushButton("Flip V")
        self.flip_v_button.setToolTip("Flip vertically (Ctrl+J)\nMirrors the object along the Y axis")
        self.flip_v_button.setStyleSheet(button_style)
        self.flip_v_button.clicked.connect(lambda: self.quickTransform("flip_v"))
        quick_transform_layout.addWidget(self.flip_v_button)
        
        # Rotate 90° clockwise
        self.rotate_cw_button = QPushButton("Rotate CW")
        self.rotate_cw_button.setToolTip("Rotate 90° clockwise (Ctrl+Shift+R)\nQuick rotation for precise alignment")
        self.rotate_cw_button.setStyleSheet(button_style)
        self.rotate_cw_button.clicked.connect(lambda: self.quickTransform("rotate_90_cw"))
        quick_transform_layout.addWidget(self.rotate_cw_button)
        
        # Rotate 90° counter-clockwise
        self.rotate_ccw_button = QPushButton("Rotate CCW")
        self.rotate_ccw_button.setToolTip("Rotate 90° counter-clockwise (Ctrl+Shift+L)\nQuick rotation for precise alignment")
        self.rotate_ccw_button.setStyleSheet(button_style)
        self.rotate_ccw_button.clicked.connect(lambda: self.quickTransform("rotate_90_ccw"))
        quick_transform_layout.addWidget(self.rotate_ccw_button)
        
        # Reset transform
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset all transformations (Ctrl+R)\nReturns object to its original state")
        self.reset_button.setStyleSheet(button_style)
        self.reset_button.clicked.connect(self.reset_transform_values)
        quick_transform_layout.addWidget(self.reset_button)
        
        quick_transform_group.setLayout(quick_transform_layout)
        layout.addWidget(quick_transform_group)
        
        # Status label for visual feedback
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                color: #2196F3;
                padding: 4px;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Set the main layout
        self.setLayout(layout)
        
        # Select translate mode by default
        self.mode_group.buttons()[0].setChecked(True)
        
    def onModeChanged(self, mode):
        """Handle mode change with visual feedback and animation."""
        # Store the old mode
        old_mode = self.current_transform_mode
        self.current_transform_mode = mode
        
        # Create fade-out animation for the mode group
        fade_out = QPropertyAnimation(self.mode_group, b"windowOpacity")
        fade_out.setDuration(150)  # Short duration for subtle effect
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        
        # Create fade-in animation
        fade_in = QPropertyAnimation(self.mode_group, b"windowOpacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        
        # Sequential animation group
        transition = QSequentialAnimationGroup()
        transition.addAnimation(fade_out)
        transition.addAnimation(fade_in)
        
        # Update UI elements between animations
        def update_ui():
            # Update radio button styles with smooth color transition
            for button in self.mode_group.buttons():
                if button.isChecked():
                    button.setStyleSheet("""
                        QRadioButton {
                            padding: 8px;
                            border-radius: 4px;
                            margin: 2px;
                            background-color: #E3F2FD;
                            border: 1px solid #2196F3;
                        }
                        QRadioButton:hover {
                            background-color: #BBDEFB;
                        }
                    """)
                else:
                    button.setStyleSheet("""
                        QRadioButton {
                            padding: 8px;
                            border-radius: 4px;
                            margin: 2px;
                        }
                        QRadioButton:hover {
                            background-color: rgba(33, 150, 243, 0.1);
                        }
                    """)
            
            # Update status label with mode-specific color
            mode_colors = {
                'translate': '#2196F3',  # Blue
                'rotate': '#4CAF50',     # Green
                'scale': '#FF9800'       # Orange
            }
            color = mode_colors.get(mode, '#2196F3')
            self.status_label.setText(f"Active Mode: {mode.capitalize()}")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    padding: 4px;
                    font-size: 10pt;
                    font-weight: bold;
                }}
            """)
            
            # Update mode indicator
            self._update_mode_indicator(mode)
            
            # Emit mode change signal
            self.mode_changed.emit(mode)
            
            # Update preview if needed
            if self._preview_active:
                self.updatePreview()
        
        # Connect the update function to the fade-out animation's finished signal
        fade_out.finished.connect(update_ui)
        
        # Start animation
        transition.start(QAbstractAnimation.DeleteWhenStopped)
        
        # Log the mode change
        self.logger.info(f"Transform mode changed: {old_mode} -> {mode}")

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

    def quickTransform(self, transform_type):
        """Apply quick transformation presets with visual feedback."""
        if not self._preview_active:
            return
            
        # Store current state for preview
        self.preview_points = self.points.copy()
        
        # Apply transform with visual feedback
        if transform_type == "flip_h":
            self.scale_x_spin.setValue(-self.scale_x_spin.value())
            self.show_transform_feedback("Flipped horizontally")
        elif transform_type == "flip_v":
            self.scale_y_spin.setValue(-self.scale_y_spin.value())
            self.show_transform_feedback("Flipped vertically")
        elif transform_type == "rotate_90_cw":
            current_angle = self.rotation_spin.value()
            self.rotation_spin.setValue((current_angle + 90) % 360)
            self.show_transform_feedback("Rotated 90° clockwise")
        elif transform_type == "rotate_90_ccw":
            current_angle = self.rotation_spin.value()
            self.rotation_spin.setValue((current_angle - 90) % 360)
            self.show_transform_feedback("Rotated 90° counter-clockwise")
            
        # Update preview
        self.updatePreview()
        
        # Clear preview after a short delay
        QTimer.singleShot(1000, self.clearPreview)
        
    def show_transform_feedback(self, message):
        """Show visual feedback for transform operations."""
        # Update status label with transform message
        self.status_label.setText(message)
        self.status_label.setStyleSheet("QLabel { color: #2196F3; font-weight: bold; }")
        
        # Reset style after delay
        QTimer.singleShot(1000, lambda: self.status_label.setStyleSheet("QLabel { color: #2196F3; }"))
        
        # Log the transform operation
        self.logger.info(f"Quick transform: {message}")
        
    def setupShortcuts(self):
        """Set up keyboard shortcuts for quick transforms."""
        # Flip horizontal
        self.flip_h_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        self.flip_h_shortcut.activated.connect(lambda: self.quickTransform("flip_h"))
        
        # Flip vertical
        self.flip_v_shortcut = QShortcut(QKeySequence("Ctrl+J"), self)
        self.flip_v_shortcut.activated.connect(lambda: self.quickTransform("flip_v"))
        
        # Rotate 90° clockwise
        self.rotate_cw_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        self.rotate_cw_shortcut.activated.connect(lambda: self.quickTransform("rotate_90_cw"))
        
        # Rotate 90° counter-clockwise
        self.rotate_ccw_shortcut = QShortcut(QKeySequence("Ctrl+Shift+L"), self)
        self.rotate_ccw_shortcut.activated.connect(lambda: self.quickTransform("rotate_90_ccw"))
        
        # Reset transform
        self.reset_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.reset_shortcut.activated.connect(self.reset_transform_values)
        
    def updatePreview(self):
        """Update the preview display with visual guides."""
        if not self._preview_active:
            return
            
        # Clear existing preview
        self.clearPreview()
        
        # Draw the transformed shape
        preview_path = QPainterPath()
        preview_path.moveTo(self.preview_points[0][0], self.preview_points[0][1])
        for point in self.preview_points[1:]:
            preview_path.lineTo(point[0], point[1])
        if len(self.preview_points) >= 3:
            preview_path.lineTo(self.preview_points[0][0], self.preview_points[0][1])
            
        # Set preview style based on mode
        mode_colors = {
            'translate': '#2196F3',  # Blue
            'rotate': '#4CAF50',     # Green
            'scale': '#FF9800'       # Orange
        }
        color = mode_colors.get(self.current_transform_mode, '#2196F3')
        
        # Draw preview with mode-specific style
        preview_pen = QPen(QColor(color), 1, Qt.PenStyle.DashLine)
        self.scene.addPath(preview_path, preview_pen)
        
        # Add visual guides based on transform mode
        if self.current_transform_mode == 'translate':
            self._draw_translation_guides()
        elif self.current_transform_mode == 'rotate':
            self._draw_rotation_guides()
        elif self.current_transform_mode == 'scale':
            self._draw_scale_guides()
            
        # Update the scene
        self.scene.update()
        
    def _draw_translation_guides(self):
        """Draw visual guides for translation."""
        # Calculate center point
        center_x = sum(p[0] for p in self.preview_points) / len(self.preview_points)
        center_y = sum(p[1] for p in self.preview_points) / len(self.preview_points)
        
        # Draw translation arrows
        arrow_size = 20
        arrow_pen = QPen(QColor('#2196F3'), 1, Qt.PenStyle.SolidLine)
        
        # X-axis arrow
        x_arrow = QPainterPath()
        x_arrow.moveTo(center_x, center_y)
        x_arrow.lineTo(center_x + arrow_size, center_y)
        x_arrow.lineTo(center_x + arrow_size - 5, center_y - 5)
        x_arrow.moveTo(center_x + arrow_size, center_y)
        x_arrow.lineTo(center_x + arrow_size - 5, center_y + 5)
        self.scene.addPath(x_arrow, arrow_pen)
        
        # Y-axis arrow
        y_arrow = QPainterPath()
        y_arrow.moveTo(center_x, center_y)
        y_arrow.lineTo(center_x, center_y + arrow_size)
        y_arrow.lineTo(center_x - 5, center_y + arrow_size - 5)
        y_arrow.moveTo(center_x, center_y + arrow_size)
        y_arrow.lineTo(center_x + 5, center_y + arrow_size - 5)
        self.scene.addPath(y_arrow, arrow_pen)
        
        # Add tooltips
        for item in self.scene.items():
            if isinstance(item, QGraphicsPathItem):
                item.setToolTip(f"Translation Guide\nX: {self.translate_x.value():.2f}\nY: {self.translate_y.value():.2f}")
                
    def _draw_rotation_guides(self):
        """Draw visual guides for rotation with draggable handle."""
        # Calculate center point
        center_x = sum(p[0] for p in self.preview_points) / len(self.preview_points)
        center_y = sum(p[1] for p in self.preview_points) / len(self.preview_points)
        self._rotation_center = QPointF(center_x, center_y)
        
        # Draw rotation arc
        radius = 30
        angle = self.rotation_spin.value()
        arc_rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
        arc_pen = QPen(QColor('#4CAF50'), 1, Qt.PenStyle.DashLine)
        arc_item = self.scene.addEllipse(arc_rect, arc_pen)
        arc_item.setStartAngle(0)
        arc_item.setSpanAngle(angle * 16)  # Convert degrees to 1/16th of a degree for Qt
        
        # Draw rotation handle
        handle_pen = QPen(QColor('#4CAF50'), 1, Qt.PenStyle.SolidLine)
        handle_path = QPainterPath()
        handle_path.moveTo(center_x, center_y)
        handle_x = center_x + radius * np.cos(np.radians(angle))
        handle_y = center_y + radius * np.sin(np.radians(angle))
        handle_path.lineTo(handle_x, handle_y)
        
        # Create draggable handle
        self._rotation_handle = self.scene.addPath(handle_path, handle_pen)
        self._rotation_handle.setFlag(QGraphicsItem.ItemIsMovable, False)  # We handle movement manually
        self._rotation_handle.setToolTip(f"Rotation Guide\nAngle: {angle:.1f}°\nDrag to rotate")
        self._rotation_handle.setData(0, "rotation_handle")  # Tag for identification
        
        # Add angle label
        label_x = handle_x + 10
        label_y = handle_y + 10
        angle_label = self.scene.addText(f"{angle:.1f}°")
        angle_label.setPos(label_x, label_y)
        angle_label.setDefaultTextColor(QColor('#4CAF50'))
        
    def _draw_scale_guides(self):
        """Draw visual guides for scaling with draggable handles."""
        # Calculate bounding box
        min_x = min(p[0] for p in self.preview_points)
        max_x = max(p[0] for p in self.preview_points)
        min_y = min(p[1] for p in self.preview_points)
        max_y = max(p[1] for p in self.preview_points)
        
        # Draw scaling grid
        grid_pen = QPen(QColor('#FF9800'), 1, Qt.PenStyle.DashLine)
        
        # Draw grid lines
        for i in range(4):
            # Vertical lines
            x = min_x + (max_x - min_x) * (i + 1) / 4
            self.scene.addLine(x, min_y, x, max_y, grid_pen)
            
            # Horizontal lines
            y = min_y + (max_y - min_y) * (i + 1) / 4
            self.scene.addLine(min_x, y, max_x, y, grid_pen)
            
        # Clear existing scale handles
        for handle in self._scale_handles:
            self.scene.removeItem(handle)
        self._scale_handles.clear()
        
        # Draw scale handles
        handle_pen = QPen(QColor('#FF9800'), 1, Qt.PenStyle.SolidLine)
        handle_size = self.HANDLE_SIZE
        
        # Corner handles with labels
        corners = [
            (min_x, min_y, "top_left", "↖"),
            (max_x, min_y, "top_right", "↗"),
            (max_x, max_y, "bottom_right", "↘"),
            (min_x, max_y, "bottom_left", "↙")
        ]
        
        for x, y, handle_id, arrow in corners:
            # Draw handle
            handle = QRectF(x - handle_size/2, y - handle_size/2, handle_size, handle_size)
            handle_item = self.scene.addRect(handle, handle_pen)
            handle_item.setToolTip(f"Scale Guide\nX: {self.scale_x.value():.2f}\nY: {self.scale_y.value():.2f}\nDrag to scale")
            handle_item.setData(0, handle_id)
            self._scale_handles.append(handle_item)
            
            # Draw direction arrow
            arrow_item = self.scene.addText(arrow)
            arrow_item.setPos(x + handle_size/2, y + handle_size/2)
            arrow_item.setDefaultTextColor(QColor('#FF9800'))
            
        # Add scale labels
        scale_text = f"Scale: {self.scale_x.value():.2f} × {self.scale_y.value():.2f}"
        label = self.scene.addText(scale_text)
        label.setPos(min_x, min_y - 20)
        label.setDefaultTextColor(QColor('#FF9800'))
        
    def clearPreview(self):
        """Clear the preview display and guides."""
        # Remove all preview items
        for item in self.scene.items():
            if isinstance(item, (QGraphicsPathItem, QGraphicsEllipseItem, 
                               QGraphicsLineItem, QGraphicsRectItem,
                               QGraphicsTextItem)):
                self.scene.removeItem(item)
                
        # Reset handle references
        self._rotation_handle = None
        self._scale_handles.clear()
        self._rotation_center = None
        
        # Update the scene
        self.scene.update()

    def mousePressEvent(self, event):
        """Handle mouse press events for draggable handles."""
        if not self._preview_active:
            return
            
        if self.current_transform_mode == 'rotate' and self._rotation_handle:
            if self._rotation_handle.contains(event.pos()):
                self._dragging = True
                self._drag_handle = self._rotation_handle
                self._drag_start = event.pos()
                self._highlight_handle(self._rotation_handle)
                event.accept()
                return
                
        elif self.current_transform_mode == 'scale':
            for handle in self._scale_handles:
                if handle.contains(event.pos()):
                    self._dragging = True
                    self._drag_handle = handle
                    self._drag_start = event.pos()
                    self._highlight_handle(handle)
                    event.accept()
                    return
                    
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move events for draggable handles."""
        if not self._dragging or not self._drag_handle:
            super().mouseMoveEvent(event)
            return
            
        if self.current_transform_mode == 'rotate':
            self._handle_rotation_drag(event)
        elif self.current_transform_mode == 'scale':
            self._handle_scale_drag(event)
            
        event.accept()
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release events for draggable handles."""
        if self._dragging:
            self._dragging = False
            if self._drag_handle:
                self._unhighlight_handle(self._drag_handle)
            self._drag_handle = None
            self._drag_start = None
            event.accept()
            return
            
        super().mouseReleaseEvent(event)
        
    def _handle_rotation_drag(self, event):
        """Handle rotation handle dragging."""
        if not self._rotation_center:
            return
            
        # Calculate angle from center to mouse position
        delta = event.pos() - self._rotation_center
        angle = np.degrees(np.arctan2(delta.y(), delta.x()))
        if angle < 0:
            angle += 360  # Normalize to 0-360 degrees
            
        # Update rotation value
        self.rotation_spin.setValue(angle)
        self.updatePreview()
        
    def _handle_scale_drag(self, event):
        """Handle scale handle dragging."""
        if not self._drag_start:
            return
            
        delta = event.pos() - self._drag_start
        handle_id = self._drag_handle.data(0)
        
        # Get current scale values
        current_x = self.scale_x.value()
        current_y = self.scale_y.value()
        
        # Calculate new scale values based on handle position
        if "left" in handle_id:
            new_x = current_x - delta.x() * self.SCALE_SENSITIVITY
        elif "right" in handle_id:
            new_x = current_x + delta.x() * self.SCALE_SENSITIVITY
        else:
            new_x = current_x
            
        if "top" in handle_id:
            new_y = current_y - delta.y() * self.SCALE_SENSITIVITY
        elif "bottom" in handle_id:
            new_y = current_y + delta.y() * self.SCALE_SENSITIVITY
        else:
            new_y = current_y
            
        # Update scale values with minimum limit
        self.scale_x.setValue(max(0.1, new_x))
        self.scale_y.setValue(max(0.1, new_y))
        self.updatePreview()
        
    def _highlight_handle(self, handle):
        """Highlight a handle during dragging."""
        if isinstance(handle, QGraphicsPathItem):
            handle.setPen(QPen(QColor('#4CAF50'), 2, Qt.PenStyle.SolidLine))
        elif isinstance(handle, QGraphicsRectItem):
            handle.setPen(QPen(QColor('#FF9800'), 2, Qt.PenStyle.SolidLine))
            
    def _unhighlight_handle(self, handle):
        """Remove highlight from a handle."""
        if isinstance(handle, QGraphicsPathItem):
            handle.setPen(QPen(QColor('#4CAF50'), 1, Qt.PenStyle.SolidLine))
        elif isinstance(handle, QGraphicsRectItem):
            handle.setPen(QPen(QColor('#FF9800'), 1, Qt.PenStyle.SolidLine)) 