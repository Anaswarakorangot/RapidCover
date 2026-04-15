"""
External API services for weather, AQI, traffic, and platform status.

Hybrid architecture:
  - Attempts live API calls (OpenWeatherMap, WAQI) with timeout=5
  - Falls back to in-memory mock data if live call fails or key is empty
  - Every response includes "source": "live" | "mock" so the admin UI knows

In-memory mock conditions are still settable via set_conditions() for
admin simulation — the trigger engine uses get_current() which tries
live first, then mock.
"""

import httpx
import random
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from app.config import get_settings
from app.utils.time_utils import utcnow
from sqlalchemy.orm import Session


class DataSourceError(Exception):
    """Raised when a live data source fails and no mock fallback is allowed."""
    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"[{source}] {message}")


# ─── In-memory storage for simulated conditions ─────────────────────────────
_zone_conditions: dict[int, dict] = {}


# ─── Pydantic models ────────────────────────────────────────────────────────

class WeatherData(BaseModel):
    """Weather data from API."""
    zone_id: int
    temp_celsius: float
    rainfall_mm_hr: float
    humidity: float
    timestamp: datetime
    source: str = "mock"  # "live" | "mock"


class AQIData(BaseModel):
    """Air Quality Index data."""
    zone_id: int
    aqi: int
    pm25: float
    pm10: float
    category: str  # good, moderate, unhealthy, hazardous
    timestamp: datetime
    source: str = "mock"


class TrafficData(BaseModel):
    """Traffic/road status data."""
    zone_id: int
    blocked_roads: int
    congestion_level: str  # low, medium, high, severe
    avg_delay_mins: float
    timestamp: datetime
    source: str = "mock"


class PlatformStatus(BaseModel):
    """Dark store platform operational status."""
    zone_id: int
    is_open: bool
    closure_reason: Optional[str] = None
    closed_since: Optional[datetime] = None
    timestamp: datetime
    source: str = "mock"


class ShutdownStatus(BaseModel):
    """Civic shutdown/curfew status."""
    zone_id: int
    is_active: bool
    reason: Optional[str] = None
    started_at: Optional[datetime] = None
    expected_end: Optional[datetime] = None
    timestamp: datetime
    source: str = "mock"


# ─── Data source health tracking ────────────────────────────────────────────

_source_status: dict[str, dict] = {
    "openweathermap": {"status": "unknown", "last_check": None, "last_success": None},
    "waqi_aqi":       {"status": "unknown", "last_check": None, "last_success": None},
    "zepto_ops":      {"status": "mock",    "last_check": None, "last_success": None},
    "traffic_feed":   {"status": "mock",    "last_check": None, "last_success": None},
    "civic_api":      {"status": "mock",    "last_check": None, "last_success": None},
}


def get_source_health() -> dict:
    """Return current health status of all data sources."""
    return {k: {**v} for k, v in _source_status.items()}


def _update_source(name: str, success: bool):
    """Update data source health tracking."""
    now = utcnow()
    _source_status[name]["last_check"] = now
    if success:
        _source_status[name]["status"] = "live"
        _source_status[name]["last_success"] = now
    else:
        _source_status[name]["status"] = "mock"


# ─── Weather Observation Persistence ────────────────────────────────────────

def log_weather_observation(
    db: Session,
    weather_data: WeatherData,
    api_provider: str = None,
    confidence: float = None
) -> None:
    """
    Persist weather observation to database for historical tracking.

    Args:
        db: Database session
        weather_data: WeatherData object from API
        api_provider: e.g. "openweathermap", "mock"
        confidence: 0.0-1.0 confidence score
    """
    from app.models.weather_observation import WeatherObservation

    try:
        observation = WeatherObservation(
            zone_id=weather_data.zone_id,
            temp_celsius=weather_data.temp_celsius,
            rainfall_mm_hr=weather_data.rainfall_mm_hr,
            source=weather_data.source,
            api_provider=api_provider or "unknown",
            confidence=confidence or (1.0 if weather_data.source == "live" else 0.7),
            observed_at=weather_data.timestamp,
        )
        db.add(observation)
        db.commit()
    except Exception as e:
        print(f"[external_apis] Failed to log weather observation: {e}")
        db.rollback()


