from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent
from app.models.zone import Zone
from app.schemas.claim import ClaimResponse, ClaimListResponse, ClaimSummary, PayoutMetadata, ClaimExplanationResponse
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


# =============================================================================
# Claim Explanation API  (Person 1 — Task 1)
# =============================================================================

def _build_payout_formula(vd: dict) -> str:
    """Build a human-readable payout formula string from validation_data."""
    pc = vd.get("payout_calculation", {})
    if not pc:
        return ""
    hours = pc.get("disruption_hours")
    rate = pc.get("hourly_rate")
    amount = pc.get("final_payout") or pc.get("adjusted_payout") or pc.get("base_payout")
    sev_mult = pc.get("severity_multiplier")
    riqi_mult = pc.get("riqi_multiplier")

    parts = []
    if hours is not None and rate is not None:
        parts.append(f"{hours} hrs × ₹{rate}/hr")
    if riqi_mult and riqi_mult != 1.0:
        parts.append(f"× {riqi_mult} RIQI")
    if sev_mult and sev_mult != 1.0:
        parts.append(f"× {sev_mult} severity")
    if amount is not None:
        parts.append(f"= ₹{amount}")
    return " ".join(parts) if parts else f"₹{amount}" if amount else ""


def _plain_language_reason(claim: Claim, trigger: TriggerEvent | None, vd: dict, fraud_result: dict) -> str:
    """Build a plain-language explanation string from all available data."""
    status_val = claim.status.value if hasattr(claim.status, "value") else str(claim.status)
    lines = []

    # Trigger context
    if trigger:
        t_type = trigger.trigger_type.value if hasattr(trigger.trigger_type, "value") else str(trigger.trigger_type)
        source_data = {}
        try:
            source_data = json.loads(trigger.source_data) if trigger.source_data else {}
        except Exception:
            pass

        if t_type == "rain":
            mm = source_data.get("rainfall_mm_hr")
            val = f" ({mm}mm/hr)" if mm else ""
            lines.append(f"Heavy rain{val} was detected in your zone.")
        elif t_type == "heat":
            temp = source_data.get("temp_celsius")
            val = f" ({temp}°C)" if temp else ""
            lines.append(f"Extreme heat{val} was detected in your zone.")
        elif t_type == "aqi":
            aqi = source_data.get("aqi")
            val = f" (AQI {aqi})" if aqi else ""
            lines.append(f"Dangerous air quality{val} was detected in your zone.")
        elif t_type == "shutdown":
            lines.append("A civic shutdown was confirmed in your area.")
        elif t_type == "closure":
            lines.append("Your dark store was force-closed.")
        else:
            lines.append(f"A {t_type} trigger event was detected in your zone.")

    # Decision
    if status_val == "paid":
        lines.append(f"Your claim was approved and ₹{claim.amount:.0f} was paid automatically.")
    elif status_val == "pending":
        lines.append("Your claim is under review. No action needed from you.")
    elif status_val == "approved":
        lines.append("Your claim was approved and payment is being processed.")
    elif status_val == "rejected":
        fraud_dec = fraud_result.get("decision", "")
        if fraud_dec == "auto_reject":
            reasons = fraud_result.get("hard_reject_reasons", [])
            if reasons:
                lines.append(f"Claim rejected: {reasons[0]}")
            else:
                lines.append("Claim rejected due to fraud risk signals.")
        else:
            lines.append("Claim could not be processed at this time.")

    # Fraud — only surface if it affected the outcome
    if fraud_result.get("decision") in ("enhanced_validation", "manual_review"):
        lines.append("Your claim required additional verification before processing.")

    return " ".join(lines)


def _extract_source_info(claim: Claim) -> tuple[str | None, list[str], str]:
    """Extract trigger source, data_sources list, and source_mode from source_metadata."""
    trigger_source = None
    data_sources = []
    source_mode = "live"
    try:
        sm = json.loads(claim.source_metadata) if claim.source_metadata else {}
        trigger_source = sm.get("primary_source") or sm.get("source")
        data_sources = sm.get("sources_used") or sm.get("sources") or []
        if sm.get("demo_mode") or sm.get("mode") == "demo":
            source_mode = "demo"
        elif sm.get("mode") == "fallback":
            source_mode = "fallback"
    except Exception:
        pass
    return trigger_source, data_sources, source_mode


