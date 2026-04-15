"""
Stress scenario service for monsoon reserve-needed calculations.

Models different disaster scenarios and calculates the reserve needed
to cover projected claims above the available city reserve.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.partner import Partner
from app.utils.time_utils import utcnow
from app.models.policy import Policy
from app.models.zone import Zone
from app.models.claim import Claim, ClaimStatus
from app.schemas.stress_scenarios import (
    StressScenarioResponse,
    StressScenarioListResponse,
    StressCityMetrics,
)


# Scenario definitions with trigger probabilities and severity multipliers
STRESS_SCENARIOS = {
    "monsoon_14day_bangalore": {
        "name": "14-Day Monsoon Stress (Bangalore)",
        "days": 14,
        "city": "bangalore",
        "trigger_probability": 0.75,  # 75% of policies will have claims
        "severity_multiplier": 1.3,   # Higher severity due to sustained rain
        "assumptions": [
            "Heavy rain (>55mm/hr) sustained for 14 consecutive days",
            "All Bangalore zones affected uniformly",
            "75% of active policies will generate claims",
            "Average claim amount increased by 30% due to sustained event",
        ],
    },
    "aqi_crisis_7day_delhi": {
        "name": "7-Day AQI Crisis (Delhi NCR)",
        "days": 7,
        "city": "delhi",
        "trigger_probability": 0.85,  # 85% of policies will have claims
        "severity_multiplier": 1.2,
        "assumptions": [
            "AQI sustained above 400 for 7 consecutive days",
            "All Delhi zones affected uniformly",
            "85% of active policies will generate claims",
            "Includes Connaught Place, Saket, and Dwarka zones",
        ],
    },
    "citywide_bandh_3day_mumbai": {
        "name": "3-Day City-wide Bandh (Mumbai)",
        "days": 3,
        "city": "mumbai",
        "trigger_probability": 0.95,  # Near total disruption
        "severity_multiplier": 1.5,   # Civic shutdowns are most impactful
        "assumptions": [
            "Complete civic shutdown for 3 consecutive days",
            "All Mumbai zones affected (Andheri, Bandra, Powai)",
            "95% of active policies will generate claims",
            "Maximum payout per day applied",
        ],
    },
    "combined_monsoon_heat_bengaluru": {
        "name": "Monsoon + Heat Wave Combo (Bangalore)",
        "days": 7,
        "city": "bangalore",
        "trigger_probability": 0.80,
        "severity_multiplier": 1.4,
        "assumptions": [
            "Heavy rain in morning, extreme heat (>43°C) in afternoon",
            "Double trigger events per day possible",
            "80% of active policies will generate claims",
            "Compounded severity due to multiple trigger types",
        ],
    },
}

# Average payout per claim per tier (based on TIER_CONFIG defaults)
AVG_PAYOUT_BY_TIER = {
    "flex": 200,      # Average ~Rs.200 per claim (max Rs.250/day)
    "standard": 320,  # Average ~Rs.320 per claim (max Rs.400/day)
    "pro": 400,       # Average ~Rs.400 per claim (max Rs.500/day)
}


def get_city_metrics(city: str, db: Session, days: int = 7) -> StressCityMetrics:
    """
    Get city-level metrics for stress calculations.

    Args:
        city: City name (case-insensitive match)
        db: Database session
        days: Days to look back for premium calculations

    Returns:
        StressCityMetrics with active policies, premiums, and zones
    """
    now = utcnow()
    period_start = now - timedelta(days=days)

    # Get all zones in the city
    city_zones = db.query(Zone).filter(Zone.city.ilike(f"%{city}%")).all()
    zone_ids = [z.id for z in city_zones]

    if not zone_ids:
        return StressCityMetrics(
            city=city,
            active_policies=0,
            avg_weekly_premium=0.0,
            total_weekly_reserve=0.0,
            zone_count=0,
        )

    # Get partners in these zones
    partner_ids_query = db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids))
    partner_ids = [p[0] for p in partner_ids_query.all()]

    if not partner_ids:
        return StressCityMetrics(
            city=city,
            active_policies=0,
            avg_weekly_premium=0.0,
            total_weekly_reserve=0.0,
            zone_count=len(zone_ids),
        )

    # Count active policies
    active_policies = (
        db.query(func.count(Policy.id))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.is_active == True,
            Policy.starts_at <= now,
            Policy.expires_at > now,
        )
        .scalar()
    ) or 0

    # Calculate total weekly premiums collected recently
    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0.0

    avg_premium = total_premiums / active_policies if active_policies > 0 else 0.0

    return StressCityMetrics(
        city=city,
        active_policies=active_policies,
        avg_weekly_premium=round(avg_premium, 2),
        total_weekly_reserve=round(float(total_premiums), 2),
        zone_count=len(zone_ids),
    )


def calculate_stress_scenario(
    scenario_id: str,
    db: Session,
) -> StressScenarioResponse:
    """
    Calculate reserve needed for a specific stress scenario.

    Formula:
        projected_claims = active_policies × trigger_probability × days
        projected_payout = projected_claims × avg_payout × severity_multiplier
        reserve_needed = max(projected_payout - city_reserve_available, 0)

    Args:
        scenario_id: The scenario identifier
        db: Database session

    Returns:
        StressScenarioResponse with full breakdown
    """
    scenario = STRESS_SCENARIOS.get(scenario_id)
    if not scenario:
        return StressScenarioResponse(
            scenario_id=scenario_id,
            scenario_name="Unknown Scenario",
            days=0,
            projected_claims=0,
            projected_payout=0.0,
            city_reserve_available=0.0,
            reserve_needed=0.0,
            formula_breakdown={},
            assumptions=["Scenario not found"],
            data_source="mock",
        )

    city = scenario["city"]
    days = scenario["days"]
    trigger_probability = scenario["trigger_probability"]
    severity_multiplier = scenario["severity_multiplier"]

    # Get city metrics
    metrics = get_city_metrics(city, db, days=7)

    # Calculate projected claims
    # Each policy can have 1 claim per day during the stress period
    projected_claims = int(metrics.active_policies * trigger_probability * days)

    # Calculate average payout (weighted by typical tier distribution)
    # Assume 40% flex, 40% standard, 20% pro
    weighted_avg_payout = (
        AVG_PAYOUT_BY_TIER["flex"] * 0.40 +
        AVG_PAYOUT_BY_TIER["standard"] * 0.40 +
        AVG_PAYOUT_BY_TIER["pro"] * 0.20
    )

    # Apply severity multiplier
    avg_payout_with_severity = weighted_avg_payout * severity_multiplier

    # Calculate projected payout
    projected_payout = projected_claims * avg_payout_with_severity

    # City reserve available = premiums collected in last 7 days
    city_reserve_available = metrics.total_weekly_reserve

    # Reserve needed = gap between projected payout and available reserve
    reserve_needed = max(projected_payout - city_reserve_available, 0)

    # Determine data source
    data_source = "live" if metrics.active_policies > 0 else "mock"

    formula_breakdown = {
        "step_1_active_policies": metrics.active_policies,
        "step_2_trigger_probability": trigger_probability,
        "step_3_days": days,
        "step_4_projected_claims": f"{metrics.active_policies} × {trigger_probability} × {days} = {projected_claims}",
        "step_5_weighted_avg_payout": round(weighted_avg_payout, 2),
        "step_6_severity_multiplier": severity_multiplier,
        "step_7_avg_payout_with_severity": round(avg_payout_with_severity, 2),
        "step_8_projected_payout": f"{projected_claims} × {round(avg_payout_with_severity, 2)} = {round(projected_payout, 2)}",
        "step_9_city_reserve_available": round(city_reserve_available, 2),
        "step_10_reserve_needed": f"max({round(projected_payout, 2)} - {round(city_reserve_available, 2)}, 0) = {round(reserve_needed, 2)}",
        "city_metrics": {
            "city": city,
            "zone_count": metrics.zone_count,
            "avg_weekly_premium": metrics.avg_weekly_premium,
        },
    }

    return StressScenarioResponse(
        scenario_id=scenario_id,
        scenario_name=scenario["name"],
        days=days,
        projected_claims=projected_claims,
        projected_payout=round(projected_payout, 2),
        city_reserve_available=round(city_reserve_available, 2),
        reserve_needed=round(reserve_needed, 2),
        formula_breakdown=formula_breakdown,
        assumptions=scenario["assumptions"],
        data_source=data_source,
    )


def get_all_stress_scenarios(db: Session) -> StressScenarioListResponse:
    """
    Calculate all stress scenarios and return aggregated results.

    Returns:
        StressScenarioListResponse with all scenarios and total reserve needed
    """
    scenarios = []
    total_reserve_needed = 0.0

    for scenario_id in STRESS_SCENARIOS:
        scenario = calculate_stress_scenario(scenario_id, db)
        scenarios.append(scenario)
        total_reserve_needed += scenario.reserve_needed

    return StressScenarioListResponse(
        scenarios=scenarios,
        computed_at=utcnow(),
        total_reserve_needed=round(total_reserve_needed, 2),
    )


def get_scenario_ids() -> list[str]:
    """Return list of available scenario IDs."""
    return list(STRESS_SCENARIOS.keys())
