"""
premium_service.py
-----------------------------------------------------------------------------
RapidCover Premium Engine - pricing, underwriting gates, RIQI scoring,
payout calculation, zone pool share cap, sustained event protocol.

Source: RapidCover Phase 2 Team Guide, Guidewire DEVTrails 2026.

# Fixed pricing tiers based on specification image:
# Flex (Part-time)    = Rs.22/week | Max payout Rs.250/day | 2 days/week | Max Rs.500/week | Ratio ~1:23
# Standard (Full-time) = Rs.33/week | Max payout Rs.400/day | 3 days/week | Max Rs.1200/week | Ratio ~1:36
# Pro (Peak rider)    = Rs.45/week | Max payout Rs.500/day | 4 days/week | Max Rs.2000/week | Ratio ~1:44

Algorithm: Gradient Boosted Regression (manually calibrated weights).
-----------------------------------------------------------------------------
"""

from datetime import date
from typing import Optional

from app.services.ml_service import (
    premium_model,
    PartnerFeatures,
)


# ------------------------------------------------------------------------------
# TIER CONFIGURATION
# ------------------------------------------------------------------------------

TIER_CONFIG: dict = {
    "flex": {
        "weekly_premium":  22,
        "max_payout_day":  250,  # Max Weekly = 250 * 2 = 500. Ratio = 500/22 = 22.7
        "max_days_week":   2,
        "label":           "[FLEX] ⚡ Flex (Part-time)",
        "best_for":        "Part-time, 4–5 hrs/day",
    },
    "standard": {
        "weekly_premium":  33,
        "max_payout_day":  400,  # Max Weekly = 400 * 3 = 1200. Ratio = 1200/33 = 36.3
        "max_days_week":   3,
        "label":           "[STANDARD] 🛵 Standard (Full-time)",
        "best_for":        "Full-time, 8–10 hrs/day",
    },
    "pro": {
        "weekly_premium":  45,
        "max_payout_day":  500,  # Max Weekly = 500 * 4 = 2000. Ratio = 2000/45 = 44.4
        "max_days_week":   4,
        "label":           "[PRO] 🏆 Pro (Peak rider)",
        "best_for":        "Peak warriors, 12+ hrs/day",
    },
}

# Underwriting gate thresholds - Section 2A of team guide
MIN_ACTIVE_DAYS_TO_BUY   = 7   # Minimum 7 active days before cover starts
AUTO_DOWNGRADE_DAYS      = 5   # auto-downgrade to Flex if < 5 active days in last 30

# Demo exception: Delhi zones skip the 7-day check (for judging demo)
DEMO_EXEMPT_CITIES = ["Delhi"]  # Partners in these cities bypass MIN_ACTIVE_DAYS check

# Sustained event protocol - Section 2E
SUSTAINED_EVENT_THRESHOLD_DAYS   = 5     # trigger fires 5+ consecutive days → Sustained Event
SUSTAINED_EVENT_PAYOUT_FACTOR    = 0.70  # 70% of daily tier payout in sustained mode
SUSTAINED_EVENT_MAX_DAYS         = 21    # max coverage in sustained event mode
REINSURANCE_REVIEW_DAY           = 7     # flag reinsurance at day 7
CITY_PAYOUT_CAP_PCT              = 1.20  # city-level payout capped at 120% of weekly pool


# ------------------------------------------------------------------------------
# RIQI ZONE SCORING
# ------------------------------------------------------------------------------

# RIQI = Road Infrastructure Quality Index (0–100)
# 0 = worst roads, 100 = best roads
# Higher RIQI = better infrastructure = less disruption per mm of rain
# Derived from: OpenStreetMap + NDMA flood maps + suspension history
# NOTE: These are hardcoded city-level defaults for demo.
# In production: compute per dark-store zone polygon.

