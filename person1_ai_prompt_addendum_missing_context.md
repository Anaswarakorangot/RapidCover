# Addendum: Missing Context Files for Person 1 Prompt

These files were referenced by tests/components but were not included in the earlier prompt. Use this as additional context. Preserve public APIs unless changes are required by the Person 1 scope.

--- FILE: backend/app/services/multi_trigger_resolver.py ---
``python
"""
Multi-Trigger Resolver for RapidCover.

Prevents duplicate payouts when multiple triggers fire together (e.g., rain + AQI + shutdown).
Groups triggers by partner + zone within a 6-hour window. Highest payout wins with optional
10% uplift for confirmed severe disruption.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy
from app.models.partner import Partner
from app.models.trigger_event import TriggerEvent, TriggerType


# Configuration
AGGREGATION_WINDOW_HOURS = 6
SEVERE_DISRUPTION_UPLIFT_PERCENT = 10.0  # 10% uplift for 3+ simultaneous triggers


def generate_aggregation_group_id() -> str:
    """Generate a unique aggregation group ID."""
    return f"AGG-{uuid.uuid4().hex[:12].upper()}"


def find_triggers_in_window(
    zone_id: int,
    window_start: datetime,
    window_end: datetime,
    db: Session,
) -> list[TriggerEvent]:
    """
    Find all trigger events in a zone within a time window.

    Args:
        zone_id: Zone to search
        window_start: Start of time window
        window_end: End of time window
        db: Database session

    Returns:
        List of TriggerEvent objects in the window
    """
    return (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == zone_id,
            TriggerEvent.started_at >= window_start,
            TriggerEvent.started_at <= window_end,
        )
        .order_by(TriggerEvent.started_at.asc())
        .all()
    )


def find_existing_claim_in_window(
    policy_id: int,
    zone_id: int,
    window_start: datetime,
    window_end: datetime,
    db: Session,
) -> Optional[Claim]:
    """
    Find an existing claim for a policy in the aggregation window.

    Args:
        policy_id: Policy to check
        zone_id: Zone ID for the trigger
        window_start: Start of aggregation window
        window_end: End of aggregation window
        db: Database session

    Returns:
        Existing Claim if found, None otherwise
    """
    return (
        db.query(Claim)
        .join(TriggerEvent, Claim.trigger_event_id == TriggerEvent.id)
        .filter(
            Claim.policy_id == policy_id,
            TriggerEvent.zone_id == zone_id,
            Claim.created_at >= window_start,
            Claim.created_at <= window_end,
            Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED, ClaimStatus.PAID]),
        )
        .order_by(Claim.created_at.asc())
        .first()
    )


def calculate_aggregation_window(trigger_time: datetime) -> tuple[datetime, datetime]:
    """
    Calculate the 6-hour aggregation window centered around the trigger time.

    Returns (window_start, window_end)
    """
    # Window is 3 hours before to 3 hours after
    window_start = trigger_time - timedelta(hours=AGGREGATION_WINDOW_HOURS / 2)
    window_end = trigger_time + timedelta(hours=AGGREGATION_WINDOW_HOURS / 2)
    return (window_start, window_end)


def should_apply_severe_disruption_uplift(triggers: list[TriggerEvent]) -> bool:
    """
    Determine if severe disruption uplift should apply.

    Uplift applies when 3+ distinct trigger types fire simultaneously.
    """
    unique_types = set(t.trigger_type for t in triggers)
    return len(unique_types) >= 3


def calculate_aggregated_payout(
    triggers: list[TriggerEvent],
    policy: Policy,
    base_payouts: dict[int, float],
) -> tuple[float, dict]:
    """
    Calculate the aggregated payout for multiple triggers.

    Strategy: Highest payout wins, with optional uplift for severe disruption.

    Args:
        triggers: List of trigger events to aggregate
        policy: The policy for payout calculation
        base_payouts: Dict mapping trigger_id -> calculated payout amount

    Returns:
        (final_payout, aggregation_metadata)
    """
    if not triggers or not base_payouts:
        return (0.0, {})

    # Find the highest payout trigger
    highest_payout = 0.0
    primary_trigger_id = None
    for trigger in triggers:
        payout = base_payouts.get(trigger.id, 0.0)
        if payout > highest_payout:
            highest_payout = payout
            primary_trigger_id = trigger.id

    # Calculate pre-aggregation total (what would have been paid without aggregation)
    pre_aggregation_total = sum(base_payouts.values())

    # Determine if severe disruption uplift applies
    apply_uplift = should_apply_severe_disruption_uplift(triggers)
    uplift_percent = SEVERE_DISRUPTION_UPLIFT_PERCENT if apply_uplift else 0.0
    uplift_amount = highest_payout * (uplift_percent / 100)
    final_payout = highest_payout + uplift_amount

    # Apply policy daily limit
    final_payout = min(final_payout, policy.max_daily_payout)

    # Identify suppressed triggers
    suppressed_trigger_ids = [t.id for t in triggers if t.id != primary_trigger_id]

    # Build aggregation metadata
    aggregation_metadata = {
        "group_id": generate_aggregation_group_id(),
        "is_aggregated": len(triggers) > 1,
        "primary_trigger_id": primary_trigger_id,
        "suppressed_triggers": suppressed_trigger_ids,
        "pre_aggregation_payout": round(pre_aggregation_total, 2),
        "post_aggregation_payout": round(final_payout, 2),
        "savings": round(pre_aggregation_total - final_payout, 2),
        "uplift_applied": apply_uplift,
        "uplift_percent": uplift_percent,
        "uplift_amount": round(uplift_amount, 2),
        "triggers_in_window": [
            {
                "id": t.id,
                "type": t.trigger_type.value,
                "severity": t.severity,
                "payout": base_payouts.get(t.id, 0.0),
                "started_at": t.started_at.isoformat() if t.started_at else None,
            }
            for t in triggers
        ],
        "window_hours": AGGREGATION_WINDOW_HOURS,
        "aggregated_at": datetime.utcnow().isoformat(),
    }

    return (final_payout, aggregation_metadata)


def check_and_resolve_aggregation(
    trigger_event: TriggerEvent,
    policy: Policy,
    calculated_payout: float,
    db: Session,
) -> tuple[bool, Optional[Claim], dict]:
    """
    Check if this trigger should be aggregated with existing claims.

    This is the main entry point called from claims_processor.

    Args:
        trigger_event: The new trigger event
        policy: Policy being claimed against
        calculated_payout: The payout calculated for this trigger alone
        db: Database session

    Returns:
        (should_create_new_claim, existing_claim_to_update, aggregation_metadata)

        If should_create_new_claim is True, create a new claim with aggregation_metadata.
        If existing_claim is returned, update it instead of creating new.
    """
    trigger_time = trigger_event.started_at or datetime.utcnow()
    window_start, window_end = calculate_aggregation_window(trigger_time)

    # Check for existing claim in window
    existing_claim = find_existing_claim_in_window(
        policy.id,
        trigger_event.zone_id,
        window_start,
        window_end,
        db,
    )

    if existing_claim is None:
        # No existing claim - this is the first trigger in the window
        # Create new claim with basic aggregation metadata (not yet aggregated)
        aggregation_metadata = {
            "group_id": generate_aggregation_group_id(),
            "is_aggregated": False,
            "primary_trigger_id": trigger_event.id,
            "suppressed_triggers": [],
            "pre_aggregation_payout": round(calculated_payout, 2),
            "post_aggregation_payout": round(calculated_payout, 2),
            "savings": 0.0,
            "uplift_applied": False,
            "uplift_percent": 0.0,
            "uplift_amount": 0.0,
            "triggers_in_window": [
                {
                    "id": trigger_event.id,
                    "type": trigger_event.trigger_type.value,
                    "severity": trigger_event.severity,
                    "payout": calculated_payout,
                    "started_at": trigger_time.isoformat(),
                }
            ],
            "window_hours": AGGREGATION_WINDOW_HOURS,
            "aggregated_at": datetime.utcnow().isoformat(),
        }
        return (True, None, aggregation_metadata)

    # Existing claim found - this trigger should be aggregated
    # Parse existing claim's aggregation data
    existing_validation = {}
    try:
        existing_validation = json.loads(existing_claim.validation_data or "{}")
    except json.JSONDecodeError:
        pass

    existing_aggregation = existing_validation.get("aggregation", {})

    # Get all triggers in window including current
    triggers_in_window = find_triggers_in_window(trigger_event.zone_id, window_start, window_end, db)

    # Build payout map - use existing data plus new trigger
    base_payouts = {}
    for tw in existing_aggregation.get("triggers_in_window", []):
        base_payouts[tw["id"]] = tw["payout"]
    base_payouts[trigger_event.id] = calculated_payout

    # Calculate new aggregated payout
    final_payout, new_aggregation = calculate_aggregated_payout(
        triggers_in_window,
        policy,
        base_payouts,
    )

    # Preserve the original group ID
    new_aggregation["group_id"] = existing_aggregation.get("group_id", new_aggregation["group_id"])

    # Check if new trigger has higher payout than current claim
    if calculated_payout > existing_claim.amount:
        # Update existing claim with higher payout
        new_aggregation["primary_trigger_id"] = trigger_event.id
        new_aggregation["post_aggregation_payout"] = round(final_payout, 2)

        # Don't create new claim - update existing
        return (False, existing_claim, new_aggregation)
    else:
        # Current trigger is suppressed - just update aggregation metadata
        return (False, existing_claim, new_aggregation)


def update_claim_with_aggregation(
    claim: Claim,
    new_payout: float,
    aggregation_metadata: dict,
    db: Session,
) -> Claim:
    """
    Update an existing claim with new aggregation data.

    Args:
        claim: The claim to update
        new_payout: New payout amount (may be higher due to uplift)
        aggregation_metadata: Updated aggregation metadata
        db: Database session

    Returns:
        Updated Claim
    """
    validation = {}
    try:
        validation = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        pass

    validation["aggregation"] = aggregation_metadata

    # Update claim
    claim.amount = new_payout
    claim.validation_data = json.dumps(validation)

    db.commit()
    db.refresh(claim)

    return claim


def get_aggregation_stats(db: Session) -> dict:
    """
    Get statistics about trigger aggregation.

    Returns dict with:
    - total_aggregated_claims: Claims with aggregation
    - total_triggers_suppressed: Triggers that didn't generate separate claims
    - total_savings: Sum of prevented duplicate payouts
    """
    # Query all claims with aggregation data
    claims = db.query(Claim).filter(
        Claim.validation_data.ilike('%"is_aggregated": true%')
    ).all()

    total_aggregated = 0
    total_suppressed = 0
    total_savings = 0.0

    for claim in claims:
        try:
            validation = json.loads(claim.validation_data or "{}")
            aggregation = validation.get("aggregation", {})

            if aggregation.get("is_aggregated"):
                total_aggregated += 1
                total_suppressed += len(aggregation.get("suppressed_triggers", []))
                total_savings += aggregation.get("savings", 0.0)
        except json.JSONDecodeError:
            continue

    return {
        "total_aggregated_claims": total_aggregated,
        "total_triggers_suppressed": total_suppressed,
        "total_savings": round(total_savings, 2),
        "computed_at": datetime.utcnow().isoformat(),
    }


def get_claim_aggregation_details(claim_id: int, db: Session) -> Optional[dict]:
    """
    Get aggregation details for a specific claim.

    Returns the aggregation metadata or None if not found.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        return None

    try:
        validation = json.loads(claim.validation_data or "{}")
        return validation.get("aggregation")
    except json.JSONDecodeError:
        return None
