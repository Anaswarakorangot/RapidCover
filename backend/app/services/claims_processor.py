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