def log_aqi_observation(
    db: Session,
    aqi_data: AQIData,
    api_provider: str = None,
    confidence: float = None
) -> None:
    """
    Persist AQI observation to database for historical tracking.

    Args:
        db: Database session
        aqi_data: AQIData object from API
        api_provider: e.g. "waqi", "mock"
        confidence: 0.0-1.0 confidence score
    """
    from app.models.weather_observation import WeatherObservation

    try:
        observation = WeatherObservation(
            zone_id=aqi_data.zone_id,
            aqi=aqi_data.aqi,
            source=aqi_data.source,
            api_provider=api_provider or "unknown",
            confidence=confidence or (1.0 if aqi_data.source == "live" else 0.7),
            observed_at=aqi_data.timestamp,
        )
        db.add(observation)
        db.commit()
    except Exception as e:
        print(f"[external_apis] Failed to log AQI observation: {e}")
        db.rollback()


# ─── Helper: zone condition defaults ────────────────────────────────────────

def _get_zone_conditions(zone_id: int) -> dict:
    """Get or initialize conditions for a zone."""
    if zone_id not in _zone_conditions:
        _zone_conditions[zone_id] = {
            "weather": {"temp": 32.0, "rainfall": 0.0, "humidity": 60.0},
            "aqi": {"value": 150, "pm25": 55.0, "pm10": 85.0},
            "traffic": {"blocked": 0, "congestion": "medium", "delay": 5.0},
            "platform": {"is_open": True, "reason": None, "since": None},
            "shutdown": {"is_active": False, "reason": None, "since": None},
            "partial_disruption": {},  # For partial disruption simulation data
        }
    # Ensure partial_disruption key exists for older initialized zones
    if "partial_disruption" not in _zone_conditions[zone_id]:
        _zone_conditions[zone_id]["partial_disruption"] = {}
    return _zone_conditions[zone_id]


def set_partial_disruption_data(
    zone_id: int,
    expected_orders: Optional[int] = None,
    actual_orders: Optional[int] = None,
    partial_factor_override: Optional[float] = None,
) -> dict:
    """Set partial disruption simulation data for a zone."""
    conditions = _get_zone_conditions(zone_id)
    pd = conditions["partial_disruption"]

    if expected_orders is not None:
        pd["expected_orders"] = expected_orders
    if actual_orders is not None:
        pd["actual_orders"] = actual_orders
    if partial_factor_override is not None:
        pd["partial_factor_override"] = partial_factor_override

    return pd


def get_partial_disruption_data(zone_id: int) -> dict:
    """Get partial disruption data for a zone."""
    conditions = _get_zone_conditions(zone_id)
    return conditions.get("partial_disruption", {})


def clear_partial_disruption_data(zone_id: int) -> None:
    """Clear partial disruption data for a zone."""
    conditions = _get_zone_conditions(zone_id)
    conditions["partial_disruption"] = {}


# ═════════════════════════════════════════════════════════════════════════════
#  WEATHER — OpenWeatherMap with mock fallback
# ═════════════════════════════════════════════════════════════════════════════

