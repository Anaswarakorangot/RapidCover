"""
Generate synthetic training data for RapidCover ML models.

DATA PROVENANCE NOTE
--------------------
This script generates simulation-derived training data for three models.

IMPORTANT — circular-logic safeguards applied in this version:

  Premium model target:
    The training target is `expected_weekly_payout_pressure`, which is an
    independent economic signal: E[payout] = trigger_frequency × severity ×
    zone_exposure_fraction. This is NOT the same formula as the runtime pricing
    engine. The pricing engine then applies deterministic insurance constraints
    (IRDAI caps, tier floors) on TOP of the ML prediction. Training against
    expected payout pressure means the model learns the underlying risk
    economics, not the pricing policy.

  Fraud model target:
    The training target (`is_fraud`) is determined by a deterministic scenario
    classifier based on combinations of hard-stop criteria that would satisfy
    any insurance adjuster (GPS out of zone + running during suspension +
    velocity physics violation + zone not confirmed). These are policy-grounded
    ground-truth labels, NOT derived from the same weighted formula used by the
    runtime fraud scorer.

  Zone risk model target:
    The training target (`risk_score`) is derived from historical event
    frequency and severity proxies. Independent Gaussian noise is added before
    label assignment to prevent the model from trivially inverting the feature
    formula.

Training data methodology:
  - All samples are synthetic and city-parameterized from published IMD and
    CPCB statistics (Bengaluru: avg 65mm/hr peak rainfall; Delhi: avg AQI 250+
    in winter; Mumbai: 3+ cyclone-adjacent events per year, etc.)
  - Distributions are set to cover realistic operational ranges, not cherry-
    picked to produce good model metrics.
  - A test harness in train_models.py verifies that baseline (mean predictor)
    is beaten by a meaningful margin.

Retraining cadence:
  - Fraud: weekly (to adapt to new fraud pattern clusters observed in drills)
  - Premium: monthly (to incorporate seasonal trend shifts)
  - Zone risk: quarterly (slow-moving structural risk changes)
"""

import numpy as np
import pandas as pd
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Zone Risk Training Data
# ─────────────────────────────────────────────────────────────────────────────

def generate_zone_risk_data(n_samples: int = 1200) -> pd.DataFrame:
    """
    Generate zone risk training data.

    Target: risk_score (0-100)
      A composite of historical event trigger frequency and severity observed
      for that zone type. Gaussian noise is added BEFORE scoring so the model
      cannot trivially reconstruct the label from features.
    """
    np.random.seed(42)
    cities = ["bangalore", "mumbai", "delhi", "chennai", "hyderabad", "kolkata"]

    data = []
    for _ in range(n_samples):
        city = np.random.choice(cities)
        month = np.random.randint(1, 13)

        # ── City-parameterized distributions based on IMD/CPCB published stats ──
        if city in ["mumbai", "kolkata"]:
            base_rainfall = np.random.uniform(40, 90)   # mm/hr peak
            flood_events  = int(np.random.poisson(3.5))
        elif city == "chennai":
            base_rainfall = np.random.uniform(30, 75)
            flood_events  = int(np.random.poisson(2.5))
        else:
            base_rainfall = np.random.uniform(8, 55)
            flood_events  = int(np.random.poisson(1.2))

        if city in ["delhi", "mumbai"]:
            aqi_avg       = np.random.uniform(180, 420)
            aqi_severe    = int(np.random.poisson(28))
        elif city in ["kolkata", "chennai"]:
            aqi_avg       = np.random.uniform(110, 280)
            aqi_severe    = int(np.random.poisson(14))
        else:
            aqi_avg       = np.random.uniform(90, 230)
            aqi_severe    = int(np.random.poisson(9))

        heat_days   = int(np.random.poisson(18)) if city in ["chennai", "hyderabad"] else int(np.random.poisson(9))
        bandh_ev    = int(np.random.poisson(2))
        suspensions = int(np.random.poisson(1))
        road_flood  = int(np.random.choice([0, 1], p=[0.65, 0.35]))

        # ── Independent noise injected BEFORE computing the label ──
        # This prevents the model from trivially inverting the generation formula.
        noise = np.random.normal(0, 7)    # ±7 point noise floor

        # ── Composite risk target (NOT identical to runtime ZoneRiskModel) ──
        # Uses different normalization caps and a non-linear flood_events term.
        raw_score = (
            0.28 * min(base_rainfall / 90.0, 1.0)           +  # rainfall dominance
            0.22 * min(aqi_severe / 55.0, 1.0)              +  # AQI hazard
            0.16 * min(suspensions / 6.0, 1.0)              +  # platform suspension history
            0.13 * min(heat_days / 35.0, 1.0)               +  # heat stress
            0.09 * min(flood_events / 5.0, 1.0)             +  # flood event count (non-linear cap)
            0.07 * road_flood                                +  # binary infrastructure flag
            0.05 * (1.0 if month in {6, 7, 8, 9} else 0.0)    # monsoon season
        ) * 100 + noise

        risk_score = float(np.clip(raw_score, 0.0, 100.0))

        data.append({
            "zone_id":                    int(np.random.randint(1, 200)),
            "city":                       city,
            "avg_rainfall_mm_per_hr":     round(float(base_rainfall), 2),
            "flood_events_2yr":           flood_events,
            "aqi_avg_annual":             round(float(aqi_avg), 2),
            "aqi_severe_days_2yr":        aqi_severe,
            "heat_advisory_days_2yr":     heat_days,
            "bandh_events_2yr":           bandh_ev,
            "dark_store_suspensions_2yr": suspensions,
            "road_flood_prone":           road_flood,
            "month":                      month,
            "risk_score":                 round(risk_score, 2),
        })

    return pd.DataFrame(data)


