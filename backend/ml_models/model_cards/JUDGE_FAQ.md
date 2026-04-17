# RapidCover ML — Judge FAQ

**Purpose**: Short, precise answers to every likely judge question about RapidCover's ML.
**Target**: Answer each in under 45 seconds orally. Written version here for reference.

---

## Q1. What is actually learned here? Is this just hardcoded logic?

**No. Three models are genuinely trained:**

1. **Zone Risk Scorer** — XGBoost Regressor trained to predict how disruptive a zone is based on rainfall, AQI, heat, suspension history, and seasonal patterns. It learns non-linear combinations of these features that the manual formula cannot capture.

2. **Premium Engine** — XGBoost Regressor trained to predict *expected weekly payout pressure* (how much the insurer expects to pay out per week for a given partner profile). This is an independent economic signal — not the pricing formula.

3. **Fraud Triage** — RandomForestClassifier trained on policy-grounded fraud scenario labels to identify suspicious claim patterns across GPS, device, zone, and activity features.

**The manual/fallback models still exist** as a safety net — if ML fails, the system keeps running. This is a feature, not a weakness: it means the deterministic rules still protect every payout even if all ML is unavailable.

---

## Q2. What data trained the models?

**City-parameterized simulation data** derived from published real-world statistics:

- **Zone risk**: IMD (India Meteorological Department) city-level baseline rainfall intensity, CPCB AQI distributions, and published dark-store suspension frequency patterns. 1,200 samples across 6 cities.
- **Premium**: City trigger frequencies estimated from published gig platform disruption reports (mumbai: 11.8% per 26-day window, down to delhi: 8.2%). Income severity from gig worker income surveys (flex Rs.420/day, standard Rs.560/day, pro Rs.720/day). 1,500 samples.
- **Fraud**: Three strata — legitimate profiles (60%), explicit fraud scenarios modeled after documented GPS spoofing, activity paradox, and frequency abuse patterns (25%), grey-area ambiguous cases (15%). 2,500 samples.

We acknowledge this is **simulation data**. The training methodology document and model cards are transparent about this. The models are built to be retrained with real claim data as it accumulates.

---

## Q3. How do you avoid circular logic in pricing?

**The premium model does not learn the pricing formula.** It learns the *expected payout pressure*:

```
Target = trigger_frequency(city) × income_severity(tier)
       × exposure(active_days/26) × seasonal_load × RIQI_load
       + noise(18% std)
```

This is computed from **first-principles economic variables** (city-level frequency, tier income profiles), not from the pricing engine's formula.

The pricing formula's constraints — IRDAI 3x cap, tier floor prices, loyalty discount — are applied **after** the ML prediction as deterministic post-processing. The model can never learn them because they are never in the training loop.

**Evidence**: The premium model R² is 0.66, not 0.95+. A model learning its own formula would score > 0.95. Honest learning against an independent noisy target produces honest metrics.

---

## Q4. How do you stop GPS spoofing?

**Three independent layers:**

1. **Physics hard-stop**: GPS velocity > 60 km/h during an event window is physically impossible for a delivery partner on foot or bicycle. This fires *before any ML*, auto-rejects, and cannot be overridden by the fraud ML score.

2. **Centroid drift check**: A partner's 30-day GPS centroid is compared to the dark store location. Drift > 15km triggers a manual review flag — also deterministic, pre-ML.

3. **ML triage**: The RandomForestClassifier sees `max_gps_velocity_kmh` and `gps_in_zone` as its two highest-importance features (32% and 22% respectively). It catches spoofing attempts that stay below the velocity threshold but show other anomalous patterns.

The GPS velocity check **alone** is enough to stop naive spoofing. The ML layer catches more sophisticated pattern combinations.

---

## Q5. Why should anyone trust this payout?

**Every payout goes through five verification layers:**

1. **Trigger evidence**: Zone suspension confirmed by platform API + at least one corroborating external signal (IMD, CPCB, or traffic API). Not ML-generated.
2. **Fraud hard-stops**: GPS physics, activity paradox, zone confirmation — all deterministic, all pre-ML.
3. **ML triage**: Fraud score with reason codes; grey-area cases routed to enhanced validation or manual review.
4. **Claims processor**: Multi-gate validation (policy active, eligibility, reserve check).
5. **Payout ledger**: Every payout recorded with trigger evidence hash, fraud decision, and ML score at time of decision. Fully auditable.

**The Trust Center** surfaces all five layers for every claim — partners and insurers can see the exact evidence chain.

---

## Q6. What happens when data sources disagree?

**Explicit conflict resolution in the trigger engine:**

- If the platform API says zone is suspended but IMD shows no weather event and traffic APIs show no blockage → claim goes to **enhanced_validation** (not auto-approved)
- If two out of three external sources confirm disruption, zone suspension is confirmed
- If GPS data contradicts the claimed zone → GPS fraud check fires regardless of zone status
- Centroid drift flagging is independent of zone confirmation — it fires even if the zone is validly suspended

The system has a **multi-trigger resolver** that handles partial evidence explicitly. Disagreement = caution, not approval.

---

## Q7. What does the model decide alone, and what does it never decide alone?

| Decision | Who decides |
|----------|-------------|
| Zone risk score | ML (XGBoost) — feeds into pricing |
| Expected payout pressure | ML (XGBoost) — feeds into pricing |
| Final premium | ML output + IRDAI cap + tier floor (deterministic) |
| GPS velocity fraud | **Deterministic only** — ML not consulted |
| Run-during-suspension reject | **Deterministic only** — ML not consulted |
| Zone confirmation | **External APIs only** — not ML |
| Claim auto-approve (low fraud) | ML score < 0.50, then claims processor validates |
| Claim auto-reject (high fraud) | ML score > 0.90 OR any hard stop fires |
| Claim manual review | ML score 0.75–0.90 → human adjuster |
| Payout amount | Actuarial formula + ledger — not ML |
| Reserve calculation | Actuarial math — not ML |

**The ML models are advisors, not authorities.** Every high-stakes decision has a deterministic gate that ML cannot override.
