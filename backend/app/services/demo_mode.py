"""
Demo mode orchestration service.

This module exposes structured demo scenarios that run against the real
trigger/claim pipeline while keeping payouts mocked.
"""

from __future__ import annotations

import json
from itertools import count
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.claim import Claim, ClaimStatus
from app.models.partner import Partner
from app.models.trigger_event import SustainedEvent, TriggerEvent, TriggerType
from app.models.zone import Zone
from app.services.claims_processor import process_trigger_event
from app.services.external_apis import clear_partial_disruption_data, get_partial_disruption_data, set_partial_disruption_data
from app.services.payout_service import process_payout
from app.services.policy_lifecycle import check_adverse_selection
from app.services.trigger_detector import clear_sustained_event, inject_sustained_event_history
from app.utils.time_utils import utcnow

SCENARIO_DEFINITIONS = [
    {
        "id": "standard_trigger",
        "label": "Standard Trigger",
        "description": "Create a live trigger and auto-process claims for the selected zone.",
        "defaults": {
            "trigger_type": "rain",
            "severity": 4,
            "inject_sustained_days": 0,
            "partial_factor_override": None,
            "expected_orders": None,
            "actual_orders": None,
            "auto_mark_paid": True,
        },
    },
    {
        "id": "sustained_trigger",
        "label": "Sustained Trigger",
        "description": "Preload consecutive history so the next event activates 70% sustained payout mode.",
        "defaults": {
            "trigger_type": "rain",
            "severity": 4,
            "inject_sustained_days": 5,
            "partial_factor_override": None,
            "expected_orders": None,
            "actual_orders": None,
            "auto_mark_paid": True,
        },
    },
    {
        "id": "partial_payout",
        "label": "Partial Payout",
        "description": "Inject disruption factors or order-drop data to create partial payouts.",
        "defaults": {
            "trigger_type": "rain",
            "severity": 3,
            "inject_sustained_days": 0,
            "partial_factor_override": 0.5,
            "expected_orders": 100,
            "actual_orders": 45,
            "auto_mark_paid": True,
        },
    },
    {
        "id": "adverse_selection_block",
        "label": "Purchase Block Proof",
        "description": "Fire a severity 3+ event and prove production purchase checks would block new enrollment.",
        "defaults": {
            "trigger_type": "rain",
            "severity": 4,
            "inject_sustained_days": 0,
            "partial_factor_override": None,
            "expected_orders": None,
            "actual_orders": None,
            "auto_mark_paid": False,
        },
    },
    {
        "id": "city_suspension",
        "label": "City Suspension",
        "description": "Mark the selected city suspended and prove policy sales are frozen at city level.",
        "defaults": {
            "trigger_type": "rain",
            "severity": 4,
            "inject_sustained_days": 0,
            "partial_factor_override": None,
            "expected_orders": None,
            "actual_orders": None,
            "auto_mark_paid": False,
        },
    },
]

_demo_runs: dict[int, dict[str, Any]] = {}
_run_counter = count(1)


def _trigger_type_from_string(value: str | TriggerType) -> TriggerType:
    if isinstance(value, TriggerType):
        return value
    normalized = (value or "rain").strip().lower()
    return {
        "rain": TriggerType.RAIN,
        "heat": TriggerType.HEAT,
        "aqi": TriggerType.AQI,
        "shutdown": TriggerType.SHUTDOWN,
        "closure": TriggerType.CLOSURE,
    }[normalized]


def _scenario_defaults(scenario_type: str) -> dict[str, Any]:
    for scenario in SCENARIO_DEFINITIONS:
        if scenario["id"] == scenario_type:
            return dict(scenario["defaults"])
    return dict(SCENARIO_DEFINITIONS[0]["defaults"])


def _recent_runs(limit: int = 10) -> list[dict[str, Any]]:
    return sorted(_demo_runs.values(), key=lambda item: item["run_id"], reverse=True)[:limit]


def _get_sample_partner(zone_id: int, db: Session) -> Optional[Partner]:
    return (
        db.query(Partner)
        .filter(Partner.zone_id == zone_id, Partner.is_active == True)
        .order_by(Partner.id.asc())
        .first()
    )


def _purchase_preview(zone_id: int, db: Session, *, demo_override: bool) -> dict[str, Any]:
    partner = _get_sample_partner(zone_id, db)
    if not partner:
        return {"available": None, "reason": "No active partner found in selected zone for purchase preview.", "partner_id": None}

    settings = get_settings()
    original_mode = settings.demo_mode
    try:
        settings.demo_mode = demo_override
        allowed, reason = check_adverse_selection(partner, db)
    finally:
        settings.demo_mode = original_mode

    return {
        "available": allowed,
        "reason": reason or ("Demo override bypass active" if demo_override else "No adverse-selection block"),
        "partner_id": partner.id,
    }


