"""
Admin API endpoints for dashboard, simulation, and management.

Note: In production, these would require admin authentication.
For demo purposes, they are open.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.zone import Zone
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent, TriggerType
from app.schemas.zone import ZoneResponse
from app.schemas.claim import ClaimResponse
from app.data.seed_zones import seed_zones, get_zone_count
from app.services.external_apis import (
    MockWeatherAPI,
    MockAQIAPI,
    MockPlatformAPI,
    MockCivicAPI,
    reset_all_conditions,
)
from app.services.trigger_detector import detect_and_save_triggers, end_trigger, get_all_active_triggers
from app.services.claims_processor import (
    process_trigger_event,
    approve_claim,
    reject_claim,
)
from app.services.payout_service import process_payout


router = APIRouter(prefix="/admin", tags=["admin"])


# Response schemas
class DashboardStats(BaseModel):
    total_partners: int
    active_policies: int
    total_zones: int
    active_triggers: int
    pending_claims: int
    approved_claims: int
    total_paid_amount: float


class TriggerResponse(BaseModel):
    id: int
    zone_id: int
    zone_name: Optional[str] = None
    trigger_type: TriggerType
    severity: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminClaimResponse(BaseModel):
    id: int
    policy_id: int
    partner_name: Optional[str] = None
    partner_phone: Optional[str] = None
    zone_name: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    amount: float
    status: ClaimStatus
    fraud_score: float
    created_at: datetime
    paid_at: Optional[datetime] = None


# Simulation request schemas
class WeatherSimulation(BaseModel):
    zone_id: int
    temp_celsius: Optional[float] = None
    rainfall_mm_hr: Optional[float] = None
    humidity: Optional[float] = None


class AQISimulation(BaseModel):
    zone_id: int
    aqi: Optional[int] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None


class ShutdownSimulation(BaseModel):
    zone_id: int
    reason: str = "Civic shutdown - curfew in effect"


class ClosureSimulation(BaseModel):
    zone_id: int
    reason: str = "Force majeure - infrastructure issue"


class SeedResponse(BaseModel):
    zones_created: int
    total_zones: int


class ClaimActionRequest(BaseModel):
    reason: Optional[str] = None


class PayoutRequest(BaseModel):
    upi_ref: Optional[str] = None


# Dashboard endpoints
@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overall platform statistics."""
    now = datetime.utcnow()

    total_partners = db.query(func.count(Partner.id)).scalar()
    active_policies = (
        db.query(func.count(Policy.id))
        .filter(
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .scalar()
    )
    total_zones = db.query(func.count(Zone.id)).scalar()
    active_triggers = (
        db.query(func.count(TriggerEvent.id))
        .filter(TriggerEvent.ended_at.is_(None))
        .scalar()
    )
    pending_claims = (
        db.query(func.count(Claim.id))
        .filter(Claim.status == ClaimStatus.PENDING)
        .scalar()
    )
    approved_claims = (
        db.query(func.count(Claim.id))
        .filter(Claim.status == ClaimStatus.APPROVED)
        .scalar()
    )
    total_paid = (
        db.query(func.sum(Claim.amount))
        .filter(Claim.status == ClaimStatus.PAID)
        .scalar()
    ) or 0

    return DashboardStats(
        total_partners=total_partners,
        active_policies=active_policies,
        total_zones=total_zones,
        active_triggers=active_triggers,
        pending_claims=pending_claims,
        approved_claims=approved_claims,
        total_paid_amount=total_paid,
    )


# Zone endpoints
@router.get("/zones", response_model=list[ZoneResponse])
def get_all_zones(db: Session = Depends(get_db)):
    """Get all zones with risk scores."""
    return db.query(Zone).order_by(Zone.city, Zone.name).all()


@router.post("/seed", response_model=SeedResponse)
def seed_database(db: Session = Depends(get_db)):
    """Seed database with initial zone data."""
    created = seed_zones(db)
    total = get_zone_count(db)

    return SeedResponse(zones_created=len(created), total_zones=total)


# Trigger endpoints
@router.get("/triggers", response_model=list[TriggerResponse])
def get_triggers(
    active_only: bool = Query(False),
    zone_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get trigger events."""
    query = db.query(TriggerEvent)

    if active_only:
        query = query.filter(TriggerEvent.ended_at.is_(None))

    if zone_id:
        query = query.filter(TriggerEvent.zone_id == zone_id)

    triggers = (
        query
        .order_by(TriggerEvent.started_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Enrich with zone name
    result = []
    for t in triggers:
        zone = db.query(Zone).filter(Zone.id == t.zone_id).first()
        result.append(TriggerResponse(
            id=t.id,
            zone_id=t.zone_id,
            zone_name=zone.name if zone else None,
            trigger_type=t.trigger_type,
            severity=t.severity,
            started_at=t.started_at,
            ended_at=t.ended_at,
            created_at=t.created_at,
        ))

    return result


@router.post("/triggers/{trigger_id}/end")
def end_trigger_event(trigger_id: int, db: Session = Depends(get_db)):
    """Mark a trigger event as ended."""
    trigger = end_trigger(trigger_id, db)

    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found",
        )

    return {"message": "Trigger ended", "trigger_id": trigger_id}


@router.post("/triggers/{trigger_id}/process")
def process_trigger(trigger_id: int, db: Session = Depends(get_db)):
    """Process a trigger into claims for affected policies."""
    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == trigger_id).first()

    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found",
        )

    claims = process_trigger_event(trigger, db)

    return {
        "message": f"Processed trigger into {len(claims)} claims",
        "trigger_id": trigger_id,
        "claims_created": len(claims),
    }


# Claims management endpoints
@router.get("/claims", response_model=list[AdminClaimResponse])
def get_all_claims(
    status_filter: Optional[ClaimStatus] = None,
    zone_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get all claims with filtering."""
    query = db.query(Claim)

    if status_filter:
        query = query.filter(Claim.status == status_filter)

    if zone_id:
        query = query.join(TriggerEvent).filter(TriggerEvent.zone_id == zone_id)

    claims = (
        query
        .order_by(Claim.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Enrich with partner and zone info
    result = []
    for c in claims:
        policy = db.query(Policy).filter(Policy.id == c.policy_id).first()
        partner = db.query(Partner).filter(Partner.id == policy.partner_id).first() if policy else None
        trigger = db.query(TriggerEvent).filter(TriggerEvent.id == c.trigger_event_id).first()
        zone = db.query(Zone).filter(Zone.id == trigger.zone_id).first() if trigger else None

        result.append(AdminClaimResponse(
            id=c.id,
            policy_id=c.policy_id,
            partner_name=partner.name if partner else None,
            partner_phone=partner.phone if partner else None,
            zone_name=zone.name if zone else None,
            trigger_type=trigger.trigger_type if trigger else None,
            amount=c.amount,
            status=c.status,
            fraud_score=c.fraud_score,
            created_at=c.created_at,
            paid_at=c.paid_at,
        ))

    return result


@router.post("/claims/{claim_id}/approve")
def approve_claim_endpoint(
    claim_id: int,
    db: Session = Depends(get_db),
):
    """Manually approve a pending claim."""
    claim = approve_claim(claim_id, db)

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found or not pending",
        )

    return {"message": "Claim approved", "claim_id": claim_id}


@router.post("/claims/{claim_id}/reject")
def reject_claim_endpoint(
    claim_id: int,
    request: ClaimActionRequest = None,
    db: Session = Depends(get_db),
):
    """Manually reject a claim."""
    reason = request.reason if request else None
    claim = reject_claim(claim_id, db, reason)

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    return {"message": "Claim rejected", "claim_id": claim_id}


@router.post("/claims/{claim_id}/payout")
def payout_claim_endpoint(
    claim_id: int,
    request: PayoutRequest = None,
    db: Session = Depends(get_db),
):
    """Process an approved claim payout through the payout service."""
    upi_ref = request.upi_ref if request else f"UPI{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{claim_id}"
    claim = db.query(Claim).filter(Claim.id == claim_id).first()

    if not claim or claim.status != ClaimStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found or not approved",
        )

    success, payout_ref, payout_data = process_payout(claim, db, upi_ref=upi_ref)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=payout_data or {"error": "Payout processing failed"},
        )

    return {
        "message": "Claim paid",
        "claim_id": claim_id,
        "upi_ref": payout_ref,
    }


# Simulation endpoints
@router.post("/simulate/weather")
def simulate_weather(
    simulation: WeatherSimulation,
    auto_detect: bool = Query(True, description="Auto-detect and create triggers"),
    db: Session = Depends(get_db),
):
    """Set weather conditions for a zone."""
    zone = db.query(Zone).filter(Zone.id == simulation.zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    weather = MockWeatherAPI.set_conditions(
        zone_id=simulation.zone_id,
        temp_celsius=simulation.temp_celsius,
        rainfall_mm_hr=simulation.rainfall_mm_hr,
        humidity=simulation.humidity,
    )

    response = {
        "zone_id": simulation.zone_id,
        "zone_name": zone.name,
        "weather": weather.model_dump(),
        "triggers_created": [],
    }

    if auto_detect:
        triggers = detect_and_save_triggers(simulation.zone_id, db)
        response["triggers_created"] = [t.id for t in triggers]

    return response


@router.post("/simulate/aqi")
def simulate_aqi(
    simulation: AQISimulation,
    auto_detect: bool = Query(True, description="Auto-detect and create triggers"),
    db: Session = Depends(get_db),
):
    """Set AQI conditions for a zone."""
    zone = db.query(Zone).filter(Zone.id == simulation.zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    aqi = MockAQIAPI.set_conditions(
        zone_id=simulation.zone_id,
        aqi=simulation.aqi,
        pm25=simulation.pm25,
        pm10=simulation.pm10,
    )

    response = {
        "zone_id": simulation.zone_id,
        "zone_name": zone.name,
        "aqi": aqi.model_dump(),
        "triggers_created": [],
    }

    if auto_detect:
        triggers = detect_and_save_triggers(simulation.zone_id, db)
        response["triggers_created"] = [t.id for t in triggers]

    return response


@router.post("/simulate/shutdown")
def simulate_shutdown(
    simulation: ShutdownSimulation,
    auto_detect: bool = Query(True, description="Auto-detect and create triggers"),
    db: Session = Depends(get_db),
):
    """Trigger a civic shutdown for a zone."""
    zone = db.query(Zone).filter(Zone.id == simulation.zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    shutdown = MockCivicAPI.set_shutdown(
        zone_id=simulation.zone_id,
        reason=simulation.reason,
    )

    response = {
        "zone_id": simulation.zone_id,
        "zone_name": zone.name,
        "shutdown": shutdown.model_dump(),
        "triggers_created": [],
    }

    if auto_detect:
        triggers = detect_and_save_triggers(simulation.zone_id, db)
        response["triggers_created"] = [t.id for t in triggers]

    return response


@router.post("/simulate/closure")
def simulate_closure(
    simulation: ClosureSimulation,
    auto_detect: bool = Query(True, description="Auto-detect and create triggers"),
    db: Session = Depends(get_db),
):
    """Trigger a dark store closure for a zone."""
    zone = db.query(Zone).filter(Zone.id == simulation.zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    closure = MockPlatformAPI.set_store_closed(
        zone_id=simulation.zone_id,
        reason=simulation.reason,
    )

    response = {
        "zone_id": simulation.zone_id,
        "zone_name": zone.name,
        "platform_status": closure.model_dump(),
        "triggers_created": [],
    }

    if auto_detect:
        triggers = detect_and_save_triggers(simulation.zone_id, db)
        response["triggers_created"] = [t.id for t in triggers]

    return response


@router.post("/simulate/clear/{zone_id}")
def clear_zone_conditions(zone_id: int, db: Session = Depends(get_db)):
    """Clear all simulated conditions for a zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    # Reset all conditions for this zone
    MockWeatherAPI.set_conditions(zone_id, temp_celsius=32.0, rainfall_mm_hr=0.0, humidity=60.0)
    MockAQIAPI.set_conditions(zone_id, aqi=150, pm25=55.0, pm10=85.0)
    MockPlatformAPI.set_store_open(zone_id)
    MockCivicAPI.clear_shutdown(zone_id)

    return {
        "message": f"Conditions cleared for zone {zone.name}",
        "zone_id": zone_id,
    }


# Auto-renewal endpoint
@router.post("/process-auto-renewals")
def process_auto_renewals_endpoint(db: Session = Depends(get_db)):
    """
    Process auto-renewals for all eligible policies.

    Finds policies where:
    - auto_renew = True
    - Expiring within 24 hours OR in grace period
    - Not already renewed

    Creates new renewal policies with 5% loyalty discount.
    In production, this would run as a scheduled job (e.g., hourly).
    """
    from app.services.policy_lifecycle import process_auto_renewals

    results = process_auto_renewals(db)

    renewed_count = sum(1 for r in results if r.get("status") == "renewed")
    failed_count = sum(1 for r in results if r.get("status") == "failed")

    return {
        "message": f"Auto-renewal processing complete",
        "total_processed": len(results),
        "renewed": renewed_count,
        "failed": failed_count,
        "details": results,
    }


@router.post("/simulate/reset")
def reset_all_simulations():
    """Reset all simulated conditions across all zones."""
    reset_all_conditions()

    return {"message": "All simulated conditions reset"}
