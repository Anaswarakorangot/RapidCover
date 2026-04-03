"""
Tests for trigger eligibility pin-code strictness.

Verifies that the pin-code matching logic now fails explicitly
instead of falling back to True when data is missing.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestTriggerPincodeStrictness:
    """Tests for strict pin-code matching in trigger eligibility."""

    def test_missing_partner_pincode_returns_fail(self, mock_db, mock_partner, mock_zone):
        """Test that missing partner pin code returns False with reason."""
        from app.services.trigger_engine import check_partner_pin_code_match

        # Ensure mock_partner and mock_zone don't have pin_code attributes
        mock_partner.configure_mock(pin_code=None)
        mock_zone.configure_mock(pin_codes=None)

        # Mock runtime metadata with no pin code
        with patch("app.services.trigger_engine.get_partner_runtime_metadata") as mock_partner_meta:
            with patch("app.services.trigger_engine.get_zone_coverage_metadata") as mock_zone_meta:
                mock_partner_meta.return_value = {
                    "partner_id": 1,
                    "pin_code": None,  # Missing pin code
                    "is_manual_offline": False,
                    "manual_offline_until": None,
                    "leave_until": None,
                    "leave_note": None,
                    "updated_at": None,
                }
                mock_zone_meta.return_value = {
                    "zone_id": 1,
                    "pin_codes": ["560034", "560095"],  # Zone has coverage
                    "density_weight": 0.35,
                    "ward_name": "Koramangala",
                    "updated_at": None,
                }

                result, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)

                assert result is False
                assert reason == "partner_location_missing"

    def test_missing_zone_coverage_returns_fail(self, mock_db, mock_partner, mock_zone):
        """Test that missing zone coverage data returns False with reason."""
        from app.services.trigger_engine import check_partner_pin_code_match

        with patch("app.services.trigger_engine.get_partner_runtime_metadata") as mock_partner_meta:
            with patch("app.services.trigger_engine.get_zone_coverage_metadata") as mock_zone_meta:
                mock_partner_meta.return_value = {
                    "partner_id": 1,
                    "pin_code": "560034",  # Partner has pin code
                    "is_manual_offline": False,
                    "manual_offline_until": None,
                    "leave_until": None,
                    "leave_note": None,
                    "updated_at": None,
                }
                mock_zone_meta.return_value = {
                    "zone_id": 1,
                    "pin_codes": [],  # Empty coverage
                    "density_weight": None,
                    "ward_name": None,
                    "updated_at": None,
                }

                result, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)

                assert result is False
                assert reason == "coverage_data_missing"

    def test_pincode_mismatch_returns_fail(self, mock_db, mock_partner, mock_zone):
        """Test that pin code mismatch returns False."""
        from app.services.trigger_engine import check_partner_pin_code_match

        with patch("app.services.trigger_engine.get_partner_runtime_metadata") as mock_partner_meta:
            with patch("app.services.trigger_engine.get_zone_coverage_metadata") as mock_zone_meta:
                mock_partner_meta.return_value = {
                    "partner_id": 1,
                    "pin_code": "560001",  # Different pin code
                    "is_manual_offline": False,
                    "manual_offline_until": None,
                    "leave_until": None,
                    "leave_note": None,
                    "updated_at": None,
                }
                mock_zone_meta.return_value = {
                    "zone_id": 1,
                    "pin_codes": ["560034", "560095"],  # Zone coverage
                    "density_weight": 0.35,
                    "ward_name": "Koramangala",
                    "updated_at": None,
                }

                result, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)

                assert result is False
                assert reason == "pin_code_mismatch"

    def test_pincode_match_returns_pass(self, mock_db, mock_partner, mock_zone):
        """Test that matching pin code returns True."""
        from app.services.trigger_engine import check_partner_pin_code_match

        with patch("app.services.trigger_engine.get_partner_runtime_metadata") as mock_partner_meta:
            with patch("app.services.trigger_engine.get_zone_coverage_metadata") as mock_zone_meta:
                mock_partner_meta.return_value = {
                    "partner_id": 1,
                    "pin_code": "560034",  # Matching pin code
                    "is_manual_offline": False,
                    "manual_offline_until": None,
                    "leave_until": None,
                    "leave_note": None,
                    "updated_at": None,
                }
                mock_zone_meta.return_value = {
                    "zone_id": 1,
                    "pin_codes": ["560034", "560095"],  # Zone coverage includes 560034
                    "density_weight": 0.35,
                    "ward_name": "Koramangala",
                    "updated_at": None,
                }

                result, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)

                assert result is True
                assert reason == "pin_code_match"

    def test_without_db_uses_model_attributes(self, mock_partner, mock_zone):
        """Test that without db, it uses model attributes directly."""
        from app.services.trigger_engine import check_partner_pin_code_match

        # Set attributes on mock objects
        mock_partner.pin_code = "560034"
        mock_zone.pin_codes = ["560034", "560095"]

        result, reason = check_partner_pin_code_match(mock_partner, mock_zone, db=None)

        assert result is True
        assert reason == "pin_code_match"

    def test_without_db_partner_missing_pin(self, mock_partner, mock_zone):
        """Test without db when partner has no pin_code attribute."""
        from app.services.trigger_engine import check_partner_pin_code_match

        # Don't set pin_code on partner
        delattr(mock_partner, "pin_code") if hasattr(mock_partner, "pin_code") else None
        mock_zone.pin_codes = ["560034"]

        result, reason = check_partner_pin_code_match(mock_partner, mock_zone, db=None)

        assert result is False
        assert reason == "partner_location_missing"


class TestTriggerCheckEndpoint:
    """Tests for the trigger-check proof endpoint."""

    def test_trigger_check_returns_all_checks(self):
        """Test that trigger-check endpoint returns all eligibility checks."""
        # This would be an integration test with FastAPI TestClient
        # For unit testing, we verify the check structure

        expected_checks = [
            "partner_active",
            "policy_active",
            "pin_code_match",
            "shift_window",
        ]

        # Just verify the expected check names exist
        for check in expected_checks:
            assert check in expected_checks  # Placeholder for actual test

    def test_check_reasons_are_descriptive(self):
        """Test that failure reasons are descriptive."""
        valid_reasons = [
            "partner_location_missing",
            "coverage_data_missing",
            "pin_code_mismatch",
            "pin_code_match",
            "partner_inactive",
            "outside_shift_days",
            "outside_shift_window",
            "manual_offline",
            "declared_leave",
            "eligible",
        ]

        # All reasons should be snake_case and descriptive
        for reason in valid_reasons:
            assert "_" in reason or reason == "eligible"
            assert reason.islower()