````

--- FILE: backend/app/services/riqi_service.py ---
``python
"""
RIQI (Road Infrastructure Quality Index) service with DB-driven provenance.

Reads RIQI scores from zone_risk_profiles table first, falling back to
city-level defaults when zone data is not available.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.zone import Zone
from app.models.zone_risk_profile import ZoneRiskProfile
from app.schemas.riqi import (
    RiqiInputMetrics,
    RiqiProvenanceResponse,
    RiqiListResponse,
    RiqiRecomputeResponse,
)
from app.services.premium_service import (
    CITY_RIQI_SCORES,
    RIQI_PAYOUT_MULTIPLIER,
    RIQI_PREMIUM_ADJUSTMENT,
    get_riqi_band,
)


def _ensure_zone_risk_profiles_table(db: Session) -> None:
    """Create the zone_risk_profiles table if it doesn't exist."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS zone_risk_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER UNIQUE NOT NULL,
            riqi_score REAL NOT NULL DEFAULT 55.0,
            riqi_band VARCHAR(20) NOT NULL DEFAULT 'urban_fringe',
            historical_suspensions INTEGER DEFAULT 0,
            closure_frequency REAL DEFAULT 0.0,
            weather_severity_freq REAL DEFAULT 0.0,
            aqi_severity_freq REAL DEFAULT 0.0,
            zone_density REAL DEFAULT 0.0,
            calculated_from VARCHAR(50) NOT NULL DEFAULT 'seeded',
            last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (zone_id) REFERENCES zones (id)
        )
    """))
    db.commit()


def get_riqi_for_zone(
    zone_id: int,
    db: Session,
    zone: Optional[Zone] = None,
) -> RiqiProvenanceResponse:
    """
    Get RIQI data for a zone with full provenance.

    First checks zone_risk_profiles table, then falls back to city defaults.

    Args:
        zone_id: The zone ID
        db: Database session
        zone: Optional pre-fetched Zone object

    Returns:
        RiqiProvenanceResponse with score, band, and provenance info
    """
    _ensure_zone_risk_profiles_table(db)

    if not zone:
        zone = db.query(Zone).filter(Zone.id == zone_id).first()

    if not zone:
        # Return a default response for missing zone
        return RiqiProvenanceResponse(
            zone_id=zone_id,
            zone_code="UNKNOWN",
            zone_name="Unknown Zone",
            city="unknown",
            riqi_score=55.0,
            riqi_band="urban_fringe",
            payout_multiplier=RIQI_PAYOUT_MULTIPLIER["urban_fringe"],
            premium_adjustment=RIQI_PREMIUM_ADJUSTMENT["urban_fringe"],
            input_metrics=RiqiInputMetrics(
                historical_suspensions=0,
                closure_frequency=0.0,
                weather_severity_freq=0.0,
                aqi_severity_freq=0.0,
                zone_density=0.0,
            ),
            calculated_from="fallback_city_default",
            last_updated_at=None,
        )

    # Try to get from zone_risk_profiles table
    profile = db.query(ZoneRiskProfile).filter(ZoneRiskProfile.zone_id == zone_id).first()

    if profile:
        # Use DB data
        riqi_band = profile.riqi_band
        return RiqiProvenanceResponse(
            zone_id=zone_id,
            zone_code=zone.code,
            zone_name=zone.name,
            city=zone.city,
            riqi_score=profile.riqi_score,
            riqi_band=riqi_band,
            payout_multiplier=RIQI_PAYOUT_MULTIPLIER.get(riqi_band, 1.25),
            premium_adjustment=RIQI_PREMIUM_ADJUSTMENT.get(riqi_band, 1.15),
            input_metrics=RiqiInputMetrics(
                historical_suspensions=profile.historical_suspensions,
                closure_frequency=profile.closure_frequency,
                weather_severity_freq=profile.weather_severity_freq,
                aqi_severity_freq=profile.aqi_severity_freq,
                zone_density=profile.zone_density,
            ),
            calculated_from=profile.calculated_from,
            last_updated_at=profile.last_updated_at,
        )

    # Fallback to city default
    city_lower = zone.city.lower()
    riqi_score = CITY_RIQI_SCORES.get(city_lower, 55.0)
    riqi_band = get_riqi_band(riqi_score)

    return RiqiProvenanceResponse(
        zone_id=zone_id,
        zone_code=zone.code,
        zone_name=zone.name,
        city=zone.city,
        riqi_score=riqi_score,
        riqi_band=riqi_band,
        payout_multiplier=RIQI_PAYOUT_MULTIPLIER.get(riqi_band, 1.25),
        premium_adjustment=RIQI_PREMIUM_ADJUSTMENT.get(riqi_band, 1.15),
        input_metrics=RiqiInputMetrics(
            historical_suspensions=0,
            closure_frequency=0.0,
            weather_severity_freq=0.0,
            aqi_severity_freq=0.0,
            zone_density=0.0,
        ),
        calculated_from="fallback_city_default",
        last_updated_at=None,
    )


def get_riqi_by_zone_code(zone_code: str, db: Session) -> Optional[RiqiProvenanceResponse]:
    """Get RIQI data for a zone by its code."""
    zone = db.query(Zone).filter(Zone.code == zone_code).first()
    if not zone:
        return None
    return get_riqi_for_zone(zone.id, db, zone=zone)


def get_all_riqi_profiles(db: Session) -> RiqiListResponse:
    """
    Get RIQI profiles for all zones.

    Returns:
        RiqiListResponse with all zone profiles and metadata
    """
    _ensure_zone_risk_profiles_table(db)

    zones = db.query(Zone).order_by(Zone.city, Zone.name).all()
    profiles = []
    from_db_count = 0

    for zone in zones:
        profile = get_riqi_for_zone(zone.id, db, zone=zone)
        profiles.append(profile)
        if profile.calculated_from != "fallback_city_default":
            from_db_count += 1

    data_source = "database" if from_db_count == len(zones) else "mixed"

    return RiqiListResponse(
        zones=profiles,
        total=len(profiles),
        data_source=data_source,
    )


def seed_zone_risk_profiles(db: Session) -> int:
    """
    Seed zone_risk_profiles for all zones with city-based defaults.

    Returns number of profiles created.
    """
    _ensure_zone_risk_profiles_table(db)

    zones = db.query(Zone).all()
    created = 0

    # Zone-specific RIQI overrides (more granular than city defaults)
    ZONE_RIQI_OVERRIDES = {
        # Bangalore zones
        "BLR-KRM": {"riqi_score": 65.0, "closure_frequency": 0.8, "weather_severity_freq": 1.2},   # Koramangala - better infra
        "BLR-IND": {"riqi_score": 68.0, "closure_frequency": 0.5, "weather_severity_freq": 0.9},   # Indiranagar - good area
        "BLR-HSR": {"riqi_score": 60.0, "closure_frequency": 1.0, "weather_severity_freq": 1.5},   # HSR - medium
        "BLR-WFD": {"riqi_score": 55.0, "closure_frequency": 1.2, "weather_severity_freq": 1.8},   # Whitefield - outer, worse
        "BLR-BEL": {"riqi_score": 48.0, "closure_frequency": 1.8, "weather_severity_freq": 2.5},   # Bellandur - flood-prone

        # Mumbai zones
        "MUM-AND": {"riqi_score": 52.0, "closure_frequency": 1.5, "weather_severity_freq": 2.0},   # Andheri - flood-prone
        "MUM-BAN": {"riqi_score": 58.0, "closure_frequency": 1.0, "weather_severity_freq": 1.5},   # Bandra - better
        "MUM-POW": {"riqi_score": 45.0, "closure_frequency": 2.0, "weather_severity_freq": 2.2},   # Powai - lake area

        # Delhi zones
        "DEL-CP": {"riqi_score": 72.0, "closure_frequency": 0.5, "aqi_severity_freq": 3.0},        # Connaught Place - urban core
        "DEL-SAK": {"riqi_score": 60.0, "closure_frequency": 0.8, "aqi_severity_freq": 2.5},       # Saket - medium
        "DEL-DWK": {"riqi_score": 55.0, "closure_frequency": 1.0, "aqi_severity_freq": 2.8},       # Dwarka - outer
    }

    for zone in zones:
        # Check if already exists
        existing = db.query(ZoneRiskProfile).filter(ZoneRiskProfile.zone_id == zone.id).first()
        if existing:
            continue

        # Get zone-specific or city default
        city_default = CITY_RIQI_SCORES.get(zone.city.lower(), 55.0)
        override = ZONE_RIQI_OVERRIDES.get(zone.code, {})

        riqi_score = override.get("riqi_score", city_default)
        riqi_band = get_riqi_band(riqi_score)

        profile = ZoneRiskProfile(
            zone_id=zone.id,
            riqi_score=riqi_score,
            riqi_band=riqi_band,
            historical_suspensions=override.get("historical_suspensions", 0),
            closure_frequency=override.get("closure_frequency", 1.0),
            weather_severity_freq=override.get("weather_severity_freq", 1.0),
            aqi_severity_freq=override.get("aqi_severity_freq", 1.0),
            zone_density=override.get("zone_density", 50.0),
            calculated_from="seeded",
        )

        db.add(profile)
        created += 1

    if created:
        db.commit()

    return created


def recompute_riqi_for_zone(zone_code: str, db: Session) -> Optional[RiqiRecomputeResponse]:
    """
    Recompute RIQI score for a zone based on current metrics.

    This is a simplified recomputation - in production, this would
    use actual historical data from triggers, closures, etc.

    Returns:
        RiqiRecomputeResponse or None if zone not found
    """
    _ensure_zone_risk_profiles_table(db)

    zone = db.query(Zone).filter(Zone.code == zone_code).first()
    if not zone:
        return None

    profile = db.query(ZoneRiskProfile).filter(ZoneRiskProfile.zone_id == zone.id).first()

    old_score = profile.riqi_score if profile else CITY_RIQI_SCORES.get(zone.city.lower(), 55.0)
    old_band = profile.riqi_band if profile else get_riqi_band(old_score)

    # Simplified recomputation formula:
    # RIQI = 100 - (suspensions * 2 + closures * 5 + weather * 3 + aqi * 3 + density_penalty)
    # Clamped to [0, 100]

    if profile:
        suspensions = profile.historical_suspensions
        closures = profile.closure_frequency
        weather = profile.weather_severity_freq
        aqi = profile.aqi_severity_freq
        density = profile.zone_density
    else:
        suspensions = 0
        closures = 1.0
        weather = 1.0
        aqi = 1.0
        density = 50.0

    # Density penalty: high density = more partners = more claims = slightly lower RIQI
    density_penalty = max(0, (density - 100) * 0.05)

    new_score = 100 - (
        suspensions * 2 +
        closures * 5 +
        weather * 3 +
        aqi * 3 +
        density_penalty
    )
    new_score = max(0, min(100, round(new_score, 1)))
    new_band = get_riqi_band(new_score)

    # Update or create profile
    if profile:
        profile.riqi_score = new_score
        profile.riqi_band = new_band
        profile.calculated_from = "computed"
        profile.last_updated_at = datetime.utcnow()
    else:
        profile = ZoneRiskProfile(
            zone_id=zone.id,
            riqi_score=new_score,
            riqi_band=new_band,
            historical_suspensions=suspensions,
            closure_frequency=closures,
            weather_severity_freq=weather,
            aqi_severity_freq=aqi,
            zone_density=density,
            calculated_from="computed",
        )
        db.add(profile)

    db.commit()

    return RiqiRecomputeResponse(
        zone_code=zone_code,
        old_riqi_score=old_score,
        new_riqi_score=new_score,
        old_band=old_band,
        new_band=new_band,
        recomputed_at=datetime.utcnow(),
        metrics_used=RiqiInputMetrics(
            historical_suspensions=suspensions,
            closure_frequency=closures,
            weather_severity_freq=weather,
            aqi_severity_freq=aqi,
            zone_density=density,
        ),
    )


def get_riqi_score_for_premium(
    city: str,
    zone_id: Optional[int],
    db: Session,
) -> tuple[float, str, str]:
    """
    Get RIQI score for premium calculation with provenance.

    This function is called by premium_service.py to get RIQI data.

    Args:
        city: City name
        zone_id: Optional zone ID

    Returns:
        (riqi_score, riqi_band, calculated_from)
    """
    if zone_id:
        _ensure_zone_risk_profiles_table(db)

        profile = db.query(ZoneRiskProfile).filter(ZoneRiskProfile.zone_id == zone_id).first()
        if profile:
            return profile.riqi_score, profile.riqi_band, profile.calculated_from

    # Fallback to city default
    riqi_score = CITY_RIQI_SCORES.get(city.lower(), 55.0)
    riqi_band = get_riqi_band(riqi_score)

    return riqi_score, riqi_band, "fallback_city_default"
````

--- FILE: backend/app/services/stress_scenario_service.py ---
``python
"""
Stress scenario service for monsoon reserve-needed calculations.

