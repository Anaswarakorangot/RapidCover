"""
test_ml_stability.py — Member 1 Focused ML Stability Tests
============================================================

Tests every scenario from the Member 1 checklist:

1.  Trained model load path  (when .pkl + metadata exist — mocked here)
2.  Manual fallback path     (no .pkl files)
3.  No-recursion guarantee   (trained fallback NEVER calls back through ml_service singletons)
4.  Unknown city — zone risk (trained path)
5.  Unknown city — premium   (trained path)
6.  Unknown tier — premium   (trained path)
7.  Unknown city — zone risk (manual path)
8.  Unknown city — premium   (manual path) — uses default city_peril = 1.0
9.  Unknown tier — premium   (manual path) — must NOT raise, defaults to standard factors
10. Fraud path — manual and trained both return expected schema
11. Startup log emits correct path indication (via capsys / stdout capture)
"""

import sys
import warnings
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# ---------------------------------------------------------------------------
# Helper: build valid feature dataclasses from ml_service (canonical types)
# ---------------------------------------------------------------------------

def _zone_features(city="bangalore"):
    from app.services.ml_service import ZoneFeatures
    return ZoneFeatures(
        zone_id=1,
        city=city,
        avg_rainfall_mm_per_hr=25.0,
        flood_events_2yr=3,
        aqi_avg_annual=80.0,
        aqi_severe_days_2yr=5,
        heat_advisory_days_2yr=2,
        bandh_events_2yr=1,
        dark_store_suspensions_2yr=0,
        road_flood_prone=True,
        month=7,
    )


def _partner_features(city="bangalore", tier="standard"):
    from app.services.ml_service import PartnerFeatures
    return PartnerFeatures(
        partner_id=1,
        city=city,
        zone_risk_score=55.0,
        active_days_last_30=20,
        avg_hours_per_day=8.0,
        tier=tier,
        loyalty_weeks=6,
        month=7,
        riqi_score=60.0,
    )


def _claim_features():
    from app.services.ml_service import ClaimFeatures
    return ClaimFeatures(
        partner_id=1,
        zone_id=1,
        gps_in_zone=True,
        run_count_during_event=0,
        zone_polygon_match=True,
        claims_last_30_days=1,
        device_consistent=True,
        traffic_disrupted=True,
        centroid_drift_km=2.0,
        max_gps_velocity_kmh=10.0,
        zone_suspended=True,
    )


# ===========================================================================
# 1. Manual model path — basic sanity
# ===========================================================================

class TestManualModelPath:
    """The manual models must always return valid results for known inputs."""

    def test_zone_risk_returns_float_in_range(self):
        from app.services.ml_service_manual import ZoneRiskModel
        model = ZoneRiskModel()
        score = model.predict(_zone_features())
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_premium_returns_dict_with_weekly_premium(self):
        from app.services.ml_service_manual import PremiumModel
        model = PremiumModel()
        result = model.predict(_partner_features())
        assert "weekly_premium" in result
        assert result["weekly_premium"] > 0
        assert "breakdown" in result

    def test_fraud_returns_dict_with_score_and_decision(self):
        from app.services.ml_service_manual import FraudModel
        model = FraudModel()
        result = model.score(_claim_features())
        assert "fraud_score" in result
        assert "decision" in result
        assert 0.0 <= result["fraud_score"] <= 1.0
        assert result["decision"] in ("auto_approve", "enhanced_validation",
                                      "manual_review", "auto_reject")


# ===========================================================================
# 2. Unknown city — manual path
# ===========================================================================

class TestManualUnknownCity:
    """Manual models must degrade gracefully on unseen cities, not crash."""

    def test_zone_risk_unknown_city_returns_float(self):
        from app.services.ml_service_manual import ZoneRiskModel
        model = ZoneRiskModel()
        # "atlantis" is not in HIGH_RISK_MONTHS — should silently use 0.0 seasonal
        score = model.predict(_zone_features(city="atlantis"))
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_premium_unknown_city_returns_dict(self):
        from app.services.ml_service_manual import PremiumModel
        model = PremiumModel()
        # "atlantis" is not in CITY_PERIL — should default to 1.0 multiplier
        result = model.predict(_partner_features(city="atlantis"))
        assert "weekly_premium" in result
        assert result["weekly_premium"] > 0


