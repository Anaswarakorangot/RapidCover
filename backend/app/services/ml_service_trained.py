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
import time

from app.services.ml_monitoring import ml_monitor


# Get the path to trained models
ML_MODELS_DIR = Path(__file__).parent.parent.parent / "ml_models"


# Load ML model metadata (version info, training metrics, features)
MODEL_METADATA = {}
try:
    metadata_path = ML_MODELS_DIR / "model_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            MODEL_METADATA = json.load(f)
        print(f"[ML] Loaded model metadata v{MODEL_METADATA.get('version', '1.0.0')}")
        print(f"[ML] Training date: {MODEL_METADATA.get('training_date', 'unknown')}")

        # Log individual model info
        models = MODEL_METADATA.get("models", {})
        if "zone_risk" in models:
            print(f"[ML] Zone Risk: {models['zone_risk']['model_type']} (R²={models['zone_risk']['r2_score']:.3f})")
        if "premium" in models:
            print(f"[ML] Premium: {models['premium']['model_type']} (R²={models['premium']['r2_score']:.3f})")
        if "fraud" in models:
            print(f"[ML] Fraud: {models['fraud']['model_type']} (ROC-AUC={models['fraud']['roc_auc']:.3f})")
    else:
        print(f"[ML] Warning: Model metadata file not found at {metadata_path}")
except Exception as e:
    print(f"[ML] Warning: Could not load model metadata: {e}")


