from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text, Boolean
from sqlalchemy.sql import func
import enum
from app.database import Base


class DrillType(str, enum.Enum):
    FLASH_FLOOD = "flash_flood"
    AQI_SPIKE = "aqi_spike"
    HEATWAVE = "heatwave"
    STORE_CLOSURE = "store_closure"
    CURFEW = "curfew"


class DrillStatus(str, enum.Enum):
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DrillSession(Base):
    __tablename__ = "drill_sessions"

    id = Column(Integer, primary_key=True, index=True)
    drill_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID string
    drill_type = Column(Enum(DrillType), nullable=False)
    zone_id = Column(Integer, nullable=False)
    zone_code = Column(String(20), nullable=False)
    preset = Column(String(50), nullable=False)

    status = Column(Enum(DrillStatus), default=DrillStatus.STARTED)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Pipeline events stored as JSON array
    pipeline_events = Column(Text, nullable=True)  # JSON string

    # Reference to trigger event created by drill
    trigger_event_id = Column(Integer, nullable=True)

    # Impact metrics
    affected_partners = Column(Integer, default=0)  # Partners in zone
    eligible_partners = Column(Integer, default=0)  # Partners with active policies
    claims_created = Column(Integer, default=0)
    claims_paid = Column(Integer, default=0)
    claims_pending = Column(Integer, default=0)

    # Financial metrics
    payouts_total = Column(Float, default=0.0)

    # Skipped reasons stored as JSON dict
    skipped_reasons = Column(Text, nullable=True)  # JSON string

    # Latency metrics in milliseconds
    trigger_latency_ms = Column(Integer, nullable=True)
    claim_creation_latency_ms = Column(Integer, nullable=True)
    payout_latency_ms = Column(Integer, nullable=True)
    total_latency_ms = Column(Integer, nullable=True)

    # Errors stored as JSON array
    errors = Column(Text, nullable=True)  # JSON string

    # Force mode bypasses duration requirements
    force_mode = Column(Boolean, default=False)
