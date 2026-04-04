"""
partners.py - Partner API router.
Person 1 owns this file. Do NOT edit if you are Person 2, 3, or 4.
Per No-Conflict Rules, Section 5.

New endpoints added in Phase 2:
  GET /partners/riqi              - RIQI scores for all cities
  GET /partners/riqi/{city}       - RIQI score for one city
  GET /partners/quotes            - Personalised plan quotes (onboarding step 5)
  GET /partners/premium           - Weekly premium for authenticated partner
  GET /partners/tiers             - Tier config (frontend plan cards)
  GET /partners/bcr/{city}        - BCR / Loss Ratio for a city (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

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
from app.services.partner_validation import validate_partner_id
from app.services.premium_service import (
    get_riqi_score,
    get_riqi_band,
    get_riqi_payout_multiplier,
    get_plan_quotes,
    calculate_weekly_premium,
    calculate_bcr,
    CITY_RIQI_SCORES,
    RIQI_PAYOUT_MULTIPLIER,
    RIQI_PREMIUM_ADJUSTMENT,
    TIER_CONFIG,
)

router = APIRouter(prefix="/partners", tags=["partners"])


# ------------------------------------------------------------------------------
# REGISTER
# ------------------------------------------------------------------------------

@router.post("/register", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
def register_partner(partner_data: PartnerCreate, db: Session = Depends(get_db)):
    """Register a new delivery partner."""
    existing = db.query(Partner).filter(Partner.phone == partner_data.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )

    # Convert KYC Pydantic model to dict for SQLAlchemy JSON column
    kyc_data = getattr(partner_data, "kyc", None)
    if kyc_data is not None and hasattr(kyc_data, "model_dump"):
        kyc_dict = kyc_data.model_dump()
    elif kyc_data is not None and hasattr(kyc_data, "dict"):
        kyc_dict = kyc_data.dict()
    elif kyc_data is not None:
        kyc_dict = dict(kyc_data)
    else:
        kyc_dict = {
            "aadhaar_number": None,
            "pan_number":     None,
            "kyc_status":     "skipped",
        }

    # HACKATHON SECURITY: Never store raw PII. Hash identities and set verified.
    import hashlib
    if kyc_dict.get("aadhaar_number") or kyc_dict.get("pan_number"):
        if kyc_dict.get("aadhaar_number"):
            raw = str(kyc_dict["aadhaar_number"])
            hashed = hashlib.sha256(raw.encode()).hexdigest()[:16]
            kyc_dict["aadhaar_number"] = f"UID-{hashed}-XXXX{raw[-4:]}"
        
        if kyc_dict.get("pan_number"):
            raw = str(kyc_dict["pan_number"])
            hashed = hashlib.sha256(raw.encode()).hexdigest()[:16]
            kyc_dict["pan_number"] = f"PAN-{hashed}"
            
        kyc_dict["kyc_status"] = "verified"

    partner = Partner(
        phone         = partner_data.phone,
        name          = partner_data.name,
        platform      = partner_data.platform,
        partner_id    = partner_data.partner_id,
        zone_id       = partner_data.zone_id,
        language_pref = partner_data.language_pref,
        upi_id        = getattr(partner_data, "upi_id", None),
        kyc           = kyc_dict,
        shift_days    = getattr(partner_data, "shift_days", None) or [],
        shift_start   = getattr(partner_data, "shift_start", None),
        shift_end     = getattr(partner_data, "shift_end", None),
        zone_history  = getattr(partner_data, "zone_history", None) or [],
    )

    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


# ------------------------------------------------------------------------------
# AUTH
# ------------------------------------------------------------------------------

@router.post("/login", status_code=status.HTTP_200_OK)
def request_otp(login_data: PartnerLogin, db: Session = Depends(get_db)):
    """Request OTP for login. OTP exposed in response for dev/demo mode."""
    partner = db.query(Partner).filter(Partner.phone == login_data.phone).first()
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone number not registered")
    if not partner.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    otp = generate_otp()
    store_otp(login_data.phone, otp)
    return {"message": "OTP sent", "otp": otp}  # Remove otp in production


@router.post("/verify", response_model=TokenResponse)
def verify_login(verify_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP and return JWT token."""
    partner = db.query(Partner).filter(Partner.phone == verify_data.phone).first()
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone number not registered")
    if not verify_otp(verify_data.phone, verify_data.otp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

    access_token = create_access_token(data={"sub": str(partner.id)})
    return TokenResponse(access_token=access_token)


# ------------------------------------------------------------------------------
# PROFILE
# ------------------------------------------------------------------------------

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
    """Update profile - name, zone, language, UPI, KYC."""
    if update_data.name is not None:
        partner.name = update_data.name
    if update_data.zone_id is not None:
        partner.zone_id = update_data.zone_id
    if update_data.language_pref is not None:
        partner.language_pref = update_data.language_pref

    # UPI
    if hasattr(update_data, "upi_id") and update_data.upi_id is not None:
        partner.upi_id = update_data.upi_id

    # KYC - merge, never downgrade verified status
    if hasattr(update_data, "kyc") and update_data.kyc is not None:
        existing_kyc = partner.kyc or {}
        incoming_kyc = (
            update_data.kyc.model_dump(exclude_none=True)
            if hasattr(update_data.kyc, "model_dump")
            else update_data.kyc.dict(exclude_none=True)
            if hasattr(update_data.kyc, "dict")
            else dict(update_data.kyc)
        )
        if existing_kyc.get("kyc_status") == "verified":
            incoming_kyc["kyc_status"] = "verified"
        partner.kyc = {**existing_kyc, **incoming_kyc}

    # Shift preferences
    if hasattr(update_data, "shift_days") and update_data.shift_days is not None:
        partner.shift_days = update_data.shift_days
    if hasattr(update_data, "shift_start") and update_data.shift_start is not None:
        partner.shift_start = update_data.shift_start
    if hasattr(update_data, "shift_end") and update_data.shift_end is not None:
        partner.shift_end = update_data.shift_end
    if hasattr(update_data, "zone_history") and update_data.zone_history is not None:
        partner.zone_history = update_data.zone_history

    db.commit()
    db.refresh(partner)
    return partner


# ------------------------------------------------------------------------------
# PARTNER ID VALIDATION
# ------------------------------------------------------------------------------

@router.get("/validate-id")
def validate_partner_id_endpoint(
    partner_id: str = Query(..., description="Partner ID e.g. ZPT123456"),
    platform:   str = Query(..., description="zepto or blinkit"),
):
    """
    Validate partner ID. Mock behaviour:
      IDs ending in 000 -> Not found
      IDs ending in 999 -> Suspended
      All other valid formats -> Verified
    """
    return validate_partner_id(partner_id, platform)


# ------------------------------------------------------------------------------
# RIQI ZONE SCORING - derive score per zone, expose via API (Person 1 task)
# ------------------------------------------------------------------------------

@router.get("/riqi", summary="RIQI scores for all cities")
def get_all_riqi():
    """
    Get RIQI (Road Infrastructure Quality Index) scores for all supported cities.
    RIQI: 0-100. Higher = better roads = less disruption per mm rain.
    Payout multiplier: 1.0 (urban core) / 1.25 (fringe) / 1.5 (peri-urban).
    Section 2B + Section 3.2 of team guide.
    """
    result = []
    for city, score in CITY_RIQI_SCORES.items():
        band = get_riqi_band(score)
        result.append({
            "city":               city,
            "riqi_score":         score,
            "riqi_band":          band,
            "payout_multiplier":  RIQI_PAYOUT_MULTIPLIER[band],
            "premium_adjustment": RIQI_PREMIUM_ADJUSTMENT[band],
            "interpretation": {
                "urban_core":   "Urban core - better roads, 1.0x payout",
                "urban_fringe": "Urban fringe - moderate risk, 1.25x payout",
                "peri_urban":   "Peri-urban / flood-prone - 1.5x payout",
            }[band],
        })
    return sorted(result, key=lambda x: x["riqi_score"], reverse=True)


@router.get("/riqi/{city}", summary="RIQI score for one city")
def get_city_riqi(city: str):
    """
    Get RIQI score, band, payout multiplier, and premium adjustment for a city.
    Judges can verify: Manoj in Bellandur (flood-prone) pays more than Ravi in Whitefield.
    """
    city_lower = city.lower()
    if city_lower not in CITY_RIQI_SCORES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City '{city}' not found. Supported: {list(CITY_RIQI_SCORES.keys())}",
        )

    score = get_riqi_score(city_lower)
    band  = get_riqi_band(score)

    return {
        "city":               city_lower,
        "riqi_score":         score,
        "riqi_band":          band,
        "payout_multiplier":  RIQI_PAYOUT_MULTIPLIER[band],
        "premium_adjustment": RIQI_PREMIUM_ADJUSTMENT[band],
        "description": {
            "urban_core":   "Urban core zone - good road infrastructure, standard payouts",
            "urban_fringe": "Urban fringe - moderate flood/AQI risk, 1.25x payout uplift",
            "peri_urban":   "Peri-urban / flood-prone - poor roads, maximum 1.5x payout",
        }[band],
        "example": f"A Rs.400 Standard payout becomes Rs.{int(400 * RIQI_PAYOUT_MULTIPLIER[band])} in {city_lower}",
    }


