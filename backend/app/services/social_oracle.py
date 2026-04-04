"""
Social Oracle Verification Engine.

Verifies social media posts against real-world data:
  1. Extract location → map to a zone with GPS coordinates
  2. Extract event type (rain, flood, heat, AQI, shutdown, closure)
  3. Call real APIs (OpenWeatherMap, WAQI) using zone GPS
  4. Compare claimed conditions vs. actual sensor data
  5. Compute a confidence score (0–100%)

This replaces the old keyword-match fake logic.
"""

import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.zone import Zone
from app.services.external_apis import (
    MockWeatherAPI, MockAQIAPI, MockTrafficAPI,
    _get_zone_coords,
)


# ─── Event type classification ──────────────────────────────────────────────

EVENT_KEYWORDS: dict[str, list[str]] = {
    "rain": [
        "rain", "raining", "rainfall", "heavy rain", "downpour",
        "waterlog", "waterlogging", "waterlogged", "flood", "flooded",
        "flooding", "inundated", "submerged", "knee-level", "waist-level",
        "water-logged", "water logging", "deluge", "cloudburst",
        "thunderstorm", "storm", "cyclone", "torrent",
        "drainage", "overflowing", "nala", "puddle",
    ],
    "heat": [
        "heat", "heatwave", "heat wave", "scorching",
        "sunstroke", "heat stroke", "dehydration", "temperature",
        "hot", "extreme heat", "sweltering", "boiling",
        "45°", "44°", "43°", "42°", "41°", "40°",
        "45 degree", "44 degree", "43 degree", "42 degree",
    ],
    "aqi": [
        "aqi", "air quality", "pollution", "smog", "haze",
        "pm2.5", "pm10", "hazardous air", "toxic air",
        "breathing difficulty", "breathing problem", "breathing issues", "breathing issue",
        "can't breathe", "cannot breathe", "suffocating",
        "visibility", "dust", "smoke",
    ],
    "shutdown": [
        "shutdown", "curfew", "bandh", "strike", "hartal",
        "section 144", "lockdown", "protest", "riot",
        "violence", "lathi", "tear gas",
        "road block", "roadblock", "barricade",
    ],
    "closure": [
        "store closed", "dark store", "warehouse closed",
        "hub closed", "centre closed", "center closed",
        "not operational", "operations suspended",
        "force majeure", "closed down", "shut down temporarily",
    ],
}

# Keywords that indicate fake / spam / joke posts
FAKE_INDICATORS = [
    "alien", "ufo", "zombie", "just kidding", "jk", "lol",
    "prank", "hoax", "fake", "satire", "meme", "clickbait",
    "not real", "rumor", "rumour",
]

# Common location name → zone name mapping (Indian cities / areas)
# This supplements the DB zone name lookup
LOCATION_ALIASES: dict[str, str] = {
    # Bangalore
    "koramangala": "Koramangala",
    "indiranagar": "Indiranagar",
    "hsr layout": "HSR Layout",
    "hsr": "HSR Layout",
    "whitefield": "Whitefield",
    "electronic city": "Electronic City",
    "marathahalli": "Marathahalli",
    "bellandur": "Bellandur",
    "btm layout": "BTM Layout",
    "btm": "BTM Layout",
    "jayanagar": "Jayanagar",
    "jp nagar": "JP Nagar",
    "rajajinagar": "Rajajinagar",
    "hebbal": "Hebbal",
    "yelahanka": "Yelahanka",
    "bangalore": "Bangalore",
    "bengaluru": "Bangalore",
    "blr": "Bangalore",
    # Mumbai
    "andheri": "Andheri East",
    "andheri east": "Andheri East",
    "andheri west": "Andheri West",
    "bandra": "Bandra",
    "dadar": "Dadar",
    "lower parel": "Lower Parel",
    "goregaon": "Goregaon",
    "malad": "Malad",
    "borivali": "Borivali",
    "mumbai": "Mumbai",
    # Delhi / NCR
    "connaught place": "Connaught Place",
    "cp": "Connaught Place",
    "dwarka": "Dwarka",
    "noida": "Noida",
    "gurgaon": "Gurgaon",
    "gurugram": "Gurgaon",
    "lajpat nagar": "Lajpat Nagar",
    "saket": "Saket",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    # Chennai
    "chennai": "Chennai",
    "t nagar": "T Nagar",
    "anna nagar": "Anna Nagar",
    "adyar": "Adyar",
    # Hyderabad
    "hyderabad": "Hyderabad",
    "hitec city": "Hitec City",
    "hi-tech city": "Hitec City",
    "hitech city": "Hitec City",
    "madhapur": "Madhapur",
    "gachibowli": "Gachibowli",
    # Pune
    "pune": "Pune",
    "kothrud": "Kothrud",
    "hinjewadi": "Hinjewadi",
    # Kolkata
    "kolkata": "Kolkata",
    "salt lake": "Salt Lake",
    # Generic
    "100ft road": "Indiranagar",
    "100 feet road": "Indiranagar",
    "silk board": "HSR Layout",
    "outer ring road": "Bellandur",
    "orr": "Bellandur",
}

