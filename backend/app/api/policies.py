from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy, PolicyStatus, TIER_CONFIG
from app.models.zone import Zone
from app.schemas.policy import (
    PolicyCreate,
    PolicyResponse,
    PolicyQuote,
    PolicyResponseExtended,
    PolicyRenewRequest,
    PolicyRenewalQuote,
    AutoRenewUpdate,
)
from app.services.auth import get_current_partner
from app.services.premium import calculate_premium, get_all_quotes
from app.services.policy_lifecycle import (
    compute_policy_status,
    get_renewal_quote,
    renew_policy,
    build_extended_response,
    GRACE_PERIOD_HOURS,
)
from app.services.policy_certificate import generate_certificate_pdf, get_certificate_filename

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
            Policy.expires_at > datetime.utcnow(),
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
    now = datetime.utcnow()
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


@router.get("/active", response_model=PolicyResponseExtended)
def get_active_policy(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get the current partner's active policy with lifecycle status."""
    # Use naive UTC datetime for SQLite compatibility
    now = datetime.utcnow()
    grace_cutoff = now - timedelta(hours=GRACE_PERIOD_HOURS)

    # Find policy that is either:
    # 1. Active and not expired
    # 2. Active and in grace period (expired within last 48 hours)
    policy = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > grace_cutoff,  # Include grace period
        )
        .order_by(Policy.expires_at.desc())
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active policy found",
        )

    return build_extended_response(policy)


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
    policy.status = PolicyStatus.CANCELLED
    db.commit()
    db.refresh(policy)

    return policy


@router.get("/{policy_id}/renewal-quote", response_model=PolicyRenewalQuote)
def get_policy_renewal_quote(
    policy_id: int,
    tier: str = None,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get renewal quote for a policy with loyalty discount."""
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

    # Get zone for premium calculation
    zone = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    # Parse tier if provided
    from app.models.policy import PolicyTier
    new_tier = None
    if tier:
        try:
            new_tier = PolicyTier(tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {tier}. Valid tiers are: flex, standard, pro",
            )

    return get_renewal_quote(policy, new_tier, zone)


@router.post("/{policy_id}/renew", response_model=PolicyResponseExtended)
def renew_policy_endpoint(
    policy_id: int,
    renewal_data: PolicyRenewRequest,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Renew a policy, creating a new linked policy."""
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

    # Check if renewal is allowed
    status_info, timing = compute_policy_status(policy)
    if not timing["can_renew"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy cannot be renewed yet. Renewal is available 2 days before expiry or during grace period.",
        )

    # Check for existing future policy (already renewed)
    now = datetime.utcnow()
    existing_future = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.starts_at > now,
        )
        .first()
    )

    if existing_future:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending renewal policy.",
        )

    new_policy = renew_policy(
        policy=policy,
        partner=partner,
        db=db,
        new_tier=renewal_data.tier,
        auto_renew=renewal_data.auto_renew,
    )

    return build_extended_response(new_policy)


@router.patch("/{policy_id}/auto-renew", response_model=PolicyResponse)
def update_auto_renew(
    policy_id: int,
    update_data: AutoRenewUpdate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Toggle auto-renewal setting for a policy."""
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
            detail="Cannot update auto-renew on inactive policy",
        )

    policy.auto_renew = update_data.auto_renew
    db.commit()
    db.refresh(policy)

    return policy


@router.get("/{policy_id}/certificate")
def download_certificate(
    policy_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Download policy certificate as PDF."""
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

    # Get zone name for certificate
    zone_name = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
        if zone:
            zone_name = zone.name

    # Generate PDF
    pdf_bytes = generate_certificate_pdf(policy, partner, zone_name)
    filename = get_certificate_filename(policy)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