Models different disaster scenarios and calculates the reserve needed
to cover projected claims above the available city reserve.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.partner import Partner
from app.models.policy import Policy
from app.models.zone import Zone
from app.models.claim import Claim, ClaimStatus
from app.schemas.stress_scenarios import (
    StressScenarioResponse,
    StressScenarioListResponse,
    StressCityMetrics,
)


# Scenario definitions with trigger probabilities and severity multipliers
STRESS_SCENARIOS = {
    "monsoon_14day_bangalore": {
        "name": "14-Day Monsoon Stress (Bangalore)",
        "days": 14,
        "city": "bangalore",
        "trigger_probability": 0.75,  # 75% of policies will have claims
        "severity_multiplier": 1.3,   # Higher severity due to sustained rain
        "assumptions": [
            "Heavy rain (>55mm/hr) sustained for 14 consecutive days",
            "All Bangalore zones affected uniformly",
            "75% of active policies will generate claims",
            "Average claim amount increased by 30% due to sustained event",
        ],
    },
    "aqi_crisis_7day_delhi": {
        "name": "7-Day AQI Crisis (Delhi NCR)",
        "days": 7,
        "city": "delhi",
        "trigger_probability": 0.85,  # 85% of policies will have claims
        "severity_multiplier": 1.2,
        "assumptions": [
            "AQI sustained above 400 for 7 consecutive days",
            "All Delhi zones affected uniformly",
            "85% of active policies will generate claims",
            "Includes Connaught Place, Saket, and Dwarka zones",
        ],
    },
    "citywide_bandh_3day_mumbai": {
        "name": "3-Day City-wide Bandh (Mumbai)",
        "days": 3,
        "city": "mumbai",
        "trigger_probability": 0.95,  # Near total disruption
        "severity_multiplier": 1.5,   # Civic shutdowns are most impactful
        "assumptions": [
            "Complete civic shutdown for 3 consecutive days",
            "All Mumbai zones affected (Andheri, Bandra, Powai)",
            "95% of active policies will generate claims",
            "Maximum payout per day applied",
        ],
    },
    "combined_monsoon_heat_bengaluru": {
        "name": "Monsoon + Heat Wave Combo (Bangalore)",
        "days": 7,
        "city": "bangalore",
        "trigger_probability": 0.80,
        "severity_multiplier": 1.4,
        "assumptions": [
            "Heavy rain in morning, extreme heat (>43Â°C) in afternoon",
            "Double trigger events per day possible",
            "80% of active policies will generate claims",
            "Compounded severity due to multiple trigger types",
        ],
    },
}

# Average payout per claim per tier (based on TIER_CONFIG defaults)
AVG_PAYOUT_BY_TIER = {
    "flex": 200,      # Average ~Rs.200 per claim (max Rs.250/day)
    "standard": 320,  # Average ~Rs.320 per claim (max Rs.400/day)
    "pro": 400,       # Average ~Rs.400 per claim (max Rs.500/day)
}


def get_city_metrics(city: str, db: Session, days: int = 7) -> StressCityMetrics:
    """
    Get city-level metrics for stress calculations.

    Args:
        city: City name (case-insensitive match)
        db: Database session
        days: Days to look back for premium calculations

    Returns:
        StressCityMetrics with active policies, premiums, and zones
    """
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all zones in the city
    city_zones = db.query(Zone).filter(Zone.city.ilike(f"%{city}%")).all()
    zone_ids = [z.id for z in city_zones]

    if not zone_ids:
        return StressCityMetrics(
            city=city,
            active_policies=0,
            avg_weekly_premium=0.0,
            total_weekly_reserve=0.0,
            zone_count=0,
        )

    # Get partners in these zones
    partner_ids_query = db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids))
    partner_ids = [p[0] for p in partner_ids_query.all()]

    if not partner_ids:
        return StressCityMetrics(
            city=city,
            active_policies=0,
            avg_weekly_premium=0.0,
            total_weekly_reserve=0.0,
            zone_count=len(zone_ids),
        )

    # Count active policies
    active_policies = (
        db.query(func.count(Policy.id))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .scalar()
    ) or 0

    # Calculate total weekly premiums collected recently
    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0.0

    avg_premium = total_premiums / active_policies if active_policies > 0 else 0.0

    return StressCityMetrics(
        city=city,
        active_policies=active_policies,
        avg_weekly_premium=round(avg_premium, 2),
        total_weekly_reserve=round(float(total_premiums), 2),
        zone_count=len(zone_ids),
    )


def calculate_stress_scenario(
    scenario_id: str,
    db: Session,
) -> StressScenarioResponse:
    """
    Calculate reserve needed for a specific stress scenario.

    Formula:
        projected_claims = active_policies Ã— trigger_probability Ã— days
        projected_payout = projected_claims Ã— avg_payout Ã— severity_multiplier
        reserve_needed = max(projected_payout - city_reserve_available, 0)

    Args:
        scenario_id: The scenario identifier
        db: Database session

    Returns:
        StressScenarioResponse with full breakdown
    """
    scenario = STRESS_SCENARIOS.get(scenario_id)
    if not scenario:
        return StressScenarioResponse(
            scenario_id=scenario_id,
            scenario_name="Unknown Scenario",
            days=0,
            projected_claims=0,
            projected_payout=0.0,
            city_reserve_available=0.0,
            reserve_needed=0.0,
            formula_breakdown={},
            assumptions=["Scenario not found"],
            data_source="mock",
        )

    city = scenario["city"]
    days = scenario["days"]
    trigger_probability = scenario["trigger_probability"]
    severity_multiplier = scenario["severity_multiplier"]

    # Get city metrics
    metrics = get_city_metrics(city, db, days=7)

    # Calculate projected claims
    # Each policy can have 1 claim per day during the stress period
    projected_claims = int(metrics.active_policies * trigger_probability * days)

    # Calculate average payout (weighted by typical tier distribution)
    # Assume 40% flex, 40% standard, 20% pro
    weighted_avg_payout = (
        AVG_PAYOUT_BY_TIER["flex"] * 0.40 +
        AVG_PAYOUT_BY_TIER["standard"] * 0.40 +
        AVG_PAYOUT_BY_TIER["pro"] * 0.20
    )

    # Apply severity multiplier
    avg_payout_with_severity = weighted_avg_payout * severity_multiplier

    # Calculate projected payout
    projected_payout = projected_claims * avg_payout_with_severity

    # City reserve available = premiums collected in last 7 days
    city_reserve_available = metrics.total_weekly_reserve

    # Reserve needed = gap between projected payout and available reserve
    reserve_needed = max(projected_payout - city_reserve_available, 0)

    # Determine data source
    data_source = "live" if metrics.active_policies > 0 else "mock"

    formula_breakdown = {
        "step_1_active_policies": metrics.active_policies,
        "step_2_trigger_probability": trigger_probability,
        "step_3_days": days,
        "step_4_projected_claims": f"{metrics.active_policies} Ã— {trigger_probability} Ã— {days} = {projected_claims}",
        "step_5_weighted_avg_payout": round(weighted_avg_payout, 2),
        "step_6_severity_multiplier": severity_multiplier,
        "step_7_avg_payout_with_severity": round(avg_payout_with_severity, 2),
        "step_8_projected_payout": f"{projected_claims} Ã— {round(avg_payout_with_severity, 2)} = {round(projected_payout, 2)}",
        "step_9_city_reserve_available": round(city_reserve_available, 2),
        "step_10_reserve_needed": f"max({round(projected_payout, 2)} - {round(city_reserve_available, 2)}, 0) = {round(reserve_needed, 2)}",
        "city_metrics": {
            "city": city,
            "zone_count": metrics.zone_count,
            "avg_weekly_premium": metrics.avg_weekly_premium,
        },
    }

    return StressScenarioResponse(
        scenario_id=scenario_id,
        scenario_name=scenario["name"],
        days=days,
        projected_claims=projected_claims,
        projected_payout=round(projected_payout, 2),
        city_reserve_available=round(city_reserve_available, 2),
        reserve_needed=round(reserve_needed, 2),
        formula_breakdown=formula_breakdown,
        assumptions=scenario["assumptions"],
        data_source=data_source,
    )


def get_all_stress_scenarios(db: Session) -> StressScenarioListResponse:
    """
    Calculate all stress scenarios and return aggregated results.

    Returns:
        StressScenarioListResponse with all scenarios and total reserve needed
    """
    scenarios = []
    total_reserve_needed = 0.0

    for scenario_id in STRESS_SCENARIOS:
        scenario = calculate_stress_scenario(scenario_id, db)
        scenarios.append(scenario)
        total_reserve_needed += scenario.reserve_needed

    return StressScenarioListResponse(
        scenarios=scenarios,
        computed_at=datetime.utcnow(),
        total_reserve_needed=round(total_reserve_needed, 2),
    )


def get_scenario_ids() -> list[str]:
    """Return list of available scenario IDs."""
    return list(STRESS_SCENARIOS.keys())
````

