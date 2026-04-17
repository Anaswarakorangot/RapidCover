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


@router.get("/metadata", summary="Get ML model metadata and version info")
def get_ml_metadata():
    """
    GET /admin/ml-stats/metadata

    Returns ML model metadata including:
    - Model versions and training dates
    - Training/test metrics (MSE, MAE, R², ROC-AUC)
    - Feature lists for each model
    - Model types (XGBRegressor, IsolationForest, etc.)

    Useful for MLOps tracking and model versioning.
    """
    from app.services.ml_service_trained import get_model_metadata

    metadata = get_model_metadata()

    if not metadata:
        return {
            "error": "Model metadata not available",
            "message": "Model metadata file not found or failed to load"
        }

    return metadata