def _claim_summary(claims: list[Claim]) -> dict[str, int]:
    return {
        "total": len(claims),
        "pending": sum(1 for claim in claims if claim.status == ClaimStatus.PENDING),
        "approved": sum(1 for claim in claims if claim.status == ClaimStatus.APPROVED),
        "rejected": sum(1 for claim in claims if claim.status == ClaimStatus.REJECTED),
        "paid": sum(1 for claim in claims if claim.status == ClaimStatus.PAID),
    }


def _claim_view(claim: Claim) -> dict[str, Any]:
    try:
        validation = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        validation = {}
    payout = validation.get("payout_calculation", {})
    sustained = validation.get("sustained_event", {})
    partial = payout.get("partial_disruption", {})
    return {
        "claim_id": claim.id,
        "status": claim.status.value,
        "amount": claim.amount,
        "upi_ref": claim.upi_ref,
        "partner_visibility": {
            "claims_history": True,
            "latest_payout_banner": claim.status == ClaimStatus.PAID,
        },
        "payout": {
            "final_payout": payout.get("final_payout", claim.amount),
            "after_partial_disruption": payout.get("after_partial_disruption"),
            "after_sustained_modifier": payout.get("after_sustained_modifier"),
            "partial_factor": partial.get("factor"),
            "partial_reason": partial.get("reason"),
            "sustained_modifier": payout.get("sustained_event_modifier"),
            "is_sustained": sustained.get("is_sustained", False),
            "consecutive_days": sustained.get("consecutive_days", 0),
        },
    }


def list_demo_scenarios(db: Session) -> dict[str, Any]:
    zones = db.query(Zone).order_by(Zone.city.asc(), Zone.name.asc()).all()
    return {
        "scenarios": SCENARIO_DEFINITIONS,
        "zones": [{"id": zone.id, "name": zone.name, "code": zone.code, "city": zone.city, "is_suspended": zone.is_suspended} for zone in zones],
        "recent_runs": _recent_runs(),
    }


def get_demo_run(run_id: int) -> Optional[dict[str, Any]]:
    return _demo_runs.get(run_id)


