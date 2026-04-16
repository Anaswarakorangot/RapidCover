from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


class ZoneResponse(BaseModel):
    id: int
    code: str
    name: str
    city: str
    risk_score: float
    is_suspended: bool = False
    dark_store_lat: Optional[float] = None
    dark_store_lng: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ZoneRiskUpdate(BaseModel):
    """Update zone risk score (called by ML service)."""
    risk_score: float


class ZoneCreate(BaseModel):
    code: str
    name: str
    city: str
    is_suspended: Optional[bool] = False
    polygon: Optional[str] = None
    dark_store_lat: Optional[float] = None
    dark_store_lng: Optional[float] = None


# =============================================================================
# Trust API Schemas (Person 1 deliverables)
# =============================================================================

class NonTriggerEvidence(BaseModel):
    """A single non-trigger measurement compared against the threshold."""
    measured_at: datetime
    trigger_type: str
    measured_value: float
    threshold: float
    unit: str
    gap: float          # how far below threshold (threshold - measured)
    source: str
    plain_reason: str   # e.g. "Rain reached 22mm/hr. Your plan triggers at 55mm/hr."


class TriggerThreshold(BaseModel):
    value: float
    unit: str
    duration: str


class TriggerEvidenceResponse(BaseModel):
    """
    GET /zones/{zone_id}/trigger-evidence
    Explains recent non-trigger cases: measured vs threshold comparisons.
    """
    zone_id: int
    zone_name: str
    checked_at: datetime
    recent_non_triggers: List[NonTriggerEvidence]
    thresholds: dict  # trigger_type -> TriggerThreshold dict
    source_health: str = "live"   # "live" | "stale" | "fallback"


class AnonymizedPayout(BaseModel):
    """A single anonymized payout record for the ledger."""
    anonymized_id: str      # e.g. "P-7f2a" — never raw partner_id
    amount: float
    trigger_type: str
    paid_at: datetime


class PayoutLedgerResponse(BaseModel):
    """
    GET /zones/{zone_id}/payout-ledger
    Anonymized proof of past payouts in a zone.
    """
    zone_id: int
    zone_name: str
    period_days: int
    total_paid: float
    total_claims: int
    affected_partners_count: int
    median_payout_time_hours: Optional[float]
    last_successful_payout_at: Optional[datetime]
    miss_rate_pct: float    # % of trigger windows with 0 claims (measurement gap)
    recent_payouts: List[AnonymizedPayout]


class ActiveTriggerSummary(BaseModel):
    trigger_type: str
    started_at: datetime


class LedgerSummary(BaseModel):
    total_paid: float
    last_payout_at: Optional[datetime]
    median_payout_hours: Optional[float]
    total_claims: int


class ZoneMapEntry(BaseModel):
    """
    GET /zones/map  —  one entry per zone.
    Frontend renders polygons + markers from this response.
    """
    id: int
    code: str
    name: str
    city: str
    risk_score: float
    density_band: str
    is_suspended: bool
    dark_store_lat: Optional[float]
    dark_store_lng: Optional[float]
    polygon: Optional[str]       # GeoJSON string
    active_trigger: Optional[ActiveTriggerSummary]
    ledger_summary: LedgerSummary
    source_health: str            # "live" | "stale" | "fallback"
    pricing_mode: str             # "trained_ml" | "fallback_rule_based"

