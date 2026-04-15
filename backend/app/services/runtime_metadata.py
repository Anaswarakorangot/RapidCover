import json
import logging
from datetime import datetime, time, timedelta
from typing import Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy.sql import text, func

from app.models.partner import Partner
from app.utils.time_utils import utcnow

logger = logging.getLogger("runtime_metadata")

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
UNSET = object()

def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetimes stored in auxiliary metadata tables."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

def _parse_shift_time(value: Optional[str]) -> Optional[time]:
    """Parse HH:MM strings used in partner shift preferences."""
    if not value:
        return None
    try:
        hour, minute = value.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except (ValueError, AttributeError):
        return None

# --- DB Table Management ---

def _ensure_partner_runtime_metadata_table(db: Session) -> None:
    """Create the partner runtime metadata table if it does not exist yet."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS partner_runtime_metadata (
            partner_id INTEGER PRIMARY KEY,
            pin_code TEXT NULL,
            is_manual_offline INTEGER NOT NULL DEFAULT 0,
            manual_offline_until TEXT NULL,
            leave_until TEXT NULL,
            leave_note TEXT NULL,
            updated_at TEXT NOT NULL
        )
    """))
    db.commit()

def _ensure_zone_coverage_metadata_table(db: Session) -> None:
    """Create the zone coverage metadata table if it does not exist yet."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS zone_coverage_metadata (
            zone_id INTEGER PRIMARY KEY,
            pin_codes_json TEXT NULL,
            density_weight REAL NULL,
            ward_name TEXT NULL,
            updated_at TEXT NOT NULL
        )
    """))
    db.commit()

def _ensure_partner_platform_activity_table(db: Session) -> None:
    """Create the partner platform activity table if it does not exist yet."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS partner_platform_activity (
            partner_id INTEGER PRIMARY KEY,
            platform_logged_in INTEGER NOT NULL DEFAULT 1,
            active_shift INTEGER NOT NULL DEFAULT 1,
            orders_accepted_recent INTEGER NOT NULL DEFAULT 5,
            orders_completed_recent INTEGER NOT NULL DEFAULT 4,
            last_app_ping TEXT NOT NULL,
            zone_dwell_minutes INTEGER NOT NULL DEFAULT 60,
            suspicious_inactivity INTEGER NOT NULL DEFAULT 0,
            platform TEXT NOT NULL DEFAULT 'zomato',
            updated_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'simulated'
        )
    """))
    db.commit()

# --- Partner Runtime Metadata ---

def get_partner_runtime_metadata(partner_id: int, db: Session) -> dict:
    """Fetch persisted partner runtime metadata used by the claims engine."""
    _ensure_partner_runtime_metadata_table(db)
    row = db.execute(
        text("""
            SELECT partner_id, pin_code, is_manual_offline, manual_offline_until, leave_until, leave_note, updated_at
            FROM partner_runtime_metadata
            WHERE partner_id = :partner_id
        """),
        {"partner_id": partner_id},
    ).mappings().first()

    if not row:
        return {
            "partner_id": partner_id,
            "pin_code": None,
            "is_manual_offline": False,
            "manual_offline_until": None,
            "leave_until": None,
            "leave_note": None,
            "updated_at": None,
        }

    return {
        "partner_id": row["partner_id"],
        "pin_code": row["pin_code"],
        "is_manual_offline": bool(row["is_manual_offline"]),
        "manual_offline_until": _parse_iso_datetime(row["manual_offline_until"]),
        "leave_until": _parse_iso_datetime(row["leave_until"]),
        "leave_note": row["leave_note"],
        "updated_at": _parse_iso_datetime(row["updated_at"]),
    }

