"""
Centralized logging configuration for BESS Sizing Tool

Provides consistent logging across all modules with appropriate formatting,
log levels, and output handling. Supports both console and file logging.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Default log directory
LOG_DIR = Path("logs")


def setup_logger(name, level=logging.INFO, log_to_file=True):
    """
    Set up a logger with consistent formatting.

    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Logging level (default: logging.INFO)
        log_to_file: Whether to also log to a file (default: True)

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

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create file handler for persistent logging
    if log_to_file:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LOG_DIR / f"bess_sizing_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # If we can't write to log file, continue with console-only logging
            logger.warning(f"Could not create log file: {e}. Continuing with console-only logging.")

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
