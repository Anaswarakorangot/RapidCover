# Model Card: Zone Risk Scorer (v2.0)

**Model ID**: `zone_risk_model.pkl`
**Version**: 2.0.0
**Training Date**: 2026-04-17
**Model Type**: XGBoost Regressor (GradientBoostingRegressor fallback)

---

## Purpose

Predict a **zone risk score (0–100)** for a dark store delivery zone, reflecting the expected frequency and severity of disruptive events (floods, AQI hazards, heat advisories, bandh strikes, dark store suspensions).

This score is an upstream input to the Premium Engine and is also surfaced directly in the worker's zone selection UI.

---

## What the Score Represents

A zone risk score of 75 means: this zone has historically experienced high-frequency or high-severity disruptions across rainfall, air quality, heat, and suspension history. Partners working here face greater income disruption risk. The premium engine uses this as a multiplier on expected payout pressure.

---

## Training Target

```
risk_score =
    0.28 × rainfall_factor     (normalized to 90mm/hr cap)
  + 0.22 × aqi_factor          (normalized to 55 severe days cap)
  + 0.16 × suspension_factor   (normalized to 6 suspensions cap)
  + 0.13 × heat_factor         (normalized to 35 days cap)
  + 0.09 × flood_events_factor  (normalized to 5 events cap)
  + 0.07 × road_flood_prone    (binary geography flag)
  + 0.05 × seasonal_flag       (monsoon months: Jun-Sep)
  + noise(0, 7)                 ← independent noise injected BEFORE scoring
```

**How it differs from the runtime ZoneRiskModel**: The normalization caps are different (e.g., 90mm/hr vs 80mm/hr, 6 suspensions vs 8), and the flood events term uses a different non-linear cap. The independent ±7-point noise injection means the model cannot trivially reconstruct labels from features.

---

## Training Data

- **Source**: City-parameterized simulation from published IMD and CPCB statistics
- **City distributions**:
  - mumbai/kolkata: high rainfall (40–90mm/hr), higher flood events (Poisson λ=3.5)
  - chennai: moderate-high rainfall (30–75mm/hr), Poisson λ=2.5
  - delhi/mumbai: high AQI (180–420), severe days (λ=28)
  - bangalore/hyderabad: lower rainfall, moderate AQI
- **Total samples**: 1,200
- **Split**: 60% train / 20% val / 20% test

---

## Input Features

| Feature | Type | Description |
|---------|------|-------------|
| city_encoded | categorical | LabelEncoded city |
| avg_rainfall_mm_per_hr | float | Average peak rainfall intensity |
| flood_events_2yr | int | Flood/cyclone-adjacent events in past 2 years |
| aqi_avg_annual | float | Annual average AQI |
| aqi_severe_days_2yr | int | Days with AQI > 300 in past 2 years |
| heat_advisory_days_2yr | int | Days with heat advisory in past 2 years |
| bandh_events_2yr | int | Bandh/closure events in past 2 years |
| dark_store_suspensions_2yr | int | Platform suspension occurrences in past 2 years |
| road_flood_prone | binary | Whether zone has flood-prone road infrastructure |
| month | int (1–12) | Month (captures seasonal variability) |

---

## Baseline Comparison

| Method | Test MAE | Test R² |
|--------|---------|---------|
| City-mean predictor | 7.60 | 0.3697 |
| **XGBoost (v2.0)** | **6.43** | **0.5727** |

The ML model reduces MAE by **15%** over a naive city-mean baseline.

---

## Performance Metrics (Test Set — Held-Out 20%)

| Metric | Value |
|--------|-------|
| Test MAE | 6.43 points |
| Test R² | 0.5727 |
| Val R² | 0.5955 |
| CV R² (5-fold) | 0.5703 ± 0.0662 |

> R² of ~0.57 is expected and honest for a noisy simulation with ±7 point injected noise. The model learns the signal but cannot overfit the noise — which is the intended behavior.

---

## Feature Importances (Top 5)

| Feature | Importance |
|---------|-----------|
| road_flood_prone | 22.0% |
| avg_rainfall_mm_per_hr | 18.7% |
| aqi_severe_days_2yr | 14.3% |
| dark_store_suspensions_2yr | 12.9% |
| heat_advisory_days_2yr | 10.1% |

---

## Zone Risk Interpretation

| Score Range | Risk Grade | Meaning |
|-------------|-----------|---------|
| 0–25 | Low | Historically stable zone. Few disruptions. |
| 25–50 | Moderate | Some seasonal disruptions. Standard premiums. |
| 50–75 | Elevated | Frequent disruptions. Zone multiplier applies. |
| 75–100 | High | High disruption history. Significant premium loading. |

---

## Confidence / Reliability

- Scores for known high-risk cities (mumbai, kolkata) are more reliable — more training samples in those distributions
- Scores for edge-case inputs (very high AQI + very high rainfall simultaneously) may be less stable due to sparse training coverage in those combinations
- All scores pass through a 0–100 clip

---

## Limitations

- Based on simulation data, not actual historical claim trigger logs
- City-level distributions are parameterized from published IMD/CPCB stats, not real-time feeds
- Hyper-local micro-zone variation (e.g., a specific street known to flood) is not captured — only zone-level aggregates
- Seasonal signal is binary (monsoon vs non-monsoon); city-specific month risk not fully resolved in this target

---

## Fallback Behavior

If model is unavailable:
→ Falls back to `ml_service_manual.ZoneRiskModel` (7-weight linear formula)
→ Logged with `fallback=True` in ML monitoring

---

## Retraining Cadence

- **Quarterly** — zone-level risk patterns change slowly
- Retrigger on: new city added, significant infrastructure change, or post-monsoon recalibration

---

## What the Model Never Decides Alone

- Zone risk score is an input to the premium calculation, not a standalone payout trigger
- Zone suspension (the event trigger used for claims) is determined separately by the trigger detection engine — not by the ML risk score
- A high risk score does not independently authorize or block a claim
