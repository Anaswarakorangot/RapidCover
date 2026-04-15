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
from app.utils.time_utils import utcnow
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
        profile.last_updated_at = utcnow()
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
        recomputed_at=utcnow(),
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
