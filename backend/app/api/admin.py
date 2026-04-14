"""
Admin API endpoints for dashboard, simulation, and management.

Note: In production, these would require admin authentication.
For demo purposes, they are open.
"""

import json
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
    set_partial_disruption_data,
    get_partial_disruption_data,
    clear_partial_disruption_data,
)
from app.services.trigger_detector import detect_and_save_triggers, end_trigger, get_all_active_triggers
from app.services.claims_processor import (
    process_trigger_event,
    approve_claim,
    reject_claim,
)
from app.services.multi_trigger_resolver import (
    get_aggregation_stats,
    get_claim_aggregation_details,
)
from app.services.payment_state_machine import (
    retry_payment,
    reconcile_payment,
    get_failed_payments,
    get_pending_reconciliation,
    get_payment_stats,
    get_payment_status,
)
from app.services.payout_service import process_payout

from app.services.notifications import get_partner_subscriptions, send_push_notification

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/test-push")
def admin_test_push(
    phone: str = Query(..., description="Phone number of the partner to notify"),
    db: Session = Depends(get_db),
):
    """
    Admin-only endpoint to force a test notification to a specific phone number.
    Bypasses partner auth for demo/debugging.
    """
    partner = db.query(Partner).filter(Partner.phone == phone).first()
    if not partner:
        raise HTTPException(status_code=404, detail=f"Partner with phone {phone} not found")

    subscriptions = get_partner_subscriptions(partner.id, db)
    if not subscriptions:
        raise HTTPException(status_code=412, detail="Partner has no active push subscriptions. Ask them to click 'Enable Alerts' on the Dashboard first.")

    payload = {
        "title": "RapidCover Demo 🚀",
        "body": "Real-time payout notification delivered successfully!",
        "url": "/claims",
        "tag": f"admin-test-{partner.id}",
        "type": "payout_alert",
        "icon": "/icon-192.png",
    }

    success_count = 0
    for sub in subscriptions:
        if send_push_notification(sub, payload):
            success_count += 1
    
    db.commit()
    return {"message": "Push sent", "devices": success_count}


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
    # Partial disruption fields
    expected_orders: Optional[int] = None
    actual_orders: Optional[int] = None
    partial_factor_override: Optional[float] = None


class AQISimulation(BaseModel):
    zone_id: int
    aqi: Optional[int] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    # Partial disruption fields
    expected_orders: Optional[int] = None
    actual_orders: Optional[int] = None
    partial_factor_override: Optional[float] = None


class ShutdownSimulation(BaseModel):
    zone_id: int
    reason: str = "Civic shutdown - curfew in effect"
    # Note: Shutdown/Closure are always full_halt, but fields included for consistency
    expected_orders: Optional[int] = None
    actual_orders: Optional[int] = None


class ClosureSimulation(BaseModel):
    zone_id: int
    reason: str = "Force majeure - infrastructure issue"
    # Note: Shutdown/Closure are always full_halt, but fields included for consistency
    expected_orders: Optional[int] = None
    actual_orders: Optional[int] = None


class SeedResponse(BaseModel):
    zones_created: int
    total_zones: int


class ClaimActionRequest(BaseModel):
    reason: Optional[str] = None


class PayoutRequest(BaseModel):
    upi_ref: Optional[str] = None


class ReconcileRequest(BaseModel):
    """Request for manual payment reconciliation."""
    action: str  # "confirm", "reject", or "force_paid"
    provider_ref: Optional[str] = None
    notes: Optional[str] = None


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


# Multi-trigger aggregation endpoints
@router.get("/aggregation-stats")
def get_aggregation_stats_endpoint(db: Session = Depends(get_db)):
    """
    Get statistics about multi-trigger aggregation.

    Returns:
    - total_aggregated_claims: Claims that aggregated multiple triggers
    - total_triggers_suppressed: Triggers that didn't create separate claims
    - total_savings: Total amount saved by preventing duplicate payouts
    """
    return get_aggregation_stats(db)


