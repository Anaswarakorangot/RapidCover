from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.policy import PolicyTier


class PolicyCreate(BaseModel):
    tier: PolicyTier
    auto_renew: bool = True


class PolicyResponse(BaseModel):
    id: int
    partner_id: int
    tier: PolicyTier
    weekly_premium: float
    max_daily_payout: float
    max_days_per_week: int
    starts_at: datetime
    expires_at: datetime
    is_active: bool
    auto_renew: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyQuote(BaseModel):
    """Premium quote based on partner's zone risk score."""
    tier: PolicyTier
    base_premium: float
    risk_adjustment: float
    final_premium: float
    max_daily_payout: float
    max_days_per_week: int
