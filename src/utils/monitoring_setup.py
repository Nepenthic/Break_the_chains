"""
Monitoring setup and configuration script.
Sets up performance monitoring, logging, and alerting for the production environment.
"""

import os
import json
import logging
import psutil
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Configuration constants
MONITORING_CONFIG = {
    'memory': {
        'warning_threshold': 250,  # MB
        'critical_threshold': 300,  # MB
        'check_interval': 60  # seconds
    },
    'render_times': {
        'warning_threshold': 0.1,  # seconds
        'critical_threshold': 0.5,  # seconds
        'sample_size': 100
    },
    'export_times': {
        'warning_threshold': 10,  # seconds
        'critical_threshold': 20,  # seconds
        'by_dataset_size': True
    }
}

ALERT_CONFIG = {
    'email': {
        'enabled': True,
        'recipients': ['team@example.com'],
        'threshold': 'warning'
    },
    'logging': {
        'enabled': True,
        'path': 'logs/alerts.log',
        'rotation': '1 day'
    },
    'dashboard': {
        'enabled': True,
        'update_interval': 5  # seconds
    }
}

class MonitoringSetup:
    """Sets up and configures the monitoring system."""

    def __init__(self):
        """Initialize monitoring setup."""
        self.base_dir = Path.cwd()
        self.logs_dir = self.base_dir / 'logs'
        self.config_dir = self.base_dir / 'config'
        self.setup_directories()
        self.setup_logging()

    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.logs_dir,
            self.config_dir,
            self.logs_dir / 'performance',
            self.logs_dir / 'errors',
            self.logs_dir / 'alerts'
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        """Configure logging for different components."""
        # Performance logging
        perf_logger = logging.getLogger('performance')
        perf_handler = RotatingFileHandler(
            self.logs_dir / 'performance/metrics.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        perf_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        perf_handler.setFormatter(perf_formatter)
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)

        # Error logging
        error_logger = logging.getLogger('errors')
        error_handler = RotatingFileHandler(
            self.logs_dir / 'errors/error.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
            'Exception: %(exc_info)s'
        )
        error_handler.setFormatter(error_formatter)
        error_logger.addHandler(error_handler)
        error_logger.setLevel(logging.ERROR)

        # Alert logging
        alert_logger = logging.getLogger('alerts')
        alert_handler = RotatingFileHandler(
            self.logs_dir / 'alerts/alert.log',
            maxBytes=5*1024*1024,
            backupCount=3
        )
        alert_formatter = logging.Formatter(
            '%(asctime)s - ALERT - %(levelname)s - %(message)s'
        )
        alert_handler.setFormatter(alert_formatter)
        alert_logger.addHandler(alert_handler)
        alert_logger.setLevel(logging.WARNING)

    def save_configs(self):
        """Save monitoring and alert configurations."""
        config_files = {
            'monitoring_config.json': MONITORING_CONFIG,
            'alert_config.json': ALERT_CONFIG
        }
        for filename, config in config_files.items():
            with open(self.config_dir / filename, 'w') as f:
                json.dump(config, f, indent=2)

    def verify_system_resources(self):
        """Verify system resources meet requirements."""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_count = psutil.cpu_count()

        requirements_met = True
        issues = []

        # Check memory
        if memory.available < 512 * 1024 * 1024:  # 512MB
            requirements_met = False
            issues.append("Insufficient memory available")

        # Check disk space
        if disk.free < 1024 * 1024 * 1024:  # 1GB
            requirements_met = False
            issues.append("Insufficient disk space")

        # Check CPU cores
        if cpu_count < 2:
            requirements_met = False
            issues.append("Insufficient CPU cores")

        return requirements_met, issues

    def setup_monitoring(self):
        """Set up the complete monitoring system."""
        try:
            # Verify system resources
            requirements_met, issues = self.verify_system_resources()
            if not requirements_met:
                raise RuntimeError(f"System requirements not met: {', '.join(issues)}")

            # Create directories
            self.setup_directories()

            # Configure logging
            self.setup_logging()

            # Save configurations
            self.save_configs()

            # Log successful setup
            logging.getLogger('performance').info("Monitoring system setup complete")
            return True, "Monitoring system setup successfully"

        except Exception as e:
            error_msg = f"Failed to set up monitoring system: {str(e)}"
            logging.getLogger('errors').error(error_msg, exc_info=True)
            return False, error_msg

def main():
    """Main entry point for monitoring setup."""
    setup = MonitoringSetup()
    success, message = setup.setup_monitoring()
    
    if success:
        print("✓ Monitoring system setup complete")
        print("  - Logging configured")
        print("  - Configurations saved")
        print("  - System resources verified")
    else:
        print("✗ Monitoring system setup failed")
        print(f"  Error: {message}")
        exit(1)

if __name__ == '__main__':
    main() 