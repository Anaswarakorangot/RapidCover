"""
ml_service_trained.py
-----------------------------------------------------------------------------
RapidCover ML Service - Production version with trained models.

Loads real trained XGBoost/scikit-learn models from ml_models/ directory.
Falls back to manual models if trained models not available.
-----------------------------------------------------------------------------
"""

from dataclasses import dataclass
from pathlib import Path
import joblib
import numpy as np
import json


# Get the path to trained models
ML_MODELS_DIR = Path(__file__).parent.parent.parent / "ml_models"


# ------------------------------------------------------------------------------
# INPUT DATACLASSES (same as original)
# ------------------------------------------------------------------------------

@dataclass
class ZoneFeatures:
    """Features for Zone Risk Scorer (XGBoost Classifier)."""
    zone_id:                     int
    city:                        str
    avg_rainfall_mm_per_hr:      float
    flood_events_2yr:            int
    aqi_avg_annual:              float
    aqi_severe_days_2yr:         int
    heat_advisory_days_2yr:      int
    bandh_events_2yr:            int
    dark_store_suspensions_2yr:  int
    road_flood_prone:            bool
    month:                       int   # 1-12


@dataclass
class PartnerFeatures:
    """Features for Dynamic Premium Engine (Gradient Boosted Regression)."""
    partner_id:           int
    city:                 str
    zone_risk_score:      float   # 0-100
    active_days_last_30:  int
    avg_hours_per_day:    float
    tier:                 str     # flex | standard | pro
    loyalty_weeks:        int
    month:                int
    riqi_score:           float   # 0-100


@dataclass
class ClaimFeatures:
    """Features for Fraud Anomaly Detector (Isolation Forest)."""
    partner_id:               int
    zone_id:                  int
    gps_in_zone:              bool
    run_count_during_event:   int
    zone_polygon_match:       bool
    claims_last_30_days:      int
    device_consistent:        bool
    traffic_disrupted:        bool
    centroid_drift_km:        float
    max_gps_velocity_kmh:     float
    zone_suspended:           bool


# ------------------------------------------------------------------------------
# TRAINED MODEL WRAPPERS
# ------------------------------------------------------------------------------

class TrainedZoneRiskModel:
    """XGBoost/GradientBoosting Regressor for zone risk scoring."""

    def __init__(self):
        self.model = None
        self.city_encoder = None
        self._load_model()

    def _load_model(self):
        """Load trained model and encoders."""
        try:
            model_path = ML_MODELS_DIR / "zone_risk_model.pkl"
            encoder_path = ML_MODELS_DIR / "zone_risk_city_encoder.pkl"

            if model_path.exists() and encoder_path.exists():
                self.model = joblib.load(model_path)
                self.city_encoder = joblib.load(encoder_path)
                print(f"[ML] Loaded trained Zone Risk model from {model_path}")
            else:
                print(f"[ML] Trained models not found at {model_path}")
                print("[ML] Falling back to manual zone risk model")
        except Exception as e:
            print(f"[ML] Error loading zone risk model: {e}")
            print("[ML] Falling back to manual zone risk model")

    def predict(self, features: ZoneFeatures) -> float:
        """Returns risk score 0-100."""
        if self.model is None or self.city_encoder is None:
            # Fallback to manual model
            return self._manual_predict(features)

        try:
            # Encode city
            city_encoded = self.city_encoder.transform([features.city.lower()])[0]

            # Prepare features
            X = np.array([[
                city_encoded,
                features.avg_rainfall_mm_per_hr,
                features.flood_events_2yr,
                features.aqi_avg_annual,
                features.aqi_severe_days_2yr,
                features.heat_advisory_days_2yr,
                features.bandh_events_2yr,
                features.dark_store_suspensions_2yr,
                int(features.road_flood_prone),
                features.month
            ]])

            # Predict
            risk_score = self.model.predict(X)[0]
            return round(float(np.clip(risk_score, 0, 100)), 2)

        except Exception as e:
            print(f"[ML] Error predicting zone risk: {e}")
            return self._manual_predict(features)

    def _manual_predict(self, features: ZoneFeatures) -> float:
        """Fallback manual prediction (original logic)."""
        from app.services.ml_service import zone_risk_model as manual_model
        return manual_model.predict(features)


