from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database (SQLite for dev, PostgreSQL for production)
    database_url: str = "sqlite:///./rapidcover.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT Authentication
    jwt_secret: str = "development-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # External APIs
    openweathermap_api_key: str = ""
    waqi_api_key: str = ""
    cpcb_api_key: str = ""
    news_api_key: str = ""
    waqi_api_key: str = ""
    groq_api_key: str = ""

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_account_number: str = ""

    # Stripe (TEST MODE)
    stripe_secret_key: str = ""
    frontend_url: str = "http://localhost:5173"

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # App Settings
    debug: bool = True
    environment: str = "development"
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    json_logging: bool = False  # Enable JSON logging for production

    # Demo Mode Configuration (Phase 3)
    demo_mode: bool = False  # Global demo mode toggle - uses mock data instead of live APIs
    demo_exempt_cities: list[str] = []  # Cities that always use live data even in demo mode

    # Zero-Touch Automation
    auto_payout_enabled: bool = False  # Enable for demo mode to auto-pay approved claims

    # Web Push Notifications (VAPID)
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_claim_email: str = "mailto:admin@rapidcover.in"

    # Error Tracking (Phase 4 - Optional)
    sentry_dsn: str = ""  # Leave empty to disable Sentry

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
