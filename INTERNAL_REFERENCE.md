# RapidCover Internal Reference

This document is an internal technical reference for new team members joining the RapidCover repository with zero prior context.

It is based on:

- the current codebase in this repository
- the root `README.md`
- the local DEVTrails use-case PDF referenced by the team
- the implementation-status screenshots provided alongside this request

Where something is inferred rather than explicitly implemented, that is called out clearly.

---

## 1. Project Overview

### What this application does

RapidCover is a prototype parametric income-protection platform for Indian delivery partners, focused on Q-commerce workers such as Zepto and Blinkit riders. The system aims to protect workers from income loss caused by external disruptions like heavy rain, extreme heat, poor air quality, civic shutdowns, and dark store closures.

The product includes:

- a mobile-first React frontend for partner onboarding and self-service
- a FastAPI backend for partner, policy, claims, zone, trigger, and admin APIs
- mock external data services for weather, AQI, shutdown, and platform status
- a basic claims-processing pipeline driven by trigger events

### Problem it solves

The core problem comes from the DEVTrails 2026 challenge and the repository README:

- gig workers lose income immediately when external conditions stop deliveries
- these workers typically do not have income protection
- the product must insure loss of income only
- the pricing model must be weekly, not monthly

This implementation specifically frames the problem around dark-store delivery partners in high-frequency urban logistics.

### Core features currently present

- Partner registration with phone, name, platform, and zone selection
- OTP-based login flow with JWT session handling
- Zone seeding and zone lookup APIs
- Weekly policy quote generation and policy creation
- Mock trigger simulation for rain, heat, AQI, shutdown, and closure
- Trigger storage in the database
- Rule-based claim generation from triggers
- Rule-based fraud scoring
- Worker dashboard, policy screen, claims history, profile screen, and basic admin dashboard

---

## 2. Original Plan vs Current Implementation

### Intended design inferred from README, PDF, and project structure

The intended product is more ambitious than the code currently delivers.

From the README and DEVTrails PDF, the intended design includes:

- a true installable PWA or mobile-like experience
- weekly parametric insurance for Q-commerce delivery partners
- optimized onboarding for a specific delivery persona
- dynamic AI/ML pricing based on hyper-local risk
- real or mock integrations with external APIs
- automatic trigger detection and automatic claim initiation
- instant payout simulation through payment rails such as Razorpay test mode
- fraud detection with delivery-specific intelligence
- partner and admin dashboards
- multilingual user experience
- analytics around loss ratio, forecasting, and operational exposure

The screenshots provided with this request align with that intended roadmap. They also match what the code suggests:

- Phase 1 mostly complete in concept and documentation
- Phase 2 partially implemented
- Phase 3 only lightly implemented

### What is actually implemented

What is real in code today:

- Basic backend CRUD and workflow for partners, policies, claims, triggers, zones
- Basic frontend app with routing and protected pages
- OTP login, but only in development style
- Weekly policy purchase flow
- Mock event simulation from the admin page
- Trigger detection against mock services
- Claim generation and manual admin progression to payout
- Rule-based fraud scoring
- Randomized zone risk scores for seeded zones

### Major differences and missing parts

The biggest gaps between the intended design and the implementation are:

#### Product and workflow gaps

- Zero-touch automation is now implemented: triggers auto-create claims with fraud scoring when simulation endpoints are called
- Optional auto-payout in demo mode via `AUTO_PAYOUT_ENABLED=true` environment variable
- No real payout integration: payout is just a status change with a generated fake UPI reference
- No push notification system
- No real GPS collection or zone auto-detection
- No real Partner ID validation
- No KYC or Aadhaar-face verification workflow
- No real worker activity validation from a platform partner feed

#### AI/ML gaps

- No ML model is present in the repository
- Zone risk scores are random seed values
- Premium pricing is simple rules based on risk-score bands
- Fraud detection is weighted rule scoring, not anomaly-detection ML
- No LSTM, XGBoost, predictive forecasting, or loss-ratio engine

#### Platform/PWA gaps

