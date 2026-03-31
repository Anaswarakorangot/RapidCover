"""
Trigger Engine — the brain of RapidCover's parametric insurance.

Reads data from external_apis.py, applies threshold + duration conditions,
and fires claim events when conditions are sustained past the de minimis rule.

Key design decisions:
  - 45-minute de minimis: events under 45 mins → no payout (IRDAI exclusion)
  - Duration tracking via in-memory dict (active_events)
  - Each poll checks conditions; if threshold breached AND duration met → fire
  - If conditions drop below threshold → clear the event tracker
  - Integrates with existing trigger_detector.py for DB persistence
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.trigger_event import TriggerEvent, TriggerType, TRIGGER_THRESHOLDS
from app.models.zone import Zone
from app.models.partner import Partner
from app.models.policy import Policy
from app.database import SessionLocal
from app.services.external_apis import (
    MockWeatherAPI,
    MockAQIAPI,
    MockPlatformAPI,
    MockCivicAPI,
    get_source_health,
)

logger = logging.getLogger("trigger_engine")

# ─── Thresholds from README ────────────────────────────────────────────────

RAIN_THRESHOLD_MM_HR = 55       # >55mm/hr
HEAT_THRESHOLD_CELSIUS = 43     # >43°C sustained 4+ hrs
AQI_THRESHOLD = 400             # >400 for 3+ hrs
MIN_DURATION_MINUTES = 45       # De minimis exclusion — events < 45 min = no payout

# Per-trigger minimum durations (in minutes)
TRIGGER_MIN_DURATION = {
    "rain":     30,    # 30 mins sustained
    "heat":     240,   # 4 hours
    "aqi":      180,   # 3 hours
    "shutdown": 120,   # 2 hours
    "closure":  90,    # 90 minutes
}

# ─── In-memory tracking of ongoing events ──────────────────────────────────
# Format: { "zone_id:trigger_type": { "start": timestamp, "details": dict } }
active_events: dict[str, dict] = {}

# ─── Trigger log (in-memory ring buffer for admin UI) ──────────────────────
_trigger_log: list[dict] = []
_MAX_LOG_ENTRIES = 200


def _add_log(zone_id: int, zone_code: str, event_type: str, message: str, level: str = "info"):
    """Append to the trigger log ring buffer."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "zone_id": zone_id,
        "zone_code": zone_code,
        "event_type": event_type,
        "message": message,
        "level": level,
    }
    _trigger_log.append(entry)
    # Keep buffer bounded
    if len(_trigger_log) > _MAX_LOG_ENTRIES:
        _trigger_log.pop(0)
    logger.info(f"[{zone_code}] [{event_type}] {message}")


def get_trigger_log(limit: int = 50) -> list[dict]:
    """Return the most recent trigger log entries."""
    return _trigger_log[-limit:]


