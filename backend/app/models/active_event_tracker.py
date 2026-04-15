"""
ActiveEventTracker — persistent tracking for in-progress trigger events.

Replaces the in-memory `active_events` dictionary in trigger_engine.py.
Ensures that if the server restarts, it can resume tracking events correctly
(the duration clock is not lost).
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class ActiveEventTracker(Base):
    """
    Tracks trigger events that are currently in progress (threshold breached
    but minimum duration not yet met).

    Once the duration requirement IS met, the tracker row is deleted and a
    TriggerEvent is created. If conditions clear before duration is met,
    the tracker row is simply deleted.
    """
    __tablename__ = "active_event_trackers"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # rain, heat, aqi, shutdown, closure

    # When the threshold was first breached (epoch seconds for precision)
    started_at_epoch = Column(Float, nullable=False)

    # Last observed details (JSON)
    details_json = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("zone_id", "event_type", name="uq_zone_event_type"),
    )