def upsert_partner_runtime_metadata(
    partner_id: int,
    db: Session,
    *,
    pin_code: Optional[str] = UNSET,
    is_manual_offline: Optional[bool] = UNSET,
    manual_offline_until: Optional[datetime] = UNSET,
    leave_until: Optional[datetime] = UNSET,
    leave_note: Optional[str] = UNSET,
) -> dict:
    """Create or update partner runtime metadata."""
    _ensure_partner_runtime_metadata_table(db)
    existing = get_partner_runtime_metadata(partner_id, db)

    payload = {
        "partner_id": partner_id,
        "pin_code": existing["pin_code"] if pin_code is UNSET else pin_code,
        "is_manual_offline": int(existing["is_manual_offline"] if is_manual_offline is UNSET else is_manual_offline),
        "manual_offline_until": (
            existing["manual_offline_until"].isoformat() if existing["manual_offline_until"] else None
        ) if manual_offline_until is UNSET else (
            manual_offline_until.isoformat() if manual_offline_until is not None else None
        ),
        "leave_until": (
            existing["leave_until"].isoformat() if existing["leave_until"] else None
        ) if leave_until is UNSET else (
            leave_until.isoformat() if leave_until is not None else None
        ),
        "leave_note": existing["leave_note"] if leave_note is UNSET else leave_note,
        "updated_at": utcnow().isoformat(),
    }

    if is_manual_offline is False and manual_offline_until is UNSET:
        payload["manual_offline_until"] = None

    db.execute(
        text("""
            INSERT INTO partner_runtime_metadata (
                partner_id, pin_code, is_manual_offline, manual_offline_until, leave_until, leave_note, updated_at
            ) VALUES (
                :partner_id, :pin_code, :is_manual_offline, :manual_offline_until, :leave_until, :leave_note, :updated_at
            )
            ON CONFLICT(partner_id) DO UPDATE SET
                pin_code = excluded.pin_code,
                is_manual_offline = excluded.is_manual_offline,
                manual_offline_until = excluded.manual_offline_until,
                leave_until = excluded.leave_until,
                leave_note = excluded.leave_note,
                updated_at = excluded.updated_at
        """),
        payload,
    )
    db.commit()
    return get_partner_runtime_metadata(partner_id, db)

# --- Zone Coverage Metadata ---

def get_zone_coverage_metadata(zone_id: int, db: Session) -> dict:
    """Fetch persisted pin-code and density metadata for a zone."""
    _ensure_zone_coverage_metadata_table(db)
    row = db.execute(
        text("""
            SELECT zone_id, pin_codes_json, density_weight, ward_name, updated_at
            FROM zone_coverage_metadata
            WHERE zone_id = :zone_id
        """),
        {"zone_id": zone_id},
    ).mappings().first()

    if not row:
        return {
            "zone_id": zone_id,
            "pin_codes": [],
            "density_weight": None,
            "ward_name": None,
            "updated_at": None,
        }

    try:
        pin_codes = json.loads(row["pin_codes_json"]) if row["pin_codes_json"] else []
    except json.JSONDecodeError:
        pin_codes = []

    return {
        "zone_id": row["zone_id"],
        "pin_codes": pin_codes,
        "density_weight": row["density_weight"],
        "ward_name": row["ward_name"],
        "updated_at": _parse_iso_datetime(row["updated_at"]),
    }

def upsert_zone_coverage_metadata(
    zone_id: int,
    db: Session,
    *,
    pin_codes: Optional[list[str]] = None,
    density_weight: Optional[float] = None,
    ward_name: Optional[str] = None,
) -> dict:
    """Create or update zone coverage metadata."""
    _ensure_zone_coverage_metadata_table(db)
    existing = get_zone_coverage_metadata(zone_id, db)

    normalized_pin_codes = existing["pin_codes"] if pin_codes is None else sorted({
        str(pin).strip() for pin in pin_codes if str(pin).strip()
    })
    payload = {
        "zone_id": zone_id,
        "pin_codes_json": json.dumps(normalized_pin_codes),
        "density_weight": density_weight if density_weight is not None else existing["density_weight"],
        "ward_name": ward_name if ward_name is not None else existing["ward_name"],
        "updated_at": utcnow().isoformat(),
    }

    db.execute(
        text("""
            INSERT INTO zone_coverage_metadata (
                zone_id, pin_codes_json, density_weight, ward_name, updated_at
            ) VALUES (
                :zone_id, :pin_codes_json, :density_weight, :ward_name, :updated_at
            )
            ON CONFLICT(zone_id) DO UPDATE SET
                pin_codes_json = excluded.pin_codes_json,
                density_weight = excluded.density_weight,
                ward_name = excluded.ward_name,
                updated_at = excluded.updated_at
        """),
        payload,
    )
    db.commit()
    return get_zone_coverage_metadata(zone_id, db)

# --- Partner Platform Activity ---

def get_db_partner_platform_activity(partner_id: int, db: Session) -> dict:
    """Fetch persisted platform activity for a partner from DB."""
    _ensure_partner_platform_activity_table(db)
    row = db.execute(
        text("""
            SELECT partner_id, platform_logged_in, active_shift, orders_accepted_recent,
                   orders_completed_recent, last_app_ping, zone_dwell_minutes,
                   suspicious_inactivity, platform, updated_at, source
            FROM partner_platform_activity
            WHERE partner_id = :partner_id
        """),
        {"partner_id": partner_id},
    ).mappings().first()

    if not row:
        now = utcnow().isoformat()
        p = db.query(Partner).filter(Partner.id == partner_id).first()
        actual_platform = p.platform.value if p and p.platform else "zepto"
        return {
            "partner_id": partner_id,
            "platform_logged_in": True,
            "active_shift": True,
            "orders_accepted_recent": 5,
            "orders_completed_recent": 4,
            "last_app_ping": now,
            "zone_dwell_minutes": 60,
            "suspicious_inactivity": False,
            "platform": actual_platform,
            "updated_at": now,
            "source": "default",
        }

    return {
        "partner_id": row["partner_id"],
        "platform_logged_in": bool(row["platform_logged_in"]),
        "active_shift": bool(row["active_shift"]),
        "orders_accepted_recent": row["orders_accepted_recent"],
        "orders_completed_recent": row["orders_completed_recent"],
        "last_app_ping": row["last_app_ping"],
        "zone_dwell_minutes": row["zone_dwell_minutes"],
        "suspicious_inactivity": bool(row["suspicious_inactivity"]),
        "platform": row["platform"],
        "updated_at": row["updated_at"],
        "source": row["source"],
    }