--- FILE: backend/app/services/payout_service.py ---
``python
"""
Payout service for RapidCover.

Handles structured payout processing with full transaction logs,
UPI reference generation, payout audit trails, and city-level caps.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy
from app.models.partner import Partner
from app.models.zone import Zone
from app.models.trigger_event import TriggerEvent, TriggerType
from app.services.notifications import notify_claim_paid
from app.services.payment_state_machine import (
    initiate_payment,
    confirm_payment,
    fail_payment,
    get_payment_status,
    PaymentStatus,
)

logger = logging.getLogger(__name__)

# City-level hard cap configuration
CITY_HARD_CAP_RATIO = 1.20  # 120% - Reinsurance activates above this

TRIGGER_TYPE_LABELS = {
    TriggerType.RAIN: "Heavy Rain",
    TriggerType.HEAT: "Extreme Heat",
    TriggerType.AQI: "High AQI",
    TriggerType.SHUTDOWN: "Civic Shutdown",
    TriggerType.CLOSURE: "Store Closure",
}


def check_city_hard_cap(partner: Partner, db: Session, days: int = 7) -> tuple[bool, float, float]:
    """
    Check if city-level payout hard cap has been reached.

    Reinsurance activates when city payouts exceed 120% of premiums collected.

    Args:
        partner: The partner to check (uses their zone to determine city)
        db: Database session
        days: Number of days to look back (default 7 for weekly)

    Returns tuple of:
        - is_capped: bool - True if city is at/above 120% cap
        - current_ratio: float - Current BCR ratio
        - remaining_capacity: float - Amount in INR that can still be paid out before cap
    """
    if not partner.zone_id:
        # Partner not assigned to zone, allow payout
        return (False, 0.0, float('inf'))

    # Get partner's zone and city
    zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
    if not zone:
        return (False, 0.0, float('inf'))

    city = zone.city
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all zones in the city
    city_zones = db.query(Zone).filter(Zone.city.ilike(f"%{city}%")).all()
    zone_ids = [z.id for z in city_zones]

    if not zone_ids:
        return (False, 0.0, float('inf'))

    # Get partners in these zones
    partner_ids = [
        p[0] for p in
        db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids)).all()
    ]

    if not partner_ids:
        return (False, 0.0, float('inf'))

    # Calculate total premiums collected this period
    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0.0

    # Calculate total claims paid this period
    total_claims_paid = (
        db.query(func.sum(Claim.amount))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id.in_(partner_ids),
            Claim.status == ClaimStatus.PAID,
            Claim.paid_at >= period_start,
            Claim.paid_at <= now,
        )
        .scalar()
    ) or 0.0

    # Calculate current ratio
    current_ratio = total_claims_paid / total_premiums if total_premiums > 0 else 0.0

    # Calculate remaining capacity (up to 120% of premiums)
    max_payout = total_premiums * CITY_HARD_CAP_RATIO
    remaining_capacity = max(0, max_payout - total_claims_paid)

    # Check if capped
    is_capped = current_ratio >= CITY_HARD_CAP_RATIO

    logger.info(
        f"City hard cap check for {city}: "
        f"premiums={total_premiums:.2f}, claims={total_claims_paid:.2f}, "
        f"ratio={current_ratio:.2%}, capped={is_capped}"
    )

    return (is_capped, round(current_ratio, 4), round(remaining_capacity, 2))


def generate_upi_ref(policy_id: int, claim_id: int) -> str:
    """Generate a unique UPI transaction reference."""
    epoch = int(datetime.utcnow().timestamp())
    return f"RAPID{policy_id:06d}{claim_id:06d}{epoch % 100000:05d}"


def build_transaction_log(
    claim: Claim,
    policy: Policy,
    partner: Partner,
    trigger: Optional[TriggerEvent],
    upi_ref: str,
    payout_metadata: dict,
) -> dict:
    """Build a structured transaction log for a payout (stored in validation_data)."""
    # Determine payout channel
    primary_channel = "UPI/Stripe" if partner.upi_id else "IMPS/Bank"
    
    return {
        "transaction": {
            "ref": upi_ref,
            "channel": primary_channel,
            "provider": "Stripe Connect Mock" if partner.upi_id else "IMPS Gateway Mock",
            "amount": claim.amount,
            "currency": "INR",
            "status": "SUCCESS",
            "initiated_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        },
        "claim": {
            "id": claim.id,
            "policy_id": claim.policy_id,
            "trigger_event_id": claim.trigger_event_id,
            "fraud_score": claim.fraud_score,
        },
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "phone": partner.phone,
            "zone_id": partner.zone_id,
        },
        "policy": {
            "id": policy.id,
            "tier": policy.tier,
            "max_daily_payout": policy.max_daily_payout,
            "max_days_per_week": policy.max_days_per_week,
        },
        "trigger": {
            "id": trigger.id if trigger else None,
            "type": trigger.trigger_type.value if trigger else None,
            "label": TRIGGER_TYPE_LABELS.get(trigger.trigger_type, "Unknown") if trigger else None,
            "severity": trigger.severity if trigger else None,
            "zone_id": trigger.zone_id if trigger else None,
            "started_at": trigger.started_at.isoformat() if trigger and trigger.started_at else None,
        },
        "payout_metadata": payout_metadata,
        "version": "1.0",
    }

from app.config import get_settings

import uuid
import time

def process_stripe_payout_mock(partner: Partner, amount: float, claim_id: int) -> tuple[bool, str, dict]:
    """Simulate a payout via Stripe API (Mock)."""
    # Simulate API latency
    time.sleep(0.5)
    
    transfer_id = f"tr_{uuid.uuid4().hex[:24]}"
    
    stripe_data = {
        "id": transfer_id,
        "object": "transfer",
        "amount": int(amount * 100),
        "currency": "inr",
        "destination": f"acct_{partner.id}mock",
        "description": f"RapidCover Claim #{claim_id}",
        "status": "paid"
    }
    
    return True, transfer_id, {"stripe_response": stripe_data}


def process_payout(
    claim: Claim,
    db: Session,
    upi_ref: Optional[str] = None,
    skip_hard_cap_check: bool = False,
) -> tuple[bool, str, dict]:
    """
    Process a payout for an approved claim.

    Uses the payment state machine for idempotency and retry tracking.
    Checks city-level 120% hard cap before processing unless skip_hard_cap_check=True.

    Returns (success, upi_ref, transaction_log).
    On failure, upi_ref contains error reason if hard cap blocked.
    """
    if claim.status != ClaimStatus.APPROVED:
        logger.warning(f"Cannot pay claim {claim.id} with status {claim.status}")
        return False, "", {}

    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy:
        return False, "", {}

    partner = db.query(Partner).filter(Partner.id == policy.partner_id).first()
    if not partner:
        return False, "", {}

    # Check city-level 120% hard cap
    if not skip_hard_cap_check:
        is_capped, current_ratio, remaining_capacity = check_city_hard_cap(partner, db)
        if is_capped:
            logger.warning(
                f"City hard cap reached for claim {claim.id}. "
                f"Current ratio: {current_ratio:.2%}, claim amount: â‚¹{claim.amount}"
            )
            return False, f"CITY_CAP_REACHED:{current_ratio:.2%}", {
                "error": "city_hard_cap_reached",
                "current_ratio": current_ratio,
                "cap_ratio": CITY_HARD_CAP_RATIO,
                "remaining_capacity": remaining_capacity,
                "claim_amount": claim.amount,
            }

        # If claim amount exceeds remaining capacity, reduce to capacity
        if claim.amount > remaining_capacity and remaining_capacity > 0:
            logger.info(
                f"Reducing claim {claim.id} from â‚¹{claim.amount} to â‚¹{remaining_capacity} "
                f"due to city cap (ratio: {current_ratio:.2%})"
            )
            claim.amount = remaining_capacity

    # Initiate payment via state machine (creates idempotency key)
    init_success, init_data = initiate_payment(claim, db)
    if not init_success:
        # Check if already confirmed (idempotent success)
        payment_state = get_payment_status(claim)
        if payment_state.get("current_status") == PaymentStatus.CONFIRMED.value:
            logger.info(f"Claim {claim.id} already confirmed (idempotent)")
            return True, claim.upi_ref or "", {"already_confirmed": True}
        logger.warning(f"Payment initiation failed for claim {claim.id}: {init_data}")
        return False, "", init_data

    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()

    existing = {}
    try:
        existing = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        pass
    payout_metadata = existing.get("payout_calculation", {})

    settings = get_settings()
    stripe_success = False
    stripe_error = None

    if not upi_ref:
        # Utilize Stripe mock if UPI exists, else IMPS mock
        try:
            if partner.upi_id:
                stripe_success, tr_ref, stripe_data = process_stripe_payout_mock(partner, claim.amount, claim.id)
                if stripe_success:
                    upi_ref = tr_ref
                    payout_metadata["stripe"] = stripe_data
                else:
                    stripe_error = "Stripe mock returned failure"
            else:
                # IMPS Fallback
                logger.info(f"Using IMPS fallback for partner {partner.id} (no UPI)")
                upi_ref = f"IMPS{uuid.uuid4().hex[:12].upper()}"
                payout_metadata["imps"] = {
                    "bank_name": partner.bank_name,
                    "account_number": f"****{partner.account_number[-4:]}" if partner.account_number else None,
                    "ifsc": partner.ifsc_code
                }
                stripe_success = True  # Consider IMPS successful immediately
        except Exception as e:
            stripe_success = False
            stripe_error = str(e)
            logger.error(f"Payout exception for claim {claim.id}: {e}")

    if not stripe_success and not upi_ref:
        # Payment failed - record failure in state machine
        fail_payment(claim, stripe_error or "Payment provider failure", db)
        logger.warning(f"Payment failed for claim {claim.id}: {stripe_error}")
        return False, "", {"error": stripe_error or "Payment failed"}

    # If no upi_ref yet (shouldn't happen but fallback)
    if not upi_ref:
        upi_ref = generate_upi_ref(policy.id, claim.id)

    # Confirm payment in state machine
    confirm_success = confirm_payment(
        claim, upi_ref, db,
        additional_data=payout_metadata.get("stripe") or payout_metadata.get("imps"),
    )

    if not confirm_success:
        logger.warning(f"Payment confirmation failed for claim {claim.id}")
        return False, "", {"error": "Payment confirmation failed"}

    transaction_log = build_transaction_log(claim, policy, partner, trigger, upi_ref, payout_metadata)

    # Add hard cap check info to transaction log
    if not skip_hard_cap_check:
        is_capped, current_ratio, remaining_capacity = check_city_hard_cap(partner, db)
        transaction_log["city_cap_check"] = {
            "current_ratio": current_ratio,
            "cap_ratio": CITY_HARD_CAP_RATIO,
            "remaining_capacity_after": remaining_capacity - claim.amount,
            "checked_at": datetime.utcnow().isoformat(),
        }

    # Update validation_data with transaction log (claim already updated by confirm_payment)
    try:
        existing = json.loads(claim.validation_data or "{}")
    except json.JSONDecodeError:
        existing = {}

    existing["transaction_log"] = transaction_log
    existing["payout_status"] = "SUCCESS"
    existing["paid_at"] = datetime.utcnow().isoformat()
    claim.validation_data = json.dumps(existing)

    db.commit()
    db.refresh(claim)

    logger.info(f"Payout processed: claim={claim.id}, partner={partner.id}, amount=Rs.{claim.amount}, ref={upi_ref}")
    notify_claim_paid(claim, db)

    return True, upi_ref, transaction_log


def process_bulk_payouts(claim_ids: list[int], db: Session) -> dict:
    """Process payouts for multiple approved claims."""
    results = {"processed": 0, "failed": 0, "skipped": 0, "transactions": []}

    for claim_id in claim_ids:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim or claim.status != ClaimStatus.APPROVED:
            results["skipped"] += 1
            continue

        success, upi_ref, _ = process_payout(claim, db)
        if success:
            results["processed"] += 1
            results["transactions"].append({"claim_id": claim_id, "upi_ref": upi_ref, "amount": claim.amount})
        else:
            results["failed"] += 1
            results["transactions"].append({"claim_id": claim_id, "error": "Payout processing failed"})

    return results


def get_transaction_log(claim: Claim) -> Optional[dict]:
    """Retrieve the stored transaction log for a paid claim."""
    if not claim.validation_data:
        return None
    try:
        return json.loads(claim.validation_data).get("transaction_log")
    except json.JSONDecodeError:
        return None
````

--- FILE: backend/app/api/policies.py ---
``python
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy, PolicyStatus, TIER_CONFIG
from app.models.claim import Claim, ClaimStatus
from app.models.zone import Zone
from app.schemas.policy import (
    PolicyCreate,
    PolicyResponse,
    PolicyQuote,
    PolicyResponseExtended,
    PolicyRenewRequest,
    PolicyRenewalQuote,
    AutoRenewUpdate,
)
from app.services.auth import get_current_partner
from app.services.premium import calculate_premium, get_all_quotes
from app.services.policy_lifecycle import (
    compute_policy_status,
    get_renewal_quote,
    renew_policy,
    build_extended_response,
    GRACE_PERIOD_HOURS,
)


# Enrollment suspension threshold
LOSS_RATIO_SUSPENSION_THRESHOLD = 0.85  # 85% - Suspend new enrollments above this


class ReinsuranceReviewResponse(BaseModel):
    """Response for reinsurance review endpoint."""
    flagged_policies: List[int]
    total_claims_amount: float
    review_triggered: bool
    threshold_ratio: float
    policies_checked: int

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("/admin/reinsurance-review", response_model=ReinsuranceReviewResponse)
def reinsurance_review(db: Session = Depends(get_db)):
    """
    Admin API endpoint to flag policies for reinsurance review on day 7.
    Flags policies where total claims > 3x weekly premium.
    """
    now = datetime.utcnow()
    # Find active policies created at least 7 days ago (or around 7 days for demo)
    day_7_cutoff = now - timedelta(days=7)
    
    policies = db.query(Policy).filter(
        Policy.is_active == True,
        Policy.created_at <= (now - timedelta(days=6))
    ).all()

    flagged_policies = []
    total_claims_amount = 0.0

    for policy in policies:
        # Sum claims for this policy
        claims_total = db.query(func.sum(Claim.amount)).filter(
            Claim.policy_id == policy.id,
            Claim.status == ClaimStatus.PAID
        ).scalar() or 0.0
        
        if claims_total > (3 * policy.weekly_premium):
            flagged_policies.append(policy.id)
            total_claims_amount += claims_total
            
    return ReinsuranceReviewResponse(
        flagged_policies=flagged_policies,
        total_claims_amount=total_claims_amount,
        review_triggered=len(flagged_policies) > 0,
        threshold_ratio=3.0,
        policies_checked=len(policies)
    )


def check_city_enrollment_status(partner: Partner, db: Session, days: int = 7) -> tuple[bool, str, float]:
    """
    Check if new enrollments are allowed in partner's city based on loss ratio.

    When loss ratio exceeds 85%, new enrollments are suspended to protect
    the insurance pool from excessive losses.

    Args:
        partner: The partner trying to enroll
        db: Database session
        days: Number of days to calculate loss ratio (default 7)

    Returns tuple of:
        - allowed: bool - True if enrollment is allowed
        - reason: str - Reason if not allowed
        - loss_ratio: float - Current loss ratio
    """
    if not partner.zone_id:
        # Partner not assigned to zone, allow enrollment
        return (True, "", 0.0)

    # Get partner's zone and city
    zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
    if not zone:
        return (True, "", 0.0)

    city = zone.city
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all zones in the city
    city_zones = db.query(Zone).filter(Zone.city.ilike(f"%{city}%")).all()
    zone_ids = [z.id for z in city_zones]

    if not zone_ids:
        return (True, "", 0.0)

    # Get partners in these zones
    partner_ids = [
        p[0] for p in
        db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids)).all()
    ]

    if not partner_ids:
        return (True, "", 0.0)

    # Calculate total premiums collected this period
    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0.0

    # Calculate total claims paid this period
    total_claims_paid = (
        db.query(func.sum(Claim.amount))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id.in_(partner_ids),
            Claim.status == ClaimStatus.PAID,
            Claim.paid_at >= period_start,
            Claim.paid_at <= now,
        )
        .scalar()
    ) or 0.0

    # Calculate loss ratio (BCR)
    loss_ratio = total_claims_paid / total_premiums if total_premiums > 0 else 0.0

    if loss_ratio > LOSS_RATIO_SUSPENSION_THRESHOLD:
        return (
            False,
            f"New enrollments suspended in {city} due to high loss ratio ({loss_ratio:.1%}). "
            f"Please try again later.",
            loss_ratio,
        )

    return (True, "", loss_ratio)


@router.get("/quotes", response_model=list[PolicyQuote])
def get_policy_quotes(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get premium quotes for all tiers based on partner's zone."""
    zone = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    return get_all_quotes(zone)


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_data: PolicyCreate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Create a new insurance policy for the current partner."""
    # Check city enrollment status (loss ratio < 85%)
    allowed, reason, _ = check_city_enrollment_status(partner, db)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason,
        )

    # Check for existing active policy
    existing = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active policy. Wait for it to expire or cancel it first.",
        )

    # Get zone for premium calculation
    zone = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    # Calculate premium
    quote = calculate_premium(policy_data.tier, zone)

    # Create policy (starts now, expires in 7 days)
    now = datetime.utcnow()
    policy = Policy(
        partner_id=partner.id,
        tier=policy_data.tier,
        weekly_premium=quote.final_premium,
        max_daily_payout=quote.max_daily_payout,
        max_days_per_week=quote.max_days_per_week,
        starts_at=now,
        expires_at=now + timedelta(days=7),
        auto_renew=policy_data.auto_renew,
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return policy


@router.get("/active", response_model=PolicyResponseExtended)
def get_active_policy(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get the current partner's active policy with lifecycle status."""
    # Use naive UTC datetime for SQLite compatibility
    now = datetime.utcnow()
    grace_cutoff = now - timedelta(hours=GRACE_PERIOD_HOURS)

    # Find policy that is either:
    # 1. Active and not expired
    # 2. Active and in grace period (expired within last 48 hours)
    policy = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > grace_cutoff,  # Include grace period
        )
        .order_by(Policy.expires_at.desc())
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active policy found",
        )

    return build_extended_response(policy)