- The frontend includes a manifest and mobile meta tags, but no service worker
- PWA install readiness is incomplete
- Manifest references icon files that do not exist in `frontend/public`

#### Security and operations gaps

- Admin endpoints are intentionally unauthenticated
- OTP is returned in API responses during login
- OTP storage is in-memory only
- Trigger conditions are stored in-memory only
- Database schema is created with `create_all`, with no migrations
- No test suite is present

---

## 3. System Architecture

### Overall architecture

The project is a two-part web application:

1. Frontend
   A React 19 + Vite application in `frontend/`

2. Backend
   A FastAPI + SQLAlchemy application in `backend/`

The backend serves JSON APIs only. The frontend is a separate client application that calls the backend over HTTP.

### Backend layers

The backend is organized into the following layers:

- `app/main.py`
  FastAPI app initialization, CORS, app lifespan, database initialization

- `app/api/`
  HTTP route handlers for partners, policies, claims, zones, triggers, and admin

- `app/models/`
  SQLAlchemy ORM models

- `app/schemas/`
  Pydantic request and response models

- `app/services/`
  Business logic such as auth, premium calculation, external API simulation, trigger detection, fraud scoring, and claims processing

- `app/data/`
  Seed data for known dark-store zones

### Frontend layers

The frontend is organized into:

- `src/App.jsx`
  Route definitions and protected/public route logic

- `src/context/AuthContext.jsx`
  Auth state, token bootstrapping, login, logout, profile refresh

- `src/services/api.js`
  Single API client wrapper for the backend

- `src/pages/`
  Main application screens

- `src/components/`
  Layout and small reusable UI primitives

### Tech stack used

#### Frontend

- React 19
- React Router 7
- Vite 8
- Tailwind CSS 4 via `@tailwindcss/vite`

#### Backend

- FastAPI
- SQLAlchemy 2
- Pydantic settings
- `python-jose` for JWT
- `passlib` present, though password hashing is not central here

#### Data and storage

- SQLite by default for development
- PostgreSQL intended for production
- In-memory dictionaries used for OTP storage and mock condition storage

### Component interaction and data flow

At a high level:

1. The frontend calls backend APIs through `src/services/api.js`
2. Login returns a JWT that is saved in local storage
3. Protected frontend screens use that token for authenticated calls
4. Admin can seed zones and simulate events
5. Simulation updates in-memory mock condition state
6. Trigger detection writes `TriggerEvent` records to the database
7. Claims processing converts a trigger into `Claim` records for eligible policies
8. Worker-facing pages display policies, claims, and active disruptions

---

## 4. Application Workflow

### End-user workflow

The intended worker flow is:

1. Register
2. Log in with OTP
3. Select or confirm zone
4. View policy quotes
5. Purchase weekly coverage
6. Wait for covered disruptions
7. Receive automated payout

The current implemented flow is:

1. Register using name, phone, platform, and manually selected zone
2. Request OTP
3. Enter OTP, which is exposed directly by the backend in development
4. Authenticate and land on the dashboard
5. View zone and optional active policy
6. Purchase a policy from the Policy page
7. Admin simulates an event
8. Backend creates a trigger AND automatically processes claims
9. Backend auto-approves, rejects, or leaves claims pending based on fraud score
10. If `AUTO_PAYOUT_ENABLED=true`, approved claims are also auto-paid
11. Worker sees claim history and payout state immediately

### Internal backend workflow

#### Registration

- `POST /api/v1/partners/register`
- Creates a `Partner` row
- No KYC or partner-ID validation happens

#### Login

- `POST /api/v1/partners/login`
- Backend generates and stores OTP in memory
- For demo purposes, the OTP is returned in the response
- `POST /api/v1/partners/verify`
- Returns a JWT token if OTP matches

#### Policy creation

- `GET /api/v1/policies/quotes`
- Calculates quotes using tier config plus a risk band adjustment
- `POST /api/v1/policies`
- Creates a 7-day active policy if no active policy exists

#### Trigger simulation and detection

