"""
Zone reassignment model for 24-hour acceptance workflow.

When a partner is proposed to move to a new zone (e.g., Zepto/Blinkit reassignment),
they have 24 hours to accept or reject. If no action is taken, the proposal expires.
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ReassignmentStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ZoneReassignment(Base):
    __tablename__ = "zone_reassignments"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)
    old_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    new_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)

    status = Column(Enum(ReassignmentStatus), default=ReassignmentStatus.PROPOSED, nullable=False)

    # Premium adjustment calculation
    premium_adjustment = Column(Float, default=0.0)  # Positive = credit, Negative = debit
    remaining_days = Column(Integer, default=0)

    # Timestamps for the workflow
    proposed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # proposed_at + 24h
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    partner = relationship("Partner", foreign_keys=[partner_id])
    old_zone = relationship("Zone", foreign_keys=[old_zone_id])
    new_zone = relationship("Zone", foreign_keys=[new_zone_id])
