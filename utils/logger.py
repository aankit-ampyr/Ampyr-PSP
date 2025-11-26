"""
Centralized logging configuration for BESS Sizing Tool

Provides consistent logging across all modules with appropriate formatting,
log levels, and output handling.
"""

import logging
import sys
from pathlib import Path


def setup_logger(name, level=logging.INFO):
    """
    Set up a logger with consistent formatting.

    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Logging level (default: logging.INFO)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        >>> from utils.logger import setup_logger
        >>> logger = setup_logger(__name__)
        >>> logger.info("Application started")
        >>> logger.warning("Configuration issue detected")
        >>> logger.error("Failed to load data file")
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger


def get_logger(name):
    """
    Get a logger instance (shorthand for setup_logger).

    Args:
        name: Logger name (typically __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return setup_logger(name)


# Module-level logger for this utility
logger = setup_logger(__name__)
