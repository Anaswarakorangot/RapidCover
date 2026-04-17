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
    device_fingerprint: Optional[str] = None  # Device fingerprint for fraud detection
    created_at: datetime
    paid_at: Optional[datetime] = None

    # Nested trigger event info
    trigger_type: Optional[TriggerType] = None
    trigger_started_at: Optional[datetime] = None

    # Payout metadata from validation_data
    payout_metadata: Optional[PayoutMetadata] = None

    # Partial disruption data
    disruption_category: Optional[str] = None
    disruption_factor: Optional[float] = None

    # Payment state machine status
    payment_status: Optional[str] = None

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


# =============================================================================
# Claim Explanation Schema (Person 1 trust deliverable)
# =============================================================================

class ClaimExplanationResponse(BaseModel):
    """
    GET /claims/{claim_id}/explanation
    Full human-readable explanation of a claim decision.
    Turns every claim into something a rider, judge, or admin can understand.
    """
    claim_id: int
    status: str                          # paid | pending | rejected
    decision: str                        # One-line summary of what happened

    # Trigger context
    trigger_source: Optional[str]        # e.g. "OpenWeatherMap"
    trigger_type: Optional[str]          # rain | heat | aqi | shutdown | closure
    trigger_started_at: Optional[datetime]
    trigger_ended_at: Optional[datetime]

    # Zone context
    zone_match: bool
    zone_name: Optional[str]
    zone_code: Optional[str]

    # Payout formula (human-readable string built from stored data)
    payout_formula: Optional[str]        # e.g. "3.5 hrs × ₹120/hr × 1.25 RIQI = ₹525"
    amount: float

    # Fraud assessment
    fraud_decision: str                  # auto_approve | enhanced_validation | manual_review | auto_reject
    fraud_score: float
    fraud_reasons: list[str]             # plain-language fraud factor notes

    # Payment
    payment_status: Optional[str]        # completed | pending | failed
    upi_ref: Optional[str]
    paid_at: Optional[datetime]

    # The plain-language explanation (main copy)
    plain_language_reason: str

    # Data provenance
    source_mode: str = "live"            # "live" | "demo" | "fallback"
    data_sources: list[str] = []        # e.g. ["OpenWeatherMap", "IMD"]