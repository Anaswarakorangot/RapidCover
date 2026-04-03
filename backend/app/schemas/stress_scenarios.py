"""
Schemas for stress scenario calculations.

Stress scenarios model potential disaster impacts and calculate
the reserve needed to cover projected claims.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StressScenarioResponse(BaseModel):
    """Response for a single stress scenario calculation."""
    scenario_id: str
    scenario_name: str
    days: int
    projected_claims: int
    projected_payout: float
    city_reserve_available: float
    reserve_needed: float  # max(projected_payout - city_reserve_available, 0)
    formula_breakdown: dict
    assumptions: list[str]
    data_source: str  # "live" | "seeded" | "mock"


class StressScenarioListResponse(BaseModel):
    """Response for list of all stress scenarios."""
    scenarios: list[StressScenarioResponse]
    computed_at: datetime
    total_reserve_needed: float


class StressCityMetrics(BaseModel):
    """City-level metrics used in stress calculations."""
    city: str
    active_policies: int
    avg_weekly_premium: float
    total_weekly_reserve: float
    zone_count: int
