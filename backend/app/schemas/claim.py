from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any
from app.models.claim import ClaimStatus
from app.models.trigger_event import TriggerType


class PayoutMetadata(BaseModel):
    """Structured payout calculation details included in ClaimResponse."""
    disruption_hours: Optional[float] = None
    hourly_rate: Optional[float] = None
    severity: Optional[int] = None
    severity_multiplier: Optional[float] = None
    base_payout: Optional[float] = None
    adjusted_payout: Optional[float] = None
    final_payout: Optional[float] = None
    trigger_type: Optional[str] = None
    zone_id: Optional[int] = None


class ClaimResponse(BaseModel):
    id: int
    policy_id: int
    trigger_event_id: int
    amount: float
    status: ClaimStatus
    fraud_score: float
    upi_ref: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    # Nested trigger event info
    trigger_type: Optional[TriggerType] = None
    trigger_started_at: Optional[datetime] = None

    # Payout metadata from validation_data
    payout_metadata: Optional[PayoutMetadata] = None

    model_config = {"from_attributes": True}


class ClaimListResponse(BaseModel):
    claims: list[ClaimResponse]
    total: int
    page: int
    page_size: int


class ClaimSummary(BaseModel):
    """Summary of claims for a partner."""
    total_claims: int
    total_paid: float
    pending_claims: int
    pending_amount: float