# City-level fallback coordinates (when no zone match in DB)
CITY_COORDS: dict[str, tuple[float, float]] = {
    "Bangalore": (12.9716, 77.5946),
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Pune": (18.5204, 73.8567),
    "Kolkata": (22.5726, 88.3639),
}


# ─── Data classes for structured results ─────────────────────────────────────

@dataclass
class LocationResult:
    found: bool = False
    raw_match: str = ""
    zone_name: str = ""
    zone_code: str = ""
    zone_id: Optional[int] = None
    lat: float = 0.0
    lon: float = 0.0
    source: str = ""  # "database", "alias", "city_fallback"


@dataclass
class EventResult:
    found: bool = False
    event_type: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    is_suspicious: bool = False  # fake indicators found
    suspicious_keywords: list[str] = field(default_factory=list)


@dataclass
class APIVerification:
    """Result from one API check."""
    source: str = ""          # "OpenWeatherMap", "WAQI"
    is_live: bool = False     # True if real API responded
    data: dict = field(default_factory=dict)
    supports_claim: bool = False
    reason: str = ""


@dataclass
class OracleVerdict:
    """Final oracle decision."""
    confidence: float = 0.0
    verified: bool = False
    zone_code: str = ""
    trigger_type: str = ""
    summary: str = ""


# ─── Core extraction functions ───────────────────────────────────────────────

def extract_location(text: str, db: Session) -> LocationResult:
    """
    Extract a location from raw text and map it to a zone.

    Strategy:
      1. Try to match a zone code directly (e.g. BLR-047)
      2. Try to match known location aliases
      3. Try to match zone names from the DB
      4. Fall back to city-level match
    """
    lower = text.lower()
    result = LocationResult()

    # 1. Direct zone code match (BLR-047, MUM-021, etc.)
    code_match = re.search(r'\b([A-Z]{3}-\d{3})\b', text, re.IGNORECASE)
    if code_match:
        code = code_match.group(1).upper()
        zone = db.query(Zone).filter(Zone.code == code).first()
        if zone:
            lat = zone.dark_store_lat or _get_zone_coords(zone.id)[0]
            lon = zone.dark_store_lng or _get_zone_coords(zone.id)[1]
            return LocationResult(
                found=True, raw_match=code, zone_name=zone.name,
                zone_code=zone.code, zone_id=zone.id,
                lat=lat, lon=lon, source="database"
            )

    # 2. Match location aliases
    best_alias_match = ""
    best_alias_name = ""
    for alias, canonical_name in LOCATION_ALIASES.items():
        if alias in lower and len(alias) > len(best_alias_match):
            best_alias_match = alias
            best_alias_name = canonical_name

    if best_alias_name:
        # Try to find in DB
        zone = db.query(Zone).filter(
            Zone.name.ilike(f"%{best_alias_name}%")
        ).first()
        if zone:
            lat = zone.dark_store_lat or _get_zone_coords(zone.id)[0]
            lon = zone.dark_store_lng or _get_zone_coords(zone.id)[1]
            return LocationResult(
                found=True, raw_match=best_alias_match,
                zone_name=zone.name, zone_code=zone.code,
                zone_id=zone.id, lat=lat, lon=lon, source="database"
            )

        # Not in DB — try city-level fallback
        for city_name, coords in CITY_COORDS.items():
            if city_name.lower() in best_alias_name.lower() or best_alias_name in LOCATION_ALIASES.values():
                # Find the city this alias belongs to
                city = _guess_city_for_area(best_alias_name)
                if city and city in CITY_COORDS:
                    lat, lon = CITY_COORDS[city]
                    return LocationResult(
                        found=True, raw_match=best_alias_match,
                        zone_name=best_alias_name, zone_code=f"{city[:3].upper()}-UNK",
                        lat=lat, lon=lon, source="alias"
                    )

    # 3. Match zone names from DB directly
    zones = db.query(Zone).all()
    for zone in zones:
        if zone.name.lower() in lower or lower in zone.name.lower():
            lat = zone.dark_store_lat or _get_zone_coords(zone.id)[0]
            lon = zone.dark_store_lng or _get_zone_coords(zone.id)[1]
            return LocationResult(
                found=True, raw_match=zone.name.lower(),
                zone_name=zone.name, zone_code=zone.code,
                zone_id=zone.id, lat=lat, lon=lon, source="database"
            )

    # 4. City-level fallback
    for city_name, coords in CITY_COORDS.items():
        if city_name.lower() in lower:
            zone = db.query(Zone).filter(Zone.city.ilike(f"%{city_name}%")).first()
            if zone:
                lat = zone.dark_store_lat or coords[0]
                lon = zone.dark_store_lng or coords[1]
                return LocationResult(
                    found=True, raw_match=city_name.lower(),
                    zone_name=zone.name, zone_code=zone.code,
                    zone_id=zone.id, lat=lat, lon=lon, source="database"
                )
            return LocationResult(
                found=True, raw_match=city_name.lower(),
                zone_name=city_name, zone_code=f"{city_name[:3].upper()}-001",
                lat=coords[0], lon=coords[1], source="city_fallback"
            )

    return result  # not found


