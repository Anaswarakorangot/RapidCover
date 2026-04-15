"""
Time utility functions for Python 3.12+ compatibility.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Return the current UTC time as a timezone-aware datetime object.

    This replaces the deprecated datetime.utcnow() which returns naive datetime objects.

    Returns:
        datetime: Current UTC time with timezone info

    Example:
        >>> from app.utils.time_utils import utcnow
        >>> now = utcnow()
        >>> now.tzinfo  # Will be timezone.utc
    """
    return datetime.now(timezone.utc)
