"""
Tests for payment reconciliation state machine.

Tests payment state transitions, idempotency keys, retry logic,
and manual reconciliation.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.models.claim import ClaimStatus
from app.services.payment_state_machine import (
    PaymentStatus,
    generate_idempotency_key,
    get_payment_status,
    initiate_payment,
    confirm_payment,
    fail_payment,
    retry_payment,
    mark_for_reconciliation,
    reconcile_payment,
    MAX_PAYMENT_RETRIES,
    RECONCILE_THRESHOLD_ATTEMPTS,
)


class TestIdempotencyKey:
    """Test idempotency key generation."""

    def test_key_format(self):
        """Key should follow the RC-CLM-{id}-ATT-{num} format."""
        key = generate_idempotency_key(claim_id=42, attempt_num=1)
        assert key == "RC-CLM-42-ATT-001"

    def test_key_uniqueness_per_attempt(self):
        """Each attempt should have a unique key."""
        key1 = generate_idempotency_key(claim_id=42, attempt_num=1)
        key2 = generate_idempotency_key(claim_id=42, attempt_num=2)
        assert key1 != key2

    def test_key_uniqueness_per_claim(self):
        """Different claims should have different keys."""
        key1 = generate_idempotency_key(claim_id=1, attempt_num=1)
        key2 = generate_idempotency_key(claim_id=2, attempt_num=1)
        assert key1 != key2


class TestPaymentStatusEnum:
    """Test PaymentStatus enum values."""

    def test_all_statuses_defined(self):
        """All expected payment statuses should be defined."""
        expected = ["not_started", "initiated", "confirmed", "failed", "reconcile_pending"]
        for status in expected:
            assert PaymentStatus(status) is not None

    def test_status_values(self):
        """Status values should match expected strings."""
        assert PaymentStatus.NOT_STARTED.value == "not_started"
        assert PaymentStatus.INITIATED.value == "initiated"
        assert PaymentStatus.CONFIRMED.value == "confirmed"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.RECONCILE_PENDING.value == "reconcile_pending"


class TestInitiatePayment:
    """Test payment initiation."""

    @pytest.fixture
    def approved_claim(self, mock_claim):
        """Create an approved claim."""
        mock_claim.status = ClaimStatus.APPROVED
        mock_claim.validation_data = "{}"
        return mock_claim

    def test_initiate_creates_idempotency_key(self, approved_claim, mock_db):
        """Initiation should create an idempotency key."""
        success, data = initiate_payment(approved_claim, mock_db)

        assert success is True
        assert "idempotency_key" in data
        assert data["idempotency_key"].startswith("RC-CLM-")

    def test_initiate_sets_status_to_initiated(self, approved_claim, mock_db):
        """Initiation should set status to INITIATED."""
        success, data = initiate_payment(approved_claim, mock_db)

        assert success is True
        validation = json.loads(approved_claim.validation_data)
        assert validation["payment_state"]["current_status"] == "initiated"

    def test_initiate_records_attempt(self, approved_claim, mock_db):
        """Initiation should record attempt details."""
        success, data = initiate_payment(approved_claim, mock_db)

        assert success is True
        assert data["attempt_num"] == 1
        assert "initiated_at" in data
        assert data["status"] == "pending"

    def test_cannot_initiate_non_approved_claim(self, mock_claim, mock_db):
        """Cannot initiate payment for non-approved claims."""
        mock_claim.status = ClaimStatus.PENDING
        mock_claim.validation_data = "{}"

        success, data = initiate_payment(mock_claim, mock_db)

        assert success is False
        assert "error" in data

    def test_cannot_initiate_already_confirmed(self, approved_claim, mock_db):
        """Cannot initiate payment if already confirmed."""
        approved_claim.validation_data = json.dumps({
            "payment_state": {"current_status": "confirmed"}
        })

        success, data = initiate_payment(approved_claim, mock_db)

        assert success is False
        assert "already confirmed" in data["error"].lower()


class TestConfirmPayment:
    """Test payment confirmation."""

    @pytest.fixture
    def initiated_claim(self, mock_claim):
        """Create a claim with initiated payment."""
        mock_claim.status = ClaimStatus.APPROVED
        mock_claim.validation_data = json.dumps({
            "payment_state": {
                "current_status": "initiated",
                "idempotency_key": "RC-CLM-1-ATT-001",
                "attempts": [{"attempt_id": "abc", "status": "pending"}],
                "total_attempts": 1,
            }
        })
        return mock_claim

    def test_confirm_sets_status_to_confirmed(self, initiated_claim, mock_db):
        """Confirmation should set status to CONFIRMED."""
        success = confirm_payment(initiated_claim, "tr_abc123", mock_db)

        assert success is True
        validation = json.loads(initiated_claim.validation_data)
        assert validation["payment_state"]["current_status"] == "confirmed"

    def test_confirm_updates_claim_status(self, initiated_claim, mock_db):
        """Confirmation should update claim to PAID status."""
        confirm_payment(initiated_claim, "tr_abc123", mock_db)

        assert initiated_claim.status == ClaimStatus.PAID
        assert initiated_claim.upi_ref == "tr_abc123"
        assert initiated_claim.paid_at is not None

    def test_confirm_records_provider_ref(self, initiated_claim, mock_db):
        """Confirmation should record provider reference in attempt."""
        confirm_payment(initiated_claim, "tr_abc123", mock_db)

        validation = json.loads(initiated_claim.validation_data)
        last_attempt = validation["payment_state"]["attempts"][-1]
        assert last_attempt["provider_ref"] == "tr_abc123"
        assert last_attempt["status"] == "success"

    def test_cannot_confirm_non_initiated(self, mock_claim, mock_db):
        """Cannot confirm payment that wasn't initiated."""
        mock_claim.validation_data = json.dumps({
            "payment_state": {"current_status": "not_started"}
        })

        success = confirm_payment(mock_claim, "tr_abc123", mock_db)

        assert success is False