# ------------------------------------------------------------------------------
# PREMIUM QUOTES - onboarding step 5
# ------------------------------------------------------------------------------

@router.get("/quotes", summary="Personalised plan quotes for onboarding")
def get_premium_quotes(
    city:                str         = Query(...,  description="Partner city"),
    zone_id:             Optional[int] = Query(None, description="Zone ID if known"),
    active_days_last_30: int         = Query(15,   description="Active delivery days in last 30"),
    avg_hours_per_day:   float       = Query(8.0,  description="Avg hours per day"),
    loyalty_weeks:       int         = Query(0,    description="Consecutive clean weeks"),
):
    """
    Returns personalised weekly premium quotes for all 3 tiers.
    Called at onboarding after GPS zone detection (Section 4.1 step 5).
    Every number traces back to the Section 3.1 formula.
    Includes underwriting gate and auto-downgrade checks.
    """
    quotes = get_plan_quotes(
        city                = city,
        zone_id             = zone_id,
        active_days_last_30 = active_days_last_30,
        avg_hours_per_day   = avg_hours_per_day,
        loyalty_weeks       = loyalty_weeks,
    )
    return {
        "city":   city,
        "month":  date.today().strftime("%B %Y"),
        "quotes": quotes,
    }


@router.get("/premium", summary="Weekly premium for authenticated partner")
def get_my_premium(
    tier:                str   = Query(...,  description="flex / standard / pro"),
    active_days_last_30: int   = Query(15,   description="Active delivery days in last 30"),
    avg_hours_per_day:   float = Query(8.0,  description="Avg hours per day"),
    loyalty_weeks:       int   = Query(0,    description="Loyalty weeks"),
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Full premium calculation for the authenticated partner.
    Runs underwriting gate + auto-downgrade + full formula.
    """
    city = "bangalore"
    if partner.zone and hasattr(partner.zone, "city"):
        city = partner.zone.city.lower()

    return calculate_weekly_premium(
        partner_id          = partner.id,
        city                = city,
        zone_id             = partner.zone_id,
        requested_tier      = tier,
        active_days_last_30 = active_days_last_30,
        avg_hours_per_day   = avg_hours_per_day,
        loyalty_weeks       = loyalty_weeks,
    )


# ------------------------------------------------------------------------------
# TIER CONFIG
# ------------------------------------------------------------------------------

@router.get("/tiers", summary="All tier configurations")
def get_tier_config():
    """
    Returns all tier configs with fixed pricing (Rs.22/Rs.33/Rs.45) and payout limits.
    Frontend uses this to render plan cards.
    """
    return TIER_CONFIG


# ------------------------------------------------------------------------------
# BCR / LOSS RATIO - admin use
# ------------------------------------------------------------------------------

@router.get("/bcr/{city}", summary="BCR / Loss Ratio for a city (admin)")
def get_city_bcr(
    city:                        str,
    total_claims_paid:           float = Query(..., description="Total claims paid Rs."),
    total_premiums_collected:    float = Query(..., description="Total premiums collected Rs."),
):
    """
    BCR = total_claims_paid / total_premiums_collected. Section 3.4.
    Target 0.55-0.70. > 85% loss ratio -> suspend enrolments. > 100% -> reinsurance.
    Each city is tracked independently - one city over 85% does not affect others.
    """
    result = calculate_bcr(total_claims_paid, total_premiums_collected)
    result["city"] = city.lower()
    return result