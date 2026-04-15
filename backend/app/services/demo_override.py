"""
Demo Override Service

Demo mode = Testing/Override mode for demonstrations.
- Uses REAL database and REAL users
- BYPASSES restrictions to show features work
- Allows manual triggering of events
- Overrides safety checks for demonstration purposes

When demo mode is ON:
- Adverse selection blocking is BYPASSED
- Policy purchase allowed during active events
- 7-day activity requirement BYPASSED
- Manual trigger firing enabled
- Partial payout overrides available
"""

# Global demo override state
_demo_override_enabled = False


def is_demo_override() -> bool:
    """Check if demo override mode is enabled."""
    return _demo_override_enabled


def set_demo_override(enabled: bool) -> bool:
    """
    Enable or disable demo override mode.

    Args:
        enabled: True to enable overrides, False for normal production mode

    Returns:
        The new override state
    """
    global _demo_override_enabled
    _demo_override_enabled = enabled
    return _demo_override_enabled


def should_bypass_adverse_selection() -> bool:
    """
    Check if adverse selection blocking should be bypassed.

    Returns True in demo mode to allow policy purchase during active events.
    """
    return _demo_override_enabled


def should_bypass_activity_gate() -> bool:
    """
    Check if 7-day activity requirement should be bypassed.

    Returns True in demo mode to allow immediate policy purchase.
    """
    return _demo_override_enabled


def should_bypass_fraud_rejection() -> bool:
    """
    Check if fraud auto-rejection should be bypassed.

    Returns True in demo mode to allow high-fraud-score claims.
    """
    return _demo_override_enabled


def get_override_status() -> dict:
    """Get current demo override status."""
    return {
        "enabled": _demo_override_enabled,
        "mode": "demo_override" if _demo_override_enabled else "production",
        "bypasses_active": {
            "adverse_selection": _demo_override_enabled,
            "activity_gate": _demo_override_enabled,
            "fraud_rejection": _demo_override_enabled,
        } if _demo_override_enabled else {},
        "description": "Demo mode bypasses restrictions for feature demonstration" if _demo_override_enabled else "Production mode with all safety checks active"
    }
