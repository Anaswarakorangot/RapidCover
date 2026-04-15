"""
Trigger detection service for parametric insurance events.

Monitors external data sources and creates TriggerEvents when thresholds are breached.
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.trigger_event import TriggerEvent, TriggerType, TRIGGER_THRESHOLDS
from app.models.zone import Zone
from app.services.claims_processor import process_trigger_event
from app.utils.time_utils import utcnow
from app.services.external_apis import (
    MockWeatherAPI,
    MockAQIAPI,
    MockPlatformAPI,
    MockCivicAPI,
    WeatherData,
    AQIData,
    PlatformStatus,
    ShutdownStatus,
    get_partial_disruption_data,
)


# Sustained Event Tracking
# Tracks consecutive days of same trigger type in same zone
# Sustained event thresholds
SUSTAINED_EVENT_THRESHOLD_DAYS = 5  # Days before sustained mode activates
SUSTAINED_EVENT_MAX_DAYS = 21  # Maximum days for sustained payout
SUSTAINED_EVENT_PAYOUT_MODIFIER = 0.70  # 70% payout per day in sustained mode


def track_sustained_event(
    zone_id: int,
    trigger_type: TriggerType,
    db: Session,
    event_date: datetime = None
) -> dict:
    """
    Track consecutive trigger events for sustained event detection (Persistent).
    """
    from app.models.trigger_event import SustainedEvent
    
    if event_date is None:
        event_date = utcnow()

    date_str = event_date.strftime("%Y-%m-%d")

    # Fetch existing sustained state
    record = (
        db.query(SustainedEvent)
        .filter(SustainedEvent.zone_id == zone_id, SustainedEvent.trigger_type == trigger_type)
        .first()
    )

    if not record:
        record = SustainedEvent(
            zone_id=zone_id,
            trigger_type=trigger_type,
            consecutive_days=1,
            last_event_at=event_date,
            history_json=json.dumps([date_str]),
            is_sustained=False
        )
        db.add(record)
    else:
        # Check if this is a consecutive day or same day
        history = json.loads(record.history_json)
        
        if date_str not in history:
            last_dt = record.last_event_at.date()
            curr_dt = event_date.date()
            
            if (curr_dt - last_dt).days == 1:
                record.consecutive_days += 1
            elif (curr_dt - last_dt).days > 1:
                # Reset if gap exists
                record.consecutive_days = 1
                history = []
            
            history.append(date_str)
            record.history_json = json.dumps(history[-SUSTAINED_EVENT_MAX_DAYS:])
            record.last_event_at = event_date
            record.is_sustained = record.consecutive_days >= SUSTAINED_EVENT_THRESHOLD_DAYS

    db.commit()

    return {
        "is_sustained": record.is_sustained,
        "consecutive_days": record.consecutive_days,
        "payout_modifier": SUSTAINED_EVENT_PAYOUT_MODIFIER if record.is_sustained else 1.0,
        "max_days_reached": record.consecutive_days >= SUSTAINED_EVENT_MAX_DAYS,
        "bypass_weekly_cap": record.is_sustained,
    }


def inject_sustained_event_history(zone_id: int, trigger_type: TriggerType, db: Session, days: int = 5) -> dict:
    """
    Inject consecutive days history into DB for testing.
    """
    from app.models.trigger_event import SustainedEvent
    
    today = utcnow()
    injected_dates = []
    for i in range(days - 1, 0, -1):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        injected_dates.append(date_str)

    # Upsert record
    record = (
        db.query(SustainedEvent)
        .filter(SustainedEvent.zone_id == zone_id, SustainedEvent.trigger_type == trigger_type)
        .first()
    )
    
    if record:
        record.consecutive_days = days - 1
        record.last_event_at = today - timedelta(days=1)
        record.history_json = json.dumps(injected_dates)
        record.is_sustained = (days - 1) >= SUSTAINED_EVENT_THRESHOLD_DAYS
    else:
        record = SustainedEvent(
            zone_id=zone_id,
            trigger_type=trigger_type,
            consecutive_days=days - 1,
            last_event_at=today - timedelta(days=1),
            history_json=json.dumps(injected_dates),
            is_sustained=(days - 1) >= SUSTAINED_EVENT_THRESHOLD_DAYS
        )
        db.add(record)
    
    db.commit()

    return {
        "zone_id": zone_id,
        "trigger_type": trigger_type.value,
        "injected_days": days - 1,
        "dates": injected_dates,
        "next_run_will_be_day": days,
    }


def clear_sustained_event_history(db: Session, zone_id: int = None, trigger_type: TriggerType = None):
    """
    Clear persistent sustained event history.
    """
    from app.models.trigger_event import SustainedEvent
    
    query = db.query(SustainedEvent)
    if zone_id is not None and trigger_type is not None:
        query = query.filter(SustainedEvent.zone_id == zone_id, SustainedEvent.trigger_type == trigger_type)
    
    query.delete()
    db.commit()

    return {"cleared": True}


def get_sustained_event_info(zone_id: int, trigger_type: TriggerType, db: Session) -> dict:
    """
    Get current sustained event info from DB.
    """
    from app.models.trigger_event import SustainedEvent
    
    record = (
        db.query(SustainedEvent)
        .filter(SustainedEvent.zone_id == zone_id, SustainedEvent.trigger_type == trigger_type)
        .first()
    )

    if not record:
        return {
            "is_sustained": False,
            "consecutive_days": 0,
            "payout_modifier": 1.0,
            "max_days_reached": False,
            "bypass_weekly_cap": False,
        }

    return {
        "is_sustained": record.is_sustained,
        "consecutive_days": record.consecutive_days,
        "payout_modifier": SUSTAINED_EVENT_PAYOUT_MODIFIER if record.is_sustained else 1.0,
        "max_days_reached": record.consecutive_days >= SUSTAINED_EVENT_MAX_DAYS,
        "bypass_weekly_cap": record.is_sustained,
    }


def clear_sustained_event(zone_id: int, trigger_type: TriggerType, db: Session) -> None:
    """
    Delete sustained event tracking for a zone/trigger combination.
    """
    from app.models.trigger_event import SustainedEvent
    db.query(SustainedEvent).filter(
        SustainedEvent.zone_id == zone_id, 
        SustainedEvent.trigger_type == trigger_type
    ).delete()
    db.commit()


def _calculate_severity(value: float, threshold: float) -> int:
    """
    Calculate severity level (1-5) based on how much the value exceeds threshold.

    Severity levels:
    1 = Just above threshold (100-110%)
    2 = Moderately above (110-125%)
    3 = Significantly above (125-150%)
    4 = Severely above (150-200%)
    5 = Extremely above (>200%)
    """
    ratio = value / threshold if threshold > 0 else 1

    if ratio < 1.1:
        return 1
    elif ratio < 1.25:
        return 2
    elif ratio < 1.5:
        return 3
    elif ratio < 2.0:
        return 4
    else:
        return 5


def check_rain_trigger(
    zone_id: int,
    weather_data: Optional[WeatherData] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if heavy rain/flood trigger should fire.

    Threshold: >55mm/hr sustained 30+ mins
    """
    if weather_data is None:
        weather_data = MockWeatherAPI.get_current(zone_id)

    threshold = TRIGGER_THRESHOLDS[TriggerType.RAIN]["threshold"]

    if weather_data.rainfall_mm_hr > threshold:
        severity = _calculate_severity(weather_data.rainfall_mm_hr, threshold)

        source_data = {
            "rainfall_mm_hr": weather_data.rainfall_mm_hr,
            "threshold": threshold,
            "humidity": weather_data.humidity,
            "timestamp": weather_data.timestamp.isoformat(),
        }

        # Include partial disruption data if set
        partial_data = get_partial_disruption_data(zone_id)
        if partial_data:
            source_data.update(partial_data)

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.RAIN,
            started_at=utcnow(),
            severity=severity,
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_heat_trigger(
    zone_id: int,
    weather_data: Optional[WeatherData] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if extreme heat trigger should fire.

    Threshold: >43°C sustained 4+ hours
    """
    if weather_data is None:
        weather_data = MockWeatherAPI.get_current(zone_id)

    threshold = TRIGGER_THRESHOLDS[TriggerType.HEAT]["threshold"]

    if weather_data.temp_celsius > threshold:
        severity = _calculate_severity(weather_data.temp_celsius, threshold)

        source_data = {
            "temp_celsius": weather_data.temp_celsius,
            "threshold": threshold,
            "humidity": weather_data.humidity,
            "timestamp": weather_data.timestamp.isoformat(),
        }

        # Include partial disruption data if set
        partial_data = get_partial_disruption_data(zone_id)
        if partial_data:
            source_data.update(partial_data)

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.HEAT,
            started_at=utcnow(),
            severity=severity,
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_aqi_trigger(
    zone_id: int,
    aqi_data: Optional[AQIData] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if dangerous AQI trigger should fire.

    Threshold: >400 for 3+ hours
    """
    if aqi_data is None:
        aqi_data = MockAQIAPI.get_current(zone_id)

    threshold = TRIGGER_THRESHOLDS[TriggerType.AQI]["threshold"]

    if aqi_data.aqi > threshold:
        severity = _calculate_severity(aqi_data.aqi, threshold)

        source_data = {
            "aqi": aqi_data.aqi,
            "threshold": threshold,
            "pm25": aqi_data.pm25,
            "pm10": aqi_data.pm10,
            "category": aqi_data.category,
            "timestamp": aqi_data.timestamp.isoformat(),
        }

        # Include partial disruption data if set
        partial_data = get_partial_disruption_data(zone_id)
        if partial_data:
            source_data.update(partial_data)

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.AQI,
            started_at=utcnow(),
            severity=severity,
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_shutdown_trigger(
    zone_id: int,
    shutdown_data: Optional[ShutdownStatus] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if civic shutdown/curfew trigger should fire.

    Threshold: 2+ hours civic closure
    """
    if shutdown_data is None:
        shutdown_data = MockCivicAPI.get_shutdown_status(zone_id)

    if shutdown_data.is_active and shutdown_data.started_at:
        # For demo, we trigger immediately when shutdown is detected
        # In production, would check duration

        source_data = {
            "reason": shutdown_data.reason,
            "started_at": shutdown_data.started_at.isoformat() if shutdown_data.started_at else None,
            "expected_end": shutdown_data.expected_end.isoformat() if shutdown_data.expected_end else None,
            "timestamp": shutdown_data.timestamp.isoformat(),
        }

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.SHUTDOWN,
            started_at=shutdown_data.started_at or utcnow(),
            severity=3,  # Default severity for civic shutdowns
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_closure_trigger(
    zone_id: int,
    platform_data: Optional[PlatformStatus] = None,
    db: Optional[Session] = None,
) -> Optional[TriggerEvent]:
    """
    Check if dark store closure trigger should fire.

    Threshold: >90 mins dark store closure
    """
    if platform_data is None:
        platform_data = MockPlatformAPI.get_store_status(zone_id)

    if not platform_data.is_open and platform_data.closed_since:
        # For demo, we trigger immediately when closure is detected
        # In production, would check 90+ min duration

        source_data = {
            "closure_reason": platform_data.closure_reason,
            "closed_since": platform_data.closed_since.isoformat() if platform_data.closed_since else None,
            "timestamp": platform_data.timestamp.isoformat(),
        }

        trigger = TriggerEvent(
            zone_id=zone_id,
            trigger_type=TriggerType.CLOSURE,
            started_at=platform_data.closed_since or utcnow(),
            severity=2,  # Default severity for closures
            source_data=json.dumps(source_data),
        )

        return trigger

    return None


def check_all_triggers(zone_id: int, db: Session) -> list[TriggerEvent]:
    """
    Check all trigger types for a zone.

    Returns list of triggered events (not yet persisted).
    """
    from app.services.external_apis import log_weather_observation, log_aqi_observation

    triggers = []

    # Get all current conditions
    weather = MockWeatherAPI.get_current(zone_id)
    aqi = MockAQIAPI.get_current(zone_id)
    platform = MockPlatformAPI.get_store_status(zone_id)
    shutdown = MockCivicAPI.get_shutdown_status(zone_id)

    # Log weather and AQI observations for historical tracking
    log_weather_observation(db, weather, api_provider="openweathermap" if weather.source == "live" else "mock")
    log_aqi_observation(db, aqi, api_provider="waqi" if aqi.source == "live" else "mock")

    # Check each trigger type
    rain_trigger = check_rain_trigger(zone_id, weather)
    if rain_trigger:
        triggers.append(rain_trigger)

    heat_trigger = check_heat_trigger(zone_id, weather)
    if heat_trigger:
        triggers.append(heat_trigger)

    aqi_trigger = check_aqi_trigger(zone_id, aqi)
    if aqi_trigger:
        triggers.append(aqi_trigger)

    shutdown_trigger = check_shutdown_trigger(zone_id, shutdown)
    if shutdown_trigger:
        triggers.append(shutdown_trigger)

    closure_trigger = check_closure_trigger(zone_id, platform)
    if closure_trigger:
        triggers.append(closure_trigger)

    return triggers


def detect_and_save_triggers(zone_id: int, db: Session) -> list[TriggerEvent]:
    """
    Detect triggers for a zone and save them to database.

    Checks for duplicate triggers to avoid creating multiple events
    for the same ongoing condition.
    """
    triggers = check_all_triggers(zone_id, db)
    saved_triggers = []

    for trigger in triggers:
        # Check if there's already an active (non-ended) trigger of this type
        existing = (
            db.query(TriggerEvent)
            .filter(
                TriggerEvent.zone_id == zone_id,
                TriggerEvent.trigger_type == trigger.trigger_type,
                TriggerEvent.ended_at.is_(None),
            )
            .first()
        )

        if not existing:
            db.add(trigger)
            saved_triggers.append(trigger)

    if saved_triggers:
        db.commit()
        for t in saved_triggers:
            db.refresh(t)

        # AUTO-PROCESS: Generate claims immediately when triggers are detected
        for trigger in saved_triggers:
            try:
                process_trigger_event(trigger, db)
            except Exception as e:
                # Log error but don't fail trigger creation
                print(f"Error auto-processing trigger {trigger.id}: {e}")

    return saved_triggers


def end_trigger(trigger_id: int, db: Session) -> Optional[TriggerEvent]:
    """
    Mark a trigger event as ended.
    """
    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == trigger_id).first()

    if trigger and not trigger.ended_at:
        trigger.ended_at = utcnow()
        db.commit()
        db.refresh(trigger)

    return trigger


def get_active_triggers(zone_id: int, db: Session) -> list[TriggerEvent]:
    """
    Get all active (non-ended) triggers for a zone.
    """
    return (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == zone_id,
            TriggerEvent.ended_at.is_(None),
        )
        .order_by(TriggerEvent.started_at.desc())
        .all()
    )


def get_all_active_triggers(db: Session) -> list[TriggerEvent]:
    """
    Get all active triggers across all zones.
    """
    return (
        db.query(TriggerEvent)
        .filter(TriggerEvent.ended_at.is_(None))
        .order_by(TriggerEvent.started_at.desc())
        .all()
    )