def get_engine_status() -> dict:
    """Return engine status for admin UI."""
    return {
        "active_events": len(active_events),
        "active_event_keys": list(active_events.keys()),
        "log_entries": len(_trigger_log),
        "data_sources": get_source_health(),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  Main entry point — called by scheduler every 45 seconds
# ═════════════════════════════════════════════════════════════════════════════

def check_all_triggers(force: bool = False, zone_code: str = None):
    """
    Poll all zones (or a specific zone) and check trigger conditions.

    Args:
        force: If True, skip duration requirement (for demo simulation)
        zone_code: If set, only check this specific zone code
    """
    db = SessionLocal()
    try:
        # Get all zones with active policies
        zones = _get_active_zones(db)

        if zone_code:
            zones = [z for z in zones if z.code == zone_code]

        if not zones:
            return

        for zone in zones:
            _check_zone_triggers(zone, db, force=force)

    except Exception as e:
        logger.error(f"[trigger_engine] Error in check_all_triggers: {e}")
    finally:
        db.close()


def _get_active_zones(db: Session) -> list[Zone]:
    """Get all zones that have at least one active policy."""
    now = datetime.utcnow()

    # Get zone IDs with active policies
    zone_ids_with_policies = (
        db.query(Partner.zone_id)
        .join(Policy, Policy.partner_id == Partner.id)
        .filter(
            Partner.is_active == True,
            Partner.zone_id.isnot(None),
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .distinct()
        .all()
    )
    zone_ids = [z[0] for z in zone_ids_with_policies]

    if not zone_ids:
        # If no policies exist, still return all zones (for demo)
        return db.query(Zone).all()

    return db.query(Zone).filter(Zone.id.in_(zone_ids)).all()


def _check_zone_triggers(zone: Zone, db: Session, force: bool = False):
    """Check all trigger types for a single zone."""

    lat = zone.dark_store_lat
    lon = zone.dark_store_lng

    # Fetch current conditions from all data sources
    weather = MockWeatherAPI.get_current(zone.id, lat, lon)
    aqi_data = MockAQIAPI.get_current(zone.id, lat, lon)
    platform = MockPlatformAPI.get_store_status(zone.id)
    shutdown = MockCivicAPI.get_shutdown_status(zone.id)

    # ── Rain ──────────────────────────────────────────────────────────────
    rain_triggered = weather.rainfall_mm_hr >= RAIN_THRESHOLD_MM_HR
    _handle_event(zone, "rain", rain_triggered, db, force, {
        "rainfall_mm_hr": weather.rainfall_mm_hr,
        "threshold": RAIN_THRESHOLD_MM_HR,
        "humidity": weather.humidity,
        "data_source": weather.source,
    })

    # ── Heat ──────────────────────────────────────────────────────────────
    heat_triggered = weather.temp_celsius >= HEAT_THRESHOLD_CELSIUS
    _handle_event(zone, "heat", heat_triggered, db, force, {
        "temp_celsius": round(weather.temp_celsius, 1),
        "threshold": HEAT_THRESHOLD_CELSIUS,
        "data_source": weather.source,
    })

    # ── AQI ───────────────────────────────────────────────────────────────
    aqi_triggered = aqi_data.aqi >= AQI_THRESHOLD
    _handle_event(zone, "aqi", aqi_triggered, db, force, {
        "aqi": aqi_data.aqi,
        "threshold": AQI_THRESHOLD,
        "pm25": aqi_data.pm25,
        "category": aqi_data.category,
        "data_source": aqi_data.source,
    })

    # ── Shutdown ──────────────────────────────────────────────────────────
    shutdown_triggered = shutdown.is_active
    _handle_event(zone, "shutdown", shutdown_triggered, db, force, {
        "reason": shutdown.reason,
        "started_at": shutdown.started_at.isoformat() if shutdown.started_at else None,
        "data_source": shutdown.source,
    })

    # ── Dark store closure ────────────────────────────────────────────────
    closure_triggered = not platform.is_open
    _handle_event(zone, "closure", closure_triggered, db, force, {
        "closure_reason": platform.closure_reason,
        "closed_since": platform.closed_since.isoformat() if platform.closed_since else None,
        "data_source": platform.source,
    })


# ═════════════════════════════════════════════════════════════════════════════
#  Duration enforcement — the 45-minute de minimis rule
# ═════════════════════════════════════════════════════════════════════════════

def _handle_event(
    zone: Zone,
    event_type: str,
    triggered: bool,
    db: Session,
    force: bool,
    details: dict,
):
    """
    Track event duration and fire trigger when minimum duration is met.

    The de minimis rule: events under MIN_DURATION_MINUTES (45 min) produce
    no payout. Each trigger type also has its own minimum from the README.
    """
    key = f"{zone.id}:{event_type}"
    now = time.time()

    if triggered:
        if key not in active_events:
            # Event just started — begin the duration clock
            active_events[key] = {"start": now, "details": details}
            _add_log(zone.id, zone.code, event_type,
                     f"Threshold breached — duration clock started. Details: {_summarize(details)}",
                     "warning")

        else:
            # Event ongoing — check if duration requirement met
            duration_min = (now - active_events[key]["start"]) / 60.0
            min_required = max(
                MIN_DURATION_MINUTES,
                TRIGGER_MIN_DURATION.get(event_type, MIN_DURATION_MINUTES),
            )

            if force or duration_min >= min_required:
                # Duration met (or force-fired for demo) — create trigger event
                _fire_trigger(zone, event_type, duration_min, details, db, force)
                # Remove from tracking so we don't re-fire every poll
                active_events.pop(key, None)
            else:
                remaining = min_required - duration_min
                _add_log(zone.id, zone.code, event_type,
                         f"Duration {duration_min:.0f}m / {min_required:.0f}m required — {remaining:.0f}m remaining",
                         "info")
    else:
        # Event ended — clear tracking
        if key in active_events:
            duration_min = (now - active_events[key]["start"]) / 60.0
            _add_log(zone.id, zone.code, event_type,
                     f"Condition cleared after {duration_min:.0f}m — below threshold, no trigger fired",
                     "info")
            active_events.pop(key, None)


def _fire_trigger(
    zone: Zone,
    event_type: str,
    duration_min: float,
    details: dict,
    db: Session,
    force: bool,
):
    """Create a TriggerEvent in the database and kick off claims processing."""
    from app.services.trigger_detector import _calculate_severity
    from app.services.claims_processor import process_trigger_event

    # Map event type string to TriggerType enum
    type_map = {
        "rain": TriggerType.RAIN,
        "heat": TriggerType.HEAT,
        "aqi": TriggerType.AQI,
        "shutdown": TriggerType.SHUTDOWN,
        "closure": TriggerType.CLOSURE,
    }
    trigger_type = type_map.get(event_type)
    if not trigger_type:
        return

    # Check for duplicate active trigger
    existing = (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == zone.id,
            TriggerEvent.trigger_type == trigger_type,
            TriggerEvent.ended_at.is_(None),
        )
        .first()
    )
    if existing and not force:
        _add_log(zone.id, zone.code, event_type,
                 f"Trigger already active (ID: {existing.id}) — skipping duplicate",
                 "info")
        return

    # Calculate severity
    thresholds = TRIGGER_THRESHOLDS.get(trigger_type, {})
    threshold_val = thresholds.get("threshold", 1)
    actual_val = details.get("rainfall_mm_hr") or details.get("temp_celsius") or details.get("aqi") or 1
    severity = _calculate_severity(actual_val, threshold_val) if threshold_val > 0 else 3

    # Create trigger event
    source_data = {
        **details,
        "duration_minutes": round(duration_min),
        "force_fired": force,
        "engine_version": "v2",
    }

    trigger = TriggerEvent(
        zone_id=zone.id,
        trigger_type=trigger_type,
        started_at=datetime.utcnow() - timedelta(minutes=duration_min),
        severity=severity,
        source_data=json.dumps(source_data),
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)

    _add_log(zone.id, zone.code, event_type,
             f"🔥 TRIGGER FIRED — ID: {trigger.id}, severity: {severity}, duration: {duration_min:.0f}m"
             + (" [FORCE]" if force else ""),
             "critical")

    # Auto-process claims for this trigger
    try:
        claims = process_trigger_event(trigger, db)
        _add_log(zone.id, zone.code, event_type,
                 f"Claims auto-processed: {len(claims)} claims created",
                 "info")
    except Exception as e:
        _add_log(zone.id, zone.code, event_type,
                 f"Error processing claims: {e}",
                 "error")


def _summarize(details: dict) -> str:
    """Create a short summary string from details dict."""
    parts = []
    if "rainfall_mm_hr" in details:
        parts.append(f"rain={details['rainfall_mm_hr']}mm/hr")
    if "temp_celsius" in details:
        parts.append(f"temp={details['temp_celsius']}°C")
    if "aqi" in details:
        parts.append(f"AQI={details['aqi']}")
    if "reason" in details and details["reason"]:
        parts.append(f"reason={details['reason']}")
    if "data_source" in details:
        parts.append(f"src={details['data_source']}")
    return ", ".join(parts) if parts else str(details)
