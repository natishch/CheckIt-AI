"""Structured logging configuration for check-it-ai application."""

import logging
import sys
from typing import Any

from src.check_it_ai.config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter that adds structured information to log records."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Add custom fields if they exist
        extras = []
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                extras.append(f"{key}={value}")

        # Build log message
        base_msg = super().format(record)
        if extras:
            return f"{base_msg} | {' '.join(extras)}"
        return base_msg


def setup_logger(
    name: str,
    level: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """Set up a logger with structured formatting.

    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses settings.log_level
        format_string: Custom format string. If None, uses default format

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set level
    log_level = level or settings.log_level
    logger.setLevel(getattr(logging, log_level.upper()))

    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    if format_string is None:
        format_string = (
            "%(asctime)s | %(name)s | %(levelname)s | "
            "%(filename)s:%(lineno)d | %(message)s"
        )

    formatter = StructuredFormatter(
        format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context: Any,
) -> None:
    """Log a message with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields to include in log
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra=context)


# Create default application logger
app_logger = setup_logger("check_it_ai")
