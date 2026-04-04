<div align="center">

# 🛵 RapidCover — Phase 2 Additions
### *Production-Grade Features Built on Top of Core Platform*

**Guidewire DEVTrails 2026 — Phase 2 Submission**

[![Phase 2](https://img.shields.io/badge/Phase-2%20Complete-00B894?style=for-the-badge)](.)
[![Features](https://img.shields.io/badge/New%20Features-25%2B-8B2FC9?style=for-the-badge)](.)
[![Tests](https://img.shields.io/badge/Test%20Coverage-12%20Suites-FF6B35?style=for-the-badge)](.)

---

> **"Phase 1 was a good prototype. Phase 2 makes it a serious production-grade system."**

</div>

## 📌 Phase 2 Table of Contents

1. [What Changed — Summary](#-what-changed--summary)
2. [Multi-Trigger Arbitration Engine](#1--multi-trigger-arbitration-engine)
3. [7-Factor Fraud Scoring Model](#2--7-factor-fraud-scoring-model-upgraded-from-6-factor)
4. [RIQI — Road Infrastructure Quality Index](#3--riqi--road-infrastructure-quality-index)
5. [Underwriting Gate & Auto-Downgrade](#4--underwriting-gate--auto-downgrade)
6. [Sustained Event Protocol (Consecutive Disruption)](#5--sustained-event-protocol-consecutive-disruption)
7. [Zone Pool Share Cap (Mass Event Protection)](#6--zone-pool-share-cap-mass-event-protection)
8. [BCR / Loss Ratio Monitoring](#7--bcr--loss-ratio-monitoring)
9. [City-Specific Seasonal Risk Calendar](#8--city-specific-seasonal-risk-calendar)
10. [Zone Density Risk Bands](#9--zone-density-risk-bands)
11. [Sudden Zone Reassignment Handling](#10--sudden-zone-reassignment-handling)
12. [Stress Test Scenarios (6 Actuarial Scenarios)](#11--stress-test-scenarios-6-actuarial-scenarios)
13. [Social Oracle Verification Engine](#12--social-oracle-verification-engine)
14. [Oracle Reliability & Fallback System](#13--oracle-reliability--fallback-system)
15. [Platform Activity Simulation Layer](#14--platform-activity-simulation-layer)
16. [Real-World Validation Matrix (10-Check Pre-Payout)](#15--real-world-validation-matrix-10-check-pre-payout)
17. [Payment Reconciliation & Payout State Machine](#16--payment-reconciliation--payout-state-machine)
18. [Active Shift Window Check](#17--active-shift-window-check)
19. [Multilingual Notification Templates](#18--multilingual-notification-templates)
20. [Pin-Code / Ward-Level Trigger Precision](#19--pin-code--ward-level-trigger-precision)
21. [Drill Execution Engine (Structured Simulations)](#20--drill-execution-engine-structured-simulations)
22. [System Health Verification Panel](#21--system-health-verification-panel)
23. [Live API Data Panel](#22--live-api-data-panel)
24. [Demo Checklist (Hackathon-Ready)](#23--demo-checklist-hackathon-ready)
25. [Admin Dashboard — 15 Tabs](#24--admin-dashboard--15-tabs)
26. [Onboarding Flow (Redesigned)](#25--onboarding-flow-redesigned)
27. [Pricing Tier Alignment](#26--pricing-tier-alignment)
28. [Standard Insurance Exclusions Screen](#27--standard-insurance-exclusions-screen)
29. [Key Formulas (Every Number Explainable)](#-key-formulas-every-number-explainable)
30. [Test Coverage](#-test-coverage)
31. [Phase 2 File Map](#-phase-2-file-map)

---

## 🔄 What Changed — Summary

| Area | Phase 1 | Phase 2 |
|------|---------|---------|
| **Fraud Detection** | 6-factor rules-based | 7-factor weighted model with GPS centroid drift + velocity physics check |
| **Premium Engine** | Flat ₹29/39/79 tiers | Aligned to ₹22/33/45 with 7-factor ML formula + RIQI + seasonal + loyalty |
| **Payout Logic** | Simple hourly rate | RIQI multiplier + sustained event mode + zone pool share cap |
| **Trigger Matching** | City-level average | Pin-code / ward-level precision |
| **Zone Management** | Static assignment | Dynamic reassignment with 24hr acceptance + premium recalculation |
| **Stress Testing** | None | 6 actuarial scenarios (monsoon 14-day, cyclone, AQI spike, bandh, collusion) |
| **Data Validation** | GPS + zone check | 10-check pre-payout validation matrix with confidence scores |
| **Admin Dashboard** | 3 tabs | 15 tabs (BCR, Fraud Queue, Zone Map, Drills, RIQI, Oracle, etc.) |
| **Notifications** | English only | English + Hindi with template system |
| **Oracle System** | None | Social Oracle with NLP + real API cross-validation |
| **Onboarding** | Direct registration | Guided onboarding flow with eligibility gate + shift selection |

---

## 1. 🔀 Multi-Trigger Arbitration Engine

**Problem:** Multiple triggers (rain + AQI + shutdown) can fire simultaneously → duplicate payouts.

**Solution:** The claims processor groups triggers by partner + time + zone and deduplicates:
- Only one claim per partner per trigger window (cryptographic event ID)
- If overlapping triggers exist, the highest-severity payout is applied
- Secondary triggers are logged but not paid

**Files:**
- `backend/app/services/claims_processor.py` → duplicate claim detection + event ID dedup
- `backend/app/services/trigger_engine.py` → de minimis rule (45-min threshold) prevents micro-trigger spam

---

## 2. 🔍 7-Factor Fraud Scoring Model (Upgraded from 6-Factor)

**Problem:** Old model used only GPS + zone checks. No centroid drift or velocity detection.

**Solution:** Full 7-factor weighted fraud model with hard reject rules:

```
fraud_score = w1×gps_coherence + w2×run_count_check + w3×zone_polygon_match
            + w4×claim_frequency + w5×device_fingerprint + w6×traffic_cross_check
            + w7×centroid_drift_score

Weights: w1=0.25, w2=0.25, w3=0.15, w4=0.15, w5=0.10, w6=0.05, w7=0.05
```

| Score Range | Decision |
|------------|----------|
| < 0.50 | ✅ Auto-approve |
| 0.50 – 0.75 | 🔍 Enhanced validation |
| 0.75 – 0.90 | 👁 Manual review queue |
| > 0.90 | ❌ Auto-reject |

**Hard Reject Rules (override score):**
- GPS velocity > 60 km/h between pings → GPS spoof
- Centroid drift > 15km from declared dark store → location fraud
- Run count > 0 during disruption window → Activity Paradox
- Zone not suspended by platform

**New in Phase 2:**
- `w7: centroid_drift_score` — 30-day GPS centroid tracking
- Velocity physics check (haversine distance / time between pings)
- `compute_centroid()` and `compute_max_velocity_kmh()` helper functions

**Files:**
- `backend/app/services/fraud_service.py` — Full 7-factor model
- `backend/app/services/ml_service.py` — `FraudAnomalyModel` class with weighted scoring

---

## 3. 🛣️ RIQI — Road Infrastructure Quality Index

**Problem:** Same rain amount causes different disruption depending on road quality. Bellandur (flood-prone) ≠ Whitefield.

**Solution:** RIQI score (0–100) per zone with provenance tracking:

| RIQI Band | Score Range | Payout Multiplier | Premium Adjustment |
|-----------|-----------|-------------------|-------------------|
| Urban Core | > 70 | 1.00× | 1.00× |
| Urban Fringe | 40–70 | 1.25× | 1.15× |
| Peri-Urban | < 40 | 1.50× | 1.30× |

**Per-Zone Overrides (not just city-level):**
- BLR-BEL (Bellandur): RIQI 48 — flood-prone, 1.25× payout
- DEL-CP (Connaught Place): RIQI 72 — urban core, 1.00× payout
- MUM-POW (Powai): RIQI 45 — lake area, 1.25× payout

**Provenance Tracking:** Every RIQI score shows its data source:
- `seeded` — initial setup values
- `computed` — recomputed from historical metrics
- `fallback_city_default` — city average when zone data unavailable

**Files:**
- `backend/app/services/riqi_service.py` — RIQI scoring + provenance
- `backend/app/models/zone_risk_profile.py` — DB model
- `backend/app/schemas/riqi.py` — API schemas
- `frontend/src/components/admin/RiqiProvenancePanel.jsx` — Admin UI

---

## 4. 🚪 Underwriting Gate & Auto-Downgrade

**Problem:** Anyone could buy any policy tier regardless of activity level.

**Solution:**
- **Minimum 7 active delivery days** in last 30 before cover starts
- **Auto-downgrade to Flex** if < 5 active days in last 30 (cannot self-select Standard/Pro)
- Demo exception: Delhi zones bypass the 7-day check for judging

**Files:**
- `backend/app/services/premium_service.py` — `check_underwriting_gate()`, `apply_auto_downgrade()`

---

## 5. ⏱️ Sustained Event Protocol (Consecutive Disruption)

**Problem:** What if a monsoon lasts 14 days? Normal payout mode drains reserves.

**Solution:** Consecutive Disruption Protocol from Guidewire specification:

| Mode | Payout | Cap |
|------|--------|-----|
| Normal (Days 1–4) | Standard tier payout (e.g. ₹400/day) | Weekly cap applies |
| Sustained (Day 5+) | 70% of daily tier max (e.g. ₹280/day) | No weekly cap, max 21 days |

- Day 7: Automatic reinsurance threshold review flagged in admin
- City-level payouts capped at 120% of weekly premium pool

**Files:**
- `backend/app/services/premium_service.py` — `calculate_payout()` with sustained event modifier

---

## 6. 🏗️ Zone Pool Share Cap (Mass Event Protection)

**Problem:** One busy zone draining entire payout reserve during mass disruption.

**Solution:**
```
payout_per_partner = min(calculated_payout, zone_pool_share)
zone_pool_share = city_weekly_reserve × zone_density_weight / partners_in_event
City hard cap: total event payout ≤ 120% of city weekly premium pool
```

| Zone Density | Partners | Weight |
|-------------|----------|--------|
| Low | < 50 | 0.15 |
| Medium | 50–150 | 0.35 |
| High | > 150 | 0.50 |

**Files:**
- `backend/app/services/premium_service.py` — `calculate_zone_pool_share()`
- `backend/app/services/claims_processor.py` — Applied during claim creation

---

## 7. 📉 BCR / Loss Ratio Monitoring

**Problem:** No financial health monitoring dashboard.

**Solution:**
```
BCR = total_claims_paid / total_premiums_collected
Target BCR: 0.55 – 0.70
```

| Loss Ratio | Action |
|-----------|--------|
| < 55% | Below target (under-paying) |
| 55–70% | ✅ Healthy |
| 70–85% | ⚠️ Warning |
| > 85% | 🛑 Suspend new enrolments |
| > 100% | 🚨 Reinsurance treaty activation |

**Files:**
- `backend/app/services/premium_service.py` — `calculate_bcr()`
- `frontend/src/components/admin/BCRPanel.jsx` — City-level BCR dashboard with charts

---

## 8. 🗓️ City-Specific Seasonal Risk Calendar

**Problem:** Flat +18% monsoon multiplier across all cities.

**Solution:** Per-city monthly multipliers:

| City | High Risk Months | Primary Peril | Multiplier |
|------|-----------------|---------------|------------|
| Bangalore | Jun–Sep | Flash floods | +20% |
| Mumbai | Jul–Sep | Monsoon flooding | +25% |
| Delhi NCR | Oct–Jan | Dangerous AQI | +18% |
| Chennai | Oct–Dec | NE monsoon / cyclone | +22% |
| Hyderabad | Jul–Sep | Flash floods | +15% |
| Kolkata | Jun–Sep | Cyclone / flooding | +20% |

Each city has a separate premium pool — Delhi AQI pool is independent of Mumbai rain pool.

**Files:**
- `backend/app/services/ml_service.py` — `CITY_SEASONAL_MULTIPLIERS` lookup table

---

## 9. 🏢 Zone Density Risk Bands

**Problem:** No visibility into partner concentration risk per zone.

**Solution:** Each zone tagged with density band (Low/Medium/High) affecting pool share caps:
- Visible on admin Zone Map panel
- Zone density weight drives mass event payout proportioning

**Files:**
- `backend/app/services/claims_processor.py` — `_get_zone_density_weight()`
- `frontend/src/components/admin/ZoneMapPanel.jsx` — density visualization

---

## 10. 🔄 Sudden Zone Reassignment Handling

**Problem:** Zepto frequently restructures dark store zones mid-week. No handling existed.

**Solution:** Full state machine for zone reassignment:

```
proposed ──(partner accepts)──► accepted ──► zone_id updated
    │
    ├──(partner rejects)──► rejected
    │
    └──(24h timeout)──► expired
```

- Partner gets 24-hour window to accept new zone risk score
- System recalculates premium for remaining days in the week
- Difference is credited/debited on next Monday auto-renewal
- Zone reassignment history logged in partner profile

**Files:**
- `backend/app/services/zone_reassignment_service.py` — Full state machine
- `backend/app/models/zone_reassignment.py` — DB model + `ReassignmentStatus` enum
- `backend/app/schemas/zone_reassignment.py` — API schemas
- `frontend/src/components/admin/ReassignmentQueuePanel.jsx` — Admin queue UI
- `frontend/src/components/ReassignmentCountdown.jsx` — Partner-facing countdown

---

## 11. ⚡ Stress Test Scenarios (6 Actuarial Scenarios)

**Problem:** No modelling of extreme but plausible disaster scenarios.

**Solution:** 6 hardcoded stress scenarios with reserve calculations:

| Scenario | Partners | Est. Payout | % Weekly Pool | System Mode |
|----------|----------|------------|--------------|-------------|
| 14-Day Monsoon (BLR+BOM) | 4,200 | ₹88.2L | ~200% | Sustained Event + Reinsurance |
| AQI Spike (DEL+NOI+GGN) | 5,100 | ₹76.5L | ~165% | Proportional reduction |
| Cyclone (CHN+BOM) | 6,000 | ₹1.08 Cr | ~380% | Immediate reinsurance |
| Civic Shutdown (Bandh, 3d) | 3,500 | ₹63L | ~145% | Normal → proportional Day 3 |
| Dark Store Closure (BLR, 40%) | 700 | ₹4.2L | ~18% | Normal payout + zone reassignment |
| Collusion Ring (50 fake accounts) | 50 | ₹0 (blocked) | 8% exposure | Auto-reject + fraud queue |

Each scenario calculates: `projected_claims`, `projected_payout`, `city_reserve_available`, `reserve_needed`.

**Files:**
- `backend/app/services/stress_scenario_service.py` — 4 built-in scenarios with formulas
- `backend/app/services/drill_service.py` — 6 drill presets including stress scenarios
- `frontend/src/components/admin/StressProofPanel.jsx` — Admin stress widget
- `frontend/src/components/StressWidget.jsx` — Detailed stress scenario component

---

## 12. 🔮 Social Oracle Verification Engine

**Problem:** No external validation of trigger claims beyond weather/AQI APIs.

**Solution:** Full NLP-powered social media verification pipeline:

1. **Extract location** from text → map to zone (DB lookup, alias match, city fallback)
2. **Classify event type** → rain, heat, AQI, shutdown, closure (keyword scoring)
3. **Call real APIs** (OpenWeatherMap, WAQI) using zone GPS coordinates
4. **Cross-validate** weather + AQI + traffic data against claimed conditions
5. **Compute confidence score** (0–100%) with weighted factors

**Confidence Score Weights:**
- Location found in DB: +15
- Event identified: +10
- Primary API confirms: +40 (live) / +25 (mock)
- Secondary API supports: +15 (live) / +8 (mock)
- Traffic cross-validation: +10
- No fake indicators: +10

**Verdict:**
- ≥ 70% → ✅ Claim VERIFIED, autonomous trigger eligible
- 40–70% → ⚠️ INCONCLUSIVE, manual review
- < 40% → ❌ Claim REJECTED

**Files:**
- `backend/app/services/social_oracle.py` — Full pipeline (672 lines)
- `backend/app/api/social_oracle_api.py` — API endpoints
- `frontend/src/components/admin/SocialOraclePanel.jsx` — Admin UI with streaming verification

---

## 13. 🛡️ Oracle Reliability & Fallback System

**Problem:** What if API data is wrong, delayed, or conflicting?

**Solution:** Multi-source validation built into trigger engine:
- Data source health monitoring (live/mock status per API)
- Oracle agreement scoring between weather, AQI, and traffic sources
- Stale data detection in validation matrix
- Fallback to mock mode when live APIs fail
- Confidence scores propagated through entire claim pipeline

**Files:**
- `backend/app/services/external_apis.py` — `get_source_health()`, live/mock auto-fallback
- `backend/app/services/verification_service.py` — 9-component system health check
- `backend/tests/test_oracle_reliability.py` — Oracle-specific test suite

---

## 14. 📱 Platform Activity Simulation Layer

**Problem:** No real integration with gig platforms (Zepto, Blinkit).

**Solution:** Structured mock platform feeds with realistic signals:
- Platform login status
- Active shift detection
- Orders accepted/completed (recent count)
- Last app ping timestamp
- Zone dwell time (minutes)
- Suspicious inactivity flag
- Per-partner DB persistence (`partner_platform_activity` table)

**Files:**
- `backend/app/services/claims_processor.py` — `get_db_partner_platform_activity()`, `upsert_db_partner_platform_activity()`
- `backend/app/services/external_apis.py` — `MockPlatformAPI`, `evaluate_partner_platform_eligibility()`
- `backend/tests/test_platform_activity_simulation.py` — Test suite

---

## 15. ✅ Real-World Validation Matrix (10-Check Pre-Payout)

**Problem:** Claims had minimal validation before payout.

**Solution:** Every claim runs through a 10-check validation matrix:

| # | Check | Source |
|---|-------|--------|
| 1 | Source threshold breach confirmed | Weather/AQI API |
| 2 | Zone match confirmed | Database |
| 3 | Pin-code match confirmed | Zone coverage metadata |
| 4 | Active policy confirmed | Policy DB |
| 5 | Shift-window confirmed | Partner runtime metadata |
| 6 | Partner activity (not offline/leave) | Runtime metadata |
| 7 | Platform activity confirmed | Platform simulation |
| 8 | Fraud score below threshold | 7-factor fraud model |
| 9 | Data freshness acceptable | Data source tag |
| 10 | Cross-source agreement | Oracle reliability engine |

Each check returns: `check_name`, `passed`, `reason`, `source`, `confidence` (0–1).

**Files:**
- `backend/app/services/claims_processor.py` — `build_validation_matrix()`
- `frontend/src/components/admin/TriggerProofPanel.jsx` — Visual validation matrix

---

## 16. 💳 Payment Reconciliation & Payout State Machine

**Problem:** No retry or recovery if payment fails.

**Solution:** Payout service with structured states:
- `payment_initiated` → `payment_confirmed` → claim marked PAID
- `payment_failed` → retry with new UPI reference
- Mock Razorpay integration with UPI reference generation
- SLA latency tracking per payout step

**Files:**
- `backend/app/services/payout_service.py` — `process_payout()`, `generate_upi_ref()`
- `backend/app/api/payments.py` — Payment endpoints

---

## 17. ⏰ Active Shift Window Check

**Problem:** Rain at 3 AM should not trigger payout for a daytime worker.

**Solution:**
- Partner declares active shift window at onboarding (e.g. Mon–Sat, 8AM–10PM)
- Trigger validation checks: was partner in declared active window at time of disruption?
- If partner manually went offline before trigger → no payout
- If partner declared leave → no payout
- Overnight shifts supported (e.g. 22:00–06:00)

**Files:**
- `backend/app/services/claims_processor.py` — `is_partner_available_for_trigger()`
- Partner model: `shift_days`, `shift_start`, `shift_end` fields

---

## 18. 🔔 Multilingual Notification Templates

**Problem:** Notifications only in English.

**Solution:** Template-based notifications with language support:
- **English (en)** and **Hindi (hi)** with fallback to English
- Templates for: claim_created, claim_approved, claim_paid, claim_rejected, trigger_forecast, policy_expiring, policy_renewed, zone_reassignment_proposed, zone_reassignment_accepted
- Trigger type labels localized (भारी बारिश, अत्यधिक गर्मी, etc.)
- Preview system for admin testing

**Files:**
- `backend/app/services/notification_templates.py` — Template engine + renderers
- `frontend/src/components/admin/NotificationPreviewPanel.jsx` — Admin preview UI

---

## 19. 📍 Pin-Code / Ward-Level Trigger Precision

**Problem:** City-average data used for triggers. AQI 380 in Anand Vihar ≠ AQI 380 in Dwarka.

**Solution:**
- Each zone has associated pin codes stored in `zone_coverage_metadata` table
- Trigger engine checks partner's pin code against zone pin codes
- Ward-level mapping for more precise trigger matching
- Partner runtime metadata includes `pin_code` field

**Files:**
- `backend/app/services/claims_processor.py` — `get_zone_coverage_metadata()`, pin-code matching
- `backend/app/services/trigger_engine.py` — `check_partner_pin_code_match()`
- `backend/tests/test_trigger_pincode_strictness.py` — Pin-code test suite

---

## 20. 🎯 Drill Execution Engine (Structured Simulations)

**Problem:** Manual trigger simulation with no structured output.

**Solution:** Full drill framework with preset scenarios:

| Drill Type | Trigger | Description |
|-----------|---------|-------------|
| Flash Flood | Rain 72mm/hr | Standard rain trigger test |
| AQI Spike | AQI 450 | Hazardous air quality test |
| Heatwave | 46°C | Extreme heat trigger test |
| Store Closure | Force majeure | Dark store closed (power outage) |
| Curfew | Section 144 | Civic shutdown test |
| Monsoon 14-Day | Sustained rain | Stress scenario: sustained event protocol |
| Multi-City AQI | AQI 480 across NCR | Stress scenario: zone pool share cap |
| Cyclone | CHN+BOM | Stress scenario: reinsurance activation |
| Bandh | City-wide strike | Stress scenario: shutdown + closure combo |
| Collusion Fraud | GPS spoofing | Fraud detection stress test |

Each drill produces a 9-step pipeline with latency metrics:
`injected → threshold_crossed → trigger_fired → eligible_partners_found → claims_created → fraud_scored → payouts_sent → notifications_sent → completed`

**Files:**
- `backend/app/services/drill_service.py` — 10 presets, pipeline execution
- `backend/app/models/drill_session.py` — DB tracking model
- `backend/app/api/admin_drills.py` — Drill API endpoints
- `frontend/src/components/admin/DrillPanel.jsx` — Admin drill UI
- `frontend/src/components/admin/DrillTimeline.jsx` — Pipeline visualization

---

## 21. 🔧 System Health Verification Panel

**Problem:** No way to verify all system components are working.

**Solution:** 9-component health check with latency tracking:
- Database connection
- Auth endpoints
- Zone list availability
- Trigger engine status
- Mock API injectability
- Claims processor availability
- Payout service configuration
- Push notification (VAPID) keys
- External data source health

**Files:**
- `backend/app/services/verification_service.py` — 9 health checks
- `frontend/src/components/admin/VerificationPanel.jsx` — Admin verification UI

---

## 22. 📡 Live API Data Panel

**Problem:** No visibility into actual data flowing through the system.

**Solution:** Admin panel showing real-time data from all connected APIs:
- OpenWeatherMap live weather data per zone
- WAQI/CPCB AQI readings
- Traffic conditions
- Platform status
- Source health (live vs mock)

**Files:**
- `frontend/src/components/admin/LiveDataPanel.jsx` — Real-time data visualization

---

## 23. ✅ Demo Checklist (Hackathon-Ready)

**Problem:** No structured way to verify all features work during demo.

**Solution:** Interactive checklist mapping to Guidewire judging criteria:
- Registration Process
- Policy Management
- Dynamic Premium Calculation
- Claims Management
- Product Variety
- Insurance Domain knowledge

**Files:**
- `frontend/src/components/admin/DemoChecklist.jsx` — Interactive checklist

---

## 24. 🖥️ Admin Dashboard — 15 Tabs

Phase 2 expanded the admin dashboard from 3 tabs to **15 fully functional tabs**:

| Tab | Purpose | Component |
|-----|---------|-----------|
| 📊 Overview | Key metrics, active policies, payout flow | `AdminStats.jsx` |
| 📉 BCR / Loss Ratio | City-level BCR with 85% suspension toggle | `BCRPanel.jsx` |
| 🗺️ Zone Map | Live zone map with density + trigger overlay | `ZoneMapPanel.jsx` |
| 🔍 Fraud Queue | Pending claims with one-click approve/reject | `FraudQueuePanel.jsx` |
| 🎯 Drills | Structured drill execution with 10 presets | `DrillPanel.jsx` |
| 📡 Live API Data | Real-time weather/AQI/traffic readings | `LiveDataPanel.jsx` |
| 🔍 Verification | 9-component system health check | `VerificationPanel.jsx` |
| ⚡ Stress Proof | Actuarial stress scenario modelling | `StressProofPanel.jsx` |
| 🔄 Reassignments | Zone reassignment queue management | `ReassignmentQueuePanel.jsx` |
| 🎯 Trigger Proof | Validation matrix visualization per claim | `TriggerProofPanel.jsx` |
| 📊 RIQI Provenance | Zone-level RIQI scores with data sources | `RiqiProvenancePanel.jsx` |
| 🔔 Notifications | Multilingual notification preview + test | `NotificationPreviewPanel.jsx` |
| ✅ Demo Checklist | Judging criteria verification checklist | `DemoChecklist.jsx` |
| 🔮 Auto-Oracle | Social media verification engine | `SocialOraclePanel.jsx` |
| ⚙️ Legacy Sim | Original trigger simulation + exclusions | `TriggerPanel.jsx` + `ExclusionsCard.jsx` |

---

## 25. 📱 Onboarding Flow (Redesigned)

**Problem:** Direct registration page without guided onboarding.

**Solution:** Multi-step onboarding wizard:
1. Welcome screen with product explanation
2. Partner ID entry + platform selection
3. GPS zone detection
4. Eligibility check (7-day activity gate)
5. Shift window selection
6. Plan selection with personalized premium
7. UPI link + push notification permission

**Files:**
- `frontend/src/components/ui/OnboardingFlow.jsx` — Full onboarding wizard
- `frontend/src/components/ui/RapidCoverOnboarding.jsx` — Onboarding components

---

## 26. 💰 Pricing Tier Alignment

**Phase 1 (Mismatched):** README said ₹39/59/89, code had ₹29/49/79.

**Phase 2 (Aligned to Guidewire spec):**

| Tier | Weekly Premium | Max Payout/Day | Max Days/Week | Max Weekly | Ratio |
|------|---------------|----------------|---------------|-----------|-------|
| ⚡ Flex | ₹22/week | ₹250 | 2 days | ₹500 | ~1:23 |
| 🛵 Standard | ₹33/week | ₹400 | 3 days | ₹1,200 | ~1:36 |
| 🏆 Pro | ₹45/week | ₹500 | 4 days | ₹2,000 | ~1:44 |

**Files:**
- `backend/app/services/premium_service.py` — `TIER_CONFIG` with aligned values

---

## 27. 🚫 Standard Insurance Exclusions Screen

Added IRDAI-aligned exclusions displayed at onboarding:
- War & Armed Conflict
- Pandemic / Epidemic Declaration
- Nuclear & Radioactive Events
- Government Policy Changes
- Platform Operational Decisions
- Self-Inflicted / Voluntary Loss
- Health, Accident & Life (strictly out of scope)
- Vehicle Damage & Repair
- Disruptions Under 45 Minutes (de minimis)
- Claims After 48-Hour Window

**Files:**
- `frontend/src/components/admin/ExclusionsCard.jsx` — Exclusions display

---

## 📐 Key Formulas (Every Number Explainable)

### Premium Formula
```
Weekly Premium = Base (trigger_probability × avg_income_lost × days_exposed)
  × city_peril_multiplier
  × zone_risk_score_multiplier (0.8–1.4)
  × seasonal_index (city-specific, monthly)
  × activity_tier_factor (Flex=0.8, Standard=1.0, Pro=1.35)
  × RIQI_adjustment (urban=1.0, fringe=1.15, peri-urban=1.3)
  × loyalty_discount (1.0 → 0.94 after 4 clean weeks → 0.90 after 12)
  Capped at 3× base tier
```

### Payout Formula
```
Payout = disruption_hours × hourly_earning_baseline × zone_disruption_multiplier
  Capped at: daily_tier_max × eligible_disruption_days

Sustained Event Mode (5+ consecutive days):
  Payout_per_day = 0.70 × daily_tier_max, no weekly cap, max 21 days
```

### BCR / Loss Ratio
```
BCR = total_claims_paid / total_premiums_collected
Target: 0.55–0.70  |  >85% → suspend enrolments  |  >100% → reinsurance
```

### Zone Pool Share
```
payout_per_partner = min(calculated_payout, zone_pool_share)
zone_pool_share = city_weekly_reserve × zone_density_weight / partners_in_event
City hard cap: total event payout ≤ 120% of city weekly premium pool
```

---

## 🧪 Test Coverage

Phase 2 added **12 comprehensive test suites**:

| Test Suite | Lines | What It Tests |
|-----------|-------|---------------|
| `test_phase2_tasks.py` | 930 | All Phase 2 feature integration |
| `test_drills.py` | 590 | Drill execution pipeline |
| `test_partner_experience.py` | 510 | Partner onboarding + dashboard |
| `test_platform_activity_simulation.py` | 507 | Platform feed simulation |
| `test_validation_matrix.py` | 401 | 10-check pre-payout validation |
| `test_oracle_reliability.py` | 350 | Oracle data reliability |
| `test_riqi_provenance.py` | 295 | RIQI scoring + provenance |
| `test_zone_reassignment_flow.py` | 291 | Zone reassignment state machine |
| `test_trigger_pincode_strictness.py` | 255 | Pin-code level trigger matching |
| `test_notification_templates.py` | 245 | Multilingual notification rendering |
| `test_stress_scenarios.py` | 204 | Actuarial stress modelling |
| `conftest.py` | 88 | Test configuration + fixtures |

---

## 📁 Phase 2 File Map

### Backend — New Services (Phase 2)
| File | Purpose |
|------|---------|
| `services/riqi_service.py` | RIQI scoring with DB provenance |
| `services/social_oracle.py` | NLP social media verification |
| `services/zone_reassignment_service.py` | 24hr zone reassignment state machine |
| `services/stress_scenario_service.py` | Actuarial stress modelling |
| `services/drill_service.py` | Structured drill execution |
| `services/verification_service.py` | 9-component health check |
| `services/notification_templates.py` | Multilingual notification templates |
| `services/fraud_service.py` | 7-factor fraud model (upgraded) |
| `services/premium_service.py` | Full premium engine (rewritten) |

### Backend — New Models (Phase 2)
| File | Purpose |
|------|---------|
| `models/zone_reassignment.py` | Reassignment + status enum |
| `models/zone_risk_profile.py` | RIQI per-zone profile |
| `models/drill_session.py` | Drill execution tracking |

### Backend — New API Routes (Phase 2)
| File | Purpose |
|------|---------|
| `api/experience.py` | Partner experience endpoints |
| `api/admin_panel.py` | Admin panel stats + config |
| `api/admin_drills.py` | Drill execution API |
| `api/social_oracle_api.py` | Social oracle verification |

### Frontend — New Admin Components (Phase 2)
| File | Purpose |
|------|---------|
| `BCRPanel.jsx` | BCR / Loss Ratio dashboard |
| `ZoneMapPanel.jsx` | Interactive zone map |
| `FraudQueuePanel.jsx` | Fraud claim review queue |
| `DrillPanel.jsx` | Drill execution UI |
| `DrillTimeline.jsx` | Pipeline step visualization |
| `LiveDataPanel.jsx` | Real-time API data viewer |
| `VerificationPanel.jsx` | System health checks |
| `StressProofPanel.jsx` | Stress scenario widget |
| `ReassignmentQueuePanel.jsx` | Zone reassignment queue |
| `TriggerProofPanel.jsx` | Validation matrix viewer |
| `RiqiProvenancePanel.jsx` | RIQI score provenance |
| `NotificationPreviewPanel.jsx` | Notification template preview |
| `DemoChecklist.jsx` | Judging criteria checklist |
| `SocialOraclePanel.jsx` | Social oracle UI |
| `ImpactPanel.jsx` | Drill impact metrics |

---

<div align="center">

---

*Phase 2 extended the core system with advanced features such as multi-trigger arbitration, payment reconciliation, 7-factor fraud validation, RIQI urban/rural scoring, and oracle reliability systems to address real-world edge cases like overlapping triggers, payment failures, and unreliable data sources.*

**RapidCover Phase 2 — From Good Prototype to Production-Grade System**

*Built for Guidewire DEVTrails 2026*

</div>
