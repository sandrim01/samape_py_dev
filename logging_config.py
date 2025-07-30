"""
Logging configuration for the SAMAPE application.
"""
import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging(app):
    """Configure logging for the application."""
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(app.root_path, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure log level based on environment
    if app.config.get('FLASK_ENV') == 'production':
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s:%(lineno)d: %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Configure main application logger
    app.logger.setLevel(log_level)
    
    # File handler for general logs
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(logs_dir, 'samape.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    
    # File handler for errors only
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(logs_dir, 'samape_errors.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Console handler for development
    if not app.config.get('FLASK_ENV') == 'production':
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        app.logger.addHandler(console_handler)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    
    # Log application startup
    app.logger.info(f"SAMAPE application started - Environment: {app.config.get('FLASK_ENV', 'development')}")
    
    return app.logger

def get_logger(name):
    """Get a logger for a specific module."""
    return logging.getLogger(name)
