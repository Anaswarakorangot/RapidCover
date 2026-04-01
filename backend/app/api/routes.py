from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from models  import Partner
from schemas import PartnerRegisterSchema, PartnerUpdateSchema, PartnerResponseSchema
from kyc     import KYCSchema
from db      import get_db          # your existing DB session dependency
from auth    import get_current_user, create_access_token, hash_password  # your existing auth helpers
from app.database import get_db
from app.schemas.kyc import KYCSchema
from app.database import get_db
from app.models.partner import Partner

router = APIRouter(prefix="/api", tags=["partners"])


# ── Register ──────────────────────────────────────────────────
@router.post("/register", response_model=PartnerResponseSchema, status_code=201)
def register(payload: PartnerRegisterSchema, db: Session = Depends(get_db)):
    existing = db.query(Partner).filter(Partner.phone == payload.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    kyc_data = None
    if payload.kyc:
        kyc_data = payload.kyc.dict()

    partner = Partner(
        name          = payload.name,
        phone         = payload.phone.replace(" ", ""),
        platform      = payload.platform,
        partner_id    = payload.partner_id,
        zone_id       = payload.zone_id,
        upi_id        = payload.upi_id,
        kyc           = kyc_data or {
            "aadhaar_number": None,
            "pan_number":     None,
            "kyc_status":     "skipped",
        },
    )

    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


# ── Get My Profile ────────────────────────────────────────────
@router.get("/profile/me", response_model=PartnerResponseSchema)
def get_profile(current_user: Partner = Depends(get_current_user)):
    return current_user


# ── Update Profile (name / language / UPI / KYC) ─────────────
@router.patch("/profile/me", response_model=PartnerResponseSchema)
def update_profile(
    payload: PartnerUpdateSchema,
    db: Session = Depends(get_db),
    current_user: Partner = Depends(get_current_user),
):
    if payload.name is not None:
        current_user.name = payload.name

    if payload.language_pref is not None:
        current_user.language_pref = payload.language_pref

    if payload.upi_id is not None:
        current_user.upi_id = payload.upi_id

    if payload.kyc is not None:
        # Merge incoming KYC with existing so we don't overwrite verified status
        existing_kyc = current_user.kyc or {}
        incoming_kyc = payload.kyc.dict(exclude_none=True)

        # Don't downgrade a verified KYC
        if existing_kyc.get("kyc_status") == "verified":
            incoming_kyc["kyc_status"] = "verified"

        current_user.kyc = {**existing_kyc, **incoming_kyc}

    db.commit()
    db.refresh(current_user)
    return current_user


# ── Validate Partner ID ───────────────────────────────────────
@router.get("/validate-partner-id")
def validate_partner_id(partner_id: str, platform: str, db: Session = Depends(get_db)):
    """
    Mock validation — in production, call the platform's API.
    Returns { valid: bool, message: str }
    """
    import re
    patterns = {
        "zepto":   r"^ZPT\d{6,}$",
        "blinkit": r"^BLK\d{6,}$",
    }
    pattern = patterns.get(platform)
    if not pattern:
        return {"valid": False, "message": "Unknown platform"}

    if re.match(pattern, partner_id.strip().upper()):
        # Check not already taken
        taken = db.query(Partner).filter(Partner.partner_id == partner_id.strip()).first()
        if taken:
            return {"valid": False, "message": "Partner ID already registered"}
        return {"valid": True, "message": "Partner ID verified ✓"}

    return {"valid": False, "message": f"Invalid {platform.capitalize()} partner ID format"}


# ── Get Zones ─────────────────────────────────────────────────
@router.get("/zones")
def get_zones(db: Session = Depends(get_db)):
    from models import Zone   # import your Zone model here
    zones = db.query(Zone).all()
    return zones


# ── Nearest Zones ─────────────────────────────────────────────
@router.get("/zones/nearest")
def get_nearest_zones(lat: float, lng: float, db: Session = Depends(get_db)):
    from models import Zone
    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    zones = db.query(Zone).all()
    results = []
    for zone in zones:
        dist = haversine(lat, lng, zone.latitude, zone.longitude)
        results.append({"zone": zone, "distance_km": round(dist, 2)})

    results.sort(key=lambda x: x["distance_km"])
    return results[:5]  # return top 5 nearest