class TestFailPayment:
    """Test payment failure recording."""

    @pytest.fixture
    def initiated_claim(self, mock_claim):
        """Create a claim with initiated payment."""
        mock_claim.status = ClaimStatus.APPROVED
        mock_claim.validation_data = json.dumps({
            "payment_state": {
                "current_status": "initiated",
                "attempts": [{"attempt_id": "abc", "status": "pending"}],
                "total_attempts": 1,
            }
        })
        return mock_claim

    def test_fail_records_error(self, initiated_claim, mock_db):
        """Failure should record error message."""
        fail_payment(initiated_claim, "Insufficient funds", mock_db)

        validation = json.loads(initiated_claim.validation_data)
        last_attempt = validation["payment_state"]["attempts"][-1]
        assert last_attempt["error"] == "Insufficient funds"
        assert last_attempt["status"] == "failed"

    def test_fail_sets_status_to_failed(self, initiated_claim, mock_db):
        """First failure should set status to FAILED."""
        fail_payment(initiated_claim, "Error", mock_db)

        validation = json.loads(initiated_claim.validation_data)
        assert validation["payment_state"]["current_status"] == "failed"

    def test_fail_escalates_after_threshold(self, mock_claim, mock_db):
        """Should escalate to reconciliation after threshold failures."""
        mock_claim.status = ClaimStatus.APPROVED
        mock_claim.validation_data = json.dumps({
            "payment_state": {
                "current_status": "initiated",
                "attempts": [{"attempt_id": "a1"}, {"attempt_id": "a2"}],
                "total_attempts": RECONCILE_THRESHOLD_ATTEMPTS,
            }
        })

        fail_payment(mock_claim, "Error", mock_db)

        validation = json.loads(mock_claim.validation_data)
        assert validation["payment_state"]["current_status"] == "reconcile_pending"


class TestRetryPayment:
    """Test payment retry functionality."""

    @pytest.fixture
    def failed_claim(self, mock_claim):
        """Create a claim with failed payment."""
        mock_claim.status = ClaimStatus.APPROVED
        mock_claim.validation_data = json.dumps({
            "payment_state": {
                "current_status": "failed",
                "attempts": [{"attempt_id": "abc", "status": "failed"}],
                "total_attempts": 1,
                "max_retries": MAX_PAYMENT_RETRIES,
            }
        })
        return mock_claim

    def test_retry_creates_new_attempt(self, failed_claim, mock_db):
        """Retry should create a new payment attempt."""
        success, data = retry_payment(failed_claim, mock_db)

        assert success is True
        assert data["attempt_num"] == 2

    def test_retry_generates_new_idempotency_key(self, failed_claim, mock_db):
        """Retry should generate a new idempotency key."""
        success, data = retry_payment(failed_claim, mock_db)

        assert data["idempotency_key"] == "RC-CLM-1-ATT-002"

    def test_cannot_retry_confirmed_payment(self, mock_claim, mock_db):
        """Cannot retry a confirmed payment."""
        mock_claim.validation_data = json.dumps({
            "payment_state": {"current_status": "confirmed"}
        })

        success, data = retry_payment(mock_claim, mock_db)

        assert success is False
        assert "already confirmed" in data["error"].lower()

    def test_cannot_retry_reconcile_pending(self, mock_claim, mock_db):
        """Cannot auto-retry a payment pending reconciliation."""
        mock_claim.validation_data = json.dumps({
            "payment_state": {"current_status": "reconcile_pending"}
        })

        success, data = retry_payment(mock_claim, mock_db)

        assert success is False
        assert "reconciliation" in data["error"].lower()

    def test_cannot_exceed_max_retries(self, mock_claim, mock_db):
        """Cannot retry beyond maximum attempts."""
        mock_claim.status = ClaimStatus.APPROVED
        mock_claim.validation_data = json.dumps({
            "payment_state": {
                "current_status": "failed",
                "total_attempts": MAX_PAYMENT_RETRIES,
            }
        })

        success, data = retry_payment(mock_claim, mock_db)

        assert success is False
        assert "maximum retries" in data["error"].lower()


