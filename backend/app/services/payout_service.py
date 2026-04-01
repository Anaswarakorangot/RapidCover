"""
Payout service for RapidCover.

Handles structured payout processing with detailed transaction logs,
UPI reference generation, and payout audit trails.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy
from app.models.partner import Partner
from app.models.trigger_event import TriggerEvent, TriggerType
from app.services.notifications import notify_claim_paid

logger = logging.getLogger(__name__)


# Payout channel configuration
PAYOUT_CHANNEL = "UPI"
PAYOUT_PROVIDER = "RapidCover"


def generate_upi_ref(policy_id: int, claim_id: int) -> str:
    """
    Generate a unique UPI transaction reference.

    Format: RAPID<policy_id:06d><claim_id:06d><epoch_suffix>
    """
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
    """
    Build a structured transaction log entry for a payout.

    This log is stored in validation_data and can be used for:
    - Audit trails
    - Dispute resolution
    - Analytics and reporting
    """
    trigger_labels = {
        TriggerType.RAIN: "Heavy Rain",
        TriggerType.HEAT: "Extreme Heat",
        TriggerType.AQI: "High AQI",
        TriggerType.SHUTDOWN: "Civic Shutdown",
        TriggerType.CLOSURE: "Store Closure",
    }

    transaction = {
        "transaction": {
            "ref": upi_ref,
            "channel": PAYOUT_CHANNEL,
            "provider": PAYOUT_PROVIDER,
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
            "upi_id": getattr(partner, "upi_id", None),
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
            "label": trigger_labels.get(trigger.trigger_type, "Unknown") if trigger else None,
            "severity": trigger.severity if trigger else None,
            "zone_id": trigger.zone_id if trigger else None,
            "started_at": trigger.started_at.isoformat() if trigger and trigger.started_at else None,
        },
        "payout_metadata": payout_metadata,
        "version": "1.0",
    }
    return transaction


def process_payout(
    claim: Claim,
    db: Session,
    upi_ref: Optional[str] = None,
) -> tuple[bool, str, dict]:
    """
    Process a payout for an approved claim.

    Returns:
        (success: bool, upi_ref: str, transaction_log: dict)
    """
    if claim.status != ClaimStatus.APPROVED:
        logger.warning(f"Cannot pay claim {claim.id} with status {claim.status}")
        return False, "", {}

    # Fetch related records for rich transaction log
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy:
        logger.error(f"Policy not found for claim {claim.id}")
        return False, "", {}

    partner = db.query(Partner).filter(Partner.id == policy.partner_id).first()
    if not partner:
        logger.error(f"Partner not found for policy {policy.id}")
        return False, "", {}

    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()

    # Generate UPI reference if not provided
    if not upi_ref:
        upi_ref = generate_upi_ref(policy.id, claim.id)

    # Extract existing payout metadata from validation_data
    existing_validation = {}
    try:
        existing_validation = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        pass

    payout_metadata = existing_validation.get("payout_calculation", {})

    # Build structured transaction log
    transaction_log = build_transaction_log(
        claim=claim,
        policy=policy,
        partner=partner,
        trigger=trigger,
        upi_ref=upi_ref,
        payout_metadata=payout_metadata,
    )

    # Merge transaction log into validation_data
    existing_validation["transaction_log"] = transaction_log
    existing_validation["payout_status"] = "SUCCESS"
    existing_validation["paid_at"] = datetime.utcnow().isoformat()

    # Update claim record
    claim.status = ClaimStatus.PAID
    claim.upi_ref = upi_ref
    claim.paid_at = datetime.utcnow()
    claim.validation_data = json.dumps(existing_validation)

    db.commit()
    db.refresh(claim)

    logger.info(
        f"Payout processed: claim={claim.id}, partner={partner.id}, "
        f"amount=₹{claim.amount}, ref={upi_ref}"
    )

    # Send push notification
    notify_claim_paid(claim, db)

    return True, upi_ref, transaction_log


def process_bulk_payouts(
    claim_ids: list[int],
    db: Session,
) -> dict:
    """
    Process payouts for multiple approved claims in batch.

    Returns summary with success/failure counts and transaction refs.
    """
    results = {
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "transactions": [],
    }

    for claim_id in claim_ids:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            results["skipped"] += 1
            continue

        if claim.status != ClaimStatus.APPROVED:
            results["skipped"] += 1
            continue

        success, upi_ref, log = process_payout(claim, db)
        if success:
            results["processed"] += 1
            results["transactions"].append({
                "claim_id": claim_id,
                "upi_ref": upi_ref,
                "amount": claim.amount,
            })
        else:
            results["failed"] += 1
            results["transactions"].append({
                "claim_id": claim_id,
                "error": "Payout processing failed",
            })

    logger.info(
        f"Bulk payout complete: {results['processed']} processed, "
        f"{results['failed']} failed, {results['skipped']} skipped"
    )
    return results


def get_transaction_log(claim: Claim) -> Optional[dict]:
    """
    Retrieve the transaction log for a paid claim.
    """
    if not claim.validation_data:
        return None
    try:
        data = json.loads(claim.validation_data)
        return data.get("transaction_log")
    except json.JSONDecodeError:
        return None