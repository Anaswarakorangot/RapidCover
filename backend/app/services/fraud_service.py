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