CITY_RIQI_SCORES: dict = {
    "bangalore": 62.0,   # Bellandur flood-prone, mixed infrastructure
    "mumbai":    45.0,   # Urban fringe zones heavily flood-prone
    "delhi":     58.0,   # Mixed - Anand Vihar vs Dwarka very different
    "chennai":   55.0,   # Coastal + NE monsoon exposure
    "hyderabad": 68.0,   # Relatively better road infrastructure
    "kolkata":   42.0,   # Low-lying, cyclone exposure, older roads
}

# Payout multipliers per RIQI band (Section 3.2 / Section 2B)
RIQI_PAYOUT_MULTIPLIER: dict = {
    "urban_core":   1.00,   # RIQI > 70 - better roads, less disruption
    "urban_fringe": 1.25,   # RIQI 40–70
    "peri_urban":   1.50,   # RIQI < 40 - poor roads, max disruption
}

# Premium adjustment for low-RIQI (higher risk = higher premium)
RIQI_PREMIUM_ADJUSTMENT: dict = {
    "urban_core":   1.00,
    "urban_fringe": 1.15,
    "peri_urban":   1.30,
}


def get_riqi_score(city: str, zone_id: Optional[int] = None) -> float:
    """Return RIQI score for city. In production: per zone polygon."""
    return CITY_RIQI_SCORES.get(city.lower(), 55.0)


def get_riqi_band(riqi_score: float) -> str:
    """Return RIQI band label."""
    if riqi_score > 70:
        return "urban_core"
    elif riqi_score >= 40:
        return "urban_fringe"
    return "peri_urban"


def get_riqi_payout_multiplier(city: str, zone_id: Optional[int] = None) -> float:
    """Return payout multiplier (1.0 / 1.25 / 1.5) for zone."""
    riqi = get_riqi_score(city, zone_id)
    band = get_riqi_band(riqi)
    return RIQI_PAYOUT_MULTIPLIER[band]


# ------------------------------------------------------------------------------
# UNDERWRITING GATE
# ------------------------------------------------------------------------------

def check_underwriting_gate(active_days_last_30: int) -> dict:
    """
    Block policy purchase if < 7 active delivery days in last 30.
    Section 2A of team guide.
    """
    if active_days_last_30 < MIN_ACTIVE_DAYS_TO_BUY:
        return {
            "allowed": False,
            "reason":  (
                f"Cover starts after you complete {MIN_ACTIVE_DAYS_TO_BUY} active "
                f"delivery days. You have {active_days_last_30} active days in the last 30."
            ),
        }
    return {"allowed": True, "reason": None}


def apply_auto_downgrade(tier: str, active_days_last_30: int) -> tuple:
    """
    Auto-downgrade to Flex if < 5 active days in last 30.
    Workers cannot self-select Standard or Pro if activity does not match.
    Section 2A of team guide.

    Returns (effective_tier, was_downgraded)
    """
    if active_days_last_30 < AUTO_DOWNGRADE_DAYS and tier != "flex":
        return "flex", True
    return tier, False


# ------------------------------------------------------------------------------
# WEEKLY PREMIUM CALCULATOR
# ------------------------------------------------------------------------------

