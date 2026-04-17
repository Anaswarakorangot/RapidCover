<div align="center">

# 🛵 RapidCover

### **Parametric Income Insurance Engine for India's Q-Commerce Delivery Workforce**

[![Platform](https://img.shields.io/badge/Platform-PWA%20(Mobile%20First)-8B2FC9?style=for-the-badge)](/)
[![Persona](https://img.shields.io/badge/Persona-Zepto%20%2F%20Blinkit%20Partners-FF6B35?style=for-the-badge)](/)
[![Hackathon](https://img.shields.io/badge/Guidewire-DEVTrails%202026-232F3E?style=for-the-badge)](/)
[![Insurance](https://img.shields.io/badge/Insurance-Parametric%20Income%20Protection-00B894?style=for-the-badge)](/)
[![ML Models](https://img.shields.io/badge/ML-3%20Trained%20Models-3498DB?style=for-the-badge)](/)
[![Tests](https://img.shields.io/badge/Tests-24%20Suites-27AE60?style=for-the-badge)](/)

<br/>

### 🔗 Live Demo

| Service | Link |
|---------|------|
| **Frontend** | [https://rapidcover-frontend.onrender.com](https://rapidcover-frontend.onrender.com) |
| **Backend API** | [https://rapidcover-backend.onrender.com](https://rapidcover-backend.onrender.com) |
| **Admin Panel** | [https://rapidcover-frontend.onrender.com/admin](https://rapidcover-frontend.onrender.com/admin) |

> **Admin Access:** Use `/admin` route. Default credentials configured via environment variables (`DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`).

<br/>

> *"Last month, a flash flood hit my dark store zone at 6 PM — peak hour. Zepto suspended the entire zone. I sat outside for 3 hours. Zero runs. Zero income. Nobody compensated. I just went home."*
>
> — **Manoj, 24**, Zepto Delivery Partner, Bellandur, Bangalore

<br/>

[📊 Pitch Deck](https://drive.google.com/file/d/1GGulslqDDAer2gFGl240MeIDa-fxa-Xx/view?usp=sharing) &nbsp;|&nbsp; [🎬 Demo Video](https://youtu.be/EYyQ2fW9NLc) &nbsp;|&nbsp; [🕸️ Knowledge Graph](https://anaswarakorangot.github.io/RapidCover/assets/knowledge-graph.html)

</div>

---

## 📌 Table of Contents

| # | Section | # | Section |
|---|---------|---|---------|
| 1 | [Problem Statement](#-the-problem) | 2 | [What RapidCover Is](#-what-rapidcover-is) |
| 3 | [Key Features](#-key-features) | 4 | [System Architecture](#-system-architecture) |
| 5 | [Tech Stack](#-tech-stack) | 6 | [ML Models & Training](#-ml-models--training-pipeline) |
| 7 | [Parametric Triggers](#-parametric-triggers) | 8 | [Fraud Detection](#-fraud-detection-architecture) |
| 9 | [Zero-Touch Claim Flow](#-zero-touch-claim-flow) | 10 | [Weekly Premium Model](#-weekly-premium-model) |
| 11 | [Admin Dashboard](#-admin-dashboard) | 12 | [Partner Experience](#-partner-experience) |
| 13 | [API Reference](#-api-reference) | 14 | [Installation & Setup](#-installation--setup) |
| 15 | [Environment Variables](#-environment-variables) | 16 | [Running the Demo](#-running-the-demo) |
| 17 | [Testing](#-testing) | 18 | [Actuarial Model](#-actuarial-model) |
| 19 | [Exclusions](#-exclusions) | 20 | [Business Viability](#-business-viability) |
| 21 | [Team](#-team) | 22 | [Contributing](#-contributing) |

---

## 💔 The Problem

India's Q-Commerce sector — Zepto, Blinkit, Swiggy Instamart — runs on **500,000+ gig delivery partners**. These workers earn per delivery, per shift. When an external disruption hits (flood, heatwave, curfew), income stops instantly:

```
Dark Store Suspended → Worker has NO other pickup point → Income = ₹0
```

| Disruption Event | Duration | Avg Income Lost | Current Compensation |
|---|---|---|---|
| Flash flood (zone-level) | 4–8 hours | ₹400–₹700 | ₹0 |
| Cyclone warning suspension | 2–4 days | ₹2,000–₹4,000 | ₹0 |
| Extreme heat advisory | 6–10 hours | ₹500–₹900 | ₹0 |
| Dangerous AQI breach | 3–6 hours | ₹250–₹500 | ₹0 |
| Curfew / Section 144 | 1–3 days | ₹800–₹2,400 | ₹0 |

**No bank product covers this. No platform compensates. RapidCover does — automatically, in under 60 seconds.**

---

## 🛡️ What RapidCover Is

RapidCover is a **weekly parametric income insurance platform** that automatically detects disruption events via real-time APIs, validates them through a 10-check pipeline, and credits payouts to the worker's UPI wallet — with **zero human intervention**.

```
TRADITIONAL INSURANCE:
  Event → File claim → Adjuster reviews → 7–21 days → Maybe payout

RAPIDCOVER PARAMETRIC:
  Event detected → APIs validate → 10-check matrix → UPI credit in ~49 seconds
                                                       Worker did nothing.
```

**Strictly covers income loss only.** No health. No vehicle. No accidents. No life insurance.

---

## ⚡ Key Features

### Core Insurance Engine
- **5 parametric triggers** — Rain/Flood, Extreme Heat, Dangerous AQI, Civic Shutdown, Dark Store Closure
- **Zero-touch claims** — 11-step automated pipeline from trigger detection to UPI payout
- **10-check validation matrix** — Source breach, zone polygon, pin-code, active policy, shift window, partner activity, platform confirmation, fraud score, data freshness, cross-source oracle
- **Multi-trigger arbitration** — Resolves overlapping events (e.g., rain + closure simultaneously)
- **Sustained event protocol** — 14-day monsoon mode with 70% payout to preserve reserves

### ML-Powered Intelligence
- **3 trained models** with serialized `.pkl` artifacts and full model metadata
- **Zone Risk Scorer** — XGBoost Regressor, 10 features, R² = 0.57
- **Dynamic Premium Engine** — XGBoost Regressor, 8 features, R² = 0.66
- **Fraud Detector** — Isolation Forest + 7-Factor Weighted Scoring, F1 = 0.96, ROC-AUC = 0.995

### Fraud Prevention (Isolation Forest + Collusion Detection)
- **Isolation Forest** for anomaly detection across multivariate GPS, activity, and device patterns
- **Collusion Detection** — Device fingerprinting, IP clustering, timing correlation analysis
- GPS coherence & velocity physics check (>60 km/h = spoof)
- Activity paradox detection (runs during disruption = hard reject)
- 30-day GPS centroid drift tracking (>15 km = auto-flag)
- Device fingerprinting & IP clustering for fraud rings
- Cryptographic duplicate event rejection

### Partner Experience (PWA)
- **Progressive Web App** — installable via WhatsApp link, no app store required
- **Service worker** with offline caching and background sync
- **Web Push notifications** (VAPID) — lock-screen alerts in English & Hindi
- **UPI deep links** — GPay/PhonePe one-tap payments
- **Guided onboarding flow** with eligibility check, shift selection, and RIQI-adjusted plan cards
- **Trust Center** — full transparency on how claims are validated

### Admin Dashboard (15+ Tabs)
- Real-time BCR / Loss Ratio monitoring with city-level granularity
- Interactive zone map with Leaflet (density + trigger overlay)
- Fraud queue (one-click approve/reject/bulk actions)
- Drill execution engine (10 structured presets + stress scenarios)
- Social Oracle verification panel (NLP + live API cross-check)
- Live API data feeds, RIQI provenance, notification preview, payment reconciliation
- Demo mode scenario simulation & instant replay

### Infrastructure & Compliance
- **Background scheduler** (APScheduler) polling trigger engine every 45 seconds
- **Payment state machine** with auto-reconciliation for failed/stuck payouts
- **Zone reassignment state machine** — 24-hour countdown for partner zone transfers
- **Policy lifecycle management** — Auto-renewal, adverse selection gates, SS Code 2020 compliance
- **Social Security Code (SS Code) compliance** — 90/120-day engagement gates per platform mix
- **Rate limiting** (SlowAPI) and global exception handling
- **Sentry integration** for error tracking (optional)
- **Redis caching** (FastAPICache) with InMemory fallback
- **Structured JSON logging** with configurable levels
- **WebSocket real-time streaming** for admin claim/trigger updates
- **Alembic migrations** for database schema management

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     MOBILE LAYER (PWA)                               │
│   React 19 + Vite 8 — Partner App + Admin Dashboard                  │
│   TailwindCSS 4  |  Web Push API  |  Leaflet Maps  |  UPI Deep Link │
│   Service Worker  |  Offline Mode  |  EN + HI Internationalization   │
└──────────────────────────────────────────────────────────────────────┘
                         ↕ REST API (18 route modules)
┌──────────────────────────────────────────────────────────────────────┐
│              BACKEND — Python + FastAPI (39 services)                 │
│                                                                      │
│  Auth          │  Policy Engine    │  Trigger Engine                  │
│  Claims Proc.  │  Fraud Service    │  Fraud Detector                 │
│  Payout Svc.   │  Premium Engine   │  ML Service (3 models)          │
│  Drill Engine  │  RIQI Service     │  Social Oracle (NLP)            │
│  Zone Reassign │  Scheduler        │  Reconciliation                 │
│  Notifications │  Collusion Det.   │  Device Fingerprint             │
│  Demo Mode     │  Stress Scenarios │  Prediction Service             │
│  Verification  │  Policy Lifecycle │  Policy Certificate (PDF)       │
│  Replay Svc.   │  Payment State M. │  Runtime Metadata               │
└──────────────────────────────────────────────────────────────────────┘
       ↕                      ↕                       ↕
┌───────────────┐  ┌─────────────────────┐  ┌──────────────────┐
│  ML MODELS    │  │   EXTERNAL APIs     │  │  PAYMENT LAYER   │
│  (Serialized) │  │  OpenWeatherMap     │  │  Razorpay Test   │
│               │  │  WAQI/CPCB AQI      │  │  Stripe Test     │
│  zone_risk    │  │  Mock Traffic       │  │  Mock UPI        │
│  premium      │  │  Mock Civic Alert   │  └──────────────────┘
│  fraud        │  │  Platform Activity  │
│               │  │  Social Oracle NLP  │
│  + encoders   │  │  Groq AI Chat       │
└───────────────┘  └─────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────────┐
│         DATA LAYER — SQLite (dev) / PostgreSQL (prod)                │
│                                                                      │
│   Partners  │ Zones  │ Policies  │ Claims  │ Trigger Events          │
│   Zone Risk Profiles  │ Zone Reassignments  │ Push Subscriptions     │
│   Drill Sessions  │ Weather Observations  │ Predictions              │
│   GPS Pings  │ Partner Devices  │ Sustained Events                   │
│   Active Event Trackers  │ System Settings                           │
└──────────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────────┐
│   BACKGROUND JOBS — APScheduler (SQLAlchemy persistent job store)    │
│   Trigger polling (45s) │ Payment reconciliation │ Event tracking    │
└──────────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────────┐
│   NOTIFICATIONS — Web Push (VAPID/pywebpush) + Template Engine      │
│   English │ Hindi  │ Multilingual fallback chain                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19 + Vite 8 (PWA) | Android-installable app with push notifications, native GPS, UPI deep links |
| **Styling** | TailwindCSS v4 | Responsive mobile-first design system |
| **Maps** | Leaflet + React-Leaflet | Zone visualization, dark store mapping |
| **Routing** | React Router v7 | SPA with protected routes and auth guards |
| **Backend** | Python + FastAPI | Async REST API with 39 service modules and 18 route modules |
| **Database** | SQLite (dev) / PostgreSQL (prod) | 16 SQLAlchemy models with Alembic migrations |
| **Caching** | Redis (primary) / InMemory (fallback) | API response caching via FastAPICache |
| **ML** | XGBoost + scikit-learn + pandas + NumPy | 3 trained models with joblib serialization |
| **Anomaly Detection** | Isolation Forest | Multivariate fraud pattern detection |
| **Scheduler** | APScheduler | Persistent background jobs (trigger polling, reconciliation) |
| **Weather** | OpenWeatherMap API (free tier) | Real-time rainfall, temperature, humidity per zone GPS |
| **AQI** | WAQI / aqicn.org + CPCB API | Station-level air quality data for Indian cities |
| **Traffic** | Mock road condition feed | Cross-validation layer for trigger verification |
| **Payments** | Razorpay Test Mode + Stripe Test Mode | Full payout demonstration (no real transactions) |
| **Notifications** | pywebpush (VAPID) | Lock-screen push in English + Hindi |
| **Auth** | JWT (python-jose) + OTP + bcrypt | Partner OTP login + Admin email/password auth |
| **PDF** | ReportLab | Policy certificate generation |
| **Monitoring** | Sentry SDK (optional) | Production error tracking with 10% sampling |
| **Rate Limiting** | SlowAPI | Request throttling per endpoint |
| **Testing** | pytest (backend) + Vitest + React Testing Library (frontend) | 24 backend test suites + frontend integration tests |

---

## 🧠 ML Models & Training Pipeline

Three production ML models are trained on synthetic but domain-realistic data, with full provenance tracking.

### Model 1 — Zone Risk Scorer

| Attribute | Value |
|-----------|-------|
| Algorithm | XGBoost Regressor |
| Features | 10 (city, avg rainfall, flood events, AQI, heat advisories, bandh events, dark store suspensions, road flood prone, month) |
| Training Split | 720 train / 240 val / 240 test |
| Test R² | 0.5727 |
| Test MAE | 6.43 |
| Cross-Val R² | 0.5703 ± 0.066 |
| Top Feature | `road_flood_prone` (21.9% importance) |

<div align="center">
<img src="./assets/model1_xgboost_zone_risk_scorer.svg" width="100%" alt="Model 1 — XGBoost Zone Risk Scorer: feature provenance to risk score"/>
</div>

---

### Model 2 — Dynamic Premium Engine

| Attribute | Value |
|-----------|-------|
| Algorithm | XGBoost Regressor |
| Target | Expected weekly payout pressure (independent of pricing formula) |
| Features | 8 (city, zone risk score, active days, avg hours, tier, loyalty weeks, month, RIQI score) |
| Training Split | 900 train / 300 val / 300 test |
| Test R² | 0.6646 |
| Test MAE | ₹10.71 |
| Cross-Val R² | 0.6881 ± 0.033 |
| Note | Deterministic price floor, IRDAI cap, and loyalty adjustments applied post-prediction |

<div align="center">
<img src="./assets/model2_randomforest_disruption_classifier.svg" width="100%" alt="Model 2 — XGBoost Dynamic Premium Engine: features to weekly premium"/>
</div>

---

### Model 3 — Fraud Detector

| Attribute | Value |
|-----------|-------|
| Algorithm | **Isolation Forest** + 7-Factor Weighted Scoring |
| Features | 9 (GPS in zone, run count, zone polygon match, claim frequency, device consistency, traffic disrupted, centroid drift, GPS velocity, zone suspended) |
| Weight Distribution | GPS 0.25 + Run Count 0.25 + Zone Polygon 0.15 + Claim Frequency 0.15 + Device FP 0.10 + Traffic 0.05 + Centroid Drift 0.05 |
| Hard Rejects | GPS velocity >60 km/h, zone not suspended, activity paradox, centroid drift >15 km |
| Thresholds | <0.50 auto-approve \| 0.50–0.75 enhanced \| 0.75–0.90 manual \| >0.90 auto-reject |
| Architecture | Isolation Forest detects multivariate anomalies. Deterministic hard-stops override scoring. 7-factor model assists triage in grey areas. |

> ⚠️ **Note:** Model 3 uses **Isolation Forest** (unsupervised anomaly detection), not Random Forest. The two are distinct algorithms — Isolation Forest isolates anomalies by random feature splitting, making it ideal for fraud detection where labelled fraud samples are scarce.

<div align="center">
<img src="./assets/model3_isolation_forest_fraud_detector.svg" width="100%" alt="Model 3 — Isolation Forest Fraud Anomaly Detector: behavioral signals to fraud verdict"/>
</div>

---

### Training Pipeline

```
backend/ml_training/
├── generate_training_data.py   # Synthetic data generation with domain constraints
├── train_models.py             # Full training pipeline with cross-validation
├── data/                       # Generated training datasets
└── README.md                   # Model cards and methodology

backend/ml_models/
├── zone_risk_model.pkl         # Serialized zone risk model
├── premium_model.pkl           # Serialized premium model
├── fraud_model.pkl             # Serialized fraud model (Isolation Forest)
├── *_encoder.pkl               # Label encoders (city, tier)
└── model_metadata.json         # Full provenance, metrics, feature importances
```

---

## ⚡ Parametric Triggers

Five conditions that automatically fire a payout — no claim form, no human review:

| # | Trigger | Source | Threshold | Validation |
|---|---------|--------|-----------|------------|
| 1 | **Heavy Rain / Flood** | OpenWeatherMap + IMD | >55mm/hr sustained 30+ min OR IMD orange/red alert | Zone polygon + ops suspension + traffic + GPS |
| 2 | **Extreme Heat** | OpenWeatherMap + IMD | >43°C sustained 4+ hours OR state advisory | Zone-level temp + partner GPS in zone |
| 3 | **Dangerous AQI** | CPCB / WAQI | AQI >400 (Severe) for 3+ hours | Station-level AQI at nearest monitor + zone polygon |
| 4 | **Civic Shutdown** | Mock civic feed + NLP | Official curfew / Section 144 / bandh for 2+ hours | Zone boundary + traffic cross-check |
| 5 | **Dark Store Closure** | Mock platform ops API | Assigned dark store closed >90 min (non-maintenance) | Timestamped closure log + active shift + traffic |

### 10-Check Validation Matrix (Every Payout)

```
[1. Source threshold breach] → [2. Zone polygon match]
         ↓
[3. Pin-code / ward match]  → [4. Active policy confirmed]
         ↓
[5. Shift-window check]     → [6. Partner activity (not offline)]
         ↓
[7. Platform activity]      → [8. 7-Factor Fraud Score < 0.90?]
         ↓
[9. Data freshness check]   → [10. Cross-source agreement (Oracle)]
         ↓
[Payout Calculated + RIQI]  → [Zone Pool Share Cap Applied]
         ↓
[UPI Credit via Razorpay]   → [Push Notification in Partner's Language]
```

---

## 🔍 Fraud Detection Architecture

**Isolation Forest** for anomaly detection combined with seven weighted deterministic factors:

```
fraud_score = 0.25×gps_coherence + 0.25×run_count_check + 0.15×zone_polygon_match
            + 0.15×claim_frequency + 0.10×device_fingerprint + 0.05×traffic_cross_check
            + 0.05×centroid_drift_score

anomaly_flag = IsolationForest(GPS_patterns, device_patterns, activity_patterns)
```

| Score Range | Decision |
|-------------|----------|
| < 0.50 | ✅ Auto-approve |
| 0.50 – 0.75 | 🔍 Enhanced validation |
| 0.75 – 0.90 | 👁 Manual review queue |
| > 0.90 | ❌ Auto-reject with explanation |

### Attack Vectors & Detection

| Attack | Method | Detection |
|--------|--------|-----------|
| GPS Spoofing | Fake location in suspended zone | Velocity physics check — >60 km/h between pings = spoof |
| Activity Paradox | Claim disruption while completing runs | `run_count > 0` during window → **hard reject** |
| Zone Boundary Gaming | Register high-risk zone, operate elsewhere | 30-day GPS centroid must stay within 15 km of declared dark store |
| Duplicate Events | Claim same disruption twice | Cryptographic event ID per trigger — DB-level rejection |
| Collusion Ring | Multiple fake partners, same device/network | Device fingerprint + IP clustering (`collusion_detector.py`) |
| Centroid Drift | GPS suddenly in new zone | 30-day centroid drift >15 km = auto-flag |
| Multivariate Anomalies | Complex fraud patterns | Isolation Forest flags unusual combinations of features |

---

## 🔄 Zero-Touch Claim Flow

<div align="center">
<img src="./assets/zero_touch_claim.png" width="100%" alt="Zero-Touch Claim Flow — Parametric Trigger Pipeline showing 11 steps from disruption detection to UPI payout in ~49 seconds"/>
</div>

The end-to-end flow from disruption to payout with zero partner intervention:

```
┌──────────────────────────────────────────────────────────────┐
│                    ZERO-TOUCH CLAIM PIPELINE                  │
│                                                              │
│  1. Trigger detected (ward-level threshold breach)           │
│  2. Active shift check — is partner in declared window?      │
│  3. Zone polygon match (GPS coordinates)                     │
│  4. Platform suspension confirmed (mock ops API)             │
│  5. Traffic cross-check (road disruption confirmed)          │
│  6. GPS coherence + centroid drift check                     │
│  7. Run count = 0 during disruption window                   │
│  8. 7-Factor fraud score computed (ML + deterministic)       │
│  9. Isolation Forest anomaly detection                       │
│  10. Payout calculated (RIQI multiplier + zone pool cap)     │
│  11. UPI credit via Razorpay/Stripe mock                     │
│  12. Push notification in partner's language (EN / HI)       │
│                                                              │
│  Partner action required:  ZERO                              │
│  Trigger to money in wallet:  ~49 seconds                    │
└──────────────────────────────────────────────────────────────┘
```

### Live Example

> **Wednesday 5:47 PM, Bellandur.** IMD: 72mm/hr. OpenWeatherMap confirms.
>
> **5:47:23** — Zone BLR-BEL polygon match confirmed. RIQI: 48.
> **5:47:28** — Shift window: Manoj active Mon-Sat 8AM-10PM. ✅
> **5:47:35** — Zepto mock ops: Zone suspended.
> **5:47:44** — GPS: 200m from dark store. Centroid drift: 0.2 km. ✅
> **5:47:54** — 7-Factor fraud score: 0.11. Isolation Forest: Normal. Auto-approve.
> **5:48:02** — Payout: ₹272 × 1.25 RIQI = **₹340**.
> **5:48:12** — Lock screen (Kannada): *"₹340 ನಿಮ್ಮ UPI ಗೆ ಜಮಾ ಆಗಿದೆ."*
>
> **Total time: 49 seconds. Manoj did nothing.**

---

## 💰 Weekly Premium Model

Gig workers earn weekly, spend weekly, plan weekly. RapidCover is priced to match.

### Base Tiers

| Tier | Weekly Premium | Max Payout / Day | Max Days / Week | Ratio |
|------|---------------|-----------------|-----------------|-------|
| ⚡ **Flex** (Part-time) | ₹22/week | ₹250 | 2 days | ~1:23 |
| 🛵 **Standard** (Full-time) | ₹33/week | ₹400 | 3 days | ~1:36 |
| 🏆 **Pro** (Peak rider) | ₹45/week | ₹500 | 4 days | ~1:44 |

### 7-Factor Dynamic Pricing (ML-Powered)

```
PERSONALIZED WEEKLY PREMIUM =
  Base Tier Price
  × City Peril Multiplier           (city-specific)
  × Zone Risk Score Multiplier      (0.8–1.4, RIQI per pin-code)
  × Seasonal Disruption Index       (BLR +20% Jun-Sep, DEL +18% Oct-Jan)
  × RIQI Adjustment                 (urban=1.0, fringe=1.15, peri-urban=1.3)
  × Activity Tier Factor            (Flex=0.8, Standard=1.0, Pro=1.35)
  × Partner Active Hours Factor     (more hours = more exposure)
  × Loyalty Discount                (−6% after 4 weeks, −10% after 12 weeks)
  Capped at 3× base tier (IRDAI microinsurance cap)
```

### Underwriting Gates

- **Minimum 7 active delivery days** in last 30 before cover starts
- **Auto-downgrade to Flex** if <5 active days in last 30
- Worker on leave / voluntarily offline → no payout even if trigger fires

---

## 📊 Admin Dashboard

<div align="center">
<img src="./assets/admin_oversight.png" width="100%" alt="Admin Dashboard — 15+ tabs showing data harvesting, core analytics engine with 3 ML models, and risk protocols including the Bornhuetter-Ferguson actuarial engine"/>
</div>

The admin panel is a full-screen dark-themed dashboard with **15+ tabs** for insurer operations:

| Tab | Component | Purpose |
|-----|-----------|---------|
| 📊 Overview | `AdminStats.jsx` | Key metrics, active policies, payout flow |
| 📉 BCR / Loss Ratio | `BCRPanel.jsx` | City-level BCR with 85% suspension toggle |
| 🗺️ Zone Map | `ZoneMapPanel.jsx` | Interactive Leaflet map with density + trigger overlay |
| 🔍 Fraud Queue | `FraudQueuePanel.jsx` | Pending claims with approve/reject/bulk actions |
| 🎯 Drills | `DrillPanel.jsx` | 10 structured drill presets with timeline visualization |
| 📡 Live API Data | `LiveDataPanel.jsx` | Real-time weather/AQI/traffic per zone |
| ✅ Verification | `VerificationPanel.jsx` | 9-component system health check |
| ⚡ Stress Proof | `StressProofPanel.jsx` | 14-day monsoon scenario + reserve calculation |
| 🔄 Reassignments | `ReassignmentQueuePanel.jsx` | Zone reassignment queue (24hr state machine) |
| 🎯 Trigger Proof | `TriggerProofPanel.jsx` | 10-check validation matrix per claim |
| 📊 RIQI Provenance | `RiqiProvenancePanel.jsx` | Zone-level RIQI scores with data source tracking |
| 🔔 Notifications | `NotificationPreviewPanel.jsx` | Multilingual notification preview + test |
| 🔮 Social Oracle | `SocialOraclePanel.jsx` | NLP verification engine (paste text → real API cross-check) |
| 💰 Payments | `PaymentReconciliationPanel.jsx` | Payment reconciliation + premium collection |
| 🧠 Intelligence | `InsurerIntelligencePanel.jsx` | Disruption predictions, risk profiles, trends |
| 📊 Aggregation | `AggregationPanel.jsx` | Multi-trigger event resolution & overlap handling |
| 🎬 Demo Mode | `DemoModeScenarioPanel.jsx` | Scenario-based simulation with instant replay |
| ⏱️ Instant Replay | `InstantReplayPanel.jsx` | Replay historical scenarios (monsoon, AQI crisis, fraud) |
| 📈 Impact Analysis | `ImpactPanel.jsx` | Drill impact metrics (claims, payouts, engagement) |
| 🔧 System Settings | `SettingsPanel.jsx` | Runtime configuration & feature toggles |
| 📉 Partial Disruption | `PartialDisruptionPanel.jsx` | Simulate disruptions affecting zone subsets |
| 💳 Premium Collection | `PremiumCollectionPanel.jsx` | Premium revenue & collection analytics |

---

## 👤 Partner Experience

### Pages & Flows

| Route | Page | Description |
|-------|------|-------------|
| `/onboarding` | `OnboardingFlow.jsx` | Guided onboarding — eligibility, shift selection, plan cards |
| `/register` | `Register.jsx` | Partner registration with Zepto/Blinkit ID validation |
| `/login` | `Login.jsx` | OTP-based authentication |
| `/dashboard` | `Dashboard.jsx` | Coverage status, earnings protected, payout history, streak |
| `/policy` | `Policy.jsx` | Policy details, renewal, certificate PDF |
| `/claims` | `Claims.jsx` | Claim history and status tracking |
| `/trust-center` | `TrustCenter.jsx` | Transparency — how claims are validated |
| `/profile` | `Profile.jsx` | Partner profile management |
| `/admin` | `Admin.jsx` | Full admin dashboard (no Layout wrapper) |

### Key Components

- **`ProofCard.jsx`** — Visual proof of each validation step
- **`StressWidget.jsx`** — Actuarial stress scenario visualization
- **`RapidBot.jsx`** — AI-powered support chatbot (Groq integration)
- **`ReassignmentCountdown.jsx`** — Live countdown for zone reassignment acceptance
- **`UpiSelector.jsx`** — UPI app selection with deep links
- **`TermsModal.jsx`** — IRDAI-compliant terms and exclusions
- **`OfflineFallbackCard.jsx`** — Offline mode graceful degradation

---

## 📡 API Reference

All endpoints are versioned under `/api/v1`. The backend exposes **18 route modules**:

| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| **Partners** | `/partners` | `POST /register`, `POST /login`, `POST /verify`, `GET /me` |
| **Experience** | `/partners` | Partner experience & engagement endpoints |
| **Policies** | `/policies` | `POST /`, `GET /{id}`, `GET /quotes`, certificate generation |
| **Payments** | `/payments` | Stripe checkout, Razorpay orders, payment verification |
| **Claims** | `/claims` | `GET /`, `POST /process`, claim status tracking |
| **Zones** | `/zones` | `GET /`, `GET /nearest`, risk profiles, reassignment |
| **Triggers** | `/triggers` | Active trigger events |
| **Admin** | `/admin` | Simulation, stats, ML monitoring, partner management |
| **Admin Panel** | `/admin/panel` | Dashboard data, drill execution, BCR, stress scenarios |
| **Admin Drills** | `/admin/drills` | Drill sessions, presets, results |
| **Admin Monitoring** | `/admin/monitoring` | ML model performance metrics |
| **Notifications** | `/notifications` | Push subscription management, test notifications |
| **Social Oracle** | `/oracle` | Text verification pipeline |
| **AI Chat** | `/ai` | Groq-powered conversational assistant (RapidBot) |
| **Intelligence** | `/intelligence` | Disruption predictions, risk profiles, analytics |
| **Experience** | `/partners/experience` | Partner dashboard state, premium breakdown, eligibility |
| **WebSocket** | `/ws/claims/{partner_id}` | Real-time claim/trigger updates for admin |
| **Zone Activity** | `/zones/partners/{id}/activity` | Partner platform activity (shifts, runs, location) |
| **Drill Impact** | `/drills/{id}/impact` | Drill outcome metrics (payouts, engagement) |
| **Reconciliation** | `/payments/reconciliation` | Payment state monitoring & retry logic |
| **Collusion Check** | `/admin/fraud-queue/collusion-check` | Device fingerprint & IP clustering analysis |

### Health & Monitoring

```
GET /         → Service info + version
GET /health   → Component health: database, external APIs, demo mode status
GET /docs     → Interactive Swagger UI (auto-generated OpenAPI 3.0)
```

---

## 🚀 Installation & Setup

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| PostgreSQL (recommended) | 15+ |
| Redis (optional) | 7+ |

### Option A: PostgreSQL (Recommended)

```powershell
# 1. Start PostgreSQL via Docker
docker run --name rapidcover-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rapidcover \
  -p 5432:5432 -d postgres:15-alpine

# 2. Backend setup
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env → set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rapidcover

# 4. Start backend
python -m uvicorn app.main:app --reload

# 5. Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Option B: SQLite (Quick Start)

```powershell
# Backend (no Docker needed — SQLite is the default)
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend App | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Admin Panel | http://localhost:5173/admin |

---

## ⚙️ Environment Variables

Create `backend/.env` from `backend/.env.example`:

| Key | Description | Default / Example |
|-----|-------------|-------------------|
| `DATABASE_URL` | SQLite or PostgreSQL URI | `sqlite:///./rapidcover.db` |
| `REDIS_URL` | Redis connection (optional) | `redis://localhost:6379/0` |
| `JWT_SECRET` | Secret for token signing | `your-secret-key` |
| `OPENWEATHERMAP_API_KEY` | OpenWeatherMap free tier key | `your-owm-key` |
| `WAQI_API_KEY` | WAQI / aqicn.org API key | `your-waqi-key` |
| `CPCB_API_KEY` | CPCB AQI API key | `your-cpcb-key` |
| `NEWS_API_KEY` | NewsAPI key (civic disruptions) | `your-news-key` |
| `RAZORPAY_KEY_ID` | Razorpay test mode key | `rzp_test_xxxxx` |
| `RAZORPAY_KEY_SECRET` | Razorpay test secret | `xxxxx` |
| `STRIPE_SECRET_KEY` | Stripe test secret key | `sk_test_xxxxx` |
| `GROQ_API_KEY` | Groq AI chat API key | `your-groq-key` |
| `VAPID_PUBLIC_KEY` | Web Push VAPID public key | (generate with `npx web-push generate-vapid-keys`) |
| `VAPID_PRIVATE_KEY` | Web Push VAPID private key | (see above) |
| `AUTO_PAYOUT_ENABLED` | Enable zero-touch auto-payout | `false` |
| `DEMO_MODE` | Use mock data instead of live APIs | `false` |
| `SENTRY_DSN` | Sentry error tracking (optional) | `` |
| `ENVIRONMENT` | `development` or `production` | `development` |

> **Note:** The system gracefully degrades when API keys are missing — it falls back to mock data with clear logging.

---

## 🧪 Running the Demo

### Admin Simulation

1. Open the **Admin Dashboard** at `/admin`
2. Navigate to the **Demo Mode** tab
3. Select a scenario (e.g., "Heavy Rain in Bellandur")
4. Watch the trigger engine detect the event, run the 10-check validation, compute fraud scores, and dispatch payouts — all in real-time

### Drill Execution

1. Go to the **Drills** tab in the Admin Dashboard
2. Select one of 10 presets (Monsoon Flood, Heatwave, AQI Crisis, etc.)
3. Execute the drill and observe the timeline of events
4. Review results in the **Trigger Proof** tab

### PWA Installation (Android)

1. Open the deployed URL in **Google Chrome** on Android
2. Tap the three-dot menu (⋮) → **"Install app"**
3. Launch from home screen for native-like push notifications

---

## 🧪 Testing

### Backend (pytest)

```powershell
cd backend
python -m pytest tests/ -v
```

**24 test suites** covering:

| Suite | Coverage |
|-------|----------|
| `test_phase2_tasks.py` | Full Phase 2 feature validation (31 KB) |
| `test_trust_apis.py` | Trust Center API integration (32 KB) |
| `test_drills.py` | Drill execution engine (23 KB) |
| `test_ml_stability.py` | ML model determinism & drift detection |
| `test_partner_experience.py` | Partner onboarding & engagement flows |
| `test_payment_reconciliation.py` | Payment state machine & recovery |
| `test_platform_activity_simulation.py` | Platform activity validation |
| `test_validation_matrix.py` | 10-check validation matrix correctness |
| `test_multi_trigger_resolver.py` | Overlapping event arbitration |
| `test_oracle_reliability.py` | Social Oracle NLP accuracy |
| `test_notification_templates.py` | Multilingual template rendering |
| `test_partial_disruption.py` | Partial disruption payout logic |
| `test_riqi_provenance.py` | RIQI score data source tracking |
| `test_stress_scenarios.py` | Actuarial stress scenario modeling |
| `test_zone_reassignment_flow.py` | 24hr zone reassignment state machine |
| `test_trigger_pincode_strictness.py` | Pin-code level trigger precision |
| `test_demo_mode_scenarios.py` | Demo mode simulation |
| ... | 7 more suites |

### Frontend (Vitest)

```powershell
cd frontend
npm run test            # Run all tests
npm run test:watch      # Watch mode
npm run test:ui         # Interactive UI
```

---

## 📐 Actuarial Model

### Key Assumptions

| Parameter | Value | Basis |
|-----------|-------|-------|
| Target Loss Ratio | 58–65% | Global parametric benchmark (Swiss Re) |
| Disruptions per partner per year | 18–24 days | IMD event frequency (top 10 cities, 2019–2024) |
| Average claim payout per event | ₹380 | Blended across all tiers |
| Claim frequency per policy per week | 0.09 | ~1 claim per 11 weeks |
| Expense ratio | 22% | Zero-CAC B2B distribution model |

### Claims Reserve Methodology

Rolling IBNR reserve using adapted Bornhuetter-Ferguson method:

```
Weekly Reserve = (Active Policies × Claim Frequency × Avg Payout)
              + IBNR Buffer (15%)
              + Catastrophe Reserve (5% of gross premium)

Example (10,000 policies, Standard tier):
  Base liability:    10,000 × 0.09 × ₹380     = ₹3,42,000 / week
  IBNR buffer (15%): ₹3,42,000 × 0.15         = ₹51,300
  Cat reserve (5%):  (10,000 × ₹59) × 0.05    = ₹29,500
  ──────────────────────────────────────────────
  Total weekly reserve:                        = ₹4,22,800
```

### Correlation Risk

City-level payout cap at 120% of that city's weekly premium pool (standard parametric practice per Caribbean CCRIF model). Above threshold, proportional reduction applies — disclosed at onboarding.

---

## 🚫 Exclusions

RapidCover is a **parametric income protection product** with strictly defined scope. Full exclusions are presented to every partner at onboarding (`ExclusionsCard.jsx` + `TermsModal.jsx`):

| Category | Details |
|----------|---------|
| War & Armed Conflict | War, invasion, armed insurgency, terrorism |
| Pandemic / Epidemic | Government-declared public health emergencies |
| Nuclear Events | Nuclear reaction, radiation, contamination |
| Government Policy | Regulatory changes, GST shifts, commission restructuring |
| Platform Operations | Scheduled maintenance, algorithm changes |
| Self-Inflicted Loss | Voluntary offline, account suspension |
| Health / Accident / Life | Strictly excluded — not a health/life product |
| Vehicle Damage | Bike, scooter, repair costs |
| Disruptions < 45 Min | De minimis threshold |
| Claims After 48 Hours | Stale claim prevention |

---

## 📈 Business Viability

| Metric | Value | Basis |
|--------|-------|-------|
| Q-Commerce delivery partners | 500,000+ | Zepto + Blinkit headcounts |
| Avg disruption days per year | 18–24 | IMD top 10 cities |
| Willingness to pay | ₹22–45/week | <1% of weekly earnings |
| Year 1 target (BLR + MUM + DEL) | 25,000 partners | Metro pilot |
| Year 1 gross premium | ₹4.33 Cr | 25,000 × ₹33 avg × 52 weeks |
| Target loss ratio | 55–70% (BCR) | Parametric global benchmark |

**Strategic Moat:** RapidCover generates India's first structured dark-store-zone disruption dataset — suspension frequency, duration, road conditions, zone-level risk scores. Data that Zepto and Blinkit don't have. That is the B2B licensing opportunity that outlasts the insurance product.

**Distribution:** One B2B integration with Zepto's partner app → 100,000+ workers onboarded via a single WhatsApp link. Marginal CAC = ₹0.

---

## 👥 Team

RapidCover was built by the team at Guidewire DEVTrails 2026:

- **[Anaswara K](https://github.com/Anaswarakorangot)**
- **[Venakta Kanna Bhavan Surya Adapa](https://github.com/avkbsurya119)**
- **[Yuva Hasini Duddekunta](https://github.com/Yuvahasini)**
- **[Amritha](https://github.com/amrithasnidhi)**

---

## 🤝 Contributing

We welcome contributions. Please follow these steps:

1. **Fork** the repository
2. **Create a branch** (`git checkout -b feature/your-feature`)
3. **Commit** your changes with descriptive messages
4. **Push** to your fork and open a **Pull Request**

### Development Guidelines

- Backend: Follow PEP 8. Add tests for new services in `backend/tests/`.
- Frontend: Use existing component patterns. Run `npm run lint` before committing.
- ML: Document model changes in `ml_models/model_metadata.json`.
- All API changes must include OpenAPI schema updates (auto-generated by FastAPI).

---

## 📄 License

This project was built for the **Guidewire DEVTrails 2026 Hackathon**. License terms are pending finalization.

---

<div align="center">

*"Insurance has always been designed for people with bank accounts, salaries, and time to file paperwork.*
*RapidCover is designed for people with a bike, a phone, and 10 minutes between runs."*

<br/>

**RapidCover — Because Manoj's EMI doesn't pause for the rain.**

<br/>

*Built for Guidewire DEVTrails 2026*

</div>