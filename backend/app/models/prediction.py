"""
Prediction models for insurer intelligence features.

WeeklyPrediction: Per-zone predictions for the upcoming week
CityRiskProfile: City-level risk aggregation with recommendations
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class WeeklyPrediction(Base):
    """Per-zone weekly predictions for disruption events."""
    __tablename__ = "weekly_predictions"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False, index=True)

    # Prediction week (start date)
    week_start = Column(DateTime(timezone=True), nullable=False, index=True)

    # Trigger probabilities (0.0 - 1.0)
    rain_probability = Column(Float, default=0.0)
    heat_probability = Column(Float, default=0.0)
    aqi_probability = Column(Float, default=0.0)
    shutdown_probability = Column(Float, default=0.0)
    closure_probability = Column(Float, default=0.0)

    # Expected outcomes
    expected_triggers = Column(Integer, default=0)
    expected_claims = Column(Integer, default=0)
    expected_payout_total = Column(Float, default=0.0)
    expected_loss_ratio = Column(Float, default=0.0)

    # Confidence and data quality
    confidence_score = Column(Float, default=0.5)  # 0.0 - 1.0
    data_sources = Column(Text, nullable=True)  # JSON: sources used for prediction

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    zone = relationship("Zone", backref="predictions")


class CityRiskProfile(Base):
    """City-level risk aggregation with actionable recommendations."""
    __tablename__ = "city_risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(50), nullable=False, index=True)

    # Profile week (start date)
    week_start = Column(DateTime(timezone=True), nullable=False, index=True)

    # Current state (last 7 days)
    current_loss_ratio = Column(Float, default=0.0)
    total_premiums_7d = Column(Float, default=0.0)
    total_payouts_7d = Column(Float, default=0.0)
    total_claims_7d = Column(Integer, default=0)
    total_triggers_7d = Column(Integer, default=0)

    # Predictions for next week
    predicted_loss_ratio = Column(Float, default=0.0)
    predicted_claims = Column(Integer, default=0)
    predicted_payout_total = Column(Float, default=0.0)

    # Risk flags
    is_at_risk = Column(Boolean, default=False)  # loss ratio > 70%
    requires_reinsurance = Column(Boolean, default=False)  # loss ratio > 100%

    # Recommendations
    recommendation_action = Column(String(50), nullable=True)  # suspend | reprice_up | reprice_down | maintain
    recommendation_premium_adjustment = Column(Float, nullable=True)  # percentage adjustment
    recommendation_reason = Column(Text, nullable=True)  # explanation

    # Confidence
    confidence_score = Column(Float, default=0.5)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
