from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


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


class TriggerEvidenceResponse(BaseModel):
    """Evidence of why a trigger DID or DID NOT fire."""
    zone_id: int
    metric_name: str              # e.g. "Rainfall Rate"
    current_value: float          # e.g. 22.0
    threshold_value: float        # e.g. 30.0
    trigger_type: str
    is_active: bool
    source_health: str            # "Healthy", "Degraded", "Stale"
    last_updated: datetime
    message: str                  # "Rain reached 22mm/hr. Your plan triggers at 30mm/hr."


class PayoutLedgerEntry(BaseModel):
    amount: float
    paid_at: datetime
    payout_time_mins: int


class PayoutLedgerResponse(BaseModel):
    """Trust building recent payout data for a zone."""
    zone_id: int
    recent_payouts: List[PayoutLedgerEntry]
    median_payout_time_mins: int
    total_paid_this_month: float
    total_paid_this_week: float
    miss_rate_disclosure: float   # e.g. 0.02 (2% rejected)
    last_payout_at: Optional[datetime]


class ZoneMapPolygon(BaseModel):
    zone_id: int
    zone_name: str
    coordinates: List[List[float]] # List of [lat, lng]
    color: str                    # Hex base on risk
    is_active: bool
    is_suspended: bool


class ZoneMapMarker(BaseModel):
    id: str
    type: str                     # "dark_store", "trigger"
    lat: float
    lng: float
    label: str


class ZoneMapResponse(BaseModel):
    """Full map state for Leaflet rendering."""
    polygons: List[ZoneMapPolygon]
    markers: List[ZoneMapMarker]
    center: Optional[List[float]] = None # [lat, lng]
    zoom: Optional[int] = None
    risk_color_layer: str         # "density", "risk", "status"
    fetched_at: datetime
