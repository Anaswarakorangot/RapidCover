"""
Verification Service — System health checks for admin dashboard.

Provides comprehensive health checks for all system components:
- Auth endpoint
- Zone list
- Trigger engine
- Simulation (mock APIs)
- Claim creation
- Payout service
- Push notifications
"""

import time
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.drill import VerificationCheck
from app.config import get_settings


def _timed_check(check_fn) -> tuple[bool, str, int]:
    """Run a check function and return (success, message, latency_ms)."""
    start = time.time()
    try:
        success, message = check_fn()
        latency = int((time.time() - start) * 1000)
        return success, message, latency
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return False, f"Exception: {str(e)}", latency


def check_auth_endpoint(db: Session) -> tuple[bool, str]:
    """Verify auth/partner endpoints are reachable."""
    from app.models.partner import Partner

    # Simple DB query to ensure connection works
    try:
        count = db.query(Partner).limit(1).count()
        return True, f"Partner table accessible, {count} sample records"
    except Exception as e:
        return False, f"Database error: {str(e)}"


def check_zone_list(db: Session) -> tuple[bool, str]:
    """Verify zones endpoint returns data."""
    from app.models.zone import Zone

    try:
        zones = db.query(Zone).all()
        if len(zones) == 0:
            return False, "No zones found in database"
        return True, f"Found {len(zones)} zones"
    except Exception as e:
        return False, f"Zone query error: {str(e)}"


def check_trigger_engine(db: Session) -> tuple[bool, str]:
    """Verify trigger engine is operational."""
    try:
        from app.services.trigger_engine import get_engine_status
        from app.services.scheduler import get_scheduler_status

        engine = get_engine_status()
        scheduler = get_scheduler_status()

        if not scheduler.get("running", False):
            return False, "Scheduler not running"

        return True, f"Engine active with {engine['active_events']} events, {engine['log_entries']} log entries"
    except Exception as e:
        return False, f"Engine check error: {str(e)}"


def check_simulation(db: Session) -> tuple[bool, str]:
    """Verify mock APIs are injectable."""
    try:
        from app.services.external_apis import (
            MockWeatherAPI,
            MockAQIAPI,
            MockPlatformAPI,
            MockCivicAPI,
            _get_zone_conditions,
        )

        # Test weather injection
        MockWeatherAPI.set_conditions(
            zone_id=9999,  # Test zone
            temp_celsius=35.0,
            rainfall_mm_hr=0.0,
        )

        # Verify it was set in internal state
        # (get_current may use live API if configured)
        conditions = _get_zone_conditions(9999)
        if conditions['weather']['temp'] != 35.0:
            return False, "Weather injection failed"

        # Reset
        MockWeatherAPI.set_conditions(9999, temp_celsius=32.0, rainfall_mm_hr=0.0)

        return True, "Mock APIs injectable and working"
    except Exception as e:
        return False, f"Simulation check error: {str(e)}"


def check_claim_creation(db: Session) -> tuple[bool, str]:
    """Verify claims processor is available."""
    try:
        from app.services.claims_processor import (
            get_eligible_policies,
            calculate_payout_amount,
        )

        # Test function availability
        _ = get_eligible_policies
        _ = calculate_payout_amount

        return True, "Claims processor functions available"
    except ImportError as e:
        return False, f"Claims processor import error: {str(e)}"
    except Exception as e:
        return False, f"Claims check error: {str(e)}"


def check_payout_service(db: Session) -> tuple[bool, str]:
    """Verify payout service (UPI/Razorpay) is configured."""
    settings = get_settings()

    try:
        from app.services.payout_service import process_payout

        # Check if Razorpay keys are configured
        has_razorpay = bool(settings.razorpay_key_id and settings.razorpay_key_secret)

        if has_razorpay:
            return True, "Razorpay credentials configured"
        else:
            return True, "Payout service available (mock mode - no Razorpay keys)"
    except ImportError as e:
        return False, f"Payout service import error: {str(e)}"
    except Exception as e:
        return False, f"Payout check error: {str(e)}"


