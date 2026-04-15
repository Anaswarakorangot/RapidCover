"""
Tests for multi-trigger resolver feature.

Tests trigger aggregation within 6-hour windows, payout calculation
with highest-wins strategy, and severe disruption uplift.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.models.trigger_event import TriggerType
from app.models.claim import ClaimStatus
from app.utils.time_utils import utcnow
from app.services.multi_trigger_resolver import (
    generate_aggregation_group_id,
    find_triggers_in_window,
    calculate_aggregation_window,
    should_apply_severe_disruption_uplift,
    calculate_aggregated_payout,
    check_and_resolve_aggregation,
    AGGREGATION_WINDOW_HOURS,
    SEVERE_DISRUPTION_UPLIFT_PERCENT,
)


class TestAggregationGroupId:
    """Test aggregation group ID generation."""

    def test_generate_unique_ids(self):
        """Each call should generate a unique ID."""
        ids = [generate_aggregation_group_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_id_format(self):
        """IDs should follow the AGG- prefix format."""
        group_id = generate_aggregation_group_id()
        assert group_id.startswith("AGG-")
        assert len(group_id) == 16  # AGG- + 12 hex chars


class TestAggregationWindow:
    """Test aggregation window calculation."""

    def test_window_is_6_hours(self):
        """Window should be 6 hours total (3 before, 3 after)."""
        trigger_time = datetime(2024, 1, 15, 12, 0, 0)
        window_start, window_end = calculate_aggregation_window(trigger_time)

        duration = (window_end - window_start).total_seconds() / 3600
        assert duration == AGGREGATION_WINDOW_HOURS

    def test_window_centered_on_trigger(self):
        """Window should be centered on trigger time."""
        trigger_time = datetime(2024, 1, 15, 12, 0, 0)
        window_start, window_end = calculate_aggregation_window(trigger_time)

        # Trigger should be in the middle
        assert window_start == trigger_time - timedelta(hours=3)
        assert window_end == trigger_time + timedelta(hours=3)


class TestSevereDisruptionUplift:
    """Test severe disruption uplift determination."""

    def test_uplift_with_3_trigger_types(self):
        """Uplift should apply with 3+ distinct trigger types."""
        triggers = [
            MagicMock(trigger_type=TriggerType.RAIN),
            MagicMock(trigger_type=TriggerType.AQI),
            MagicMock(trigger_type=TriggerType.SHUTDOWN),
        ]
        assert should_apply_severe_disruption_uplift(triggers) is True

    def test_no_uplift_with_2_trigger_types(self):
        """Uplift should not apply with only 2 trigger types."""
        triggers = [
            MagicMock(trigger_type=TriggerType.RAIN),
            MagicMock(trigger_type=TriggerType.AQI),
        ]
        assert should_apply_severe_disruption_uplift(triggers) is False

    def test_no_uplift_with_1_trigger_type(self):
        """Uplift should not apply with single trigger."""
        triggers = [MagicMock(trigger_type=TriggerType.RAIN)]
        assert should_apply_severe_disruption_uplift(triggers) is False

    def test_no_uplift_with_duplicates(self):
        """Multiple triggers of same type don't count as different types."""
        triggers = [
            MagicMock(trigger_type=TriggerType.RAIN),
            MagicMock(trigger_type=TriggerType.RAIN),
            MagicMock(trigger_type=TriggerType.RAIN),
        ]
        assert should_apply_severe_disruption_uplift(triggers) is False