@router.get("/history", response_model=list[PolicyResponse])
def get_policy_history(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get all policies for the current partner."""
    policies = (
        db.query(Policy)
        .filter(Policy.partner_id == partner.id)
        .order_by(Policy.created_at.desc())
        .all()
    )

    return policies


@router.post("/{policy_id}/cancel", response_model=PolicyResponse)
def cancel_policy(
    policy_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Cancel an active policy."""
    policy = (
        db.query(Policy)
        .filter(
            Policy.id == policy_id,
            Policy.partner_id == partner.id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    if not policy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy is already cancelled",
        )

    policy.is_active = False
    policy.auto_renew = False
    policy.status = PolicyStatus.CANCELLED
    db.commit()
    db.refresh(policy)

    return policy


@router.get("/{policy_id}/renewal-quote", response_model=PolicyRenewalQuote)
def get_policy_renewal_quote(
    policy_id: int,
    tier: str = None,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Get renewal quote for a policy with loyalty discount."""
    policy = (
        db.query(Policy)
        .filter(
            Policy.id == policy_id,
            Policy.partner_id == partner.id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    # Get zone for premium calculation
    zone = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    # Parse tier if provided
    from app.models.policy import PolicyTier
    new_tier = None
    if tier:
        try:
            new_tier = PolicyTier(tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {tier}. Valid tiers are: flex, standard, pro",
            )

    return get_renewal_quote(policy, new_tier, zone)


@router.post("/{policy_id}/renew", response_model=PolicyResponseExtended)
def renew_policy_endpoint(
    policy_id: int,
    renewal_data: PolicyRenewRequest,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Renew a policy, creating a new linked policy."""
    policy = (
        db.query(Policy)
        .filter(
            Policy.id == policy_id,
            Policy.partner_id == partner.id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    # Check if renewal is allowed
    status_info, timing = compute_policy_status(policy)
    if not timing["can_renew"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy cannot be renewed yet. Renewal is available 2 days before expiry or during grace period.",
        )

    # Check for existing future policy (already renewed)
    now = datetime.utcnow()
    existing_future = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.starts_at > now,
        )
        .first()
    )

    if existing_future:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending renewal policy.",
        )

    new_policy = renew_policy(
        policy=policy,
        partner=partner,
        db=db,
        new_tier=renewal_data.tier,
        auto_renew=renewal_data.auto_renew,
    )

    return build_extended_response(new_policy)


@router.patch("/{policy_id}/auto-renew", response_model=PolicyResponse)
def update_auto_renew(
    policy_id: int,
    update_data: AutoRenewUpdate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Toggle auto-renewal setting for a policy."""
    policy = (
        db.query(Policy)
        .filter(
            Policy.id == policy_id,
            Policy.partner_id == partner.id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    if not policy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update auto-renew on inactive policy",
        )

    policy.auto_renew = update_data.auto_renew
    db.commit()
    db.refresh(policy)

    return policy


@router.get("/{policy_id}/certificate")
def download_certificate(
    policy_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Download policy certificate as PDF."""
    policy = (
        db.query(Policy)
        .filter(
            Policy.id == policy_id,
            Policy.partner_id == partner.id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    # Get zone name for certificate
    zone_name = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
        if zone:
            zone_name = zone.name

    from app.services.policy_certificate import generate_certificate_pdf, get_certificate_filename

    # Generate PDF
    pdf_bytes = generate_certificate_pdf(policy, partner, zone_name)
    filename = get_certificate_filename(policy)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
````

--- FILE: backend/app/api/zones.py ---
``python
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.zone import Zone
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.partner import Partner
from app.schemas.zone import ZoneResponse, ZoneCreate, ZoneRiskUpdate
from app.services.claims_processor import (
    get_partner_runtime_metadata,
    get_zone_coverage_metadata,
    upsert_partner_runtime_metadata,
    upsert_zone_coverage_metadata,
)


class BCRResponse(BaseModel):
    """Benefit-to-Cost Ratio response for a city."""
    city: str
    total_premiums_collected: float
    total_claims_paid: float
    bcr: float  # claims_paid / premiums_collected
    loss_ratio: float  # BCR as percentage (BCR * 100)
    policy_count: int
    claim_count: int
    period_start: datetime
    period_end: datetime


class ZoneReassignmentRequest(BaseModel):
    """Request to reassign a partner to a new zone."""
    partner_id: int
    new_zone_id: int


class ZoneReassignmentResponse(BaseModel):
    """Response for zone reassignment."""
    partner_id: int
    old_zone_id: Optional[int]
    new_zone_id: int
    premium_adjustment: float  # Positive = credit, Negative = debit
    new_weekly_premium: float
    days_remaining: int
    policy_id: Optional[int]
    reassignment_logged: bool


class ZoneCoverageMetadataRequest(BaseModel):
    """Coverage metadata for ward/pin-code matching and density weighting."""
    pin_codes: list[str] = []
    density_weight: Optional[float] = None
    ward_name: Optional[str] = None


class ZoneCoverageMetadataResponse(BaseModel):
    zone_id: int
    pin_codes: list[str]
    density_weight: Optional[float] = None
    ward_name: Optional[str] = None
    updated_at: Optional[datetime] = None


class PartnerAvailabilityRequest(BaseModel):
    """Runtime partner availability controls used by claims processing."""
    pin_code: Optional[str] = None
    is_manual_offline: Optional[bool] = None
    manual_offline_until: Optional[datetime] = None
    leave_until: Optional[datetime] = None
    leave_note: Optional[str] = None


class PartnerAvailabilityResponse(BaseModel):
    partner_id: int
    pin_code: Optional[str] = None
    is_manual_offline: bool
    manual_offline_until: Optional[datetime] = None
    leave_until: Optional[datetime] = None
    leave_note: Optional[str] = None
    updated_at: Optional[datetime] = None


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates in km using Haversine formula."""
    R = 6371  # Earth's radius in km
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

router = APIRouter(prefix="/zones", tags=["zones"])

# =============================================================================
# Zone Reassignment 24-Hour Workflow Endpoints
# =============================================================================

from app.schemas.zone_reassignment import (
    ZoneReassignmentProposal,
    ZoneReassignmentResponse as NewReassignmentResponse,
    ZoneReassignmentListResponse,
    ZoneReassignmentActionResponse,
)
from app.models.zone_reassignment import ReassignmentStatus


@router.post("/reassignments/propose", response_model=NewReassignmentResponse)
def propose_zone_reassignment(
    proposal: ZoneReassignmentProposal,
    db: Session = Depends(get_db),
):
    """
    Propose a zone reassignment with 24-hour acceptance window.

    Creates a proposal that the partner must accept or reject within 24 hours.
    If no action is taken, the proposal expires automatically.

    This is the new workflow that replaces instant reassignment for cases
    where partner consent is required.
    """
    from app.services.zone_reassignment_service import propose_reassignment

    result, error = propose_reassignment(proposal.partner_id, proposal.new_zone_id, db)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return result


@router.post("/reassignments/{reassignment_id}/accept", response_model=ZoneReassignmentActionResponse)
def accept_zone_reassignment(
    reassignment_id: int,
    db: Session = Depends(get_db),
):
    """
    Accept a pending zone reassignment proposal.

    Must be called within 24 hours of the proposal.
    Updates the partner's zone_id and logs the change.
    """
    from app.services.zone_reassignment_service import accept_reassignment

    result, error = accept_reassignment(reassignment_id, db)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return result


@router.post("/reassignments/{reassignment_id}/reject", response_model=ZoneReassignmentActionResponse)
def reject_zone_reassignment(
    reassignment_id: int,
    db: Session = Depends(get_db),
):
    """
    Reject a pending zone reassignment proposal.

    The partner remains in their current zone.
    """
    from app.services.zone_reassignment_service import reject_reassignment

    result, error = reject_reassignment(reassignment_id, db)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return result


@router.get("/reassignments/{reassignment_id}", response_model=NewReassignmentResponse)
def get_zone_reassignment(
    reassignment_id: int,
    db: Session = Depends(get_db),
):
    """Get details of a specific zone reassignment."""
    from app.services.zone_reassignment_service import get_reassignment

    result = get_reassignment(reassignment_id, db)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reassignment not found",
        )

    return result


@router.delete("/reassignments/{reassignment_id}")
def delete_zone_reassignment(
    reassignment_id: int,
    db: Session = Depends(get_db),
):
    """Delete a zone reassignment (for testing/admin purposes)."""
    from app.models.zone_reassignment import ZoneReassignment

    reassignment = db.query(ZoneReassignment).filter(ZoneReassignment.id == reassignment_id).first()
    if not reassignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reassignment not found",
        )

    db.delete(reassignment)
    db.commit()
    return {"message": f"Reassignment {reassignment_id} deleted"}


@router.get("/reassignments", response_model=ZoneReassignmentListResponse)
def list_zone_reassignments(
    partner_id: Optional[int] = None,
    status_filter: Optional[ReassignmentStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List zone reassignments with optional filters.

    For admin: Lists all reassignments
    For partner: Filter by partner_id to see their proposals
    """
    from app.services.zone_reassignment_service import list_reassignments

    return list_reassignments(
        db,
        partner_id=partner_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post("/reassignments/expire-stale")
def expire_stale_reassignments(db: Session = Depends(get_db)):
    """
    Background job endpoint to expire stale proposals.

    Marks any proposals past their 24-hour window as expired.
    In production, this would be called by a scheduled job.
    """
    from app.services.zone_reassignment_service import expire_stale_proposals

    expired_count = expire_stale_proposals(db)

    return {
        "message": f"Expired {expired_count} stale proposals",
        "expired_count": expired_count,
    }





@router.get("/nearest")
def get_nearest_zones(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    limit: int = Query(3, ge=1, le=10, description="Maximum zones to return"),
    db: Session = Depends(get_db),
):
    """Find nearest zones to given GPS coordinates."""
    zones = db.query(Zone).all()

    zones_with_distance = []
    for zone in zones:
        if zone.dark_store_lat and zone.dark_store_lng:
            distance = haversine_distance(lat, lng, zone.dark_store_lat, zone.dark_store_lng)
            zones_with_distance.append({
                "zone": ZoneResponse.model_validate(zone),
                "distance_km": round(distance, 2),
            })

    zones_with_distance.sort(key=lambda x: x["distance_km"])
    return zones_with_distance[:limit]


@router.get("", response_model=list[ZoneResponse])
def list_zones(
    city: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all zones, optionally filtered by city."""
    query = db.query(Zone)

    if city:
        query = query.filter(Zone.city.ilike(f"%{city}%"))

    zones = query.offset(skip).limit(limit).all()
    return zones


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    """Get zone details including risk score."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    return zone


@router.get("/code/{zone_code}", response_model=ZoneResponse)
def get_zone_by_code(zone_code: str, db: Session = Depends(get_db)):
    """Get zone details by zone code (e.g., BLR-047)."""
    zone = db.query(Zone).filter(Zone.code == zone_code).first()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    return zone


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(zone_data: ZoneCreate, db: Session = Depends(get_db)):
    """Create a new zone (admin endpoint)."""
    existing = db.query(Zone).filter(Zone.code == zone_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone code already exists",
        )

    zone = Zone(
        code=zone_data.code,
        name=zone_data.name,
        city=zone_data.city,
        polygon=zone_data.polygon,
        dark_store_lat=zone_data.dark_store_lat,
        dark_store_lng=zone_data.dark_store_lng,
    )

    db.add(zone)
    db.commit()
    db.refresh(zone)

    return zone


@router.patch("/{zone_id}/risk", response_model=ZoneResponse)
def update_zone_risk(
    zone_id: int,
    risk_data: ZoneRiskUpdate,
    db: Session = Depends(get_db),
):
    """Update zone risk score (called by ML service)."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    if not 0 <= risk_data.risk_score <= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk score must be between 0 and 100",
        )

    zone.risk_score = risk_data.risk_score
    db.commit()
    db.refresh(zone)

    return zone


def calculate_city_bcr(city: str, db: Session, days: int = 7) -> BCRResponse:
    """
    Calculate Benefit-to-Cost Ratio for a city.

    BCR = total_claims_paid / total_premiums_collected

    Args:
        city: City name to calculate BCR for
        db: Database session
        days: Number of days to look back (default 7 for weekly)

    Returns BCRResponse with all financial metrics.
    """
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all zones in the city
    city_zones = db.query(Zone).filter(Zone.city.ilike(f"%{city}%")).all()
    zone_ids = [z.id for z in city_zones]

    if not zone_ids:
        return BCRResponse(
            city=city,
            total_premiums_collected=0.0,
            total_claims_paid=0.0,
            bcr=0.0,
            loss_ratio=0.0,
            policy_count=0,
            claim_count=0,
            period_start=period_start,
            period_end=now,
        )

    # Get partners in these zones
    partner_ids_query = db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids))
    partner_ids = [p[0] for p in partner_ids_query.all()]

    # Calculate total premiums collected (from active policies created in period)
    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0.0

    # Calculate total claims paid
    total_claims_paid = (
        db.query(func.sum(Claim.amount))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id.in_(partner_ids),
            Claim.status == ClaimStatus.PAID,
            Claim.paid_at >= period_start,
            Claim.paid_at <= now,
        )
        .scalar()
    ) or 0.0

    # Count policies and claims
    policy_count = (
        db.query(func.count(Policy.id))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0

    claim_count = (
        db.query(func.count(Claim.id))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id.in_(partner_ids),
            Claim.status == ClaimStatus.PAID,
            Claim.paid_at >= period_start,
            Claim.paid_at <= now,
        )
        .scalar()
    ) or 0

    # Calculate BCR (avoid division by zero)
    bcr = total_claims_paid / total_premiums if total_premiums > 0 else 0.0
    loss_ratio = bcr * 100  # As percentage

    return BCRResponse(
        city=city,
        total_premiums_collected=round(total_premiums, 2),
        total_claims_paid=round(total_claims_paid, 2),
        bcr=round(bcr, 4),
        loss_ratio=round(loss_ratio, 2),
        policy_count=policy_count,
        claim_count=claim_count,
        period_start=period_start,
        period_end=now,
    )


@router.get("/bcr/{city}", response_model=BCRResponse)
def get_city_bcr(
    city: str,
    days: int = Query(7, ge=1, le=365, description="Number of days to calculate BCR for"),
    db: Session = Depends(get_db),
):
    """
    Get Benefit-to-Cost Ratio (BCR) for a city.

    BCR = total_claims_paid / total_premiums_collected

    - BCR < 1.0 means profitable (collecting more than paying out)
    - BCR > 1.0 means losing money
    - BCR > 1.2 triggers reinsurance (120% hard cap)

    Loss ratio is BCR expressed as percentage.
    """
    return calculate_city_bcr(city, db, days)


@router.get("/{zone_id}/coverage", response_model=ZoneCoverageMetadataResponse)
def get_zone_coverage(zone_id: int, db: Session = Depends(get_db)):
    """Get pin-code coverage and density metadata for a zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    return ZoneCoverageMetadataResponse(**get_zone_coverage_metadata(zone_id, db))


@router.put("/{zone_id}/coverage", response_model=ZoneCoverageMetadataResponse)
def update_zone_coverage(
    zone_id: int,
    request: ZoneCoverageMetadataRequest,
    db: Session = Depends(get_db),
):
    """Update ward/pin-code coverage and density metadata for a zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    if request.density_weight is not None and not 0 <= request.density_weight <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="density_weight must be between 0 and 1",
        )

    metadata = upsert_zone_coverage_metadata(
        zone_id,
        db,
        pin_codes=request.pin_codes,
        density_weight=request.density_weight,
        ward_name=request.ward_name,
    )
    return ZoneCoverageMetadataResponse(**metadata)


@router.get("/partners/{partner_id}/availability", response_model=PartnerAvailabilityResponse)
def get_partner_availability(partner_id: int, db: Session = Depends(get_db)):
    """Get runtime availability controls for a partner."""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    return PartnerAvailabilityResponse(**get_partner_runtime_metadata(partner_id, db))


@router.put("/partners/{partner_id}/availability", response_model=PartnerAvailabilityResponse)
def update_partner_availability(
    partner_id: int,
    request: PartnerAvailabilityRequest,
    db: Session = Depends(get_db),
):
    """Update runtime availability controls for a partner."""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    metadata = upsert_partner_runtime_metadata(
        partner_id,
        db,
        **{
            field: getattr(request, field)
            for field in request.model_fields_set
        },
    )
    return PartnerAvailabilityResponse(**metadata)


@router.post("/reassign", response_model=ZoneReassignmentResponse)
def reassign_partner_zone(
    reassignment: ZoneReassignmentRequest,
    db: Session = Depends(get_db),
):
    """
    Reassign a partner to a new zone mid-week.

    When Zepto/Blinkit reassigns a partner to a new dark store:
    - Recalculates premium for remaining days based on new zone's risk
    - Computes credit/debit adjustment for next renewal
    - Logs reassignment history in partner record

    Returns adjustment details for frontend display.
    """
    from app.services.premium import calculate_premium

    # Get partner
    partner = db.query(Partner).filter(Partner.id == reassignment.partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    # Get new zone
    new_zone = db.query(Zone).filter(Zone.id == reassignment.new_zone_id).first()
    if not new_zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    old_zone_id = partner.zone_id

    # Get current active policy
    now = datetime.utcnow()
    active_policy = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > now,
        )
        .first()
    )

    premium_adjustment = 0.0
    new_weekly_premium = 0.0
    days_remaining = 0
    policy_id = None

    if active_policy:
        policy_id = active_policy.id

        # Calculate days remaining in current policy
        days_remaining = max(0, (active_policy.expires_at - now).days)

        # Get old zone for comparison
        old_zone = db.query(Zone).filter(Zone.id == old_zone_id).first() if old_zone_id else None

        # Calculate new premium based on new zone
        new_quote = calculate_premium(active_policy.tier, new_zone)
        old_daily_rate = active_policy.weekly_premium / 7
        new_daily_rate = new_quote.final_premium / 7

        # Premium adjustment = (old_rate - new_rate) * days_remaining
        # Positive = credit to partner (new zone is cheaper)
        # Negative = debit from partner (new zone is more expensive)
        premium_adjustment = round((old_daily_rate - new_daily_rate) * days_remaining, 2)
        new_weekly_premium = new_quote.final_premium

    # Update partner's zone
    zone_history = list(partner.zone_history or [])
    zone_history.append({
        "old_zone_id": old_zone_id,
        "new_zone_id": reassignment.new_zone_id,
        "effective_at": now.isoformat(),
        "policy_id": policy_id,
        "premium_adjustment": premium_adjustment,
        "new_weekly_premium": new_weekly_premium,
        "days_remaining": days_remaining,
    })
    partner.zone_history = zone_history[-50:]
    partner.zone_id = reassignment.new_zone_id
    db.commit()
    db.refresh(partner)

    return ZoneReassignmentResponse(
        partner_id=partner.id,
        old_zone_id=old_zone_id,
        new_zone_id=reassignment.new_zone_id,
        premium_adjustment=premium_adjustment,
        new_weekly_premium=new_weekly_premium,
        days_remaining=days_remaining,
        policy_id=policy_id,
        reassignment_logged=True,
    )



# =============================================================================
# PLATFORM ACTIVITY ENDPOINTS (Feature 3)
# =============================================================================

class PartnerPlatformActivityResponse(BaseModel):
    partner_id: int
    platform_logged_in: bool
    active_shift: bool
    orders_accepted_recent: int
    orders_completed_recent: int
    last_app_ping: str
    zone_dwell_minutes: int
    suspicious_inactivity: bool
    platform: str
    updated_at: str
    source: str


class PartnerPlatformActivityRequest(BaseModel):
    platform_logged_in: Optional[bool] = None
    active_shift: Optional[bool] = None
    orders_accepted_recent: Optional[int] = None
    orders_completed_recent: Optional[int] = None
    last_app_ping: Optional[str] = None
    zone_dwell_minutes: Optional[int] = None
    suspicious_inactivity: Optional[bool] = None
    platform: Optional[str] = None


class PartnerPlatformEligibilityResponse(BaseModel):
    partner_id: int
    eligible: bool
    score: float
    reasons: list[dict]
    activity: dict


@router.get(
    "/partners/{partner_id}/activity",
    response_model=PartnerPlatformActivityResponse,
    tags=["zones"],
)
def get_partner_activity(partner_id: int, db: Session = Depends(get_db)):
    """
    GET /zones/partners/{partner_id}/activity

    Return current simulated platform activity for a delivery partner.
    Shows Zomato/Swiggy/Zepto/Blinkit login state, shift, orders, and ping.
    """
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Partner {partner_id} not found")

    from app.services.claims_processor import get_db_partner_platform_activity
    activity = get_db_partner_platform_activity(partner_id, db)
    return PartnerPlatformActivityResponse(**activity)


@router.put(
    "/partners/{partner_id}/activity",
    response_model=PartnerPlatformActivityResponse,
    tags=["zones"],
)
def update_partner_activity(
    partner_id: int,
    request: PartnerPlatformActivityRequest,
    db: Session = Depends(get_db),
):
    """
    PUT /zones/partners/{partner_id}/activity

    Admin control: toggle partner platform activity state.
    Set active_shift=false to simulate partner being offline.
    Set suspicious_inactivity=true to simulate fraud signal.
    Claim approval logic reads this data before authorising payout.
    """
    from fastapi import HTTPException
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail=f"Partner {partner_id} not found")

    from app.services.claims_processor import upsert_db_partner_platform_activity
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    activity = upsert_db_partner_platform_activity(partner_id, db, **updates)
    return PartnerPlatformActivityResponse(**activity)


@router.get(
    "/partners/{partner_id}/activity/eligibility",
    response_model=PartnerPlatformEligibilityResponse,
    tags=["zones"],
)
def get_partner_activity_eligibility(partner_id: int, db: Session = Depends(get_db)):
    """
    GET /zones/partners/{partner_id}/activity/eligibility

    Evaluate whether this partner's platform activity qualifies them for payout.
    Returns check-by-check breakdown (logged in, active shift, recent orders, ping).
    """
    from fastapi import HTTPException
    from app.services.external_apis import evaluate_partner_platform_eligibility

    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail=f"Partner {partner_id} not found")

    result = evaluate_partner_platform_eligibility(partner_id)
    return PartnerPlatformEligibilityResponse(**result)


@router.get("/partners/activity/bulk", tags=["zones"])
def get_all_partners_activity(
    zone_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    GET /zones/partners/activity/bulk

    Return platform activity for all partners (optionally filtered by zone).
    Used by admin LiveDataPanel to show fleet-wide activity at a glance.
    """
    from app.services.claims_processor import get_db_partner_platform_activity
    from app.services.external_apis import evaluate_partner_platform_eligibility

    query = db.query(Partner).filter(Partner.is_active == True)
    if zone_id:
        query = query.filter(Partner.zone_id == zone_id)
    partners = query.limit(200).all()

    results = []
    for p in partners:
        activity = get_db_partner_platform_activity(p.id, db)
        eligibility = evaluate_partner_platform_eligibility(p.id)
        results.append({
            "partner_id": p.id,
            "partner_name": p.name,
            "zone_id": p.zone_id,
            "activity": activity,
            "platform_eligible": eligibility["eligible"],
            "platform_score": eligibility["score"],
        })

    return {
        "total": len(results),
        "zone_id": zone_id,
        "partners": results,
    }
````

--- FILE: frontend/src/services/adminApi.js ---
``javascript
/**
 * adminApi.js  â€“  Admin API client wrappers
 *
 * B2 owns shared API helpers; B1 admin components import from here.
 *
 * All calls go to /api/v1/admin/*
 * Admin endpoints are intentionally unauthenticated in this demo.
 */

const BASE = (import.meta.env.VITE_API_URL || '/api/v1') + '/admin';

// â”€â”€ Shared helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function getToken() {
  return localStorage.getItem('access_token');
}

function jsonHeaders() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) { }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function get(path, params = {}) {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const res = await fetch(url.toString(), { headers: jsonHeaders() });
  return handleResponse(res);
}

async function post(path, body = null) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: jsonHeaders(),
    ...(body != null ? { body: JSON.stringify(body) } : {}),
  });
  return handleResponse(res);
}

// â”€â”€ Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** @returns {DashboardStats} */
export async function getDashboardStats() {
  return get('/dashboard');
}

// â”€â”€ Zones â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getAllZones() {
  return get('/zones');
}

export async function seedZones() {
  return post('/seed');
}

// â”€â”€ Trigger management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/**
 * @param {{ active_only?: boolean, zone_id?: number, skip?: number, limit?: number }} params
 */
export async function getTriggers(params = {}) {
  return get('/triggers', params);
}

export async function endTrigger(triggerId) {
  return post(`/triggers/${triggerId}/end`);
}

export async function processTrigger(triggerId) {
  return post(`/triggers/${triggerId}/process`);
}

// â”€â”€ Claims management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/**
 * @param {{ status_filter?: string, zone_id?: number, skip?: number, limit?: number }} params
 */
export async function getAdminClaims(params = {}) {
  return get('/claims', params);
}

export async function approveClaim(claimId) {
  return post(`/claims/${claimId}/approve`);
}

export async function rejectClaim(claimId, reason = null) {
  return post(`/claims/${claimId}/reject`, reason ? { reason } : null);
}

export async function payoutClaim(claimId, upiRef = null) {
  return post(`/claims/${claimId}/payout`, upiRef ? { upi_ref: upiRef } : null);
}

// â”€â”€ Simulation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/**
 * @param {number} zoneId
 * @param {{ temp_celsius?: number, rainfall_mm_hr?: number, humidity?: number }} params
 */
export async function simulateWeather(zoneId, params = {}) {
  return post('/simulate/weather', { zone_id: zoneId, ...params });
}

/**
 * @param {number} zoneId
 * @param {{ aqi?: number, pm25?: number, pm10?: number }} params
 */
export async function simulateAqi(zoneId, params = {}) {
  return post('/simulate/aqi', { zone_id: zoneId, ...params });
}

export async function simulateShutdown(zoneId, reason = 'Civic shutdown - curfew in effect') {
  return post('/simulate/shutdown', { zone_id: zoneId, reason });
}

export async function simulateClosure(zoneId, reason = 'Force majeure - infrastructure issue') {
  return post('/simulate/closure', { zone_id: zoneId, reason });
}

export async function clearZoneConditions(zoneId) {
  return post(`/simulate/clear/${zoneId}`);
}

export async function resetAllSimulations() {
  return post('/simulate/reset');
}

export async function processAutoRenewals() {
  return post('/process-auto-renewals');
}

// â”€â”€ Admin Panel â€“ Stress Scenarios â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getStressScenarios() {
  return get('/panel/stress-scenarios');
}