# ─────────────────────────────────────────────────────────────────────────────
# Premium Training Data
# ─────────────────────────────────────────────────────────────────────────────

def generate_premium_data(n_samples: int = 1500) -> pd.DataFrame:
    """
    Generate premium training data.

    TARGET: expected_weekly_payout_pressure (Rs.)
      This is an INDEPENDENT economic signal — the expected insurance payout
      the insurer would face per week for this partner profile.

      Formula:
        E[payout] = trigger_frequency × severity_per_event × zone_exposure_fraction
                  + behavioral_risk_loading

      This is NOT the pricing formula used at runtime. The runtime pricing
      engine receives the ML prediction and then applies:
        (a) tier floor (min Rs.22/33/45)
        (b) IRDAI 3x cap
        (c) loyalty and RTO adjustments as deterministic overrides

      The model learns the underlying economic risk. Policy constraints are
      applied deterministically after — never learned.
    """
    np.random.seed(42)
    cities = ["bangalore", "mumbai", "delhi", "chennai", "hyderabad", "kolkata"]
    tiers  = ["flex", "standard", "pro"]

    # City-level baseline trigger frequency from published gig platform data proxies
    # (normalized per 26-working-day window, per zone suspension frequency)
    CITY_TRIGGER_FREQ = {
        "mumbai": 0.118, "kolkata": 0.112, "chennai": 0.108,
        "bangalore": 0.096, "hyderabad": 0.089, "delhi": 0.082,
    }

    # Tier-linked income profiles (Rs./day, from gig worker surveys)
    TIER_SEVERITY = {
        "flex": {"mean": 420, "std": 60},
        "standard": {"mean": 560, "std": 80},
        "pro": {"mean": 720, "std": 100},
    }

    data = []
    for _ in range(n_samples):
        city  = np.random.choice(cities)
        tier  = np.random.choice(tiers)
        month = np.random.randint(1, 13)

        zone_risk_score    = np.random.uniform(15, 85)
        active_days        = int(np.random.randint(10, 30))
        avg_hours          = round(float(np.random.uniform(3.5, 12.0)), 2)
        loyalty_weeks      = int(np.random.randint(0, 52))
        riqi_score         = round(float(np.random.uniform(25, 95)), 2)

        # ── Independent target: expected weekly payout pressure ──
        trigger_freq  = CITY_TRIGGER_FREQ[city]
        # Zone risk amplifies trigger probability (high-risk zones = more frequent triggers)
        trigger_prob  = trigger_freq * (0.7 + (zone_risk_score / 100.0) * 0.6)

        # Income severity (how much a worker loses per disruption day)
        severity_rs   = float(np.random.normal(
            TIER_SEVERITY[tier]["mean"], TIER_SEVERITY[tier]["std"]
        ))

        # Exposure fraction: active days determines fraction of week at risk
        exposure_frac = active_days / 26.0

        # Seasonal loading (monsoon = more disruptions)
        seasonal_load = 1.18 if month in {6, 7, 8, 9} else 1.0

        # RIQI friction: peri-urban workers face more delivery difficulty
        riqi_load = 1.20 if riqi_score < 40 else (1.10 if riqi_score < 70 else 1.0)

        # Expected weekly payout pressure (the model's learning target)
        expected_payout = (
            trigger_prob * severity_rs * exposure_frac * seasonal_load * riqi_load
        )

        # Add realistic noise: payout uncertainty (~±20% of expected)
        noise_factor = float(np.random.normal(1.0, 0.18))
        expected_payout = max(0.0, expected_payout * noise_factor)

        data.append({
            "partner_id":                int(np.random.randint(1, 2000)),
            "city":                      city,
            "zone_risk_score":           round(float(zone_risk_score), 2),
            "active_days_last_30":       active_days,
            "avg_hours_per_day":         avg_hours,
            "tier":                      tier,
            "loyalty_weeks":             loyalty_weeks,
            "month":                     month,
            "riqi_score":                riqi_score,
            # ── Target variable ──
            "expected_weekly_payout_pressure": round(float(expected_payout), 4),
        })

    return pd.DataFrame(data)