def extract_event_type(text: str) -> EventResult:
    """
    Classify the event type from raw text.
    Also flags suspicious / fake content.
    """
    lower = text.lower()
    result = EventResult()

    # Check for fake indicators first
    for word in FAKE_INDICATORS:
        if word in lower:
            result.is_suspicious = True
            result.suspicious_keywords.append(word)

    # Score each event type by number of keyword matches
    scores: dict[str, list[str]] = {}
    for event_type, keywords in EVENT_KEYWORDS.items():
        matched = []
        for kw in keywords:
            if kw in lower:
                matched.append(kw)
        if matched:
            scores[event_type] = matched

    if scores:
        # Pick the event type with the most matches
        best = max(scores, key=lambda k: len(scores[k]))
        result.found = True
        result.event_type = best
        result.matched_keywords = scores[best]

    return result


def _guess_city_for_area(area_name: str) -> Optional[str]:
    """Guess which city an area belongs to."""
    bangalore_areas = [
        "Koramangala", "Indiranagar", "HSR Layout", "Whitefield",
        "Electronic City", "Marathahalli", "Bellandur", "BTM Layout",
        "Jayanagar", "JP Nagar", "Rajajinagar", "Hebbal", "Yelahanka",
    ]
    mumbai_areas = [
        "Andheri East", "Andheri West", "Bandra", "Dadar",
        "Lower Parel", "Goregaon", "Malad", "Borivali",
    ]
    delhi_areas = [
        "Connaught Place", "Dwarka", "Noida", "Gurgaon",
        "Lajpat Nagar", "Saket",
    ]
    chennai_areas = ["T Nagar", "Anna Nagar", "Adyar"]
    hyderabad_areas = ["Hitec City", "Madhapur", "Gachibowli"]

    if area_name in bangalore_areas:
        return "Bangalore"
    if area_name in mumbai_areas:
        return "Mumbai"
    if area_name in delhi_areas:
        return "Delhi"
    if area_name in chennai_areas:
        return "Chennai"
    if area_name in hyderabad_areas:
        return "Hyderabad"
    return None


# ─── API verification ────────────────────────────────────────────────────────

