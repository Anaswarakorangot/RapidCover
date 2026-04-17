"""
Admin Authentication API
-------------------------
JWT-based authentication for admin panel access.

Endpoints:
- POST /admin/auth/register - Create new admin account
- POST /admin/auth/login - Login with email + password
- GET /admin/auth/me - Get current admin profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt

from app.config import get_settings
from app.database import get_db
from app.models.admin import Admin
from app.schemas.admin import AdminRegister, AdminLogin, AdminToken, AdminResponse
from app.core.admin_deps import get_current_admin
from app.utils.time_utils import utcnow

settings = get_settings()
router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_admin_token(admin_id: int) -> str:
    """
    Create JWT token for admin with 7-day expiry.

    Token includes:
    - sub: admin ID
    - type: "admin" (to distinguish from partner tokens)
    - exp: expiration timestamp
    """
    payload = {
        "sub": str(admin_id),
        "type": "admin",
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@router.post("/register", response_model=AdminToken, status_code=status.HTTP_201_CREATED)
def register_admin(data: AdminRegister, db: Session = Depends(get_db)):
    """
    Register new admin account.

    Returns:
        AdminToken with access_token and admin profile

    Raises:
        400: Email already registered
    """
    # Check if email already exists
    existing = db.query(Admin).filter(Admin.email == data.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create admin
    admin = Admin(
        email=data.email.lower(),
        hashed_password=pwd_context.hash(data.password),
        full_name=data.full_name,
        is_active=True,
        is_superadmin=False  # First admin must be manually promoted in DB
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Generate token
    token = create_admin_token(admin.id)

    return AdminToken(
        access_token=token,
        admin=AdminResponse.model_validate(admin)
    )


@router.post("/login", response_model=AdminToken)
def login_admin(data: AdminLogin, db: Session = Depends(get_db)):
    """
    Login with email + password.

    Updates last_login timestamp on successful login.

    Returns:
        AdminToken with access_token and admin profile

    Raises:
        401: Invalid credentials
        403: Account inactive
    """
    # Find admin by email
    admin = db.query(Admin).filter(Admin.email == data.email.lower()).first()

    # Verify credentials
    if not admin or not pwd_context.verify(data.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if account is active
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive - contact administrator"
        )

    # Update last login timestamp
    admin.last_login = utcnow()
    db.commit()
    db.refresh(admin)

    # Generate token
    token = create_admin_token(admin.id)

    return AdminToken(
        access_token=token,
        admin=AdminResponse.model_validate(admin)
    )


@router.get("/me", response_model=AdminResponse)
def get_admin_profile(admin: Admin = Depends(get_current_admin)):
    """
    Get current admin profile from JWT token.

    Requires valid admin JWT token in Authorization header.
    """
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
    return AdminResponse.model_validate(admin)
