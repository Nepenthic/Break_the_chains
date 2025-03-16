"""
Main entry point for the CAD application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Break the Chains")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Break the Chains Team")
    app.setOrganizationDomain("breakthechains.org")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 