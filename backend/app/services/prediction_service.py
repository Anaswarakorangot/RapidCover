"""
Prediction Service for Insurer Intelligence.

Computes zone-level disruption probabilities, expected claims, loss ratio projections,
and generates actionable recommendations for city-level risk management.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.zone import Zone
from app.utils.time_utils import utcnow
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent, TriggerType
from app.models.prediction import WeeklyPrediction, CityRiskProfile

logger = logging.getLogger(__name__)

# Seasonal patterns (simplified) - month index to probability multiplier
MONSOON_MONTHS = {6: 1.8, 7: 2.2, 8: 2.0, 9: 1.5}  # June-Sept
HEAT_MONTHS = {4: 1.6, 5: 2.0, 6: 1.4}  # April-June
AQI_MONTHS = {10: 1.3, 11: 2.0, 12: 1.8, 1: 1.5}  # Oct-Jan

# Base probabilities by trigger type (weekly probability for an event)
BASE_PROBABILITIES = {
    TriggerType.RAIN: 0.15,
    TriggerType.HEAT: 0.10,
    TriggerType.AQI: 0.08,
    TriggerType.SHUTDOWN: 0.02,
    TriggerType.CLOSURE: 0.05,
}

# Average payout per trigger type (INR)
AVG_PAYOUT_PER_TRIGGER = {
    TriggerType.RAIN: 350,
    TriggerType.HEAT: 280,
    TriggerType.AQI: 300,
    TriggerType.SHUTDOWN: 320,
    TriggerType.CLOSURE: 200,
}


def compute_zone_disruption_probability(
    zone: Zone,
    db: Session,
    trigger_type: TriggerType,
) -> float:
    """
    Compute the probability of a specific trigger type occurring in a zone.

    Uses:
    - Historical trigger frequency for this zone
    - Seasonal patterns
    - City-level risk factors
    """
    now = utcnow()
    month = now.month

    # Base probability
    base_prob = BASE_PROBABILITIES.get(trigger_type, 0.05)

    # Seasonal multiplier
    seasonal_mult = 1.0
    if trigger_type == TriggerType.RAIN:
        seasonal_mult = MONSOON_MONTHS.get(month, 1.0)
    elif trigger_type == TriggerType.HEAT:
        seasonal_mult = HEAT_MONTHS.get(month, 1.0)
    elif trigger_type == TriggerType.AQI:
        seasonal_mult = AQI_MONTHS.get(month, 1.0)

    # Historical frequency (last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    historical_count = (
        db.query(func.count(TriggerEvent.id))
        .filter(
            TriggerEvent.zone_id == zone.id,
            TriggerEvent.trigger_type == trigger_type,
            TriggerEvent.started_at >= thirty_days_ago,
        )
        .scalar()
    ) or 0

    # Historical adjustment (if more triggers than expected, increase probability)
    historical_mult = 1.0 + (historical_count * 0.1)
    historical_mult = min(historical_mult, 2.0)  # Cap at 2x

    # Zone risk score adjustment
    risk_mult = 1.0 + ((zone.risk_score - 50) / 100)  # risk_score 50 = neutral

    probability = base_prob * seasonal_mult * historical_mult * risk_mult
    return min(probability, 0.95)  # Cap at 95%


def compute_expected_claims(
    zone: Zone,
    db: Session,
    trigger_probabilities: dict[TriggerType, float],
) -> tuple[int, float]:
    """
    Compute expected claims and payout for a zone based on trigger probabilities.

    Returns: (expected_claims, expected_payout)
    """
    # Count active policies in zone
    now = utcnow()
    active_policies = (
        db.query(func.count(Policy.id))
        .join(Partner, Policy.partner_id == Partner.id)
        .filter(
            Partner.zone_id == zone.id,
            Partner.is_active == True,
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .scalar()
    ) or 0

    if active_policies == 0:
        return 0, 0.0

    # Expected claims = sum(probability * partners_affected * claim_rate)
    # Assume 85% of partners file a claim when a trigger occurs
    claim_rate = 0.85

    total_expected_claims = 0.0
    total_expected_payout = 0.0

    for trigger_type, prob in trigger_probabilities.items():
        expected_triggers = prob  # probability of at least one trigger
        expected_claims = expected_triggers * active_policies * claim_rate
        avg_payout = AVG_PAYOUT_PER_TRIGGER.get(trigger_type, 300)
        expected_payout = expected_claims * avg_payout

        total_expected_claims += expected_claims
        total_expected_payout += expected_payout

    return int(total_expected_claims), round(total_expected_payout, 2)


def compute_loss_ratio_projection(
    zone: Zone,
    db: Session,
    expected_payout: float,
) -> float:
    """
    Compute projected loss ratio for a zone.

    Loss Ratio = Expected Payouts / Expected Premiums
    """
    now = utcnow()

    # Total weekly premiums from active policies in zone
    weekly_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .join(Partner, Policy.partner_id == Partner.id)
        .filter(
            Partner.zone_id == zone.id,
            Partner.is_active == True,
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .scalar()
    ) or 0.0

    if weekly_premiums == 0:
        return 0.0

    loss_ratio = (expected_payout / weekly_premiums) * 100
    return round(loss_ratio, 1)


def generate_recommendation(
    city: str,
    current_loss_ratio: float,
    predicted_loss_ratio: float,
) -> dict:
    """
    Generate actionable recommendation based on loss ratio trends.

    Returns: {action, premium_adjustment, reason}
    """
    # Decision thresholds
    HEALTHY_MAX = 70
    WATCH_MAX = 85
    SUSPEND_THRESHOLD = 100

    action = "maintain"
    premium_adjustment = None
    reason = "Loss ratio within healthy range. No action needed."

    if predicted_loss_ratio >= SUSPEND_THRESHOLD:
        action = "suspend"
        reason = f"Predicted loss ratio ({predicted_loss_ratio:.0f}%) exceeds 100%. Suspend new enrollments and trigger reinsurance review."
    elif predicted_loss_ratio >= WATCH_MAX:
        action = "reprice_up"
        # Suggest premium increase proportional to excess risk
        excess = predicted_loss_ratio - HEALTHY_MAX
        premium_adjustment = min(30, excess * 0.5)  # Cap at 30%
        reason = f"Predicted loss ratio ({predicted_loss_ratio:.0f}%) approaching danger zone. Recommend {premium_adjustment:.0f}% premium increase."
    elif predicted_loss_ratio < 50 and current_loss_ratio < 50:
        action = "reprice_down"
        # Consider premium reduction for very low loss ratios
        premium_adjustment = -5
        reason = f"Loss ratio very healthy ({predicted_loss_ratio:.0f}%). Consider 5% premium reduction to attract more partners."
    elif current_loss_ratio > predicted_loss_ratio + 15:
        action = "monitor"
        reason = f"Loss ratio improving (current: {current_loss_ratio:.0f}% → predicted: {predicted_loss_ratio:.0f}%). Continue monitoring."

    return {
        "action": action,
        "premium_adjustment": premium_adjustment,
        "reason": reason,
    }


def cleanup_duplicate_predictions(db: Session) -> int:
    """Remove duplicate predictions, keeping only the most recent one per zone/week."""
    from sqlalchemy import text

    # Get all zone/week combinations with duplicates
    duplicates = (
        db.query(
            WeeklyPrediction.zone_id,
            WeeklyPrediction.week_start,
            func.count(WeeklyPrediction.id).label('count')
        )
        .group_by(WeeklyPrediction.zone_id, WeeklyPrediction.week_start)
        .having(func.count(WeeklyPrediction.id) > 1)
        .all()
    )

    deleted_count = 0
    for zone_id, week_start, count in duplicates:
        # Get all predictions for this zone/week, ordered by id (keep the first one)
        predictions = (
            db.query(WeeklyPrediction)
            .filter(
                WeeklyPrediction.zone_id == zone_id,
                WeeklyPrediction.week_start == week_start,
            )
            .order_by(WeeklyPrediction.id)
            .all()
        )
        # Delete all but the first one
        for p in predictions[1:]:
            db.delete(p)
            deleted_count += 1

    db.commit()
    return deleted_count


def generate_weekly_predictions(db: Session) -> list[WeeklyPrediction]:
    """
    Generate or update weekly predictions for all zones.

    Called by scheduled job or manually from admin.
    """
    # First, clean up any existing duplicates
    cleanup_duplicate_predictions(db)

    now = utcnow()
    week_start = now - timedelta(days=now.weekday())  # Start of current week
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    zones = db.query(Zone).all()
    predictions = []

    for zone in zones:
        # Compute trigger probabilities
        trigger_probs = {}
        for trigger_type in TriggerType:
            trigger_probs[trigger_type] = compute_zone_disruption_probability(
                zone, db, trigger_type
            )

        # Compute expected outcomes
        expected_claims, expected_payout = compute_expected_claims(
            zone, db, trigger_probs
        )
        expected_loss_ratio = compute_loss_ratio_projection(
            zone, db, expected_payout
        )

        # Expected triggers (sum of probabilities rounded)
        expected_triggers = int(sum(trigger_probs.values()))

        # Confidence score based on data availability
        thirty_days_ago = now - timedelta(days=30)
        historical_data_count = (
            db.query(func.count(TriggerEvent.id))
            .filter(
                TriggerEvent.zone_id == zone.id,
                TriggerEvent.started_at >= thirty_days_ago,
            )
            .scalar()
        ) or 0
        confidence = min(0.5 + (historical_data_count * 0.1), 0.95)

        # Check for existing prediction this week
        existing = (
            db.query(WeeklyPrediction)
            .filter(
                WeeklyPrediction.zone_id == zone.id,
                WeeklyPrediction.week_start == week_start,
            )
            .first()
        )

        if existing:
            prediction = existing
        else:
            prediction = WeeklyPrediction(zone_id=zone.id, week_start=week_start)
            db.add(prediction)

        # Update prediction values
        prediction.rain_probability = trigger_probs.get(TriggerType.RAIN, 0)
        prediction.heat_probability = trigger_probs.get(TriggerType.HEAT, 0)
        prediction.aqi_probability = trigger_probs.get(TriggerType.AQI, 0)
        prediction.shutdown_probability = trigger_probs.get(TriggerType.SHUTDOWN, 0)
        prediction.closure_probability = trigger_probs.get(TriggerType.CLOSURE, 0)
        prediction.expected_triggers = expected_triggers
        prediction.expected_claims = expected_claims
        prediction.expected_payout_total = expected_payout
        prediction.expected_loss_ratio = expected_loss_ratio
        prediction.confidence_score = confidence
        prediction.data_sources = json.dumps(["historical_triggers", "seasonal_patterns", "zone_risk_score"])

        predictions.append(prediction)

    db.commit()
    logger.info(f"Generated {len(predictions)} weekly predictions")
    return predictions


def cleanup_duplicate_city_profiles(db: Session) -> int:
    """Remove duplicate city risk profiles, keeping only the most recent one per city/week."""
    duplicates = (
        db.query(
            CityRiskProfile.city,
            CityRiskProfile.week_start,
            func.count(CityRiskProfile.id).label('count')
        )
        .group_by(CityRiskProfile.city, CityRiskProfile.week_start)
        .having(func.count(CityRiskProfile.id) > 1)
        .all()
    )

    deleted_count = 0
    for city, week_start, count in duplicates:
        profiles = (
            db.query(CityRiskProfile)
            .filter(
                CityRiskProfile.city == city,
                CityRiskProfile.week_start == week_start,
            )
            .order_by(CityRiskProfile.id)
            .all()
        )
        for p in profiles[1:]:
            db.delete(p)
            deleted_count += 1

    db.commit()
    return deleted_count


def generate_city_risk_profiles(db: Session) -> list[CityRiskProfile]:
    """
    Generate or update city-level risk profiles with recommendations.

    Aggregates zone predictions to city level and generates actionable recommendations.
    """
    # First, clean up any existing duplicates
    cleanup_duplicate_city_profiles(db)

    now = utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)

    # Get unique cities
    cities = db.query(Zone.city).distinct().all()
    profiles = []

    for (city,) in cities:
        # Get zones in city
        city_zones = db.query(Zone).filter(Zone.city == city).all()
        zone_ids = [z.id for z in city_zones]

        if not zone_ids:
            continue

        # Current state (last 7 days)
        partner_ids = [
            p[0] for p in
            db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids)).all()
        ]

        total_premiums = (
            db.query(func.sum(Policy.weekly_premium))
            .filter(
                Policy.partner_id.in_(partner_ids) if partner_ids else False,
                Policy.is_active == True,
            )
            .scalar()
        ) or 0.0

        total_payouts = (
            db.query(func.sum(Claim.amount))
            .join(TriggerEvent, Claim.trigger_event_id == TriggerEvent.id)
            .filter(
                TriggerEvent.zone_id.in_(zone_ids),
                Claim.status == ClaimStatus.PAID,
                Claim.paid_at >= seven_days_ago,
            )
            .scalar()
        ) or 0.0

        total_claims = (
            db.query(func.count(Claim.id))
            .join(TriggerEvent, Claim.trigger_event_id == TriggerEvent.id)
            .filter(
                TriggerEvent.zone_id.in_(zone_ids),
                Claim.created_at >= seven_days_ago,
            )
            .scalar()
        ) or 0

        total_triggers = (
            db.query(func.count(TriggerEvent.id))
            .filter(
                TriggerEvent.zone_id.in_(zone_ids),
                TriggerEvent.started_at >= seven_days_ago,
            )
            .scalar()
        ) or 0

        current_lr = (total_payouts / total_premiums * 100) if total_premiums > 0 else 0

        # Get predictions for this week
        city_predictions = (
            db.query(WeeklyPrediction)
            .filter(
                WeeklyPrediction.zone_id.in_(zone_ids),
                WeeklyPrediction.week_start == week_start,
            )
            .all()
        )

        predicted_claims = sum(p.expected_claims for p in city_predictions)
        predicted_payout = sum(p.expected_payout_total for p in city_predictions)
        predicted_lr = (predicted_payout / total_premiums * 100) if total_premiums > 0 else 0

        # Generate recommendation
        recommendation = generate_recommendation(city, current_lr, predicted_lr)

        # Risk flags
        is_at_risk = predicted_lr > 70
        requires_reinsurance = predicted_lr > 100

        # Confidence (average of zone predictions)
        avg_confidence = (
            sum(p.confidence_score for p in city_predictions) / len(city_predictions)
            if city_predictions else 0.5
        )

        # Check for existing profile
        existing = (
            db.query(CityRiskProfile)
            .filter(
                CityRiskProfile.city == city,
                CityRiskProfile.week_start == week_start,
            )
            .first()
        )

        if existing:
            profile = existing
        else:
            profile = CityRiskProfile(city=city, week_start=week_start)
            db.add(profile)

        # Update profile
        profile.current_loss_ratio = round(current_lr, 1)
        profile.total_premiums_7d = total_premiums
        profile.total_payouts_7d = total_payouts
        profile.total_claims_7d = total_claims
        profile.total_triggers_7d = total_triggers
        profile.predicted_loss_ratio = round(predicted_lr, 1)
        profile.predicted_claims = predicted_claims
        profile.predicted_payout_total = predicted_payout
        profile.is_at_risk = is_at_risk
        profile.requires_reinsurance = requires_reinsurance
        profile.recommendation_action = recommendation["action"]
        profile.recommendation_premium_adjustment = recommendation["premium_adjustment"]
        profile.recommendation_reason = recommendation["reason"]
        profile.confidence_score = round(avg_confidence, 2)

        profiles.append(profile)

    db.commit()
    logger.info(f"Generated {len(profiles)} city risk profiles")
    return profiles


def get_intelligence_summary(db: Session) -> dict:
    """
    Get executive summary of insurer intelligence.

    Returns at-risk cities, alerts, and totals for admin dashboard.
    """
    now = utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get all city profiles for this week
    profiles = (
        db.query(CityRiskProfile)
        .filter(CityRiskProfile.week_start == week_start)
        .all()
    )

    at_risk_cities = [p.city for p in profiles if p.is_at_risk]
    reinsurance_cities = [p.city for p in profiles if p.requires_reinsurance]

    total_predicted_claims = sum(p.predicted_claims for p in profiles)
    total_predicted_payout = sum(p.predicted_payout_total for p in profiles)

    # Build alerts
    alerts = []
    for p in profiles:
        if p.requires_reinsurance:
            alerts.append({
                "level": "critical",
                "city": p.city,
                "message": f"Loss ratio {p.predicted_loss_ratio:.0f}% - reinsurance activation required",
            })
        elif p.is_at_risk:
            alerts.append({
                "level": "warning",
                "city": p.city,
                "message": f"Loss ratio {p.predicted_loss_ratio:.0f}% - premium adjustment recommended",
            })

    return {
        "week_start": week_start.isoformat(),
        "total_cities": len(profiles),
        "at_risk_cities": at_risk_cities,
        "reinsurance_required": reinsurance_cities,
        "total_predicted_claims": total_predicted_claims,
        "total_predicted_payout": total_predicted_payout,
        "alerts": alerts,
        "computed_at": now.isoformat(),
    }