def get_model_metadata() -> dict:
    """
    Get ML model metadata including version, training info, and metrics.

    Returns:
        Dict with version, training_date, and per-model metrics
    """
    return MODEL_METADATA


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
        start_time = time.time()
        fallback_used = False

        if self.model is None or self.city_encoder is None:
            result = self._manual_predict(features)
            fallback_used = True
            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("zone_risk", latency_ms, fallback=fallback_used)
            return result

        try:
            # Explicit unknown-city guard — encoder raises ValueError for unseen labels
            try:
                city_encoded = self.city_encoder.transform([features.city.lower()])[0]
            except ValueError:
                print(f"[ML] Unknown city '{features.city}' for zone risk encoder — using manual fallback")
                result = self._manual_predict(features)
                fallback_used = True
                latency_ms = (time.time() - start_time) * 1000
                ml_monitor.record_prediction("zone_risk", latency_ms, fallback=fallback_used)
                return result

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

            risk_score = self.model.predict(X)[0]
            result = round(float(np.clip(risk_score, 0, 100)), 2)
            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("zone_risk", latency_ms, fallback=False)
            return result

        except Exception as e:
            print(f"[ML] Error predicting zone risk: {e} — using manual fallback")
            result = self._manual_predict(features)
            fallback_used = True
            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("zone_risk", latency_ms, fallback=fallback_used)
            return result

    def _manual_predict(self, features: ZoneFeatures) -> float:
        """
        Fallback manual prediction.
        Imports directly from ml_service_manual to avoid circular imports
        and recursion through ml_service.py singletons.
        """
        from app.services.ml_service_manual import zone_risk_model as _manual
        return _manual.predict(features)


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
        """Returns weekly_premium + breakdown + feature_contributions for UI."""
        start_time = time.time()
        fallback_used = False

        if self.model is None or self.city_encoder is None or self.tier_encoder is None:
            result = self._manual_predict(features)
            fallback_used = True
            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("premium", latency_ms, fallback=fallback_used)
            return result

        try:
            # Explicit unknown-label guard
            try:
                city_encoded = self.city_encoder.transform([features.city.lower()])[0]
                tier_encoded = self.tier_encoder.transform([features.tier.lower()])[0]
            except ValueError as ve:
                print(f"[ML] Unknown city/tier for premium encoder ('{ve}') — using manual fallback")
                result = self._manual_predict(features)
                fallback_used = True
                latency_ms = (time.time() - start_time) * 1000
                ml_monitor.record_prediction("premium", latency_ms, fallback=fallback_used)
                return result

            # Prepare base feature vector
            base_vec = np.array([[
                city_encoded,
                features.zone_risk_score,
                features.active_days_last_30,
                features.avg_hours_per_day,
                tier_encoded,
                features.loyalty_weeks,
                features.month,
                features.riqi_score
            ]])

            raw_payout = float(self.model.predict(base_vec)[0])

            # Deterministic insurance constraints (NEVER learned by ML)
            base_prices = {"flex": 22, "standard": 33, "pro": 45}
            tier = features.tier.lower()
            base = base_prices.get(tier, 33)
            cap = base * 3.0
            weekly_premium = float(np.clip(raw_payout, base, cap))

            # ------------------------------------------------------------------
            # Feature contribution — perturbation-based attribution
            # Replace each feature with a neutral mid-range value and measure
            # the change in predicted payout pressure.
            # impact_rs > 0 means the feature raises the premium vs neutral.
            # Person 2 uses this to display top quote drivers in the UI.
            # ------------------------------------------------------------------
            feature_names = [
                "city_encoded", "zone_risk_score", "active_days_last_30",
                "avg_hours_per_day", "tier_encoded", "loyalty_weeks",
                "month", "riqi_score"
            ]
            neutral_vec = np.array([[
                city_encoded, 50.0, 22, 6.0, tier_encoded, 4, 6, 65.0
            ]])
            feature_labels = {
                "zone_risk_score":     "Zone Risk Level",
                "active_days_last_30": "Active Days This Month",
                "avg_hours_per_day":   "Avg Daily Hours",
                "loyalty_weeks":       "Loyalty Duration",
                "month":               "Current Season",
                "riqi_score":          "Infrastructure Quality (RIQI)",
                "city_encoded":        "City Risk Profile",
                "tier_encoded":        "Coverage Tier",
            }
            contributions = []
            for i, fname in enumerate(feature_names):
                if fname in ("city_encoded", "tier_encoded"):
                    continue
                perturbed = base_vec.copy()
                perturbed[0, i] = neutral_vec[0, i]
                perturbed_payout = float(self.model.predict(perturbed)[0])
                impact = raw_payout - perturbed_payout
                contributions.append({
                    "feature": fname,
                    "label": feature_labels.get(fname, fname),
                    "value": float(base_vec[0, i]),
                    "impact_rs": round(float(impact), 2),
                    "direction": "increases" if impact > 0.5 else ("decreases" if impact < -0.5 else "neutral"),
                })
            contributions.sort(key=lambda x: abs(x["impact_rs"]), reverse=True)

            result = {
                "weekly_premium": int(round(weekly_premium)),
                "base_price": base,
                "tier": tier,
                "cap_value": int(cap),
                "cap_applied": bool(weekly_premium >= cap),
                "model_type": "trained_ml",
                "ml_raw_payout_pressure": round(raw_payout, 2),
                "deterministic_constraints": {
                    "tier_floor_applied": bool(weekly_premium <= base + 1),
                    "irdai_cap_applied": bool(weekly_premium >= cap - 1),
                    "note": "IRDAI 3x cap and tier floor enforced deterministically after ML output"
                },
                "breakdown": {
                    "ml_predicted_payout_pressure_rs": round(raw_payout, 2),
                    "note": "ML predicts expected payout pressure. Tier floor + IRDAI cap applied deterministically."
                },
                "feature_contributions": contributions,
                "top_driver": contributions[0]["label"] if contributions else "Coverage Tier",
            }

            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("premium", latency_ms, fallback=False)
            return result

        except Exception as e:
            print(f"[ML] Error predicting premium: {e} — using manual fallback")
            result = self._manual_predict(features)
            fallback_used = True
            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("premium", latency_ms, fallback=fallback_used)
            return result

    def _manual_predict(self, features: PartnerFeatures) -> dict:
        """
        Fallback manual prediction.
        Imports directly from ml_service_manual to avoid circular imports
        and recursion through ml_service.py singletons.
        """
        from app.services.ml_service_manual import premium_model as _manual
        return _manual.predict(features)


