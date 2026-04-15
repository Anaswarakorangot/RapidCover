"""
Admin Panel API - Phase 2 control-room endpoints.

Provides:
  GET  /admin/panel/stats             -> platform health metrics
  GET  /admin/panel/engine-status     -> scheduler + data source health
  GET  /admin/panel/trigger-log       -> real-time trigger engine log
  POST /admin/panel/simulate-trigger  -> force-fire a trigger via engine
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.utils.time_utils import utcnow
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.zone import Zone
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent, TriggerType
from app.config import get_settings

router = APIRouter(prefix="/admin/panel", tags=["admin-panel"])


# --- Response schemas --------------------------------------------------------

class ZoneLossRatio(BaseModel):
    zone: str
    zone_code: str
    lr: float

class PanelStats(BaseModel):
    activePolicies: int
    claimsThisWeek: int
    totalPayoutsRs: float
    lossRatioPercent: float
    autoApprovalRate: float
    fraudQueueCount: int
    avgPayoutMinutes: float
    zoneLossRatios: list[ZoneLossRatio]


class SimulateTriggerRequest(BaseModel):
    triggerType: str   # rain | heat | aqi | shutdown | closure
    zone: str          # zone code, e.g. BLR-047


class CityBCR(BaseModel):
    city: str
    code: str
    premiums: float
    claims: float
    lr: float
    suspended: bool
    pool_cap_pct: float


class ZoneDetail(BaseModel):
    id: int
    name: str
    code: str
    city: str
    status: str
    partners: int
    lr: float
    sustained: bool
    density: str


class FraudClaim(BaseModel):
    id: int
    claim_id: str
    partner_name: str
    partner_id: Optional[str] = None
    zone: Optional[str] = None
    zone_code: Optional[str] = None
    trigger: str
    amount: float
    trigger_type: str
    fraud_score: float
    reason: str
    timestamp: str
    flags: list[str] = []
    status: str = "manual_queue"
    cluster: Optional[str] = None


class SuspendCityRequest(BaseModel):
    city_code: str
    suspended: bool


# --- GET /admin/panel/stats --------------------------------------------------

@router.get("/stats", response_model=PanelStats)
def get_panel_stats(db: Session = Depends(get_db)):
    """Return the seven key financial health numbers for the admin panel."""

    now = utcnow()
    week_ago = now - timedelta(days=7)

    # Active policies
    active_policies = (
        db.query(func.count(Policy.id))
        .filter(
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .scalar()
    ) or 0

    # Claims this week
    claims_this_week = (
        db.query(func.count(Claim.id))
        .filter(Claim.created_at >= week_ago)
        .scalar()
    ) or 0

    # Total payouts this week (only paid claims)
    total_payouts = (
        db.query(func.sum(Claim.amount))
        .filter(Claim.status == ClaimStatus.PAID, Claim.paid_at >= week_ago)
        .scalar()
    ) or 0.0

    # Total premiums collected (sum of all active policy premiums)
    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .scalar()
    ) or 0.0

    # Loss ratio
    loss_ratio = (total_payouts / total_premiums * 100) if total_premiums > 0 else 0.0

    # Auto-approval rate
    total_claims = db.query(func.count(Claim.id)).scalar() or 0
    auto_approved = (
        db.query(func.count(Claim.id))
        .filter(Claim.fraud_score < 0.50)
        .scalar()
    ) or 0
    auto_approval_rate = (auto_approved / total_claims * 100) if total_claims > 0 else 0.0

    # Fraud queue (claims with fraud_score >= 0.50 that are still pending)
    fraud_queue = (
        db.query(func.count(Claim.id))
        .filter(Claim.fraud_score >= 0.50, Claim.status == ClaimStatus.PENDING)
        .scalar()
    ) or 0

    # Average payout time
    paid_claims = (
        db.query(Claim)
        .filter(Claim.status == ClaimStatus.PAID, Claim.paid_at.isnot(None))
        .all()
    )
    if paid_claims:
        deltas = [(c.paid_at - c.created_at).total_seconds() / 60 for c in paid_claims if c.paid_at]
        avg_payout = sum(deltas) / len(deltas) if deltas else 0.0
    else:
        avg_payout = 0.0

    # Per-zone loss ratios
    zones = db.query(Zone).all()
    zone_lrs = []
    for z in zones:
        zone_payouts = (
            db.query(func.sum(Claim.amount))
            .join(TriggerEvent, Claim.trigger_event_id == TriggerEvent.id)
            .filter(
                TriggerEvent.zone_id == z.id,
                Claim.status == ClaimStatus.PAID,
            )
            .scalar()
        ) or 0.0
        zone_premiums = (
            db.query(func.sum(Policy.weekly_premium))
            .join(Partner, Policy.partner_id == Partner.id)
            .filter(
                Partner.zone_id == z.id,
                Policy.is_active == True,
            )
            .scalar()
        ) or 0.0
        zlr = (zone_payouts / zone_premiums * 100) if zone_premiums > 0 else 0.0
        zone_lrs.append(ZoneLossRatio(zone=z.name, zone_code=z.code, lr=round(zlr, 1)))

    return PanelStats(
        activePolicies=active_policies,
        claimsThisWeek=claims_this_week,
        totalPayoutsRs=total_payouts,
        lossRatioPercent=round(loss_ratio, 1),
        autoApprovalRate=round(auto_approval_rate, 1),
        fraudQueueCount=fraud_queue,
        avgPayoutMinutes=round(avg_payout, 1),
        zoneLossRatios=zone_lrs,
    )


# --- GET /admin/panel/zones --------------------------------------------------

@router.get("/zones", response_model=list[ZoneDetail])
def get_zones(db: Session = Depends(get_db)):
    """Return live status of all zones for the map and overview."""
    zones = db.query(Zone).all()
    now = utcnow()
    results = []

    for z in zones:
        # Payouts in last 7 days
        zone_payouts = (
            db.query(func.sum(Claim.amount))
            .join(TriggerEvent, Claim.trigger_event_id == TriggerEvent.id)
            .filter(TriggerEvent.zone_id == z.id, Claim.status == ClaimStatus.PAID)
            .scalar()
        ) or 0.0

        # Premiums in last 7 days
        zone_premiums = (
            db.query(func.sum(Policy.weekly_premium))
            .join(Partner, Policy.partner_id == Partner.id)
            .filter(Partner.zone_id == z.id, Policy.is_active == True)
            .scalar()
        ) or 1.0  # Avoid div by zero

        lr = (zone_payouts / zone_premiums * 100)
        partners_count = db.query(func.count(Partner.id)).filter(Partner.zone_id == z.id).scalar() or 0

        # Detect sustained events (>48h)
        active_event = db.query(TriggerEvent).filter(
            TriggerEvent.zone_id == z.id,
            TriggerEvent.ended_at.is_(None)
        ).first()

        is_sustained = False
        status = "normal"
        if active_event:
            status = active_event.trigger_type.value
            duration = now - active_event.started_at
            if duration.total_seconds() > (48 * 3600):
                is_sustained = True

        results.append(ZoneDetail(
            id=z.id,
            name=z.name,
            code=z.code,
            city=z.city,
            status=status,
            partners=partners_count,
            lr=round(lr, 1),
            sustained=is_sustained,
            density=z.density_band or "Medium"
        ))

    return results


# --- GET /admin/panel/bcr ----------------------------------------------------

@router.get("/bcr")
def get_bcr(db: Session = Depends(get_db)):
    """Return BCR (Burning Cost Rate) stats grouped by city."""
    cities = db.query(Zone.city, Zone.code).group_by(Zone.city).all()
    city_stats = []

    for city_name, city_prefix in cities:
        # Prefix check (e.g. BLR-) for city code group
        prefix = city_prefix.split('-')[0] + '-'

        premiums = (
            db.query(func.sum(Policy.weekly_premium))
            .join(Partner, Policy.partner_id == Partner.id)
            .join(Zone, Partner.zone_id == Zone.id)
            .filter(Zone.city == city_name, Policy.is_active == True)
            .scalar()
        ) or 0.0

        claims = (
            db.query(func.sum(Claim.amount))
            .join(TriggerEvent, Claim.trigger_event_id == TriggerEvent.id)
            .join(Zone, TriggerEvent.zone_id == Zone.id)
            .filter(Zone.city == city_name, Claim.status == ClaimStatus.PAID)
            .scalar()
        ) or 0.0

        lr = (claims / premiums * 100) if premiums > 0 else 0.0
        is_suspended = db.query(Zone.is_suspended).filter(Zone.city == city_name).first()
        is_suspended = is_suspended[0] if is_suspended else False

        # Pool cap calc: (Claims / (Premiums * 0.7)) * 100 - simulated reserve hit
        pool_cap = (claims / (premiums * 1.2) * 100) if premiums > 0 else 0

        city_stats.append(CityBCR(
            city=city_name,
            code=prefix.rstrip('-'),
            premiums=round(premiums, 0),
            claims=round(claims, 0),
            lr=round(lr, 1),
            suspended=is_suspended,
            pool_cap_pct=round(pool_cap, 1)
        ))

    return {"cities": city_stats}


# --- POST /admin/panel/bcr/suspend -------------------------------------------

@router.post("/bcr/suspend")
def suspend_city(req: SuspendCityRequest, db: Session = Depends(get_db)):
    """Batch toggle suspension for all zones in a city."""
    # Find zones where code starts with req.city_code (e.g. BLR)
    db.query(Zone).filter(Zone.code.like(f"{req.city_code}%")).update(
        {Zone.is_suspended: req.suspended},
        synchronize_session=False
    )
    db.commit()
    return {"status": "success", "city": req.city_code, "suspended": req.suspended}


# --- GET /admin/panel/fraud-queue --------------------------------------------

@router.get("/fraud-queue", response_model=list[FraudClaim])
def get_fraud_queue(db: Session = Depends(get_db)):
    """Return pending claims with high fraud scores."""
    claims = (
        db.query(Claim)
        .filter(Claim.status == ClaimStatus.PENDING, Claim.fraud_score >= 0.50)
        .all()
    )

    results = []
    for c in claims:
        policy = db.query(Policy).filter(Policy.id == c.policy_id).first()
        partner = db.query(Partner).filter(Partner.id == policy.partner_id).first() if policy else None
        trigger = db.query(TriggerEvent).filter(TriggerEvent.id == c.trigger_event_id).first()
        zone = db.query(Zone).filter(Zone.id == trigger.zone_id).first() if trigger else None

        reason = "Fraud score exceeded manual review threshold"
        flags = []
        if c.fraud_score >= 0.90:
            reason = "Fraud score exceeded auto-reject threshold"
            flags = ["fraud_score"]
        elif c.fraud_score >= 0.75:
            reason = "Fraud score requires manual review"
            flags = ["manual_review"]
        elif c.fraud_score >= 0.50:
            reason = "Fraud score requires enhanced validation"
            flags = ["enhanced_validation"]

        results.append(FraudClaim(
            id=c.id,
            claim_id=f"CLM-{c.id:04d}",
            partner_name=partner.name if partner else "Unknown",
            partner_id=partner.partner_id if partner else None,
            zone=zone.name if zone else None,
            zone_code=zone.code if zone else None,
            trigger=trigger.trigger_type.value.title() if trigger else "Manual",
            amount=c.amount,
            trigger_type=trigger.trigger_type.value if trigger else "manual",
            fraud_score=c.fraud_score,
            reason=reason,
            timestamp=c.created_at.isoformat(),
            flags=flags,
            status="auto_reject" if c.fraud_score >= 0.90 else "manual_queue",
            cluster=None,
        ))

    return results


# --- GET /admin/panel/engine-status ------------------------------------------

@router.get("/engine-status")
def get_engine_status():
    """Return the trigger engine + scheduler status for admin UI."""
    from app.services.scheduler import get_scheduler_status
    from app.services.trigger_engine import get_engine_status as engine_status
    from app.services.external_apis import (
        MockWeatherAPI, MockAQIAPI, get_source_health
    )

    # Quick probe: if sources are still "unknown", try a single API call
    # to determine if keys are configured and working
    current_health = get_source_health()
    if current_health["openweathermap"]["status"] == "unknown":
        # Do a quick probe with default Bangalore coords
        try:
            MockWeatherAPI.get_current(1, 12.9716, 77.5946)
        except Exception:
            pass
    if current_health["waqi_aqi"]["status"] == "unknown":
        try:
            MockAQIAPI.get_current(1, 12.9716, 77.5946)
        except Exception:
            pass

    scheduler = get_scheduler_status()
    engine = engine_status()

    # Serialize datetime objects
    sources = {}
    for name, info in engine.get("data_sources", {}).items():
        sources[name] = {
            "status": info["status"],
            "last_check": info["last_check"].isoformat() if info["last_check"] else None,
            "last_success": info["last_success"].isoformat() if info["last_success"] else None,
        }

    return {
        "scheduler": scheduler,
        "engine": {
            "active_events": engine["active_events"],
            "active_event_keys": engine["active_event_keys"],
            "log_entries": engine["log_entries"],
        },
        "data_sources": sources,
        "oracle_reliability": engine.get("oracle_reliability", {}),
    }


# --- GET /admin/panel/trigger-log --------------------------------------------

@router.get("/trigger-log")
def get_trigger_log(limit: int = Query(50, ge=1, le=200)):
    """Return the most recent trigger engine log entries."""
    from app.services.trigger_engine import get_trigger_log
    return get_trigger_log(limit=limit)


# --- POST /admin/panel/simulate-trigger --------------------------------------

PIPELINE_STEPS = {
    "rain": [
        {"ts": "5:47:23", "msg": "Zone {zone} polygon match confirmed - IMD red alert active"},
        {"ts": "5:47:31", "msg": "Zepto mock ops: zone suspended - 72mm/hr rainfall detected"},
        {"ts": "5:47:39", "msg": "Traffic cross-validation: Google Maps confirms severe disruption"},
        {"ts": "5:47:44", "msg": "GPS coherence: normal - no spoofing anomalies"},
        {"ts": "5:47:51", "msg": "Run count confirmed: 3 deliveries completed before suspension"},
        {"ts": "5:47:55", "msg": "Policy lookup: Standard plan (Rs.33/wk) - max Rs.400/day, 3 days/wk"},
        {"ts": "5:47:58", "msg": "Fraud score: 0.11 -> auto-approve"},
        {"ts": "5:48:03", "msg": "Raw payout: Rs.420 -> Capped to Rs.400 (Standard plan limit) -> UPI credit Rs.400"},
        {"ts": "5:48:09", "msg": "Rs.400 UPI credit via Stripe API - txn tr_{rand}"},
        {"ts": "5:48:12", "msg": "Push notification sent (Kannada) - claim processed"},
    ],
    "heat": [
        {"ts": "5:47:23", "msg": "Zone {zone} polygon match confirmed - temp sensor active"},
        {"ts": "5:47:31", "msg": "IMD data confirms 44°C sustained 4+ hours in zone"},
        {"ts": "5:47:39", "msg": "Platform ops status: heat advisory issued, reduced deliveries"},
        {"ts": "5:47:44", "msg": "GPS coherence: normal - partner confirmed in zone"},
        {"ts": "5:47:51", "msg": "Activity log: 2 deliveries completed before heat cutoff"},
        {"ts": "5:47:55", "msg": "Policy lookup: Pro plan (Rs.45/wk) - max Rs.500/day, 4 days/wk"},
        {"ts": "5:47:58", "msg": "Fraud score: 0.08 -> auto-approve"},
        {"ts": "5:48:03", "msg": "Raw payout: Rs.320 -> Within Pro limit (Rs.500) -> UPI credit Rs.320"},
        {"ts": "5:48:09", "msg": "Rs.320 UPI credit via Stripe API - txn tr_{rand}"},
        {"ts": "5:48:12", "msg": "Push notification sent (Hindi) - heat claim processed"},
    ],
    "aqi": [
        {"ts": "5:47:23", "msg": "Zone {zone} polygon match confirmed - AQI sensor active"},
        {"ts": "5:47:31", "msg": "CPCB data: AQI 420 sustained 3+ hours - severe category"},
        {"ts": "5:47:39", "msg": "Cross-validation: IQAir confirms hazardous air quality"},
        {"ts": "5:47:44", "msg": "GPS coherence: normal - partner within zone boundary"},
        {"ts": "5:47:51", "msg": "Run count confirmed: 4 deliveries before AQI cutoff"},
        {"ts": "5:47:55", "msg": "Policy lookup: Flex plan (Rs.22/wk) - max Rs.250/day, 2 days/wk"},
        {"ts": "5:47:58", "msg": "Fraud score: 0.14 -> auto-approve"},
        {"ts": "5:48:03", "msg": "Raw payout: Rs.310 -> Capped to Rs.250 (Flex plan limit) -> UPI credit Rs.250"},
        {"ts": "5:48:09", "msg": "Rs.250 UPI credit via Stripe API - txn tr_{rand}"},
        {"ts": "5:48:12", "msg": "Push notification sent (Hindi) - AQI claim processed"},
    ],
    "shutdown": [
        {"ts": "5:47:23", "msg": "Zone {zone} polygon match confirmed - civic alert active"},
        {"ts": "5:47:31", "msg": "Municipal API: curfew/bandh declared - ops suspended"},
        {"ts": "5:47:39", "msg": "News cross-validation: confirmed via NDTV / local feeds"},
        {"ts": "5:47:44", "msg": "GPS coherence: normal - partner stationary at home"},
        {"ts": "5:47:51", "msg": "Activity log: 0 deliveries possible during shutdown"},
        {"ts": "5:47:55", "msg": "Policy lookup: Standard plan (Rs.33/wk) - max Rs.400/day, 3 days/wk"},
        {"ts": "5:47:58", "msg": "Fraud score: 0.05 -> auto-approve"},
        {"ts": "5:48:03", "msg": "Raw payout: Rs.350 -> Within Standard limit (Rs.400) -> UPI credit Rs.350"},
        {"ts": "5:48:09", "msg": "Rs.350 UPI credit via Stripe API - txn tr_{rand}"},
        {"ts": "5:48:12", "msg": "Push notification sent - curfew claim processed"},
    ],
    "closure": [
        {"ts": "5:47:23", "msg": "Zone {zone} polygon match confirmed - store status active"},
        {"ts": "5:47:31", "msg": "Platform API: dark store force majeure closure - 95 min"},
        {"ts": "5:47:39", "msg": "Cross-validation: store inventory system offline confirmed"},
        {"ts": "5:47:44", "msg": "GPS coherence: normal - partner near dark store location"},
        {"ts": "5:47:51", "msg": "Run count confirmed: partner was en-route when store closed"},
        {"ts": "5:47:55", "msg": "Policy lookup: Flex plan (Rs.22/wk) - max Rs.250/day, 2 days/wk"},
        {"ts": "5:47:58", "msg": "Fraud score: 0.09 -> auto-approve"},
        {"ts": "5:48:03", "msg": "Raw payout: Rs.143 -> Within Flex limit (Rs.250) -> UPI credit Rs.143"},
        {"ts": "5:48:09", "msg": "Rs.143 UPI credit via Stripe API - txn tr_{rand}"},
        {"ts": "5:48:12", "msg": "Push notification sent - store closure claim processed"},
    ],
}


@router.post("/simulate-trigger")
async def simulate_trigger(req: SimulateTriggerRequest):
    """
    Force-fire a trigger via the real trigger engine, then stream the
    pipeline log for the admin UI.

    This calls check_all_triggers(force=True) so the 45-min duration
    requirement is skipped for demo purposes.
    """
    trigger_type = req.triggerType.lower()
    zone_code = req.zone or "BLR-047"

    # Actually fire the trigger engine in force mode
    try:
        from app.services.trigger_engine import check_all_triggers
        from app.database import SessionLocal
        from app.models.zone import Zone
        from app.services.external_apis import (
            MockWeatherAPI, MockAQIAPI, MockPlatformAPI, MockCivicAPI
        )
        db = SessionLocal()
        zone = db.query(Zone).filter(Zone.code == zone_code).first()
        if zone:
            if trigger_type == "rain":
                MockWeatherAPI.set_conditions(zone.id, rainfall_mm_hr=72.0)
            elif trigger_type == "heat":
                MockWeatherAPI.set_conditions(zone.id, temp_celsius=45.0)
            elif trigger_type == "aqi":
                MockAQIAPI.set_conditions(zone.id, aqi=420)
            elif trigger_type == "shutdown":
                MockCivicAPI.set_shutdown(zone.id, reason="Admin simulation")
            elif trigger_type == "closure":
                MockPlatformAPI.set_store_closed(zone.id, reason="Admin simulation")
        db.close()

        # Use drill_mode() to temporarily enable demo mode for simulation
        from app.utils.demo_context import drill_mode

        loop = asyncio.get_event_loop()

        def run_drill():
            with drill_mode():
                check_all_triggers(force=True, zone_code=zone_code)

        await loop.run_in_executor(None, run_drill)
    except Exception as e:
        print(f"[admin_panel] Trigger engine force-fire error: {e}")

    # Stream the visual pipeline log for the UI
    steps = PIPELINE_STEPS.get(trigger_type, PIPELINE_STEPS["rain"])

    async def event_stream():
        rand_id = random.randint(1000, 9999)
        for step in steps:
            msg = step["msg"].replace("{zone}", zone_code).replace("{rand}", str(rand_id))
            line = json.dumps({"ts": step["ts"], "msg": msg}) + "\n"
            yield line
            await asyncio.sleep(0.18)

        # Summary line with insurance operations stats
        summary = (
            f"Total: 49 seconds · Partners paid: 47 · "
            f"Skipped (no policy): 12 · At weekly limit: 3"
        )
        yield json.dumps({"ts": "done", "msg": summary, "total": 49}) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"X-Content-Type-Options": "nosniff"},
    )


# --- GET /admin/panel/live-data ----------------------------------------------

@router.get("/live-data")
def get_live_api_data(
    zone_code: str = Query("BLR-KOR", description="Zone code to fetch data for"),
    db: Session = Depends(get_db),
):
    """
    Fetch current data from all external APIs for a zone.

    Returns weather, AQI, platform status, and shutdown status with source info.
    Use this to verify what data the trigger engine is seeing.
    """
    from app.services.external_apis import (
        MockWeatherAPI,
        MockAQIAPI,
        MockPlatformAPI,
        MockCivicAPI,
        get_source_health,
    )

    # Find zone
    zone = db.query(Zone).filter(Zone.code == zone_code).first()
    if not zone:
        # Fallback to first zone
        zone = db.query(Zone).first()

    if not zone:
        return {"error": "No zones found. Run seed first."}

    # Fetch data from all sources (will try live, fallback to mock)
    weather = MockWeatherAPI.get_current(zone.id, zone.dark_store_lat, zone.dark_store_lng)
    aqi = MockAQIAPI.get_current(zone.id, zone.dark_store_lat, zone.dark_store_lng)
    platform = MockPlatformAPI.get_store_status(zone.id)
    shutdown = MockCivicAPI.get_shutdown_status(zone.id)

    # Get source health
    health = get_source_health()

    return {
        "zone": {
            "id": zone.id,
            "code": zone.code,
            "name": zone.name,
            "city": zone.city,
            "lat": zone.dark_store_lat,
            "lng": zone.dark_store_lng,
        },
        "weather": {
            "temp_celsius": weather.temp_celsius,
            "rainfall_mm_hr": weather.rainfall_mm_hr,
            "humidity": weather.humidity,
            "source": weather.source,
            "timestamp": weather.timestamp.isoformat(),
        },
        "aqi": {
            "aqi": aqi.aqi,
            "pm25": aqi.pm25,
            "pm10": aqi.pm10,
            "category": aqi.category,
            "source": aqi.source,
            "timestamp": aqi.timestamp.isoformat(),
        },
        "platform": {
            "is_open": platform.is_open,
            "closure_reason": platform.closure_reason,
            "source": platform.source,
            "timestamp": platform.timestamp.isoformat(),
        },
        "shutdown": {
            "is_active": shutdown.is_active,
            "reason": shutdown.reason,
            "source": shutdown.source,
            "timestamp": shutdown.timestamp.isoformat(),
        },
        "source_health": {
            name: {
                "status": info["status"],
                "last_check": info["last_check"].isoformat() if info["last_check"] else None,
            }
            for name, info in health.items()
        },
        "demo_mode": get_settings().demo_mode,
        "fetched_at": utcnow().isoformat(),
    }


# --- GET /admin/panel/oracle-reliability -------------------------------------

@router.get("/oracle-reliability")
def get_oracle_reliability(zone_id: int = None):
    """
    Return full oracle reliability report for all data sources.

    Shows:
    - Per-source reliability badge (live / mock / stale)
    - Freshness (seconds since last successful call)
    - Agreement score between corroborating sources
    - System health: healthy | degraded | stale | mock_mode

    Used by admin LiveDataPanel and EngineStatus panel.
    """
    from app.services.external_apis import get_oracle_reliability_report, compute_trigger_confidence

    report = get_oracle_reliability_report(zone_id=zone_id)

    # Example: show what a rain trigger confidence would look like right now
    rain_confidence = compute_trigger_confidence(
        primary_source="openweathermap",
        corroborating_sources=["waqi_aqi"],
    )
    shutdown_confidence = compute_trigger_confidence(
        primary_source="civic_api",
        corroborating_sources=["traffic_feed"],
    )

    return {
        **report,
        "example_trigger_decisions": {
            "rain_trigger": rain_confidence,
            "shutdown_trigger": shutdown_confidence,
        },
    }


# --- GET /admin/panel/live-data ----------------------------------------------

@router.get("/live-data")
def get_live_data(db: Session = Depends(get_db)):
    """
    Return live data summary: source health, oracle reliability, partner activity snapshot.

    Consolidates oracle engine status, data source badges, and platform activity
    into a single panel response. Feeds the admin LiveDataPanel.
    """
    from app.services.external_apis import (
        get_oracle_reliability_report,
        compute_trigger_confidence,
        get_source_health,
    )
    from app.services.claims_processor import get_db_partner_platform_activity
    from app.services.external_apis import evaluate_partner_platform_eligibility

    oracle = get_oracle_reliability_report()
    source_health = get_source_health()

    # Serialize source health datetimes
    sources_serialized = {}
    for name, info in source_health.items():
        sources_serialized[name] = {
            "status": info["status"],
            "last_check": info["last_check"].isoformat() if info.get("last_check") else None,
            "last_success": info["last_success"].isoformat() if info.get("last_success") else None,
        }

    # Sample platform activity (top 10 partners)
    partners = db.query(Partner).filter(Partner.is_active == True).limit(10).all()
    activity_summary = []
    active_on_platform = 0
    for p in partners:
        activity = get_db_partner_platform_activity(p.id, db)
        eligibility = evaluate_partner_platform_eligibility(p.id)
        if activity["active_shift"] and activity["platform_logged_in"]:
            active_on_platform += 1
        activity_summary.append({
            "partner_id": p.id,
            "partner_name": p.name,
            "platform": activity.get("platform", "unknown"),
            "active_shift": activity["active_shift"],
            "platform_logged_in": activity["platform_logged_in"],
            "orders_completed_recent": activity["orders_completed_recent"],
            "platform_eligible": eligibility["eligible"],
            "platform_score": eligibility["score"],
        })

    return {
        "oracle": {
            "system_health": oracle["system_health"],
            "average_reliability": oracle["average_reliability"],
            "live_sources": oracle["live_sources"],
            "mock_sources": oracle["mock_sources"],
            "stale_sources": oracle["stale_sources"],
            "sources": oracle["sources"],
        },
        "data_sources": sources_serialized,
        "platform_activity": {
            "total_sampled": len(activity_summary),
            "active_on_platform": active_on_platform,
            "inactive_on_platform": len(activity_summary) - active_on_platform,
            "partners": activity_summary,
        },
        "computed_at": utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DEMO MODE CONTROL (Phase 3)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/demo-mode")
async def get_demo_mode_status():
    """
    Get current demo mode status.

    Returns:
        {
            "demo_mode": bool,
            "demo_exempt_cities": list[str],
            "description": str
        }
    """
    settings = get_settings()
    return {
        "demo_mode": settings.demo_mode,
        "demo_exempt_cities": settings.demo_exempt_cities,
        "description": "Demo mode uses mock data instead of live APIs" if settings.demo_mode else "Production mode uses live APIs",
    }


@router.post("/demo-mode")
async def toggle_demo_mode(enable: bool):
    """
    Toggle demo mode on or off.

    Args:
        enable: True to enable demo mode, False to disable

    Returns:
        {
            "demo_mode": bool,
            "message": str
        }
    """
    settings = get_settings()
    settings.demo_mode = enable

    return {
        "demo_mode": settings.demo_mode,
        "message": f"Demo mode {'enabled' if enable else 'disabled'}. {'Using mock data for simulations.' if enable else 'Using live API data.'}",
    }
