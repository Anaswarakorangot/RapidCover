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
```

If you do not set `VITE_API_URL`, the frontend already defaults to `http://localhost:8000/api/v1`.

## 4. Seed development data

The registration flow depends on zones. After starting the backend, seed zones before testing the app.

Option 1: Use the admin page in the frontend after logging in.

Option 2: Call the admin seed endpoint directly from the backend docs or with a request:

```bash
POST http://localhost:8000/api/v1/admin/seed
```

Once zones are seeded, the registration page will show zone options.

## 5. Typical local workflow

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

## 6. Common issues

### Registration page shows no zones

Seed zones through `POST /api/v1/admin/seed`, then refresh the frontend.

### Frontend cannot reach the backend

Check that:

- the backend is running on port `8000`
- the frontend is using `VITE_API_URL=http://localhost:8000/api/v1`

### Database file location

For local development, SQLite is created from the backend default database URL:

```text
sqlite:///./rapidcover.db
```

This means the database file is created relative to the backend working directory.

## 7. Recommended first checks after clone

1. Start the backend and confirm `http://localhost:8000/health` returns healthy.
2. Start the frontend and confirm the app opens at `http://localhost:5173`.
3. Seed zones.
4. Register a user and verify the zone dropdown is populated.
