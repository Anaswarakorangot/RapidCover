"""
ml_service.py
-----------------------------------------------------------------------------
RapidCover ML Service - Three models wrapped as ML-shaped interfaces.
Source: RapidCover Phase 2 Team Guide, Guidewire DEVTrails 2026.

Model 1 - Zone Risk Scorer
  Algorithm : XGBoost Classifier (manually calibrated weights)
  Interface : zone_risk_model.predict(zone_features) -> score 0-100

Model 2 - Dynamic Premium Engine
  Algorithm : Gradient Boosted Regression (manually calibrated)
  Interface : premium_model.predict(partner_features) -> weekly premium Rs.

Model 3 - Fraud Anomaly Detector
  Algorithm : Isolation Forest (manually calibrated 7-factor scorer)
  Interface : fraud_model.score(claim_features) -> fraud score 0-1

IMPORTANT: Weights are manually calibrated for hackathon demo.
In production, replace with trained scikit-learn/XGBoost models.
Interfaces are drop-in replaceable with real models.
-----------------------------------------------------------------------------
"""

from dataclasses import dataclass


# ------------------------------------------------------------------------------
# INPUT DATACLASSES
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
    """
    Features for Fraud Anomaly Detector (Isolation Forest).

    Exact 7 factors from Section 3.3 of team guide:
      w1=0.25 gps_coherence
      w2=0.25 run_count_check
      w3=0.15 zone_polygon_match
      w4=0.15 claim_frequency_score
      w5=0.10 device_fingerprint_match
      w6=0.05 traffic_cross_check
      w7=0.05 centroid_drift_score
    """
    partner_id:               int
    zone_id:                  int
    gps_in_zone:              bool    # w1: within 500m of dark store
    run_count_during_event:   int     # w2: any run = hard reject
    zone_polygon_match:       bool    # w3: zone confirmed in event polygon
    claims_last_30_days:      int     # w4: frequency check
    device_consistent:        bool    # w5: fingerprint match
    traffic_disrupted:        bool    # w6: at least 1 road blocked
    centroid_drift_km:        float   # w7: 30-day centroid vs dark store
    max_gps_velocity_kmh:     float   # hard check: >60 = spoof
    zone_suspended:           bool    # hard gate: must be confirmed


# ------------------------------------------------------------------------------
# MODEL 1 - ZONE RISK SCORER (XGBoost Classifier)
# ------------------------------------------------------------------------------

class ZoneRiskModel:
    """
    XGBoost Classifier - manually calibrated weights.
    Output: risk score 0-100 per dark store zone.

    Feature weights (manually calibrated, NOT trained on real data):
      W_RAINFALL   = 0.30
      W_AQI        = 0.20
      W_SUSPENSION = 0.15
      W_HEAT       = 0.12
      W_BANDH      = 0.10
      W_ROAD_FLOOD = 0.08
      W_SEASONAL   = 0.05
    """

    W_RAINFALL   = 0.30
    W_AQI        = 0.20
    W_SUSPENSION = 0.15
    W_HEAT       = 0.12
    W_BANDH      = 0.10
    W_ROAD_FLOOD = 0.08
    W_SEASONAL   = 0.05

    CAP_RAINFALL   = 80.0
    CAP_AQI_DAYS   = 60
    CAP_HEAT_DAYS  = 30
    CAP_BANDH      = 10
    CAP_SUSPENSION = 8

    # High-risk months per city - from Section 2C
    HIGH_RISK_MONTHS: dict = {
        "bangalore": {6, 7, 8, 9},
        "mumbai":    {7, 8, 9},
        "delhi":     {10, 11, 12, 1},
        "chennai":   {10, 11, 12},
        "hyderabad": {7, 8, 9},
        "kolkata":   {6, 7, 8, 9},
    }

    def predict(self, features: ZoneFeatures) -> float:
        """Returns risk score 0-100. Mimics XGBoost.predict_proba() x 100."""
        city = features.city.lower()

        f_rainfall   = min(features.avg_rainfall_mm_per_hr       / self.CAP_RAINFALL, 1.0)
        f_aqi        = min(features.aqi_severe_days_2yr          / self.CAP_AQI_DAYS, 1.0)
        f_heat       = min(features.heat_advisory_days_2yr       / self.CAP_HEAT_DAYS, 1.0)
        f_bandh      = min(features.bandh_events_2yr             / self.CAP_BANDH, 1.0)
        f_suspension = min(features.dark_store_suspensions_2yr   / self.CAP_SUSPENSION, 1.0)
        f_road       = 1.0 if features.road_flood_prone else 0.0
        f_seasonal   = 1.0 if features.month in self.HIGH_RISK_MONTHS.get(city, set()) else 0.0

        score = (
            self.W_RAINFALL   * f_rainfall   +
            self.W_AQI        * f_aqi        +
            self.W_HEAT       * f_heat       +
            self.W_BANDH      * f_bandh      +
            self.W_SUSPENSION * f_suspension +
            self.W_ROAD_FLOOD * f_road       +
            self.W_SEASONAL   * f_seasonal
        ) * 100

        return round(min(max(score, 0.0), 100.0), 2)


