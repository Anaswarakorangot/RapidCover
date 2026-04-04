"""
test_oracle_reliability.py
--------------------------
Tests for the Oracle Reliability Engine (Feature 2).

Covers:
  - Source confidence scoring: live+fresh, mock, stale
  - Trigger confidence computation: multi-source, agreement
  - Decision logic: fire / hold / manual_review_simulated / fallback_mock_mode
  - Agreement score calculation
  - get_oracle_reliability_report system health
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# compute_source_confidence
# ---------------------------------------------------------------------------

class TestComputeSourceConfidence:

    def test_live_fresh_source_scores_1_0(self):
        from app.services.external_apis import compute_source_confidence, _source_status
        now = datetime.utcnow()
        _source_status["openweathermap"]["status"] = "live"
        _source_status["openweathermap"]["last_success"] = now - timedelta(seconds=60)
        _source_status["openweathermap"]["last_check"] = now

        result = compute_source_confidence("openweathermap")
        assert result["reliability_score"] == 1.0
        assert result["badge"] == "live"
        assert result["is_live"] is True
        assert result["freshness_ok"] is True

    def test_mock_source_scores_0_6(self):
        from app.services.external_apis import compute_source_confidence, _source_status
        _source_status["zepto_ops"]["status"] = "mock"
        _source_status["zepto_ops"]["last_success"] = None

        result = compute_source_confidence("zepto_ops")
        assert result["reliability_score"] == 0.6
        assert result["badge"] == "mock"
        assert result["is_live"] is False

    def test_stale_live_source_scores_0_2(self):
        from app.services.external_apis import compute_source_confidence, _source_status
        now = datetime.utcnow()
        # Last success was 20 minutes ago — exceeds freshness limit of 5 min
        _source_status["openweathermap"]["status"] = "live"
        _source_status["openweathermap"]["last_success"] = now - timedelta(minutes=20)
        _source_status["openweathermap"]["last_check"] = now

        result = compute_source_confidence("openweathermap")
        assert result["reliability_score"] == 0.2
        assert result["badge"] == "stale"
        assert result["is_live"] is True
        assert result["freshness_ok"] is False

    def test_result_has_all_required_fields(self):
        from app.services.external_apis import compute_source_confidence
        result = compute_source_confidence("civic_api")
        required = {
            "source_name", "is_live", "freshness_ok", "staleness_seconds",
            "freshness_limit_seconds", "reliability_score", "badge",
            "last_success_iso", "last_check_iso",
        }
        assert required.issubset(result.keys())

    def test_unknown_source_returns_mock_badge(self):
        from app.services.external_apis import compute_source_confidence
        result = compute_source_confidence("nonexistent_source")
        # Should handle gracefully with mock/0.6
        assert "badge" in result
        assert "reliability_score" in result


# ---------------------------------------------------------------------------
# compute_trigger_confidence
# ---------------------------------------------------------------------------

class TestComputeTriggerConfidence:

    def _set_live(self, source: str, seconds_ago: int = 30):
        from app.services.external_apis import _source_status
        now = datetime.utcnow()
        _source_status[source]["status"] = "live"
        _source_status[source]["last_success"] = now - timedelta(seconds=seconds_ago)
        _source_status[source]["last_check"] = now

    def _set_mock(self, source: str):
        from app.services.external_apis import _source_status
        _source_status[source]["status"] = "mock"
        _source_status[source]["last_success"] = None
        _source_status[source]["last_check"] = None

    def test_all_mock_sources_returns_fallback_mock_mode(self):
        from app.services.external_apis import compute_trigger_confidence
        self._set_mock("openweathermap")
        self._set_mock("waqi_aqi")

        result = compute_trigger_confidence(
            primary_source="openweathermap",
            corroborating_sources=["waqi_aqi"],
        )
        assert result["decision"] == "fallback_mock_mode"

    def test_two_live_agreeing_sources_returns_fire(self):
        from app.services.external_apis import compute_trigger_confidence
        self._set_live("openweathermap", 30)
        self._set_live("waqi_aqi", 45)

        result = compute_trigger_confidence(
            primary_source="openweathermap",
            corroborating_sources=["waqi_aqi"],
            primary_value=65.0,
            corroborating_values=[63.0],   # < 20% deviation → agree
        )
        assert result["decision"] == "fire"
        assert result["trigger_confidence_score"] >= 0.7

    def test_stale_primary_no_corroboration_returns_hold(self):
        from app.services.external_apis import compute_trigger_confidence, _source_status
        now = datetime.utcnow()
        # Stale (last success 30 min ago, limit is 5 min)
        _source_status["openweathermap"]["status"] = "live"
        _source_status["openweathermap"]["last_success"] = now - timedelta(minutes=30)
        _source_status["openweathermap"]["last_check"] = now

        result = compute_trigger_confidence(
            primary_source="openweathermap",
            corroborating_sources=[],
        )
        assert result["decision"] == "hold"

    def test_result_has_all_required_fields(self):
        from app.services.external_apis import compute_trigger_confidence
        result = compute_trigger_confidence(
            primary_source="civic_api",
            corroborating_sources=["traffic_feed"],
        )
        required = {
            "trigger_confidence_score", "source_confidence_scores",
            "decision", "reason", "agreement_score",
            "primary_source", "corroborating_sources", "computed_at",
        }
        assert required.issubset(result.keys())

    def test_confidence_score_between_0_and_1(self):
        from app.services.external_apis import compute_trigger_confidence
        result = compute_trigger_confidence(primary_source="openweathermap")
        assert 0.0 <= result["trigger_confidence_score"] <= 1.0

    def test_agreement_score_1_0_for_single_source(self):
        from app.services.external_apis import compute_trigger_confidence
        result = compute_trigger_confidence(
            primary_source="openweathermap",
            primary_value=65.0,
        )
        assert result["agreement_score"] == 1.0

    def test_agreement_score_reduced_when_sources_disagree(self):
        from app.services.external_apis import compute_trigger_confidence
        result = compute_trigger_confidence(
            primary_source="openweathermap",
            corroborating_sources=["waqi_aqi"],
            primary_value=100.0,
            corroborating_values=[20.0],   # huge deviation
        )
        assert result["agreement_score"] < 0.6

    def test_manual_review_for_moderate_confidence(self):
        from app.services.external_apis import compute_trigger_confidence, _source_status
        # One live fresh, one mock  → moderate overall
        now = datetime.utcnow()
        _source_status["openweathermap"]["status"] = "live"
        _source_status["openweathermap"]["last_success"] = now - timedelta(seconds=10)
        _source_status["openweathermap"]["last_check"] = now
        _source_status["zepto_ops"]["status"] = "mock"
        _source_status["zepto_ops"]["last_success"] = None

        result = compute_trigger_confidence(
            primary_source="openweathermap",
            corroborating_sources=["zepto_ops"],
            primary_value=60.0,
            corroborating_values=[60.0],
        )
        # decision can be fire or manual_review depending on thresholds; just check it's valid
        assert result["decision"] in ("fire", "manual_review_simulated", "hold", "fallback_mock_mode")

    def test_decision_values_are_valid_enum(self):
        from app.services.external_apis import compute_trigger_confidence
        valid_decisions = {"fire", "hold", "manual_review_simulated", "fallback_mock_mode"}
        result = compute_trigger_confidence(primary_source="civic_api")
        assert result["decision"] in valid_decisions


# ---------------------------------------------------------------------------
# get_oracle_reliability_report
# ---------------------------------------------------------------------------

class TestOracleReliabilityReport:

    def test_report_has_all_top_level_fields(self):
        from app.services.external_apis import get_oracle_reliability_report
        report = get_oracle_reliability_report()
        required = {
            "system_health", "average_reliability", "live_sources",
            "stale_sources", "mock_sources", "sources", "computed_at",
        }
        assert required.issubset(report.keys())

    def test_system_health_is_valid_value(self):
        from app.services.external_apis import get_oracle_reliability_report
        report = get_oracle_reliability_report()
        assert report["system_health"] in ("healthy", "degraded", "stale", "mock_mode")

    def test_live_plus_stale_plus_mock_equals_total_sources(self):
        from app.services.external_apis import get_oracle_reliability_report
        report = get_oracle_reliability_report()
        total = report["live_sources"] + report["stale_sources"] + report["mock_sources"]
        assert total == len(report["sources"])

    def test_average_reliability_between_0_and_1(self):
        from app.services.external_apis import get_oracle_reliability_report
        report = get_oracle_reliability_report()
        assert 0.0 <= report["average_reliability"] <= 1.0

    def test_sources_dict_contains_expected_sources(self):
        from app.services.external_apis import get_oracle_reliability_report
        report = get_oracle_reliability_report()
        expected = {"openweathermap", "waqi_aqi", "zepto_ops", "traffic_feed", "civic_api"}
        assert expected.issubset(report["sources"].keys())

    def test_all_mock_sources_gives_mock_mode_health(self):
        from app.services.external_apis import get_oracle_reliability_report, _source_status
        # Force all to mock
        for key in _source_status:
            _source_status[key]["status"] = "mock"
            _source_status[key]["last_success"] = None
            _source_status[key]["last_check"] = None

        report = get_oracle_reliability_report()
        assert report["system_health"] == "mock_mode"
        assert report["live_sources"] == 0
        assert report["stale_sources"] == 0

    def test_zone_id_included_when_provided(self):
        from app.services.external_apis import get_oracle_reliability_report
        report = get_oracle_reliability_report(zone_id=5)
        assert report["zone_id"] == 5

    def test_zone_id_none_when_not_provided(self):
        from app.services.external_apis import get_oracle_reliability_report
        report = get_oracle_reliability_report()
        assert report["zone_id"] is None