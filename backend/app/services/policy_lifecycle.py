"""
Policy lifecycle management service.

Handles:
- Policy status computation (active, grace period, lapsed, cancelled)
- Renewal quotes with loyalty discounts
- Policy renewal with chain linking
- Claim eligibility checking
- Batch processing of lapsed policies
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.partner import Partner
from app.utils.time_utils import utcnow
from app.models.policy import Policy, PolicyTier, PolicyStatus, TIER_CONFIG
from app.models.zone import Zone
from app.models.trigger_event import TriggerEvent, TriggerType
from app.schemas.policy import (
    PolicyStatus as PolicyStatusSchema,
    PolicyResponseExtended,
    PolicyRenewalQuote,
)
from app.services.premium import calculate_premium


# Constants
GRACE_PERIOD_HOURS = 48
LOYALTY_DISCOUNT_PERCENT = 5
RENEWAL_WINDOW_DAYS = 2  # Can renew starting 2 days before expiry

# Adverse selection: minimum severity to block enrollment
ADVERSE_SELECTION_MIN_SEVERITY = 3


def check_adverse_selection(
    partner: Partner,
    db: Session,
) -> tuple[bool, str]:
    """
    Block policy purchase/renewal during active high-severity events.

    When a high-severity trigger event (severity >= 3) is currently active
    in the partner's zone, new enrollments and renewals are blocked to
    prevent adverse selection (buying insurance AFTER a known event starts).

    This implements the IRDAI-recommended lock-out period.

    Args:
        partner: The partner trying to purchase/renew
        db: Database session

    Returns:
        (allowed: bool, reason: str)
    """
    if not partner.zone_id:
        return (True, "")

    # Check for active high-severity events in partner's zone
    active_events = (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == partner.zone_id,
            TriggerEvent.ended_at.is_(None),  # Still active
            TriggerEvent.severity >= ADVERSE_SELECTION_MIN_SEVERITY,
        )
        .all()
    )

    if active_events:
        event_types = [e.trigger_type.value for e in active_events]
        return (
            False,
            f"Policy purchase blocked: active weather/disruption alert(s) in your zone "
            f"({', '.join(event_types)}). To prevent adverse selection, new enrollments "
            f"are suspended during active high-severity events. Please try again after "
            f"the event subsides.",
        )

    return (True, "")


def compute_policy_status(
    policy: Policy,
) -> Tuple[PolicyStatusSchema, dict]:
    """
    Compute the current status of a policy based on dates.

    Returns (status, timing_info) where timing_info contains:
    - days_until_expiry: Days until policy expires (None if expired)
    - hours_until_grace_ends: Hours left in grace period (None if not in grace)
    - can_renew: Whether renewal is currently allowed
    """
    now = utcnow()

    # Ensure expires_at is timezone-aware for consistent comparison
    expires_at = policy.expires_at
    if expires_at.tzinfo is None:
        from datetime import timezone
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # Calculate grace period end (48 hours after expiry)
    grace_ends_at = expires_at + timedelta(hours=GRACE_PERIOD_HOURS)

    # Check if cancelled
    if not policy.is_active or policy.status == PolicyStatus.CANCELLED:
        return PolicyStatusSchema.CANCELLED, {
            "days_until_expiry": None,
            "hours_until_grace_ends": None,
            "can_renew": False,
        }

    # Check if still active (not expired)
    if now < expires_at:
        days_until = (expires_at - now).days
        # Can renew if within RENEWAL_WINDOW_DAYS of expiry
        can_renew = days_until <= RENEWAL_WINDOW_DAYS
        return PolicyStatusSchema.ACTIVE, {
            "days_until_expiry": days_until,
            "hours_until_grace_ends": None,
            "can_renew": can_renew,
        }

    # Check if in grace period (expired but within 48 hours)
    if now < grace_ends_at:
        hours_left = (grace_ends_at - now).total_seconds() / 3600
        return PolicyStatusSchema.GRACE_PERIOD, {
            "days_until_expiry": None,
            "hours_until_grace_ends": round(hours_left, 1),
            "can_renew": True,
        }

    # Policy has lapsed (past grace period)
    return PolicyStatusSchema.LAPSED, {
        "days_until_expiry": None,
        "hours_until_grace_ends": None,
        "can_renew": False,
    }


def get_renewal_quote(
    policy: Policy,
    new_tier: Optional[PolicyTier],
    zone: Optional[Zone],
) -> PolicyRenewalQuote:
    """
    Calculate renewal quote with loyalty discount.

    Args:
        policy: The policy being renewed
        new_tier: Optional new tier (defaults to current tier)
        zone: Partner's zone for risk adjustment

    Returns:
        PolicyRenewalQuote with 5% loyalty discount applied
    """
    tier = new_tier or policy.tier
    base_quote = calculate_premium(tier, zone)

    # Calculate loyalty discount (5% of final premium after risk adjustment)
    loyalty_discount = round(base_quote.final_premium * LOYALTY_DISCOUNT_PERCENT / 100, 2)
    final_premium = round(base_quote.final_premium - loyalty_discount, 2)

    return PolicyRenewalQuote(
        tier=tier,
        base_premium=base_quote.base_premium,
        risk_adjustment=base_quote.risk_adjustment,
        loyalty_discount=loyalty_discount,
        final_premium=final_premium,
        max_daily_payout=base_quote.max_daily_payout,
        max_days_per_week=base_quote.max_days_per_week,
    )


def renew_policy(
    policy: Policy,
    partner: Partner,
    db: Session,
    new_tier: Optional[PolicyTier] = None,
    auto_renew: bool = True,
) -> Policy:
    """
    Renew a policy, creating a new linked policy.

    Args:
        policy: The policy being renewed
        partner: The partner owning the policy
        db: Database session
        new_tier: Optional tier change
        auto_renew: Auto-renewal preference for new policy

    Returns:
        The newly created policy
    """
    # Get zone for premium calculation
    zone = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    # Get renewal quote
    quote = get_renewal_quote(policy, new_tier, zone)

    # Determine start time:
    # - If current policy is still active, start when it expires
    # - If in grace period or lapsed, start now
    now = utcnow()
    expires_at = policy.expires_at
    # Ensure timezone-aware for consistent comparison
    if expires_at.tzinfo is None:
        from datetime import timezone
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now < expires_at:
        # Policy still active, start new one when old expires
        starts_at = expires_at
    else:
        # In grace period or lapsed, start immediately
        starts_at = now

    # Create new policy linked to the old one
    new_policy = Policy(
        partner_id=partner.id,
        tier=quote.tier,
        weekly_premium=quote.final_premium,
        max_daily_payout=quote.max_daily_payout,
        max_days_per_week=quote.max_days_per_week,
        starts_at=starts_at,
        expires_at=starts_at + timedelta(days=7),
        auto_renew=auto_renew,
        status=PolicyStatus.ACTIVE,
        renewed_from_id=policy.id,
    )

    # Mark old policy as no longer active if it was
    if policy.is_active and now >= expires_at:
        policy.is_active = False
        policy.status = PolicyStatus.LAPSED

    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)

    return new_policy


def is_claim_eligible(policy: Policy) -> bool:
    """
    Check if a policy is eligible for claims.

    Claims are valid for ACTIVE and GRACE_PERIOD status.
    """
    status, _ = compute_policy_status(policy)
    return status in [PolicyStatusSchema.ACTIVE, PolicyStatusSchema.GRACE_PERIOD]


def process_auto_renewals(db: Session) -> list[dict]:
    """
    Process auto-renewals for eligible policies.

    Finds policies where:
    - auto_renew = True
    - is_active = True
    - Expiring within 1 day OR in grace period
    - No existing future renewal policy

    Returns list of renewal results with partner info.
    """
    now = utcnow()

    # Find policies eligible for auto-renewal:
    # - auto_renew enabled
    # - active
    # - expiring within 24 hours OR already in grace period (expired < 48h ago)
    renewal_window = now + timedelta(days=1)  # 1 day ahead
    grace_cutoff = now - timedelta(hours=GRACE_PERIOD_HOURS)

    eligible_policies = (
        db.query(Policy)
        .filter(
            Policy.auto_renew == True,
            Policy.is_active == True,
            Policy.expires_at > grace_cutoff,  # Not lapsed yet
            Policy.expires_at <= renewal_window,  # Expiring soon or already expired
        )
        .all()
    )

    results = []

    for policy in eligible_policies:
        # Check if already has a future renewal
        existing_renewal = (
            db.query(Policy)
            .filter(
                Policy.partner_id == policy.partner_id,
                Policy.renewed_from_id == policy.id,
            )
            .first()
        )

        if existing_renewal:
            continue  # Already renewed, skip

        # Get partner for this policy
        from app.models.partner import Partner
        partner = db.query(Partner).filter(Partner.id == policy.partner_id).first()

        if not partner:
            continue

        # Get zone for premium calculation
        zone = None
        zone_name = "N/A"
        if partner.zone_id:
            zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
            if zone:
                zone_name = zone.name

        try:
            # Renew the policy
            new_policy = renew_policy(
                policy=policy,
                partner=partner,
                db=db,
                new_tier=None,  # Keep same tier
                auto_renew=True,  # Keep auto-renew enabled
            )

            results.append({
                "status": "renewed",
                "partner_id": partner.id,
                "partner_name": partner.name,
                "partner_phone": partner.phone,
                "zone": zone_name,
                "old_policy_id": policy.id,
                "new_policy_id": new_policy.id,
                "tier": new_policy.tier.value,
                "premium": new_policy.weekly_premium,
                "starts_at": new_policy.starts_at.isoformat(),
                "expires_at": new_policy.expires_at.isoformat(),
            })
        except Exception as e:
            results.append({
                "status": "failed",
                "partner_id": partner.id,
                "partner_name": partner.name,
                "old_policy_id": policy.id,
                "error": str(e),
            })

    return results


def update_lapsed_policies(db: Session) -> int:
    """
    Batch job to mark expired policies as lapsed.

    This should be run periodically (e.g., hourly) to update
    policy statuses for policies that have passed their grace period.

    Returns:
        Number of policies marked as lapsed
    """
    # Use naive UTC datetime for SQLite compatibility
    now = utcnow()
    grace_cutoff = now - timedelta(hours=GRACE_PERIOD_HOURS)

    # Find active policies that have expired and passed grace period
    lapsed_policies = (
        db.query(Policy)
        .filter(
            Policy.is_active == True,
            Policy.status.in_([PolicyStatus.ACTIVE, PolicyStatus.GRACE_PERIOD]),
            Policy.expires_at < grace_cutoff,
        )
        .all()
    )

    for policy in lapsed_policies:
        policy.is_active = False
        policy.status = PolicyStatus.LAPSED

    if lapsed_policies:
        db.commit()

    return len(lapsed_policies)


def build_extended_response(policy: Policy) -> PolicyResponseExtended:
    """
    Build an extended policy response with computed fields.
    """
    status, timing_info = compute_policy_status(policy)

    return PolicyResponseExtended(
        id=policy.id,
        partner_id=policy.partner_id,
        tier=policy.tier,
        weekly_premium=policy.weekly_premium,
        max_daily_payout=policy.max_daily_payout,
        max_days_per_week=policy.max_days_per_week,
        starts_at=policy.starts_at,
        expires_at=policy.expires_at,
        is_active=policy.is_active,
        auto_renew=policy.auto_renew,
        created_at=policy.created_at,
        renewed_from_id=policy.renewed_from_id,
        status=status,
        days_until_expiry=timing_info["days_until_expiry"],
        hours_until_grace_ends=timing_info["hours_until_grace_ends"],
        can_renew=timing_info["can_renew"],
    )
