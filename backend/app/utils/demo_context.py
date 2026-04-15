"""
Demo Context Manager for Drill Isolation

Provides context managers for temporarily enabling demo mode during drill execution.
This ensures drills use mock data without affecting production state.
"""
from contextlib import contextmanager
from app.config import get_settings


@contextmanager
def drill_mode():
    """
    Temporarily enable demo mode for drill execution.

    This context manager ensures that drill simulations always use mock data
    by temporarily enabling settings.demo_mode. After the drill completes,
    the original demo_mode setting is restored.

    Usage:
        with drill_mode():
            check_all_triggers(force=True, zone_code=zone.code)

    Example:
        # Before entering context: demo_mode = False (production mode)
        with drill_mode():
            # Inside context: demo_mode = True (drill mode)
            simulate_weather_event()
        # After exiting context: demo_mode = False (restored)
    """
    settings = get_settings()
    original = settings.demo_mode

    try:
        settings.demo_mode = True
        yield
    finally:
        settings.demo_mode = original


@contextmanager
def production_mode():
    """
    Temporarily disable demo mode to force live API usage.

    This is the inverse of drill_mode() - it ensures live data is used
    even if demo_mode is globally enabled.

    Usage:
        with production_mode():
            # Force live API call even if demo_mode is True
            live_weather = MockWeatherAPI.get_current(zone_id)
    """
    settings = get_settings()
    original = settings.demo_mode

    try:
        settings.demo_mode = False
        yield
    finally:
        settings.demo_mode = original
