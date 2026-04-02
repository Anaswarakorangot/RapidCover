from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.api.router import api_router
# Import models so they register with SQLAlchemy Base
from app.models import Partner, Zone, Policy, TriggerEvent, Claim
from app.services.scheduler import start_scheduler, stop_scheduler

settings = get_settings()
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting RapidCover API...")
    init_db()
    print("Database tables created.")
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
    allow_origins=DEFAULT_CORS_ORIGINS,
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
