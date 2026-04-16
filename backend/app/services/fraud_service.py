"""
fraud_service.py
-----------------------------------------------------------------------------
RapidCover Fraud Detection Service - 7-factor anomaly scorer.
Source: RapidCover Phase 2 Team Guide, Section 3.3 + Section 2F.

Algorithm: Isolation Forest (manually calibrated weights).

7 Factors (exact from Section 3.3):
  w1 = 0.25  gps_coherence          - within 500m of dark store
  w2 = 0.25  run_count_check        - Activity Paradox hard rule
  w3 = 0.15  zone_polygon_match     - event polygon confirmed
  w4 = 0.15  claim_frequency_score  - last 30 days
  w5 = 0.10  device_fingerprint     - consistency check
  w6 = 0.05  traffic_cross_check    - road disruption confirmed
  w7 = 0.05  centroid_drift_score   - 30-day GPS centroid (Section 2F)

Hard rejects (pre-filter, override score):
  - GPS velocity > 60 km/h between pings = spoof (Section 2F)
  - Zone not suspended by platform
  - Any run completed during suspended window (Activity Paradox)
  - Centroid drift > 15km from declared dark store (Section 2F)

Thresholds:
  < 0.50       → auto_approve
  0.50 – 0.75  → enhanced_validation
  0.75 – 0.90  → manual_review
  > 0.90       → auto_reject
-----------------------------------------------------------------------------
"""

import math
from app.services.ml_service import fraud_model, ClaimFeatures


# ------------------------------------------------------------------------------
# MAIN SCORING ENTRY POINT
# ------------------------------------------------------------------------------

def score_claim(features: ClaimFeatures) -> dict:
    """
    Score a claim for fraud. Delegates to fraud_model.score().
    Returns full result with score, decision, factors, hard_reject_reasons.
    """
    return fraud_model.score(features)


def score_claim_simple(
    partner_id:              int,
    zone_id:                 int,
    gps_in_zone:             bool,
    run_count_during_event:  int,
    zone_polygon_match:      bool,
    claims_last_30_days:     int,
    device_consistent:       bool,
    traffic_disrupted:       bool,
    centroid_drift_km:       float,
    max_gps_velocity_kmh:    float,
    zone_suspended:          bool,
) -> dict:
    """
    Simplified scoring for admin simulation / testing without raw GPS pings.
    Builds ClaimFeatures and delegates to fraud_model.score().
    """
    features = ClaimFeatures(
        partner_id             = partner_id,
        zone_id                = zone_id,
        gps_in_zone            = gps_in_zone,
        run_count_during_event = run_count_during_event,
        zone_polygon_match     = zone_polygon_match,
        claims_last_30_days    = claims_last_30_days,
        device_consistent      = device_consistent,
        traffic_disrupted      = traffic_disrupted,
        centroid_drift_km      = centroid_drift_km,
        max_gps_velocity_kmh   = max_gps_velocity_kmh,
        zone_suspended         = zone_suspended,
    )
    return fraud_model.score(features)


