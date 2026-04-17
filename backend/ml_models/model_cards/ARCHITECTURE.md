# RapidCover ML Architecture: Learned vs Deterministic Boundaries

**Version**: 2.0.0
**Last Updated**: 2026-04-17

---

## Overview

RapidCover is a **hyper-local insurance decision engine** for dark-store gig delivery partners. It uses a two-layer architecture: ML intelligence where it adds value, deterministic insurance rules where they are non-negotiable.

This document is the authoritative reference for what the ML models learn, what the deterministic rules enforce, and what the system can never decide alone.

---

## The Two-Layer Architecture

```
Partner/Claim Input
        |
        v
+-----------------------------+
|  LAYER 1: DETERMINISTIC     |  <-- Always runs first. Always overrides ML.
|  HARD GATES                 |
|                             |
|  - GPS velocity > 60 km/h   | -> auto_reject (GPS spoof)
|  - run_count > 0            | -> auto_reject (activity paradox)
|  - zone_suspended = False   | -> auto_reject (unconfirmed zone)
|  - IRDAI 3x premium cap     | -> clamp regardless of ML output
|  - Tier floor price         | -> enforce regardless of ML output
+-----------------------------+
        |
        | (passes Layer 1 check)
        v
+-----------------------------+
|  LAYER 2: ML INTELLIGENCE   |  <-- Informs, never final authority alone.
|                             |
|  Zone Risk Model            | -> risk score 0-100 (input to pricing + UI)
|  Premium Engine             | -> expected payout pressure (Rs.)
|  Fraud Triage Model         | -> fraud score 0-1 + reason codes
+-----------------------------+
        |
        v
+-----------------------------+
|  LAYER 3: DETERMINISTIC     |  <-- Post-ML constraints always enforced.
|  POST-ML CONSTRAINTS        |
|                             |
|  - Apply tier premium floor |
|  - Apply IRDAI 3x cap       |
|  - Claims processor gates   |
|  - Payout service ledger    |
|  - Reserve checks           |
+-----------------------------+
        |
        v
 Final Decision / Output
```

---

## What Each ML Model Learns

### Zone Risk Scorer
- **Learns**: How historical rainfall, AQI, heat, bandh events, and platform suspension frequency combine to produce a zone's disruption risk score
- **Input features**: Environmental and operational zone history (10 features)
- **Output**: Risk score 0–100 (continuous regression)
- **Used for**: Premium loading multiplier; zone selection UI; insurer zone risk dashboard
- **Does NOT decide**: Whether a zone suspension is active (separate trigger engine), whether a claim is valid

### Premium Engine
- **Learns**: Expected weekly payout pressure (Rs.) as a function of partner risk profile
- **Target**: E\[payout\] = trigger_frequency × income severity × exposure × seasonal/RIQI loads
- **Does NOT learn**: The pricing formula itself, IRDAI caps, loyalty discounts (these are deterministic)
- **Output**: Raw expected payout pressure (before deterministic clamping)
- **Used for**: Pricing input; feature contributions for quote explanation UI
- **Does NOT decide**: Final premium (deterministic constraints always applied after)

### Fraud Triage Model
- **Learns**: Patterns of behavioral anomalies across GPS, device, zone, and activity signals that characterize fraudulent claim profiles
- **Training labels**: Independent policy-grounded fraud scenarios (GPS spoofing, activity paradox, frequency abuse, multi-signal anomaly)
- **Does NOT learn**: The weights from the runtime manual fraud scorer (labels are independent)
- **Output**: Fraud score 0–1 + decision + reason codes
- **Used for**: Claims triage; enhanced validation routing; fraud reason codes in UI
- **Does NOT decide**: Final claim approval (always passes through hard-stop layer + claims processor)

---

## What Is Always Deterministic (ML Can Never Change These)

| Rule | Layer | Reason |
|------|-------|--------|
| GPS velocity > 60 km/h = reject | Pre-ML hard stop | Physics impossibility — no fraud model exempts this |
| run_count > 0 during suspension = reject | Pre-ML hard stop | Activity paradox — insurance principle |
| Zone not confirmed by platform API = reject | Pre-ML hard stop | No zone, no valid claim basis |
| Tier floor prices (Rs.22/33/45) | Post-ML clamp | IRDAI regulatory minimum |
| IRDAI 3x premium cap | Post-ML clamp | Microinsurance regulation |
| Loyalty discount | Post-ML clamp | Contractual partner benefit |
| Payout ledger entry | Post-ML process | Every payout is ledger-recorded regardless of ML |
| Reserve calculation | Post-ML process | Actuarial reserve math is not ML |

---

## What the ML Models Never Decide Alone

1. **No claim is approved or rejected by ML alone.** Deterministic hard-stops run first; claims processing gates run after.
2. **No premium is set by ML alone.** The ML predicts risk pressure; tier floor and IRDAI cap always apply.
3. **No zone suspension is declared by ML.** The trigger detection engine uses external APIs (IMD, CPCB, platform) independently.
4. **No payout is issued without a ledger entry.** The payout service enforces this independently of ML.

---

## Fallback Chain (When ML is Unavailable)

```
Trained XGBoost/IsolationForest model (normal path)
    |
    | model file missing / exception / unknown city
    v
Manual calibrated model (ml_service_manual.*)
    |
    | (identical interface, slightly different outputs)
    v
All deterministic hard-stops still apply
All IRDAI constraints still apply
Fallback logged in ml_monitoring
```

The system has **zero ML-only failure modes**. If all ML fails, the deterministic layer still protects every payout.

---

## Model Versioning

| Model | File | Version | Algorithm |
|-------|------|---------|-----------|
| Zone Risk | zone_risk_model.pkl | 2.0.0 | XGBoost Regressor |
| Premium | premium_model.pkl | 2.0.0 | XGBoost Regressor |
| Fraud | fraud_model.pkl | 2.0.0 | IsolationForest |

Training metadata, metrics, and feature importances are in `model_metadata.json`.

---

## Governance References

- [Premium Model Card](./premium_model_card.md)
- [Fraud Model Card](./fraud_model_card.md)
- [Zone Risk Model Card](./zone_risk_model_card.md)
- [Judge FAQ](./JUDGE_FAQ.md)
