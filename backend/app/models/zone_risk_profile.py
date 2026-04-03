"""
Zone risk profile model for RIQI (Road Infrastructure Quality Index) data.

Stores per-zone RIQI scores and associated metrics instead of relying
on hardcoded city-level defaults. Supports provenance tracking.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ZoneRiskProfile(Base):
    __tablename__ = "zone_risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), unique=True, nullable=False, index=True)

    # RIQI score (0-100) - higher = better infrastructure
    riqi_score = Column(Float, nullable=False, default=55.0)
    riqi_band = Column(String(20), nullable=False, default="urban_fringe")  # urban_core/urban_fringe/peri_urban

    # Input metrics used to calculate RIQI
    historical_suspensions = Column(Integer, default=0)  # Platform suspension count in last 12 months
    closure_frequency = Column(Float, default=0.0)  # Average closures per month
    weather_severity_freq = Column(Float, default=0.0)  # Weather events per month
    aqi_severity_freq = Column(Float, default=0.0)  # AQI breach events per month
    zone_density = Column(Float, default=0.0)  # Partner density (partners per sq km)

    # Provenance tracking
    calculated_from = Column(String(50), nullable=False, default="seeded")  # seeded | computed | manual | fallback_city_default
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    zone = relationship("Zone", backref="risk_profile", uselist=False)
