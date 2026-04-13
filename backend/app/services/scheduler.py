"""
Background Scheduler — polls trigger engine every 45 seconds.

Uses asyncio background task (no extra dependency needed).
Integrated into FastAPI's lifespan via start_scheduler() / stop_scheduler().

The scheduler is the heartbeat: it calls check_all_triggers() on a loop,
which fetches data from external_apis.py and evaluates thresholds via
trigger_engine.py. No admin needs to press anything.
"""

import asyncio
import logging
from datetime import datetime

logger = logging.getLogger("scheduler")

# ─── State ───────────────────────────────────────────────────────────────────

_scheduler_task: asyncio.Task = None
_scheduler_running: bool = False
_last_poll_time: datetime = None
_last_reconciliation_time: datetime = None
_poll_count: int = 0
_poll_interval_seconds: int = 45


def get_scheduler_status() -> dict:
    """Return scheduler status for the admin UI."""
    return {
        "running": _scheduler_running,
        "poll_interval_seconds": _poll_interval_seconds,
        "last_poll": _last_poll_time.isoformat() if _last_poll_time else None,
        "last_reconciliation": _last_reconciliation_time.isoformat() if _last_reconciliation_time else None,
        "poll_count": _poll_count,
    }


# ─── Background loop ────────────────────────────────────────────────────────

async def _poll_loop():
    """Run trigger engine check in a loop."""
    global _scheduler_running, _last_poll_time, _last_reconciliation_time, _poll_count

    _scheduler_running = True
    logger.info(f"[scheduler] Started — polling every {_poll_interval_seconds}s")

    while _scheduler_running:
        try:
            # Run the synchronous trigger engine in a thread pool
            # to avoid blocking the async event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _run_trigger_check)

            _last_poll_time = datetime.utcnow()
            _poll_count += 1

            if _should_run_reconciliation(_last_reconciliation_time):
                await loop.run_in_executor(None, _run_reconciliation_check)
                _last_reconciliation_time = datetime.utcnow()

            if _poll_count % 10 == 0:
                logger.info(f"[scheduler] Poll #{_poll_count} completed at {_last_poll_time}")

        except Exception as e:
            logger.error(f"[scheduler] Error during poll: {e}")

        # Wait for next interval
        await asyncio.sleep(_poll_interval_seconds)


def _run_trigger_check():
    """Execute the trigger engine check (runs in thread pool)."""
    from app.services.trigger_engine import check_all_triggers
    check_all_triggers()


def _should_run_reconciliation(last_run: datetime | None) -> bool:
    """Return True when the reconciliation interval has elapsed."""
    from app.services.reconciliation_job import RECONCILIATION_INTERVAL_SECONDS

    if last_run is None:
        return True

    return (datetime.utcnow() - last_run).total_seconds() >= RECONCILIATION_INTERVAL_SECONDS


def _run_reconciliation_check():
    """Execute one payment reconciliation pass (runs in thread pool)."""
    from app.services.reconciliation_job import run_reconciliation_job

    result = run_reconciliation_job()
    activity = (
        result.get("retried", 0)
        + result.get("retry_failed", 0)
        + result.get("escalated_failed", 0)
        + result.get("escalated_stuck", 0)
    )
    if activity:
        logger.info(f"[scheduler] Reconciliation job result: {result}")


# ─── Start / Stop ────────────────────────────────────────────────────────────

def start_scheduler():
    """Start the background scheduler. Call from FastAPI lifespan startup."""
    global _scheduler_task

    if _scheduler_task is not None:
        logger.warning("[scheduler] Already running, skipping start")
        return

    try:
        loop = asyncio.get_event_loop()
        _scheduler_task = loop.create_task(_poll_loop())
        logger.info("[scheduler] Background trigger polling started")
    except RuntimeError:
        # No event loop yet — will be started later
        logger.warning("[scheduler] No event loop available, deferring start")


def stop_scheduler():
    """Stop the background scheduler. Call from FastAPI lifespan shutdown."""
    global _scheduler_task, _scheduler_running

    _scheduler_running = False

    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("[scheduler] Stopped")