def verify_weather(lat: float, lon: float, zone_id: int, event_type: str) -> APIVerification:
    """
    Call OpenWeatherMap for live weather data and check
    if conditions support the claimed event.
    """
    result = APIVerification(source="OpenWeatherMap")

    try:
        weather = MockWeatherAPI.get_current(
            zone_id=zone_id or 1, lat=lat, lon=lon
        )
        result.is_live = weather.source == "live"
        result.data = {
            "rainfall_mm_hr": weather.rainfall_mm_hr,
            "temp_celsius": weather.temp_celsius,
            "humidity": weather.humidity,
            "source": weather.source,
        }

        if event_type == "rain":
            # Check for rain / waterlogging conditions
            if weather.rainfall_mm_hr >= 5.0:
                result.supports_claim = True
                result.reason = (
                    f"Rainfall {weather.rainfall_mm_hr} mm/hr detected "
                    f"(threshold: 5 mm/hr) — CONFIRMS flooding claim"
                )
            elif weather.humidity >= 85:
                # High humidity can accompany waterlogging even if
                # current rain reading is low (post-rain)
                result.supports_claim = True
                result.reason = (
                    f"Rainfall {weather.rainfall_mm_hr} mm/hr is below threshold, "
                    f"but humidity {weather.humidity}% is very high — "
                    f"PARTIAL confirmation (post-rain waterlogging possible)"
                )
            else:
                result.supports_claim = False
                result.reason = (
                    f"Rainfall {weather.rainfall_mm_hr} mm/hr, "
                    f"humidity {weather.humidity}% — "
                    f"conditions do NOT support flooding claim"
                )

        elif event_type == "heat":
            if weather.temp_celsius >= 38.0:
                result.supports_claim = True
                result.reason = (
                    f"Temperature {weather.temp_celsius}°C "
                    f"(threshold: 38°C) — CONFIRMS heat claim"
                )
            else:
                result.supports_claim = False
                result.reason = (
                    f"Temperature {weather.temp_celsius}°C — "
                    f"below heat threshold (38°C)"
                )

        else:
            # For non-weather events, weather data is supplementary
            result.reason = (
                f"Weather: {weather.temp_celsius}°C, "
                f"{weather.rainfall_mm_hr} mm/hr rain, "
                f"{weather.humidity}% humidity (supplementary data)"
            )

    except Exception as e:
        result.reason = f"Weather API call failed: {e}"

    return result


def verify_aqi(lat: float, lon: float, zone_id: int, event_type: str) -> APIVerification:
    """
    Call WAQI/CPCB for real AQI data and check
    if conditions support the claimed event.
    """
    result = APIVerification(source="WAQI/CPCB")

    try:
        aqi_data = MockAQIAPI.get_current(
            zone_id=zone_id or 1, lat=lat, lon=lon
        )
        result.is_live = aqi_data.source == "live"
        result.data = {
            "aqi": aqi_data.aqi,
            "pm25": aqi_data.pm25,
            "pm10": aqi_data.pm10,
            "category": aqi_data.category,
            "source": aqi_data.source,
        }

        if event_type == "aqi":
            if aqi_data.aqi >= 200:
                result.supports_claim = True
                result.reason = (
                    f"AQI {aqi_data.aqi} ({aqi_data.category}) — "
                    f"CONFIRMS hazardous air quality claim"
                )
            elif aqi_data.aqi >= 100:
                result.supports_claim = True
                result.reason = (
                    f"AQI {aqi_data.aqi} ({aqi_data.category}) — "
                    f"CONFIRMS unhealthy air quality. Delivery disruption likely."
                )
            else:
                result.supports_claim = False
                result.reason = (
                    f"AQI {aqi_data.aqi} ({aqi_data.category}) — "
                    f"air quality is within safe limits, does NOT support claim"
                )
        else:
            result.reason = (
                f"AQI: {aqi_data.aqi} ({aqi_data.category}), "
                f"PM2.5: {aqi_data.pm25}, PM10: {aqi_data.pm10} "
                f"(supplementary data)"
            )

    except Exception as e:
        result.reason = f"AQI API call failed: {e}"

    return result


def verify_traffic(zone_id: int, event_type: str) -> APIVerification:
    """
    Check traffic conditions for the zone.
    Currently mock-based but provides cross-validation signals.
    """
    result = APIVerification(source="Traffic/Congestion Feed")

    try:
        traffic = MockTrafficAPI.get_current(zone_id or 1)
        result.is_live = traffic.source == "live"
        result.data = {
            "congestion_level": traffic.congestion_level,
            "blocked_roads": traffic.blocked_roads,
            "avg_delay_mins": traffic.avg_delay_mins,
            "source": traffic.source,
        }

        if event_type in ["rain", "shutdown"]:
            if traffic.congestion_level in ["high", "severe"] or traffic.blocked_roads > 0:
                result.supports_claim = True
                result.reason = (
                    f"Congestion: {traffic.congestion_level}, "
                    f"{traffic.blocked_roads} blocked roads, "
                    f"{traffic.avg_delay_mins} min avg delay — "
                    f"SUPPORTS disruption claim"
                )
            else:
                result.supports_claim = False
                result.reason = (
                    f"Congestion: {traffic.congestion_level}, "
                    f"no blocked roads — traffic is nominal"
                )
        else:
            result.reason = (
                f"Traffic: {traffic.congestion_level} congestion, "
                f"{traffic.blocked_roads} blocked roads "
                f"(supplementary)"
            )

    except Exception as e:
        result.reason = f"Traffic API failed: {e}"

    return result


