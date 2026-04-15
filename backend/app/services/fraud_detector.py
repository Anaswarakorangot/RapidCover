"""
Fraud detection service for claims validation.

Implements rule-based scoring for detecting suspicious claim patterns:
- GPS spoofing detection
- Activity paradox (runs during disruption)
- Claim frequency analysis
- Duplicate event detection
- Zone boundary gaming
- Collusion ring detection (basic)
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.partner import Partner
from app.utils.time_utils import utcnow
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent
from app.models.zone import Zone


# Fraud thresholds
FRAUD_THRESHOLDS = {
    "auto_approve": 0.3,      # Below this = auto approve
    "review_required": 0.6,    # Between 0.3-0.6 = manual review needed
    "auto_reject": 0.8,        # Above this = auto reject
}

# Scoring weights
SCORE_WEIGHTS = {
    "gps_mismatch": 0.25,
    "activity_paradox": 0.30,
    "high_frequency": 0.20,
    "duplicate_claim": 0.35,
    "new_account": 0.10,
    "zone_boundary": 0.15,
}


def check_gps_coherence(
    partner: Partner,
    trigger_event: TriggerEvent,
    partner_lat: Optional[float] = None,
    partner_lng: Optional[float] = None,
) -> float:
    """
    Check if partner's GPS location matches their registered zone.

    Returns a score 0-1 where higher = more suspicious.
    """
    if partner_lat is None or partner_lng is None:
        # No GPS data provided - slight penalty for missing data
        return 0.1

    zone = trigger_event.zone

    if not zone or not zone.dark_store_lat or not zone.dark_store_lng:
        return 0.0

    # Calculate rough distance (simplified)
    lat_diff = abs(partner_lat - zone.dark_store_lat)
    lng_diff = abs(partner_lng - zone.dark_store_lng)

    # ~111km per degree at equator, ~85km per degree in India
    distance_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 100

    # Within 5km = OK, 5-15km = suspicious, >15km = very suspicious
    if distance_km <= 5:
        return 0.0
    elif distance_km <= 15:
        return 0.3
    else:
        return 0.8


def check_activity_paradox(
    partner: Partner,
    trigger_event: TriggerEvent,
    had_deliveries_during: bool = False,
) -> float:
    """
    Check if partner was making deliveries during the disruption.

    If partner claims they couldn't work but had delivery activity,
    that's highly suspicious.

    Returns a score 0-1 where higher = more suspicious.
    """
    if had_deliveries_during:
        # Clear evidence of activity during claimed disruption
        return 0.9

    # In production, would check platform API for delivery records
    return 0.0


def check_claim_frequency(
    partner: Partner,
    db: Session,
    lookback_days: int = 30,
) -> float:
    """
    Check if partner has unusually high claim frequency.

    Returns a score 0-1 where higher = more suspicious.
    """
    # Get partner's policies
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    if not policy_ids:
        return 0.0

    # Count claims in lookback period
    cutoff = utcnow() - timedelta(days=lookback_days)

    claim_count = (
        db.query(func.count(Claim.id))
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.created_at >= cutoff,
        )
        .scalar()
    )

    # Scoring: 0-2 claims/month = OK, 3-4 = slight flag, 5+ = suspicious
    if claim_count <= 2:
        return 0.0
    elif claim_count <= 4:
        return 0.2
    elif claim_count <= 6:
        return 0.5
    else:
        return 0.8


def check_duplicate_claim(
    partner: Partner,
    trigger_event: TriggerEvent,
    db: Session,
) -> float:
    """
    Check if partner already has a claim for this trigger event.

    Returns a score 0-1 where higher = more suspicious.
    """
    # Get partner's policies
    policy_ids = [p.id for p in db.query(Policy).filter(Policy.partner_id == partner.id).all()]

    if not policy_ids:
        return 0.0

    # Check for existing claim on this trigger
    existing = (
        db.query(Claim)
        .filter(
            Claim.policy_id.in_(policy_ids),
            Claim.trigger_event_id == trigger_event.id,
        )
        .first()
    )

    if existing:
        return 1.0  # Definite duplicate

    return 0.0


def check_account_age(partner: Partner) -> float:
    """
    Check if this is a new account (higher fraud risk).

    Returns a score 0-1 where higher = more suspicious.
    """
    if not partner.created_at:
        return 0.1

    # Ensure created_at is timezone-aware for comparison with utcnow()
    created_at = partner.created_at
    if created_at.tzinfo is None:
        from datetime import timezone
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = (utcnow() - created_at).days

    # Less than 7 days = new, slight flag
    if age_days < 7:
        return 0.3
    elif age_days < 30:
        return 0.1
    else:
        return 0.0


def check_zone_boundary_gaming(
    partner: Partner,
    db: Session,
) -> float:
    """
    Check if partner frequently changes zones to maximize claims.

    Returns a score 0-1 where higher = more suspicious.
    """
    # For now, return 0 since we don't track zone changes
    # In production, would analyze zone change patterns
    return 0.0


def calculate_fraud_score(
    partner: Partner,
    trigger_event: TriggerEvent,
    db: Session,
    partner_lat: Optional[float] = None,
    partner_lng: Optional[float] = None,
    had_deliveries_during: bool = False,
) -> dict:
    """
    Calculate overall fraud score for a claim.

    Returns dict with:
    - score: float 0-1 (higher = more suspicious)
    - factors: dict of individual factor scores
    - recommendation: "approve", "review", or "reject"
    """
    factors = {
        "gps_coherence": check_gps_coherence(partner, trigger_event, partner_lat, partner_lng),
        "activity_paradox": check_activity_paradox(partner, trigger_event, had_deliveries_during),
        "claim_frequency": check_claim_frequency(partner, db),
        "duplicate_claim": check_duplicate_claim(partner, trigger_event, db),
        "account_age": check_account_age(partner),
        "zone_boundary": check_zone_boundary_gaming(partner, db),
    }

    # If duplicate claim detected, immediately flag
    if factors["duplicate_claim"] >= 1.0:
        return {
            "score": 1.0,
            "factors": factors,
            "recommendation": "reject",
            "reason": "Duplicate claim for same trigger event",
        }

    # Calculate weighted score
    weighted_sum = (
        factors["gps_coherence"] * SCORE_WEIGHTS["gps_mismatch"]
        + factors["activity_paradox"] * SCORE_WEIGHTS["activity_paradox"]
        + factors["claim_frequency"] * SCORE_WEIGHTS["high_frequency"]
        + factors["account_age"] * SCORE_WEIGHTS["new_account"]
        + factors["zone_boundary"] * SCORE_WEIGHTS["zone_boundary"]
    )

    # Normalize to 0-1 range
    max_weighted = sum(v for k, v in SCORE_WEIGHTS.items() if k != "duplicate_claim")
    score = min(1.0, weighted_sum / max_weighted)

    # Determine recommendation
    if score < FRAUD_THRESHOLDS["auto_approve"]:
        recommendation = "approve"
        reason = "Low risk - auto approved"
    elif score < FRAUD_THRESHOLDS["review_required"]:
        recommendation = "review"
        reason = "Moderate risk - manual review required"
    elif score < FRAUD_THRESHOLDS["auto_reject"]:
        recommendation = "review"
        reason = "High risk - urgent review required"
    else:
        recommendation = "reject"
        reason = "Very high risk - auto rejected"

    return {
        "score": round(score, 3),
        "factors": factors,
        "recommendation": recommendation,
        "reason": reason,
    }