class TestCalculateAggregatedPayout:
    """Test aggregated payout calculation."""

    @pytest.fixture
    def triggers_with_payouts(self):
        """Create triggers with known payouts."""
        triggers = [
            MagicMock(id=1, trigger_type=TriggerType.RAIN, severity=4, started_at=utcnow()),
            MagicMock(id=2, trigger_type=TriggerType.AQI, severity=3, started_at=utcnow()),
            MagicMock(id=3, trigger_type=TriggerType.HEAT, severity=2, started_at=utcnow()),
        ]
        payouts = {1: 300.0, 2: 250.0, 3: 150.0}
        return triggers, payouts

    def test_highest_payout_wins(self, triggers_with_payouts, mock_policy):
        """The trigger with highest payout should be primary."""
        triggers, payouts = triggers_with_payouts
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert meta["primary_trigger_id"] == 1  # Highest payout (300)
        assert 2 in meta["suppressed_triggers"]
        assert 3 in meta["suppressed_triggers"]

    def test_uplift_applied_for_severe_disruption(self, triggers_with_payouts, mock_policy):
        """10% uplift should be applied when 3+ trigger types."""
        triggers, payouts = triggers_with_payouts
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert meta["uplift_applied"] is True
        assert meta["uplift_percent"] == SEVERE_DISRUPTION_UPLIFT_PERCENT
        assert meta["uplift_amount"] == 30.0  # 10% of 300

        # Final payout includes uplift
        expected = 300.0 * 1.10  # 330
        assert final_payout == pytest.approx(expected, rel=0.01)

    def test_no_uplift_for_2_triggers(self, mock_policy):
        """No uplift with only 2 trigger types."""
        triggers = [
            MagicMock(id=1, trigger_type=TriggerType.RAIN, severity=4, started_at=utcnow()),
            MagicMock(id=2, trigger_type=TriggerType.AQI, severity=3, started_at=utcnow()),
        ]
        payouts = {1: 300.0, 2: 250.0}
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert meta["uplift_applied"] is False
        assert meta["uplift_percent"] == 0.0
        assert final_payout == 300.0  # No uplift

    def test_savings_calculated_correctly(self, triggers_with_payouts, mock_policy):
        """Savings should be difference between pre and post aggregation."""
        triggers, payouts = triggers_with_payouts
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        pre_aggregation = sum(payouts.values())  # 700
        assert meta["pre_aggregation_payout"] == pre_aggregation
        assert meta["savings"] == pre_aggregation - final_payout

    def test_daily_limit_applied(self, mock_policy):
        """Daily limit should cap the final payout."""
        triggers = [
            MagicMock(id=1, trigger_type=TriggerType.RAIN, severity=5, started_at=utcnow()),
        ]
        payouts = {1: 500.0}
        mock_policy.max_daily_payout = 400.0  # Limit below payout

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert final_payout == 400.0  # Capped at daily limit

    def test_metadata_includes_trigger_details(self, triggers_with_payouts, mock_policy):
        """Metadata should include details of all triggers in window."""
        triggers, payouts = triggers_with_payouts
        mock_policy.max_daily_payout = 1000.0

        final_payout, meta = calculate_aggregated_payout(triggers, mock_policy, payouts)

        assert len(meta["triggers_in_window"]) == 3
        for tw in meta["triggers_in_window"]:
            assert "id" in tw
            assert "type" in tw
            assert "severity" in tw
            assert "payout" in tw


class TestCheckAndResolveAggregation:
    """Test the main aggregation check function."""

    @pytest.fixture
    def mock_trigger(self):
        """Create a mock trigger event."""
        trigger = MagicMock()
        trigger.id = 1
        trigger.zone_id = 1
        trigger.trigger_type = TriggerType.RAIN
        trigger.severity = 4
        trigger.started_at = utcnow()
        return trigger

    def test_first_trigger_creates_new_claim(self, mock_trigger, mock_policy, mock_db):
        """First trigger in window should allow new claim creation."""
        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.first.return_value = None

        should_create, existing, meta = check_and_resolve_aggregation(
            mock_trigger, mock_policy, 300.0, mock_db
        )

        assert should_create is True
        assert existing is None
        assert meta["is_aggregated"] is False
        assert meta["primary_trigger_id"] == mock_trigger.id

    def test_subsequent_trigger_aggregates(self, mock_trigger, mock_policy, mock_db, mock_claim):
        """Subsequent trigger in window should aggregate with existing claim."""
        # Setup existing claim
        mock_claim.validation_data = json.dumps({
            "aggregation": {
                "group_id": "AGG-TEST123",
                "is_aggregated": False,
                "primary_trigger_id": 0,
                "triggers_in_window": [{"id": 0, "payout": 200.0}]
            }
        })
        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.first.return_value = mock_claim

        # Mock finding triggers in window
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            MagicMock(id=0, trigger_type=TriggerType.AQI, severity=3, started_at=utcnow()),
            mock_trigger,
        ]

        should_create, existing, meta = check_and_resolve_aggregation(
            mock_trigger, mock_policy, 300.0, mock_db
        )

        # Should NOT create new claim when aggregating
        assert should_create is False
        assert existing is not None
        assert meta["is_aggregated"] is True


class TestAggregationStats:
    """Test aggregation statistics."""

    def test_metadata_structure(self):
        """Aggregation metadata should have all required fields."""
        triggers = [
            MagicMock(id=1, trigger_type=TriggerType.RAIN, severity=4, started_at=utcnow()),
        ]
        payouts = {1: 300.0}
        policy = MagicMock(max_daily_payout=1000.0)

        final_payout, meta = calculate_aggregated_payout(triggers, policy, payouts)

        required_fields = [
            "group_id", "is_aggregated", "primary_trigger_id",
            "suppressed_triggers", "pre_aggregation_payout",
            "post_aggregation_payout", "savings", "uplift_applied",
            "uplift_percent", "uplift_amount", "triggers_in_window",
            "window_hours", "aggregated_at"
        ]
        for field in required_fields:
            assert field in meta, f"Missing field: {field}"