class MockWeatherAPI:
    """Weather API: tries live OpenWeatherMap, falls back to mock."""

    @staticmethod
    def _fetch_live(zone_id: int, lat: float = None, lon: float = None) -> Optional[WeatherData]:
        """Try to fetch live weather from OpenWeatherMap."""
        settings = get_settings()
        api_key = settings.openweathermap_api_key

        if not api_key:
            return None

        try:
            # Use zone lat/lon if provided, else default coords by zone
            if lat is None or lon is None:
                lat, lon = _get_zone_coords(zone_id)

            r = httpx.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lon, "appid": api_key},
                timeout=5.0,
            )
            r.raise_for_status()
            d = r.json()

            _update_source("openweathermap", True)

            return WeatherData(
                zone_id=zone_id,
                temp_celsius=round(d["main"]["temp"] - 273.15, 1),
                rainfall_mm_hr=d.get("rain", {}).get("1h", 0.0),
                humidity=d["main"].get("humidity", 60.0),
                timestamp=utcnow(),
                source="live",
            )
        except Exception as e:
            _update_source("openweathermap", False)
            print(f"[external_apis] OpenWeatherMap failed for zone {zone_id}: {e}")
            return None

    @staticmethod
    def get_current(zone_id: int, lat: float = None, lon: float = None) -> WeatherData:
        """
        Get current weather — live first unless demo mode is enabled.

        Behavior:
        - Demo mode ON: returns mock/simulated data (for admin drills & testing)
        - Demo mode OFF: tries live API. If live fails, raises DataSourceError
          instead of silently falling back to mock data.

        Demo mode can be controlled via:
        - settings.demo_mode (global toggle)
        - settings.demo_exempt_cities (cities that always use live data)
        """
        settings = get_settings()

        if settings.demo_mode:
            # Demo mode — use simulated conditions
            conditions = _get_zone_conditions(zone_id)
            weather = conditions["weather"]
            return WeatherData(
                zone_id=zone_id,
                temp_celsius=weather["temp"],
                rainfall_mm_hr=weather["rainfall"],
                humidity=weather["humidity"],
                timestamp=utcnow(),
                source="mock",
            )

        # Production mode — live API only, no silent fallback
        live = MockWeatherAPI._fetch_live(zone_id, lat, lon)
        if live:
            return live

        # Live API failed — return mock with degraded flag rather than crashing
        # the trigger engine. The source="mock_fallback" signals this is NOT
        # intentional simulation but a degraded-mode response.
        _update_source("openweathermap", False)
        conditions = _get_zone_conditions(zone_id)
        weather = conditions["weather"]
        return WeatherData(
            zone_id=zone_id,
            temp_celsius=weather["temp"],
            rainfall_mm_hr=weather["rainfall"],
            humidity=weather["humidity"],
            timestamp=utcnow(),
            source="mock_fallback",
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        temp_celsius: Optional[float] = None,
        rainfall_mm_hr: Optional[float] = None,
        humidity: Optional[float] = None,
    ) -> WeatherData:
        """Set weather conditions for simulation (always returns mock data)."""
        conditions = _get_zone_conditions(zone_id)
        if temp_celsius is not None:
            conditions["weather"]["temp"] = temp_celsius
        if rainfall_mm_hr is not None:
            conditions["weather"]["rainfall"] = rainfall_mm_hr
        if humidity is not None:
            conditions["weather"]["humidity"] = humidity

        # Return mock data directly (simulations always use mock)
        weather = conditions["weather"]
        return WeatherData(
            zone_id=zone_id,
            temp_celsius=weather["temp"],
            rainfall_mm_hr=weather["rainfall"],
            humidity=weather["humidity"],
            timestamp=utcnow(),
            source="mock",
        )


# ═════════════════════════════════════════════════════════════════════════════
#  AQI — WAQI / CPCB with mock fallback
# ═════════════════════════════════════════════════════════════════════════════

