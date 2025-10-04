"""
Centralized Logging Configuration for Multi-Material Printer Controllers

Provides flexible logging configuration with support for:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Multiple output destinations (console, file, web streaming)
- Component-specific logging controls
- Real-time log level adjustment
- Structured log formatting

Usage:
    from logging_config import setup_logging, get_logger, set_log_level

    # Setup logging for a component
    logger = setup_logging('print_manager', level='INFO')

    # Get configured logger
    logger = get_logger('pump_control')

    # Change log level at runtime
    set_log_level('mmu_control', 'DEBUG')
"""

import logging
import logging.handlers
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Union

# Global configuration
_LOG_CONFIG = {
    'levels': {
        'print_manager': 'INFO',
        'mmu_control': 'INFO',
        'pump_control': 'INFO',
        'printer_comms': 'INFO',
        'web_interface': 'INFO'
    },
    'outputs': {
        'console': True,
        'file': False,
        'web_stream': True
    },
    'format': {
        'console': '[%(asctime)s] %(name)s.%(levelname)s: %(message)s',
        'file': '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        'web': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    },
    'file_config': {
        'max_size_mb': 10,
        'backup_count': 5,
        'log_dir': None  # Will be set to config directory
    }
}

_LOGGERS: Dict[str, logging.Logger] = {}
_WEB_LOG_HANDLER = None

class WebSocketLogHandler(logging.Handler):
    """Custom log handler that can send logs to web interface via callback"""

    def __init__(self, callback=None):
        super().__init__()
        self.callback = callback
        self.log_buffer = []
        self.max_buffer_size = 1000

    def emit(self, record):
        try:
            msg = self.format(record)

            # Add to buffer
            self.log_buffer.append({
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': msg
            })

            # Trim buffer if needed
            if len(self.log_buffer) > self.max_buffer_size:
                self.log_buffer.pop(0)

            # Send to web interface if callback available
            if self.callback:
                self.callback(record.levelname.lower(), msg)

        except Exception:
            self.handleError(record)

    def get_recent_logs(self, count=100):
        """Get recent log entries for web interface"""
        return self.log_buffer[-count:]

    def set_callback(self, callback):
        """Set callback function for real-time log streaming"""
        self.callback = callback

def load_config():
    """Load logging configuration from file if available"""
    global _LOG_CONFIG

    try:
        # Try to load from config directory
        config_path = get_config_dir() / 'logging_config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                stored_config = json.load(f)
                _LOG_CONFIG.update(stored_config)
                print(f"Loaded logging config from {config_path}")
    except Exception as e:
        print(f"Could not load logging config: {e}, using defaults")

def save_config():
    """Save current logging configuration to file"""
    try:
        config_path = get_config_dir() / 'logging_config.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(_LOG_CONFIG, f, indent=2)

    except Exception as e:
        print(f"Could not save logging config: {e}")

def get_config_dir():
    """Get configuration directory path"""
    # Try to find config directory relative to this file
    current_dir = Path(__file__).parent

    # Look for config directory at repository root
    for parent in [current_dir, current_dir.parent, current_dir.parent.parent]:
        config_dir = parent / 'config'
        if config_dir.exists():
            return config_dir

    # Fallback to creating config in current directory
    config_dir = current_dir / 'config'
    config_dir.mkdir(exist_ok=True)
    return config_dir

def setup_logging(component_name: str, level: Optional[str] = None,
                 console: Optional[bool] = None,
                 file_output: Optional[bool] = None) -> logging.Logger:
    """
    Setup logging for a component with flexible configuration

    Args:
        component_name: Name of the component (e.g., 'print_manager')
        level: Log level override for this component
        console: Enable/disable console output for this component
        file_output: Enable/disable file output for this component

    Returns:
        Configured logger instance
    """
    global _WEB_LOG_HANDLER

    # Load configuration if not already done
    if not _LOG_CONFIG.get('_loaded'):
        load_config()
        _LOG_CONFIG['_loaded'] = True

    # Create logger
    logger = logging.getLogger(component_name)
    logger.handlers.clear()  # Remove any existing handlers

    # Set log level
    log_level = level or _LOG_CONFIG['levels'].get(component_name, 'INFO')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Console handler
    if console is not False and _LOG_CONFIG['outputs']['console']:
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = logging.Formatter(_LOG_CONFIG['format']['console'])
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    # File handler
    if (file_output or _LOG_CONFIG['outputs']['file']):
        try:
            log_dir = Path(_LOG_CONFIG['file_config']['log_dir'] or get_config_dir())
            log_dir.mkdir(exist_ok=True)

            log_file = log_dir / f'{component_name}.log'
            max_size = _LOG_CONFIG['file_config']['max_size_mb'] * 1024 * 1024
            backup_count = _LOG_CONFIG['file_config']['backup_count']

            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_size, backupCount=backup_count
            )
            file_format = logging.Formatter(_LOG_CONFIG['format']['file'])
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

        except Exception as e:
            print(f"Could not setup file logging for {component_name}: {e}")

    # Web streaming handler (shared across all loggers)
    if _LOG_CONFIG['outputs']['web_stream']:
        if _WEB_LOG_HANDLER is None:
            _WEB_LOG_HANDLER = WebSocketLogHandler()
            web_format = logging.Formatter(_LOG_CONFIG['format']['web'])
            _WEB_LOG_HANDLER.setFormatter(web_format)

        logger.addHandler(_WEB_LOG_HANDLER)

    # Store logger reference
    _LOGGERS[component_name] = logger

    logger.info(f"Logging initialized for {component_name} (level: {log_level})")
    return logger