- Admin uses simulation endpoints
- Mock condition storage is updated
- Trigger detector evaluates the current conditions
- If a threshold is breached and no equivalent active trigger exists, a new `TriggerEvent` is stored

#### Claims processing (Zero-Touch)

- Claims are automatically processed when triggers are created
- Eligible active policies in the same zone are loaded
- Payout amount is calculated
- Daily and weekly limits are checked
- Fraud score is calculated
- Claim is created with status `approved`, `pending`, or `rejected`
- If `AUTO_PAYOUT_ENABLED=true`, approved claims are immediately marked as paid with a UPI reference

#### Payout

- Admin manually calls the payout action
- Claim status changes to `paid`
- A fake UPI reference is generated if none is supplied

### Internal processing logic summary

The core engine now works as:

- zone condition exists
- condition breaches threshold
- trigger event is recorded
- claims are automatically processed (zero-touch)
- partner policies in that zone are scanned
- payout is calculated with severity and limits
- fraud score assigns approval path
- claim is shown in frontend immediately
- if auto-payout enabled, approved claims are paid instantly

This is now a fully automatic parametric insurance workflow for the demo environment.

---

## 5. UI / Screens Breakdown

### Screen inventory from code

The frontend contains these screens in `frontend/src/pages/`:

- `Register.jsx`
- `Login.jsx`
- `Dashboard.jsx`
- `Policy.jsx`
- `Claims.jsx`
- `Profile.jsx`
- `Admin.jsx`

### Register

Purpose:

- onboard a new worker
- collect name, phone, platform, and zone

Current behavior:

- fetches zones from backend
- disables the zone selector while zones are loading
- allows registration with nullable `zone_id`

### Login

Purpose:

- request OTP and verify it

Current behavior:

- two-step phone then OTP flow
- dev OTP is shown on screen when returned by backend

### Dashboard

Purpose:

- landing screen after login
- show policy, claims summary, zone info, and active disruptions

Current behavior:

- pulls active policy
- pulls claim summary
- optionally loads current zone and active triggers for that zone

### Policy

Purpose:

- show available weekly plans
- purchase or cancel coverage

Current behavior:

- shows three tiers from backend quotes
- displays zone-based discount/surcharge
- allows one active policy at a time

### Claims

Purpose:

- show automatic claim history
- show pending and paid amounts

Current behavior:

- lists recent claims
- shows trigger type and claim status

### Profile

Purpose:

- show basic account details
- edit name and language preference

Current behavior:

- language can be stored
- UI itself remains English-only
- zone details are minimal and only show zone ID

### Admin

Purpose:

- seed zone data
- simulate trigger events
- process claims
- approve, reject, and pay claims

Current behavior:

- works as a demo control panel
- has no admin authentication or role separation

### Layout and navigation

`frontend/src/components/Layout.jsx` provides:

- top app bar
- bottom tab navigation
- mobile-first container layout

### Assets

Assets found in the repository:

- `frontend/src/assets/hero.png`
- `frontend/src/assets/react.svg`
- `frontend/src/assets/vite.svg`
- `frontend/public/favicon.svg`
- `frontend/public/icons.svg`
- `frontend/public/manifest.json`

Observations:

- `hero.png` is a stylized isometric purple layered graphic; it appears unused in the current app
- `react.svg` and `vite.svg` are template leftovers and appear unused
- `manifest.json` exists, but the PWA is incomplete
- `manifest.json` points to `/icon-192.png` and `/icon-512.png`, which are not present

---

## 6. Codebase Breakdown

### Root structure

```text
RapidCover/
├─ README.md
├─ SETUP.md
├─ INTERNAL_REFERENCE.md
├─ backend/
└─ frontend/
```

### Backend structure

```text
backend/
├─ requirements.txt
├─ README.md
└─ app/
   ├─ main.py
   ├─ config.py
   ├─ database.py
   ├─ api/
   ├─ models/
   ├─ schemas/
   ├─ services/
   └─ data/
```

### Key backend files

#### `backend/app/main.py`