def upsert_db_partner_platform_activity(partner_id: int, db: Session, **kwargs) -> dict:
    """Create or update partner platform activity in DB."""
    _ensure_partner_platform_activity_table(db)
    existing = get_db_partner_platform_activity(partner_id, db)

    allowed = {
        "platform_logged_in", "active_shift", "orders_accepted_recent",
        "orders_completed_recent", "last_app_ping", "zone_dwell_minutes",
        "suspicious_inactivity", "platform",
    }
    for key, val in kwargs.items():
        if key in allowed:
            existing[key] = val

    payload = {
        "partner_id": partner_id,
        "platform_logged_in": int(existing["platform_logged_in"]),
        "active_shift": int(existing["active_shift"]),
        "orders_accepted_recent": existing["orders_accepted_recent"],
        "orders_completed_recent": existing["orders_completed_recent"],
        "last_app_ping": existing["last_app_ping"],
        "zone_dwell_minutes": existing["zone_dwell_minutes"],
        "suspicious_inactivity": int(existing["suspicious_inactivity"]),
        "platform": existing["platform"],
        "updated_at": utcnow().isoformat(),
        "source": "admin_override",
    }

    db.execute(
        text("""
            INSERT INTO partner_platform_activity (
                partner_id, platform_logged_in, active_shift, orders_accepted_recent,
                orders_completed_recent, last_app_ping, zone_dwell_minutes,
                suspicious_inactivity, platform, updated_at, source
            ) VALUES (
                :partner_id, :platform_logged_in, :active_shift, :orders_accepted_recent,
                :orders_completed_recent, :last_app_ping, :zone_dwell_minutes,
                :suspicious_inactivity, :platform, :updated_at, :source
            )
            ON CONFLICT(partner_id) DO UPDATE SET
                platform_logged_in = excluded.platform_logged_in,
                active_shift = excluded.active_shift,
                orders_accepted_recent = excluded.orders_accepted_recent,
                orders_completed_recent = excluded.orders_completed_recent,
                last_app_ping = excluded.last_app_ping,
                zone_dwell_minutes = excluded.zone_dwell_minutes,
                suspicious_inactivity = excluded.suspicious_inactivity,
                platform = excluded.platform,
                updated_at = excluded.updated_at,
                source = excluded.source
        """),
        payload,
    )
    db.commit()
    return get_db_partner_platform_activity(partner_id, db)

# --- Availability Checks ---

def is_partner_available_for_trigger(
    partner: Partner,
    db: Session,
    trigger_time: Optional[datetime] = None,
) -> tuple[bool, str]:
    """
    Check whether the partner should be eligible when the trigger fires.
    """
    trigger_time = trigger_time or utcnow()

    if not partner.is_active:
        return False, "partner_inactive"

    runtime_metadata = get_partner_runtime_metadata(partner.id, db)
    if runtime_metadata["is_manual_offline"]:
        offline_until = runtime_metadata["manual_offline_until"]
        if offline_until is None or trigger_time <= offline_until:
            return False, "manual_offline"

    leave_until = runtime_metadata["leave_until"]
    if leave_until and trigger_time <= leave_until:
        return False, "declared_leave"

    shift_days = [str(day).strip().lower()[:3] for day in (partner.shift_days or []) if day]
    trigger_day = DAY_NAMES[trigger_time.weekday()]
    if shift_days and trigger_day not in shift_days:
        return False, "outside_shift_days"

    shift_start = _parse_shift_time(getattr(partner, "shift_start", None))
    shift_end = _parse_shift_time(getattr(partner, "shift_end", None))
    if shift_start and shift_end:
        current_time = trigger_time.time()
        if shift_start <= shift_end:
            in_window = shift_start <= current_time <= shift_end
        else:
            in_window = current_time >= shift_start or current_time <= shift_end

        if not in_window:
            return False, "outside_shift_window"

    return True, "eligible"