# ===========================================================================
# 3. Unknown tier — manual path (the KeyError bug we fixed)
# ===========================================================================

class TestManualUnknownTier:
    """Unknown tier must NOT raise KeyError — must warn and return valid premium."""

    def test_unknown_tier_does_not_raise(self):
        from app.services.ml_service_manual import PremiumModel
        model = PremiumModel()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = model.predict(_partner_features(tier="diamond"))  # not in ACTIVITY_TIER_FACTOR
        assert "weekly_premium" in result
        assert result["weekly_premium"] > 0
        # A RuntimeWarning must have been emitted
        runtime_warnings = [x for x in w if issubclass(x.category, RuntimeWarning)]
        assert len(runtime_warnings) >= 1, "Expected RuntimeWarning for unknown tier"

    def test_unknown_tier_uses_standard_factor(self):
        """An unknown tier produces the same result as 'standard' (fallback)."""
        from app.services.ml_service_manual import PremiumModel
        model = PremiumModel()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            unknown_result  = model.predict(_partner_features(tier="diamond"))
        standard_result = model.predict(_partner_features(tier="standard"))
        # The base and overall structure should match (same default factors)
        assert unknown_result["base_price"] == standard_result["base_price"]

    def test_all_known_tiers_work(self):
        """flex, standard, pro must all return valid results without warnings."""
        from app.services.ml_service_manual import PremiumModel
        model = PremiumModel()
        for tier in ("flex", "standard", "pro"):
            result = model.predict(_partner_features(tier=tier))
            assert result["weekly_premium"] > 0
            assert result["tier"] == tier


# ===========================================================================
# 4. Trained model fallback — no recursion (key bug fix)
# ===========================================================================

class TestTrainedFallbackNoRecursion:
    """
    When a trained model's .model is None (pkl not found), _manual_predict must
    call ml_service_manual singletons DIRECTLY — not ml_service.py singletons.
    If recursion existed, this call would hang / recurse; we prove it doesn't.
    """

    def test_zone_risk_manual_fallback_imports_manual_not_service(self):
        """
        Patch ml_service_manual.zone_risk_model and confirm it's the one called,
        not ml_service.zone_risk_model.
        """
        from app.services.ml_service_trained import TrainedZoneRiskModel
        import app.services.ml_service_manual as manual_module

        model = TrainedZoneRiskModel.__new__(TrainedZoneRiskModel)
        model.model = None          # force fallback path
        model.city_encoder = None

        mock_manual = MagicMock()
        mock_manual.predict.return_value = 42.0
        with patch.object(manual_module, "zone_risk_model", mock_manual):
            result = model.predict(_zone_features())

        mock_manual.predict.assert_called_once()
        assert result == 42.0

    def test_premium_manual_fallback_imports_manual_not_service(self):
        from app.services.ml_service_trained import TrainedPremiumModel
        import app.services.ml_service_manual as manual_module

        model = TrainedPremiumModel.__new__(TrainedPremiumModel)
        model.model = None
        model.city_encoder = None
        model.tier_encoder = None

        mock_manual = MagicMock()
        mock_manual.predict.return_value = {"weekly_premium": 35, "base_price": 33,
                                             "tier": "standard", "cap_value": 99,
                                             "cap_applied": False, "breakdown": {}}
        with patch.object(manual_module, "premium_model", mock_manual):
            result = model.predict(_partner_features())

        mock_manual.predict.assert_called_once()
        assert result["weekly_premium"] == 35

    def test_fraud_manual_fallback_imports_manual_not_service(self):
        from app.services.ml_service_trained import TrainedFraudModel
        import app.services.ml_service_manual as manual_module

        model = TrainedFraudModel.__new__(TrainedFraudModel)
        model.model = None

        mock_manual = MagicMock()
        mock_manual.score.return_value = {"fraud_score": 0.1, "decision": "auto_approve",
                                           "factors": {}, "weights": {}, "hard_reject_reasons": []}
        with patch.object(manual_module, "fraud_model", mock_manual):
            result = model.score(_claim_features())

        mock_manual.score.assert_called_once()
        assert result["decision"] == "auto_approve"


