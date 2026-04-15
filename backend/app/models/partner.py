from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, JSON
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
    upi_id = Column(String, nullable=True)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    aadhaar_hash = Column(String(64), nullable=True)  # SHA-256 hash of Aadhaar
    platform = Column(Enum(Platform), nullable=False)
    partner_id = Column(String(50), nullable=True)  # Platform-specific ID
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    language_pref = Column(Enum(Language), default=Language.ENGLISH)
    is_active = Column(Boolean, default=True)
    # Shift preferences
    shift_days = Column(JSON, nullable=True, default=lambda: [])      # e.g. ["mon","tue","wed","thu","fri"]
    shift_start = Column(String(10), nullable=True)                    # e.g. "09:00"
    shift_end = Column(String(10), nullable=True)                      # e.g. "18:00"

    # Zone history (list of {zone_id, from_date, to_date})
    zone_history = Column(JSON, nullable=True, default=lambda: [])

    # IMPS Fallback fields
    bank_name = Column(String(100), nullable=True)
    account_number = Column(String(30), nullable=True)
    ifsc_code = Column(String(20), nullable=True)

    # Social Security Code compliance (90/120-day rule)
    platform_engagement_days = Column(Integer, default=0)  # Total days worked on platform
    engagement_start_date = Column(DateTime(timezone=True), nullable=True)  # When they started
    ss_code_eligible = Column(Boolean, default=False)  # Cached eligibility flag

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    zone = relationship("Zone", back_populates="partners")
    policies = relationship("Policy", back_populates="partner")
    push_subscriptions = relationship("PushSubscription", back_populates="partner")
    gps_pings = relationship("PartnerGPSPing", back_populates="partner")
    devices = relationship("PartnerDevice", back_populates="partner")
    kyc = Column(JSON, nullable=True, default=lambda: {
        "aadhaar_number": None,
        "pan_number":     None,
        "kyc_status":     "skipped",
    })