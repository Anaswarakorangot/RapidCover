from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy, TIER_CONFIG
from app.models.zone import Zone
from app.schemas.policy import PolicyCreate, PolicyResponse, PolicyQuote
from app.services.auth import get_current_partner
from app.services.premium import calculate_premium, get_all_quotes

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/quotes", response_model=list[PolicyQuote])
def get_policy_quotes(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get premium quotes for all tiers based on partner's zone."""
    zone = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    return get_all_quotes(zone)


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_data: PolicyCreate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Create a new insurance policy for the current partner."""
    # Check for existing active policy
    existing = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active policy. Wait for it to expire or cancel it first.",
        )

    # Get zone for premium calculation
    zone = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    # Calculate premium
    quote = calculate_premium(policy_data.tier, zone)

    # Create policy (starts now, expires in 7 days)
    now = datetime.now(timezone.utc)
    policy = Policy(
        partner_id=partner.id,
        tier=policy_data.tier,
        weekly_premium=quote.final_premium,
        max_daily_payout=quote.max_daily_payout,
        max_days_per_week=quote.max_days_per_week,
        starts_at=now,
        expires_at=now + timedelta(days=7),
        auto_renew=policy_data.auto_renew,
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return policy


@router.get("/active", response_model=PolicyResponse)
def get_active_policy(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get the current partner's active policy."""
    policy = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active policy found",
        )

    return policy


@router.get("/history", response_model=list[PolicyResponse])
def get_policy_history(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get all policies for the current partner."""
    policies = (
        db.query(Policy)
        .filter(Policy.partner_id == partner.id)
        .order_by(Policy.created_at.desc())
        .all()
    )

    return policies


@router.post("/{policy_id}/cancel", response_model=PolicyResponse)
def cancel_policy(
    policy_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Cancel an active policy."""
    policy = (
        db.query(Policy)
        .filter(
            Policy.id == policy_id,
            Policy.partner_id == partner.id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    if not policy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy is already cancelled",
        )

    policy.is_active = False
    policy.auto_renew = False
    db.commit()
    db.refresh(policy)

    return policy
