"""
Tests for stress scenario calculations and reserve-needed feature.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class TestStressScenarios:
    """Tests for stress scenario service."""

    def test_monsoon_scenario_calculates_reserve_needed(self, mock_db):
        """Test that monsoon scenario correctly calculates reserve_needed."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        # Mock the city metrics query
        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="bangalore",
                active_policies=100,
                avg_weekly_premium=35.0,
                total_weekly_reserve=3500.0,
                zone_count=5,
            )

            result = calculate_stress_scenario("monsoon_14day_bangalore", mock_db)

            assert result.scenario_id == "monsoon_14day_bangalore"
            assert result.days == 14
            assert result.projected_claims > 0
            assert result.projected_payout > 0

            # reserve_needed = max(projected_payout - city_reserve_available, 0)
            expected_reserve = max(result.projected_payout - result.city_reserve_available, 0)
            assert result.reserve_needed == expected_reserve
            assert result.reserve_needed >= 0

    def test_stress_scenario_with_zero_premiums(self, mock_db):
        """Test scenario with no collected premiums (zero reserve)."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="bangalore",
                active_policies=50,
                avg_weekly_premium=0.0,
                total_weekly_reserve=0.0,
                zone_count=5,
            )

            result = calculate_stress_scenario("monsoon_14day_bangalore", mock_db)

            # With zero reserve, reserve_needed = projected_payout
            assert result.city_reserve_available == 0.0
            assert result.reserve_needed == result.projected_payout

    def test_stress_scenario_formula_breakdown_complete(self, mock_db):
        """Test that formula breakdown contains all required steps."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="bangalore",
                active_policies=100,
                avg_weekly_premium=35.0,
                total_weekly_reserve=3500.0,
                zone_count=5,
            )

            result = calculate_stress_scenario("monsoon_14day_bangalore", mock_db)

            # Check all steps are present
            breakdown = result.formula_breakdown
            assert "step_1_active_policies" in breakdown
            assert "step_2_trigger_probability" in breakdown
            assert "step_3_days" in breakdown
            assert "step_4_projected_claims" in breakdown
            assert "step_5_weighted_avg_payout" in breakdown
            assert "step_6_severity_multiplier" in breakdown
            assert "step_7_avg_payout_with_severity" in breakdown
            assert "step_8_projected_payout" in breakdown
            assert "step_9_city_reserve_available" in breakdown
            assert "step_10_reserve_needed" in breakdown

    def test_multiple_scenarios_return_all(self, mock_db):
        """Test that get_all_stress_scenarios returns all defined scenarios."""
        from app.services.stress_scenario_service import (
            get_all_stress_scenarios,
            get_scenario_ids,
        )

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="test",
                active_policies=50,
                avg_weekly_premium=30.0,
                total_weekly_reserve=1500.0,
                zone_count=3,
            )

            result = get_all_stress_scenarios(mock_db)
            scenario_ids = get_scenario_ids()

            assert len(result.scenarios) == len(scenario_ids)
            assert result.total_reserve_needed >= 0
            assert result.computed_at is not None

            # Check all scenarios are present
            returned_ids = {s.scenario_id for s in result.scenarios}
            for expected_id in scenario_ids:
                assert expected_id in returned_ids

    def test_unknown_scenario_returns_default(self, mock_db):
        """Test that unknown scenario ID returns safe default."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        result = calculate_stress_scenario("nonexistent_scenario", mock_db)

        assert result.scenario_name == "Unknown Scenario"
        assert result.days == 0
        assert result.projected_claims == 0
        assert result.reserve_needed == 0.0
        assert "Scenario not found" in result.assumptions

    def test_data_source_is_live_when_policies_exist(self, mock_db):
        """Test that data_source is 'live' when active policies exist."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="delhi",
                active_policies=25,  # > 0
                avg_weekly_premium=40.0,
                total_weekly_reserve=1000.0,
                zone_count=3,
            )

            result = calculate_stress_scenario("aqi_crisis_7day_delhi", mock_db)
            assert result.data_source == "live"

    def test_data_source_is_mock_when_no_policies(self, mock_db):
        """Test that data_source is 'mock' when no active policies."""
        from app.services.stress_scenario_service import calculate_stress_scenario

        with patch("app.services.stress_scenario_service.get_city_metrics") as mock_metrics:
            mock_metrics.return_value = MagicMock(
                city="delhi",
                active_policies=0,  # No policies
                avg_weekly_premium=0.0,
                total_weekly_reserve=0.0,
                zone_count=3,
            )

            result = calculate_stress_scenario("aqi_crisis_7day_delhi", mock_db)
            assert result.data_source == "mock"
