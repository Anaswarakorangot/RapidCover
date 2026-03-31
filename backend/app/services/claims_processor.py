"""
Claims auto-creation processor.

When a trigger event fires, this service:
1. Finds all active policies in the affected zone
2. Validates each partner (GPS coherence, no activity paradox)
3. Calculates payout amount (based on policy tier and disruption duration)
4. Computes fraud score
5. Creates claims with appropriate status
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.partner import Partner
from app.models.policy import Policy, TIER_CONFIG
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent, TriggerType
from app.models.zone import Zone
from app.services.fraud_detector import calculate_fraud_score, FRAUD_THRESHOLDS
from app.services.notifications import (
    notify_claim_created,
    notify_claim_approved,
    notify_claim_paid,
    notify_claim_rejected,
)
from app.config import get_settings


# Payout configuration
HOURLY_PAYOUT_RATES = {
    TriggerType.RAIN: 50,      # ₹50/hour
    TriggerType.HEAT: 40,      # ₹40/hour
    TriggerType.AQI: 45,       # ₹45/hour
    TriggerType.SHUTDOWN: 60,  # ₹60/hour (civic shutdowns are more impactful)
    TriggerType.CLOSURE: 55,   # ₹55/hour
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


def calculate_payout_amount(
    trigger_event: TriggerEvent,
    policy: Policy,
    disruption_hours: Optional[float] = None,
) -> float:
    """
    Calculate payout amount based on trigger type, duration, and policy limits.

    Returns payout amount in INR.
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

    # Apply policy daily limit
    daily_limit = policy.max_daily_payout
    final_payout = min(adjusted_payout, daily_limit)

    return round(final_payout, 2)


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


def get_eligible_policies(zone_id: int, db: Session) -> list[tuple[Policy, Partner]]:
    """
    Get all active policies for partners in a zone.

    Returns list of (Policy, Partner) tuples.
    """
    now = datetime.utcnow()

    results = (
        db.query(Policy, Partner)
        .join(Partner, Policy.partner_id == Partner.id)
        .filter(
            Partner.zone_id == zone_id,
            Partner.is_active == True,
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .all()
    )

    return results


def process_trigger_event(
    trigger_event: TriggerEvent,
    db: Session,
    disruption_hours: Optional[float] = None,
) -> list[Claim]:
    """
    Process a trigger event and create claims for eligible partners.

    Returns list of created claims.
    """
    zone_id = trigger_event.zone_id
    created_claims = []

    # Get eligible policies in the affected zone
    eligible = get_eligible_policies(zone_id, db)

    for policy, partner in eligible:
        # Calculate payout amount
        payout = calculate_payout_amount(trigger_event, policy, disruption_hours)

        # Check daily limit
        within_daily, daily_remaining = check_daily_limit(partner, policy, payout, db)
        if not within_daily:
            payout = daily_remaining  # Reduce to remaining limit

        if payout <= 0:
            continue  # Skip if no payout available

        # Check weekly limit
        has_weekly_days, _ = check_weekly_limit(partner, policy, db)
        if not has_weekly_days:
            continue  # Skip if weekly days exhausted

        # Calculate fraud score
        fraud_result = calculate_fraud_score(partner, trigger_event, db)

        # Determine claim status based on fraud score
        if fraud_result["recommendation"] == "approve":
            status = ClaimStatus.APPROVED
        elif fraud_result["recommendation"] == "reject":
            status = ClaimStatus.REJECTED
        else:
            status = ClaimStatus.PENDING

        # Build validation data
        validation_data = {
            "fraud_analysis": fraud_result,
            "daily_limit_check": {"within_limit": within_daily, "remaining": daily_remaining},
            "payout_calculation": {
                "disruption_hours": disruption_hours or DEFAULT_DISRUPTION_HOURS,
                "hourly_rate": HOURLY_PAYOUT_RATES.get(trigger_event.trigger_type, 50),
                "severity_multiplier": 1.0 + (trigger_event.severity - 1) * 0.125,
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

        # Auto-payout for demo mode: immediately pay approved claims
        settings = get_settings()
        if settings.auto_payout_enabled and claim.status == ClaimStatus.APPROVED:
            claim.status = ClaimStatus.PAID
            claim.upi_ref = f"RAPID{policy.id:06d}{int(datetime.utcnow().timestamp())}"
            claim.paid_at = datetime.utcnow()

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
