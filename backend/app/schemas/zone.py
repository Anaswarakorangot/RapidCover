from pydantic import BaseModel
from datetime import datetime
from typing import Optional


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