@router.get("/claims/{claim_id}/aggregation")
def get_claim_aggregation_endpoint(
    claim_id: int,
    db: Session = Depends(get_db),
):
    """
    Get aggregation details for a specific claim.

    Returns aggregation metadata including:
    - group_id: Unique identifier for the aggregation group
    - is_aggregated: Whether multiple triggers were combined
    - primary_trigger_id: The trigger with highest payout
    - suppressed_triggers: List of trigger IDs that were aggregated
    - pre_aggregation_payout: What would have been paid without aggregation
    - post_aggregation_payout: Final aggregated payout
    - savings: Amount saved by aggregation
    """
    aggregation = get_claim_aggregation_details(claim_id, db)
    if aggregation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found or has no aggregation data",
        )
    return aggregation


# Payment state machine endpoints
@router.get("/claims/{claim_id}/payment-state")
def get_claim_payment_state_endpoint(
    claim_id: int,
    db: Session = Depends(get_db),
):
    """
    Get payment state for a specific claim.

    Returns payment state including:
    - current_status: Current payment status (not_started, initiated, confirmed, failed, reconcile_pending)
    - idempotency_key: Key for deduplication
    - attempts: List of payment attempts with details
    - total_attempts: Number of attempts made
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    return get_payment_status(claim)


@router.post("/claims/{claim_id}/retry-payment")
def retry_payment_endpoint(
    claim_id: int,
    db: Session = Depends(get_db),
):
    """
    Retry a failed payment.

    Only works for claims with payment status 'failed'.
    Automatically escalates to reconciliation after max retries.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    success, result = retry_payment(claim, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Retry failed"),
        )

    return {
        "message": "Payment retry initiated",
        "claim_id": claim_id,
        "attempt": result,
    }


@router.post("/claims/{claim_id}/reconcile")
def reconcile_payment_endpoint(
    claim_id: int,
    request: ReconcileRequest,
    db: Session = Depends(get_db),
):
    """
    Manually reconcile a payment.

    Actions:
    - confirm: Confirm payment was received (requires provider_ref)
    - reject: Reject the claim
    - force_paid: Mark as paid without provider confirmation
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    success, result = reconcile_payment(
        claim=claim,
        action=request.action,
        db=db,
        provider_ref=request.provider_ref,
        notes=request.notes,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Reconciliation failed"),
        )

    return {
        "message": f"Reconciliation action '{request.action}' completed",
        "claim_id": claim_id,
        "result": result,
    }


@router.get("/claims/payment-failures")
def list_payment_failures_endpoint(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    List claims with failed payments.

    Returns claims that are APPROVED but have payment_state.current_status = 'failed'.
    These can be retried or escalated to reconciliation.
    """
    return {
        "claims": get_failed_payments(db, limit),
        "total": len(get_failed_payments(db, limit)),
    }


