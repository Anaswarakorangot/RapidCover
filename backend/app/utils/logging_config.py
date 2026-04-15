"""
Structured Logging Configuration (Phase 4)

JSON logging for production debugging and monitoring.
"""
import logging
import json
import sys
from datetime import datetime
from app.utils.time_utils import utcnow


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs logs in JSON format for easy parsing by log aggregators
    (ELK, CloudWatch, Datadog, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", json_format: bool = False):
    """
    Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON formatter; if False, use standard formatter

    Example:
        # For development (human-readable)
        setup_logging("DEBUG", json_format=False)

        # For production (JSON for log aggregators)
        setup_logging("INFO", json_format=True)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        # Standard formatter for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root_logger


# Convenience function for adding structured data to logs
def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    Log a message with additional context fields.

    Example:
        log_with_context(
            logger,
            "INFO",
            "Policy created",
            partner_id=123,
            policy_id=456,
            tier="standard"
        )
    """
    extra = {"extra_fields": kwargs}
    logger.log(getattr(logging, level.upper()), message, extra=extra)