def get_logger(component_name: str) -> logging.Logger:
    """Get existing logger or create new one with default settings"""
    if component_name in _LOGGERS:
        return _LOGGERS[component_name]
    else:
        return setup_logging(component_name)

def set_log_level(component_name: str, level: str):
    """Change log level for a component at runtime"""
    if component_name in _LOGGERS:
        logger = _LOGGERS[component_name]
        logger.setLevel(getattr(logging, level.upper()))
        _LOG_CONFIG['levels'][component_name] = level.upper()
        logger.info(f"Log level changed to {level.upper()}")
    else:
        _LOG_CONFIG['levels'][component_name] = level.upper()

def set_web_callback(callback):
    """Set callback function for web log streaming"""
    global _WEB_LOG_HANDLER
    if _WEB_LOG_HANDLER:
        _WEB_LOG_HANDLER.set_callback(callback)

def get_recent_logs(count=100):
    """Get recent log entries for web interface"""
    global _WEB_LOG_HANDLER
    if _WEB_LOG_HANDLER:
        return _WEB_LOG_HANDLER.get_recent_logs(count)
    return []

def configure_logging(config_dict: dict):
    """Update logging configuration with new settings"""
    global _LOG_CONFIG
    _LOG_CONFIG.update(config_dict)
    save_config()

    # Reconfigure existing loggers
    for component_name in _LOGGERS:
        setup_logging(component_name)

def get_logging_config():
    """Get current logging configuration"""
    return _LOG_CONFIG.copy()

# Convenience functions for common log patterns
def log_function_entry(logger, func_name, **kwargs):
    """Log function entry with parameters"""
    if logger.isEnabledFor(logging.DEBUG):
        params = ', '.join(f'{k}={v}' for k, v in kwargs.items())
        logger.debug(f"→ {func_name}({params})")

def log_function_exit(logger, func_name, result=None):
    """Log function exit with result"""
    if logger.isEnabledFor(logging.DEBUG):
        if result is not None:
            logger.debug(f"← {func_name} → {result}")
        else:
            logger.debug(f"← {func_name}")

def log_error_with_traceback(logger, error, context=""):
    """Log error with full traceback information"""
    import traceback
    logger.error(f"{context}Error: {error}")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Traceback:\n{traceback.format_exc()}")

# Initialize default configuration
load_config()