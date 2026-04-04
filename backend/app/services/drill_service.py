"""
Drill Service — Structured drill execution for admin verification.

Provides preset-based drill configurations and pipeline execution with
detailed metrics and event streaming.
"""

import json
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional
from sqlalchemy.orm import Session

from app.models.drill_session import DrillSession, DrillType, DrillStatus
from app.models.zone import Zone
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent
from app.schemas.drill import (
    DrillPipelineEvent,
    DrillImpactResponse,
    LatencyMetrics,
)
from app.services.external_apis import (
    MockWeatherAPI,
    MockAQIAPI,
    MockPlatformAPI,
    MockCivicAPI,
)


# ─── Drill Presets ─────────────────────────────────────────────────────────────

DRILL_PRESETS = {
    "flash_flood": {
        "conditions": {
            "weather": {"rainfall_mm_hr": 72, "humidity": 95}
        },
        "trigger_type": "rain",
        "description": "Heavy rainfall exceeding 72mm/hr with 95% humidity",
    },
    "aqi_spike": {
        "conditions": {
            "aqi": {"aqi": 450, "pm25": 280}
        },
        "trigger_type": "aqi",
        "description": "Hazardous AQI spike to 450 with PM2.5 at 280",
    },
    "heatwave": {
        "conditions": {
            "weather": {"temp_celsius": 46}
        },
        "trigger_type": "heat",
        "description": "Extreme heat wave with temperature at 46°C",
    },
    "store_closure": {
        "conditions": {
            "platform": {"is_open": False, "reason": "Power outage"}
        },
        "trigger_type": "closure",
        "description": "Dark store closure due to power outage",
    },
    "curfew": {
        "conditions": {
            "shutdown": {"is_active": True, "reason": "Curfew order"}
        },
        "trigger_type": "shutdown",
        "description": "Civic shutdown due to curfew order",
    },
    # ─── Phase 2 Team Guide Stress Scenarios (Section 2E) ───────────────────────
    "monsoon_14day": {
        "conditions": {
            "weather": {"rainfall_mm_hr": 65, "humidity": 98},
            "sustained": {"consecutive_days": 14, "cities": ["bangalore", "mumbai"]},
        },
        "trigger_type": "rain",
        "description": "14-day sustained monsoon in BLR+BOM. Tests sustained event protocol (70% payout factor, 21-day max, reinsurance flag at day 7).",
        "stress_scenario": True,
        "target_cities": ["bangalore", "mumbai"],
    },
    "multi_city_aqi": {
        "conditions": {
            "aqi": {"aqi": 480, "pm25": 320, "pm10": 450},
            "multi_city": {"cities": ["delhi", "noida", "gurgaon"]},
        },
        "trigger_type": "aqi",
        "description": "Multi-city AQI spike across NCR (DEL+NOI+GGN). Tests zone pool share cap and city-level 120% hard cap.",
        "stress_scenario": True,
        "target_cities": ["delhi", "noida", "gurgaon"],
    },
    "cyclone": {
        "conditions": {
            "weather": {"rainfall_mm_hr": 95, "wind_kmh": 120, "humidity": 100},
            "shutdown": {"is_active": True, "reason": "Cyclone Warning - Stay Indoors"},
        },
        "trigger_type": "rain",
        "description": "Cyclone scenario in CHN+BOM. Combines rain trigger with civic shutdown. Tests multi-trigger handling.",
        "stress_scenario": True,
        "target_cities": ["chennai", "mumbai"],
    },
    "bandh": {
        "conditions": {
            "shutdown": {"is_active": True, "reason": "Bandh / General Strike"},
            "platform": {"is_open": False, "reason": "Bandh - All stores closed"},
        },
        "trigger_type": "shutdown",
        "description": "City-wide bandh / general strike. All stores closed. Tests shutdown + closure combination.",
        "stress_scenario": True,
    },
    "collusion_fraud": {
        "conditions": {
            "weather": {"rainfall_mm_hr": 58, "humidity": 85},
            "fraud_test": {
                "fake_gps_coherence": 0.15,
                "activity_paradox": True,
                "claim_frequency_spike": 5,
                "new_accounts": 3,
            },
        },
        "trigger_type": "rain",
        "description": "Fraud detection stress test. Simulates collusion ring with GPS spoofing, activity paradox, and suspicious claim patterns. Tests fraud scoring thresholds.",
        "stress_scenario": True,
        "fraud_test": True,
    },
}


