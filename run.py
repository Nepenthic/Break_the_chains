#!/usr/bin/env python3
"""
Entry point for the CAD/CAM program.
"""

import sys
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from main import CADCAMMainWindow

def setup_logging():
    """Configure logging for the application."""
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Add file handler
    fh = logging.FileHandler('cadcam.log')
    fh.setLevel(logging.DEBUG)
    
    # Add console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Create formatters and add them to the handlers
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    fh.setFormatter(file_formatter)
    ch.setFormatter(console_formatter)
    
    # Add handlers to the root logger
    root_logger.addHandler(fh)
    root_logger.addHandler(ch)
    
    return root_logger

def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions."""
    # Log the exception
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Show error dialog to user
    error_msg = f"An error occurred: {str(exc_value)}\n\n"
    error_msg += "Please check cadcam.log for details."
    
    QMessageBox.critical(None, "Error", error_msg)
    
    # Exit the application
    sys.exit(1)

def main():
    """Main entry point."""
    try:
        # Set up logging
        logger = setup_logging()
        logger.info("Starting CAD/CAM application")
        
        # Set up exception handling
        sys.excepthook = handle_exception
        
        # Create application
        app = QApplication(sys.argv)
        
        # Set application style
        app.setStyle('Fusion')
        
        # Create and show main window
        window = CADCAMMainWindow()
        window.show()
        
        logger.info("Application window created and shown")
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        logger.error(traceback.format_exc())
        QMessageBox.critical(None, "Startup Error", 
                           f"Failed to start application: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 