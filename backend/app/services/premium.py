from typing import Optional
from sqlalchemy.orm import Session

from app.models.policy import PolicyTier, TIER_CONFIG
from app.models.zone import Zone
from app.schemas.policy import PolicyQuote


def calculate_premium(
    tier: PolicyTier,
    zone: Optional[Zone] = None,
    db: Optional[Session] = None,
) -> PolicyQuote:
    """
    Calculate premium based on tier and zone risk score.

    The Dynamic Premium Engine adjusts base premium by zone risk:
    - Low risk zones (0-30): 10% discount
    - Medium risk zones (31-60): No adjustment
    - High risk zones (61-80): 15% surcharge
    - Very high risk zones (81-100): 30% surcharge
    """
    config = TIER_CONFIG[tier]
    base_premium = config["weekly_premium"]

    # Default risk adjustment (no zone specified)
    risk_adjustment = 0.0

    if zone:
        risk_score = zone.risk_score

        if risk_score <= 30:
            risk_adjustment = -0.10 * base_premium  # 10% discount
        elif risk_score <= 60:
            risk_adjustment = 0.0  # No adjustment
        elif risk_score <= 80:
            risk_adjustment = 0.15 * base_premium  # 15% surcharge
        else:
            risk_adjustment = 0.30 * base_premium  # 30% surcharge

    final_premium = round(base_premium + risk_adjustment, 2)

    return PolicyQuote(
        tier=tier,
        base_premium=base_premium,
        risk_adjustment=round(risk_adjustment, 2),
        final_premium=final_premium,
        max_daily_payout=config["max_daily_payout"],
        max_days_per_week=config["max_days_per_week"],
    )


def get_all_quotes(zone: Optional[Zone] = None) -> list[PolicyQuote]:
    """Get premium quotes for all tiers."""
    return [calculate_premium(tier, zone) for tier in PolicyTier]
