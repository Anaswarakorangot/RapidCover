<div align="center">

# 🛵 RapidCover
### *Parametric Income Intelligence for India's Q-Commerce Last-Mile Warriors*

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

<br/>

---

</div>

## 📌 Table of Contents

1. [The Problem We're Solving](#-the-problem-were-solving)
2. [Meet Our Persona — Manoj](#-meet-our-persona--manoj)
3. [What RapidCover Is](#-what-rapidcover-is)
4. [Why Mobile App (PWA)](#-why-mobile-app-pwa)
5. [Weekly Premium Model](#-weekly-premium-model)
6. [Parametric Triggers](#-parametric-triggers)
7. [AI/ML Integration Plan](#-aiml-integration-plan)
8. [Fraud Detection Architecture](#-fraud-detection-architecture)
9. [Application Workflow](#-application-workflow)
10. [Analytics Dashboard](#-analytics-dashboard)
11. [Tech Stack & Architecture](#-tech-stack--architecture)
12. [Development Plan — 6 Weeks](#-development-plan--6-weeks)
13. [Business Viability](#-business-viability)

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
| Dangerous AQI breach | 3–6 hours | ₹300–₹600 | ₹0 |
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

**What RapidCover delivers:** ₹59/week. Rain detected → zone suspension confirmed → UPI credit in 8 minutes. Manoj did nothing. Money arrived on his lock screen.

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

### Base Tiers

| Tier | Weekly Premium | Max Payout / Day | Max Days / Week | Best For |
|------|---------------|-----------------|-----------------|----------|
| ⚡ Flex | ₹39/week | ₹350 | 2 days | Part-time, 4–5 hrs/day |
| 🛵 Standard | ₹59/week | ₹600 | 3 days | Full-time, 8–10 hrs/day |
| 🏆 Pro | ₹89/week | ₹900 | 4 days | Peak warriors, 12+ hrs/day |

### ML Dynamic Pricing Layer

Every partner gets a personalized weekly quote every Monday from our gradient-boosted regression model:

```
PERSONALIZED WEEKLY PREMIUM =
  Base Tier Price
  × Zone Flood Risk Multiplier        (pin-code level, 2-yr IMD history)
  × Seasonal Disruption Index         (+18% monsoon, −10% winter)
  × Dark Store Suspension History     (stores with 3+ past suspensions = higher risk)
  × Partner Active Hours Factor       (more hours = more exposure)
  × AQI Trend Adjustment             (rolling 7-day CPCB average for zone)
  × Road Condition Risk Factor        (flood-prone roads in zone = higher risk)
  × Loyalty Discount                  (−6% after 4 clean weeks, −10% after 12 weeks)
```

**Example:** Manoj (Bellandur, flood-prone, 10 hrs/day, July) → ₹71/week. Ravi (Whitefield, low-risk, 6 hrs/day, January) → ₹49/week. Same product. Fair price. Transparent breakdown shown every Monday.

### Why Weekly Works
- Zepto pays partners weekly — premium aligns with earnings
- ₹59/week = ₹8.40/day = less than one chai
- 3-day grace period on missed payment before lapse
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

### Validation Pipeline (Every Claim)
```
[Trigger Detected] → [Zone Polygon Match] → [Platform Suspension Confirmed]
       ↓
[Traffic / Road Data Cross-Check] → [GPS Coherence Check]
       ↓
[Run Count Drop Confirmed] → [ML Fraud Score < 0.70?]
       ↓
[Payout Calculated] → [Razorpay UPI Credit] → [Push Notification to Lock Screen]
```

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

## 🔍 Fraud Detection Architecture

Six Q-Commerce-specific attack vectors with bespoke detection:

| Attack Vector | How It's Attempted | RapidCover Detection |
|--------------|-------------------|---------------------|
| GPS Spoofing | Fake location in suspended zone | Trajectory coherence analysis — impossible speed jumps flagged; cell tower cross-check |
| Activity Paradox | Claim disruption while completing runs | `run_count > 0` during window → hard reject |
| Zone Boundary Gaming | Register high-risk zone, operate in safe zone | 30-day GPS centroid must stay within 3km of declared dark store |
| Duplicate Event Claiming | Claim same disruption twice | Cryptographic event ID per trigger — duplicate → hard DB reject |
| Collusion Ring | Multiple fake partners, same device/network | Device fingerprint + IP clustering; >3 policies sharing 2 identifiers → flagged |
| Synthetic Identity | Fabricated Zepto partner IDs | Partner ID validated via mock API + Aadhaar KYC + face liveness at onboarding |

> **Double Indemnity:** Policy is Aadhaar-linked, not platform-linked. Payouts capped at verified weekly earning baseline. We recommend IRDAI establish a **Gig Worker Parametric Claims Registry** — RapidCover is architected to plug in from day one.

---

## 🔄 Application Workflow

```
┌──────────────────────────────────────────────────────────────┐
│              ONBOARDING FLOW  (Under 3 minutes)              │
│                                                              │
│  Install PWA via WhatsApp link → OTP Login                   │
│  → Zepto Partner ID Validation → KYC Lite (Aadhaar + Face)  │
│  → GPS detects Dark Store Zone                               │
│  → AI generates Zone Risk Score with plain explanation       │
│  → 3 personalised plan cards shown → Partner selects         │
│  → UPI linked → Language set → Push permission granted       │
│  → ✅ POLICY ACTIVE immediately                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    WEEKLY RENEWAL FLOW                       │
│                                                              │
│  Every Monday 6 AM:                                          │
│  ML recalculates premium → Push notification to lock screen  │
│  → UPI auto-debit → Home screen shows ✅ Coverage Active     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  ZERO-TOUCH CLAIM FLOW                       │
│                                                              │
│  Disruption detected → Zone + platform + traffic validated   │
│  → GPS coherence + run count drop confirmed                  │
│  → ML fraud score computed → Payout calculated               │
│  → Razorpay UPI credit → Push notification in partner's lang │
│                                                              │
│  Partner action required : ZERO                              │
│  Trigger to money in wallet : ~8 minutes                     │
└──────────────────────────────────────────────────────────────┘
```

### The Zero-Touch Experience — Live

> **Wednesday 5:47 PM, Bellandur.** IMD: 72mm/hr. OpenWeatherMap confirms. Traffic mock API: 2 of 3 zone access roads waterlogged.
>
> **5:47:23** — Zone BLR-047 polygon match confirmed.
> **5:47:31** — Zepto mock ops: Zone suspended. Logged.
> **5:47:39** — Traffic cross-validation passed.
> **5:47:44** — Manoj's GPS: 200m from dark store. Coherence normal.
> **5:47:51** — Run count: 0. Confirmed.
> **5:47:58** — Fraud score: 0.11. Auto-approve.
> **5:48:09** — ₹272 UPI credit via Razorpay mock.
> **5:48:12** — Lock screen in Kannada: *"ನಿಮ್ಮ ಜೋನ್‌ನಲ್ಲಿ ಭಾರೀ ಮಳೆ ಪತ್ತೆಯಾಗಿದೆ. ₹272 ನಿಮ್ಮ UPI ಗೆ ಜಮಾ ಆಗಿದೆ. ಸುರಕ್ಷಿತವಾಗಿರಿ, ಮನೋಜ್."*
>
> **Manoj did nothing. Total time: 49 seconds.**

---

## 📊 Analytics Dashboard

### Worker Dashboard
- Coverage status — Active ✅ / days remaining this week
- Total earnings protected since joining RapidCover
- This week's premium paid, max payout available, days covered left
- Last 4 payouts — disruption type, date, ₹ credited
- Streak counter — consecutive clean weeks toward loyalty discount
- Zone risk score with plain-language explanation
- Upcoming risk alert — proactive warning if IMD forecasts disruption in 48 hrs

### Insurer / Admin Dashboard
- Live India map — active triggers, policy density, real-time payout flow per zone
- Disruption intelligence — active events, projected liability, LSTM next-week forecast every Sunday
- Financial health — rolling 4-week loss ratio per zone; zones with LR > 80% flagged for repricing
- Fraud queue — flagged claims with anomaly scores, one-click review/approve/reject
- Partner health — churn rate, streak distribution, plan trends, vernacular engagement
- Predictive reserve widget — next week's projected liability per city

---

## 🏗️ Tech Stack & Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     MOBILE LAYER (PWA)                           │
│   React.js + Tailwind CSS — Partner App + Admin Dashboard        │
│   Web Push API  |  Native GPS  |  UPI Deep Links  |  6 Languages │
└──────────────────────────────────────────────────────────────────┘
                         ↕ REST API / WebSocket
┌──────────────────────────────────────────────────────────────────┐
│              BACKEND — Python + FastAPI                          │
│   Auth | Policy Engine | Trigger Engine | Payout Service         │
└──────────────────────────────────────────────────────────────────┘
       ↕                      ↕                       ↕
┌───────────────┐  ┌─────────────────────┐  ┌──────────────────┐
│  ML SERVICE   │  │   EXTERNAL APIs     │  │  PAYMENT LAYER   │
│  XGBoost      │  │  OpenWeatherMap     │  │  Razorpay Test   │
│  Scikit-learn │  │  CPCB AQI API       │  │  Mock UPI        │
│  LSTM         │  │  IMD Alert Feed     │  └──────────────────┘
└───────────────┘  │  Mock Zepto Ops API │
                   │  Mock Traffic API   │
                   │  NewsAPI (NLP)      │
                   │  Mock KYC Service   │
                   └─────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│         DATA — PostgreSQL + Redis                                │
│         Policies | Claims | GPS Logs | Events | Fraud Flags      │
└──────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│   NOTIFICATIONS — Web Push + Twilio SMS + WhatsApp mock          │
│   Tamil | Kannada | Telugu | Hindi | Marathi | Bengali           │
└──────────────────────────────────────────────────────────────────┘
```

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React.js + Tailwind (PWA) | Android install via WhatsApp link; push notifications; native GPS; UPI deep links |
| Backend | Python + FastAPI | Async performance for real-time trigger pipeline |
| Database | PostgreSQL + Redis | Records integrity + real-time trigger state cache |
| ML | scikit-learn + XGBoost + statsmodels | Standard, deployable as microservices |
| Weather | OpenWeatherMap (free tier) | Real-time + 7-day forecast, pin-code level |
| AQI | aqicn.org + CPCB API (free) | Station-level Indian city data |
| Traffic | Mock road condition feed | Second-layer trigger cross-validation |
| Payments | Razorpay Test Mode + Mock UPI | Full payout demo, no real transactions |
| Notifications | Web Push + Twilio Trial + WhatsApp mock | Lock screen + SMS + WhatsApp in 6 languages |
| Geospatial | Turf.js + PostGIS | Zone polygon matching, GPS trajectory analysis |
| Hosting | Railway / Render (free tier) | Zero-cost hackathon deployment |

---

## 📅 Development Plan — 6 Weeks

### Phase 1 — Ideation & Foundation (Weeks 1–2) ✅
- [x] Persona research — Q-Commerce delivery partner income model
- [x] 5 parametric triggers designed with zone-polygon + traffic validation
- [x] Weekly premium ML model defined
- [x] 6 fraud attack vectors identified with detection architecture
- [x] Tech stack finalized — PWA with justification
- [x] README submitted
- [ ] Figma wireframes — 6 screens: install, onboarding, home, policy, payout, admin
- [ ] 2-minute pitch video uploaded

**Deliverable:** This README + 2-min video

### Phase 2 — Core Product (Weeks 3–4)
- PWA scaffold — Android installable, push notifications live
- Partner registration, OTP login, Zepto ID validation, KYC lite
- Native GPS zone detection + Zone Risk Scorer (Model 1)
- Policy creation + dynamic premium engine (Model 2)
- All 5 triggers wired to real/mock APIs including traffic data
- Zero-touch claim pipeline end-to-end
- Razorpay test mode payout + lock screen push on claim
- Worker dashboard — coverage, earnings protected, payout history

**Deliverable:** Working PWA demo + 2-min video

### Phase 3 — Intelligence & Scale (Weeks 5–6)
- Fraud detection pipeline live — Isolation Forest + all 6 vectors (Model 3)
- Admin dashboard — live map, loss ratio, fraud queue, LSTM predictor (Model 4)
- Streak loyalty system
- Vernacular UI — Kannada, Tamil, Hindi, Telugu, Marathi, Bengali
- End-to-end disruption simulation — fake rainstorm → auto payout → push to phone
- Final 5-min demo video (PWA screen recording on phone)
- Pitch deck PDF finalized

**Deliverable:** Final 5-min demo + pitch deck PDF

---

## 📈 Business Viability

| Metric | Number | Basis |
|--------|--------|-------|
| Q-Commerce delivery partners in India | 500,000+ | Zepto + Blinkit disclosed headcounts |
| Avg disruption days per partner per year | 18–24 days | IMD event frequency in top 10 cities |
| Income lost per disruption day | ₹600–₹900 | 8–15 runs/hr × peak rates |
| Annual income at risk per partner | ₹10,800–₹21,600 | 18–24 days × daily loss |
| Willingness to pay | ₹39–₹89/week | < 1.5% of weekly earnings |
| Year 1 target (Bangalore, Mumbai, Delhi) | 25,000 partners | Metro pilot cities |
| Year 1 gross premium | ₹9.1 Cr | 25,000 × ₹364 avg × 4 quarters |
| Target loss ratio | 58–65% | Parametric insurance global benchmark |

**The Strategic Moat:** RapidCover generates the first-ever dark-store-zone operational disruption dataset for India's Q-Commerce network — suspension frequency, duration, road condition correlation, zone-level risk scores. Data that Zepto and Blinkit themselves don't have in structured form. That is the licensing and B2B opportunity that outlasts the insurance product.

**Distribution:** One B2B integration with Zepto's partner app = 100,000+ workers onboarded via a single WhatsApp link. Distribution cost = ₹0 marginal.

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
