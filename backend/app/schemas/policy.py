from pydantic import BaseModel, computed_field
from datetime import datetime
from typing import Optional
from enum import Enum
from app.models.policy import PolicyTier


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    LAPSED = "lapsed"
    CANCELLED = "cancelled"


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
    pricing_mode: str = "standard"  # e.g. "standard", "surged", "loyalty"
    audit_breakdown: Optional[dict] = None


class PolicyResponseExtended(BaseModel):
    """Extended policy response with computed lifecycle fields."""
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
    renewed_from_id: Optional[int] = None

    # Computed lifecycle fields
    status: PolicyStatus
    days_until_expiry: Optional[int] = None
    hours_until_grace_ends: Optional[float] = None
    can_renew: bool = False

    model_config = {"from_attributes": True}


class PolicyRenewRequest(BaseModel):
    """Request to renew a policy."""
    tier: Optional[PolicyTier] = None  # Optional tier change
    auto_renew: bool = True


class PolicyRenewalQuote(BaseModel):
    """Renewal quote with loyalty discount."""
    tier: PolicyTier
    base_premium: float
    risk_adjustment: float
    loyalty_discount: float
    final_premium: float
    max_daily_payout: float
    max_days_per_week: int
    pricing_mode: str = "loyalty"
    audit_breakdown: Optional[dict] = None


class AutoRenewUpdate(BaseModel):
    """Request to update auto-renewal preference."""
    auto_renew: bool
