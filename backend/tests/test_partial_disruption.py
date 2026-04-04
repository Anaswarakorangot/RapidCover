"""
Tests for partial disruption mode feature.

Tests the determine_disruption_category() function and payout calculations
with partial disruption factors.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.models.trigger_event import TriggerType
from app.services.claims_processor import (
    determine_disruption_category,
    calculate_payout_amount,
    DISRUPTION_CATEGORIES,
)


class TestDetermineDisruptionCategory:
    """Test the disruption category determination logic."""

    def test_shutdown_always_full_halt(self, mock_trigger_event, mock_policy):
        """Shutdown triggers are always full halt regardless of severity."""
        mock_trigger_event.trigger_type = TriggerType.SHUTDOWN

        for severity in range(1, 6):
            category, factor, reason = determine_disruption_category(
                TriggerType.SHUTDOWN, severity
            )
            assert category == "full_halt"
            assert factor == 1.0
            assert "shutdown_or_closure" in reason

    def test_closure_always_full_halt(self, mock_trigger_event, mock_policy):
        """Closure triggers are always full halt regardless of severity."""
        for severity in range(1, 6):
            category, factor, reason = determine_disruption_category(
                TriggerType.CLOSURE, severity
            )
            assert category == "full_halt"
            assert factor == 1.0

    def test_severity_5_full_halt(self):
        """Severity 5 weather/AQI events get full halt."""
        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=5
        )
        assert category == "full_halt"
        assert factor == 1.0
        assert "severity_5" in reason

    def test_severity_4_full_halt(self):
        """Severity 4 events also get full halt (severe enough)."""
        category, factor, reason = determine_disruption_category(
            TriggerType.HEAT, severity=4
        )
        assert category == "full_halt"
        assert factor == 1.0

    def test_severity_3_severe_reduction(self):
        """Severity 3 events get severe reduction (75%)."""
        category, factor, reason = determine_disruption_category(
            TriggerType.AQI, severity=3
        )
        assert category == "severe_reduction"
        assert factor == 0.75
        assert "severity_3" in reason

    def test_severity_2_moderate_reduction(self):
        """Severity 2 events get moderate reduction (50%)."""
        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=2
        )
        assert category == "moderate_reduction"
        assert factor == 0.50
        assert "severity_2" in reason

    def test_severity_1_minor_reduction(self):
        """Severity 1 events get minor reduction (25%)."""
        category, factor, reason = determine_disruption_category(
            TriggerType.HEAT, severity=1
        )
        assert category == "minor_reduction"
        assert factor == 0.25
        assert "severity_1" in reason

    def test_partial_factor_override(self):
        """Explicit partial_factor_override is used when provided."""
        source_data = {"partial_factor_override": 0.6}

        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=5, source_data=source_data
        )

        assert factor == 0.6
        assert "partial_factor_override" in reason

    def test_order_data_90_percent_reduction(self):
        """90%+ order reduction gets full halt."""
        source_data = {"expected_orders": 100, "actual_orders": 5}

        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=3, source_data=source_data
        )

        assert category == "full_halt"
        assert factor == 1.0
        assert "order_reduction_95%" in reason

    def test_order_data_70_percent_reduction(self):
        """70-90% order reduction gets severe reduction."""
        source_data = {"expected_orders": 100, "actual_orders": 20}

        category, factor, reason = determine_disruption_category(
            TriggerType.AQI, severity=3, source_data=source_data
        )

        assert category == "severe_reduction"
        assert factor == 0.75
        assert "order_reduction" in reason

    def test_order_data_50_percent_reduction(self):
        """40-70% order reduction gets moderate reduction."""
        source_data = {"expected_orders": 100, "actual_orders": 50}

        category, factor, reason = determine_disruption_category(
            TriggerType.RAIN, severity=2, source_data=source_data
        )

        assert category == "moderate_reduction"
        assert factor == 0.50

    def test_order_data_25_percent_reduction(self):
        """20-40% order reduction gets minor reduction."""
        source_data = {"expected_orders": 100, "actual_orders": 70}

        category, factor, reason = determine_disruption_category(
            TriggerType.HEAT, severity=1, source_data=source_data
        )

        assert category == "minor_reduction"
        assert factor == 0.25


class TestCalculatePayoutWithPartialDisruption:
    """Test payout calculation with partial disruption factors."""

    @pytest.fixture
    def mock_trigger_severity_3(self, mock_trigger_event):
        """Trigger with severity 3 for partial testing."""
        mock_trigger_event.severity = 3
        mock_trigger_event.trigger_type = TriggerType.RAIN
        return mock_trigger_event

    def test_payout_with_moderate_reduction(self, mock_trigger_severity_3, mock_policy):
        """Payout should be reduced with partial disruption factor."""
        mock_trigger_severity_3.severity = 2  # Moderate reduction (50%)

        payout, details = calculate_payout_amount(
            mock_trigger_severity_3,
            mock_policy,
            disruption_hours=4,
        )

        # Check partial disruption is applied
        assert "partial_disruption" in details
        assert details["partial_disruption"]["category"] == "moderate_reduction"
        assert details["partial_disruption"]["factor"] == 0.50

        # Verify the factor was applied
        after_severity = details["after_severity"]
        after_partial = details["after_partial_disruption"]
        assert after_partial == pytest.approx(after_severity * 0.50, rel=0.01)

    def test_payout_with_order_data(self, mock_trigger_severity_3, mock_policy):
        """Payout calculation should use order data when provided."""
        partial_data = {"expected_orders": 20, "actual_orders": 10}  # 50% reduction

        payout, details = calculate_payout_amount(
            mock_trigger_severity_3,
            mock_policy,
            disruption_hours=4,
            partial_disruption_data=partial_data,
        )

        # Check partial disruption metadata includes order data
        pd = details["partial_disruption"]
        assert pd["expected_orders"] == 20
        assert pd["actual_orders"] == 10
        assert pd["category"] == "moderate_reduction"

    def test_full_halt_no_reduction(self, mock_trigger_event, mock_policy):
        """Full halt (severity 5) should not reduce payout."""
        mock_trigger_event.severity = 5
        mock_trigger_event.trigger_type = TriggerType.RAIN

        payout, details = calculate_payout_amount(
            mock_trigger_event,
            mock_policy,
            disruption_hours=4,
        )

        pd = details["partial_disruption"]
        assert pd["category"] == "full_halt"
        assert pd["factor"] == 1.0

        # Verify no reduction applied
        assert details["after_severity"] == details["after_partial_disruption"]


class TestDisruptionCategories:
    """Test the disruption categories configuration."""

    def test_all_categories_defined(self):
        """All expected categories should be defined."""
        expected = ["full_halt", "severe_reduction", "moderate_reduction", "minor_reduction"]
        for cat in expected:
            assert cat in DISRUPTION_CATEGORIES
            assert "factor" in DISRUPTION_CATEGORIES[cat]
            assert "description" in DISRUPTION_CATEGORIES[cat]

    def test_factors_in_valid_range(self):
        """All factors should be between 0 and 1."""
        for cat, config in DISRUPTION_CATEGORIES.items():
            assert 0 <= config["factor"] <= 1.0

    def test_full_halt_is_100_percent(self):
        """Full halt should be 100% payout."""
        assert DISRUPTION_CATEGORIES["full_halt"]["factor"] == 1.0

    def test_factors_decrease_with_severity(self):
        """Factors should decrease: full > severe > moderate > minor."""
        assert DISRUPTION_CATEGORIES["full_halt"]["factor"] > DISRUPTION_CATEGORIES["severe_reduction"]["factor"]
        assert DISRUPTION_CATEGORIES["severe_reduction"]["factor"] > DISRUPTION_CATEGORIES["moderate_reduction"]["factor"]
        assert DISRUPTION_CATEGORIES["moderate_reduction"]["factor"] > DISRUPTION_CATEGORIES["minor_reduction"]["factor"]
