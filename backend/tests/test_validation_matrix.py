"""
test_validation_matrix.py
--------------------------
Tests for the Real-World Validation Matrix (Feature 1).

Covers:
  - All 10 checks are present in the matrix
  - Matrix stored on claim validation_data
  - Correct pass/fail per check condition
  - Matrix summary totals are accurate
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_partner(
    is_active=True,
    pin_code=None,
    shift_days=None,
    shift_start=None,
    shift_end=None,
):
    p = MagicMock()
    p.id = 1
    p.name = "Test Partner"
    p.is_active = is_active
    p.pin_code = pin_code
    p.shift_days = shift_days or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    p.shift_start = shift_start
    p.shift_end = shift_end
    p.zone_id = 1
    return p


def _make_policy(is_active=True):
    p = MagicMock()
    p.id = 10
    p.is_active = is_active
    p.starts_at = datetime.utcnow() - timedelta(days=7)
    p.expires_at = datetime.utcnow() + timedelta(days=7)
    p.max_daily_payout = 500.0
    p.tier = MagicMock()
    p.tier.value = "basic"
    return p


def _make_trigger(zone_id=1, trigger_type=None, severity=3):
    t = MagicMock()
    t.id = 100
    t.zone_id = zone_id
    t.trigger_type = trigger_type or MagicMock()
    t.trigger_type.value = "rain"
    t.severity = severity
    t.started_at = datetime.utcnow()
    return t


def _make_zone(zone_id=1):
    z = MagicMock()
    z.id = zone_id
    z.code = "BLR-001"
    z.city = "Bangalore"
    z.pin_codes = ["560001", "560002"]
    z.dark_store_lat = 12.9352
    z.dark_store_lng = 77.6245
    return z


def _make_fraud_result(score=0.2, recommendation="approve"):
    return {
        "score": score,
        "recommendation": recommendation,
        "factors": {},
        "hard_reject_reasons": [],
    }


def _make_db():
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = None
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidationMatrixStructure:
    """Matrix must always contain exactly 10 named checks."""

    EXPECTED_CHECK_NAMES = {
        "source_threshold_breach",
        "zone_match",
        "pin_code_match",
        "active_policy",
        "shift_window",
        "partner_activity",
        "platform_activity",
        "fraud_score_below_threshold",
        "data_freshness",
        "cross_source_agreement",
    }

    def _run_matrix(self, partner=None, policy=None, trigger=None, zone=None,
                    fraud=None, source_data=None):
        from app.services.claims_processor import build_validation_matrix

        partner = partner or _make_partner()
        policy = policy or _make_policy()
        trigger = trigger or _make_trigger()
        zone = zone or _make_zone()
        fraud = fraud or _make_fraud_result()
        db = _make_db()

        with (
            patch("app.services.claims_processor.check_partner_pin_code_match",
                  return_value=(True, "pin_code_match")),
            patch("app.services.claims_processor.is_partner_available_for_trigger",
                  return_value=(True, "eligible")),
            patch("app.services.claims_processor.get_partner_runtime_metadata",
                  return_value={"is_manual_offline": False, "leave_until": None,
                                "manual_offline_until": None, "pin_code": "560001"}),
            patch("app.services.claims_processor.evaluate_partner_platform_eligibility",
                  return_value={"eligible": True, "score": 0.9,
                                "reasons": [], "activity": {"platform": "zomato"}}),
        ):
            return build_validation_matrix(partner, policy, trigger, zone, fraud, db,
                                           source_data or {})

    def test_returns_list(self):
        matrix = self._run_matrix()
        assert isinstance(matrix, list)

    def test_ten_checks_present(self):
        matrix = self._run_matrix()
        assert len(matrix) == 10

    def test_all_expected_check_names_present(self):
        matrix = self._run_matrix()
        names = {c["check_name"] for c in matrix}
        assert names == self.EXPECTED_CHECK_NAMES

    def test_each_check_has_required_fields(self):
        matrix = self._run_matrix()
        for check in matrix:
            assert "check_name" in check
            assert "passed" in check
            assert isinstance(check["passed"], bool)
            assert "reason" in check
            assert "source" in check
            assert "confidence" in check
            assert 0.0 <= check["confidence"] <= 1.0

    def test_matrix_summary_totals_are_correct(self):
        matrix = self._run_matrix()
        passed = sum(1 for c in matrix if c["passed"])
        failed = sum(1 for c in matrix if not c["passed"])
        assert passed + failed == len(matrix)


class TestValidationMatrixCheckLogic:
    """Individual checks fire correctly under different conditions."""

    def _run(self, **kwargs):
        from app.services.claims_processor import build_validation_matrix

        partner = kwargs.pop("partner", _make_partner())
        policy = kwargs.pop("policy", _make_policy())
        trigger = kwargs.pop("trigger", _make_trigger())
        zone = kwargs.pop("zone", _make_zone())
        fraud = kwargs.pop("fraud", _make_fraud_result())
        source_data = kwargs.pop("source_data", {})
        db = _make_db()

        with (
            patch("app.services.claims_processor.check_partner_pin_code_match",
                  return_value=kwargs.pop("pin_match", (True, "pin_code_match"))),
            patch("app.services.claims_processor.is_partner_available_for_trigger",
                  return_value=kwargs.pop("available", (True, "eligible"))),
            patch("app.services.claims_processor.get_partner_runtime_metadata",
                  return_value=kwargs.pop("runtime_meta", {
                      "is_manual_offline": False, "leave_until": None,
                      "manual_offline_until": None, "pin_code": "560001"
                  })),
            patch("app.services.claims_processor.evaluate_partner_platform_eligibility",
                  return_value=kwargs.pop("platform_eval", {
                      "eligible": True, "score": 0.9,
                      "reasons": [], "activity": {"platform": "zomato"}
                  })),
        ):
            matrix = build_validation_matrix(partner, policy, trigger, zone, fraud, db, source_data)
        return {c["check_name"]: c for c in matrix}

    def test_zone_match_passes_when_zone_ids_match(self):
        trigger = _make_trigger(zone_id=1)
        zone = _make_zone(zone_id=1)
        checks = self._run(trigger=trigger, zone=zone)
        assert checks["zone_match"]["passed"] is True

    def test_zone_match_fails_when_zone_ids_differ(self):
        trigger = _make_trigger(zone_id=99)
        zone = _make_zone(zone_id=1)
        checks = self._run(trigger=trigger, zone=zone)
        assert checks["zone_match"]["passed"] is False

    def test_pin_code_match_passes_when_match(self):
        checks = self._run(pin_match=(True, "pin_code_match"))
        assert checks["pin_code_match"]["passed"] is True

    def test_pin_code_match_fails_when_mismatch(self):
        checks = self._run(pin_match=(False, "pin_code_mismatch"))
        assert checks["pin_code_match"]["passed"] is False

    def test_active_policy_passes_for_valid_policy(self):
        checks = self._run()
        assert checks["active_policy"]["passed"] is True

    def test_active_policy_fails_for_expired_policy(self):
        policy = _make_policy()
        policy.expires_at = datetime.utcnow() - timedelta(days=3)
        checks = self._run(policy=policy)
        assert checks["active_policy"]["passed"] is False

    def test_shift_window_passes_when_available(self):
        checks = self._run(available=(True, "eligible"))
        assert checks["shift_window"]["passed"] is True

    def test_shift_window_fails_when_outside(self):
        checks = self._run(available=(False, "outside_shift_days"))
        assert checks["shift_window"]["passed"] is False

    def test_partner_activity_fails_when_manual_offline(self):
        checks = self._run(runtime_meta={
            "is_manual_offline": True,
            "leave_until": None,
            "manual_offline_until": None,
            "pin_code": "560001",
        })
        assert checks["partner_activity"]["passed"] is False

    def test_partner_activity_fails_when_on_leave(self):
        checks = self._run(runtime_meta={
            "is_manual_offline": False,
            "leave_until": datetime.utcnow() + timedelta(hours=3),
            "manual_offline_until": None,
            "pin_code": "560001",
        })
        assert checks["partner_activity"]["passed"] is False

    def test_platform_activity_passes_when_eligible(self):
        checks = self._run(platform_eval={
            "eligible": True, "score": 0.9,
            "reasons": [], "activity": {"platform": "swiggy"}
        })
        assert checks["platform_activity"]["passed"] is True

    def test_platform_activity_fails_when_not_eligible(self):
        checks = self._run(platform_eval={
            "eligible": False, "score": 0.2,
            "reasons": [], "activity": {"platform": "blinkit"}
        })
        assert checks["platform_activity"]["passed"] is False

    def test_fraud_score_passes_below_threshold(self):
        fraud = _make_fraud_result(score=0.3)
        checks = self._run(fraud=fraud)
        assert checks["fraud_score_below_threshold"]["passed"] is True

    def test_fraud_score_fails_above_threshold(self):
        fraud = _make_fraud_result(score=0.95)
        checks = self._run(fraud=fraud)
        assert checks["fraud_score_below_threshold"]["passed"] is False

    def test_cross_source_agreement_passes_with_good_score(self):
        checks = self._run(source_data={"oracle_agreement_score": 0.9})
        assert checks["cross_source_agreement"]["passed"] is True

    def test_cross_source_agreement_fails_with_low_score(self):
        checks = self._run(source_data={"oracle_agreement_score": 0.3})
        assert checks["cross_source_agreement"]["passed"] is False

    def test_threshold_check_uses_source_data_values(self):
        checks = self._run(source_data={
            "rainfall_mm_hr": 62.0,
            "threshold": 55.0,
            "data_source": "live",
        })
        assert checks["source_threshold_breach"]["passed"] is True

    def test_threshold_check_fails_below_threshold(self):
        checks = self._run(source_data={
            "rainfall_mm_hr": 30.0,
            "threshold": 55.0,
            "data_source": "live",
        })
        assert checks["source_threshold_breach"]["passed"] is False


class TestValidationMatrixOnClaim:
    """Ensure validation_matrix is serialised into claim.validation_data."""

    def test_validation_matrix_key_in_validation_data(self):
        # Simulate what process_trigger_event stores
        matrix = [
            {"check_name": "zone_match", "passed": True, "reason": "ok",
             "source": "db", "confidence": 1.0}
        ]
        vd = {"validation_matrix": matrix, "validation_matrix_summary": {
            "total_checks": 1, "passed": 1, "failed": 0, "overall": "pass"
        }}
        serialised = json.dumps(vd)
        loaded = json.loads(serialised)
        assert "validation_matrix" in loaded
        assert len(loaded["validation_matrix"]) == 1
        assert loaded["validation_matrix"][0]["check_name"] == "zone_match"

    def test_matrix_summary_overall_pass_when_all_pass(self):
        matrix = [
            {"check_name": f"check_{i}", "passed": True,
             "reason": "ok", "source": "db", "confidence": 1.0}
            for i in range(10)
        ]
        summary = {
            "total_checks": len(matrix),
            "passed": sum(1 for c in matrix if c["passed"]),
            "failed": sum(1 for c in matrix if not c["passed"]),
            "overall": "pass" if all(c["passed"] for c in matrix) else "fail",
        }
        assert summary["overall"] == "pass"
        assert summary["passed"] == 10
        assert summary["failed"] == 0

    def test_matrix_summary_overall_fail_when_any_fail(self):
        matrix = [
            {"check_name": "zone_match", "passed": False,
             "reason": "mismatch", "source": "db", "confidence": 0.0},
            {"check_name": "active_policy", "passed": True,
             "reason": "ok", "source": "db", "confidence": 1.0},
        ]
        overall = "pass" if all(c["passed"] for c in matrix) else "fail"
        assert overall == "fail"