- starts FastAPI
- runs `init_db()` on startup
- configures permissive CORS
- mounts the versioned router

#### `backend/app/database.py`

- creates SQLAlchemy engine
- switches behavior between SQLite and non-SQLite URLs
- exposes `get_db()` dependency
- creates tables with `Base.metadata.create_all()`

#### `backend/app/config.py`

- central settings object
- default database URL is SQLite
- includes placeholders for Redis, external APIs, Razorpay, and Twilio

#### `backend/app/models/partner.py`

- partner data model
- includes platform enum and language enum
- includes Aadhaar hash and partner ID fields, but they are not actively used in workflow

#### `backend/app/models/policy.py`

- policy tiers and current tier config
- note: code tier values differ from README business plan values

#### `backend/app/models/trigger_event.py`

- supported trigger types and thresholds
- stores active or ended disruption events

#### `backend/app/models/claim.py`

- claim amount, status, fraud score, validation payload, UPI ref

#### `backend/app/api/*.py`

- route layer
- simple CRUD and orchestration endpoints

#### `backend/app/services/external_apis.py`

- mock data providers
- central simulation state stored in memory

#### `backend/app/services/trigger_detector.py`

- evaluates simulated data against thresholds
- creates `TriggerEvent` records

#### `backend/app/services/claims_processor.py`

- converts a trigger into claims for affected active policies
- applies payout logic and fraud outcome

#### `backend/app/services/fraud_detector.py`

- computes a weighted risk score for suspicious claims

#### `backend/app/services/premium.py`

- returns quotes based on policy tier and zone risk band

#### `backend/app/data/seed_zones.py`

- seeds 11 sample zones across Bangalore, Mumbai, and Delhi
- assigns randomized risk scores

### Frontend structure

```text
frontend/
├─ package.json
├─ vite.config.js
├─ index.html
├─ public/
└─ src/
   ├─ main.jsx
   ├─ App.jsx
   ├─ index.css
   ├─ services/
   ├─ context/
   ├─ components/
   ├─ pages/
   └─ assets/
```

### Key frontend files

#### `frontend/src/services/api.js`

- central fetch wrapper
- attaches JWT from local storage
- redirects to login on 401
- exposes methods for all worker and admin endpoints

#### `frontend/src/context/AuthContext.jsx`

- bootstraps auth from stored token
- fetches current profile
- exposes login/logout helpers

#### `frontend/src/App.jsx`

- defines public and protected routes
- wraps authenticated routes in shared layout

#### `frontend/src/pages/*.jsx`

- each file corresponds to one main application screen

#### `frontend/src/components/ui/`

- primitive shared components: button, input, card

---

## 7. Internal Logic

### Premium calculation

Premium logic is currently straightforward:

- start with the tier base premium
- read the worker's zone risk score
- apply one of four banded adjustments:
  - low risk: discount
  - medium risk: no change
  - high risk: surcharge
  - very high risk: bigger surcharge

This is deterministic rule logic, not ML.

### Trigger detection

Supported trigger types:

- rain
- heat
- AQI
- shutdown
- closure

Important detail:

- the code defines threshold comments like 30 minutes or 4 hours
- but in practice, several trigger checks fire immediately based on current simulated state
- duration logic is mostly descriptive, not truly enforced

### Severity calculation

For rain, heat, and AQI:

- severity is derived from how far a measured value exceeds a threshold
- it returns a value from 1 to 5

For shutdown and closure:

- fixed demo severities are used

### Claim creation

Claim processing does the following:

1. find active policies whose partners belong to the trigger zone
2. calculate a base payout from trigger type and disruption hours
3. increase payout based on severity
4. cap payout by the policy daily max
5. check weekly claim-day allowance
6. compute fraud score
7. create claim with `approved`, `pending`, or `rejected`

### Fraud logic

Fraud scoring is based on:

- GPS coherence
- activity paradox
- claim frequency
- duplicate claim check
- account age
- zone boundary gaming placeholder

Important caveat:

- the inputs needed for strong validation do not actually exist in the system today
- GPS and delivery activity are not collected from the real user journey
- several fraud checks therefore default to light penalties or placeholders

### Authentication logic

- OTP is stored in a Python dictionary
- JWT uses a configurable secret
- authenticated endpoints rely on bearer token parsing

This is good enough for a demo, but not for production or a serious multi-instance backend.

---

## 8. Setup & Local Development

### Repository-level setup

There is already a dedicated onboarding document at `SETUP.md`. That file should be the starting point for new developers.

### Backend local setup

Expected flow:

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend default URLs:

- `http://localhost:8000`
- `http://localhost:8000/docs`

### Frontend local setup

Expected flow:

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL:

- `http://localhost:5173`

### Environment assumptions

The backend uses development defaults even without a `.env` file:

- SQLite database
- default JWT secret
- empty external service credentials

### Seed data requirement

The registration flow depends on zones being present. A fresh local environment should seed zones using:

- Admin UI button, or
- `POST /api/v1/admin/seed`

### Validation notes from this analysis

Two practical environment issues appeared during inspection:

1. Frontend build did not complete in this sandbox because Vite/Tailwind native dependency loading failed under the current environment.
2. A direct backend import check failed in the current machine Python due to a local `pydantic` / `pydantic-settings` version mismatch outside the repository.

These failures are environment-specific observations from this analysis session, not proof that the repository is fundamentally broken in a clean virtual environment.

---

## 9. Limitations & Flaws

### Product limitations

- Not a full PWA despite manifest presence
- No service worker
- No push notifications
- No real payment gateway integration
- No real external API integrations
- No background scheduler polling zones continuously
- No live map or predictive analytics

### Security limitations

- Admin endpoints are open to any authenticated frontend user who navigates to `/admin`
- The backend itself does not enforce admin role checks
- OTP is returned to the client during login
- JWT secret defaults to a development value
- CORS allows all origins

### Data and persistence limitations

- OTP store is in-memory and disappears on restart
- Mock external condition state is in-memory and disappears on restart
- SQLite is acceptable for local demo only
- No migrations are present

### Workflow limitations

- Trigger detection is only run when simulation endpoints are called
- Claims ARE now automatically processed when a trigger is created (zero-touch)
- Payout can be automatic in demo mode via `AUTO_PAYOUT_ENABLED=true`
- No audit trail or event bus exists

### Code quality and implementation issues

- `frontend/src/components/ui/Button.jsx` appears to contain malformed JSX in the loading spinner SVG attributes
- the frontend contains several mojibake or encoding artifacts in emoji and Unicode text
- `manifest.json` references missing icon PNGs
- `hero.png`, `react.svg`, and `vite.svg` appear unused
- partner language selection exists, but localized UI content does not
- profile page shows only zone ID instead of richer zone details

### Architecture issues

- Business logic is spread between routes and services rather than being consistently isolated
- Several admin endpoints enrich records with repeated per-row queries instead of efficient joined queries
- The system models duration-based triggers, but actual duration tracking is mostly not enforced

---

## 10. Deviation from Intended Design

This is the section new team members should read if they want the shortest explanation of "what the README promises versus what the app actually does."

### Promised or implied by design

- installable worker-first mobile app
- AI-driven pricing and fraud scoring
- real-time trigger monitoring
- seamless zero-touch claim pipeline
- instant payout demo
- worker and insurer intelligence dashboards
- multilingual engagement

### Actually delivered

- mobile-shaped React web app
- backend CRUD and workflow prototype
- mock simulation engine
- rule-based trigger and fraud logic
- manual admin-assisted claim pipeline
- basic dashboards only

### Key mismatches

- PWA claim: partially scaffolded, not actually completed
- AI/ML claim: represented mostly as placeholders and rules
- instant payout claim: simulated by claim status updates (auto-payout available in demo mode)
- multilingual claim: enum and profile field exist, but content is not translated
- zero-touch claim claim: NOW IMPLEMENTED - claims auto-created when triggers fire
- advanced admin analytics claim: not implemented

