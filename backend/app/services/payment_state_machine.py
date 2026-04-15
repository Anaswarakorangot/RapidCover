"""
Payment State Machine for RapidCover.

Tracks payment states with idempotency keys, retry logic, and reconciliation support.
States are stored in claim.validation_data["payment_state"] to avoid model changes.

State Flow:
    NOT_STARTED → INITIATED → CONFIRMED → (claim.status=PAID)
                           → FAILED → (retry or escalate)
                           → RECONCILE_PENDING → (manual review)
"""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy.orm import Session

from app.models.claim import Claim, ClaimStatus
from app.utils.time_utils import utcnow
from app.models.policy import Policy
from app.models.partner import Partner


class PaymentStatus(str, Enum):
    """Payment state machine states."""
    NOT_STARTED = "not_started"
    INITIATED = "initiated"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    RECONCILE_PENDING = "reconcile_pending"


# Configuration
MAX_PAYMENT_RETRIES = 3
RECONCILE_THRESHOLD_ATTEMPTS = 2  # After this many failures, escalate to reconciliation


def generate_idempotency_key(claim_id: int, attempt_num: int) -> str:
    """
    Generate a unique idempotency key for a payment attempt.

    Format: RC-CLM-{claim_id}-ATT-{attempt_num:03d}
    """
    return f"RC-CLM-{claim_id}-ATT-{attempt_num:03d}"


def _get_payment_state(claim: Claim) -> dict:
    """Get payment state from claim validation_data."""
    try:
        validation = json.loads(claim.validation_data or "{}")
        return validation.get("payment_state", {
            "current_status": PaymentStatus.NOT_STARTED.value,
            "idempotency_key": None,
            "attempts": [],
            "total_attempts": 0,
            "max_retries": MAX_PAYMENT_RETRIES,
        })
    except json.JSONDecodeError:
        return {
            "current_status": PaymentStatus.NOT_STARTED.value,
            "idempotency_key": None,
            "attempts": [],
            "total_attempts": 0,
            "max_retries": MAX_PAYMENT_RETRIES,
        }


def _save_payment_state(claim: Claim, payment_state: dict, db: Session) -> None:
    """Save payment state to claim validation_data."""
    try:
        validation = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        validation = {}

    validation["payment_state"] = payment_state
    claim.validation_data = json.dumps(validation)
    db.commit()
    db.refresh(claim)


def get_payment_status(claim: Claim) -> dict:
    """
    Get current payment status for a claim.

    Returns:
        Dict with current_status, idempotency_key, attempts, etc.
    """
    return _get_payment_state(claim)


def initiate_payment(claim: Claim, db: Session) -> tuple[bool, dict]:
    """
    Initiate a payment attempt for a claim.

    Creates idempotency key and sets status to INITIATED.

    Args:
        claim: The claim to pay
        db: Database session

    Returns:
        (success, payment_attempt_data)
    """
    if claim.status != ClaimStatus.APPROVED:
        return (False, {"error": "Claim must be APPROVED to initiate payment"})

    state = _get_payment_state(claim)

    # Check if already in a non-retryable state
    current_status = state.get("current_status")
    if current_status == PaymentStatus.CONFIRMED.value:
        return (False, {"error": "Payment already confirmed"})
    if current_status == PaymentStatus.RECONCILE_PENDING.value:
        return (False, {"error": "Payment is pending reconciliation"})

    # Generate new attempt
    attempt_num = state.get("total_attempts", 0) + 1

    if attempt_num > MAX_PAYMENT_RETRIES:
        return (False, {"error": f"Maximum retries ({MAX_PAYMENT_RETRIES}) exceeded"})

    idempotency_key = generate_idempotency_key(claim.id, attempt_num)

    attempt_data = {
        "attempt_id": str(uuid.uuid4()),
        "attempt_num": attempt_num,
        "idempotency_key": idempotency_key,
        "initiated_at": utcnow().isoformat(),
        "status": "pending",
        "provider_ref": None,
        "error": None,
        "completed_at": None,
    }

    # Update state
    state["current_status"] = PaymentStatus.INITIATED.value
    state["idempotency_key"] = idempotency_key
    state["total_attempts"] = attempt_num
    state["attempts"].append(attempt_data)

    _save_payment_state(claim, state, db)

    return (True, attempt_data)