# ------------------------------------------------------------------------------
# GPS HELPER FUNCTIONS
# ------------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns distance in km between two GPS coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_max_velocity_kmh(pings: list) -> float:
    """
    Velocity physics check - Section 2F of team guide.
    Computes max speed (km/h) between consecutive GPS pings.
    > 60 km/h on a delivery bike = physically impossible = GPS spoof.

    Each ping: {"lat": float, "lng": float, "ts": int (epoch seconds)}
    """
    if len(pings) < 2:
        return 0.0

    max_kmh = 0.0
    for i in range(len(pings) - 1):
        p1, p2  = pings[i], pings[i + 1]
        dist_km = haversine_km(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
        dt_hrs  = (p2["ts"] - p1["ts"]) / 3600.0
        if dt_hrs <= 0:
            continue
        max_kmh = max(max_kmh, dist_km / dt_hrs)

    return round(max_kmh, 2)


def compute_centroid(pings: list) -> dict:
    """
    Compute 30-day GPS centroid - Section 2F of team guide.
    centroid = average of all GPS pings over last 30 days.

    Each ping: {"lat": float, "lng": float}
    Returns {"lat": float, "lng": float}
    """
    if not pings:
        return {"lat": 0.0, "lng": 0.0}

    avg_lat = sum(p["lat"] for p in pings) / len(pings)
    avg_lng = sum(p["lng"] for p in pings) / len(pings)
    return {"lat": round(avg_lat, 6), "lng": round(avg_lng, 6)}


# ------------------------------------------------------------------------------
# WEATHER CONSISTENCY CHECKING (Phase 2 - Historical Data)
# ------------------------------------------------------------------------------

def check_weather_consistency(
    db,
    zone_id: int,
    trigger_time: "datetime",
    claimed_temp: float = None,
    claimed_rainfall: float = None,
    claimed_aqi: int = None,
    tolerance_hours: float = 1.0
) -> dict:
    """
    Check if claimed weather matches stored observations within ±tolerance_hours.

    Args:
        db: Database session
        zone_id: Zone ID
        trigger_time: When the trigger event occurred
        claimed_temp: Temperature claimed by trigger (°C)
        claimed_rainfall: Rainfall claimed by trigger (mm/hr)
        claimed_aqi: AQI claimed by trigger
        tolerance_hours: Time window for matching observations (default ±1 hour)

    Returns:
        {
            "consistent": bool,
            "confidence": float (0.0-1.0),
            "reason": str,
            "observations_found": int,
            "discrepancy": str or None
        }
    """
    from datetime import timedelta
    from app.models.weather_observation import WeatherObservation
    from app.utils.time_utils import utcnow

    # Query observations within tolerance window
    start_time = trigger_time - timedelta(hours=tolerance_hours)
    end_time = trigger_time + timedelta(hours=tolerance_hours)

    observations = (
        db.query(WeatherObservation)
        .filter(
            WeatherObservation.zone_id == zone_id,
            WeatherObservation.observed_at >= start_time,
            WeatherObservation.observed_at <= end_time
        )
        .order_by(WeatherObservation.observed_at.desc())
        .all()
    )

    if not observations:
        return {
            "consistent": True,  # Can't disprove without data
            "confidence": 0.5,   # Low confidence due to no data
            "reason": "No historical observations found for comparison",
            "observations_found": 0,
            "discrepancy": None
        }

    # Check temperature consistency
    if claimed_temp is not None:
        obs_temps = [o.temp_celsius for o in observations if o.temp_celsius is not None]
        if obs_temps:
            avg_temp = sum(obs_temps) / len(obs_temps)
            temp_diff = abs(claimed_temp - avg_temp)

            # Flag if difference > 5°C (unrealistic variation in 1 hour)
            if temp_diff > 5.0:
                return {
                    "consistent": False,
                    "confidence": 0.9,
                    "reason": f"Temperature mismatch: claimed {claimed_temp}°C vs observed avg {avg_temp:.1f}°C",
                    "observations_found": len(observations),
                    "discrepancy": f"temp_diff_{temp_diff:.1f}C"
                }

    # Check rainfall consistency
    if claimed_rainfall is not None:
        obs_rain = [o.rainfall_mm_hr for o in observations if o.rainfall_mm_hr is not None]
        if obs_rain:
            avg_rain = sum(obs_rain) / len(obs_rain)
            rain_diff = abs(claimed_rainfall - avg_rain)

            # Flag if difference > 20mm/hr (significant discrepancy)
            if rain_diff > 20.0:
                return {
                    "consistent": False,
                    "confidence": 0.85,
                    "reason": f"Rainfall mismatch: claimed {claimed_rainfall}mm/hr vs observed avg {avg_rain:.1f}mm/hr",
                    "observations_found": len(observations),
                    "discrepancy": f"rain_diff_{rain_diff:.1f}mm"
                }

    # Check AQI consistency
    if claimed_aqi is not None:
        obs_aqi = [o.aqi for o in observations if o.aqi is not None]
        if obs_aqi:
            avg_aqi = sum(obs_aqi) / len(obs_aqi)
            aqi_diff = abs(claimed_aqi - avg_aqi)

            # Flag if difference > 100 (different AQI category)
            if aqi_diff > 100:
                return {
                    "consistent": False,
                    "confidence": 0.8,
                    "reason": f"AQI mismatch: claimed {claimed_aqi} vs observed avg {avg_aqi:.0f}",
                    "observations_found": len(observations),
                    "discrepancy": f"aqi_diff_{aqi_diff:.0f}"
                }

    # All checks passed
    confidence = 0.9 if len(observations) >= 3 else 0.7
    return {
        "consistent": True,
        "confidence": confidence,
        "reason": "Weather data consistent with historical observations",
        "observations_found": len(observations),
        "discrepancy": None
    }


def check_device_fingerprint_enhanced(db, partner_id: int, lookback_days: int = 30) -> dict:
    """
    Enhanced device fingerprint analysis using PartnerDevice table.

    Flags suspicious patterns:
    - Too many different devices (>3 in 30 days = suspicious)
    - Rapid device switching (>2 devices in 24 hours)
    - New device with no history

    Args:
        db: Database session
        partner_id: Partner ID
        lookback_days: Days to look back for device history

    Returns:
        {
            "consistent": bool,
            "reason": str,
            "device_count": int,
            "rapid_switching": bool
        }
    """
    from datetime import timedelta
    from app.models.fraud import PartnerDevice
    from app.utils.time_utils import utcnow

    cutoff = utcnow() - timedelta(days=lookback_days)

    devices = (
        db.query(PartnerDevice)
        .filter(
            PartnerDevice.partner_id == partner_id,
            PartnerDevice.last_seen_at >= cutoff
        )
        .order_by(PartnerDevice.last_seen_at.desc())
        .all()
    )

    device_count = len(devices)

    # Flag if too many devices
    if device_count > 3:
        return {
            "consistent": False,
            "reason": f"Too many devices ({device_count}) used in {lookback_days} days",
            "device_count": device_count,
            "rapid_switching": False
        }

    # Check for rapid switching (>2 devices in 24 hours)
    if device_count >= 2:
        recent_24h = utcnow() - timedelta(hours=24)
        recent_devices = [d for d in devices if d.last_seen_at >= recent_24h]

        if len(recent_devices) > 2:
            return {
                "consistent": False,
                "reason": f"Rapid device switching: {len(recent_devices)} devices in 24 hours",
                "device_count": device_count,
                "rapid_switching": True
            }

    return {
        "consistent": True,
        "reason": "Device usage pattern normal",
        "device_count": device_count,
        "rapid_switching": False
    }


def build_claim_features(
    partner_id:               int,
    zone_id:                  int,
    claim_gps_lat:            float,
    claim_gps_lng:            float,
    dark_store_lat:           float,
    dark_store_lng:           float,
    zone_radius_km:           float,
    run_count_during_event:   int,
    claims_last_30_days:      int,
    device_id:                str,
    last_known_device_id:     str,
    zone_suspended:           bool,
    zone_polygon_match:       bool,
    traffic_disrupted:        bool,
    gps_pings_30d:            list,     # {"lat", "lng", "ts"}
    centroid_30d_lat:         float,
    centroid_30d_lng:         float,
) -> ClaimFeatures:
    """
    Build ClaimFeatures from raw claim data.
    Called by claims processor before fraud scoring.
    """
    gps_in_zone = (
        haversine_km(claim_gps_lat, claim_gps_lng, dark_store_lat, dark_store_lng)
        <= zone_radius_km
    )
    device_consistent  = (device_id == last_known_device_id)
    max_velocity       = compute_max_velocity_kmh(gps_pings_30d)
    centroid_drift_km  = haversine_km(
        centroid_30d_lat, centroid_30d_lng,
        dark_store_lat,   dark_store_lng,
    )

    return ClaimFeatures(
        partner_id             = partner_id,
        zone_id                = zone_id,
        gps_in_zone            = gps_in_zone,
        run_count_during_event = run_count_during_event,
        zone_polygon_match     = zone_polygon_match,
        claims_last_30_days    = claims_last_30_days,
        device_consistent      = device_consistent,
        traffic_disrupted      = traffic_disrupted,
        centroid_drift_km      = centroid_drift_km,
        max_gps_velocity_kmh   = max_velocity,
        zone_suspended         = zone_suspended,
    )


# ------------------------------------------------------------------------------
# DECISION LABELS (for API responses + admin dashboard)
# ------------------------------------------------------------------------------

DECISION_LABELS: dict = {
    "auto_approve":        {"label": "✅ Auto-approved",       "color": "green"},
    "enhanced_validation": {"label": "🔍 Enhanced validation", "color": "amber"},
    "manual_review":       {"label": "👁 Manual review",       "color": "orange"},
    "auto_reject":         {"label": "❌ Auto-rejected",        "color": "red"},
}


def get_decision_label(decision: str) -> dict:
    return DECISION_LABELS.get(decision, {"label": decision, "color": "gray"})


# ------------------------------------------------------------------------------
# COMPATIBILITY WRAPPER - matches old fraud_detector.calculate_fraud_score()
# ------------------------------------------------------------------------------

# Thresholds matching the old fraud_detector.py interface
FRAUD_THRESHOLDS = {
    "auto_approve": 0.50,      # Below this = auto approve (was 0.3 in old, 0.5 in new 7-factor)
    "review_required": 0.75,   # Between 0.50-0.75 = enhanced validation
    "manual_review": 0.90,     # Between 0.75-0.90 = manual review
    "auto_reject": 0.90,       # Above this = auto reject
}


def calculate_fraud_score(
    partner,
    trigger_event,
    db,
    partner_lat: float = None,
    partner_lng: float = None,
    had_deliveries_during: bool = False,
) -> dict:
    """
    Compatibility wrapper for the 7-factor fraud model.

    Matches the old fraud_detector.calculate_fraud_score() signature so that
    claims_processor.py can switch to the new model without code changes.

    New factors added (Section 2F + Section 3.3):
      - w7: centroid_drift_score (0.05)
      - Velocity physics check (>60km/h = spoof)
    """
    from sqlalchemy.orm import Session
    from sqlalchemy import func
    from datetime import datetime, timedelta
    from app.models.policy import Policy
    from app.models.claim import Claim
    from app.models.zone import Zone

    from app.models.fraud import PartnerGPSPing, PartnerDevice
    from app.utils.time_utils import utcnow

    zone = trigger_event.zone if trigger_event else None
    if not zone and trigger_event:
        zone = db.query(Zone).filter(Zone.id == trigger_event.zone_id).first()

    # Get dark store coordinates
    dark_store_lat = zone.dark_store_lat if zone else 0.0
    dark_store_lng = zone.dark_store_lng if zone else 0.0

    # Default claim GPS to partner's zone dark store if not provided
    claim_lat = partner_lat if partner_lat is not None else dark_store_lat
    claim_lng = partner_lng if partner_lng is not None else dark_store_lng

    # Check GPS coherence (within 500m = 0.5km of dark store)
    gps_distance = haversine_km(claim_lat, claim_lng, dark_store_lat, dark_store_lng)
    gps_in_zone = gps_distance <= 0.5  # 500m threshold

    # Run count during event (Activity Paradox)
    run_count = 1 if had_deliveries_during else 0

    # Zone polygon match - assume true if GPS is within reasonable distance
    zone_polygon_match = gps_distance <= 5.0  # 5km for polygon match

    # Claim frequency - count claims in last 30 days
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]
    claims_last_30 = 0
    if policy_ids:
        cutoff = utcnow() - timedelta(days=30)
        claims_last_30 = (
            db.query(func.count(Claim.id))
            .filter(Claim.policy_id.in_(policy_ids), Claim.created_at >= cutoff)
            .scalar()
        ) or 0

    # 1. Device fingerprint consistency (enhanced with historical analysis)
    device_check = check_device_fingerprint_enhanced(db, partner.id, lookback_days=30)
    device_consistent = device_check["consistent"]

    # 2. Weather consistency check (Phase 2 - Historical data)
    weather_check = {"consistent": True, "confidence": 0.5, "reason": "No weather data to check"}
    if trigger_event and hasattr(trigger_event, 'started_at') and trigger_event.started_at:
        # Extract weather values from trigger event metadata if available
        trigger_temp = getattr(trigger_event, 'temp_celsius', None)
        trigger_rainfall = getattr(trigger_event, 'rainfall_mm_hr', None)
        trigger_aqi = getattr(trigger_event, 'aqi', None)

        weather_check = check_weather_consistency(
            db=db,
            zone_id=zone.id if zone else 0,
            trigger_time=trigger_event.started_at,
            claimed_temp=trigger_temp,
            claimed_rainfall=trigger_rainfall,
            claimed_aqi=trigger_aqi,
            tolerance_hours=1.0
        )

    # 3. Max GPS velocity (spoof detection)
    # Fetch recent pings for this partner
    recent_pings = (
        db.query(PartnerGPSPing)
        .filter(PartnerGPSPing.partner_id == partner.id)
        .order_by(PartnerGPSPing.created_at.desc())
        .limit(10)
        .all()
    )
    
    ping_data = []
    for p in reversed(recent_pings):
        ping_data.append({
            "lat": p.lat,
            "lng": p.lng,
            "ts": p.created_at.timestamp()
        })
    
    max_velocity_kmh = compute_max_velocity_kmh(ping_data)

    # 3. Centroid drift (location anchoring)
    # Fetch 30-day history
    cutoff_30d = utcnow() - timedelta(days=30)
    history_pings = (
        db.query(PartnerGPSPing)
        .filter(PartnerGPSPing.partner_id == partner.id, PartnerGPSPing.created_at >= cutoff_30d)
        .all()
    )
    
    centroid_drift_km = 0.0
    if history_pings:
        hist_data = [{"lat": p.lat, "lng": p.lng} for p in history_pings]
        centroid = compute_centroid(hist_data)
        centroid_drift_km = haversine_km(
            centroid["lat"], centroid["lng"],
            dark_store_lat, dark_store_lng
        )
    else:
        # If no history, we fall back to the current distance
        centroid_drift_km = gps_distance

    # Zone suspended - true if trigger event exists and is active
    zone_suspended = trigger_event is not None and trigger_event.ended_at is None
    traffic_disrupted = zone_suspended

    # Build features and score
    features = ClaimFeatures(
        partner_id=partner.id,
        zone_id=zone.id if zone else 0,
        gps_in_zone=gps_in_zone,
        run_count_during_event=run_count,
        zone_polygon_match=zone_polygon_match,
        claims_last_30_days=claims_last_30,
        device_consistent=device_consistent,
        traffic_disrupted=traffic_disrupted,
        centroid_drift_km=centroid_drift_km,
        max_gps_velocity_kmh=max_velocity_kmh,
        zone_suspended=zone_suspended,
    )

    result = fraud_model.score(features)

    # Map decision to recommendation (old format compatibility)
    decision_to_recommendation = {
        "auto_approve": "approve",
        "enhanced_validation": "review",
        "manual_review": "review",
        "auto_reject": "reject",
    }
    recommendation = decision_to_recommendation.get(result["decision"], "review")

    # Build reason string
    if result["hard_reject_reasons"]:
        reason = "; ".join(result["hard_reject_reasons"])
    elif recommendation == "approve":
        reason = "Low risk - auto approved (7-factor model)"
    elif recommendation == "reject":
        reason = "Very high risk - auto rejected (7-factor model)"
    else:
        reason = f"Moderate risk ({result['decision']}) - review required"

    # Add weather inconsistency to hard reject reasons if flagged
    if not weather_check["consistent"] and weather_check["confidence"] > 0.7:
        result["hard_reject_reasons"].append(
            f"Weather data inconsistency: {weather_check['reason']}"
        )
        # Escalate recommendation if weather is highly inconsistent
        if recommendation == "approve":
            recommendation = "review"
            reason = f"Weather inconsistency detected: {weather_check['reason']}"

    # Add device fingerprint issues to hard reject reasons if flagged
    if not device_check["consistent"]:
        result["hard_reject_reasons"].append(
            f"Device fingerprint issue: {device_check['reason']}"
        )
        # Escalate recommendation if device switching is suspicious
        if recommendation == "approve":
            recommendation = "review"
            reason = f"Device fingerprint issue: {device_check['reason']}"

    # Return in old format for compatibility
    factor_scores = result.get("factors", {})
    return {
        "score": result["fraud_score"],
        "factors": {
            "gps_coherence": 1 - factor_scores.get("w1_gps_coherence", 0.0),
            "activity_paradox": 1 - factor_scores.get("w2_run_count_clean", 0.0),
            "claim_frequency": factor_scores.get("w4_claim_frequency", 0.0),
            "duplicate_claim": 0.0,  # Handled separately in claims_processor
            "account_age": 0.0,  # Not in 7-factor model
            "zone_boundary": 1 - factor_scores.get("w3_zone_polygon_match", 0.0),
            # New factors from 7-factor model
            "centroid_drift_km": factor_scores.get("w7_centroid_drift_km", 0.0),
            "device_consistent": factor_scores.get("w5_device_consistent", 0.0),
            "traffic_disrupted": factor_scores.get("w6_traffic_disrupted", 0.0),
            # Phase 2 enhancements - historical data checks
            "weather_consistent": weather_check["consistent"],
            "weather_confidence": weather_check["confidence"],
            "device_count": device_check["device_count"],
            "rapid_device_switching": device_check.get("rapid_switching", False),
        },
        "recommendation": recommendation,
        "reason": reason,
        "model_version": "7-factor-enhanced",  # Updated version
        "raw_result": result,  # Include full result for debugging
        # Phase 2 additions - detailed checks for audit trail
        "historical_checks": {
            "weather_check": weather_check,
            "device_check": device_check,
        },
    }
