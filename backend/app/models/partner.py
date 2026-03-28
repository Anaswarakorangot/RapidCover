from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class Platform(str, enum.Enum):
    ZEPTO = "zepto"
    BLINKIT = "blinkit"


class Language(str, enum.Enum):
    ENGLISH = "en"
    TAMIL = "ta"
    KANNADA = "kn"
    TELUGU = "te"
    HINDI = "hi"
    MARATHI = "mr"
    BENGALI = "bn"


class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    aadhaar_hash = Column(String(64), nullable=True)  # SHA-256 hash of Aadhaar
    platform = Column(Enum(Platform), nullable=False)
    partner_id = Column(String(50), nullable=True)  # Platform-specific ID
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    language_pref = Column(Enum(Language), default=Language.ENGLISH)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    zone = relationship("Zone", back_populates="partners")
    policies = relationship("Policy", back_populates="partner")