# ------------------------------------------------------------------------------
# MODEL 2 - DYNAMIC PREMIUM ENGINE (Gradient Boosted Regression)
# ------------------------------------------------------------------------------

class PremiumModel:
    """
    Gradient Boosted Regression - manually calibrated multiplicative formula.

    Full formula from Section 3.1 of team guide:
      Weekly Premium =
        Base (trigger_probability x avg_income_lost_per_day x days_exposed)
        x city_peril_multiplier
        x zone_risk_score_multiplier (0.8-1.4)
        x seasonal_index (city-specific monthly - NOT flat national index)
        x activity_tier_factor (Flex=0.8, Standard=1.0, Pro=1.35)
        x RIQI_adjustment (urban_core=1.0, urban_fringe=1.15, peri_urban=1.3)
        x loyalty_discount (1.0 -> 0.94 after 4 weeks -> 0.90 after 12)
      Capped at 3x base tier (IRDAI microinsurance cap)
    """

    # Fixed base prices per final specification table:
    # Flex:     Rs.22 (Max Weekly Rs.500, Ratio ~1:23)
    # Standard: Rs.33 (Max Weekly Rs.1200, Ratio ~1:36)
    # Pro:      Rs.45 (Max Weekly Rs.2000, Ratio ~1:44)
    BASE_PRICES    = {"flex": 22, "standard": 33, "pro": 45}
    CAP_MULTIPLIER = 3.0  # IRDAI microinsurance cap

    # Activity tier factor - exact values from Section 3.1
    ACTIVITY_TIER_FACTOR = {"flex": 0.80, "standard": 1.00, "pro": 1.35}

    # City peril multipliers (actuarially calibrated)
    CITY_PERIL: dict = {
        "mumbai":    1.30,
        "kolkata":   1.25,
        "chennai":   1.22,
        "bangalore": 1.18,
        "hyderabad": 1.15,
        "delhi":     1.10,
    }

    # City-specific seasonal multipliers - per Section 2C, NOT flat national index
    SEASONAL_INDEX: dict = {
        "bangalore": {6: 1.20, 7: 1.20, 8: 1.20, 9: 1.20},    # +20% Jun-Sep
        "mumbai":    {7: 1.25, 8: 1.25, 9: 1.25},              # +25% Jul-Sep
        "delhi":     {10: 1.18, 11: 1.18, 12: 1.18, 1: 1.18},  # +18% Oct-Jan
        "chennai":   {10: 1.22, 11: 1.22, 12: 1.22},           # +22% Oct-Dec
        "hyderabad": {7: 1.15, 8: 1.15, 9: 1.15},              # +15% Jul-Sep
        "kolkata":   {6: 1.20, 7: 1.20, 8: 1.20, 9: 1.20},    # +20% Jun-Sep
    }

    # RIQI adjustment - exact values from Section 3.1
    RIQI_ADJUSTMENT: dict = {
        "urban_core":   1.00,   # RIQI > 70
        "urban_fringe": 1.15,   # RIQI 40-70
        "peri_urban":   1.30,   # RIQI < 40
    }

    def _riqi_band(self, riqi_score: float) -> str:
        if riqi_score > 70:
            return "urban_core"
        elif riqi_score >= 40:
            return "urban_fringe"
        return "peri_urban"

    def _seasonal(self, city: str, month: int) -> float:
        return self.SEASONAL_INDEX.get(city.lower(), {}).get(month, 1.0)

    def _loyalty(self, loyalty_weeks: int) -> float:
        """Returns loyalty multiplier. Exact values from Section 3.1."""
        if loyalty_weeks >= 12:
            return 0.90
        elif loyalty_weeks >= 4:
            return 0.94
        return 1.0

    def predict(self, features: PartnerFeatures) -> dict:
        """
        Returns weekly_premium (Rs.) + full itemised breakdown.
        Mimics GradientBoostingRegressor.predict().
        """
        tier = features.tier.lower()
        base = self.BASE_PRICES.get(tier, self.BASE_PRICES["standard"])
        city = features.city.lower()

        # Base component: trigger_probability x avg_income_lost x days_exposed
        trigger_probability     = 0.09    # ~1 claim per 11 weeks baseline
        avg_income_lost_per_day = 500.0   # Rs.500 midpoint (range Rs.420-Rs.720 from doc)
        days_exposed            = min(features.active_days_last_30 / 26.0, 1.0)

        # Multipliers (exact per Section 3.1)
        city_peril            = self.CITY_PERIL.get(city, 1.0)
        zone_risk_multiplier  = 0.8 + (features.zone_risk_score / 100.0) * 0.6  # 0.8-1.4
        seasonal_index        = self._seasonal(city, features.month)
        activity_tier_factor  = self.ACTIVITY_TIER_FACTOR[tier]
        riqi_band             = self._riqi_band(features.riqi_score)
        riqi_adjustment       = self.RIQI_ADJUSTMENT[riqi_band]
        loyalty_discount      = self._loyalty(features.loyalty_weeks)

        # Apply full formula
        base_component = trigger_probability * avg_income_lost_per_day * days_exposed
        adjusted = (
            base_component       *
            city_peril           *
            zone_risk_multiplier *
            seasonal_index       *
            activity_tier_factor *
            riqi_adjustment      *
            loyalty_discount
        )

        # Scale to Rs. (keep in meaningful range above base price)
        raw_premium    = base + (adjusted * 0.08)
        cap            = base * self.CAP_MULTIPLIER
        weekly_premium = round(min(max(raw_premium, base), cap))

        return {
            "weekly_premium":  int(weekly_premium),
            "base_price":      base,
            "tier":            tier,
            "cap_value":       int(cap),
            "cap_applied":     weekly_premium >= cap,
            "breakdown": {
                "trigger_probability":      trigger_probability,
                "avg_income_lost_per_day":  avg_income_lost_per_day,
                "days_exposed_factor":      round(days_exposed, 3),
                "city_peril_multiplier":    city_peril,
                "zone_risk_multiplier":     round(zone_risk_multiplier, 3),
                "seasonal_index":           seasonal_index,
                "activity_tier_factor":     activity_tier_factor,
                "riqi_adjustment":          riqi_adjustment,
                "riqi_band":                riqi_band,
                "loyalty_discount":         loyalty_discount,
            },
        }