def run_demo_scenario(payload: dict[str, Any], db: Session) -> dict[str, Any]:
    scenario_type = payload.get("scenario_type") or "standard_trigger"
    merged = {**_scenario_defaults(scenario_type), **payload}

    zone = db.query(Zone).filter(Zone.id == merged["zone_id"]).first()
    if not zone:
        raise ValueError(f"Zone {merged['zone_id']} not found")

    trigger_type = _trigger_type_from_string(merged.get("trigger_type"))
    now = utcnow()
    source_data: dict[str, Any] = {
        "source": "manual_admin_demo",
        "created_via": "demo_scenario_runner",
        "scenario_type": scenario_type,
        "mock_payout_mode": True,
        "force_fired": not merged.get("enforce_restrictions", True),
        "auto_mark_paid": bool(merged.get("auto_mark_paid")),
        "run_requested_at": now.isoformat(),
    }
    cleanup_actions: list[str] = []
    injected_sustained = False
    city_suspension_applied = False

    if merged.get("inject_sustained_days", 0):
        inject_sustained_event_history(zone.id, trigger_type, db, days=int(merged["inject_sustained_days"]))
        injected_sustained = True
        cleanup_actions.append("clear_sustained_history")

    if any(merged.get(key) is not None for key in ("partial_factor_override", "expected_orders", "actual_orders")):
        partial = set_partial_disruption_data(
            zone.id,
            expected_orders=merged.get("expected_orders"),
            actual_orders=merged.get("actual_orders"),
            partial_factor_override=merged.get("partial_factor_override"),
        )
        source_data.update(partial)
        cleanup_actions.append("clear_partial_disruption")

    if scenario_type == "city_suspension":
        for city_zone in db.query(Zone).filter(Zone.city == zone.city).all():
            city_zone.is_suspended = True
        db.commit()
        city_suspension_applied = True
        cleanup_actions.append("restore_city_suspension")

    production_before = _purchase_preview(zone.id, db, demo_override=False)

    existing = (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == zone.id,
            TriggerEvent.trigger_type == trigger_type,
            TriggerEvent.ended_at.is_(None),
        )
        .first()
    )
    if existing:
        raise ValueError(
            f"Active {trigger_type.value} trigger already exists for {zone.name}. Clean it up before running another scenario."
        )

    trigger = TriggerEvent(
        zone_id=zone.id,
        trigger_type=trigger_type,
        severity=int(merged.get("severity", 4)),
        started_at=now,
        ended_at=None,
        source_data=json.dumps(source_data),
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    cleanup_actions.append("end_trigger")

    claims = process_trigger_event(trigger, db, disruption_hours=merged.get("disruption_hours"))
    if merged.get("auto_mark_paid"):
        for claim in claims:
            if claim.status == ClaimStatus.APPROVED:
                process_payout(claim, db, skip_hard_cap_check=True)
        db.commit()
        for claim in claims:
            db.refresh(claim)

    production_after = _purchase_preview(zone.id, db, demo_override=False)
    demo_after = _purchase_preview(zone.id, db, demo_override=True)

    sustained_record = (
        db.query(SustainedEvent)
        .filter(SustainedEvent.zone_id == zone.id, SustainedEvent.trigger_type == trigger_type)
        .first()
    )

    run_id = next(_run_counter)
    run_summary = {
        "run_id": run_id,
        "scenario_type": scenario_type,
        "status": "completed",
        "executed_at": utcnow().isoformat(),
        "zone": {"id": zone.id, "name": zone.name, "code": zone.code, "city": zone.city, "is_suspended": zone.is_suspended},
        "trigger": {"id": trigger.id, "type": trigger.trigger_type.value, "severity": trigger.severity, "started_at": trigger.started_at.isoformat(), "active": trigger.ended_at is None},
        "claims": {"summary": _claim_summary(claims), "items": [_claim_view(claim) for claim in claims[:20]]},
        "visibility": {
            "partner_zone_alert": True,
            "partner_claims_history": len(claims) > 0,
            "partner_latest_payout_banner": any(claim.status == ClaimStatus.PAID for claim in claims),
            "admin_claims_queue": len(claims) > 0,
        },
        "purchase_checks": {
            "before_run_production": production_before,
            "after_run_production": production_after,
            "after_run_demo_override": demo_after,
        },
        "sustained_event": {
            "injected": injected_sustained,
            "record_present": sustained_record is not None,
            "is_sustained": bool(sustained_record.is_sustained) if sustained_record else False,
            "consecutive_days": sustained_record.consecutive_days if sustained_record else 0,
        },
        "partial_disruption": get_partial_disruption_data(zone.id),
        "city_suspension": {"applied": city_suspension_applied, "city": zone.city},
        "payout_mode": {"mode": "mock_only", "description": "Real triggers and claims on the real DB, with mocked payout processing only."},
        "cleanup": {"available": True, "actions": cleanup_actions},
    }
    _demo_runs[run_id] = run_summary
    return run_summary


def cleanup_demo_run(run_id: int, db: Session) -> dict[str, Any]:
    run = _demo_runs.get(run_id)
    if not run:
        raise ValueError(f"Demo run {run_id} not found")

    trigger_id = run.get("trigger", {}).get("id")
    zone_id = run.get("zone", {}).get("id")
    trigger_type = run.get("trigger", {}).get("type")
    cleanup_log: list[str] = []

    if trigger_id:
        trigger = db.query(TriggerEvent).filter(TriggerEvent.id == trigger_id).first()
        if trigger and trigger.ended_at is None:
            trigger.ended_at = utcnow()
            cleanup_log.append(f"ended trigger {trigger_id}")
            run["trigger"]["active"] = False
            run["trigger"]["ended_at"] = trigger.ended_at.isoformat()

    if zone_id and "clear_partial_disruption" in run.get("cleanup", {}).get("actions", []):
        clear_partial_disruption_data(zone_id)
        cleanup_log.append(f"cleared partial disruption for zone {zone_id}")

    if zone_id and trigger_type and "clear_sustained_history" in run.get("cleanup", {}).get("actions", []):
        clear_sustained_event(zone_id, _trigger_type_from_string(trigger_type), db)
        cleanup_log.append(f"cleared sustained history for zone {zone_id}/{trigger_type}")

    if run.get("city_suspension", {}).get("applied"):
        city = run["zone"]["city"]
        for city_zone in db.query(Zone).filter(Zone.city == city).all():
            city_zone.is_suspended = False
        cleanup_log.append(f"restored city suspension flags for {city}")

    db.commit()
    run["status"] = "cleaned_up"
    run["cleaned_up_at"] = utcnow().isoformat()
    run["cleanup_log"] = cleanup_log
    return run


def set_demo_mode(enabled: bool) -> bool:
    settings = get_settings()
    settings.demo_mode = enabled
    return settings.demo_mode


def get_demo_mode_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "enabled": settings.demo_mode,
        "mode": "demo_override" if settings.demo_mode else "production",
        "bypasses_active": {
            "adverse_selection": settings.demo_mode,
            "activity_gate": settings.demo_mode,
            "fraud_rejection": False,
        } if settings.demo_mode else {},
        "description": (
            "Demo mode: Bypasses purchase restrictions for walkthroughs while keeping the real trigger and claims pipeline intact."
            if settings.demo_mode
            else "Production mode: all purchase and claim safeguards are active."
        ),
        "demo_exempt_cities": settings.demo_exempt_cities,
        "recent_runs": _recent_runs(limit=5),
    }
