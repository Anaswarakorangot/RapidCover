from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class PolicyTier(str, enum.Enum):
    FLEX = "flex"
    STANDARD = "standard"
    PRO = "pro"


class PolicyStatus(str, enum.Enum):
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    LAPSED = "lapsed"
    CANCELLED = "cancelled"


# Tier configuration based on specification image
# Flex:     250/day * 2 days = 500 max/week. Ratio 500/22 = 22.7 (~1:23)
# Standard: 400/day * 3 days = 1200 max/week. Ratio 1200/33 = 36.3 (~1:36)
# Pro:      500/day * 4 days = 2000 max/week. Ratio 2000/45 = 44.4 (~1:44)
TIER_CONFIG = {
    PolicyTier.FLEX: {
        "weekly_premium": 22,
        "max_daily_payout": 250,
        "max_days_per_week": 2,
    },
    PolicyTier.STANDARD: {
        "weekly_premium": 33,
        "max_daily_payout": 400,
        "max_days_per_week": 3,
    },
    PolicyTier.PRO: {
        "weekly_premium": 45,
        "max_daily_payout": 500,
        "max_days_per_week": 4,
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

    # Policy lifecycle status
    status = Column(Enum(PolicyStatus), default=PolicyStatus.ACTIVE)
    grace_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Renewal chain tracking
    renewed_from_id = Column(Integer, ForeignKey("policies.id"), nullable=True)

    # Stripe payment tracking (TEST MODE)
    stripe_session_id = Column(String, nullable=True, unique=True)
    stripe_payment_intent = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    partner = relationship("Partner", back_populates="policies")
    claims = relationship("Claim", back_populates="policy")
    renewed_from = relationship("Policy", remote_side="Policy.id", backref="renewed_to")