# ------------------------------------------------------------------------------
# MODEL 3 - FRAUD ANOMALY DETECTOR (Isolation Forest)
# ------------------------------------------------------------------------------

class FraudModel:
    '''
    Isolation Forest - manually calibrated 7-factor anomaly scorer.
    
    EXACT weights from Section 3.3 of team guide:
      w1 = 0.25 gps_coherence
      w2 = 0.25 run_count_check
      w3 = 0.15 zone_polygon_match
      w4 = 0.15 claim_frequency_score
      w5 = 0.10 device_fingerprint_match
      w6 = 0.05 traffic_cross_check
      w7 = 0.05 centroid_drift_score - Section 2 F addition

    Score thresholds (Section 3.3):
      < 0.50      -> auto_approve
      0.50 - 0.75 -> enhanced_validation
      0.75 - 0.90 -> manual_review
      > 0.90      -> auto_reject

    Hard rejects (override score regardless):
      - GPS velocity > 60 km/h (Section 2 F velocity physics check)
      - Zone not suspended     (Section 4.2 step 4)
      - Run count > 0          (Activity Paradox, Section 4.2 step 7)

    NOTE: Weights manually calibrated - not trained on real data.
    Centroid drift > 15km -> manual review flag (Section 2 F).
    '''
    
    # Exact weights from Section 3.3
    W1_GPS_COHERENCE       = 0.25
    W2_RUN_COUNT           = 0.25
    W3_ZONE_POLYGON        = 0.15
    W4_CLAIM_FREQUENCY     = 0.15
    W5_DEVICE_FINGERPRINT  = 0.10
    W6_TRAFFIC_CROSS_CHECK = 0.05
    W7_CENTROID_DRIFT      = 0.05   # w7 = 0.05 per spec

    VELOCITY_SPOOF_KMH   = 60.0    # Section 2F: >60km/h = spoof
    CENTROID_FLAG_KM     = 15.0    # Section 2F: >15km = manual review
    MAX_CLEAN_CLAIMS_30D = 3

    def score(self, features: ClaimFeatures) -> dict:
        """
        Returns fraud score 0-1, decision, factor breakdown.
        Mimics IsolationForest.decision_function() normalised 0-1.
        """
        hard_reject_reasons = []

        # -- Hard pre-checks -----------------------------------------------
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

        # -- w1: GPS coherence ---------------------------------------------
        f1 = 0.0 if features.gps_in_zone else 1.0

        # -- w2: Run count check -------------------------------------------
        f2 = 1.0 if features.run_count_during_event > 0 else 0.0

        # -- w3: Zone polygon match ----------------------------------------
        f3 = 0.0 if features.zone_polygon_match else 1.0

        # -- w4: Claim frequency -------------------------------------------
        f4 = min(features.claims_last_30_days / self.MAX_CLEAN_CLAIMS_30D, 1.0)

        # -- w5: Device fingerprint ----------------------------------------
        f5 = 0.0 if features.device_consistent else 1.0

        # -- w6: Traffic cross-check ---------------------------------------
        f6 = 0.0 if features.traffic_disrupted else 1.0

        # -- w7: Centroid drift (w7=0.05) ----------------------------------
        if features.centroid_drift_km > self.CENTROID_FLAG_KM:
            f7 = 1.0
            if features.centroid_drift_km not in [r for r in hard_reject_reasons]:
                hard_reject_reasons.append(
                    f"Centroid drift {features.centroid_drift_km:.1f} km "
                    f"exceeds {self.CENTROID_FLAG_KM} km - manual review"
                )
        else:
            f7 = features.centroid_drift_km / self.CENTROID_FLAG_KM

        # -- Weighted score ------------------------------------------------
        fraud_score = (
            self.W1_GPS_COHERENCE       * f1 +
            self.W2_RUN_COUNT           * f2 +
            self.W3_ZONE_POLYGON        * f3 +
            self.W4_CLAIM_FREQUENCY     * f4 +
            self.W5_DEVICE_FINGERPRINT  * f5 +
            self.W6_TRAFFIC_CROSS_CHECK * f6 +
            self.W7_CENTROID_DRIFT      * f7
        )
        fraud_score = round(min(max(fraud_score, 0.0), 1.0), 4)

        # -- Decision ------------------------------------------------------
        if hard_reject_reasons:
            decision    = "auto_reject"
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
            "decision":    decision,
            "factors": {
                "w1_gps_coherence":      round(1 - f1, 2),
                "w2_run_count_clean":    round(1 - f2, 2),
                "w3_zone_polygon_match": round(1 - f3, 2),
                "w4_claim_frequency":    round(f4, 2),
                "w5_device_consistent":  round(1 - f5, 2),
                "w6_traffic_disrupted":  round(1 - f6, 2),
                "w7_centroid_drift_km":  features.centroid_drift_km,
            },
            "weights": {
                "w1": self.W1_GPS_COHERENCE,
                "w2": self.W2_RUN_COUNT,
                "w3": self.W3_ZONE_POLYGON,
                "w4": self.W4_CLAIM_FREQUENCY,
                "w5": self.W5_DEVICE_FINGERPRINT,
                "w6": self.W6_TRAFFIC_CROSS_CHECK,
                "w7": self.W7_CENTROID_DRIFT,
            },
            "hard_reject_reasons": hard_reject_reasons,
        }