def confirm_payment(
    claim: Claim,
    provider_ref: str,
    db: Session,
    additional_data: Optional[dict] = None,
) -> bool:
    """
    Confirm a successful payment.

    Args:
        claim: The claim that was paid
        provider_ref: Reference from payment provider (e.g., Stripe transfer ID)
        db: Database session
        additional_data: Optional extra data to store (e.g., Stripe response)

    Returns:
        True if confirmed successfully
    """
    state = _get_payment_state(claim)

    if state.get("current_status") != PaymentStatus.INITIATED.value:
        return False

    # Update the current attempt
    if state["attempts"]:
        current_attempt = state["attempts"][-1]
        current_attempt["status"] = "success"
        current_attempt["provider_ref"] = provider_ref
        current_attempt["completed_at"] = utcnow().isoformat()
        if additional_data:
            current_attempt["provider_data"] = additional_data

    state["current_status"] = PaymentStatus.CONFIRMED.value

    _save_payment_state(claim, state, db)

    # Update claim status
    claim.status = ClaimStatus.PAID
    claim.paid_at = utcnow()
    claim.upi_ref = provider_ref
    db.commit()
    db.refresh(claim)

    return True


def fail_payment(
    claim: Claim,
    error: str,
    db: Session,
    error_code: Optional[str] = None,
) -> bool:
    """
    Record a failed payment attempt.

    Args:
        claim: The claim with failed payment
        error: Error message
        db: Database session
        error_code: Optional error code from provider

    Returns:
        True if recorded successfully
    """
    state = _get_payment_state(claim)

    if state.get("current_status") != PaymentStatus.INITIATED.value:
        return False

    # Update the current attempt
    if state["attempts"]:
        current_attempt = state["attempts"][-1]
        current_attempt["status"] = "failed"
        current_attempt["error"] = error
        current_attempt["error_code"] = error_code
        current_attempt["completed_at"] = utcnow().isoformat()

    # Determine next status based on attempt count
    total_attempts = state.get("total_attempts", 1)

    if total_attempts >= RECONCILE_THRESHOLD_ATTEMPTS:
        # Escalate to reconciliation after multiple failures
        state["current_status"] = PaymentStatus.RECONCILE_PENDING.value
        state["reconcile_reason"] = f"Auto-escalated after {total_attempts} failed attempts"
        state["escalated_at"] = utcnow().isoformat()
    else:
        # Allow retry
        state["current_status"] = PaymentStatus.FAILED.value

    _save_payment_state(claim, state, db)

    return True


def retry_payment(claim: Claim, db: Session) -> tuple[bool, dict]:
    """
    Retry a failed payment.

    Args:
        claim: The claim to retry payment for
        db: Database session

    Returns:
        (success, payment_attempt_data or error)
    """
    state = _get_payment_state(claim)
    current_status = state.get("current_status")

    # Only allow retry from FAILED status
    if current_status != PaymentStatus.FAILED.value:
        if current_status == PaymentStatus.CONFIRMED.value:
            return (False, {"error": "Payment already confirmed, cannot retry"})
        if current_status == PaymentStatus.RECONCILE_PENDING.value:
            return (False, {"error": "Payment requires reconciliation, cannot auto-retry"})
        if current_status == PaymentStatus.NOT_STARTED.value:
            return (False, {"error": "Payment not yet initiated"})
        return (False, {"error": f"Cannot retry from status: {current_status}"})

    # Check retry limit
    total_attempts = state.get("total_attempts", 0)
    if total_attempts >= MAX_PAYMENT_RETRIES:
        return (False, {"error": f"Maximum retries ({MAX_PAYMENT_RETRIES}) exceeded"})

    # Initiate new attempt
    return initiate_payment(claim, db)


def mark_for_reconciliation(
    claim: Claim,
    reason: str,
    db: Session,
) -> bool:
    """
    Mark a payment for manual reconciliation.

    Args:
        claim: The claim to mark
        reason: Reason for reconciliation
        db: Database session

    Returns:
        True if marked successfully
    """
    state = _get_payment_state(claim)

    state["current_status"] = PaymentStatus.RECONCILE_PENDING.value
    state["reconcile_reason"] = reason
    state["escalated_at"] = utcnow().isoformat()

    _save_payment_state(claim, state, db)

    return True