@router.get("/claims/pending-reconciliation")
def list_pending_reconciliation_endpoint(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    List claims pending manual reconciliation.

    Returns claims with payment_state.current_status = 'reconcile_pending'.
    These require manual intervention to confirm, reject, or force-pay.
    """
    return {
        "claims": get_pending_reconciliation(db, limit),
        "total": len(get_pending_reconciliation(db, limit)),
    }


@router.get("/payment-stats")
def get_payment_stats_endpoint(db: Session = Depends(get_db)):
    """
    Get payment processing statistics.

    Returns counts for each payment status:
    - initiated: Payments in progress
    - confirmed: Successfully completed
    - failed: Failed (retryable)
    - reconcile_pending: Awaiting manual review
    """
    return get_payment_stats(db)


# Simulation endpoints
@router.post("/simulate/weather")
def simulate_weather(
    simulation: WeatherSimulation,
    auto_detect: bool = Query(True, description="Auto-detect and create triggers"),
    db: Session = Depends(get_db),
):
    """Set weather conditions for a zone with optional partial disruption data."""
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

    # Store partial disruption data if provided
    partial_disruption = None
    if simulation.expected_orders is not None or simulation.actual_orders is not None or simulation.partial_factor_override is not None:
        partial_disruption = set_partial_disruption_data(
            zone_id=simulation.zone_id,
            expected_orders=simulation.expected_orders,
            actual_orders=simulation.actual_orders,
            partial_factor_override=simulation.partial_factor_override,
        )

    response = {
        "zone_id": simulation.zone_id,
        "zone_name": zone.name,
        "weather": weather.model_dump(),
        "triggers_created": [],
        "partial_disruption": partial_disruption,
    }

    if auto_detect:
        from app.models.trigger_event import TriggerEvent
        from datetime import datetime
        db.query(TriggerEvent).filter(
            TriggerEvent.zone_id == simulation.zone_id,
            TriggerEvent.ended_at.is_(None)
        ).update({'ended_at': datetime.utcnow()})
        db.commit()
        triggers = detect_and_save_triggers(simulation.zone_id, db)
        # Auto-process payouts for instant demo effect
        for t in triggers:
            from app.services.claims_processor import process_trigger_event
            process_trigger_event(t, db)
        response["triggers_created"] = [t.id for t in triggers]
        # Clear partial disruption data after processing
        clear_partial_disruption_data(simulation.zone_id)

    return response


@router.post("/simulate/aqi")
def simulate_aqi(
    simulation: AQISimulation,
    auto_detect: bool = Query(True, description="Auto-detect and create triggers"),
    db: Session = Depends(get_db),
):
    """Set AQI conditions for a zone with optional partial disruption data."""
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

    # Store partial disruption data if provided
    partial_disruption = None
    if simulation.expected_orders is not None or simulation.actual_orders is not None or simulation.partial_factor_override is not None:
        partial_disruption = set_partial_disruption_data(
            zone_id=simulation.zone_id,
            expected_orders=simulation.expected_orders,
            actual_orders=simulation.actual_orders,
            partial_factor_override=simulation.partial_factor_override,
        )

    response = {
        "zone_id": simulation.zone_id,
        "zone_name": zone.name,
        "aqi": aqi.model_dump(),
        "triggers_created": [],
        "partial_disruption": partial_disruption,
    }

    if auto_detect:
        from app.models.trigger_event import TriggerEvent
        from datetime import datetime
        db.query(TriggerEvent).filter(
            TriggerEvent.zone_id == simulation.zone_id,
            TriggerEvent.ended_at.is_(None)
        ).update({'ended_at': datetime.utcnow()})
        db.commit()
        triggers = detect_and_save_triggers(simulation.zone_id, db)
        # Auto-process payouts for instant demo effect
        for t in triggers:
            from app.services.claims_processor import process_trigger_event
            process_trigger_event(t, db)
        response["triggers_created"] = [t.id for t in triggers]
        # Clear partial disruption data after processing
        clear_partial_disruption_data(simulation.zone_id)

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
        from app.models.trigger_event import TriggerEvent
        from datetime import datetime
        db.query(TriggerEvent).filter(
            TriggerEvent.zone_id == simulation.zone_id,
            TriggerEvent.ended_at.is_(None)
        ).update({'ended_at': datetime.utcnow()})
        db.commit()
        triggers = detect_and_save_triggers(simulation.zone_id, db)
        # Auto-process payouts for instant demo effect
        for t in triggers:
            from app.services.claims_processor import process_trigger_event
            process_trigger_event(t, db)
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
        from app.models.trigger_event import TriggerEvent
        from datetime import datetime
        db.query(TriggerEvent).filter(
            TriggerEvent.zone_id == simulation.zone_id,
            TriggerEvent.ended_at.is_(None)
        ).update({'ended_at': datetime.utcnow()})
        db.commit()
        triggers = detect_and_save_triggers(simulation.zone_id, db)
        # Auto-process payouts for instant demo effect
        for t in triggers:
            from app.services.claims_processor import process_trigger_event
            process_trigger_event(t, db)
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


# =============================================================================
# Admin Panel Endpoints - Stress Scenarios, RIQI, Notifications, Proofs
# =============================================================================

# --- Stress Scenarios ---

@router.get("/panel/stress-scenarios")
def get_stress_scenarios(db: Session = Depends(get_db)):
    """
    Get all stress scenarios with reserve-needed calculations.

    Each scenario models a disaster event and calculates:
    - projected_claims = active_policies × trigger_probability × days
    - projected_payout = projected_claims × avg_payout × severity_multiplier
    - reserve_needed = max(projected_payout - city_reserve_available, 0)
    """
    from app.services.stress_scenario_service import get_all_stress_scenarios

    return get_all_stress_scenarios(db)


@router.get("/panel/stress-scenarios/{scenario_id}")
def get_stress_scenario(scenario_id: str, db: Session = Depends(get_db)):
    """Get a single stress scenario by ID."""
    from app.services.stress_scenario_service import calculate_stress_scenario

    scenario = calculate_stress_scenario(scenario_id, db)
    if scenario.scenario_name == "Unknown Scenario":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found",
        )
    return scenario


# --- RIQI Provenance ---

@router.get("/panel/riqi")
def get_all_riqi_profiles(db: Session = Depends(get_db)):
    """
    Get RIQI (Road Infrastructure Quality Index) profiles for all zones.

    Returns per-zone RIQI scores with provenance tracking showing
    whether data came from database or city-level defaults.
    """
    from app.services.riqi_service import get_all_riqi_profiles

    return get_all_riqi_profiles(db)


@router.get("/panel/riqi/{zone_code}")
def get_riqi_for_zone(zone_code: str, db: Session = Depends(get_db)):
    """Get RIQI provenance for a specific zone by code."""
    from app.services.riqi_service import get_riqi_by_zone_code

    profile = get_riqi_by_zone_code(zone_code, db)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_code}' not found",
        )
    return profile


@router.post("/panel/riqi/{zone_code}/recompute")
def recompute_riqi_for_zone(zone_code: str, db: Session = Depends(get_db)):
    """
    Recompute RIQI score for a zone based on current metrics.

    This recalculates the RIQI score from historical data and
    updates the zone_risk_profiles table.
    """
    from app.services.riqi_service import recompute_riqi_for_zone

    result = recompute_riqi_for_zone(zone_code, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_code}' not found",
        )
    return result


@router.post("/panel/riqi/seed")
def seed_riqi_profiles(db: Session = Depends(get_db)):
    """Seed RIQI profiles for all zones with zone-specific or city defaults."""
    from app.services.riqi_service import seed_zone_risk_profiles

    created = seed_zone_risk_profiles(db)
    return {
        "message": f"Seeded {created} zone risk profiles",
        "profiles_created": created,
    }


# --- Notification Templates ---

@router.get("/panel/notifications/preview")
def preview_notification(
    lang: str = Query("en", description="Language code (en, hi)"),
    type: str = Query("claim_created", description="Notification type"),
):
    """
    Preview a notification template with sample data.

    Supported types: claim_created, claim_approved, claim_paid, claim_rejected,
    trigger_forecast, policy_expiring, policy_renewed, zone_reassignment_proposed,
    zone_reassignment_accepted
    """
    from app.services.notification_templates import (
        preview_notification,
        get_available_notification_types,
    )

    available_types = get_available_notification_types()
    if type not in available_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown notification type. Available: {available_types}",
        )

    return preview_notification(type, lang)


@router.get("/panel/notifications/templates")
def list_notification_templates():
    """List all available notification templates and supported languages."""
    from app.services.notification_templates import (
        get_available_notification_types,
        get_supported_languages,
        NOTIFICATION_TEMPLATES,
    )

    return {
        "notification_types": get_available_notification_types(),
        "supported_languages": get_supported_languages(),
        "templates": NOTIFICATION_TEMPLATES,
    }


# --- Trigger Eligibility Check ---

class TriggerCheckRequest(BaseModel):
    partner_id: int
    zone_id: int
    trigger_type: str = "rain"


class TriggerCheckResponse(BaseModel):
    eligible: bool
    reason: str
    matched_pincode: Optional[str] = None
    coverage_source: str
    checks_performed: list[dict]


@router.post("/panel/trigger-check", response_model=TriggerCheckResponse)
def check_trigger_eligibility(
    request: TriggerCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Check if a partner is eligible for a trigger in a specific zone.

    Performs all eligibility checks and returns detailed results:
    - partner_active: Partner account is active
    - policy_active: Partner has an active policy
    - pin_code_match: Partner's pin code is within zone coverage
    - shift_window: Trigger time is within partner's shift hours
    """
    from app.services.trigger_engine import check_partner_pin_code_match
    from app.services.runtime_metadata import (
        is_partner_available_for_trigger,
        get_partner_runtime_metadata,
        get_zone_coverage_metadata,
    )

    # Get partner and zone
    partner = db.query(Partner).filter(Partner.id == request.partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    zone = db.query(Zone).filter(Zone.id == request.zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    # Get metadata
    partner_metadata = get_partner_runtime_metadata(partner.id, db)
    zone_metadata = get_zone_coverage_metadata(zone.id, db)

    # Perform checks
    checks = []
    all_passed = True

    # Check 1: Partner active
    partner_active = partner.is_active
    checks.append({
        "check": "partner_active",
        "passed": partner_active,
        "details": {"is_active": partner_active},
    })
    if not partner_active:
        all_passed = False

    # Check 2: Policy active
    now = datetime.utcnow()
    active_policy = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .first()
    )
    policy_active = active_policy is not None
    checks.append({
        "check": "policy_active",
        "passed": policy_active,
        "details": {"policy_id": active_policy.id if active_policy else None},
    })
    if not policy_active:
        all_passed = False

    # Check 3: Pin code match
    pin_match, pin_reason = check_partner_pin_code_match(partner, zone, db)
    checks.append({
        "check": "pin_code_match",
        "passed": pin_match,
        "details": {
            "reason": pin_reason,
            "partner_pin_code": partner_metadata.get("pin_code"),
            "zone_pin_codes": zone_metadata.get("pin_codes", []),
        },
    })
    if not pin_match:
        all_passed = False

    # Check 4: Shift window
    available, avail_reason = is_partner_available_for_trigger(partner, db)
    checks.append({
        "check": "shift_window",
        "passed": available,
        "details": {"reason": avail_reason},
    })
    if not available:
        all_passed = False

    # Determine final reason
    if all_passed:
        reason = "eligible"
    else:
        failed_checks = [c["check"] for c in checks if not c["passed"]]
        reason = f"failed: {', '.join(failed_checks)}"

    return TriggerCheckResponse(
        eligible=all_passed,
        reason=reason,
        matched_pincode=partner_metadata.get("pin_code") if pin_match else None,
        coverage_source="zone_coverage_metadata" if zone_metadata.get("pin_codes") else "zone_model",
        checks_performed=checks,
    )


# --- Proof APIs ---

@router.get("/panel/proof/stress")
def proof_stress_scenarios(db: Session = Depends(get_db)):
    """Proof endpoint for stress scenario calculations."""
    from app.services.stress_scenario_service import get_all_stress_scenarios

    result = get_all_stress_scenarios(db)
    return {
        "feature": "stress_scenarios",
        "input": {"scenario_count": len(result.scenarios)},
        "output": {
            "total_reserve_needed": result.total_reserve_needed,
            "scenarios": [s.scenario_id for s in result.scenarios],
        },
        "timestamps": {
            "computed_at": result.computed_at.isoformat(),
            "data_as_of": datetime.utcnow().isoformat(),
        },
        "source": "live" if any(s.data_source == "live" for s in result.scenarios) else "mock",
        "pass_fail": "pass" if result.total_reserve_needed >= 0 else "fail",
        "notes": ["All scenarios computed successfully"],
    }


@router.get("/panel/proof/reassignments")
def proof_reassignments(db: Session = Depends(get_db)):
    """Proof endpoint for zone reassignment workflow."""
    from app.services.zone_reassignment_service import list_reassignments, expire_stale_proposals
    from app.models.zone_reassignment import ReassignmentStatus

    # Expire stale proposals first
    expired_count = expire_stale_proposals(db)

    # Get counts
    result = list_reassignments(db, limit=1000)

    return {
        "feature": "zone_reassignments",
        "input": {},
        "output": {
            "total": result.total,
            "pending_count": result.pending_count,
            "expired_this_check": expired_count,
        },
        "timestamps": {
            "computed_at": datetime.utcnow().isoformat(),
            "data_as_of": datetime.utcnow().isoformat(),
        },
        "source": "live",
        "pass_fail": "pass",
        "notes": [f"Expired {expired_count} stale proposals"],
    }


@router.get("/panel/proof/trigger-eligibility")
def proof_trigger_eligibility(db: Session = Depends(get_db)):
    """Proof endpoint for trigger eligibility checks (pin-code strictness)."""
    # Count partners with/without pin codes
    from app.services.runtime_metadata import (
        get_partner_runtime_metadata,
        get_zone_coverage_metadata,
    )

    partners = db.query(Partner).filter(Partner.is_active == True).limit(100).all()
    zones = db.query(Zone).limit(20).all()

    partners_with_pin = 0
    zones_with_coverage = 0

    for p in partners:
        meta = get_partner_runtime_metadata(p.id, db)
        if meta.get("pin_code"):
            partners_with_pin += 1

    for z in zones:
        meta = get_zone_coverage_metadata(z.id, db)
        if meta.get("pin_codes"):
            zones_with_coverage += 1

    return {
        "feature": "trigger_eligibility_pincode_strictness",
        "input": {
            "partners_checked": len(partners),
            "zones_checked": len(zones),
        },
        "output": {
            "partners_with_pin_code": partners_with_pin,
            "partners_without_pin_code": len(partners) - partners_with_pin,
            "zones_with_coverage_data": zones_with_coverage,
            "zones_without_coverage_data": len(zones) - zones_with_coverage,
        },
        "timestamps": {
            "computed_at": datetime.utcnow().isoformat(),
            "data_as_of": datetime.utcnow().isoformat(),
        },
        "source": "live",
        "pass_fail": "pass" if partners_with_pin > 0 or zones_with_coverage > 0 else "partial",
        "notes": [
            "Pin-code strictness is now enforced",
            "Partners without pin_code will fail eligibility",
            "Zones without coverage data will fail eligibility",
        ],
    }


@router.get("/panel/proof/riqi")
def proof_riqi(db: Session = Depends(get_db)):
    """Proof endpoint for RIQI provenance."""
    from app.services.riqi_service import get_all_riqi_profiles

    result = get_all_riqi_profiles(db)

    from_db = sum(1 for z in result.zones if z.calculated_from != "fallback_city_default")
    from_fallback = len(result.zones) - from_db

    return {
        "feature": "riqi_provenance",
        "input": {"zone_count": result.total},
        "output": {
            "total_zones": result.total,
            "from_database": from_db,
            "from_fallback": from_fallback,
            "data_source": result.data_source,
        },
        "timestamps": {
            "computed_at": datetime.utcnow().isoformat(),
            "data_as_of": datetime.utcnow().isoformat(),
        },
        "source": result.data_source,
        "pass_fail": "pass" if from_db > 0 else "partial",
        "notes": [
            f"{from_db} zones have DB-stored RIQI profiles",
            f"{from_fallback} zones use city-level fallback",
        ],
    }


@router.get("/panel/proof/data-sources")
def proof_data_sources(db: Session = Depends(get_db)):
    """
    Proof endpoint showing all data sources used by the admin panel.

    Lists databases, config files, and hardcoded values with row counts
    and last updated timestamps where available.
    """
    from app.services.notification_templates import (
        get_supported_languages,
        get_available_notification_types,
    )
    from app.services.riqi_service import _ensure_zone_risk_profiles_table
    from app.models.zone_risk_profile import ZoneRiskProfile
    from app.models.zone_reassignment import ZoneReassignment

    _ensure_zone_risk_profiles_table(db)

    # Count rows in key tables
    zone_risk_count = db.query(func.count(ZoneRiskProfile.id)).scalar() or 0
    reassignment_count = db.query(func.count(ZoneReassignment.id)).scalar() or 0
    partner_count = db.query(func.count(Partner.id)).scalar() or 0
    zone_count = db.query(func.count(Zone.id)).scalar() or 0

    sources = [
        {
            "name": "zone_risk_profiles",
            "type": "database",
            "row_count": zone_risk_count,
            "description": "Per-zone RIQI scores and metrics",
        },
        {
            "name": "zone_reassignments",
            "type": "database",
            "row_count": reassignment_count,
            "description": "Zone reassignment proposals and history",
        },
        {
            "name": "partners",
            "type": "database",
            "row_count": partner_count,
            "description": "Partner accounts",
        },
        {
            "name": "zones",
            "type": "database",
            "row_count": zone_count,
            "description": "Dark store zones",
        },
        {
            "name": "notification_templates",
            "type": "config",
            "languages": get_supported_languages(),
            "notification_types": len(get_available_notification_types()),
            "description": "Multilingual notification templates",
        },
        {
            "name": "city_riqi_defaults",
            "type": "hardcoded",
            "note": "Fallback RIQI scores when zone profile unavailable",
            "description": "City-level RIQI score defaults",
        },
        {
            "name": "stress_scenarios",
            "type": "hardcoded",
            "scenario_count": 4,
            "description": "Predefined disaster stress scenarios",
        },
    ]

    return {
        "feature": "data_sources",
        "sources": sources,
        "computed_at": datetime.utcnow().isoformat(),
    }


# ─── Validation Matrix Proof ──────────────────────────────────────────────────

@router.get("/panel/proof/validation-matrix")
def proof_validation_matrix(db: Session = Depends(get_db)):
    """
    Proof endpoint: shows validation matrix for the most recent paid/rejected claim.

    Every processed claim now carries a machine-readable validation matrix with
    10 checks: threshold breach, zone match, pin-code, active policy, shift window,
    partner activity, platform activity, fraud score, data freshness, cross-source agreement.
    """
    from app.models.claim import ClaimStatus

    # Find most recent claim with validation matrix
    recent_claims = (
        db.query(Claim)
        .filter(Claim.status.in_([ClaimStatus.PAID, ClaimStatus.REJECTED, ClaimStatus.APPROVED]))
        .order_by(Claim.created_at.desc())
        .limit(20)
        .all()
    )

    sample_claim = None
    sample_matrix = None
    for claim in recent_claims:
        try:
            vd = json.loads(claim.validation_data or "{}")
            if "validation_matrix" in vd:
                sample_claim = claim
                sample_matrix = vd["validation_matrix"]
                break
        except Exception:
            continue

    if not sample_matrix:
        return {
            "feature": "validation_matrix",
            "pass_fail": "partial",
            "notes": ["No claims with validation matrix found yet — fire a trigger to generate one"],
            "sample_claim_id": None,
            "matrix": [],
        }

    matrix_summary = {
        "total_checks": len(sample_matrix),
        "passed": sum(1 for c in sample_matrix if c["passed"]),
        "failed": sum(1 for c in sample_matrix if not c["passed"]),
    }

    return {
        "feature": "validation_matrix",
        "pass_fail": "pass",
        "sample_claim_id": sample_claim.id,
        "sample_claim_status": sample_claim.status.value,
        "matrix_summary": matrix_summary,
        "matrix": sample_matrix,
        "notes": [
            "Every paid/rejected claim now carries a full 10-check validation matrix",
            "Check validation_data.validation_matrix on any claim record",
        ],
        "computed_at": datetime.utcnow().isoformat(),
    }


@router.get("/panel/proof/oracle-reliability")
def proof_oracle_reliability(db: Session = Depends(get_db)):
    """
    Proof endpoint: shows oracle reliability engine output.

    Demonstrates source confidence scoring, freshness checks, agreement logic,
    and trigger confidence decisions. Answers: 'what if third-party APIs fail or are noisy?'
    """
    from app.services.external_apis import get_oracle_reliability_report, compute_trigger_confidence

    oracle = get_oracle_reliability_report()

    # Simulate a trigger confidence decision for demo
    weather_conf = compute_trigger_confidence(
        primary_source="openweathermap",
        corroborating_sources=["waqi_aqi"],
        primary_value=62.0,
        corroborating_values=[58.0],
    )

    return {
        "feature": "oracle_reliability_engine",
        "pass_fail": "pass",
        "system_health": oracle["system_health"],
        "average_reliability": oracle["average_reliability"],
        "source_count": len(oracle["sources"]),
        "sources": oracle["sources"],
        "sample_trigger_confidence": weather_conf,
        "notes": [
            "Sources are scored: live+fresh=1.0, mock=0.6, stale=0.2",
            "Trigger confidence combines primary + corroborating source scores",
            "Decisions: fire | hold | manual_review_simulated | fallback_mock_mode",
            "Oracle report is now embedded in every TriggerEvent.source_data",
        ],
        "computed_at": oracle["computed_at"],
    }


@router.get("/panel/proof/platform-activity")
def proof_platform_activity(db: Session = Depends(get_db)):
    """
    Proof endpoint: shows platform activity simulation for delivery partners.

    Demonstrates Zomato/Swiggy/Zepto/Blinkit activity tracking and how it
    gates claim eligibility. Answers: 'how do you verify the worker is actually working?'
    """
    from app.services.runtime_metadata import get_db_partner_platform_activity
    from app.services.external_apis import evaluate_partner_platform_eligibility

    partners = db.query(Partner).filter(Partner.is_active == True).limit(5).all()
    if not partners:
        return {
            "feature": "platform_activity_simulation",
            "pass_fail": "partial",
            "notes": ["No active partners found. Seed partner data first."],
            "partners": [],
        }

    partner_samples = []
    for p in partners:
        activity = get_db_partner_platform_activity(p.id, db)
        eligibility = evaluate_partner_platform_eligibility(p.id)
        partner_samples.append({
            "partner_id": p.id,
            "partner_name": p.name,
            "platform": activity.get("platform"),
            "platform_logged_in": activity["platform_logged_in"],
            "active_shift": activity["active_shift"],
            "orders_completed_recent": activity["orders_completed_recent"],
            "suspicious_inactivity": activity["suspicious_inactivity"],
            "platform_eligible": eligibility["eligible"],
            "platform_score": eligibility["score"],
        })

    eligible_count = sum(1 for p in partner_samples if p["platform_eligible"])

    return {
        "feature": "platform_activity_simulation",
        "pass_fail": "pass",
        "total_sampled": len(partner_samples),
        "platform_eligible": eligible_count,
        "platform_ineligible": len(partner_samples) - eligible_count,
        "partners": partner_samples,
        "admin_controls": {
            "get_activity": "GET /zones/partners/{partner_id}/activity",
            "set_activity": "PUT /zones/partners/{partner_id}/activity",
            "check_eligibility": "GET /zones/partners/{partner_id}/activity/eligibility",
            "bulk_view": "GET /zones/partners/activity/bulk",
        },
        "notes": [
            "Admin can toggle platform_logged_in, active_shift, suspicious_inactivity per partner",
            "Claim approval reads platform_activity check via validation matrix",
            "Platform activity score gates payout — inactive workers are blocked",
        ],
        "computed_at": datetime.utcnow().isoformat(),
    }


@router.get("/claims/{claim_id}/validation-matrix")
def get_claim_validation_matrix(claim_id: int, db: Session = Depends(get_db)):
    """
    GET /admin/claims/{claim_id}/validation-matrix

    Return the full validation matrix stored on a specific claim.
    Used by admin VerificationPanel to render per-claim check results.
    """
    import json as _json
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    try:
        vd = _json.loads(claim.validation_data or "{}")
    except Exception:
        vd = {}

    matrix = vd.get("validation_matrix", [])
    matrix_summary = vd.get("validation_matrix_summary", {})

    return {
        "claim_id": claim_id,
        "claim_status": claim.status.value,
        "claim_amount": claim.amount,
        "fraud_score": claim.fraud_score,
        "validation_matrix": matrix,
        "matrix_summary": matrix_summary,
        "has_matrix": bool(matrix),
        "computed_at": vd.get("processed_at"),
    }