class MockAQIAPI:
    """AQI API: tries live WAQI (aqicn.org), falls back to mock."""

    @staticmethod
    def _get_category(aqi: int) -> str:
        if aqi <= 50:
            return "good"
        elif aqi <= 100:
            return "moderate"
        elif aqi <= 200:
            return "unhealthy"
        elif aqi <= 300:
            return "very_unhealthy"
        else:
            return "hazardous"

    @staticmethod
    def _fetch_live(zone_id: int, lat: float = None, lon: float = None) -> Optional[AQIData]:
        """Try to fetch live AQI from WAQI."""
        settings = get_settings()
        api_key = settings.cpcb_api_key  # reusing cpcb_api_key for WAQI token

        if not api_key:
            return None

        try:
            if lat is None or lon is None:
                lat, lon = _get_zone_coords(zone_id)

            r = httpx.get(
                f"https://api.waqi.info/feed/geo:{lat};{lon}/",
                params={"token": api_key},
                timeout=5.0,
            )
            r.raise_for_status()
            data = r.json()

            if data.get("status") != "ok":
                return None

            aqi_val = int(data["data"]["aqi"])
            _update_source("waqi_aqi", True)

            return AQIData(
                zone_id=zone_id,
                aqi=aqi_val,
                pm25=data["data"].get("iaqi", {}).get("pm25", {}).get("v", 55.0),
                pm10=data["data"].get("iaqi", {}).get("pm10", {}).get("v", 85.0),
                category=MockAQIAPI._get_category(aqi_val),
                timestamp=utcnow(),
                source="live",
            )
        except Exception as e:
            _update_source("waqi_aqi", False)
            print(f"[external_apis] WAQI AQI failed for zone {zone_id}: {e}")
            return None

    @staticmethod
    def get_current(zone_id: int, lat: float = None, lon: float = None) -> AQIData:
        """
        Get current AQI — live first unless demo mode is enabled.

        Behavior:
        - Demo mode ON: returns mock/simulated data
        - Demo mode OFF: tries live API. If live fails, returns degraded-mode
          response with source="mock_fallback" instead of silently pretending.
        """
        settings = get_settings()

        if settings.demo_mode:
            # Demo mode — use simulated conditions
            conditions = _get_zone_conditions(zone_id)
            aqi_data = conditions["aqi"]
            return AQIData(
                zone_id=zone_id,
                aqi=aqi_data["value"],
                pm25=aqi_data["pm25"],
                pm10=aqi_data["pm10"],
                category=MockAQIAPI._get_category(aqi_data["value"]),
                timestamp=utcnow(),
                source="mock",
            )

        # Production mode — live API only, no silent fallback
        live = MockAQIAPI._fetch_live(zone_id, lat, lon)
        if live:
            return live

        # Live API failed — return degraded-mode response
        _update_source("waqi_aqi", False)
        conditions = _get_zone_conditions(zone_id)
        aqi_data = conditions["aqi"]
        return AQIData(
            zone_id=zone_id,
            aqi=aqi_data["value"],
            pm25=aqi_data["pm25"],
            pm10=aqi_data["pm10"],
            category=MockAQIAPI._get_category(aqi_data["value"]),
            timestamp=utcnow(),
            source="mock_fallback",
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        aqi: Optional[int] = None,
        pm25: Optional[float] = None,
        pm10: Optional[float] = None,
    ) -> AQIData:
        """Set AQI conditions for simulation (always returns mock data)."""
        conditions = _get_zone_conditions(zone_id)
        if aqi is not None:
            conditions["aqi"]["value"] = aqi
        if pm25 is not None:
            conditions["aqi"]["pm25"] = pm25
        if pm10 is not None:
            conditions["aqi"]["pm10"] = pm10

        # Return mock data directly (simulations always use mock)
        aqi_data = conditions["aqi"]
        return AQIData(
            zone_id=zone_id,
            aqi=aqi_data["value"],
            pm25=aqi_data["pm25"],
            pm10=aqi_data["pm10"],
            category=MockAQIAPI._get_category(aqi_data["value"]),
            timestamp=utcnow(),
            source="mock",
        )


# ═════════════════════════════════════════════════════════════════════════════
#  TRAFFIC — Mock (no real public API)
# ═════════════════════════════════════════════════════════════════════════════

class MockTrafficAPI:
    """Mock traffic/road status API."""

    @staticmethod
    def get_current(zone_id: int) -> TrafficData:
        conditions = _get_zone_conditions(zone_id)
        traffic = conditions["traffic"]
        return TrafficData(
            zone_id=zone_id,
            blocked_roads=traffic["blocked"],
            congestion_level=traffic["congestion"],
            avg_delay_mins=traffic["delay"],
            timestamp=utcnow(),
            source="mock",
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        blocked_roads: Optional[int] = None,
        congestion_level: Optional[str] = None,
        avg_delay_mins: Optional[float] = None,
    ) -> TrafficData:
        conditions = _get_zone_conditions(zone_id)
        if blocked_roads is not None:
            conditions["traffic"]["blocked"] = blocked_roads
        if congestion_level is not None:
            conditions["traffic"]["congestion"] = congestion_level
        if avg_delay_mins is not None:
            conditions["traffic"]["delay"] = avg_delay_mins
        return MockTrafficAPI.get_current(zone_id)


# ═════════════════════════════════════════════════════════════════════════════
#  PLATFORM (Zepto/Blinkit) — Mock
# ═════════════════════════════════════════════════════════════════════════════