def get_preset_for_drill_type(drill_type: DrillType) -> dict:
    """Map DrillType enum to preset configuration."""
    mapping = {
        DrillType.FLASH_FLOOD: "flash_flood",
        DrillType.AQI_SPIKE: "aqi_spike",
        DrillType.HEATWAVE: "heatwave",
        DrillType.STORE_CLOSURE: "store_closure",
        DrillType.CURFEW: "curfew",
        # Phase 2 stress scenarios
        DrillType.MONSOON_14DAY: "monsoon_14day",
        DrillType.MULTI_CITY_AQI: "multi_city_aqi",
        DrillType.CYCLONE: "cyclone",
        DrillType.BANDH: "bandh",
        DrillType.COLLUSION_FRAUD: "collusion_fraud",
    }
    preset_name = mapping.get(drill_type, "flash_flood")
    return DRILL_PRESETS.get(preset_name, DRILL_PRESETS["flash_flood"])


def apply_preset_conditions(zone_id: int, preset_name: str) -> dict:
    """
    Apply all conditions for a named preset to mock APIs.

    Returns dict with applied conditions or error.
    """
    preset = DRILL_PRESETS.get(preset_name)
    if not preset:
        return {"error": f"Unknown preset: {preset_name}"}

    applied = {}
    conditions = preset["conditions"]

    if "weather" in conditions:
        weather_cond = conditions["weather"]
        MockWeatherAPI.set_conditions(
            zone_id,
            temp_celsius=weather_cond.get("temp_celsius"),
            rainfall_mm_hr=weather_cond.get("rainfall_mm_hr"),
            humidity=weather_cond.get("humidity"),
        )
        applied["weather"] = weather_cond

    if "aqi" in conditions:
        aqi_cond = conditions["aqi"]
        MockAQIAPI.set_conditions(
            zone_id,
            aqi=aqi_cond.get("aqi"),
            pm25=aqi_cond.get("pm25"),
            pm10=aqi_cond.get("pm10"),
        )
        applied["aqi"] = aqi_cond

    if "platform" in conditions:
        platform_cond = conditions["platform"]
        if not platform_cond.get("is_open", True):
            MockPlatformAPI.set_store_closed(zone_id, platform_cond.get("reason", "Drill test"))
        else:
            MockPlatformAPI.set_store_open(zone_id)
        applied["platform"] = platform_cond

    if "shutdown" in conditions:
        shutdown_cond = conditions["shutdown"]
        if shutdown_cond.get("is_active", False):
            MockCivicAPI.set_shutdown(zone_id, shutdown_cond.get("reason", "Drill test"))
        else:
            MockCivicAPI.clear_shutdown(zone_id)
        applied["shutdown"] = shutdown_cond

    return {"applied": preset_name, "conditions": applied}


# ─── Drill Session Management ──────────────────────────────────────────────────