# ─── Confidence scoring ──────────────────────────────────────────────────────

def compute_confidence(
    location: LocationResult,
    event: EventResult,
    weather_check: APIVerification,
    aqi_check: APIVerification,
    traffic_check: APIVerification,
) -> OracleVerdict:
    """
    Compute a final confidence score (0–100%) based on all checks.

    Scoring weights:
      - Location found in DB:          +15
      - Event type identified:         +10
      - Primary API supports claim:    +40 (live) / +25 (mock)
      - Secondary API supports:        +15 (live) / +8 (mock)
      - Traffic cross-validation:      +10
      - No fake indicators:            +10
      - Multiple keyword matches:      +5 per extra match (up to +10)

    Penalties:
      - Fake indicators found:         -40
      - No location found:             -20
      - No event identified:           -25
      - Primary API contradicts:       -30
    """
    score = 0.0
    event_type = event.event_type

    # Location
    if location.found:
        if location.source == "database":
            score += 15
        elif location.source == "alias":
            score += 12
        else:
            score += 8
    else:
        score -= 20

    # Event identification
    if event.found:
        score += 10
        # Bonus for multiple keyword matches (strong signal)
        extra_kw = min(len(event.matched_keywords) - 1, 2)
        score += extra_kw * 5
    else:
        score -= 25

    # Fake indicators
    if event.is_suspicious:
        score -= 40

    if not event.is_suspicious:
        score += 10

    # Primary API check (weather for rain/heat, AQI for aqi events)
    primary = weather_check if event_type in ["rain", "heat"] else aqi_check
    if primary.supports_claim:
        score += 40 if primary.is_live else 25
    elif event.found and event_type in ["rain", "heat", "aqi"]:
        # Primary API specifically contradicts
        if not primary.supports_claim and primary.data:
            score -= 15

    # Secondary API (the other one)
    secondary = aqi_check if event_type in ["rain", "heat"] else weather_check
    if secondary.supports_claim:
        score += 15 if secondary.is_live else 8

    # Traffic cross-validation
    if traffic_check.supports_claim:
        score += 10

    # For shutdown/closure events (no reliable API), give partial credit
    # based on text analysis quality
    if event_type in ["shutdown", "closure"]:
        if event.found and location.found and not event.is_suspicious:
            score += 20  # Text-only verification bonus
        if len(event.matched_keywords) >= 2:
            score += 10

    # Clamp to 0–100
    score = max(0.0, min(100.0, score))

    verified = score >= 70.0
    zone_code = location.zone_code if location.found else "UNKNOWN"

    if verified:
        summary = f"Confidence {score:.1f}% — Claim VERIFIED. Autonomous trigger eligible."
    elif score >= 40:
        summary = f"Confidence {score:.1f}% — INCONCLUSIVE. Manual review recommended."
    else:
        summary = f"Confidence {score:.1f}% — Claim REJECTED. Likely false alarm or misinformation."

    return OracleVerdict(
        confidence=round(score, 1),
        verified=verified,
        zone_code=zone_code,
        trigger_type=event_type or "unknown",
        summary=summary,
    )


# ─── Main orchestrator ───────────────────────────────────────────────────────

def run_full_verification(text: str, db: Session) -> dict:
    """
    Run the complete Social Oracle pipeline and return all results.

    Returns a dict with all intermediate results so the API layer
    can stream them as NDJSON log lines.
    """
    location = extract_location(text, db)
    event = extract_event_type(text)

    zone_id = location.zone_id or 0

    weather_check = verify_weather(
        location.lat, location.lon, zone_id, event.event_type
    )
    aqi_check = verify_aqi(
        location.lat, location.lon, zone_id, event.event_type
    )
    traffic_check = verify_traffic(zone_id, event.event_type)

    verdict = compute_confidence(
        location, event, weather_check, aqi_check, traffic_check
    )

    return {
        "location": location,
        "event": event,
        "weather": weather_check,
        "aqi": aqi_check,
        "traffic": traffic_check,
        "verdict": verdict,
    }