class MockPlatformAPI:
    """Mock Q-Commerce platform API."""

    @staticmethod
    def get_store_status(zone_id: int) -> PlatformStatus:
        conditions = _get_zone_conditions(zone_id)
        platform = conditions["platform"]
        return PlatformStatus(
            zone_id=zone_id,
            is_open=platform["is_open"],
            closure_reason=platform["reason"],
            closed_since=platform["since"],
            timestamp=utcnow(),
            source="mock",
        )

    @staticmethod
    def set_store_closed(zone_id: int, reason: str) -> PlatformStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["platform"]["is_open"] = False
        conditions["platform"]["reason"] = reason
        conditions["platform"]["since"] = utcnow()
        return MockPlatformAPI.get_store_status(zone_id)

    @staticmethod
    def set_store_open(zone_id: int) -> PlatformStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["platform"]["is_open"] = True
        conditions["platform"]["reason"] = None
        conditions["platform"]["since"] = None
        return MockPlatformAPI.get_store_status(zone_id)


# ═════════════════════════════════════════════════════════════════════════════
#  CIVIC SHUTDOWN — Mock
# ═════════════════════════════════════════════════════════════════════════════

class MockCivicAPI:
    """Mock civic/government shutdown status API."""

    @staticmethod
    def get_shutdown_status(zone_id: int) -> ShutdownStatus:
        conditions = _get_zone_conditions(zone_id)
        shutdown = conditions["shutdown"]

        expected_end = None
        if shutdown["is_active"] and shutdown["since"]:
            expected_end = shutdown["since"] + timedelta(hours=4)

        return ShutdownStatus(
            zone_id=zone_id,
            is_active=shutdown["is_active"],
            reason=shutdown["reason"],
            started_at=shutdown["since"],
            expected_end=expected_end,
            timestamp=utcnow(),
            source="mock",
        )

    @staticmethod
    def set_shutdown(zone_id: int, reason: str) -> ShutdownStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["shutdown"]["is_active"] = True
        conditions["shutdown"]["reason"] = reason
        conditions["shutdown"]["since"] = utcnow()
        return MockCivicAPI.get_shutdown_status(zone_id)

    @staticmethod
    def clear_shutdown(zone_id: int) -> ShutdownStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["shutdown"]["is_active"] = False
        conditions["shutdown"]["reason"] = None
        conditions["shutdown"]["since"] = None
        return MockCivicAPI.get_shutdown_status(zone_id)


# ─── Utilities ───────────────────────────────────────────────────────────────

# Default coords for zones (used when zone model doesn't have lat/lon)
_ZONE_COORDS = {
    1: (12.9352, 77.6245),    # Koramangala, Bangalore
    2: (19.1136, 72.8697),    # Andheri East, Mumbai
    3: (28.6315, 77.2167),    # Connaught Place, Delhi
}


def _get_zone_coords(zone_id: int) -> tuple[float, float]:
    """Get lat/lon for a zone, with sensible defaults."""
    return _ZONE_COORDS.get(zone_id, (12.9716, 77.5946))  # default: Bangalore


def reset_all_conditions():
    """Reset all zone conditions to defaults."""
    global _zone_conditions
    _zone_conditions = {}


def get_all_active_conditions() -> dict[int, dict]:
    """Get all zones with non-default conditions."""
    return _zone_conditions.copy()


def apply_drill_preset(zone_id: int, preset_name: str) -> dict:
    """
    Apply drill preset conditions to a zone.

    This is a convenience wrapper that delegates to drill_service.apply_preset_conditions.
    Importing here to avoid circular imports.
    """
    from app.services.drill_service import apply_preset_conditions
    return apply_preset_conditions(zone_id, preset_name)


# ═════════════════════════════════════════════════════════════════════════════
#  ORACLE RELIABILITY ENGINE
#  Scores data sources and computes trigger confidence decisions.
# ═════════════════════════════════════════════════════════════════════════════

# Freshness thresholds (seconds)
SOURCE_FRESHNESS_LIMITS = {
    "openweathermap": 300,   # 5 minutes
    "waqi_aqi":       600,   # 10 minutes
    "zepto_ops":      60,    # 1 minute (mock)
    "traffic_feed":   120,   # 2 minutes (mock)
    "civic_api":      120,   # 2 minutes (mock)
}

