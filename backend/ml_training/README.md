# RapidCover ML Training Pipeline (v2.0)

This directory contains the ML training pipeline for RapidCover's three production models.

## What Changed in v2.0

| | v1.0 | v2.0 |
|-|------|------|
| Premium target | Formula-derived `weekly_premium` (circular) | `expected_weekly_payout_pressure` (independent economic signal) |
| Fraud model | IsolationForest (unsupervised) | IsolationForest (unsupervised) |
| Fraud labels | Formula-derived fraud scores (circular) | Policy-grounded deterministic scenarios |
| Training split | 80/20 train/test | 60/20/20 train/val/test |
| Baselines | None | City-mean / tier-mean / rule-based comparisons |
| Feature importances | Not saved | Saved in `model_metadata.json` |

---

## Models

### 1. Zone Risk Scorer — XGBoost Regressor
- **Predicts**: Risk score (0–100) for a dark store zone
- **Target**: Composite event frequency/severity with **independent noise injection** (prevents trivial formula inversion)
- **Test MAE**: 6.43 (baseline city-mean: 7.60) — **15% improvement**
- **Test R²**: 0.5727 (CV: 0.5703 ± 0.0662)
- **Top feature**: road_flood_prone (22.0%)
- **Model card**: [zone_risk_model_card.md](../ml_models/model_cards/zone_risk_model_card.md)

### 2. Premium Engine — XGBoost Regressor
- **Predicts**: Expected weekly payout pressure (Rs.) — **NOT the pricing formula**
- **Target**: `E[payout] = trigger_freq × severity × exposure × seasonal_load × riqi_load + noise`
- **Deterministic post-processing**: IRDAI 3x cap + tier floor applied after ML output
- **Test MAE**: Rs. 10.71 (baseline tier-mean: Rs. 17.84) — **40% improvement**
- **Test R²**: 0.6646 (CV: 0.6881 ± 0.0325)
- **Top feature**: active_days_last_30 (33.1%)
- **Model card**: [premium_model_card.md](../ml_models/model_cards/premium_model_card.md)

### 3. Fraud Detector — IsolationForest (unsupervised)
- **Predicts**: Binary fraud probability (is_fraud: 0/1)
- **Labels**: Policy-grounded deterministic scenarios — **NOT derived from runtime scoring formula**
- **Test F1**: 0.960; AUC: 0.995; Recall: 0.994
- **Baseline (rule-only)**: F1 = 1.000 (rules are the label source — ML adds grey-area coverage)
- **Top feature**: gps_in_zone (32.1%)
- **Model card**: [fraud_model_card.md](../ml_models/model_cards/fraud_model_card.md)

> **On the fraud baseline**: Rule-based scores 1.000 F1 because the training labels are derived from those rules. In real-world operation, ML adds value on cases that partially comply with the hard thresholds — the 0.994 recall is what matters there.

---

## Directory Structure

```
ml_training/
    README.md                    # This file
    generate_training_data.py    # Generate training datasets with independent targets
    train_models.py              # Train all three models with baselines + feature importances
    data/
        zone_risk_training.csv   # 1,200 samples
        premium_training.csv     # 1,500 samples
        fraud_training.csv       # 2,500 samples (30.9% fraud, 3-stratum sampling)

ml_models/
    model_metadata.json          # Training metadata, metrics, baselines, feature importances
    zone_risk_model.pkl          # Trained zone risk model
    zone_risk_city_encoder.pkl   # City label encoder
    premium_model.pkl            # Trained premium model
    premium_city_encoder.pkl     # City label encoder
    premium_tier_encoder.pkl     # Tier label encoder
    fraud_model.pkl              # Trained fraud model (IsolationForest)
    model_cards/
        ARCHITECTURE.md          # Learned vs deterministic boundary reference
        JUDGE_FAQ.md             # Sub-45-second answers to all judge questions
        premium_model_card.md    # Full premium model documentation
        fraud_model_card.md      # Full fraud model documentation
        zone_risk_model_card.md  # Full zone risk model documentation
```

---

## Usage

### 1. Generate Training Data

```bash
cd backend/ml_training
python generate_training_data.py
```

Produces 3 CSV files in `ml_training/data/`:
- `zone_risk_training.csv` — 1,200 samples, independent noise-injected target
- `premium_training.csv` — 1,500 samples, expected payout pressure as target
- `fraud_training.csv` — 2,500 samples, policy-grounded binary labels (3 strata)

### 2. Train Models

```bash
cd backend/ml_training
python train_models.py
```

Outputs:
- Trains all 3 models with 60/20/20 split
- Prints baseline vs ML comparison table
- Saves models + encoders to `../ml_models/`
- Saves `model_metadata.json` with metrics, feature importances, and provenance

### 3. Use Trained Models

The ML service (`app/services/ml_service.py`) auto-loads trained models if `model_metadata.json` exists:

```python
from app.services.ml_service import zone_risk_model, premium_model, fraud_model

# Zone risk
risk_score = zone_risk_model.predict(zone_features)  # returns float 0-100

# Premium (includes feature_contributions for UI)
result = premium_model.predict(partner_features)
# result["weekly_premium"]       -> final premium (with IRDAI cap applied)
# result["ml_raw_payout_pressure"] -> what ML predicted before clamping
# result["feature_contributions"]  -> list of {label, impact_rs, direction} for top drivers

# Fraud
fraud_result = fraud_model.score(claim_features)
# fraud_result["fraud_score"]   -> 0-1
# fraud_result["decision"]      -> auto_approve / enhanced_validation / manual_review / auto_reject
# fraud_result["hard_reject_reasons"] -> deterministic hard-stop reasons (if any)
```

---

## Data Provenance Summary

| Model | Target | Independent? | Circular risk |
|-------|--------|-------------|--------------|
| Zone risk | risk_score (composite + ±7pt noise) | Yes — different caps + noise | None |
| Premium | expected_weekly_payout_pressure | Yes — economic first-principles | None |
| Fraud | is_fraud (5 adjuster scenarios) | Yes — not derived from scorer formula | None |

---

## Architecture Reference

See [`ml_models/model_cards/ARCHITECTURE.md`](../ml_models/model_cards/ARCHITECTURE.md) for the full learned-vs-deterministic boundary specification.

---

## Judge FAQ

See [`ml_models/model_cards/JUDGE_FAQ.md`](../ml_models/model_cards/JUDGE_FAQ.md) for answers to all 7 likely judge questions in under 45 seconds each.

---

## Retraining Schedule

| Model | Cadence | Trigger |
|-------|---------|---------|
| Fraud | Weekly | New drill sessions, suspicious clusters, new fraud evidence |
| Premium | Monthly | Seasonal shifts, new city data |
| Zone risk | Quarterly | New cities, major infrastructure changes |

---

## Fallback Chain

When trained models are unavailable: `TrainedModel → ManualModel (ml_service_manual.*)`

All deterministic hard-stops (GPS velocity, run count, zone suspension) remain active regardless of which model path is used.

---

## Dependencies

```
scikit-learn >= 1.3.0
xgboost >= 2.0.0       (recommended; falls back to GradientBoosting if unavailable)
pandas >= 2.0.0
numpy >= 1.24.0
joblib >= 1.3.0
```
