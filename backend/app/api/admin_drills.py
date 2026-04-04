"""
Admin Drills API - Structured drill execution and verification endpoints.

Provides:
  POST /admin/panel/drills/run          -> Start a drill, returns drill_id
  GET  /admin/panel/drills/{drill_id}   -> Get drill status
  GET  /admin/panel/drills/{drill_id}/stream -> SSE stream of pipeline events
  GET  /admin/panel/drills/{drill_id}/impact -> Get impact metrics after completion
  GET  /admin/panel/drills/history      -> List recent drills
  POST /admin/panel/verification/run    -> Run health checks
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.zone import Zone
from app.models.drill_session import DrillSession, DrillType, DrillStatus
from app.schemas.drill import (
    DrillRunRequest,
    DrillStartResponse,
    DrillStatusResponse,
    DrillPipelineEvent,
    DrillImpactResponse,
    DrillHistoryItem,
    DrillHistoryResponse,
    VerificationResponse,
    VerificationCheck,
)
from app.services.drill_service import (
    create_drill_session,
    execute_drill,
    get_drill_impact,
    get_drill_history,
    add_pipeline_event,
    DRILL_PRESETS,
)
from app.services.trigger_detector import inject_sustained_event_history
from app.models.trigger_event import TriggerType

router = APIRouter(prefix="/admin/panel", tags=["admin-drills"])


# --- POST /admin/panel/drills/run ---------------------------------------------

@router.post("/drills/run", response_model=DrillStartResponse)
def run_drill(
    req: DrillRunRequest,
    db: Session = Depends(get_db),
):
    """
    Start a structured drill execution.

    Returns immediately with drill_id. Use /drills/{drill_id}/stream for real-time
    pipeline events, or /drills/{drill_id}/impact for final metrics.
    """
    # Look up zone by code
    zone = db.query(Zone).filter(Zone.code == req.zone_code).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone not found: {req.zone_code}")

    # Determine preset name
    preset_name = req.preset or req.drill_type.value

    # Inject sustained event history for demo (to trigger 70% payout)
    if req.simulate_sustained_days >= 5:
        # Map drill_type to TriggerType
        drill_to_trigger = {
            DrillType.FLASH_FLOOD: TriggerType.RAIN,
            DrillType.AQI_SPIKE: TriggerType.AQI,
            DrillType.HEATWAVE: TriggerType.HEAT,
            DrillType.STORE_CLOSURE: TriggerType.CLOSURE,
            DrillType.CURFEW: TriggerType.SHUTDOWN,
            DrillType.MONSOON_14DAY: TriggerType.RAIN,
            DrillType.MULTI_CITY_AQI: TriggerType.AQI,
            DrillType.CYCLONE: TriggerType.RAIN,
            DrillType.BANDH: TriggerType.SHUTDOWN,
            DrillType.COLLUSION_FRAUD: TriggerType.RAIN,
        }
        trigger_type = drill_to_trigger.get(req.drill_type, TriggerType.RAIN)
        inject_sustained_event_history(zone.id, trigger_type, req.simulate_sustained_days)

    # Create drill session
    drill_session = create_drill_session(
        drill_type=req.drill_type,
        zone_id=zone.id,
        zone_code=zone.code,
        preset=preset_name,
        force=req.force,
        db=db,
    )

    # Execute drill synchronously (for now - can be made async)
    try:
        execute_drill(drill_session, zone, db)
    except Exception as e:
        # Drill failed, but we still return the drill_id so status can be checked
        pass

    db.refresh(drill_session)

    return DrillStartResponse(
        drill_id=drill_session.drill_id,
        status=drill_session.status,
        zone_code=drill_session.zone_code,
        drill_type=drill_session.drill_type,
        message=f"Drill {'completed' if drill_session.status == DrillStatus.COMPLETED else 'started'} for zone {zone.code}",
    )


# --- GET /admin/panel/drills/{drill_id} --------------------------------------

@router.get("/drills/{drill_id}", response_model=DrillStatusResponse)
def get_drill_status(
    drill_id: str,
    db: Session = Depends(get_db),
):
    """Get current status of a drill."""
    drill = db.query(DrillSession).filter(DrillSession.drill_id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    events = json.loads(drill.pipeline_events or "[]")

    return DrillStatusResponse(
        drill_id=drill.drill_id,
        status=drill.status,
        drill_type=drill.drill_type,
        zone_code=drill.zone_code,
        started_at=drill.started_at,
        completed_at=drill.completed_at,
        events_count=len(events),
        trigger_event_id=drill.trigger_event_id,
        claims_created=drill.claims_created,
    )


# --- GET /admin/panel/drills/{drill_id}/stream --------------------------------

@router.get("/drills/{drill_id}/stream")
async def stream_drill_events(
    drill_id: str,
    db: Session = Depends(get_db),
):
    """
    Stream pipeline events for a drill in NDJSON format.

    Yields events as they were recorded. If drill is already complete,
    streams all events immediately.
    """
    drill = db.query(DrillSession).filter(DrillSession.drill_id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    events = json.loads(drill.pipeline_events or "[]")

    async def event_stream():
        for event in events:
            yield json.dumps(event) + "\n"
            await asyncio.sleep(0.1)  # Small delay for visual effect

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"X-Content-Type-Options": "nosniff"},
    )


# --- GET /admin/panel/drills/{drill_id}/impact --------------------------------

@router.get("/drills/{drill_id}/impact", response_model=DrillImpactResponse)
def get_drill_impact_endpoint(
    drill_id: str,
    db: Session = Depends(get_db),
):
    """Get impact metrics for a completed drill."""
    impact = get_drill_impact(drill_id, db)
    if not impact:
        raise HTTPException(status_code=404, detail="Drill not found")
    return impact


# --- GET /admin/panel/drills/history ------------------------------------------

@router.get("/drills/history", response_model=DrillHistoryResponse)
def get_drill_history_endpoint(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent drill history."""
    drills = get_drill_history(db, limit=limit)

    items = [
        DrillHistoryItem(
            drill_id=d.drill_id,
            drill_type=d.drill_type,
            zone_code=d.zone_code,
            status=d.status,
            started_at=d.started_at,
            completed_at=d.completed_at,
            claims_created=d.claims_created,
            total_latency_ms=d.total_latency_ms,
        )
        for d in drills
    ]

    return DrillHistoryResponse(drills=items, total=len(items))