def _extract_fraud_result(vd: dict) -> dict:
    """Extract fraud decision from validation_data."""
    fraud = vd.get("fraud", {}) or vd.get("fraud_result", {})
    if not fraud:
        return {"decision": "auto_approve", "fraud_score": 0.0, "hard_reject_reasons": []}
    return {
        "decision": fraud.get("decision", "auto_approve"),
        "fraud_score": fraud.get("score") or fraud.get("fraud_score", 0.0),
        "hard_reject_reasons": fraud.get("hard_reject_reasons", []),
    }


def _fraud_plain_reasons(fraud_result: dict, fraud_score: float) -> list[str]:
    """Build plain-language list of fraud factor notes."""
    reasons = []
    decision = fraud_result.get("decision", "auto_approve")
    hard = fraud_result.get("hard_reject_reasons", [])
    if hard:
        reasons.extend(hard)
    elif decision == "auto_approve":
        reasons.append("All fraud checks passed.")
    elif decision == "enhanced_validation":
        reasons.append(f"Moderate fraud score ({fraud_score:.2f}) — enhanced checks applied.")
    elif decision == "manual_review":
        reasons.append(f"High fraud score ({fraud_score:.2f}) — manual review required.")
    elif decision == "auto_reject":
        reasons.append(f"Very high fraud score ({fraud_score:.2f}) — auto-rejected.")
    return reasons


@router.get("/{claim_id}/explanation", response_model=ClaimExplanationResponse, tags=["claims"])
def get_claim_explanation(
    claim_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    GET /claims/{claim_id}/explanation

    Returns a full human-readable explanation of why a claim was paid,
    pending, or rejected. Includes trigger source, zone match, payout
    formula, fraud decision, and plain-language summary.

    Designed to turn black-box payout logic into something a rider,
    judge, or admin can understand.
    """
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id, Claim.policy_id.in_(policy_ids))
        .first()
    )
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    # Load policy & zone
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    zone: Zone | None = None
    if policy and partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    # Load trigger event
    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()

    # Parse stored blobs
    vd: dict = {}
    try:
        vd = json.loads(claim.validation_data) if claim.validation_data else {}
    except Exception:
        pass

    fraud_result = _extract_fraud_result(vd)
    trigger_source, data_sources, source_mode = _extract_source_info(claim)

    # Derive trigger source from trigger event source_data if source_metadata is sparse
    if not trigger_source and trigger and trigger.source_data:
        try:
            sd = json.loads(trigger.source_data)
            trigger_source = sd.get("source") or sd.get("provider")
        except Exception:
            pass

    # Payment state
    payment_status: str | None = None
    ps = vd.get("payment_state", {})
    if ps:
        payment_status = ps.get("current_status")
    if not payment_status:
        status_val = claim.status.value if hasattr(claim.status, "value") else str(claim.status)
        payment_status = "completed" if status_val == "paid" else status_val

    # Zone match
    zone_match = bool(vd.get("zone_match", True))

    # Payout formula string
    payout_formula = _build_payout_formula(vd)

    # Fraud
    fraud_reasons = _fraud_plain_reasons(fraud_result, float(claim.fraud_score or 0.0))

    # Status
    status_val = claim.status.value if hasattr(claim.status, "value") else str(claim.status)

    # Decision one-liner
    decision_map = {
        "paid": "Claim approved and payment completed.",
        "approved": "Claim approved, payment being processed.",
        "pending": "Claim is under review.",
        "rejected": "Claim was rejected.",
    }
    decision = decision_map.get(status_val, f"Claim status: {status_val}.")

    # Plain language reason
    plain_reason = _plain_language_reason(claim, trigger, vd, fraud_result)

    return ClaimExplanationResponse(
        claim_id=claim.id,
        status=status_val,
        decision=decision,
        trigger_source=trigger_source,
        trigger_type=trigger.trigger_type.value if trigger and hasattr(trigger.trigger_type, "value") else None,
        trigger_started_at=trigger.started_at if trigger else None,
        trigger_ended_at=trigger.ended_at if trigger else None,
        zone_match=zone_match,
        zone_name=zone.name if zone else None,
        zone_code=zone.code if zone else None,
        payout_formula=payout_formula or None,
        amount=claim.amount,
        fraud_decision=fraud_result.get("decision", "auto_approve"),
        fraud_score=float(claim.fraud_score or 0.0),
        fraud_reasons=fraud_reasons,
        payment_status=payment_status,
        upi_ref=claim.upi_ref,
        paid_at=claim.paid_at,
        plain_language_reason=plain_reason,
        source_mode=source_mode,
        data_sources=data_sources,
    )