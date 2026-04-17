"""
admin_monitoring.py
-----------------------------------------------------------------------------
Admin Monitoring API - ML model performance metrics endpoint.

Provides real-time stats on model predictions, fallbacks, and latencies.
Part of MLOps monitoring for production readiness.
-----------------------------------------------------------------------------
"""

from fastapi import APIRouter
from app.services.ml_monitoring import ml_monitor


router = APIRouter(prefix="/admin/ml-stats", tags=["admin-monitoring"])


@router.get("", summary="Get ML model performance statistics")
def get_ml_stats():
    """
    GET /admin/ml-stats

    Returns real-time ML model performance metrics:
    - predictions_total: Total predictions made by each model
    - fallbacks_total: Times manual fallback was used
    - latency_ms_avg: Average prediction latency
    - last_prediction_at: Timestamp of most recent prediction

    Useful for monitoring model health, detecting fallback spikes,
    and tracking inference performance in production.
    """
    return ml_monitor.get_stats()


@router.post("/reset", summary="Reset ML statistics (admin only)")
def reset_ml_stats():
    """
    POST /admin/ml-stats/reset

    Resets all monitoring counters to zero.
    Use for testing or after deploying new models.
    """
    ml_monitor.reset_stats()
    return {"message": "ML statistics reset successfully"}
