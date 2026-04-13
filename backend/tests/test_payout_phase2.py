import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.claim import ClaimStatus
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.trigger_event import TriggerEvent
from app.services.payment_state_machine import PaymentStatus
from app.services.payout_service import process_payout
from app.services.reconciliation_job import run_reconciliation_cycle


def _query_for(value):
    query = MagicMock()
    query.filter.return_value.first.return_value = value
    return query


def test_process_payout_prefers_razorpay_when_configured(mock_db, mock_claim, mock_partner, mock_policy, mock_trigger_event):
    mock_claim.status = ClaimStatus.APPROVED
    mock_claim.validation_data = "{}"
    mock_policy.max_days_per_week = 3

    def query_side_effect(model):
        mapping = {
            Policy: _query_for(mock_policy),
            Partner: _query_for(mock_partner),
            TriggerEvent: _query_for(mock_trigger_event),
        }
        return mapping[model]

    mock_db.query.side_effect = query_side_effect

    with patch("app.services.payout_service.get_settings", return_value=SimpleNamespace(razorpay_key_id="rzp_test", stripe_secret_key="sk_test")), \
         patch("app.services.payout_service.check_city_hard_cap", return_value=(False, 0.0, 9999.0)), \
         patch("app.services.payout_service.initiate_payment", return_value=(True, {"attempt_num": 1})), \
         patch("app.services.payout_service.confirm_payment", return_value=True) as confirm_mock, \
         patch("app.services.payout_service.notify_claim_paid"), \
         patch("app.services.payout_service.process_razorpay_payout_mock", return_value=(True, "pout_test_123", {"razorpay_response": {"id": "pout_test_123"}})) as razorpay_mock, \
         patch("app.services.payout_service.process_stripe_payout_mock") as stripe_mock:
        success, payout_ref, transaction_log = process_payout(mock_claim, mock_db)

    assert success is True
    assert payout_ref == "pout_test_123"
    assert "razorpay" in transaction_log["payout_metadata"]
    razorpay_mock.assert_called_once()
    stripe_mock.assert_not_called()
    assert confirm_mock.call_args.kwargs["additional_data"] == {"razorpay_response": {"id": "pout_test_123"}}


def test_process_payout_falls_back_to_direct_transfer_without_provider_keys(mock_db, mock_claim, mock_partner, mock_policy, mock_trigger_event):
    mock_claim.status = ClaimStatus.APPROVED
    mock_claim.validation_data = "{}"
    mock_policy.max_days_per_week = 3
    mock_partner.bank_name = "Demo Bank"
    mock_partner.account_number = "1234567890"
    mock_partner.ifsc_code = "DEMO0001234"

    def query_side_effect(model):
        mapping = {
            Policy: _query_for(mock_policy),
            Partner: _query_for(mock_partner),
            TriggerEvent: _query_for(mock_trigger_event),
        }
        return mapping[model]

    mock_db.query.side_effect = query_side_effect

    with patch("app.services.payout_service.get_settings", return_value=SimpleNamespace(razorpay_key_id="", stripe_secret_key="")), \
         patch("app.services.payout_service.check_city_hard_cap", return_value=(False, 0.0, 9999.0)), \
         patch("app.services.payout_service.initiate_payment", return_value=(True, {"attempt_num": 1})), \
         patch("app.services.payout_service.confirm_payment", return_value=True) as confirm_mock, \
         patch("app.services.payout_service.notify_claim_paid"):
        success, payout_ref, transaction_log = process_payout(mock_claim, mock_db)

    assert success is True
    assert payout_ref.startswith("RAPID")
    assert transaction_log["transaction"]["provider"] == "Direct Transfer Mock"
    assert "direct_transfer" in transaction_log["payout_metadata"]
    assert confirm_mock.call_args.kwargs["additional_data"]["mode"] == "UPI"


def test_reconciliation_cycle_retries_failed_and_escalates_stuck(mock_db, mock_claim):
    failed_claim = MagicMock()
    failed_claim.id = 11
    failed_claim.status = ClaimStatus.APPROVED
    failed_claim.validation_data = json.dumps({
        "payment_state": {
            "current_status": PaymentStatus.FAILED.value,
            "total_attempts": 1,
            "max_retries": 3,
            "attempts": [{"attempt_id": "a1", "status": "failed"}],
        }
    })

    stuck_claim = MagicMock()
    stuck_claim.id = 12
    stuck_claim.status = ClaimStatus.APPROVED
    stuck_claim.validation_data = json.dumps({
        "payment_state": {
            "current_status": PaymentStatus.INITIATED.value,
            "total_attempts": 1,
            "attempts": [{
                "attempt_id": "a2",
                "status": "pending",
                "initiated_at": (datetime.utcnow() - timedelta(minutes=20)).isoformat(),
            }],
        }
    })

    failed_query = MagicMock()
    failed_query.filter.return_value.all.return_value = [failed_claim]

    initiated_query = MagicMock()
    initiated_query.filter.return_value.all.return_value = [stuck_claim]

    mock_db.query.side_effect = [failed_query, initiated_query]

    with patch("app.services.reconciliation_job.process_payout", return_value=(True, "RAPID123", {})) as payout_mock, \
         patch("app.services.reconciliation_job.mark_for_reconciliation") as reconcile_mock:
        result = run_reconciliation_cycle(mock_db)

    assert result["retried"] == 1
    assert result["escalated_stuck"] == 1
    payout_mock.assert_called_once_with(failed_claim, mock_db)
    reconcile_mock.assert_called_once()