# ------------------------------------------------------------------------------
# SINGLETONS - import these everywhere
# ------------------------------------------------------------------------------


# --------------------------------------------------------------------------
# SINGLETONS - import these everywhere
# -----------------------------------------------------------------------------
# Loading strategy:
#   1. Check for model_metadata.json in ml_models/
#   2. If found, load trained XGBoost/sklearn models (pricing_mode = "trained_ml")
#   3. If missing or import fails, use manually calibrated models (pricing_mode = "fallback_rule_based")
#
# IMPORTANT: ml_service_trained._manual_predict() imports from ml_service_manual
# directly — never back through this module — to prevent circular import recursion.
# --------------------------------------------------------------------------

try:
    from pathlib import Path as _Path
    import importlib as _importlib

    _ML_MODELS_DIR = _Path(__file__).parent.parent.parent / "ml_models"
    _metadata_path = _ML_MODELS_DIR / "model_metadata.json"

    if _metadata_path.exists():
        print("[ML] ─────────────────────────────────────────────────────────")
        print(f"[ML] model_metadata.json found at: {_metadata_path}")
        print("[ML] Loading TRAINED XGBoost/sklearn models (pricing_mode=trained_ml)")
        from app.services.ml_service_trained import (
            zone_risk_model,
            premium_model,
            fraud_model,
        )
        print("[ML] ✓ zone_risk_model  → TrainedZoneRiskModel")
        print("[ML] ✓ premium_model    → TrainedPremiumModel")
        print("[ML] ✓ fraud_model      → TrainedFraudModel")
        print("[ML] ─────────────────────────────────────────────────────────")
    else:
        print("[ML] ─────────────────────────────────────────────────────────")
        print(f"[ML] No model_metadata.json at {_metadata_path}")
        print("[ML] Loading MANUAL calibrated models (pricing_mode=fallback_rule_based)")
        zone_risk_model = ZoneRiskModel()
        premium_model   = PremiumModel()
        fraud_model     = FraudModel()
        print("[ML] ✓ zone_risk_model  → ZoneRiskModel (manual weights)")
        print("[ML] ✓ premium_model    → PremiumModel (manual formula)")
        print("[ML] ✓ fraud_model      → FraudModel (7-factor manual)")
        print("[ML] ─────────────────────────────────────────────────────────")

except ImportError as _e:
    print("[ML] ─────────────────────────────────────────────────────────")
    print(f"[ML] ImportError while loading trained models: {_e}")
    print("[ML] Falling back to MANUAL calibrated models")
    zone_risk_model = ZoneRiskModel()
    premium_model   = PremiumModel()
    fraud_model     = FraudModel()
    print("[ML] ✓ zone_risk_model  → ZoneRiskModel (manual weights)")
    print("[ML] ✓ premium_model    → PremiumModel (manual formula)")
    print("[ML] ✓ fraud_model      → FraudModel (7-factor manual)")
    print("[ML] ─────────────────────────────────────────────────────────")