from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal, QTimer
import time

class Viewport(QWidget):
    """Minimal viewport implementation for testing."""
    
    # Signals
    viewportUpdated = pyqtSignal()
    shapeSelected = pyqtSignal(int)  # shape_id
    selectionCleared = pyqtSignal()
    
    # Quality scaling thresholds
    QUALITY_SCALE_FPS_THRESHOLD = 45  # Target FPS for quality scaling
    QUALITY_SCALE_INTERVAL = 1000  # Check every 1 second
    QUALITY_LEVELS = {
        'high': {'mesh_detail': 1.0, 'texture_quality': 1.0, 'preview_quality': 1.0},
        'medium': {'mesh_detail': 0.75, 'texture_quality': 0.75, 'preview_quality': 0.75},
        'low': {'mesh_detail': 0.5, 'texture_quality': 0.5, 'preview_quality': 0.5}
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.shapes = []
        self.selected_shape = None
        
        # Dynamic quality scaling
        self.current_quality_level = 'high'
        self.fps_history = []
        self.last_quality_check = time.time()
        self.quality_scale_timer = QTimer()
        self.quality_scale_timer.timeout.connect(self._check_quality_scaling)
        self.quality_scale_timer.start(self.QUALITY_SCALE_INTERVAL)
    
    def add_shape(self):
        """Add a test shape."""
        shape_id = len(self.shapes)
        self.shapes.append({
            'id': shape_id,
            'type': 'rectangle',
            'position': (0, 0),
            'size': (100, 100)
        })
        self.viewportUpdated.emit()
        return shape_id
    
    def update(self):
        """Update the viewport."""
        super().update()
        self.viewportUpdated.emit()
    
    def select_shape(self, shape_id: int):
        """Select a shape by ID."""
        if 0 <= shape_id < len(self.shapes):
            self.selected_shape = shape_id
            self.shapeSelected.emit(shape_id)
            self.update()
    
    def clear_selection(self):
        """Clear shape selection."""
        self.selected_shape = None
        self.selectionCleared.emit()
        self.update()
    
    def _check_quality_scaling(self):
        """Adjust quality settings based on performance."""
        current_time = time.time()
        if not self.fps_history:
            return
            
        # Calculate average FPS
        avg_fps = len(self.fps_history) / (current_time - self.last_quality_check)
        self.fps_history.clear()
        self.last_quality_check = current_time
        
        # Adjust quality level based on FPS
        if avg_fps < self.QUALITY_SCALE_FPS_THRESHOLD * 0.8:  # Below 80% of target
            if self.current_quality_level == 'high':
                self.current_quality_level = 'medium'
            elif self.current_quality_level == 'medium':
                self.current_quality_level = 'low'
        elif avg_fps > self.QUALITY_SCALE_FPS_THRESHOLD * 1.2:  # Above 120% of target
            if self.current_quality_level == 'low':
                self.current_quality_level = 'medium'
            elif self.current_quality_level == 'medium':
                self.current_quality_level = 'high'
        
        # Apply quality settings
        self._apply_quality_settings()
        
    def _apply_quality_settings(self):
        """Apply current quality level settings."""
        settings = self.QUALITY_LEVELS[self.current_quality_level]
        
        # Update mesh detail level
        self.scene_manager.set_mesh_detail(settings['mesh_detail'])
        
        # Update texture quality
        self.scene_manager.set_texture_quality(settings['texture_quality'])
        
        # Update preview quality
        if hasattr(self, 'preview_overlay'):
            self.preview_overlay.set_quality(settings['preview_quality'])
            
        self.update()
    
    def _on_frame(self):
        """Track frame times for quality scaling."""
        self.fps_history.append(time.time())
        super()._on_frame()

class TransformPreviewOverlay:
    """Manages transform preview visualization in the viewport."""
    
    # Preview update thresholds
    UPDATE_INTERVAL_MS = 16  # ~60 FPS
    BATCH_UPDATE_SIZE = 5  # Number of shapes to update per frame
    
    def __init__(self, viewport):
        # ... existing code ...
        
        # Selective update settings
        self.last_update = time.time()
        self.update_queue = []
        self.quality = 1.0
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_update_queue)
        self.update_timer.start(self.UPDATE_INTERVAL_MS)
    
    def set_quality(self, quality_level: float):
        """Set preview quality level (0.0 to 1.0)."""
        self.quality = max(0.1, min(1.0, quality_level))
        self._adjust_update_interval()
    
    def _adjust_update_interval(self):
        """Adjust update interval based on quality level."""
        # Scale interval inversely with quality (lower quality = less frequent updates)
        interval = int(self.UPDATE_INTERVAL_MS / self.quality)
        self.update_timer.setInterval(interval)
    
    def update_preview(self, axes_values, transform_mode=None):
        """Queue preview update with selective processing."""
        if not self.active:
            return
            
        self.axes_values.update(axes_values)
        if transform_mode is not None:
            self.transform_mode = transform_mode
            
        # Add update to queue
        self.update_queue.append({
            'axes_values': self.axes_values.copy(),
            'transform_mode': self.transform_mode
        })
        
        # Limit queue size
        if len(self.update_queue) > 100:
            self.update_queue = self.update_queue[-100:]
    
    def _process_update_queue(self):
        """Process queued preview updates selectively."""
        current_time = time.time()
        if not self.update_queue or (current_time - self.last_update) * 1000 < self.UPDATE_INTERVAL_MS:
            return
            
        # Process a batch of updates
        updates_to_process = min(self.BATCH_UPDATE_SIZE, len(self.update_queue))
        latest_update = self.update_queue[-1]  # Always include the most recent update
        
        # Clear queue and apply latest state
        self.update_queue.clear()
        
        # Apply the update
        if self.original_state:
            self._apply_preview_transform(
                latest_update['axes_values'],
                latest_update['transform_mode']
            )
            
        self.last_update = current_time
        self.viewport.update()
    
    def _apply_preview_transform(self, axes_values, transform_mode):
        """Apply preview transform with performance optimization."""
        if not self.original_state:
            return
            
        # Calculate total transform based on all active axes
        transform_matrix = self._calculate_transform_matrix(axes_values, transform_mode)
        
        # Apply transform to selected shapes
        for shape_id, original in self.original_state.items():
            shape = self.viewport.scene_manager.get_shape(shape_id)
            if shape:
                # Apply transform based on quality level
                if self.quality < 1.0:
                    # Use simplified transform for lower quality
                    self._apply_simplified_transform(shape, transform_matrix)
                else:
                    # Use full transform
                    self._apply_full_transform(shape, transform_matrix, original)
    
    def _apply_simplified_transform(self, shape, transform_matrix):
        """Apply simplified transform for better performance."""
        # Apply transform only to bounding box for preview
        shape.transform_preview_bounds(transform_matrix)
    
    def _apply_full_transform(self, shape, transform_matrix, original_state):
        """Apply full transform with all details."""
        # Apply transform to full mesh
        shape.transform_preview_full(transform_matrix, original_state) 