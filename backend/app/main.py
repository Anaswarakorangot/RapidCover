import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.utils.rate_limiter import limiter
from app.database import init_db, SessionLocal
from app.api.router import api_router
from app.data.seed_zones import seed_zones
from app.data.seed_partner import seed_partners
from app.seed_admin import seed_default_admin
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

    # Run Alembic migrations
    try:
        from alembic.config import Config
        from alembic import command
        from pathlib import Path
        alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied")
    except Exception as migration_err:
        logger.warning(f"Migration execution skipped: {migration_err}")

    # Seed default admin (automatic on startup if no admins exist)
    seed_default_admin()

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

    # Initialize API response cache (Redis preferred, InMemory fallback)
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend
    try:
        import redis.asyncio as aioredis
        from fastapi_cache.backends.redis import RedisBackend
        redis_url = getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
        await redis_client.ping()
        FastAPICache.init(RedisBackend(redis_client), prefix="rapidcover-cache")
        logger.info("FastAPICache initialized with Redis backend")
    except Exception as cache_err:
        logger.warning(
            f"Redis unavailable ({cache_err}) — using InMemoryBackend for caching"
        )
        FastAPICache.init(InMemoryBackend(), prefix="rapidcover-cache")

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


# Custom OpenAPI schema with enhanced documentation
def custom_openapi():
    """Generate custom OpenAPI schema with detailed documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title="RapidCover API",
        version="1.0.0",
        description="""
## Zero-Touch Parametric Insurance API

RapidCover provides automated income protection for India's gig economy workers.

### 🎯 Key Features
- 🤖 **ML-Powered Risk Scoring** - XGBoost zone risk, Gradient Boosting premium, Isolation Forest fraud detection
- ⚡ **Zero-Touch Automation** - Auto-claim generation, GPS-based zone detection, partner ID validation
- 🔍 **7-Factor Fraud Detection** - GPS coherence, activity paradox, claim frequency, duplicate detection
- 📊 **Real-Time Monitoring** - MLOps dashboard, performance metrics, fallback tracking
- 🔔 **Push Notifications** - PWA-enabled instant claim alerts
- 🎯 **5 Parametric Triggers** - Rain, Heat, AQI, Shutdown, Dark Store Closure

### 📡 Live Data Sources
- OpenWeatherMap API (rain, temperature)
- OpenAQ API (air quality)
- Platform APIs (partner validation, activity tracking)

### 🔐 Authentication
- **Partners**: OTP-based login with JWT tokens (`POST /partners/login` → `POST /partners/verify`)
- **Admins**: Email/password login with JWT tokens (`POST /admin/auth/login`)

### 📈 Coverage
- **Cities**: Bangalore, Mumbai, Delhi
- **Zones**: 11 dark store zones with GPS detection
- **Tiers**: Flex (₹22/week), Standard (₹33/week), Pro (₹45/week)

### 🚀 Quick Start
1. Register partner: `POST /partners/register`
2. Detect zone: `GET /zones/nearest?lat=X&lng=Y`
3. Get quotes: `GET /partners/quotes?city=bangalore`
4. Create policy: `POST /policies`
5. Trigger event simulation: `POST /admin/simulate/weather`

### 📊 Monitoring
- ML Stats: `GET /admin/ml-stats`
- Health Check: `GET /health`
- API Docs: `GET /docs`

---
🤖 Built with **FastAPI**, **XGBoost**, **PostgreSQL**, **Redis**, and **React PWA**
        """,
        routes=app.routes,
    )

    openapi_schema["info"]["x-logo"] = {
        "url": "https://rapidcover.in/logo.png",
        "altText": "RapidCover Logo"
    }

    # Add tags metadata for better organization
    openapi_schema["tags"] = [
        {"name": "partners", "description": "Partner authentication, registration, and profile management"},
        {"name": "policies", "description": "Policy quotes, creation, and management"},
        {"name": "claims", "description": "Claims processing and status tracking"},
        {"name": "zones", "description": "Zone listing and GPS-based detection"},
        {"name": "triggers", "description": "Active trigger events"},
        {"name": "admin", "description": "Admin operations and simulation"},
        {"name": "admin-monitoring", "description": "ML model performance monitoring"},
        {"name": "notifications", "description": "Push notification subscriptions"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Rate limiting (Phase 4)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_error_logger = logging.getLogger("rapidcover.errors")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global fallback exception handler.

    Logs the full traceback internally for debugging while returning a clean,
    standardised JSON error body to the client — preventing verbose stack
    traces or internal details from leaking into API responses.
    """
    _error_logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Our team has been notified.",
        },
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
