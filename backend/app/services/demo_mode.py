"""
Demo Mode Service

Provides rich demo data for showcasing features:
- Active trigger events (rain, AQI, heat)
- Partial payout claims (sustained events)
- Adverse selection blocking
- Realistic partner activity
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.utils.time_utils import utcnow


class DemoDataGenerator:
    """Generate realistic demo data for showcasing features."""

    @staticmethod
    def get_active_triggers() -> List[Dict[str, Any]]:
        """
        Generate active demo triggers showing different event types.

        Returns triggers for:
        1. Heavy rain (Bangalore) - ongoing for 2 hours
        2. Extreme heat (Delhi) - ongoing for 6 hours
        3. Dangerous AQI (Mumbai) - ongoing for 4 hours
        4. Civic shutdown (Chennai) - just started
        """
        now = utcnow()

        return [
            {
                "id": 9001,
                "zone_id": 1,
                "zone_name": "Koramangala",
                "zone_code": "BLR-047",
                "city": "Bangalore",
                "trigger_type": "rain",
                "severity": 4,
                "started_at": (now - timedelta(hours=2)).isoformat(),
                "ended_at": None,
                "is_sustained": True,
                "metadata": {
                    "rainfall_mm_hr": 68.5,
                    "threshold": 55,
                    "source": "IMD",
                    "confidence": 0.95
                },
                "description": "Heavy rainfall detected - 68.5mm/hr (threshold: 55mm/hr)",
                "partners_affected": 42,
                "claims_auto_generated": 38,
                "payout_mode": "partial (70% daily, no weekly cap)"
            },
            {
                "id": 9002,
                "zone_id": 8,
                "zone_name": "Connaught Place",
                "zone_code": "DEL-009",
                "city": "Delhi",
                "trigger_type": "heat",
                "severity": 3,
                "started_at": (now - timedelta(hours=6)).isoformat(),
                "ended_at": None,
                "is_sustained": False,
                "metadata": {
                    "temperature_celsius": 45.2,
                    "threshold": 43,
                    "source": "IMD",
                    "confidence": 0.92
                },
                "description": "Extreme heat advisory - 45.2°C (threshold: 43°C)",
                "partners_affected": 28,
                "claims_auto_generated": 25,
                "payout_mode": "full weekly payout"
            },
            {
                "id": 9003,
                "zone_id": 5,
                "zone_name": "Andheri East",
                "zone_code": "MUM-021",
                "city": "Mumbai",
                "trigger_type": "aqi",
                "severity": 5,
                "started_at": (now - timedelta(hours=4)).isoformat(),
                "ended_at": None,
                "is_sustained": True,
                "metadata": {
                    "aqi_level": 438,
                    "threshold": 400,
                    "source": "CPCB",
                    "confidence": 0.88
                },
                "description": "Hazardous air quality - AQI 438 (threshold: 400)",
                "partners_affected": 67,
                "claims_auto_generated": 61,
                "payout_mode": "partial (70% daily, no weekly cap)"
            },
            {
                "id": 9004,
                "zone_id": 11,
                "zone_name": "T. Nagar",
                "zone_code": "CHN-011",
                "city": "Chennai",
                "trigger_type": "shutdown",
                "severity": 4,
                "started_at": (now - timedelta(minutes=30)).isoformat(),
                "ended_at": None,
                "is_sustained": False,
                "metadata": {
                    "reason": "Political bandh",
                    "government_order": "GO-2026-04-15",
                    "source": "District Administration"
                },
                "description": "Civic shutdown declared - Political bandh in effect",
                "partners_affected": 89,
                "claims_auto_generated": 83,
                "payout_mode": "full weekly payout"
            }
        ]

    @staticmethod
    def get_partial_payout_claims() -> List[Dict[str, Any]]:
        """
        Generate demo claims showing partial payout (sustained events).

        Shows claims with 70% daily payout, no weekly cap.
        """
        now = utcnow()

        return [
            {
                "id": 5001,
                "claim_id": "CLM-5001",
                "partner_name": "Rajesh Kumar",
                "partner_id": "ZPT456789",
                "zone": "Koramangala",
                "trigger": "Heavy Rain",
                "trigger_type": "rain",
                "amount": 190.0,  # 70% of Rs.272 (standard tier daily payout)
                "status": "paid",
                "fraud_score": 0.08,
                "timestamp": (now - timedelta(hours=1, minutes=45)).isoformat(),
                "payout_type": "partial",
                "payout_percentage": 70,
                "sustained_event": True,
                "day_in_event": 1,
                "upi_ref": "RC-PARTIAL-1234567890"
            },
            {
                "id": 5002,
                "claim_id": "CLM-5002",
                "partner_name": "Priya Sharma",
                "partner_id": "ZPT234567",
                "zone": "Andheri East",
                "trigger": "Dangerous AQI",
                "trigger_type": "aqi",
                "amount": 154.0,  # 70% of Rs.220 (flex tier daily payout)
                "status": "approved",
                "fraud_score": 0.12,
                "timestamp": (now - timedelta(hours=3, minutes=20)).isoformat(),
                "payout_type": "partial",
                "payout_percentage": 70,
                "sustained_event": True,
                "day_in_event": 2,
                "upi_ref": None
            },
            {
                "id": 5003,
                "claim_id": "CLM-5003",
                "partner_name": "Amit Patel",
                "partner_id": "BLK567890",
                "zone": "Koramangala",
                "trigger": "Heavy Rain",
                "trigger_type": "rain",
                "amount": 238.0,  # 70% of Rs.340 (pro tier daily payout)
                "status": "pending",
                "fraud_score": 0.05,
                "timestamp": (now - timedelta(minutes=30)).isoformat(),
                "payout_type": "partial",
                "payout_percentage": 70,
                "sustained_event": True,
                "day_in_event": 1,
                "upi_ref": None
            }
        ]

    @staticmethod
    def get_adverse_selection_scenario() -> Dict[str, Any]:
        """
        Generate scenario demonstrating adverse selection blocking.

        Shows active high-severity event in zone that blocks new enrollments.
        """
        now = utcnow()

        return {
            "blocked": True,
            "reason": "Policy purchase blocked: active weather/disruption alert(s) in your zone (rain, aqi). "
                     "To prevent adverse selection, new enrollments are suspended during active high-severity events. "
                     "Please try again after the event subsides.",
            "active_events": [
                {
                    "type": "rain",
                    "severity": 4,
                    "started": (now - timedelta(hours=2)).isoformat(),
                    "description": "Heavy rainfall - 68.5mm/hr"
                },
                {
                    "type": "aqi",
                    "severity": 5,
                    "started": (now - timedelta(hours=4)).isoformat(),
                    "description": "Hazardous air quality - AQI 438"
                }
            ],
            "estimated_clearance": (now + timedelta(hours=3)).isoformat(),
            "message": "You can purchase a policy once weather conditions improve (estimated: 3 hours)"
        }

    @staticmethod
    def get_demo_partner_activity() -> Dict[str, Any]:
        """Generate realistic partner activity data for demo."""
        return {
            "active_days_last_30": 24,
            "total_deliveries": 187,
            "avg_daily_earnings": 650,
            "total_earnings_protected": 4850,
            "claims_approved": 7,
            "claims_paid": 6,
            "total_payout_received": 1450,
            "uptime_percentage": 86.7,
            "loyalty_weeks": 8,
            "current_tier": "standard",
            "zone_changes": 2
        }

    @staticmethod
    def get_demo_stats() -> Dict[str, Any]:
        """Generate demo statistics for dashboard."""
        return {
            "total_partners": 1247,
            "active_policies": 892,
            "total_claims": 2341,
            "claims_approved": 2103,
            "total_payout": 587450,
            "avg_approval_time_minutes": 3.2,
            "fraud_detection_rate": 0.042,
            "partner_satisfaction": 4.7
        }


# Global demo mode state (in production, this would be in Redis or database)
_demo_mode_enabled = False


def is_demo_mode() -> bool:
    """Check if demo mode is currently enabled."""
    return _demo_mode_enabled


def set_demo_mode(enabled: bool) -> bool:
    """
    Enable or disable demo mode.

    Args:
        enabled: True to enable demo mode, False to disable

    Returns:
        The new demo mode state
    """
    global _demo_mode_enabled
    _demo_mode_enabled = enabled
    return _demo_mode_enabled


def get_demo_mode_status() -> Dict[str, Any]:
    """Get current demo mode status with metadata."""
    return {
        "enabled": _demo_mode_enabled,
        "mode": "demo" if _demo_mode_enabled else "production",
        "features": {
            "active_triggers": True,
            "partial_payouts": True,
            "adverse_selection": True,
            "rich_analytics": True
        } if _demo_mode_enabled else {},
        "warning": "Demo mode active - all data is simulated" if _demo_mode_enabled else None
    }
