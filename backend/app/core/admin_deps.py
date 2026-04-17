"""
Admin Dependencies - JWT verification for admin endpoints

NOTE: For this hackathon demo, admin panel endpoints are intentionally
accessible without authentication. get_current_admin returns None when
no token is provided, and endpoints continue to function normally.
"""

from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.admin import Admin

settings = get_settings()
# auto_error=False → returns None instead of 401 when no token is provided
security = HTTPBearer(auto_error=False)


def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Admin]:
    """
    Optionally verify admin JWT token and return admin object.

    Returns None (instead of raising 401) when no token is provided,
    so all admin panel endpoints remain accessible during demo mode.
    Returns the Admin object when a valid token is provided.
    """
    # No token provided — allow access in demo mode
    if not credentials:
        return None

    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        admin_id = int(payload.get("sub"))
        token_type = payload.get("type")

        # Verify this is an admin token (not a partner token)
        if token_type != "admin":
            return None

        # Get admin from database
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if not admin or not admin.is_active:
            return None

        return admin

    except (JWTError, Exception):
        return None