export async function getStressScenario(scenarioId) {
  return get(`/panel/stress-scenarios/${scenarioId}`);
}

// â”€â”€ Admin Panel â€“ RIQI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getRiqiProfiles() {
  return get('/panel/riqi');
}

export async function getRiqiForZone(zoneCode) {
  return get(`/panel/riqi/${zoneCode}`);
}

export async function recomputeRiqi(zoneCode) {
  return post(`/panel/riqi/${zoneCode}/recompute`);
}

export async function seedRiqiProfiles() {
  return post('/panel/riqi/seed');
}

// â”€â”€ Admin Panel â€“ Notification Templates â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/**
 * Preview a notification template with sample data.
 * @param {string} type  e.g. 'claim_created'
 * @param {string} lang  e.g. 'en', 'hi'
 */
export async function previewNotification(type = 'claim_created', lang = 'en') {
  return get('/panel/notifications/preview', { type, lang });
}

export async function listNotificationTemplates() {
  return get('/panel/notifications/templates');
}

// â”€â”€ Admin Panel â€“ Trigger eligibility check â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function checkTriggerEligibility(partnerId, zoneId, triggerType = 'rain') {
  return post('/panel/trigger-check', {
    partner_id: partnerId,
    zone_id: zoneId,
    trigger_type: triggerType,
  });
}

