from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class PolicyTier(str, enum.Enum):
    FLEX = "flex"
    STANDARD = "standard"
    PRO = "pro"


# Tier configuration
TIER_CONFIG = {
    PolicyTier.FLEX: {
        "weekly_premium": 29,
        "max_daily_payout": 250,
        "max_days_per_week": 3,
    },
    PolicyTier.STANDARD: {
        "weekly_premium": 49,
        "max_daily_payout": 350,
        "max_days_per_week": 5,
    },
    PolicyTier.PRO: {
        "weekly_premium": 79,
        "max_daily_payout": 500,
        "max_days_per_week": 7,
    },
}


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    tier = Column(Enum(PolicyTier), nullable=False)

    # Premium and payout limits (may differ from tier defaults due to dynamic pricing)
    weekly_premium = Column(Float, nullable=False)
    max_daily_payout = Column(Float, nullable=False)
    max_days_per_week = Column(Integer, nullable=False)

    # Policy period
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    partner = relationship("Partner", back_populates="policies")
    claims = relationship("Claim", back_populates="policy")
