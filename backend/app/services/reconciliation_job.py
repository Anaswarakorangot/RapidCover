"""
Background payment reconciliation job.

Runs periodic checks to:
- retry failed payments that still have retry budget
- escalate permanently failed payments to reconciliation
- escalate stuck initiated payments older than 15 minutes
"""

import logging
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.claim import Claim, ClaimStatus
from app.services.payment_state_machine import (
    MAX_PAYMENT_RETRIES,
    PaymentStatus,
    get_payment_status,
    mark_for_reconciliation,
)
from app.services.payout_service import process_payout

logger = logging.getLogger(__name__)

RECONCILIATION_INTERVAL_SECONDS = 300
STUCK_INITIATED_THRESHOLD_MINUTES = 15


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO timestamp from validation data."""
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def run_reconciliation_cycle(db) -> dict:
    """Run one reconciliation pass using the provided database session."""
    results = {
        "retried": 0,
        "retry_failed": 0,
        "escalated_failed": 0,
        "escalated_stuck": 0,
        "computed_at": datetime.utcnow().isoformat(),
    }

    failed_claims = (
        db.query(Claim)
        .filter(
            Claim.status == ClaimStatus.APPROVED,
            Claim.validation_data.ilike(
                f'%"current_status": "{PaymentStatus.FAILED.value}"%'
            ),
        )
        .all()
    )

    for claim in failed_claims:
        state = get_payment_status(claim)
        if state.get("current_status") != PaymentStatus.FAILED.value:
            continue

        total_attempts = state.get("total_attempts", 0)
        max_retries = state.get("max_retries", MAX_PAYMENT_RETRIES)

        if total_attempts >= max_retries:
            mark_for_reconciliation(
                claim,
                f"Maximum retries exceeded ({total_attempts}/{max_retries})",
                db,
            )
            results["escalated_failed"] += 1
            continue

        success, provider_ref, error_data = process_payout(claim, db)
        if success:
            logger.info(
                f"[reconciliation] Retried claim {claim.id} successfully with ref {provider_ref}"
            )
            results["retried"] += 1
        else:
            logger.warning(
                f"[reconciliation] Retry failed for claim {claim.id}: {error_data}"
            )
            results["retry_failed"] += 1

    initiated_claims = (
        db.query(Claim)
        .filter(
            Claim.status == ClaimStatus.APPROVED,
            Claim.validation_data.ilike(
                f'%"current_status": "{PaymentStatus.INITIATED.value}"%'
            ),
        )
        .all()
    )

    threshold = datetime.utcnow() - timedelta(minutes=STUCK_INITIATED_THRESHOLD_MINUTES)

    for claim in initiated_claims:
        state = get_payment_status(claim)
        if state.get("current_status") != PaymentStatus.INITIATED.value:
            continue

        current_attempt = state.get("attempts", [])[-1] if state.get("attempts") else {}
        initiated_at = _parse_timestamp(current_attempt.get("initiated_at"))

        if initiated_at and initiated_at <= threshold:
            mark_for_reconciliation(
                claim,
                f"Payment stuck in initiated state for more than {STUCK_INITIATED_THRESHOLD_MINUTES} minutes",
                db,
            )
            logger.warning(f"[reconciliation] Escalated stuck initiated claim {claim.id}")
            results["escalated_stuck"] += 1

    return results


def run_reconciliation_job() -> dict:
    """Create a DB session and execute one reconciliation pass."""
    db = SessionLocal()
    try:
        return run_reconciliation_cycle(db)
    finally:
        db.close()
