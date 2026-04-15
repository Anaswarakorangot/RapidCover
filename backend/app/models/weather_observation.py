"""
Weather Observation Model

Persists weather and AQI observations from external APIs for:
- Historical fraud detection (weather consistency checks)
- Data lineage tracking for regulatory compliance
- Oracle confidence scoring
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utcnow


class WeatherObservation(Base):
    """
    Historical weather and AQI observations from external data sources.

    Used for:
    1. Fraud detection - compare claim weather vs stored observations
    2. Data lineage - track source and confidence of trigger events
    3. Oracle reliability - validate cross-source consistency
    """
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False, index=True)

    # Weather measurements (nullable - not all sources provide all data)
    temp_celsius = Column(Float, nullable=True)
    rainfall_mm_hr = Column(Float, nullable=True)
    aqi = Column(Integer, nullable=True)

    # Data provenance
    source = Column(String, nullable=False)  # "live", "mock", "stale", "oracle"
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    api_provider = Column(String, nullable=True)  # "openweathermap", "waqi", etc.

    # Timestamps
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)  # When the measurement was taken
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)  # When we stored it

    # Relationships
    zone = relationship("Zone", backref="weather_observations")

    def __repr__(self):
        return (
            f"<WeatherObservation(zone_id={self.zone_id}, "
            f"source={self.source}, observed_at={self.observed_at})>"
        )

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "zone_id": self.zone_id,
            "temp_celsius": self.temp_celsius,
            "rainfall_mm_hr": self.rainfall_mm_hr,
            "aqi": self.aqi,
            "source": self.source,
            "confidence": self.confidence,
            "api_provider": self.api_provider,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
