"""
ml_monitoring.py
-----------------------------------------------------------------------------
ML Model Monitoring Service - Production instrumentation for trained models.

Tracks predictions, fallbacks, latencies for zone risk, premium, fraud models.
Singleton pattern for global stats collection.
-----------------------------------------------------------------------------
"""

import time
from datetime import datetime
from threading import Lock
from typing import Dict, Any


class MLMonitor:
    """Singleton monitor for ML model performance tracking."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize monitoring counters."""
        self.stats = {
            "zone_risk": {
                "predictions_total": 0,
                "fallbacks_total": 0,
                "latency_ms_total": 0.0,
                "latency_ms_avg": 0.0,
                "last_prediction_at": None,
            },
            "premium": {
                "predictions_total": 0,
                "fallbacks_total": 0,
                "latency_ms_total": 0.0,
                "latency_ms_avg": 0.0,
                "last_prediction_at": None,
            },
            "fraud": {
                "predictions_total": 0,
                "fallbacks_total": 0,
                "latency_ms_total": 0.0,
                "latency_ms_avg": 0.0,
                "last_prediction_at": None,
            },
            "service_started_at": datetime.utcnow().isoformat(),
        }
        self._lock_stats = Lock()

    def record_prediction(self, model_name: str, latency_ms: float, fallback: bool = False):
        """
        Record prediction metrics.

        Args:
            model_name: "zone_risk" | "premium" | "fraud"
            latency_ms: Prediction latency in milliseconds
            fallback: True if manual fallback was used
        """
        with self._lock_stats:
            if model_name not in self.stats:
                return

            model_stats = self.stats[model_name]
            model_stats["predictions_total"] += 1

            if fallback:
                model_stats["fallbacks_total"] += 1

            # Update latency
            model_stats["latency_ms_total"] += latency_ms
            model_stats["latency_ms_avg"] = (
                model_stats["latency_ms_total"] / model_stats["predictions_total"]
            )

            model_stats["last_prediction_at"] = datetime.utcnow().isoformat()

    def get_stats(self) -> Dict[str, Any]:
        """Return current monitoring statistics."""
        with self._lock_stats:
            # Deep copy to avoid race conditions
            return {
                "zone_risk": dict(self.stats["zone_risk"]),
                "premium": dict(self.stats["premium"]),
                "fraud": dict(self.stats["fraud"]),
                "service_started_at": self.stats["service_started_at"],
                "snapshot_at": datetime.utcnow().isoformat(),
            }

    def reset_stats(self):
        """Reset all counters (for testing/admin use)."""
        with self._lock_stats:
            self._initialize()


# Singleton instance
ml_monitor = MLMonitor()
