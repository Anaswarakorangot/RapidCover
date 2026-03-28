"""
Mock external API services for weather, AQI, traffic, and platform status.

These simulate real-world data sources that would trigger parametric insurance payouts.
In production, these would connect to actual APIs (OpenWeatherMap, CPCB AQI, etc.).
"""

import random
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel


# In-memory storage for simulated conditions per zone
# In production, this would be Redis or similar
_zone_conditions: dict[int, dict] = {}


class WeatherData(BaseModel):
    """Weather data from API."""
    zone_id: int
    temp_celsius: float
    rainfall_mm_hr: float
    humidity: float
    timestamp: datetime


class AQIData(BaseModel):
    """Air Quality Index data."""
    zone_id: int
    aqi: int
    pm25: float
    pm10: float
    category: str  # good, moderate, unhealthy, hazardous
    timestamp: datetime


class TrafficData(BaseModel):
    """Traffic/road status data."""
    zone_id: int
    blocked_roads: int
    congestion_level: str  # low, medium, high, severe
    avg_delay_mins: float
    timestamp: datetime


class PlatformStatus(BaseModel):
    """Dark store platform operational status."""
    zone_id: int
    is_open: bool
    closure_reason: Optional[str] = None
    closed_since: Optional[datetime] = None
    timestamp: datetime


class ShutdownStatus(BaseModel):
    """Civic shutdown/curfew status."""
    zone_id: int
    is_active: bool
    reason: Optional[str] = None
    started_at: Optional[datetime] = None
    expected_end: Optional[datetime] = None
    timestamp: datetime


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


class MockWeatherAPI:
    """Mock weather API service."""

    @staticmethod
    def get_current(zone_id: int) -> WeatherData:
        """Get current weather for a zone."""
        conditions = _get_zone_conditions(zone_id)
        weather = conditions["weather"]

        return WeatherData(
            zone_id=zone_id,
            temp_celsius=weather["temp"],
            rainfall_mm_hr=weather["rainfall"],
            humidity=weather["humidity"],
            timestamp=datetime.utcnow(),
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


class MockAQIAPI:
    """Mock Air Quality Index API service."""

    @staticmethod
    def _get_category(aqi: int) -> str:
        """Get AQI category from value."""
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
    def get_current(zone_id: int) -> AQIData:
        """Get current AQI for a zone."""
        conditions = _get_zone_conditions(zone_id)
        aqi_data = conditions["aqi"]

        return AQIData(
            zone_id=zone_id,
            aqi=aqi_data["value"],
            pm25=aqi_data["pm25"],
            pm10=aqi_data["pm10"],
            category=MockAQIAPI._get_category(aqi_data["value"]),
            timestamp=datetime.utcnow(),
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


class MockTrafficAPI:
    """Mock traffic/road status API service."""

    @staticmethod
    def get_current(zone_id: int) -> TrafficData:
        """Get current traffic status for a zone."""
        conditions = _get_zone_conditions(zone_id)
        traffic = conditions["traffic"]

        return TrafficData(
            zone_id=zone_id,
            blocked_roads=traffic["blocked"],
            congestion_level=traffic["congestion"],
            avg_delay_mins=traffic["delay"],
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def set_conditions(
        zone_id: int,
        blocked_roads: Optional[int] = None,
        congestion_level: Optional[str] = None,
        avg_delay_mins: Optional[float] = None,
    ) -> TrafficData:
        """Set traffic conditions for simulation."""
        conditions = _get_zone_conditions(zone_id)

        if blocked_roads is not None:
            conditions["traffic"]["blocked"] = blocked_roads
        if congestion_level is not None:
            conditions["traffic"]["congestion"] = congestion_level
        if avg_delay_mins is not None:
            conditions["traffic"]["delay"] = avg_delay_mins

        return MockTrafficAPI.get_current(zone_id)


class MockPlatformAPI:
    """Mock Q-Commerce platform (Zepto/Blinkit) API service."""

    @staticmethod
    def get_store_status(zone_id: int) -> PlatformStatus:
        """Get dark store operational status."""
        conditions = _get_zone_conditions(zone_id)
        platform = conditions["platform"]

        return PlatformStatus(
            zone_id=zone_id,
            is_open=platform["is_open"],
            closure_reason=platform["reason"],
            closed_since=platform["since"],
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def set_store_closed(zone_id: int, reason: str) -> PlatformStatus:
        """Mark a dark store as closed."""
        conditions = _get_zone_conditions(zone_id)
        conditions["platform"]["is_open"] = False
        conditions["platform"]["reason"] = reason
        conditions["platform"]["since"] = datetime.utcnow()

        return MockPlatformAPI.get_store_status(zone_id)

    @staticmethod
    def set_store_open(zone_id: int) -> PlatformStatus:
        """Mark a dark store as open."""
        conditions = _get_zone_conditions(zone_id)
        conditions["platform"]["is_open"] = True
        conditions["platform"]["reason"] = None
        conditions["platform"]["since"] = None

        return MockPlatformAPI.get_store_status(zone_id)


class MockCivicAPI:
    """Mock civic/government shutdown status API."""

    @staticmethod
    def get_shutdown_status(zone_id: int) -> ShutdownStatus:
        """Get civic shutdown/curfew status."""
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
        )

    @staticmethod
    def set_shutdown(zone_id: int, reason: str) -> ShutdownStatus:
        """Activate a civic shutdown/curfew."""
        conditions = _get_zone_conditions(zone_id)
        conditions["shutdown"]["is_active"] = True
        conditions["shutdown"]["reason"] = reason
        conditions["shutdown"]["since"] = datetime.utcnow()

        return MockCivicAPI.get_shutdown_status(zone_id)

    @staticmethod
    def clear_shutdown(zone_id: int) -> ShutdownStatus:
        """Clear a civic shutdown."""
        conditions = _get_zone_conditions(zone_id)
        conditions["shutdown"]["is_active"] = False
        conditions["shutdown"]["reason"] = None
        conditions["shutdown"]["since"] = None

        return MockCivicAPI.get_shutdown_status(zone_id)


def reset_all_conditions():
    """Reset all zone conditions to defaults."""
    global _zone_conditions
    _zone_conditions = {}


def get_all_active_conditions() -> dict[int, dict]:
    """Get all zones with non-default conditions."""
    return _zone_conditions.copy()