def calculate_weekly_premium(
    partner_id:          int,
    city:                str,
    zone_id:             Optional[int],
    requested_tier:      str,
    active_days_last_30: int,
    avg_hours_per_day:   float,
    loyalty_weeks:       int,
) -> dict:
    """
    Full premium calculation pipeline. Called every Monday 6AM for renewal.

    Steps:
      1. Underwriting gate
      2. Auto-downgrade check
      3. RIQI score lookup
      4. premium_model.predict() with all features
      5. Return premium + full itemised breakdown

    Every number is traceable to a formula - per team guide Section 3.
    """
    # Step 1: Underwriting gate
    gate = check_underwriting_gate(active_days_last_30)
    if not gate["allowed"]:
        return {"allowed": False, "gate_reason": gate["reason"], "weekly_premium": None}

    # Step 2: Auto-downgrade
    effective_tier, was_downgraded = apply_auto_downgrade(requested_tier, active_days_last_30)

    # Step 3: RIQI
    riqi_score = get_riqi_score(city, zone_id)
    riqi_band  = get_riqi_band(riqi_score)

    # Step 4: ML model predict
    features = PartnerFeatures(
        partner_id          = partner_id,
        city                = city,
        zone_risk_score     = riqi_score,
        active_days_last_30 = active_days_last_30,
        avg_hours_per_day   = avg_hours_per_day,
        tier                = effective_tier,
        loyalty_weeks       = loyalty_weeks,
        month               = date.today().month,
        riqi_score          = riqi_score,
    )
    result = premium_model.predict(features)
    tier_cfg = TIER_CONFIG[effective_tier]

    return {
        "allowed":          True,
        "gate_reason":      None,
        "weekly_premium":   result["weekly_premium"],
        "base_price":       result["base_price"],
        "tier":             effective_tier,
        "tier_label":       tier_cfg["label"],
        "max_payout_day":   tier_cfg["max_payout_day"],
        "max_days_week":    tier_cfg["max_days_week"],
        "was_downgraded":   was_downgraded,
        "downgrade_reason": (
            f"Auto-downgraded to Flex: only {active_days_last_30} active days "
            f"in last 30 (minimum {AUTO_DOWNGRADE_DAYS} for {requested_tier})"
        ) if was_downgraded else None,
        "riqi": {
            "score":              riqi_score,
            "band":               riqi_band,
            "payout_multiplier":  RIQI_PAYOUT_MULTIPLIER[riqi_band],
            "premium_adjustment": RIQI_PREMIUM_ADJUSTMENT[riqi_band],
        },
        "breakdown":  result["breakdown"],
        "cap_applied": result["cap_applied"],
        "cap_value":   result["cap_value"],
    }


# ------------------------------------------------------------------------------
# PAYOUT CALCULATOR
# ------------------------------------------------------------------------------

def calculate_payout(
    tier:                str,
    disruption_hours:    float,
    avg_hourly_earning:  float,
    city:                str,
    zone_id:             Optional[int] = None,
    consecutive_days:    int = 1,
) -> dict:
    """
    Payout formula from Section 3.2 of team guide:

      Payout = disruption_hours × hourly_earning_baseline × zone_disruption_multiplier
      Capped at: daily_tier_max × eligible_disruption_days

    Sustained Event Mode (5+ consecutive days, Section 2E):
      Payout_per_day = 0.70 × daily_tier_max, no weekly cap, max 21 days
    """
    tier_cfg         = TIER_CONFIG.get(tier.lower(), TIER_CONFIG["standard"])
    riqi_multiplier  = get_riqi_payout_multiplier(city, zone_id)
    sustained_event  = consecutive_days >= SUSTAINED_EVENT_THRESHOLD_DAYS

    if sustained_event:
        # Sustained event mode: 70% of daily max, no weekly cap, up to 21 days
        daily_payout    = tier_cfg["max_payout_day"] * SUSTAINED_EVENT_PAYOUT_FACTOR
        eligible_days   = min(consecutive_days, SUSTAINED_EVENT_MAX_DAYS)
        raw_payout      = daily_payout * min(disruption_hours / 8, 1.0) * riqi_multiplier
        capped_payout   = min(raw_payout, daily_payout)
        reinsurance_flag = consecutive_days >= REINSURANCE_REVIEW_DAY
    else:
        raw_payout       = disruption_hours * avg_hourly_earning * riqi_multiplier
        capped_payout    = min(raw_payout, tier_cfg["max_payout_day"])
        eligible_days    = 1
        reinsurance_flag = False

    return {
        "payout":             round(capped_payout, 2),
        "raw_payout":         round(raw_payout, 2),
        "cap_applied":        raw_payout > tier_cfg["max_payout_day"],
        "max_payout_day":     tier_cfg["max_payout_day"],
        "riqi_multiplier":    riqi_multiplier,
        "disruption_hours":   disruption_hours,
        "hourly_rate":        avg_hourly_earning,
        "sustained_event":    sustained_event,
        "consecutive_days":   consecutive_days,
        "reinsurance_flag":   reinsurance_flag,
    }


