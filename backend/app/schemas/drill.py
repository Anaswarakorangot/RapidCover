from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any
from app.models.drill_session import DrillType, DrillStatus


class DrillRunRequest(BaseModel):
    drill_type: DrillType
    zone_code: str = Field(..., description="Zone code e.g. BLR-047")
    force: bool = Field(default=True, description="Bypass duration requirements")
    preset: Optional[str] = Field(default=None, description="Custom preset name, defaults to drill_type value")
    simulate_sustained_days: int = Field(default=0, description="Inject N consecutive days history for 70% payout demo (0 = disabled, 5+ triggers sustained mode)")


class DrillStartResponse(BaseModel):
    drill_id: str
    status: DrillStatus
    zone_code: str
    drill_type: DrillType
    message: str


class DrillPipelineEvent(BaseModel):
    step: str
    message: str
    ts: datetime
    metadata: Optional[dict[str, Any]] = None


class DrillStatusResponse(BaseModel):
    drill_id: str
    status: DrillStatus
    drill_type: DrillType
    zone_code: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    events_count: int = 0
    trigger_event_id: Optional[int] = None
    claims_created: int = 0


class LatencyMetrics(BaseModel):
    trigger_latency_ms: Optional[int] = None
    claim_creation_latency_ms: Optional[int] = None
    payout_latency_ms: Optional[int] = None
    total_latency_ms: Optional[int] = None


class SkippedPartner(BaseModel):
    reason: str
    count: int


class DrillImpactResponse(BaseModel):
    drill_id: str
    status: DrillStatus
    affected_partners: int
    eligible_partners: int
    claims_created: int
    claims_paid: int
    claims_pending: int
    payouts_total: float
    skipped_partners: dict[str, int]  # reason -> count
    latency_metrics: LatencyMetrics


class VerificationCheck(BaseModel):
    name: str
    status: str  # "pass", "fail", "skip"
    message: str
    latency_ms: Optional[int] = None


class VerificationResponse(BaseModel):
    overall_status: str  # "healthy", "degraded", "unhealthy"
    checks: list[VerificationCheck]
    run_at: datetime


class DrillHistoryItem(BaseModel):
    drill_id: str
    drill_type: DrillType
    zone_code: str
    status: DrillStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    claims_created: int
    total_latency_ms: Optional[int] = None

    model_config = {"from_attributes": True}


class DrillHistoryResponse(BaseModel):
    drills: list[DrillHistoryItem]
    total: int
