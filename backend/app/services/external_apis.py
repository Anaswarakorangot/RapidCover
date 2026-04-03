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
    now = datetime.utcnow()
    _source_status[name]["last_check"] = now
    if success:
        _source_status[name]["status"] = "live"
        _source_status[name]["last_success"] = now
    else:
        _source_status[name]["status"] = "mock"


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
        }
    return _zone_conditions[zone_id]


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
                timestamp=datetime.utcnow(),
                source="live",
            )
        except Exception as e:
            _update_source("openweathermap", False)
            print(f"[external_apis] OpenWeatherMap failed for zone {zone_id}: {e}")
            return None

    @staticmethod
    def get_current(zone_id: int, lat: float = None, lon: float = None) -> WeatherData:
        """Get current weather — live first, mock fallback."""
        live = MockWeatherAPI._fetch_live(zone_id, lat, lon)
        if live:
            return live

        # Fallback to mock/simulated conditions
        conditions = _get_zone_conditions(zone_id)
        weather = conditions["weather"]
        return WeatherData(
            zone_id=zone_id,
            temp_celsius=weather["temp"],
            rainfall_mm_hr=weather["rainfall"],
            humidity=weather["humidity"],
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        temp_celsius: Optional[float] = None,
        rainfall_mm_hr: Optional[float] = None,
        humidity: Optional[float] = None,
    ) -> WeatherData:
        """Set weather conditions for simulation."""
        conditions = _get_zone_conditions(zone_id)
        if temp_celsius is not None:
            conditions["weather"]["temp"] = temp_celsius
        if rainfall_mm_hr is not None:
            conditions["weather"]["rainfall"] = rainfall_mm_hr
        if humidity is not None:
            conditions["weather"]["humidity"] = humidity
        return MockWeatherAPI.get_current(zone_id)


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
                timestamp=datetime.utcnow(),
                source="live",
            )
        except Exception as e:
            _update_source("waqi_aqi", False)
            print(f"[external_apis] WAQI AQI failed for zone {zone_id}: {e}")
            return None

    @staticmethod
    def get_current(zone_id: int, lat: float = None, lon: float = None) -> AQIData:
        """Get current AQI — live first, mock fallback."""
        live = MockAQIAPI._fetch_live(zone_id, lat, lon)
        if live:
            return live

        conditions = _get_zone_conditions(zone_id)
        aqi_data = conditions["aqi"]
        return AQIData(
            zone_id=zone_id,
            aqi=aqi_data["value"],
            pm25=aqi_data["pm25"],
            pm10=aqi_data["pm10"],
            category=MockAQIAPI._get_category(aqi_data["value"]),
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        aqi: Optional[int] = None,
        pm25: Optional[float] = None,
        pm10: Optional[float] = None,
    ) -> AQIData:
        """Set AQI conditions for simulation."""
        conditions = _get_zone_conditions(zone_id)
        if aqi is not None:
            conditions["aqi"]["value"] = aqi
        if pm25 is not None:
            conditions["aqi"]["pm25"] = pm25
        if pm10 is not None:
            conditions["aqi"]["pm10"] = pm10
        return MockAQIAPI.get_current(zone_id)


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
            timestamp=datetime.utcnow(),
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
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_store_closed(zone_id: int, reason: str) -> PlatformStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["platform"]["is_open"] = False
        conditions["platform"]["reason"] = reason
        conditions["platform"]["since"] = datetime.utcnow()
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
            timestamp=datetime.utcnow(),
            source="mock",
        )

    @staticmethod
    def set_shutdown(zone_id: int, reason: str) -> ShutdownStatus:
        conditions = _get_zone_conditions(zone_id)
        conditions["shutdown"]["is_active"] = True
        conditions["shutdown"]["reason"] = reason
        conditions["shutdown"]["since"] = datetime.utcnow()
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