# Agreement deviation threshold (as a fraction of the value)
AGREEMENT_DEVIATION_THRESHOLD = 0.20   # 20% deviation = disagreement


def compute_source_confidence(source_name: str) -> dict:
    """
    Compute reliability score for a single data source.

    Returns a dict with:
      - source_name
      - is_live: bool
      - freshness_ok: bool
      - staleness_seconds: float | None
      - reliability_score: 0.0–1.0
      - badge: "live" | "mock" | "stale"
      - last_success_iso: str | None
    """
    now = utcnow()
    info = _source_status.get(source_name, {})

    is_live = info.get("status") == "live"
    last_success = info.get("last_success")
    last_check = info.get("last_check")

    freshness_limit = SOURCE_FRESHNESS_LIMITS.get(source_name, 300)
    staleness_seconds = None
    freshness_ok = False

    if last_success:
        staleness_seconds = (now - last_success).total_seconds()
        freshness_ok = staleness_seconds <= freshness_limit

    # Score: live + fresh = 1.0, mock = 0.6, stale = 0.2
    if is_live and freshness_ok:
        reliability_score = 1.0
        badge = "live"
    elif is_live and not freshness_ok:
        reliability_score = 0.2
        badge = "stale"
    else:
        reliability_score = 0.6   # mock is useful but not ground-truth
        badge = "mock"

    return {
        "source_name": source_name,
        "is_live": is_live,
        "freshness_ok": freshness_ok,
        "staleness_seconds": round(staleness_seconds, 1) if staleness_seconds is not None else None,
        "freshness_limit_seconds": freshness_limit,
        "reliability_score": reliability_score,
        "badge": badge,
        "last_success_iso": last_success.isoformat() if last_success else None,
        "last_check_iso": last_check.isoformat() if last_check else None,
    }


def compute_trigger_confidence(
    primary_source: str,
    corroborating_sources: list[str] = None,
    primary_value: float = None,
    corroborating_values: list[float] = None,
) -> dict:
    """
    Compute trigger confidence given one primary + optional corroborating sources.

    Decision logic:
      - If primary stale and no corroboration → hold
      - If ≥2 sources agree strongly → confidence high → fire
      - If only mock source → demo mode, mark as mock
      - If live and mock disagree beyond threshold → reduce confidence
      - Otherwise standard scoring

    Returns:
      - trigger_confidence_score: 0.0–1.0
      - source_confidence_scores: dict per source
      - decision: "fire" | "hold" | "manual_review_simulated" | "fallback_mock_mode"
      - reason: human-readable reason string
      - agreement_score: 0.0–1.0 (1.0 = all sources agree perfectly)
    """
    corroborating_sources = corroborating_sources or []
    corroborating_values = corroborating_values or []

    primary_conf = compute_source_confidence(primary_source)
    corr_confs = [compute_source_confidence(s) for s in corroborating_sources]
    all_confs = {primary_source: primary_conf}
    for c in corr_confs:
        all_confs[c["source_name"]] = c

    # Compute agreement score
    all_values = []
    if primary_value is not None:
        all_values.append(primary_value)
    all_values.extend([v for v in corroborating_values if v is not None])

    agreement_score = 1.0
    if len(all_values) >= 2:
        mean_val = sum(all_values) / len(all_values)
        if mean_val > 0:
            max_dev = max(abs(v - mean_val) / mean_val for v in all_values)
            agreement_score = max(0.0, 1.0 - max_dev)

    # Base confidence from primary source
    base_conf = primary_conf["reliability_score"]
    # Boost from corroborating sources
    if corr_confs:
        avg_corr = sum(c["reliability_score"] for c in corr_confs) / len(corr_confs)
        trigger_confidence = base_conf * 0.6 + avg_corr * 0.4
    else:
        trigger_confidence = base_conf

    # Apply agreement penalty if sources disagree
    trigger_confidence *= (0.5 + 0.5 * agreement_score)
    trigger_confidence = round(min(1.0, max(0.0, trigger_confidence)), 3)

    # Decision logic
    primary_live = primary_conf["is_live"]
    primary_fresh = primary_conf["freshness_ok"]
    all_mock = all(c["badge"] == "mock" for c in all_confs.values())
    sources_agree = agreement_score >= (1.0 - AGREEMENT_DEVIATION_THRESHOLD)

    if all_mock:
        decision = "fallback_mock_mode"
        reason = "All sources are mock/simulated — demo mode active"
    elif not primary_live and not corr_confs:
        decision = "hold"
        reason = "Primary source offline and no corroborating sources available"
    elif not primary_fresh and not corroborating_sources:
        decision = "hold"
        reason = f"Primary source ({primary_source}) data is stale and unconfirmed"
    elif trigger_confidence >= 0.7 and sources_agree:
        decision = "fire"
        reason = f"Confidence {trigger_confidence:.0%} — sources agree (agreement={agreement_score:.0%})"
    elif trigger_confidence >= 0.5:
        decision = "manual_review_simulated"
        reason = f"Moderate confidence {trigger_confidence:.0%} — requires simulated review"
    else:
        decision = "hold"
        reason = f"Low confidence {trigger_confidence:.0%} — holding trigger"

    return {
        "trigger_confidence_score": trigger_confidence,
        "source_confidence_scores": all_confs,
        "decision": decision,
        "reason": reason,
        "agreement_score": round(agreement_score, 3),
        "primary_source": primary_source,
        "corroborating_sources": corroborating_sources,
        "computed_at": utcnow().isoformat(),
    }


