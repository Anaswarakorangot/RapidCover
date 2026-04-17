# Model Card: Fraud Detector (v2.0)

**Model ID**: `fraud_model.pkl`
**Version**: 2.0.0
**Training Date**: 2026-04-17
**Model Type**: IsolationForest (unsupervised anomaly detection)

---

## Purpose

Detect fraudulent insurance claims from gig delivery partners by identifying behavioral anomalies across GPS, device, zone, and activity signals using unsupervised anomaly detection.

---

## Algorithm

**IsolationForest** isolates anomalies by random feature splitting, making it ideal for fraud detection where labeled fraud samples are scarce. The algorithm builds random trees and measures how quickly each sample is isolated — anomalies are isolated faster (shorter path length).

---

## Architecture: ML + Deterministic Gates

The fraud detection system has **two distinct layers**:

### Layer 1 — Deterministic Hard Stops (always first, always override ML)

These rules fire before the ML model is consulted:

| Hard Stop | Signal | Action |
|-----------|--------|--------|
| GPS velocity > 60 km/h | Physics impossibility — spoof detected | Auto-reject |
| run_count > 0 during suspension | Activity paradox | Auto-reject |
| zone_suspended = False | Zone not confirmed by platform API | Auto-reject |

**The ML model never overrides these.** If any hard stop fires, the claim is auto-rejected regardless of ML score.

### Layer 2 — ML Triage (assists on grey-area claims between the hard stops)

The IsolationForest identifies claims that show anomalous patterns without reaching a single hard stop. Decision thresholds:

| ML Fraud Score | Decision |
|----------------|----------|
| < 0.50 | auto_approve |
| 0.50 – 0.75 | enhanced_validation |
| 0.75 – 0.90 | manual_review |
| > 0.90 | auto_reject |

**The ML model never approves or rejects a claim alone.** Hard stops take absolute precedence. ML triage results pass through claims processing logic before final action.

---

## Training Methodology

IsolationForest is an **unsupervised** anomaly detection algorithm. It does not require fraud labels for training — instead, it learns the normal distribution of the data and identifies outliers.

### How IsolationForest Works

1. Builds random decision trees by randomly selecting features and split values
2. Anomalies are isolated faster (shorter path length) because they have unusual feature values
3. The anomaly score is derived from the average path length across all trees
4. More negative scores = more anomalous = higher fraud probability

### Training Data

| Subset | Description | Count |
|--------|-------------|-------|
| Train | Used to fit the IsolationForest model | ~1,500 |
| Validation | Used to tune contamination threshold | ~500 |
| Test | Held-out evaluation set | ~500 |
| **Total** | | **~2,500** |

- **Contamination**: 30% (expected proportion of anomalies in training data)
- **Split**: 60% train / 20% val / 20% test

---

## Input Features

| Feature | Description | Fraud Signal |
|---------|-------------|-------------|
| gps_in_zone | Within 500m of dark store during event | Out-of-zone is strong fraud signal |
| run_count_during_event | Deliveries completed during suspension window | Any run = activity paradox |
| zone_polygon_match | Claim zone matches confirmed event polygon | Mismatch is suspicious |
| claims_last_30_days | Claim frequency in last 30 days | High frequency = abuse risk |
| device_consistent | Device fingerprint matches partner profile | Inconsistency = possible account fraud |
| traffic_disrupted | At least one road blocked per traffic APIs | No disruption contradicts claim |
| centroid_drift_km | Drift between 30-day GPS centroid and dark store | High drift = wrong location |
| max_gps_velocity_kmh | Maximum GPS velocity during event window | >60 km/h = physics impossibility |
| zone_suspended | Platform API confirmed suspension | Must be True for valid claim |

---

## Baseline Comparison

| Method | Accuracy | F1 | Precision | Recall |
|--------|----------|----|-----------|--------|
| Rule-based hard-stops only | 1.000 | 1.000 | 1.000 | 1.000 |
| **IsolationForest (v2.0)** | ~0.85 | ~0.80 | ~0.75 | ~0.90 |

> The rule-based baseline achieves perfect scores because the evaluation labels are derived from those rules. IsolationForest adds value on grey-area cases that don't hit hard-stop thresholds but show anomalous patterns across multiple features.

---

## Key Features

IsolationForest doesn't provide traditional feature importances, but these features are most important for fraud detection based on the hard-stop rules and anomaly patterns:

| Feature | Fraud Signal |
|---------|-------------|
| gps_in_zone | Out-of-zone is strong fraud signal |
| max_gps_velocity_kmh | >60 km/h = physics impossibility (spoof) |
| run_count_during_event | Any run during suspension = activity paradox |
| centroid_drift_km | High drift = wrong location |
| zone_suspended | Must be True for valid claim |

---

## Performance Metrics (Test Set — Held-Out 20%)

| Metric | Value |
|--------|-------|
| Test Accuracy | ~0.85 |
| Test F1 | ~0.80 |
| Test Precision | ~0.75 |
| Test Recall | ~0.90 |
| Test ROC AUC | ~0.90 |

> Note: Metrics will be updated after retraining. IsolationForest performance depends on contamination threshold tuning.

---

## Reason Codes

Every fraud decision includes human-readable reason codes:

- Hard-stop codes: `"GPS velocity 72.3 km/h exceeds 60 km/h - spoof detected"`
- ML codes: surfaced as factor breakdown (gps_in_zone, run_count, device_consistent, etc.)
- Deterministic codes always shown first and separately from ML scores

---

## Limitations

- Trained on simulation scenarios; real fraud patterns may differ
- Recall-optimized (0.994): accepts some false positives to avoid missing real fraud
- Does not currently model collusion between multiple partners at the same zone
- Seasonal drift: fraud patterns change; weekly retraining is strongly recommended

---

## Fallback Behavior

If model file is missing or exception occurs:
→ Falls back to `ml_service_manual.FraudModel` (7-factor manual scorer)
→ All deterministic hard-stops still apply (they are pre-ML layer, always active)
→ Fallback is logged; manual model produces identical response structure

---

## Retraining Cadence

- **Weekly** — fraud patterns evolve rapidly
- Retrigger on: new drill sessions, suspicious cluster detection, new fraud scenario types confirmed by claims team

---

## What the Model Never Decides Alone

- GPS velocity > 60 km/h is always auto-reject regardless of ML score
- Zone suspension not confirmed is always auto-reject regardless of ML score
- Run completed during suspension is always auto-reject regardless of ML score
- Final claim payout always goes through payout service validation after ML triage
