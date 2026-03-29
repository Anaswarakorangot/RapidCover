# RapidCover Setup Guide

This guide is for a fresh clone of the repository on a local development machine.

## 1. Clone the repository

```bash
git clone https://github.com/Anaswarakorangot/RapidCover.git
cd RapidCover
```

## 2. Backend setup

RapidCover uses FastAPI for the backend. The current development configuration uses SQLite by default, so PostgreSQL is not required for a first local run.

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file if you want to override defaults:

```bash
copy .env.example .env
```

If `.env.example` is not present yet, you can still run locally because the backend has development defaults in `app/config.py`.

For push notifications, add VAPID keys to `backend/.env`:

```bash
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_CLAIM_EMAIL=mailto:admin@example.com
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend URLs:

- API root: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## 3. Frontend setup

Open a new terminal:

```bash
cd frontend
npm install
```

Start the frontend:

```bash
npm run dev
```

Frontend URL:

- App: `http://localhost:5173`

Optional frontend environment file:

Create `frontend/.env` if you want to point the frontend to a different backend URL.

```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_VAPID_PUBLIC_KEY=your-vapid-public-key
```

If you do not set `VITE_API_URL`, the frontend already defaults to `http://localhost:8000/api/v1`.

`VITE_VAPID_PUBLIC_KEY` is required if you want to test PWA push notifications locally.

## 4. Web push notification setup

Push notifications require:

1. Install frontend dependencies:

```bash
cd frontend
npm install
```

2. Install backend dependencies:

```bash
cd backend
pip install -r requirements.txt
```

3. Generate VAPID keys:

```bash
npx web-push generate-vapid-keys
```

4. Add the generated values to your local env files:

```bash
# backend/.env
VAPID_PRIVATE_KEY=your-generated-private-key
VAPID_PUBLIC_KEY=your-generated-public-key
VAPID_CLAIM_EMAIL=mailto:admin@example.com

# frontend/.env
VITE_VAPID_PUBLIC_KEY=your-generated-public-key
```

The frontend public key and backend public key must match.

## 5. Seed development data

The registration flow depends on zones. After starting the backend, seed zones before testing the app.

Option 1: Use the admin page in the frontend after logging in.

Option 2: Call the admin seed endpoint directly from the backend docs or with a request:

```bash
POST http://localhost:8000/api/v1/admin/seed
```

Once zones are seeded, the registration page will show zone options.

## 6. Typical local workflow

Terminal 1:

```bash
cd backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Open the app at `http://localhost:5173`.

## 7. Common issues

### Registration page shows no zones

Seed zones through `POST /api/v1/admin/seed`, then refresh the frontend.

### Frontend cannot reach the backend

Check that:

- the backend is running on port `8000`
- the frontend is using `VITE_API_URL=http://localhost:8000/api/v1`

### Push notifications are not working

Check that:

- `frontend/.env` contains `VITE_VAPID_PUBLIC_KEY`
- `backend/.env` contains `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, and `VAPID_CLAIM_EMAIL`
- the frontend and backend public keys are identical
- you restarted both dev servers after changing env files

### Database file location

For local development, SQLite is created from the backend default database URL:

```text
sqlite:///./rapidcover.db
```

This means the database file is created relative to the backend working directory.

## 8. Recommended first checks after clone

1. Start the backend and confirm `http://localhost:8000/health` returns healthy.
2. Start the frontend and confirm the app opens at `http://localhost:5173`.
3. Seed zones.
4. Register a user and verify the zone dropdown is populated.
