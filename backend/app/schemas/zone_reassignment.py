"""
Schemas for zone reassignment 24-hour acceptance workflow.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.zone_reassignment import ReassignmentStatus


class ZoneReassignmentProposal(BaseModel):
    """Request to propose a zone reassignment."""
    partner_id: int
    new_zone_id: int


class ZoneReassignmentResponse(BaseModel):
    """Response for a zone reassignment."""
    id: int
    partner_id: int
    old_zone_id: Optional[int]
    new_zone_id: int
    status: ReassignmentStatus
    premium_adjustment: float
    remaining_days: int
    proposed_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    hours_remaining: Optional[float] = None  # Computed field for convenience

    # Additional context
    old_zone_name: Optional[str] = None
    new_zone_name: Optional[str] = None
    partner_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ZoneReassignmentListResponse(BaseModel):
    """Response for listing zone reassignments."""
    reassignments: list[ZoneReassignmentResponse]
    total: int
    pending_count: int


class ZoneReassignmentActionResponse(BaseModel):
    """Response for accept/reject actions."""
    id: int
    status: ReassignmentStatus
    message: str
    zone_updated: bool = False
    new_zone_id: Optional[int] = None
