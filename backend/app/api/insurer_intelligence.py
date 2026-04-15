"""
Insurer Intelligence API - Predictive analytics and risk management endpoints.

Provides:
  GET  /admin/intelligence/predictions    -> Weekly predictions by zone
  GET  /admin/intelligence/risk-profiles  -> City risk profiles with recommendations
  GET  /admin/intelligence/summary        -> Executive summary (at-risk cities, alerts)
  POST /admin/intelligence/refresh        -> Regenerate all predictions
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.time_utils import utcnow
from app.models.prediction import WeeklyPrediction, CityRiskProfile
from app.services.prediction_service import (
    generate_weekly_predictions,
    generate_city_risk_profiles,
    get_intelligence_summary,
)

router = APIRouter(prefix="/admin/intelligence", tags=["insurer-intelligence"])


# --- Response schemas --------------------------------------------------------

class TriggerProbabilities(BaseModel):
    rain: float
    heat: float
    aqi: float
    shutdown: float
    closure: float


class ZonePredictionResponse(BaseModel):
    zone_id: int
    zone_name: str
    zone_code: str
    city: str
    week_start: str
    probabilities: TriggerProbabilities
    expected_triggers: int
    expected_claims: int
    expected_payout_total: float
    expected_loss_ratio: float
    confidence_score: float


class CityRiskProfileResponse(BaseModel):
    city: str
    week_start: str
    current_loss_ratio: float
    total_premiums_7d: float
    total_payouts_7d: float
    total_claims_7d: int
    total_triggers_7d: int
    predicted_loss_ratio: float
    predicted_claims: int
    predicted_payout_total: float
    is_at_risk: bool
    requires_reinsurance: bool
    recommendation: dict
    confidence_score: float


class IntelligenceSummaryResponse(BaseModel):
    week_start: str
    total_cities: int
    at_risk_cities: list[str]
    reinsurance_required: list[str]
    total_predicted_claims: int
    total_predicted_payout: float
    alerts: list[dict]
    computed_at: str


class RefreshResponse(BaseModel):
    status: str
    predictions_generated: int
    profiles_generated: int
    computed_at: str


# --- GET /admin/intelligence/predictions -------------------------------------

@router.get("/predictions", response_model=list[ZonePredictionResponse])
def get_predictions(
    city: Optional[str] = Query(None, description="Filter by city"),
    db: Session = Depends(get_db),
):
    """
    Get weekly predictions for all zones (or filtered by city).

    Returns predicted trigger probabilities, expected claims, and loss ratios.
    """
    from app.models.zone import Zone

    now = utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    query = (
        db.query(WeeklyPrediction)
        .join(Zone, WeeklyPrediction.zone_id == Zone.id)
        .filter(WeeklyPrediction.week_start == week_start)
    )

    if city:
        query = query.filter(Zone.city.ilike(f"%{city}%"))

    predictions = query.all()

    # If no predictions exist for this week, generate them
    if not predictions:
        generate_weekly_predictions(db)
        predictions = query.all()

    results = []
    for p in predictions:
        zone = db.query(Zone).filter(Zone.id == p.zone_id).first()
        if not zone:
            continue

        results.append(ZonePredictionResponse(
            zone_id=p.zone_id,
            zone_name=zone.name,
            zone_code=zone.code,
            city=zone.city,
            week_start=p.week_start.isoformat(),
            probabilities=TriggerProbabilities(
                rain=round(p.rain_probability, 3),
                heat=round(p.heat_probability, 3),
                aqi=round(p.aqi_probability, 3),
                shutdown=round(p.shutdown_probability, 3),
                closure=round(p.closure_probability, 3),
            ),
            expected_triggers=p.expected_triggers,
            expected_claims=p.expected_claims,
            expected_payout_total=p.expected_payout_total,
            expected_loss_ratio=p.expected_loss_ratio,
            confidence_score=round(p.confidence_score, 2),
        ))

    return results


# --- GET /admin/intelligence/risk-profiles -----------------------------------

@router.get("/risk-profiles", response_model=list[CityRiskProfileResponse])
def get_risk_profiles(
    at_risk_only: bool = Query(False, description="Only return at-risk cities"),
    db: Session = Depends(get_db),
):
    """
    Get city-level risk profiles with actionable recommendations.

    Returns current and predicted loss ratios, risk flags, and premium adjustment suggestions.
    """
    now = utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    query = db.query(CityRiskProfile).filter(
        CityRiskProfile.week_start == week_start
    )

    if at_risk_only:
        query = query.filter(CityRiskProfile.is_at_risk == True)

    profiles = query.all()

    # If no profiles exist for this week, generate them
    if not profiles:
        generate_weekly_predictions(db)
        generate_city_risk_profiles(db)
        profiles = query.all()

    results = []
    for p in profiles:
        results.append(CityRiskProfileResponse(
            city=p.city,
            week_start=p.week_start.isoformat(),
            current_loss_ratio=p.current_loss_ratio,
            total_premiums_7d=p.total_premiums_7d,
            total_payouts_7d=p.total_payouts_7d,
            total_claims_7d=p.total_claims_7d,
            total_triggers_7d=p.total_triggers_7d,
            predicted_loss_ratio=p.predicted_loss_ratio,
            predicted_claims=p.predicted_claims,
            predicted_payout_total=p.predicted_payout_total,
            is_at_risk=p.is_at_risk,
            requires_reinsurance=p.requires_reinsurance,
            recommendation={
                "action": p.recommendation_action,
                "premium_adjustment": p.recommendation_premium_adjustment,
                "reason": p.recommendation_reason,
            },
            confidence_score=p.confidence_score,
        ))

    return results


# --- GET /admin/intelligence/summary -----------------------------------------

@router.get("/summary", response_model=IntelligenceSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    """
    Get executive summary of insurer intelligence.

    Returns at-risk cities, alerts, and aggregate predictions for the current week.
    """
    now = utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if predictions exist
    prediction_count = (
        db.query(WeeklyPrediction)
        .filter(WeeklyPrediction.week_start == week_start)
        .count()
    )

    if prediction_count == 0:
        generate_weekly_predictions(db)
        generate_city_risk_profiles(db)

    summary = get_intelligence_summary(db)

    return IntelligenceSummaryResponse(**summary)


# --- POST /admin/intelligence/refresh ----------------------------------------

@router.post("/refresh", response_model=RefreshResponse)
def refresh_predictions(db: Session = Depends(get_db)):
    """
    Regenerate all predictions and risk profiles.

    Forces recalculation using latest data. Use after major data updates or
    when seasonal patterns change.
    """
    # Delete ALL existing predictions first to ensure clean slate
    db.query(WeeklyPrediction).delete()
    db.query(CityRiskProfile).delete()
    db.commit()

    predictions = generate_weekly_predictions(db)
    profiles = generate_city_risk_profiles(db)

    return RefreshResponse(
        status="success",
        predictions_generated=len(predictions),
        profiles_generated=len(profiles),
        computed_at=utcnow().isoformat(),
    )
