"""Production logging configuration with structured logging and rotation."""

import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
import json

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record):
        """Format log record with additional structured data."""
        # Get the original format
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'extra'):
            log_obj['extra'] = record.extra
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)

def setup_production_logging(log_dir: str = 'logs'):
    """Set up production logging configuration."""
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create handlers
    handlers = {
        # Main application log with rotation
        'app': logging.handlers.RotatingFileHandler(
            filename=log_path / 'app.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        ),
        # Performance metrics log
        'performance': logging.handlers.RotatingFileHandler(
            filename=log_path / 'performance.log',
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5
        ),
        # Error log
        'error': logging.handlers.RotatingFileHandler(
            filename=log_path / 'error.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        ),
        # Console output for critical issues
        'console': logging.StreamHandler()
    }
    
    # Configure formatters
    structured_formatter = StructuredFormatter()
    for handler in handlers.values():
        handler.setFormatter(structured_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Add handlers to root logger
    for handler in handlers.values():
        root_logger.addHandler(handler)
    
    # Configure specific loggers
    loggers = {
        'performance': {
            'level': logging.INFO,
            'handlers': ['performance', 'console'],
            'propagate': False
        },
        'error': {
            'level': logging.ERROR,
            'handlers': ['error', 'console'],
            'propagate': True
        },
        'state': {
            'level': logging.INFO,
            'handlers': ['app'],
            'propagate': True
        }
    }
    
    for logger_name, config in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(config['level'])
        logger.propagate = config['propagate']
        
        # Remove existing handlers
        logger.handlers = []
        
        # Add configured handlers
        for handler_name in config['handlers']:
            logger.addHandler(handlers[handler_name])
    
    # Log initial setup
    logging.info('Production logging configured', extra={
        'log_dir': str(log_path),
        'handlers': list(handlers.keys()),
        'loggers': list(loggers.keys())
    })

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name) 