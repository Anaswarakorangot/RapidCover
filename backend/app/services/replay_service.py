"""
Replay Service - Scripted historical and demo scenarios for RapidCover.

Allows replaying specific trigger conditions and claims processing logic
for demonstration and drill purposes.
"""

import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.trigger_event import TriggerEvent, TriggerType
from app.models.zone import Zone
from app.models.fraud import PartnerGPSPing
from app.services.claims_processor import process_trigger_event
from app.utils.time_utils import utcnow

REPLAY_SCENARIOS = {
    "mumbai_monsoon_2024": {
        "label": "Mumbai Monsoon (July 2024)",
        "trigger_type": TriggerType.RAIN,
        "severity": 5,
        "description": "Scripted replay of the record July 2024 floods. Triggers 100% payout check for all active riders in the zone.",
        "source_data": {
            "rainfall_mm_hr": 115.0,
            "threshold": 55.0,
            "data_source": "historical_replay",
            "oracle_agreement_score": 0.98,
        }
    },
    "delhi_aqi_crisis": {
        "label": "Delhi Winter AQI Crisis (Nov 2025)",
        "trigger_type": TriggerType.AQI,
        "severity": 4,
        "description": "Hazardous AQI simulation (Level 400+). Triggers protective income shifts for dark store partners.",
        "source_data": {
            "aqi": 425.0,
            "pm25": 380.0,
            "threshold": 400.0,
            "data_source": "historical_replay",
        }
    },
    "fraud_attack_mumbai": {
        "label": "Organized Fraud Attack (Mumbai Central)",
        "trigger_type": TriggerType.RAIN,
        "severity": 5,
        "description": "Simulates a coordinated GPS spoofing attack during a rain event. CMS should identify the centroid drift cluster.",
        "source_data": {
            "rainfall_mm_hr": 65.0,
            "threshold": 55.0,
            "is_fraud_demo": True,
            "data_source": "historical_replay",
        },
        "inject_fraud": True
    }
}

def trigger_replay_scenario(
    scenario_name: str, 
    db: Session, 
    target_zone_code: Optional[str] = None
) -> dict:
    """
    Execute a scripted replay scenario. Verifies zone, injects trigger, 
    and optionally injects fraudulent GPS data before running the claims processor.
    """
    if scenario_name not in REPLAY_SCENARIOS:
        raise ValueError(f"Scenario '{scenario_name}' not found.")

    config = REPLAY_SCENARIOS[scenario_name]
    
    # Identify target zone
    if target_zone_code:
        zone = db.query(Zone).filter(Zone.code == target_zone_code).first()
    else:
        # Fallback to first zone in a city mentioned in label, or just the first zone
        if "Mumbai" in config["label"]:
            zone = db.query(Zone).filter(Zone.city.ilike("%Mumbai%")).first()
        elif "Delhi" in config["label"]:
            zone = db.query(Zone).filter(Zone.city.ilike("%Delhi%")).first()
        else:
            zone = db.query(Zone).first()

    if not zone:
        # Emergency fallback for empty DB
        raise ValueError("No matching zone found for replay.")

    # 1. Inject the Trigger Event
    trigger = TriggerEvent(
        zone_id=zone.id,
        trigger_type=config["trigger_type"],
        started_at=utcnow(),
        severity=config["severity"],
        source_data=json.dumps({
            **config["source_data"],
            "source": f"REPLAY:{scenario_name}",
            "force_fired": True,  # Ensure demo bypasses some production restrictions
            "replay_mode": True
        })
    )
    db.add(trigger)
    db.flush() # Get ID

    # 2. (Optional) Inject Fraud for demo
    if config.get("inject_fraud"):
        _inject_fraudulent_pings(zone, db)

    # 3. Process the event
    claims = process_trigger_event(trigger, db)
    
    return {
        "scenario": scenario_name,
        "trigger_id": trigger.id,
        "zone_code": zone.code,
        "claims_created": len(claims),
        "status": "success"
    }

def _inject_fraudulent_pings(zone: Zone, db: Session):
    """
    Injects a 'cluster' of GPS pings that are physically displaced 
    from the dark store by 8km to trigger 'centroid drift' flags in the fraud engine.
    """
    from app.models.partner import Partner
    
    # Get a few partners in this zone
    partners = db.query(Partner).filter(Partner.zone_id == zone.id).limit(5).all()
    
    now = utcnow()
    # Dark store is at zone.dark_store_lat, zone.dark_store_lng
    # We shift them away by 0.1 degree (approx 10-11km)
    spoof_lat = zone.dark_store_lat + 0.1
    spoof_lng = zone.dark_store_lng + 0.1

    for p in partners:
        ping = PartnerGPSPing(
            partner_id=p.id,
            lat=spoof_lat,
            lng=spoof_lng,
            created_at=now
        )
        db.add(ping)
    
    db.commit()

def get_replay_scenarios_list() -> List[dict]:
    """Returns a list of scenarios for the frontend dropdown."""
    return [
        {"id": k, "label": v["label"], "description": v["description"]}
        for k, v in REPLAY_SCENARIOS.items()
    ]
