"""
Multi-Trigger Resolver for RapidCover.

Prevents duplicate payouts when multiple triggers fire together (e.g., rain + AQI + shutdown).
Groups triggers by partner + zone within a 6-hour window. Highest payout wins with optional
10% uplift for confirmed severe disruption.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.claim import Claim, ClaimStatus
from app.utils.time_utils import utcnow
from app.models.policy import Policy
from app.models.partner import Partner
from app.models.trigger_event import TriggerEvent, TriggerType


# Configuration
AGGREGATION_WINDOW_HOURS = 6
SEVERE_DISRUPTION_UPLIFT_PERCENT = 10.0  # 10% uplift for 3+ simultaneous triggers


def generate_aggregation_group_id() -> str:
    """Generate a unique aggregation group ID."""
    return f"AGG-{uuid.uuid4().hex[:12].upper()}"


def find_triggers_in_window(
    zone_id: int,
    window_start: datetime,
    window_end: datetime,
    db: Session,
) -> list[TriggerEvent]:
    """
    Find all trigger events in a zone within a time window.

    Args:
        zone_id: Zone to search
        window_start: Start of time window
        window_end: End of time window
        db: Database session

    Returns:
        List of TriggerEvent objects in the window
    """
    return (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == zone_id,
            TriggerEvent.started_at >= window_start,
            TriggerEvent.started_at <= window_end,
        )
        .order_by(TriggerEvent.started_at.asc())
        .all()
    )


def find_existing_claim_in_window(
    policy_id: int,
    zone_id: int,
    window_start: datetime,
    window_end: datetime,
    db: Session,
) -> Optional[Claim]:
    """
    Find an existing claim for a policy in the aggregation window.

    Args:
        policy_id: Policy to check
        zone_id: Zone ID for the trigger
        window_start: Start of aggregation window
        window_end: End of aggregation window
        db: Database session

    Returns:
        Existing Claim if found, None otherwise
    """
    return (
        db.query(Claim)
        .join(TriggerEvent, Claim.trigger_event_id == TriggerEvent.id)
        .filter(
            Claim.policy_id == policy_id,
            TriggerEvent.zone_id == zone_id,
            Claim.created_at >= window_start,
            Claim.created_at <= window_end,
            Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED, ClaimStatus.PAID]),
        )
        .order_by(Claim.created_at.asc())
        .first()
    )


def calculate_aggregation_window(trigger_time: datetime) -> tuple[datetime, datetime]:
    """
    Calculate the 6-hour aggregation window centered around the trigger time.

    Returns (window_start, window_end)
    """
    # Window is 3 hours before to 3 hours after
    window_start = trigger_time - timedelta(hours=AGGREGATION_WINDOW_HOURS / 2)
    window_end = trigger_time + timedelta(hours=AGGREGATION_WINDOW_HOURS / 2)
    return (window_start, window_end)


def should_apply_severe_disruption_uplift(triggers: list[TriggerEvent]) -> bool:
    """
    Determine if severe disruption uplift should apply.

    Uplift applies when 3+ distinct trigger types fire simultaneously.
    """
    unique_types = set(t.trigger_type for t in triggers)
    return len(unique_types) >= 3


def calculate_aggregated_payout(
    triggers: list[TriggerEvent],
    policy: Policy,
    base_payouts: dict[int, float],
) -> tuple[float, dict]:
    """
    Calculate the aggregated payout for multiple triggers.

    Strategy: Highest payout wins, with optional uplift for severe disruption.

    Args:
        triggers: List of trigger events to aggregate
        policy: The policy for payout calculation
        base_payouts: Dict mapping trigger_id -> calculated payout amount

    Returns:
        (final_payout, aggregation_metadata)
    """
    if not triggers or not base_payouts:
        return (0.0, {})

    # Find the highest payout trigger
    highest_payout = 0.0
    primary_trigger_id = None
    for trigger in triggers:
        payout = base_payouts.get(trigger.id, 0.0)
        if payout > highest_payout:
            highest_payout = payout
            primary_trigger_id = trigger.id

    # Calculate pre-aggregation total (what would have been paid without aggregation)
    pre_aggregation_total = sum(base_payouts.values())

    # Determine if severe disruption uplift applies
    apply_uplift = should_apply_severe_disruption_uplift(triggers)
    uplift_percent = SEVERE_DISRUPTION_UPLIFT_PERCENT if apply_uplift else 0.0
    uplift_amount = highest_payout * (uplift_percent / 100)
    final_payout = highest_payout + uplift_amount

    # Apply policy daily limit
    final_payout = min(final_payout, policy.max_daily_payout)

    # Identify suppressed triggers
    suppressed_trigger_ids = [t.id for t in triggers if t.id != primary_trigger_id]

    # Build aggregation metadata
    aggregation_metadata = {
        "group_id": generate_aggregation_group_id(),
        "is_aggregated": len(triggers) > 1,
        "primary_trigger_id": primary_trigger_id,
        "suppressed_triggers": suppressed_trigger_ids,
        "pre_aggregation_payout": round(pre_aggregation_total, 2),
        "post_aggregation_payout": round(final_payout, 2),
        "savings": round(pre_aggregation_total - final_payout, 2),
        "uplift_applied": apply_uplift,
        "uplift_percent": uplift_percent,
        "uplift_amount": round(uplift_amount, 2),
        "triggers_in_window": [
            {
                "id": t.id,
                "type": t.trigger_type.value,
                "severity": t.severity,
                "payout": base_payouts.get(t.id, 0.0),
                "started_at": t.started_at.isoformat() if t.started_at else None,
            }
            for t in triggers
        ],
        "window_hours": AGGREGATION_WINDOW_HOURS,
        "aggregated_at": utcnow().isoformat(),
    }

    return (final_payout, aggregation_metadata)


def check_and_resolve_aggregation(
    trigger_event: TriggerEvent,
    policy: Policy,
    calculated_payout: float,
    db: Session,
) -> tuple[bool, Optional[Claim], dict]:
    """
    Check if this trigger should be aggregated with existing claims.

    This is the main entry point called from claims_processor.

    Args:
        trigger_event: The new trigger event
        policy: Policy being claimed against
        calculated_payout: The payout calculated for this trigger alone
        db: Database session

    Returns:
        (should_create_new_claim, existing_claim_to_update, aggregation_metadata)

        If should_create_new_claim is True, create a new claim with aggregation_metadata.
        If existing_claim is returned, update it instead of creating new.
    """
    trigger_time = trigger_event.started_at or utcnow()
    window_start, window_end = calculate_aggregation_window(trigger_time)

    # Check for existing claim in window
    existing_claim = find_existing_claim_in_window(
        policy.id,
        trigger_event.zone_id,
        window_start,
        window_end,
        db,
    )

    if existing_claim is None:
        # No existing claim - this is the first trigger in the window
        # Create new claim with basic aggregation metadata (not yet aggregated)
        aggregation_metadata = {
            "group_id": generate_aggregation_group_id(),
            "is_aggregated": False,
            "primary_trigger_id": trigger_event.id,
            "suppressed_triggers": [],
            "pre_aggregation_payout": round(calculated_payout, 2),
            "post_aggregation_payout": round(calculated_payout, 2),
            "savings": 0.0,
            "uplift_applied": False,
            "uplift_percent": 0.0,
            "uplift_amount": 0.0,
            "triggers_in_window": [
                {
                    "id": trigger_event.id,
                    "type": trigger_event.trigger_type.value,
                    "severity": trigger_event.severity,
                    "payout": calculated_payout,
                    "started_at": trigger_time.isoformat(),
                }
            ],
            "window_hours": AGGREGATION_WINDOW_HOURS,
            "aggregated_at": utcnow().isoformat(),
        }
        return (True, None, aggregation_metadata)

    # Existing claim found - this trigger should be aggregated
    # Parse existing claim's aggregation data
    existing_validation = {}
    try:
        existing_validation = json.loads(existing_claim.validation_data or "{}")
    except json.JSONDecodeError:
        pass

    existing_aggregation = existing_validation.get("aggregation", {})

    # Get all triggers in window including current
    triggers_in_window = find_triggers_in_window(trigger_event.zone_id, window_start, window_end, db)

    # Build payout map - use existing data plus new trigger
    base_payouts = {}
    for tw in existing_aggregation.get("triggers_in_window", []):
        base_payouts[tw["id"]] = tw["payout"]
    base_payouts[trigger_event.id] = calculated_payout

    # Calculate new aggregated payout
    final_payout, new_aggregation = calculate_aggregated_payout(
        triggers_in_window,
        policy,
        base_payouts,
    )

    # Preserve the original group ID
    new_aggregation["group_id"] = existing_aggregation.get("group_id", new_aggregation["group_id"])

    # Check if new trigger has higher payout than current claim
    if calculated_payout > existing_claim.amount:
        # Update existing claim with higher payout
        new_aggregation["primary_trigger_id"] = trigger_event.id
        new_aggregation["post_aggregation_payout"] = round(final_payout, 2)

        # Don't create new claim - update existing
        return (False, existing_claim, new_aggregation)
    else:
        # Current trigger is suppressed - just update aggregation metadata
        return (False, existing_claim, new_aggregation)


def update_claim_with_aggregation(
    claim: Claim,
    new_payout: float,
    aggregation_metadata: dict,
    db: Session,
) -> Claim:
    """
    Update an existing claim with new aggregation data.

    Args:
        claim: The claim to update
        new_payout: New payout amount (may be higher due to uplift)
        aggregation_metadata: Updated aggregation metadata
        db: Database session

    Returns:
        Updated Claim
    """
    validation = {}
    try:
        validation = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        pass

    validation["aggregation"] = aggregation_metadata

    # Update claim
    claim.amount = new_payout
    claim.validation_data = json.dumps(validation)

    db.commit()
    db.refresh(claim)

    return claim


def get_aggregation_stats(db: Session) -> dict:
    """
    Get statistics about trigger aggregation.

    Returns dict with:
    - total_aggregated_claims: Claims with aggregation
    - total_triggers_suppressed: Triggers that didn't generate separate claims
    - total_savings: Sum of prevented duplicate payouts
    """
    # Query all claims with aggregation data
    claims = db.query(Claim).filter(
        Claim.validation_data.ilike('%"is_aggregated": true%')
    ).all()

    total_aggregated = 0
    total_suppressed = 0
    total_savings = 0.0

    for claim in claims:
        try:
            validation = json.loads(claim.validation_data or "{}")
            aggregation = validation.get("aggregation", {})

            if aggregation.get("is_aggregated"):
                total_aggregated += 1
                total_suppressed += len(aggregation.get("suppressed_triggers", []))
                total_savings += aggregation.get("savings", 0.0)
        except json.JSONDecodeError:
            continue

    return {
        "total_aggregated_claims": total_aggregated,
        "total_triggers_suppressed": total_suppressed,
        "total_savings": round(total_savings, 2),
        "computed_at": utcnow().isoformat(),
    }


def get_claim_aggregation_details(claim_id: int, db: Session) -> Optional[dict]:
    """
    Get aggregation details for a specific claim.

    Returns the aggregation metadata or None if not found.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        return None

    try:
        validation = json.loads(claim.validation_data or "{}")
        return validation.get("aggregation")
    except json.JSONDecodeError:
        return None
