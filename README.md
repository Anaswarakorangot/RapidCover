<div align="center">

# 📘 [➡️ Phase 2 Additions — Click Here for Full Details](./PHASE2_README.md)

> **Phase 2 adds 25+ production-grade features:** multi-trigger arbitration, 7-factor fraud model, RIQI urban/rural scoring, zone reassignment, 6 actuarial stress scenarios, social oracle verification, 10-check validation matrix, and a 15-tab admin dashboard.

---

# 🛵 RapidCover
### *Parametric Income Intelligence for India's Q-Commerce Last-Mile Warriors*

[🚀 Live Demo (Render/Railway)](https://rapidcover.onrender.com) &nbsp; | &nbsp; [📽️ Pitch Video](https://youtube.com/rapidcover) &nbsp; | &nbsp; [📘 Phase 2 Features](./PHASE2_README.md)

<br/>

> **"Last month, a flash flood hit my dark store zone at 6 PM — peak hour. Zepto suspended the entire zone. I sat outside the dark store for 3 hours waiting. Zero runs. Zero income. Nobody called. Nobody compensated. I just went home."**
>
> *— Manoj, 24, Zepto Delivery Partner, Bellandur, Bangalore*

<br/>

![Platform](https://img.shields.io/badge/Platform-Mobile%20App%20(PWA)-8B2FC9?style=for-the-badge)
![Persona](https://img.shields.io/badge/Persona-Q--Commerce%20%7C%20Zepto%20%2F%20Blinkit-FF6B35?style=for-the-badge)
![Hackathon](https://img.shields.io/badge/Guidewire-DEVTrails%202026-232F3E?style=for-the-badge)
![Insurance Type](https://img.shields.io/badge/Insurance-Parametric%20Income%20Protection-00B894?style=for-the-badge)
![Coverage](https://img.shields.io/badge/Coverage-Income%20Loss%20ONLY-E74C3C?style=for-the-badge)
![Phase](https://img.shields.io/badge/Phase-2%20Complete-00B894?style=for-the-badge)

<br/>

---

</div>

## 📌 Table of Contents

0. [**📘 Phase 2 Features (Separate Document)**](./PHASE2_README.md)
1. [The Problem We're Solving](#-the-problem-were-solving)
2. [Meet Our Persona — Manoj](#-meet-our-persona--manoj)
3. [What RapidCover Is](#-what-rapidcover-is)
4. [Why Mobile App (PWA)](#-why-mobile-app-pwa)
5. [Weekly Premium Model](#-weekly-premium-model)
6. [Parametric Triggers](#-parametric-triggers)
7. [What RapidCover Does NOT Cover](#-what-rapidcover-does-not-cover--standard-exclusions)
8. [AI/ML Integration Plan](#-aiml-integration-plan)
9. [Fraud Detection Architecture](#-fraud-detection-architecture)
10. [Application Workflow](#-application-workflow)
11. [Analytics Dashboard](#-analytics-dashboard)
12. [Tech Stack & Architecture](#-tech-stack--architecture)
13. [Actuarial Model](#-actuarial-model--financial-viability--pricing-basis)
14. [Phase 2 Features Summary](#-phase-2-features-summary)
15. [Development Plan](#-development-plan)
16. [Quick Start (One-Command Setup)](#-quick-start)
17. [Environment Variables](#-environment-variables)
18. [Running the Demo](#-running-the-simulation-demo)
19. [Installation on Mobile](#-pwa-installation-on-android)
20. [Business Viability](#-business-viability)

---

## 💔 The Problem We're Solving

India's Q-Commerce boom — Zepto's 10-minute delivery promise, Blinkit's dark store model — runs on **500,000+ hyper-local delivery partners**. These workers earn per run, per shift. No work = no pay.

When an external disruption hits a Q-Commerce worker, the loss is not gradual — it is instant and total:

```
Dark Store Suspended → Worker has NO other pickup point → Income = ₹0
```

| Event | Duration | Avg Income Lost | Current Compensation |
|-------|----------|----------------|---------------------|
| Flash flood (zone-level) | 4–8 hours | ₹400–₹700 | ₹0 |
| Cyclone warning suspension | 2–4 days | ₹2,000–₹4,000 | ₹0 |
| Extreme heat advisory | 6–10 hours | ₹500–₹900 | ₹0 |
| Dangerous AQI breach | 3–6 hours | ₹250–₹500 | ₹0 |
| Curfew / Section 144 | 1–3 days | ₹800–₹2,400 | ₹0 |

No bank product covers this. No platform compensates for it. **RapidCover does — automatically, in under 10 minutes.**

---

## 👤 Meet Our Persona — Manoj

**Manoj, 24. Zepto Delivery Partner. Bellandur, Bangalore.**

- Works 6 days a week, 8–10 hours/day at the Bellandur dark store (Zone BLR-047)
- Earns ₹700–₹900/day — 10–15 runs/hour during peak
- EMI on his bike. Sends ₹4,000 home monthly to Tumkur
- Uses a Redmi Note 12. Lives inside WhatsApp, GPay, and the Zepto partner app
- Last monsoon: 3 zone suspensions in 6 weeks. Lost ₹6,400. Borrowed from his cousin

**What Manoj needs:** Pay a small weekly amount and never think about insurance again. When Zepto suspends his zone — money should just arrive on his phone.

**What RapidCover delivers:** ₹33/week (Standard tier). Rain detected → zone suspension confirmed → 10-check validation matrix → UPI credit in 49 seconds. Manoj did nothing. Money arrived on his lock screen.

---

## 🛡️ What RapidCover Is

RapidCover is a **weekly parametric income insurance platform** built exclusively for Zepto and Blinkit delivery partners.

**Strictly covers income loss only.** No health. No vehicle. No accidents. No life insurance.

```
TRADITIONAL INSURANCE:
Event happens → Worker files claim → Adjuster reviews → 7–21 days → Maybe payout

RAPIDCOVER PARAMETRIC:
Event happens → APIs detect it → System validates → Push notification + UPI credit → 8 minutes
                                                      Worker did absolutely nothing
```

---

## 📱 Why Mobile App (PWA)

Manoj is on a bike. Never at a desk. The core promise — *"money just arrives"* — requires a push notification on his lock screen. A web app cannot do this reliably.

| Moment | Web App | Mobile PWA |
|--------|---------|------------|
| Disruption alert — notify instantly | ❌ Needs browser open | ✅ Push to lock screen |
| Payout confirmation | ❌ Must open browser | ✅ Appears on lock screen |
| Onboarding in a 3-min tea break | ❌ Awkward on phone browser | ✅ Native smooth flow |
| GPS zone validation | ❌ Browser GPS unreliable | ✅ Native GPS, accurate |
| UPI deep link for payment | ❌ Clunky mobile browser redirect | ✅ Opens GPay/PhonePe directly |
| Weekly premium reminder | ❌ No reliable mechanism | ✅ Scheduled push notification |

**Why PWA over native Android:** Installs on any Android device from a single WhatsApp link — no app store, no approval wait. Same React codebase, real push notifications, native GPS, UPI deep links. This mirrors exactly how Zepto onboards its own partners today.

---

## 💰 Weekly Premium Model

Gig workers earn weekly, spend weekly, plan weekly. RapidCover is priced to match.

### Base Tiers (Aligned to Guidewire Spec: ₹20–50/week range)

| Tier | Weekly Premium | Max Payout / Day | Max Days / Week | Max Weekly | Ratio |
|------|---------------|-----------------|-----------------|------------|-------|
| ⚡ **Flex** (Part-time) | ₹22/week | ₹250 | 2 days | ₹500 | ~1:23 |
| 🛵 **Standard** (Full-time) | ₹33/week | ₹400 | 3 days | ₹1,200 | ~1:36 |
| 🏆 **Pro** (Peak rider) | ₹45/week | ₹500 | 4 days | ₹2,000 | ~1:44 |

### Underwriting Gates (Phase 2)

- **Minimum 7 active delivery days** in last 30 before cover starts
- **Auto-downgrade to Flex** if < 5 active days in last 30 (cannot self-select Standard/Pro)
- Worker on leave / voluntarily offline → no payout even if trigger fires

### ML Dynamic Pricing Layer (7-Factor Formula)

Every partner gets a personalized weekly quote every Monday from our gradient-boosted regression model:

```
PERSONALIZED WEEKLY PREMIUM =
  Base Tier Price
  × City Peril Multiplier             (city-specific, per Guidewire formula)
  × Zone Risk Score Multiplier        (0.8–1.4, pin-code level RIQI score)
  × Seasonal Disruption Index         (city-specific monthly: BLR +20% Jun-Sep, DEL +18% Oct-Jan)
  × RIQI Adjustment                   (urban=1.0, fringe=1.15, peri-urban=1.3)
  × Activity Tier Factor              (Flex=0.8, Standard=1.0, Pro=1.35)
  × Partner Active Hours Factor       (more hours = more exposure)
  × Loyalty Discount                  (−6% after 4 clean weeks, −10% after 12 weeks)
  Capped at 3× base tier (IRDAI microinsurance cap)
```

**Example:** Manoj (Bellandur, RIQI 48, flood-prone, 10 hrs/day, July) → ₹48/week. Ravi (Whitefield, RIQI 55, low-risk, 6 hrs/day, January) → ₹33/week. Same product. Fair price. Transparent breakdown shown every Monday.

### Why Weekly Works
- Zepto pays partners weekly — premium aligns with earnings
- ₹33/week = ₹4.70/day = less than one chai
- 48-hour grace period on missed payment before lapse
- Auto-renews every Monday 6 AM via UPI auto-debit

---

## ⚡ Parametric Triggers

5 conditions that automatically fire a payout. No claim form. No human review.

### Trigger 1: Heavy Rain / Flood
```
Source     : OpenWeatherMap API + IMD district advisory + Mock road condition API
Threshold  : Rainfall > 55mm/hr sustained 30+ mins in dark store pin code
             OR IMD orange/red alert issued for district
Validation : Zone polygon match + Zepto mock ops suspension confirmed
             + Traffic mock API confirms road access disruption
             + Partner GPS active in zone during window
Payout     : Proportional to disruption hours × hourly earning baseline
```

### Trigger 2: Extreme Heat
```
Source     : OpenWeatherMap API + IMD heat wave bulletin
Threshold  : Temperature > 43°C sustained 4+ hours in zone
             OR State govt issues outdoor work restriction advisory
Validation : Zone-level temp confirmed at dark store location + Partner GPS in zone
Payout     : Full disruption window up to daily maximum
```

### Trigger 3: Dangerous AQI
```
Source     : CPCB open data API + aqicn.org (free tier)
Threshold  : AQI > 400 (Severe) in partner's zone for 3+ hours
             OR Govt issues outdoor work restriction
Validation : Station-level AQI at nearest monitor to dark store + zone polygon check
Payout     : Hours of breach × hourly earning rate
```

### Trigger 4: Civic Shutdown / Curfew / Bandh
```
Source     : Mock civic alert feed + NLP on news headlines (NewsAPI)
             + Mock traffic / road blockade feed
Threshold  : Official curfew, Section 144, or bandh in delivery zone for 2+ hours
Validation : Zone boundary check + Traffic mock confirms road blockades
             + Cross-reference with public authority announcements
Payout     : Full income coverage for shutdown duration
```

### Trigger 5: Dark Store Force Majeure Closure
```
Source     : Mock Zepto / Blinkit operational status API + Mock traffic feed
Threshold  : Assigned dark store closed > 90 mins due to external event
             (not scheduled maintenance)
Validation : Platform-side closure log verified (timestamped)
             + Partner had active shift + Traffic mock confirms access disruption
Payout     : Full shift income covered
Note       : Most Q-Commerce-specific trigger in existence — unique to RapidCover
```

### Validation Pipeline (Every Claim — 10-Check Matrix, Phase 2)
```
[1. Source threshold breach confirmed]  → [2. Zone polygon match]
       ↓
[3. Pin-code / ward match]  → [4. Active policy confirmed]
       ↓
[5. Shift-window check]  → [6. Partner activity (not offline/leave)]
       ↓
[7. Platform activity confirmed]  → [8. 7-Factor Fraud Score < 0.90?]
       ↓
[9. Data freshness check]  → [10. Cross-source agreement (Oracle)]
       ↓
[Payout Calculated + RIQI Multiplier]  → [Zone Pool Share Cap Applied]
       ↓
[Razorpay UPI Credit]  → [Push Notification in Partner's Language]
```

---

## 🚫 What RapidCover Does NOT Cover — Standard Exclusions

RapidCover is a **parametric income protection product** with a strictly defined scope. The following are permanently excluded from coverage, in alignment with IRDAI guidelines and standard parametric insurance practice.

> These exclusions are non-negotiable and are presented to every partner at onboarding before policy activation. A dedicated "What's not covered" screen is shown before the first premium is collected.

### Excluded Events

| Exclusion Category | Details |
|--------------------|---------|
| **War & Armed Conflict** | Loss of income caused by war, invasion, civil war, military coup, armed insurgency, or terrorism — whether declared or undeclared |
| **Pandemic / Epidemic Declaration** | National or state government-declared public health emergencies (e.g. COVID-19 type lockdowns). Routine disease outbreaks not classified as emergencies are NOT excluded |
| **Nuclear & Radioactive Events** | Any disruption arising from nuclear reaction, radiation, or radioactive contamination |
| **Government Policy Changes** | Income loss caused by regulatory changes, GST/policy shifts, or platform-level policy decisions (e.g. commission restructuring) |
| **Platform Operational Decisions** | Planned maintenance, scheduled downtimes, algorithm changes, surge pricing removal, or voluntary platform shutdowns unrelated to an external disruption event |
| **Self-Inflicted / Voluntary Loss** | Worker voluntarily going offline, account suspension due to partner-side violations, deliberate avoidance of runs |
| **Health, Accident & Life** | Any medical expenses, hospitalisation, disability, or death — strictly excluded. RapidCover is NOT a health or life insurance product |
| **Vehicle Damage & Repair** | Bike, scooter, or vehicle damage, repair costs, fuel costs, or any mobility-related expense — strictly excluded |
| **Financial Market Events** | Currency devaluation, fuel price spikes, or inflation-driven earning reductions |
| **Disruptions Under 45 Minutes** | De minimis threshold — events resolving within 45 minutes do not qualify for a payout to prevent micro-claim abuse |
| **Claims Filed After 48 Hours** | Any claim submission or trigger validation attempted more than 48 hours after the disruption event window closes |
| **Collateral or Consequential Loss** | Any indirect loss beyond the verified income window (e.g. loss of tip income, future earning projections, reputational impact) |

### Why These Exclusions Exist

These exclusions serve three purposes:

1. **Regulatory alignment** — IRDAI requires parametric products to define triggers and exclusions with precision. Ambiguous exclusions create claims disputes that defeat the zero-touch model.
2. **Product integrity** — RapidCover's promise is *automatic payout for verifiable external disruptions*. Events that cannot be objectively verified via API (war, self-infliction) cannot participate in the parametric model.
3. **Financial sustainability** — Catastrophic or correlated risks (pandemic, war) are uninsurable at the individual policy level without reinsurance treaty support. Including them would make the product non-viable.

### ℹ️ What About Accidents & Health?

If Manoj gets into an accident while delivering, RapidCover does not cover this. However, he is not unprotected:

| Coverage Type | Product | Cost |
|--------------|---------|------|
| Accidental death / disability | PM Suraksha Bima Yojana | ₹20/year |
| Life cover | PM Jeevan Jyoti Bima Yojana | ₹436/year |
| Accident during active delivery | Zepto / Blinkit platform insurance | ₹0 (included) |

RapidCover is designed to complement — not replace — these products.

---

## 🤖 AI/ML Integration Plan

Four models — each solving a distinct business problem. AI is load-bearing, not decorative.

### Model 1 — Zone Risk Scorer
```
Purpose   : Risk score (0–100) per dark store zone at onboarding
Algorithm : XGBoost Classifier
Features  : 2-yr IMD rainfall, CPCB AQI history, NDMA flood maps,
            dark store suspension history, OSM road infrastructure,
            historical traffic blockade frequency
Output    : Zone Risk Score with plain-language explanation shown to partner
Training  : Public IMD + CPCB + NDMA + OSM datasets (all free)
```

### Model 2 — Dynamic Premium Engine
```
Purpose   : Personalized weekly premium every Monday per partner
Algorithm : Gradient Boosted Regression (scikit-learn)
Features  : Zone Risk Score, active hours, season index, AQI trend,
            road condition risk, claim history, dark store suspension frequency
Output    : Weekly premium in ₹ with itemized breakdown in app
Retrain   : Weekly with new disruption + claim data
```

### Model 3 — Fraud Anomaly Detector
```
Purpose   : Fraud score per claim before payout release
Algorithm : Isolation Forest (unsupervised) + deterministic rule layer
Features  : GPS trajectory coherence, run count during disruption,
            zone match, claim frequency, device fingerprint, traffic cross-check
Output    : Fraud score 0–1
            < 0.50  → Auto-approve
            0.50–0.75 → Enhanced validation
            0.75–0.90 → Manual review queue
            > 0.90  → Auto-reject with explanation to partner
Baseline  : 60-day rolling partner behavior window
```

### Model 4 — Disruption Predictor (Admin)
```
Purpose   : Forecast next week's claim liability for insurers
Algorithm : LSTM on weather + traffic time series
Features  : IMD 7-day forecast, historical claim patterns, AQI trend,
            traffic disruption history, civic event calendar
Output    : Expected payout liability (₹) per zone — shown every Sunday evening
```

---

## 🔍 Fraud Detection Architecture (7-Factor Model — Phase 2 Upgrade)

Seven weighted factors with hard reject rules. Upgraded from Phase 1's 6-factor model.

### 7-Factor Weighted Fraud Score
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

### Attack Vectors with Detection

| Attack Vector | How It's Attempted | RapidCover Detection |
|--------------|-------------------|---------------------|
| GPS Spoofing | Fake location in suspended zone | Velocity physics check — >60 km/h between pings = spoof; centroid drift detection |
| Activity Paradox | Claim disruption while completing runs | `run_count > 0` during window → **hard reject** (w2) |
| Zone Boundary Gaming | Register high-risk zone, operate in safe zone | **30-day GPS centroid** must stay within 15km of declared dark store (w7) |
| Duplicate Event Claiming | Claim same disruption twice | Cryptographic event ID per trigger — duplicate → hard DB reject |
| Collusion Ring | Multiple fake partners, same device/network | Device fingerprint + IP clustering; shared devices flagged (w5) |
| Synthetic Identity | Fabricated Zepto partner IDs | Partner ID validated via mock API + Aadhaar KYC + face liveness at onboarding |
| Centroid Drift | GPS suddenly appears in new zone | **30-day centroid drift** > 15km = auto-flag for manual review (w7, Phase 2) |

> **Double Indemnity:** Policy is Aadhaar-linked, not platform-linked. Payouts capped at verified weekly earning baseline. We recommend IRDAI establish a **Gig Worker Parametric Claims Registry** — RapidCover is architected to plug in from day one.

---

## 🔄 Application Workflow

```
┌──────────────────────────────────────────────────────────────┐
│        ONBOARDING FLOW  (Under 3 minutes, Phase 2)           │
│                                                              │
│  Install PWA via WhatsApp link → OTP Login                   │
│  → Zepto Partner ID Validation → KYC Lite (Aadhaar + Face)  │
│  → GPS detects Dark Store Zone + RIQI Score                  │
│  → Eligibility Check (7 active days in last 30?)             │
│  → Shift Window Selection (active hours + days)              │
│  → 3 personalised plan cards with RIQI-adjusted premium      │
│  → UPI linked → Language set → Push permission granted       │
│  → ✅ POLICY ACTIVE immediately                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    WEEKLY RENEWAL FLOW                       │
│                                                              │
│  Every Monday 6 AM:                                          │
│  ML recalculates premium (7-factor formula)                  │
│  → Push notification to lock screen                          │
│  → UPI auto-debit → Home screen shows ✅ Coverage Active     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│         ZERO-TOUCH CLAIM FLOW  (11-Step, Phase 2)            │
│                                                              │
│  1. Trigger detected (ward-level threshold breach)           │
│  2. Active shift check — is partner in declared window?      │
│  3. Zone polygon match (Turf.js)                             │
│  4. Platform suspension confirmed (mock ops API)             │
│  5. Traffic cross-check (road disruption confirmed)          │
│  6. GPS coherence + centroid drift check                     │
│  7. Run count = 0 during disruption window                   │
│  8. 7-Factor fraud score computed                            │
│  9. Payout calculated (RIQI multiplier + zone pool cap)      │
│  10. UPI credit via Razorpay mock                            │
│  11. Push notification in partner's language                 │
│                                                              │
│  Partner action required : ZERO                              │
│  Trigger to money in wallet : ~49 seconds                    │
└──────────────────────────────────────────────────────────────┘
```

### The Zero-Touch Experience — Live

> **Wednesday 5:47 PM, Bellandur.** IMD: 72mm/hr. OpenWeatherMap confirms. Traffic mock API: 2 of 3 zone access roads waterlogged.
>
> **5:47:23** — Zone BLR-BEL polygon match confirmed. RIQI: 48 (peri-urban fringe).
> **5:47:25** — Shift window check: Manoj active Mon-Sat 8AM-10PM. ✅ In window.
> **5:47:28** — Pin-code match: 560103 ∈ BLR-BEL coverage. ✅
> **5:47:31** — Zepto mock ops: Zone suspended. Logged.
> **5:47:35** — Platform activity: logged in, 4 orders completed, dwell 60min. ✅
> **5:47:39** — Traffic cross-validation passed.
> **5:47:44** — GPS: 200m from dark store. Centroid drift: 0.2km (< 15km limit). ✅
> **5:47:51** — Run count: 0. Activity Paradox clear. ✅
> **5:47:54** — 7-Factor fraud score: 0.11. Auto-approve.
> **5:47:58** — Validation matrix: 10/10 checks passed. Confidence: 0.95.
> **5:48:02** — Payout: ₹272 × 1.25 RIQI multiplier = ₹340.
> **5:48:09** — ₹340 UPI credit via Razorpay mock.
> **5:48:12** — Lock screen in Kannada: *"ನಿಮ್ಮ ಜೋನ್‌ನಲ್ಲಿ ಭಾರೀ ಮಳೆ ಪತ್ತೆಯಾಗಿದೆ. ₹340 ನಿಮ್ಮ UPI ಗೆ ಜಮಾ ಆಗಿದೆ. ಸುರಕ್ಷಿತವಾಗಿರಿ, ಮನೋಜ್."*
>
> **Manoj did nothing. Total time: 49 seconds.**

---

## 📊 Analytics Dashboard

### Worker Dashboard
- Coverage status banner — Active ✅ (green) / Grace Period (orange) / Expired (red)
- Earnings protected counter — total payouts received since joining
- This week: premium paid, max payout available, disruption days remaining
- Last 4 payouts — trigger type, date, amount, duration
- Streak counter — clean weeks with progress to loyalty discount (4 weeks / 12 weeks)
- Zone risk score with RIQI band + plain-language explanation
- 48-hour weather alert — proactive push if IMD forecasts disruption in zone
- Renewal countdown — days until Monday 6AM auto-renewal
- Zone reassignment countdown — if proposal pending, shows hours remaining

### Insurer / Admin Dashboard (15 Tabs — Phase 2)

| Tab | Purpose |
|-----|--------|
| 📊 Overview | Key metrics, active policies, payout flow |
| 📉 BCR / Loss Ratio | City-level BCR with 85% suspension toggle |
| 🗺️ Zone Map | Live zone map with density + trigger overlay |
| 🔍 Fraud Queue | Pending claims with one-click approve/reject/bulk-reject |
| 🎯 Drills | Structured drill execution with 10 presets + 5 stress scenarios |
| 📡 Live API Data | Real-time weather/AQI/traffic readings per zone |
| 🔍 Verification | 9-component system health check |
| ⚡ Stress Proof | 14-day monsoon stress scenario + reserve calculation |
| 🔄 Reassignments | Zone reassignment queue management |
| 🎯 Trigger Proof | 10-check validation matrix visualization per claim |
| 📊 RIQI Provenance | Zone-level RIQI scores with data source tracking |
| 🔔 Notifications | Multilingual notification preview + test |
| ✅ Demo Checklist | Judging criteria verification checklist |
| 🔮 Auto-Oracle | Social media verification engine (NLP + API cross-check) |
| ⚙️ Legacy Sim | Original trigger simulation + exclusions screen |

---

## 🏗️ Tech Stack & Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     MOBILE LAYER (PWA)                           │
│   React.js + Vite — Partner App + 15-Tab Admin Dashboard         │
│   Web Push API  |  Native GPS  |  UPI Deep Links  |  EN + HI    │
└──────────────────────────────────────────────────────────────────┘
                         ↕ REST API (16 route modules)
┌──────────────────────────────────────────────────────────────────┐
│              BACKEND — Python + FastAPI (24 services)             │
│   Auth | Policy Engine | Trigger Engine | Claims Processor       │
│   Fraud Service | Payout Service | Drill Service | RIQI Service  │
│   Social Oracle | Premium Engine | Zone Reassignment | Scheduler │
└──────────────────────────────────────────────────────────────────┘
       ↕                      ↕                       ↕
┌───────────────┐  ┌─────────────────────┐  ┌──────────────────┐
│  ML SERVICE   │  │   EXTERNAL APIs     │  │  PAYMENT LAYER   │
│  GBR Premium  │  │  OpenWeatherMap     │  │  Razorpay Test   │
│  Fraud 7-Fctr │  │  WAQI/CPCB AQI      │  │  Mock UPI        │
│  Zone Risk    │  │  Mock Zepto Ops API │  └──────────────────┘
└───────────────┘  │  Mock Traffic API   │
                   │  Mock Civic API     │
                   │  Platform Activity  │
                   │  Social Oracle NLP  │
                   └─────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│         DATA — SQLite (dev) / PostgreSQL (prod)                  │
│   Policies | Claims | Triggers | Partners | Zones | Drills       │
│   Zone Risk Profiles | Zone Reassignments | Push Subscriptions   │
│   Partner Runtime Metadata | Platform Activity | Zone Coverage   │
└──────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│   NOTIFICATIONS — Web Push (VAPID) + Template Engine             │
│   English | Hindi (with fallback chain)                          │
└──────────────────────────────────────────────────────────────────┘
```

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React.js + Vite (PWA) | Android install via WhatsApp link; push notifications; native GPS; UPI deep links |
| Backend | Python + FastAPI (24 services, 16 API modules) | Async performance for real-time trigger pipeline |
| Database | SQLite (dev) / PostgreSQL (prod) | Records integrity + easy local development |
| ML | Gradient Boosted Regression + Isolation Forest (calibrated weights) | Premium pricing + 7-factor fraud detection |
| Weather | OpenWeatherMap (free tier) with mock fallback | Real-time + 7-day forecast, zone GPS-level |
| AQI | WAQI / aqicn.org + CPCB API (free) with mock fallback | Station-level Indian city data |
| Traffic | Mock road condition feed | Second-layer trigger cross-validation |
| Payments | Razorpay Test Mode + Mock UPI | Full payout demo, no real transactions |
| Notifications | Web Push (VAPID/pywebpush) + multilingual templates | Lock screen push in English + Hindi |
| Geospatial | Zone polygon matching, GPS centroid tracking | Fraud detection + zone boundary validation |
| Hosting | Railway / Render (free tier) | Zero-cost hackathon deployment |

---

## 📐 Actuarial Model — Financial Viability & Pricing Basis

RapidCover's weekly premium is not just an ML output — it is grounded in actuarial first principles. This section documents the loss model, reserve methodology, and break-even analysis that underpin the product's financial sustainability.

### Key Actuarial Assumptions

| Parameter | Value | Basis |
|-----------|-------|-------|
| Target Loss Ratio | 58–65% | Global parametric insurance benchmark (Swiss Re, 2023) |
| Expected disruption events per partner per year | 18–24 days | IMD event frequency analysis — top 10 Indian cities, 2019–2024 |
| Average income lost per disruption day | ₹420–₹720 | 8–15 runs/hr × Zepto/Blinkit per-run rates × disruption duration |
| Average claim payout per event | ₹380 | Blended across all 3 tiers and disruption types |
| Claim frequency per active policy per week | 0.09 | ~1 claim per 11 weeks per partner at full exposure |
| Expense ratio (ops + tech + distribution) | 22% | Estimate based on zero-CAC B2B distribution model |
| Profit / surplus margin | 13–20% | Residual after loss ratio + expense ratio |

### Weekly Premium Break-Even Analysis

```
MINIMUM VIABLE WEEKLY PREMIUM (Standard Tier — ₹59/week target):

Expected Weekly Payout per Policy  = Claim Frequency × Avg Payout
                                   = 0.09 × ₹380
                                   = ₹34.20

Required Premium (at 65% LR)       = ₹34.20 / 0.65
                                   = ₹52.60  ← break-even floor

Add expense ratio (22%)            = ₹52.60 / (1 - 0.22)
                                   = ₹67.40  ← fully loaded cost

Standard tier premium set at ₹59/week — below fully loaded cost intentionally
during Year 1 to drive adoption. Viable at scale with B2B distribution
eliminating marginal CAC.

PRO TIER (₹89/week):
Expected payout = 0.13 × ₹620 = ₹80.60
Required at 65% LR = ₹124 → subsidised in Year 1 at ₹89
Reaches sustainability at 10,000+ policies due to risk pooling.
```

### Loss Ratio Monitoring

RapidCover monitors loss ratio at three levels:

| Level | Frequency | Action Trigger |
|-------|-----------|----------------|
| Zone-level loss ratio | Weekly | LR > 80% in any zone → automatic premium repricing next Monday |
| City-level loss ratio | Monthly | LR > 75% city-wide → reinsurance threshold review |
| Product-level loss ratio | Quarterly | LR > 70% product-wide → IRDAI filing + pricing committee review |

### Claims Reserve Methodology

RapidCover maintains a rolling **Incurred But Not Reported (IBNR)** reserve using the Bornhuetter-Ferguson method adapted for parametric products:

```
Weekly Reserve Requirement = 
  (Active Policies × Expected Claim Frequency × Avg Payout)
  + IBNR Buffer (15% of expected weekly liability)
  + Catastrophe Reserve (5% of gross premium collected)

Example (10,000 active policies, Standard tier):
  Base liability     = 10,000 × 0.09 × ₹380     = ₹3,42,000 / week
  IBNR buffer (15%)  = ₹3,42,000 × 0.15          = ₹51,300
  Cat reserve (5%)   = (10,000 × ₹59) × 0.05     = ₹29,500
  ─────────────────────────────────────────────────────────────
  Total weekly reserve requirement                = ₹4,22,800
```

### Correlation Risk & Catastrophe Scenario

The primary risk in a Q-Commerce parametric product is **zone-level correlation** — a single flood event hitting multiple partners in the same dark store zone simultaneously.

| Scenario | Affected Partners | Estimated Payout | % of Weekly Premium Pool |
|----------|------------------|-----------------|--------------------------|
| Single zone flood (BLR-047) | 180 partners | ₹68,400 | 11.5% (manageable) |
| City-wide flood (all Bangalore zones) | 2,400 partners | ₹9,12,000 | 153% → **reinsurance trigger** |
| Multi-city cyclone (Mumbai + Chennai) | 6,000 partners | ₹22,80,000 | **Requires treaty reinsurance** |

**Mitigation:** RapidCover caps single-event city-level payouts at 120% of that city's weekly premium pool. Above this threshold, a proportional reduction applies — disclosed to partners at onboarding. This is standard parametric practice (Caribbean CCRIF model).

### Year 1 Financial Projections (Bangalore + Mumbai + Delhi Pilot)

| Quarter | Active Policies | Gross Premium | Expected Claims | Loss Ratio | Net Position |
|---------|----------------|---------------|-----------------|------------|--------------|
| Q1 | 5,000 | ₹76.7L | ₹49.8L | 65% | −₹16.9L (investment phase) |
| Q2 | 12,000 | ₹1.84Cr | ₹1.10Cr | 60% | −₹8.1L |
| Q3 | 20,000 | ₹3.07Cr | ₹1.72Cr | 56% | +₹22.3L |
| Q4 | 25,000 | ₹3.84Cr | ₹2.11Cr | 55% | +₹48.6L |
| **Year 1** | **25,000** | **₹9.11Cr** | **₹5.42Cr** | **59.5%** | **+₹45.9L** |

> Note: Year 1 operates below break-even in Q1–Q2 intentionally — standard loss leader strategy for parametric market entry. B2B distribution via Zepto integration eliminates CAC, making this viable.

---

## 🚀 Phase 2 Features Summary

> **📘 For full details on every Phase 2 feature, see [PHASE2_README.md](./PHASE2_README.md)**

Phase 2 added **25+ production-grade features** on top of the Phase 1 core:

| # | Feature | Status | Key Files |
|---|---------|--------|----------|
| 1 | Multi-Trigger Arbitration | ✅ Done | `claims_processor.py`, `trigger_engine.py` |
| 2 | 7-Factor Fraud Model (GPS centroid + velocity) | ✅ Done | `fraud_service.py`, `ml_service.py` |
| 3 | RIQI Road Infrastructure Quality Index | ✅ Done | `riqi_service.py`, `zone_risk_profile.py` |
| 4 | Underwriting Gate & Auto-Downgrade | ✅ Done | `premium_service.py` |
| 5 | Sustained Event Protocol (14-day monsoon) | ✅ Done | `premium_service.py` |
| 6 | Zone Pool Share Cap (mass event) | ✅ Done | `premium_service.py`, `claims_processor.py` |
| 7 | BCR / Loss Ratio Monitoring | ✅ Done | `premium_service.py`, `BCRPanel.jsx` |
| 8 | City-Specific Seasonal Multipliers | ✅ Done | `ml_service.py` |
| 9 | Zone Density Risk Bands | ✅ Done | `claims_processor.py`, `ZoneMapPanel.jsx` |
| 10 | Zone Reassignment (24hr state machine) | ✅ Done | `zone_reassignment_service.py` |
| 11 | 6 Actuarial Stress Scenarios | ✅ Done | `stress_scenario_service.py`, `drill_service.py` |
| 12 | Social Oracle Verification (NLP + API) | ✅ Done | `social_oracle.py`, `SocialOraclePanel.jsx` |
| 13 | Oracle Reliability & Fallback | ✅ Done | `external_apis.py`, `verification_service.py` |
| 14 | Platform Activity Simulation | ✅ Done | `claims_processor.py`, `external_apis.py` |
| 15 | 10-Check Validation Matrix | ✅ Done | `claims_processor.py`, `TriggerProofPanel.jsx` |
| 16 | Payment Reconciliation | ✅ Done | `payout_service.py` |
| 17 | Active Shift Window Check | ✅ Done | `claims_processor.py` |
| 18 | Multilingual Notifications (EN + HI) | ✅ Done | `notification_templates.py` |
| 19 | Pin-Code / Ward-Level Triggers | ✅ Done | `trigger_engine.py`, `claims_processor.py` |
| 20 | Drill Execution Engine (10 presets) | ✅ Done | `drill_service.py`, `DrillPanel.jsx` |
| 21 | System Health Verification | ✅ Done | `verification_service.py` |
| 22 | Live API Data Panel | ✅ Done | `LiveDataPanel.jsx` |
| 23 | Demo Checklist | ✅ Done | `DemoChecklist.jsx` |
| 24 | Onboarding Flow (redesigned) | ✅ Done | `OnboardingFlow.jsx` |
| 25 | Pricing Tier Alignment (₹22/33/45) | ✅ Done | `premium_service.py` |
| 26 | Exclusions Screen (IRDAI) | ✅ Done | `ExclusionsCard.jsx` |
| 27 | 15-Tab Admin Dashboard | ✅ Done | `Admin.jsx` + 20 admin components |

---

## 📅 Development Plan

### Phase 1 — Ideation & Foundation (Weeks 1–2) ✅
- [x] Persona research — Q-Commerce delivery partner income model
- [x] 5 parametric triggers designed with zone-polygon + traffic validation
- [x] Weekly premium ML model defined
- [x] 6 fraud attack vectors identified with detection architecture
- [x] Tech stack finalized — PWA with justification
- [x] README submitted

**Deliverable:** README + pitch concept

### Phase 2 — Core Product + Production Features (Weeks 3–6) ✅
- [x] PWA scaffold — Android installable, push notifications live
- [x] Partner registration, OTP login, Zepto/Blinkit ID validation
- [x] Native GPS zone detection + Zone Risk Scorer (RIQI per-zone)
- [x] Policy creation + 7-factor dynamic premium engine
- [x] All 5 triggers wired to real/mock APIs including traffic data
- [x] Zero-touch 11-step claim pipeline end-to-end
- [x] 7-factor fraud detection with centroid drift + velocity check
- [x] Razorpay test mode payout + lock screen push on claim
- [x] Worker dashboard — coverage, earnings protected, payout history, streak
- [x] 15-tab admin dashboard with BCR, fraud queue, zone map, drills
- [x] Policy lifecycle — renewal, grace period, cancellation, exclusions
- [x] Policy certificate PDF generation
- [x] Underwriting gate (7-day activity check) + auto-downgrade
- [x] Sustained event protocol (14-day monsoon, 70% payout mode)
- [x] Zone pool share cap (mass event protection)
- [x] Zone reassignment with 24hr acceptance + premium recalc
- [x] 6 actuarial stress scenarios modelled
- [x] Social Oracle (NLP + real API cross-validation)
- [x] 10-check pre-payout validation matrix
- [x] Multilingual notifications (English + Hindi)
- [x] Pin-code / ward-level trigger precision
- [x] Drill execution engine (10 presets)
- [x] 12 test suites (4,500+ lines of tests)
- [x] Onboarding flow redesigned with eligibility + shift selection

**Deliverable:** Working PWA demo + deployed URL

---

## 📈 Business Viability

| Metric | Number | Basis |
|--------|--------|-------|
| Q-Commerce delivery partners in India | 500,000+ | Zepto + Blinkit disclosed headcounts |
| Avg disruption days per partner per year | 18–24 days | IMD event frequency in top 10 cities |
| Income lost per disruption day | ₹600–₹900 | 8–15 runs/hr × peak rates |
| Annual income at risk per partner | ₹10,800–₹21,600 | 18–24 days × daily loss |
| Willingness to pay | ₹22–₹45/week | < 1% of weekly earnings |
| Year 1 target (Bangalore, Mumbai, Delhi) | 25,000 partners | Metro pilot cities |
| Year 1 gross premium | ₹4.33 Cr | 25,000 × ₹33 avg × 52 weeks |
| Target loss ratio | 55–70% (BCR 0.55–0.70) | Parametric insurance global benchmark |

**The Strategic Moat:** RapidCover generates the first-ever dark-store-zone operational disruption dataset for India's Q-Commerce network — suspension frequency, duration, road condition correlation, zone-level risk scores. Data that Zepto and Blinkit themselves don't have in structured form. That is the licensing and B2B opportunity that outlasts the insurance product.

**Distribution:** One B2B integration with Zepto's partner app = 100,000+ workers onboarded via a single WhatsApp link. Distribution cost = ₹0 marginal.

---

## 🚀 Quick Start & Development Setup

> **Production Recommendation:** The application is transitioning to a persistent, data-driven architecture. Local file-based SQLite is deprecated for development. Please use PostgreSQL.

### 1. Database Setup (PostgreSQL)
Start a local PostgreSQL instance using Docker:
```powershell
docker run --name rapidcover-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=rapidcover -p 5432:5432 -d postgres:15-alpine
```
Ensure your `backend/.env` is updated to point to this: `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rapidcover`

### 2. Application Setup
Get your local dev environment running:

```powershell
# Backend (Python 3.10+)
cd backend && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Frontend (Node.js)
cd frontend && npm install && npm run dev
```

## ⚙️ Environment Variables

Create a `.env` file in the `backend/` directory based on `.env.example`:

| Key | Description | Example |
|-----|-------------|---------|
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `postgresql://user:pass@localhost/rapidcover` |
| `JWT_SECRET` | Secret key for auth tokens | `your-secret-key-12345` |
| `OPENWEATHERMAP_API_KEY` | Key from OpenWeatherMap | `your-owm-api-key` |
| `CPCB_API_KEY` | CPCB (AQI) API key | `your-cpcb-key` |
| `AUTO_PAYOUT_ENABLED` | Toggle zero-touch automation | `true` |
| `VAPID_PUBLIC_KEY` | Web Push public key | `BNxxxxxxxx...` |
| `VAPID_PRIVATE_KEY` | Web Push private key | `xxxxxxxx...` |

## 🧪 Running the Simulation Demo

To see the parametric engine in action:

1. Log in to the **Admin Dashboard** (`/admin`).
2. Navigate to the **Trigger Sim** tab.
3. Use the sliders to force a "Heavy Rain" or "Severe AQI" event in a specific zone.
4. Watch the **Fraud Queue** or **Claims Queue** process the auto-payout in seconds.

## 📱 PWA Installation on Android Chrome

1. Open the Deployed URL in **Google Chrome** on Android.
2. Tap the **three-dot menu** (⋮) -> Select **"Install app"**.
3. Launch from your home screen for native-like push notifications.

---

<div align="center">

---

*"Insurance has always been designed for people with bank accounts, salaries, and time to file paperwork.*
*RapidCover is designed for people with a bike, a phone, and 10 minutes between runs."*

<br/>

**RapidCover — Because Manoj's EMI doesn't pause for the rain.**

---

*Built for Guidewire DEVTrails 2026*

</div>