// â”€â”€ Zone Reassignment (admin-side) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function proposeReassignment(partnerId, newZoneId) {
  const res = await fetch(`/api/v1/admin/reassignments`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ partner_id: partnerId, new_zone_id: newZoneId }),
  });
  return handleResponse(res);
}

// â”€â”€ Multi-Trigger Aggregation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** Get aggregation stats (total aggregated claims, triggers suppressed, savings) */
export async function getAggregationStats() {
  return get('/aggregation-stats');
}

/** Get aggregation details for a specific claim */
export async function getClaimAggregation(claimId) {
  return get(`/claims/${claimId}/aggregation`);
}

// â”€â”€ Payment State Machine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** Get payment state for a specific claim */
export async function getClaimPaymentState(claimId) {
  return get(`/claims/${claimId}/payment-state`);
}

/** Retry a failed payment */
export async function retryPayment(claimId) {
  return post(`/claims/${claimId}/retry-payment`);
}

/**
 * Manually reconcile a payment.
 * @param {number} claimId
 * @param {{ action: 'confirm'|'reject'|'force_paid', provider_ref?: string, notes?: string }} data
 */
export async function reconcilePayment(claimId, data) {
  return post(`/claims/${claimId}/reconcile`, data);
}

/** List claims with failed payments */
export async function getPaymentFailures(limit = 50) {
  return get('/claims/payment-failures', { limit });
}