def get_oracle_reliability_report(zone_id: int = None) -> dict:
    """
    Full oracle reliability report — all sources with freshness + overall system health.
    """
    all_sources = list(_source_status.keys())
    source_reports = {s: compute_source_confidence(s) for s in all_sources}

    live_count = sum(1 for r in source_reports.values() if r["badge"] == "live")
    stale_count = sum(1 for r in source_reports.values() if r["badge"] == "stale")
    mock_count = sum(1 for r in source_reports.values() if r["badge"] == "mock")

    avg_reliability = sum(r["reliability_score"] for r in source_reports.values()) / len(source_reports) if source_reports else 0.0

    if live_count >= 2:
        system_health = "healthy"
    elif live_count == 1:
        system_health = "degraded"
    elif stale_count > 0:
        system_health = "stale"
    else:
        system_health = "mock_mode"

    return {
        "zone_id": zone_id,
        "system_health": system_health,
        "average_reliability": round(avg_reliability, 3),
        "live_sources": live_count,
        "stale_sources": stale_count,
        "mock_sources": mock_count,
        "sources": source_reports,
        "computed_at": utcnow().isoformat(),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  PLATFORM ACTIVITY SIMULATION
#  Simulates per-partner delivery platform activity (Zomato/Swiggy/Zepto/Blinkit).
# ═════════════════════════════════════════════════════════════════════════════

# In-memory store: partner_id -> activity dict
_partner_platform_activity: dict[int, dict] = {}


# Default configurable simulation parameters (admin can override per-partner)
_PLATFORM_SIMULATION_DEFAULTS = {
    "platform_logged_in": True,
    "active_shift": True,
    "orders_accepted_recent": 6,
    "orders_completed_recent": 5,
    "zone_dwell_minutes": 60,
    "suspicious_inactivity": False,
    "platform": "zepto",
}


def _default_partner_activity(partner_id: int) -> dict:
    """
    Return default platform activity for a partner.

    Uses deterministic, configurable defaults instead of random values.
    Admin can override per-partner via set_partner_platform_activity().
    """
    now = utcnow()
    defaults = _PLATFORM_SIMULATION_DEFAULTS.copy()
    return {
        "partner_id": partner_id,
        "platform_logged_in": defaults["platform_logged_in"],
        "active_shift": defaults["active_shift"],
        "orders_accepted_recent": defaults["orders_accepted_recent"],
        "orders_completed_recent": defaults["orders_completed_recent"],
        "last_app_ping": now.isoformat(),
        "zone_dwell_minutes": defaults["zone_dwell_minutes"],
        "suspicious_inactivity": defaults["suspicious_inactivity"],
        "platform": defaults["platform"],
        "updated_at": now.isoformat(),
        "source": "simulated",
    }


def get_partner_platform_activity(partner_id: int) -> dict:
    """Get (or initialize) platform activity for a partner."""
    if partner_id not in _partner_platform_activity:
        _partner_platform_activity[partner_id] = _default_partner_activity(partner_id)
    return dict(_partner_platform_activity[partner_id])


def set_partner_platform_activity(partner_id: int, **kwargs) -> dict:
    """
    Update platform activity fields for a partner (admin control).

    Accepted kwargs: platform_logged_in, active_shift, orders_accepted_recent,
    orders_completed_recent, last_app_ping, zone_dwell_minutes,
    suspicious_inactivity, platform
    """
    existing = get_partner_platform_activity(partner_id)
    allowed_fields = {
        "platform_logged_in", "active_shift", "orders_accepted_recent",
        "orders_completed_recent", "last_app_ping", "zone_dwell_minutes",
        "suspicious_inactivity", "platform",
    }
    for key, val in kwargs.items():
        if key in allowed_fields:
            existing[key] = val
    existing["updated_at"] = utcnow().isoformat()
    existing["source"] = "admin_override"
    _partner_platform_activity[partner_id] = existing
    return dict(existing)


def evaluate_partner_platform_eligibility(partner_id: int) -> dict:
    """
    Check if a partner's platform activity qualifies them for a payout.

    Rules:
      - Must be logged into platform
      - Must have an active shift
      - Must have completed ≥1 order in recent window
      - Not flagged for suspicious inactivity
      - Must have pinged app within last 30 minutes

    Returns:
      - eligible: bool
      - score: 0.0–1.0 (platform activity score)
      - reasons: list of pass/fail reasons
      - activity: the raw activity dict
    """
    activity = get_partner_platform_activity(partner_id)
    reasons = []
    score_parts = []

    # Check: logged in
    if activity["platform_logged_in"]:
        reasons.append({"check": "platform_logged_in", "pass": True, "note": "Partner logged into platform app"})
        score_parts.append(1.0)
    else:
        reasons.append({"check": "platform_logged_in", "pass": False, "note": "Partner not logged into platform"})
        score_parts.append(0.0)

    # Check: active shift
    if activity["active_shift"]:
        reasons.append({"check": "active_shift", "pass": True, "note": "Partner on active shift"})
        score_parts.append(1.0)
    else:
        reasons.append({"check": "active_shift", "pass": False, "note": "Partner not on shift"})
        score_parts.append(0.0)

    # Check: recent orders completed
    completed = activity.get("orders_completed_recent", 0)
    if completed >= 1:
        reasons.append({"check": "orders_completed_recent", "pass": True, "note": f"{completed} orders completed recently"})
        score_parts.append(min(1.0, completed / 5.0))
    else:
        reasons.append({"check": "orders_completed_recent", "pass": False, "note": "No recent order completions"})
        score_parts.append(0.0)

    # Check: suspicious inactivity
    if not activity.get("suspicious_inactivity", False):
        reasons.append({"check": "suspicious_inactivity", "pass": True, "note": "No inactivity flags"})
        score_parts.append(1.0)
    else:
        reasons.append({"check": "suspicious_inactivity", "pass": False, "note": "Suspicious inactivity flag active"})
        score_parts.append(0.0)

    # Check: last app ping within 30 min
    try:
        last_ping = datetime.fromisoformat(activity["last_app_ping"])
        minutes_since_ping = (utcnow() - last_ping).total_seconds() / 60.0
        if minutes_since_ping <= 30:
            reasons.append({"check": "last_app_ping", "pass": True, "note": f"Last ping {minutes_since_ping:.0f}m ago"})
            score_parts.append(1.0)
        else:
            reasons.append({"check": "last_app_ping", "pass": False, "note": f"Last ping {minutes_since_ping:.0f}m ago (>30m)"})
            score_parts.append(0.0)
    except Exception:
        reasons.append({"check": "last_app_ping", "pass": False, "note": "Cannot parse last ping timestamp"})
        score_parts.append(0.0)

    score = sum(score_parts) / len(score_parts) if score_parts else 0.0
    eligible = all(r["pass"] for r in reasons)

    return {
        "partner_id": partner_id,
        "eligible": eligible,
        "score": round(score, 3),
        "reasons": reasons,
        "activity": activity,
    }