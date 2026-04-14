from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PartnerGPSPing(Base):
    """
    Persistent store for partner GPS trajectory.
    Required for calculate_fraud_score velocity and centroid drift checks.
    """
    __tablename__ = "partner_gps_pings"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)
    
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    
    # Platform source (Zomato/Swiggy/Internal)
    source = Column(String, default="internal")
    
    # Device context
    device_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    partner = relationship("Partner", back_populates="gps_pings")


class PartnerDevice(Base):
    """
    Tracking for device consistency (Fingerprinting).
    """
    __tablename__ = "partner_devices"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)
    
    device_id = Column(String, nullable=False, index=True)
    model = Column(String, nullable=True)
    os_version = Column(String, nullable=True)
    
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    partner = relationship("Partner", back_populates="devices")
