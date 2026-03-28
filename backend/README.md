# RapidCover Backend

FastAPI backend for RapidCover - Parametric income insurance for Q-Commerce delivery partners.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis (optional, for production)

### Setup

1. Create and activate a virtual environment:

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment:

```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Run the development server:

```bash
uvicorn app.main:app --reload
```

5. Open API docs at http://localhost:8000/docs

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment configuration
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── partner.py       # Delivery partner
│   │   ├── policy.py        # Insurance policy
│   │   ├── claim.py         # Claims/payouts
│   │   ├── zone.py          # Dark store zones
│   │   └── trigger_event.py # Disruption events
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── partner.py
│   │   ├── policy.py
│   │   ├── claim.py
│   │   └── zone.py
│   ├── api/                 # API routes
│   │   ├── router.py        # Main router
│   │   ├── partners.py      # Partner registration/auth
│   │   ├── policies.py      # Policy management
│   │   ├── claims.py        # Claim history
│   │   └── zones.py         # Zone management
│   └── services/            # Business logic
│       ├── auth.py          # JWT/OTP authentication
│       └── premium.py       # Premium calculation
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

### Partners
- `POST /api/v1/partners/register` - Register new partner
- `POST /api/v1/partners/login` - Request OTP
- `POST /api/v1/partners/verify` - Verify OTP, get JWT
- `GET /api/v1/partners/me` - Get current partner profile
- `PATCH /api/v1/partners/me` - Update profile

### Policies
- `GET /api/v1/policies/quotes` - Get premium quotes for all tiers
- `POST /api/v1/policies` - Create new policy
- `GET /api/v1/policies/active` - Get active policy
- `GET /api/v1/policies/history` - Get policy history
- `POST /api/v1/policies/{id}/cancel` - Cancel policy

### Claims
- `GET /api/v1/claims` - Get claim history (paginated)
- `GET /api/v1/claims/summary` - Get claims summary
- `GET /api/v1/claims/{id}` - Get claim details

### Zones
- `GET /api/v1/zones` - List zones
- `GET /api/v1/zones/{id}` - Get zone details
- `GET /api/v1/zones/code/{code}` - Get zone by code
- `POST /api/v1/zones` - Create zone (admin)
- `PATCH /api/v1/zones/{id}/risk` - Update risk score (ML service)

## Policy Tiers

| Tier | Weekly Premium | Daily Payout | Max Days/Week |
|------|---------------|--------------|---------------|
| Flex | ₹29 | ₹250 | 3 |
| Standard | ₹49 | ₹350 | 5 |
| Pro | ₹79 | ₹500 | 7 |

Premium is adjusted based on zone risk score:
- Low risk (0-30): 10% discount
- Medium risk (31-60): No adjustment
- High risk (61-80): 15% surcharge
- Very high risk (81-100): 30% surcharge

## Development

### Database Migrations (coming soon)

```bash
# Initialize Alembic
alembic init migrations

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Running Tests (coming soon)

```bash
pytest
```
