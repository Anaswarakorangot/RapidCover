from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.partner import Partner
from app.schemas.partner import (
    PartnerCreate,
    PartnerResponse,
    PartnerLogin,
    OTPVerify,
    TokenResponse,
    PartnerUpdate,
)
from app.services.auth import (
    generate_otp,
    store_otp,
    verify_otp,
    create_access_token,
    get_current_partner,
)

router = APIRouter(prefix="/partners", tags=["partners"])


@router.post("/register", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
def register_partner(partner_data: PartnerCreate, db: Session = Depends(get_db)):
    """Register a new delivery partner."""
    # Check if phone already exists
    existing = db.query(Partner).filter(Partner.phone == partner_data.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )

    partner = Partner(
        phone=partner_data.phone,
        name=partner_data.name,
        platform=partner_data.platform,
        partner_id=partner_data.partner_id,
        zone_id=partner_data.zone_id,
        language_pref=partner_data.language_pref,
    )

    db.add(partner)
    db.commit()
    db.refresh(partner)

    return partner


@router.post("/login", status_code=status.HTTP_200_OK)
def request_otp(login_data: PartnerLogin, db: Session = Depends(get_db)):
    """Request OTP for login."""
    partner = db.query(Partner).filter(Partner.phone == login_data.phone).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not registered",
        )

    if not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    otp = generate_otp()
    store_otp(login_data.phone, otp)

    # In production, send OTP via SMS/WhatsApp
    # For development, return OTP in response
    return {"message": "OTP sent", "otp": otp}  # Remove otp in production


@router.post("/verify", response_model=TokenResponse)
def verify_login(verify_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP and return JWT token."""
    partner = db.query(Partner).filter(Partner.phone == verify_data.phone).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not registered",
        )

    if not verify_otp(verify_data.phone, verify_data.otp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    access_token = create_access_token(data={"sub": str(partner.id)})
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=PartnerResponse)
def get_current_partner_profile(partner: Partner = Depends(get_current_partner)):
    """Get current partner's profile."""
    return partner


@router.patch("/me", response_model=PartnerResponse)
def update_partner_profile(
    update_data: PartnerUpdate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """Update current partner's profile."""
    if update_data.name is not None:
        partner.name = update_data.name
    if update_data.zone_id is not None:
        partner.zone_id = update_data.zone_id
    if update_data.language_pref is not None:
        partner.language_pref = update_data.language_pref

    db.commit()
    db.refresh(partner)
    return partner