# --- GET /admin/panel/drills/presets ------------------------------------------

@router.get("/drills/presets")
def get_drill_presets():
    """Get available drill presets."""
    presets = []
    for name, config in DRILL_PRESETS.items():
        presets.append({
            "name": name,
            "trigger_type": config["trigger_type"],
            "description": config.get("description", ""),
            "conditions": config["conditions"],
        })
    return {"presets": presets}


# --- POST /admin/panel/verification/run ---------------------------------------

@router.post("/verification/run", response_model=VerificationResponse)
def run_verification(db: Session = Depends(get_db)):
    """
    Run system health verification checks.

    Checks:
    - auth_endpoint: Partner login endpoint reachable
    - zone_list: Zones endpoint returns data
    - trigger_engine: Engine status check
    - simulation: Mock APIs injectable
    - claim_creation: Claims processor available
    - payout_service: UPI/Razorpay configured
    - push_notifications: VAPID keys configured
    """
    from app.services.verification_service import run_all_checks

    checks = run_all_checks(db)

    # Determine overall status
    passed = sum(1 for c in checks if c.status == "pass")
    failed = sum(1 for c in checks if c.status == "fail")
    skipped = sum(1 for c in checks if c.status == "skip")

    if failed > 0:
        overall = "unhealthy"
    elif skipped > 2:
        overall = "degraded"
    else:
        overall = "healthy"

    return VerificationResponse(
        overall_status=overall,
        checks=checks,
        run_at=datetime.utcnow(),
    )
