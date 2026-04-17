from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ClaimStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False, index=True)
    trigger_event_id = Column(Integer, ForeignKey("trigger_events.id"), nullable=False, index=True)

    amount = Column(Float, nullable=False)
    status = Column(Enum(ClaimStatus), default=ClaimStatus.PENDING, index=True)

    # Fraud detection score (0-1, higher = more suspicious)
    fraud_score = Column(Float, default=0.0)

    # Validation data from pipeline (JSON string)
    # Contains: zone_match, platform_confirmation, traffic_check, gps_coherence
    validation_data = Column(Text, nullable=True)

    # Data lineage tracking (JSON string)
    # Contains: primary_source, corroborating, confidence, sources_used, oracle_result
    # Used for regulatory compliance and audit trails
    source_metadata = Column(Text, nullable=True)

    # UPI transaction reference
    upi_ref = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    policy = relationship("Policy", back_populates="claims")
    trigger_event = relationship("TriggerEvent", back_populates="claims")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_claim_policy_status', 'policy_id', 'status'),  # Filter claims by policy and status
        Index('ix_claim_created_at', 'created_at'),  # Time-based queries
        Index('ix_claim_trigger_status', 'trigger_event_id', 'status'),  # Claims per trigger
    )
