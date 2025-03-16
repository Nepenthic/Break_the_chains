"""Main application entry point."""

from PyQt6.QtWidgets import QApplication
import sys
import os
from pathlib import Path
from .utils.logging_config import setup_production_logging, get_logger
from .viewport import Viewport
from .transform_tab import TransformTab
from .utils.state_management import TransformStateManager
from .utils.hardware_profile import HardwareProfile

def setup_production_environment():
    """Set up the production environment."""
    # Create necessary directories
    dirs = ['logs', 'checkpoints', 'reports']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    
    # Set up logging
    setup_production_logging()
    logger = get_logger('main')
    
    # Log environment setup
    logger.info('Production environment initialized', extra={
        'directories_created': dirs,
        'python_version': sys.version,
        'qt_version': QApplication.instance().applicationVersion()
    })
    
    return logger

def main():
    """Main application entry point."""
    # Initialize production environment
    logger = setup_production_environment()
    
    try:
        # Create application instance
        app = QApplication(sys.argv)
        app.setApplicationName('Transform System')
        app.setApplicationVersion('1.0.0')
        
        # Initialize hardware profile
        hardware_profile = HardwareProfile.detect()
        hardware_profile.log_profile()
        
        # Create main window and components
        viewport = Viewport()
        transform_tab = TransformTab()
        state_manager = TransformStateManager(transform_tab, viewport)
        
        # Log successful initialization
        logger.info('Application components initialized', extra={
            'hardware_tier': hardware_profile.tier,
            'viewport_quality': viewport.current_quality_level,
            'batch_size': state_manager.current_batch_size
        })
        
        # Start application
        viewport.show()
        transform_tab.show()
        
        # Enter event loop
        return app.exec()
        
    except Exception as e:
        logger.error('Application startup failed', exc_info=True, extra={
            'error_type': type(e).__name__,
            'error_message': str(e)
        })
        raise

if __name__ == '__main__':
    sys.exit(main()) 