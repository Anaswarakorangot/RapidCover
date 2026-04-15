"""
Generate synthetic training data for ML models.

Creates realistic training datasets based on:
- Historical claim patterns
- Zone risk profiles
- Partner behavior patterns
- Fraud scenarios
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path


def generate_zone_risk_data(n_samples=1000):
    """Generate synthetic zone risk training data."""
    np.random.seed(42)

    cities = ["bangalore", "mumbai", "delhi", "chennai", "hyderabad", "kolkata"]

    data = []
    for _ in range(n_samples):
        city = np.random.choice(cities)
        month = np.random.randint(1, 13)

        # Generate correlated features
        if city in ["mumbai", "kolkata"]:
            base_rainfall = np.random.uniform(40, 80)
            flood_events = np.random.poisson(3)
        else:
            base_rainfall = np.random.uniform(10, 50)
            flood_events = np.random.poisson(1)

        if city in ["delhi", "mumbai"]:
            aqi_avg = np.random.uniform(200, 400)
            aqi_severe_days = np.random.poisson(25)
        else:
            aqi_avg = np.random.uniform(100, 250)
            aqi_severe_days = np.random.poisson(10)

        heat_days = np.random.poisson(15) if city in ["chennai", "hyderabad"] else np.random.poisson(8)
        bandh_events = np.random.poisson(2)
        suspensions = np.random.poisson(1)
        road_flood_prone = np.random.choice([0, 1], p=[0.7, 0.3])

        # Calculate actual risk score (ground truth)
        # Based on manual model but with some noise
        risk_score = (
            0.30 * min(base_rainfall / 80.0, 1.0) +
            0.20 * min(aqi_severe_days / 60.0, 1.0) +
            0.15 * min(suspensions / 8.0, 1.0) +
            0.12 * min(heat_days / 30.0, 1.0) +
            0.10 * min(bandh_events / 10.0, 1.0) +
            0.08 * road_flood_prone +
            0.05 * (1 if month in [6, 7, 8, 9] else 0)
        ) * 100

        # Add some noise
        risk_score += np.random.normal(0, 5)
        risk_score = np.clip(risk_score, 0, 100)

        data.append({
            'zone_id': np.random.randint(1, 100),
            'city': city,
            'avg_rainfall_mm_per_hr': round(base_rainfall, 2),
            'flood_events_2yr': flood_events,
            'aqi_avg_annual': round(aqi_avg, 2),
            'aqi_severe_days_2yr': aqi_severe_days,
            'heat_advisory_days_2yr': heat_days,
            'bandh_events_2yr': bandh_events,
            'dark_store_suspensions_2yr': suspensions,
            'road_flood_prone': road_flood_prone,
            'month': month,
            'risk_score': round(risk_score, 2)
        })

    return pd.DataFrame(data)


def generate_premium_data(n_samples=1000):
    """Generate synthetic premium training data."""
    np.random.seed(42)

    cities = ["bangalore", "mumbai", "delhi", "chennai", "hyderabad", "kolkata"]
    tiers = ["flex", "standard", "pro"]
    base_prices = {"flex": 22, "standard": 33, "pro": 45}

    data = []
    for _ in range(n_samples):
        city = np.random.choice(cities)
        tier = np.random.choice(tiers)
        month = np.random.randint(1, 13)

        zone_risk_score = np.random.uniform(20, 80)
        active_days = np.random.randint(15, 30)
        avg_hours = np.random.uniform(4, 12)
        loyalty_weeks = np.random.randint(0, 20)
        riqi_score = np.random.uniform(30, 90)

        # Calculate premium using the manual formula
        base = base_prices[tier]
        trigger_prob = 0.09
        avg_income_lost = 500.0
        days_exposed = min(active_days / 26.0, 1.0)

        city_peril = {"mumbai": 1.30, "kolkata": 1.25, "chennai": 1.22,
                     "bangalore": 1.18, "hyderabad": 1.15, "delhi": 1.10}.get(city, 1.0)
        zone_multiplier = 0.8 + (zone_risk_score / 100.0) * 0.6
        seasonal = 1.2 if month in [6, 7, 8, 9] else 1.0
        activity_factor = {"flex": 0.80, "standard": 1.00, "pro": 1.35}[tier]
        riqi_adj = 1.0 if riqi_score > 70 else (1.15 if riqi_score >= 40 else 1.30)
        loyalty = 0.90 if loyalty_weeks >= 12 else (0.94 if loyalty_weeks >= 4 else 1.0)

        base_component = trigger_prob * avg_income_lost * days_exposed
        adjusted = base_component * city_peril * zone_multiplier * seasonal * activity_factor * riqi_adj * loyalty

        weekly_premium = base + (adjusted * 0.08)
        weekly_premium = np.clip(weekly_premium, base, base * 3.0)

        # Add noise
        weekly_premium += np.random.normal(0, 2)
        weekly_premium = max(weekly_premium, base)

        data.append({
            'partner_id': np.random.randint(1, 1000),
            'city': city,
            'zone_risk_score': round(zone_risk_score, 2),
            'active_days_last_30': active_days,
            'avg_hours_per_day': round(avg_hours, 2),
            'tier': tier,
            'loyalty_weeks': loyalty_weeks,
            'month': month,
            'riqi_score': round(riqi_score, 2),
            'weekly_premium': round(weekly_premium, 2)
        })

    return pd.DataFrame(data)


def generate_fraud_data(n_samples=2000):
    """Generate synthetic fraud detection training data."""
    np.random.seed(42)

    data = []

    # Generate 70% legitimate claims
    n_legit = int(n_samples * 0.7)
    for _ in range(n_legit):
        gps_in_zone = np.random.choice([0, 1], p=[0.1, 0.9])  # 90% in zone
        run_count = 0  # No runs during event
        zone_polygon_match = np.random.choice([0, 1], p=[0.05, 0.95])  # 95% match
        claims_last_30 = np.random.poisson(1)  # Low frequency
        device_consistent = np.random.choice([0, 1], p=[0.1, 0.9])  # 90% consistent
        traffic_disrupted = np.random.choice([0, 1], p=[0.1, 0.9])  # 90% disrupted
        centroid_drift = np.random.uniform(0, 5)  # Low drift
        velocity = np.random.uniform(0, 40)  # Normal velocity
        zone_suspended = 1  # Confirmed suspension

        # Calculate fraud score
        f1 = 0.0 if gps_in_zone else 1.0
        f2 = 1.0 if run_count > 0 else 0.0
        f3 = 0.0 if zone_polygon_match else 1.0
        f4 = min(claims_last_30 / 3.0, 1.0)
        f5 = 0.0 if device_consistent else 1.0
        f6 = 0.0 if traffic_disrupted else 1.0
        f7 = min(centroid_drift / 15.0, 1.0)

        fraud_score = 0.25*f1 + 0.25*f2 + 0.15*f3 + 0.15*f4 + 0.10*f5 + 0.05*f6 + 0.05*f7
        fraud_score = np.clip(fraud_score, 0, 1)

        is_fraud = 0  # Legitimate claim

        data.append({
            'partner_id': np.random.randint(1, 1000),
            'zone_id': np.random.randint(1, 100),
            'gps_in_zone': gps_in_zone,
            'run_count_during_event': run_count,
            'zone_polygon_match': zone_polygon_match,
            'claims_last_30_days': claims_last_30,
            'device_consistent': device_consistent,
            'traffic_disrupted': traffic_disrupted,
            'centroid_drift_km': round(centroid_drift, 2),
            'max_gps_velocity_kmh': round(velocity, 2),
            'zone_suspended': zone_suspended,
            'fraud_score': round(fraud_score, 4),
            'is_fraud': is_fraud
        })

    # Generate 30% fraudulent claims
    n_fraud = n_samples - n_legit
    for _ in range(n_fraud):
        # Fraudulent patterns
        gps_in_zone = np.random.choice([0, 1], p=[0.6, 0.4])  # 60% NOT in zone
        run_count = np.random.poisson(2)  # Activity paradox
        zone_polygon_match = np.random.choice([0, 1], p=[0.4, 0.6])  # 40% no match
        claims_last_30 = np.random.poisson(4)  # High frequency
        device_consistent = np.random.choice([0, 1], p=[0.5, 0.5])  # Inconsistent
        traffic_disrupted = np.random.choice([0, 1], p=[0.4, 0.6])  # Less disrupted
        centroid_drift = np.random.uniform(5, 25)  # High drift
        velocity = np.random.uniform(20, 80)  # Higher velocity
        zone_suspended = np.random.choice([0, 1], p=[0.3, 0.7])  # Sometimes not suspended

        f1 = 0.0 if gps_in_zone else 1.0
        f2 = 1.0 if run_count > 0 else 0.0
        f3 = 0.0 if zone_polygon_match else 1.0
        f4 = min(claims_last_30 / 3.0, 1.0)
        f5 = 0.0 if device_consistent else 1.0
        f6 = 0.0 if traffic_disrupted else 1.0
        f7 = min(centroid_drift / 15.0, 1.0)

        fraud_score = 0.25*f1 + 0.25*f2 + 0.15*f3 + 0.15*f4 + 0.10*f5 + 0.05*f6 + 0.05*f7
        fraud_score = np.clip(fraud_score, 0, 1)

        is_fraud = 1  # Fraudulent claim

        data.append({
            'partner_id': np.random.randint(1, 1000),
            'zone_id': np.random.randint(1, 100),
            'gps_in_zone': gps_in_zone,
            'run_count_during_event': run_count,
            'zone_polygon_match': zone_polygon_match,
            'claims_last_30_days': claims_last_30,
            'device_consistent': device_consistent,
            'traffic_disrupted': traffic_disrupted,
            'centroid_drift_km': round(centroid_drift, 2),
            'max_gps_velocity_kmh': round(velocity, 2),
            'zone_suspended': zone_suspended,
            'fraud_score': round(fraud_score, 4),
            'is_fraud': is_fraud
        })

    df = pd.DataFrame(data)
    # Shuffle the dataset
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


def main():
    """Generate all training datasets."""
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)

    print("Generating Zone Risk training data...")
    zone_df = generate_zone_risk_data(n_samples=1000)
    zone_df.to_csv(output_dir / "zone_risk_training.csv", index=False)
    print(f"  [OK] Saved {len(zone_df)} samples to zone_risk_training.csv")
    print(f"  Risk score range: {zone_df['risk_score'].min():.2f} - {zone_df['risk_score'].max():.2f}")

    print("\nGenerating Premium training data...")
    premium_df = generate_premium_data(n_samples=1000)
    premium_df.to_csv(output_dir / "premium_training.csv", index=False)
    print(f"  [OK] Saved {len(premium_df)} samples to premium_training.csv")
    print(f"  Premium range: Rs.{premium_df['weekly_premium'].min():.2f} - Rs.{premium_df['weekly_premium'].max():.2f}")

    print("\nGenerating Fraud Detection training data...")
    fraud_df = generate_fraud_data(n_samples=2000)
    fraud_df.to_csv(output_dir / "fraud_training.csv", index=False)
    print(f"  [OK] Saved {len(fraud_df)} samples to fraud_training.csv")
    print(f"  Fraud distribution: {fraud_df['is_fraud'].value_counts().to_dict()}")
    print(f"  Fraud score range: {fraud_df['fraud_score'].min():.4f} - {fraud_df['fraud_score'].max():.4f}")

    print("\n[SUCCESS] All training data generated successfully!")
    print(f"   Output directory: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
