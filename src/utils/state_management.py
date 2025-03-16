from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
import hashlib
from ..utils.logging import TransformLogger
import numpy as np
import time
import psutil
from .hardware_profile import HardwareProfile
from collections import deque
import logging

@dataclass
class TransformState:
    """Represents a complete state of the transform system."""
    timestamp: datetime
    scene_state: Dict[str, Any]  # Shape positions, rotations, scales
    transform_history: List[Dict[str, Any]]  # Transform operations history
    ui_state: Dict[str, Any]  # UI component states
    mode: str  # Current transform mode
    selected_shapes: List[str]  # Currently selected shape IDs
    active_axes: List[str]  # Currently active transform axes
    snap_settings: Dict[str, Any]  # Current snap settings
    performance_metrics: Optional[Dict[str, Any]] = None  # Current performance metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'scene_state': self.scene_state,
            'transform_history': self.transform_history,
            'ui_state': self.ui_state,
            'mode': self.mode,
            'selected_shapes': self.selected_shapes,
            'active_axes': self.active_axes,
            'snap_settings': self.snap_settings,
            'performance_metrics': self.performance_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransformState':
        """Create TransformState from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            scene_state=data['scene_state'],
            transform_history=data['transform_history'],
            ui_state=data['ui_state'],
            mode=data['mode'],
            selected_shapes=data['selected_shapes'],
            active_axes=data['active_axes'],
            snap_settings=data['snap_settings'],
            performance_metrics=data.get('performance_metrics')
        )
    
    def calculate_hash(self) -> str:
        """Calculate a hash of critical state components."""
        hash_input = json.dumps({
            'scene_state': self.scene_state,
            'mode': self.mode,
            'selected_shapes': self.selected_shapes,
            'active_axes': self.active_axes
        }, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()

class PerformanceMetrics:
    """Tracks and manages performance metrics during runtime."""
    
    def __init__(self, max_samples: int = 1000):
        """Initialize performance metrics tracking."""
        self.max_samples = max_samples
        self.frame_times: deque = deque(maxlen=max_samples)
        self.memory_usage: deque = deque(maxlen=max_samples)
        self.operation_times: deque = deque(maxlen=max_samples)
        self.last_frame_time = time.time()
        self.logger = logging.getLogger(__name__)
    
    def record_frame(self):
        """Record frame time."""
        current_time = time.time()
        frame_time = (current_time - self.last_frame_time) * 1000  # Convert to ms
        self.frame_times.append(frame_time)
        self.last_frame_time = current_time
        
        # Record memory usage
        memory = psutil.Process().memory_info()
        self.memory_usage.append(memory.rss / (1024 * 1024))  # Convert to MB
    
    def record_operation(self, duration: float):
        """Record operation time."""
        self.operation_times.append(duration)
    
    def get_current_metrics(self) -> Dict[str, float]:
        """Get current performance metrics."""
        try:
            frame_time = self.frame_times[-1] if self.frame_times else 0
            memory_usage = self.memory_usage[-1] if self.memory_usage else 0
            operation_time = self.operation_times[-1] if self.operation_times else 0
            
            return {
                'frame_time': frame_time,
                'memory_usage': memory_usage,
                'operation_time': operation_time
            }
        except Exception as e:
            self.logger.error(f"Error getting metrics: {str(e)}", exc_info=True)
            return {
                'frame_time': 0,
                'memory_usage': 0,
                'operation_time': 0
            }
    
    def get_average_metrics(self, window: Optional[int] = None) -> Dict[str, float]:
        """Get average metrics over the specified window."""
        try:
            if window is None:
                window = len(self.frame_times)
            
            window = min(window, len(self.frame_times))
            
            if window == 0:
                return {
                    'avg_frame_time': 0,
                    'avg_memory_usage': 0,
                    'avg_operation_time': 0
                }
            
            recent_frames = list(self.frame_times)[-window:]
            recent_memory = list(self.memory_usage)[-window:]
            recent_operations = list(self.operation_times)[-window:]
            
            return {
                'avg_frame_time': sum(recent_frames) / len(recent_frames),
                'avg_memory_usage': sum(recent_memory) / len(recent_memory),
                'avg_operation_time': sum(recent_operations) / len(recent_operations) if recent_operations else 0
            }
        except Exception as e:
            self.logger.error(f"Error calculating averages: {str(e)}", exc_info=True)
            return {
                'avg_frame_time': 0,
                'avg_memory_usage': 0,
                'avg_operation_time': 0
            }
    
    def reset(self):
        """Reset all metrics."""
        self.frame_times.clear()
        self.memory_usage.clear()
        self.operation_times.clear()
        self.last_frame_time = time.time()

class TransformStateManager:
    """Manages transform system state with checkpointing and rollback capabilities."""
    
    # Batch size configuration
    BATCH_SIZES = {
        'low-end': {'default': 25, 'max': 50},
        'mid-range': {'default': 50, 'max': 100},
        'high-end': {'default': 100, 'max': 200}
    }
    
    def __init__(self, transform_tab, viewport, scene_manager):
        self.transform_tab = transform_tab
        self.viewport = viewport
        self.scene_manager = scene_manager
        self.logger = TransformLogger('state_manager.log')
        
        self.checkpoints: List[TransformState] = []
        self.max_checkpoints = 50  # Maximum number of checkpoints to maintain
        self.checkpoint_counter = 0
        
        # Create checkpoints directory
        os.makedirs('checkpoints', exist_ok=True)
        
        # Set up automatic checkpointing
        self._setup_auto_checkpoints()
        
        # Add manual checkpoint button to UI
        self._setup_manual_checkpoint_ui()
        
        self.performance_metrics = PerformanceMetrics(viewport)
        
        # Set up frame time monitoring
        self.viewport.frameSwapped.connect(self._update_frame_time)
        
        # Get hardware profile for batch size optimization
        self.hardware_profile = HardwareProfile.detect()
        self.batch_config = self.BATCH_SIZES[self.hardware_profile.tier]
        
        # Initialize with hardware-appropriate batch size
        self.current_batch_size = self.batch_config['default']
        self.max_batch_size = self.batch_config['max']
        
        # Add batch size monitoring
        self._batch_performance_history = []
        self._last_batch_adjustment = time.time()
    
    def _setup_manual_checkpoint_ui(self):
        """Add manual checkpoint button to transform tab."""
        self.transform_tab.add_checkpoint_button(
            "Create Checkpoint",
            lambda: self.create_checkpoint("manual")
        )
    
    def _setup_auto_checkpoints(self):
        """Set up automatic checkpoint creation triggers."""
        # Before compound transforms
        self.transform_tab.compound_transform_started.connect(
            lambda: self.create_checkpoint("pre_compound_transform")
        )
        
        # Before mode switches
        self.transform_tab.mode_changing.connect(
            lambda old_mode, new_mode: self.create_checkpoint(f"mode_switch_{old_mode}_to_{new_mode}")
        )
        
        # On preset application
        self.transform_tab.preset_selected.connect(
            lambda preset_name: self.create_checkpoint(f"preset_application_{preset_name}")
        )
        
        # Every N operations
        self.transform_tab.transform_applied.connect(self._check_operation_count)
    
    def _check_operation_count(self, *args):
        """Create checkpoint every N operations."""
        self.checkpoint_counter += 1
        if self.checkpoint_counter >= 10:  # Create checkpoint every 10 operations
            self.create_checkpoint("operation_count")
            self.checkpoint_counter = 0
    
    def _update_frame_time(self):
        """Update frame time metrics."""
        current_time = time.perf_counter()
        if hasattr(self, '_last_frame_time'):
            frame_time = current_time - self._last_frame_time
            self.performance_metrics.update_frame_time(frame_time * 1000)  # Convert to ms
        self._last_frame_time = current_time
    
    def capture_current_state(self) -> TransformState:
        """Capture current state of the transform system."""
        try:
            # Start timing the capture
            start_time = time.perf_counter()
            
            # Capture scene state
            scene_state = {}
            for shape_id in self.scene_manager.get_all_shapes():
                shape = self.scene_manager.get_shape(shape_id)
                scene_state[shape_id] = {
                    'position': shape.transform.position.tolist(),
                    'rotation': shape.transform.rotation.tolist(),
                    'scale': shape.transform.scale.tolist(),
                    'visible': shape.is_visible,
                    'properties': shape.properties
                }
            
            # Capture UI state
            ui_state = {
                'mode_indicator': self.transform_tab.mode_indicator.text(),
                'relative_mode': self.transform_tab.relative_mode_checkbox.isChecked(),
                'snap_enabled': self.transform_tab.snap_checkbox.isChecked(),
                'transform_values': self.transform_tab.get_current_values(),
                'active_preset': self.transform_tab.preset_combo.currentText()
            }
            
            # Get current performance metrics
            performance_metrics = self.performance_metrics.get_metrics()
            
            # Record the time taken to capture state
            capture_time = (time.perf_counter() - start_time) * 1000
            self.performance_metrics.record_operation_time('state_capture', capture_time)
            
            state = TransformState(
                timestamp=datetime.now(),
                scene_state=scene_state,
                transform_history=self.transform_tab.transform_history.copy(),
                ui_state=ui_state,
                mode=self.transform_tab.current_mode,
                selected_shapes=self.viewport.get_selected_shapes(),
                active_axes=self.transform_tab.get_active_axes(),
                snap_settings=self.transform_tab.get_snap_settings(),
                performance_metrics=performance_metrics
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to capture state: {e}")
            raise
    
    def _validate_shape_state(self, current: Dict[str, Any], checkpoint: Dict[str, Any], tolerance: float = 1e-5) -> Dict[str, Any]:
        """Validate shape states with floating-point tolerance."""
        differences = {}
        
        # Compare shape counts
        if len(current) != len(checkpoint):
            differences['shape_count'] = {
                'current': len(current),
                'checkpoint': len(checkpoint),
                'message': f"Shape count mismatch: expected {len(checkpoint)}, got {len(current)}"
            }
        
        # Compare individual shapes
        for shape_id in set(current) | set(checkpoint):
            if shape_id not in current:
                differences[shape_id] = {'message': 'Missing in current state'}
                continue
            if shape_id not in checkpoint:
                differences[shape_id] = {'message': 'Missing in checkpoint state'}
                continue
            
            shape_current = current[shape_id]
            shape_checkpoint = checkpoint[shape_id]
            
            shape_diff = {}
            
            # Compare transforms with tolerance
            for attr in ['position', 'rotation', 'scale']:
                if not np.allclose(
                    np.array(shape_current[attr]),
                    np.array(shape_checkpoint[attr]),
                    atol=tolerance
                ):
                    shape_diff[attr] = {
                        'current': shape_current[attr],
                        'checkpoint': shape_checkpoint[attr],
                        'message': f"{attr} mismatch beyond tolerance of {tolerance}"
                    }
            
            # Compare other properties exactly
            for prop in ['visible', 'properties']:
                if shape_current[prop] != shape_checkpoint[prop]:
                    shape_diff[prop] = {
                        'current': shape_current[prop],
                        'checkpoint': shape_checkpoint[prop],
                        'message': f"{prop} mismatch"
                    }
            
            if shape_diff:
                differences[shape_id] = shape_diff
        
        return differences

    def validate_state(self, state: TransformState) -> bool:
        """Validate the current system state against a checkpoint with detailed component checks."""
        try:
            current_state = self.capture_current_state()
            validation_results = {}
            
            # Validate scene state with floating-point tolerance
            scene_differences = self._validate_shape_state(
                current_state.scene_state,
                state.scene_state
            )
            if scene_differences:
                validation_results['scene_state'] = scene_differences
            
            # Validate selection state
            if set(current_state.selected_shapes) != set(state.selected_shapes):
                validation_results['selection'] = {
                    'current': current_state.selected_shapes,
                    'checkpoint': state.selected_shapes,
                    'message': 'Selection state mismatch'
                }
            
            # Validate transform mode and active axes
            if current_state.mode != state.mode:
                validation_results['mode'] = {
                    'current': current_state.mode,
                    'checkpoint': state.mode,
                    'message': 'Transform mode mismatch'
                }
            
            if set(current_state.active_axes) != set(state.active_axes):
                validation_results['active_axes'] = {
                    'current': current_state.active_axes,
                    'checkpoint': state.active_axes,
                    'message': 'Active axes mismatch'
                }
            
            # Validate UI state critical components
            ui_differences = {}
            for key in ['relative_mode', 'snap_enabled']:
                if current_state.ui_state[key] != state.ui_state[key]:
                    ui_differences[key] = {
                        'current': current_state.ui_state[key],
                        'checkpoint': state.ui_state[key],
                        'message': f'UI state mismatch: {key}'
                    }
            if ui_differences:
                validation_results['ui_state'] = ui_differences
            
            # Log validation results with summary if there are mismatches
            if validation_results:
                # Calculate summary statistics
                mismatch_summary = {
                    'total_mismatches': 0,
                    'categories': {}
                }
                
                # Count mismatches by category
                if 'scene_state' in validation_results:
                    scene_mismatches = len(validation_results['scene_state'])
                    shape_position_mismatches = sum(
                        1 for shape_diff in validation_results['scene_state'].values()
                        if isinstance(shape_diff, dict) and 'position' in shape_diff
                    )
                    shape_rotation_mismatches = sum(
                        1 for shape_diff in validation_results['scene_state'].values()
                        if isinstance(shape_diff, dict) and 'rotation' in shape_diff
                    )
                    shape_scale_mismatches = sum(
                        1 for shape_diff in validation_results['scene_state'].values()
                        if isinstance(shape_diff, dict) and 'scale' in shape_diff
                    )
                    
                    mismatch_summary['categories']['scene'] = {
                        'total': scene_mismatches,
                        'position': shape_position_mismatches,
                        'rotation': shape_rotation_mismatches,
                        'scale': shape_scale_mismatches
                    }
                    mismatch_summary['total_mismatches'] += scene_mismatches
                
                if 'selection' in validation_results:
                    mismatch_summary['categories']['selection'] = 1
                    mismatch_summary['total_mismatches'] += 1
                
                if 'mode' in validation_results:
                    mismatch_summary['categories']['mode'] = 1
                    mismatch_summary['total_mismatches'] += 1
                
                if 'active_axes' in validation_results:
                    mismatch_summary['categories']['active_axes'] = 1
                    mismatch_summary['total_mismatches'] += 1
                
                if 'ui_state' in validation_results:
                    ui_mismatches = len(validation_results['ui_state'])
                    mismatch_summary['categories']['ui'] = ui_mismatches
                    mismatch_summary['total_mismatches'] += ui_mismatches
                
                # Generate human-readable summary
                summary_parts = []
                if 'scene' in mismatch_summary['categories']:
                    scene = mismatch_summary['categories']['scene']
                    scene_parts = []
                    if scene['position']: scene_parts.append(f"{scene['position']} position")
                    if scene['rotation']: scene_parts.append(f"{scene['rotation']} rotation")
                    if scene['scale']: scene_parts.append(f"{scene['scale']} scale")
                    summary_parts.append(f"Scene: {', '.join(scene_parts)}")
                
                for category in ['selection', 'mode', 'active_axes']:
                    if category in mismatch_summary['categories']:
                        summary_parts.append(category.replace('_', ' ').title())
                
                if 'ui' in mismatch_summary['categories']:
                    summary_parts.append(f"UI: {mismatch_summary['categories']['ui']} settings")
                
                summary_message = (
                    f"Validation failed with {mismatch_summary['total_mismatches']} "
                    f"mismatches: {'; '.join(summary_parts)}"
                )
                
                # Log summary first, then details
                self.logger.warning(summary_message)
                self.logger.warning(
                    "Detailed validation results",
                    extra={
                        'validation_results': validation_results,
                        'mismatch_summary': mismatch_summary,
                        'checkpoint_timestamp': state.timestamp.isoformat()
                    }
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"State validation failed: {e}")
            return False
    
    def _find_state_differences(
        self,
        state1: TransformState,
        state2: TransformState
    ) -> Dict[str, Any]:
        """Find differences between two states."""
        differences = {}
        
        # Compare scene states
        scene_diff = {}
        for shape_id in set(state1.scene_state) | set(state2.scene_state):
            if shape_id not in state1.scene_state:
                scene_diff[shape_id] = "Missing in current state"
            elif shape_id not in state2.scene_state:
                scene_diff[shape_id] = "Missing in checkpoint"
            else:
                shape1 = state1.scene_state[shape_id]
                shape2 = state2.scene_state[shape_id]
                if shape1 != shape2:
                    scene_diff[shape_id] = {
                        'current': shape1,
                        'checkpoint': shape2
                    }
        
        if scene_diff:
            differences['scene_state'] = scene_diff
        
        # Compare other critical state components
        for attr in ['mode', 'selected_shapes', 'active_axes']:
            val1 = getattr(state1, attr)
            val2 = getattr(state2, attr)
            if val1 != val2:
                differences[attr] = {
                    'current': val1,
                    'checkpoint': val2
                }
        
        return differences
    
    def create_checkpoint(self, reason: str = "manual") -> str:
        """Create a new checkpoint of the current state."""
        try:
            state = self.capture_current_state()
            
            # Generate checkpoint ID
            checkpoint_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{reason}"
            
            # Save checkpoint
            checkpoint_file = f"checkpoints/checkpoint_{checkpoint_id}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
            
            # Add to checkpoints list
            self.checkpoints.append(state)
            
            # Maintain maximum checkpoints
            if len(self.checkpoints) > self.max_checkpoints:
                oldest = self.checkpoints.pop(0)
                os.remove(f"checkpoints/checkpoint_{oldest.timestamp:%Y%m%d_%H%M%S}.json")
            
            self.logger.info(
                f"Created checkpoint: {checkpoint_id}",
                extra={'state': state.to_dict()}
            )
            
            return checkpoint_id
            
        except Exception as e:
            self.logger.error(f"Failed to create checkpoint: {e}")
            raise
    
    def rollback_to_checkpoint(self, checkpoint_id: str):
        """Rollback system to a specific checkpoint with validation."""
        try:
            # Load checkpoint state
            checkpoint_file = f"checkpoints/checkpoint_{checkpoint_id}.json"
            with open(checkpoint_file, 'r') as f:
                state_dict = json.load(f)
            
            state = TransformState.from_dict(state_dict)
            
            # Begin rollback
            self.logger.info(f"Rolling back to checkpoint: {checkpoint_id}")
            
            # Store pre-rollback state for recovery
            pre_rollback_state = self.capture_current_state()
            
            # Perform rollback
            self._apply_state(state)
            
            # Validate restored state
            if not self.validate_state(state):
                self.logger.error("Rollback validation failed, attempting recovery")
                self._apply_state(pre_rollback_state)
                raise ValueError("Rollback validation failed")
            
            self.logger.info(
                f"Successfully rolled back to checkpoint: {checkpoint_id}",
                extra={'restored_state': state.to_dict()}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to rollback to checkpoint {checkpoint_id}: {e}")
            raise
    
    def _apply_state(self, state: TransformState):
        """Apply a state to the system."""
        # Restore scene state
        for shape_id, shape_state in state.scene_state.items():
            shape = self.scene_manager.get_shape(shape_id)
            if shape:
                shape.transform.position = np.array(shape_state['position'])
                shape.transform.rotation = np.array(shape_state['rotation'])
                shape.transform.scale = np.array(shape_state['scale'])
                shape.is_visible = shape_state['visible']
                shape.properties.update(shape_state['properties'])
        
        # Restore transform history
        self.transform_tab.transform_history = state.transform_history.copy()
        
        # Restore UI state
        self.transform_tab.mode_indicator.setText(state.ui_state['mode_indicator'])
        self.transform_tab.relative_mode_checkbox.setChecked(state.ui_state['relative_mode'])
        self.transform_tab.snap_checkbox.setChecked(state.ui_state['snap_enabled'])
        self.transform_tab.set_current_values(state.ui_state['transform_values'])
        self.transform_tab.preset_combo.setCurrentText(state.ui_state['active_preset'])
        
        # Restore mode and selections
        self.transform_tab.set_mode(state.mode)
        self.viewport.clear_selection()
        for shape_id in state.selected_shapes:
            self.viewport.selectShape(shape_id)
        
        # Restore active axes and snap settings
        self.transform_tab.set_active_axes(state.active_axes)
        self.transform_tab.set_snap_settings(state.snap_settings)
        
        # Refresh viewport
        self.viewport.update()
    
    def get_latest_checkpoint(self) -> Optional[str]:
        """Get the ID of the most recent checkpoint."""
        if self.checkpoints:
            return f"{self.checkpoints[-1].timestamp:%Y%m%d_%H%M%S}"
        return None
    
    def cleanup_old_checkpoints(self, max_age_hours: int = 24):
        """Clean up checkpoints older than specified age."""
        current_time = datetime.now()
        old_checkpoints = [
            cp for cp in self.checkpoints
            if (current_time - cp.timestamp).total_seconds() > max_age_hours * 3600
        ]
        
        for checkpoint in old_checkpoints:
            checkpoint_id = f"{checkpoint.timestamp:%Y%m%d_%H%M%S}"
            checkpoint_file = f"checkpoints/checkpoint_{checkpoint_id}.json"
            
            try:
                os.remove(checkpoint_file)
                self.checkpoints.remove(checkpoint)
                self.logger.info(f"Removed old checkpoint: {checkpoint_id}")
            except Exception as e:
                self.logger.warning(f"Failed to remove checkpoint {checkpoint_id}: {e}")
    
    def _adjust_batch_size(self):
        """Dynamically adjust batch size based on performance."""
        current_time = time.time()
        if current_time - self._last_batch_adjustment < 60:  # Check every minute
            return
            
        if not self._batch_performance_history:
            return
            
        # Calculate average operation time
        avg_time = sum(t for _, t in self._batch_performance_history) / len(self._batch_performance_history)
        
        # Adjust batch size based on performance
        if avg_time < 16:  # Under 16ms (60 FPS)
            self.current_batch_size = min(
                self.current_batch_size * 1.2,
                self.max_batch_size
            )
        elif avg_time > 32:  # Over 32ms
            self.current_batch_size = max(
                self.current_batch_size * 0.8,
                self.BATCH_SIZES['low-end']['default']
            )
        
        # Clear history after adjustment
        self._batch_performance_history.clear()
        self._last_batch_adjustment = current_time
    
    def _record_batch_performance(self, operation_time):
        """Record performance of batch operations."""
        self._batch_performance_history.append((time.time(), operation_time))
        
        # Keep only recent history
        if len(self._batch_performance_history) > 100:
            self._batch_performance_history = self._batch_performance_history[-100:]
        
        # Check if we should adjust batch size
        self._adjust_batch_size() 