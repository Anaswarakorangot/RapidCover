# Prompt for Other AI: RapidCover Person 1 Implementation

You are a senior full-stack engineer working on RapidCover.

I want you to implement the "Person 1: Worker Experience + Fraud + ML + Trigger Validation" scope using the code I provide below.

Before changing anything:
- Read all provided file contents first.
- Preserve existing public APIs, function signatures, and UI contracts unless a change is clearly required.
- Do not rewrite unrelated code.
- Follow the project existing style and patterns.
- Do not invent missing files, models, schemas, or database fields.
- If you need a missing file, tell me exactly which file is needed and why.
- If you change files, return the complete updated contents of every changed file.
- Make tests deterministic.
- Do not use fake/random fallback values for business-critical outputs.

Scope:
- worker app behavior
- fraud detection quality
- ML realism
- validation matrix correctness
- trigger-to-claim correctness
- worker dashboard intelligence

Required work:
1. Fix the validation matrix completely: make all 10 checks real and stable; restore missing helper contract for tests; ensure pin-code match, platform activity, and cross-source agreement work.
2. Upgrade fraud detection: GPS spoof detection from ping history, centroid drift from real stored pings, impossible speed detection, device consistency tracking, delivery activity paradox detection, duplicate/collusion patterns, and fake weather claim defense using stored weather/advisory history.
3. Upgrade ML from wrappers to meaningful implementations: improve fraud model inputs, premium model features, and zone risk scoring inputs while keeping current interfaces.
4. Harden trigger-to-claim logic: sustained event logic, partial disruption logic, aggregation logic, and claim creation with correct validation evidence.
5. Make worker dashboard intelligent: earnings protected, active weekly coverage, renewal risk, live disruption relevance, payout proof, and forecast risk alerts.
6. Remove worker-side fake assumptions: no policy-count-as-activity fallback if actual data can be stored; no UI fallback values for premium breakdown/experience state unless clearly marked as an empty state.

Please respond with:
1. Short diagnosis.
2. Implementation plan.
3. Exact files that need changes.
4. Complete updated contents of every changed file.
5. Any migrations or schema changes required.
6. Tests to add or update.
7. Exact backend and frontend verification commands.
8. Any missing files or assumptions that block full completion.

## Main Backend Files

--- FILE: backend/app/services/claims_processor.py ---
``python
"""
Claims auto-creation processor.

When a trigger event fires, this service:
1. Finds all active policies in the affected zone
2. Validates each partner (GPS coherence, no activity paradox)
3. Calculates payout amount (based on policy tier and disruption duration)
4. Computes fraud score
5. Creates claims with appropriate status
6. Applies sustained event modifiers (70% payout after 5+ consecutive days)
"""

import json
from datetime import datetime, timedelta, time
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text

from app.models.partner import Partner
from app.models.policy import Policy, TIER_CONFIG
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent, TriggerType
from app.models.zone import Zone
from app.services.fraud_service import calculate_fraud_score, FRAUD_THRESHOLDS
from app.services.premium_service import calculate_zone_pool_share as apply_zone_pool_share_cap
from app.services.notifications import (
    notify_claim_created,
    notify_claim_approved,
    notify_claim_paid,
    notify_claim_rejected,
)
from app.services.payout_service import generate_upi_ref
from app.services.multi_trigger_resolver import (
    check_and_resolve_aggregation,
    update_claim_with_aggregation,
)
from app.config import get_settings


# Partial Disruption Categories with payout factors
# Based on severity level and trigger type
DISRUPTION_CATEGORIES = {
    "full_halt": {"factor": 1.0, "description": "Complete work stoppage"},
    "severe_reduction": {"factor": 0.75, "description": "75% income loss"},
    "moderate_reduction": {"factor": 0.50, "description": "50% income loss"},
    "minor_reduction": {"factor": 0.25, "description": "25% income loss"},
}


def determine_disruption_category(
    trigger_type: TriggerType,
    severity: int,
    source_data: Optional[dict] = None,
) -> tuple[str, float, str]:
    """
    Determine the disruption category based on trigger type and severity.

    Args:
        trigger_type: The type of trigger event
        severity: Severity level (1-5)
        source_data: Optional source data with expected/actual order info

    Returns:
        (category, factor, reason) tuple
    """
    # Shutdown and Closure are always full halt - no partial for these
    if trigger_type in [TriggerType.SHUTDOWN, TriggerType.CLOSURE]:
        return ("full_halt", 1.0, "shutdown_or_closure_always_full")

    # Check if we have order data for more precise calculation
    if source_data:
        expected_orders = source_data.get("expected_orders")
        actual_orders = source_data.get("actual_orders")
        partial_override = source_data.get("partial_factor_override")

        # If explicit override provided, use it
        if partial_override is not None:
            override = max(0.0, min(1.0, float(partial_override)))
            if override == 1.0:
                return ("full_halt", 1.0, "partial_factor_override")
            elif override >= 0.75:
                return ("severe_reduction", override, "partial_factor_override")
            elif override >= 0.50:
                return ("moderate_reduction", override, "partial_factor_override")
            else:
                return ("minor_reduction", override, "partial_factor_override")

        # Calculate from order data if available
        if expected_orders and actual_orders is not None and expected_orders > 0:
            reduction_ratio = 1 - (actual_orders / expected_orders)
            reduction_ratio = max(0.0, min(1.0, reduction_ratio))

            if reduction_ratio >= 0.90:
                return ("full_halt", 1.0, f"order_reduction_{reduction_ratio:.0%}")
            elif reduction_ratio >= 0.70:
                return ("severe_reduction", 0.75, f"order_reduction_{reduction_ratio:.0%}")
            elif reduction_ratio >= 0.40:
                return ("moderate_reduction", 0.50, f"order_reduction_{reduction_ratio:.0%}")
            elif reduction_ratio >= 0.20:
                return ("minor_reduction", 0.25, f"order_reduction_{reduction_ratio:.0%}")
            else:
                # Less than 20% reduction - minimal impact, but still apply minimum
                return ("minor_reduction", 0.25, f"order_reduction_{reduction_ratio:.0%}")

    # Default: Map severity to disruption category
    # Severity 5 -> full_halt
    # Severity 4 -> full_halt (still severe enough for full payout)
    # Severity 3 -> severe_reduction
    # Severity 2 -> moderate_reduction
    # Severity 1 -> minor_reduction
    if severity >= 4:
        return ("full_halt", 1.0, f"severity_{severity}_full")
    elif severity == 3:
        return ("severe_reduction", 0.75, "severity_3_severe")
    elif severity == 2:
        return ("moderate_reduction", 0.50, "severity_2_moderate")
    else:  # severity == 1
        return ("minor_reduction", 0.25, "severity_1_minor")


# Payout configuration
HOURLY_PAYOUT_RATES = {
    TriggerType.RAIN: 50,      # Rs.50/hour
    TriggerType.HEAT: 40,      # Rs.40/hour
    TriggerType.AQI: 45,       # Rs.45/hour
    TriggerType.SHUTDOWN: 60,  # Rs.60/hour (civic shutdowns are more impactful)
    TriggerType.CLOSURE: 55,   # Rs.55/hour
}

# Minimum disruption hours for payout
MIN_DISRUPTION_HOURS = {
    TriggerType.RAIN: 0.5,     # 30 mins
    TriggerType.HEAT: 4,       # 4 hours
    TriggerType.AQI: 3,        # 3 hours
    TriggerType.SHUTDOWN: 2,   # 2 hours
    TriggerType.CLOSURE: 1.5,  # 90 mins
}

# Default disruption duration for demo (since we're not tracking real duration)
DEFAULT_DISRUPTION_HOURS = 4

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
UNSET = object()


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


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetimes stored in auxiliary metadata tables."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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
        "updated_at": datetime.utcnow().isoformat(),
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
        "updated_at": datetime.utcnow().isoformat(),
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
        now = datetime.utcnow().isoformat()
        # Resolve the partner's actual registered platform (zepto/blinkit)
        from app.models.partner import Partner as _Partner
        p = db.query(_Partner).filter(_Partner.id == partner_id).first()
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
        "updated_at": datetime.utcnow().isoformat(),
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


def build_validation_matrix(
    partner: "Partner",
    policy: "Policy",
    trigger_event: "TriggerEvent",
    zone: Optional["Zone"],
    fraud_result: dict,
    db: Session,
    source_data: dict = None,
) -> list[dict]:
    """
    Build the pre-payout validation matrix for a claim.

    Each check has: check_name, passed, reason, source, confidence.
    All 10 checks from the spec are run.
    """
    from app.services.trigger_engine import check_partner_pin_code_match
    from app.services.external_apis import evaluate_partner_platform_eligibility

    now = datetime.utcnow()
    source_data = source_data or {}
    matrix = []

    def _check(name: str, passed: bool, reason: str, source: str, confidence: float):
        matrix.append({
            "check_name": name,
            "passed": passed,
            "reason": reason,
            "source": source,
            "confidence": round(confidence, 3),
        })

    # 1. Source threshold breach confirmed
    data_source = source_data.get("data_source", "mock")
    threshold_val = source_data.get("threshold")
    actual_val = (
        source_data.get("rainfall_mm_hr")
        or source_data.get("temp_celsius")
        or source_data.get("aqi")
    )
    if threshold_val is not None and actual_val is not None:
        threshold_ok = actual_val >= threshold_val
        _check(
            "source_threshold_breach",
            threshold_ok,
            f"Measured {actual_val} vs threshold {threshold_val}",
            data_source,
            1.0 if data_source == "live" else 0.7,
        )
    else:
        _check("source_threshold_breach", True, "Threshold confirmed by trigger event record", "trigger_db", 0.8)

    # 2. Zone match confirmed
    if zone:
        zone_match = trigger_event.zone_id == zone.id
        _check("zone_match", zone_match, f"Trigger zone {trigger_event.zone_id} == partner zone {zone.id}", "database", 1.0)
    else:
        _check("zone_match", False, "Zone not found", "database", 0.0)

    # 3. Pin-code match confirmed
    if zone:
        pin_match, pin_reason = check_partner_pin_code_match(partner, zone, db)
        partner_meta = get_partner_runtime_metadata(partner.id, db)
        _check(
            "pin_code_match",
            pin_match,
            pin_reason,
            "zone_coverage_metadata",
            0.9 if pin_match else 0.0,
        )
    else:
        _check("pin_code_match", False, "Zone unavailable for pin-code check", "none", 0.0)

    # 4. Active policy confirmed
    policy_active = (
        policy.is_active
        and policy.starts_at <= now
        and policy.expires_at > (now - timedelta(hours=48))
    )
    _check("active_policy", policy_active, f"Policy {policy.id} active from {policy.starts_at.date()} to {policy.expires_at.date()}", "database", 1.0)

    # 5. Shift-window confirmed
    available, avail_reason = is_partner_available_for_trigger(partner, db, trigger_event.started_at or now)
    _check("shift_window", available, avail_reason, "partner_runtime_metadata", 1.0 if available else 0.0)

    # 6. Partner activity confirmed (runtime metadata â€” manual offline / leave)
    runtime = get_partner_runtime_metadata(partner.id, db)
    not_manual_offline = not runtime["is_manual_offline"]
    not_on_leave = runtime["leave_until"] is None or (trigger_event.started_at or now) > runtime["leave_until"]
    partner_active_ok = not_manual_offline and not_on_leave
    _check(
        "partner_activity",
        partner_active_ok,
        "Not manually offline and not on declared leave" if partner_active_ok else "Partner marked offline or on leave",
        "partner_runtime_metadata",
        1.0 if partner_active_ok else 0.0,
    )

    # 7. Platform activity confirmed (Zomato/Swiggy/Zepto/Blinkit)
    platform_eval = evaluate_partner_platform_eligibility(partner.id)
    _check(
        "platform_activity",
        platform_eval["eligible"],
        f"Platform score {platform_eval['score']:.0%} â€” {platform_eval['activity'].get('platform', 'n/a')}",
        "platform_activity_simulation",
        platform_eval["score"],
    )

    # 8. Fraud score below threshold
    fraud_score = fraud_result.get("score", 0.5)
    fraud_ok = fraud_score < FRAUD_THRESHOLDS.get("auto_reject", 0.90)
    _check(
        "fraud_score_below_threshold",
        fraud_ok,
        f"Fraud score {fraud_score:.3f} ({'below' if fraud_ok else 'above'} reject threshold {FRAUD_THRESHOLDS.get('auto_reject', 0.90)})",
        "fraud_service",
        1.0 - fraud_score,
    )

    # 9. Data freshness acceptable
    data_source_tag = source_data.get("data_source", "mock")
    freshness_ok = data_source_tag in ("live",) or True   # mock is always "fresh" by definition
    _check(
        "data_freshness",
        freshness_ok,
        f"Data source tag: {data_source_tag}",
        data_source_tag,
        1.0 if data_source_tag == "live" else 0.7,
    )

    # 10. Cross-source agreement acceptable
    # We check if trigger_engine logged agreement via source_data
    agreement_score = source_data.get("oracle_agreement_score", 1.0)
    cross_source_ok = agreement_score >= 0.6
    _check(
        "cross_source_agreement",
        cross_source_ok,
        f"Oracle agreement score: {agreement_score:.0%}",
        "oracle_reliability_engine",
        agreement_score,
    )

    return matrix


def calculate_payout_amount(
    trigger_event: TriggerEvent,
    policy: Policy,
    disruption_hours: Optional[float] = None,
    sustained_event_modifier: float = 1.0,
    partial_disruption_data: Optional[dict] = None,
) -> tuple[float, dict]:
    """
    Calculate payout amount based on trigger type, duration, and policy limits.

    Args:
        trigger_event: The trigger event
        policy: The policy to calculate payout for
        disruption_hours: Hours of disruption (defaults to DEFAULT_DISRUPTION_HOURS)
        sustained_event_modifier: Modifier for sustained events (default 1.0, 0.70 for sustained)
        partial_disruption_data: Optional dict with expected_orders, actual_orders, or partial_factor_override

    Returns tuple of (payout_amount, calculation_details)
    """
    if disruption_hours is None:
        # Use default for demo
        disruption_hours = DEFAULT_DISRUPTION_HOURS

    # Get hourly rate for this trigger type
    hourly_rate = HOURLY_PAYOUT_RATES.get(trigger_event.trigger_type, 50)

    # Calculate base payout
    base_payout = hourly_rate * disruption_hours

    # Apply severity multiplier (1.0 to 1.5 based on severity 1-5)
    severity_multiplier = 1.0 + (trigger_event.severity - 1) * 0.125
    adjusted_payout = base_payout * severity_multiplier

    # Determine partial disruption category and factor
    category, partial_factor, partial_reason = determine_disruption_category(
        trigger_event.trigger_type,
        trigger_event.severity,
        partial_disruption_data,
    )

    # Apply partial disruption factor
    partial_adjusted = adjusted_payout * partial_factor

    # Apply sustained event modifier (70% for sustained events)
    sustained_adjusted = partial_adjusted * sustained_event_modifier

    # Apply policy daily limit
    daily_limit = policy.max_daily_payout
    final_payout = min(sustained_adjusted, daily_limit)

    # Build partial disruption metadata
    partial_disruption_meta = {
        "category": category,
        "factor": partial_factor,
        "reason": partial_reason,
    }
    if partial_disruption_data:
        if "expected_orders" in partial_disruption_data:
            partial_disruption_meta["expected_orders"] = partial_disruption_data["expected_orders"]
        if "actual_orders" in partial_disruption_data:
            partial_disruption_meta["actual_orders"] = partial_disruption_data["actual_orders"]
        if "partial_factor_override" in partial_disruption_data:
            partial_disruption_meta["factor_override_used"] = True

    calculation_details = {
        "hourly_rate": hourly_rate,
        "disruption_hours": disruption_hours,
        "base_payout": round(base_payout, 2),
        "severity_multiplier": round(severity_multiplier, 3),
        "after_severity": round(adjusted_payout, 2),
        "partial_disruption": partial_disruption_meta,
        "after_partial_disruption": round(partial_adjusted, 2),
        "sustained_event_modifier": sustained_event_modifier,
        "after_sustained_modifier": round(sustained_adjusted, 2),
        "daily_limit": daily_limit,
        "daily_limit_applied": sustained_adjusted > daily_limit,
    }

    return round(final_payout, 2), calculation_details


def check_daily_limit(
    partner: Partner,
    policy: Policy,
    proposed_payout: float,
    db: Session,
) -> tuple[bool, float]:
    """
    Check if partner has remaining daily payout capacity.

    Returns (is_within_limit, remaining_amount)
    """
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time())

    # Get today's paid/pending claims for this policy
    daily_claimed = (
        db.query(func.sum(Claim.amount))
        .filter(
            Claim.policy_id == policy.id,
            Claim.created_at >= start_of_day,
            Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED, ClaimStatus.PAID]),
        )
        .scalar()
    ) or 0

    remaining = policy.max_daily_payout - daily_claimed

    return (proposed_payout <= remaining, max(0, remaining))


def check_weekly_limit(
    partner: Partner,
    policy: Policy,
    db: Session,
) -> tuple[bool, int]:
    """
    Check if partner has remaining claim days this week.

    Returns (has_days_remaining, days_remaining)
    """
    # Get start of current week (Monday)
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = datetime.combine(start_of_week.date(), datetime.min.time())

    # Count distinct days with claims this week
    claim_days = (
        db.query(func.date(Claim.created_at))
        .filter(
            Claim.policy_id == policy.id,
            Claim.created_at >= start_of_week,
            Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED, ClaimStatus.PAID]),
        )
        .distinct()
        .count()
    )

    remaining = policy.max_days_per_week - claim_days

    return (remaining > 0, max(0, remaining))


def _parse_shift_time(value: Optional[str]) -> Optional[time]:
    """Parse HH:MM strings used in partner shift preferences."""
    if not value:
        return None
    try:
        hour, minute = value.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except (ValueError, AttributeError):
        return None


def is_partner_available_for_trigger(
    partner: Partner,
    db: Session,
    trigger_time: Optional[datetime] = None,
) -> tuple[bool, str]:
    """
    Check whether the partner should be eligible when the trigger fires.

    Uses existing partner activity + shift preference fields:
    - inactive partners are excluded
    - if shift_days are configured, the trigger day must match
    - if shift_start / shift_end are configured, the trigger time must be in-window
    """
    trigger_time = trigger_time or datetime.utcnow()

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
            # Overnight shifts like 22:00-06:00
            in_window = current_time >= shift_start or current_time <= shift_end

        if not in_window:
            return False, "outside_shift_window"

    return True, "eligible"


def _get_zone_density_weight(zone: Optional[Zone], total_partners_in_event: int) -> float:
    """
    Resolve density weight from the model if present, else infer from event size.
    """
    model_density_weight = getattr(zone, "density_weight", None) if zone else None
    if model_density_weight is not None:
        return float(model_density_weight)

    if total_partners_in_event < 50:
        return 0.15
    if total_partners_in_event <= 150:
        return 0.35
    return 0.50


def calculate_city_weekly_reserve(zone_id: int, db: Session, days: int = 7) -> float:
    """Estimate city weekly reserve from premiums collected in the recent period."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        return 0.0

    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    city_zones = db.query(Zone).filter(Zone.city.ilike(f"%{zone.city}%")).all()
    zone_ids = [z.id for z in city_zones]
    if not zone_ids:
        return 0.0

    partner_ids = [row[0] for row in db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids)).all()]
    if not partner_ids:
        return 0.0

    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0.0

    return float(total_premiums)


def get_eligible_policies(
    zone_id: int,
    db: Session,
    trigger_time: Optional[datetime] = None,
) -> list[tuple[Policy, Partner]]:
    """
    Get all active policies for partners in a zone.

    Includes policies that are:
    - Currently active (not expired)
    - Within the 48-hour grace period (expired but within grace window)

    Returns list of (Policy, Partner) tuples.
    """
    now = datetime.utcnow()

    # Grace period is 48 hours after expiry
    GRACE_PERIOD_HOURS = 48
    grace_cutoff = now - timedelta(hours=GRACE_PERIOD_HOURS)

    results = (
        db.query(Policy, Partner)
        .join(Partner, Policy.partner_id == Partner.id)
        .filter(
            Partner.zone_id == zone_id,
            Partner.is_active == True,
            Policy.is_active == True,
            Policy.starts_at <= now,
            # Include policies in grace period (expired within last 48 hours)
            Policy.expires_at > grace_cutoff,
        )
        .all()
    )

    trigger_time = trigger_time or now
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    eligible_results: list[tuple[Policy, Partner]] = []
    for policy, partner in results:
        is_available, _ = is_partner_available_for_trigger(partner, db, trigger_time)
        if not is_available:
            continue

        if zone:
            from app.services.trigger_engine import check_partner_pin_code_match
            pin_code_match, _ = check_partner_pin_code_match(partner, zone, db)
            # DONT strict-fail during hackathon demo if seed data is incomplete.
            # if not pin_code_match:
            #     continue

        eligible_results.append((policy, partner))

    return eligible_results


def process_trigger_event(
    trigger_event: TriggerEvent,
    db: Session,
    disruption_hours: Optional[float] = None,
) -> list[Claim]:
    """
    Process a trigger event and create claims for eligible partners.

    Includes sustained event detection:
    - Tracks consecutive days of same trigger type in zone
    - After 5+ consecutive days, applies 70% payout modifier
    - Bypasses weekly cap for sustained events
    - Maximum 21 days tracking

    Returns list of created claims.
    """
    # Import here to avoid circular import
    from app.services.trigger_detector import track_sustained_event

    zone_id = trigger_event.zone_id
    created_claims = []

    # Track sustained event and get modifier
    sustained_info = track_sustained_event(
        zone_id,
        trigger_event.trigger_type,
        trigger_event.started_at or datetime.utcnow()
    )

    # Get eligible policies in the affected zone
    eligible = get_eligible_policies(zone_id, db, trigger_event.started_at or datetime.utcnow())
    total_partners_in_event = len(eligible)
    city_weekly_reserve = calculate_city_weekly_reserve(zone_id, db)
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    zone_metadata = get_zone_coverage_metadata(zone_id, db)
    if zone and zone_metadata["density_weight"] is not None and getattr(zone, "density_weight", None) is None:
        setattr(zone, "density_weight", zone_metadata["density_weight"])
    zone_density_weight = _get_zone_density_weight(zone, total_partners_in_event)

    if sustained_info["max_days_reached"]:
        return []

    is_forced = False
    source_data = {}
    try:
        source_data = json.loads(trigger_event.source_data or "{}")
        is_forced = source_data.get("force_fired", False)
    except:
        pass

    # Extract partial disruption data from source_data if present
    partial_disruption_data = None
    if source_data.get("expected_orders") or source_data.get("actual_orders") is not None or source_data.get("partial_factor_override") is not None:
        partial_disruption_data = {
            k: source_data[k] for k in ["expected_orders", "actual_orders", "partial_factor_override"]
            if k in source_data
        }

    for policy, partner in eligible:
        # Calculate payout amount with sustained event modifier and partial disruption
        payout, calc_details = calculate_payout_amount(
            trigger_event,
            policy,
            disruption_hours,
            sustained_event_modifier=sustained_info["payout_modifier"],
            partial_disruption_data=partial_disruption_data,
        )

        # Check daily limit (bypass if forced for demo)
        within_daily, daily_remaining = check_daily_limit(partner, policy, payout, db)
        if not within_daily and not is_forced:
            payout = daily_remaining  # Reduce to remaining limit

        if payout <= 0 and not is_forced:
            continue  # Skip if no payout available

        # Check weekly limit (bypass for sustained events or forced demo)
        if not sustained_info["bypass_weekly_cap"] and not is_forced:
            has_weekly_days, _ = check_weekly_limit(partner, policy, db)
            if not has_weekly_days:
                continue  # Skip if weekly days exhausted

        # Apply zone pool share cap for mass events
        if not is_forced:
            zone_pool_result = apply_zone_pool_share_cap(
                calculated_payout=payout,
                city_weekly_reserve=city_weekly_reserve,
                zone_density_weight=zone_density_weight,
                total_partners_in_event=total_partners_in_event,
            )
            payout = zone_pool_result["final_payout"]
        else:
            zone_pool_result = {
                "final_payout": payout,
                "calculated_payout": payout,
                "zone_pool_share": 999999.0,
                "pool_cap_applied": False,
                "reduction_amount": 0.0,
            }

        if payout <= 0:
            continue

        # Calculate fraud score
        fraud_result = calculate_fraud_score(partner, trigger_event, db)

        # Determine claim status based on fraud score
        if fraud_result["recommendation"] == "approve":
            status = ClaimStatus.APPROVED
        elif fraud_result["recommendation"] == "reject":
            status = ClaimStatus.REJECTED
        else:
            status = ClaimStatus.PENDING

        # Build pre-payout validation matrix
        try:
            src_data = json.loads(trigger_event.source_data or "{}")
        except Exception:
            src_data = {}
        validation_matrix = build_validation_matrix(
            partner, policy, trigger_event, zone, fraud_result, db, src_data
        )
        matrix_passed = all(c["passed"] for c in validation_matrix)
        matrix_summary = {
            "total_checks": len(validation_matrix),
            "passed": sum(1 for c in validation_matrix if c["passed"]),
            "failed": sum(1 for c in validation_matrix if not c["passed"]),
            "overall": "pass" if matrix_passed else "fail",
        }
        # Check multi-trigger aggregation
        should_create_new, existing_claim, aggregation_meta = check_and_resolve_aggregation(
            trigger_event=trigger_event,
            policy=policy,
            calculated_payout=payout,
            db=db,
        )

        if not should_create_new and existing_claim:
            # Update existing claim with aggregation data instead of creating new
            update_claim_with_aggregation(
                claim=existing_claim,
                new_payout=aggregation_meta.get("post_aggregation_payout", existing_claim.amount),
                aggregation_metadata=aggregation_meta,
                db=db,
            )
            # Skip creating a new claim - this trigger was aggregated
            continue

        # Build validation data with rich payout metadata including sustained event info
        validation_data = {
            "fraud_analysis": fraud_result,
            "validation_matrix": validation_matrix,
            "validation_matrix_summary": matrix_summary,
            "daily_limit_check": {"within_limit": within_daily, "remaining": daily_remaining},
            "sustained_event": sustained_info,
            "aggregation": aggregation_meta,  # Multi-trigger aggregation data
            "payout_calculation": {
                **calc_details,
                "final_payout": payout,
                "trigger_type": trigger_event.trigger_type.value,
                "zone_id": zone_id,
                "zone_density_weight": zone_density_weight,
                "city_weekly_reserve": round(city_weekly_reserve, 2),
                "total_partners_in_event": total_partners_in_event,
                "zone_pool_share": zone_pool_result,
                "severity": trigger_event.severity,
            },
            "processed_at": datetime.utcnow().isoformat(),
        }

        # Create claim
        claim = Claim(
            policy_id=policy.id,
            trigger_event_id=trigger_event.id,
            amount=payout,
            status=status,
            fraud_score=fraud_result["score"],
            validation_data=json.dumps(validation_data),
        )

        # Auto-payout for demo mode: use payout_service for structured UPI ref + transaction log
        settings = get_settings()
        if settings.auto_payout_enabled and claim.status == ClaimStatus.APPROVED:
            from app.services.payout_service import process_stripe_payout_mock
            
            # Use the new Stripe Mock for full UI visual effect
            success, upi_ref, stripe_data = process_stripe_payout_mock(partner, claim.amount, claim.id or 0)
            
            vd = json.loads(claim.validation_data)
            vd["transaction_log"] = {
                "ref": upi_ref,
                "channel": "Stripe API",
                "provider": "RapidCover",
                "amount": claim.amount,
                "currency": "INR",
                "status": "SUCCESS",
                "initiated_at": datetime.utcnow().isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
                "auto_payout": True,
            }
            vd["stripe"] = stripe_data
            vd["payout_status"] = "SUCCESS"
            vd["paid_at"] = datetime.utcnow().isoformat()
            claim.status = ClaimStatus.PAID
            claim.upi_ref = upi_ref
            claim.paid_at = datetime.utcnow()
            claim.validation_data = json.dumps(vd)

        db.add(claim)
        created_claims.append(claim)

    if created_claims:
        db.commit()
        for claim in created_claims:
            db.refresh(claim)
            # Send push notifications based on claim status
            if claim.status == ClaimStatus.PAID:
                notify_claim_paid(claim, db)
            elif claim.status == ClaimStatus.APPROVED:
                notify_claim_approved(claim, db)
            elif claim.status == ClaimStatus.REJECTED:
                notify_claim_rejected(claim, db)
            else:
                notify_claim_created(claim, db)

    return created_claims


def process_trigger_by_id(trigger_id: int, db: Session) -> list[Claim]:
    """
    Process a trigger event by ID.
    """
    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == trigger_id).first()

    if not trigger:
        return []

    return process_trigger_event(trigger, db)


def approve_claim(claim_id: int, db: Session) -> Optional[Claim]:
    """
    Manually approve a pending claim.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()

    if claim and claim.status == ClaimStatus.PENDING:
        claim.status = ClaimStatus.APPROVED
        db.commit()
        db.refresh(claim)
        notify_claim_approved(claim, db)

    return claim


def reject_claim(claim_id: int, db: Session, reason: str = None) -> Optional[Claim]:
    """
    Manually reject a claim.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()

    if claim and claim.status in [ClaimStatus.PENDING, ClaimStatus.APPROVED]:
        claim.status = ClaimStatus.REJECTED

        # Add rejection reason to validation data
        if reason:
            validation = json.loads(claim.validation_data or "{}")
            validation["rejection_reason"] = reason
            validation["rejected_at"] = datetime.utcnow().isoformat()
            claim.validation_data = json.dumps(validation)

        db.commit()
        db.refresh(claim)
        notify_claim_rejected(claim, db)

    return claim


def mark_as_paid(
    claim_id: int,
    db: Session,
    upi_ref: str = None,
) -> Optional[Claim]:
    """
    Mark an approved claim as paid.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()

    if claim and claim.status == ClaimStatus.APPROVED:
        claim.status = ClaimStatus.PAID
        claim.paid_at = datetime.utcnow()
        claim.upi_ref = upi_ref

        db.commit()
        db.refresh(claim)
        notify_claim_paid(claim, db)

    return claim


def get_pending_claims(db: Session, zone_id: Optional[int] = None) -> list[Claim]:
    """
    Get all pending claims, optionally filtered by zone.
    """
    query = db.query(Claim).filter(Claim.status == ClaimStatus.PENDING)

    if zone_id:
        query = query.join(TriggerEvent).filter(TriggerEvent.zone_id == zone_id)

    return query.order_by(Claim.created_at.desc()).all()
````

--- FILE: backend/app/services/fraud_service.py ---
``python
"""
fraud_service.py
-----------------------------------------------------------------------------
RapidCover Fraud Detection Service - 7-factor anomaly scorer.
Source: RapidCover Phase 2 Team Guide, Section 3.3 + Section 2F.

Algorithm: Isolation Forest (manually calibrated weights).

7 Factors (exact from Section 3.3):
  w1 = 0.25  gps_coherence          - within 500m of dark store
  w2 = 0.25  run_count_check        - Activity Paradox hard rule
  w3 = 0.15  zone_polygon_match     - event polygon confirmed
  w4 = 0.15  claim_frequency_score  - last 30 days
  w5 = 0.10  device_fingerprint     - consistency check
  w6 = 0.05  traffic_cross_check    - road disruption confirmed
  w7 = 0.05  centroid_drift_score   - 30-day GPS centroid (Section 2F)

Hard rejects (pre-filter, override score):
  - GPS velocity > 60 km/h between pings = spoof (Section 2F)
  - Zone not suspended by platform
  - Any run completed during suspended window (Activity Paradox)
  - Centroid drift > 15km from declared dark store (Section 2F)

Thresholds:
  < 0.50       â†’ auto_approve
  0.50 â€“ 0.75  â†’ enhanced_validation
  0.75 â€“ 0.90  â†’ manual_review
  > 0.90       â†’ auto_reject
-----------------------------------------------------------------------------
"""

import math
from app.services.ml_service import fraud_model, ClaimFeatures


# ------------------------------------------------------------------------------
# MAIN SCORING ENTRY POINT
# ------------------------------------------------------------------------------

def score_claim(features: ClaimFeatures) -> dict:
    """
    Score a claim for fraud. Delegates to fraud_model.score().
    Returns full result with score, decision, factors, hard_reject_reasons.
    """
    return fraud_model.score(features)


def score_claim_simple(
    partner_id:              int,
    zone_id:                 int,
    gps_in_zone:             bool,
    run_count_during_event:  int,
    zone_polygon_match:      bool,
    claims_last_30_days:     int,
    device_consistent:       bool,
    traffic_disrupted:       bool,
    centroid_drift_km:       float,
    max_gps_velocity_kmh:    float,
    zone_suspended:          bool,
) -> dict:
    """
    Simplified scoring for admin simulation / testing without raw GPS pings.
    Builds ClaimFeatures and delegates to fraud_model.score().
    """
    features = ClaimFeatures(
        partner_id             = partner_id,
        zone_id                = zone_id,
        gps_in_zone            = gps_in_zone,
        run_count_during_event = run_count_during_event,
        zone_polygon_match     = zone_polygon_match,
        claims_last_30_days    = claims_last_30_days,
        device_consistent      = device_consistent,
        traffic_disrupted      = traffic_disrupted,
        centroid_drift_km      = centroid_drift_km,
        max_gps_velocity_kmh   = max_gps_velocity_kmh,
        zone_suspended         = zone_suspended,
    )
    return fraud_model.score(features)


# ------------------------------------------------------------------------------
# GPS HELPER FUNCTIONS
# ------------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns distance in km between two GPS coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_max_velocity_kmh(pings: list) -> float:
    """
    Velocity physics check - Section 2F of team guide.
    Computes max speed (km/h) between consecutive GPS pings.
    > 60 km/h on a delivery bike = physically impossible = GPS spoof.

    Each ping: {"lat": float, "lng": float, "ts": int (epoch seconds)}
    """
    if len(pings) < 2:
        return 0.0

    max_kmh = 0.0
    for i in range(len(pings) - 1):
        p1, p2  = pings[i], pings[i + 1]
        dist_km = haversine_km(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
        dt_hrs  = (p2["ts"] - p1["ts"]) / 3600.0
        if dt_hrs <= 0:
            continue
        max_kmh = max(max_kmh, dist_km / dt_hrs)

    return round(max_kmh, 2)


def compute_centroid(pings: list) -> dict:
    """
    Compute 30-day GPS centroid - Section 2F of team guide.
    centroid = average of all GPS pings over last 30 days.

    Each ping: {"lat": float, "lng": float}
    Returns {"lat": float, "lng": float}
    """
    if not pings:
        return {"lat": 0.0, "lng": 0.0}

    avg_lat = sum(p["lat"] for p in pings) / len(pings)
    avg_lng = sum(p["lng"] for p in pings) / len(pings)
    return {"lat": round(avg_lat, 6), "lng": round(avg_lng, 6)}


def build_claim_features(
    partner_id:               int,
    zone_id:                  int,
    claim_gps_lat:            float,
    claim_gps_lng:            float,
    dark_store_lat:           float,
    dark_store_lng:           float,
    zone_radius_km:           float,
    run_count_during_event:   int,
    claims_last_30_days:      int,
    device_id:                str,
    last_known_device_id:     str,
    zone_suspended:           bool,
    zone_polygon_match:       bool,
    traffic_disrupted:        bool,
    gps_pings_30d:            list,     # {"lat", "lng", "ts"}
    centroid_30d_lat:         float,
    centroid_30d_lng:         float,
) -> ClaimFeatures:
    """
    Build ClaimFeatures from raw claim data.
    Called by claims processor before fraud scoring.
    """
    gps_in_zone = (
        haversine_km(claim_gps_lat, claim_gps_lng, dark_store_lat, dark_store_lng)
        <= zone_radius_km
    )
    device_consistent  = (device_id == last_known_device_id)
    max_velocity       = compute_max_velocity_kmh(gps_pings_30d)
    centroid_drift_km  = haversine_km(
        centroid_30d_lat, centroid_30d_lng,
        dark_store_lat,   dark_store_lng,
    )

    return ClaimFeatures(
        partner_id             = partner_id,
        zone_id                = zone_id,
        gps_in_zone            = gps_in_zone,
        run_count_during_event = run_count_during_event,
        zone_polygon_match     = zone_polygon_match,
        claims_last_30_days    = claims_last_30_days,
        device_consistent      = device_consistent,
        traffic_disrupted      = traffic_disrupted,
        centroid_drift_km      = centroid_drift_km,
        max_gps_velocity_kmh   = max_velocity,
        zone_suspended         = zone_suspended,
    )


# ------------------------------------------------------------------------------
# DECISION LABELS (for API responses + admin dashboard)
# ------------------------------------------------------------------------------

DECISION_LABELS: dict = {
    "auto_approve":        {"label": "âœ… Auto-approved",       "color": "green"},
    "enhanced_validation": {"label": "ðŸ” Enhanced validation", "color": "amber"},
    "manual_review":       {"label": "ðŸ‘ Manual review",       "color": "orange"},
    "auto_reject":         {"label": "âŒ Auto-rejected",        "color": "red"},
}


def get_decision_label(decision: str) -> dict:
    return DECISION_LABELS.get(decision, {"label": decision, "color": "gray"})


# ------------------------------------------------------------------------------
# COMPATIBILITY WRAPPER - matches old fraud_detector.calculate_fraud_score()
# ------------------------------------------------------------------------------

# Thresholds matching the old fraud_detector.py interface
FRAUD_THRESHOLDS = {
    "auto_approve": 0.50,      # Below this = auto approve (was 0.3 in old, 0.5 in new 7-factor)
    "review_required": 0.75,   # Between 0.50-0.75 = enhanced validation
    "manual_review": 0.90,     # Between 0.75-0.90 = manual review
    "auto_reject": 0.90,       # Above this = auto reject
}


def calculate_fraud_score(
    partner,
    trigger_event,
    db,
    partner_lat: float = None,
    partner_lng: float = None,
    had_deliveries_during: bool = False,
) -> dict:
    """
    Compatibility wrapper for the 7-factor fraud model.

    Matches the old fraud_detector.calculate_fraud_score() signature so that
    claims_processor.py can switch to the new model without code changes.

    New factors added (Section 2F + Section 3.3):
      - w7: centroid_drift_score (0.05)
      - Velocity physics check (>60km/h = spoof)
    """
    from sqlalchemy.orm import Session
    from sqlalchemy import func
    from datetime import datetime, timedelta
    from app.models.policy import Policy
    from app.models.claim import Claim
    from app.models.zone import Zone

    zone = trigger_event.zone if trigger_event else None
    if not zone and trigger_event:
        zone = db.query(Zone).filter(Zone.id == trigger_event.zone_id).first()

    # Get dark store coordinates
    dark_store_lat = zone.dark_store_lat if zone else 0.0
    dark_store_lng = zone.dark_store_lng if zone else 0.0

    # Default claim GPS to partner's zone dark store if not provided
    claim_lat = partner_lat if partner_lat is not None else dark_store_lat
    claim_lng = partner_lng if partner_lng is not None else dark_store_lng

    # Check GPS coherence (within 500m = 0.5km of dark store)
    gps_distance = haversine_km(claim_lat, claim_lng, dark_store_lat, dark_store_lng)
    gps_in_zone = gps_distance <= 0.5  # 500m threshold

    # Run count during event (Activity Paradox)
    run_count = 1 if had_deliveries_during else 0

    # Zone polygon match - assume true if GPS is within reasonable distance
    zone_polygon_match = gps_distance <= 5.0  # 5km for polygon match

    # Claim frequency - count claims in last 30 days
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]
    claims_last_30 = 0
    if policy_ids:
        cutoff = datetime.utcnow() - timedelta(days=30)
        claims_last_30 = (
            db.query(func.count(Claim.id))
            .filter(Claim.policy_id.in_(policy_ids), Claim.created_at >= cutoff)
            .scalar()
        ) or 0

    # Device fingerprint - assume consistent for now (no device tracking in current model)
    device_consistent = True

    # Traffic disrupted - assume true if trigger fired (trigger = disruption confirmed)
    traffic_disrupted = True

    # Centroid drift - for now use GPS distance as proxy
    # In production: would compute from 30-day GPS ping history
    centroid_drift_km = gps_distance

    # Max GPS velocity - for now assume 0 (no GPS ping history available)
    # In production: would compute from consecutive GPS pings
    max_velocity_kmh = 0.0

    # Zone suspended - true if trigger event exists and is active
    zone_suspended = trigger_event is not None and trigger_event.ended_at is None

    # Build features and score
    features = ClaimFeatures(
        partner_id=partner.id,
        zone_id=zone.id if zone else 0,
        gps_in_zone=gps_in_zone,
        run_count_during_event=run_count,
        zone_polygon_match=zone_polygon_match,
        claims_last_30_days=claims_last_30,
        device_consistent=device_consistent,
        traffic_disrupted=traffic_disrupted,
        centroid_drift_km=centroid_drift_km,
        max_gps_velocity_kmh=max_velocity_kmh,
        zone_suspended=zone_suspended,
    )

    result = fraud_model.score(features)

    # Map decision to recommendation (old format compatibility)
    decision_to_recommendation = {
        "auto_approve": "approve",
        "enhanced_validation": "review",
        "manual_review": "review",
        "auto_reject": "reject",
    }
    recommendation = decision_to_recommendation.get(result["decision"], "review")

    # Build reason string
    if result["hard_reject_reasons"]:
        reason = "; ".join(result["hard_reject_reasons"])
    elif recommendation == "approve":
        reason = "Low risk - auto approved (7-factor model)"
    elif recommendation == "reject":
        reason = "Very high risk - auto rejected (7-factor model)"
    else:
        reason = f"Moderate risk ({result['decision']}) - review required"

    # Return in old format for compatibility
    return {
        "score": result["fraud_score"],
        "factors": {
            "gps_coherence": 1 - result["factors"]["w1_gps_coherence"],
            "activity_paradox": 1 - result["factors"]["w2_run_count_clean"],
            "claim_frequency": result["factors"]["w4_claim_frequency"],
            "duplicate_claim": 0.0,  # Handled separately in claims_processor
            "account_age": 0.0,  # Not in 7-factor model
            "zone_boundary": 1 - result["factors"]["w3_zone_polygon_match"],
            # New factors from 7-factor model
            "centroid_drift_km": result["factors"]["w7_centroid_drift_km"],
            "device_consistent": result["factors"]["w5_device_consistent"],
            "traffic_disrupted": result["factors"]["w6_traffic_disrupted"],
        },
        "recommendation": recommendation,
        "reason": reason,
        "model_version": "7-factor",
        "raw_result": result,  # Include full result for debugging
    }
````

--- FILE: backend/app/services/fraud_detector.py ---
``python
"""
Fraud detection service for claims validation.

Implements rule-based scoring for detecting suspicious claim patterns:
- GPS spoofing detection
- Activity paradox (runs during disruption)
- Claim frequency analysis
- Duplicate event detection
- Zone boundary gaming
- Collusion ring detection (basic)
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent
from app.models.zone import Zone


# Fraud thresholds
FRAUD_THRESHOLDS = {
    "auto_approve": 0.3,      # Below this = auto approve
    "review_required": 0.6,    # Between 0.3-0.6 = manual review needed
    "auto_reject": 0.8,        # Above this = auto reject
}

# Scoring weights
SCORE_WEIGHTS = {
    "gps_mismatch": 0.25,
    "activity_paradox": 0.30,
    "high_frequency": 0.20,
    "duplicate_claim": 0.35,
    "new_account": 0.10,
    "zone_boundary": 0.15,
}


def check_gps_coherence(
    partner: Partner,
    trigger_event: TriggerEvent,
    partner_lat: Optional[float] = None,
    partner_lng: Optional[float] = None,
) -> float:
    """
    Check if partner's GPS location matches their registered zone.

    Returns a score 0-1 where higher = more suspicious.
    """
    if partner_lat is None or partner_lng is None:
        # No GPS data provided - slight penalty for missing data
        return 0.1

    zone = trigger_event.zone

    if not zone or not zone.dark_store_lat or not zone.dark_store_lng:
        return 0.0

    # Calculate rough distance (simplified)
    lat_diff = abs(partner_lat - zone.dark_store_lat)
    lng_diff = abs(partner_lng - zone.dark_store_lng)

    # ~111km per degree at equator, ~85km per degree in India
    distance_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 100

    # Within 5km = OK, 5-15km = suspicious, >15km = very suspicious
    if distance_km <= 5:
        return 0.0
    elif distance_km <= 15:
        return 0.3
    else:
        return 0.8


def check_activity_paradox(
    partner: Partner,
    trigger_event: TriggerEvent,
    had_deliveries_during: bool = False,
) -> float:
    """
    Check if partner was making deliveries during the disruption.

    If partner claims they couldn't work but had delivery activity,
    that's highly suspicious.

    Returns a score 0-1 where higher = more suspicious.
    """
    if had_deliveries_during:
        # Clear evidence of activity during claimed disruption
        return 0.9

    # In production, would check platform API for delivery records
    return 0.0


def check_claim_frequency(
    partner: Partner,
    db: Session,
    lookback_days: int = 30,
) -> float:
    """
    Check if partner has unusually high claim frequency.

    Returns a score 0-1 where higher = more suspicious.
    """
    # Get partner's policies
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    if not policy_ids:
        return 0.0

    # Count claims in lookback period
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    claim_count = (
        db.query(func.count(Claim.id))
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.created_at >= cutoff,
        )
        .scalar()
    )

    # Scoring: 0-2 claims/month = OK, 3-4 = slight flag, 5+ = suspicious
    if claim_count <= 2:
        return 0.0
    elif claim_count <= 4:
        return 0.2
    elif claim_count <= 6:
        return 0.5
    else:
        return 0.8


def check_duplicate_claim(
    partner: Partner,
    trigger_event: TriggerEvent,
    db: Session,
) -> float:
    """
    Check if partner already has a claim for this trigger event.

    Returns a score 0-1 where higher = more suspicious.
    """
    # Get partner's policies
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    if not policy_ids:
        return 0.0

    # Check for existing claim on this trigger
    existing = (
        db.query(Claim)
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.trigger_event_id == trigger_event.id,
        )
        .first()
    )

    if existing:
        return 1.0  # Definite duplicate

    return 0.0


def check_account_age(partner: Partner) -> float:
    """
    Check if this is a new account (higher fraud risk).

    Returns a score 0-1 where higher = more suspicious.
    """
    if not partner.created_at:
        return 0.1

    age_days = (datetime.utcnow() - partner.created_at.replace(tzinfo=None)).days

    # Less than 7 days = new, slight flag
    if age_days < 7:
        return 0.3
    elif age_days < 30:
        return 0.1
    else:
        return 0.0


def check_zone_boundary_gaming(
    partner: Partner,
    db: Session,
) -> float:
    """
    Check if partner frequently changes zones to maximize claims.

    Returns a score 0-1 where higher = more suspicious.
    """
    # For now, return 0 since we don't track zone changes
    # In production, would analyze zone change patterns
    return 0.0


def calculate_fraud_score(
    partner: Partner,
    trigger_event: TriggerEvent,
    db: Session,
    partner_lat: Optional[float] = None,
    partner_lng: Optional[float] = None,
    had_deliveries_during: bool = False,
) -> dict:
    """
    Calculate overall fraud score for a claim.

    Returns dict with:
    - score: float 0-1 (higher = more suspicious)
    - factors: dict of individual factor scores
    - recommendation: "approve", "review", or "reject"
    """
    factors = {
        "gps_coherence": check_gps_coherence(partner, trigger_event, partner_lat, partner_lng),
        "activity_paradox": check_activity_paradox(partner, trigger_event, had_deliveries_during),
        "claim_frequency": check_claim_frequency(partner, db),
        "duplicate_claim": check_duplicate_claim(partner, trigger_event, db),
        "account_age": check_account_age(partner),
        "zone_boundary": check_zone_boundary_gaming(partner, db),
    }

    # If duplicate claim detected, immediately flag
    if factors["duplicate_claim"] >= 1.0:
        return {
            "score": 1.0,
            "factors": factors,
            "recommendation": "reject",
            "reason": "Duplicate claim for same trigger event",
        }

    # Calculate weighted score
    weighted_sum = (
        factors["gps_coherence"] * SCORE_WEIGHTS["gps_mismatch"]
        + factors["activity_paradox"] * SCORE_WEIGHTS["activity_paradox"]
        + factors["claim_frequency"] * SCORE_WEIGHTS["high_frequency"]
        + factors["account_age"] * SCORE_WEIGHTS["new_account"]
        + factors["zone_boundary"] * SCORE_WEIGHTS["zone_boundary"]
    )

    # Normalize to 0-1 range
    max_weighted = sum(v for k, v in SCORE_WEIGHTS.items() if k != "duplicate_claim")
    score = min(1.0, weighted_sum / max_weighted)

    # Determine recommendation
    if score < FRAUD_THRESHOLDS["auto_approve"]:
        recommendation = "approve"
        reason = "Low risk - auto approved"
    elif score < FRAUD_THRESHOLDS["review_required"]:
        recommendation = "review"
        reason = "Moderate risk - manual review required"
    elif score < FRAUD_THRESHOLDS["auto_reject"]:
        recommendation = "review"
        reason = "High risk - urgent review required"
    else:
        recommendation = "reject"
        reason = "Very high risk - auto rejected"

    return {
        "score": round(score, 3),
        "factors": factors,
        "recommendation": recommendation,
        "reason": reason,
    }
````

--- FILE: backend/app/services/ml_service.py ---
``python
"""
ml_service.py
-----------------------------------------------------------------------------
RapidCover ML Service - Three models wrapped as ML-shaped interfaces.
Source: RapidCover Phase 2 Team Guide, Guidewire DEVTrails 2026.

Model 1 - Zone Risk Scorer
  Algorithm : XGBoost Classifier (manually calibrated weights)
  Interface : zone_risk_model.predict(zone_features) -> score 0-100

Model 2 - Dynamic Premium Engine
  Algorithm : Gradient Boosted Regression (manually calibrated)
  Interface : premium_model.predict(partner_features) -> weekly premium Rs.

Model 3 - Fraud Anomaly Detector
  Algorithm : Isolation Forest (manually calibrated 7-factor scorer)
  Interface : fraud_model.score(claim_features) -> fraud score 0-1

IMPORTANT: Weights are manually calibrated for hackathon demo.
In production, replace with trained scikit-learn/XGBoost models.
Interfaces are drop-in replaceable with real models.
-----------------------------------------------------------------------------
"""

from dataclasses import dataclass


# ------------------------------------------------------------------------------
# INPUT DATACLASSES
# ------------------------------------------------------------------------------

@dataclass
class ZoneFeatures:
    """Features for Zone Risk Scorer (XGBoost Classifier)."""
    zone_id:                     int
    city:                        str
    avg_rainfall_mm_per_hr:      float
    flood_events_2yr:            int
    aqi_avg_annual:              float
    aqi_severe_days_2yr:         int
    heat_advisory_days_2yr:      int
    bandh_events_2yr:            int
    dark_store_suspensions_2yr:  int
    road_flood_prone:            bool
    month:                       int   # 1-12


@dataclass
class PartnerFeatures:
    """Features for Dynamic Premium Engine (Gradient Boosted Regression)."""
    partner_id:           int
    city:                 str
    zone_risk_score:      float   # 0-100
    active_days_last_30:  int
    avg_hours_per_day:    float
    tier:                 str     # flex | standard | pro
    loyalty_weeks:        int
    month:                int
    riqi_score:           float   # 0-100


@dataclass
class ClaimFeatures:
    """
    Features for Fraud Anomaly Detector (Isolation Forest).

    Exact 7 factors from Section 3.3 of team guide:
      w1=0.25 gps_coherence
      w2=0.25 run_count_check
      w3=0.15 zone_polygon_match
      w4=0.15 claim_frequency_score
      w5=0.10 device_fingerprint_match
      w6=0.05 traffic_cross_check
      w7=0.05 centroid_drift_score
    """
    partner_id:               int
    zone_id:                  int
    gps_in_zone:              bool    # w1: within 500m of dark store
    run_count_during_event:   int     # w2: any run = hard reject
    zone_polygon_match:       bool    # w3: zone confirmed in event polygon
    claims_last_30_days:      int     # w4: frequency check
    device_consistent:        bool    # w5: fingerprint match
    traffic_disrupted:        bool    # w6: at least 1 road blocked
    centroid_drift_km:        float   # w7: 30-day centroid vs dark store
    max_gps_velocity_kmh:     float   # hard check: >60 = spoof
    zone_suspended:           bool    # hard gate: must be confirmed


# ------------------------------------------------------------------------------
# MODEL 1 - ZONE RISK SCORER (XGBoost Classifier)
# ------------------------------------------------------------------------------

class ZoneRiskModel:
    """
    XGBoost Classifier - manually calibrated weights.
    Output: risk score 0-100 per dark store zone.

    Feature weights (manually calibrated, NOT trained on real data):
      W_RAINFALL   = 0.30
      W_AQI        = 0.20
      W_SUSPENSION = 0.15
      W_HEAT       = 0.12
      W_BANDH      = 0.10
      W_ROAD_FLOOD = 0.08
      W_SEASONAL   = 0.05
    """

    W_RAINFALL   = 0.30
    W_AQI        = 0.20
    W_SUSPENSION = 0.15
    W_HEAT       = 0.12
    W_BANDH      = 0.10
    W_ROAD_FLOOD = 0.08
    W_SEASONAL   = 0.05

    CAP_RAINFALL   = 80.0
    CAP_AQI_DAYS   = 60
    CAP_HEAT_DAYS  = 30
    CAP_BANDH      = 10
    CAP_SUSPENSION = 8

    # High-risk months per city - from Section 2C
    HIGH_RISK_MONTHS: dict = {
        "bangalore": {6, 7, 8, 9},
        "mumbai":    {7, 8, 9},
        "delhi":     {10, 11, 12, 1},
        "chennai":   {10, 11, 12},
        "hyderabad": {7, 8, 9},
        "kolkata":   {6, 7, 8, 9},
    }

    def predict(self, features: ZoneFeatures) -> float:
        """Returns risk score 0-100. Mimics XGBoost.predict_proba() x 100."""
        city = features.city.lower()

        f_rainfall   = min(features.avg_rainfall_mm_per_hr       / self.CAP_RAINFALL, 1.0)
        f_aqi        = min(features.aqi_severe_days_2yr          / self.CAP_AQI_DAYS, 1.0)
        f_heat       = min(features.heat_advisory_days_2yr       / self.CAP_HEAT_DAYS, 1.0)
        f_bandh      = min(features.bandh_events_2yr             / self.CAP_BANDH, 1.0)
        f_suspension = min(features.dark_store_suspensions_2yr   / self.CAP_SUSPENSION, 1.0)
        f_road       = 1.0 if features.road_flood_prone else 0.0
        f_seasonal   = 1.0 if features.month in self.HIGH_RISK_MONTHS.get(city, set()) else 0.0

        score = (
            self.W_RAINFALL   * f_rainfall   +
            self.W_AQI        * f_aqi        +
            self.W_HEAT       * f_heat       +
            self.W_BANDH      * f_bandh      +
            self.W_SUSPENSION * f_suspension +
            self.W_ROAD_FLOOD * f_road       +
            self.W_SEASONAL   * f_seasonal
        ) * 100

        return round(min(max(score, 0.0), 100.0), 2)


# ------------------------------------------------------------------------------
# MODEL 2 - DYNAMIC PREMIUM ENGINE (Gradient Boosted Regression)
# ------------------------------------------------------------------------------

class PremiumModel:
    """
    Gradient Boosted Regression - manually calibrated multiplicative formula.

    Full formula from Section 3.1 of team guide:
      Weekly Premium =
        Base (trigger_probability x avg_income_lost_per_day x days_exposed)
        x city_peril_multiplier
        x zone_risk_score_multiplier (0.8-1.4)
        x seasonal_index (city-specific monthly - NOT flat national index)
        x activity_tier_factor (Flex=0.8, Standard=1.0, Pro=1.35)
        x RIQI_adjustment (urban_core=1.0, urban_fringe=1.15, peri_urban=1.3)
        x loyalty_discount (1.0 -> 0.94 after 4 weeks -> 0.90 after 12)
      Capped at 3x base tier (IRDAI microinsurance cap)
    """

    # Fixed base prices per final specification table:
    # Flex:     Rs.22 (Max Weekly Rs.500, Ratio ~1:23)
    # Standard: Rs.33 (Max Weekly Rs.1200, Ratio ~1:36)
    # Pro:      Rs.45 (Max Weekly Rs.2000, Ratio ~1:44)
    BASE_PRICES    = {"flex": 22, "standard": 33, "pro": 45}
    CAP_MULTIPLIER = 3.0  # IRDAI microinsurance cap

    # Activity tier factor - exact values from Section 3.1
    ACTIVITY_TIER_FACTOR = {"flex": 0.80, "standard": 1.00, "pro": 1.35}

    # City peril multipliers (actuarially calibrated)
    CITY_PERIL: dict = {
        "mumbai":    1.30,
        "kolkata":   1.25,
        "chennai":   1.22,
        "bangalore": 1.18,
        "hyderabad": 1.15,
        "delhi":     1.10,
    }

    # City-specific seasonal multipliers - per Section 2C, NOT flat national index
    SEASONAL_INDEX: dict = {
        "bangalore": {6: 1.20, 7: 1.20, 8: 1.20, 9: 1.20},    # +20% Jun-Sep
        "mumbai":    {7: 1.25, 8: 1.25, 9: 1.25},              # +25% Jul-Sep
        "delhi":     {10: 1.18, 11: 1.18, 12: 1.18, 1: 1.18},  # +18% Oct-Jan
        "chennai":   {10: 1.22, 11: 1.22, 12: 1.22},           # +22% Oct-Dec
        "hyderabad": {7: 1.15, 8: 1.15, 9: 1.15},              # +15% Jul-Sep
        "kolkata":   {6: 1.20, 7: 1.20, 8: 1.20, 9: 1.20},    # +20% Jun-Sep
    }

    # RIQI adjustment - exact values from Section 3.1
    RIQI_ADJUSTMENT: dict = {
        "urban_core":   1.00,   # RIQI > 70
        "urban_fringe": 1.15,   # RIQI 40-70
        "peri_urban":   1.30,   # RIQI < 40
    }

    def _riqi_band(self, riqi_score: float) -> str:
        if riqi_score > 70:
            return "urban_core"
        elif riqi_score >= 40:
            return "urban_fringe"
        return "peri_urban"

    def _seasonal(self, city: str, month: int) -> float:
        return self.SEASONAL_INDEX.get(city.lower(), {}).get(month, 1.0)

    def _loyalty(self, loyalty_weeks: int) -> float:
        """Returns loyalty multiplier. Exact values from Section 3.1."""
        if loyalty_weeks >= 12:
            return 0.90
        elif loyalty_weeks >= 4:
            return 0.94
        return 1.0

    def predict(self, features: PartnerFeatures) -> dict:
        """
        Returns weekly_premium (Rs.) + full itemised breakdown.
        Mimics GradientBoostingRegressor.predict().
        """
        tier = features.tier.lower()
        base = self.BASE_PRICES.get(tier, self.BASE_PRICES["standard"])
        city = features.city.lower()

        # Base component: trigger_probability x avg_income_lost x days_exposed
        trigger_probability     = 0.09    # ~1 claim per 11 weeks baseline
        avg_income_lost_per_day = 500.0   # Rs.500 midpoint (range Rs.420-Rs.720 from doc)
        days_exposed            = min(features.active_days_last_30 / 26.0, 1.0)

        # Multipliers (exact per Section 3.1)
        city_peril            = self.CITY_PERIL.get(city, 1.0)
        zone_risk_multiplier  = 0.8 + (features.zone_risk_score / 100.0) * 0.6  # 0.8-1.4
        seasonal_index        = self._seasonal(city, features.month)
        activity_tier_factor  = self.ACTIVITY_TIER_FACTOR[tier]
        riqi_band             = self._riqi_band(features.riqi_score)
        riqi_adjustment       = self.RIQI_ADJUSTMENT[riqi_band]
        loyalty_discount      = self._loyalty(features.loyalty_weeks)

        # Apply full formula
        base_component = trigger_probability * avg_income_lost_per_day * days_exposed
        adjusted = (
            base_component       *
            city_peril           *
            zone_risk_multiplier *
            seasonal_index       *
            activity_tier_factor *
            riqi_adjustment      *
            loyalty_discount
        )

        # Scale to Rs. (keep in meaningful range above base price)
        raw_premium    = base + (adjusted * 0.08)
        cap            = base * self.CAP_MULTIPLIER
        weekly_premium = round(min(max(raw_premium, base), cap))

        return {
            "weekly_premium":  int(weekly_premium),
            "base_price":      base,
            "tier":            tier,
            "cap_value":       int(cap),
            "cap_applied":     weekly_premium >= cap,
            "breakdown": {
                "trigger_probability":      trigger_probability,
                "avg_income_lost_per_day":  avg_income_lost_per_day,
                "days_exposed_factor":      round(days_exposed, 3),
                "city_peril_multiplier":    city_peril,
                "zone_risk_multiplier":     round(zone_risk_multiplier, 3),
                "seasonal_index":           seasonal_index,
                "activity_tier_factor":     activity_tier_factor,
                "riqi_adjustment":          riqi_adjustment,
                "riqi_band":                riqi_band,
                "loyalty_discount":         loyalty_discount,
            },
        }


# ------------------------------------------------------------------------------
# MODEL 3 - FRAUD ANOMALY DETECTOR (Isolation Forest)
# ------------------------------------------------------------------------------

class FraudModel:
    '''
    Isolation Forest - manually calibrated 7-factor anomaly scorer.
    
    EXACT weights from Section 3.3 of team guide:
      w1 = 0.25 gps_coherence
      w2 = 0.25 run_count_check
      w3 = 0.15 zone_polygon_match
      w4 = 0.15 claim_frequency_score
      w5 = 0.10 device_fingerprint_match
      w6 = 0.05 traffic_cross_check
      w7 = 0.05 centroid_drift_score - Section 2 F addition

    Score thresholds (Section 3.3):
      < 0.50      -> auto_approve
      0.50 - 0.75 -> enhanced_validation
      0.75 - 0.90 -> manual_review
      > 0.90      -> auto_reject

    Hard rejects (override score regardless):
      - GPS velocity > 60 km/h (Section 2 F velocity physics check)
      - Zone not suspended     (Section 4.2 step 4)
      - Run count > 0          (Activity Paradox, Section 4.2 step 7)

    NOTE: Weights manually calibrated - not trained on real data.
    Centroid drift > 15km -> manual review flag (Section 2 F).
    '''
    
    # Exact weights from Section 3.3
    W1_GPS_COHERENCE       = 0.25
    W2_RUN_COUNT           = 0.25
    W3_ZONE_POLYGON        = 0.15
    W4_CLAIM_FREQUENCY     = 0.15
    W5_DEVICE_FINGERPRINT  = 0.10
    W6_TRAFFIC_CROSS_CHECK = 0.05
    W7_CENTROID_DRIFT      = 0.05   # w7 = 0.05 per spec

    VELOCITY_SPOOF_KMH   = 60.0    # Section 2F: >60km/h = spoof
    CENTROID_FLAG_KM     = 15.0    # Section 2F: >15km = manual review
    MAX_CLEAN_CLAIMS_30D = 3

    def score(self, features: ClaimFeatures) -> dict:
        """
        Returns fraud score 0-1, decision, factor breakdown.
        Mimics IsolationForest.decision_function() normalised 0-1.
        """
        hard_reject_reasons = []

        # -- Hard pre-checks -----------------------------------------------
        if features.max_gps_velocity_kmh > self.VELOCITY_SPOOF_KMH:
            hard_reject_reasons.append(
                f"GPS velocity {features.max_gps_velocity_kmh:.1f} km/h "
                f"exceeds {self.VELOCITY_SPOOF_KMH} km/h - spoof detected"
            )
        if not features.zone_suspended:
            hard_reject_reasons.append("Zone suspension not confirmed by platform API")
        if features.run_count_during_event > 0:
            hard_reject_reasons.append(
                f"Activity Paradox: {features.run_count_during_event} "
                f"run(s) completed during suspended window"
            )

        # -- w1: GPS coherence ---------------------------------------------
        f1 = 0.0 if features.gps_in_zone else 1.0

        # -- w2: Run count check -------------------------------------------
        f2 = 1.0 if features.run_count_during_event > 0 else 0.0

        # -- w3: Zone polygon match ----------------------------------------
        f3 = 0.0 if features.zone_polygon_match else 1.0

        # -- w4: Claim frequency -------------------------------------------
        f4 = min(features.claims_last_30_days / self.MAX_CLEAN_CLAIMS_30D, 1.0)

        # -- w5: Device fingerprint ----------------------------------------
        f5 = 0.0 if features.device_consistent else 1.0

        # -- w6: Traffic cross-check ---------------------------------------
        f6 = 0.0 if features.traffic_disrupted else 1.0

        # -- w7: Centroid drift (w7=0.05) ----------------------------------
        if features.centroid_drift_km > self.CENTROID_FLAG_KM:
            f7 = 1.0
            if features.centroid_drift_km not in [r for r in hard_reject_reasons]:
                hard_reject_reasons.append(
                    f"Centroid drift {features.centroid_drift_km:.1f} km "
                    f"exceeds {self.CENTROID_FLAG_KM} km - manual review"
                )
        else:
            f7 = features.centroid_drift_km / self.CENTROID_FLAG_KM

        # -- Weighted score ------------------------------------------------
        fraud_score = (
            self.W1_GPS_COHERENCE       * f1 +
            self.W2_RUN_COUNT           * f2 +
            self.W3_ZONE_POLYGON        * f3 +
            self.W4_CLAIM_FREQUENCY     * f4 +
            self.W5_DEVICE_FINGERPRINT  * f5 +
            self.W6_TRAFFIC_CROSS_CHECK * f6 +
            self.W7_CENTROID_DRIFT      * f7
        )
        fraud_score = round(min(max(fraud_score, 0.0), 1.0), 4)

        # -- Decision ------------------------------------------------------
        if hard_reject_reasons:
            decision    = "auto_reject"
            fraud_score = max(fraud_score, 0.91)
        elif fraud_score < 0.50:
            decision = "auto_approve"
        elif fraud_score < 0.75:
            decision = "enhanced_validation"
        elif fraud_score < 0.90:
            decision = "manual_review"
        else:
            decision = "auto_reject"

        return {
            "fraud_score": fraud_score,
            "decision":    decision,
            "factors": {
                "w1_gps_coherence":      round(1 - f1, 2),
                "w2_run_count_clean":    round(1 - f2, 2),
                "w3_zone_polygon_match": round(1 - f3, 2),
                "w4_claim_frequency":    round(f4, 2),
                "w5_device_consistent":  round(1 - f5, 2),
                "w6_traffic_disrupted":  round(1 - f6, 2),
                "w7_centroid_drift_km":  features.centroid_drift_km,
            },
            "weights": {
                "w1": self.W1_GPS_COHERENCE,
                "w2": self.W2_RUN_COUNT,
                "w3": self.W3_ZONE_POLYGON,
                "w4": self.W4_CLAIM_FREQUENCY,
                "w5": self.W5_DEVICE_FINGERPRINT,
                "w6": self.W6_TRAFFIC_CROSS_CHECK,
                "w7": self.W7_CENTROID_DRIFT,
            },
            "hard_reject_reasons": hard_reject_reasons,
        }


# ------------------------------------------------------------------------------
# SINGLETONS - import these everywhere
# ------------------------------------------------------------------------------

zone_risk_model = ZoneRiskModel()
premium_model   = PremiumModel()
fraud_model     = FraudModel()
````

--- FILE: backend/app/services/premium_service.py ---
``python
"""
premium_service.py
-----------------------------------------------------------------------------
RapidCover Premium Engine - pricing, underwriting gates, RIQI scoring,
payout calculation, zone pool share cap, sustained event protocol.

Source: RapidCover Phase 2 Team Guide, Guidewire DEVTrails 2026.

# Fixed pricing tiers based on specification image:
# Flex (Part-time)    = Rs.22/week | Max payout Rs.250/day | 2 days/week | Max Rs.500/week | Ratio ~1:23
# Standard (Full-time) = Rs.33/week | Max payout Rs.400/day | 3 days/week | Max Rs.1200/week | Ratio ~1:36
# Pro (Peak rider)    = Rs.45/week | Max payout Rs.500/day | 4 days/week | Max Rs.2000/week | Ratio ~1:44

Algorithm: Gradient Boosted Regression (manually calibrated weights).
-----------------------------------------------------------------------------
"""

from datetime import date
from typing import Optional

from app.services.ml_service import (
    premium_model,
    PartnerFeatures,
)


# ------------------------------------------------------------------------------
# TIER CONFIGURATION
# ------------------------------------------------------------------------------

TIER_CONFIG: dict = {
    "flex": {
        "weekly_premium":  22,
        "max_payout_day":  250,  # Max Weekly = 250 * 2 = 500. Ratio = 500/22 = 22.7
        "max_days_week":   2,
        "label":           "[FLEX] âš¡ Flex (Part-time)",
        "best_for":        "Part-time, 4â€“5 hrs/day",
    },
    "standard": {
        "weekly_premium":  33,
        "max_payout_day":  400,  # Max Weekly = 400 * 3 = 1200. Ratio = 1200/33 = 36.3
        "max_days_week":   3,
        "label":           "[STANDARD] ðŸ›µ Standard (Full-time)",
        "best_for":        "Full-time, 8â€“10 hrs/day",
    },
    "pro": {
        "weekly_premium":  45,
        "max_payout_day":  500,  # Max Weekly = 500 * 4 = 2000. Ratio = 2000/45 = 44.4
        "max_days_week":   4,
        "label":           "[PRO] ðŸ† Pro (Peak rider)",
        "best_for":        "Peak warriors, 12+ hrs/day",
    },
}

# Underwriting gate thresholds - Section 2A of team guide
MIN_ACTIVE_DAYS_TO_BUY   = 7   # Minimum 7 active days before cover starts
AUTO_DOWNGRADE_DAYS      = 5   # auto-downgrade to Flex if < 5 active days in last 30

# Demo exception: Delhi zones skip the 7-day check (for judging demo)
DEMO_EXEMPT_CITIES = ["Delhi", "Bangalore", "Mumbai", "Kolkata", "Chennai", "Hyderabad"]  # Partners in these cities bypass MIN_ACTIVE_DAYS check

# Sustained event protocol - Section 2E
SUSTAINED_EVENT_THRESHOLD_DAYS   = 5     # trigger fires 5+ consecutive days â†’ Sustained Event
SUSTAINED_EVENT_PAYOUT_FACTOR    = 0.70  # 70% of daily tier payout in sustained mode
SUSTAINED_EVENT_MAX_DAYS         = 21    # max coverage in sustained event mode
REINSURANCE_REVIEW_DAY           = 7     # flag reinsurance at day 7
CITY_PAYOUT_CAP_PCT              = 1.20  # city-level payout capped at 120% of weekly pool


# ------------------------------------------------------------------------------
# RIQI ZONE SCORING
# ------------------------------------------------------------------------------

# RIQI = Road Infrastructure Quality Index (0â€“100)
# 0 = worst roads, 100 = best roads
# Higher RIQI = better infrastructure = less disruption per mm of rain
# Derived from: OpenStreetMap + NDMA flood maps + suspension history
# NOTE: These are hardcoded city-level defaults for demo.
# In production: compute per dark-store zone polygon.

CITY_RIQI_SCORES: dict = {
    "bangalore": 62.0,   # Bellandur flood-prone, mixed infrastructure
    "mumbai":    45.0,   # Urban fringe zones heavily flood-prone
    "delhi":     58.0,   # Mixed - Anand Vihar vs Dwarka very different
    "chennai":   55.0,   # Coastal + NE monsoon exposure
    "hyderabad": 68.0,   # Relatively better road infrastructure
    "kolkata":   42.0,   # Low-lying, cyclone exposure, older roads
}

# Payout multipliers per RIQI band (Section 3.2 / Section 2B)
RIQI_PAYOUT_MULTIPLIER: dict = {
    "urban_core":   1.00,   # RIQI > 70 - better roads, less disruption
    "urban_fringe": 1.25,   # RIQI 40â€“70
    "peri_urban":   1.50,   # RIQI < 40 - poor roads, max disruption
}

# Premium adjustment for low-RIQI (higher risk = higher premium)
RIQI_PREMIUM_ADJUSTMENT: dict = {
    "urban_core":   1.00,
    "urban_fringe": 1.15,
    "peri_urban":   1.30,
}


def get_riqi_score(city: str, zone_id: Optional[int] = None) -> float:
    """Return RIQI score for city. In production: per zone polygon."""
    return CITY_RIQI_SCORES.get(city.lower(), 55.0)


def get_riqi_band(riqi_score: float) -> str:
    """Return RIQI band label."""
    if riqi_score > 70:
        return "urban_core"
    elif riqi_score >= 40:
        return "urban_fringe"
    return "peri_urban"


def get_riqi_payout_multiplier(city: str, zone_id: Optional[int] = None) -> float:
    """Return payout multiplier (1.0 / 1.25 / 1.5) for zone."""
    riqi = get_riqi_score(city, zone_id)
    band = get_riqi_band(riqi)
    return RIQI_PAYOUT_MULTIPLIER[band]


# ------------------------------------------------------------------------------
# UNDERWRITING GATE
# ------------------------------------------------------------------------------

def check_underwriting_gate(active_days_last_30: int) -> dict:
    """
    Block policy purchase if < 7 active delivery days in last 30.
    Section 2A of team guide.
    """
    if active_days_last_30 < MIN_ACTIVE_DAYS_TO_BUY:
        return {
            "allowed": False,
            "reason":  (
                f"Cover starts after you complete {MIN_ACTIVE_DAYS_TO_BUY} active "
                f"delivery days. You have {active_days_last_30} active days in the last 30."
            ),
        }
    return {"allowed": True, "reason": None}


def apply_auto_downgrade(tier: str, active_days_last_30: int) -> tuple:
    """
    Auto-downgrade to Flex if < 5 active days in last 30.
    Workers cannot self-select Standard or Pro if activity does not match.
    Section 2A of team guide.

    Returns (effective_tier, was_downgraded)
    """
    if active_days_last_30 < AUTO_DOWNGRADE_DAYS and tier != "flex":
        return "flex", True
    return tier, False


# ------------------------------------------------------------------------------
# WEEKLY PREMIUM CALCULATOR
# ------------------------------------------------------------------------------

def calculate_weekly_premium(
    partner_id:          int,
    city:                str,
    zone_id:             Optional[int],
    requested_tier:      str,
    active_days_last_30: int,
    avg_hours_per_day:   float,
    loyalty_weeks:       int,
) -> dict:
    """
    Full premium calculation pipeline. Called every Monday 6AM for renewal.

    Steps:
      1. Underwriting gate
      2. Auto-downgrade check
      3. RIQI score lookup
      4. premium_model.predict() with all features
      5. Return premium + full itemised breakdown

    Every number is traceable to a formula - per team guide Section 3.
    """
    # Step 1: Underwriting gate
    gate = check_underwriting_gate(active_days_last_30)
    if not gate["allowed"]:
        return {"allowed": False, "gate_reason": gate["reason"], "weekly_premium": None}

    # Step 2: Auto-downgrade
    effective_tier, was_downgraded = apply_auto_downgrade(requested_tier, active_days_last_30)

    # Step 3: RIQI
    riqi_score = get_riqi_score(city, zone_id)
    riqi_band  = get_riqi_band(riqi_score)

    # Step 4: ML model predict
    features = PartnerFeatures(
        partner_id          = partner_id,
        city                = city,
        zone_risk_score     = riqi_score,
        active_days_last_30 = active_days_last_30,
        avg_hours_per_day   = avg_hours_per_day,
        tier                = effective_tier,
        loyalty_weeks       = loyalty_weeks,
        month               = date.today().month,
        riqi_score          = riqi_score,
    )
    result = premium_model.predict(features)
    tier_cfg = TIER_CONFIG[effective_tier]

    return {
        "allowed":          True,
        "gate_reason":      None,
        "weekly_premium":   result["weekly_premium"],
        "base_price":       result["base_price"],
        "tier":             effective_tier,
        "tier_label":       tier_cfg["label"],
        "max_payout_day":   tier_cfg["max_payout_day"],
        "max_days_week":    tier_cfg["max_days_week"],
        "was_downgraded":   was_downgraded,
        "downgrade_reason": (
            f"Auto-downgraded to Flex: only {active_days_last_30} active days "
            f"in last 30 (minimum {AUTO_DOWNGRADE_DAYS} for {requested_tier})"
        ) if was_downgraded else None,
        "riqi": {
            "score":              riqi_score,
            "band":               riqi_band,
            "payout_multiplier":  RIQI_PAYOUT_MULTIPLIER[riqi_band],
            "premium_adjustment": RIQI_PREMIUM_ADJUSTMENT[riqi_band],
        },
        "breakdown":  result["breakdown"],
        "cap_applied": result["cap_applied"],
        "cap_value":   result["cap_value"],
    }


# ------------------------------------------------------------------------------
# PAYOUT CALCULATOR
# ------------------------------------------------------------------------------

def calculate_payout(
    tier:                str,
    disruption_hours:    float,
    avg_hourly_earning:  float,
    city:                str,
    zone_id:             Optional[int] = None,
    consecutive_days:    int = 1,
) -> dict:
    """
    Payout formula from Section 3.2 of team guide:

      Payout = disruption_hours Ã— hourly_earning_baseline Ã— zone_disruption_multiplier
      Capped at: daily_tier_max Ã— eligible_disruption_days

    Sustained Event Mode (5+ consecutive days, Section 2E):
      Payout_per_day = 0.70 Ã— daily_tier_max, no weekly cap, max 21 days
    """
    tier_cfg         = TIER_CONFIG.get(tier.lower(), TIER_CONFIG["standard"])
    riqi_multiplier  = get_riqi_payout_multiplier(city, zone_id)
    sustained_event  = consecutive_days >= SUSTAINED_EVENT_THRESHOLD_DAYS

    if sustained_event:
        # Sustained event mode: 70% of daily max, no weekly cap, up to 21 days
        daily_payout    = tier_cfg["max_payout_day"] * SUSTAINED_EVENT_PAYOUT_FACTOR
        eligible_days   = min(consecutive_days, SUSTAINED_EVENT_MAX_DAYS)
        raw_payout      = daily_payout * min(disruption_hours / 8, 1.0) * riqi_multiplier
        capped_payout   = min(raw_payout, daily_payout)
        reinsurance_flag = consecutive_days >= REINSURANCE_REVIEW_DAY
    else:
        raw_payout       = disruption_hours * avg_hourly_earning * riqi_multiplier
        capped_payout    = min(raw_payout, tier_cfg["max_payout_day"])
        eligible_days    = 1
        reinsurance_flag = False

    return {
        "payout":             round(capped_payout, 2),
        "raw_payout":         round(raw_payout, 2),
        "cap_applied":        raw_payout > tier_cfg["max_payout_day"],
        "max_payout_day":     tier_cfg["max_payout_day"],
        "riqi_multiplier":    riqi_multiplier,
        "disruption_hours":   disruption_hours,
        "hourly_rate":        avg_hourly_earning,
        "sustained_event":    sustained_event,
        "consecutive_days":   consecutive_days,
        "reinsurance_flag":   reinsurance_flag,
    }


# ------------------------------------------------------------------------------
# ZONE POOL SHARE CAP (Mass Event)
# ------------------------------------------------------------------------------

def calculate_zone_pool_share(
    calculated_payout:       float,
    city_weekly_reserve:     float,
    zone_density_weight:     float,
    total_partners_in_event: int,
) -> dict:
    """
    Zone Pool Share formula from Section 3.5 / Section 2D of team guide:

      payout_per_partner = min(calculated_payout, zone_pool_share)
      zone_pool_share = city_weekly_reserve Ã— zone_density_weight / partners_in_event
      City hard cap: total event payout â‰¤ 120% of city weekly premium pool

    zone_density_weight by density band:
      Low  (<50 partners):    0.15
      Medium (50â€“150):        0.35
      High (>150):            0.50
    """
    # Demo / early lifecycle can yield a 0 reserve (no "recently created" premiums yet).
    # In that case, treat the pool cap as unavailable instead of forcing payouts to 0.
    if city_weekly_reserve <= 0:
        final_payout = calculated_payout
        zone_pool_share = 0.0
        pool_cap_applied = False
    else:
        zone_pool_share = (city_weekly_reserve * zone_density_weight) / max(total_partners_in_event, 1)
        final_payout = min(calculated_payout, zone_pool_share)
        pool_cap_applied = calculated_payout > zone_pool_share

    return {
        "final_payout":       round(final_payout, 2),
        "calculated_payout":  calculated_payout,
        "zone_pool_share":    round(zone_pool_share, 2),
        "pool_cap_applied":   pool_cap_applied,
        "reduction_amount":   round(calculated_payout - final_payout, 2) if pool_cap_applied else 0,
    }


# ------------------------------------------------------------------------------
# PLAN QUOTES (onboarding)
# ------------------------------------------------------------------------------

def get_plan_quotes(
    city:                str,
    zone_id:             Optional[int],
    active_days_last_30: int,
    avg_hours_per_day:   float,
    loyalty_weeks:       int = 0,
) -> list:
    """
    Returns personalised quotes for all 3 tiers.
    Called at onboarding after GPS zone detection - Section 4.1 step 5.
    """
    quotes = []
    for tier in ["flex", "standard", "pro"]:
        quote = calculate_weekly_premium(
            partner_id          = 0,
            city                = city,
            zone_id             = zone_id,
            requested_tier      = tier,
            active_days_last_30 = active_days_last_30,
            avg_hours_per_day   = avg_hours_per_day,
            loyalty_weeks       = loyalty_weeks,
        )
        quote["tier_config"] = TIER_CONFIG[tier]
        quotes.append(quote)
    return quotes


# ------------------------------------------------------------------------------
# BCR / LOSS RATIO
# ------------------------------------------------------------------------------

def calculate_bcr(total_claims_paid: float, total_premiums_collected: float) -> dict:
    """
    BCR (Burning Cost Rate) = total_claims_paid / total_premiums_collected
    Section 3.4 of team guide.

    Target BCR: 0.55â€“0.70 (65p per Rs.1 goes to payouts)
    Loss Ratio = BCR Ã— 100
    > 85% â†’ suspend new enrolments in that city
    > 100% â†’ reinsurance treaty activation
    """
    if total_premiums_collected <= 0:
        return {"bcr": 0, "loss_ratio": 0, "status": "no_data"}

    bcr         = total_claims_paid / total_premiums_collected
    loss_ratio  = round(bcr * 100, 2)

    if loss_ratio > 100:
        status = "reinsurance_activation"
    elif loss_ratio > 85:
        status = "suspend_enrolments"
    elif loss_ratio > 70:
        status = "warning"
    elif loss_ratio >= 55:
        status = "healthy"
    else:
        status = "below_target"

    return {
        "bcr":                    round(bcr, 4),
        "loss_ratio":             loss_ratio,
        "status":                 status,
        "suspend_enrolments":     loss_ratio > 85,
        "reinsurance_trigger":    loss_ratio > 100,
        "target_range":           "55â€“70%",
    }
````

--- FILE: backend/app/services/trigger_detector.py ---
``python
"""
Trigger detection service for parametric insurance events.

Monitors external data sources and creates TriggerEvents when thresholds are breached.
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.trigger_event import TriggerEvent, TriggerType, TRIGGER_THRESHOLDS
from app.models.zone import Zone
from app.services.claims_processor import process_trigger_event
from app.services.external_apis import (
    MockWeatherAPI,
    MockAQIAPI,
    MockPlatformAPI,
    MockCivicAPI,
    WeatherData,
    AQIData,
    PlatformStatus,
    ShutdownStatus,
    get_partial_disruption_data,
)


# Sustained Event Tracking
# Tracks consecutive days of same trigger type in same zone
# Key format: "{zone_id}:{trigger_type}" -> list of date strings
_sustained_events: dict[str, list[str]] = {}

# Sustained event thresholds
SUSTAINED_EVENT_THRESHOLD_DAYS = 5  # Days before sustained mode activates
SUSTAINED_EVENT_MAX_DAYS = 21  # Maximum days for sustained payout
SUSTAINED_EVENT_PAYOUT_MODIFIER = 0.70  # 70% payout per day in sustained mode


def track_sustained_event(zone_id: int, trigger_type: TriggerType, event_date: datetime = None) -> dict:
    """
    Track consecutive trigger events for sustained event detection.

    When same trigger fires 5+ consecutive days in same zone:
    - Raises 'Sustained Event' flag
    - Switches to 70% payout per day
    - Bypasses weekly cap
    - Maximum 21 days

    Returns dict with:
    - is_sustained: bool - True if 5+ consecutive days
    - consecutive_days: int - Number of consecutive days
    - payout_modifier: float - 1.0 normal, 0.70 for sustained
    - max_days_reached: bool - True if 21 days reached
    - bypass_weekly_cap: bool - True for sustained events
    """
    if event_date is None:
        event_date = datetime.utcnow()

    key = f"{zone_id}:{trigger_type.value}"
    dates = _sustained_events.get(key, [])
    date_str = event_date.strftime("%Y-%m-%d")

    # Add date if not already tracked
    if date_str not in dates:
        dates.append(date_str)
        dates = sorted(dates)[-SUSTAINED_EVENT_MAX_DAYS:]  # Keep last 21 days
        _sustained_events[key] = dates

    # Count consecutive days ending with today/event_date
    consecutive = 1
    sorted_dates = sorted(dates, reverse=True)

    for i in range(len(sorted_dates) - 1):
        curr = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
        prev = datetime.strptime(sorted_dates[i + 1], "%Y-%m-%d")
        if (curr - prev).days == 1:
            consecutive += 1
        else:
            break

    is_sustained = consecutive >= SUSTAINED_EVENT_THRESHOLD_DAYS
    max_days_reached = consecutive >= SUSTAINED_EVENT_MAX_DAYS

    return {
        "is_sustained": is_sustained,
        "consecutive_days": consecutive,
        "payout_modifier": SUSTAINED_EVENT_PAYOUT_MODIFIER if is_sustained else 1.0,
        "max_days_reached": max_days_reached,
        "bypass_weekly_cap": is_sustained,
    }


def inject_sustained_event_history(zone_id: int, trigger_type: TriggerType, days: int = 5) -> dict:
    """
    Inject fake consecutive days history for demo purposes.

    This allows testing the 70% sustained event payout without waiting 5 real days.
    Call this BEFORE running a drill to simulate being on day N of a sustained event.

    Args:
        zone_id: Zone to inject history for
        trigger_type: Trigger type (rain, heat, etc.)
        days: Number of consecutive days to simulate (default 5 for 70% payout)

    Returns:
        Dict with injected dates and expected payout modifier
    """
    key = f"{zone_id}:{trigger_type.value}"
    today = datetime.utcnow()

    # Generate N-1 previous consecutive days (today will be added when drill runs)
    injected_dates = []
    for i in range(days - 1, 0, -1):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        injected_dates.append(date_str)

    _sustained_events[key] = injected_dates

    return {
        "zone_id": zone_id,
        "trigger_type": trigger_type.value,
        "injected_days": days - 1,
        "dates": injected_dates,
        "next_run_will_be_day": days,
        "payout_modifier_expected": SUSTAINED_EVENT_PAYOUT_MODIFIER if days >= SUSTAINED_EVENT_THRESHOLD_DAYS else 1.0,
    }


def clear_sustained_event_history(zone_id: int = None, trigger_type: TriggerType = None):
    """
    Clear sustained event history for testing.

    If zone_id and trigger_type provided, clears just that combination.
    If neither provided, clears all history.
    """
    global _sustained_events

    if zone_id is not None and trigger_type is not None:
        key = f"{zone_id}:{trigger_type.value}"
        _sustained_events.pop(key, None)
    elif zone_id is None and trigger_type is None:
        _sustained_events = {}

    return {"cleared": True}


def get_sustained_event_info(zone_id: int, trigger_type: TriggerType) -> dict:
    """
    Get current sustained event info for a zone/trigger combination without modifying state.
    """
    key = f"{zone_id}:{trigger_type.value}"
    dates = _sustained_events.get(key, [])

    if not dates:
        return {
            "is_sustained": False,
            "consecutive_days": 0,
            "payout_modifier": 1.0,
            "max_days_reached": False,
            "bypass_weekly_cap": False,
        }

    # Count consecutive days
    consecutive = 1
    sorted_dates = sorted(dates, reverse=True)

    for i in range(len(sorted_dates) - 1):
        curr = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
        prev = datetime.strptime(sorted_dates[i + 1], "%Y-%m-%d")
        if (curr - prev).days == 1:
            consecutive += 1
        else:
            break

    is_sustained = consecutive >= SUSTAINED_EVENT_THRESHOLD_DAYS

    return {
        "is_sustained": is_sustained,
        "consecutive_days": consecutive,
        "payout_modifier": SUSTAINED_EVENT_PAYOUT_MODIFIER if is_sustained else 1.0,
        "max_days_reached": consecutive >= SUSTAINED_EVENT_MAX_DAYS,
        "bypass_weekly_cap": is_sustained,
    }


def clear_sustained_event(zone_id: int, trigger_type: TriggerType) -> None:
    """
    Clear sustained event tracking for a zone/trigger combination.
    Call when a trigger event ends or conditions normalize.
    """
    key = f"{zone_id}:{trigger_type.value}"
    if key in _sustained_events:
        del _sustained_events[key]


def _calculate_severity(value: float, threshold: float) -> int:
    """
    Calculate severity level (1-5) based on how much the value exceeds threshold.

    Severity levels:
    1 = Just above threshold (100-110%)
    2 = Moderately above (110-125%)
    3 = Significantly above (125-150%)
    4 = Severely above (150-200%)
    5 = Extremely above (>200%)
    """
    ratio = value / threshold if threshold > 0 else 1

    if ratio < 1.1:
        return 1
    elif ratio < 1.25:
        return 2
    elif ratio < 1.5:
        return 3
    elif ratio < 2.0:
        return 4
    else:
        return 5


def check_rain_trigger(
    zone_id: int,
    weather_data: Optional[WeatherData] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if heavy rain/flood trigger should fire.

    Threshold: >55mm/hr sustained 30+ mins
    """
    if weather_data is None:
        weather_data = MockWeatherAPI.get_current(zone_id)

    threshold = TRIGGER_THRESHOLDS[TriggerType.RAIN]["threshold"]

    if weather_data.rainfall_mm_hr > threshold:
        severity = _calculate_severity(weather_data.rainfall_mm_hr, threshold)

        source_data = {
            "rainfall_mm_hr": weather_data.rainfall_mm_hr,
            "threshold": threshold,
            "humidity": weather_data.humidity,
            "timestamp": weather_data.timestamp.isoformat(),
        }

        # Include partial disruption data if set
        partial_data = get_partial_disruption_data(zone_id)
        if partial_data:
            source_data.update(partial_data)

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.RAIN,
            started_at=datetime.utcnow(),
            severity=severity,
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_heat_trigger(
    zone_id: int,
    weather_data: Optional[WeatherData] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if extreme heat trigger should fire.

    Threshold: >43Â°C sustained 4+ hours
    """
    if weather_data is None:
        weather_data = MockWeatherAPI.get_current(zone_id)

    threshold = TRIGGER_THRESHOLDS[TriggerType.HEAT]["threshold"]

    if weather_data.temp_celsius > threshold:
        severity = _calculate_severity(weather_data.temp_celsius, threshold)

        source_data = {
            "temp_celsius": weather_data.temp_celsius,
            "threshold": threshold,
            "humidity": weather_data.humidity,
            "timestamp": weather_data.timestamp.isoformat(),
        }

        # Include partial disruption data if set
        partial_data = get_partial_disruption_data(zone_id)
        if partial_data:
            source_data.update(partial_data)

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.HEAT,
            started_at=datetime.utcnow(),
            severity=severity,
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_aqi_trigger(
    zone_id: int,
    aqi_data: Optional[AQIData] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if dangerous AQI trigger should fire.

    Threshold: >400 for 3+ hours
    """
    if aqi_data is None:
        aqi_data = MockAQIAPI.get_current(zone_id)

    threshold = TRIGGER_THRESHOLDS[TriggerType.AQI]["threshold"]

    if aqi_data.aqi > threshold:
        severity = _calculate_severity(aqi_data.aqi, threshold)

        source_data = {
            "aqi": aqi_data.aqi,
            "threshold": threshold,
            "pm25": aqi_data.pm25,
            "pm10": aqi_data.pm10,
            "category": aqi_data.category,
            "timestamp": aqi_data.timestamp.isoformat(),
        }

        # Include partial disruption data if set
        partial_data = get_partial_disruption_data(zone_id)
        if partial_data:
            source_data.update(partial_data)

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.AQI,
            started_at=datetime.utcnow(),
            severity=severity,
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_shutdown_trigger(
    zone_id: int,
    shutdown_data: Optional[ShutdownStatus] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if civic shutdown/curfew trigger should fire.

    Threshold: 2+ hours civic closure
    """
    if shutdown_data is None:
        shutdown_data = MockCivicAPI.get_shutdown_status(zone_id)

    if shutdown_data.is_active and shutdown_data.started_at:
        # For demo, we trigger immediately when shutdown is detected
        # In production, would check duration

        source_data = {
            "reason": shutdown_data.reason,
            "started_at": shutdown_data.started_at.isoformat() if shutdown_data.started_at else None,
            "expected_end": shutdown_data.expected_end.isoformat() if shutdown_data.expected_end else None,
            "timestamp": shutdown_data.timestamp.isoformat(),
        }

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.SHUTDOWN,
            started_at=shutdown_data.started_at or datetime.utcnow(),
            severity=3,  # Default severity for civic shutdowns
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_closure_trigger(
    zone_id: int,
    platform_data: Optional[PlatformStatus] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if dark store closure trigger should fire.

    Threshold: >90 mins dark store closure
    """
    if platform_data is None:
        platform_data = MockPlatformAPI.get_store_status(zone_id)

    if not platform_data.is_open and platform_data.closed_since:
        # For demo, we trigger immediately when closure is detected
        # In production, would check 90+ min duration

        source_data = {
            "closure_reason": platform_data.closure_reason,
            "closed_since": platform_data.closed_since.isoformat() if platform_data.closed_since else None,
            "timestamp": platform_data.timestamp.isoformat(),
        }

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.CLOSURE,
            started_at=platform_data.closed_since or datetime.utcnow(),
            severity=2,  # Default severity for closures
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_all_triggers(zone_id: int, db: Session) -> list[TriggerEvent]:
    """
    Check all trigger types for a zone.

    Returns list of triggered events (not yet persisted).
    """
    triggers = []

    # Get all current conditions
    weather = MockWeatherAPI.get_current(zone_id)
    aqi = MockAQIAPI.get_current(zone_id)
    platform = MockPlatformAPI.get_store_status(zone_id)
    shutdown = MockCivicAPI.get_shutdown_status(zone_id)

    # Check each trigger type
    rain_trigger = check_rain_trigger(zone_id, weather)
    if rain_trigger:
        triggers.append(rain_trigger)

    heat_trigger = check_heat_trigger(zone_id, weather)
    if heat_trigger:
        triggers.append(heat_trigger)

    aqi_trigger = check_aqi_trigger(zone_id, aqi)
    if aqi_trigger:
        triggers.append(aqi_trigger)

    shutdown_trigger = check_shutdown_trigger(zone_id, shutdown)
    if shutdown_trigger:
        triggers.append(shutdown_trigger)

    closure_trigger = check_closure_trigger(zone_id, platform)
    if closure_trigger:
        triggers.append(closure_trigger)

    return triggers


def detect_and_save_triggers(zone_id: int, db: Session) -> list[TriggerEvent]:
    """
    Detect triggers for a zone and save them to database.

    Checks for duplicate triggers to avoid creating multiple events
    for the same ongoing condition.
    """
    triggers = check_all_triggers(zone_id, db)
    saved_triggers = []

    for trigger in triggers:
        # Check if there's already an active (non-ended) trigger of this type
        existing = (
            db.query(TriggerEvent)
            .filter(
                TriggerEvent.zone_id == zone_id,
                TriggerEvent.trigger_type == trigger.trigger_type,
                TriggerEvent.ended_at.is_(None),
            )
            .first()
        )

        if not existing:
            db.add(trigger)
            saved_triggers.append(trigger)

    if saved_triggers:
        db.commit()
        for t in saved_triggers:
            db.refresh(t)

        # AUTO-PROCESS: Generate claims immediately when triggers are detected
        for trigger in saved_triggers:
            try:
                process_trigger_event(trigger, db)
            except Exception as e:
                # Log error but don't fail trigger creation
                print(f"Error auto-processing trigger {trigger.id}: {e}")

    return saved_triggers


def end_trigger(trigger_id: int, db: Session) -> Optional[TriggerEvent]:
    """
    Mark a trigger event as ended.
    """
    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == trigger_id).first()

    if trigger and not trigger.ended_at:
        trigger.ended_at = datetime.utcnow()
        db.commit()
        db.refresh(trigger)

    return trigger


def get_active_triggers(zone_id: int, db: Session) -> list[TriggerEvent]:
    """
    Get all active (non-ended) triggers for a zone.
    """
    return (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == zone_id,
            TriggerEvent.ended_at.is_(None),
        )
        .order_by(TriggerEvent.started_at.desc())
        .all()
    )


def get_all_active_triggers(db: Session) -> list[TriggerEvent]:
    """
    Get all active triggers across all zones.
    """
    return (
        db.query(TriggerEvent)
        .filter(TriggerEvent.ended_at.is_(None))
        .order_by(TriggerEvent.started_at.desc())
        .all()
    )
````

--- FILE: backend/app/services/trigger_engine.py ---
``python
"""
Trigger Engine â€” the brain of RapidCover's parametric insurance.

Reads data from external_apis.py, applies threshold + duration conditions,
and fires claim events when conditions are sustained past the de minimis rule.

Key design decisions:
  - 45-minute de minimis: events under 45 mins â†’ no payout (IRDAI exclusion)
  - Duration tracking via in-memory dict (active_events)
  - Each poll checks conditions; if threshold breached AND duration met â†’ fire
  - If conditions drop below threshold â†’ clear the event tracker
  - Integrates with existing trigger_detector.py for DB persistence
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.trigger_event import TriggerEvent, TriggerType, TRIGGER_THRESHOLDS
from app.models.zone import Zone
from app.models.partner import Partner
from app.models.policy import Policy
from app.database import SessionLocal
from app.services.claims_processor import (
    get_partner_runtime_metadata,
    get_zone_coverage_metadata,
    is_partner_available_for_trigger,
)
from app.services.external_apis import (
    MockWeatherAPI,
    MockAQIAPI,
    MockPlatformAPI,
    MockCivicAPI,
    get_source_health,
    compute_trigger_confidence,
    get_oracle_reliability_report,
)

logger = logging.getLogger("trigger_engine")

# â”€â”€â”€ Thresholds from README â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

RAIN_THRESHOLD_MM_HR = 55       # >55mm/hr
HEAT_THRESHOLD_CELSIUS = 43     # >43Â°C sustained 4+ hrs
AQI_THRESHOLD = 400             # >400 for 3+ hrs
MIN_DURATION_MINUTES = 45       # De minimis exclusion â€” events < 45 min = no payout

# Per-trigger minimum durations (in minutes)
TRIGGER_MIN_DURATION = {
    "rain":     30,    # 30 mins sustained
    "heat":     240,   # 4 hours
    "aqi":      180,   # 3 hours
    "shutdown": 120,   # 2 hours
    "closure":  90,    # 90 minutes
}

# â”€â”€â”€ In-memory tracking of ongoing events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Format: { "zone_id:trigger_type": { "start": timestamp, "details": dict } }
active_events: dict[str, dict] = {}
forecast_alert_state: dict[int, str] = {}

# â”€â”€â”€ Trigger log (in-memory ring buffer for admin UI) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_trigger_log: list[dict] = []
_MAX_LOG_ENTRIES = 200
FORECAST_ALERT_COOLDOWN_HOURS = 24


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
    oracle = get_oracle_reliability_report()
    return {
        "active_events": len(active_events),
        "active_event_keys": list(active_events.keys()),
        "log_entries": len(_trigger_log),
        "data_sources": get_source_health(),
        "oracle_reliability": oracle,
    }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Main entry point â€” called by scheduler every 45 seconds
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def check_all_triggers(force: bool = False, zone_code: str = None, prefer_mock: bool = False):
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
            if not prefer_mock:
                _run_forecast_alerts(zone, db)
            _check_zone_triggers(zone, db, force=force, prefer_mock=prefer_mock)

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


def _check_zone_triggers(zone: Zone, db: Session, force: bool = False, prefer_mock: bool = False):
    """Check all trigger types for a single zone."""

    lat = zone.dark_store_lat
    lon = zone.dark_store_lng

    # Fetch current conditions from all data sources
    weather = MockWeatherAPI.get_current(zone.id, lat, lon, prefer_mock=prefer_mock)
    aqi_data = MockAQIAPI.get_current(zone.id, lat, lon, prefer_mock=prefer_mock)
    platform = MockPlatformAPI.get_store_status(zone.id)
    shutdown = MockCivicAPI.get_shutdown_status(zone.id)

    # â”€â”€ Rain â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    rain_triggered = weather.rainfall_mm_hr >= RAIN_THRESHOLD_MM_HR
    _handle_event(zone, "rain", rain_triggered, db, force, {
        "rainfall_mm_hr": weather.rainfall_mm_hr,
        "threshold": RAIN_THRESHOLD_MM_HR,
        "humidity": weather.humidity,
        "data_source": weather.source,
    })

    # â”€â”€ Heat â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    heat_triggered = weather.temp_celsius >= HEAT_THRESHOLD_CELSIUS
    _handle_event(zone, "heat", heat_triggered, db, force, {
        "temp_celsius": round(weather.temp_celsius, 1),
        "threshold": HEAT_THRESHOLD_CELSIUS,
        "data_source": weather.source,
    })

    # â”€â”€ AQI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    aqi_triggered = aqi_data.aqi >= AQI_THRESHOLD
    _handle_event(zone, "aqi", aqi_triggered, db, force, {
        "aqi": aqi_data.aqi,
        "threshold": AQI_THRESHOLD,
        "pm25": aqi_data.pm25,
        "category": aqi_data.category,
        "data_source": aqi_data.source,
    })

    # â”€â”€ Shutdown â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    shutdown_triggered = shutdown.is_active
    _handle_event(zone, "shutdown", shutdown_triggered, db, force, {
        "reason": shutdown.reason,
        "started_at": shutdown.started_at.isoformat() if shutdown.started_at else None,
        "data_source": shutdown.source,
    })

    # â”€â”€ Dark store closure â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    closure_triggered = not platform.is_open
    _handle_event(zone, "closure", closure_triggered, db, force, {
        "closure_reason": platform.closure_reason,
        "closed_since": platform.closed_since.isoformat() if platform.closed_since else None,
        "data_source": platform.source,
    })


def _run_forecast_alerts(zone: Zone, db: Session) -> int:
    """Dispatch forecast alerts for a zone with a 24-hour cooldown."""
    now = datetime.utcnow()
    last_sent_iso = forecast_alert_state.get(zone.id)
    if last_sent_iso:
        last_sent = datetime.fromisoformat(last_sent_iso)
        if now - last_sent < timedelta(hours=FORECAST_ALERT_COOLDOWN_HOURS):
            return 0

    alerts = check_48hr_forecast(zone.id, db, zone=zone)
    if not alerts:
        return 0

    sent_count = send_forecast_alerts(zone.id, db, zone=zone)
    forecast_alert_state[zone.id] = now.isoformat()

    if sent_count > 0:
        _add_log(zone.id, zone.code, "forecast", f"Sent {sent_count} forecast alert push notifications", "info")
    else:
        _add_log(zone.id, zone.code, "forecast", "Forecast conditions matched, but no active push subscriptions were available", "info")

    return sent_count


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Duration enforcement â€” the 45-minute de minimis rule
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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
            # Force mode (admin drills / demos): one poll must fire â€” do not wait for a
            # second scheduler tick to satisfy duration (normal path below).
            if force:
                _fire_trigger(zone, event_type, 0.0, details, db, force)
            else:
                # Event just started â€” begin the duration clock
                active_events[key] = {"start": now, "details": details}
                _add_log(zone.id, zone.code, event_type,
                         f"Threshold breached â€” duration clock started. Details: {_summarize(details)}",
                         "warning")

        else:
            # Event ongoing â€” check if duration requirement met
            duration_min = (now - active_events[key]["start"]) / 60.0
            min_required = max(
                MIN_DURATION_MINUTES,
                TRIGGER_MIN_DURATION.get(event_type, MIN_DURATION_MINUTES),
            )

            if force or duration_min >= min_required:
                # Duration met (or force-fired for demo) â€” create trigger event
                _fire_trigger(zone, event_type, duration_min, details, db, force)
                # Remove from tracking so we don't re-fire every poll
                active_events.pop(key, None)
            else:
                remaining = min_required - duration_min
                _add_log(zone.id, zone.code, event_type,
                         f"Duration {duration_min:.0f}m / {min_required:.0f}m required â€” {remaining:.0f}m remaining",
                         "info")
    else:
        # Event ended â€” clear tracking
        if key in active_events:
            duration_min = (now - active_events[key]["start"]) / 60.0
            _add_log(zone.id, zone.code, event_type,
                     f"Condition cleared after {duration_min:.0f}m â€” below threshold, no trigger fired",
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
    from app.services.claims_processor import (
        process_trigger_event,
        get_eligible_policies,
        calculate_payout_amount,
        check_daily_limit,
        check_weekly_limit,
    )

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
                 f"Trigger already active (ID: {existing.id}) â€” skipping duplicate",
                 "info")
        return

    # Calculate severity
    thresholds = TRIGGER_THRESHOLDS.get(trigger_type, {})
    threshold_val = thresholds.get("threshold", 1)
    actual_val = details.get("rainfall_mm_hr") or details.get("temp_celsius") or details.get("aqi") or 1
    severity = _calculate_severity(actual_val, threshold_val) if threshold_val > 0 else 3

    # Compute oracle confidence for this trigger
    primary_source = details.get("data_source", "mock")
    oracle_conf = compute_trigger_confidence(
        primary_source=primary_source,
        primary_value=details.get("rainfall_mm_hr") or details.get("temp_celsius") or details.get("aqi"),
    )

    # Create trigger event
    source_data = {
        **details,
        "duration_minutes": round(duration_min),
        "force_fired": force,
        "engine_version": "v2",
        "oracle_confidence": oracle_conf["trigger_confidence_score"],
        "oracle_decision": oracle_conf["decision"],
        "oracle_agreement_score": oracle_conf["agreement_score"],
        "oracle_reason": oracle_conf["reason"],
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
             f"ðŸ”¥ TRIGGER FIRED â€” ID: {trigger.id}, severity: {severity}, duration: {duration_min:.0f}m"
             + (" [FORCE]" if force else ""),
             "critical")

    # â”€â”€â”€ Plan-based payout with detailed logging â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Count all partners in zone vs those with active policies
    all_partners_in_zone = db.query(Partner).filter(
        Partner.zone_id == zone.id, Partner.is_active == True
    ).count()

    eligible = get_eligible_policies(zone.id, db)
    no_policy_count = all_partners_in_zone - len(eligible)

    # Auto-process claims for this trigger
    # Forced immediate fire uses duration_min=0 so the de-minimis clock is bypassed, but
    # payout math still needs a positive disruption window â€” otherwise hourly_rate * 0 = 0
    # and every claim is skipped. Use default hours when force-fired at zero duration.
    try:
        disruption_hours = duration_min / 60.0
        if force and disruption_hours <= 0:
            disruption_hours = None
        claims = process_trigger_event(trigger, db, disruption_hours=disruption_hours)

        # Build detailed payout summary for logs
        paid_count = len(claims)
        weekly_limit_count = 0
        daily_limit_count = 0
        cap_applied_count = 0

        # Check which eligible partners DIDN'T get a claim (weekly/daily limit)
        claim_policy_ids = {c.policy_id for c in claims}
        for policy, partner in eligible:
            if policy.id not in claim_policy_ids:
                has_weekly, _ = check_weekly_limit(partner, policy, db)
                if not has_weekly:
                    weekly_limit_count += 1
                else:
                    daily_limit_count += 1

        # Check which claims had their payout capped
        for claim in claims:
            policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
            if policy and claim.amount >= policy.max_daily_payout * 0.99:
                cap_applied_count += 1

        # Log the rich summary
        plan_summary_parts = [f"âœ… Paid: {paid_count}"]
        if no_policy_count > 0:
            plan_summary_parts.append(f"â›” No policy: {no_policy_count}")
        if weekly_limit_count > 0:
            plan_summary_parts.append(f"ðŸ“… Weekly limit: {weekly_limit_count}")
        if daily_limit_count > 0:
            plan_summary_parts.append(f"ðŸ’° Daily limit: {daily_limit_count}")
        if cap_applied_count > 0:
            plan_summary_parts.append(f"ðŸ“‰ Cap applied: {cap_applied_count}")

        _add_log(zone.id, zone.code, event_type,
                 f"Claims processed â€” {' Â· '.join(plan_summary_parts)}",
                 "info")

        # Log individual claim details with plan tier
        for claim in claims:
            policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
            tier_label = policy.tier.value.capitalize() if policy else "?"
            max_payout = policy.max_daily_payout if policy else "?"
            was_capped = " (CAPPED)" if policy and claim.amount >= policy.max_daily_payout * 0.99 else ""
            _add_log(zone.id, zone.code, event_type,
                     f"  â†’ Claim #{claim.id}: â‚¹{claim.amount:.0f}{was_capped} [{tier_label} plan, max â‚¹{max_payout}/day] "
                     f"fraud={claim.fraud_score:.2f} status={claim.status.value}",
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
        parts.append(f"temp={details['temp_celsius']}Â°C")
    if "aqi" in details:
        parts.append(f"AQI={details['aqi']}")
    if "reason" in details and details["reason"]:
        parts.append(f"reason={details['reason']}")
    if "data_source" in details:
        parts.append(f"src={details['data_source']}")
    return ", ".join(parts) if parts else str(details)


def check_partner_pin_code_match(partner: Partner, zone: Zone, db: Session = None) -> tuple[bool, str]:
    """
    Validate partner PIN-code eligibility with strict checking.

    Returns:
        (True, "pin_code_match") - Partner pin code matches zone coverage
        (False, "partner_location_missing") - Partner has no pin code set
        (False, "coverage_data_missing") - Zone has no coverage pin codes configured
        (False, "pin_code_mismatch") - Partner pin code not in zone coverage
    """
    partner_pin_code = getattr(partner, "pin_code", None)
    zone_pin_codes = getattr(zone, "pin_codes", None)

    if db is not None:
        runtime_metadata = get_partner_runtime_metadata(partner.id, db)
        coverage_metadata = get_zone_coverage_metadata(zone.id, db)
        partner_pin_code = runtime_metadata["pin_code"] or partner_pin_code
        if coverage_metadata["pin_codes"]:
            zone_pin_codes = coverage_metadata["pin_codes"]

    # Strict validation - explicit fail reasons instead of fallback-to-true
    if not partner_pin_code:
        return False, "partner_location_missing"

    if not zone_pin_codes or len(zone_pin_codes) == 0:
        return False, "coverage_data_missing"

    if partner_pin_code in zone_pin_codes:
        return True, "pin_code_match"

    return False, "pin_code_mismatch"


def check_48hr_forecast(zone_id: int, db: Session) -> list[dict]:
    """Check forecast and return list of predicted alerts."""
    alerts = []

    mock_rain_forecast = 35.0
    mock_temp_forecast = 41.0

    if mock_rain_forecast > 30:
        alerts.append({
            "type": "rain",
            "message": "Heavy rain predicted (>30mm) in the next 48 hours. Please be prepared.",
            "severity": "high",
        })

    if mock_temp_forecast > 40:
        alerts.append({
            "type": "heat",
            "message": "Extreme heat predicted (>40Â°C) in the next 48 hours. Stay hydrated.",
            "severity": "high",
        })

    return alerts


def send_forecast_alerts(zone_id: int, db: Session):
    """Send push notifications to partners in zone."""
    alerts = check_48hr_forecast(zone_id, db)
    if not alerts:
        return 0

    partners = db.query(Partner).filter(
        Partner.zone_id == zone_id,
        Partner.is_active == True,
    ).all()
    if not partners:
        return 0

    from app.services.notifications import send_push_notification, get_partner_subscriptions

    success_count = 0
    for alert in alerts:
        payload = {
            "title": f"Weather Alert: {alert['type'].capitalize()}",
            "body": alert["message"],
            "url": "/",
            "tag": f"forecast-alert-{alert['type']}",
            "type": "weather_alert",
            "icon": "/icon-192.png",
        }

        for partner in partners:
            subscriptions = get_partner_subscriptions(partner.id, db)
            for sub in subscriptions:
                if send_push_notification(sub, payload):
                    success_count += 1

    db.commit()
    logger.info(f"Sent {len(alerts)} forecast alerts to zone {zone_id}. Total pushes: {success_count}")
    return success_count


def _fetch_openweather_forecast(zone: Optional[Zone]) -> dict:
    """Fetch a compact 48-hour rain/heat forecast for alerting."""
    settings = get_settings()
    if not zone or not settings.openweathermap_api_key:
        return {"source": "mock"}

    if zone.dark_store_lat is None or zone.dark_store_lng is None:
        return {"source": "mock"}

    try:
        response = httpx.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={
                "lat": zone.dark_store_lat,
                "lon": zone.dark_store_lng,
                "appid": settings.openweathermap_api_key,
            },
            timeout=5.0,
        )
        response.raise_for_status()
        data = response.json()
        horizon = datetime.utcnow() + timedelta(hours=48)
        entries = []
        for item in data.get("list", []):
            timestamp = datetime.utcfromtimestamp(item.get("dt", 0))
            if timestamp > horizon:
                continue

            rain_3h = item.get("rain", {}).get("3h", 0.0) or 0.0
            entries.append({
                "temp_celsius": round(item["main"]["temp"] - 273.15, 1),
                "rainfall_mm_hr": float(rain_3h) / 3.0,
            })

        if not entries:
            return {"source": "mock"}

        return {
            "source": "live",
            "max_temp_celsius": max(entry["temp_celsius"] for entry in entries),
            "max_rainfall_mm_hr": max(entry["rainfall_mm_hr"] for entry in entries),
        }
    except Exception:
        return {"source": "mock"}


def check_48hr_forecast(zone_id: int, db: Session, zone: Zone = None) -> list[dict]:
    """Check forecast and return list of predicted alerts."""
    alerts = []
    zone = zone or db.query(Zone).filter(Zone.id == zone_id).first()
    forecast = _fetch_openweather_forecast(zone)
    rain_forecast = forecast.get("max_rainfall_mm_hr", 35.0)
    temp_forecast = forecast.get("max_temp_celsius", 41.0)

    if rain_forecast > 30:
        alerts.append({
            "type": "rain",
            "message": f"Heavy rain predicted (~{rain_forecast:.0f}mm/hr peak) in the next 48 hours. Please be prepared.",
            "severity": "high",
            "source": forecast.get("source", "mock"),
        })

    if temp_forecast > 40:
        alerts.append({
            "type": "heat",
            "message": f"Extreme heat predicted (~{temp_forecast:.0f}C peak) in the next 48 hours. Stay hydrated.",
            "severity": "high",
            "source": forecast.get("source", "mock"),
        })

    return alerts


def send_forecast_alerts(zone_id: int, db: Session, zone: Zone = None):
    """Send push notifications to partners in zone after eligibility filtering."""
    zone = zone or db.query(Zone).filter(Zone.id == zone_id).first()
    alerts = check_48hr_forecast(zone_id, db, zone=zone)
    if not alerts:
        return 0

    partners = db.query(Partner).filter(
        Partner.zone_id == zone_id,
        Partner.is_active == True,
    ).all()
    if not partners:
        return 0

    from app.services.notifications import send_push_notification, get_partner_subscriptions

    success_count = 0
    for alert in alerts:
        payload = {
            "title": f"Weather Alert: {alert['type'].capitalize()}",
            "body": alert["message"],
            "url": "/",
            "tag": f"forecast-alert-{alert['type']}",
            "type": "weather_alert",
            "icon": "/icon-192.png",
        }

        for partner in partners:
            pin_code_ok, _ = check_partner_pin_code_match(partner, zone, db) if zone else (True, "zone_missing")
            if not pin_code_ok:
                continue

            subscriptions = get_partner_subscriptions(partner.id, db)
            for sub in subscriptions:
                if send_push_notification(sub, payload):
                    success_count += 1

    db.commit()
    logger.info(f"Sent {len(alerts)} forecast alerts to zone {zone_id}. Total pushes: {success_count}")
    return success_count
````

--- FILE: backend/app/services/external_apis.py ---
``python
"""
External API services for weather, AQI, traffic, and platform status.

Hybrid architecture:
  - Attempts live API calls (OpenWeatherMap, WAQI) with timeout=5
  - Falls back to in-memory mock data if live call fails or key is empty
  - Every response includes "source": "live" | "mock" so the admin UI knows

In-memory mock conditions are still settable via set_conditions() for
admin simulation â€” the trigger engine uses get_current() which tries
live first, then mock.
"""

import httpx
import random
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from app.config import get_settings


# â”€â”€â”€ In-memory storage for simulated conditions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_zone_conditions: dict[int, dict] = {}


# â”€â”€â”€ Pydantic models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class WeatherData(BaseModel):
    """Weather data from API."""
    zone_id: int
    temp_celsius: float
    rainfall_mm_hr: float
    humidity: float
    timestamp: datetime
    source: str = "mock"  # "live" | "mock"


class AQIData(BaseModel):
    """Air Quality Index data."""
    zone_id: int
    aqi: int
    pm25: float
    pm10: float
    category: str  # good, moderate, unhealthy, hazardous
    timestamp: datetime
    source: str = "mock"


class TrafficData(BaseModel):
    """Traffic/road status data."""
    zone_id: int
    blocked_roads: int
    congestion_level: str  # low, medium, high, severe
    avg_delay_mins: float
    timestamp: datetime
    source: str = "mock"


class PlatformStatus(BaseModel):
    """Dark store platform operational status."""
    zone_id: int
    is_open: bool
    closure_reason: Optional[str] = None
    closed_since: Optional[datetime] = None
    timestamp: datetime
    source: str = "mock"


class ShutdownStatus(BaseModel):
    """Civic shutdown/curfew status."""
    zone_id: int
    is_active: bool
    reason: Optional[str] = None
    started_at: Optional[datetime] = None
    expected_end: Optional[datetime] = None
    timestamp: datetime
    source: str = "mock"


# â”€â”€â”€ Data source health tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_source_status: dict[str, dict] = {
    "openweathermap": {"status": "unknown", "last_check": None, "last_success": None},
    "waqi_aqi":       {"status": "unknown", "last_check": None, "last_success": None},
    "zepto_ops":      {"status": "mock",    "last_check": None, "last_success": None},
    "traffic_feed":   {"status": "mock",    "last_check": None, "last_success": None},
    "civic_api":      {"status": "mock",    "last_check": None, "last_success": None},
}


def get_source_health() -> dict:
    """Return current health status of all data sources."""
    return {k: {**v} for k, v in _source_status.items()}


def _update_source(name: str, success: bool):
    """Update data source health tracking."""
    now = datetime.utcnow()
    _source_status[name]["last_check"] = now
    if success:
        _source_status[name]["status"] = "live"
        _source_status[name]["last_success"] = now
    else:
        _source_status[name]["status"] = "mock"


# â”€â”€â”€ Helper: zone condition defaults â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_zone_conditions(zone_id: int) -> dict:
    """Get or initialize conditions for a zone."""
    if zone_id not in _zone_conditions:
        _zone_conditions[zone_id] = {
            "weather": {"temp": 32.0, "rainfall": 0.0, "humidity": 60.0},
            "aqi": {"value": 150, "pm25": 55.0, "pm10": 85.0},
            "traffic": {"blocked": 0, "congestion": "medium", "delay": 5.0},
            "platform": {"is_open": True, "reason": None, "since": None},
            "shutdown": {"is_active": False, "reason": None, "since": None},
            "partial_disruption": {},  # For partial disruption simulation data
        }
    # Ensure partial_disruption key exists for older initialized zones
    if "partial_disruption" not in _zone_conditions[zone_id]:
        _zone_conditions[zone_id]["partial_disruption"] = {}
    return _zone_conditions[zone_id]


def set_partial_disruption_data(
    zone_id: int,
    expected_orders: Optional[int] = None,
    actual_orders: Optional[int] = None,
    partial_factor_override: Optional[float] = None,
) -> dict:
    """Set partial disruption simulation data for a zone."""
    conditions = _get_zone_conditions(zone_id)
    pd = conditions["partial_disruption"]

    if expected_orders is not None:
        pd["expected_orders"] = expected_orders
    if actual_orders is not None:
        pd["actual_orders"] = actual_orders
    if partial_factor_override is not None:
        pd["partial_factor_override"] = partial_factor_override

    return pd


def get_partial_disruption_data(zone_id: int) -> dict:
    """Get partial disruption data for a zone."""
    conditions = _get_zone_conditions(zone_id)
    return conditions.get("partial_disruption", {})


def clear_partial_disruption_data(zone_id: int) -> None:
    """Clear partial disruption data for a zone."""
    conditions = _get_zone_conditions(zone_id)
    conditions["partial_disruption"] = {}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  WEATHER â€” OpenWeatherMap with mock fallback
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MockWeatherAPI:
    """Weather API: tries live OpenWeatherMap, falls back to mock."""

    @staticmethod
    def _fetch_live(zone_id: int, lat: float = None, lon: float = None) -> Optional[WeatherData]:
        """Try to fetch live weather from OpenWeatherMap."""
        settings = get_settings()
        api_key = settings.openweathermap_api_key

        if not api_key:
            return None

        try:
            # Use zone lat/lon if provided, else default coords by zone
            if lat is None or lon is None:
                lat, lon = _get_zone_coords(zone_id)

            r = httpx.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lon, "appid": api_key},
                timeout=5.0,
            )
            r.raise_for_status()
            d = r.json()

            _update_source("openweathermap", True)

            return WeatherData(
                zone_id=zone_id,
                temp_celsius=round(d["main"]["temp"] - 273.15, 1),
                rainfall_mm_hr=d.get("rain", {}).get("1h", 0.0),
                humidity=d["main"].get("humidity", 60.0),
                timestamp=datetime.utcnow(),
                source="live",
            )
        except Exception as e:
            _update_source("openweathermap", False)
            print(f"[external_apis] OpenWeatherMap failed for zone {zone_id}: {e}")
            return None

    @staticmethod
    def get_current(zone_id: int, lat: float = None, lon: float = None, prefer_mock: bool = False) -> WeatherData:
        """Get current weather â€” live first unless a drill explicitly prefers mock data."""
        live = None if prefer_mock else MockWeatherAPI._fetch_live(zone_id, lat, lon)
        if live:
            return live

        # Fallback to mock/simulated conditions
        conditions = _get_zone_conditions(zone_id)
        weather = conditions["weather"]
        return WeatherData(
            zone_id=zone_id,
            temp_celsius=weather["temp"],
            rainfall_mm_hr=weather["rainfall"],
            humidity=weather["humidity"],
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        temp_celsius: Optional[float] = None,
        rainfall_mm_hr: Optional[float] = None,
        humidity: Optional[float] = None,
    ) -> WeatherData:
        """Set weather conditions for simulation."""
        conditions = _get_zone_conditions(zone_id)
        if temp_celsius is not None:
            conditions["weather"]["temp"] = temp_celsius
        if rainfall_mm_hr is not None:
            conditions["weather"]["rainfall"] = rainfall_mm_hr
        if humidity is not None:
            conditions["weather"]["humidity"] = humidity
        return MockWeatherAPI.get_current(zone_id, prefer_mock=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  AQI â€” WAQI / CPCB with mock fallback
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MockAQIAPI:
    """AQI API: tries live WAQI (aqicn.org), falls back to mock."""

    @staticmethod
    def _get_category(aqi: int) -> str:
        if aqi <= 50:
            return "good"
        elif aqi <= 100:
            return "moderate"
        elif aqi <= 200:
            return "unhealthy"
        elif aqi <= 300:
            return "very_unhealthy"
        else:
            return "hazardous"

    @staticmethod
    def _fetch_live(zone_id: int, lat: float = None, lon: float = None) -> Optional[AQIData]:
        """Try to fetch live AQI from WAQI."""
        settings = get_settings()
        api_key = settings.cpcb_api_key  # reusing cpcb_api_key for WAQI token

        if not api_key:
            return None

        try:
            if lat is None or lon is None:
                lat, lon = _get_zone_coords(zone_id)

            r = httpx.get(
                f"https://api.waqi.info/feed/geo:{lat};{lon}/",
                params={"token": api_key},
                timeout=5.0,
            )
            r.raise_for_status()
            data = r.json()

            if data.get("status") != "ok":
                return None

            aqi_val = int(data["data"]["aqi"])
            _update_source("waqi_aqi", True)

            return AQIData(
                zone_id=zone_id,
                aqi=aqi_val,
                pm25=data["data"].get("iaqi", {}).get("pm25", {}).get("v", 55.0),
                pm10=data["data"].get("iaqi", {}).get("pm10", {}).get("v", 85.0),
                category=MockAQIAPI._get_category(aqi_val),
                timestamp=datetime.utcnow(),
                source="live",
            )
        except Exception as e:
            _update_source("waqi_aqi", False)
            print(f"[external_apis] WAQI AQI failed for zone {zone_id}: {e}")
            return None

    @staticmethod
    def get_current(zone_id: int, lat: float = None, lon: float = None, prefer_mock: bool = False) -> AQIData:
        """Get current AQI â€” live first unless a drill explicitly prefers mock data."""
        live = None if prefer_mock else MockAQIAPI._fetch_live(zone_id, lat, lon)
        if live:
            return live

        conditions = _get_zone_conditions(zone_id)
        aqi_data = conditions["aqi"]
        return AQIData(
            zone_id=zone_id,
            aqi=aqi_data["value"],
            pm25=aqi_data["pm25"],
            pm10=aqi_data["pm10"],
            category=MockAQIAPI._get_category(aqi_data["value"]),
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        aqi: Optional[int] = None,
        pm25: Optional[float] = None,
        pm10: Optional[float] = None,
    ) -> AQIData:
        """Set AQI conditions for simulation."""
        conditions = _get_zone_conditions(zone_id)
        if aqi is not None:
            conditions["aqi"]["value"] = aqi
        if pm25 is not None:
            conditions["aqi"]["pm25"] = pm25
        if pm10 is not None:
            conditions["aqi"]["pm10"] = pm10
        return MockAQIAPI.get_current(zone_id, prefer_mock=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TRAFFIC â€” Mock (no real public API)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MockTrafficAPI:
    """Mock traffic/road status API."""

    @staticmethod
    def get_current(zone_id: int) -> TrafficData:
        conditions = _get_zone_conditions(zone_id)
        traffic = conditions["traffic"]
        return TrafficData(
            zone_id=zone_id,
            blocked_roads=traffic["blocked"],
            congestion_level=traffic["congestion"],
            avg_delay_mins=traffic["delay"],
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        blocked_roads: Optional[int] = None,
        congestion_level: Optional[str] = None,
        avg_delay_mins: Optional[float] = None,
    ) -> TrafficData:
        conditions = _get_zone_conditions(zone_id)
        if blocked_roads is not None:
            conditions["traffic"]["blocked"] = blocked_roads
        if congestion_level is not None:
            conditions["traffic"]["congestion"] = congestion_level
        if avg_delay_mins is not None:
            conditions["traffic"]["delay"] = avg_delay_mins
        return MockTrafficAPI.get_current(zone_id)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  PLATFORM (Zepto/Blinkit) â€” Mock
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MockPlatformAPI:
    """Mock Q-Commerce platform API."""

    @staticmethod
    def get_store_status(zone_id: int) -> PlatformStatus:
        conditions = _get_zone_conditions(zone_id)
        platform = conditions["platform"]
        return PlatformStatus(
            zone_id=zone_id,
            is_open=platform["is_open"],
            closure_reason=platform["reason"],
            closed_since=platform["since"],
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_store_closed(zone_id: int, reason: str) -> PlatformStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["platform"]["is_open"] = False
        conditions["platform"]["reason"] = reason
        conditions["platform"]["since"] = datetime.utcnow()
        return MockPlatformAPI.get_store_status(zone_id)

    @staticmethod
    def set_store_open(zone_id: int) -> PlatformStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["platform"]["is_open"] = True
        conditions["platform"]["reason"] = None
        conditions["platform"]["since"] = None
        return MockPlatformAPI.get_store_status(zone_id)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  CIVIC SHUTDOWN â€” Mock
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MockCivicAPI:
    """Mock civic/government shutdown status API."""

    @staticmethod
    def get_shutdown_status(zone_id: int) -> ShutdownStatus:
        conditions = _get_zone_conditions(zone_id)
        shutdown = conditions["shutdown"]

        expected_end = None
        if shutdown["is_active"] and shutdown["since"]:
            expected_end = shutdown["since"] + timedelta(hours=4)

        return ShutdownStatus(
            zone_id=zone_id,
            is_active=shutdown["is_active"],
            reason=shutdown["reason"],
            started_at=shutdown["since"],
            expected_end=expected_end,
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_shutdown(zone_id: int, reason: str) -> ShutdownStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["shutdown"]["is_active"] = True
        conditions["shutdown"]["reason"] = reason
        conditions["shutdown"]["since"] = datetime.utcnow()
        return MockCivicAPI.get_shutdown_status(zone_id)

    @staticmethod
    def clear_shutdown(zone_id: int) -> ShutdownStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["shutdown"]["is_active"] = False
        conditions["shutdown"]["reason"] = None
        conditions["shutdown"]["since"] = None
        return MockCivicAPI.get_shutdown_status(zone_id)


# â”€â”€â”€ Utilities â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Default coords for zones (used when zone model doesn't have lat/lon)
_ZONE_COORDS = {
    1: (12.9352, 77.6245),    # Koramangala, Bangalore
    2: (19.1136, 72.8697),    # Andheri East, Mumbai
    3: (28.6315, 77.2167),    # Connaught Place, Delhi
}


def _get_zone_coords(zone_id: int) -> tuple[float, float]:
    """Get lat/lon for a zone, with sensible defaults."""
    return _ZONE_COORDS.get(zone_id, (12.9716, 77.5946))  # default: Bangalore


def reset_all_conditions():
    """Reset all zone conditions to defaults."""
    global _zone_conditions
    _zone_conditions = {}


def get_all_active_conditions() -> dict[int, dict]:
    """Get all zones with non-default conditions."""
    return _zone_conditions.copy()


def apply_drill_preset(zone_id: int, preset_name: str) -> dict:
    """
    Apply drill preset conditions to a zone.

    This is a convenience wrapper that delegates to drill_service.apply_preset_conditions.
    Importing here to avoid circular imports.
    """
    from app.services.drill_service import apply_preset_conditions
    return apply_preset_conditions(zone_id, preset_name)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ORACLE RELIABILITY ENGINE
#  Scores data sources and computes trigger confidence decisions.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# Freshness thresholds (seconds)
SOURCE_FRESHNESS_LIMITS = {
    "openweathermap": 300,   # 5 minutes
    "waqi_aqi":       600,   # 10 minutes
    "zepto_ops":      60,    # 1 minute (mock)
    "traffic_feed":   120,   # 2 minutes (mock)
    "civic_api":      120,   # 2 minutes (mock)
}

# Agreement deviation threshold (as a fraction of the value)
AGREEMENT_DEVIATION_THRESHOLD = 0.20   # 20% deviation = disagreement


def compute_source_confidence(source_name: str) -> dict:
    """
    Compute reliability score for a single data source.

    Returns a dict with:
      - source_name
      - is_live: bool
      - freshness_ok: bool
      - staleness_seconds: float | None
      - reliability_score: 0.0â€“1.0
      - badge: "live" | "mock" | "stale"
      - last_success_iso: str | None
    """
    now = datetime.utcnow()
    info = _source_status.get(source_name, {})

    is_live = info.get("status") == "live"
    last_success = info.get("last_success")
    last_check = info.get("last_check")

    freshness_limit = SOURCE_FRESHNESS_LIMITS.get(source_name, 300)
    staleness_seconds = None
    freshness_ok = False

    if last_success:
        staleness_seconds = (now - last_success).total_seconds()
        freshness_ok = staleness_seconds <= freshness_limit

    # Score: live + fresh = 1.0, mock = 0.6, stale = 0.2
    if is_live and freshness_ok:
        reliability_score = 1.0
        badge = "live"
    elif is_live and not freshness_ok:
        reliability_score = 0.2
        badge = "stale"
    else:
        reliability_score = 0.6   # mock is useful but not ground-truth
        badge = "mock"

    return {
        "source_name": source_name,
        "is_live": is_live,
        "freshness_ok": freshness_ok,
        "staleness_seconds": round(staleness_seconds, 1) if staleness_seconds is not None else None,
        "freshness_limit_seconds": freshness_limit,
        "reliability_score": reliability_score,
        "badge": badge,
        "last_success_iso": last_success.isoformat() if last_success else None,
        "last_check_iso": last_check.isoformat() if last_check else None,
    }


def compute_trigger_confidence(
    primary_source: str,
    corroborating_sources: list[str] = None,
    primary_value: float = None,
    corroborating_values: list[float] = None,
) -> dict:
    """
    Compute trigger confidence given one primary + optional corroborating sources.

    Decision logic:
      - If primary stale and no corroboration â†’ hold
      - If â‰¥2 sources agree strongly â†’ confidence high â†’ fire
      - If only mock source â†’ demo mode, mark as mock
      - If live and mock disagree beyond threshold â†’ reduce confidence
      - Otherwise standard scoring

    Returns:
      - trigger_confidence_score: 0.0â€“1.0
      - source_confidence_scores: dict per source
      - decision: "fire" | "hold" | "manual_review_simulated" | "fallback_mock_mode"
      - reason: human-readable reason string
      - agreement_score: 0.0â€“1.0 (1.0 = all sources agree perfectly)
    """
    corroborating_sources = corroborating_sources or []
    corroborating_values = corroborating_values or []

    primary_conf = compute_source_confidence(primary_source)
    corr_confs = [compute_source_confidence(s) for s in corroborating_sources]
    all_confs = {primary_source: primary_conf}
    for c in corr_confs:
        all_confs[c["source_name"]] = c

    # Compute agreement score
    all_values = []
    if primary_value is not None:
        all_values.append(primary_value)
    all_values.extend([v for v in corroborating_values if v is not None])

    agreement_score = 1.0
    if len(all_values) >= 2:
        mean_val = sum(all_values) / len(all_values)
        if mean_val > 0:
            max_dev = max(abs(v - mean_val) / mean_val for v in all_values)
            agreement_score = max(0.0, 1.0 - max_dev)

    # Base confidence from primary source
    base_conf = primary_conf["reliability_score"]
    # Boost from corroborating sources
    if corr_confs:
        avg_corr = sum(c["reliability_score"] for c in corr_confs) / len(corr_confs)
        trigger_confidence = base_conf * 0.6 + avg_corr * 0.4
    else:
        trigger_confidence = base_conf

    # Apply agreement penalty if sources disagree
    trigger_confidence *= (0.5 + 0.5 * agreement_score)
    trigger_confidence = round(min(1.0, max(0.0, trigger_confidence)), 3)

    # Decision logic
    primary_live = primary_conf["is_live"]
    primary_fresh = primary_conf["freshness_ok"]
    all_mock = all(c["badge"] == "mock" for c in all_confs.values())
    sources_agree = agreement_score >= (1.0 - AGREEMENT_DEVIATION_THRESHOLD)

    if all_mock:
        decision = "fallback_mock_mode"
        reason = "All sources are mock/simulated â€” demo mode active"
    elif not primary_live and not corr_confs:
        decision = "hold"
        reason = "Primary source offline and no corroborating sources available"
    elif not primary_fresh and not corroborating_sources:
        decision = "hold"
        reason = f"Primary source ({primary_source}) data is stale and unconfirmed"
    elif trigger_confidence >= 0.7 and sources_agree:
        decision = "fire"
        reason = f"Confidence {trigger_confidence:.0%} â€” sources agree (agreement={agreement_score:.0%})"
    elif trigger_confidence >= 0.5:
        decision = "manual_review_simulated"
        reason = f"Moderate confidence {trigger_confidence:.0%} â€” requires simulated review"
    else:
        decision = "hold"
        reason = f"Low confidence {trigger_confidence:.0%} â€” holding trigger"

    return {
        "trigger_confidence_score": trigger_confidence,
        "source_confidence_scores": all_confs,
        "decision": decision,
        "reason": reason,
        "agreement_score": round(agreement_score, 3),
        "primary_source": primary_source,
        "corroborating_sources": corroborating_sources,
        "computed_at": datetime.utcnow().isoformat(),
    }


def get_oracle_reliability_report(zone_id: int = None) -> dict:
    """
    Full oracle reliability report â€” all sources with freshness + overall system health.
    """
    all_sources = list(_source_status.keys())
    source_reports = {s: compute_source_confidence(s) for s in all_sources}

    live_count = sum(1 for r in source_reports.values() if r["badge"] == "live")
    stale_count = sum(1 for r in source_reports.values() if r["badge"] == "stale")
    mock_count = sum(1 for r in source_reports.values() if r["badge"] == "mock")

    avg_reliability = sum(r["reliability_score"] for r in source_reports.values()) / len(source_reports) if source_reports else 0.0

    if live_count >= 2:
        system_health = "healthy"
    elif live_count == 1:
        system_health = "degraded"
    elif stale_count > 0:
        system_health = "stale"
    else:
        system_health = "mock_mode"

    return {
        "zone_id": zone_id,
        "system_health": system_health,
        "average_reliability": round(avg_reliability, 3),
        "live_sources": live_count,
        "stale_sources": stale_count,
        "mock_sources": mock_count,
        "sources": source_reports,
        "computed_at": datetime.utcnow().isoformat(),
    }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  PLATFORM ACTIVITY SIMULATION
#  Simulates per-partner delivery platform activity (Zomato/Swiggy/Zepto/Blinkit).
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# In-memory store: partner_id -> activity dict
_partner_platform_activity: dict[int, dict] = {}


def _default_partner_activity(partner_id: int) -> dict:
    """Return default (active, working) platform activity for a partner."""
    now = datetime.utcnow()
    return {
        "partner_id": partner_id,
        "platform_logged_in": True,
        "active_shift": True,
        "orders_accepted_recent": random.randint(3, 12),
        "orders_completed_recent": random.randint(2, 10),
        "last_app_ping": now.isoformat(),
        "zone_dwell_minutes": random.randint(20, 120),
        "suspicious_inactivity": False,
        "platform": random.choice(["zomato", "swiggy", "zepto", "blinkit"]),
        "updated_at": now.isoformat(),
        "source": "simulated",
    }


def get_partner_platform_activity(partner_id: int) -> dict:
    """Get (or initialize) platform activity for a partner."""
    if partner_id not in _partner_platform_activity:
        _partner_platform_activity[partner_id] = _default_partner_activity(partner_id)
    return dict(_partner_platform_activity[partner_id])


def set_partner_platform_activity(partner_id: int, **kwargs) -> dict:
    """
    Update platform activity fields for a partner (admin control).

    Accepted kwargs: platform_logged_in, active_shift, orders_accepted_recent,
    orders_completed_recent, last_app_ping, zone_dwell_minutes,
    suspicious_inactivity, platform
    """
    existing = get_partner_platform_activity(partner_id)
    allowed_fields = {
        "platform_logged_in", "active_shift", "orders_accepted_recent",
        "orders_completed_recent", "last_app_ping", "zone_dwell_minutes",
        "suspicious_inactivity", "platform",
    }
    for key, val in kwargs.items():
        if key in allowed_fields:
            existing[key] = val
    existing["updated_at"] = datetime.utcnow().isoformat()
    existing["source"] = "admin_override"
    _partner_platform_activity[partner_id] = existing
    return dict(existing)


def evaluate_partner_platform_eligibility(partner_id: int) -> dict:
    """
    Check if a partner's platform activity qualifies them for a payout.

    Rules:
      - Must be logged into platform
      - Must have an active shift
      - Must have completed â‰¥1 order in recent window
      - Not flagged for suspicious inactivity
      - Must have pinged app within last 30 minutes

    Returns:
      - eligible: bool
      - score: 0.0â€“1.0 (platform activity score)
      - reasons: list of pass/fail reasons
      - activity: the raw activity dict
    """
    activity = get_partner_platform_activity(partner_id)
    reasons = []
    score_parts = []

    # Check: logged in
    if activity["platform_logged_in"]:
        reasons.append({"check": "platform_logged_in", "pass": True, "note": "Partner logged into platform app"})
        score_parts.append(1.0)
    else:
        reasons.append({"check": "platform_logged_in", "pass": False, "note": "Partner not logged into platform"})
        score_parts.append(0.0)

    # Check: active shift
    if activity["active_shift"]:
        reasons.append({"check": "active_shift", "pass": True, "note": "Partner on active shift"})
        score_parts.append(1.0)
    else:
        reasons.append({"check": "active_shift", "pass": False, "note": "Partner not on shift"})
        score_parts.append(0.0)

    # Check: recent orders completed
    completed = activity.get("orders_completed_recent", 0)
    if completed >= 1:
        reasons.append({"check": "orders_completed_recent", "pass": True, "note": f"{completed} orders completed recently"})
        score_parts.append(min(1.0, completed / 5.0))
    else:
        reasons.append({"check": "orders_completed_recent", "pass": False, "note": "No recent order completions"})
        score_parts.append(0.0)

    # Check: suspicious inactivity
    if not activity.get("suspicious_inactivity", False):
        reasons.append({"check": "suspicious_inactivity", "pass": True, "note": "No inactivity flags"})
        score_parts.append(1.0)
    else:
        reasons.append({"check": "suspicious_inactivity", "pass": False, "note": "Suspicious inactivity flag active"})
        score_parts.append(0.0)

    # Check: last app ping within 30 min
    try:
        last_ping = datetime.fromisoformat(activity["last_app_ping"])
        minutes_since_ping = (datetime.utcnow() - last_ping).total_seconds() / 60.0
        if minutes_since_ping <= 30:
            reasons.append({"check": "last_app_ping", "pass": True, "note": f"Last ping {minutes_since_ping:.0f}m ago"})
            score_parts.append(1.0)
        else:
            reasons.append({"check": "last_app_ping", "pass": False, "note": f"Last ping {minutes_since_ping:.0f}m ago (>30m)"})
            score_parts.append(0.0)
    except Exception:
        reasons.append({"check": "last_app_ping", "pass": False, "note": "Cannot parse last ping timestamp"})
        score_parts.append(0.0)

    score = sum(score_parts) / len(score_parts) if score_parts else 0.0
    eligible = all(r["pass"] for r in reasons)

    return {
        "partner_id": partner_id,
        "eligible": eligible,
        "score": round(score, 3),
        "reasons": reasons,
        "activity": activity,
    }
````

--- FILE: backend/app/api/experience.py ---
``python
"""
experience.py - Partner Experience State API router.
Person 1 owns this file. Do NOT edit if you are Person 2, 3, or 4.
Per No-Conflict Rules, Section 5.

Mount in router.py:
    from app.api.experience import router as experience_router
    api_router.include_router(experience_router)

Endpoints:
  GET /partners/me/experience-state  - Full dashboard state in one call
  GET /partners/me/premium-breakdown - Itemised premium factors
  GET /partners/me/eligibility       - Tier lock/unlock based on activity
  GET /partners/me/zone-history      - Real zone reassignment history
  GET /partners/me/renewal-preview   - Simplified renewal quote for profile page
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.zone import Zone
from app.models.trigger_event import TriggerEvent
from app.services.auth import get_current_partner
from app.services.premium_service import (
    get_riqi_score,
    get_riqi_band,
    RIQI_PREMIUM_ADJUSTMENT,
    TIER_CONFIG as SVC_TIER_CONFIG,
    MIN_ACTIVE_DAYS_TO_BUY,
    AUTO_DOWNGRADE_DAYS,
    DEMO_EXEMPT_CITIES,
)

router = APIRouter(prefix="/partners", tags=["experience"])


# ---------------------------------------------------------------------------
# Internal helpers  (private â€“ not endpoints)
# ---------------------------------------------------------------------------

def _get_partner_city(partner: Partner, db: Session) -> str:
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
        if zone and zone.city:
            return zone.city.lower()
    return "bangalore"


def _count_active_days_last_30(partner: Partner, db: Session) -> int:
    """
    Count distinct calendar days partner had at least one paid/approved claim
    in the last 30 days.  Falls back to policy-days if no claims yet.
    """
    since = datetime.utcnow() - timedelta(days=30)

    claim_days = (
        db.query(func.date(Claim.created_at))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id == partner.id,
            Claim.created_at >= since,
            Claim.status.in_([ClaimStatus.APPROVED, ClaimStatus.PAID]),
        )
        .distinct()
        .count()
    )
    if claim_days > 0:
        return min(claim_days, 30)

    # Fallback â€“ each policy â‰ˆ 7 active days
    policy_count = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.starts_at >= since,
        )
        .count()
    )
    return min(policy_count * 7, 30)


def _loyalty_weeks(partner: Partner, db: Session) -> int:
    """Count consecutive policy weeks with no gap > 48 hours."""
    policies = (
        db.query(Policy)
        .filter(Policy.partner_id == partner.id)
        .order_by(Policy.expires_at.desc())
        .all()
    )
    if not policies:
        return 0
    weeks = 0
    prev_start = None
    for p in policies:
        if prev_start is None:
            weeks = 1
            prev_start = p.starts_at
            continue
        gap_hours = (prev_start - p.expires_at).total_seconds() / 3600
        if gap_hours <= 48:
            weeks += 1
            prev_start = p.starts_at
        else:
            break
    return weeks


def _get_latest_payout(partner: Partner, db: Session) -> Optional[dict]:
    claim = (
        db.query(Claim)
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id == partner.id,
            Claim.status == ClaimStatus.PAID,
        )
        .order_by(Claim.paid_at.desc())
        .first()
    )
    if not claim:
        return None
    return {
        "claim_id": claim.id,
        "status": "paid",
        "amount": claim.amount,
        "upi_ref": claim.upi_ref or "",
        "paid_at": claim.paid_at.isoformat() if claim.paid_at else None,
    }


def _get_active_zone_alert(partner: Partner, db: Session) -> Optional[dict]:
    """Return most recent trigger fired in partner's zone within the last 6 hours."""
    if not partner.zone_id:
        return None
    since = datetime.utcnow() - timedelta(hours=6)
    trigger = (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == partner.zone_id,
            TriggerEvent.started_at >= since,
        )
        .order_by(TriggerEvent.started_at.desc())
        .first()
    )
    if not trigger:
        return None

    severity_label = {1: "low", 2: "low", 3: "medium", 4: "high", 5: "critical"}.get(
        trigger.severity, "medium"
    )
    type_label = (
        trigger.trigger_type.value
        if hasattr(trigger.trigger_type, "value")
        else str(trigger.trigger_type)
    )
    messages = {
        "rain":     "Heavy rain alert in your zone. Disruption payouts active.",
        "heat":     "Extreme heat warning. Stay hydrated. Payout active.",
        "aqi":      "High AQI detected. Health advisory in effect.",
        "shutdown": "Civic shutdown in your area. Payout processing.",
        "closure":  "Store closure detected. Coverage active.",
    }
    return {
        "type":       type_label,
        "message":    messages.get(type_label, f"{type_label.title()} event active in your zone."),
        "severity":   severity_label,
        "trigger_id": trigger.id,
        "started_at": trigger.started_at.isoformat() if trigger.started_at else None,
    }


def _get_zone_reassignment_card(partner: Partner, db: Session) -> Optional[dict]:
    """
    Return the most recent reassignment card if it happened in the last 24 hours.
    Returns None if no recent reassignment.
    """
    history = partner.zone_history or []
    if not history:
        return None
    latest = history[-1]
    effective_at_str = latest.get("effective_at")
    if not effective_at_str:
        return None
    try:
        effective_at = datetime.fromisoformat(effective_at_str)
    except ValueError:
        return None
    if datetime.utcnow() - effective_at > timedelta(hours=24):
        return None

    old_zone_id  = latest.get("old_zone_id")
    new_zone_id  = latest.get("new_zone_id")
    old_zone     = db.query(Zone).filter(Zone.id == old_zone_id).first() if old_zone_id else None
    new_zone     = db.query(Zone).filter(Zone.id == new_zone_id).first() if new_zone_id else None

    return {
        "old_zone":       old_zone.name if old_zone else f"Zone #{old_zone_id}",
        "new_zone":       new_zone.name if new_zone else f"Zone #{new_zone_id}",
        "old_zone_code":  old_zone.code if old_zone else None,
        "new_zone_code":  new_zone.code if new_zone else None,
        "premium_delta":  round(latest.get("premium_adjustment", 0), 2),
        "hours_left":     latest.get("days_remaining", 0) * 24,
        "effective_at":   effective_at_str,
    }


def _build_premium_breakdown(partner: Partner, db: Session) -> dict:
    """Compute itemised premium breakdown from real partner data."""
    city       = _get_partner_city(partner, db)
    riqi       = get_riqi_score(city, partner.zone_id)
    band       = get_riqi_band(riqi)
    riqi_adj   = RIQI_PREMIUM_ADJUSTMENT[band]
    loyalty_wks = _loyalty_weeks(partner, db)
    # 1% discount per loyalty week, cap at 10%
    loyalty_discount = round(max(0.0, 1.0 - (loyalty_wks * 0.01)), 3)

    # Get tier from active policy; default to standard
    active_policy = (
        db.query(Policy)
        .filter(Policy.partner_id == partner.id, Policy.is_active == True)
        .order_by(Policy.expires_at.desc())
        .first()
    )
    tier = (
        active_policy.tier.value
        if active_policy and hasattr(active_policy.tier, "value")
        else (active_policy.tier if active_policy else "standard")
    )
    base = SVC_TIER_CONFIG.get(tier, SVC_TIER_CONFIG["standard"])["weekly_premium"]

    # Seasonal index: monsoon Junâ€“Sep = 1.20, else 1.00
    month          = datetime.utcnow().month
    seasonal_index = 1.20 if month in (6, 7, 8, 9) else 1.00

    # Zone risk factor from Zone.risk_score (0â€“100, centre at 50)
    zone_risk_factor = 1.0
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
        if zone and zone.risk_score is not None:
            zone_risk_factor = round(1.0 + (zone.risk_score - 50) / 200, 2)

    total = round(base * zone_risk_factor * seasonal_index * riqi_adj * loyalty_discount, 2)

    return {
        "tier":             tier,
        "base":             base,
        "zone_risk":        zone_risk_factor,
        "seasonal_index":   seasonal_index,
        "riqi_adjustment":  riqi_adj,
        "activity_factor":  1.0,
        "loyalty_discount": loyalty_discount,
        "total":            total,
        "city":             city,
        "riqi_band":        band,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/me/experience-state", summary="Full dashboard state for partner app")
def get_experience_state(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Single endpoint consumed by Dashboard.jsx on load and polled every 5 s during drills.

    All fields are null-safe:
    - zone_alert is None  â†’ do NOT show alert card
    - zone_reassignment is None â†’ do NOT show reassignment card
    - latest_payout.status == "paid" â†’ show payout banner near top of dashboard
    """
    zone_alert       = _get_active_zone_alert(partner, db)
    zone_reassignment = _get_zone_reassignment_card(partner, db)
    loyalty_wks      = _loyalty_weeks(partner, db)
    breakdown        = _build_premium_breakdown(partner, db)
    latest_payout    = _get_latest_payout(partner, db)

    return {
        "zone_alert":        zone_alert,
        "zone_reassignment": zone_reassignment,
        "loyalty": {
            "streak_weeks":     loyalty_wks,
            "discount_unlocked": loyalty_wks >= 4,
            "next_milestone":   max(4, ((loyalty_wks // 4) + 1) * 4),
            "discount_pct":     min(loyalty_wks, 10),
        },
        "premium_breakdown": breakdown,
        "latest_payout":     latest_payout,
        "fetched_at":        datetime.utcnow().isoformat(),
    }


@router.get("/me/premium-breakdown", summary="Itemised weekly premium for authenticated partner")
def get_premium_breakdown(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Returns full itemised premium breakdown using real partner zone, tier,
    current month, loyalty, and activity.
    Replaces all TIER_PRICES fallback math in UI.
    """
    return _build_premium_breakdown(partner, db)


@router.get("/me/eligibility", summary="Tier lock/unlock based on backend-calculated activity")
def get_eligibility(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Returns which tiers the partner may purchase.
    Frontend must use allowed_tiers / blocked_tiers / reasons directly â€”
    no local eligibility logic allowed.

    Delhi exception: Partners in Delhi bypass the 7-day minimum rule per Team Guide.
    """
    active_days = _count_active_days_last_30(partner, db)
    loyalty_wks = _loyalty_weeks(partner, db)
    city = _get_partner_city(partner, db)

    # Delhi exception: skip 7-day minimum check for demo purposes
    is_demo_exempt = city.lower() in [c.lower() for c in DEMO_EXEMPT_CITIES]

    if active_days < MIN_ACTIVE_DAYS_TO_BUY and not is_demo_exempt:
        allowed_tiers = []
        blocked_tiers = ["flex", "standard", "pro"]
        reasons = {
            t: f"Need {MIN_ACTIVE_DAYS_TO_BUY} active days in last 30. You have {active_days}."
            for t in blocked_tiers
        }
    elif active_days < AUTO_DOWNGRADE_DAYS:
        allowed_tiers = ["flex"]
        blocked_tiers = ["standard", "pro"]
        reasons = {
            t: f"Need {AUTO_DOWNGRADE_DAYS}+ active days for {t}. You have {active_days}."
            for t in blocked_tiers
        }
    else:
        allowed_tiers = ["flex", "standard", "pro"]
        blocked_tiers = []
        reasons = {}

    return {
        "active_days_last_30": active_days,
        "loyalty_weeks":       loyalty_wks,
        "allowed_tiers":       allowed_tiers,
        "blocked_tiers":       blocked_tiers,
        "reasons":             reasons,
        "gate_blocked":        active_days < MIN_ACTIVE_DAYS_TO_BUY,
    }


@router.get("/me/zone-history", summary="Real zone reassignment history for profile page")
def get_zone_history(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Returns actual reassignment history from partner.zone_history.
    Each entry is enriched with zone name/code/city from the DB.
    Returns empty list (not an error) when no history exists.
    """
    raw = partner.zone_history or []
    enriched = []
    for entry in raw:
        old_zone_id = entry.get("old_zone_id")
        new_zone_id = entry.get("new_zone_id")
        old_zone    = db.query(Zone).filter(Zone.id == old_zone_id).first() if old_zone_id else None
        new_zone    = db.query(Zone).filter(Zone.id == new_zone_id).first() if new_zone_id else None
        enriched.append({
            "old_zone_id":          old_zone_id,
            "old_zone_name":        old_zone.name if old_zone else f"Zone #{old_zone_id}",
            "old_zone_code":        old_zone.code if old_zone else None,
            "old_zone_city":        old_zone.city if old_zone else None,
            "new_zone_id":          new_zone_id,
            "new_zone_name":        new_zone.name if new_zone else f"Zone #{new_zone_id}",
            "new_zone_code":        new_zone.code if new_zone else None,
            "new_zone_city":        new_zone.city if new_zone else None,
            "effective_at":         entry.get("effective_at"),
            "premium_adjustment":   entry.get("premium_adjustment", 0),
            "new_weekly_premium":   entry.get("new_weekly_premium", 0),
            "days_remaining":       entry.get("days_remaining", 0),
            "policy_id":            entry.get("policy_id"),
        })
    return {
        "history":     list(reversed(enriched)),   # most recent first
        "total":       len(enriched),
        "has_history": len(enriched) > 0,
    }


@router.get(
    "/me/reassignments",
    summary="List partner's zone reassignment proposals",
)
def get_my_reassignments(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Return all zone reassignment proposals for the authenticated partner,
    most-recent first.  Consumed by Dashboard.jsx to show the accept/reject card.

    Response shape:
    {
      reassignments: [ ZoneReassignmentResponse, ... ],
      total: int,
      pending_count: int,
    }
    """
    from app.services.zone_reassignment_service import list_reassignments
    from app.models.zone_reassignment import ReassignmentStatus

    return list_reassignments(db, partner_id=partner.id)


@router.post(
    "/me/reassignments/{reassignment_id}/accept",
    summary="Accept a pending zone reassignment proposal",
)
def accept_my_reassignment(
    reassignment_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Accept a proposed zone reassignment.

    - Updates partner.zone_id to the new zone
    - Appends an entry to partner.zone_history
    - Returns the updated reassignment or a 4xx error
    """
    from fastapi import HTTPException, status as http_status
    from app.services.zone_reassignment_service import (
        accept_reassignment,
        get_reassignment,
    )

    # Ownership guard
    existing = get_reassignment(reassignment_id, db)
    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Reassignment not found",
        )
    if existing.partner_id != partner.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Not your reassignment",
        )

    result, error = accept_reassignment(reassignment_id, db)
    if not result:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=error or "Could not accept reassignment",
        )
    return result


@router.post(
    "/me/reassignments/{reassignment_id}/reject",
    summary="Reject a pending zone reassignment proposal",
)
def reject_my_reassignment(
    reassignment_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Reject a proposed zone reassignment.

    - Partner stays in current zone
    - Proposal status â†’ rejected
    """
    from fastapi import HTTPException, status as http_status
    from app.services.zone_reassignment_service import (
        reject_reassignment,
        get_reassignment,
    )

    existing = get_reassignment(reassignment_id, db)
    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Reassignment not found",
        )
    if existing.partner_id != partner.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Not your reassignment",
        )

    result, error = reject_reassignment(reassignment_id, db)
    if not result:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=error or "Could not reject reassignment",
        )
    return result


@router.get("/me/renewal-preview", summary="Simplified renewal quote for profile page")
def get_renewal_preview(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Simplified renewal quote for profile page.
    Replaces hardcoded renewal premium breakdown in Profile.jsx.
    Same structure as the full renewal-quote flow, minus partner decision fields.
    """
    policy = (
        db.query(Policy)
        .filter(Policy.partner_id == partner.id)
        .order_by(Policy.expires_at.desc())
        .first()
    )
    if not policy:
        return {
            "has_policy":        False,
            "renewal_available": False,
            "message":           "No policy found. Purchase a plan to get started.",
        }

    loyalty_wks          = _loyalty_weeks(partner, db)
    loyalty_discount_pct = min(loyalty_wks, 10)
    breakdown            = _build_premium_breakdown(partner, db)
    tier                 = (
        policy.tier.value if hasattr(policy.tier, "value") else str(policy.tier)
    )
    base_premium         = SVC_TIER_CONFIG.get(tier, SVC_TIER_CONFIG["standard"])["weekly_premium"]
    loyalty_discount_amt = round(base_premium * loyalty_discount_pct / 100, 2)
    renewal_premium      = max(round(breakdown["total"] - loyalty_discount_amt, 2), 1.0)

    return {
        "has_policy":              True,
        "renewal_available":       True,
        "current_tier":            tier,
        "current_premium":         policy.weekly_premium,
        "renewal_premium":         renewal_premium,
        "loyalty_weeks":           loyalty_wks,
        "loyalty_discount_pct":    loyalty_discount_pct,
        "loyalty_discount_amount": loyalty_discount_amt,
        "breakdown":               breakdown,
        "expires_at":              policy.expires_at.isoformat() if policy.expires_at else None,
        "auto_renew":              policy.auto_renew,
    }
````

--- FILE: backend/app/api/partners.py ---
``python
"""
partners.py - Partner API router.
Person 1 owns this file. Do NOT edit if you are Person 2, 3, or 4.
Per No-Conflict Rules, Section 5.

New endpoints added in Phase 2:
  GET /partners/riqi              - RIQI scores for all cities
  GET /partners/riqi/{city}       - RIQI score for one city
  GET /partners/quotes            - Personalised plan quotes (onboarding step 5)
  GET /partners/premium           - Weekly premium for authenticated partner
  GET /partners/tiers             - Tier config (frontend plan cards)
  GET /partners/bcr/{city}        - BCR / Loss Ratio for a city (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.database import get_db
from app.models.partner import Partner
from app.schemas.partner import (
    PartnerCreate,
    PartnerResponse,
    PartnerLogin,
    OTPVerify,
    TokenResponse,
    PartnerUpdate,
)
from app.services.auth import (
    generate_otp,
    store_otp,
    verify_otp,
    create_access_token,
    get_current_partner,
)
from app.services.partner_validation import validate_partner_id
from app.services.premium_service import (
    get_riqi_score,
    get_riqi_band,
    get_riqi_payout_multiplier,
    get_plan_quotes,
    calculate_weekly_premium,
    calculate_bcr,
    CITY_RIQI_SCORES,
    RIQI_PAYOUT_MULTIPLIER,
    RIQI_PREMIUM_ADJUSTMENT,
    TIER_CONFIG,
)

router = APIRouter(prefix="/partners", tags=["partners"])


# ------------------------------------------------------------------------------
# REGISTER
# ------------------------------------------------------------------------------

@router.post("/register", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
def register_partner(partner_data: PartnerCreate, db: Session = Depends(get_db)):
    """Register a new delivery partner."""
    existing = db.query(Partner).filter(Partner.phone == partner_data.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )

    # Convert KYC Pydantic model to dict for SQLAlchemy JSON column
    kyc_data = getattr(partner_data, "kyc", None)
    if kyc_data is not None and hasattr(kyc_data, "model_dump"):
        kyc_dict = kyc_data.model_dump()
    elif kyc_data is not None and hasattr(kyc_data, "dict"):
        kyc_dict = kyc_data.dict()
    elif kyc_data is not None:
        kyc_dict = dict(kyc_data)
    else:
        kyc_dict = {
            "aadhaar_number": None,
            "pan_number":     None,
            "kyc_status":     "skipped",
        }

    # HACKATHON SECURITY: Never store raw PII. Hash identities and set verified.
    import hashlib
    if kyc_dict.get("aadhaar_number") or kyc_dict.get("pan_number"):
        if kyc_dict.get("aadhaar_number"):
            raw = str(kyc_dict["aadhaar_number"])
            hashed = hashlib.sha256(raw.encode()).hexdigest()[:16]
            kyc_dict["aadhaar_number"] = f"UID-{hashed}-XXXX{raw[-4:]}"
        
        if kyc_dict.get("pan_number"):
            raw = str(kyc_dict["pan_number"])
            hashed = hashlib.sha256(raw.encode()).hexdigest()[:16]
            kyc_dict["pan_number"] = f"PAN-{hashed}"
            
        kyc_dict["kyc_status"] = "verified"

    partner = Partner(
        phone         = partner_data.phone,
        name          = partner_data.name,
        platform      = partner_data.platform,
        partner_id    = partner_data.partner_id,
        zone_id       = partner_data.zone_id,
        language_pref = partner_data.language_pref,
        upi_id        = getattr(partner_data, "upi_id", None),
        kyc           = kyc_dict,
        shift_days    = getattr(partner_data, "shift_days", None) or [],
        shift_start   = getattr(partner_data, "shift_start", None),
        shift_end     = getattr(partner_data, "shift_end", None),
        zone_history  = getattr(partner_data, "zone_history", None) or [],
    )

    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


# ------------------------------------------------------------------------------
# AUTH
# ------------------------------------------------------------------------------

@router.post("/login", status_code=status.HTTP_200_OK)
def request_otp(login_data: PartnerLogin, db: Session = Depends(get_db)):
    """Request OTP for login. OTP exposed in response for dev/demo mode."""
    partner = db.query(Partner).filter(Partner.phone == login_data.phone).first()
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone number not registered")
    if not partner.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    otp = generate_otp()
    store_otp(login_data.phone, otp)
    return {"message": "OTP sent", "otp": otp}  # Remove otp in production


@router.post("/verify", response_model=TokenResponse)
def verify_login(verify_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP and return JWT token."""
    partner = db.query(Partner).filter(Partner.phone == verify_data.phone).first()
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone number not registered")
    if not verify_otp(verify_data.phone, verify_data.otp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

    access_token = create_access_token(data={"sub": str(partner.id)})
    return TokenResponse(access_token=access_token)


# ------------------------------------------------------------------------------
# PROFILE
# ------------------------------------------------------------------------------

@router.get("/me", response_model=PartnerResponse)
def get_current_partner_profile(partner: Partner = Depends(get_current_partner)):
    """Get current partner's profile."""
    return partner


@router.patch("/me", response_model=PartnerResponse)
def update_partner_profile(
    update_data: PartnerUpdate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Update profile - name, zone, language, UPI, KYC."""
    if update_data.name is not None:
        partner.name = update_data.name
    if update_data.zone_id is not None:
        partner.zone_id = update_data.zone_id
    if update_data.language_pref is not None:
        partner.language_pref = update_data.language_pref

    # UPI
    if hasattr(update_data, "upi_id") and update_data.upi_id is not None:
        partner.upi_id = update_data.upi_id

    # KYC - merge, never downgrade verified status
    if hasattr(update_data, "kyc") and update_data.kyc is not None:
        existing_kyc = partner.kyc or {}
        incoming_kyc = (
            update_data.kyc.model_dump(exclude_none=True)
            if hasattr(update_data.kyc, "model_dump")
            else update_data.kyc.dict(exclude_none=True)
            if hasattr(update_data.kyc, "dict")
            else dict(update_data.kyc)
        )
        if existing_kyc.get("kyc_status") == "verified":
            incoming_kyc["kyc_status"] = "verified"
        partner.kyc = {**existing_kyc, **incoming_kyc}

    # Shift preferences
    if hasattr(update_data, "shift_days") and update_data.shift_days is not None:
        partner.shift_days = update_data.shift_days
    if hasattr(update_data, "shift_start") and update_data.shift_start is not None:
        partner.shift_start = update_data.shift_start
    if hasattr(update_data, "shift_end") and update_data.shift_end is not None:
        partner.shift_end = update_data.shift_end
    if hasattr(update_data, "zone_history") and update_data.zone_history is not None:
        partner.zone_history = update_data.zone_history

    db.commit()
    db.refresh(partner)
    return partner


# ------------------------------------------------------------------------------
# PARTNER ID & AVAILABILITY VALIDATION
# ------------------------------------------------------------------------------

@router.get("/check-availability")
def check_availability(
    phone: Optional[str] = Query(None, description="Phone number to check"),
    partner_id: Optional[str] = Query(None, description="Partner ID to check"),
    db: Session = Depends(get_db)
):
    """Check if a phone number or partner ID is already registered."""
    result = {"phone_taken": False, "partner_id_taken": False}
    if phone:
        if db.query(Partner).filter(Partner.phone == phone).first():
            result["phone_taken"] = True
    if partner_id:
        if db.query(Partner).filter(Partner.partner_id == partner_id).first():
            result["partner_id_taken"] = True
    return result

@router.get("/validate-id")
def validate_partner_id_endpoint(
    partner_id: str = Query(..., description="Partner ID e.g. ZPT123456"),
    platform:   str = Query(..., description="zepto or blinkit"),
):
    """
    Validate partner ID. Mock behaviour:
      IDs ending in 000 -> Not found
      IDs ending in 999 -> Suspended
      All other valid formats -> Verified
    """
    return validate_partner_id(partner_id, platform)


# ------------------------------------------------------------------------------
# RIQI ZONE SCORING - derive score per zone, expose via API (Person 1 task)
# ------------------------------------------------------------------------------

@router.get("/riqi", summary="RIQI scores for all cities")
def get_all_riqi():
    """
    Get RIQI (Road Infrastructure Quality Index) scores for all supported cities.
    RIQI: 0-100. Higher = better roads = less disruption per mm rain.
    Payout multiplier: 1.0 (urban core) / 1.25 (fringe) / 1.5 (peri-urban).
    Section 2B + Section 3.2 of team guide.
    """
    result = []
    for city, score in CITY_RIQI_SCORES.items():
        band = get_riqi_band(score)
        result.append({
            "city":               city,
            "riqi_score":         score,
            "riqi_band":          band,
            "payout_multiplier":  RIQI_PAYOUT_MULTIPLIER[band],
            "premium_adjustment": RIQI_PREMIUM_ADJUSTMENT[band],
            "interpretation": {
                "urban_core":   "Urban core - better roads, 1.0x payout",
                "urban_fringe": "Urban fringe - moderate risk, 1.25x payout",
                "peri_urban":   "Peri-urban / flood-prone - 1.5x payout",
            }[band],
        })
    return sorted(result, key=lambda x: x["riqi_score"], reverse=True)


@router.get("/riqi/{city}", summary="RIQI score for one city")
def get_city_riqi(city: str):
    """
    Get RIQI score, band, payout multiplier, and premium adjustment for a city.
    Judges can verify: Manoj in Bellandur (flood-prone) pays more than Ravi in Whitefield.
    """
    city_lower = city.lower()
    if city_lower not in CITY_RIQI_SCORES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City '{city}' not found. Supported: {list(CITY_RIQI_SCORES.keys())}",
        )

    score = get_riqi_score(city_lower)
    band  = get_riqi_band(score)

    return {
        "city":               city_lower,
        "riqi_score":         score,
        "riqi_band":          band,
        "payout_multiplier":  RIQI_PAYOUT_MULTIPLIER[band],
        "premium_adjustment": RIQI_PREMIUM_ADJUSTMENT[band],
        "description": {
            "urban_core":   "Urban core zone - good road infrastructure, standard payouts",
            "urban_fringe": "Urban fringe - moderate flood/AQI risk, 1.25x payout uplift",
            "peri_urban":   "Peri-urban / flood-prone - poor roads, maximum 1.5x payout",
        }[band],
        "example": f"A Rs.400 Standard payout becomes Rs.{int(400 * RIQI_PAYOUT_MULTIPLIER[band])} in {city_lower}",
    }


# ------------------------------------------------------------------------------
# PREMIUM QUOTES - onboarding step 5
# ------------------------------------------------------------------------------

@router.get("/quotes", summary="Personalised plan quotes for onboarding")
def get_premium_quotes(
    city:                str         = Query(...,  description="Partner city"),
    zone_id:             Optional[int] = Query(None, description="Zone ID if known"),
    active_days_last_30: int         = Query(15,   description="Active delivery days in last 30"),
    avg_hours_per_day:   float       = Query(8.0,  description="Avg hours per day"),
    loyalty_weeks:       int         = Query(0,    description="Consecutive clean weeks"),
):
    """
    Returns personalised weekly premium quotes for all 3 tiers.
    Called at onboarding after GPS zone detection (Section 4.1 step 5).
    Every number traces back to the Section 3.1 formula.
    Includes underwriting gate and auto-downgrade checks.
    """
    quotes = get_plan_quotes(
        city                = city,
        zone_id             = zone_id,
        active_days_last_30 = active_days_last_30,
        avg_hours_per_day   = avg_hours_per_day,
        loyalty_weeks       = loyalty_weeks,
    )
    return {
        "city":   city,
        "month":  date.today().strftime("%B %Y"),
        "quotes": quotes,
    }


@router.get("/premium", summary="Weekly premium for authenticated partner")
def get_my_premium(
    tier:                str   = Query(...,  description="flex / standard / pro"),
    active_days_last_30: int   = Query(15,   description="Active delivery days in last 30"),
    avg_hours_per_day:   float = Query(8.0,  description="Avg hours per day"),
    loyalty_weeks:       int   = Query(0,    description="Loyalty weeks"),
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Full premium calculation for the authenticated partner.
    Runs underwriting gate + auto-downgrade + full formula.
    """
    city = "bangalore"
    if partner.zone and hasattr(partner.zone, "city"):
        city = partner.zone.city.lower()

    return calculate_weekly_premium(
        partner_id          = partner.id,
        city                = city,
        zone_id             = partner.zone_id,
        requested_tier      = tier,
        active_days_last_30 = active_days_last_30,
        avg_hours_per_day   = avg_hours_per_day,
        loyalty_weeks       = loyalty_weeks,
    )


# ------------------------------------------------------------------------------
# TIER CONFIG
# ------------------------------------------------------------------------------

@router.get("/tiers", summary="All tier configurations")
def get_tier_config():
    """
    Returns all tier configs with fixed pricing (Rs.22/Rs.33/Rs.45) and payout limits.
    Frontend uses this to render plan cards.
    """
    return TIER_CONFIG


# ------------------------------------------------------------------------------
# BCR / LOSS RATIO - admin use
# ------------------------------------------------------------------------------

@router.get("/bcr/{city}", summary="BCR / Loss Ratio for a city (admin)")
def get_city_bcr(
    city:                        str,
    total_claims_paid:           float = Query(..., description="Total claims paid Rs."),
    total_premiums_collected:    float = Query(..., description="Total premiums collected Rs."),
):
    """
    BCR = total_claims_paid / total_premiums_collected. Section 3.4.
    Target 0.55-0.70. > 85% loss ratio -> suspend enrolments. > 100% -> reinsurance.
    Each city is tracked independently - one city over 85% does not affect others.
    """
    result = calculate_bcr(total_claims_paid, total_premiums_collected)
    result["city"] = city.lower()
    return result
````

--- FILE: backend/app/api/claims.py ---
``python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent
from app.schemas.claim import ClaimResponse, ClaimListResponse, ClaimSummary, PayoutMetadata
from app.services.auth import get_current_partner
from app.services.payout_service import get_transaction_log

router = APIRouter(prefix="/claims", tags=["claims"])


def _build_claim_response(claim: Claim, trigger) -> ClaimResponse:
    """Build ClaimResponse and extract payout_metadata from validation_data."""
    payout_metadata = None
    disruption_category = None
    disruption_factor = None
    payment_status = None

    if claim.validation_data:
        try:
            vd = json.loads(claim.validation_data)
            pc = vd.get("payout_calculation")
            if pc:
                payout_metadata = PayoutMetadata(
                    disruption_hours=pc.get("disruption_hours"),
                    hourly_rate=pc.get("hourly_rate"),
                    severity=pc.get("severity"),
                    severity_multiplier=pc.get("severity_multiplier"),
                    base_payout=pc.get("base_payout"),
                    adjusted_payout=pc.get("adjusted_payout"),
                    final_payout=pc.get("final_payout"),
                    trigger_type=pc.get("trigger_type"),
                    zone_id=pc.get("zone_id"),
                )

                # Extract partial disruption data
                pd = pc.get("partial_disruption")
                if pd:
                    disruption_category = pd.get("category")
                    disruption_factor = pd.get("factor")

            # Extract payment state machine status
            ps = vd.get("payment_state")
            if ps:
                payment_status = ps.get("current_status")
        except Exception:
            pass

    return ClaimResponse(
        id=claim.id,
        policy_id=claim.policy_id,
        trigger_event_id=claim.trigger_event_id,
        amount=claim.amount,
        status=claim.status,
        fraud_score=claim.fraud_score,
        upi_ref=claim.upi_ref,
        created_at=claim.created_at,
        paid_at=claim.paid_at,
        trigger_type=trigger.trigger_type if trigger else None,
        trigger_started_at=trigger.started_at if trigger else None,
        payout_metadata=payout_metadata,
        disruption_category=disruption_category,
        disruption_factor=disruption_factor,
        payment_status=payment_status,
    )


@router.get("", response_model=ClaimListResponse)
def get_claims(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status_filter: ClaimStatus | None = None,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get claim history for the current partner."""
    policy_ids = (
        db.query(Policy.id)
        .filter(Policy.partner_id == partner.id)
        .subquery()
    )

    query = db.query(Claim).filter(Claim.policy_id.in_(policy_ids))

    if status_filter:
        query = query.filter(Claim.status == status_filter)

    total = query.count()

    claims = (
        query
        .order_by(Claim.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    claim_responses = []
    for claim in claims:
        trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()
        claim_responses.append(_build_claim_response(claim, trigger))

    return ClaimListResponse(
        claims=claim_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=ClaimSummary)
def get_claims_summary(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get summary of claims for the current partner."""
    policy_ids = (
        db.query(Policy.id)
        .filter(Policy.partner_id == partner.id)
        .subquery()
    )

    total_claims = db.query(Claim).filter(Claim.policy_id.in_(policy_ids)).count()

    total_paid = (
        db.query(func.sum(Claim.amount))
        .filter(Claim.policy_id.in_(policy_ids), Claim.status == ClaimStatus.PAID)
        .scalar()
    ) or 0.0

    pending_claims = (
        db.query(Claim)
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]),
        )
        .count()
    )

    pending_amount = (
        db.query(func.sum(Claim.amount))
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]),
        )
        .scalar()
    ) or 0.0

    return ClaimSummary(
        total_claims=total_claims,
        total_paid=total_paid,
        pending_claims=pending_claims,
        pending_amount=pending_amount,
    )


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get details of a specific claim."""
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id, Claim.policy_id.in_(policy_ids))
        .first()
    )

    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()
    return _build_claim_response(claim, trigger)


@router.get("/{claim_id}/transaction")
def get_claim_transaction(
    claim_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get the full transaction log for a paid claim."""
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id, Claim.policy_id.in_(policy_ids))
        .first()
    )

    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    log = get_transaction_log(claim)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction log not available for this claim",
        )

    return {"claim_id": claim_id, "transaction_log": log}
````

## Main Frontend Files

--- FILE: frontend/src/pages/Dashboard.jsx ---
``jsx
/**
 * Dashboard.jsx  â€“  RapidCover Partner Home
 *
 * Person 1 Phase 2:
 *   - Removed ALL hardcoded constants: zoneReassignment, weatherAlert, streakWeeks
 *   - All state comes from GET /partners/me/experience-state
 *   - Polls every 5 s during active drills; stops after 2 min of inactivity
 *   - Shows strong payout banner when latest_payout.status === "paid"
 *   - Zone alert / reassignment cards only render when backend sends them (non-null)
 *
 * UI: Original green theme preserved (matching Register.jsx / Login.jsx design system).
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { getMyReassignments, acceptReassignment, rejectReassignment } from '../services/proofApi';
import { useAuth } from '../context/AuthContext';
import SourceBadge from '../components/SourceBadge';
import ReassignmentCountdown from '../components/ReassignmentCountdown';
import { useNotifications } from '../hooks/useNotifications';
import OfflineFallbackCard from '../components/OfflineFallbackCard';

const POLL_INTERVAL_MS = 5_000;
const POLL_TIMEOUT_MS  = 120_000;

/* â”€â”€â”€ Design Tokens (identical to Login.jsx & Register.jsx) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const S = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  :root {
    --green-primary: #3DB85C;
    --green-dark:    #2a9e47;
    --green-light:   #e8f7ed;
    --text-dark:     #1a2e1a;
    --text-mid:      #4a5e4a;
    --text-light:    #8a9e8a;
    --white:         #ffffff;
    --gray-bg:       #f7f9f7;
    --border:        #e2ece2;
    --warning:       #d97706;
    --error:         #dc2626;
  }

  .dash-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-bottom: 24px;
  }

  /* â”€â”€ Card â”€â”€ */
  .rc-card {
    background: var(--white);
    border-radius: 20px;
    border: 1.5px solid var(--border);
    overflow: hidden;
  }
  .rc-card-body { padding: 16px 18px; }

  /* â”€â”€ Section titles â”€â”€ */
  .rc-section-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 15px;
    color: var(--text-dark);
    margin-bottom: 12px;
  }

  /* â”€â”€ Coverage hero card â”€â”€ */
  .policy-hero {
    border-radius: 20px;
    padding: 20px 18px;
    color: white;
    position: relative;
    overflow: hidden;
  }
  .policy-hero.flex-tier     { background: linear-gradient(135deg, #059669, #10b981); }
  .policy-hero.standard-tier { background: linear-gradient(135deg, #2563eb, #3b82f6); }
  .policy-hero.pro-tier      { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }
  .policy-hero.no-policy     { background: linear-gradient(135deg, #6b7280, #9ca3af); }

  .policy-hero-label  { font-size: 11px; opacity: 0.75; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
  .policy-hero-tier   { font-family: 'Nunito', sans-serif; font-size: 26px; font-weight: 900; margin-top: 2px; text-transform: capitalize; }
  .policy-hero-badge  {
    position: absolute; top: 16px; right: 16px;
    background: rgba(255,255,255,0.25); border-radius: 20px;
    font-size: 11px; font-weight: 700; padding: 4px 10px;
  }
  .policy-hero-grid   { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-top: 16px; }
  .policy-hero-stat-label { font-size: 10px; opacity: 0.7; }
  .policy-hero-stat-val   { font-family: 'Nunito', sans-serif; font-size: 18px; font-weight: 800; }
  .policy-hero-footer { margin-top: 14px; display: flex; align-items: center; justify-content: space-between; }
  .policy-hero-expires { font-size: 11px; opacity: 0.7; }
  .policy-hero-btn {
    font-size: 11px; background: rgba(255,255,255,0.2); color: white;
    border: none; border-radius: 20px; padding: 6px 14px; cursor: pointer;
    font-family: 'DM Sans', sans-serif; font-weight: 600;
  }
  .policy-hero-btn:hover { background: rgba(255,255,255,0.3); }

  /* â”€â”€ Alert cards â”€â”€ */
  .alert-card {
    border-radius: 16px;
    padding: 14px 16px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
  .alert-orange { background: #fff7ed; border: 1.5px solid #fed7aa; }
  .alert-blue   { background: #eff6ff; border: 1.5px solid #bfdbfe; }
  .alert-red    { background: #fef2f2; border: 1.5px solid #fecaca; }
  .alert-green  { background: #f0fdf4; border: 1.5px solid #bbf7d0; }
  .alert-purple { background: #faf5ff; border: 1.5px solid #e9d5ff; }
  .alert-title  { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 13px; }
  .alert-orange .alert-title { color: #9a3412; }
  .alert-blue   .alert-title { color: #1e40af; }
  .alert-red    .alert-title { color: #991b1b; }
  .alert-green  .alert-title { color: #166534; }
  .alert-purple .alert-title { color: #6b21a8; }
  .alert-body   { font-size: 12px; margin-top: 2px; line-height: 1.5; }
  .alert-orange .alert-body { color: #c2410c; }
  .alert-blue   .alert-body { color: #1d4ed8; }
  .alert-red    .alert-body { color: #dc2626; }
  .alert-green  .alert-body { color: #166534; }
  .alert-purple .alert-body { color: #6b21a8; }

  .alert-actions { display: flex; gap: 8px; margin-top: 10px; }
  .alert-btn-outline {
    flex: 1; padding: 7px; border-radius: 10px; font-size: 12px; font-weight: 600;
    border: 1.5px solid #f97316; color: #9a3412; background: transparent; cursor: pointer;
    font-family: 'DM Sans', sans-serif;
  }
  .alert-btn-fill {
    flex: 2; padding: 7px; border-radius: 10px; font-size: 12px; font-weight: 600;
    border: none; color: white; background: #f97316; cursor: pointer;
    font-family: 'DM Sans', sans-serif;
  }
  .alert-badge {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 12px;
    margin-left: auto;
  }
  .alert-orange .alert-badge { background: #ffedd5; color: #9a3412; }
  .alert-blue   .alert-badge { background: #dbeafe; color: #1e40af; }
  .alert-green  .alert-badge { background: #dcfce7; color: #166534; }
  .alert-purple .alert-badge { background: #ede9fe; color: #6b21a8; }

  /* â”€â”€ Payout banner â”€â”€ */
  .payout-banner {
    background: linear-gradient(135deg, var(--green-primary), var(--green-dark));
    border-radius: 20px;
    padding: 16px 18px;
    color: white;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    position: relative;
    box-shadow: 0 6px 20px rgba(61,184,92,0.35);
  }
  .payout-banner-title   { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 17px; }
  .payout-banner-sub     { font-size: 13px; opacity: 0.9; margin-top: 2px; }
  .payout-banner-time    { font-size: 11px; opacity: 0.7; margin-top: 4px; }
  .payout-banner-dismiss {
    position: absolute; top: 12px; right: 14px;
    background: rgba(255,255,255,0.2); border: none; color: white;
    font-size: 16px; width: 24px; height: 24px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; line-height: 1;
  }
  .payout-banner-dismiss:hover { background: rgba(255,255,255,0.35); }

  /* â”€â”€ Streak bar â”€â”€ */
  .streak-bar-wrap { margin-bottom: 8px; }
  .streak-bar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
  .streak-bar-label  { font-size: 12px; color: var(--text-mid); }
  .streak-bar-val    { font-size: 12px; font-weight: 700; }
  .streak-track { background: #e5e7eb; border-radius: 99px; height: 7px; overflow: hidden; }
  .streak-fill  { height: 7px; border-radius: 99px; transition: width 0.5s ease; }
  .streak-fill.green  { background: #22c55e; }
  .streak-fill.blue   { background: #3b82f6; }
  .streak-fill.purple { background: #8b5cf6; }
  .streak-fill.amber  { background: #f59e0b; }

  /* â”€â”€ Premium breakdown â”€â”€ */
  .breakdown-row { display: flex; justify-content: space-between; align-items: baseline; padding: 4px 0; font-size: 13px; }
  .breakdown-key  { color: var(--text-mid); }
  .breakdown-note { font-size: 11px; color: var(--text-light); margin-left: 4px; }
  .breakdown-val  { font-weight: 600; color: var(--text-dark); }
  .breakdown-val.positive { color: #f97316; }
  .breakdown-val.negative { color: #22c55e; }
  .breakdown-total { border-top: 1.5px solid var(--border); margin-top: 6px; padding-top: 8px; display: flex; justify-content: space-between; }
  .breakdown-total-key { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 14px; color: var(--text-dark); }
  .breakdown-total-val { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 16px; color: var(--green-dark); }

  /* â”€â”€ Trigger chips â”€â”€ */
  .trigger-chip {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px; border-radius: 12px; border: 1px solid;
    font-size: 13px; margin-bottom: 8px;
  }

  /* â”€â”€ Quick action tiles â”€â”€ */
  .qa-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .qa-tile {
    background: var(--white); border: 1.5px solid var(--border); border-radius: 18px;
    padding: 16px 12px; text-align: center; text-decoration: none;
    transition: box-shadow 0.2s, transform 0.2s;
  }
  .qa-tile:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-1px); }
  .qa-tile-icon  { font-size: 24px; }
  .qa-tile-label { font-size: 12px; font-weight: 600; color: var(--text-dark); margin-top: 6px; font-family: 'Nunito', sans-serif; }

  /* â”€â”€ Earnings tiles â”€â”€ */
  .earn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .earn-tile  { background: var(--white); border: 1.5px solid var(--border); border-radius: 18px; padding: 16px; text-align: center; }
  .earn-label  { font-size: 11px; color: var(--text-light); margin-bottom: 4px; }
  .earn-amount { font-family: 'Nunito', sans-serif; font-size: 22px; font-weight: 900; }
  .earn-claims { font-size: 11px; color: var(--text-light); margin-top: 2px; }

  /* â”€â”€ Claims list â”€â”€ */
  .claim-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 0; border-bottom: 1px solid var(--border);
  }
  .claim-row:last-child { border-bottom: none; }
  .claim-label { font-size: 13px; font-weight: 600; color: var(--text-dark); }
  .claim-date  { font-size: 11px; color: var(--text-light); margin-top: 1px; }
  .claim-amount { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px; color: var(--text-dark); text-align: right; }
  .claim-status {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
    text-align: right; margin-top: 2px; display: inline-block;
  }
  .st-paid     { background: #dcfce7; color: #166534; }
  .st-pending  { background: #fef9c3; color: #854d0e; }
  .st-approved { background: #dbeafe; color: #1e40af; }
  .st-rejected { background: #fee2e2; color: #991b1b; }

  /* â”€â”€ Coverage list â”€â”€ */
  .cov-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; font-size: 13px; color: var(--text-mid); }

  /* â”€â”€ Section header with action â”€â”€ */
  .sec-hdr { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
  .sec-hdr-link { font-size: 12px; font-weight: 600; color: var(--green-dark); text-decoration: none; }

  /* â”€â”€ Monday badge â”€â”€ */
  .monday-badge {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
    background: #dbeafe; color: #1e40af; margin-left: 8px;
  }

  /* â”€â”€ Toggle button â”€â”€ */
  .rc-toggle-btn {
    font-size: 11px; font-weight: 600; color: var(--green-dark); background: var(--green-light);
    border: none; border-radius: 20px; padding: 4px 12px; cursor: pointer; font-family: 'DM Sans', sans-serif;
  }

  /* â”€â”€ No policy CTA â”€â”€ */
  .no-policy-cta { text-align: center; padding: 28px 16px; }
  .no-policy-icon  { font-size: 48px; }
  .no-policy-title { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; color: var(--text-dark); margin: 10px 0 6px; }
  .no-policy-sub   { font-size: 13px; color: var(--text-mid); margin-bottom: 18px; }
  .rc-btn-primary {
    display: inline-block; background: var(--green-primary); color: white;
    border: none; border-radius: 14px; padding: 13px 28px; font-family: 'Nunito', sans-serif;
    font-weight: 800; font-size: 15px; cursor: pointer; text-decoration: none;
    transition: background 0.2s;
  }
  .rc-btn-primary:hover { background: var(--green-dark); }

  /* â”€â”€ Live badge â”€â”€ */
  .live-badge {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
    background: var(--green-light); color: var(--green-dark);
    display: inline-flex; align-items: center; gap: 4px;
  }
  .live-dot {
    width: 6px; height: 6px; background: var(--green-primary);
    border-radius: 50%; animation: pulse 1.5s infinite;
  }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  @keyframes spin   { to { transform: rotate(360deg); } }
`;

/* â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */

const TRIGGER_INFO = {
  rain:     { icon: 'ðŸŒ§ï¸', label: 'Heavy Rain',      color: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
  heat:     { icon: 'ðŸŒ¡ï¸', label: 'Extreme Heat',    color: '#fef2f2', border: '#fecaca', text: '#991b1b' },
  aqi:      { icon: 'ðŸ’¨', label: 'Dangerous AQI',   color: '#fffbeb', border: '#fde68a', text: '#92400e' },
  shutdown: { icon: 'ðŸš«', label: 'Civic Shutdown',   color: '#faf5ff', border: '#e9d5ff', text: '#6b21a8' },
  closure:  { icon: 'ðŸª', label: 'Store Closure',    color: '#f9fafb', border: '#e5e7eb', text: '#374151' },
};
const STATUS_CLS = { paid: 'st-paid', pending: 'st-pending', approved: 'st-approved', rejected: 'st-rejected' };
const BASES      = { flex: 22, standard: 33, pro: 45 };
const COV_EVENTS = [
  { icon: 'ðŸŒ§ï¸', label: 'Heavy Rain & Floods' },
  { icon: 'ðŸŒ¡ï¸', label: 'Extreme Heat (>43Â°C)' },
  { icon: 'ðŸ’¨', label: 'Dangerous AQI (>400)' },
  { icon: 'ðŸš«', label: 'Curfew & Bandh' },
  { icon: 'ðŸª', label: 'Dark Store Closures' },
];

/* â”€â”€â”€ Sub-components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */

/** Shown prominently at top when a paid claim exists */
function PayoutBanner({ payout, onDismiss }) {
  if (!payout || payout.status !== 'paid') return null;
  return (
    <div className="payout-banner">
      <span style={{ fontSize: 28 }}>ðŸ’¸</span>
      <div style={{ flex: 1 }}>
        <p className="payout-banner-title">Money Sent!</p>
        <p className="payout-banner-sub">
          â‚¹{payout.amount} paid via UPI{payout.upi_ref ? ` Â· Ref: ${payout.upi_ref}` : ''}
        </p>
        {payout.paid_at && (
          <p className="payout-banner-time">
            {new Date(payout.paid_at).toLocaleString('en-IN', {
              day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
            })}
          </p>
        )}
      </div>
      <button className="payout-banner-dismiss" onClick={onDismiss} aria-label="Dismiss">Ã—</button>
    </div>
  );
}

/** Only renders when backend sends a non-null zone_alert */
function ZoneAlertCard({ alert }) {
  if (!alert) return null;
  const alertClass = alert.severity === 'high' || alert.severity === 'critical' ? 'alert-red' : 'alert-blue';
  const icon = TRIGGER_INFO[alert.type]?.icon || 'âš ï¸';
  return (
    <div className={`alert-card ${alertClass}`}>
      <span style={{ fontSize: 22 }}>{icon}</span>
      <div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="alert-title">48-Hour {alert.type?.charAt(0).toUpperCase() + alert.type?.slice(1)} Alert</span>
          <span className="alert-badge">{alert.severity?.toUpperCase()}</span>
        </div>
        <p className="alert-body">{alert.message}</p>
        <p style={{ fontSize: 11, color: '#3b82f6', marginTop: 4 }}>Keep your documents handy for quick claims.</p>
      </div>
    </div>
  );
}

/** Only renders when pending reassignment exists */
function ZoneReassignmentCard({ card, onAccept, onDismiss, processing }) {
  if (!card) return null;
  const { old_zone, new_zone, premium_delta, expires_at } = card;
  return (
    <div className="alert-card alert-orange">
      <span style={{ fontSize: 22 }}>ðŸ“</span>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="alert-title">Zone Reassignment</span>
          {expires_at && <ReassignmentCountdown expiresAt={expires_at} onExpire={onDismiss} />}
        </div>
        <p className="alert-body">
          Your zone is changing from <strong>{old_zone}</strong> to <strong>{new_zone}</strong>.
          {premium_delta !== 0 && (
            <span style={{ color: premium_delta > 0 ? '#166534' : '#c2410c' }}>
              {' '}Premium {premium_delta > 0 ? `-â‚¹${premium_delta}` : `+â‚¹${Math.abs(premium_delta)}`}/week.
            </span>
          )}
        </p>
        <div className="alert-actions">
          <button
            className="alert-btn-outline"
            onClick={onDismiss}
            disabled={processing}
          >
            {processing ? 'Processing...' : 'Decline'}
          </button>
          <button
            className="alert-btn-fill"
            onClick={onAccept}
            disabled={processing}
          >
            {processing ? 'Processing...' : 'Accept New Zone'}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Loyalty/streak progress bars â€“ same visual as original */
function StreakProgressBar({ loyalty }) {
  if (!loyalty) return null;
  const { streak_weeks, next_milestone } = loyalty;
  const w4  = Math.min((streak_weeks / 4)  * 100, 100);
  const w12 = Math.min((streak_weeks / 12) * 100, 100);
  const done4  = streak_weeks >= 4;
  const done12 = streak_weeks >= 12;

  return (
    <div className="rc-card">
      <div className="rc-card-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <span className="rc-section-title" style={{ marginBottom: 0 }}>ðŸ”¥ Loyalty Streak</span>
          <span style={{ fontSize: 12, color: 'var(--text-light)', fontWeight: 600 }}>
            {streak_weeks} week{streak_weeks !== 1 ? 's' : ''} active
          </span>
        </div>
        <div className="streak-bar-wrap">
          <div className="streak-bar-header">
            <span className="streak-bar-label">{done4 ? 'âœ…' : 'ðŸŽ¯'} 4-week milestone (6% off)</span>
            <span className="streak-bar-val" style={{ color: done4 ? '#22c55e' : 'var(--text-mid)' }}>
              {done4 ? 'Unlocked!' : `${streak_weeks}/4 wks`}
            </span>
          </div>
          <div className="streak-track">
            <div className={`streak-fill ${done4 ? 'green' : 'blue'}`} style={{ width: `${w4}%` }} />
          </div>
        </div>
        <div className="streak-bar-wrap" style={{ marginTop: 12 }}>
          <div className="streak-bar-header">
            <span className="streak-bar-label">{done12 ? 'âœ…' : 'ðŸ†'} 12-week milestone (10% off)</span>
            <span className="streak-bar-val" style={{ color: done12 ? '#22c55e' : 'var(--text-mid)' }}>
              {done12 ? 'Unlocked!' : `${streak_weeks}/12 wks`}
            </span>
          </div>
          <div className="streak-track">
            <div className={`streak-fill ${done12 ? 'green' : 'purple'}`} style={{ width: `${w12}%` }} />
          </div>
        </div>
        {!done4 && (
          <p style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 10 }}>
            Keep your policy active every week to unlock loyalty discounts.
          </p>
        )}
      </div>
    </div>
  );
}

/** Premium breakdown â€“ collapsible, same design as original */
export function WeeklyPremiumBreakdown({ breakdown, policy }) {
  const today    = new Date();
  const isMonday = today.getDay() === 1;
  const [open, setOpen] = useState(isMonday);

  // Only render if we have a policy
  if (!policy) return null;

  // Show unavailable state when backend breakdown is not available
  // (B2: removed hardcoded fallback values per phase 2 requirements)
  if (!breakdown) {
    return (
      <div className="rc-card">
        <div className="rc-card-body">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span className="rc-section-title" style={{ marginBottom: 0 }}>ðŸ“Š Premium Breakdown</span>
              {isMonday && <span className="monday-badge">This week</span>}
            </div>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-light)', marginTop: 8 }}>
            Premium breakdown is unavailable right now. Check back later.
          </p>
        </div>
      </div>
    );
  }

  const rows = [
    { label: 'Base Premium',       note: policy?.tier ? `${policy.tier} plan` : '',      val: `â‚¹${breakdown.base}`,                cls: '' },
    { label: 'Zone Risk Factor',   note: 'Zone surcharge',                                val: `+â‚¹${breakdown.zone_risk}`,          cls: 'positive' },
    { label: 'Seasonal Index',     note: 'City-specific monthly',                         val: `Ã—${Number(breakdown.seasonal_index).toFixed(2)}`,  cls: '' },
    { label: 'RIQI Adjustment',    note: breakdown.riqi_band || '',                        val: `Ã—${Number(breakdown.riqi_adjustment).toFixed(2)}`, cls: 'positive' },
    { label: 'Activity Tier Factor', note: policy?.tier || '',                             val: `Ã—${Number(breakdown.activity_factor).toFixed(2)}`, cls: '' },
    { label: 'Loyalty Discount',   note: breakdown.loyalty_weeks ? `${breakdown.loyalty_weeks}-week streak` : '4-week streak', val: `Ã—${Number(breakdown.loyalty_discount).toFixed(2)}`, cls: 'negative' },
    { label: 'Platform Fee',       note: 'Waived',                                        val: 'â‚¹0',                                cls: '' },
  ];
  const total = breakdown.total;

  return (
    <div className="rc-card">
      <div className="rc-card-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span className="rc-section-title" style={{ marginBottom: 0 }}>ðŸ“Š Premium Breakdown</span>
            {isMonday && <span className="monday-badge">This week</span>}
          </div>
          <button className="rc-toggle-btn" onClick={() => setOpen(v => !v)}>{open ? 'Hide' : 'Show'}</button>
        </div>

        {!open ? (
          <p style={{ fontSize: 13, color: 'var(--text-mid)', marginTop: 8 }}>
            Total: <strong style={{ color: 'var(--text-dark)' }}>â‚¹{total}/week</strong>
          </p>
        ) : (
          <div style={{ marginTop: 12 }}>
            {rows.map(r => (
              <div className="breakdown-row" key={r.label}>
                <span className="breakdown-key">
                  {r.label}
                  {r.note && <span className="breakdown-note">({r.note})</span>}
                </span>
                <span className={`breakdown-val ${r.cls}`}>{r.val}</span>
              </div>
            ))}
            <div className="breakdown-total">
              <span className="breakdown-total-key">Total This Week</span>
              <span className="breakdown-total-val">â‚¹{total}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* â”€â”€â”€ Main Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [expState,      setExpState]      = useState(null);
  const [policy,        setPolicy]        = useState(null);
  const [summary,       setSummary]       = useState(null);
  const [zone,          setZone]          = useState(null);
  const [triggers,      setTriggers]      = useState([]);
  const [recentClaims,  setRecentClaims]  = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState(null);
  const [payoutDismissed,   setPayoutDismissed]   = useState(false);
  const [reassignDismissed, setReassignDismissed] = useState(false);
  const [pollingActive, setPollingActive] = useState(true);
  const [pendingReassignment, setPendingReassignment] = useState(null);
  const [reassignProcessing, setReassignProcessing] = useState(false);
  const [offlineSim, setOfflineSim] = useState(false);
  const { isSupported, permission, isSubscribed, enableNotifications } = useNotifications();
  const [hasActivatedThisSession, setHasActivatedThisSession] = useState(false);
  const [notifLoading, setNotifLoading] = useState(false);

  const pollRef         = useRef(null);
  const activityRef     = useRef(null);
  const seenPayoutIdRef = useRef(null);

  /* â”€â”€ idle timer â”€â”€ */
  const resetActivityTimer = useCallback(() => {
    if (activityRef.current) clearTimeout(activityRef.current);
    setPollingActive(true);
    activityRef.current = setTimeout(() => setPollingActive(false), POLL_TIMEOUT_MS);
  }, []);

  /* â”€â”€ fetch all in parallel â”€â”€ */
  const fetchAll = useCallback(async (isInitial = false) => {
    try {
      const [expRes, polRes, sumRes, claimsRes, reassignRes] = await Promise.allSettled([
        api.getPartnerExperienceState().catch(() => null),
        api.getActivePolicy().catch(() => null),
        api.getClaimsSummary().catch(() => null),
        api.getClaims({ limit: 5 }).catch(() => ({ claims: [] })),
        getMyReassignments().catch(() => ({ reassignments: [] })),
      ]);

      if (expRes.status === 'fulfilled' && expRes.value) {
        const exp = expRes.value;
        setExpState(exp);
        const lp = exp.latest_payout;
        if (lp?.status === 'paid' && lp.claim_id !== seenPayoutIdRef.current) {
          seenPayoutIdRef.current = lp.claim_id;
          setPayoutDismissed(false);
        }
        if (exp.zone_alert) resetActivityTimer();
      }

      if (polRes.status === 'fulfilled')    setPolicy(polRes.value);
      if (sumRes.status === 'fulfilled')    setSummary(sumRes.value);
      if (claimsRes.status === 'fulfilled') {
        const raw = claimsRes.value;
        // API may return {claims:[]} or a plain array
        setRecentClaims(Array.isArray(raw) ? raw : (raw?.claims || []));
      }

      // Get pending reassignment (status === 'proposed')
      if (reassignRes.status === 'fulfilled' && reassignRes.value) {
        console.log('[Dashboard] Reassignments response:', reassignRes.value);
        const allReassignments = reassignRes.value.reassignments || [];
        const pending = allReassignments.find(r => r.status === 'proposed');
        console.log('[Dashboard] Pending reassignment:', pending);
        if (pending && !reassignDismissed) {
          setPendingReassignment(pending);
        }
      }

      // Also load zone & active triggers if we have a zone_id
      if (isInitial && user?.zone_id) {
        const z  = await api.getZone(user.zone_id).catch(() => null);
        const tr = await api.getActiveTriggers(user.zone_id).catch(() => ({ triggers: [] }));
        setZone(z);
        setTriggers(tr.triggers || []);
      }

      if (isInitial) setError(null);
    } catch (err) {
      if (isInitial) setError(err.message);
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [user?.zone_id, resetActivityTimer, reassignDismissed]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchAll(true);
    resetActivityTimer();
    return () => {
      if (pollRef.current)    clearInterval(pollRef.current);
      if (activityRef.current) clearTimeout(activityRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (pollingActive) {
      pollRef.current = setInterval(() => fetchAll(false), POLL_INTERVAL_MS);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pollingActive, fetchAll]);

  /* â”€â”€ reassignment accept/reject handlers â”€â”€ */
  const handleAcceptReassignment = async () => {
    if (!pendingReassignment?.id) return;
    setReassignProcessing(true);
    try {
      await acceptReassignment(pendingReassignment.id);
      setPendingReassignment(null);
      setReassignDismissed(true);
      // Refresh to get updated zone_id
      fetchAll(false);
    } catch (err) {
      console.error('Failed to accept reassignment:', err);
    } finally {
      setReassignProcessing(false);
    }
  };

  const handleRejectReassignment = async () => {
    if (!pendingReassignment?.id) return;
    setReassignProcessing(true);
    try {
      await rejectReassignment(pendingReassignment.id);
      setPendingReassignment(null);
      setReassignDismissed(true);
    } catch (err) {
      console.error('Failed to reject reassignment:', err);
    } finally {
      setReassignProcessing(false);
    }
  };

  const handleEnableNotifications = async () => {
    try {
      await enableNotifications();
      setHasActivatedThisSession(true);
    } catch (err) {
      console.error('Notification failed:', err);
    }
  };

  /* â”€â”€ derived â”€â”€ */
  const zoneAlert       = expState?.zone_alert       ?? null;
  const loyalty         = expState?.loyalty          ?? null;
  const premiumBreakdown = expState?.premium_breakdown ?? null;
  const latestPayout    = expState?.latest_payout    ?? null;

  // Build reassignment card data from pending reassignment (has ID for API calls)
  const zoneReassignmentCard = pendingReassignment ? {
    old_zone: pendingReassignment.old_zone_name || `Zone #${pendingReassignment.old_zone_id}`,
    new_zone: pendingReassignment.new_zone_name || `Zone #${pendingReassignment.new_zone_id}`,
    premium_delta: pendingReassignment.premium_adjustment || 0,
    expires_at: pendingReassignment.expires_at,
  } : null;

  const daysLeft  = policy ? Math.ceil((new Date(policy.expires_at) - new Date()) / 864e5) : 0;
  const tierClass = { flex: 'flex-tier', standard: 'standard-tier', pro: 'pro-tier' }[policy?.tier] || 'no-policy';

  /* â”€â”€ loading state â”€â”€ */
  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 240 }}>
      <div style={{
        width: 32, height: 32,
        border: '3px solid var(--green-light)',
        borderTopColor: 'var(--green-primary)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
    </div>
  );

  return (
    <>
      <style>{S}</style>
      <div className="dash-wrap">

        {/* â”€â”€ Welcome header â”€â”€ */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 900, fontSize: 22, color: 'var(--text-dark)' }}>
              Hello, {user?.name?.split(' ')[0] || 'Partner'} ðŸ‘‹
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-light)', marginTop: 2 }}>
              {zone ? `${zone.name} (${zone.code})` : 'Set your zone in profile'}
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
            <button 
              onClick={() => setOfflineSim(!offlineSim)}
              style={{
                fontSize: 10, background: offlineSim ? '#ef4444' : 'transparent', 
                border: '1.5px solid ' + (offlineSim ? '#ef4444' : '#e2ece2'), padding: '2px 8px', borderRadius: 12,
                color: offlineSim ? 'white' : 'var(--text-light)', cursor: 'pointer', marginBottom: 2, fontFamily: "'DM Sans', sans-serif"
              }}
            >
              Offline Sim
            </button>
            {policy && (
              <span style={{
                display: 'flex', alignItems: 'center', gap: 6, background: 'var(--green-light)',
                border: '1px solid #bbf7d0', color: 'var(--green-dark)', fontSize: 11,
                fontWeight: 700, padding: '5px 12px', borderRadius: 20,
              }}>
                <span style={{ width: 6, height: 6, background: 'var(--green-primary)', borderRadius: '50%', animation: 'pulse 1.5s infinite' }} />
                Covered
              </span>
            )}
            {pollingActive && (
              <span style={{ fontSize: 10, color: 'var(--text-light)' }}>ðŸ”„ Live</span>
            )}
          </div>
        </div>
        
        {offlineSim && <OfflineFallbackCard />}

        {/* â”€â”€ 0. Notification Prompt (Hackathon Demo - Shows once per session until clicked) â”€â”€ */}
        {!hasActivatedThisSession && isSupported && permission !== 'denied' && (
          <div className="alert-card alert-purple" style={{ cursor: 'pointer' }} onClick={handleEnableNotifications}>
            <span style={{ fontSize: 22 }}>ðŸ””</span>
            <div style={{ flex: 1 }}>
              <span className="alert-title">{isSubscribed ? 'Pushes Synced' : 'Enable Payout Alerts'}</span>
              <p className="alert-body">
                {isSubscribed ? 'Your phone is currently receiving updates' : 'Get notified the second a payment hits your UPI ID'}
              </p>
              <button 
                className="alert-btn-fill" 
                style={{ marginTop: 8, background: '#22c55e', width: 'auto', padding: '6px 16px' }}
              >
                {isSubscribed ? 'Re-Sync' : 'Activate'}
              </button>
            </div>
          </div>
        )}

        {/* â”€â”€ 1. Payout Banner â€“ always top, only when paid â”€â”€ */}
        {!payoutDismissed && (
          <PayoutBanner payout={latestPayout} onDismiss={() => setPayoutDismissed(true)} />
        )}

        {/* â”€â”€ 2. Zone Alert â€“ only when backend sends one â”€â”€ */}
        <ZoneAlertCard alert={zoneAlert} />

        {/* â”€â”€ 3. Zone Reassignment â€“ only when pending reassignment exists â”€â”€ */}
        {!reassignDismissed && zoneReassignmentCard && (
          <ZoneReassignmentCard
            card={zoneReassignmentCard}
            onAccept={handleAcceptReassignment}
            onDismiss={handleRejectReassignment}
            processing={reassignProcessing}
          />
        )}

        {/* â”€â”€ 4. Active Triggers â”€â”€ */}
        {triggers.length > 0 && (
          <div className="alert-card alert-red">
            <span style={{ fontSize: 22 }}>âš ï¸</span>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span className="alert-title">Active Disruptions in Your Zone</span>
                <span style={{ marginLeft: 8, background: '#ef4444', color: 'white', fontSize: 10, fontWeight: 800, padding: '2px 7px', borderRadius: 10 }}>
                  {triggers.length}
                </span>
              </div>
              {triggers.map(t => (
                <div key={t.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'white', padding: '10px 14px', borderRadius: '12px', border: '1px solid #e5e7eb', marginTop: '8px' }}>
                  <SourceBadge type={t.trigger_type} severity={t.severity} size="md" />
                </div>
              ))}
              {policy && (
                <p style={{ fontSize: 12, color: '#dc2626', marginTop: 6, fontWeight: 600 }}>
                  âœ… You're covered! Claims will be auto-processed.
                </p>
              )}
            </div>
          </div>
        )}

        {/* â”€â”€ 5. Coverage Hero Card â”€â”€ */}
        {policy ? (
          <div className={`policy-hero ${tierClass}`}>
            <p className="policy-hero-label">Active Policy</p>
            <p className="policy-hero-tier">{policy.tier}</p>
            <span className="policy-hero-badge">Active</span>
            <div className="policy-hero-grid">
              <div>
                <p className="policy-hero-stat-label">Daily Payout</p>
                <p className="policy-hero-stat-val">â‚¹{policy.max_daily_payout}</p>
              </div>
              <div>
                <p className="policy-hero-stat-label">Max Days/Wk</p>
                <p className="policy-hero-stat-val">{policy.max_days_per_week}</p>
              </div>
              <div>
                <p className="policy-hero-stat-label">Days Left</p>
                <p className="policy-hero-stat-val">{daysLeft > 0 ? daysLeft : 'â€”'}</p>
              </div>
            </div>
            <div className="policy-hero-footer">
              <div>
                <p className="policy-hero-expires">
                  Expires {new Date(policy.expires_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                </p>
                <p style={{ fontSize: 10, opacity: 0.65, marginTop: 2 }}>
                  Next week: â‚¹{BASES[policy.tier] || 'â€”'} â€” zone risk + seasonal included
                </p>
              </div>
              <Link to="/policy"><button className="policy-hero-btn">Details â†’</button></Link>
            </div>
          </div>
        ) : (
          <div className="rc-card">
            <div className="no-policy-cta">
              <div className="no-policy-icon">ðŸ›¡ï¸</div>
              <p className="no-policy-title">No Active Policy</p>
              <p className="no-policy-sub">Protect your income from disruptions</p>
              <Link to="/policy" className="rc-btn-primary">Get Coverage</Link>
            </div>
          </div>
        )}

        {/* â”€â”€ 6. Loyalty Streak â”€â”€ */}
        <StreakProgressBar loyalty={loyalty} />

        {/* â”€â”€ 7. Weekly Premium Breakdown â”€â”€ */}
        <WeeklyPremiumBreakdown breakdown={premiumBreakdown} policy={policy} />

        {/* â”€â”€ 8. Earnings Summary â”€â”€ */}
        <div>
          <p className="rc-section-title">Earnings</p>
          <div className="earn-grid">
            <div className="earn-tile">
              <p className="earn-label">Total Received</p>
              <p className="earn-amount" style={{ color: 'var(--green-dark)' }}>â‚¹{summary?.total_paid || 0}</p>
              <p className="earn-claims">{summary?.total_claims || 0} claims</p>
            </div>
            <div className="earn-tile">
              <p className="earn-label">Pending</p>
              <p className="earn-amount" style={{ color: '#f97316' }}>â‚¹{summary?.pending_amount || 0}</p>
              <p className="earn-claims">{summary?.pending_claims || 0} claims</p>
            </div>
          </div>
        </div>

        {/* â”€â”€ 9. Recent Claims â”€â”€ */}
        {recentClaims.length > 0 && (
          <div className="rc-card">
            <div className="rc-card-body">
              <div className="sec-hdr">
                <span className="rc-section-title" style={{ marginBottom: 0 }}>Recent Claims</span>
                <Link to="/claims" className="sec-hdr-link">View All â†’</Link>
              </div>
              {recentClaims.map(claim => (
                <div className="claim-row" key={claim.id}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <SourceBadge type={claim.trigger_type} showLabel={false} size="lg" />
                    <div>
                      <p className="claim-label" style={{textTransform: 'capitalize'}}>{claim.trigger_type}</p>
                      <p className="claim-date">
                        {new Date(claim.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="claim-amount">â‚¹{claim.amount}</p>
                    <span className={`claim-status ${STATUS_CLS[claim.status] || 'st-pending'}`}>{claim.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* â”€â”€ 10. Quick Actions â”€â”€ */}
        <div>
          <p className="rc-section-title">Quick Actions</p>
          <div className="qa-grid">
            <Link to="/policy" className="qa-tile">
              <div className="qa-tile-icon">ðŸ“‹</div>
              <p className="qa-tile-label">View Policy</p>
            </Link>
            <Link to="/claims" className="qa-tile">
              <div className="qa-tile-icon">ðŸ’°</div>
              <p className="qa-tile-label">Claim History</p>
            </Link>
          </div>
        </div>

        {/* â”€â”€ 11. Coverage events â”€â”€ */}
        <div className="rc-card">
          <div className="rc-card-body">
            <p className="rc-section-title">You're covered for:</p>
            {COV_EVENTS.map(e => (
              <div className="cov-row" key={e.label}>
                <span style={{ fontSize: 18 }}>{e.icon}</span>
                <span>{e.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div style={{ background: '#fef2f2', border: '1.5px solid #fecaca', borderRadius: 16, padding: '14px 16px', color: '#dc2626', fontSize: 13 }}>
            {error}
          </div>
        )}

      </div>
    </>
  );
}

export default Dashboard;
````

--- FILE: frontend/src/pages/Claims.jsx ---
``jsx
/**
 * Claims.jsx  â€“  Partner claims list
 *
 * Person 1 Phase 2:
 *   - Shows payout banner when a new paid claim arrives
 *   - Fetches claims, claims summary
 *   - Now themed with the green design system!
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import ProofCard from '../components/ProofCard';

const POLL_INTERVAL_MS = 5_000;
const POLL_TIMEOUT_MS = 120_000;

const S = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  :root {
    --green-primary: #3DB85C;
    --green-dark:    #2a9e47;
    --green-light:   #e8f7ed;
    --text-dark:     #1a2e1a;
    --text-mid:      #4a5e4a;
    --text-light:    #8a9e8a;
    --white:         #ffffff;
    --gray-bg:       #f7f9f7;
    --border:        #e2ece2;
    --warning:       #d97706;
    --error:         #dc2626;
  }

  .claims-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 24px 16px 32px;
    background: var(--gray-bg);
    min-height: 100vh;
  }

  .claims-page-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 24px;
    color: var(--text-dark);
  }
  .claims-page-sub { font-size: 13px; color: var(--text-light); margin-top: 2px; }

  .claims-card {
    background: var(--white);
    border-radius: 20px;
    border: 1.5px solid var(--border);
    padding: 16px 18px;
    margin-bottom: 12px;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 20px;
  }
  .summary-card {
    background: var(--white);
    border: 1.5px solid var(--border);
    border-radius: 16px;
    padding: 12px;
    text-align: center;
  }
  .summary-val { font-family: 'Nunito', sans-serif; font-size: 20px; font-weight: 900; }
  .summary-lbl { font-size: 11px; color: var(--text-mid); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }

  .claim-row {
    display: flex; justify-content: space-between; align-items: flex-start;
  }
  .claim-amt { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; color: var(--text-dark); }
  .claim-date { font-size: 12px; color: var(--text-light); margin-top: 2px; }
  .claim-badge { 
    font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px; 
    display: inline-flex; align-items: center; gap: 4px; border: 1.5px solid transparent;
  }
  .badge-paid { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
  .badge-approved { background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }
  .badge-pending { background: #fffbeb; color: #b45309; border-color: #fde68a; }
  .badge-rejected { background: #fef2f2; color: #991b1b; border-color: #fecaca; }

  .claim-footer { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border); }
  .claim-ref { font-size: 11.5px; color: var(--green-dark); font-weight: 600; }
  .claim-fraud { font-size: 11.5px; color: #b45309; font-weight: 600; }

  .payout-banner {
    position: relative; background: var(--green-primary); color: white;
    border-radius: 20px; padding: 16px; margin-bottom: 16px;
    display: flex; gap: 12px; align-items: flex-start;
  }
  .payout-icon { font-size: 28px; }
  .pb-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 16px; margin-bottom: 2px; }
  .pb-sub { font-size: 12.5px; opacity: 0.9; }
  .pb-close {
    position: absolute; top: 12px; right: 14px;
    background: transparent; border: none; color: white;
    font-size: 20px; opacity: 0.8; cursor: pointer;
  }

  .empty-state { text-align: center; padding: 40px 20px; }
  .empty-icon { font-size: 48px; margin-bottom: 12px; }
  .empty-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 18px; color: var(--text-dark); }
  .empty-sub { font-size: 13px; color: var(--text-mid); margin-top: 4px; }
`;

const STATUS_STYLES = {
  paid: { class: 'badge-paid', label: 'PAID', icon: 'âœ…' },
  approved: { class: 'badge-approved', label: 'APPROVED', icon: 'ðŸ‘' },
  pending: { class: 'badge-pending', label: 'PENDING', icon: 'â³' },
  rejected: { class: 'badge-rejected', label: 'REJECTED', icon: 'âŒ' },
};

function PayoutBanner({ claim, onDismiss }) {
  if (!claim) return null;
  return (
    <div className="payout-banner">
      <span className="payout-icon">ðŸ’¸</span>
      <div>
        <p className="pb-title">Payout received!</p>
        <p className="pb-sub">
          â‚¹{claim.amount} Â· Claim #{claim.id}
          {claim.upi_ref ? (claim.upi_ref.startsWith('tr_') ? ` Â· Stripe: ${claim.upi_ref}` : ` Â· UPI: ${claim.upi_ref}`) : ''}
        </p>
      </div>
      <button className="pb-close" onClick={onDismiss}>Ã—</button>
    </div>
  );
}

// Replaced local ClaimCard with B2 ProofCard.

export default function Claims() {
  const [claims, setClaims] = useState([]);
  const [summary, setSummary] = useState(null);
  const [newPaidClaim, setNewPaidClaim] = useState(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pollingActive, setPollingActive] = useState(true);

  const pollRef = useRef(null);
  const activityRef = useRef(null);
  const seenPaidIdsRef = useRef(new Set());

  const fetchAll = useCallback(async (isInitial = false) => {
    try {
      const [claimsRes, summaryRes, triggersRes] = await Promise.allSettled([
        api.getClaims({ limit: 20 }),
        api.getClaimsSummary(),
        api.getActiveTriggers().catch(() => []),
      ]);

      if (claimsRes.status === 'fulfilled') {
        const list = Array.isArray(claimsRes.value) ? claimsRes.value : (claimsRes.value?.claims || []);
        setClaims(list);

        const paidNow = list.find(
          c => c.status === 'paid' && !seenPaidIdsRef.current.has(c.id)
        );
        if (paidNow) {
          seenPaidIdsRef.current.add(paidNow.id);
          setNewPaidClaim(paidNow);
          setBannerDismissed(false);
          resetActivityTimer();
        }
      }

      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value);

      if (triggersRes.status === 'fulfilled') {
        const triggers = Array.isArray(triggersRes.value) ? triggersRes.value : (triggersRes.value?.triggers || []);
        if (triggers.length > 0) resetActivityTimer();
      }

      if (isInitial) setError(null);
    } catch (err) {
      if (isInitial) setError(err.message);
    } finally {
      if (isInitial) setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const resetActivityTimer = useCallback(() => {
    if (activityRef.current) clearTimeout(activityRef.current);
    setPollingActive(true);
    activityRef.current = setTimeout(() => setPollingActive(false), POLL_TIMEOUT_MS);
  }, []);

  useEffect(() => {
    fetchAll(true);
    resetActivityTimer();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (activityRef.current) clearTimeout(activityRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (pollingActive) {
      pollRef.current = setInterval(() => fetchAll(false), POLL_INTERVAL_MS);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pollingActive, fetchAll]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--gray-bg)' }}>
        <div style={{ width: 32, height: 32, border: '3px solid var(--green-light)', borderTopColor: 'var(--green-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      </div>
    );
  }

  return (
    <>
      <style>{S}</style>
      <div className="claims-wrap">
        <div>
          <h1 className="claims-page-title">Claims</h1>
          <p className="claims-page-sub">
            {pollingActive ? 'ðŸ”„ Auto-updating' : 'Your automatic payouts'}
          </p>
        </div>

        {!bannerDismissed && (
          <PayoutBanner claim={newPaidClaim} onDismiss={() => setBannerDismissed(true)} />
        )}

        {summary && (
          <div className="summary-grid">
            <div className="summary-card">
              <p className="summary-val text-green-dark" style={{ color: 'var(--green-dark)' }}>
                {/* Count of paid claims = total_claims - pending_claims */}
                {(summary.total_claims ?? 0) - (summary.pending_claims ?? 0)}
              </p>
              <p className="summary-lbl">Paid</p>
            </div>
            <div className="summary-card">
              <p className="summary-val text-orange-500" style={{ color: '#d97706' }}>{summary.pending_claims ?? 0}</p>
              <p className="summary-lbl">Pending</p>
            </div>
            <div className="summary-card">
              <p className="summary-val">{summary.total_claims ?? 0}</p>
              <p className="summary-lbl">Total</p>
            </div>
          </div>
        )}

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '12px', borderRadius: '12px', color: '#991b1b', fontSize: 13, marginBottom: 16 }}>
            {error}
          </div>
        )}

        {claims.length === 0 ? (
          <div className="empty-state">
            <p className="empty-icon">ðŸ“­</p>
            <p className="empty-title">No claims yet</p>
            <p className="empty-sub">Claims appear here when a trigger fires in your zone.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {claims.map(claim => (
              <ProofCard
                key={claim.id}
                triggerType={claim.trigger_type}
                severity={claim.severity}
                status={claim.status}
                amount={claim.amount}
                upiRef={claim.upi_ref}
                createdAt={claim.created_at}
                paidAt={claim.paid_at}
                fraudScore={claim.fraud_score}
                claimId={claim.id}
                validationData={claim.validation_data}
                disruptionCategory={claim.disruption_category}
                disruptionFactor={claim.disruption_factor}
                paymentStatus={claim.payment_status}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
````

--- FILE: frontend/src/pages/Policy.jsx ---
``jsx
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../services/api';

/* â”€â”€â”€ Design tokens matching Register.jsx â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const S = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  :root {
    --green-primary: #3DB85C;
    --green-dark:    #2a9e47;
    --green-light:   #e8f7ed;
    --text-dark:     #1a2e1a;
    --text-mid:      #4a5e4a;
    --text-light:    #8a9e8a;
    --white:         #ffffff;
    --gray-bg:       #f7f9f7;
    --border:        #e2ece2;
    --warning:       #d97706;
    --error:         #dc2626;
  }

  .pol-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-bottom: 32px;
  }

  /* â”€â”€ Page header â”€â”€ */
  .pol-page-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 900;
    font-size: 24px;
    color: var(--text-dark);
  }
  .pol-page-sub { font-size: 13px; color: var(--text-light); margin-top: 2px; }

  /* â”€â”€ Card â”€â”€ */
  .pol-card {
    background: var(--white);
    border-radius: 20px;
    border: 1.5px solid var(--border);
    overflow: hidden;
  }
  .pol-card.ring-active { border-color: var(--green-primary); box-shadow: 0 0 0 3px rgba(61,184,92,0.15); }
  .pol-card.locked { opacity: 0.55; }

  .pol-card-body    { padding: 18px 18px 14px; }
  .pol-card-footer  { padding: 0 18px 16px; }

  /* â”€â”€ Plan card header â”€â”€ */
  .plan-hdr { display: flex; justify-content: space-between; align-items: flex-start; }
  .plan-icon { font-size: 28px; }
  .plan-name { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 20px; margin-top: 4px; text-transform: capitalize; }
  .plan-lock-badge {
    display: inline-block; font-size: 10px; font-weight: 700;
    background: #f3f4f6; color: #6b7280; padding: 3px 9px; border-radius: 10px; margin-top: 4px;
  }
  .plan-price-big { font-family: 'Nunito', sans-serif; font-size: 28px; font-weight: 900; color: var(--text-dark); }
  .plan-price-sub { font-size: 12px; color: var(--text-light); text-align: right; }
  .plan-zone-adj  { font-size: 11px; text-align: right; margin-top: 2px; }

  .plan-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }
  .plan-stat { background: var(--gray-bg); border-radius: 12px; padding: 10px 12px; }
  .plan-stat-label { font-size: 11px; color: var(--text-light); }
  .plan-stat-val   { font-family: 'Nunito', sans-serif; font-size: 16px; font-weight: 800; color: var(--text-dark); margin-top: 2px; }

  .plan-ineligible-note {
    margin-top: 12px;
    background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px;
    padding: 8px 12px; font-size: 12px; color: #92400e;
  }

  /* â”€â”€ Plan CTA button â”€â”€ */
  .plan-btn {
    width: 100%; padding: 14px; border-radius: 14px;
    font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px;
    border: none; cursor: pointer; transition: background 0.2s, opacity 0.2s;
  }
  .plan-btn.primary { background: var(--green-primary); color: white; }
  .plan-btn.primary:hover { background: var(--green-dark); }
  .plan-btn.secondary { background: var(--gray-bg); color: var(--text-light); cursor: not-allowed; }
  .plan-btn.outline { background: transparent; border: 1.5px solid var(--border); color: var(--text-mid); cursor: not-allowed; }

  /* â”€â”€ Active policy banner â”€â”€ */
  .active-pol-banner {
    border-radius: 18px;
    padding: 16px 18px;
    border: 1.5px solid;
    margin-bottom: 16px;
  }
  .active-pol-banner.st-active        { background: #f0fdf4; border-color: #bbf7d0; }
  .active-pol-banner.st-grace_period  { background: #fffbeb; border-color: #fde68a; }
  .active-pol-banner.st-lapsed        { background: #fef2f2; border-color: #fecaca; }
  .active-pol-banner.st-cancelled     { background: #f9fafb; border-color: #e5e7eb; }

  .apb-row { display: flex; justify-content: space-between; align-items: flex-start; }
  .apb-tier { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; text-transform: uppercase; }
  .apb-badge { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px; }
  .apb-badge.st-active        { background: #dcfce7; color: #166534; }
  .apb-badge.st-grace_period  { background: #fef9c3; color: #854d0e; }
  .apb-badge.st-lapsed        { background: #fee2e2; color: #991b1b; }
  .apb-badge.st-cancelled     { background: #f3f4f6; color: #374151; }
  .apb-sub { font-size: 12px; color: var(--text-mid); margin-top: 3px; }
  .apb-next-premium { font-size: 12px; color: var(--text-light); margin-top: 2px; }

  .apb-toggle-row { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
  .rc-toggle {
    position: relative; display: inline-block; width: 44px; height: 24px;
  }
  .rc-toggle input { opacity: 0; width: 0; height: 0; }
  .rc-toggle-slider {
    position: absolute; cursor: pointer; inset: 0; border-radius: 24px;
    background: #d1d5db; transition: background 0.25s;
  }
  .rc-toggle-slider:before {
    content: ''; position: absolute; height: 18px; width: 18px;
    left: 3px; bottom: 3px; background: white; border-radius: 50%;
    transition: transform 0.25s;
  }
  .rc-toggle input:checked + .rc-toggle-slider { background: var(--green-primary); }
  .rc-toggle input:checked + .rc-toggle-slider:before { transform: translateX(20px); }
  .apb-toggle-label { font-size: 13px; color: var(--text-mid); }

  .apb-actions { display: flex; gap: 8px; margin-top: 12px; }
  .apb-action-btn {
    flex: 1; padding: 9px; border-radius: 12px; font-size: 12px; font-weight: 700;
    font-family: 'DM Sans', sans-serif; cursor: pointer; transition: opacity 0.2s;
    border: 1.5px solid var(--border); background: var(--white); color: var(--text-dark);
  }
  .apb-action-btn.danger { color: var(--error); border-color: #fecaca; }
  .apb-action-btn.primary { background: var(--green-primary); color: white; border-color: var(--green-primary); }

  /* â”€â”€ Eligibility gate â”€â”€ */
  .eligib-gate {
    border-radius: 14px; padding: 14px 16px;
    border: 1.5px solid #fde68a; background: #fffbeb;
    margin-bottom: 16px;
  }
  .eligib-gate.pass { border-color: #bbf7d0; background: #f0fdf4; }
  .eligib-gate-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 14px; }
  .eligib-gate.fail  .eligib-gate-title { color: #92400e; }
  .eligib-gate.pass  .eligib-gate-title { color: #166534; }
  .eligib-gate-sub { font-size: 12px; margin-top: 4px; }
  .eligib-gate.fail .eligib-gate-sub { color: #b45309; }
  .eligib-gate.pass .eligib-gate-sub { color: #15803d; }

  /* â”€â”€ Exclusions modal â”€â”€ */
  .excl-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.55);
    display: flex; align-items: flex-end; justify-content: center; z-index: 100;
  }
  .excl-sheet {
    background: var(--white); width: 100%; max-width: 480px;
    border-radius: 24px 24px 0 0; max-height: 90vh;
    display: flex; flex-direction: column;
  }
  .excl-header { padding: 20px 20px 14px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .excl-title  { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 20px; color: var(--text-dark); }
  .excl-sub    { font-size: 13px; color: var(--text-mid); margin-top: 3px; }
  .excl-list   { overflow-y: auto; flex: 1; padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; }
  .excl-item   { display: flex; gap: 12px; padding: 12px 14px; background: var(--gray-bg); border: 1px solid var(--border); border-radius: 14px; }
  .excl-item-title { font-size: 13px; font-weight: 700; color: var(--text-dark); }
  .excl-item-desc  { font-size: 11.5px; color: var(--text-mid); margin-top: 2px; }
  .excl-footer { padding: 14px 20px 24px; border-top: 1px solid var(--border); flex-shrink: 0; }
  .excl-check-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 14px; cursor: pointer; }
  .excl-check { width: 18px; height: 18px; flex-shrink: 0; accent-color: var(--green-primary); margin-top: 2px; }
  .excl-check-label { font-size: 13px; color: var(--text-dark); }
  .excl-cta {
    width: 100%; padding: 15px; background: var(--green-primary); color: white;
    border: none; border-radius: 14px; font-family: 'Nunito', sans-serif; font-weight: 900;
    font-size: 15px; cursor: pointer; transition: background 0.2s;
  }
  .excl-cta:disabled { background: var(--border); color: var(--text-light); cursor: not-allowed; }
  .excl-cta:not(:disabled):hover { background: var(--green-dark); }
  .excl-view-link {
    width: 100%; text-align: center; font-size: 13px; color: var(--text-mid);
    background: none; border: none; cursor: pointer; padding: 8px;
    font-family: 'DM Sans', sans-serif; text-decoration: underline; margin-top: 16px;
  }

  /* â”€â”€ Premium breakdown (renewal modal) â”€â”€ */
  .breakdown-modal-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 13px; }
  .breakdown-modal-key { color: var(--text-mid); }
  .breakdown-modal-val { font-weight: 600; color: var(--text-dark); }
  .breakdown-modal-val.neg { color: var(--green-dark); }
  .breakdown-modal-total {
    border-top: 1.5px solid var(--border); margin-top: 6px; padding-top: 10px;
    display: flex; justify-content: space-between;
    font-family: 'Nunito', sans-serif; font-weight: 900;
    font-size: 15px; color: var(--text-dark);
  }
  .breakdown-modal-total .val { color: var(--green-dark); text-align: right; }

  /* â”€â”€ Renewal modal â”€â”€ */
  .renew-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.55);
    display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px;
  }
  .renew-modal {
    background: var(--white); border-radius: 24px; max-width: 400px; width: 100%;
    padding: 24px; max-height: 90vh; overflow-y: auto;
  }
  .renew-title { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 20px; color: var(--text-dark); margin-bottom: 16px; }
  .tier-chips { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin-bottom: 16px; }
  .tier-chip {
    padding: 10px 8px; border-radius: 12px; border: 1.5px solid var(--border);
    text-align: center; cursor: pointer; transition: all 0.2s; background: var(--white);
  }
  .tier-chip.selected { border-color: var(--green-primary); background: var(--green-light); }
  .tier-chip.disabled { opacity: 0.4; cursor: not-allowed; }
  .tier-chip-name  { font-size: 13px; font-weight: 700; text-transform: capitalize; margin-top: 2px; }
  .tier-chip-price { font-size: 11px; color: var(--text-light); }
  .renew-actions { display: flex; gap: 10px; margin-top: 16px; }
  .renew-cancel {
    flex: 1; padding: 13px; border-radius: 14px; border: 1.5px solid var(--border);
    background: transparent; color: var(--text-mid); font-family: 'Nunito', sans-serif;
    font-weight: 700; font-size: 14px; cursor: pointer;
  }
  .renew-confirm {
    flex: 2; padding: 13px; border-radius: 14px; border: none;
    background: var(--green-primary); color: white; font-family: 'Nunito', sans-serif;
    font-weight: 800; font-size: 14px; cursor: pointer;
  }
  .renew-confirm:disabled { background: var(--border); cursor: not-allowed; }

  /* â”€â”€ Info box â”€â”€ */
  .info-box { background: var(--gray-bg); border-radius: 16px; padding: 16px 18px; margin-top: 16px; }
  .info-box-title { font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 14px; margin-bottom: 10px; }
  .info-box li { font-size: 12.5px; color: var(--text-mid); margin-bottom: 6px; list-style: disc; margin-left: 16px; }
`;

/* â”€â”€â”€ Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const EXCLUSIONS = [
  { icon: 'âš”ï¸', title: 'War and armed conflict', desc: 'Losses arising from war, invasion, or armed hostilities.' },
  { icon: 'ðŸ¦ ', title: 'Pandemic / epidemic declaration', desc: 'Disruptions due to a government-declared pandemic or epidemic.' },
  { icon: 'â˜¢ï¸', title: 'Nuclear and radioactive events', desc: 'Any loss caused by nuclear, radioactive, or radiation hazard.' },
  { icon: 'ðŸ›ï¸', title: 'Government policy or regulatory changes', desc: 'Policy changes, bans, or regulatory decisions by any authority.' },
  { icon: 'âš™ï¸', title: 'Platform operational decisions', desc: 'Planned maintenance, algorithm changes, or app updates by Zepto.' },
  { icon: 'ðŸ™‹', title: 'Self-inflicted / voluntary offline', desc: 'Choosing to go offline or voluntarily skipping shifts.' },
  { icon: 'ðŸ¥', title: 'Health, accident, life', desc: 'Personal health events, accidents, or life insurance claims.' },
  { icon: 'ðŸ”§', title: 'Vehicle damage and repair', desc: 'Downtime due to vehicle breakdown, servicing, or repair.' },
  { icon: 'â±ï¸', title: 'Disruptions under 45 minutes', desc: 'Any disruption lasting less than 45 minutes is not covered.' },
  { icon: 'ðŸ—“ï¸', title: 'Claims after 48-hour window', desc: 'Claims must be submitted within 48 hours of the disruption.' },
];

const TIER_META = {
  flex: { icon: 'âš¡', label: 'Flex', subtitle: 'Part-time Â· 4â€“5 hrs/day' },
  standard: { icon: 'ðŸ›µ', label: 'Standard', subtitle: 'Full-time Â· 8â€“10 hrs/day' },
  pro: { icon: 'ðŸ†', label: 'Pro', subtitle: 'Peak warrior Â· 12+ hrs/day' }
};

const TIER_LIMITS = {
  flex: { max_payout_day: 250, max_days_week: 2, weekly_premium: 22 },
  standard: { max_payout_day: 400, max_days_week: 3, weekly_premium: 33 },
  pro: { max_payout_day: 500, max_days_week: 4, weekly_premium: 45 },
};

/* â”€â”€â”€ ExclusionsScreen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function ExclusionsScreen({ onAccept }) {
  const [checked, setChecked] = useState(false);
  return (
    <div className="excl-overlay">
      <div className="excl-sheet">
        <div className="excl-header">
          <p className="excl-title">âš ï¸ What's Not Covered</p>
          <p className="excl-sub">Read all 10 exclusions before your first premium is collected.</p>
        </div>
        <div className="excl-list">
          {EXCLUSIONS.map((ex, i) => (
            <div className="excl-item" key={i}>
              <span style={{ fontSize: 22, flexShrink: 0, marginTop: 2 }}>{ex.icon}</span>
              <div>
                <p className="excl-item-title">{ex.title}</p>
                <p className="excl-item-desc">{ex.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="excl-footer">
          <label className="excl-check-row">
            <input className="excl-check" type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} />
            <span className="excl-check-label">I have read and understood all 10 exclusions listed above.</span>
          </label>
          <button className="excl-cta" disabled={!checked} onClick={onAccept}>
            I Understand â€” Continue to Plans
          </button>
        </div>
      </div>
    </div>
  );
}

/* â”€â”€â”€ PremiumBreakdown â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function PremiumBreakdown({ breakdown }) {
  if (!breakdown) return null;

  return (
    <div style={{ background: '#eff6ff', borderRadius: 14, padding: 14, border: '1px solid #bfdbfe', marginTop: 12 }}>
      <p style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 800, fontSize: 12, color: '#1e40af', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
        Premium Breakdown (Next Week)
      </p>
      
      <div className="breakdown-modal-row">
        <span className="breakdown-modal-key">Base Premium</span>
        <span className="breakdown-modal-val">â‚¹{breakdown.base_premium}</span>
      </div>
      
      {breakdown.activity_multiplier !== 1.0 && (
        <div className="breakdown-modal-row">
          <span className="breakdown-modal-key">Activity Tier</span>
          <span className="breakdown-modal-val text-blue-600">Ã—{breakdown.activity_multiplier}</span>
        </div>
      )}
      {breakdown.zone_risk_adjustment !== 0 && (
        <div className="breakdown-modal-row">
          <span className="breakdown-modal-key">Zone Factor</span>
          <span className="breakdown-modal-val text-red-600">+{breakdown.zone_risk_adjustment}</span>
        </div>
      )}
      {breakdown.loyalty_discount !== 0 && (
        <div className="breakdown-modal-row">
          <span className="breakdown-modal-key">Loyalty Discount</span>
          <span className="breakdown-modal-val text-green-600">-{breakdown.loyalty_discount}</span>
        </div>
      )}

      <div className="breakdown-modal-total">
        <span>Total</span>
        <span className="val">â‚¹{breakdown.total}/week</span>
      </div>
    </div>
  );
}

/* â”€â”€â”€ Main Policy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export default function Policy() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [activePolicy, setActivePolicy] = useState(null);
  const [eligibility, setEligibility] = useState(null);
  const [breakdown, setBreakdown] = useState(null);
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [showRenewalModal, setShowRenewalModal] = useState(false);
  const [renewalQuote, setRenewalQuote] = useState(null);
  const [selectedRenewalTier, setSelectedRenewalTier] = useState(null);
  const [renewalLoading, setRenewalLoading] = useState(false);
  const [downloadingCert, setDownloadingCert] = useState(false);
  const [togglingAutoRenew, setTogglingAutoRenew] = useState(false);
  const [showExclusions, setShowExclusions] = useState(false);
  const [exclusionsAccepted, setExclusionsAccepted] = useState(false);
  const [pendingTier, setPendingTier] = useState(null);
  const [error, setError] = useState(null);
  const [paymentStatus, setPaymentStatus] = useState(null);

  // Handle Stripe redirect (payment success/cancel)
  useEffect(() => {
    const payment = searchParams.get('payment');
    const sessionId = searchParams.get('session_id');

    if (payment === 'success' && sessionId) {
      setPaymentStatus('confirming');
      api.confirmPayment(sessionId)
        .then(() => {
          setPaymentStatus('success');
          // Clear URL params
          setSearchParams({});
          // Reload policy data
          load();
        })
        .catch((err) => {
          setPaymentStatus('error');
          setError(err.message);
        });
    } else if (payment === 'cancelled') {
      setPaymentStatus('cancelled');
      setSearchParams({});
    }
  }, [searchParams]);

  useEffect(() => { load(); }, []);

  async function load() {
    try {
      const [pd, elig, breakd, qd] = await Promise.all([
        api.getActivePolicy().catch(() => null),
        api.getPartnerEligibility().catch(() => null),
        api.getPremiumBreakdown().catch(() => null),
        api.getPolicyQuotes().catch(() => [])
      ]);
      setActivePolicy(pd);
      setEligibility(elig);
      setBreakdown(breakd);
      setQuotes(Array.isArray(qd) ? qd : []);
    } catch (e) {
      console.error(e);
      setError(e.message);
    } finally { 
      setLoading(false); 
    }
  }

  function initiatePurchase(tier) {
    if (!exclusionsAccepted) { setPendingTier(tier); setShowExclusions(true); }
    else handlePurchase(tier);
  }

  function onExclusionsAccept() {
    setExclusionsAccepted(true); setShowExclusions(false);
    if (pendingTier) { handlePurchase(pendingTier); setPendingTier(null); }
  }

  async function handlePurchase(tier) {
    setPurchasing(tier);
    try {
      // Create Stripe checkout session and redirect
      const { checkout_url } = await api.createCheckoutSession(tier, false);
      window.location.href = checkout_url;
    }
    catch (e) {
      alert(e.message);
      setPurchasing(null);
    }
    // Don't reset purchasing state - page will redirect to Stripe
  }

  async function handleCancel() {
    if (!window.confirm('Are you sure you want to cancel your policy?')) return;
    setCancelling(true);
    try { await api.cancelPolicy(activePolicy.id); await load(); }
    catch (e) { alert(e.message); }
    finally { setCancelling(false); }
  }

  async function openRenewalModal() {
    setShowRenewalModal(true);
    setSelectedRenewalTier(activePolicy?.tier);
    setRenewalLoading(true);
    try {
      const q = await api.getRenewalQuote(activePolicy.id, activePolicy.tier);
      setRenewalQuote(q);
    } catch (e) { alert(e.message); setShowRenewalModal(false); }
    finally { setRenewalLoading(false); }
  }

  async function handleTierChange(tier) {
    setSelectedRenewalTier(tier); 
    setRenewalLoading(true);
    try {
      const q = await api.getRenewalQuote(activePolicy.id, tier);
      setRenewalQuote(q);
    } catch (e) { console.error(e); }
    finally { setRenewalLoading(false); }
  }

  async function handleRenew() {
    setRenewalLoading(true);
    try {
      await api.renewPolicy(activePolicy.id, selectedRenewalTier !== activePolicy.tier ? selectedRenewalTier : null, activePolicy.auto_renew);
      setShowRenewalModal(false); setRenewalQuote(null); await load();
    } catch (e) { alert(e.message); }
    finally { setRenewalLoading(false); }
  }

  async function handleToggleAutoRenew() {
    setTogglingAutoRenew(true);
    try { 
      // Toggle auto_renew via patch
      await api.updateAutoRenew(activePolicy.id, !activePolicy.auto_renew);
      await load(); 
    }
    catch (e) { alert(e.message); }
    finally { setTogglingAutoRenew(false); }
  }

  async function handleDownloadCert() {
    setDownloadingCert(true);
    try {
      const blob = await api.downloadCertificate(activePolicy.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `policy_certificate_${activePolicy.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch(e) { alert(e.message); }
    finally { setDownloadingCert(false); }
  }

  function countdown() {
    if (!activePolicy) return null;
    if (activePolicy.status === 'active' && activePolicy.days_until_expiry != null) {
      const d = activePolicy.days_until_expiry;
      if (d === 0) return 'Expires today';
      if (d === 1) return 'Expires tomorrow';
      return `Expires in ${d} days`;
    }
    if (activePolicy.status === 'grace_period' && activePolicy.hours_until_grace_ends != null) {
      const h = Math.floor(activePolicy.hours_until_grace_ends);
      return h < 1 ? 'Grace period ending soon' : `Grace period: ${h}h left`;
    }
    return null;
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--gray-bg)' }}>
      <div style={{ width: 32, height: 32, border: '3px solid var(--green-light)', borderTopColor: 'var(--green-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
    </div>
  );

  const polSt = activePolicy?.status || 'active';
  const ST_LABELS = { active: 'Active', grace_period: 'Grace Period', lapsed: 'Lapsed', cancelled: 'Cancelled' };
  const cd = countdown();
  const currentTier = activePolicy?.tier || null;
  const gateBlocked = eligibility?.gate_blocked ?? false;

  return (
    <>
      <style>{S}</style>
      <div className="pol-wrap" style={{ padding: '24px 16px', background: 'var(--gray-bg)', minHeight: '100vh' }}>

        {/* Exclusions modal */}
        {showExclusions && <ExclusionsScreen onAccept={onExclusionsAccept} />}

        {/* Header */}
        <div style={{ marginBottom: 16 }}>
          <h1 className="pol-page-title">Insurance Plans</h1>
          <p className="pol-page-sub">Choose coverage that fits your activity level</p>
        </div>

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '12px', borderRadius: '12px', color: '#991b1b', fontSize: 13, marginBottom: 16 }}>
            {error}
          </div>
        )}

        {/* Payment status banner */}
        {paymentStatus === 'confirming' && (
          <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', padding: '16px', borderRadius: '12px', color: '#1e40af', fontSize: 14, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 20, height: 20, border: '2px solid #bfdbfe', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            Confirming your payment...
          </div>
        )}
        {paymentStatus === 'success' && (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '16px', borderRadius: '12px', color: '#166534', fontSize: 14, marginBottom: 16 }}>
            âœ… Payment successful! Your policy is now active.
          </div>
        )}
        {paymentStatus === 'cancelled' && (
          <div style={{ background: '#fffbeb', border: '1px solid #fde68a', padding: '16px', borderRadius: '12px', color: '#92400e', fontSize: 14, marginBottom: 16 }}>
            Payment was cancelled. You can try again below.
          </div>
        )}

        {/* Demo mode notice */}
        <div style={{ background: '#faf5ff', border: '1px solid #e9d5ff', padding: '10px 14px', borderRadius: '10px', color: '#6b21a8', fontSize: 12, marginBottom: 16 }}>
          ðŸ§ª <strong>Demo Mode:</strong> Stripe test mode - no real money charged. Use card <code style={{ background: '#ede9fe', padding: '2px 6px', borderRadius: 4 }}>4242 4242 4242 4242</code>
        </div>

        {/* Eligibility gate */}
        {gateBlocked && (
          <div className="eligib-gate fail">
            <p className="eligib-gate-title">
              â³ Cover starts after 7 active delivery days
            </p>
            <p className="eligib-gate-sub">
              You have <strong>{eligibility?.active_days_last_30 ?? 0}</strong> active days.
              Complete 7 days to unlock coverage.
            </p>
          </div>
        )}

        {/* Active policy banner */}
        {activePolicy && (
          <div className={`active-pol-banner st-${polSt}`}>
            <div className="apb-row">
              <div>
                <p className="apb-tier">{activePolicy.tier.toUpperCase()} Plan</p>
                <p className="apb-sub">{cd || `Expires ${new Date(activePolicy.expires_at).toLocaleDateString('en-IN')}`}</p>
                <p className="apb-next-premium">Next premium: â‚¹{breakdown?.total ?? TIER_LIMITS[activePolicy.tier].weekly_premium}/week</p>
              </div>
              <span className={`apb-badge st-${polSt}`}>{ST_LABELS[polSt]}</span>
            </div>
            {activePolicy.can_renew && (
              <div className="apb-toggle-row">
                <label className="rc-toggle">
                  <input type="checkbox" checked={!!activePolicy.auto_renew} onChange={handleToggleAutoRenew} disabled={togglingAutoRenew} />
                  <span className="rc-toggle-slider" />
                </label>
                <span className="apb-toggle-label">Auto-renewal</span>
              </div>
            )}
            <div className="apb-actions">
              {activePolicy.can_renew && (
                <button className="apb-action-btn primary" onClick={openRenewalModal}>Renew</button>
              )}
              <button className="apb-action-btn" onClick={handleDownloadCert} disabled={downloadingCert}>
                {downloadingCert ? 'Downloadingâ€¦' : 'Certificate'}
              </button>
              {(polSt === 'active' || polSt === 'grace_period') && (
                <button className="apb-action-btn danger" onClick={handleCancel} disabled={cancelling}>
                  {cancelling ? 'Wait...' : 'Cancel'}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Plan cards */}
        {['flex', 'standard', 'pro'].map(tier => {
          const isCurrent = currentTier === tier;
          const isAllowed = eligibility?.allowed_tiers?.includes(tier) ?? true;
          const isBlocked = eligibility?.blocked_tiers?.includes(tier) ?? gateBlocked;
          const meta = TIER_META[tier];
          const limits = TIER_LIMITS[tier];
          const displayPremium = isCurrent && breakdown?.total ? breakdown.total : limits.weekly_premium;
          const reason = eligibility?.reasons?.[tier];

          return (
            <div key={tier} className={`pol-card ${isCurrent ? 'ring-active' : ''} ${isBlocked ? 'locked' : ''}`} style={{ marginBottom: 12 }}>
              <div className="pol-card-body">
                <div className="plan-hdr">
                  <div>
                    <span className="plan-icon">{meta.icon}</span>
                    <p className="plan-name">{meta.label}</p>
                    {isBlocked && <span className="plan-lock-badge">ðŸ”’ Locked</span>}
                    {isCurrent && <span className="plan-lock-badge" style={{background: 'var(--green-primary)', color:'white'}}>âœ… Current</span>}
                  </div>
                  <div>
                    <p className="plan-price-big">â‚¹{displayPremium}</p>
                    <p className="plan-price-sub">/week</p>
                  </div>
                </div>

                {isBlocked && reason && !gateBlocked && (
                  <div className="plan-ineligible-note">â„¹ï¸ {reason}</div>
                )}

                <div className="plan-stats">
                  <div className="plan-stat">
                    <p className="plan-stat-label">Daily Payout</p>
                    <p className="plan-stat-val">â‚¹{limits.max_payout_day}</p>
                  </div>
                  <div className="plan-stat">
                    <p className="plan-stat-label">Max Days/Week</p>
                    <p className="plan-stat-val">{limits.max_days_week}</p>
                  </div>
                </div>
              </div>
              <div className="pol-card-footer">
                <button
                  className={`plan-btn ${isCurrent || isBlocked || activePolicy ? 'secondary' : 'primary'}`}
                  disabled={!!activePolicy || isBlocked || purchasing === tier}
                  onClick={() => initiatePurchase(tier)}
                >
                  {purchasing === tier ? 'Processingâ€¦' : 
                   isCurrent ? 'Current Plan' : 
                   activePolicy ? 'Already Covered' : 
                   isBlocked ? 'Not Eligible' : 'Get This Plan'}
                </button>
              </div>
            </div>
          );
        })}

        <button className="excl-view-link" onClick={() => setShowExclusions(true)}>
          âš ï¸ View all 10 policy exclusions
        </button>

        <div className="info-box">
          <p className="info-box-title">How it works:</p>
          <ul>
            <li>Pay weekly premium via UPI</li>
            <li>Automatic payout when trigger events occur</li>
            <li>No claim forms â€” events detected automatically</li>
            <li>Money credited to your UPI within minutes</li>
            <li>48-hour grace period after expiry for renewal</li>
          </ul>
        </div>

        {/* Renewal modal */}
        {showRenewalModal && (
          <div className="renew-overlay">
            <div className="renew-modal">
              <p className="renew-title">Renew Your Policy</p>
              <p style={{ fontSize: 12, color: 'var(--text-light)', marginBottom: 12 }}>Select Plan</p>
              
              <div className="tier-chips">
                {['flex', 'standard', 'pro'].map(tier => {
                  const el = eligibility?.allowed_tiers?.includes(tier) ?? true;
                  return (
                    <div
                      key={tier}
                      className={`tier-chip ${selectedRenewalTier === tier ? 'selected' : ''} ${!el ? 'disabled' : ''}`}
                      onClick={() => el && handleTierChange(tier)}
                    >
                      <div style={{ fontSize: 20 }}>{TIER_META[tier].icon}</div>
                      <p className="tier-chip-name">{tier}</p>
                      <p className="tier-chip-price">â‚¹{TIER_LIMITS[tier].weekly_premium}</p>
                    </div>
                  );
                })}
              </div>

              {renewalLoading ? (
                <div style={{ textAlign: 'center', padding: 24 }}>
                  <div style={{ width: 28, height: 28, border: '3px solid var(--green-light)', borderTopColor: 'var(--green-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto' }} />
                </div>
              ) : renewalQuote ? (
                <PremiumBreakdown breakdown={{
                  base_premium: renewalQuote.base_premium,
                  activity_multiplier: renewalQuote.activity_multiplier || 1,
                  zone_risk_adjustment: renewalQuote.zone_risk_adjustment || 0,
                  loyalty_discount: renewalQuote.loyalty_discount_applied || 0,
                  total: renewalQuote.final_premium
                }} />
              ) : null}

              <div className="renew-actions">
                <button className="renew-cancel" onClick={() => { setShowRenewalModal(false); setRenewalQuote(null); }}>Cancel</button>
                <button className="renew-confirm" onClick={handleRenew} disabled={renewalLoading || !renewalQuote}>
                  {renewalLoading ? 'Processingâ€¦' : 'Confirm Renewal'}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </>
  );
}
````

--- FILE: frontend/src/pages/Profile.jsx ---
``jsx
/**
 * Profile.jsx  â€“  Partner profile, zone history, renewal preview
 *
 * Person 1 Phase 2:
 *   - Removed MOCK_ZONE_HISTORY constant
 *   - Removed hardcoded renewal premium breakdown
 *   - Zone history from GET /partners/me/zone-history
 *   - Renewal preview from GET /partners/me/renewal-preview
 *   - Empty state shown when no zone history exists
 *   - "Zone #id" chip replaced with actual zone name/code/city when available
 *
 * UI: Original green theme restored (matching Login.jsx / Register.jsx).
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { NotificationToggle } from '../components/NotificationToggle';
import { UpiSelector } from '../components/ui/UpiSelector';
import RapidBot from '../components/RapidBot';
import PrivacyConsentPanel from '../components/PrivacyConsentPanel';
import HelpSupportPanel from '../components/HelpSupportPanel';
import api from '../services/api';

/* â”€â”€â”€ Design tokens matching Register.jsx â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const S = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

  :root {
    --green-primary: #3DB85C;
    --green-dark:    #2a9e47;
    --green-light:   #e8f7ed;
    --text-dark:     #1a2e1a;
    --text-mid:      #4a5e4a;
    --text-light:    #8a9e8a;
    --white:         #ffffff;
    --gray-bg:       #f7f9f7;
    --border:        #e2ece2;
    --warning:       #d97706;
    --error:         #dc2626;
  }

  .prf-wrap {
    font-family: 'DM Sans', sans-serif;
    color: var(--text-dark);
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-bottom: 40px;
  }

  /* â”€â”€ Shared card â”€â”€ */
  .prf-card {
    background: var(--white);
    border-radius: 20px;
    border: 1.5px solid var(--border);
    overflow: hidden;
  }
  .prf-card-body { padding: 18px; }

  /* â”€â”€ Section title â”€â”€ */
  .prf-section-title {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 14px;
    color: var(--text-dark);
    margin-bottom: 4px;
  }
  .prf-section-sub { font-size: 11.5px; color: var(--text-light); margin-bottom: 12px; }

  /* â”€â”€ Avatar hero â”€â”€ */
  .prf-hero {
    background: linear-gradient(135deg, var(--green-primary), var(--green-dark));
    border-radius: 20px;
    padding: 24px 18px;
    display: flex;
    align-items: center;
    gap: 16px;
    color: white;
  }
  .prf-avatar {
    width: 60px; height: 60px; border-radius: 50%;
    background: rgba(255,255,255,0.25);
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; flex-shrink: 0;
    border: 2px solid rgba(255,255,255,0.4);
  }
  .prf-hero-name   { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 18px; }
  .prf-hero-phone  { font-size: 13px; opacity: 0.8; margin-top: 2px; }
  .prf-hero-plat   { font-size: 11px; opacity: 0.65; margin-top: 1px; text-transform: capitalize; }

  /* â”€â”€ Inline input â”€â”€ */
  .prf-input {
    width: 100%;
    padding: 12px 14px;
    border: 1.5px solid var(--border);
    border-radius: 13px;
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    background: var(--gray-bg);
    outline: none;
    color: var(--text-dark);
    transition: border-color 0.2s, box-shadow 0.2s;
    box-sizing: border-box;
  }
  .prf-input:focus {
    border-color: var(--green-primary);
    box-shadow: 0 0 0 3px rgba(61,184,92,0.12);
    background: var(--white);
  }
  .prf-input.valid   { border-color: var(--green-primary); }
  .prf-input.invalid { border-color: var(--warning); }

  .prf-label {
    font-family: 'Nunito', sans-serif;
    font-size: 12.5px; font-weight: 700; color: var(--text-dark);
    display: block; margin-bottom: 6px;
  }
  .prf-hint { font-size: 11.5px; color: var(--text-light); margin-top: 4px; }
  .prf-hint.warn { color: var(--warning); }

  .prf-field { margin-bottom: 14px; }
  .prf-input-wrap { position: relative; }
  .prf-input-icon {
    position: absolute; right: 12px; top: 50%;
    transform: translateY(-50%); font-size: 14px;
  }

  /* â”€â”€ Buttons â”€â”€ */
  .prf-btn-primary {
    background: var(--green-primary); color: white; border: none;
    border-radius: 13px; padding: 13px; width: 100%;
    font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px;
    cursor: pointer; transition: background 0.2s;
  }
  .prf-btn-primary:hover { background: var(--green-dark); }
  .prf-btn-primary:disabled { background: var(--border); cursor: not-allowed; }

  .prf-btn-outline {
    background: transparent; color: var(--text-dark);
    border: 1.5px solid var(--border); border-radius: 13px; padding: 10px 16px;
    font-family: 'DM Sans', sans-serif; font-weight: 600; font-size: 13px;
    cursor: pointer; transition: border-color 0.2s;
  }
  .prf-btn-outline:hover { border-color: var(--green-primary); color: var(--green-dark); }

  .prf-btn-secondary {
    background: var(--gray-bg); color: var(--text-mid); border: 1.5px solid var(--border);
    border-radius: 13px; padding: 11px; font-family: 'DM Sans', sans-serif;
    font-weight: 600; font-size: 14px; cursor: pointer;
  }

  .prf-btn-danger {
    background: transparent; color: var(--error); border: 1.5px solid #fecaca;
    border-radius: 13px; padding: 13px; width: 100%;
    font-family: 'Nunito', sans-serif; font-weight: 800; font-size: 15px;
    cursor: pointer;
  }

  .prf-btn-row { display: flex; gap: 8px; }

  /* â”€â”€ Select â”€â”€ */
  .prf-select {
    width: 100%; padding: 12px 14px; border: 1.5px solid var(--border);
    border-radius: 13px; font-size: 14px; font-family: 'DM Sans', sans-serif;
    background: var(--gray-bg); outline: none; color: var(--text-dark);
    appearance: none; -webkit-appearance: none;
  }

  /* â”€â”€ KYC status badges â”€â”€ */
  .kyc-badge {
    font-size: 12px; font-weight: 700; padding: 4px 12px;
    border-radius: 10px; display: inline-block;
  }
  .kyc-verified  { background: var(--green-light); color: var(--green-dark); }
  .kyc-pending   { background: #fef3c7; color: #92400e; }
  .kyc-failed    { background: #fef2f2; color: var(--error); }
  .kyc-skipped   { background: var(--gray-bg); color: var(--text-light); }

  /* â”€â”€ Zone history â”€â”€ */
  .zh-item {
    border: 1.5px solid var(--border); border-radius: 14px;
    padding: 12px 14px; background: var(--gray-bg); margin-bottom: 10px;
  }
  .zh-item:last-child { margin-bottom: 0; }
  .zh-meta { display: flex; justify-content: space-between; margin-bottom: 6px; }
  .zh-date   { font-size: 12px; font-weight: 700; color: var(--text-dark); }
  .zh-reason { font-size: 11px; color: var(--text-light); }
  .zh-zones  { display: flex; align-items: center; gap: 8px; font-size: 13px; }
  .zh-old    { color: var(--text-mid); }
  .zh-arrow  { color: var(--text-light); }
  .zh-new    { font-weight: 700; color: var(--text-dark); }
  .zh-premium { display: flex; align-items: center; gap: 6px; margin-top: 5px; font-size: 12px; }
  .zh-prem-label { color: var(--text-light); }
  .zh-prem-old   { color: var(--text-mid); }
  .zh-prem-new.up   { color: #f97316; font-weight: 700; }
  .zh-prem-new.down { color: var(--green-dark); font-weight: 700; }

  /* â”€â”€ Renewal breakdown â”€â”€ */
  .ren-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 13px; }
  .ren-key  { color: var(--text-mid); }
  .ren-note { font-size: 10.5px; color: var(--text-light); margin-left: 4px; }
  .ren-val  { font-weight: 600; color: var(--text-dark); }
  .ren-val.neg { color: var(--green-dark); }
  .ren-total {
    border-top: 1.5px solid var(--border); padding-top: 10px; margin-top: 6px;
    display: flex; justify-content: space-between;
    font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 16px;
  }
  .ren-total .val { color: var(--green-dark); }

  /* â”€â”€ Action links â”€â”€ */
  .prf-action-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 11px 0; border-bottom: 1px solid var(--border);
    font-size: 13px; color: var(--text-mid); cursor: pointer;
    background: none; border-left: none; border-right: none; border-top: none;
    width: 100%; text-align: left; font-family: 'DM Sans', sans-serif;
  }
  .prf-action-row:last-child { border-bottom: none; }
  .prf-action-row:hover { color: var(--text-dark); }

  /* â”€â”€ Zone info chip â”€â”€ */
  .zone-chip {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--green-light); color: var(--green-dark);
    font-size: 13px; font-weight: 700; padding: 6px 14px;
    border-radius: 20px; margin-top: 4px;
  }

  /* â”€â”€ File upload area â”€â”€ */
  .prf-file-label {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 14px; border: 1.5px dashed var(--border);
    border-radius: 13px; background: var(--gray-bg);
    cursor: pointer; font-size: 13px; color: var(--text-mid);
    transition: border-color 0.2s;
  }
  .prf-file-label.has-file { border-color: var(--green-primary); background: var(--green-light); color: var(--green-dark); }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* â”€â”€ Legal Modal â”€â”€ */
  .legal-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.4); backdrop-filter: blur(4px);
    z-index: 2000; display: flex; align-items: flex-end;
  }
  .legal-sheet {
    background: white; width: 100%; max-height: 85vh;
    border-radius: 24px 24px 0 0; padding: 24px;
    display: flex; flex-direction: column; gap: 16px;
    animation: slideUp 0.3s ease-out; overflow-y: auto;
  }
  @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
  
  .legal-title { font-family: 'Nunito', sans-serif; font-weight: 900; font-size: 20px; }
  .legal-body  { font-size: 14px; line-height: 1.6; color: var(--text-mid); }
  .legal-section { margin-bottom: 20px; }
  .legal-h3 { font-weight: 700; color: var(--text-dark); margin-bottom: 8px; font-size: 15px; }
  
  .support-card {
    background: var(--green-light); border-radius: 16px; padding: 16px;
    display: flex; align-items: center; gap: 12px; border: 1px solid var(--green-primary);
    text-decoration: none; color: var(--green-dark); font-weight: 700;
  }
  .grok-card {
    background: #1a2e1a; border-radius: 16px; padding: 18px;
    display: flex; align-items: center; gap: 14px; border: 1.5px solid rgba(61, 184, 92, 0.3);
    cursor: pointer; color: #fff; font-weight: 700;
    transition: transform 0.2s, border-color 0.2s;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  }
  .grok-card:active { transform: scale(0.97); }
  .grok-card:hover { border-color: var(--green-primary); }
`;

/* â”€â”€â”€ LANGUAGES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'à¤¹à¤¿à¤¨à¥à¤¦à¥€ (Hindi)' },
  { code: 'ta', label: 'à®¤à®®à®¿à®´à¯ (Tamil)' },
  { code: 'kn', label: 'à²•à²¨à³à²¨à²¡ (Kannada)' },
  { code: 'te', label: 'à°¤à±†à°²à±à°—à± (Telugu)' },
  { code: 'mr', label: 'à¤®à¤°à¤¾à¤ à¥€ (Marathi)' },
  { code: 'bn', label: 'à¦¬à¦¾à¦‚à¦²à¦¾ (Bengali)' },
];

function validateUPI(v) { return /^[\w.\-]{3,}@[\w]{3,}$/.test(v.trim()); }
function validateAadhaar(v) { return /^\d{12}$/.test(v.replace(/\s/g, '')); }
function validatePAN(v) { return /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(v.trim().toUpperCase()); }

/* â”€â”€â”€ UpiSetup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function UpiSetup({ currentUpiId, onSave }) {
  const [editing, setEditing] = useState(false);
  const [upiId, setUpiId] = useState(currentUpiId || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const valid = upiId.trim() ? validateUPI(upiId) : null;

  async function save() {
    if (!valid) { setError('Invalid UPI ID format'); return; }
    setSaving(true); setError('');
    try {
      await api.updateProfile({ upi_id: upiId.trim() });
      onSave?.(upiId.trim()); setEditing(false);
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  }

  if (!editing) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <div>
        {currentUpiId
          ? <><p style={{ fontWeight: 700, fontSize: 14 }}>{currentUpiId}</p><p style={{ fontSize: 12, color: 'var(--green-primary)', marginTop: 2 }}>âœ“ UPI linked</p></>
          : <p style={{ fontSize: 13, color: 'var(--text-light)', fontStyle: 'italic' }}>No UPI ID linked yet</p>
        }
      </div>
      <button className="prf-btn-outline" onClick={() => setEditing(true)}>{currentUpiId ? 'Change' : 'Add UPI'}</button>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <UpiSelector 
        value={upiId}
        onChange={v => { setUpiId(v); setError(''); }}
      />
      {error && <p style={{ fontSize: 12, color: 'var(--error)', background: '#fef2f2', padding: '6px 10px', borderRadius: 8 }}>{error}</p>}
      <div className="prf-btn-row">
        <button className="prf-btn-secondary" style={{ flex: 1 }} onClick={() => { setEditing(false); setUpiId(currentUpiId || ''); setError(''); }}>Cancel</button>
        <button className="prf-btn-primary" style={{ flex: 2 }} onClick={save} disabled={!valid || saving}>
          {saving ? 'Savingâ€¦' : 'Save UPI'}
        </button>
      </div>
    </div>
  );
}

/* â”€â”€â”€ KycSetup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function KycSetup({ currentKyc, onSave }) {
  const [editing, setEditing] = useState(false);
  const [aadhaar, setAadhaar] = useState(currentKyc?.aadhaar_number || '');
  const [pan, setPan] = useState(currentKyc?.pan_number || '');
  const [aadhaarFile, setAadhaarFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const av = aadhaar.trim() ? validateAadhaar(aadhaar) : null;
  const pv = pan.trim() ? validatePAN(pan) : null;

  const st = currentKyc?.kyc_status || 'skipped';
  const ST_MAP = {
    verified: { label: 'âœ“ KYC Verified', cls: 'kyc-verified' },
    pending:  { label: 'â³ KYC Pending Review', cls: 'kyc-pending' },
    failed:   { label: 'âœ— KYC Failed', cls: 'kyc-failed' },
    skipped:  { label: 'KYC not submitted', cls: 'kyc-skipped' },
  };
  const badge = ST_MAP[st] || ST_MAP.skipped;

  async function save() {
    if (aadhaar && !validateAadhaar(aadhaar)) { setError('Aadhaar must be 12 digits'); return; }
    if (pan && !validatePAN(pan)) { setError('Invalid PAN format (e.g. ABCDE1234F)'); return; }
    setSaving(true); setError('');
    try {
      await api.updateProfile({
        kyc: {
          aadhaar_number: aadhaar.replace(/\s/g, '') || null,
          pan_number: pan.toUpperCase() || null,
          kyc_status: aadhaar ? 'pending' : 'skipped',
        }
      });
      onSave?.({ aadhaar_number: aadhaar, pan_number: pan, kyc_status: aadhaar ? 'pending' : 'skipped' });
      setEditing(false);
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  }

  if (!editing) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className={`kyc-badge ${badge.cls}`}>{badge.label}</span>
        <button className="prf-btn-outline" onClick={() => setEditing(true)}>
          {st === 'skipped' ? 'Add KYC' : 'Update'}
        </button>
      </div>
      {currentKyc?.aadhaar_number && <p style={{ fontSize: 13, color: 'var(--text-mid)' }}>Aadhaar: â€¢â€¢â€¢â€¢  â€¢â€¢â€¢â€¢  {currentKyc.aadhaar_number.slice(-4)}</p>}
      {currentKyc?.pan_number && <p style={{ fontSize: 13, color: 'var(--text-mid)' }}>PAN: {currentKyc.pan_number}</p>}
      <p style={{ fontSize: 11, color: 'var(--text-light)' }}>ðŸ”’ Mock KYC â€” no real data stored</p>
    </div>
  );

  const inp = (v) => ({ className: `prf-input${v === true ? ' valid' : v === false ? ' invalid' : ''}` });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p style={{ fontSize: 12, background: '#fff8e1', border: '1px solid #fde68a', borderRadius: 8, padding: '6px 10px', color: '#92400e' }}>
        ðŸ”’ Mock KYC â€” fields are for demo only
      </p>
      <div className="prf-field">
        <label className="prf-label">Aadhaar Number <span style={{ fontWeight: 400, color: 'var(--text-light)' }}>(optional)</span></label>
        <div className="prf-input-wrap">
          <input {...inp(av)} placeholder="1234 5678 9012" maxLength={14} value={aadhaar} onChange={e => { setAadhaar(e.target.value); setError(''); }} />
          {av !== null && <span className="prf-input-icon" style={{ color: av ? 'var(--green-primary)' : 'var(--warning)' }}>{av ? 'âœ“' : 'âœ—'}</span>}
        </div>
        <p className={`prf-hint${av === false ? ' warn' : ''}`}>{av === false ? 'Must be 12 digits' : '12-digit Aadhaar number'}</p>
      </div>
      <div className="prf-field">
        <label className="prf-label">PAN Number <span style={{ fontWeight: 400, color: 'var(--text-light)' }}>(optional)</span></label>
        <div className="prf-input-wrap">
          <input {...inp(pv)} placeholder="ABCDE1234F" maxLength={10} value={pan} onChange={e => { setPan(e.target.value.toUpperCase()); setError(''); }} />
          {pv !== null && <span className="prf-input-icon" style={{ color: pv ? 'var(--green-primary)' : 'var(--warning)' }}>{pv ? 'âœ“' : 'âœ—'}</span>}
        </div>
        <p className={`prf-hint${pv === false ? ' warn' : ''}`}>{pv === false ? 'Format: ABCDE1234F' : 'e.g. ABCDE1234F'}</p>
      </div>
      <div className="prf-field">
        <label className="prf-label">Upload Aadhaar <span style={{ fontWeight: 400, color: 'var(--text-light)' }}>(optional)</span></label>
        <label htmlFor="prf-aadhaar-file" className={`prf-file-label${aadhaarFile ? ' has-file' : ''}`}>
          <span>{aadhaarFile ? 'âœ…' : 'ðŸ“Ž'}</span>
          <span>{aadhaarFile ? aadhaarFile.name : 'Tap to upload Aadhaar (image/PDF)'}</span>
        </label>
        <input id="prf-aadhaar-file" type="file" accept="image/*,.pdf" style={{ display: 'none' }} onChange={e => setAadhaarFile(e.target.files[0] || null)} />
        <p className="prf-hint">JPEG, PNG or PDF Â· Mock upload</p>
      </div>
      {error && <p style={{ fontSize: 12, color: 'var(--error)', background: '#fef2f2', padding: '6px 10px', borderRadius: 8 }}>{error}</p>}
      <div className="prf-btn-row">
        <button className="prf-btn-secondary" style={{ flex: 1 }} onClick={() => { setEditing(false); setError(''); }}>Cancel</button>
        <button className="prf-btn-primary" style={{ flex: 2 }} onClick={save} disabled={saving}>{saving ? 'Savingâ€¦' : 'Save KYC'}</button>
      </div>
    </div>
  );
}

/* â”€â”€â”€ BankSetup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function BankSetup({ partner, onSave }) {
  const [editing, setEditing] = useState(false);
  const [bankName, setBankName] = useState(partner?.bank_name || '');
  const [accNum, setAccNum] = useState(partner?.account_number || '');
  const [ifsc, setIfsc] = useState(partner?.ifsc_code || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function save() {
    setSaving(true); setError('');
    try {
      await api.updateProfile({ 
        bank_name: bankName.trim(), 
        account_number: accNum.trim(),
        ifsc_code: ifsc.trim().toUpperCase()
      });
      onSave?.({ bank_name: bankName, account_number: accNum, ifsc_code: ifsc });
      setEditing(false);
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  }

  if (!editing) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <div>
        {partner?.bank_name 
          ? <><p style={{ fontWeight: 700, fontSize: 14 }}>{partner.bank_name}</p><p style={{ fontSize: 12, color: 'var(--green-primary)', marginTop: 2 }}>âœ“ Account ****{partner.account_number?.slice(-4)}</p></>
          : <p style={{ fontSize: 13, color: 'var(--text-light)', fontStyle: 'italic' }}>No bank account linked yet</p>
        }
      </div>
      <button className="prf-btn-outline" onClick={() => setEditing(true)}>{partner?.bank_name ? 'Update' : 'Setup Bank'}</button>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="prf-field">
        <label className="prf-label">Bank Name</label>
        <input className="prf-input" value={bankName} onChange={e => setBankName(e.target.value)} placeholder="e.g. HDFC Bank" />
      </div>
      <div className="prf-field">
        <label className="prf-label">Account Number</label>
        <input className="prf-input" value={accNum} onChange={e => setAccNum(e.target.value)} placeholder="Full account number" />
      </div>
      <div className="prf-field">
        <label className="prf-label">IFSC Code</label>
        <input className="prf-input" value={ifsc} onChange={e => setIfsc(e.target.value.toUpperCase())} placeholder="HDFC0001234" maxLength={11} />
      </div>
      {error && <p style={{ fontSize: 12, color: 'var(--error)', background: '#fef2f2', padding: '6px 10px', borderRadius: 8 }}>{error}</p>}
      <div className="prf-btn-row">
        <button className="prf-btn-secondary" style={{ flex: 1 }} onClick={() => setEditing(false)}>Cancel</button>
        <button className="prf-btn-primary" style={{ flex: 2 }} onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Save Bank Details'}</button>
      </div>
    </div>
  );
}

/* â”€â”€â”€ ZoneHistorySection â€“ real data from backend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function ZoneHistorySection({ zoneHistoryData, loading }) {
  const [open, setOpen] = useState(false);

  const history = zoneHistoryData?.history || [];
  const hasHistory = zoneHistoryData?.has_history && history.length > 0;

  return (
    <div className="prf-card">
      <div className="prf-card-body">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <p className="prf-section-title" style={{ marginBottom: 0 }}>ðŸ“ Zone Reassignment History</p>
          {hasHistory && (
            <button
              style={{ fontSize: 11, fontWeight: 700, color: 'var(--green-dark)', background: 'var(--green-light)', border: 'none', borderRadius: 20, padding: '4px 12px', cursor: 'pointer' }}
              onClick={() => setOpen(v => !v)}
            >
              {open ? 'Hide' : `Show (${history.length})`}
            </button>
          )}
        </div>

        {loading ? (
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>Loading historyâ€¦</p>
        ) : !hasHistory ? (
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>No zone changes yet.</p>
        ) : !open ? (
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>
            {history.length} past zone change{history.length !== 1 ? 's' : ''} on record.
          </p>
        ) : history.map((h, i) => {
          const oldZone = h.old_zone_name || h.oldZone || 'â€”';
          const newZone = h.new_zone_name || h.newZone || 'â€”';
          const premBefore = h.premium_before ?? h.premiumBefore;
          const premAfter  = h.premium_after  ?? h.premiumAfter;
          const reason     = h.reason || h.reassignment_reason || '';
          const dateStr    = h.effective_at || h.date;
          const up = premAfter > premBefore;
          const delta = Math.abs((premAfter || 0) - (premBefore || 0));

          return (
            <div className="zh-item" key={i}>
              <div className="zh-meta">
                <span className="zh-date">
                  {dateStr ? new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'â€”'}
                </span>
                {reason && <span className="zh-reason">{reason}</span>}
              </div>
              <div className="zh-zones">
                <span className="zh-old">{oldZone}</span>
                <span className="zh-arrow">â†’</span>
                <span className="zh-new">{newZone}</span>
              </div>
              {premBefore != null && premAfter != null && (
                <div className="zh-premium">
                  <span className="zh-prem-label">Premium:</span>
                  <span className="zh-prem-old">â‚¹{premBefore}</span>
                  <span className="zh-arrow">â†’</span>
                  <span className={`zh-prem-new ${up ? 'up' : 'down'}`}>
                    â‚¹{premAfter}/wk ({up ? `+â‚¹${delta}` : `-â‚¹${delta}`})
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* â”€â”€â”€ RenewalBreakdownCard â€“ real data from backend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export function RenewalBreakdownCard({ renewalPreview, renewalLoading, onRenew }) {
  // If backend data available, use it
  if (!renewalLoading && renewalPreview?.has_policy && renewalPreview?.breakdown) {
    const bd    = renewalPreview.breakdown;
    const tier  = renewalPreview.current_tier || 'standard';
    const total = renewalPreview.renewal_premium;

    const rows = [
      ['Base Premium',       `â‚¹${bd.base}`,                             `${tier} plan`,          false],
      ['Zone Risk Factor',   `+â‚¹${bd.zone_risk ?? 0}`,                  'Zone surcharge',        false],
      ['Seasonal Index',     `Ã—${Number(bd.seasonal_index ?? 1).toFixed(2)}`,  'City-specific monthly', false],
      ['RIQI Adjustment',   `Ã—${Number(bd.riqi_adjustment ?? 1).toFixed(2)}`, bd.riqi_band || '',    false],
      ['Activity Tier Factor', `Ã—${Number(bd.activity_factor ?? 1).toFixed(2)}`, tier,              false],
      ['Loyalty Discount',   `Ã—${Number(bd.loyalty_discount ?? 1).toFixed(2)}`,
        renewalPreview.loyalty_streak_weeks ? `${renewalPreview.loyalty_streak_weeks}-week streak` : '',
        bd.loyalty_discount < 1],
      ['Platform Fee',       'â‚¹0',                                       'Waived',                false],
    ];

    return (
      <div className="prf-card">
        <div className="prf-card-body">
          <p className="prf-section-title">ðŸ”„ Next Week Premium Breakdown</p>
          <p className="prf-section-sub">All formula factors â€” recalculated every Monday</p>
          {rows.map(([k, v, note, neg]) => (
            <div className="ren-row" key={k}>
              <span className="ren-key">{k}{note ? <span className="ren-note">({note})</span> : null}</span>
              <span className={`ren-val${neg ? ' neg' : ''}`}>{v}</span>
            </div>
          ))}
          <div className="ren-total">
            <span>Total Next Week</span>
            <span className="val">â‚¹{total}</span>
          </div>
          {renewalPreview.expires_at && (
            <p style={{ fontSize: 11, color: 'var(--text-light)', marginTop: 10 }}>
              Current policy expires {new Date(renewalPreview.expires_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </p>
          )}
          {renewalPreview.renewal_available && onRenew && (
            <button className="prf-btn-primary" style={{ marginTop: 14 }} onClick={onRenew}>
              Renew Now
            </button>
          )}
        </div>
      </div>
    );
  }

  if (renewalLoading) {
    return (
      <div className="prf-card">
        <div className="prf-card-body">
          <p className="prf-section-title">ðŸ”„ Next Week Premium Breakdown</p>
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>Loading renewal dataâ€¦</p>
        </div>
      </div>
    );
  }

  if (!renewalPreview?.has_policy) {
    return (
      <div className="prf-card">
        <div className="prf-card-body">
          <p className="prf-section-title">ðŸ”„ Next Week Premium Breakdown</p>
          <p style={{ fontSize: 13, color: 'var(--text-light)' }}>
            {renewalPreview?.message || 'No active policy found.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="prf-card">
      <div className="prf-card-body">
        <p className="prf-section-title">ðŸ”„ Next Week Premium Breakdown</p>
        <p style={{ fontSize: 13, color: 'var(--text-light)' }}>
          Renewal pricing is unavailable right now. Refresh after backend premium data is ready.
        </p>
      </div>
    </div>
  );
}

/* â”€â”€â”€ Main Profile â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export function Profile() {
  const navigate = useNavigate();
  const { user, logout, refreshUser } = useAuth();

  const [editing,  setEditing]  = useState(false);
  const [name,     setName]     = useState(user?.name || '');
  const [language, setLanguage] = useState(user?.language_pref || 'en');
  const [saving,   setSaving]   = useState(false);
  const [upiId,    setUpiId]    = useState(user?.upi_id || '');
  const [kyc,      setKyc]      = useState(user?.kyc || null);
  const [bankInfo, setBankInfo] = useState({ 
    bank_name: user?.bank_name, 
    account_number: user?.account_number, 
    ifsc_code: user?.ifsc_code 
  });

  const [zoneHistoryData, setZoneHistoryData] = useState(null);
  const [historyLoading,  setHistoryLoading]  = useState(true);
  const [renewalPreview,  setRenewalPreview]  = useState(null);
  const [renewalLoading,  setRenewalLoading]  = useState(true);
  const [legalModal,      setLegalModal]     = useState(null); // 'terms', 'privacy', 'support', 'rapidbot', 'privacy_consent'


  // â”€â”€ Load zone history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  useEffect(() => {
    api.getZoneHistory()
      .then(data => setZoneHistoryData(data))
      .catch(() => setZoneHistoryData({ history: [], total: 0, has_history: false }))
      .finally(() => setHistoryLoading(false));
  }, []);

  // â”€â”€ Load renewal preview â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  useEffect(() => {
    api.getRenewalPreview()
      .then(data => setRenewalPreview(data))
      .catch(() => setRenewalPreview(null))
      .finally(() => setRenewalLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateProfile({ name, language_pref: language });
      await refreshUser();
      setEditing(false);
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  }

  return (
    <>
      <style>{S}</style>
      <div className="prf-wrap">

        {/* â”€â”€ Hero â”€â”€ */}
        <div className="prf-hero">
          <div className="prf-avatar">P</div>
          <div>
            <p className="prf-hero-name">{user?.name}</p>
            <p className="prf-hero-phone">{user?.phone}</p>
            <p className="prf-hero-plat">{user?.platform} Partner</p>
          </div>
        </div>

        {/* â”€â”€ Edit Info â”€â”€ */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">Personal Info</p>
            {editing ? (
              <>
                <div className="prf-field">
                  <label className="prf-label">Full Name</label>
                  <input className="prf-input" value={name} onChange={e => setName(e.target.value)} />
                </div>
                <div className="prf-field">
                  <label className="prf-label">Language</label>
                  <select className="prf-select" value={language} onChange={e => setLanguage(e.target.value)}>
                    {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
                  </select>
                </div>
                <div className="prf-btn-row">
                  <button className="prf-btn-secondary" style={{ flex: 1 }} onClick={() => setEditing(false)}>Cancel</button>
                  <button className="prf-btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving}>
                    {saving ? 'Savingâ€¦' : 'Save Changes'}
                  </button>
                </div>
              </>
            ) : (
              <button className="prf-btn-outline" style={{ width: '100%' }} onClick={() => setEditing(true)}>
                Edit Profile
              </button>
            )}
          </div>
        </div>

        {/* â”€â”€ Zone chip â€“ show real name/code if available â”€â”€ */}
        {user?.zone_id && (
          <div className="prf-card">
            <div className="prf-card-body">
              <p className="prf-section-title">Your Zone</p>
              <div className="zone-chip">
                {user.zone_name
                  ? `${user.zone_name}${user.zone_code ? ` Â· ${user.zone_code}` : ''}`
                  : `Zone #${user.zone_id}`}
              </div>
            </div>
          </div>
        )}

        {/* â”€â”€ Zone History â€“ real backend data â”€â”€ */}
        <ZoneHistorySection zoneHistoryData={zoneHistoryData} loading={historyLoading} />

        {/* â”€â”€ Renewal Breakdown â€“ real backend data â”€â”€ */}
        <RenewalBreakdownCard
          renewalPreview={renewalPreview}
          renewalLoading={renewalLoading}
          onRenew={() => navigate('/policy')}
        />

        {/* â”€â”€ UPI Linking â”€â”€ */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">UPI Linking</p>
            <p className="prf-section-sub">Link your UPI ID to receive claim payouts instantly</p>
            <UpiSetup currentUpiId={upiId} onSave={u => setUpiId(u)} />
          </div>
        </div>

        {/* â”€â”€ Bank Account (IMPS Fallback) â”€â”€ */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">Bank Account (IMPS Fallback)</p>
            <p className="prf-section-sub">Backup payout channel if UPI fails or is unlinked</p>
            <BankSetup 
              partner={{...user, ...bankInfo}} 
              onSave={b => setBankInfo(b)} 
            />
          </div>
        </div>

        {/* â”€â”€ KYC â”€â”€ */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">KYC Verification</p>
            <p className="prf-section-sub">Complete KYC to unlock higher claim limits</p>
            <KycSetup currentKyc={kyc} onSave={k => setKyc(k)} />
          </div>
        </div>

        {/* â”€â”€ Notifications â”€â”€ */}
        <div className="prf-card">
          <div className="prf-card-body">
            <p className="prf-section-title">Notifications</p>
            <NotificationToggle />
          </div>
        </div>

        {/* â”€â”€ Account links â”€â”€ */}
        <div className="prf-card">
          <div className="prf-card-body" style={{ padding: '10px 18px' }}>
            <button className="prf-action-row" onClick={() => setLegalModal('terms')}>
              <span>Terms of Service</span>
              <span style={{ color: 'var(--text-light)' }}>-&gt;</span>
            </button>
            <button className="prf-action-row" onClick={() => setLegalModal('privacy')}>
              <span>Privacy Policy</span>
              <span style={{ color: 'var(--text-light)' }}>-&gt;</span>
            </button>
            <button className="prf-action-row" onClick={() => setLegalModal('privacy_consent')}>
              <span>Your Data & Consent</span>
              <span style={{ color: 'var(--text-light)' }}>-&gt;</span>
            </button>
            <button className="prf-action-row" onClick={() => setLegalModal('support')}>
              <span>Help & Support</span>
              <span style={{ color: 'var(--text-light)' }}>-&gt;</span>
            </button>
          </div>
        </div>

        {/* â”€â”€ Legal Modals â”€â”€ */}
        {legalModal && (
          <div className="legal-overlay" onClick={() => setLegalModal(null)}>
            <div 
              className="legal-sheet" 
              onClick={e => e.stopPropagation()}
              style={legalModal === 'rapidbot' ? { padding: 0, overflow: 'hidden' } : {}}
            >
              {/* Header logic (hidden for RapidBot to use its own) */}
              {legalModal !== 'rapidbot' && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <h2 className="legal-title">
                    {legalModal === 'terms' && 'Terms of Service'}
                    {legalModal === 'privacy' && 'Privacy Policy'}
                    {legalModal === 'privacy_consent' && 'Your Data & Consent'}
                    {legalModal === 'support' && 'Help & Support'}
                  </h2>
                  <button 
                    onClick={() => setLegalModal(null)}
                    style={{ background: 'var(--gray-bg)', border: 'none', borderRadius: '50%', width: 32, height: 32, cursor: 'pointer', fontSize: 18 }}
                  >âœ•</button>
                </div>
              )}

              <div className={legalModal === 'rapidbot' ? '' : 'legal-body'} style={legalModal === 'rapidbot' ? { height: '85vh' } : {}}>
                {legalModal === 'rapidbot' && <RapidBot />}
                {legalModal === 'privacy_consent' && <PrivacyConsentPanel />}
                
                {legalModal === 'terms' && (
                  <>
                    <div className="legal-section">
                      <h3 className="legal-h3">1. Coverage Scope</h3>
                      <p>RapidCover provides parametric insurance for gig delivery partners. Payouts are triggered automatically based on hyper-local weather and civic data.</p>
                    </div>
                    <div className="legal-section">
                      <h3 className="legal-h3">2. Payout Eligibility</h3>
                      <p>Partners must maintain an active delivery status during the disruption window. Claims are processed via real-time data oracles and are final once issued.</p>
                    </div>
                    <div className="legal-section">
                      <h3 className="legal-h3">3. Fair Use</h3>
                      <p>Any attempt to manipulate GPS data or simulate false platform activity will result in immediate policy cancellation without refund.</p>
                    </div>
                  </>
                )}

                {legalModal === 'privacy' && (
                  <>
                    <div className="legal-section">
                      <h3 className="legal-h3">1. Data Encryption</h3>
                      <p>Your Aadhaar and PAN details are hashed using SHA-256 before storage. We do not store plain-text identity documents.</p>
                    </div>
                    <div className="legal-section">
                      <h3 className="legal-h3">2. Location Privacy</h3>
                      <p>Location data is used exclusively for verifying your presence in your assigned zone during disruption events. We do not track you outside of active coverage windows.</p>
                    </div>
                    <div className="legal-section">
                      <h3 className="legal-h3">3. Payment Security</h3>
                      <p>UPI IDs are stored only to facilitate instant payouts via NPCI-approved gateways. We do not have access to your bank account details.</p>
                    </div>
                  </>
                )}

                {legalModal === 'support' && (
                  <>
                    <div className="grok-card" onClick={() => setLegalModal('rapidbot')} style={{ marginBottom: 20 }}>
                      <div className="bmsg-bot-avatar" style={{ border: '1.5px solid rgba(61, 184, 92, 0.3)', background: '#ffffff', color: '#3DB85C' }}>R</div>
                      <div>
                        <div style={{ fontSize: 15 }}>Talk to RapidBot AI</div>
                        <div style={{ fontSize: 11, opacity: 0.7, fontWeight: 400 }}>Instant help with policy locks, payouts & zones</div>
                      </div>
                    </div>
                    <HelpSupportPanel />
                  </>
                )}
              </div>
              
              <button 
                className="prf-btn-primary" 
                style={{ marginTop: 20 }}
                onClick={() => setLegalModal(null)}
              >
                Understood
              </button>
            </div>
          </div>
        )}

        {/* â”€â”€ Logout â”€â”€ */}
        <button className="prf-btn-danger" onClick={() => { logout(); navigate('/login'); }}>Logout</button>

        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-light)' }}>RapidCover v1.0.0</p>
      </div>
    </>
  );
}

export default Profile;
````

--- FILE: frontend/src/services/api.js ---
``javascript
/**
 * api.js  â€“  RapidCover frontend API client
 *
 * Person 1 Phase 2 additions are in the "EXPERIENCE STATE" section at the bottom.
 * All existing methods are preserved unchanged.
 */

const BASE = import.meta.env.VITE_API_URL || '/api/v1';

// â”€â”€ Shared helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function getToken() {
  return localStorage.getItem('access_token');
}

function authHeaders() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) { }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// â”€â”€ Auth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function requestOtp(phone) {
  const res = await fetch(`${BASE}/partners/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  });
  return handleResponse(res);
}

async function verifyOtp(phone, otp) {
  const res = await fetch(`${BASE}/partners/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, otp }),
  });
  return handleResponse(res);
}

async function register(partnerData) {
  const res = await fetch(`${BASE}/partners/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(partnerData),
  });
  return handleResponse(res);
}

async function requestRegisterOtp(phone) {
  // For registration, we generate a demo OTP client-side since the phone isn't registered yet.
  // In production, this would call a dedicated /partners/register-otp endpoint.
  await new Promise(r => setTimeout(r, 500)); // Simulate network delay
  const otp = String(Math.floor(100000 + Math.random() * 900000)); // 6-digit OTP
  return { message: 'OTP sent', otp };
}

// â”€â”€ Profile â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function getProfile() {
  const res = await fetch(`${BASE}/partners/me`, { headers: authHeaders() });
  return handleResponse(res);
}

async function updateProfile(data) {
  const res = await fetch(`${BASE}/partners/me`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

// â”€â”€ Policies â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function getActivePolicy() {
  const res = await fetch(`${BASE}/policies/active`, { headers: authHeaders() });
  return handleResponse(res);
}

async function getPolicyHistory() {
  const res = await fetch(`${BASE}/policies/history`, { headers: authHeaders() });
  return handleResponse(res);
}

async function getPolicyQuotes() {
  const res = await fetch(`${BASE}/policies/quotes`, { headers: authHeaders() });
  return handleResponse(res);
}

async function createPolicy(tier, autoRenew = true) {
  const res = await fetch(`${BASE}/policies`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tier, auto_renew: autoRenew }),
  });
  return handleResponse(res);
}

// â”€â”€ Stripe Payments â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function createCheckoutSession(tier, autoRenew = false) {
  const res = await fetch(`${BASE}/payments/checkout?tier=${tier}&auto_renew=${autoRenew}`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

async function confirmPayment(sessionId) {
  const res = await fetch(`${BASE}/payments/confirm?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

async function cancelPolicy(policyId) {
  const res = await fetch(`${BASE}/policies/${policyId}/cancel`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

async function getRenewalQuote(policyId, tier = null) {
  const url = new URL(`${BASE}/policies/${policyId}/renewal-quote`, window.location.origin);
  if (tier) url.searchParams.set('tier', tier);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function renewPolicy(policyId, tier = null, autoRenew = true) {
  const res = await fetch(`${BASE}/policies/${policyId}/renew`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ tier, auto_renew: autoRenew }),
  });
  return handleResponse(res);
}

async function updateAutoRenew(policyId, autoRenew) {
  const res = await fetch(`${BASE}/policies/${policyId}/auto-renew`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify({ auto_renew: autoRenew }),
  });
  return handleResponse(res);
}

async function downloadCertificate(policyId) {
  const res = await fetch(`${BASE}/policies/${policyId}/certificate`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.blob();
}

// â”€â”€ Claims â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function getClaimsSummary() {
  const res = await fetch(`${BASE}/claims/summary`, { headers: authHeaders() });
  return handleResponse(res);
}

async function getClaims(params = {}) {
  const url = new URL(`${BASE}/claims`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// â”€â”€ Triggers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function getActiveTriggers(zoneId = null) {
  const url = new URL(`${BASE}/triggers/active`, window.location.origin);
  if (zoneId) url.searchParams.set('zone_id', zoneId);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function getZone(zoneId) {
  const res = await fetch(`${BASE}/zones/${zoneId}`, { headers: authHeaders() });
  return handleResponse(res);
}

// â”€â”€ Zones â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function getZones(city = null) {
  const url = new URL(`${BASE}/zones`, window.location.origin);
  if (city) url.searchParams.set('city', city);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function getNearestZones(lat, lng) {
  const url = new URL(`${BASE}/zones/nearest`, window.location.origin);
  url.searchParams.set('lat', lat);
  url.searchParams.set('lng', lng);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// â”€â”€ RIQI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function getRiqiScores() {
  const res = await fetch(`${BASE}/partners/riqi`, { headers: authHeaders() });
  return handleResponse(res);
}

async function getCityRiqi(city) {
  const res = await fetch(`${BASE}/partners/riqi/${encodeURIComponent(city)}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// â”€â”€ Premium (legacy â€“ kept for backward compat) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function getPremiumQuotes(city, activeDays = 15, avgHours = 8, loyaltyWeeks = 0) {
  const url = new URL(`${BASE}/partners/quotes`, window.location.origin);
  url.searchParams.set('city', city);
  url.searchParams.set('active_days_last_30', activeDays);
  url.searchParams.set('avg_hours_per_day', avgHours);
  url.searchParams.set('loyalty_weeks', loyaltyWeeks);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// â”€â”€ Notifications â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function getNotificationStatus(endpoint = null) {
  const url = new URL(`${BASE}/notifications/status`, window.location.origin);
  if (endpoint) url.searchParams.set('endpoint', endpoint);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function subscribePush(subscriptionData) {
  const res = await fetch(`${BASE}/notifications/subscribe`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(subscriptionData),
  });
  return handleResponse(res);
}

async function unsubscribePush(endpoint = null) {
  const res = await fetch(`${BASE}/notifications/unsubscribe`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ endpoint }),
  });
  return handleResponse(res);
}

// â”€â”€ Validation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function validatePartnerId(partnerId, platform) {
  const url = new URL(`${BASE}/partners/validate-id`, window.location.origin);
  url.searchParams.set('partner_id', partnerId);
  url.searchParams.set('platform', platform);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

async function checkAvailability(phone, partnerId) {
  const url = new URL(`${BASE}/partners/check-availability`, window.location.origin);
  if (phone) url.searchParams.set('phone', phone);
  if (partnerId) url.searchParams.set('partner_id', partnerId);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// EXPERIENCE STATE  â€“  Person 1, Phase 2
// These five methods replace every hardcoded constant in dashboard / profile / policy.
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

/**
 * Master dashboard state â€“ replaces zoneReassignment, weatherAlert, streakWeeks.
 * Poll every 5 s during active drills.
 *
 * Response shape:
 * {
 *   zone_alert:        { type, message, severity, trigger_id, started_at } | null,
 *   zone_reassignment: { old_zone, new_zone, premium_delta, hours_left, ... } | null,
 *   loyalty:           { streak_weeks, discount_unlocked, next_milestone, discount_pct },
 *   premium_breakdown: { base, zone_risk, seasonal_index, riqi_adjustment,
 *                        activity_factor, loyalty_discount, total, city, riqi_band },
 *   latest_payout:     { claim_id, status:"paid", amount, upi_ref, paid_at } | null,
 *   fetched_at:        ISO string,
 * }
 */
async function getPartnerExperienceState() {
  const res = await fetch(`${BASE}/partners/me/experience-state`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Itemised premium breakdown. Replaces ALL TIER_PRICES multiplier math in UI.
 */
async function getPremiumBreakdown() {
  const res = await fetch(`${BASE}/partners/me/premium-breakdown`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Tier eligibility from backend. Frontend must use this to lock/unlock plan cards.
 *
 * Response: { active_days_last_30, loyalty_weeks, allowed_tiers, blocked_tiers, reasons, gate_blocked }
 */
async function getPartnerEligibility() {
  const res = await fetch(`${BASE}/partners/me/eligibility`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Real zone history. Replaces MOCK_ZONE_HISTORY in Profile.jsx.
 *
 * Response: { history:[{old_zone_name, new_zone_name, new_zone_code, effective_at, ...}], total, has_history }
 */
async function getZoneHistory() {
  const res = await fetch(`${BASE}/partners/me/zone-history`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Simplified renewal quote for profile page.
 * Replaces hardcoded renewal premium breakdown in Profile.jsx.
 */
async function getRenewalPreview() {
  const res = await fetch(`${BASE}/partners/me/renewal-preview`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// â”€â”€ Default export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const api = {
  // Auth
  requestOtp,
  verifyOtp,
  register,
  requestRegisterOtp,
  // Profile
  getProfile,
  updateProfile,
  // Policies
  getActivePolicy,
  getPolicyHistory,
  getPolicyQuotes,
  createPolicy,
  createCheckoutSession,
  confirmPayment,
  cancelPolicy,
  getRenewalQuote,
  renewPolicy,
  updateAutoRenew,
  downloadCertificate,
  // Claims
  getClaimsSummary,
  getClaims,
  // Triggers
  getActiveTriggers,
  // Zones
  getZone,
  getZones,
  getNearestZones,
  // RIQI
  getRiqiScores,
  getCityRiqi,
  // Premium (legacy)
  getPremiumQuotes,
  // Notifications
  getNotificationStatus,
  subscribePush,
  unsubscribePush,
  // Validation
  validatePartnerId,
  checkAvailability,
  // â”€â”€ Experience State (Person 1, Phase 2) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  getPartnerExperienceState,
  getPremiumBreakdown,
  getPartnerEligibility,
  getZoneHistory,
  getRenewalPreview,
};

export default api;
// â”€â”€ Platform Activity (zones router) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Base URL for zones endpoints
const ZONES_BASE = (import.meta.env.VITE_API_URL || '/api/v1') + '/zones';

function zonesAuthHeaders() {
  const token = localStorage.getItem('access_token');
  return { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

async function zonesHandleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const b = await res.json(); detail = b.detail || JSON.stringify(b); } catch (_) { }
    throw new Error(detail);
  }
  return res.json();
}

export async function getPartnerPlatformActivity(partnerId) {
  const res = await fetch(`${ZONES_BASE}/partners/${partnerId}/activity`, { headers: zonesAuthHeaders() });
  return zonesHandleResponse(res);
}

export async function setPartnerPlatformActivity(partnerId, data) {
  const res = await fetch(`${ZONES_BASE}/partners/${partnerId}/activity`, {
    method: 'PUT',
    headers: zonesAuthHeaders(),
    body: JSON.stringify(data),
  });
  return zonesHandleResponse(res);
}

export async function getPartnerPlatformEligibility(partnerId) {
  const res = await fetch(`${ZONES_BASE}/partners/${partnerId}/activity/eligibility`, { headers: zonesAuthHeaders() });
  return zonesHandleResponse(res);
}

export async function getBulkPlatformActivity(zoneId = null) {
  const url = new URL(`${ZONES_BASE}/partners/activity/bulk`, window.location.origin);
  if (zoneId) url.searchParams.set('zone_id', zoneId);
  const res = await fetch(url.toString(), { headers: zonesAuthHeaders() });
  return zonesHandleResponse(res);
}
````

--- FILE: frontend/src/services/proofApi.js ---
``javascript
/**
 * proofApi.js  â€“  Partner-side reassignment & proof API wrappers
 *
 * B2 owns this file.
 *
 * Covers:
 *   - Zone reassignment accept / reject (partner-initiated)
 *   - Active triggers enriched with source metadata
 *   - Countdown helpers driven by backend expires_at
 */

const BASE = import.meta.env.VITE_API_URL || '/api/v1';

// â”€â”€ Shared helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function getToken() {
  return localStorage.getItem('access_token');
}

function authHeaders() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// â”€â”€ Zone Reassignment (partner-facing) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/**
 * List all zone reassignment proposals for the logged-in partner.
 *
 * @returns {{ reassignments: ReassignmentResponse[], total: number, pending_count: number }}
 */
export async function getMyReassignments() {
  const res = await fetch(`${BASE}/partners/me/reassignments`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/**
 * Accept a pending zone reassignment proposal.
 * Updates partner.zone_id on the backend when successful.
 *
 * @param {number} reassignmentId
 * @returns {ZoneReassignmentActionResponse}
 */
export async function acceptReassignment(reassignmentId) {
  const res = await fetch(
    `${BASE}/partners/me/reassignments/${reassignmentId}/accept`,
    { method: 'POST', headers: authHeaders() }
  );
  return handleResponse(res);
}

/**
 * Reject a pending zone reassignment proposal.
 *
 * @param {number} reassignmentId
 * @returns {ZoneReassignmentActionResponse}
 */
export async function rejectReassignment(reassignmentId) {
  const res = await fetch(
    `${BASE}/partners/me/reassignments/${reassignmentId}/reject`,
    { method: 'POST', headers: authHeaders() }
  );
  return handleResponse(res);
}

// â”€â”€ Trigger proofs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/**
 * Get active trigger events, optionally filtered to a zone.
 *
 * @param {number|null} zoneId
 * @returns {{ triggers: TriggerEvent[] }}
 */
export async function getActiveTriggerProofs(zoneId = null) {
  const url = new URL(`${BASE}/triggers/active`, window.location.origin);
  if (zoneId) url.searchParams.set('zone_id', zoneId);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse(res);
}

// â”€â”€ Countdown helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/**
 * Return hours and minutes remaining until an ISO expiry timestamp.
 *
 * @param {string} expiresAt  ISO 8601 string from backend
 * @returns {{ totalMs: number, hours: number, minutes: number, seconds: number, expired: boolean }}
 */
export function parseCountdown(expiresAt) {
  const diff = new Date(expiresAt).getTime() - Date.now();
  if (diff <= 0) {
    return { totalMs: 0, hours: 0, minutes: 0, seconds: 0, expired: true };
  }
  const totalSeconds = Math.floor(diff / 1000);
  return {
    totalMs: diff,
    hours: Math.floor(totalSeconds / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
    expired: false,
  };
}

/**
 * Format countdown into a human-readable label.
 *
 * @param {string} expiresAt
 * @returns {string}  e.g. "23h 14m left" | "Expired"
 */
export function formatCountdown(expiresAt) {
  const cd = parseCountdown(expiresAt);
  if (cd.expired) return 'Expired';
  if (cd.hours > 0) return `${cd.hours}h ${cd.minutes}m left`;
  if (cd.minutes > 0) return `${cd.minutes}m ${cd.seconds}s left`;
  return `${cd.seconds}s left`;
}

/**
 * Return CSS urgency class based on how much time is left.
 *
 * @param {string} expiresAt
 * @returns {'safe'|'warn'|'urgent'|'expired'}
 */
export function countdownUrgency(expiresAt) {
  const cd = parseCountdown(expiresAt);
  if (cd.expired) return 'expired';
  if (cd.hours >= 12) return 'safe';
  if (cd.hours >= 4) return 'warn';
  return 'urgent';
}

// â”€â”€ Default export (named re-export for backward compat) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const proofApi = {
  getMyReassignments,
  acceptReassignment,
  rejectReassignment,
  getActiveTriggerProofs,
  parseCountdown,
  formatCountdown,
  countdownUrgency,
};

export default proofApi;
````

--- FILE: frontend/src/components/ProofCard.jsx ---
``jsx
/**
 * ProofCard.jsx  â€“  Reusable proof / timestamp card
 *
 * Person 3 Upgrades:
 *   - Now expandable to show "Claim Explanation" details
 *   - Shows exact metrics (e.g. 87mm/hr) and calculation breakdown
 *   - Professional icon-free UI
 *
 * B2 shared component. Used in Claims list, partner Dashboard, and demo proofs.
 *
 * Props:
 *   triggerType        {string}       'rain' | 'heat' | 'aqi' | 'shutdown' | 'closure'
 *   severity           {number?}      1â€“5, shown via SourceBadge
 *   status             {string}       'paid' | 'approved' | 'pending' | 'rejected'
 *   amount             {number?}      payout amount in â‚¹
 *   upiRef             {string?}      UPI reference (shown only for paid)
 *   createdAt          {string?}      ISO timestamp of claim / trigger creation
 *   paidAt             {string?}      ISO timestamp of payout
 *   metricValue        {string?}      Optional measurement label e.g. "87mm/hr", "AQI 410"
 *   fraudScore         {number?}      0.0â€“1.0 fraud score (shows warning if > 0.5)
 *   claimId            {number?}      Claim ID for reference
 *   validationData     {object|string?} Detailed validation and metric logic
 *   disruptionCategory {string?}      'full_halt' | 'severe_reduction' | 'moderate_reduction' | 'minor_reduction'
 *   disruptionFactor   {number?}      0.0â€“1.0 payout factor
 *   paymentStatus      {string?}      'not_started' | 'initiated' | 'confirmed' | 'failed' | 'reconcile_pending'
 */

import { useState } from 'react';
import SourceBadge from './SourceBadge';

/* â”€â”€â”€ Status config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const STATUS_CFG = {
  paid:     { bg: '#dcfce7', color: '#166534', border: '#bbf7d0', label: 'PAID' },
  approved: { bg: '#dbeafe', color: '#1e40af', border: '#bfdbfe', label: 'APPROVED' },
  pending:  { bg: '#fef9c3', color: '#854d0e', border: '#fde68a', label: 'PENDING' },
  rejected: { bg: '#fee2e2', color: '#991b1b', border: '#fecaca', label: 'REJECTED' },
};

const FALLBACK_STATUS = { bg: '#f3f4f6', color: '#374151', border: '#e5e7eb', label: 'UNKNOWN' };

/* â”€â”€â”€ Disruption category config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const DISRUPTION_CFG = {
  full_halt:          { icon: 'ðŸ›‘', label: 'Full Halt',          color: '#ef4444', bg: '#fee2e2' },
  severe_reduction:   { icon: 'âš ï¸', label: 'Severe Reduction',   color: '#f97316', bg: '#ffedd5' },
  moderate_reduction: { icon: 'ðŸ“‰', label: 'Moderate Reduction', color: '#eab308', bg: '#fef9c3' },
  minor_reduction:    { icon: 'ðŸ“Š', label: 'Minor Reduction',    color: '#3b82f6', bg: '#dbeafe' },
};

/* â”€â”€â”€ Payment status config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const PAY_CFG = {
  not_started:       { icon: 'â¸ï¸', label: 'Not started',      color: '#6b7280' },
  initiated:         { icon: 'ðŸ”„', label: 'Processing',        color: '#1e40af' },
  confirmed:         { icon: 'âœ…', label: 'Payment confirmed', color: '#166534' },
  failed:            { icon: 'âŒ', label: 'Payment failed',    color: '#991b1b' },
  reconcile_pending: { icon: 'âš ï¸', label: 'Under review',     color: '#854d0e' },
};

/* â”€â”€â”€ Date helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function fmtDate(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function fmtShort(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

/* â”€â”€â”€ Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export default function ProofCard({
  triggerType,
  severity,
  status = 'pending',
  amount,
  upiRef,
  createdAt,
  paidAt,
  metricValue,
  fraudScore,
  claimId,
  validationData,
  disruptionCategory,
  disruptionFactor,
  paymentStatus,
}) {
  const [expanded, setExpanded] = useState(false);
  const stCfg = STATUS_CFG[status] || FALLBACK_STATUS;
  const dCfg = disruptionCategory ? DISRUPTION_CFG[disruptionCategory] : null;
  const pCfg = paymentStatus ? PAY_CFG[paymentStatus] : null;

  // Attempt to parse validation data for the deep dive
  let trLog = null;
  if (validationData) {
    try {
      const parsed = typeof validationData === 'string' ? JSON.parse(validationData) : validationData;
      trLog = parsed.transaction_log || parsed;
    } catch (e) {
      console.warn("Failed to parse claim validation data", e);
    }
  }

  const calculation = trLog?.payout_metadata?.payout_calculation;
  const cityCap = trLog?.city_cap_check;
  const triggerDetail = trLog?.trigger || {};

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      style={{
        background: '#ffffff',
        border: '1.5px solid #e2ece2',
        borderRadius: 18,
        overflow: 'hidden',
        fontFamily: "'DM Sans', sans-serif",
        cursor: 'pointer',
        transition: 'transform 0.1s, box-shadow 0.2s',
        transform: expanded ? 'scale(1.01)' : 'scale(1)',
        boxShadow: expanded ? '0 8px 24px rgba(61, 184, 92, 0.1)' : 'none',
      }}
    >
      {/* Header strip */}
      <div
        style={{
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #e2ece2',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <SourceBadge type={triggerType} severity={severity} size="md" />
          {(metricValue || triggerDetail.severity_label) && (
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                background: '#f3f4f6',
                color: '#374151',
                padding: '2px 8px',
                borderRadius: 20,
              }}
            >
              {metricValue || triggerDetail.severity_label}
            </span>
          )}
          {/* Disruption category badge */}
          {dCfg && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 3,
                background: dCfg.bg,
                color: dCfg.color,
                fontSize: 10,
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 20,
              }}
            >
              {dCfg.icon} {dCfg.label}
              {disruptionFactor != null && ` Â· ${(disruptionFactor * 100).toFixed(0)}%`}
            </span>
          )}
        </div>

        {/* Status chip */}
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: stCfg.bg,
            color: stCfg.color,
            border: `1.5px solid ${stCfg.border}`,
            fontSize: 11,
            fontWeight: 700,
            padding: '3px 10px',
            borderRadius: 20,
            whiteSpace: 'nowrap',
          }}
        >
          {stCfg.label}
        </span>
      </div>

      {/* Body */}
      <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {/* Amount */}
        {amount != null && (
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
            <span style={{
              fontFamily: "'Nunito', sans-serif",
              fontWeight: 900,
              fontSize: 22,
              color: status === 'paid' ? '#2a9e47' : '#1a2e1a',
            }}>
              Rs.{amount}
            </span>
            {claimId && (
              <span style={{ fontSize: 11, color: '#8a9e8a' }}>- Claim #{claimId}</span>
            )}
          </div>
        )}

        {/* Timestamps */}
        {createdAt && !expanded && (
          <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
             {fmtDate(createdAt)}
          </p>
        )}
        {paidAt && !expanded && (
          <p style={{ fontSize: 12, color: '#2a9e47', fontWeight: 600, margin: 0 }}>
            Paid {fmtShort(paidAt)}
          </p>
        )}

        {/* Expanded View - "The Why" */}
        {expanded && (
          <div style={{ 
            marginTop: 12, 
            paddingTop: 12, 
            borderTop: '1px dashed #e2ece2',
            display: 'flex',
            flexDirection: 'column',
            gap: 12
          }}>
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#8a9e8a', textTransform: 'uppercase', marginBottom: 6 }}>Payout Explanation</p>
              <div style={{ background: '#f7f9f7', borderRadius: 12, padding: 12, fontSize: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ color: '#4a5e4a' }}>Trigger Source</span>
                  <span style={{ fontWeight: 600 }}>{triggerDetail.label || triggerType}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ color: '#4a5e4a' }}>Disruption Metric</span>
                  <span style={{ fontWeight: 600 }}>{metricValue || 'Detected'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #e2ece2', marginTop: 8, paddingTop: 8 }}>
                  <span style={{ color: '#4a5e4a' }}>Payout Formula</span>
                  <span style={{ fontWeight: 600, color: '#2a9e47' }}>Auto-calculated</span>
                </div>
              </div>
            </div>

            {cityCap && (
              <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 12, padding: 10 }}>
                <p style={{ fontSize: 11, fontWeight: 700, color: '#92400e', marginBottom: 2 }}>City Hard Cap Status</p>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span>Current City BCR</span>
                  <span style={{ fontWeight: 600 }}>{(cityCap.current_ratio * 100).toFixed(1)}%</span>
                </div>
                <p style={{ fontSize: 10, color: '#b45309', marginTop: 4 }}>
                  Reinsurance active above 120%. Your payout is protected.
                </p>
              </div>
            )}

            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: 11, color: '#8a9e8a', marginBottom: 2 }}>Initiated</p>
                <p style={{ fontSize: 12, fontWeight: 600 }}>{fmtShort(createdAt)}</p>
              </div>
              {paidAt && (
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 11, color: '#2a9e47', marginBottom: 2 }}>Settled</p>
                  <p style={{ fontSize: 12, fontWeight: 600 }}>{fmtShort(paidAt)}</p>
                </div>
              )}
            </div>

            {upiRef && status === 'paid' && (
              <div style={{
                fontSize: 12,
                fontWeight: 700,
                color: upiRef.startsWith('tr_') ? '#4f46e5' : '#2a9e47',
                background: upiRef.startsWith('tr_') ? '#e0e7ff' : '#f0fdf4',
                padding: '8px 12px',
                borderRadius: 10,
              }}>
                <div style={{ fontSize: 10, opacity: 0.7, marginBottom: 2 }}>{upiRef.startsWith('tr_') ? 'Payment via Stripe Connect' : 'Payment via UPI Direct'}</div>
                {upiRef}
              </div>
            )}

            <p style={{ fontSize: 11, color: '#8a9e8a', textAlign: 'center', marginTop: 4 }}>Tap again to collapse</p>
          </div>
        )}

        {/* Payment state indicator */}
        {pCfg && paymentStatus !== 'not_started' && paymentStatus !== 'confirmed' && (
          <p style={{
            fontSize: 11,
            color: pCfg.color,
            background: `${pCfg.color}12`,
            padding: '4px 10px',
            borderRadius: 8,
            margin: 0,
            fontWeight: 600,
          }}>
            {pCfg.icon} {pCfg.label}
          </p>
        )}

        {/* Fraud warning */}
        {fraudScore != null && fraudScore > 0.5 && !expanded && (
          <p style={{
            fontSize: 11,
            color: '#b45309',
            background: '#fffbeb',
            padding: '4px 10px',
            borderRadius: 8,
            margin: 0,
          }}>
            Manual review status (score: {fraudScore.toFixed(2)})
          </p>
        )}
      </div>
    </div>
  );
}
````

--- FILE: frontend/src/components/StressWidget.jsx ---
``jsx
import React, { useState } from 'react';

const SCENARIOS = [
    {
        id: 'S1',
        name: '14-Day Monsoon',
        cities: 'BLR + BOM',
        partners: 4200,
        payout: 'â‚¹82.32L',
        payoutRaw: 8232000,
        poolPct: '~190%',
        mode: 'Day 5: Sustained Event - 70% payout mode. Day 7: Reinsurance flagged. City cap 120% - Reinsurance activation.',
        badge: 'reinsurance',
        detail: {
            blr: { partners: 1800, payout: 'â‚¹35.28L', calc: '1,800 x 14d x Rs.280/d @70% of Rs.400' },
            bom: { partners: 2400, payout: 'â‚¹47.04L', calc: '2,400 x 14d x Rs.280/d @70% of Rs.400' },
            note: 'Days 1-4: Normal mode (Rs.400/d Standard max). Day 5+: Sustained Event flag - 70% payout (Rs.280/d), no weekly cap, max 21 days.',
        },
    },
    {
        id: 'S2',
        name: 'AQI Spike',
        cities: 'DEL + NOI + GGN',
        partners: 5100,
        payout: 'â‚¹81.6L',
        payoutRaw: 8160000,
        poolPct: '~180%',
        mode: 'Day 5: Sustained Event flag. Proportional reduction via zone pool share cap. Each city loss ratio monitored independently.',
        badge: 'reinsurance',
        detail: {
            del: { partners: 3200, payout: 'â‚¹51.2L', calc: '3,200 x 5d x Rs.400 @70% = Rs.280 (sustained from day 5)' },
            noi: { partners: 1900, payout: 'â‚¹30.4L', calc: '1,900 x 5d x Rs.400 @70% = Rs.280 (sustained from day 5)' },
            note: 'Ward-level trigger data applies â€” Anand Vihar AQI does not auto-trigger Dwarka. Each ward threshold checked independently.',
        },
    },
    {
        id: 'S3',
        name: 'Cyclone',
        cities: 'CHN + BOM',
        partners: 6000,
        payout: 'â‚¹90L',
        payoutRaw: 9000000,
        poolPct: '~320%',
        mode: 'Reinsurance activation on Day 1 (Loss Ratio immediately exceeds 100%). City payout capped at 120% of weekly pool.',
        badge: 'catastrophic',
        detail: {
            chn: { partners: 2200, payout: 'â‚¹33L', calc: '2,200 x 3d x Rs.500 (Pro max)' },
            bom: { partners: 3800, payout: 'â‚¹57L', calc: '3,800 x 3d x Rs.500 (Pro max)' },
            note: 'Catastrophic event. Reinsurance treaty activates immediately. Partners receive proportional reduction via zone_pool_share formula.',
        },
    },
    {
        id: 'S4',
        name: 'State Bandh',
        cities: 'All zones',
        partners: 3500,
        payout: 'â‚¹42L',
        payoutRaw: 4200000,
        poolPct: '~97%',
        mode: 'Normal payout Days 1-2. Day 3: Proportional reduction if pool approaches cap. Active shift check filters partners on leave.',
        badge: 'proportional',
        detail: {
            note: '~3,500 active partners (excluding those on declared leave or voluntarily offline). Day 3 triggers proportional reduction. Reinsurance review flagged. Govt policy exclusion does NOT apply â€” bandh is operational disruption, not regulatory override.',
        },
    },
    {
        id: 'S5',
        name: 'Dark Store Mass Closure',
        cities: 'BLR (40% stores)',
        partners: 700,
        payout: 'â‚¹2.8L',
        payoutRaw: 280000,
        poolPct: '~18%',
        mode: 'Normal payout Day 1. Zone reassignment protocol activated: 24h acceptance window, premium recalculated for remaining days.',
        badge: 'normal',
        detail: {
            note: 'FSSAI regulatory order closes 40% of Bangalore dark stores. Direct trigger is store closure (covered), not government policy change. Zone reassignment history logged in partner profile.',
        },
    },
    {
        id: 'S6',
        name: 'Collusion Ring',
        cities: '50 fake accounts, same zone',
        partners: 50,
        payout: 'â‚¹0',
        payoutRaw: 0,
        poolPct: '8%',
        mode: 'Auto-reject + Fraud queue. Expected: 35â€“40 accounts auto-rejected (score >0.90), 10â€“15 to manual queue (0.75â€“0.90).',
        badge: 'fraud',
        detail: {
            signals: [
                'device_fingerprint_match (w5)',
                'centroid_drift_score (w7)',
                'claim_frequency_score (w4)',
                'gps_coherence (w1)',
            ],
            note: 'Admin fraud queue shows cluster pattern â€” all 50 claims from same event, same zone, same device profile. Bulk-reject available.',
        },
    },
];

const BADGE_STYLES = {
    reinsurance: { bg: '#fee2e2', color: 'var(--error)', label: 'Reinsurance' },
    catastrophic: { bg: '#fef2f2', color: 'var(--error)', label: 'Catastrophic' },
    proportional: { bg: '#fef9c3', color: 'var(--warning)', label: 'Proportional' },
    normal: { bg: 'var(--green-light)', color: 'var(--green-primary)', label: 'Normal' },
    fraud: { bg: '#f3e8ff', color: '#9333ea', label: 'Fraud Blocked' },
};

export default function StressWidget() {
    const [expanded, setExpanded] = useState(null);

    function toggle(id) {
        setExpanded(prev => (prev === id ? null : id));
    }

    return (
        <section className="stress-widget">
            <div className="stress-widget__header" style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h2 className="stress-widget__title" style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1.5rem', color: 'var(--text-dark)' }}>âš¡ Stress Scenarios</h2>
                    <p className="stress-widget__subtitle" style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.4rem' }}>
                        Actuarial stress test â€” 6 scenarios modelling extreme but plausible events
                    </p>
                </div>
                <span className="stress-widget__count" style={{ fontSize: '0.75rem', fontWeight: 800, background: 'var(--gray-bg)', padding: '0.4rem 0.8rem', borderRadius: '10px', color: 'var(--text-mid)' }}>{SCENARIOS.length} scenarios</span>
            </div>

            <div className="stress-table-wrapper" style={{ background: 'var(--white)', borderRadius: '24px', border: '1.5px solid var(--border)', overflow: 'hidden' }}>
                <table className="stress-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead style={{ background: 'var(--gray-bg)', borderBottom: '1.5px solid var(--border)' }}>
                        <tr style={{ textAlign: 'left' }}>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>ID</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Scenario</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>Cities</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)', textAlign: 'right' }}>Partners</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)', textAlign: 'right' }}>Est. Payout</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)', textAlign: 'center' }}>Weekly Pool</th>
                            <th style={{ padding: '1rem', fontSize: '0.7rem', fontWeight: 900, textTransform: 'uppercase', color: 'var(--text-light)' }}>System Mode</th>
                            <th style={{ padding: '1rem' }}></th>
                        </tr>
                    </thead>
                    <tbody>
                        {SCENARIOS.map(s => {
                            const badge = BADGE_STYLES[s.badge];
                            const isOpen = expanded === s.id;
                            return (
                                <React.Fragment key={s.id}>
                                    <tr 
                                        style={{ borderBottom: '1px solid var(--border)', background: isOpen ? 'var(--gray-bg)' : 'transparent', transition: 'all 0.15s' }}
                                    >
                                        <td style={{ padding: '1rem' }}><code style={{ fontWeight: 800 }}>{s.id}</code></td>
                                        <td style={{ padding: '1rem', fontWeight: 700, fontSize: '0.9rem' }}>{s.name}</td>
                                        <td style={{ padding: '1rem', fontSize: '0.8rem', color: 'var(--text-mid)' }}>{s.cities}</td>
                                        <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 700 }}>{s.partners.toLocaleString()}</td>
                                        <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 900, color: 'var(--text-dark)' }}>{s.payout}</td>
                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                            <span 
                                                style={{ fontSize: '0.65rem', fontWeight: 900, padding: '0.3rem 0.6rem', borderRadius: '8px', background: badge.bg, color: badge.color, border: `1px solid ${badge.color}25` }}
                                            >
                                                {s.poolPct}
                                            </span>
                                        </td>
                                        <td style={{ padding: '1rem' }}>
                                            <span 
                                                style={{ fontSize: '0.65rem', fontWeight: 900, padding: '0.3rem 0.6rem', borderRadius: '8px', background: 'var(--gray-bg)', color: 'var(--text-mid)', textTransform: 'uppercase' }}
                                            >
                                                {badge.label}
                                            </span>
                                        </td>
                                        <td style={{ padding: '1rem' }}>
                                            <button 
                                                onClick={() => toggle(s.id)}
                                                style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: 'var(--text-light)', transition: 'transform 0.2s', transform: isOpen ? 'rotate(180deg)' : 'none' }}
                                            >
                                                â–¼
                                            </button>
                                        </td>
                                    </tr>
                                    {isOpen && (
                                        <tr style={{ background: 'var(--gray-bg)' }}>
                                            <td colSpan={8} style={{ padding: '0 1rem 1.5rem' }}>
                                                <div style={{ background: 'var(--white)', border: '1.5px solid var(--border)', borderRadius: '18px', padding: '1.25rem' }}>
                                                    <p style={{ fontSize: '0.85rem', color: 'var(--text-dark)', lineHeight: 1.6, marginBottom: '1rem' }}>
                                                        <strong style={{ fontFamily: 'Nunito', color: 'var(--green-primary)' }}>System Response:</strong> {s.mode}
                                                    </p>

                                                    {s.detail.blr && (
                                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                                            <div style={{ background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '12px' }}>
                                                                <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>Bangalore</span>
                                                                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{s.detail.blr.payout}</span>
                                                                <code style={{ fontSize: '0.6rem', display: 'block', marginTop: '0.2rem', opacity: 0.7 }}>{s.detail.blr.calc}</code>
                                                            </div>
                                                            <div style={{ background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '12px' }}>
                                                                <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>Mumbai</span>
                                                                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{s.detail.bom.payout}</span>
                                                                <code style={{ fontSize: '0.6rem', display: 'block', marginTop: '0.2rem', opacity: 0.7 }}>{s.detail.bom.calc}</code>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {s.detail.del && (
                                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                                            <div style={{ background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '12px' }}>
                                                                <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>Delhi NCR</span>
                                                                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{s.detail.del.payout}</span>
                                                            </div>
                                                            <div style={{ background: 'var(--gray-bg)', padding: '0.75rem', borderRadius: '12px' }}>
                                                                <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>Satellite</span>
                                                                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-dark)' }}>{s.detail.noi.payout}</span>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {s.detail.signals && (
                                                        <div style={{ marginBottom: '1rem' }}>
                                                            <span style={{ fontSize: '0.7rem', fontWeight: 900, color: 'var(--text-light)', textTransform: 'uppercase', display: 'block', marginBottom: '0.4rem' }}>Fraud Signals</span>
                                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                                                {s.detail.signals.map((sig, i) => (
                                                                    <span key={i} style={{ fontSize: '0.65rem', background: 'var(--gray-bg)', padding: '0.2rem 0.5rem', borderRadius: '6px', color: 'var(--text-mid)', fontWeight: 600 }}>{sig}</span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}

                                                    <p style={{ fontSize: '0.75rem', color: 'var(--text-light)', padding: '0.75rem', background: 'var(--gray-bg)', borderRadius: '10px', marginTop: '0.5rem', borderLeft: '3px solid var(--border)' }}>
                                                        {s.detail.note}
                                                    </p>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            <div style={{ marginTop: '2.5rem', background: 'var(--white)', border: '1.5px solid var(--border)', borderRadius: '24px', padding: '1.5rem 2rem' }}>
                <p style={{ fontFamily: 'Nunito', fontWeight: 900, fontSize: '1rem', color: 'var(--text-dark)', marginBottom: '1.5rem' }}>Actuarial Payout Exposure</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {SCENARIOS.map(s => {
                        const maxPayout = 10800000;
                        const pct = s.payoutRaw === 0 ? 2 : Math.round((s.payoutRaw / maxPayout) * 100);
                        const badge = BADGE_STYLES[s.badge];
                        return (
                            <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <span style={{ width: 20, fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-light)' }}>{s.id}</span>
                                <div style={{ flex: 1, height: 10, background: 'var(--gray-bg)', borderRadius: '5px', overflow: 'hidden' }}>
                                    <div
                                        style={{ width: `${pct}%`, height: '100%', background: badge.color, borderRadius: '5px', transition: 'width 1s ease' }}
                                    />
                                </div>
                                <span style={{ width: 60, fontSize: '0.8rem', fontWeight: 900, color: 'var(--text-dark)', textAlign: 'right' }}>{s.payout}</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}
````

## Supporting Files

--- FILE: backend/app/database.py ---
``python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()

# SQLite requires different engine configuration
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call this on app startup."""
    Base.metadata.create_all(bind=engine)
````

--- FILE: backend/requirements.txt ---
``text
# FastAPI and server
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Database
sqlalchemy>=2.0.25
psycopg2-binary>=2.9.9
alembic>=1.13.1

# Redis
redis>=5.0.1

# Configuration
pydantic-settings>=2.1.0

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# HTTP client for external APIs
httpx>=0.26.0

# Utilities
python-dotenv>=1.0.0

# Push notifications
pywebpush>=2.0.0

# PDF generation
reportlab>=4.0.0
razorpay>=1.4.0
stripe
````

--- FILE: frontend/package.json ---
``json
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "test": "vitest run --config vitest.config.js",
    "test:watch": "vitest --config vitest.config.js",
    "test:ui": "vitest --ui --config vitest.config.js"
  },
  "dependencies": {
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "react-router-dom": "^7.13.2"
  },
  "devDependencies": {
    "@eslint/js": "^9.39.4",
    "@tailwindcss/vite": "^4.2.2",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/react": "^19.2.14",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.1",
    "@vitest/ui": "^4.1.2",
    "autoprefixer": "^10.4.27",
    "eslint": "^9.39.4",
    "eslint-plugin-react-hooks": "^7.0.1",
    "eslint-plugin-react-refresh": "^0.5.2",
    "globals": "^17.4.0",
    "jsdom": "^29.0.1",
    "postcss": "^8.5.8",
    "tailwindcss": "^4.2.2",
    "vite": "^8.0.1",
    "vitest": "^4.1.2"
  }
}
````

--- FILE: backend/app/models/__init__.py ---
``python
from app.models.partner import Partner
from app.models.zone import Zone
from app.models.policy import Policy
from app.models.trigger_event import TriggerEvent
from app.models.claim import Claim
from app.models.push_subscription import PushSubscription
from app.models.drill_session import DrillSession, DrillType, DrillStatus
from app.models.zone_reassignment import ZoneReassignment, ReassignmentStatus
from app.models.zone_risk_profile import ZoneRiskProfile

__all__ = [
    "Partner",
    "Zone",
    "Policy",
    "TriggerEvent",
    "Claim",
    "PushSubscription",
    "DrillSession",
    "DrillType",
    "DrillStatus",
    "ZoneReassignment",
    "ReassignmentStatus",
    "ZoneRiskProfile",
]
````

--- FILE: backend/app/models/claim.py ---
``python
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ClaimStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    trigger_event_id = Column(Integer, ForeignKey("trigger_events.id"), nullable=False)

    amount = Column(Float, nullable=False)
    status = Column(Enum(ClaimStatus), default=ClaimStatus.PENDING)

    # Fraud detection score (0-1, higher = more suspicious)
    fraud_score = Column(Float, default=0.0)

    # Validation data from pipeline (JSON string)
    # Contains: zone_match, platform_confirmation, traffic_check, gps_coherence
    validation_data = Column(Text, nullable=True)

    # UPI transaction reference
    upi_ref = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    policy = relationship("Policy", back_populates="claims")
    trigger_event = relationship("TriggerEvent", back_populates="claims")
````

--- FILE: backend/app/models/drill_session.py ---
``python
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text, Boolean
from sqlalchemy.sql import func
import enum
from app.database import Base


class DrillType(str, enum.Enum):
    FLASH_FLOOD = "flash_flood"
    AQI_SPIKE = "aqi_spike"
    HEATWAVE = "heatwave"
    STORE_CLOSURE = "store_closure"
    CURFEW = "curfew"
    # Phase 2 Team Guide Stress Scenarios (Section 2E)
    MONSOON_14DAY = "monsoon_14day"           # 14-day sustained monsoon (BLR+BOM)
    MULTI_CITY_AQI = "multi_city_aqi"         # Multi-city AQI spike (DEL+NOI+GGN)
    CYCLONE = "cyclone"                       # Cyclone scenario (CHN+BOM)
    BANDH = "bandh"                           # City-wide civic shutdown / bandh
    COLLUSION_FRAUD = "collusion_fraud"       # Fraud detection stress test


class DrillStatus(str, enum.Enum):
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DrillSession(Base):
    __tablename__ = "drill_sessions"

    id = Column(Integer, primary_key=True, index=True)
    drill_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID string
    drill_type = Column(Enum(DrillType), nullable=False)
    zone_id = Column(Integer, nullable=False)
    zone_code = Column(String(20), nullable=False)
    preset = Column(String(50), nullable=False)

    status = Column(Enum(DrillStatus), default=DrillStatus.STARTED)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Pipeline events stored as JSON array
    pipeline_events = Column(Text, nullable=True)  # JSON string

    # Reference to trigger event created by drill
    trigger_event_id = Column(Integer, nullable=True)

    # Impact metrics
    affected_partners = Column(Integer, default=0)  # Partners in zone
    eligible_partners = Column(Integer, default=0)  # Partners with active policies
    claims_created = Column(Integer, default=0)
    claims_paid = Column(Integer, default=0)
    claims_pending = Column(Integer, default=0)

    # Financial metrics
    payouts_total = Column(Float, default=0.0)

    # Skipped reasons stored as JSON dict
    skipped_reasons = Column(Text, nullable=True)  # JSON string

    # Latency metrics in milliseconds
    trigger_latency_ms = Column(Integer, nullable=True)
    claim_creation_latency_ms = Column(Integer, nullable=True)
    payout_latency_ms = Column(Integer, nullable=True)
    total_latency_ms = Column(Integer, nullable=True)

    # Errors stored as JSON array
    errors = Column(Text, nullable=True)  # JSON string

    # Force mode bypasses duration requirements
    force_mode = Column(Boolean, default=False)
````

--- FILE: backend/app/models/partner.py ---
``python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class Platform(str, enum.Enum):
    ZEPTO = "zepto"
    BLINKIT = "blinkit"


class Language(str, enum.Enum):
    ENGLISH = "en"
    TAMIL = "ta"
    KANNADA = "kn"
    TELUGU = "te"
    HINDI = "hi"
    MARATHI = "mr"
    BENGALI = "bn"


class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    upi_id = Column(String, nullable=True)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    aadhaar_hash = Column(String(64), nullable=True)  # SHA-256 hash of Aadhaar
    platform = Column(Enum(Platform), nullable=False)
    partner_id = Column(String(50), nullable=True)  # Platform-specific ID
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    language_pref = Column(Enum(Language), default=Language.ENGLISH)
    is_active = Column(Boolean, default=True)
    # Shift preferences
    shift_days = Column(JSON, nullable=True, default=lambda: [])      # e.g. ["mon","tue","wed","thu","fri"]
    shift_start = Column(String(10), nullable=True)                    # e.g. "09:00"
    shift_end = Column(String(10), nullable=True)                      # e.g. "18:00"

    # Zone history (list of {zone_id, from_date, to_date})
    zone_history = Column(JSON, nullable=True, default=lambda: [])

    # IMPS Fallback fields
    bank_name = Column(String(100), nullable=True)
    account_number = Column(String(30), nullable=True)
    ifsc_code = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    zone = relationship("Zone", back_populates="partners")
    policies = relationship("Policy", back_populates="partner")
    push_subscriptions = relationship("PushSubscription", back_populates="partner")
    kyc = Column(JSON, nullable=True, default=lambda: {
        "aadhaar_number": None,
        "pan_number":     None,
        "kyc_status":     "skipped",
    })
````

--- FILE: backend/app/models/policy.py ---
``python
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class PolicyTier(str, enum.Enum):
    FLEX = "flex"
    STANDARD = "standard"
    PRO = "pro"


class PolicyStatus(str, enum.Enum):
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    LAPSED = "lapsed"
    CANCELLED = "cancelled"


# Tier configuration based on specification image
# Flex:     250/day * 2 days = 500 max/week. Ratio 500/22 = 22.7 (~1:23)
# Standard: 400/day * 3 days = 1200 max/week. Ratio 1200/33 = 36.3 (~1:36)
# Pro:      500/day * 4 days = 2000 max/week. Ratio 2000/45 = 44.4 (~1:44)
TIER_CONFIG = {
    PolicyTier.FLEX: {
        "weekly_premium": 22,
        "max_daily_payout": 250,
        "max_days_per_week": 2,
    },
    PolicyTier.STANDARD: {
        "weekly_premium": 33,
        "max_daily_payout": 400,
        "max_days_per_week": 3,
    },
    PolicyTier.PRO: {
        "weekly_premium": 45,
        "max_daily_payout": 500,
        "max_days_per_week": 4,
    },
}


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    tier = Column(Enum(PolicyTier), nullable=False)

    # Premium and payout limits (may differ from tier defaults due to dynamic pricing)
    weekly_premium = Column(Float, nullable=False)
    max_daily_payout = Column(Float, nullable=False)
    max_days_per_week = Column(Integer, nullable=False)

    # Policy period
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=True)

    # Policy lifecycle status
    status = Column(Enum(PolicyStatus), default=PolicyStatus.ACTIVE)
    grace_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Renewal chain tracking
    renewed_from_id = Column(Integer, ForeignKey("policies.id"), nullable=True)

    # Stripe payment tracking (TEST MODE)
    stripe_session_id = Column(String, nullable=True, unique=True)
    stripe_payment_intent = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    partner = relationship("Partner", back_populates="policies")
    claims = relationship("Claim", back_populates="policy")
    renewed_from = relationship("Policy", remote_side="Policy.id", backref="renewed_to")
````

--- FILE: backend/app/models/push_subscription.py ---
``python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh_key = Column(String(200), nullable=False)
    auth_key = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    partner = relationship("Partner", back_populates="push_subscriptions")
````

--- FILE: backend/app/models/trigger_event.py ---
``python
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class TriggerType(str, enum.Enum):
    RAIN = "rain"           # Heavy rain/flood (>55mm/hr sustained 30+ mins)
    HEAT = "heat"           # Extreme heat (>43Â°C sustained 4+ hours)
    AQI = "aqi"             # Dangerous AQI (>400 for 3+ hours)
    SHUTDOWN = "shutdown"   # Civic shutdown/curfew/bandh (2+ hours)
    CLOSURE = "closure"     # Dark store force majeure closure (>90 mins)


# Trigger thresholds
TRIGGER_THRESHOLDS = {
    TriggerType.RAIN: {
        "threshold": 55,       # mm/hr
        "duration_mins": 30,
    },
    TriggerType.HEAT: {
        "threshold": 43,       # Â°C
        "duration_hours": 4,
    },
    TriggerType.AQI: {
        "threshold": 400,
        "duration_hours": 3,
    },
    TriggerType.SHUTDOWN: {
        "duration_hours": 2,
    },
    TriggerType.CLOSURE: {
        "duration_mins": 90,
    },
}


class TriggerEvent(Base):
    __tablename__ = "trigger_events"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    trigger_type = Column(Enum(TriggerType), nullable=False)

    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Severity level (1-5)
    severity = Column(Integer, default=1)

    # Raw API response data (JSON string)
    source_data = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    zone = relationship("Zone", back_populates="trigger_events")
    claims = relationship("Claim", back_populates="trigger_event")
````

--- FILE: backend/app/models/zone.py ---
``python
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., BLR-047
    name = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False, index=True)

    # Polygon stored as GeoJSON string (for PostGIS, use Geometry type)
    polygon = Column(Text, nullable=True)

    # Risk score computed by ML model (0-100)
    risk_score = Column(Float, default=50.0)

    # Admin controls & visibility
    is_suspended = Column(Boolean, default=False)
    density_band = Column(String(20), default="Medium")  # Low, Medium, High

    # Dark store location
    dark_store_lat = Column(Float, nullable=True)
    dark_store_lng = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    partners = relationship("Partner", back_populates="zone")
    trigger_events = relationship("TriggerEvent", back_populates="zone")
````

--- FILE: backend/app/models/zone_reassignment.py ---
``python
"""
Zone reassignment model for 24-hour acceptance workflow.

When a partner is proposed to move to a new zone (e.g., Zepto/Blinkit reassignment),
they have 24 hours to accept or reject. If no action is taken, the proposal expires.
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ReassignmentStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ZoneReassignment(Base):
    __tablename__ = "zone_reassignments"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)
    old_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    new_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)

    status = Column(Enum(ReassignmentStatus), default=ReassignmentStatus.PROPOSED, nullable=False)

    # Premium adjustment calculation
    premium_adjustment = Column(Float, default=0.0)  # Positive = credit, Negative = debit
    remaining_days = Column(Integer, default=0)

    # Timestamps for the workflow
    proposed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # proposed_at + 24h
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    partner = relationship("Partner", foreign_keys=[partner_id])
    old_zone = relationship("Zone", foreign_keys=[old_zone_id])
    new_zone = relationship("Zone", foreign_keys=[new_zone_id])
````

--- FILE: backend/app/models/zone_risk_profile.py ---
``python
"""
Zone risk profile model for RIQI (Road Infrastructure Quality Index) data.

Stores per-zone RIQI scores and associated metrics instead of relying
on hardcoded city-level defaults. Supports provenance tracking.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ZoneRiskProfile(Base):
    __tablename__ = "zone_risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), unique=True, nullable=False, index=True)

    # RIQI score (0-100) - higher = better infrastructure
    riqi_score = Column(Float, nullable=False, default=55.0)
    riqi_band = Column(String(20), nullable=False, default="urban_fringe")  # urban_core/urban_fringe/peri_urban

    # Input metrics used to calculate RIQI
    historical_suspensions = Column(Integer, default=0)  # Platform suspension count in last 12 months
    closure_frequency = Column(Float, default=0.0)  # Average closures per month
    weather_severity_freq = Column(Float, default=0.0)  # Weather events per month
    aqi_severity_freq = Column(Float, default=0.0)  # AQI breach events per month
    zone_density = Column(Float, default=0.0)  # Partner density (partners per sq km)

    # Provenance tracking
    calculated_from = Column(String(50), nullable=False, default="seeded")  # seeded | computed | manual | fallback_city_default
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    zone = relationship("Zone", backref="risk_profile", uselist=False)
````

--- FILE: backend/app/schemas/__init__.py ---
``python
from app.schemas.partner import (
    PartnerCreate,
    PartnerResponse,
    PartnerLogin,
    OTPVerify,
    TokenResponse,
)
from app.schemas.policy import (
    PolicyCreate,
    PolicyResponse,
    PolicyTier,
)
from app.schemas.claim import (
    ClaimResponse,
    ClaimStatus,
)
from app.schemas.zone import (
    ZoneResponse,
)

__all__ = [
    "PartnerCreate",
    "PartnerResponse",
    "PartnerLogin",
    "OTPVerify",
    "TokenResponse",
    "PolicyCreate",
    "PolicyResponse",
    "PolicyTier",
    "ClaimResponse",
    "ClaimStatus",
    "ZoneResponse",
]
````

--- FILE: backend/app/schemas/claim.py ---
``python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any
from app.models.claim import ClaimStatus
from app.models.trigger_event import TriggerType


class PayoutMetadata(BaseModel):
    """Structured payout calculation details included in ClaimResponse."""
    disruption_hours: Optional[float] = None
    hourly_rate: Optional[float] = None
    severity: Optional[int] = None
    severity_multiplier: Optional[float] = None
    base_payout: Optional[float] = None
    adjusted_payout: Optional[float] = None
    final_payout: Optional[float] = None
    trigger_type: Optional[str] = None
    zone_id: Optional[int] = None


class ClaimResponse(BaseModel):
    id: int
    policy_id: int
    trigger_event_id: int
    amount: float
    status: ClaimStatus
    fraud_score: float
    upi_ref: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    # Nested trigger event info
    trigger_type: Optional[TriggerType] = None
    trigger_started_at: Optional[datetime] = None

    # Payout metadata from validation_data
    payout_metadata: Optional[PayoutMetadata] = None

    # Partial disruption data
    disruption_category: Optional[str] = None
    disruption_factor: Optional[float] = None

    # Payment state machine status
    payment_status: Optional[str] = None

    model_config = {"from_attributes": True}


class ClaimListResponse(BaseModel):
    claims: list[ClaimResponse]
    total: int
    page: int
    page_size: int


class ClaimSummary(BaseModel):
    """Summary of claims for a partner."""
    total_claims: int
    total_paid: float
    pending_claims: int
    pending_amount: float
````

--- FILE: backend/app/schemas/drill.py ---
``python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any
from app.models.drill_session import DrillType, DrillStatus


class DrillRunRequest(BaseModel):
    drill_type: DrillType
    zone_code: str = Field(..., description="Zone code e.g. BLR-047")
    force: bool = Field(default=True, description="Bypass duration requirements")
    preset: Optional[str] = Field(default=None, description="Custom preset name, defaults to drill_type value")
    simulate_sustained_days: int = Field(default=0, description="Inject N consecutive days history for 70% payout demo (0 = disabled, 5+ triggers sustained mode)")


class DrillStartResponse(BaseModel):
    drill_id: str
    status: DrillStatus
    zone_code: str
    drill_type: DrillType
    message: str


class DrillPipelineEvent(BaseModel):
    step: str
    message: str
    ts: datetime
    metadata: Optional[dict[str, Any]] = None


class DrillStatusResponse(BaseModel):
    drill_id: str
    status: DrillStatus
    drill_type: DrillType
    zone_code: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    events_count: int = 0
    trigger_event_id: Optional[int] = None
    claims_created: int = 0


class LatencyMetrics(BaseModel):
    trigger_latency_ms: Optional[int] = None
    claim_creation_latency_ms: Optional[int] = None
    payout_latency_ms: Optional[int] = None
    total_latency_ms: Optional[int] = None


class SkippedPartner(BaseModel):
    reason: str
    count: int


class DrillImpactResponse(BaseModel):
    drill_id: str
    status: DrillStatus
    affected_partners: int
    eligible_partners: int
    claims_created: int
    claims_paid: int
    claims_pending: int
    payouts_total: float
    skipped_partners: dict[str, int]  # reason -> count
    latency_metrics: LatencyMetrics


class VerificationCheck(BaseModel):
    name: str
    status: str  # "pass", "fail", "skip"
    message: str
    latency_ms: Optional[int] = None


class VerificationResponse(BaseModel):
    overall_status: str  # "healthy", "degraded", "unhealthy"
    checks: list[VerificationCheck]
    run_at: datetime


class DrillHistoryItem(BaseModel):
    drill_id: str
    drill_type: DrillType
    zone_code: str
    status: DrillStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    claims_created: int
    total_latency_ms: Optional[int] = None

    model_config = {"from_attributes": True}


class DrillHistoryResponse(BaseModel):
    drills: list[DrillHistoryItem]
    total: int
````

--- FILE: backend/app/schemas/kyc.py ---
``python

from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum


class KYCStatus(str, Enum):
    pending  = "pending"
    verified = "verified"
    failed   = "failed"
    skipped  = "skipped"


class KYCSchema(BaseModel):
    aadhaar_number: Optional[str] = None
    pan_number:     Optional[str] = None
    kyc_status:     KYCStatus = KYCStatus.skipped

    @validator("aadhaar_number")
    def validate_aadhaar(cls, v):
        if v is None:
            return v
        if v.startswith("UID-"):
            return v
        digits = v.replace(" ", "")
        if not digits.isdigit() or len(digits) != 12:
            raise ValueError("Aadhaar must be 12 digits")
        return digits

    @validator("pan_number")
    def validate_pan(cls, v):
        if v is None:
            return v
        if v.startswith("PAN-"):
            return v
        import re
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v.strip().upper()):
            raise ValueError("Invalid PAN format (e.g. ABCDE1234F)")
        return v.strip().upper()

    class Config:
        use_enum_values = True
````

--- FILE: backend/app/schemas/notification.py ---
``python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh_key: str
    auth_key: str


class PushSubscriptionDelete(BaseModel):
    endpoint: Optional[str] = None


class PushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationStatusResponse(BaseModel):
    is_subscribed: bool
    subscription_count: int


class NotificationPayload(BaseModel):
    title: str
    body: str
    icon: Optional[str] = "/icon-192.png"
    url: Optional[str] = "/"
    tag: Optional[str] = "rapidcover-notification"
    type: Optional[str] = None
    claim_id: Optional[int] = None
````

--- FILE: backend/app/schemas/partner.py ---
``python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from app.models.partner import Platform, Language
from app.schemas.kyc import KYCSchema   

class PartnerCreate(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$", description="Phone number")
    name: str = Field(..., min_length=2, max_length=100)
    platform: Platform
    partner_id: Optional[str] = None
    zone_id: Optional[int] = None
    language_pref: Language = Language.ENGLISH
    upi_id: Optional[str] = None
    kyc:    Optional[KYCSchema] = None
    shift_days: Optional[list] = None        # e.g. ["mon","tue","wed"]
    shift_start: Optional[str] = None        # e.g. "09:00"
    shift_end: Optional[str] = None          # e.g. "18:00"
    zone_history: Optional[list] = None      # e.g. [{"zone_id": 1, "from": "2026-01"}]
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    @validator("upi_id")
    def validate_upi(cls, v):
        if v is None:
            return v
        import re
        if not re.match(r"^[\w.\-]{3,}@[\w]{3,}$", v.strip()):
            raise ValueError("Invalid UPI ID format (e.g. name@okaxis)")
        return v.strip()

class PartnerLogin(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")


class OTPVerify(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    otp: str = Field(..., min_length=6, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PartnerResponse(BaseModel):
    id: int
    phone: str
    name: str
    platform: Platform
    partner_id: Optional[str] = None
    zone_id: Optional[int] = None
    language_pref: Language
    is_active: bool
    created_at: datetime
    upi_id: Optional[str] = None
    kyc:    Optional[KYCSchema] = None
    shift_days: Optional[list] = None
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None
    zone_history: Optional[list] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    model_config = {"from_attributes": True}


class PartnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    zone_id: Optional[int] = None
    language_pref: Optional[Language] = None
    upi_id: Optional[str] = None
    kyc:    Optional[KYCSchema] = None
    shift_days: Optional[list] = None
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None
    zone_history: Optional[list] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
````

--- FILE: backend/app/schemas/policy.py ---
``python
from pydantic import BaseModel, computed_field
from datetime import datetime
from typing import Optional
from enum import Enum
from app.models.policy import PolicyTier


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    LAPSED = "lapsed"
    CANCELLED = "cancelled"


class PolicyCreate(BaseModel):
    tier: PolicyTier
    auto_renew: bool = True


class PolicyResponse(BaseModel):
    id: int
    partner_id: int
    tier: PolicyTier
    weekly_premium: float
    max_daily_payout: float
    max_days_per_week: int
    starts_at: datetime
    expires_at: datetime
    is_active: bool
    auto_renew: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyQuote(BaseModel):
    """Premium quote based on partner's zone risk score."""
    tier: PolicyTier
    base_premium: float
    risk_adjustment: float
    final_premium: float
    max_daily_payout: float
    max_days_per_week: int


class PolicyResponseExtended(BaseModel):
    """Extended policy response with computed lifecycle fields."""
    id: int
    partner_id: int
    tier: PolicyTier
    weekly_premium: float
    max_daily_payout: float
    max_days_per_week: int
    starts_at: datetime
    expires_at: datetime
    is_active: bool
    auto_renew: bool
    created_at: datetime
    renewed_from_id: Optional[int] = None

    # Computed lifecycle fields
    status: PolicyStatus
    days_until_expiry: Optional[int] = None
    hours_until_grace_ends: Optional[float] = None
    can_renew: bool = False

    model_config = {"from_attributes": True}


class PolicyRenewRequest(BaseModel):
    """Request to renew a policy."""
    tier: Optional[PolicyTier] = None  # Optional tier change
    auto_renew: bool = True


class PolicyRenewalQuote(BaseModel):
    """Renewal quote with loyalty discount."""
    tier: PolicyTier
    base_premium: float
    risk_adjustment: float
    loyalty_discount: float
    final_premium: float
    max_daily_payout: float
    max_days_per_week: int


class AutoRenewUpdate(BaseModel):
    """Request to update auto-renewal preference."""
    auto_renew: bool
````

--- FILE: backend/app/schemas/riqi.py ---
``python
"""
Schemas for RIQI (Road Infrastructure Quality Index) provenance APIs.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RiqiInputMetrics(BaseModel):
    """Input metrics used to calculate RIQI score."""
    historical_suspensions: int
    closure_frequency: float
    weather_severity_freq: float
    aqi_severity_freq: float
    zone_density: float


class RiqiProvenanceResponse(BaseModel):
    """Full RIQI provenance response for a zone."""
    zone_id: int
    zone_code: str
    zone_name: str
    city: str
    riqi_score: float
    riqi_band: str  # urban_core | urban_fringe | peri_urban
    payout_multiplier: float
    premium_adjustment: float
    input_metrics: RiqiInputMetrics
    calculated_from: str  # seeded | computed | fallback_city_default
    last_updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RiqiListResponse(BaseModel):
    """Response for listing all zone RIQI profiles."""
    zones: list[RiqiProvenanceResponse]
    total: int
    data_source: str  # "database" | "mixed"


class RiqiRecomputeResponse(BaseModel):
    """Response after recomputing RIQI for a zone."""
    zone_code: str
    old_riqi_score: float
    new_riqi_score: float
    old_band: str
    new_band: str
    recomputed_at: datetime
    metrics_used: RiqiInputMetrics
````

--- FILE: backend/app/schemas/stress_scenarios.py ---
``python
"""
Schemas for stress scenario calculations.

Stress scenarios model potential disaster impacts and calculate
the reserve needed to cover projected claims.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StressScenarioResponse(BaseModel):
    """Response for a single stress scenario calculation."""
    scenario_id: str
    scenario_name: str
    days: int
    projected_claims: int
    projected_payout: float
    city_reserve_available: float
    reserve_needed: float  # max(projected_payout - city_reserve_available, 0)
    formula_breakdown: dict
    assumptions: list[str]
    data_source: str  # "live" | "seeded" | "mock"


class StressScenarioListResponse(BaseModel):
    """Response for list of all stress scenarios."""
    scenarios: list[StressScenarioResponse]
    computed_at: datetime
    total_reserve_needed: float


class StressCityMetrics(BaseModel):
    """City-level metrics used in stress calculations."""
    city: str
    active_policies: int
    avg_weekly_premium: float
    total_weekly_reserve: float
    zone_count: int
````

--- FILE: backend/app/schemas/zone.py ---
``python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ZoneResponse(BaseModel):
    id: int
    code: str
    name: str
    city: str
    risk_score: float
    is_suspended: bool = False
    dark_store_lat: Optional[float] = None
    dark_store_lng: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ZoneRiskUpdate(BaseModel):
    """Update zone risk score (called by ML service)."""
    risk_score: float


class ZoneCreate(BaseModel):
    code: str
    name: str
    city: str
    is_suspended: Optional[bool] = False
    polygon: Optional[str] = None
    dark_store_lat: Optional[float] = None
    dark_store_lng: Optional[float] = None
````

--- FILE: backend/app/schemas/zone_reassignment.py ---
``python
"""
Schemas for zone reassignment 24-hour acceptance workflow.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.zone_reassignment import ReassignmentStatus


class ZoneReassignmentProposal(BaseModel):
    """Request to propose a zone reassignment."""
    partner_id: int
    new_zone_id: int


class ZoneReassignmentResponse(BaseModel):
    """Response for a zone reassignment."""
    id: int
    partner_id: int
    old_zone_id: Optional[int]
    new_zone_id: int
    status: ReassignmentStatus
    premium_adjustment: float
    remaining_days: int
    proposed_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    hours_remaining: Optional[float] = None  # Computed field for convenience

    # Additional context
    old_zone_name: Optional[str] = None
    new_zone_name: Optional[str] = None
    partner_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ZoneReassignmentListResponse(BaseModel):
    """Response for listing zone reassignments."""
    reassignments: list[ZoneReassignmentResponse]
    total: int
    pending_count: int


class ZoneReassignmentActionResponse(BaseModel):
    """Response for accept/reject actions."""
    id: int
    status: ReassignmentStatus
    message: str
    zone_updated: bool = False
    new_zone_id: Optional[int] = None
````

## Test Files

--- FILE: backend/tests/test_validation_matrix.py ---
``python
"""
test_validation_matrix.py
--------------------------
Tests for the Real-World Validation Matrix (Feature 1).

Covers:
  - All 10 checks are present in the matrix
  - Matrix stored on claim validation_data
  - Correct pass/fail per check condition
  - Matrix summary totals are accurate
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_partner(
    is_active=True,
    pin_code=None,
    shift_days=None,
    shift_start=None,
    shift_end=None,
):
    p = MagicMock()
    p.id = 1
    p.name = "Test Partner"
    p.is_active = is_active
    p.pin_code = pin_code
    p.shift_days = shift_days or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    p.shift_start = shift_start
    p.shift_end = shift_end
    p.zone_id = 1
    return p


def _make_policy(is_active=True):
    p = MagicMock()
    p.id = 10
    p.is_active = is_active
    p.starts_at = datetime.utcnow() - timedelta(days=7)
    p.expires_at = datetime.utcnow() + timedelta(days=7)
    p.max_daily_payout = 500.0
    p.tier = MagicMock()
    p.tier.value = "basic"
    return p


def _make_trigger(zone_id=1, trigger_type=None, severity=3):
    t = MagicMock()
    t.id = 100
    t.zone_id = zone_id
    t.trigger_type = trigger_type or MagicMock()
    t.trigger_type.value = "rain"
    t.severity = severity
    t.started_at = datetime.utcnow()
    return t


def _make_zone(zone_id=1):
    z = MagicMock()
    z.id = zone_id
    z.code = "BLR-001"
    z.city = "Bangalore"
    z.pin_codes = ["560001", "560002"]
    z.dark_store_lat = 12.9352
    z.dark_store_lng = 77.6245
    return z


def _make_fraud_result(score=0.2, recommendation="approve"):
    return {
        "score": score,
        "recommendation": recommendation,
        "factors": {},
        "hard_reject_reasons": [],
    }


def _make_db():
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = None
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidationMatrixStructure:
    """Matrix must always contain exactly 10 named checks."""

    EXPECTED_CHECK_NAMES = {
        "source_threshold_breach",
        "zone_match",
        "pin_code_match",
        "active_policy",
        "shift_window",
        "partner_activity",
        "platform_activity",
        "fraud_score_below_threshold",
        "data_freshness",
        "cross_source_agreement",
    }

    def _run_matrix(self, partner=None, policy=None, trigger=None, zone=None,
                    fraud=None, source_data=None):
        from app.services.claims_processor import build_validation_matrix

        partner = partner or _make_partner()
        policy = policy or _make_policy()
        trigger = trigger or _make_trigger()
        zone = zone or _make_zone()
        fraud = fraud or _make_fraud_result()
        db = _make_db()

        with (
            patch("app.services.claims_processor.check_partner_pin_code_match",
                  return_value=(True, "pin_code_match")),
            patch("app.services.claims_processor.is_partner_available_for_trigger",
                  return_value=(True, "eligible")),
            patch("app.services.claims_processor.get_partner_runtime_metadata",
                  return_value={"is_manual_offline": False, "leave_until": None,
                                "manual_offline_until": None, "pin_code": "560001"}),
            patch("app.services.claims_processor.evaluate_partner_platform_eligibility",
                  return_value={"eligible": True, "score": 0.9,
                                "reasons": [], "activity": {"platform": "zomato"}}),
        ):
            return build_validation_matrix(partner, policy, trigger, zone, fraud, db,
                                           source_data or {})

    def test_returns_list(self):
        matrix = self._run_matrix()
        assert isinstance(matrix, list)

    def test_ten_checks_present(self):
        matrix = self._run_matrix()
        assert len(matrix) == 10

    def test_all_expected_check_names_present(self):
        matrix = self._run_matrix()
        names = {c["check_name"] for c in matrix}
        assert names == self.EXPECTED_CHECK_NAMES

    def test_each_check_has_required_fields(self):
        matrix = self._run_matrix()
        for check in matrix:
            assert "check_name" in check
            assert "passed" in check
            assert isinstance(check["passed"], bool)
            assert "reason" in check
            assert "source" in check
            assert "confidence" in check
            assert 0.0 <= check["confidence"] <= 1.0

    def test_matrix_summary_totals_are_correct(self):
        matrix = self._run_matrix()
        passed = sum(1 for c in matrix if c["passed"])
        failed = sum(1 for c in matrix if not c["passed"])
        assert passed + failed == len(matrix)


class TestValidationMatrixCheckLogic:
    """Individual checks fire correctly under different conditions."""

    def _run(self, **kwargs):
        from app.services.claims_processor import build_validation_matrix

        partner = kwargs.pop("partner", _make_partner())
        policy = kwargs.pop("policy", _make_policy())
        trigger = kwargs.pop("trigger", _make_trigger())
        zone = kwargs.pop("zone", _make_zone())
        fraud = kwargs.pop("fraud", _make_fraud_result())
        source_data = kwargs.pop("source_data", {})
        db = _make_db()

        with (
            patch("app.services.claims_processor.check_partner_pin_code_match",
                  return_value=kwargs.pop("pin_match", (True, "pin_code_match"))),
            patch("app.services.claims_processor.is_partner_available_for_trigger",
                  return_value=kwargs.pop("available", (True, "eligible"))),
            patch("app.services.claims_processor.get_partner_runtime_metadata",
                  return_value=kwargs.pop("runtime_meta", {
                      "is_manual_offline": False, "leave_until": None,
                      "manual_offline_until": None, "pin_code": "560001"
                  })),
            patch("app.services.claims_processor.evaluate_partner_platform_eligibility",
                  return_value=kwargs.pop("platform_eval", {
                      "eligible": True, "score": 0.9,
                      "reasons": [], "activity": {"platform": "zomato"}
                  })),
        ):
            matrix = build_validation_matrix(partner, policy, trigger, zone, fraud, db, source_data)
        return {c["check_name"]: c for c in matrix}

    def test_zone_match_passes_when_zone_ids_match(self):
        trigger = _make_trigger(zone_id=1)
        zone = _make_zone(zone_id=1)
        checks = self._run(trigger=trigger, zone=zone)
        assert checks["zone_match"]["passed"] is True

    def test_zone_match_fails_when_zone_ids_differ(self):
        trigger = _make_trigger(zone_id=99)
        zone = _make_zone(zone_id=1)
        checks = self._run(trigger=trigger, zone=zone)
        assert checks["zone_match"]["passed"] is False

    def test_pin_code_match_passes_when_match(self):
        checks = self._run(pin_match=(True, "pin_code_match"))
        assert checks["pin_code_match"]["passed"] is True

    def test_pin_code_match_fails_when_mismatch(self):
        checks = self._run(pin_match=(False, "pin_code_mismatch"))
        assert checks["pin_code_match"]["passed"] is False

    def test_active_policy_passes_for_valid_policy(self):
        checks = self._run()
        assert checks["active_policy"]["passed"] is True

    def test_active_policy_fails_for_expired_policy(self):
        policy = _make_policy()
        policy.expires_at = datetime.utcnow() - timedelta(days=3)
        checks = self._run(policy=policy)
        assert checks["active_policy"]["passed"] is False

    def test_shift_window_passes_when_available(self):
        checks = self._run(available=(True, "eligible"))
        assert checks["shift_window"]["passed"] is True

    def test_shift_window_fails_when_outside(self):
        checks = self._run(available=(False, "outside_shift_days"))
        assert checks["shift_window"]["passed"] is False

    def test_partner_activity_fails_when_manual_offline(self):
        checks = self._run(runtime_meta={
            "is_manual_offline": True,
            "leave_until": None,
            "manual_offline_until": None,
            "pin_code": "560001",
        })
        assert checks["partner_activity"]["passed"] is False

    def test_partner_activity_fails_when_on_leave(self):
        checks = self._run(runtime_meta={
            "is_manual_offline": False,
            "leave_until": datetime.utcnow() + timedelta(hours=3),
            "manual_offline_until": None,
            "pin_code": "560001",
        })
        assert checks["partner_activity"]["passed"] is False

    def test_platform_activity_passes_when_eligible(self):
        checks = self._run(platform_eval={
            "eligible": True, "score": 0.9,
            "reasons": [], "activity": {"platform": "swiggy"}
        })
        assert checks["platform_activity"]["passed"] is True

    def test_platform_activity_fails_when_not_eligible(self):
        checks = self._run(platform_eval={
            "eligible": False, "score": 0.2,
            "reasons": [], "activity": {"platform": "blinkit"}
        })
        assert checks["platform_activity"]["passed"] is False

    def test_fraud_score_passes_below_threshold(self):
        fraud = _make_fraud_result(score=0.3)
        checks = self._run(fraud=fraud)
        assert checks["fraud_score_below_threshold"]["passed"] is True

    def test_fraud_score_fails_above_threshold(self):
        fraud = _make_fraud_result(score=0.95)
        checks = self._run(fraud=fraud)
        assert checks["fraud_score_below_threshold"]["passed"] is False

    def test_cross_source_agreement_passes_with_good_score(self):
        checks = self._run(source_data={"oracle_agreement_score": 0.9})
        assert checks["cross_source_agreement"]["passed"] is True

    def test_cross_source_agreement_fails_with_low_score(self):
        checks = self._run(source_data={"oracle_agreement_score": 0.3})
        assert checks["cross_source_agreement"]["passed"] is False

    def test_threshold_check_uses_source_data_values(self):
        checks = self._run(source_data={
            "rainfall_mm_hr": 62.0,
            "threshold": 55.0,
            "data_source": "live",
        })
        assert checks["source_threshold_breach"]["passed"] is True

    def test_threshold_check_fails_below_threshold(self):
        checks = self._run(source_data={
            "rainfall_mm_hr": 30.0,
            "threshold": 55.0,
            "data_source": "live",
        })
        assert checks["source_threshold_breach"]["passed"] is False


class TestValidationMatrixOnClaim:
    """Ensure validation_matrix is serialised into claim.validation_data."""

    def test_validation_matrix_key_in_validation_data(self):
        # Simulate what process_trigger_event stores
        matrix = [
            {"check_name": "zone_match", "passed": True, "reason": "ok",
             "source": "db", "confidence": 1.0}
        ]
        vd = {"validation_matrix": matrix, "validation_matrix_summary": {
            "total_checks": 1, "passed": 1, "failed": 0, "overall": "pass"
        }}
        serialised = json.dumps(vd)
        loaded = json.loads(serialised)
        assert "validation_matrix" in loaded
        assert len(loaded["validation_matrix"]) == 1
        assert loaded["validation_matrix"][0]["check_name"] == "zone_match"

    def test_matrix_summary_overall_pass_when_all_pass(self):
        matrix = [
            {"check_name": f"check_{i}", "passed": True,
             "reason": "ok", "source": "db", "confidence": 1.0}
            for i in range(10)
        ]
        summary = {
            "total_checks": len(matrix),
            "passed": sum(1 for c in matrix if c["passed"]),
            "failed": sum(1 for c in matrix if not c["passed"]),
            "overall": "pass" if all(c["passed"] for c in matrix) else "fail",
        }
        assert summary["overall"] == "pass"
        assert summary["passed"] == 10
        assert summary["failed"] == 0

    def test_matrix_summary_overall_fail_when_any_fail(self):
        matrix = [
            {"check_name": "zone_match", "passed": False,
             "reason": "mismatch", "source": "db", "confidence": 0.0},
            {"check_name": "active_policy", "passed": True,
             "reason": "ok", "source": "db", "confidence": 1.0},
        ]
        overall = "pass" if all(c["passed"] for c in matrix) else "fail"
        assert overall == "fail"
````

--- FILE: backend/tests/test_trigger_pincode_strictness.py ---
``python
"""
Tests for trigger eligibility pin-code strictness.

Verifies that the pin-code matching logic now fails explicitly
instead of falling back to True when data is missing.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestTriggerPincodeStrictness:
    """Tests for strict pin-code matching in trigger eligibility."""

    def test_missing_partner_pincode_returns_fail(self, mock_db, mock_partner, mock_zone):
        """Test that missing partner pin code returns False with reason."""
        from app.services.trigger_engine import check_partner_pin_code_match

        # Ensure mock_partner and mock_zone don't have pin_code attributes
        mock_partner.configure_mock(pin_code=None)
        mock_zone.configure_mock(pin_codes=None)

        # Mock runtime metadata with no pin code
        with patch("app.services.trigger_engine.get_partner_runtime_metadata") as mock_partner_meta:
            with patch("app.services.trigger_engine.get_zone_coverage_metadata") as mock_zone_meta:
                mock_partner_meta.return_value = {
                    "partner_id": 1,
                    "pin_code": None,  # Missing pin code
                    "is_manual_offline": False,
                    "manual_offline_until": None,
                    "leave_until": None,
                    "leave_note": None,
                    "updated_at": None,
                }
                mock_zone_meta.return_value = {
                    "zone_id": 1,
                    "pin_codes": ["560034", "560095"],  # Zone has coverage
                    "density_weight": 0.35,
                    "ward_name": "Koramangala",
                    "updated_at": None,
                }

                result, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)

                assert result is False
                assert reason == "partner_location_missing"

    def test_missing_zone_coverage_returns_fail(self, mock_db, mock_partner, mock_zone):
        """Test that missing zone coverage data returns False with reason."""
        from app.services.trigger_engine import check_partner_pin_code_match

        with patch("app.services.trigger_engine.get_partner_runtime_metadata") as mock_partner_meta:
            with patch("app.services.trigger_engine.get_zone_coverage_metadata") as mock_zone_meta:
                mock_partner_meta.return_value = {
                    "partner_id": 1,
                    "pin_code": "560034",  # Partner has pin code
                    "is_manual_offline": False,
                    "manual_offline_until": None,
                    "leave_until": None,
                    "leave_note": None,
                    "updated_at": None,
                }
                mock_zone_meta.return_value = {
                    "zone_id": 1,
                    "pin_codes": [],  # Empty coverage
                    "density_weight": None,
                    "ward_name": None,
                    "updated_at": None,
                }

                result, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)

                assert result is False
                assert reason == "coverage_data_missing"

    def test_pincode_mismatch_returns_fail(self, mock_db, mock_partner, mock_zone):
        """Test that pin code mismatch returns False."""
        from app.services.trigger_engine import check_partner_pin_code_match

        with patch("app.services.trigger_engine.get_partner_runtime_metadata") as mock_partner_meta:
            with patch("app.services.trigger_engine.get_zone_coverage_metadata") as mock_zone_meta:
                mock_partner_meta.return_value = {
                    "partner_id": 1,
                    "pin_code": "560001",  # Different pin code
                    "is_manual_offline": False,
                    "manual_offline_until": None,
                    "leave_until": None,
                    "leave_note": None,
                    "updated_at": None,
                }
                mock_zone_meta.return_value = {
                    "zone_id": 1,
                    "pin_codes": ["560034", "560095"],  # Zone coverage
                    "density_weight": 0.35,
                    "ward_name": "Koramangala",
                    "updated_at": None,
                }

                result, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)

                assert result is False
                assert reason == "pin_code_mismatch"

    def test_pincode_match_returns_pass(self, mock_db, mock_partner, mock_zone):
        """Test that matching pin code returns True."""
        from app.services.trigger_engine import check_partner_pin_code_match

        with patch("app.services.trigger_engine.get_partner_runtime_metadata") as mock_partner_meta:
            with patch("app.services.trigger_engine.get_zone_coverage_metadata") as mock_zone_meta:
                mock_partner_meta.return_value = {
                    "partner_id": 1,
                    "pin_code": "560034",  # Matching pin code
                    "is_manual_offline": False,
                    "manual_offline_until": None,
                    "leave_until": None,
                    "leave_note": None,
                    "updated_at": None,
                }
                mock_zone_meta.return_value = {
                    "zone_id": 1,
                    "pin_codes": ["560034", "560095"],  # Zone coverage includes 560034
                    "density_weight": 0.35,
                    "ward_name": "Koramangala",
                    "updated_at": None,
                }

                result, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)

                assert result is True
                assert reason == "pin_code_match"

    def test_without_db_uses_model_attributes(self, mock_partner, mock_zone):
        """Test that without db, it uses model attributes directly."""
        from app.services.trigger_engine import check_partner_pin_code_match

        # Set attributes on mock objects
        mock_partner.pin_code = "560034"
        mock_zone.pin_codes = ["560034", "560095"]

        result, reason = check_partner_pin_code_match(mock_partner, mock_zone, db=None)

        assert result is True
        assert reason == "pin_code_match"

    def test_without_db_partner_missing_pin(self, mock_partner, mock_zone):
        """Test without db when partner has no pin_code attribute."""
        from app.services.trigger_engine import check_partner_pin_code_match

        # Don't set pin_code on partner
        delattr(mock_partner, "pin_code") if hasattr(mock_partner, "pin_code") else None
        mock_zone.pin_codes = ["560034"]

        result, reason = check_partner_pin_code_match(mock_partner, mock_zone, db=None)

        assert result is False
        assert reason == "partner_location_missing"


class TestTriggerCheckEndpoint:
    """Tests for the trigger-check proof endpoint."""

    def test_trigger_check_returns_all_checks(self):
        """Test that trigger-check endpoint returns all eligibility checks."""
        # This would be an integration test with FastAPI TestClient
        # For unit testing, we verify the check structure

        expected_checks = [
            "partner_active",
            "policy_active",
            "pin_code_match",
            "shift_window",
        ]

        # Just verify the expected check names exist
        for check in expected_checks:
            assert check in expected_checks  # Placeholder for actual test

    def test_check_reasons_are_descriptive(self):
        """Test that failure reasons are descriptive."""
        valid_reasons = [
            "partner_location_missing",
            "coverage_data_missing",
            "pin_code_mismatch",
            "pin_code_match",
            "partner_inactive",
            "outside_shift_days",
            "outside_shift_window",
            "manual_offline",
            "declared_leave",
            "eligible",
        ]

        # All reasons should be snake_case and descriptive
        for reason in valid_reasons:
            assert "_" in reason or reason == "eligible"
            assert reason.islower()
````

--- FILE: backend/tests/test_platform_activity_simulation.py ---
``python
"""
test_platform_activity_simulation.py
--------------------------------------
Tests for the Platform Activity Simulation (Feature 3).

Covers:
  - get/set partner platform activity (in-memory and DB-backed)
  - evaluate_partner_platform_eligibility â€” all 5 checks
  - DB persistence via upsert_db_partner_platform_activity
  - GET/PUT /zones/partners/{partner_id}/activity endpoints
  - Claim eligibility gates on platform activity
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# In-memory platform activity (external_apis.py)
# ---------------------------------------------------------------------------

class TestGetSetPartnerPlatformActivity:

    def setup_method(self):
        """Clear in-memory store before each test."""
        from app.services.external_apis import _partner_platform_activity
        _partner_platform_activity.clear()

    def test_get_returns_default_for_new_partner(self):
        from app.services.external_apis import get_partner_platform_activity
        activity = get_partner_platform_activity(999)
        assert activity["partner_id"] == 999
        assert activity["platform_logged_in"] is True
        assert activity["active_shift"] is True
        assert activity["suspicious_inactivity"] is False
        assert activity["orders_completed_recent"] >= 1

    def test_set_updates_specified_fields(self):
        from app.services.external_apis import set_partner_platform_activity, get_partner_platform_activity
        set_partner_platform_activity(1, active_shift=False, platform_logged_in=False)
        activity = get_partner_platform_activity(1)
        assert activity["active_shift"] is False
        assert activity["platform_logged_in"] is False

    def test_set_does_not_overwrite_unspecified_fields(self):
        from app.services.external_apis import set_partner_platform_activity, get_partner_platform_activity
        # First set platform
        set_partner_platform_activity(2, platform="blinkit")
        # Then update only orders
        set_partner_platform_activity(2, orders_completed_recent=0)
        activity = get_partner_platform_activity(2)
        assert activity["platform"] == "blinkit"
        assert activity["orders_completed_recent"] == 0

    def test_source_becomes_admin_override_after_set(self):
        from app.services.external_apis import set_partner_platform_activity, get_partner_platform_activity
        set_partner_platform_activity(3, suspicious_inactivity=True)
        activity = get_partner_platform_activity(3)
        assert activity["source"] == "admin_override"

    def test_platform_field_accepts_known_platforms(self):
        from app.services.external_apis import set_partner_platform_activity, get_partner_platform_activity
        for platform in ["zomato", "swiggy", "zepto", "blinkit"]:
            set_partner_platform_activity(10, platform=platform)
            assert get_partner_platform_activity(10)["platform"] == platform

    def test_updated_at_changes_after_set(self):
        from app.services.external_apis import get_partner_platform_activity, set_partner_platform_activity
        before = get_partner_platform_activity(4)["updated_at"]
        import time; time.sleep(0.01)
        set_partner_platform_activity(4, orders_accepted_recent=20)
        after = get_partner_platform_activity(4)["updated_at"]
        assert after >= before


# ---------------------------------------------------------------------------
# evaluate_partner_platform_eligibility
# ---------------------------------------------------------------------------

class TestEvaluatePartnerPlatformEligibility:

    def setup_method(self):
        from app.services.external_apis import _partner_platform_activity
        _partner_platform_activity.clear()

    def _set_active(self, partner_id=1):
        from app.services.external_apis import set_partner_platform_activity
        set_partner_platform_activity(
            partner_id,
            platform_logged_in=True,
            active_shift=True,
            orders_completed_recent=5,
            suspicious_inactivity=False,
            last_app_ping=datetime.utcnow().isoformat(),
        )

    def _set_inactive(self, partner_id=1):
        from app.services.external_apis import set_partner_platform_activity
        set_partner_platform_activity(
            partner_id,
            platform_logged_in=False,
            active_shift=False,
            orders_completed_recent=0,
            suspicious_inactivity=True,
            last_app_ping=(datetime.utcnow() - timedelta(hours=2)).isoformat(),
        )

    def test_fully_active_partner_is_eligible(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        self._set_active(1)
        result = evaluate_partner_platform_eligibility(1)
        assert result["eligible"] is True
        assert result["score"] > 0.8

    def test_fully_inactive_partner_is_not_eligible(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        self._set_inactive(1)
        result = evaluate_partner_platform_eligibility(1)
        assert result["eligible"] is False
        assert result["score"] < 0.5

    def test_result_has_required_fields(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        result = evaluate_partner_platform_eligibility(1)
        assert "eligible" in result
        assert "score" in result
        assert "reasons" in result
        assert "activity" in result
        assert isinstance(result["reasons"], list)

    def test_five_checks_are_present(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        self._set_active(1)
        result = evaluate_partner_platform_eligibility(1)
        check_names = {r["check"] for r in result["reasons"]}
        expected = {
            "platform_logged_in", "active_shift",
            "orders_completed_recent", "suspicious_inactivity", "last_app_ping",
        }
        assert check_names == expected

    def test_not_logged_in_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, platform_logged_in=False)
        result = evaluate_partner_platform_eligibility(1)
        login_check = next(r for r in result["reasons"] if r["check"] == "platform_logged_in")
        assert login_check["pass"] is False
        assert result["eligible"] is False

    def test_not_on_shift_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, active_shift=False)
        result = evaluate_partner_platform_eligibility(1)
        shift_check = next(r for r in result["reasons"] if r["check"] == "active_shift")
        assert shift_check["pass"] is False

    def test_zero_orders_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, orders_completed_recent=0)
        result = evaluate_partner_platform_eligibility(1)
        order_check = next(r for r in result["reasons"] if r["check"] == "orders_completed_recent")
        assert order_check["pass"] is False

    def test_suspicious_inactivity_flag_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, suspicious_inactivity=True)
        result = evaluate_partner_platform_eligibility(1)
        inactivity_check = next(r for r in result["reasons"] if r["check"] == "suspicious_inactivity")
        assert inactivity_check["pass"] is False

    def test_old_ping_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        old_ping = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        set_partner_platform_activity(1, last_app_ping=old_ping)
        result = evaluate_partner_platform_eligibility(1)
        ping_check = next(r for r in result["reasons"] if r["check"] == "last_app_ping")
        assert ping_check["pass"] is False

    def test_score_between_0_and_1(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        result = evaluate_partner_platform_eligibility(1)
        assert 0.0 <= result["score"] <= 1.0

    def test_high_order_count_boosts_score(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, orders_completed_recent=20)
        result_high = evaluate_partner_platform_eligibility(1)

        self._set_active(2)
        set_partner_platform_activity(2, orders_completed_recent=1)
        result_low = evaluate_partner_platform_eligibility(2)

        # Both eligible but high-order partner has >= score
        assert result_high["score"] >= result_low["score"]


# ---------------------------------------------------------------------------
# DB-backed platform activity (claims_processor.py)
# ---------------------------------------------------------------------------

class TestDbPartnerPlatformActivity:

    def _make_db(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        return db

    def test_get_returns_defaults_when_no_row(self):
        from app.services.claims_processor import get_db_partner_platform_activity
        db = self._make_db()
        result = get_db_partner_platform_activity(1, db)
        assert result["partner_id"] == 1
        assert result["platform_logged_in"] is True
        assert result["active_shift"] is True
        assert result["suspicious_inactivity"] is False
        assert result["source"] == "default"

    def test_upsert_calls_db_execute(self):
        from app.services.claims_processor import upsert_db_partner_platform_activity
        db = self._make_db()
        # Should not raise
        upsert_db_partner_platform_activity(1, db, active_shift=False)
        assert db.execute.called
        assert db.commit.called

    def test_upsert_returns_dict_with_partner_id(self):
        from app.services.claims_processor import upsert_db_partner_platform_activity
        db = self._make_db()
        result = upsert_db_partner_platform_activity(1, db, platform="swiggy")
        assert isinstance(result, dict)
        assert result["partner_id"] == 1

    def test_get_parses_db_row_correctly(self):
        from app.services.claims_processor import get_db_partner_platform_activity
        db = MagicMock()
        now_iso = datetime.utcnow().isoformat()
        db.execute.return_value.mappings.return_value.first.return_value = {
            "partner_id": 5,
            "platform_logged_in": 0,
            "active_shift": 1,
            "orders_accepted_recent": 3,
            "orders_completed_recent": 2,
            "last_app_ping": now_iso,
            "zone_dwell_minutes": 45,
            "suspicious_inactivity": 0,
            "platform": "zepto",
            "updated_at": now_iso,
            "source": "admin_override",
        }
        result = get_db_partner_platform_activity(5, db)
        assert result["platform_logged_in"] is False   # integer 0 â†’ bool False
        assert result["active_shift"] is True           # integer 1 â†’ bool True
        assert result["platform"] == "zepto"
        assert result["source"] == "admin_override"


# ---------------------------------------------------------------------------
# Validation matrix includes platform_activity check
# ---------------------------------------------------------------------------

class TestPlatformActivityInValidationMatrix:

    def test_platform_activity_check_present_in_matrix(self):
        """build_validation_matrix must include a platform_activity check."""
        from app.services.claims_processor import build_validation_matrix
        from unittest.mock import MagicMock, patch
        from datetime import datetime, timedelta

        partner = MagicMock()
        partner.id = 1
        partner.is_active = True
        partner.shift_days = []
        partner.shift_start = None
        partner.shift_end = None

        policy = MagicMock()
        policy.id = 10
        policy.is_active = True
        policy.starts_at = datetime.utcnow() - timedelta(days=1)
        policy.expires_at = datetime.utcnow() + timedelta(days=7)

        trigger = MagicMock()
        trigger.id = 100
        trigger.zone_id = 1
        trigger.trigger_type.value = "rain"
        trigger.started_at = datetime.utcnow()

        zone = MagicMock()
        zone.id = 1
        zone.pin_codes = ["560001"]

        fraud = {"score": 0.2, "recommendation": "approve"}
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None

        with (
            patch("app.services.claims_processor.check_partner_pin_code_match",
                  return_value=(True, "pin_code_match")),
            patch("app.services.claims_processor.is_partner_available_for_trigger",
                  return_value=(True, "eligible")),
            patch("app.services.claims_processor.get_partner_runtime_metadata",
                  return_value={"is_manual_offline": False, "leave_until": None,
                                "manual_offline_until": None, "pin_code": "560001"}),
            patch("app.services.claims_processor.evaluate_partner_platform_eligibility",
                  return_value={"eligible": True, "score": 0.85,
                                "reasons": [], "activity": {"platform": "zomato"}}),
        ):
            matrix = build_validation_matrix(partner, policy, trigger, zone, fraud, db, {})

        check_names = {c["check_name"] for c in matrix}
        assert "platform_activity" in check_names

    def test_platform_ineligible_sets_check_failed(self):
        from app.services.claims_processor import build_validation_matrix
        from unittest.mock import MagicMock, patch
        from datetime import datetime, timedelta

        partner = MagicMock()
        partner.id = 1
        partner.is_active = True
        partner.shift_days = []
        partner.shift_start = None
        partner.shift_end = None

        policy = MagicMock()
        policy.id = 10
        policy.is_active = True
        policy.starts_at = datetime.utcnow() - timedelta(days=1)
        policy.expires_at = datetime.utcnow() + timedelta(days=7)

        trigger = MagicMock()
        trigger.id = 100
        trigger.zone_id = 1
        trigger.trigger_type.value = "rain"
        trigger.started_at = datetime.utcnow()

        zone = MagicMock()
        zone.id = 1
        zone.pin_codes = ["560001"]

        fraud = {"score": 0.2, "recommendation": "approve"}
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None

        with (
            patch("app.services.claims_processor.check_partner_pin_code_match",
                  return_value=(True, "pin_code_match")),
            patch("app.services.claims_processor.is_partner_available_for_trigger",
                  return_value=(True, "eligible")),
            patch("app.services.claims_processor.get_partner_runtime_metadata",
                  return_value={"is_manual_offline": False, "leave_until": None,
                                "manual_offline_until": None, "pin_code": "560001"}),
            patch("app.services.claims_processor.evaluate_partner_platform_eligibility",
                  return_value={"eligible": False, "score": 0.0,
                                "reasons": [], "activity": {"platform": "zepto"}}),
        ):
            matrix = build_validation_matrix(partner, policy, trigger, zone, fraud, db, {})

        platform_check = next(c for c in matrix if c["check_name"] == "platform_activity")
        assert platform_check["passed"] is False
        assert platform_check["confidence"] == 0.0
````

--- FILE: backend/tests/test_partial_disruption.py ---
``python
"""
Tests for partial disruption mode feature.

Tests the determine_disruption_category() function and payout calculations
with partial disruption factors.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.models.trigger_event import TriggerType
from app.services.claims_processor import (
    determine_disruption_category,
    calculate_payout_amount,
    DISRUPTION_CATEGORIES,
)


class TestDetermineDisruptionCategory:
    """Test the disruption category determination logic."""

    def test_shutdown_always_full_halt(self, mock_trigger_event, mock_policy):
        """Shutdown triggers are always full halt regardless of severity."""
        mock_trigger_event.trigger_type = TriggerType.SHUTDOWN

        for severity in range(1, 6):
            category, factor, reason = determine_disruption_category(
                TriggerType.SHUTDOWN, severity
            )
            assert category == "full_halt"
            assert factor == 1.0
            assert "shutdown_or_closure" in reason

    def test_closure_always_full_halt(self, mock_trigger_event, mock_policy):
        """Closure triggers are always full halt regardless of severity."""
        for severity in range(1, 6):
            category, factor, reason = determine_disruption_category(
                TriggerType.CLOSURE, severity
            )
            assert category == "full_halt"
            assert factor == 1.0

    def test_severity_5_full_halt(self):
        """Severity 5 weather/AQI events get full halt."""
        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=5
        )
        assert category == "full_halt"
        assert factor == 1.0
        assert "severity_5" in reason

    def test_severity_4_full_halt(self):
        """Severity 4 events also get full halt (severe enough)."""
        category, factor, reason = determine_disruption_category(
            TriggerType.HEAT, severity=4
        )
        assert category == "full_halt"
        assert factor == 1.0

    def test_severity_3_severe_reduction(self):
        """Severity 3 events get severe reduction (75%)."""
        category, factor, reason = determine_disruption_category(
            TriggerType.AQI, severity=3
        )
        assert category == "severe_reduction"
        assert factor == 0.75
        assert "severity_3" in reason

    def test_severity_2_moderate_reduction(self):
        """Severity 2 events get moderate reduction (50%)."""
        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=2
        )
        assert category == "moderate_reduction"
        assert factor == 0.50
        assert "severity_2" in reason

    def test_severity_1_minor_reduction(self):
        """Severity 1 events get minor reduction (25%)."""
        category, factor, reason = determine_disruption_category(
            TriggerType.HEAT, severity=1
        )
        assert category == "minor_reduction"
        assert factor == 0.25
        assert "severity_1" in reason

    def test_partial_factor_override(self):
        """Explicit partial_factor_override is used when provided."""
        source_data = {"partial_factor_override": 0.6}

        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=5, source_data=source_data
        )

        assert factor == 0.6
        assert "partial_factor_override" in reason

    def test_order_data_90_percent_reduction(self):
        """90%+ order reduction gets full halt."""
        source_data = {"expected_orders": 100, "actual_orders": 5}

        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=3, source_data=source_data
        )

        assert category == "full_halt"
        assert factor == 1.0
        assert "order_reduction_95%" in reason

    def test_order_data_70_percent_reduction(self):
        """70-90% order reduction gets severe reduction."""
        source_data = {"expected_orders": 100, "actual_orders": 20}

        category, factor, reason = determine_disruption_category(
            TriggerType.AQI, severity=3, source_data=source_data
        )

        assert category == "severe_reduction"
        assert factor == 0.75
        assert "order_reduction" in reason

    def test_order_data_50_percent_reduction(self):
        """40-70% order reduction gets moderate reduction."""
        source_data = {"expected_orders": 100, "actual_orders": 50}

        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=2, source_data=source_data
        )

        assert category == "moderate_reduction"
        assert factor == 0.50

    def test_order_data_25_percent_reduction(self):
        """20-40% order reduction gets minor reduction."""
        source_data = {"expected_orders": 100, "actual_orders": 70}

        category, factor, reason = determine_disruption_category(
            TriggerType.HEAT, severity=1, source_data=source_data
        )

        assert category == "minor_reduction"
        assert factor == 0.25


class TestCalculatePayoutWithPartialDisruption:
    """Test payout calculation with partial disruption factors."""

    @pytest.fixture
    def mock_trigger_severity_3(self, mock_trigger_event):
        """Trigger with severity 3 for partial testing."""
        mock_trigger_event.severity = 3
        mock_trigger_event.trigger_type = TriggerType.RAIN
        return mock_trigger_event

    def test_payout_with_moderate_reduction(self, mock_trigger_severity_3, mock_policy):
        """Payout should be reduced with partial disruption factor."""
        mock_trigger_severity_3.severity = 2  # Moderate reduction (50%)

        payout, details = calculate_payout_amount(
            mock_trigger_severity_3,
            mock_policy,
            disruption_hours=4,
        )

        # Check partial disruption is applied
        assert "partial_disruption" in details
        assert details["partial_disruption"]["category"] == "moderate_reduction"
        assert details["partial_disruption"]["factor"] == 0.50

        # Verify the factor was applied
        after_severity = details["after_severity"]
        after_partial = details["after_partial_disruption"]
        assert after_partial == pytest.approx(after_severity * 0.50, rel=0.01)

    def test_payout_with_order_data(self, mock_trigger_severity_3, mock_policy):
        """Payout calculation should use order data when provided."""
        partial_data = {"expected_orders": 20, "actual_orders": 10}  # 50% reduction

        payout, details = calculate_payout_amount(
            mock_trigger_severity_3,
            mock_policy,
            disruption_hours=4,
            partial_disruption_data=partial_data,
        )

        # Check partial disruption metadata includes order data
        pd = details["partial_disruption"]
        assert pd["expected_orders"] == 20
        assert pd["actual_orders"] == 10
        assert pd["category"] == "moderate_reduction"

    def test_full_halt_no_reduction(self, mock_trigger_event, mock_policy):
        """Full halt (severity 5) should not reduce payout."""
        mock_trigger_event.severity = 5
        mock_trigger_event.trigger_type = TriggerType.RAIN

        payout, details = calculate_payout_amount(
            mock_trigger_event,
            mock_policy,
            disruption_hours=4,
        )

        pd = details["partial_disruption"]
        assert pd["category"] == "full_halt"
        assert pd["factor"] == 1.0

        # Verify no reduction applied
        assert details["after_severity"] == details["after_partial_disruption"]


class TestDisruptionCategories:
    """Test the disruption categories configuration."""

    def test_all_categories_defined(self):
        """All expected categories should be defined."""
        expected = ["full_halt", "severe_reduction", "moderate_reduction", "minor_reduction"]
        for cat in expected:
            assert cat in DISRUPTION_CATEGORIES
            assert "factor" in DISRUPTION_CATEGORIES[cat]
            assert "description" in DISRUPTION_CATEGORIES[cat]

    def test_factors_in_valid_range(self):
        """All factors should be between 0 and 1."""
        for cat, config in DISRUPTION_CATEGORIES.items():
            assert 0 <= config["factor"] <= 1.0

    def test_full_halt_is_100_percent(self):
        """Full halt should be 100% payout."""
        assert DISRUPTION_CATEGORIES["full_halt"]["factor"] == 1.0

    def test_factors_decrease_with_severity(self):
        """Factors should decrease: full > severe > moderate > minor."""
        assert DISRUPTION_CATEGORIES["full_halt"]["factor"] > DISRUPTION_CATEGORIES["severe_reduction"]["factor"]
        assert DISRUPTION_CATEGORIES["severe_reduction"]["factor"] > DISRUPTION_CATEGORIES["moderate_reduction"]["factor"]
        assert DISRUPTION_CATEGORIES["moderate_reduction"]["factor"] > DISRUPTION_CATEGORIES["minor_reduction"]["factor"]
````

--- FILE: backend/tests/test_multi_trigger_resolver.py ---
``python
"""
Tests for multi-trigger resolver feature.

Tests trigger aggregation within 6-hour windows, payout calculation
with highest-wins strategy, and severe disruption uplift.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.models.trigger_event import TriggerType
from app.models.claim import ClaimStatus
from app.services.multi_trigger_resolver import (
    generate_aggregation_group_id,
    find_triggers_in_window,
    calculate_aggregation_window,
    should_apply_severe_disruption_uplift,
    calculate_aggregated_payout,
    check_and_resolve_aggregation,
    AGGREGATION_WINDOW_HOURS,
    SEVERE_DISRUPTION_UPLIFT_PERCENT,
)


class TestAggregationGroupId:
    """Test aggregation group ID generation."""

    def test_generate_unique_ids(self):
        """Each call should generate a unique ID."""
        ids = [generate_aggregation_group_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_id_format(self):
        """IDs should follow the AGG- prefix format."""
        group_id = generate_aggregation_group_id()
        assert group_id.startswith("AGG-")
        assert len(group_id) == 16  # AGG- + 12 hex chars


class TestAggregationWindow:
    """Test aggregation window calculation."""

    def test_window_is_6_hours(self):
        """Window should be 6 hours total (3 before, 3 after)."""
        trigger_time = datetime(2024, 1, 15, 12, 0, 0)
        window_start, window_end = calculate_aggregation_window(trigger_time)

        duration = (window_end - window_start).total_seconds() / 3600
        assert duration == AGGREGATION_WINDOW_HOURS

    def test_window_centered_on_trigger(self):
        """Window should be centered on trigger time."""
        trigger_time = datetime(2024, 1, 15, 12, 0, 0)
        window_start, window_end = calculate_aggregation_window(trigger_time)

        # Trigger should be in the middle
        assert window_start == trigger_time - timedelta(hours=3)
        assert window_end == trigger_time + timedelta(hours=3)


class TestSevereDisruptionUplift:
    """Test severe disruption uplift determination."""

    def test_uplift_with_3_trigger_types(self):
        """Uplift should apply with 3+ distinct trigger types."""
        triggers = [
            MagicMock(trigger_type=TriggerType.RAIN),
            MagicMock(trigger_type=TriggerType.AQI),
            MagicMock(trigger_type=TriggerType.SHUTDOWN),
        ]
        assert should_apply_severe_disruption_uplift(triggers) is True

    def test_no_uplift_with_2_trigger_types(self):
        """Uplift should not apply with only 2 trigger types."""
        triggers = [
            MagicMock(trigger_type=TriggerType.RAIN),
            MagicMock(trigger_type=TriggerType.AQI),
        ]
        assert should_apply_severe_disruption_uplift(triggers) is False

    def test_no_uplift_with_1_trigger_type(self):
        """Uplift should not apply with single trigger."""
        triggers = [MagicMock(trigger_type=TriggerType.RAIN)]
        assert should_apply_severe_disruption_uplift(triggers) is False

    def test_no_uplift_with_duplicates(self):
        """Multiple triggers of same type don't count as different types."""
        triggers = [
            MagicMock(trigger_type=TriggerType.RAIN),
            MagicMock(trigger_type=TriggerType.RAIN),
            MagicMock(trigger_type=TriggerType.RAIN),
        ]
        assert should_apply_severe_disruption_uplift(triggers) is False


class TestCalculateAggregatedPayout:
    """Test aggregated payout calculation."""

    @pytest.fixture
    def triggers_with_payouts(self):
        """Create triggers with known payouts."""
        triggers = [
            MagicMock(id=1, trigger_type=TriggerType.RAIN, severity=4, started_at=datetime.utcnow()),
            MagicMock(id=2, trigger_type=TriggerType.AQI, severity=3, started_at=datetime.utcnow()),
            MagicMock(id=3, trigger_type=TriggerType.HEAT, severity=2, started_at=datetime.utcnow()),
        ]
        payouts = {1: 300.0, 2: 250.0, 3: 150.0}
        return triggers, payouts

    def test_highest_payout_wins(self, triggers_with_payouts, mock_policy):
        """The trigger with highest payout should be primary."""
        triggers, payouts = triggers_with_payouts
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert meta["primary_trigger_id"] == 1  # Highest payout (300)
        assert 2 in meta["suppressed_triggers"]
        assert 3 in meta["suppressed_triggers"]

    def test_uplift_applied_for_severe_disruption(self, triggers_with_payouts, mock_policy):
        """10% uplift should be applied when 3+ trigger types."""
        triggers, payouts = triggers_with_payouts
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert meta["uplift_applied"] is True
        assert meta["uplift_percent"] == SEVERE_DISRUPTION_UPLIFT_PERCENT
        assert meta["uplift_amount"] == 30.0  # 10% of 300

        # Final payout includes uplift
        expected = 300.0 * 1.10  # 330
        assert final_payout == pytest.approx(expected, rel=0.01)

    def test_no_uplift_for_2_triggers(self, mock_policy):
        """No uplift with only 2 trigger types."""
        triggers = [
            MagicMock(id=1, trigger_type=TriggerType.RAIN, severity=4, started_at=datetime.utcnow()),
            MagicMock(id=2, trigger_type=TriggerType.AQI, severity=3, started_at=datetime.utcnow()),
        ]
        payouts = {1: 300.0, 2: 250.0}
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert meta["uplift_applied"] is False
        assert meta["uplift_percent"] == 0.0
        assert final_payout == 300.0  # No uplift

    def test_savings_calculated_correctly(self, triggers_with_payouts, mock_policy):
        """Savings should be difference between pre and post aggregation."""
        triggers, payouts = triggers_with_payouts
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        pre_aggregation = sum(payouts.values())  # 700
        assert meta["pre_aggregation_payout"] == pre_aggregation
        assert meta["savings"] == pre_aggregation - final_payout

    def test_daily_limit_applied(self, mock_policy):
        """Daily limit should cap the final payout."""
        triggers = [
            MagicMock(id=1, trigger_type=TriggerType.RAIN, severity=5, started_at=datetime.utcnow()),
        ]
        payouts = {1: 500.0}
        mock_policy.max_daily_payout = 400.0  # Limit below payout

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert final_payout == 400.0  # Capped at daily limit

    def test_metadata_includes_trigger_details(self, triggers_with_payouts, mock_policy):
        """Metadata should include details of all triggers in window."""
        triggers, payouts = triggers_with_payouts
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert len(meta["triggers_in_window"]) == 3
        for tw in meta["triggers_in_window"]:
            assert "id" in tw
            assert "type" in tw
            assert "severity" in tw
            assert "payout" in tw


class TestCheckAndResolveAggregation:
    """Test the main aggregation check function."""

    @pytest.fixture
    def mock_trigger(self):
        """Create a mock trigger event."""
        trigger = MagicMock()
        trigger.id = 1
        trigger.zone_id = 1
        trigger.trigger_type = TriggerType.RAIN
        trigger.severity = 4
        trigger.started_at = datetime.utcnow()
        return trigger

    def test_first_trigger_creates_new_claim(self, mock_trigger, mock_policy, mock_db):
        """First trigger in window should allow new claim creation."""
        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.first.return_value = None

        should_create, existing, meta = check_and_resolve_aggregation(
            mock_trigger, mock_policy, 300.0, mock_db
        )

        assert should_create is True
        assert existing is None
        assert meta["is_aggregated"] is False
        assert meta["primary_trigger_id"] == mock_trigger.id

    def test_subsequent_trigger_aggregates(self, mock_trigger, mock_policy, mock_db, mock_claim):
        """Subsequent trigger in window should aggregate with existing claim."""
        # Setup existing claim
        mock_claim.validation_data = json.dumps({
            "aggregation": {
                "group_id": "AGG-TEST123",
                "is_aggregated": False,
                "primary_trigger_id": 0,
                "triggers_in_window": [{"id": 0, "payout": 200.0}]
            }
        })
        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.first.return_value = mock_claim

        # Mock finding triggers in window
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            MagicMock(id=0, trigger_type=TriggerType.AQI, severity=3, started_at=datetime.utcnow()),
            mock_trigger,
        ]

        should_create, existing, meta = check_and_resolve_aggregation(
            mock_trigger, mock_policy, 300.0, mock_db
        )

        # Should NOT create new claim when aggregating
        assert should_create is False
        assert existing is not None
        assert meta["is_aggregated"] is True


class TestAggregationStats:
    """Test aggregation statistics."""

    def test_metadata_structure(self):
        """Aggregation metadata should have all required fields."""
        triggers = [
            MagicMock(id=1, trigger_type=TriggerType.RAIN, severity=4, started_at=datetime.utcnow()),
        ]
        payouts = {1: 300.0}
        policy = MagicMock(max_daily_payout=1000.0)

        final_payout, meta = calculate_aggregated_payout(triggers, policy, payouts)

        required_fields = [
            "group_id", "is_aggregated", "primary_trigger_id",
            "suppressed_triggers", "pre_aggregation_payout",
            "post_aggregation_payout", "savings", "uplift_applied",
            "uplift_percent", "uplift_amount", "triggers_in_window",
            "window_hours", "aggregated_at"
        ]
        for field in required_fields:
            assert field in meta, f"Missing field: {field}"
````

--- FILE: backend/tests/test_riqi_provenance.py ---
``python
"""
Tests for RIQI (Road Infrastructure Quality Index) provenance system.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestRiqiProvenance:
    """Tests for RIQI data provenance tracking."""

    @pytest.fixture
    def mock_zone_risk_profile(self):
        """Create a mock zone risk profile."""
        profile = MagicMock()
        profile.id = 1
        profile.zone_id = 1
        profile.riqi_score = 65.0
        profile.riqi_band = "urban_fringe"
        profile.historical_suspensions = 2
        profile.closure_frequency = 0.8
        profile.weather_severity_freq = 1.2
        profile.aqi_severity_freq = 0.5
        profile.zone_density = 75.0
        profile.calculated_from = "seeded"
        profile.last_updated_at = datetime.utcnow()
        return profile

    def test_riqi_reads_from_db_first(self, mock_db, mock_zone, mock_zone_risk_profile):
        """Test that RIQI service reads from database first."""
        from app.services.riqi_service import get_riqi_for_zone

        # Mock the ensure table call
        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,  # Zone lookup
                mock_zone_risk_profile,  # Profile lookup
            ]

            result = get_riqi_for_zone(1, mock_db)

            assert result.riqi_score == 65.0
            assert result.calculated_from == "seeded"
            assert result.zone_code == mock_zone.code

    def test_riqi_falls_back_to_city_default(self, mock_db, mock_zone):
        """Test that RIQI falls back to city default when no DB profile."""
        from app.services.riqi_service import get_riqi_for_zone
        from app.services.premium_service import CITY_RIQI_SCORES

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,  # Zone lookup
                None,  # No profile in DB
            ]

            result = get_riqi_for_zone(1, mock_db)

            # Should use city default for Bangalore
            expected_score = CITY_RIQI_SCORES.get(mock_zone.city.lower(), 55.0)
            assert result.riqi_score == expected_score
            assert result.calculated_from == "fallback_city_default"

    def test_riqi_provenance_includes_source(self, mock_db, mock_zone, mock_zone_risk_profile):
        """Test that RIQI response includes calculated_from field."""
        from app.services.riqi_service import get_riqi_for_zone

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,
                mock_zone_risk_profile,
            ]

            result = get_riqi_for_zone(1, mock_db)

            assert hasattr(result, "calculated_from")
            assert result.calculated_from in ["seeded", "computed", "manual", "fallback_city_default"]

    def test_riqi_endpoint_returns_all_zones(self, mock_db, mock_zone):
        """Test that get_all_riqi_profiles returns data for all zones."""
        from app.services.riqi_service import get_all_riqi_profiles
        from app.schemas.riqi import RiqiProvenanceResponse, RiqiInputMetrics

        # Create multiple mock zones
        zone1 = MagicMock()
        zone1.id = 1
        zone1.code = "BLR-047"
        zone1.name = "Koramangala"
        zone1.city = "Bangalore"

        zone2 = MagicMock()
        zone2.id = 2
        zone2.code = "BLR-048"
        zone2.name = "Indiranagar"
        zone2.city = "Bangalore"

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            with patch("app.services.riqi_service.get_riqi_for_zone") as mock_get:
                # Return proper Pydantic models
                mock_response1 = RiqiProvenanceResponse(
                    zone_id=1,
                    zone_code="BLR-047",
                    zone_name="Koramangala",
                    city="Bangalore",
                    riqi_score=65.0,
                    riqi_band="urban_fringe",
                    payout_multiplier=1.25,
                    premium_adjustment=1.15,
                    input_metrics=RiqiInputMetrics(
                        historical_suspensions=0,
                        closure_frequency=1.0,
                        weather_severity_freq=1.0,
                        aqi_severity_freq=1.0,
                        zone_density=50.0,
                    ),
                    calculated_from="seeded",
                )

                mock_response2 = RiqiProvenanceResponse(
                    zone_id=2,
                    zone_code="BLR-048",
                    zone_name="Indiranagar",
                    city="Bangalore",
                    riqi_score=62.0,
                    riqi_band="urban_fringe",
                    payout_multiplier=1.25,
                    premium_adjustment=1.15,
                    input_metrics=RiqiInputMetrics(
                        historical_suspensions=0,
                        closure_frequency=1.0,
                        weather_severity_freq=1.0,
                        aqi_severity_freq=1.0,
                        zone_density=50.0,
                    ),
                    calculated_from="fallback_city_default",
                )

                mock_get.side_effect = [mock_response1, mock_response2]
                mock_db.query.return_value.order_by.return_value.all.return_value = [zone1, zone2]

                result = get_all_riqi_profiles(mock_db)

                assert result.total == 2
                assert len(result.zones) == 2
                assert result.data_source in ["database", "mixed"]

    def test_riqi_zone_endpoint_returns_metrics(self, mock_db, mock_zone, mock_zone_risk_profile):
        """Test that zone RIQI endpoint returns input metrics."""
        from app.services.riqi_service import get_riqi_for_zone

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,
                mock_zone_risk_profile,
            ]

            result = get_riqi_for_zone(1, mock_db)

            # Check input metrics are present
            assert hasattr(result, "input_metrics")
            metrics = result.input_metrics
            assert hasattr(metrics, "historical_suspensions")
            assert hasattr(metrics, "closure_frequency")
            assert hasattr(metrics, "weather_severity_freq")
            assert hasattr(metrics, "aqi_severity_freq")
            assert hasattr(metrics, "zone_density")

    def test_riqi_band_calculation(self):
        """Test RIQI band calculation from score."""
        from app.services.premium_service import get_riqi_band

        # urban_core: > 70
        assert get_riqi_band(75.0) == "urban_core"
        assert get_riqi_band(100.0) == "urban_core"

        # urban_fringe: 40-70
        assert get_riqi_band(70.0) == "urban_fringe"
        assert get_riqi_band(55.0) == "urban_fringe"
        assert get_riqi_band(40.0) == "urban_fringe"

        # peri_urban: < 40
        assert get_riqi_band(39.9) == "peri_urban"
        assert get_riqi_band(0.0) == "peri_urban"

    def test_riqi_payout_multipliers(self):
        """Test that RIQI bands have correct payout multipliers."""
        from app.services.premium_service import RIQI_PAYOUT_MULTIPLIER

        assert RIQI_PAYOUT_MULTIPLIER["urban_core"] == 1.00
        assert RIQI_PAYOUT_MULTIPLIER["urban_fringe"] == 1.25
        assert RIQI_PAYOUT_MULTIPLIER["peri_urban"] == 1.50

    def test_riqi_premium_adjustments(self):
        """Test that RIQI bands have correct premium adjustments."""
        from app.services.premium_service import RIQI_PREMIUM_ADJUSTMENT

        assert RIQI_PREMIUM_ADJUSTMENT["urban_core"] == 1.00
        assert RIQI_PREMIUM_ADJUSTMENT["urban_fringe"] == 1.15
        assert RIQI_PREMIUM_ADJUSTMENT["peri_urban"] == 1.30

    def test_seed_zone_risk_profiles(self, mock_db, mock_zone):
        """Test seeding zone risk profiles."""
        from app.services.riqi_service import seed_zone_risk_profiles

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.all.return_value = [mock_zone]
            mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing profile

            created = seed_zone_risk_profiles(mock_db)

            assert mock_db.add.called
            assert mock_db.commit.called

    def test_recompute_riqi_updates_profile(self, mock_db, mock_zone, mock_zone_risk_profile):
        """Test that recompute updates the profile in DB."""
        from app.services.riqi_service import recompute_riqi_for_zone

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,
                mock_zone_risk_profile,
            ]

            result = recompute_riqi_for_zone("BLR-047", mock_db)

            assert result is not None
            assert result.zone_code == "BLR-047"
            assert hasattr(result, "old_riqi_score")
            assert hasattr(result, "new_riqi_score")
            assert mock_zone_risk_profile.calculated_from == "computed"
````

--- FILE: backend/tests/test_partner_experience.py ---
``python
"""
tests/test_partner_experience.py

Backend tests for Member 1 â€“ Partner Experience Slice.

Run with:  pytest backend/tests/test_partner_experience.py -v

Tests:
  - experience-state returns null-safe payloads
  - eligibility locks correct tiers
  - zone-history returns real data and empty state
  - renewal-preview returns correct breakdown structure
  - new paid claim appears after simulated drill (integration-style)
"""

import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.partner import Partner, Platform, Language
from app.models.policy import Policy, PolicyTier, PolicyStatus
from app.models.claim import Claim, ClaimStatus
from app.models.zone import Zone
from app.models.trigger_event import TriggerEvent, TriggerType
from app.services.auth import create_access_token

# â”€â”€ SQLite in-memory test DB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

TEST_DB_URL = "sqlite:///./test_experience.db"

engine         = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSession()
    yield session
    session.close()


@pytest.fixture()
def client():
    return TestClient(app)


# â”€â”€ Factory helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def make_zone(db, name="Test Zone", code="TST-001", city="bangalore"):
    zone = Zone(code=code, name=name, city=city, risk_score=50.0)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def make_partner(db, zone_id=None, phone="9999900001"):
    partner = Partner(
        phone=phone,
        name="Test Partner",
        platform=Platform.ZEPTO,
        partner_id="ZPT123456",
        zone_id=zone_id,
        language_pref=Language.ENGLISH,
        zone_history=[],
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def make_policy(db, partner_id, tier=PolicyTier.STANDARD, is_active=True, days_ago=0):
    now = datetime.utcnow() - timedelta(days=days_ago)
    policy = Policy(
        partner_id=partner_id,
        tier=tier,
        weekly_premium=33.0,
        max_daily_payout=400.0,
        max_days_per_week=3,
        starts_at=now,
        expires_at=now + timedelta(days=7),
        is_active=is_active,
        auto_renew=True,
        status=PolicyStatus.ACTIVE,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def make_claim(db, policy_id, amount=400.0, status=ClaimStatus.PAID, trigger_id=1):
    claim = Claim(
        policy_id=policy_id,
        trigger_event_id=trigger_id,
        amount=amount,
        status=status,
        fraud_score=0.1,
        upi_ref="RAPID001002001234",
        paid_at=datetime.utcnow() if status == ClaimStatus.PAID else None,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def make_trigger(db, zone_id, trigger_type=TriggerType.RAIN, severity=4, hours_ago=1):
    trigger = TriggerEvent(
        zone_id=zone_id,
        trigger_type=trigger_type,
        severity=severity,
        started_at=datetime.utcnow() - timedelta(hours=hours_ago),
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    return trigger


def auth_token(partner_id: int) -> str:
    return create_access_token(data={"sub": str(partner_id)})


def auth_header(partner_id: int) -> dict:
    return {"Authorization": f"Bearer {auth_token(partner_id)}"}


# â”€â”€ Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestExperienceState:
    """GET /partners/me/experience-state"""

    def test_returns_null_safe_payload_no_policy_no_trigger(self, client, db):
        """Endpoint must return without error even when partner has no policy / trigger."""
        zone    = make_zone(db, code="TST-100")
        partner = make_partner(db, zone_id=zone.id, phone="9000000100")
        res     = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["zone_alert"]        is None   # no trigger â†’ null
        assert data["zone_reassignment"] is None   # no history â†’ null
        assert data["latest_payout"]     is None   # no claims â†’ null
        assert "loyalty"           in data
        assert "premium_breakdown" in data
        assert "fetched_at"        in data

    def test_zone_alert_present_when_trigger_fired(self, client, db):
        """zone_alert must be non-null when a trigger fired within 6 hours."""
        zone    = make_zone(db, code="TST-101")
        partner = make_partner(db, zone_id=zone.id, phone="9000000101")
        _       = make_trigger(db, zone.id, hours_ago=2)

        res  = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["zone_alert"] is not None
        assert "type"     in data["zone_alert"]
        assert "message"  in data["zone_alert"]
        assert "severity" in data["zone_alert"]

    def test_zone_alert_null_when_trigger_too_old(self, client, db):
        """zone_alert must be null when the last trigger is older than 6 hours."""
        zone    = make_zone(db, code="TST-102")
        partner = make_partner(db, zone_id=zone.id, phone="9000000102")
        _       = make_trigger(db, zone.id, hours_ago=10)

        res  = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["zone_alert"] is None

    def test_latest_payout_populated_after_paid_claim(self, client, db):
        """latest_payout must be non-null and contain amount/upi_ref after a paid claim."""
        zone    = make_zone(db, code="TST-103")
        partner = make_partner(db, zone_id=zone.id, phone="9000000103")
        policy  = make_policy(db, partner.id)
        trigger = make_trigger(db, zone.id)
        claim   = make_claim(db, policy.id, amount=400.0, status=ClaimStatus.PAID, trigger_id=trigger.id)

        res  = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        data = res.json()
        lp   = data["latest_payout"]
        assert lp is not None
        assert lp["status"]  == "paid"
        assert lp["amount"]  == 400.0
        assert lp["claim_id"] == claim.id


class TestEligibility:
    """GET /partners/me/eligibility"""

    def test_gate_blocked_when_no_active_days(self, client, db):
        """Partner with zero activity must be fully blocked."""
        zone    = make_zone(db, code="ELG-001")
        partner = make_partner(db, zone_id=zone.id, phone="9100000001")
        res     = client.get(
            "/api/v1/partners/me/eligibility",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["gate_blocked"] is True
        assert data["allowed_tiers"] == []
        assert set(data["blocked_tiers"]) == {"flex", "standard", "pro"}

    def test_only_flex_allowed_when_low_activity(self, client, db):
        """Partner with <AUTO_DOWNGRADE_DAYS active days should only get flex."""
        # AUTO_DOWNGRADE_DAYS = 5 from premium_service.py
        # Create 3 paid claims (distinct days) to simulate 3 active days
        zone    = make_zone(db, code="ELG-002")
        partner = make_partner(db, zone_id=zone.id, phone="9100000002")
        policy  = make_policy(db, partner.id)
        trigger = make_trigger(db, zone.id)

        for i in range(3):
            claim = make_claim(
                db, policy.id,
                amount=250.0,
                status=ClaimStatus.PAID,
                trigger_id=trigger.id,
            )
            # Manually set created_at to simulate distinct days (SQLite stores as string)
            claim.created_at = datetime.utcnow() - timedelta(days=i)
            db.commit()

        res  = client.get(
            "/api/v1/partners/me/eligibility",
            headers=auth_header(partner.id),
        )
        data = res.json()
        # With MIN_ACTIVE_DAYS=7 gate, 3 days is below gate â†’ fully blocked
        assert data["gate_blocked"] is True

    def test_all_tiers_allowed_with_sufficient_activity(self, client, db):
        """Partner with â‰¥7 active days (proxied via policies) gets all tiers."""
        zone    = make_zone(db, code="ELG-003")
        partner = make_partner(db, zone_id=zone.id, phone="9100000003")

        # Create 2 policies (14 proxy days) to exceed MIN_ACTIVE_DAYS_TO_BUY=7
        for i in range(2):
            make_policy(db, partner.id, days_ago=i * 7)

        res  = client.get(
            "/api/v1/partners/me/eligibility",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["gate_blocked"] is False
        assert set(data["allowed_tiers"]) == {"flex", "standard", "pro"}
        assert data["blocked_tiers"] == []


class TestZoneHistory:
    """GET /partners/me/zone-history"""

    def test_empty_state_when_no_history(self, client, db):
        """Must return has_history=False and empty list, not a 404 or error."""
        zone    = make_zone(db, code="ZH-001")
        partner = make_partner(db, zone_id=zone.id, phone="9200000001")
        res     = client.get(
            "/api/v1/partners/me/zone-history",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["has_history"] is False
        assert data["history"]     == []
        assert data["total"]       == 0

    def test_history_enriched_with_zone_names(self, client, db):
        """History entries must include zone name (not just ID) when zone exists."""
        zone1   = make_zone(db, code="ZH-002", name="Koramangala North")
        zone2   = make_zone(db, code="ZH-003", name="Whitefield South")
        partner = make_partner(db, zone_id=zone2.id, phone="9200000002")

        # Inject zone_history directly
        partner.zone_history = [{
            "old_zone_id":      zone1.id,
            "new_zone_id":      zone2.id,
            "effective_at":     datetime.utcnow().isoformat(),
            "premium_adjustment": -2.5,
            "new_weekly_premium": 35.5,
            "days_remaining":   4,
            "policy_id":        None,
        }]
        db.commit()

        res  = client.get(
            "/api/v1/partners/me/zone-history",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["has_history"] is True
        entry = data["history"][0]
        assert entry["old_zone_name"] == "Koramangala North"
        assert entry["new_zone_name"] == "Whitefield South"
        assert entry["old_zone_code"] == "ZH-002"
        assert entry["new_zone_code"] == "ZH-003"


class TestRenewalPreview:
    """GET /partners/me/renewal-preview"""

    def test_no_policy_returns_has_policy_false(self, client, db):
        zone    = make_zone(db, code="RP-001")
        partner = make_partner(db, zone_id=zone.id, phone="9300000001")
        res     = client.get(
            "/api/v1/partners/me/renewal-preview",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["has_policy"] is False

    def test_with_policy_returns_breakdown(self, client, db):
        """Must return full breakdown structure with correct keys."""
        zone    = make_zone(db, code="RP-002")
        partner = make_partner(db, zone_id=zone.id, phone="9300000002")
        _       = make_policy(db, partner.id)
        res     = client.get(
            "/api/v1/partners/me/renewal-preview",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["has_policy"]        is True
        assert data["renewal_available"] is True
        assert "renewal_premium"         in data
        assert "breakdown"               in data
        bd = data["breakdown"]
        for key in ("base", "zone_risk", "seasonal_index", "riqi_adjustment", "total"):
            assert key in bd, f"Missing breakdown key: {key}"
        assert data["renewal_premium"]   > 0


class TestPremiumBreakdown:
    """GET /partners/me/premium-breakdown"""

    def test_returns_itemised_factors(self, client, db):
        zone    = make_zone(db, code="PB-001")
        partner = make_partner(db, zone_id=zone.id, phone="9400000001")
        _       = make_policy(db, partner.id)
        res     = client.get(
            "/api/v1/partners/me/premium-breakdown",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        for key in ("base", "zone_risk", "seasonal_index", "riqi_adjustment",
                    "loyalty_discount", "total", "city", "riqi_band"):
            assert key in data, f"Missing key: {key}"
        assert data["total"] > 0
        assert data["base"]  > 0

    def test_no_hardcoded_fallback_values(self, client, db):
        """Total must differ from raw base when zone risk / seasonal / RIQI apply."""
        zone         = make_zone(db, code="PB-002", city="mumbai")  # riqi 45 â†’ fringe
        zone.risk_score = 70  # above midpoint â†’ zone_risk > 1
        db.commit()
        partner = make_partner(db, zone_id=zone.id, phone="9400000002")
        _       = make_policy(db, partner.id)
        res  = client.get(
            "/api/v1/partners/me/premium-breakdown",
            headers=auth_header(partner.id),
        )
        data = res.json()
        # For Mumbai fringe + risk 70: total should be > base
        assert data["total"] >= data["base"]


class TestDrillSimulation:
    """
    Integration-style test: simulate admin drill, verify paid claim
    surfaces in experience-state without manual refresh.
    """

    def test_paid_claim_surfaces_in_experience_state(self, client, db):
        """
        After a claim is paid:
          - experience-state.latest_payout.status == "paid"
          - amount and upi_ref are present
        """
        zone    = make_zone(db, code="DRL-001")
        partner = make_partner(db, zone_id=zone.id, phone="9500000001")
        policy  = make_policy(db, partner.id)
        trigger = make_trigger(db, zone.id, hours_ago=0)

        # Simulate drill: create a paid claim directly
        claim = Claim(
            policy_id         = policy.id,
            trigger_event_id  = trigger.id,
            amount            = 400.0,
            status            = ClaimStatus.PAID,
            fraud_score       = 0.05,
            upi_ref           = "RAPID_DRILL_TEST_001",
            paid_at           = datetime.utcnow(),
            validation_data   = json.dumps({"auto_payout": True}),
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)

        # Now check experience-state â€” must reflect the paid claim
        res  = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        lp   = data["latest_payout"]
        assert lp             is not None
        assert lp["status"]   == "paid"
        assert lp["amount"]   == 400.0
        assert lp["upi_ref"]  == "RAPID_DRILL_TEST_001"
        assert lp["claim_id"] == claim.id

        # Zone alert should also be active (trigger < 6 hours ago)
        assert data["zone_alert"] is not None
````

--- FILE: backend/tests/test_phase2_tasks.py ---
``python
"""
Phase 2 Task Verification Tests
================================
Tests all 22 tasks from Person 1 and Person 2 task lists.

Run with: python tests/test_phase2_tasks.py
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# PERSON 1 TESTS - Pricing + Premium Engine + ML Wrapper
# ============================================================================

class TestPerson1Tasks:
    """Tests for Person 1: Backend Pricing + Premium Engine + ML Wrapper"""

    # -------------------------------------------------------------------------
    # Task 1: Fix pricing tiers to Rs.22/Rs.33/Rs.45
    # -------------------------------------------------------------------------
    def test_task1_pricing_tiers_premium_service(self):
        """Verify TIER_CONFIG has correct prices in premium_service.py"""
        from app.services.premium_service import TIER_CONFIG

        assert TIER_CONFIG["flex"]["weekly_premium"] == 22, "Flex should be Rs.22"
        assert TIER_CONFIG["standard"]["weekly_premium"] == 33, "Standard should be Rs.33"
        assert TIER_CONFIG["pro"]["weekly_premium"] == 45, "Pro should be Rs.45"
        print("[PASS] Task 1: Pricing tiers Rs.22/33/45")

    def test_task1_pricing_tiers_ml_service(self):
        """Verify BASE_PRICES in ml_service.py matches"""
        from app.services.ml_service import PremiumModel

        model = PremiumModel()
        assert model.BASE_PRICES["flex"] == 22
        assert model.BASE_PRICES["standard"] == 33
        assert model.BASE_PRICES["pro"] == 45
        print("[PASS] Task 1b: ML Service pricing tiers")

    # -------------------------------------------------------------------------
    # Task 2: Full premium formula implementation
    # -------------------------------------------------------------------------
    def test_task2_premium_formula_components(self):
        """Verify full premium formula has all required components"""
        from app.services.ml_service import PremiumModel, PartnerFeatures

        model = PremiumModel()

        # Check all required components exist
        assert hasattr(model, 'CITY_PERIL'), "Missing city_peril_multiplier"
        assert hasattr(model, 'SEASONAL_INDEX'), "Missing seasonal_index"
        assert hasattr(model, 'ACTIVITY_TIER_FACTOR'), "Missing activity_tier_factor"
        assert hasattr(model, 'RIQI_ADJUSTMENT'), "Missing RIQI_adjustment"
        assert hasattr(model, 'CAP_MULTIPLIER'), "Missing cap (3x)"
        assert model.CAP_MULTIPLIER == 3.0, "Cap should be 3x base tier"

        # Test formula execution
        features = PartnerFeatures(
            partner_id=1,
            city="bangalore",
            zone_risk_score=50.0,
            active_days_last_30=15,
            avg_hours_per_day=8.0,
            tier="standard",
            loyalty_weeks=0,
            month=7,  # Monsoon month
            riqi_score=55.0,
        )
        result = model.predict(features)

        assert "weekly_premium" in result
        assert "breakdown" in result
        assert result["breakdown"]["city_peril_multiplier"] > 0
        assert result["breakdown"]["seasonal_index"] >= 1.0
        assert result["breakdown"]["activity_tier_factor"] > 0
        assert result["breakdown"]["riqi_adjustment"] > 0
        assert result["breakdown"]["loyalty_discount"] <= 1.0
        print("[PASS] Task 2: Full premium formula")

    # -------------------------------------------------------------------------
    # Task 3: City-specific seasonal multiplier table
    # -------------------------------------------------------------------------
    def test_task3_seasonal_multipliers(self):
        """Verify city-specific seasonal multipliers match spec"""
        from app.services.ml_service import PremiumModel

        model = PremiumModel()
        seasonal = model.SEASONAL_INDEX

        # Bangalore: Jun-Sep +20%
        assert all(seasonal["bangalore"].get(m, 1.0) == 1.20 for m in [6, 7, 8, 9]), \
            "Bangalore should be +20% Jun-Sep"

        # Mumbai: Jul-Sep +25%
        assert all(seasonal["mumbai"].get(m, 1.0) == 1.25 for m in [7, 8, 9]), \
            "Mumbai should be +25% Jul-Sep"

        # Delhi: Oct-Jan +18%
        assert all(seasonal["delhi"].get(m, 1.0) == 1.18 for m in [10, 11, 12, 1]), \
            "Delhi should be +18% Oct-Jan"

        # Chennai: Oct-Dec +22%
        assert all(seasonal["chennai"].get(m, 1.0) == 1.22 for m in [10, 11, 12]), \
            "Chennai should be +22% Oct-Dec"

        # Hyderabad: Jul-Sep +15%
        assert all(seasonal["hyderabad"].get(m, 1.0) == 1.15 for m in [7, 8, 9]), \
            "Hyderabad should be +15% Jul-Sep"

        # Kolkata: Jun-Sep +20%
        assert all(seasonal["kolkata"].get(m, 1.0) == 1.20 for m in [6, 7, 8, 9]), \
            "Kolkata should be +20% Jun-Sep"

        print("[PASS] Task 3: City-specific seasonal multipliers")

    # -------------------------------------------------------------------------
    # Task 4: RIQI zone scoring - derive, store, expose via API
    # -------------------------------------------------------------------------
    def test_task4_riqi_scoring(self):
        """Verify RIQI scoring functions exist and work"""
        from app.services.premium_service import (
            get_riqi_score,
            get_riqi_band,
            get_riqi_payout_multiplier,
            CITY_RIQI_SCORES,
        )

        # Check cities have RIQI scores
        assert "bangalore" in CITY_RIQI_SCORES
        assert "mumbai" in CITY_RIQI_SCORES
        assert "delhi" in CITY_RIQI_SCORES

        # Test functions
        score = get_riqi_score("bangalore")
        assert 0 <= score <= 100, "RIQI score should be 0-100"

        band = get_riqi_band(score)
        assert band in ["urban_core", "urban_fringe", "peri_urban"]

        multiplier = get_riqi_payout_multiplier("bangalore")
        assert multiplier in [1.0, 1.25, 1.5]

        print("[PASS] Task 4: RIQI zone scoring")

    # -------------------------------------------------------------------------
    # Task 5: RIQI multiplier to payout (1.0/1.25/1.5)
    # -------------------------------------------------------------------------
    def test_task5_riqi_multipliers(self):
        """Verify RIQI payout multipliers are 1.0/1.25/1.5"""
        from app.services.premium_service import RIQI_PAYOUT_MULTIPLIER

        assert RIQI_PAYOUT_MULTIPLIER["urban_core"] == 1.0
        assert RIQI_PAYOUT_MULTIPLIER["urban_fringe"] == 1.25
        assert RIQI_PAYOUT_MULTIPLIER["peri_urban"] == 1.5
        print("[PASS] Task 5: RIQI multipliers 1.0/1.25/1.5")

    # -------------------------------------------------------------------------
    # Task 6: Underwriting gate (block if <7 active days)
    # -------------------------------------------------------------------------
    def test_task6_underwriting_gate(self):
        """Verify underwriting gate blocks purchase if <7 active days"""
        from app.services.premium_service import (
            check_underwriting_gate,
            MIN_ACTIVE_DAYS_TO_BUY,
        )

        assert MIN_ACTIVE_DAYS_TO_BUY == 7, "Minimum should be 7 days"

        # Should block with 5 days
        result = check_underwriting_gate(5)
        assert result["allowed"] == False
        assert "7" in result["reason"]

        # Should allow with 10 days
        result = check_underwriting_gate(10)
        assert result["allowed"] == True

        print("[PASS] Task 6: Underwriting gate (<7 days blocked)")

    # -------------------------------------------------------------------------
    # Task 7: Auto-downgrade to Flex if <5 active days
    # -------------------------------------------------------------------------
    def test_task7_auto_downgrade(self):
        """Verify auto-downgrade to Flex if <5 active days"""
        from app.services.premium_service import (
            apply_auto_downgrade,
            AUTO_DOWNGRADE_DAYS,
        )

        assert AUTO_DOWNGRADE_DAYS == 5, "Downgrade threshold should be 5 days"

        # Standard with 3 days -> should downgrade to Flex
        tier, downgraded = apply_auto_downgrade("standard", 3)
        assert tier == "flex"
        assert downgraded == True

        # Standard with 10 days -> should stay Standard
        tier, downgraded = apply_auto_downgrade("standard", 10)
        assert tier == "standard"
        assert downgraded == False

        # Flex with 3 days -> should stay Flex (already lowest)
        tier, downgraded = apply_auto_downgrade("flex", 3)
        assert tier == "flex"
        assert downgraded == False

        print("[PASS] Task 7: Auto-downgrade to Flex (<5 days)")

    # -------------------------------------------------------------------------
    # Task 8: Centroid drift factor (w7=0.05) in fraud scorer
    # -------------------------------------------------------------------------
    def test_task8_centroid_drift_factor(self):
        """Verify centroid drift factor w7=0.05 in 7-factor model"""
        from app.services.ml_service import FraudModel

        model = FraudModel()
        assert model.W7_CENTROID_DRIFT == 0.05, "w7 should be 0.05"

        # Verify total is 7 factors
        total_weight = (
            model.W1_GPS_COHERENCE +
            model.W2_RUN_COUNT +
            model.W3_ZONE_POLYGON +
            model.W4_CLAIM_FREQUENCY +
            model.W5_DEVICE_FINGERPRINT +
            model.W6_TRAFFIC_CROSS_CHECK +
            model.W7_CENTROID_DRIFT
        )
        assert abs(total_weight - 1.0) < 0.001, f"Weights should sum to 1.0, got {total_weight}"

        print("[PASS] Task 8: Centroid drift w7=0.05 (7-factor total)")

    # -------------------------------------------------------------------------
    # Task 9: Velocity physics check (>60km/h = spoof)
    # -------------------------------------------------------------------------
    def test_task9_velocity_physics_check(self):
        """Verify velocity physics check rejects >60km/h as spoof"""
        from app.services.ml_service import FraudModel, ClaimFeatures

        model = FraudModel()
        assert model.VELOCITY_SPOOF_KMH == 60.0, "Velocity threshold should be 60km/h"

        # Test with high velocity (should be rejected)
        features = ClaimFeatures(
            partner_id=1,
            zone_id=1,
            gps_in_zone=True,
            run_count_during_event=0,
            zone_polygon_match=True,
            claims_last_30_days=0,
            device_consistent=True,
            traffic_disrupted=True,
            centroid_drift_km=1.0,
            max_gps_velocity_kmh=80.0,  # > 60km/h
            zone_suspended=True,
        )
        result = model.score(features)
        assert result["decision"] == "auto_reject"
        assert any("velocity" in r.lower() or "60" in r for r in result["hard_reject_reasons"])

        print("[PASS] Task 9: Velocity physics check (>60km/h = spoof)")

    # -------------------------------------------------------------------------
    # Task 10: ml_service.py with 3 ML models
    # -------------------------------------------------------------------------
    def test_task10_ml_service_models(self):
        """Verify ml_service.py has all 3 ML-shaped models"""
        from app.services.ml_service import (
            zone_risk_model,
            premium_model,
            fraud_model,
            ZoneFeatures,
            PartnerFeatures,
            ClaimFeatures,
        )

        # Check models exist
        assert zone_risk_model is not None
        assert premium_model is not None
        assert fraud_model is not None

        # Check they have predict/score methods
        assert hasattr(zone_risk_model, 'predict')
        assert hasattr(premium_model, 'predict')
        assert hasattr(fraud_model, 'score')

        # Test zone_risk_model
        zone_features = ZoneFeatures(
            zone_id=1,
            city="bangalore",
            avg_rainfall_mm_per_hr=30.0,
            flood_events_2yr=5,
            aqi_avg_annual=150.0,
            aqi_severe_days_2yr=20,
            heat_advisory_days_2yr=10,
            bandh_events_2yr=3,
            dark_store_suspensions_2yr=4,
            road_flood_prone=True,
            month=7,
        )
        risk_score = zone_risk_model.predict(zone_features)
        assert 0 <= risk_score <= 100

        print("[PASS] Task 10: ml_service.py with 3 ML models")


# ============================================================================
# PERSON 2 TESTS - Triggers + Claims + Payout + Zones
# ============================================================================

class TestPerson2Tasks:
    """Tests for Person 2: Backend Triggers + Claims + Payout + Zones"""

    # -------------------------------------------------------------------------
    # Task 1: Active shift window check (leave/offline = no payout)
    # -------------------------------------------------------------------------
    def test_task1_shift_window_check(self):
        """Verify partner on leave or offline gets no payout"""
        from app.services.claims_processor import is_partner_available_for_trigger

        # Mock partner with shift days
        mock_partner = MagicMock()
        mock_partner.id = 1
        mock_partner.is_active = True
        mock_partner.shift_days = ["mon", "tue", "wed", "thu", "fri"]
        mock_partner.shift_start = "08:00"
        mock_partner.shift_end = "20:00"

        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "partner_id": 1,
            "pin_code": None,
            "is_manual_offline": False,
            "manual_offline_until": None,
            "leave_until": None,
            "leave_note": None,
            "updated_at": None,
        }

        # Test during work hours on a weekday
        work_time = datetime(2024, 1, 15, 10, 0)  # Monday 10 AM
        available, reason = is_partner_available_for_trigger(mock_partner, mock_db, work_time)
        assert available == True, f"Should be available during work hours, got {reason}"

        print("[PASS] Task 1: Active shift window check")

    # -------------------------------------------------------------------------
    # Task 2: Ward/pin-code level data check
    # -------------------------------------------------------------------------
    def test_task2_pincode_check(self):
        """Verify trigger matches partner's pin-code, not city average"""
        from app.services.trigger_engine import check_partner_pin_code_match

        mock_partner = MagicMock()
        mock_partner.id = 1
        mock_partner.pin_code = "560001"

        mock_zone = MagicMock()
        mock_zone.id = 1
        mock_zone.pin_codes = ["560001", "560002", "560003"]

        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = None

        # Should match
        matches, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)
        # With fallback (no pin_code fields), should return True
        assert matches == True

        print("[PASS] Task 2: Ward/pin-code level check")

    # -------------------------------------------------------------------------
    # Task 3: Active hours match in trigger engine
    # -------------------------------------------------------------------------
    def test_task3_active_hours_match(self):
        """Verify trigger must fall within partner's shift window"""
        from app.services.claims_processor import is_partner_available_for_trigger

        mock_partner = MagicMock()
        mock_partner.id = 1
        mock_partner.is_active = True
        mock_partner.shift_days = ["mon", "tue", "wed"]
        mock_partner.shift_start = "09:00"
        mock_partner.shift_end = "17:00"

        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "partner_id": 1, "pin_code": None, "is_manual_offline": False,
            "manual_offline_until": None, "leave_until": None, "leave_note": None,
            "updated_at": None,
        }

        # 3 AM on Monday - outside shift window
        night_time = datetime(2024, 1, 15, 3, 0)  # Monday 3 AM
        available, reason = is_partner_available_for_trigger(mock_partner, mock_db, night_time)
        assert available == False
        assert reason == "outside_shift_window"

        print("[PASS] Task 3: Active hours match")

    # -------------------------------------------------------------------------
    # Task 4: Sustained event mode (5+ days = 70% payout)
    # -------------------------------------------------------------------------
    def test_task4_sustained_event_mode(self):
        """Verify sustained event: 5+ consecutive days = 70% payout, no weekly cap"""
        from app.services.trigger_detector import (
            track_sustained_event,
            SUSTAINED_EVENT_THRESHOLD_DAYS,
            SUSTAINED_EVENT_PAYOUT_MODIFIER,
            SUSTAINED_EVENT_MAX_DAYS,
        )
        from app.models.trigger_event import TriggerType

        assert SUSTAINED_EVENT_THRESHOLD_DAYS == 5
        assert SUSTAINED_EVENT_PAYOUT_MODIFIER == 0.70
        assert SUSTAINED_EVENT_MAX_DAYS == 21

        # Simulate 5 consecutive days
        zone_id = 999  # Test zone
        for day in range(5):
            event_date = datetime.utcnow() - timedelta(days=4-day)
            result = track_sustained_event(zone_id, TriggerType.RAIN, event_date)

        assert result["is_sustained"] == True
        assert result["payout_modifier"] == 0.70
        assert result["bypass_weekly_cap"] == True

        print("[PASS] Task 4: Sustained event mode (5+ days = 70%)")

    # -------------------------------------------------------------------------
    # Task 5: Day 7 reinsurance threshold review flag
    # -------------------------------------------------------------------------
    def test_task5_reinsurance_review_endpoint(self):
        """Verify day 7 reinsurance review flag endpoint exists"""
        from app.api.policies import reinsurance_review, ReinsuranceReviewResponse

        # Check the endpoint function exists and has correct response model
        assert callable(reinsurance_review)
        assert ReinsuranceReviewResponse is not None

        # Check response model has required fields
        fields = ReinsuranceReviewResponse.model_fields
        assert "flagged_policies" in fields
        assert "total_claims_amount" in fields
        assert "review_triggered" in fields
        assert "threshold_ratio" in fields

        print("[PASS] Task 5: Day 7 reinsurance review flag")

    # -------------------------------------------------------------------------
    # Task 6: Zone pool share cap
    # -------------------------------------------------------------------------
    def test_task6_zone_pool_share_cap(self):
        """Verify zone pool share cap formula"""
        from app.services.premium_service import calculate_zone_pool_share

        result = calculate_zone_pool_share(
            calculated_payout=500.0,
            city_weekly_reserve=10000.0,
            zone_density_weight=0.35,
            total_partners_in_event=100,
        )

        # zone_pool_share = 10000 * 0.35 / 100 = 35
        expected_pool_share = 35.0
        assert result["zone_pool_share"] == expected_pool_share
        assert result["final_payout"] == min(500.0, expected_pool_share)
        assert result["pool_cap_applied"] == True

        print("[PASS] Task 6: Zone pool share cap")

    # -------------------------------------------------------------------------
    # Task 7: City-level 120% hard cap
    # -------------------------------------------------------------------------
    def test_task7_city_hard_cap(self):
        """Verify city-level 120% hard cap exists"""
        from app.services.payout_service import CITY_HARD_CAP_RATIO, check_city_hard_cap

        assert CITY_HARD_CAP_RATIO == 1.20, "City cap should be 120%"
        assert callable(check_city_hard_cap)

        print("[PASS] Task 7: City-level 120% hard cap")

    # -------------------------------------------------------------------------
    # Task 8: BCR calculation endpoint
    # -------------------------------------------------------------------------
    def test_task8_bcr_endpoint(self):
        """Verify BCR calculation endpoint exists"""
        from app.api.zones import calculate_city_bcr, BCRResponse

        assert callable(calculate_city_bcr)

        # Check BCR formula implementation
        from app.services.premium_service import calculate_bcr

        result = calculate_bcr(
            total_claims_paid=6500.0,
            total_premiums_collected=10000.0,
        )

        assert result["bcr"] == 0.65  # 6500/10000
        assert result["loss_ratio"] == 65.0  # 65%
        assert result["status"] == "healthy"  # 55-70% is healthy

        print("[PASS] Task 8: BCR calculation endpoint")

    # -------------------------------------------------------------------------
    # Task 9: Loss Ratio >85% flag (suspends enrollments)
    # -------------------------------------------------------------------------
    def test_task9_loss_ratio_suspension(self):
        """Verify loss ratio >85% suspends new enrollments"""
        from app.api.policies import LOSS_RATIO_SUSPENSION_THRESHOLD
        from app.services.premium_service import calculate_bcr

        assert LOSS_RATIO_SUSPENSION_THRESHOLD == 0.85

        # Test with 90% loss ratio
        result = calculate_bcr(
            total_claims_paid=9000.0,
            total_premiums_collected=10000.0,
        )

        assert result["loss_ratio"] == 90.0
        assert result["suspend_enrolments"] == True

        print("[PASS] Task 9: Loss Ratio >85% suspension flag")

    # -------------------------------------------------------------------------
    # Task 10: Zone reassignment backend
    # -------------------------------------------------------------------------
    def test_task10_zone_reassignment(self):
        """Verify zone reassignment endpoint exists with required fields"""
        from app.api.zones import (
            reassign_partner_zone,
            ZoneReassignmentRequest,
            ZoneReassignmentResponse,
        )

        assert callable(reassign_partner_zone)

        # Check request model
        req_fields = ZoneReassignmentRequest.model_fields
        assert "partner_id" in req_fields
        assert "new_zone_id" in req_fields

        # Check response model
        resp_fields = ZoneReassignmentResponse.model_fields
        assert "premium_adjustment" in resp_fields
        assert "new_weekly_premium" in resp_fields
        assert "days_remaining" in resp_fields
        assert "reassignment_logged" in resp_fields

        print("[PASS] Task 10: Zone reassignment backend")

    # -------------------------------------------------------------------------
    # Task 11: 48-hour weather alert backend
    # -------------------------------------------------------------------------
    def test_task11_weather_alert(self):
        """Verify 48-hour weather alert functions exist"""
        from app.services.trigger_engine import (
            check_48hr_forecast,
            send_forecast_alerts,
        )

        assert callable(check_48hr_forecast)
        assert callable(send_forecast_alerts)

        # Test forecast check returns alerts
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        alerts = check_48hr_forecast(zone_id=1, db=mock_db)
        assert isinstance(alerts, list)

        print("[PASS] Task 11: 48-hour weather alert backend")

    # -------------------------------------------------------------------------
    # Task 12: Razorpay test mode wiring
    # -------------------------------------------------------------------------
    def test_task12_razorpay_wiring(self):
        """Verify Razorpay payout function exists"""
        from app.services.payout_service import process_razorpay_payout

        assert callable(process_razorpay_payout)

        # Test with mock partner (should fail gracefully without keys)
        mock_partner = MagicMock()
        mock_partner.id = 1
        mock_partner.name = "Test"
        mock_partner.phone = "9999999999"
        mock_partner.upi_id = "test@upi"

        success, ref, data = process_razorpay_payout(mock_partner, 100.0, 1)

        # Should return False with error since keys not configured
        assert success == False
        assert "error" in data

        print("[PASS] Task 12: Razorpay test mode wiring")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests verifying components work together"""

    def test_fraud_service_integration(self):
        """Verify claims_processor uses 7-factor fraud model"""
        # Check that claims_processor imports from fraud_service
        import app.services.claims_processor as cp

        # The function should exist and be callable
        assert callable(cp.calculate_fraud_score)

        # Verify it's using the 7-factor model by checking the module
        from app.services.fraud_service import calculate_fraud_score as fs_calc
        # Both should be the same function
        assert cp.calculate_fraud_score == fs_calc

        print("[PASS] Integration: Fraud service uses 7-factor model")

    def test_premium_model_integration(self):
        """Verify premium_service uses ml_service.premium_model"""
        from app.services.premium_service import calculate_weekly_premium
        from app.services.ml_service import premium_model

        assert premium_model is not None
        assert callable(calculate_weekly_premium)

        print("[PASS] Integration: Premium service uses ML model")


# ============================================================================
# RUN TESTS
# ============================================================================

def run_all_tests():
    """Run all tests and print summary"""
    print("\n" + "="*70)
    print("PHASE 2 TASK VERIFICATION TESTS")
    print("="*70 + "\n")

    results = {"passed": 0, "failed": 0, "errors": []}

    # Person 1 Tests
    print("\n--- PERSON 1: Pricing + Premium Engine + ML Wrapper ---\n")
    p1 = TestPerson1Tasks()
    p1_tests = [
        ("Task 1: Pricing tiers Rs.22/33/45", p1.test_task1_pricing_tiers_premium_service),
        ("Task 1b: ML Service pricing", p1.test_task1_pricing_tiers_ml_service),
        ("Task 2: Full premium formula", p1.test_task2_premium_formula_components),
        ("Task 3: Seasonal multipliers", p1.test_task3_seasonal_multipliers),
        ("Task 4: RIQI zone scoring", p1.test_task4_riqi_scoring),
        ("Task 5: RIQI multipliers", p1.test_task5_riqi_multipliers),
        ("Task 6: Underwriting gate", p1.test_task6_underwriting_gate),
        ("Task 7: Auto-downgrade", p1.test_task7_auto_downgrade),
        ("Task 8: Centroid drift w7", p1.test_task8_centroid_drift_factor),
        ("Task 9: Velocity physics", p1.test_task9_velocity_physics_check),
        ("Task 10: ML service models", p1.test_task10_ml_service_models),
    ]

    for name, test_func in p1_tests:
        try:
            test_func()
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"PERSON 1 - {name}: {str(e)}")
            print(f"[FAIL] {name}: {e}")

    # Person 2 Tests
    print("\n--- PERSON 2: Triggers + Claims + Payout + Zones ---\n")
    p2 = TestPerson2Tasks()
    p2_tests = [
        ("Task 1: Shift window check", p2.test_task1_shift_window_check),
        ("Task 2: Pin-code check", p2.test_task2_pincode_check),
        ("Task 3: Active hours match", p2.test_task3_active_hours_match),
        ("Task 4: Sustained event", p2.test_task4_sustained_event_mode),
        ("Task 5: Reinsurance review", p2.test_task5_reinsurance_review_endpoint),
        ("Task 6: Zone pool share cap", p2.test_task6_zone_pool_share_cap),
        ("Task 7: City hard cap", p2.test_task7_city_hard_cap),
        ("Task 8: BCR endpoint", p2.test_task8_bcr_endpoint),
        ("Task 9: Loss ratio flag", p2.test_task9_loss_ratio_suspension),
        ("Task 10: Zone reassignment", p2.test_task10_zone_reassignment),
        ("Task 11: Weather alert", p2.test_task11_weather_alert),
        ("Task 12: Razorpay wiring", p2.test_task12_razorpay_wiring),
    ]

    for name, test_func in p2_tests:
        try:
            test_func()
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"PERSON 2 - {name}: {str(e)}")
            print(f"[FAIL] {name}: {e}")

    # Integration Tests
    print("\n--- INTEGRATION TESTS ---\n")
    integ = TestIntegration()
    integ_tests = [
        ("Fraud service integration", integ.test_fraud_service_integration),
        ("Premium model integration", integ.test_premium_model_integration),
    ]

    for name, test_func in integ_tests:
        try:
            test_func()
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"INTEGRATION - {name}: {str(e)}")
            print(f"[FAIL] {name}: {e}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Total: {results['passed'] + results['failed']}")

    if results["errors"]:
        print("\n--- FAILURES ---")
        for err in results["errors"]:
            print(f"  * {err}")

    print("\n")
    return results


if __name__ == "__main__":
    run_all_tests()
````

--- FILE: backend/tests/test_stress_scenarios.py ---
``python
"""
Tests for stress scenario calculations and reserve-needed feature.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class TestStressScenarios:
    """Tests for stress scenario service."""

    def test_monsoon_scenario_calculates_reserve_needed(self, mock_db):
        """Test that monsoon scenario correctly calculates reserve_needed."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        # Mock the city metrics query
        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="bangalore",
                active_policies=100,
                avg_weekly_premium=35.0,
                total_weekly_reserve=3500.0,
                zone_count=5,
            )

            result = calculate_stress_scenario("monsoon_14day_bangalore", mock_db)

            assert result.scenario_id == "monsoon_14day_bangalore"
            assert result.days == 14
            assert result.projected_claims > 0
            assert result.projected_payout > 0

            # reserve_needed = max(projected_payout - city_reserve_available, 0)
            expected_reserve = max(result.projected_payout - result.city_reserve_available, 0)
            assert result.reserve_needed == expected_reserve
            assert result.reserve_needed >= 0

    def test_stress_scenario_with_zero_premiums(self, mock_db):
        """Test scenario with no collected premiums (zero reserve)."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="bangalore",
                active_policies=50,
                avg_weekly_premium=0.0,
                total_weekly_reserve=0.0,
                zone_count=5,
            )

            result = calculate_stress_scenario("monsoon_14day_bangalore", mock_db)

            # With zero reserve, reserve_needed = projected_payout
            assert result.city_reserve_available == 0.0
            assert result.reserve_needed == result.projected_payout

    def test_stress_scenario_formula_breakdown_complete(self, mock_db):
        """Test that formula breakdown contains all required steps."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="bangalore",
                active_policies=100,
                avg_weekly_premium=35.0,
                total_weekly_reserve=3500.0,
                zone_count=5,
            )

            result = calculate_stress_scenario("monsoon_14day_bangalore", mock_db)

            # Check all steps are present
            breakdown = result.formula_breakdown
            assert "step_1_active_policies" in breakdown
            assert "step_2_trigger_probability" in breakdown
            assert "step_3_days" in breakdown
            assert "step_4_projected_claims" in breakdown
            assert "step_5_weighted_avg_payout" in breakdown
            assert "step_6_severity_multiplier" in breakdown
            assert "step_7_avg_payout_with_severity" in breakdown
            assert "step_8_projected_payout" in breakdown
            assert "step_9_city_reserve_available" in breakdown
            assert "step_10_reserve_needed" in breakdown

    def test_multiple_scenarios_return_all(self, mock_db):
        """Test that get_all_stress_scenarios returns all defined scenarios."""
        from app.services.stress_scenario_service import (
            get_all_stress_scenarios,
            get_scenario_ids,
        )

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="test",
                active_policies=50,
                avg_weekly_premium=30.0,
                total_weekly_reserve=1500.0,
                zone_count=3,
            )

            result = get_all_stress_scenarios(mock_db)
            scenario_ids = get_scenario_ids()

            assert len(result.scenarios) == len(scenario_ids)
            assert result.total_reserve_needed >= 0
            assert result.computed_at is not None

            # Check all scenarios are present
            returned_ids = {s.scenario_id for s in result.scenarios}
            for expected_id in scenario_ids:
                assert expected_id in returned_ids

    def test_unknown_scenario_returns_default(self, mock_db):
        """Test that unknown scenario ID returns safe default."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        result = calculate_stress_scenario("nonexistent_scenario", mock_db)

        assert result.scenario_name == "Unknown Scenario"
        assert result.days == 0
        assert result.projected_claims == 0
        assert result.reserve_needed == 0.0
        assert "Scenario not found" in result.assumptions

    def test_data_source_is_live_when_policies_exist(self, mock_db):
        """Test that data_source is 'live' when active policies exist."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="delhi",
                active_policies=25,  # > 0
                avg_weekly_premium=40.0,
                total_weekly_reserve=1000.0,
                zone_count=3,
            )

            result = calculate_stress_scenario("aqi_crisis_7day_delhi", mock_db)
            assert result.data_source == "live"

    def test_data_source_is_mock_when_no_policies(self, mock_db):
        """Test that data_source is 'mock' when no active policies."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="delhi",
                active_policies=0,  # No policies
                avg_weekly_premium=0.0,
                total_weekly_reserve=0.0,
                zone_count=3,
            )

            result = calculate_stress_scenario("aqi_crisis_7day_delhi", mock_db)
            assert result.data_source == "mock"
````

--- FILE: frontend/src/tests/apiIntegration.test.js ---
``javascript
/**
 * apiIntegration.test.js  â€“  API client fetch-layer integration tests
 *
 * Covers:
 *   - proofApi: getMyReassignments, acceptReassignment, rejectReassignment
 *   - api.js: getPartnerExperienceState response shape, getActiveTriggers
 *   - adminApi: getDashboardStats, simulateWeather, approveClaim
 *
 * All tests use vi.stubGlobal('fetch', ...) â€” no real network calls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// â”€â”€ Modules under test â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import proofApi, {
  getMyReassignments,
  acceptReassignment,
  rejectReassignment,
  getActiveTriggerProofs,
} from '../services/proofApi';

import api from '../services/api';
import adminApi from '../services/adminApi';

// â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** Build a fake Response object that resolves to the given JSON body */
function mockFetch(body, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

/** Extract the URL that the last fetch call was made to */
function lastUrl() {
  const calls = global.fetch.mock.calls;
  return calls[calls.length - 1][0];
}

/** Extract the init (method, headers, body) of the last fetch call */
function lastInit() {
  const calls = global.fetch.mock.calls;
  return calls[calls.length - 1][1];
}

beforeEach(() => {
  // Reset localStorage token for each test
  localStorage.clear();
  localStorage.setItem('access_token', 'test-jwt-token');
});

afterEach(() => {
  vi.restoreAllMocks();
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// proofApi â€” zone reassignment
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('proofApi.getMyReassignments', () => {
  it('calls GET /api/v1/partners/me/reassignments', async () => {
    const payload = { reassignments: [], total: 0, pending_count: 0 };
    global.fetch = mockFetch(payload);

    const result = await getMyReassignments();

    expect(lastUrl()).toContain('/api/v1/partners/me/reassignments');
    // GET calls: no method override (undefined = GET) and no request body
    expect(lastInit()?.method).toBeUndefined();
    expect(lastInit()?.body).toBeUndefined();
    expect(result).toEqual(payload);
  });

  it('attaches Authorization header', async () => {
    global.fetch = mockFetch({ reassignments: [] });
    await getMyReassignments();
    const headers = global.fetch.mock.calls[0][1]?.headers || {};
    expect(headers['Authorization']).toBe('Bearer test-jwt-token');
  });

  it('throws on non-ok response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' }),
    });
    await expect(getMyReassignments()).rejects.toThrow('Unauthorized');
  });
});

describe('proofApi.acceptReassignment', () => {
  it('calls POST /api/v1/partners/me/reassignments/7/accept', async () => {
    const payload = { id: 7, status: 'accepted', message: 'Zone reassignment accepted successfully', zone_updated: true };
    global.fetch = mockFetch(payload);

    const result = await acceptReassignment(7);

    expect(lastUrl()).toContain('/api/v1/partners/me/reassignments/7/accept');
    expect(lastInit()?.method).toBe('POST');
    expect(result.status).toBe('accepted');
  });

  it('throws with backend detail on failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Reassignment proposal has expired' }),
    });
    await expect(acceptReassignment(99)).rejects.toThrow('Reassignment proposal has expired');
  });
});

describe('proofApi.rejectReassignment', () => {
  it('calls POST /api/v1/partners/me/reassignments/3/reject', async () => {
    global.fetch = mockFetch({ id: 3, status: 'rejected', message: 'Zone reassignment rejected', zone_updated: false });

    await rejectReassignment(3);

    expect(lastUrl()).toContain('/api/v1/partners/me/reassignments/3/reject');
    expect(lastInit()?.method).toBe('POST');
  });
});

describe('proofApi.getActiveTriggerProofs', () => {
  it('calls /api/v1/triggers/active without zone filter', async () => {
    global.fetch = mockFetch({ triggers: [] });
    await getActiveTriggerProofs();
    expect(lastUrl()).toContain('/api/v1/triggers/active');
    expect(lastUrl()).not.toContain('zone_id');
  });

  it('adds zone_id query param when provided', async () => {
    global.fetch = mockFetch({ triggers: [] });
    await getActiveTriggerProofs(5);
    expect(lastUrl()).toContain('zone_id=5');
  });
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// api.js â€” experience state
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('api.getPartnerExperienceState', () => {
  it('calls GET /api/v1/partners/me/experience-state', async () => {
    const payload = {
      zone_alert: null,
      zone_reassignment: null,
      loyalty: { streak_weeks: 3, discount_unlocked: false, next_milestone: 4, discount_pct: 3 },
      premium_breakdown: { base: 33, total: 38 },
      latest_payout: null,
      fetched_at: new Date().toISOString(),
    };
    global.fetch = mockFetch(payload);

    const result = await api.getPartnerExperienceState();

    expect(lastUrl()).toContain('/api/v1/partners/me/experience-state');
    expect(result.loyalty.streak_weeks).toBe(3);
    expect(result.zone_alert).toBeNull();
  });

  it('includes Authorization header', async () => {
    global.fetch = mockFetch({ loyalty: {} });
    await api.getPartnerExperienceState();
    const headers = global.fetch.mock.calls[0][1]?.headers || {};
    expect(headers['Authorization']).toBe('Bearer test-jwt-token');
  });
});

describe('api.getActiveTriggers', () => {
  it('calls /api/v1/triggers/active with no params when zoneId omitted', async () => {
    global.fetch = mockFetch({ triggers: [] });
    await api.getActiveTriggers();
    expect(lastUrl()).toContain('/api/v1/triggers/active');
  });

  it('adds zone_id param when provided', async () => {
    global.fetch = mockFetch({ triggers: [] });
    await api.getActiveTriggers(3);
    expect(lastUrl()).toContain('zone_id=3');
  });
});

describe('api.getClaims', () => {
  it('calls /api/v1/claims with limit param', async () => {
    global.fetch = mockFetch([]);
    await api.getClaims({ limit: 5 });
    expect(lastUrl()).toContain('/api/v1/claims');
    expect(lastUrl()).toContain('limit=5');
  });
});

describe('api.createPolicy', () => {
  it('POSTs to /api/v1/policies with correct body', async () => {
    global.fetch = mockFetch({ id: 1, tier: 'standard', is_active: true });
    await api.createPolicy('standard', true);
    expect(lastUrl()).toContain('/api/v1/policies');
    expect(lastInit()?.method).toBe('POST');
    const body = JSON.parse(lastInit()?.body);
    expect(body.tier).toBe('standard');
    expect(body.auto_renew).toBe(true);
  });
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// adminApi
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('adminApi.getDashboardStats', () => {
  it('calls GET /api/v1/admin/dashboard', async () => {
    const payload = {
      total_partners: 10,
      active_policies: 6,
      total_zones: 11,
      active_triggers: 1,
      pending_claims: 2,
      approved_claims: 3,
      total_paid_amount: 750.0,
    };
    global.fetch = mockFetch(payload);
    const result = await adminApi.getDashboardStats();
    expect(lastUrl()).toContain('/api/v1/admin/dashboard');
    expect(result.total_partners).toBe(10);
  });
});

describe('adminApi.simulateWeather', () => {
  it('POSTs to /api/v1/admin/simulate/weather with zone_id and params', async () => {
    global.fetch = mockFetch({ zone_id: 2, triggers_created: [5] });
    await adminApi.simulateWeather(2, { rainfall_mm_hr: 90 });
    expect(lastUrl()).toContain('/api/v1/admin/simulate/weather');
    const body = JSON.parse(lastInit()?.body);
    expect(body.zone_id).toBe(2);
    expect(body.rainfall_mm_hr).toBe(90);
  });
});

describe('adminApi.approveClaim', () => {
  it('POSTs to /api/v1/admin/claims/14/approve', async () => {
    global.fetch = mockFetch({ message: 'Claim approved', claim_id: 14 });
    await adminApi.approveClaim(14);
    expect(lastUrl()).toContain('/api/v1/admin/claims/14/approve');
    expect(lastInit()?.method).toBe('POST');
  });
});

describe('adminApi.rejectClaim', () => {
  it('POSTs with reason when provided', async () => {
    global.fetch = mockFetch({ message: 'Claim rejected', claim_id: 11 });
    await adminApi.rejectClaim(11, 'fraud detected');
    const body = JSON.parse(lastInit()?.body);
    expect(body.reason).toBe('fraud detected');
  });

  it('POSTs with null body when no reason given', async () => {
    global.fetch = mockFetch({ message: 'Claim rejected' });
    await adminApi.rejectClaim(11);
    // fetch called with no body (null passed)
    expect(lastInit()?.body).toBeUndefined();
  });
});

describe('adminApi.previewNotification', () => {
  it('calls GET /api/v1/admin/panel/notifications/preview with type and lang', async () => {
    global.fetch = mockFetch({ type: 'claim_paid', language: 'hi', title: 'à¤­à¥à¤—à¤¤à¤¾à¤¨ à¤ªà¥à¤°à¤¾à¤ªà¥à¤¤!' });
    await adminApi.previewNotification('claim_paid', 'hi');
    expect(lastUrl()).toContain('/api/v1/admin/panel/notifications/preview');
    expect(lastUrl()).toContain('type=claim_paid');
    expect(lastUrl()).toContain('lang=hi');
  });
});

describe('adminApi.getStressScenarios', () => {
  it('calls GET /api/v1/admin/panel/stress-scenarios', async () => {
    global.fetch = mockFetch([]);
    await adminApi.getStressScenarios();
    expect(lastUrl()).toContain('/api/v1/admin/panel/stress-scenarios');
  });
});
````

--- FILE: frontend/src/tests/partner.test.js ---
``javascript
// Tests moved to partner.test.jsx (JSX extension required for @vitejs/plugin-react transform)
````

--- FILE: frontend/src/tests/partner.test.jsx ---
``jsx
/**
 * partner.test.jsx  â€“  Partner-flow component & hook tests
 * (.jsx extension so @vitejs/plugin-react applies JSX transform)
 *
 * Covers:
 *   - proofApi countdown helpers: parseCountdown, formatCountdown, countdownUrgency
 *   - ReassignmentCountdown: renders correct time, urgency classes, fires onExpire
 *   - SourceBadge: all 5 trigger types, severity chip, showLabel, unknown type
 *   - ProofCard: amount, status, UPI ref, fraud score, metric value, timestamps
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';

// â”€â”€ Pure countdown helpers (no fetch, no DOM) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import {
  parseCountdown,
  formatCountdown,
  countdownUrgency,
} from '../services/proofApi';

// â”€â”€ Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import SourceBadge from '../components/SourceBadge';
import ProofCard from '../components/ProofCard';
import ReassignmentCountdown from '../components/ReassignmentCountdown';
import { WeeklyPremiumBreakdown } from '../pages/Dashboard';
import { RenewalBreakdownCard } from '../pages/Profile';

// â”€â”€ Time helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const hoursFromNow = (h) =>
  new Date(Date.now() + h * 3_600_000).toISOString();

const hoursAgo = (h) =>
  new Date(Date.now() - h * 3_600_000).toISOString();

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// parseCountdown
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('parseCountdown', () => {
  it('returns expired=true for a past timestamp', () => {
    const cd = parseCountdown(hoursAgo(1));
    expect(cd.expired).toBe(true);
    expect(cd.totalMs).toBe(0);
  });

  it('returns expired=false and correct hours for a future timestamp', () => {
    const cd = parseCountdown(hoursFromNow(10));
    expect(cd.expired).toBe(false);
    expect(cd.hours).toBeGreaterThanOrEqual(9);
  });

  it('correctly separates hours and minutes (90 min â†’ 1h 29m)', () => {
    const cd = parseCountdown(new Date(Date.now() + 90 * 60_000).toISOString());
    expect(cd.hours).toBe(1);
    expect(cd.minutes).toBeGreaterThanOrEqual(28);
    expect(cd.minutes).toBeLessThanOrEqual(30);
  });
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// formatCountdown
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('formatCountdown', () => {
  it('returns "Expired" for a past timestamp', () => {
    expect(formatCountdown(hoursAgo(2))).toBe('Expired');
  });

  it('returns "Xh Ym left" for hours remaining', () => {
    expect(formatCountdown(hoursFromNow(15))).toMatch(/\d+h \d+m left/);
  });

  it('returns seconds-level label for < 1 minute remaining', () => {
    expect(
      formatCountdown(new Date(Date.now() + 30_000).toISOString())
    ).toMatch(/\d+s left/);
  });
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// countdownUrgency
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('countdownUrgency', () => {
  it('"expired" for past timestamp',        () => expect(countdownUrgency(hoursAgo(0.1))).toBe('expired'));
  it('"safe" for 20h remaining',            () => expect(countdownUrgency(hoursFromNow(20))).toBe('safe'));
  it('"safe" at exactly 12h boundary',      () => expect(countdownUrgency(hoursFromNow(12))).toBe('safe'));
  it('"warn" just under 12h',               () => expect(countdownUrgency(hoursFromNow(11.9))).toBe('warn'));
  it('"warn" for 6h remaining',             () => expect(countdownUrgency(hoursFromNow(6))).toBe('warn'));
  it('"warn" at exactly 4h boundary',       () => expect(countdownUrgency(hoursFromNow(4))).toBe('warn'));
  it('"urgent" just under 4h',              () => expect(countdownUrgency(hoursFromNow(3.9))).toBe('urgent'));
  it('"urgent" for 2h remaining',           () => expect(countdownUrgency(hoursFromNow(2))).toBe('urgent'));
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// ReassignmentCountdown component
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('ReassignmentCountdown', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('renders remaining time label for a future expires_at', () => {
    render(<ReassignmentCountdown expiresAt={hoursFromNow(10)} />);
    expect(screen.getByRole('timer')).toBeInTheDocument();
    expect(screen.getByText(/h \d+m left/)).toBeInTheDocument();
  });

  it('renders "Expired" for a past expires_at', () => {
    render(<ReassignmentCountdown expiresAt={hoursAgo(1)} />);
    expect(screen.getByText('Expired')).toBeInTheDocument();
  });

  it('fires onExpire callback once when countdown reaches zero', async () => {
    const onExpire = vi.fn();
    render(
      <ReassignmentCountdown
        expiresAt={new Date(Date.now() + 500).toISOString()}
        onExpire={onExpire}
      />
    );
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it('applies .rcd-safe class for 20h remaining', () => {
    const { container } = render(
      <ReassignmentCountdown expiresAt={hoursFromNow(20)} />
    );
    expect(container.querySelector('.rcd-safe')).toBeInTheDocument();
  });

  it('applies .rcd-warn class for 6h remaining', () => {
    const { container } = render(
      <ReassignmentCountdown expiresAt={hoursFromNow(6)} />
    );
    expect(container.querySelector('.rcd-warn')).toBeInTheDocument();
  });

  it('applies .rcd-urgent class for 2h remaining', () => {
    const { container } = render(
      <ReassignmentCountdown expiresAt={hoursFromNow(2)} />
    );
    expect(container.querySelector('.rcd-urgent')).toBeInTheDocument();
  });

  it('applies .rcd-expired class for past timestamp', () => {
    const { container } = render(
      <ReassignmentCountdown expiresAt={hoursAgo(1)} />
    );
    expect(container.querySelector('.rcd-expired')).toBeInTheDocument();
  });
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SourceBadge component
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('SourceBadge', () => {
  const LABELS = {
    rain: 'Heavy Rain',
    heat: 'Extreme Heat',
    aqi: 'Dangerous AQI',
    shutdown: 'Civic Shutdown',
    closure: 'Store Closure',
  };

  it.each(Object.entries(LABELS))(
    'renders correct label for type "%s"',
    (type, label) => {
      render(<SourceBadge type={type} />);
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  );

  it('renders severity chip when severity prop is provided', () => {
    render(<SourceBadge type="rain" severity={4} />);
    expect(screen.getByText('S4')).toBeInTheDocument();
  });

  it('does not render severity chip when severity is omitted', () => {
    render(<SourceBadge type="heat" />);
    expect(screen.queryByText(/^S\d$/)).not.toBeInTheDocument();
  });

  it('hides label text when showLabel=false', () => {
    render(<SourceBadge type="aqi" showLabel={false} />);
    expect(screen.queryByText('Dangerous AQI')).not.toBeInTheDocument();
  });

  it('renders fallback "Event" label for unknown type', () => {
    render(<SourceBadge type="tornado" />);
    expect(screen.getByText('Event')).toBeInTheDocument();
  });
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// ProofCard component
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

describe('ProofCard', () => {
  const BASE = {
    triggerType: 'rain',
    status: 'paid',
    amount: 250,
    claimId: 42,
    createdAt: '2026-04-01T10:00:00Z',
  };

  it('renders amount in rupees', () => {
    render(<ProofCard {...BASE} />);
    expect(screen.getByText('â‚¹250')).toBeInTheDocument();
  });

  it('renders claim ID reference', () => {
    render(<ProofCard {...BASE} />);
    expect(screen.getByText(/Claim #42/)).toBeInTheDocument();
  });

  it('renders PAID status chip', () => {
    render(<ProofCard {...BASE} />);
    expect(screen.getByText(/PAID/, { selector: 'span' })).toBeInTheDocument();
  });

  it('renders PENDING status chip', () => {
    render(<ProofCard {...BASE} status="pending" />);
    expect(screen.getByText(/PENDING/, { selector: 'span' })).toBeInTheDocument();
  });

  it('renders REJECTED status chip', () => {
    render(<ProofCard {...BASE} status="rejected" />);
    expect(screen.getByText(/REJECTED/, { selector: 'span' })).toBeInTheDocument();
  });

  it('renders UPI ref when status is paid and upiRef is provided', () => {
    render(<ProofCard {...BASE} upiRef="RAPID000042000420" />);
    expect(screen.getByText(/RAPID000042000420/)).toBeInTheDocument();
  });

  it('does NOT render UPI ref when status is not paid', () => {
    render(<ProofCard {...BASE} status="approved" upiRef="RAPID000042" />);
    expect(screen.queryByText(/RAPID000042/)).not.toBeInTheDocument();
  });

  it('renders fraud warning when fraudScore > 0.5', () => {
    render(<ProofCard {...BASE} fraudScore={0.72} />);
    expect(screen.getByText(/Under manual review/)).toBeInTheDocument();
  });

  it('does NOT render fraud warning when fraudScore â‰¤ 0.5', () => {
    render(<ProofCard {...BASE} fraudScore={0.3} />);
    expect(screen.queryByText(/Under manual review/)).not.toBeInTheDocument();
  });

  it('renders metric value chip when provided', () => {
    render(<ProofCard {...BASE} metricValue="87mm/hr" />);
    expect(screen.getByText('87mm/hr')).toBeInTheDocument();
  });

  it('renders paid timestamp when paidAt is provided', () => {
    render(<ProofCard {...BASE} paidAt="2026-04-01T11:00:00Z" />);
    expect(screen.getByText(/Paid/)).toBeInTheDocument();
  });

  it('renders correct SourceBadge for triggerType="shutdown"', () => {
    render(<ProofCard {...BASE} triggerType="shutdown" />);
    expect(screen.getByText('Civic Shutdown')).toBeInTheDocument();
  });
});

describe('WeeklyPremiumBreakdown', () => {
  it('shows backend values when breakdown data exists', () => {
    render(
      <WeeklyPremiumBreakdown
        policy={{ tier: 'standard' }}
        breakdown={{
          base: 33,
          zone_risk: 4,
          seasonal_index: 1.12,
          riqi_adjustment: 1.08,
          activity_factor: 1,
          loyalty_discount: 0.96,
          loyalty_weeks: 4,
          total: 42,
          riqi_band: 'Urban Core',
        }}
      />
    );

    expect(screen.getByText(/â‚¹42/)).toBeInTheDocument();
    expect(screen.queryByText(/unavailable right now/i)).not.toBeInTheDocument();
  });

  it('does not render synthetic premium math when breakdown is missing', () => {
    render(<WeeklyPremiumBreakdown policy={{ tier: 'standard' }} breakdown={null} />);

    expect(screen.getByText(/Premium breakdown is unavailable right now/i)).toBeInTheDocument();
    expect(screen.queryByText(/Urban Core surcharge/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/4-week streak/i)).not.toBeInTheDocument();
  });
});

describe('RenewalBreakdownCard', () => {
  it('shows backend renewal values when preview exists', () => {
    render(
      <RenewalBreakdownCard
        renewalLoading={false}
        renewalPreview={{
          has_policy: true,
          renewal_premium: 41,
          current_tier: 'standard',
          loyalty_streak_weeks: 4,
          renewal_available: true,
          breakdown: {
            base: 33,
            zone_risk: 3,
            seasonal_index: 1.1,
            riqi_adjustment: 1.05,
            activity_factor: 1,
            loyalty_discount: 0.96,
            riqi_band: 'Urban Core',
          },
        }}
      />
    );

    expect(screen.getByText(/â‚¹41/)).toBeInTheDocument();
    expect(screen.queryByText(/Renewal pricing is unavailable/i)).not.toBeInTheDocument();
  });

  it('shows unavailable state instead of static estimate when backend preview lacks breakdown', () => {
    render(
      <RenewalBreakdownCard
        renewalLoading={false}
        renewalPreview={{ has_policy: true, breakdown: null }}
      />
    );

    expect(screen.getByText(/Renewal pricing is unavailable right now/i)).toBeInTheDocument();
    expect(screen.queryByText(/Urban Fringe band/i)).not.toBeInTheDocument();
  });
});
````

--- FILE: frontend/src/tests/setup.js ---
``javascript
/**
 * setup.js  â€“  Vitest global test setup
 *
 * Runs before every test file. Extends expect with jest-dom matchers
 * and resets mocks after each test.
 */
import '@testing-library/jest-dom';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// Auto-cleanup React trees after every test
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
````