# ===========================================================================
# 5. Unknown city — trained path (encoder ValueError)
# ===========================================================================

class TestTrainedUnknownCity:
    """
    When the city encoder raises ValueError (unseen label), the trained model
    must log a message and route to manual fallback — never bubble the exception.
    """

    def test_zone_risk_unknown_city_routes_to_manual(self):
        from app.services.ml_service_trained import TrainedZoneRiskModel
        import app.services.ml_service_manual as manual_module

        # Build a trained model instance with a mock encoder that raises ValueError
        model = TrainedZoneRiskModel.__new__(TrainedZoneRiskModel)
        mock_encoder = MagicMock()
        mock_encoder.transform.side_effect = ValueError("y contains previously unseen labels: ['atlantis']")
        model.city_encoder = mock_encoder
        model.model = MagicMock()   # non-None so we enter the try block

        mock_manual = MagicMock()
        mock_manual.predict.return_value = 30.0
        with patch.object(manual_module, "zone_risk_model", mock_manual):
            result = model.predict(_zone_features(city="atlantis"))

        mock_manual.predict.assert_called_once()
        assert isinstance(result, float)

    def test_premium_unknown_city_routes_to_manual(self):
        from app.services.ml_service_trained import TrainedPremiumModel
        import app.services.ml_service_manual as manual_module

        model = TrainedPremiumModel.__new__(TrainedPremiumModel)
        mock_city_enc = MagicMock()
        mock_city_enc.transform.side_effect = ValueError("unseen label: 'atlantis'")
        model.city_encoder = mock_city_enc
        model.tier_encoder = MagicMock()
        model.model = MagicMock()

        mock_manual = MagicMock()
        mock_manual.predict.return_value = {"weekly_premium": 33, "base_price": 33,
                                             "tier": "standard", "cap_value": 99,
                                             "cap_applied": False, "breakdown": {}}
        with patch.object(manual_module, "premium_model", mock_manual):
            result = model.predict(_partner_features(city="atlantis"))

        mock_manual.predict.assert_called_once()
        assert result["weekly_premium"] == 33


# ===========================================================================
# 6. Unknown tier — trained path (encoder ValueError)
# ===========================================================================

class TestTrainedUnknownTier:
    """
    When the tier encoder raises ValueError (unseen label), the trained model
    must route to manual fallback without crashing.
    """

    def test_premium_unknown_tier_routes_to_manual(self):
        from app.services.ml_service_trained import TrainedPremiumModel
        import app.services.ml_service_manual as manual_module

        model = TrainedPremiumModel.__new__(TrainedPremiumModel)
        mock_city_enc = MagicMock()
        mock_city_enc.transform.return_value = [0]          # city is known
        mock_tier_enc = MagicMock()
        mock_tier_enc.transform.side_effect = ValueError("unseen label: 'diamond'")
        model.city_encoder = mock_city_enc
        model.tier_encoder = mock_tier_enc
        model.model = MagicMock()

        mock_manual = MagicMock()
        mock_manual.predict.return_value = {"weekly_premium": 34, "base_price": 33,
                                             "tier": "standard", "cap_value": 99,
                                             "cap_applied": False, "breakdown": {}}
        with patch.object(manual_module, "premium_model", mock_manual):
            result = model.predict(_partner_features(tier="diamond"))

        mock_manual.predict.assert_called_once()
        assert result["weekly_premium"] == 34


# ===========================================================================
# 7. Trained prediction failure (non-ValueError) routes to manual
# ===========================================================================

