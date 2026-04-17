# Model Card: Premium Engine (v2.0)

**Model ID**: `premium_model.pkl`
**Version**: 2.0.0
**Training Date**: 2026-04-17
**Model Type**: XGBoost Regressor (GradientBoostingRegressor fallback)

---

## Purpose

Predict the **expected weekly payout pressure** (Rs.) for a gig delivery partner, given their risk profile, zone, activity, and city.

The ML model learns the underlying economic risk — how much the insurer would expect to pay out per week for this partner profile. It does **not** learn the final premium formula.

---

## What the Model Learns vs What is Deterministic

| Layer | Type | Description |
|-------|------|-------------|
| Expected payout pressure | **Learned by ML** | E\[payout\] = trigger_frequency × severity × exposure × load |
| Tier floor price | **Deterministic** | Flex: Rs.22, Standard: Rs.33, Pro: Rs.45 |
| IRDAI 3× cap | **Deterministic** | Max premium = 3× tier base price |
| Loyalty discount | **Deterministic** | 6% after 4 weeks, 10% after 12 weeks |

**The model never sets the final premium alone.** The ML predicted payout pressure is clamped by deterministic actuarial and regulatory rules.

---

## Training Target

```
expected_weekly_payout_pressure =
    trigger_frequency(city) × income_severity(tier) × exposure(active_days/26)
    × seasonal_load(month) × riqi_load(riqi_score)
    + noise(~18% std)
```

This is **independent of the runtime pricing formula**. The pricing formula is policy logic applied *after* ML output.

**Why this avoids circular training**: The target is derived from first-principles economic variables (published city trigger frequencies, tier income profiles from gig worker surveys), not from the pricing engine's own formula.

---

## Training Data

- **Source**: Simulation-derived from city-parameterized distributions
- **Cities**: bangalore, mumbai, delhi, chennai, hyderabad, kolkata
- **City trigger frequencies**: mumbai=0.118, kolkata=0.112, chennai=0.108, bangalore=0.096, hyderabad=0.089, delhi=0.082 (per 26-day window)
- **Tier income severity**: flex Rs.420±60, standard Rs.560±80, pro Rs.720±100 (per day)
- **Target noise**: ~18% std (realistic payout uncertainty)
- **Total samples**: 1,500
- **Split**: 60% train / 20% val / 20% test

---

## Input Features

| Feature | Type | Description |
|---------|------|-------------|
| city_encoded | categorical | City (LabelEncoded: bangalore/mumbai/delhi/chennai/hyderabad/kolkata) |
| zone_risk_score | float (0–100) | Zone risk score from Zone Risk Model |
| active_days_last_30 | int (10–30) | How many days the partner worked this month |
| avg_hours_per_day | float (3.5–12) | Average daily working hours |
| tier_encoded | categorical | Coverage tier (flex/standard/pro) |
| loyalty_weeks | int (0–52) | Weeks of continuous partnership |
| month | int (1–12) | Calendar month (for seasonal loading) |
| riqi_score | float (25–95) | Road Infrastructure Quality Index |

---

## Baseline Comparison

| Method | Test MAE (Rs.) | Test R² |
|--------|---------------|---------|
| Tier-mean predictor | 17.84 | 0.1567 |
| **XGBoost (v2.0)** | **10.71** | **0.6646** |

The ML model improves MAE by **40%** over the naive baseline.

---

## Performance Metrics (Test Set — Held-Out 20%)

| Metric | Value |
|--------|-------|
| Test MAE | Rs. 10.71 |
| Test R² | 0.6646 |
| Val R² | 0.6971 |
| CV R² (5-fold) | 0.6881 ± 0.0325 |

> **Note**: R² of ~0.66 is honest for a noisy economic simulation. The previous v1.0 had R²=0.959 because it was trained against its own formula — that figure was not meaningful.

---

## Top Feature Contributions (from training importances)

1. `active_days_last_30` — 33.1% importance (most predictive of exposure)
2. `zone_risk_score` — 20.4%
3. `riqi_score` — 15.2%
4. `loyalty_weeks` — 10.8%
5. `month` — 9.3%

---

## Runtime Feature Contributions (Per-Quote)

The API response includes `feature_contributions` — a perturbation-based attribution showing each feature's impact (Rs.) on the predicted payout pressure for that specific partner. This powers the quote explanation UI.

---

## Limitations

- Trained on simulation data, not live claim history
- City trigger frequencies are proxies from published gig platform reports, not actual RapidCover claim data
- Performance on unseen cities (outside the 6 trained cities) will fall back to the manual formula
- Does not model sudden macro-events (protests, elections, pandemic-level disruptions)

---

## Fallback Behavior

If model files are missing, city/tier is unseen, or any exception occurs:
→ Falls back to `ml_service_manual.PremiumModel` (actuarially-calibrated formula)
→ Logged as `fallback=True` in ML monitoring
→ Result is identical in structure; `model_type` field will indicate `"manual_fallback"`

---

## Retraining Cadence

- **Monthly** (captures seasonal trend shifts)
- Retrain when: new cities are added, claim payout data from real events becomes available

---

## What the Model Never Decides Alone

- Final premium is always floored at tier minimum (regulatory requirement)
- Final premium is always capped at 3× tier base (IRDAI microinsurance regulation)
- Fraud outcome is never affected by premium ML
