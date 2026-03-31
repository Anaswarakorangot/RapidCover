from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent
from app.schemas.claim import ClaimResponse, ClaimListResponse, ClaimSummary
from app.services.auth import get_current_partner

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("", response_model=ClaimListResponse)
def get_claims(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status_filter: ClaimStatus | None = None,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get claim history for the current partner."""
    # Get partner's policy IDs
    policy_ids = (
        db.query(Policy.id)
        .filter(Policy.partner_id == partner.id)
        .subquery()
    )

    # Base query
    query = db.query(Claim).filter(Claim.policy_id.in_(policy_ids))

    if status_filter:
        query = query.filter(Claim.status == status_filter)

    # Get total count
    total = query.count()

    # Paginate
    claims = (
        query
        .order_by(Claim.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Enrich with trigger event data
    claim_responses = []
    for claim in claims:
        trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()
        claim_response = ClaimResponse(
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
        )
        claim_responses.append(claim_response)

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
    # Get partner's policy IDs
    policy_ids = (
        db.query(Policy.id)
        .filter(Policy.partner_id == partner.id)
        .subquery()
    )

    # Total claims and paid amount
    total_claims = db.query(Claim).filter(Claim.policy_id.in_(policy_ids)).count()

    paid_result = (
        db.query(func.sum(Claim.amount))
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.status == ClaimStatus.PAID,
        )
        .scalar()
    )
    total_paid = paid_result or 0.0

    # Pending claims
    pending_claims = (
        db.query(Claim)
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]),
        )
        .count()
    )

    pending_result = (
        db.query(func.sum(Claim.amount))
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]),
        )
        .scalar()
    )
    pending_amount = pending_result or 0.0

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
    # Get partner's policy IDs
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    claim = (
        db.query(Claim)
        .filter(
            Claim.id == claim_id,
            Claim.policy_id.in_(policy_ids),
        )
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()

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
    )
