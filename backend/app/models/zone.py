from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., BLR-047
    name = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False, index=True)

    # Polygon stored as GeoJSON string (for PostGIS, use Geometry type)
    polygon = Column(Text, nullable=True)

    # Risk score computed by ML model (0-100)
    risk_score = Column(Float, default=50.0)

    # Admin controls & visibility
    is_suspended = Column(Boolean, default=False)
    density_band = Column(String(20), default="Medium")  # Low, Medium, High

    # Dark store location
    dark_store_lat = Column(Float, nullable=True)
    dark_store_lng = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    partners = relationship("Partner", back_populates="zone")
    trigger_events = relationship("TriggerEvent", back_populates="zone")