### Business-rule mismatch

The README premium model and the code premium model do not match.

README tiers:

- Flex: 39/week, 350/day, 2 days
- Standard: 59/week, 600/day, 3 days
- Pro: 89/week, 900/day, 4 days

Code tiers:

- Flex: 29/week, 250/day, 3 days
- Standard: 49/week, 350/day, 5 days
- Pro: 79/week, 500/day, 7 days

This is one of the clearest implementation-vs-plan deviations in the repository.

---

## 11. Future Improvements

### Highest-value product improvements

1. ~~Complete the zero-touch flow~~ DONE
   Claims are now automatically processed when triggers are created. Auto-payout available via `AUTO_PAYOUT_ENABLED=true`.

2. Finish the PWA layer
   Add service worker, install flow, cache strategy, offline shell, and real icon assets.

3. Replace manual zone selection with actual GPS-assisted onboarding
   Even a demo geolocation flow would better match the product promise.

4. Add real role separation
   Admin endpoints should require explicit admin authentication.

5. Implement at least one realistic payment simulation
   Razorpay test mode or a clearly modeled payout adapter would make the demo much stronger.

### Engineering improvements

1. Add Alembic migrations
2. Add automated tests for auth, policy purchase, trigger creation, and claims processing
3. Move from in-memory demo state to Redis or database-backed state where appropriate
4. Introduce background jobs or scheduled trigger polling
5. Normalize backend query patterns to avoid repeated lookup loops

### Product consistency improvements

1. Align pricing tiers between README, code, and UI
2. Align trigger duration logic with actual enforcement
3. Remove or implement placeholder fields such as Aadhaar/KYC flow and partner validation
4. Replace random risk scoring with deterministic demo data or a simple reproducible model

### Frontend improvements

1. Fix malformed JSX in shared UI components
2. Clean encoding issues in strings and labels
3. Use the existing hero asset or remove unused assets
4. Improve Profile with zone details and policy summary
5. Add translated content if language preference is meant to matter

### Documentation improvements

1. Keep `README.md` as the business/pitch document
2. Keep `SETUP.md` as the onboarding/runbook
3. Use this file as the technical internal reference
4. Add an `ARCHITECTURE.md` if the system grows beyond prototype stage

---

## 12. Summary

RapidCover is currently a solid hackathon-style prototype with a clear product idea and a surprisingly complete vertical slice for a small codebase:

- worker registration and OTP login exist
- weekly policy creation exists
- mock disruptions can be simulated
- trigger records can be created
- claims can be generated and paid in a demo workflow
- worker and admin dashboards exist

However, the implementation is still much closer to a guided demo system than a finished parametric insurance platform.

The most important truth about the repository is this:

- the product story is strong
- the workflow skeleton is real
- the backend domain model is mostly in place
- but many of the hardest promised features are still mocked, manual, or only represented as placeholders

If a new team member wants to understand the project quickly, the right mental model is:

> RapidCover is a prototype of a parametric income-protection platform for Q-commerce workers, with a real full-stack demo path, but not yet a production-grade automation, payments, AI/ML, or PWA system.

---

## Appendix: Current Status Snapshot

Based on the codebase plus the implementation-status screenshots, the most accurate summary is:

### Clearly implemented

- Persona-driven product framing
- Registration
- OTP login
- JWT auth
- Policy creation
- Zone seed data
- Mock trigger APIs
- Trigger detection
- Claims generation (zero-touch automation)
- Auto-payout in demo mode
- Basic fraud scoring
- Basic admin dashboard
- Basic worker dashboard
- End-to-end simulation in demo form

### Partially implemented

- PWA scaffolding
- Dynamic premium engine
- Fraud intelligence
- Zone and disruption intelligence

### Missing or substantially incomplete

- Figma/prototype assets in repo
- pitch/demo video artefacts in repo
- push notifications
- service worker
- GPS-based onboarding
- partner-ID validation
- KYC flow
- real payment integration
- live map
- loss ratio tracking
- predictive forecasting
- real multilingual experience
