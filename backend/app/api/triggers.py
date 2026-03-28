"""
Trigger event API endpoints.

Public endpoints for viewing trigger events and active disruptions.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.zone import Zone
from app.models.trigger_event import TriggerEvent, TriggerType
from app.services.trigger_detector import get_active_triggers, get_all_active_triggers


router = APIRouter(prefix="/triggers", tags=["triggers"])


class TriggerResponse(BaseModel):
    id: int
    zone_id: int
    zone_name: Optional[str] = None
    zone_code: Optional[str] = None
    city: Optional[str] = None
    trigger_type: TriggerType
    severity: int
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ActiveTriggersResponse(BaseModel):
    total: int
    triggers: list[TriggerResponse]


@router.get("/active", response_model=ActiveTriggersResponse)
def get_active_disruptions(
    city: Optional[str] = None,
    zone_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Get all active trigger events (current disruptions).

    Useful for partners to see what disruptions are happening.
    """
    if zone_id:
        triggers = get_active_triggers(zone_id, db)
    else:
        triggers = get_all_active_triggers(db)

    # Enrich with zone info and filter by city if needed
    result = []
    for t in triggers:
        zone = db.query(Zone).filter(Zone.id == t.zone_id).first()

        if city and zone and zone.city.lower() != city.lower():
            continue

        result.append(TriggerResponse(
            id=t.id,
            zone_id=t.zone_id,
            zone_name=zone.name if zone else None,
            zone_code=zone.code if zone else None,
            city=zone.city if zone else None,
            trigger_type=t.trigger_type,
            severity=t.severity,
            started_at=t.started_at,
            ended_at=t.ended_at,
        ))

    return ActiveTriggersResponse(total=len(result), triggers=result)


@router.get("/{trigger_id}", response_model=TriggerResponse)
def get_trigger(trigger_id: int, db: Session = Depends(get_db)):
    """Get details of a specific trigger event."""
    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == trigger_id).first()

    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found",
        )

    zone = db.query(Zone).filter(Zone.id == trigger.zone_id).first()

    return TriggerResponse(
        id=trigger.id,
        zone_id=trigger.zone_id,
        zone_name=zone.name if zone else None,
        zone_code=zone.code if zone else None,
        city=zone.city if zone else None,
        trigger_type=trigger.trigger_type,
        severity=trigger.severity,
        started_at=trigger.started_at,
        ended_at=trigger.ended_at,
    )