class TrainedPremiumModel:
    """XGBoost/GradientBoosting Regressor for premium calculation."""

    def __init__(self):
        self.model = None
        self.city_encoder = None
        self.tier_encoder = None
        self._load_model()

    def _load_model(self):
        """Load trained model and encoders."""
        try:
            model_path = ML_MODELS_DIR / "premium_model.pkl"
            city_encoder_path = ML_MODELS_DIR / "premium_city_encoder.pkl"
            tier_encoder_path = ML_MODELS_DIR / "premium_tier_encoder.pkl"

            if all(p.exists() for p in [model_path, city_encoder_path, tier_encoder_path]):
                self.model = joblib.load(model_path)
                self.city_encoder = joblib.load(city_encoder_path)
                self.tier_encoder = joblib.load(tier_encoder_path)
                print(f"[ML] Loaded trained Premium model from {model_path}")
            else:
                print(f"[ML] Trained models not found")
                print("[ML] Falling back to manual premium model")
        except Exception as e:
            print(f"[ML] Error loading premium model: {e}")
            print("[ML] Falling back to manual premium model")

    def predict(self, features: PartnerFeatures) -> dict:
        """Returns weekly_premium + breakdown."""
        if self.model is None or self.city_encoder is None or self.tier_encoder is None:
            # Fallback to manual model
            return self._manual_predict(features)

        try:
            # Encode categoricals
            city_encoded = self.city_encoder.transform([features.city.lower()])[0]
            tier_encoded = self.tier_encoder.transform([features.tier.lower()])[0]

            # Prepare features
            X = np.array([[
                city_encoded,
                features.zone_risk_score,
                features.active_days_last_30,
                features.avg_hours_per_day,
                tier_encoded,
                features.loyalty_weeks,
                features.month,
                features.riqi_score
            ]])

            # Predict
            premium = self.model.predict(X)[0]

            # Apply tier base and cap
            base_prices = {"flex": 22, "standard": 33, "pro": 45}
            tier = features.tier.lower()
            base = base_prices.get(tier, 33)
            cap = base * 3.0

            premium = np.clip(premium, base, cap)

            return {
                "weekly_premium": int(round(premium)),
                "base_price": base,
                "tier": tier,
                "cap_value": int(cap),
                "cap_applied": premium >= cap,
                "model_type": "trained_ml",
                "breakdown": {
                    "ml_predicted_premium": float(premium),
                    "note": "Premium calculated using trained ML model"
                }
            }

        except Exception as e:
            print(f"[ML] Error predicting premium: {e}")
            return self._manual_predict(features)

    def _manual_predict(self, features: PartnerFeatures) -> dict:
        """Fallback manual prediction (original logic)."""
        from app.services.ml_service import premium_model as manual_model
        return manual_model.predict(features)


class TrainedFraudModel:
    """XGBoost/GradientBoosting Classifier for fraud detection."""

    # Thresholds from original model
    VELOCITY_SPOOF_KMH = 60.0
    CENTROID_FLAG_KM = 15.0

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load trained model."""
        try:
            model_path = ML_MODELS_DIR / "fraud_model.pkl"

            if model_path.exists():
                self.model = joblib.load(model_path)
                print(f"[ML] Loaded trained Fraud model from {model_path}")
            else:
                print(f"[ML] Trained model not found at {model_path}")
                print("[ML] Falling back to manual fraud model")
        except Exception as e:
            print(f"[ML] Error loading fraud model: {e}")
            print("[ML] Falling back to manual fraud model")

    def score(self, features: ClaimFeatures) -> dict:
        """Returns fraud score 0-1, decision, factor breakdown."""
        if self.model is None:
            # Fallback to manual model
            return self._manual_score(features)

        try:
            hard_reject_reasons = []

            # Hard pre-checks (same as original)
            if features.max_gps_velocity_kmh > self.VELOCITY_SPOOF_KMH:
                hard_reject_reasons.append(
                    f"GPS velocity {features.max_gps_velocity_kmh:.1f} km/h "
                    f"exceeds {self.VELOCITY_SPOOF_KMH} km/h - spoof detected"
                )
            if not features.zone_suspended:
                hard_reject_reasons.append("Zone suspension not confirmed by platform API")
            if features.run_count_during_event > 0:
                hard_reject_reasons.append(
                    f"Activity Paradox: {features.run_count_during_event} "
                    f"run(s) completed during suspended window"
                )

            # Prepare features
            X = np.array([[
                int(features.gps_in_zone),
                features.run_count_during_event,
                int(features.zone_polygon_match),
                features.claims_last_30_days,
                int(features.device_consistent),
                int(features.traffic_disrupted),
                features.centroid_drift_km,
                features.max_gps_velocity_kmh,
                int(features.zone_suspended)
            ]])

            # Predict fraud probability
            fraud_prob = self.model.predict_proba(X)[0][1]  # Probability of fraud (class 1)
            fraud_score = round(float(np.clip(fraud_prob, 0, 1)), 4)

            # Decision thresholds (same as original)
            if hard_reject_reasons:
                decision = "auto_reject"
                fraud_score = max(fraud_score, 0.91)
            elif fraud_score < 0.50:
                decision = "auto_approve"
            elif fraud_score < 0.75:
                decision = "enhanced_validation"
            elif fraud_score < 0.90:
                decision = "manual_review"
            else:
                decision = "auto_reject"

            return {
                "fraud_score": fraud_score,
                "decision": decision,
                "model_type": "trained_ml",
                "factors": {
                    "gps_in_zone": features.gps_in_zone,
                    "run_count_during_event": features.run_count_during_event,
                    "zone_polygon_match": features.zone_polygon_match,
                    "claims_last_30_days": features.claims_last_30_days,
                    "device_consistent": features.device_consistent,
                    "traffic_disrupted": features.traffic_disrupted,
                    "centroid_drift_km": features.centroid_drift_km
                },
                "hard_reject_reasons": hard_reject_reasons
            }

        except Exception as e:
            print(f"[ML] Error scoring fraud: {e}")
            return self._manual_score(features)

    def _manual_score(self, features: ClaimFeatures) -> dict:
        """Fallback manual scoring (original logic)."""
        from app.services.ml_service import fraud_model as manual_model
        return manual_model.score(features)


# ------------------------------------------------------------------------------
# SINGLETONS - Use these in production
# ------------------------------------------------------------------------------

zone_risk_model = TrainedZoneRiskModel()
premium_model = TrainedPremiumModel()
fraud_model = TrainedFraudModel()