def create_drill_session(
    drill_type: DrillType,
    zone_id: int,
    zone_code: str,
    preset: str,
    force: bool,
    db: Session,
) -> DrillSession:
    """Create a new drill session record."""
    drill_id = str(uuid.uuid4())

    session = DrillSession(
        drill_id=drill_id,
        drill_type=drill_type,
        zone_id=zone_id,
        zone_code=zone_code,
        preset=preset,
        status=DrillStatus.STARTED,
        force_mode=force,
        pipeline_events="[]",
        skipped_reasons="{}",
        errors="[]",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def add_pipeline_event(
    drill_session: DrillSession,
    step: str,
    message: str,
    metadata: Optional[dict] = None,
    db: Session = None,
) -> DrillPipelineEvent:
    """Add a pipeline event to the drill session."""
    event = DrillPipelineEvent(
        step=step,
        message=message,
        ts=datetime.utcnow(),
        metadata=metadata,
    )

    # Parse existing events
    events = json.loads(drill_session.pipeline_events or "[]")
    events.append(event.model_dump(mode="json"))
    drill_session.pipeline_events = json.dumps(events)

    if db:
        db.commit()

    return event


def complete_drill_session(
    drill_session: DrillSession,
    status: DrillStatus,
    db: Session,
    trigger_event_id: Optional[int] = None,
    error: Optional[str] = None,
):
    """Mark drill session as completed or failed."""
    drill_session.status = status
    drill_session.completed_at = datetime.utcnow()

    if trigger_event_id:
        drill_session.trigger_event_id = trigger_event_id

    if error:
        errors = json.loads(drill_session.errors or "[]")
        errors.append({"message": error, "ts": datetime.utcnow().isoformat()})
        drill_session.errors = json.dumps(errors)

    # Calculate total latency
    if drill_session.started_at and drill_session.completed_at:
        delta = drill_session.completed_at - drill_session.started_at
        drill_session.total_latency_ms = int(delta.total_seconds() * 1000)

    db.commit()


# ─── Drill Execution ───────────────────────────────────────────────────────────

def execute_drill(
    drill_session: DrillSession,
    zone: Zone,
    db: Session,
) -> list[DrillPipelineEvent]:
    """
    Execute a drill and return pipeline events.

    Steps:
    1. injected - Apply preset conditions to mock APIs
    2. threshold_crossed - Verify threshold is exceeded
    3. trigger_fired - Create TriggerEvent in DB
    4. eligible_partners_found - Find partners with active policies
    5. claims_created - Generate claims with fraud scores
    6. fraud_scored - Determine auto-approve/review/reject
    7. payouts_sent - Auto-payout if enabled
    8. notifications_sent - Dispatch push notifications
    9. completed - Summary with latency metrics
    """
    from app.services.trigger_engine import check_all_triggers, _fire_trigger, RAIN_THRESHOLD_MM_HR, HEAT_THRESHOLD_CELSIUS, AQI_THRESHOLD
    from app.services.claims_processor import get_eligible_policies, process_trigger_event
    from app.config import get_settings

    events = []
    settings = get_settings()

    # Update status to running
    drill_session.status = DrillStatus.RUNNING
    db.commit()

    preset_name = drill_session.preset
    preset = DRILL_PRESETS.get(preset_name, DRILL_PRESETS["flash_flood"])

    try:
        # Step 1: Inject conditions
        start_time = time.time()
        result = apply_preset_conditions(zone.id, preset_name)
        inject_latency = int((time.time() - start_time) * 1000)

        event = add_pipeline_event(
            drill_session, "injected",
            f"Applied {preset_name} preset conditions to zone {zone.code}",
            {"conditions": result.get("conditions", {}), "latency_ms": inject_latency},
            db,
        )
        events.append(event)

        # Step 2: Verify threshold crossed
        trigger_type = preset["trigger_type"]
        conditions = preset["conditions"]

        threshold_info = {}
        if trigger_type == "rain":
            value = conditions.get("weather", {}).get("rainfall_mm_hr", 0)
            threshold_info = {"value": value, "threshold": RAIN_THRESHOLD_MM_HR, "unit": "mm/hr"}
        elif trigger_type == "heat":
            value = conditions.get("weather", {}).get("temp_celsius", 0)
            threshold_info = {"value": value, "threshold": HEAT_THRESHOLD_CELSIUS, "unit": "°C"}
        elif trigger_type == "aqi":
            value = conditions.get("aqi", {}).get("aqi", 0)
            threshold_info = {"value": value, "threshold": AQI_THRESHOLD, "unit": "AQI"}
        elif trigger_type in ("shutdown", "closure"):
            threshold_info = {"value": True, "threshold": True, "unit": "active"}

        event = add_pipeline_event(
            drill_session, "threshold_crossed",
            f"Threshold exceeded: {threshold_info.get('value')} {threshold_info.get('unit', '')} (threshold: {threshold_info.get('threshold')})",
            threshold_info,
            db,
        )
        events.append(event)

        # Step 3: Fire trigger (this creates TriggerEvent and claims)
        trigger_start = time.time()

        # Use check_all_triggers which handles the full flow
        check_all_triggers(force=drill_session.force_mode, zone_code=zone.code, prefer_mock=True)

        trigger_latency = int((time.time() - trigger_start) * 1000)
        drill_session.trigger_latency_ms = trigger_latency

        # Find the trigger event that was just created
        trigger_event = (
            db.query(TriggerEvent)
            .filter(TriggerEvent.zone_id == zone.id)
            .order_by(TriggerEvent.created_at.desc())
            .first()
        )

        if trigger_event:
            drill_session.trigger_event_id = trigger_event.id
            event = add_pipeline_event(
                drill_session, "trigger_fired",
                f"Trigger event #{trigger_event.id} created (type: {trigger_event.trigger_type.value}, severity: {trigger_event.severity})",
                {"trigger_id": trigger_event.id, "severity": trigger_event.severity, "latency_ms": trigger_latency},
                db,
            )
            events.append(event)
        else:
            event = add_pipeline_event(
                drill_session, "trigger_fired",
                "No trigger event created (may already exist or conditions not met)",
                {"latency_ms": trigger_latency},
                db,
            )
            events.append(event)

        # Step 4: Count eligible partners
        all_partners = db.query(Partner).filter(
            Partner.zone_id == zone.id,
            Partner.is_active == True,
        ).count()
        drill_session.affected_partners = all_partners

        eligible = get_eligible_policies(zone.id, db)
        drill_session.eligible_partners = len(eligible)

        # Track skipped reasons
        skipped = {"no_policy": all_partners - len(eligible)}

        event = add_pipeline_event(
            drill_session, "eligible_partners_found",
            f"Found {len(eligible)} eligible partners out of {all_partners} in zone",
            {"eligible": len(eligible), "total": all_partners, "skipped_no_policy": skipped["no_policy"]},
            db,
        )
        events.append(event)

        # Step 5: Count claims created
        claim_start = time.time()

        if trigger_event:
            claims = db.query(Claim).filter(Claim.trigger_event_id == trigger_event.id).all()
            drill_session.claims_created = len(claims)

            # Update validation_data with drill_id for tracking
            for claim in claims:
                validation = json.loads(claim.validation_data or "{}")
                validation["drill_id"] = drill_session.drill_id
                claim.validation_data = json.dumps(validation)
            db.commit()
        else:
            claims = []

        claim_latency = int((time.time() - claim_start) * 1000)
        drill_session.claim_creation_latency_ms = claim_latency

        event = add_pipeline_event(
            drill_session, "claims_created",
            f"Created {len(claims)} claims for trigger event",
            {"count": len(claims), "latency_ms": claim_latency},
            db,
        )
        events.append(event)

        # Step 6: Fraud scoring summary
        if claims:
            fraud_summary = {
                "auto_approve": sum(1 for c in claims if c.fraud_score < 0.3),
                "review": sum(1 for c in claims if 0.3 <= c.fraud_score <= 0.6),
                "auto_reject": sum(1 for c in claims if c.fraud_score > 0.8),
            }
            event = add_pipeline_event(
                drill_session, "fraud_scored",
                f"Fraud scoring complete: {fraud_summary['auto_approve']} auto-approve, {fraud_summary['review']} review, {fraud_summary['auto_reject']} reject",
                fraud_summary,
                db,
            )
            events.append(event)

        # Step 7: Count payouts
        payout_start = time.time()
        paid_claims = [c for c in claims if c.status == ClaimStatus.PAID]
        pending_claims = [c for c in claims if c.status == ClaimStatus.PENDING]

        drill_session.claims_paid = len(paid_claims)
        drill_session.claims_pending = len(pending_claims)
        drill_session.payouts_total = sum(c.amount for c in paid_claims)

        payout_latency = int((time.time() - payout_start) * 1000)
        drill_session.payout_latency_ms = payout_latency

        auto_payout_enabled = getattr(settings, "auto_payout_enabled", False)
        event = add_pipeline_event(
            drill_session, "payouts_sent",
            f"Payouts: {len(paid_claims)} paid (₹{drill_session.payouts_total:.0f}), {len(pending_claims)} pending. Auto-payout: {'enabled' if auto_payout_enabled else 'disabled'}",
            {"paid": len(paid_claims), "pending": len(pending_claims), "total_amount": drill_session.payouts_total, "auto_payout": auto_payout_enabled},
            db,
        )
        events.append(event)

        # Step 8: Notifications (count would come from notification service)
        event = add_pipeline_event(
            drill_session, "notifications_sent",
            f"Push notifications dispatched for {len(claims)} claims",
            {"count": len(claims)},
            db,
        )
        events.append(event)

        # Step 9: Complete
        drill_session.skipped_reasons = json.dumps(skipped)
        complete_drill_session(drill_session, DrillStatus.COMPLETED, db, trigger_event.id if trigger_event else None)

        event = add_pipeline_event(
            drill_session, "completed",
            f"Drill completed successfully. Total latency: {drill_session.total_latency_ms}ms",
            {
                "total_latency_ms": drill_session.total_latency_ms,
                "claims_created": drill_session.claims_created,
                "claims_paid": drill_session.claims_paid,
                "payouts_total": drill_session.payouts_total,
            },
            db,
        )
        events.append(event)

    except Exception as e:
        complete_drill_session(drill_session, DrillStatus.FAILED, db, error=str(e))
        event = add_pipeline_event(
            drill_session, "error",
            f"Drill failed: {str(e)}",
            {"error": str(e)},
            db,
        )
        events.append(event)
        raise

    return events


def get_drill_impact(drill_id: str, db: Session) -> Optional[DrillImpactResponse]:
    """Get impact metrics for a completed drill."""
    drill = db.query(DrillSession).filter(DrillSession.drill_id == drill_id).first()
    if not drill:
        return None

    skipped = json.loads(drill.skipped_reasons or "{}")

    return DrillImpactResponse(
        drill_id=drill.drill_id,
        status=drill.status,
        affected_partners=drill.affected_partners,
        eligible_partners=drill.eligible_partners,
        claims_created=drill.claims_created,
        claims_paid=drill.claims_paid,
        claims_pending=drill.claims_pending,
        payouts_total=drill.payouts_total,
        skipped_partners=skipped,
        latency_metrics=LatencyMetrics(
            trigger_latency_ms=drill.trigger_latency_ms,
            claim_creation_latency_ms=drill.claim_creation_latency_ms,
            payout_latency_ms=drill.payout_latency_ms,
            total_latency_ms=drill.total_latency_ms,
        ),
    )


def get_drill_history(db: Session, limit: int = 20) -> list[DrillSession]:
    """Get recent drill sessions."""
    return (
        db.query(DrillSession)
        .order_by(DrillSession.started_at.desc())
        .limit(limit)
        .all()
    )
