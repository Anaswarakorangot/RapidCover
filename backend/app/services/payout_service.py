"""
Payout service for RapidCover.

Handles structured payout processing with full transaction logs,
UPI reference generation, payout audit trails, and city-level caps.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy
from app.models.partner import Partner
from app.models.zone import Zone
from app.models.trigger_event import TriggerEvent, TriggerType
from app.services.notifications import notify_claim_paid
from app.services.payment_state_machine import (
    initiate_payment,
    confirm_payment,
    fail_payment,
    get_payment_status,
    PaymentStatus,
)

logger = logging.getLogger(__name__)

# City-level hard cap configuration
CITY_HARD_CAP_RATIO = 1.20  # 120% - Reinsurance activates above this

TRIGGER_TYPE_LABELS = {
    TriggerType.RAIN: "Heavy Rain",
    TriggerType.HEAT: "Extreme Heat",
    TriggerType.AQI: "High AQI",
    TriggerType.SHUTDOWN: "Civic Shutdown",
    TriggerType.CLOSURE: "Store Closure",
}


def check_city_hard_cap(partner: Partner, db: Session, days: int = 7) -> tuple[bool, float, float]:
    """
    Check if city-level payout hard cap has been reached.

    Reinsurance activates when city payouts exceed 120% of premiums collected.

    Args:
        partner: The partner to check (uses their zone to determine city)
        db: Database session
        days: Number of days to look back (default 7 for weekly)

    Returns tuple of:
        - is_capped: bool - True if city is at/above 120% cap
        - current_ratio: float - Current BCR ratio
        - remaining_capacity: float - Amount in INR that can still be paid out before cap
    """
    if not partner.zone_id:
        # Partner not assigned to zone, allow payout
        return (False, 0.0, float('inf'))

    # Get partner's zone and city
    zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
    if not zone:
        return (False, 0.0, float('inf'))

    city = zone.city
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all zones in the city
    city_zones = db.query(Zone).filter(Zone.city.ilike(f"%{city}%")).all()
    zone_ids = [z.id for z in city_zones]

    if not zone_ids:
        return (False, 0.0, float('inf'))

    # Get partners in these zones
    partner_ids = [
        p[0] for p in
        db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids)).all()
    ]

    if not partner_ids:
        return (False, 0.0, float('inf'))

    # Calculate total premiums collected this period
    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0.0

    # Calculate total claims paid this period
    total_claims_paid = (
        db.query(func.sum(Claim.amount))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id.in_(partner_ids),
            Claim.status == ClaimStatus.PAID,
            Claim.paid_at >= period_start,
            Claim.paid_at <= now,
        )
        .scalar()
    ) or 0.0

    # Calculate current ratio
    current_ratio = total_claims_paid / total_premiums if total_premiums > 0 else 0.0

    # Calculate remaining capacity (up to 120% of premiums)
    max_payout = total_premiums * CITY_HARD_CAP_RATIO
    remaining_capacity = max(0, max_payout - total_claims_paid)

    # Check if capped
    is_capped = current_ratio >= CITY_HARD_CAP_RATIO

    logger.info(
        f"City hard cap check for {city}: "
        f"premiums={total_premiums:.2f}, claims={total_claims_paid:.2f}, "
        f"ratio={current_ratio:.2%}, capped={is_capped}"
    )

    return (is_capped, round(current_ratio, 4), round(remaining_capacity, 2))


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
    # Determine payout channel
    primary_channel = "UPI/Stripe" if partner.upi_id else "IMPS/Bank"
    
    return {
        "transaction": {
            "ref": upi_ref,
            "channel": primary_channel,
            "provider": "Stripe Connect Mock" if partner.upi_id else "IMPS Gateway Mock",
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

from app.config import get_settings

import uuid
import time

def process_stripe_payout_mock(partner: Partner, amount: float, claim_id: int) -> tuple[bool, str, dict]:
    """Simulate a payout via Stripe API (Mock)."""
    # Simulate API latency
    time.sleep(0.5)
    
    transfer_id = f"tr_{uuid.uuid4().hex[:24]}"
    
    stripe_data = {
        "id": transfer_id,
        "object": "transfer",
        "amount": int(amount * 100),
        "currency": "inr",
        "destination": f"acct_{partner.id}mock",
        "description": f"RapidCover Claim #{claim_id}",
        "status": "paid"
    }
    
    return True, transfer_id, {"stripe_response": stripe_data}


def process_payout(
    claim: Claim,
    db: Session,
    upi_ref: Optional[str] = None,
    skip_hard_cap_check: bool = False,
) -> tuple[bool, str, dict]:
    """
    Process a payout for an approved claim.

    Uses the payment state machine for idempotency and retry tracking.
    Checks city-level 120% hard cap before processing unless skip_hard_cap_check=True.

    Returns (success, upi_ref, transaction_log).
    On failure, upi_ref contains error reason if hard cap blocked.
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

    # Check city-level 120% hard cap
    if not skip_hard_cap_check:
        is_capped, current_ratio, remaining_capacity = check_city_hard_cap(partner, db)
        if is_capped:
            logger.warning(
                f"City hard cap reached for claim {claim.id}. "
                f"Current ratio: {current_ratio:.2%}, claim amount: ₹{claim.amount}"
            )
            return False, f"CITY_CAP_REACHED:{current_ratio:.2%}", {
                "error": "city_hard_cap_reached",
                "current_ratio": current_ratio,
                "cap_ratio": CITY_HARD_CAP_RATIO,
                "remaining_capacity": remaining_capacity,
                "claim_amount": claim.amount,
            }

        # If claim amount exceeds remaining capacity, reduce to capacity
        if claim.amount > remaining_capacity and remaining_capacity > 0:
            logger.info(
                f"Reducing claim {claim.id} from ₹{claim.amount} to ₹{remaining_capacity} "
                f"due to city cap (ratio: {current_ratio:.2%})"
            )
            claim.amount = remaining_capacity

    # Initiate payment via state machine (creates idempotency key)
    init_success, init_data = initiate_payment(claim, db)
    if not init_success:
        # Check if already confirmed (idempotent success)
        payment_state = get_payment_status(claim)
        if payment_state.get("current_status") == PaymentStatus.CONFIRMED.value:
            logger.info(f"Claim {claim.id} already confirmed (idempotent)")
            return True, claim.upi_ref or "", {"already_confirmed": True}
        logger.warning(f"Payment initiation failed for claim {claim.id}: {init_data}")
        return False, "", init_data

    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()

    existing = {}
    try:
        existing = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        pass
    payout_metadata = existing.get("payout_calculation", {})

    settings = get_settings()
    stripe_success = False
    stripe_error = None

    if not upi_ref:
        # Utilize Stripe mock if UPI exists, else IMPS mock
        try:
            if partner.upi_id:
                stripe_success, tr_ref, stripe_data = process_stripe_payout_mock(partner, claim.amount, claim.id)
                if stripe_success:
                    upi_ref = tr_ref
                    payout_metadata["stripe"] = stripe_data
                else:
                    stripe_error = "Stripe mock returned failure"
            else:
                # IMPS Fallback
                logger.info(f"Using IMPS fallback for partner {partner.id} (no UPI)")
                upi_ref = f"IMPS{uuid.uuid4().hex[:12].upper()}"
                payout_metadata["imps"] = {
                    "bank_name": partner.bank_name,
                    "account_number": f"****{partner.account_number[-4:]}" if partner.account_number else None,
                    "ifsc": partner.ifsc_code
                }
                stripe_success = True  # Consider IMPS successful immediately
        except Exception as e:
            stripe_success = False
            stripe_error = str(e)
            logger.error(f"Payout exception for claim {claim.id}: {e}")

    if not stripe_success and not upi_ref:
        # Payment failed - record failure in state machine
        fail_payment(claim, stripe_error or "Payment provider failure", db)
        logger.warning(f"Payment failed for claim {claim.id}: {stripe_error}")
        return False, "", {"error": stripe_error or "Payment failed"}

    # If no upi_ref yet (shouldn't happen but fallback)
    if not upi_ref:
        upi_ref = generate_upi_ref(policy.id, claim.id)

    # Confirm payment in state machine
    confirm_success = confirm_payment(
        claim, upi_ref, db,
        additional_data=payout_metadata.get("stripe") or payout_metadata.get("imps"),
    )

    if not confirm_success:
        logger.warning(f"Payment confirmation failed for claim {claim.id}")
        return False, "", {"error": "Payment confirmation failed"}

    transaction_log = build_transaction_log(claim, policy, partner, trigger, upi_ref, payout_metadata)

    # Add hard cap check info to transaction log
    if not skip_hard_cap_check:
        is_capped, current_ratio, remaining_capacity = check_city_hard_cap(partner, db)
        transaction_log["city_cap_check"] = {
            "current_ratio": current_ratio,
            "cap_ratio": CITY_HARD_CAP_RATIO,
            "remaining_capacity_after": remaining_capacity - claim.amount,
            "checked_at": datetime.utcnow().isoformat(),
        }

    # Update validation_data with transaction log (claim already updated by confirm_payment)
    try:
        existing = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        existing = {}

    existing["transaction_log"] = transaction_log
    existing["payout_status"] = "SUCCESS"
    existing["paid_at"] = datetime.utcnow().isoformat()
    claim.validation_data = json.dumps(existing)

    db.commit()
    db.refresh(claim)

    logger.info(f"Payout processed: claim={claim.id}, partner={partner.id}, amount=Rs.{claim.amount}, ref={upi_ref}")
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