class TestReconciliation:
    """Test manual reconciliation functionality."""

    @pytest.fixture
    def reconcile_pending_claim(self, mock_claim):
        """Create a claim pending reconciliation."""
        mock_claim.status = ClaimStatus.APPROVED
        mock_claim.validation_data = json.dumps({
            "payment_state": {
                "current_status": "reconcile_pending",
                "reconcile_reason": "Multiple failures",
                "attempts": [{"attempt_id": "a1"}, {"attempt_id": "a2"}],
                "total_attempts": 2,
            }
        })
        return mock_claim

    def test_reconcile_confirm(self, reconcile_pending_claim, mock_db):
        """Reconcile with confirm action should mark as paid."""
        success, result = reconcile_payment(
            reconcile_pending_claim, "confirm", mock_db, provider_ref="manual_ref"
        )

        assert success is True
        assert reconcile_pending_claim.status == ClaimStatus.PAID
        assert reconcile_pending_claim.upi_ref == "manual_ref"

    def test_reconcile_reject(self, reconcile_pending_claim, mock_db):
        """Reconcile with reject action should reject claim."""
        success, result = reconcile_payment(
            reconcile_pending_claim, "reject", mock_db
        )

        assert success is True
        assert reconcile_pending_claim.status == ClaimStatus.REJECTED

    def test_reconcile_force_paid(self, reconcile_pending_claim, mock_db):
        """Reconcile with force_paid should mark as paid without provider ref."""
        success, result = reconcile_payment(
            reconcile_pending_claim, "force_paid", mock_db
        )

        assert success is True
        assert reconcile_pending_claim.status == ClaimStatus.PAID
        assert reconcile_pending_claim.upi_ref.startswith("MANUAL-")
        assert result["force_paid"] is True

    def test_reconcile_confirm_requires_provider_ref(self, reconcile_pending_claim, mock_db):
        """Confirm action requires provider_ref."""
        success, result = reconcile_payment(
            reconcile_pending_claim, "confirm", mock_db, provider_ref=None
        )

        assert success is False
        assert "provider_ref required" in result["error"]

    def test_reconcile_invalid_action(self, reconcile_pending_claim, mock_db):
        """Invalid action should fail."""
        success, result = reconcile_payment(
            reconcile_pending_claim, "invalid_action", mock_db
        )

        assert success is False
        assert "Unknown action" in result["error"]

    def test_cannot_reconcile_non_pending(self, mock_claim, mock_db):
        """Cannot reconcile a claim not pending reconciliation."""
        mock_claim.validation_data = json.dumps({
            "payment_state": {"current_status": "confirmed"}
        })

        success, result = reconcile_payment(mock_claim, "confirm", mock_db)

        assert success is False


class TestMarkForReconciliation:
    """Test manual escalation to reconciliation."""

    def test_mark_sets_reconcile_pending(self, mock_claim, mock_db):
        """Marking should set status to reconcile_pending."""
        mock_claim.validation_data = json.dumps({
            "payment_state": {"current_status": "failed"}
        })

        mark_for_reconciliation(mock_claim, "Manual escalation", mock_db)

        validation = json.loads(mock_claim.validation_data)
        assert validation["payment_state"]["current_status"] == "reconcile_pending"
        assert validation["payment_state"]["reconcile_reason"] == "Manual escalation"

    def test_mark_records_timestamp(self, mock_claim, mock_db):
        """Marking should record escalation timestamp."""
        mock_claim.validation_data = "{}"

        mark_for_reconciliation(mock_claim, "Test", mock_db)

        validation = json.loads(mock_claim.validation_data)
        assert "escalated_at" in validation["payment_state"]


class TestGetPaymentStatus:
    """Test payment status retrieval."""

    def test_returns_default_for_new_claim(self, mock_claim):
        """New claims should return default state."""
        mock_claim.validation_data = "{}"

        status = get_payment_status(mock_claim)

        assert status["current_status"] == "not_started"
        assert status["attempts"] == []
        assert status["total_attempts"] == 0

    def test_returns_stored_state(self, mock_claim):
        """Should return stored payment state."""
        mock_claim.validation_data = json.dumps({
            "payment_state": {
                "current_status": "confirmed",
                "idempotency_key": "RC-CLM-1-ATT-001",
                "total_attempts": 1,
            }
        })

        status = get_payment_status(mock_claim)

        assert status["current_status"] == "confirmed"
        assert status["idempotency_key"] == "RC-CLM-1-ATT-001"