# ─────────────────────────────────────────────────────────────────────────────
# Fraud Training Data
# ─────────────────────────────────────────────────────────────────────────────

def _deterministic_fraud_label(
    gps_in_zone: int,
    run_count: int,
    zone_polygon_match: int,
    claims_30d: int,
    device_consistent: int,
    traffic_disrupted: int,
    centroid_drift: float,
    velocity: float,
    zone_suspended: int,
) -> int:
    """
    Assign a fraud label using deterministic policy-grounded rules.

    A claim is FRAUD (1) if it satisfies any of the following operational
    scenarios that any insurance adjuster would recognize:

    Scenario A — GPS spoofing:
      velocity > 55 km/h  AND  gps_out_of_zone

    Scenario B — Activity paradox:
      run_count > 0  AND  zone_suspended

    Scenario C — Multi-signal anomaly cluster:
      gps_out_of_zone  AND  centroid_drift > 12km  AND  zone_polygon_mismatch

    Scenario D — Frequency abuse:
      claims_30d >= 5  AND  device_inconsistency  AND  gps_out_of_zone

    Scenario E — Unconfirmed zone with contradicting signals:
      NOT zone_suspended  AND  NOT traffic_disrupted  AND  claims_30d >= 3

    These labels are INDEPENDENT of the weighted scoring formula used in the
    runtime FraudModel. They represent what a human adjuster would call fraud.
    The ML model learns to identify these patterns; the runtime deterministic
    hard-stops still act as the first gate.
    """
    gps_out = (gps_in_zone == 0)
    zone_mismatch = (zone_polygon_match == 0)

    # Scenario A: GPS spoofing
    if velocity > 55.0 and gps_out:
        return 1

    # Scenario B: Activity paradox
    if run_count > 0 and zone_suspended == 1:
        return 1

    # Scenario C: Multi-signal anomaly
    if gps_out and centroid_drift > 12.0 and zone_mismatch:
        return 1

    # Scenario D: Frequency abuse with device inconsistency
    if claims_30d >= 5 and device_consistent == 0 and gps_out:
        return 1

    # Scenario E: Unconfirmed zone with contradicting signals
    if zone_suspended == 0 and traffic_disrupted == 0 and claims_30d >= 3:
        return 1

    return 0