# ------------------------------------------------------------------------------
# ZONE POOL SHARE CAP (Mass Event)
# ------------------------------------------------------------------------------

def calculate_zone_pool_share(
    calculated_payout:       float,
    city_weekly_reserve:     float,
    zone_density_weight:     float,
    total_partners_in_event: int,
) -> dict:
    """
    Zone Pool Share formula from Section 3.5 / Section 2D of team guide:

      payout_per_partner = min(calculated_payout, zone_pool_share)
      zone_pool_share = city_weekly_reserve × zone_density_weight / partners_in_event
      City hard cap: total event payout ≤ 120% of city weekly premium pool

    zone_density_weight by density band:
      Low  (<50 partners):    0.15
      Medium (50–150):        0.35
      High (>150):            0.50
    """
    # Demo / early lifecycle can yield a 0 reserve (no "recently created" premiums yet).
    # In that case, treat the pool cap as unavailable instead of forcing payouts to 0.
    if city_weekly_reserve <= 0:
        final_payout = calculated_payout
        zone_pool_share = 0.0
        pool_cap_applied = False
    else:
        zone_pool_share = (city_weekly_reserve * zone_density_weight) / max(total_partners_in_event, 1)
        final_payout = min(calculated_payout, zone_pool_share)
        pool_cap_applied = calculated_payout > zone_pool_share

    return {
        "final_payout":       round(final_payout, 2),
        "calculated_payout":  calculated_payout,
        "zone_pool_share":    round(zone_pool_share, 2),
        "pool_cap_applied":   pool_cap_applied,
        "reduction_amount":   round(calculated_payout - final_payout, 2) if pool_cap_applied else 0,
    }


# ------------------------------------------------------------------------------
# PLAN QUOTES (onboarding)
# ------------------------------------------------------------------------------

def get_plan_quotes(
    city:                str,
    zone_id:             Optional[int],
    active_days_last_30: int,
    avg_hours_per_day:   float,
    loyalty_weeks:       int = 0,
) -> list:
    """
    Returns personalised quotes for all 3 tiers.
    Called at onboarding after GPS zone detection - Section 4.1 step 5.
    """
    quotes = []
    for tier in ["flex", "standard", "pro"]:
        quote = calculate_weekly_premium(
            partner_id          = 0,
            city                = city,
            zone_id             = zone_id,
            requested_tier      = tier,
            active_days_last_30 = active_days_last_30,
            avg_hours_per_day   = avg_hours_per_day,
            loyalty_weeks       = loyalty_weeks,
        )
        quote["tier_config"] = TIER_CONFIG[tier]
        quotes.append(quote)
    return quotes


# ------------------------------------------------------------------------------
# BCR / LOSS RATIO
# ------------------------------------------------------------------------------

def calculate_bcr(total_claims_paid: float, total_premiums_collected: float) -> dict:
    """
    BCR (Burning Cost Rate) = total_claims_paid / total_premiums_collected
    Section 3.4 of team guide.

    Target BCR: 0.55–0.70 (65p per Rs.1 goes to payouts)
    Loss Ratio = BCR × 100
    > 85% → suspend new enrolments in that city
    > 100% → reinsurance treaty activation
    """
    if total_premiums_collected <= 0:
        return {"bcr": 0, "loss_ratio": 0, "status": "no_data"}

    bcr         = total_claims_paid / total_premiums_collected
    loss_ratio  = round(bcr * 100, 2)

    if loss_ratio > 100:
        status = "reinsurance_activation"
    elif loss_ratio > 85:
        status = "suspend_enrolments"
    elif loss_ratio > 70:
        status = "warning"
    elif loss_ratio >= 55:
        status = "healthy"
    else:
        status = "below_target"

    return {
        "bcr":                    round(bcr, 4),
        "loss_ratio":             loss_ratio,
        "status":                 status,
        "suspend_enrolments":     loss_ratio > 85,
        "reinsurance_trigger":    loss_ratio > 100,
        "target_range":           "55–70%",
    }