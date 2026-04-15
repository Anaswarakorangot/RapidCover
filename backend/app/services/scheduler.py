"""
Background Scheduler — polls trigger engine every 45 seconds.

Uses APScheduler with SQLAlchemyJobStore for persistent job scheduling.
Jobs survive server restarts — no triggers are missed due to downtime.

Integrated into FastAPI's lifespan via start_scheduler() / stop_scheduler().
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from app.config import get_settings
from app.utils.time_utils import utcnow

logger = logging.getLogger("scheduler")

# ─── State ───────────────────────────────────────────────────────────────────

_scheduler: AsyncIOScheduler = None
_last_poll_time: datetime = None
_last_reconciliation_time: datetime = None
_poll_count: int = 0
_poll_interval_seconds: int = 45


def get_scheduler_status() -> dict:
    """Return scheduler status for the admin UI."""
    running = _scheduler is not None and _scheduler.running if _scheduler else False
    return {
        "running": running,
        "poll_interval_seconds": _poll_interval_seconds,
        "last_poll": _last_poll_time.isoformat() if _last_poll_time else None,
        "last_reconciliation": _last_reconciliation_time.isoformat() if _last_reconciliation_time else None,
        "poll_count": _poll_count,
        "backend": "apscheduler",
    }


# ─── Job functions ──────────────────────────────────────────────────────────

def _run_trigger_check():
    """Execute the trigger engine check (runs in thread pool)."""
    global _last_poll_time, _poll_count

    from app.services.trigger_engine import check_all_triggers
    check_all_triggers()

    _last_poll_time = utcnow()
    _poll_count += 1

    if _poll_count % 10 == 0:
        logger.info(f"[scheduler] Poll #{_poll_count} completed at {_last_poll_time}")


def _should_run_reconciliation(last_run: datetime | None) -> bool:
    """Return True when the reconciliation interval has elapsed."""
    from app.services.reconciliation_job import RECONCILIATION_INTERVAL_SECONDS

    if last_run is None:
        return True

    return (utcnow() - last_run).total_seconds() >= RECONCILIATION_INTERVAL_SECONDS


def _run_reconciliation_check():
    """Execute one payment reconciliation pass (runs in thread pool)."""
    global _last_reconciliation_time

    if not _should_run_reconciliation(_last_reconciliation_time):
        return

    from app.services.reconciliation_job import run_reconciliation_job

    result = run_reconciliation_job()
    _last_reconciliation_time = utcnow()

    activity = (
        result.get("retried", 0)
        + result.get("retry_failed", 0)
        + result.get("escalated_failed", 0)
        + result.get("escalated_stuck", 0)
    )
    if activity:
        logger.info(f"[scheduler] Reconciliation job result: {result}")


def _combined_job():
    """Combined trigger check + reconciliation (runs each poll interval)."""
    try:
        _run_trigger_check()
        _run_reconciliation_check()
    except Exception as e:
        logger.error(f"[scheduler] Error during poll: {e}")


# ─── Start / Stop ────────────────────────────────────────────────────────────

def start_scheduler():
    """Start the background scheduler. Call from FastAPI lifespan startup."""
    global _scheduler

    if _scheduler is not None:
        logger.warning("[scheduler] Already running, skipping start")
        return

    settings = get_settings()

    # Configure job stores — use SQLAlchemy for persistence
    # so jobs survive server restarts
    jobstores = {}
    try:
        jobstores["default"] = SQLAlchemyJobStore(
            url=settings.database_url,
            tablename="apscheduler_jobs",
        )
    except Exception as e:
        logger.warning(f"[scheduler] SQLAlchemyJobStore failed ({e}), using memory store")
        # Fall back to in-memory if DB isn't available
        pass

    executors = {
        "default": ThreadPoolExecutor(max_workers=2),
    }

    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults={
            "coalesce": True,          # Merge missed runs into one
            "max_instances": 1,        # Only one instance of each job at a time
            "misfire_grace_time": 60,   # Allow 60s grace for misfired jobs
        },
    )

    # Add the main polling job (replaces the asyncio.Task loop)
    _scheduler.add_job(
        _combined_job,
        trigger="interval",
        seconds=_poll_interval_seconds,
        id="trigger_poll",
        name="Trigger Engine Poll",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        f"[scheduler] APScheduler started — polling every {_poll_interval_seconds}s "
        f"(jobstore: {'sqlalchemy' if jobstores else 'memory'})"
    )


def stop_scheduler():
    """Stop the background scheduler. Call from FastAPI lifespan shutdown."""
    global _scheduler

    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[scheduler] Stopped")
