import psutil
import numpy as np
import logging
from datetime import datetime

class HardwareProfile:
    """Hardware profile detection and performance threshold management."""
    
    def __init__(self, cpu_info=None, memory_info=None):
        self.cpu_info = cpu_info or {}
        self.memory_info = memory_info or {}
        self._tier = None
        self.logger = logging.getLogger(__name__)
        self.os_info = self._get_os_info()
        
    def _get_os_info(self):
        """Get detailed OS information."""
        try:
            import platform
            return {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            }
        except Exception as e:
            self.logger.warning(f"Failed to get OS info: {e}")
            return {}
        
    @classmethod
    def detect(cls):
        """Detect hardware capabilities with enhanced detail."""
        # CPU info with extended details
        cpu_info = {
            'cores': psutil.cpu_count(logical=False),
            'threads': psutil.cpu_count(logical=True),
            'frequency': psutil.cpu_freq().max if psutil.cpu_freq() else 0
        }
        
        try:
            # Add CPU cache information if available
            import cpuinfo
            cpu_details = cpuinfo.get_cpu_info()
            cpu_info.update({
                'brand': cpu_details.get('brand_raw', ''),
                'cache_size': cpu_details.get('l3_cache_size', 0),
                'architecture': cpu_details.get('arch', ''),
                'flags': cpu_details.get('flags', [])
            })
        except ImportError:
            pass
        
        # Memory info with timing details
        memory = psutil.virtual_memory()
        memory_info = {
            'total': memory.total / (1024 * 1024 * 1024),  # GB
            'available': memory.available / (1024 * 1024 * 1024),  # GB
            'used': memory.used / (1024 * 1024 * 1024),  # GB
            'percent': memory.percent
        }
        
        try:
            # Add swap information
            swap = psutil.swap_memory()
            memory_info['swap_total'] = swap.total / (1024 * 1024 * 1024)  # GB
            memory_info['swap_used'] = swap.used / (1024 * 1024 * 1024)  # GB
        except Exception:
            pass
        
        return cls(cpu_info, memory_info)
    
    @property
    def tier(self):
        """Determine hardware tier based on capabilities with detailed scoring."""
        if self._tier is None:
            score = 0
            score_details = {}
            
            # CPU score (0-60 points)
            cpu_base_score = min(60, (
                (self.cpu_info.get('cores', 0) * 5) +  # 5 points per core
                (self.cpu_info.get('frequency', 0) / 1000)  # 1 point per GHz
            ))
            
            # CPU architecture bonus (up to 10 points)
            cpu_arch_bonus = 0
            if 'flags' in self.cpu_info:
                if 'avx2' in self.cpu_info['flags']: cpu_arch_bonus += 5
                if 'avx512f' in self.cpu_info['flags']: cpu_arch_bonus += 5
            
            cpu_score = min(60, cpu_base_score + cpu_arch_bonus)
            score += cpu_score
            score_details['cpu'] = {
                'base_score': cpu_base_score,
                'arch_bonus': cpu_arch_bonus,
                'total': cpu_score
            }
            
            # Memory score (0-40 points)
            memory_gb = self.memory_info.get('total', 0)
            memory_score = min(40, memory_gb / 2)  # 1 point per 2GB
            score += memory_score
            score_details['memory'] = {
                'total': memory_score,
                'gb_available': memory_gb
            }
            
            # Determine tier based on total score
            if score >= 80:
                self._tier = 'high-end'
            elif score >= 50:
                self._tier = 'mid-range'
            else:
                self._tier = 'low-end'
            
            # Log detailed scoring
            self.logger.info(
                "Hardware profile analysis complete",
                extra={
                    'hardware_tier': self._tier,
                    'total_score': score,
                    'score_details': score_details,
                    'cpu_info': self.cpu_info,
                    'memory_info': self.memory_info,
                    'os_info': self.os_info
                }
            )
            
        return self._tier
    
    def get_performance_thresholds(self):
        """Get performance thresholds based on hardware tier with recommendations."""
        tier = self.tier
        
        # Base thresholds
        thresholds = {
            'frame_time_threshold': 33.3,  # 30 FPS
            'memory_threshold_mb': 1024,  # 1GB
            'operation_time_threshold': 0.1,  # 100ms
        }
        
        # Adjust based on tier
        if tier == 'high-end':
            thresholds.update({
                'frame_time_threshold': 16.7,  # 60 FPS
                'memory_threshold_mb': 4096,  # 4GB
                'operation_time_threshold': 0.05,  # 50ms
            })
        elif tier == 'mid-range':
            thresholds.update({
                'frame_time_threshold': 25.0,  # 40 FPS
                'memory_threshold_mb': 2048,  # 2GB
                'operation_time_threshold': 0.075,  # 75ms
            })
        
        # Adjust based on available memory
        available_memory = self.memory_info.get('total', 0) * 1024  # Convert to MB
        if available_memory > 0:
            thresholds['memory_threshold_mb'] = min(
                thresholds['memory_threshold_mb'],
                available_memory * 0.75  # Use up to 75% of available memory
            )
        
        # Generate performance recommendations
        recommendations = self._generate_recommendations(tier, thresholds)
        thresholds['recommendations'] = recommendations
        
        return thresholds
    
    def _generate_recommendations(self, tier, thresholds):
        """Generate hardware-specific performance recommendations."""
        recommendations = []
        
        # CPU recommendations
        if self.cpu_info.get('cores', 0) <= 2:
            recommendations.append({
                'component': 'CPU',
                'type': 'warning',
                'message': 'Limited CPU cores detected. Consider reducing batch transform size.',
                'suggested_action': 'Set batch size to 50 or lower'
            })
        
        # Memory recommendations
        memory_gb = self.memory_info.get('total', 0)
        if memory_gb < 8:
            recommendations.append({
                'component': 'Memory',
                'type': 'warning',
                'message': 'Low system memory. Enable aggressive cleanup.',
                'suggested_action': 'Enable memory_optimization_mode'
            })
        
        # Performance mode recommendations
        if tier == 'low-end':
            recommendations.append({
                'component': 'Performance',
                'type': 'info',
                'message': 'Low-end hardware detected. Enabling performance optimizations.',
                'suggested_actions': [
                    'Reduce viewport quality',
                    'Disable real-time preview',
                    'Enable simplified meshes'
                ]
            })
        elif tier == 'mid-range':
            recommendations.append({
                'component': 'Performance',
                'type': 'info',
                'message': 'Mid-range hardware detected. Balanced optimizations enabled.',
                'suggested_actions': [
                    'Enable dynamic quality scaling',
                    'Use moderate batch sizes',
                    'Enable selective preview updates'
                ]
            })
        
        return recommendations
    
    def log_profile(self):
        """Log detailed hardware profile information."""
        profile_data = {
            'hardware_tier': self.tier,
            'cpu_info': self.cpu_info,
            'memory_info': self.memory_info,
            'os_info': self.os_info,
            'thresholds': self.get_performance_thresholds()
        }
        
        self.logger.info(
            "Hardware Profile Details",
            extra={
                'profile': profile_data,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Log specific warnings or recommendations
        self._log_specific_warnings()
    
    def _log_specific_warnings(self):
        """Log specific warnings based on hardware analysis."""
        # CPU warnings
        if self.cpu_info.get('cores', 0) <= 2:
            self.logger.warning(
                "Low CPU core count detected",
                extra={
                    'cores': self.cpu_info.get('cores', 0),
                    'recommendation': 'Consider reducing parallel operations'
                }
            )
        
        # Memory warnings
        memory_gb = self.memory_info.get('total', 0)
        if memory_gb < 4:
            self.logger.warning(
                "Limited system memory detected",
                extra={
                    'total_gb': memory_gb,
                    'recommendation': 'Enable memory optimization mode'
                }
            )
        
        # Performance mode recommendations
        thresholds = self.get_performance_thresholds()
        self.logger.info(
            "Performance recommendations",
            extra={
                'recommendations': thresholds['recommendations']
            }
        )