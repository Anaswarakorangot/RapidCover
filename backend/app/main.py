from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, SessionLocal
from app.api.router import api_router
from app.data.seed_zones import seed_zones
from app.data.seed_partner import seed_partners
# Import ALL models so they register with SQLAlchemy Base (tables will be created by init_db)
from app.models import (
    Partner, Zone, Policy, TriggerEvent, Claim,
    ZoneReassignment, ReassignmentStatus, ZoneRiskProfile,
    PushSubscription, DrillSession, PartnerGPSPing, PartnerDevice, SustainedEvent
)
from app.services.scheduler import start_scheduler, stop_scheduler

from os import getenv

settings = get_settings()
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

extra_origins = getenv("CORS_ORIGINS", "")
allowed_origins = DEFAULT_CORS_ORIGINS + [o.strip() for o in extra_origins.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting RapidCover API...")
    init_db()
    print("Database tables created.")
    # Seed zones on every startup (idempotent - skips existing)
    db = SessionLocal()
    try:
        created_zones = seed_zones(db)
        if created_zones:
            print(f"Seeded {len(created_zones)} new zones.")
        
        # Seed test partners
        seed_partners(db)
    finally:
        db.close()
    # Start background trigger polling (every 45s)
    start_scheduler()
    print("Background trigger scheduler started.")
    yield
    # Shutdown
    stop_scheduler()
    print("Shutting down RapidCover API...")


app = FastAPI(
    title="RapidCover API",
    description="Parametric income insurance for Q-Commerce delivery partners",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
def root():
    """Root endpoint - health check."""
    return {
        "service": "RapidCover API",
        "version": "0.1.0",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
