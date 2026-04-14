from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class TriggerType(str, enum.Enum):
    RAIN = "rain"           # Heavy rain/flood (>55mm/hr sustained 30+ mins)
    HEAT = "heat"           # Extreme heat (>43°C sustained 4+ hours)
    AQI = "aqi"             # Dangerous AQI (>400 for 3+ hours)
    SHUTDOWN = "shutdown"   # Civic shutdown/curfew/bandh (2+ hours)
    CLOSURE = "closure"     # Dark store force majeure closure (>90 mins)


# Trigger thresholds
TRIGGER_THRESHOLDS = {
    TriggerType.RAIN: {
        "threshold": 55,       # mm/hr
        "duration_mins": 30,
    },
    TriggerType.HEAT: {
        "threshold": 43,       # °C
        "duration_hours": 4,
    },
    TriggerType.AQI: {
        "threshold": 400,
        "duration_hours": 3,
    },
    TriggerType.SHUTDOWN: {
        "duration_hours": 2,
    },
    TriggerType.CLOSURE: {
        "duration_mins": 90,
    },
}


class TriggerEvent(Base):
    __tablename__ = "trigger_events"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    trigger_type = Column(Enum(TriggerType), nullable=False)

    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Severity level (1-5)
    severity = Column(Integer, default=1)

    # Raw API response data (JSON string)
    source_data = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    zone = relationship("Zone", back_populates="trigger_events")
    claims = relationship("Claim", back_populates="trigger_event")


class SustainedEvent(Base):
    """
    Persistent tracking for consecutive days of triggers.
    Replaces the in-memory _sustained_events dictionary in trigger_detector.
    """
    __tablename__ = "sustained_events"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False, index=True)
    trigger_type = Column(Enum(TriggerType), nullable=False)
    
    consecutive_days = Column(Integer, default=1)
    last_event_at = Column(DateTime(timezone=True), nullable=False)
    is_sustained = Column(Boolean, default=False)
    
    # JSON list of date strings for history
    history_json = Column(Text, default="[]") 

    # Relationships
    zone = relationship("Zone")
