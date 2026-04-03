"""
Schemas for RIQI (Road Infrastructure Quality Index) provenance APIs.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RiqiInputMetrics(BaseModel):
    """Input metrics used to calculate RIQI score."""
    historical_suspensions: int
    closure_frequency: float
    weather_severity_freq: float
    aqi_severity_freq: float
    zone_density: float


class RiqiProvenanceResponse(BaseModel):
    """Full RIQI provenance response for a zone."""
    zone_id: int
    zone_code: str
    zone_name: str
    city: str
    riqi_score: float
    riqi_band: str  # urban_core | urban_fringe | peri_urban
    payout_multiplier: float
    premium_adjustment: float
    input_metrics: RiqiInputMetrics
    calculated_from: str  # seeded | computed | fallback_city_default
    last_updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RiqiListResponse(BaseModel):
    """Response for listing all zone RIQI profiles."""
    zones: list[RiqiProvenanceResponse]
    total: int
    data_source: str  # "database" | "mixed"


class RiqiRecomputeResponse(BaseModel):
    """Response after recomputing RIQI for a zone."""
    zone_code: str
    old_riqi_score: float
    new_riqi_score: float
    old_band: str
    new_band: str
    recomputed_at: datetime
    metrics_used: RiqiInputMetrics
