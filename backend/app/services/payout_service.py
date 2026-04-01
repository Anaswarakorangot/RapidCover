"""
Payout service for RapidCover.

Handles structured payout processing with full transaction logs,
UPI reference generation, and payout audit trails.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy
from app.models.partner import Partner
from app.models.trigger_event import TriggerEvent, TriggerType
from app.services.notifications import notify_claim_paid

logger = logging.getLogger(__name__)

TRIGGER_TYPE_LABELS = {
    TriggerType.RAIN: "Heavy Rain",
    TriggerType.HEAT: "Extreme Heat",
    TriggerType.AQI: "High AQI",
    TriggerType.SHUTDOWN: "Civic Shutdown",
    TriggerType.CLOSURE: "Store Closure",
}


def generate_upi_ref(policy_id: int, claim_id: int) -> str:
    """Generate a unique UPI transaction reference."""
    epoch = int(datetime.utcnow().timestamp())
    return f"RAPID{policy_id:06d}{claim_id:06d}{epoch % 100000:05d}"


def build_transaction_log(
    claim: Claim,
    policy: Policy,
    partner: Partner,
    trigger: Optional[TriggerEvent],
    upi_ref: str,
    payout_metadata: dict,
) -> dict:
    """Build a structured transaction log for a payout (stored in validation_data)."""
    return {
        "transaction": {
            "ref": upi_ref,
            "channel": "UPI",
            "provider": "RapidCover",
            "amount": claim.amount,
            "currency": "INR",
            "status": "SUCCESS",
            "initiated_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        },
        "claim": {
            "id": claim.id,
            "policy_id": claim.policy_id,
            "trigger_event_id": claim.trigger_event_id,
            "fraud_score": claim.fraud_score,
        },
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "phone": partner.phone,
            "zone_id": partner.zone_id,
        },
        "policy": {
            "id": policy.id,
            "tier": policy.tier,
            "max_daily_payout": policy.max_daily_payout,
            "max_days_per_week": policy.max_days_per_week,
        },
        "trigger": {
            "id": trigger.id if trigger else None,
            "type": trigger.trigger_type.value if trigger else None,
            "label": TRIGGER_TYPE_LABELS.get(trigger.trigger_type, "Unknown") if trigger else None,
            "severity": trigger.severity if trigger else None,
            "zone_id": trigger.zone_id if trigger else None,
            "started_at": trigger.started_at.isoformat() if trigger and trigger.started_at else None,
        },
        "payout_metadata": payout_metadata,
        "version": "1.0",
    }


def process_payout(claim: Claim, db: Session, upi_ref: Optional[str] = None) -> tuple[bool, str, dict]:
    """
    Process a payout for an approved claim.
    Returns (success, upi_ref, transaction_log).
    """
    if claim.status != ClaimStatus.APPROVED:
        logger.warning(f"Cannot pay claim {claim.id} with status {claim.status}")
        return False, "", {}

    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy:
        return False, "", {}

    partner = db.query(Partner).filter(Partner.id == policy.partner_id).first()
    if not partner:
        return False, "", {}

    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()

    if not upi_ref:
        upi_ref = generate_upi_ref(policy.id, claim.id)

    existing = {}
    try:
        existing = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        pass

    payout_metadata = existing.get("payout_calculation", {})
    transaction_log = build_transaction_log(claim, policy, partner, trigger, upi_ref, payout_metadata)

    existing["transaction_log"] = transaction_log
    existing["payout_status"] = "SUCCESS"
    existing["paid_at"] = datetime.utcnow().isoformat()

    claim.status = ClaimStatus.PAID
    claim.upi_ref = upi_ref
    claim.paid_at = datetime.utcnow()
    claim.validation_data = json.dumps(existing)

    db.commit()
    db.refresh(claim)

    logger.info(f"Payout processed: claim={claim.id}, partner={partner.id}, amount=₹{claim.amount}, ref={upi_ref}")
    notify_claim_paid(claim, db)

    return True, upi_ref, transaction_log


def process_bulk_payouts(claim_ids: list[int], db: Session) -> dict:
    """Process payouts for multiple approved claims."""
    results = {"processed": 0, "failed": 0, "skipped": 0, "transactions": []}

    for claim_id in claim_ids:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim or claim.status != ClaimStatus.APPROVED:
            results["skipped"] += 1
            continue

        success, upi_ref, _ = process_payout(claim, db)
        if success:
            results["processed"] += 1
            results["transactions"].append({"claim_id": claim_id, "upi_ref": upi_ref, "amount": claim.amount})
        else:
            results["failed"] += 1
            results["transactions"].append({"claim_id": claim_id, "error": "Payout processing failed"})

    return results


def get_transaction_log(claim: Claim) -> Optional[dict]:
    """Retrieve the stored transaction log for a paid claim."""
    if not claim.validation_data:
        return None
    try:
        return json.loads(claim.validation_data).get("transaction_log")
    except json.JSONDecodeError:
        return None