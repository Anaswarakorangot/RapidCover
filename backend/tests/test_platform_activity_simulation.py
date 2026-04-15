"""
test_platform_activity_simulation.py
--------------------------------------
Tests for the Platform Activity Simulation (Feature 3).

Covers:
  - get/set partner platform activity (in-memory and DB-backed)
  - evaluate_partner_platform_eligibility — all 5 checks
  - DB persistence via upsert_db_partner_platform_activity
  - GET/PUT /zones/partners/{partner_id}/activity endpoints
  - Claim eligibility gates on platform activity
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.utils.time_utils import utcnow


# ---------------------------------------------------------------------------
# In-memory platform activity (external_apis.py)
# ---------------------------------------------------------------------------

class TestGetSetPartnerPlatformActivity:

    def setup_method(self):
        """Clear in-memory store before each test."""
        from app.services.external_apis import _partner_platform_activity
        _partner_platform_activity.clear()

    def test_get_returns_default_for_new_partner(self):
        from app.services.external_apis import get_partner_platform_activity
        activity = get_partner_platform_activity(999)
        assert activity["partner_id"] == 999
        assert activity["platform_logged_in"] is True
        assert activity["active_shift"] is True
        assert activity["suspicious_inactivity"] is False
        assert activity["orders_completed_recent"] >= 1

    def test_set_updates_specified_fields(self):
        from app.services.external_apis import set_partner_platform_activity, get_partner_platform_activity
        set_partner_platform_activity(1, active_shift=False, platform_logged_in=False)
        activity = get_partner_platform_activity(1)
        assert activity["active_shift"] is False
        assert activity["platform_logged_in"] is False

    def test_set_does_not_overwrite_unspecified_fields(self):
        from app.services.external_apis import set_partner_platform_activity, get_partner_platform_activity
        # First set platform
        set_partner_platform_activity(2, platform="blinkit")
        # Then update only orders
        set_partner_platform_activity(2, orders_completed_recent=0)
        activity = get_partner_platform_activity(2)
        assert activity["platform"] == "blinkit"
        assert activity["orders_completed_recent"] == 0

    def test_source_becomes_admin_override_after_set(self):
        from app.services.external_apis import set_partner_platform_activity, get_partner_platform_activity
        set_partner_platform_activity(3, suspicious_inactivity=True)
        activity = get_partner_platform_activity(3)
        assert activity["source"] == "admin_override"

    def test_platform_field_accepts_known_platforms(self):
        from app.services.external_apis import set_partner_platform_activity, get_partner_platform_activity
        for platform in ["zomato", "swiggy", "zepto", "blinkit"]:
            set_partner_platform_activity(10, platform=platform)
            assert get_partner_platform_activity(10)["platform"] == platform

    def test_updated_at_changes_after_set(self):
        from app.services.external_apis import get_partner_platform_activity, set_partner_platform_activity
        before = get_partner_platform_activity(4)["updated_at"]
        import time; time.sleep(0.01)
        set_partner_platform_activity(4, orders_accepted_recent=20)
        after = get_partner_platform_activity(4)["updated_at"]
        assert after >= before


# ---------------------------------------------------------------------------
# evaluate_partner_platform_eligibility
# ---------------------------------------------------------------------------

class TestEvaluatePartnerPlatformEligibility:

    def setup_method(self):
        from app.services.external_apis import _partner_platform_activity
        _partner_platform_activity.clear()

    def _set_active(self, partner_id=1):
        from app.services.external_apis import set_partner_platform_activity
        set_partner_platform_activity(
            partner_id,
            platform_logged_in=True,
            active_shift=True,
            orders_completed_recent=5,
            suspicious_inactivity=False,
            last_app_ping=utcnow().isoformat(),
        )

    def _set_inactive(self, partner_id=1):
        from app.services.external_apis import set_partner_platform_activity
        set_partner_platform_activity(
            partner_id,
            platform_logged_in=False,
            active_shift=False,
            orders_completed_recent=0,
            suspicious_inactivity=True,
            last_app_ping=(utcnow() - timedelta(hours=2)).isoformat(),
        )

    def test_fully_active_partner_is_eligible(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        self._set_active(1)
        result = evaluate_partner_platform_eligibility(1)
        assert result["eligible"] is True
        assert result["score"] > 0.8

    def test_fully_inactive_partner_is_not_eligible(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        self._set_inactive(1)
        result = evaluate_partner_platform_eligibility(1)
        assert result["eligible"] is False
        assert result["score"] < 0.5

    def test_result_has_required_fields(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        result = evaluate_partner_platform_eligibility(1)
        assert "eligible" in result
        assert "score" in result
        assert "reasons" in result
        assert "activity" in result
        assert isinstance(result["reasons"], list)

    def test_five_checks_are_present(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        self._set_active(1)
        result = evaluate_partner_platform_eligibility(1)
        check_names = {r["check"] for r in result["reasons"]}
        expected = {
            "platform_logged_in", "active_shift",
            "orders_completed_recent", "suspicious_inactivity", "last_app_ping",
        }
        assert check_names == expected

    def test_not_logged_in_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, platform_logged_in=False)
        result = evaluate_partner_platform_eligibility(1)
        login_check = next(r for r in result["reasons"] if r["check"] == "platform_logged_in")
        assert login_check["pass"] is False
        assert result["eligible"] is False

    def test_not_on_shift_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, active_shift=False)
        result = evaluate_partner_platform_eligibility(1)
        shift_check = next(r for r in result["reasons"] if r["check"] == "active_shift")
        assert shift_check["pass"] is False

    def test_zero_orders_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, orders_completed_recent=0)
        result = evaluate_partner_platform_eligibility(1)
        order_check = next(r for r in result["reasons"] if r["check"] == "orders_completed_recent")
        assert order_check["pass"] is False

    def test_suspicious_inactivity_flag_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, suspicious_inactivity=True)
        result = evaluate_partner_platform_eligibility(1)
        inactivity_check = next(r for r in result["reasons"] if r["check"] == "suspicious_inactivity")
        assert inactivity_check["pass"] is False

    def test_old_ping_fails_check(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        old_ping = (utcnow() - timedelta(hours=1)).isoformat()
        set_partner_platform_activity(1, last_app_ping=old_ping)
        result = evaluate_partner_platform_eligibility(1)
        ping_check = next(r for r in result["reasons"] if r["check"] == "last_app_ping")
        assert ping_check["pass"] is False

    def test_score_between_0_and_1(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility
        result = evaluate_partner_platform_eligibility(1)
        assert 0.0 <= result["score"] <= 1.0

    def test_high_order_count_boosts_score(self):
        from app.services.external_apis import evaluate_partner_platform_eligibility, set_partner_platform_activity
        self._set_active(1)
        set_partner_platform_activity(1, orders_completed_recent=20)
        result_high = evaluate_partner_platform_eligibility(1)

        self._set_active(2)
        set_partner_platform_activity(2, orders_completed_recent=1)
        result_low = evaluate_partner_platform_eligibility(2)

        # Both eligible but high-order partner has >= score
        assert result_high["score"] >= result_low["score"]


# ---------------------------------------------------------------------------
# DB-backed platform activity (claims_processor.py)
# ---------------------------------------------------------------------------

class TestDbPartnerPlatformActivity:

    def _make_db(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        return db

    def test_get_returns_defaults_when_no_row(self):
        from app.services.runtime_metadata import get_db_partner_platform_activity
        db = self._make_db()
        result = get_db_partner_platform_activity(1, db)
        assert result["partner_id"] == 1
        assert result["platform_logged_in"] is True
        assert result["active_shift"] is True
        assert result["suspicious_inactivity"] is False
        assert result["source"] == "default"

    def test_upsert_calls_db_execute(self):
        from app.services.runtime_metadata import upsert_db_partner_platform_activity
        db = self._make_db()
        # Should not raise
        upsert_db_partner_platform_activity(1, db, active_shift=False)
        assert db.execute.called
        assert db.commit.called

    def test_upsert_returns_dict_with_partner_id(self):
        from app.services.runtime_metadata import upsert_db_partner_platform_activity
        db = self._make_db()
        result = upsert_db_partner_platform_activity(1, db, platform="swiggy")
        assert isinstance(result, dict)
        assert result["partner_id"] == 1

    def test_get_parses_db_row_correctly(self):
        from app.services.runtime_metadata import get_db_partner_platform_activity
        db = MagicMock()
        now_iso = utcnow().isoformat()
        db.execute.return_value.mappings.return_value.first.return_value = {
            "partner_id": 5,
            "platform_logged_in": 0,
            "active_shift": 1,
            "orders_accepted_recent": 3,
            "orders_completed_recent": 2,
            "last_app_ping": now_iso,
            "zone_dwell_minutes": 45,
            "suspicious_inactivity": 0,
            "platform": "zepto",
            "updated_at": now_iso,
            "source": "admin_override",
        }
        result = get_db_partner_platform_activity(5, db)
        assert result["platform_logged_in"] is False   # integer 0 → bool False
        assert result["active_shift"] is True           # integer 1 → bool True
        assert result["platform"] == "zepto"
        assert result["source"] == "admin_override"


# ---------------------------------------------------------------------------
# Validation matrix includes platform_activity check
# ---------------------------------------------------------------------------

class TestPlatformActivityInValidationMatrix:

    def test_platform_activity_check_present_in_matrix(self):
        """build_validation_matrix must include a platform_activity check."""
        from app.services.claims_processor import build_validation_matrix
        from unittest.mock import MagicMock, patch
        from datetime import datetime, timedelta

        partner = MagicMock()
        partner.id = 1
        partner.is_active = True
        partner.shift_days = []
        partner.shift_start = None
        partner.shift_end = None

        policy = MagicMock()
        policy.id = 10
        policy.is_active = True
        policy.starts_at = utcnow() - timedelta(days=1)
        policy.expires_at = utcnow() + timedelta(days=7)

        trigger = MagicMock()
        trigger.id = 100
        trigger.zone_id = 1
        trigger.trigger_type.value = "rain"
        trigger.started_at = utcnow()

        zone = MagicMock()
        zone.id = 1
        zone.pin_codes = ["560001"]

        fraud = {"score": 0.2, "recommendation": "approve"}
        db = MagicMock()
        # Configure mock for GPS ping queries (data freshness check)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None  # No GPS pings found
        db.query.return_value = mock_query
        # Configure execute().mappings().first() for other queries
        db.execute.return_value.mappings.return_value.first.return_value = None

        with (
            patch("app.services.claims_processor.check_partner_pin_code_match",
                  return_value=(True, "pin_code_match")),
            patch("app.services.claims_processor.is_partner_available_for_trigger",
                  return_value=(True, "eligible")),
            patch("app.services.claims_processor.get_partner_runtime_metadata",
                  return_value={"is_manual_offline": False, "leave_until": None,
                                "manual_offline_until": None, "pin_code": "560001"}),
            patch("app.services.claims_processor.evaluate_partner_platform_eligibility",
                  return_value={"eligible": True, "score": 0.85,
                                "reasons": [], "activity": {"platform": "zomato"}}),
        ):
            matrix = build_validation_matrix(partner, policy, trigger, zone, fraud, db, {})

        check_names = {c["check_name"] for c in matrix}
        assert "platform_activity" in check_names

    def test_platform_ineligible_sets_check_failed(self):
        from app.services.claims_processor import build_validation_matrix
        from unittest.mock import MagicMock, patch
        from datetime import datetime, timedelta

        partner = MagicMock()
        partner.id = 1
        partner.is_active = True
        partner.shift_days = []
        partner.shift_start = None
        partner.shift_end = None

        policy = MagicMock()
        policy.id = 10
        policy.is_active = True
        policy.starts_at = utcnow() - timedelta(days=1)
        policy.expires_at = utcnow() + timedelta(days=7)

        trigger = MagicMock()
        trigger.id = 100
        trigger.zone_id = 1
        trigger.trigger_type.value = "rain"
        trigger.started_at = utcnow()

        zone = MagicMock()
        zone.id = 1
        zone.pin_codes = ["560001"]

        fraud = {"score": 0.2, "recommendation": "approve"}
        db = MagicMock()
        # Configure mock for GPS ping queries (data freshness check)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None  # No GPS pings found
        db.query.return_value = mock_query
        # Configure execute().mappings().first() for other queries
        db.execute.return_value.mappings.return_value.first.return_value = None

        with (
            patch("app.services.claims_processor.check_partner_pin_code_match",
                  return_value=(True, "pin_code_match")),
            patch("app.services.claims_processor.is_partner_available_for_trigger",
                  return_value=(True, "eligible")),
            patch("app.services.claims_processor.get_partner_runtime_metadata",
                  return_value={"is_manual_offline": False, "leave_until": None,
                                "manual_offline_until": None, "pin_code": "560001"}),
            patch("app.services.claims_processor.evaluate_partner_platform_eligibility",
                  return_value={"eligible": False, "score": 0.0,
                                "reasons": [], "activity": {"platform": "zepto"}}),
        ):
            matrix = build_validation_matrix(partner, policy, trigger, zone, fraud, db, {})

        platform_check = next(c for c in matrix if c["check_name"] == "platform_activity")
        assert platform_check["passed"] is False
        assert platform_check["confidence"] == 0.0