"""
Zone reassignment service with 24-hour acceptance workflow.

Implements a state machine for zone reassignment proposals:
    proposed ──(partner accepts)──> accepted ──> zone_id updated
        │
        ├──(partner rejects)──> rejected
        │
        └──(24h timeout)──> expired
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.partner import Partner
from app.models.policy import Policy
from app.models.zone import Zone
from app.models.zone_reassignment import ZoneReassignment, ReassignmentStatus
from app.schemas.zone_reassignment import (
    ZoneReassignmentResponse,
    ZoneReassignmentListResponse,
    ZoneReassignmentActionResponse,
)


# Default expiry is 24 hours from proposal
PROPOSAL_EXPIRY_HOURS = 24


def _calculate_premium_adjustment(
    partner: Partner,
    old_zone: Optional[Zone],
    new_zone: Zone,
    db: Session,
) -> tuple[float, int]:
    """
    Calculate premium adjustment for zone reassignment.

    Returns:
        (premium_adjustment, remaining_days)
        - premium_adjustment: Positive = credit (new zone cheaper), Negative = debit (new zone more expensive)
    """
    now = datetime.utcnow()

    # Get current active policy
    active_policy = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > now,
        )
        .first()
    )

    if not active_policy:
        return 0.0, 0

    # Calculate days remaining
    days_remaining = max(0, (active_policy.expires_at - now).days)

    if days_remaining == 0:
        return 0.0, 0

    # Use premium_service to calculate new premium
    from app.services.premium import calculate_premium

    try:
        new_quote = calculate_premium(active_policy.tier, new_zone)
        old_daily_rate = active_policy.weekly_premium / 7
        new_daily_rate = new_quote.final_premium / 7

        # Positive adjustment = credit (old zone was more expensive)
        # Negative adjustment = debit (new zone is more expensive)
        premium_adjustment = round((old_daily_rate - new_daily_rate) * days_remaining, 2)

        return premium_adjustment, days_remaining
    except Exception:
        return 0.0, days_remaining


def _enrich_reassignment_response(
    reassignment: ZoneReassignment,
    db: Session,
) -> ZoneReassignmentResponse:
    """Enrich a reassignment with zone and partner names."""
    now = datetime.utcnow()

    # Calculate hours remaining if proposed
    hours_remaining = None
    if reassignment.status == ReassignmentStatus.PROPOSED:
        remaining = (reassignment.expires_at - now).total_seconds() / 3600
        hours_remaining = max(0, round(remaining, 1))

    # Get related names
    partner = db.query(Partner).filter(Partner.id == reassignment.partner_id).first()
    old_zone = db.query(Zone).filter(Zone.id == reassignment.old_zone_id).first() if reassignment.old_zone_id else None
    new_zone = db.query(Zone).filter(Zone.id == reassignment.new_zone_id).first()

    return ZoneReassignmentResponse(
        id=reassignment.id,
        partner_id=reassignment.partner_id,
        old_zone_id=reassignment.old_zone_id,
        new_zone_id=reassignment.new_zone_id,
        status=reassignment.status,
        premium_adjustment=reassignment.premium_adjustment,
        remaining_days=reassignment.remaining_days,
        proposed_at=reassignment.proposed_at,
        expires_at=reassignment.expires_at,
        accepted_at=reassignment.accepted_at,
        rejected_at=reassignment.rejected_at,
        hours_remaining=hours_remaining,
        old_zone_name=old_zone.name if old_zone else None,
        new_zone_name=new_zone.name if new_zone else None,
        partner_name=partner.name if partner else None,
    )


def propose_reassignment(
    partner_id: int,
    new_zone_id: int,
    db: Session,
) -> tuple[Optional[ZoneReassignmentResponse], Optional[str]]:
    """
    Create a zone reassignment proposal.

    Args:
        partner_id: Partner to reassign
        new_zone_id: Target zone
        db: Database session

    Returns:
        (ZoneReassignmentResponse, None) on success
        (None, error_message) on failure
    """
    # Get partner
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        return None, "Partner not found"

    # Get new zone
    new_zone = db.query(Zone).filter(Zone.id == new_zone_id).first()
    if not new_zone:
        return None, "Zone not found"

    # Check if same zone
    if partner.zone_id == new_zone_id:
        return None, "Partner is already in this zone"

    # Check for existing pending proposal
    existing = (
        db.query(ZoneReassignment)
        .filter(
            ZoneReassignment.partner_id == partner_id,
            ZoneReassignment.status == ReassignmentStatus.PROPOSED,
        )
        .first()
    )
    if existing:
        return None, "Partner already has a pending reassignment proposal"

    # Get old zone
    old_zone = db.query(Zone).filter(Zone.id == partner.zone_id).first() if partner.zone_id else None

    # Calculate premium adjustment
    premium_adjustment, remaining_days = _calculate_premium_adjustment(
        partner, old_zone, new_zone, db
    )

    # Create proposal
    now = datetime.utcnow()
    reassignment = ZoneReassignment(
        partner_id=partner_id,
        old_zone_id=partner.zone_id,
        new_zone_id=new_zone_id,
        status=ReassignmentStatus.PROPOSED,
        premium_adjustment=premium_adjustment,
        remaining_days=remaining_days,
        proposed_at=now,
        expires_at=now + timedelta(hours=PROPOSAL_EXPIRY_HOURS),
    )

    db.add(reassignment)
    db.commit()
    db.refresh(reassignment)

    return _enrich_reassignment_response(reassignment, db), None


def accept_reassignment(
    reassignment_id: int,
    db: Session,
) -> tuple[Optional[ZoneReassignmentActionResponse], Optional[str]]:
    """
    Accept a zone reassignment proposal.

    Args:
        reassignment_id: The proposal to accept
        db: Database session

    Returns:
        (ZoneReassignmentActionResponse, None) on success
        (None, error_message) on failure
    """
    reassignment = db.query(ZoneReassignment).filter(ZoneReassignment.id == reassignment_id).first()
    if not reassignment:
        return None, "Reassignment not found"

    if reassignment.status != ReassignmentStatus.PROPOSED:
        return None, f"Reassignment is not pending (status: {reassignment.status.value})"

    # Check if expired
    now = datetime.utcnow()
    if now > reassignment.expires_at:
        reassignment.status = ReassignmentStatus.EXPIRED
        db.commit()
        return None, "Reassignment proposal has expired"

    # Update reassignment status
    reassignment.status = ReassignmentStatus.ACCEPTED
    reassignment.accepted_at = now

    # Update partner's zone
    partner = db.query(Partner).filter(Partner.id == reassignment.partner_id).first()
    if partner:
        # Log zone history
        zone_history = list(partner.zone_history or [])
        zone_history.append({
            "old_zone_id": reassignment.old_zone_id,
            "new_zone_id": reassignment.new_zone_id,
            "effective_at": now.isoformat(),
            "reassignment_id": reassignment.id,
            "premium_adjustment": reassignment.premium_adjustment,
            "remaining_days": reassignment.remaining_days,
        })
        partner.zone_history = zone_history[-50:]  # Keep last 50 entries
        partner.zone_id = reassignment.new_zone_id

    db.commit()

    return ZoneReassignmentActionResponse(
        id=reassignment.id,
        status=ReassignmentStatus.ACCEPTED,
        message="Zone reassignment accepted successfully",
        zone_updated=True,
        new_zone_id=reassignment.new_zone_id,
    ), None


def reject_reassignment(
    reassignment_id: int,
    db: Session,
) -> tuple[Optional[ZoneReassignmentActionResponse], Optional[str]]:
    """
    Reject a zone reassignment proposal.

    Args:
        reassignment_id: The proposal to reject
        db: Database session

    Returns:
        (ZoneReassignmentActionResponse, None) on success
        (None, error_message) on failure
    """
    reassignment = db.query(ZoneReassignment).filter(ZoneReassignment.id == reassignment_id).first()
    if not reassignment:
        return None, "Reassignment not found"

    if reassignment.status != ReassignmentStatus.PROPOSED:
        return None, f"Reassignment is not pending (status: {reassignment.status.value})"

    # Check if expired
    now = datetime.utcnow()
    if now > reassignment.expires_at:
        reassignment.status = ReassignmentStatus.EXPIRED
        db.commit()
        return None, "Reassignment proposal has expired"

    # Update status
    reassignment.status = ReassignmentStatus.REJECTED
    reassignment.rejected_at = now
    db.commit()

    return ZoneReassignmentActionResponse(
        id=reassignment.id,
        status=ReassignmentStatus.REJECTED,
        message="Zone reassignment rejected",
        zone_updated=False,
    ), None


def get_reassignment(
    reassignment_id: int,
    db: Session,
) -> Optional[ZoneReassignmentResponse]:
    """Get a single reassignment by ID."""
    reassignment = db.query(ZoneReassignment).filter(ZoneReassignment.id == reassignment_id).first()
    if not reassignment:
        return None
    return _enrich_reassignment_response(reassignment, db)


def list_reassignments(
    db: Session,
    partner_id: Optional[int] = None,
    status_filter: Optional[ReassignmentStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> ZoneReassignmentListResponse:
    """
    List zone reassignments with optional filters.

    Args:
        db: Database session
        partner_id: Filter by partner
        status_filter: Filter by status
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        ZoneReassignmentListResponse with reassignments and counts
    """
    query = db.query(ZoneReassignment)

    if partner_id:
        query = query.filter(ZoneReassignment.partner_id == partner_id)

    if status_filter:
        query = query.filter(ZoneReassignment.status == status_filter)

    total = query.count()
    pending_count = (
        db.query(ZoneReassignment)
        .filter(ZoneReassignment.status == ReassignmentStatus.PROPOSED)
        .count()
    )

    reassignments = (
        query
        .order_by(ZoneReassignment.proposed_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    enriched = [_enrich_reassignment_response(r, db) for r in reassignments]

    return ZoneReassignmentListResponse(
        reassignments=enriched,
        total=total,
        pending_count=pending_count,
    )


def expire_stale_proposals(db: Session) -> int:
    """
    Background job to expire proposals past their expiry time.

    Returns number of expired proposals.
    """
    now = datetime.utcnow()

    stale = (
        db.query(ZoneReassignment)
        .filter(
            ZoneReassignment.status == ReassignmentStatus.PROPOSED,
            ZoneReassignment.expires_at < now,
        )
        .all()
    )

    for reassignment in stale:
        reassignment.status = ReassignmentStatus.EXPIRED

    if stale:
        db.commit()

    return len(stale)
