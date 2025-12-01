"""Centralized logging configuration for the application.

This module provides a single source of truth for logging configuration,
ensuring consistent logging behavior across all modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """Set up logging configuration for the application.
    
    Configures root logger with console handler and optional file handler.
    Uses a clean, readable format suitable for both development and production.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO
        log_file: Optional path to log file. If None, only console logging.
        format_string: Optional custom format string. If None, uses default format.
    
    Returns:
        Configured root logger instance
    
    Example:
        >>> logger = setup_logging(level="INFO")
        >>> logger.info("Application started")
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Default format: timestamp, level, module, message
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    This is a convenience function that returns a logger with the given name.
    The logger will inherit configuration from the root logger.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
    
    Returns:
        Logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(name)


# Initialize logging on module import
# Use INFO level by default, can be overridden via environment variable
import os
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(level=log_level)

