import logging
import os
import time
from datetime import datetime

class TransformLogger:
    """Logger for transform operations with detailed metrics."""
    
    def __init__(self, log_file):
        self.logger = logging.getLogger('transform_system')
        self.logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # File handler with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(
            f'logs/{timestamp}_{log_file}'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message, extra=None):
        """Log info message with optional extra data."""
        self._log(logging.INFO, message, extra)
    
    def debug(self, message, extra=None):
        """Log debug message with optional extra data."""
        self._log(logging.DEBUG, message, extra)
    
    def warning(self, message, extra=None):
        """Log warning message with optional extra data."""
        self._log(logging.WARNING, message, extra)
    
    def error(self, message, extra=None):
        """Log error message with optional extra data."""
        self._log(logging.ERROR, message, extra)
    
    def _log(self, level, message, extra=None):
        """Internal method to handle logging with extra data."""
        if extra:
            message = f"{message} - Extra Data: {extra}"
        self.logger.log(level, message) 