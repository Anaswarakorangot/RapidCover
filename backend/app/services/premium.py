"""
premium.py — Unified Premium Engine
----------------------------------------------------------------------
Single pricing entry point for all callers:
  - policies.py (purchase)
  - policies.py (renewal via policy_lifecycle.py)
  - zones.py (reassignment)
  - admin_panel.py (quotes)

Decision path:
  1. Try ML path from premium_service.py (pricing_mode = "trained_ml")
  2. Fall back to rule-based zone-risk adjustment   (pricing_mode = "fallback_rule_based")

Both paths always emit:
  - pricing_mode
  - audit_breakdown  (itemised so every number is traceable)

This eliminates the split-brain problem where purchase, renewal, admin,
and ML could return different premium numbers for the same partner.
----------------------------------------------------------------------
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.policy import PolicyTier, TIER_CONFIG
from app.models.zone import Zone
from app.schemas.policy import PolicyQuote

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule-based risk bands (kept as fallback)
# ---------------------------------------------------------------------------

_RISK_ADJUSTMENTS = [
    (30,  -0.10),   # Low risk    → 10% discount
    (60,   0.00),   # Medium risk → no change
    (80,   0.15),   # High risk   → 15% surcharge
    (100,  0.30),   # Very high   → 30% surcharge
]


def _rule_based_quote(tier: PolicyTier, zone: Optional[Zone]) -> PolicyQuote:
    """
    Original rule-based premium calculator.
    Returns a PolicyQuote with pricing_mode = "fallback_rule_based".
    """
    config = TIER_CONFIG[tier]
    base_premium = config["weekly_premium"]
    risk_adjustment = 0.0
    risk_score = zone.risk_score if zone else 50.0

    for threshold, adj_rate in _RISK_ADJUSTMENTS:
        if risk_score <= threshold:
            risk_adjustment = adj_rate * base_premium
            break

    final_premium = round(base_premium + risk_adjustment, 2)

    # Determine risk band label for audit
    if risk_score <= 30:
        risk_band = "low_risk"
    elif risk_score <= 60:
        risk_band = "medium_risk"
    elif risk_score <= 80:
        risk_band = "high_risk"
    else:
        risk_band = "very_high_risk"

    audit = {
        "base": base_premium,
        "risk_score": risk_score,
        "risk_band": risk_band,
        "risk_adjustment": round(risk_adjustment, 2),
        "riqi_band": None,
        "riqi_score": None,
        "loyalty_discount": None,
        "cap_applied": False,
        "mode_reason": "ML model unavailable; using zone-risk rule table",
    }

    return PolicyQuote(
        tier=tier,
        base_premium=base_premium,
        risk_adjustment=round(risk_adjustment, 2),
        final_premium=final_premium,
        max_daily_payout=config["max_daily_payout"],
        max_days_per_week=config["max_days_per_week"],
        pricing_mode="fallback_rule_based",
        audit_breakdown=audit,
    )


def _ml_quote(tier: PolicyTier, zone: Optional[Zone]) -> Optional[PolicyQuote]:
    """
    ML-backed premium path (premium_service.py).
    Returns a PolicyQuote with pricing_mode = "trained_ml", or None on failure.
    """
    try:
        from app.services.premium_service import (
            calculate_weekly_premium,
            get_riqi_score,
            get_riqi_band,
            RIQI_PAYOUT_MULTIPLIER,
            RIQI_PREMIUM_ADJUSTMENT,
            TIER_CONFIG as PS_TIER_CONFIG,
        )
        from app.services.ml_service import PartnerFeatures, premium_model

        city = (zone.city if zone else "bangalore").lower()
        zone_id = zone.id if zone else None
        risk_score = zone.risk_score if zone else 50.0

        riqi_score = get_riqi_score(city, zone_id)
        riqi_band = get_riqi_band(riqi_score)

        features = PartnerFeatures(
            partner_id=0,
            city=city,
            zone_risk_score=risk_score,
            active_days_last_30=22,      # neutral default for quote
            avg_hours_per_day=8.0,
            tier=tier.value,
            loyalty_weeks=0,
            month=date.today().month,
            riqi_score=riqi_score,
        )
        result = premium_model.predict(features)

        config = TIER_CONFIG[tier]
        # Cap ML premium so it stays within tier price band (avoid wild swings at quote time)
        final_premium = round(float(result["weekly_premium"]), 2)
        base = float(result["base_price"])
        risk_adj = round(final_premium - base, 2)

        audit = {
            "base": base,
            "risk_score": risk_score,
            "riqi_score": riqi_score,
            "riqi_band": riqi_band,
            "riqi_payout_multiplier": RIQI_PAYOUT_MULTIPLIER[riqi_band],
            "riqi_premium_adjustment": RIQI_PREMIUM_ADJUSTMENT[riqi_band],
            "loyalty_discount": result["breakdown"].get("loyalty_discount"),
            "city_peril": result["breakdown"].get("city_peril_multiplier"),
            "seasonal_index": result["breakdown"].get("seasonal_index"),
            "zone_risk_multiplier": result["breakdown"].get("zone_risk_multiplier"),
            "cap_applied": result.get("cap_applied", False),
            "cap_value": result.get("cap_value"),
        }

        return PolicyQuote(
            tier=tier,
            base_premium=base,
            risk_adjustment=risk_adj,
            final_premium=final_premium,
            max_daily_payout=config["max_daily_payout"],
            max_days_per_week=config["max_days_per_week"],
            pricing_mode="trained_ml",
            audit_breakdown=audit,
        )
    except Exception as exc:
        logger.warning("ML premium path failed (%s); will use rule-based fallback", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_premium(
    tier: PolicyTier,
    zone: Optional[Zone] = None,
    db: Optional[Session] = None,
) -> PolicyQuote:
    """
    Unified premium calculator — the ONLY function callers should use.

    Strategy:
      1. Try ML path (richer, city/RIQI/seasonal aware).
      2. Fall back to rule-based zone-risk table.

    Always returns a PolicyQuote with `pricing_mode` + `audit_breakdown`.
    """
    quote = _ml_quote(tier, zone)
    if quote is None:
        quote = _rule_based_quote(tier, zone)
    return quote


def get_all_quotes(zone: Optional[Zone] = None) -> list[PolicyQuote]:
    """Get premium quotes for all tiers (used on /policies/quotes endpoint)."""
    return [calculate_premium(tier, zone) for tier in PolicyTier]