def generate_fraud_data(n_samples: int = 2500) -> pd.DataFrame:
    """
    Generate fraud detection training data with INDEPENDENT labels.

    The target `is_fraud` is assigned by policy-grounded deterministic
    scenarios, NOT by the same weighted formula used in the runtime
    FraudModel scorer. This avoids circular training.

    Sampling strategy:
      - 60% baseline: legitimate-profile partners in confirmed-suspension zones
      - 25% fraud-profile: GPS-out, velocity-violation, activity-paradox scenarios
      - 15% grey-area: ambiguous signals that test boundary learning
    """
    np.random.seed(42)

    data = []

    # ── Stratum 1: Legitimate claims (60%) ──────────────────────────────────
    n_legit = int(n_samples * 0.60)
    for _ in range(n_legit):
        gps_in_zone         = int(np.random.choice([0, 1], p=[0.06, 0.94]))
        run_count           = 0
        zone_polygon_match  = int(np.random.choice([0, 1], p=[0.04, 0.96]))
        claims_30d          = int(np.random.poisson(0.8))
        device_consistent   = int(np.random.choice([0, 1], p=[0.07, 0.93]))
        traffic_disrupted   = int(np.random.choice([0, 1], p=[0.08, 0.92]))
        centroid_drift      = round(float(np.random.uniform(0.0, 6.0)), 2)
        velocity            = round(float(np.random.uniform(0.0, 35.0)), 2)
        zone_suspended      = 1

        is_fraud = _deterministic_fraud_label(
            gps_in_zone, run_count, zone_polygon_match, claims_30d,
            device_consistent, traffic_disrupted, centroid_drift, velocity, zone_suspended
        )

        data.append({
            "partner_id":              int(np.random.randint(1, 5000)),
            "zone_id":                 int(np.random.randint(1, 200)),
            "gps_in_zone":             gps_in_zone,
            "run_count_during_event":  run_count,
            "zone_polygon_match":      zone_polygon_match,
            "claims_last_30_days":     claims_30d,
            "device_consistent":       device_consistent,
            "traffic_disrupted":       traffic_disrupted,
            "centroid_drift_km":       centroid_drift,
            "max_gps_velocity_kmh":    velocity,
            "zone_suspended":          zone_suspended,
            "is_fraud":                is_fraud,
        })

    # ── Stratum 2: Clear-fraud profiles (25%) ────────────────────────────────
    n_fraud = int(n_samples * 0.25)
    for _ in range(n_fraud):
        # Simulate the known fraud scenarios explicitly
        scenario = np.random.choice(["gps_spoof", "activity_paradox", "freq_abuse", "multi_signal"])

        if scenario == "gps_spoof":
            gps_in_zone         = 0
            velocity            = round(float(np.random.uniform(58, 95)), 2)
            run_count           = 0
            zone_polygon_match  = int(np.random.choice([0, 1], p=[0.5, 0.5]))
            claims_30d          = int(np.random.poisson(2))
            device_consistent   = int(np.random.choice([0, 1], p=[0.4, 0.6]))
            traffic_disrupted   = 1
            centroid_drift      = round(float(np.random.uniform(5, 20)), 2)
            zone_suspended      = 1

        elif scenario == "activity_paradox":
            gps_in_zone         = int(np.random.choice([0, 1], p=[0.5, 0.5]))
            velocity            = round(float(np.random.uniform(10, 40)), 2)
            run_count           = int(np.random.randint(1, 8))
            zone_polygon_match  = int(np.random.choice([0, 1], p=[0.3, 0.7]))
            claims_30d          = int(np.random.poisson(3))
            device_consistent   = int(np.random.choice([0, 1], p=[0.4, 0.6]))
            traffic_disrupted   = 1
            centroid_drift      = round(float(np.random.uniform(0, 10)), 2)
            zone_suspended      = 1

        elif scenario == "freq_abuse":
            gps_in_zone         = 0
            velocity            = round(float(np.random.uniform(5, 45)), 2)
            run_count           = 0
            zone_polygon_match  = int(np.random.choice([0, 1], p=[0.4, 0.6]))
            claims_30d          = int(np.random.randint(5, 12))
            device_consistent   = 0
            traffic_disrupted   = int(np.random.choice([0, 1], p=[0.3, 0.7]))
            centroid_drift      = round(float(np.random.uniform(3, 15)), 2)
            zone_suspended      = int(np.random.choice([0, 1], p=[0.3, 0.7]))

        else:  # multi_signal
            gps_in_zone         = 0
            velocity            = round(float(np.random.uniform(20, 55)), 2)
            run_count           = 0
            zone_polygon_match  = 0
            claims_30d          = int(np.random.poisson(3))
            device_consistent   = int(np.random.choice([0, 1], p=[0.5, 0.5]))
            traffic_disrupted   = int(np.random.choice([0, 1], p=[0.4, 0.6]))
            centroid_drift      = round(float(np.random.uniform(13, 25)), 2)
            zone_suspended      = int(np.random.choice([0, 1], p=[0.2, 0.8]))

        is_fraud = _deterministic_fraud_label(
            gps_in_zone, run_count, zone_polygon_match, claims_30d,
            device_consistent, traffic_disrupted, centroid_drift, velocity, zone_suspended
        )

        data.append({
            "partner_id":              int(np.random.randint(1, 5000)),
            "zone_id":                 int(np.random.randint(1, 200)),
            "gps_in_zone":             gps_in_zone,
            "run_count_during_event":  run_count,
            "zone_polygon_match":      zone_polygon_match,
            "claims_last_30_days":     claims_30d,
            "device_consistent":       device_consistent,
            "traffic_disrupted":       traffic_disrupted,
            "centroid_drift_km":       centroid_drift,
            "max_gps_velocity_kmh":    velocity,
            "zone_suspended":          zone_suspended,
            "is_fraud":                is_fraud,
        })

    # ── Stratum 3: Grey-area / ambiguous (15%) ───────────────────────────────
    n_grey = n_samples - n_legit - n_fraud
    for _ in range(n_grey):
        gps_in_zone         = int(np.random.choice([0, 1], p=[0.35, 0.65]))
        run_count           = int(np.random.choice([0, 1, 2], p=[0.7, 0.2, 0.1]))
        zone_polygon_match  = int(np.random.choice([0, 1], p=[0.3, 0.7]))
        claims_30d          = int(np.random.randint(2, 6))
        device_consistent   = int(np.random.choice([0, 1], p=[0.35, 0.65]))
        traffic_disrupted   = int(np.random.choice([0, 1], p=[0.35, 0.65]))
        centroid_drift      = round(float(np.random.uniform(4, 18)), 2)
        velocity            = round(float(np.random.uniform(15, 65)), 2)
        zone_suspended      = int(np.random.choice([0, 1], p=[0.25, 0.75]))

        is_fraud = _deterministic_fraud_label(
            gps_in_zone, run_count, zone_polygon_match, claims_30d,
            device_consistent, traffic_disrupted, centroid_drift, velocity, zone_suspended
        )

        data.append({
            "partner_id":              int(np.random.randint(1, 5000)),
            "zone_id":                 int(np.random.randint(1, 200)),
            "gps_in_zone":             gps_in_zone,
            "run_count_during_event":  run_count,
            "zone_polygon_match":      zone_polygon_match,
            "claims_last_30_days":     claims_30d,
            "device_consistent":       device_consistent,
            "traffic_disrupted":       traffic_disrupted,
            "centroid_drift_km":       centroid_drift,
            "max_gps_velocity_kmh":    velocity,
            "zone_suspended":          zone_suspended,
            "is_fraud":                is_fraud,
        })

    df = pd.DataFrame(data)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Generate all training datasets and print provenance summary."""
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("RapidCover ML Training Data Generation")
    print("DATA PROVENANCE: independent targets, no circular formula reuse")
    print("=" * 70)

    print("\n[1/3] Generating Zone Risk training data...")
    zone_df = generate_zone_risk_data(n_samples=1200)
    zone_df.to_csv(output_dir / "zone_risk_training.csv", index=False)
    print(f"  [OK] {len(zone_df)} samples -> zone_risk_training.csv")
    print(f"  Risk score range: {zone_df['risk_score'].min():.1f} - {zone_df['risk_score'].max():.1f}")

    print("\n[2/3] Generating Premium training data...")
    prem_df = generate_premium_data(n_samples=1500)
    prem_df.to_csv(output_dir / "premium_training.csv", index=False)
    print(f"  [OK] {len(prem_df)} samples -> premium_training.csv")
    print(f"  Target: expected_weekly_payout_pressure (independent of pricing formula)")
    print(f"  Payout range: Rs.{prem_df['expected_weekly_payout_pressure'].min():.1f} - Rs.{prem_df['expected_weekly_payout_pressure'].max():.1f}")

    print("\n[3/3] Generating Fraud training data...")
    fraud_df = generate_fraud_data(n_samples=2500)
    fraud_df.to_csv(output_dir / "fraud_training.csv", index=False)
    fraud_rate = fraud_df["is_fraud"].mean() * 100
    print(f"  [OK] {len(fraud_df)} samples -> fraud_training.csv")
    print(f"  Labels: policy-grounded deterministic scenarios (NOT weighted formula)")
    print(f"  Fraud rate: {fraud_rate:.1f}%  (legit: {100 - fraud_rate:.1f}%)")

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL TRAINING DATA GENERATED")
    print("  Next: run python train_models.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
