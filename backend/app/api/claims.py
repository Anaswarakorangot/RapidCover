from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent
from app.schemas.claim import (
    ClaimResponse, ClaimListResponse, ClaimSummary, PayoutMetadata, ClaimExplanationResponse
)
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


@router.get("/{claim_id}/explanation", response_model=ClaimExplanationResponse)
def get_claim_explanation(
    claim_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Get deep detailed explanation of why a claim was processed the way it was.
    Answers the roadmap trust and explainability gap.
    """
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id, Claim.policy_id.in_(policy_ids))
        .first()
    )

    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    # Extract logic from validation_data and source_metadata
    trigger_source = "Meteorological Corroboration (Manual/Demo)"
    if claim.source_metadata:
        try:
            sm = json.loads(claim.source_metadata)
            trigger_source = sm.get("primary_source", trigger_source)
        except: pass

    payout_formula = f"₹{claim.amount} payout based on policy tier"
    zone_match = True
    fraud_review = "Auto-passed"
    if claim.validation_data:
        try:
            vd = json.loads(claim.validation_data)
            pc = vd.get("payout_calculation")
            if pc:
                payout_formula = f"₹{pc.get('hourly_rate')}/hr x {pc.get('disruption_hours')} hrs x {pc.get('severity_multiplier')} Severity"
            
            fm = vd.get("fraud_metrics")
            if fm:
                fraud_review = f"Score: {claim.fraud_score:.2f} (Threshold 0.70)"
            
            zone_match = vd.get("zone_match", True)
        except: pass

    return ClaimExplanationResponse(
        claim_id=claim.id,
        trigger_source=trigger_source,
        zone_match=zone_match,
        payout_formula=payout_formula,
        fraud_review=fraud_review,
        payment_status=claim.status.value,
        transaction_proof=claim.upi_ref or "Awaiting settlement",
        is_disputed=False,
    )