def reconcile_payment(
    claim: Claim,
    action: str,
    db: Session,
    provider_ref: Optional[str] = None,
    notes: Optional[str] = None,
) -> tuple[bool, dict]:
    """
    Perform manual reconciliation on a payment.

    Args:
        claim: The claim to reconcile
        action: One of "confirm", "reject", "force_paid"
        db: Database session
        provider_ref: Payment reference (required for confirm/force_paid)
        notes: Optional reconciliation notes

    Returns:
        (success, result_data)
    """
    state = _get_payment_state(claim)

    if state.get("current_status") != PaymentStatus.RECONCILE_PENDING.value:
        return (False, {"error": "Claim is not pending reconciliation"})

    reconciliation_record = {
        "action": action,
        "performed_at": utcnow().isoformat(),
        "notes": notes,
        "previous_attempts": state.get("total_attempts", 0),
    }

    if action == "confirm":
        if not provider_ref:
            return (False, {"error": "provider_ref required for confirm action"})

        state["current_status"] = PaymentStatus.CONFIRMED.value
        reconciliation_record["provider_ref"] = provider_ref

        # Update claim
        claim.status = ClaimStatus.PAID
        claim.paid_at = utcnow()
        claim.upi_ref = provider_ref

    elif action == "reject":
        # Keep as reconcile pending but mark as manually rejected
        reconciliation_record["rejected"] = True
        claim.status = ClaimStatus.REJECTED

    elif action == "force_paid":
        # Mark as paid without provider confirmation (e.g., manual bank transfer)
        if not provider_ref:
            provider_ref = f"MANUAL-{utcnow().strftime('%Y%m%d%H%M%S')}"

        state["current_status"] = PaymentStatus.CONFIRMED.value
        reconciliation_record["provider_ref"] = provider_ref
        reconciliation_record["force_paid"] = True

        claim.status = ClaimStatus.PAID
        claim.paid_at = utcnow()
        claim.upi_ref = provider_ref

    else:
        return (False, {"error": f"Unknown action: {action}"})

    state["reconciliation"] = reconciliation_record
    _save_payment_state(claim, state, db)
    db.commit()
    db.refresh(claim)

    return (True, reconciliation_record)


def get_failed_payments(db: Session, limit: int = 50) -> list[dict]:
    """
    Get list of claims with failed payments.

    Returns claims where payment_state.current_status is 'failed'.
    """
    claims = (
        db.query(Claim)
        .filter(
            Claim.status == ClaimStatus.APPROVED,
            Claim.validation_data.ilike('%"current_status": "failed"%'),
        )
        .order_by(Claim.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for claim in claims:
        state = _get_payment_state(claim)
        policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
        partner = db.query(Partner).filter(Partner.id == policy.partner_id).first() if policy else None

        results.append({
            "claim_id": claim.id,
            "amount": claim.amount,
            "partner_name": partner.name if partner else None,
            "partner_phone": partner.phone if partner else None,
            "payment_state": state,
            "created_at": claim.created_at.isoformat(),
        })

    return results


def get_pending_reconciliation(db: Session, limit: int = 50) -> list[dict]:
    """
    Get list of claims pending reconciliation.

    Returns claims where payment_state.current_status is 'reconcile_pending'.
    """
    claims = (
        db.query(Claim)
        .filter(
            Claim.validation_data.ilike('%"current_status": "reconcile_pending"%'),
        )
        .order_by(Claim.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for claim in claims:
        state = _get_payment_state(claim)
        policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
        partner = db.query(Partner).filter(Partner.id == policy.partner_id).first() if policy else None

        results.append({
            "claim_id": claim.id,
            "amount": claim.amount,
            "partner_name": partner.name if partner else None,
            "partner_phone": partner.phone if partner else None,
            "payment_state": state,
            "reconcile_reason": state.get("reconcile_reason"),
            "escalated_at": state.get("escalated_at"),
            "created_at": claim.created_at.isoformat(),
        })

    return results


def get_payment_stats(db: Session) -> dict:
    """
    Get payment processing statistics.

    Returns counts for each payment status.
    """
    from sqlalchemy import func

    # Count by status
    initiated = db.query(func.count(Claim.id)).filter(
        Claim.validation_data.ilike('%"current_status": "initiated"%')
    ).scalar() or 0

    confirmed = db.query(func.count(Claim.id)).filter(
        Claim.validation_data.ilike('%"current_status": "confirmed"%')
    ).scalar() or 0

    failed = db.query(func.count(Claim.id)).filter(
        Claim.validation_data.ilike('%"current_status": "failed"%')
    ).scalar() or 0

    reconcile_pending = db.query(func.count(Claim.id)).filter(
        Claim.validation_data.ilike('%"current_status": "reconcile_pending"%')
    ).scalar() or 0

    return {
        "initiated": initiated,
        "confirmed": confirmed,
        "failed": failed,
        "reconcile_pending": reconcile_pending,
        "computed_at": utcnow().isoformat(),
    }
