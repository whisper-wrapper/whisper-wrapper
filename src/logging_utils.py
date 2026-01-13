"""Logging configuration for Whisper GUI Wrapper."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import LOG_DIR, APP_NAME

# Log format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log file settings
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configure application logging.

    Args:
        debug: Enable debug level logging

    Returns:
        Root logger for the application
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Create root logger
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)

    # File handler with rotation
    log_file = LOG_DIR / f"{APP_NAME}.log"
    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        logger.warning(f"Could not create log file: {e}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name under the app namespace.

    Args:
        name: Logger name (will be prefixed with app name)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"{APP_NAME}.{name}")


def get_log_file_path() -> Path:
    """Get the path to the current log file."""
    return LOG_DIR / f"{APP_NAME}.log"
