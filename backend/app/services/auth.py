from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.database import get_db
from app.models.partner import Partner

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# In-memory OTP storage (use Redis in production)
otp_store: dict[str, tuple[str, datetime]] = {}


def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return "".join([str(secrets.randbelow(10)) for _ in range(6)])


def store_otp(phone: str, otp: str) -> None:
    """Store OTP with 5-minute expiry."""
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    otp_store[phone] = (otp, expiry)


def verify_otp(phone: str, otp: str) -> bool:
    """Verify OTP and remove from store if valid."""
    if phone not in otp_store:
        return False

    stored_otp, expiry = otp_store[phone]
    if datetime.now(timezone.utc) > expiry:
        del otp_store[phone]
        return False

    if stored_otp != otp:
        return False

    del otp_store[phone]
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def get_current_partner(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Partner:
    """Get current authenticated partner from JWT token."""
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    partner_id = payload.get("sub")
    if partner_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    partner = db.query(Partner).filter(Partner.id == int(partner_id)).first()
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    if not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner account is deactivated",
        )

    return partner


def hash_aadhaar(aadhaar: str) -> str:
    """Hash Aadhaar number for storage (we never store plain Aadhaar)."""
    import hashlib
    return hashlib.sha256(aadhaar.encode()).hexdigest()
