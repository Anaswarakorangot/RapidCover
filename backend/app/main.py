from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.utils.rate_limiter import limiter
from app.database import init_db, SessionLocal
from app.api.router import api_router
from app.data.seed_zones import seed_zones
from app.data.seed_partner import seed_partners
# Import ALL models so they register with SQLAlchemy Base (tables will be created by init_db)
from app.models import (
    Partner, Zone, Policy, TriggerEvent, Claim,
    ZoneReassignment, ReassignmentStatus, ZoneRiskProfile,
    PushSubscription, DrillSession, PartnerGPSPing, PartnerDevice, SustainedEvent,
    ActiveEventTracker,
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

    # Configure Sentry error tracking (Phase 4 - Optional)
    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,  # 10% performance monitoring
            profiles_sample_rate=0.1,  # 10% profiling
        )
        print(f"Sentry error tracking enabled for environment: {settings.environment}")

    # Configure structured logging (Phase 4)
    from app.utils.logging_config import setup_logging
    logger = setup_logging(
        log_level=settings.log_level,
        json_format=settings.json_logging
    )
    logger.info("Starting RapidCover API...", extra={"extra_fields": {"environment": settings.environment}})

    init_db()
    logger.info("Database tables created")
    # Seed zones on every startup (idempotent - skips existing)
    db = SessionLocal()
    try:
        created_zones = seed_zones(db)
        if created_zones:
            logger.info(f"Seeded {len(created_zones)} new zones")

        # Seed test partners
        seed_partners(db)
    finally:
        db.close()
    # Start background trigger polling (every 45s)
    start_scheduler()
    logger.info("Background trigger scheduler started")
    yield
    # Shutdown
    stop_scheduler()
    logger.info("Shutting down RapidCover API")


app = FastAPI(
    title="RapidCover API",
    description="Parametric income insurance for Q-Commerce delivery partners",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting (Phase 4)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    """
    Enhanced health check endpoint (Phase 4).

    Returns comprehensive system health including:
    - Database connectivity
    - External API status
    - Demo mode state
    - Timestamp

    Use this for monitoring and load balancer health checks.
    """
    from app.services.external_apis import get_source_health
    from app.utils.time_utils import utcnow
    from sqlalchemy import text

    health_status = {
        "status": "healthy",
        "service": "RapidCover API",
        "version": "0.1.0",
        "timestamp": utcnow().isoformat(),
        "demo_mode": settings.demo_mode,
        "components": {}
    }

    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }

    # Check external API health
    try:
        api_health = get_source_health()
        live_sources = sum(1 for s in api_health.values() if s["status"] == "live")
        total_sources = len(api_health)

        health_status["components"]["external_apis"] = {
            "status": "healthy" if live_sources > 0 or settings.demo_mode else "degraded",
            "live_sources": live_sources,
            "total_sources": total_sources,
            "sources": {name: info["status"] for name, info in api_health.items()}
        }
    except Exception as e:
        health_status["components"]["external_apis"] = {
            "status": "unknown",
            "message": f"Error checking API health: {str(e)}"
        }

    return health_status