/** List claims pending manual reconciliation */
export async function getPendingReconciliation(limit = 50) {
  return get('/claims/pending-reconciliation', { limit });
}

/** Get payment processing statistics */
export async function getPaymentStats() {
  return get('/payment-stats');
}

// â”€â”€ Default export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const adminApi = {
  getDashboardStats,
  getAllZones,
  seedZones,
  getTriggers,
  endTrigger,
  processTrigger,
  getAdminClaims,
  approveClaim,
  rejectClaim,
  payoutClaim,
  simulateWeather,
  simulateAqi,
  simulateShutdown,
  simulateClosure,
  clearZoneConditions,
  resetAllSimulations,
  processAutoRenewals,
  getStressScenarios,
  getStressScenario,
  getRiqiProfiles,
  getRiqiForZone,
  recomputeRiqi,
  seedRiqiProfiles,
  previewNotification,
  listNotificationTemplates,
  checkTriggerEligibility,
  proposeReassignment,
  // Multi-trigger aggregation
  getAggregationStats,
  getClaimAggregation,
  // Payment state machine
  getClaimPaymentState,
  retryPayment,
  reconcilePayment,
  getPaymentFailures,
  getPendingReconciliation,
  getPaymentStats,
};

export default adminApi;

// â”€â”€ Validation Matrix â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** Get validation matrix proof (most recent claim with matrix) */
export async function getValidationMatrixProof() {
  return get('/panel/proof/validation-matrix');
}

/** Get validation matrix for a specific claim */
export async function getClaimValidationMatrix(claimId) {
  return get(`/claims/${claimId}/validation-matrix`);
}

// â”€â”€ Oracle Reliability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** Get oracle reliability proof (source confidence + trigger decisions) */
export async function getOracleReliabilityProof() {
  return get('/panel/proof/oracle-reliability');
}

/** Get full oracle reliability report (optionally filtered to a zone_id) */
export async function getOracleReliability(zoneId = null) {
  const url = new URL(`${BASE}/panel/oracle-reliability`, window.location.origin);
  if (zoneId) url.searchParams.set('zone_id', zoneId);
  const res = await fetch(url.toString(), { headers: jsonHeaders() });
  return handleResponse(res);
}

// â”€â”€ Platform Activity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** Get platform activity proof (fleet-level summary) */
export async function getPlatformActivityProof() {
  return get('/panel/proof/platform-activity');
}

/** Get live data panel (oracle + sources + platform activity combined) */
export async function getLiveData(zoneCode = null) {
  const params = zoneCode ? { zone_code: zoneCode } : {};
  return get('/panel/live-data', params);
}
````

--- FILE: frontend/src/components/ReassignmentCountdown.jsx ---
``jsx
/**
 * ReassignmentCountdown.jsx  â€“  Live countdown driven by backend expires_at
 *
 * B2 reusable component. Used in Dashboard ZoneReassignmentCard.
 *
 * Props:
 *   expiresAt  {string}  ISO 8601 UTC string from backend
 *   onExpire   {()=>void} optional callback when countdown hits zero
 */

import { useState, useEffect, useRef } from 'react';
import { parseCountdown, countdownUrgency } from '../services/proofApi';

/* â”€â”€â”€ Styles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const S = `
  .rcd-wrap {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    font-weight: 700;
    border-radius: 10px;
    padding: 3px 10px;
    transition: background 0.4s, color 0.4s;
  }

  /* Urgency states */
  .rcd-safe    { background: #dcfce7; color: #166534; }
  .rcd-warn    { background: #fef9c3; color: #854d0e; }
  .rcd-urgent  { background: #fee2e2; color: #991b1b; animation: rcd-pulse 1.2s ease-in-out infinite; }
  .rcd-expired { background: #f3f4f6; color: #6b7280; }

  .rcd-dot {
    width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  }
  .rcd-safe   .rcd-dot { background: #22c55e; }
  .rcd-warn   .rcd-dot { background: #f59e0b; }
  .rcd-urgent .rcd-dot { background: #ef4444; }

  @keyframes rcd-pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.55; }
  }
`;

/* â”€â”€â”€ Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export default function ReassignmentCountdown({ expiresAt, onExpire }) {
  const [cd, setCd] = useState(() => parseCountdown(expiresAt));
  const firedRef = useRef(false);

  useEffect(() => {
    if (!expiresAt) return;
    const tick = () => {
      const next = parseCountdown(expiresAt);
      setCd(next);
      if (next.expired && !firedRef.current) {
        firedRef.current = true;
        onExpire?.();
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [expiresAt, onExpire]);

  const urgency = countdownUrgency(expiresAt);

  let label;
  if (cd.expired) {
    label = 'Expired';
  } else if (cd.hours > 0) {
    label = `${cd.hours}h ${cd.minutes}m left`;
  } else if (cd.minutes > 0) {
    label = `${cd.minutes}m ${cd.seconds}s left`;
  } else {
    label = `${cd.seconds}s left`;
  }

  return (
    <>
      <style>{S}</style>
      <span className={`rcd-wrap rcd-${urgency}`} role="timer" aria-live="polite">
        {urgency !== 'expired' && <span className="rcd-dot" />}
        {label}
      </span>
    </>
  );
}
````

--- FILE: frontend/src/components/SourceBadge.jsx ---
``jsx
/**
 * SourceBadge.jsx  â€“  Reusable trigger-source / disruption-type badge
 *
 * B2 shared component. Used in Dashboard, Claims, ProofCard, and admin panels.
 *
 * Props:
 *   type      {string}  'rain' | 'heat' | 'aqi' | 'shutdown' | 'closure'
 *   severity  {number?} 1â€“5  (optional â€“ renders severity chip when provided)
 *   size      {'sm'|'md'|'lg'} default 'md'
 *   showLabel {boolean} default true
 */

const TYPE_MAP = {
  rain:     { icon: 'ðŸŒ§ï¸', label: 'Heavy Rain',     color: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
  heat:     { icon: 'ðŸŒ¡ï¸', label: 'Extreme Heat',   color: '#fef2f2', border: '#fecaca', text: '#991b1b' },
  aqi:      { icon: 'ðŸ’¨', label: 'Dangerous AQI',  color: '#fffbeb', border: '#fde68a', text: '#92400e' },
  shutdown: { icon: 'ðŸš«', label: 'Civic Shutdown',  color: '#faf5ff', border: '#e9d5ff', text: '#6b21a8' },
  closure:  { icon: 'ðŸª', label: 'Store Closure',   color: '#f9fafb', border: '#e5e7eb', text: '#374151' },
};

const FALLBACK = { icon: 'âš ï¸', label: 'Event', color: '#f9fafb', border: '#e5e7eb', text: '#374151' };

const SIZE_MAP = {
  sm: { fontSize: 11, padding: '2px 8px',  iconSize: 14, gap: 4 },
  md: { fontSize: 12, padding: '4px 10px', iconSize: 16, gap: 5 },
  lg: { fontSize: 13, padding: '5px 13px', iconSize: 20, gap: 6 },
};

const SEVERITY_COLORS = {
  1: { bg: '#f0fdf4', text: '#166534' },
  2: { bg: '#dbeafe', text: '#1e40af' },
  3: { bg: '#fef9c3', text: '#854d0e' },
  4: { bg: '#fee2e2', text: '#991b1b' },
  5: { bg: '#fdf2f8', text: '#9d174d' },
};

export default function SourceBadge({ type, severity, size = 'md', showLabel = true }) {
  const meta  = TYPE_MAP[type?.toLowerCase()] || FALLBACK;
  const sizes = SIZE_MAP[size] || SIZE_MAP.md;
  const sevColor = severity ? (SEVERITY_COLORS[severity] || SEVERITY_COLORS[3]) : null;

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      {/* Main type badge */}
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: sizes.gap,
          background: meta.color,
          border: `1.5px solid ${meta.border}`,
          color: meta.text,
          fontSize: sizes.fontSize,
          fontWeight: 700,
          padding: sizes.padding,
          borderRadius: 20,
          fontFamily: "'DM Sans', sans-serif",
          whiteSpace: 'nowrap',
        }}
        title={`${meta.label}${severity ? ` Â· Severity ${severity}/5` : ''}`}
      >
        <span style={{ fontSize: sizes.iconSize, lineHeight: 1 }}>{meta.icon}</span>
        {showLabel && meta.label}
      </span>

      {/* Optional severity chip */}
      {severity != null && sevColor && (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            background: sevColor.bg,
            color: sevColor.text,
            fontSize: sizes.fontSize - 1,
            fontWeight: 700,
            padding: '2px 7px',
            borderRadius: 20,
            fontFamily: "'DM Sans', sans-serif",
          }}
        >
          S{severity}
        </span>
      )}
    </span>
  );
}
````

--- FILE: frontend/src/components/OfflineFallbackCard.jsx ---
``jsx
import React from 'react';

export default function OfflineFallbackCard() {
  return (
    <div style={{
      background: '#fffbeb',
      border: '1.5px solid #fde68a',
      borderRadius: '16px',
      padding: '16px',
      marginBottom: '16px',
      display: 'flex',
      gap: '12px',
      alignItems: 'flex-start',
      fontFamily: "'DM Sans', sans-serif"
    }}>
      <div style={{
        background: '#fef3c7',
        width: 40,
        height: 40,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}>
        <span style={{ fontSize: '20px' }}>ðŸ“¶</span>
      </div>
      <div>
        <h3 style={{ 
          margin: 0, 
          fontFamily: "'Nunito', sans-serif", 
          fontSize: '16px', 
          fontWeight: 800, 
          color: '#92400e',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          Connection Lost
          <span style={{
            fontSize: '10px',
            background: '#ef4444',
            color: 'white',
            padding: '2px 6px',
            borderRadius: '12px',
            textTransform: 'uppercase',
            fontWeight: 800
          }}>Offline</span>
        </h3>
        <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#b45309', lineHeight: 1.4 }}>
          Don't worry! Your active coverage is protected. Any triggered claims will process server-side automatically. <strong>You will receive an SMS via our fallback channel.</strong>
        </p>
      </div>
    </div>
  );
}
````