def check_push_notifications(db: Session) -> tuple[bool, str]:
    """Verify VAPID keys are configured for push notifications."""
    settings = get_settings()

    try:
        has_vapid = bool(settings.vapid_private_key and settings.vapid_public_key)

        if has_vapid:
            # Verify keys are valid format
            from app.services.notifications import send_push_notification
            return True, "VAPID keys configured"
        else:
            return False, "VAPID keys not configured - push notifications disabled"
    except ImportError as e:
        return False, f"Notifications import error: {str(e)}"
    except Exception as e:
        return False, f"Push notification check error: {str(e)}"


def check_database_connection(db: Session) -> tuple[bool, str]:
    """Verify database connection is healthy."""
    try:
        # Execute a simple query
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            return True, "Database connection healthy"
        return False, "Database query returned unexpected result"
    except Exception as e:
        return False, f"Database connection error: {str(e)}"


def check_data_sources(db: Session) -> tuple[bool, str]:
    """Check external data source health."""
    try:
        from app.services.external_apis import get_source_health

        health = get_source_health()
        live_count = sum(1 for s in health.values() if s["status"] == "live")
        mock_count = sum(1 for s in health.values() if s["status"] == "mock")

        return True, f"Data sources: {live_count} live, {mock_count} mock"
    except Exception as e:
        return False, f"Data source check error: {str(e)}"


def check_insurer_intelligence(db: Session) -> tuple[bool, str]:
    """Check that insurer intelligence predictions exist or can be generated."""
    try:
        from datetime import timedelta
        from app.models.prediction import WeeklyPrediction, CityRiskProfile

        now = datetime.utcnow()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Check for recent predictions
        prediction_count = (
            db.query(WeeklyPrediction)
            .filter(WeeklyPrediction.week_start == week_start)
            .count()
        )

        profile_count = (
            db.query(CityRiskProfile)
            .filter(CityRiskProfile.week_start == week_start)
            .count()
        )

        if prediction_count > 0 and profile_count > 0:
            return True, f"Intelligence active: {prediction_count} zone predictions, {profile_count} city profiles"

        # Try to generate predictions
        from app.services.prediction_service import (
            generate_weekly_predictions,
            generate_city_risk_profiles,
        )

        predictions = generate_weekly_predictions(db)
        profiles = generate_city_risk_profiles(db)

        return True, f"Intelligence initialized: {len(predictions)} predictions, {len(profiles)} profiles"
    except Exception as e:
        return False, f"Intelligence check error: {str(e)}"


# Health check registry
HEALTH_CHECKS = [
    ("database", check_database_connection),
    ("auth_endpoint", check_auth_endpoint),
    ("zone_list", check_zone_list),
    ("trigger_engine", check_trigger_engine),
    ("simulation", check_simulation),
    ("claim_creation", check_claim_creation),
    ("payout_service", check_payout_service),
    ("push_notifications", check_push_notifications),
    ("data_sources", check_data_sources),
    ("insurer_intelligence", check_insurer_intelligence),
]


def run_all_checks(db: Session) -> list[VerificationCheck]:
    """Run all health checks and return results."""
    results = []

    for name, check_fn in HEALTH_CHECKS:
        success, message, latency = _timed_check(lambda fn=check_fn: fn(db))

        status = "pass" if success else "fail"

        # Special handling: push notifications without VAPID is a "skip" not "fail"
        if name == "push_notifications" and "not configured" in message:
            status = "skip"

        results.append(VerificationCheck(
            name=name,
            status=status,
            message=message,
            latency_ms=latency,
        ))

    return results


def run_single_check(name: str, db: Session) -> Optional[VerificationCheck]:
    """Run a single health check by name."""
    for check_name, check_fn in HEALTH_CHECKS:
        if check_name == name:
            success, message, latency = _timed_check(lambda: check_fn(db))
            return VerificationCheck(
                name=name,
                status="pass" if success else "fail",
                message=message,
                latency_ms=latency,
            )
    return None