class TrainedFraudModel:
    """RandomForestClassifier for fraud detection (supervised, v2.0).

    Trained on policy-grounded independent labels (NOT the runtime weighted
    scoring formula). Deterministic hard-stops always override ML output.
    """

    # Thresholds from original model
    VELOCITY_SPOOF_KMH = 60.0
    CENTROID_FLAG_KM = 15.0


    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load trained Isolation Forest model."""
        try:
            model_path = ML_MODELS_DIR / "fraud_model.pkl"

            if model_path.exists():
                self.model = joblib.load(model_path)
                model_type = type(self.model).__name__
                print(f"[ML] Loaded trained Fraud model ({model_type}) from {model_path}")
            else:
                print(f"[ML] Trained model not found at {model_path}")
                print("[ML] Falling back to manual fraud model")
        except Exception as e:
            print(f"[ML] Error loading fraud model: {e}")
            print("[ML] Falling back to manual fraud model")

    def score(self, features: ClaimFeatures) -> dict:
        """Returns fraud score 0-1, decision, factor breakdown."""
        start_time = time.time()
        fallback_used = False

        if self.model is None:
            # Fallback to manual model
            result = self._manual_score(features)
            fallback_used = True
            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("fraud", latency_ms, fallback=fallback_used)
            return result

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

            # Get anomaly score from Isolation Forest
            # Isolation Forest returns negative scores (more negative = more anomalous)
            anomaly_score = -self.model.score_samples(X)[0]

            # Convert anomaly score to fraud probability (0-1 scale)
            # Based on observed training data range: [-0.69, -0.35] (negated: [0.35, 0.69])
            # Map this to [0, 1] where higher anomaly = higher fraud score
            MIN_ANOMALY = 0.35  # Most normal samples
            MAX_ANOMALY = 0.70  # Most anomalous samples
            fraud_score = (anomaly_score - MIN_ANOMALY) / (MAX_ANOMALY - MIN_ANOMALY)
            fraud_score = float(np.clip(fraud_score, 0, 1))
            fraud_score = round(fraud_score, 4)

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

            result = {
                "fraud_score": float(fraud_score),
                "decision": decision,
                "model_type": "isolation_forest",
                "anomaly_score": float(anomaly_score),
                "factors": {
                    "gps_in_zone": bool(features.gps_in_zone),
                    "run_count_during_event": int(features.run_count_during_event),
                    "zone_polygon_match": bool(features.zone_polygon_match),
                    "claims_last_30_days": int(features.claims_last_30_days),
                    "device_consistent": bool(features.device_consistent),
                    "traffic_disrupted": bool(features.traffic_disrupted),
                    "centroid_drift_km": float(features.centroid_drift_km)
                },
                "hard_reject_reasons": hard_reject_reasons
            }

            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("fraud", latency_ms, fallback=False)
            return result

        except Exception as e:
            print(f"[ML] Error scoring fraud: {e} — using manual fallback")
            result = self._manual_score(features)
            fallback_used = True
            latency_ms = (time.time() - start_time) * 1000
            ml_monitor.record_prediction("fraud", latency_ms, fallback=fallback_used)
            return result

    def _manual_score(self, features: ClaimFeatures) -> dict:
        """
        Fallback manual scoring.
        Imports directly from ml_service_manual to avoid circular imports
        and recursion through ml_service.py singletons.
        """
        from app.services.ml_service_manual import fraud_model as _manual
        return _manual.score(features)


# ------------------------------------------------------------------------------
# SINGLETONS - Use these in production
# ------------------------------------------------------------------------------

zone_risk_model = TrainedZoneRiskModel()
premium_model = TrainedPremiumModel()
fraud_model = TrainedFraudModel()
