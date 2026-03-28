from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any
from app.models.claim import ClaimStatus
from app.models.trigger_event import TriggerType


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