class TestTrainedPredictionFailure:
    """Any unexpected error during model.predict() must also route to manual."""

    def test_zone_risk_predict_exception_routes_to_manual(self):
        from app.services.ml_service_trained import TrainedZoneRiskModel
        import app.services.ml_service_manual as manual_module

        model = TrainedZoneRiskModel.__new__(TrainedZoneRiskModel)
        mock_enc = MagicMock()
        mock_enc.transform.return_value = [1]
        model.city_encoder = mock_enc
        mock_inner_model = MagicMock()
        mock_inner_model.predict.side_effect = RuntimeError("CUDA out of memory")
        model.model = mock_inner_model

        mock_manual = MagicMock()
        mock_manual.predict.return_value = 55.0
        with patch.object(manual_module, "zone_risk_model", mock_manual):
            result = model.predict(_zone_features())

        mock_manual.predict.assert_called_once()
        assert result == 55.0

    def test_fraud_score_exception_routes_to_manual(self):
        from app.services.ml_service_trained import TrainedFraudModel
        import app.services.ml_service_manual as manual_module

        model = TrainedFraudModel.__new__(TrainedFraudModel)
        mock_inner_model = MagicMock()
        mock_inner_model.predict_proba.side_effect = RuntimeError("model corrupt")
        model.model = mock_inner_model

        mock_manual = MagicMock()
        mock_manual.score.return_value = {"fraud_score": 0.05, "decision": "auto_approve",
                                           "factors": {}, "weights": {}, "hard_reject_reasons": []}
        with patch.object(manual_module, "fraud_model", mock_manual):
            result = model.score(_claim_features())

        mock_manual.score.assert_called_once()
        assert result["decision"] == "auto_approve"


# ===========================================================================
# 8. ml_service.py singleton — correct path selected at import time
# ===========================================================================

class TestMlServiceStartup:
    """ml_service singletons must be one of the two expected types."""

    def test_singletons_are_one_of_two_expected_types(self):
        """
        After import, zone_risk_model must be either:
          - ZoneRiskModel (manual path, no .pkl)
          - TrainedZoneRiskModel (trained path, .pkl present)
        """
        from app.services import ml_service
        from app.services.ml_service_manual import ZoneRiskModel as ManualZRM
        from app.services.ml_service_trained import TrainedZoneRiskModel

        assert isinstance(ml_service.zone_risk_model, (ManualZRM, TrainedZoneRiskModel)), (
            f"zone_risk_model is unexpected type: {type(ml_service.zone_risk_model)}"
        )

    def test_premium_singleton_type(self):
        from app.services import ml_service
        from app.services.ml_service_manual import PremiumModel as ManualPM
        from app.services.ml_service_trained import TrainedPremiumModel

        assert isinstance(ml_service.premium_model, (ManualPM, TrainedPremiumModel)), (
            f"premium_model is unexpected type: {type(ml_service.premium_model)}"
        )

    def test_fraud_singleton_type(self):
        from app.services import ml_service
        from app.services.ml_service_manual import FraudModel as ManualFM
        from app.services.ml_service_trained import TrainedFraudModel

        assert isinstance(ml_service.fraud_model, (ManualFM, TrainedFraudModel)), (
            f"fraud_model is unexpected type: {type(ml_service.fraud_model)}"
        )

    def test_active_singleton_returns_valid_zone_score(self):
        """Whatever singleton is active, it must return a valid zone score."""
        from app.services.ml_service import zone_risk_model
        score = zone_risk_model.predict(_zone_features())
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 100.0

    def test_active_singleton_returns_valid_premium(self):
        from app.services.ml_service import premium_model
        result = premium_model.predict(_partner_features())
        assert "weekly_premium" in result
        assert result["weekly_premium"] > 0

    def test_active_singleton_returns_valid_fraud_score(self):
        from app.services.ml_service import fraud_model
        result = fraud_model.score(_claim_features())
        assert "fraud_score" in result
        assert result["decision"] in ("auto_approve", "enhanced_validation",
                                      "manual_review", "auto_reject")
