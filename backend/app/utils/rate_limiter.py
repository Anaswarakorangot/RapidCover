"""
Rate Limiter Configuration (Phase 4)

Centralized rate limiting using SlowAPI.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address


# Global rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Global default for all endpoints
    storage_uri="memory://",  # Use in-memory storage (Redis optional)
)


# Common rate limit strings
RATE_LIMITS = {
    "auth_register": "10/minute",      # Registration: 10 per minute
    "auth_login": "20/minute",         # Login: 20 per minute
    "auth_verify": "20/minute",        # OTP verify: 20 per minute
    "api_general": "100/minute",       # General API: 100 per minute
    "api_heavy": "30/minute",          # Heavy operations: 30 per minute
    "admin_simulate": "10/minute",     # Admin simulations: 10 per minute
}
