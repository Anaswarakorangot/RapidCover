"""
Social Oracle API — Streaming verification endpoint.

POST /admin/panel/social-oracle/analyze
  - Accepts raw social media text
  - Runs multi-source verification pipeline
  - Streams results as NDJSON lines for live terminal display
"""

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.services.social_oracle import run_full_verification

router = APIRouter(prefix="/admin/panel/social-oracle", tags=["social-oracle"])


class AnalyzeRequest(BaseModel):
    text: str


@router.post("/analyze")
async def analyze_social_post(req: AnalyzeRequest):
    """
    Run the Social Oracle verification pipeline on raw social media text.

    Returns NDJSON (newline-delimited JSON) stream — each line is a
    log entry the frontend renders in the terminal, with a type field
    for color-coding.
    """
    text = req.text.strip()

    # Run the synchronous verification in a thread
    db = SessionLocal()
    try:
        results = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_full_verification(text, db)
        )
    finally:
        db.close()

    location = results["location"]
    event = results["event"]
    weather = results["weather"]
    aqi = results["aqi"]
    traffic = results["traffic"]
    verdict = results["verdict"]

    async def event_stream():
        # ── Phase 1: Initialization ──
        yield _line("agent", "INITIALIZING Social Oracle Verification Pipeline...")
        await asyncio.sleep(0.3)

        yield _line("agent", f"Ingesting raw social payload ({len(text)} chars)...")
        await asyncio.sleep(0.4)

        # ── Phase 2: Text parsing ──
        if event.is_suspicious:
            yield _line("security",
                f"⚠ SUSPICIOUS CONTENT DETECTED: keywords [{', '.join(event.suspicious_keywords)}]")
            await asyncio.sleep(0.5)

        if location.found:
            yield _line("agent",
                f"LOCATION EXTRACTED: \"{location.raw_match}\" → "
                f"{location.zone_name} ({location.zone_code}) "
                f"[{location.lat:.4f}°N, {location.lon:.4f}°E] "
                f"(source: {location.source})")
        else:
            yield _line("error", "LOCATION: Could not identify location from text")
        await asyncio.sleep(0.5)

        if event.found:
            yield _line("agent",
                f"EVENT TYPE: {event.event_type.upper()} "
                f"(matched: {', '.join(event.matched_keywords[:5])})")
        else:
            yield _line("error", "EVENT TYPE: Could not classify event from text")
        await asyncio.sleep(0.4)

        # ── Phase 3: API verification ──
        yield _line("oracle", "Pinging real-world data sources for GPS-based verification...")
        await asyncio.sleep(0.6)

        # Weather
        src_tag = "LIVE" if weather.is_live else "MOCK"
        if weather.data:
            yield _line("oracle",
                f"OpenWeatherMap [{src_tag}] @ ({location.lat:.2f}, {location.lon:.2f}): "
                f"Rainfall {weather.data.get('rainfall_mm_hr', 0)} mm/hr, "
                f"Temp {weather.data.get('temp_celsius', 0)}°C, "
                f"Humidity {weather.data.get('humidity', 0)}%")
        else:
            yield _line("oracle", f"OpenWeatherMap [{src_tag}]: No data available")
        await asyncio.sleep(0.5)

        # AQI
        src_tag = "LIVE" if aqi.is_live else "MOCK"
        if aqi.data:
            yield _line("oracle",
                f"WAQI/CPCB [{src_tag}] @ ({location.lat:.2f}, {location.lon:.2f}): "
                f"AQI {aqi.data.get('aqi', 0)} ({aqi.data.get('category', 'unknown')}), "
                f"PM2.5: {aqi.data.get('pm25', 0)}, PM10: {aqi.data.get('pm10', 0)}")
        else:
            yield _line("oracle", f"WAQI/CPCB [{src_tag}]: No data available")
        await asyncio.sleep(0.5)

        # Traffic
        if traffic.data:
            yield _line("oracle",
                f"Traffic Feed [{('LIVE' if traffic.is_live else 'MOCK')}]: "
                f"Congestion: {traffic.data.get('congestion_level', 'unknown')}, "
                f"Blocked roads: {traffic.data.get('blocked_roads', 0)}, "
                f"Avg delay: {traffic.data.get('avg_delay_mins', 0)} min")
        await asyncio.sleep(0.4)

        # ── Phase 4: Cross-verification ──
        yield _line("security", "Running cross-verification against claimed conditions...")
        await asyncio.sleep(0.5)

        # Weather verdict
        if weather.reason:
            log_type = "decision" if weather.supports_claim else "error"
            yield _line(log_type, f"Weather check: {weather.reason}")
            await asyncio.sleep(0.3)

        # AQI verdict
        if aqi.reason:
            log_type = "decision" if aqi.supports_claim else "error"
            yield _line(log_type, f"AQI check: {aqi.reason}")
            await asyncio.sleep(0.3)

        # Traffic verdict
        if traffic.reason:
            log_type = "decision" if traffic.supports_claim else "error"
            yield _line(log_type, f"Traffic check: {traffic.reason}")
            await asyncio.sleep(0.3)

        # ── Phase 5: Final decision ──
        yield _line("security", "Synthesizing decision matrix...")
        await asyncio.sleep(0.6)

        if verdict.verified:
            yield _line("decision",
                f"CONFIDENCE: {verdict.confidence}%. "
                f"Autonomous Parametric Trigger APPROVED. ✓")
            await asyncio.sleep(0.3)
            yield _line("decision",
                f"Dispatching trigger for zone {verdict.zone_code} "
                f"(type: {verdict.trigger_type})...")
        elif verdict.confidence >= 40:
            yield _line("security",
                f"CONFIDENCE: {verdict.confidence}%. "
                f"INCONCLUSIVE — manual review required.")
        else:
            yield _line("error",
                f"CONFIDENCE: {verdict.confidence}%. "
                f"Autonomous Parametric Trigger REJECTED. ✗")
            await asyncio.sleep(0.2)
            yield _line("error",
                "HALTING: Payload flagged as unverified / potential misinformation.")

        await asyncio.sleep(0.3)

        # Final summary line for the frontend to parse
        yield json.dumps({
            "type": "done",
            "msg": verdict.summary,
            "confidence": verdict.confidence,
            "verified": verdict.verified,
            "zone_code": verdict.zone_code,
            "trigger_type": verdict.trigger_type,
        }) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"X-Content-Type-Options": "nosniff"},
    )


def _line(log_type: str, msg: str) -> str:
    """Format a single NDJSON log line."""
    return json.dumps({"type": log_type, "msg": msg}) + "\n"
