from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.zone import Zone
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.partner import Partner
from app.schemas.zone import ZoneResponse, ZoneCreate, ZoneRiskUpdate
from app.services.claims_processor import (
    get_partner_runtime_metadata,
    get_zone_coverage_metadata,
    upsert_partner_runtime_metadata,
    upsert_zone_coverage_metadata,
)


class BCRResponse(BaseModel):
    """Benefit-to-Cost Ratio response for a city."""
    city: str
    total_premiums_collected: float
    total_claims_paid: float
    bcr: float  # claims_paid / premiums_collected
    loss_ratio: float  # BCR as percentage (BCR * 100)
    policy_count: int
    claim_count: int
    period_start: datetime
    period_end: datetime


class ZoneReassignmentRequest(BaseModel):
    """Request to reassign a partner to a new zone."""
    partner_id: int
    new_zone_id: int


class ZoneReassignmentResponse(BaseModel):
    """Response for zone reassignment."""
    partner_id: int
    old_zone_id: Optional[int]
    new_zone_id: int
    premium_adjustment: float  # Positive = credit, Negative = debit
    new_weekly_premium: float
    days_remaining: int
    policy_id: Optional[int]
    reassignment_logged: bool


class ZoneCoverageMetadataRequest(BaseModel):
    """Coverage metadata for ward/pin-code matching and density weighting."""
    pin_codes: list[str] = []
    density_weight: Optional[float] = None
    ward_name: Optional[str] = None


class ZoneCoverageMetadataResponse(BaseModel):
    zone_id: int
    pin_codes: list[str]
    density_weight: Optional[float] = None
    ward_name: Optional[str] = None
    updated_at: Optional[datetime] = None


class PartnerAvailabilityRequest(BaseModel):
    """Runtime partner availability controls used by claims processing."""
    pin_code: Optional[str] = None
    is_manual_offline: Optional[bool] = None
    manual_offline_until: Optional[datetime] = None
    leave_until: Optional[datetime] = None
    leave_note: Optional[str] = None


class PartnerAvailabilityResponse(BaseModel):
    partner_id: int
    pin_code: Optional[str] = None
    is_manual_offline: bool
    manual_offline_until: Optional[datetime] = None
    leave_until: Optional[datetime] = None
    leave_note: Optional[str] = None
    updated_at: Optional[datetime] = None


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates in km using Haversine formula."""
    R = 6371  # Earth's radius in km
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

router = APIRouter(prefix="/zones", tags=["zones"])

# =============================================================================
# Zone Reassignment 24-Hour Workflow Endpoints
# =============================================================================

from app.schemas.zone_reassignment import (
    ZoneReassignmentProposal,
    ZoneReassignmentResponse as NewReassignmentResponse,
    ZoneReassignmentListResponse,
    ZoneReassignmentActionResponse,
)
from app.models.zone_reassignment import ReassignmentStatus


@router.post("/reassignments/propose", response_model=NewReassignmentResponse)
def propose_zone_reassignment(
    proposal: ZoneReassignmentProposal,
    db: Session = Depends(get_db),
):
    """
    Propose a zone reassignment with 24-hour acceptance window.

    Creates a proposal that the partner must accept or reject within 24 hours.
    If no action is taken, the proposal expires automatically.

    This is the new workflow that replaces instant reassignment for cases
    where partner consent is required.
    """
    from app.services.zone_reassignment_service import propose_reassignment

    result, error = propose_reassignment(proposal.partner_id, proposal.new_zone_id, db)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return result


@router.post("/reassignments/{reassignment_id}/accept", response_model=ZoneReassignmentActionResponse)
def accept_zone_reassignment(
    reassignment_id: int,
    db: Session = Depends(get_db),
):
    """
    Accept a pending zone reassignment proposal.

    Must be called within 24 hours of the proposal.
    Updates the partner's zone_id and logs the change.
    """
    from app.services.zone_reassignment_service import accept_reassignment

    result, error = accept_reassignment(reassignment_id, db)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return result


@router.post("/reassignments/{reassignment_id}/reject", response_model=ZoneReassignmentActionResponse)
def reject_zone_reassignment(
    reassignment_id: int,
    db: Session = Depends(get_db),
):
    """
    Reject a pending zone reassignment proposal.

    The partner remains in their current zone.
    """
    from app.services.zone_reassignment_service import reject_reassignment

    result, error = reject_reassignment(reassignment_id, db)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return result


@router.get("/reassignments/{reassignment_id}", response_model=NewReassignmentResponse)
def get_zone_reassignment(
    reassignment_id: int,
    db: Session = Depends(get_db),
):
    """Get details of a specific zone reassignment."""
    from app.services.zone_reassignment_service import get_reassignment

    result = get_reassignment(reassignment_id, db)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reassignment not found",
        )

    return result


@router.delete("/reassignments/{reassignment_id}")
def delete_zone_reassignment(
    reassignment_id: int,
    db: Session = Depends(get_db),
):
    """Delete a zone reassignment (for testing/admin purposes)."""
    from app.models.zone_reassignment import ZoneReassignment

    reassignment = db.query(ZoneReassignment).filter(ZoneReassignment.id == reassignment_id).first()
    if not reassignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reassignment not found",
        )

    db.delete(reassignment)
    db.commit()
    return {"message": f"Reassignment {reassignment_id} deleted"}


@router.get("/reassignments", response_model=ZoneReassignmentListResponse)
def list_zone_reassignments(
    partner_id: Optional[int] = None,
    status_filter: Optional[ReassignmentStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List zone reassignments with optional filters.

    For admin: Lists all reassignments
    For partner: Filter by partner_id to see their proposals
    """
    from app.services.zone_reassignment_service import list_reassignments

    return list_reassignments(
        db,
        partner_id=partner_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post("/reassignments/expire-stale")
def expire_stale_reassignments(db: Session = Depends(get_db)):
    """
    Background job endpoint to expire stale proposals.

    Marks any proposals past their 24-hour window as expired.
    In production, this would be called by a scheduled job.
    """
    from app.services.zone_reassignment_service import expire_stale_proposals

    expired_count = expire_stale_proposals(db)

    return {
        "message": f"Expired {expired_count} stale proposals",
        "expired_count": expired_count,
    }





@router.get("/nearest")
def get_nearest_zones(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    limit: int = Query(3, ge=1, le=10, description="Maximum zones to return"),
    db: Session = Depends(get_db),
):
    """Find nearest zones to given GPS coordinates."""
    zones = db.query(Zone).all()

    zones_with_distance = []
    for zone in zones:
        if zone.dark_store_lat and zone.dark_store_lng:
            distance = haversine_distance(lat, lng, zone.dark_store_lat, zone.dark_store_lng)
            zones_with_distance.append({
                "zone": ZoneResponse.model_validate(zone),
                "distance_km": round(distance, 2),
            })

    zones_with_distance.sort(key=lambda x: x["distance_km"])
    return zones_with_distance[:limit]


@router.get("", response_model=list[ZoneResponse])
def list_zones(
    city: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all zones, optionally filtered by city."""
    query = db.query(Zone)

    if city:
        query = query.filter(Zone.city.ilike(f"%{city}%"))

    zones = query.offset(skip).limit(limit).all()
    return zones


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    """Get zone details including risk score."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    return zone


@router.get("/code/{zone_code}", response_model=ZoneResponse)
def get_zone_by_code(zone_code: str, db: Session = Depends(get_db)):
    """Get zone details by zone code (e.g., BLR-047)."""
    zone = db.query(Zone).filter(Zone.code == zone_code).first()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    return zone


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(zone_data: ZoneCreate, db: Session = Depends(get_db)):
    """Create a new zone (admin endpoint)."""
    existing = db.query(Zone).filter(Zone.code == zone_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone code already exists",
        )

    zone = Zone(
        code=zone_data.code,
        name=zone_data.name,
        city=zone_data.city,
        polygon=zone_data.polygon,
        dark_store_lat=zone_data.dark_store_lat,
        dark_store_lng=zone_data.dark_store_lng,
    )

    db.add(zone)
    db.commit()
    db.refresh(zone)

    return zone


@router.patch("/{zone_id}/risk", response_model=ZoneResponse)
def update_zone_risk(
    zone_id: int,
    risk_data: ZoneRiskUpdate,
    db: Session = Depends(get_db),
):
    """Update zone risk score (called by ML service)."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    if not 0 <= risk_data.risk_score <= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk score must be between 0 and 100",
        )

    zone.risk_score = risk_data.risk_score
    db.commit()
    db.refresh(zone)

    return zone


def calculate_city_bcr(city: str, db: Session, days: int = 7) -> BCRResponse:
    """
    Calculate Benefit-to-Cost Ratio for a city.

    BCR = total_claims_paid / total_premiums_collected

    Args:
        city: City name to calculate BCR for
        db: Database session
        days: Number of days to look back (default 7 for weekly)

    Returns BCRResponse with all financial metrics.
    """
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all zones in the city
    city_zones = db.query(Zone).filter(Zone.city.ilike(f"%{city}%")).all()
    zone_ids = [z.id for z in city_zones]

    if not zone_ids:
        return BCRResponse(
            city=city,
            total_premiums_collected=0.0,
            total_claims_paid=0.0,
            bcr=0.0,
            loss_ratio=0.0,
            policy_count=0,
            claim_count=0,
            period_start=period_start,
            period_end=now,
        )

    # Get partners in these zones
    partner_ids_query = db.query(Partner.id).filter(Partner.zone_id.in_(zone_ids))
    partner_ids = [p[0] for p in partner_ids_query.all()]

    # Calculate total premiums collected (from active policies created in period)
    total_premiums = (
        db.query(func.sum(Policy.weekly_premium))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0.0

    # Calculate total claims paid
    total_claims_paid = (
        db.query(func.sum(Claim.amount))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id.in_(partner_ids),
            Claim.status == ClaimStatus.PAID,
            Claim.paid_at >= period_start,
            Claim.paid_at <= now,
        )
        .scalar()
    ) or 0.0

    # Count policies and claims
    policy_count = (
        db.query(func.count(Policy.id))
        .filter(
            Policy.partner_id.in_(partner_ids),
            Policy.created_at >= period_start,
            Policy.created_at <= now,
        )
        .scalar()
    ) or 0

    claim_count = (
        db.query(func.count(Claim.id))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id.in_(partner_ids),
            Claim.status == ClaimStatus.PAID,
            Claim.paid_at >= period_start,
            Claim.paid_at <= now,
        )
        .scalar()
    ) or 0

    # Calculate BCR (avoid division by zero)
    bcr = total_claims_paid / total_premiums if total_premiums > 0 else 0.0
    loss_ratio = bcr * 100  # As percentage

    return BCRResponse(
        city=city,
        total_premiums_collected=round(total_premiums, 2),
        total_claims_paid=round(total_claims_paid, 2),
        bcr=round(bcr, 4),
        loss_ratio=round(loss_ratio, 2),
        policy_count=policy_count,
        claim_count=claim_count,
        period_start=period_start,
        period_end=now,
    )


@router.get("/bcr/{city}", response_model=BCRResponse)
def get_city_bcr(
    city: str,
    days: int = Query(7, ge=1, le=365, description="Number of days to calculate BCR for"),
    db: Session = Depends(get_db),
):
    """
    Get Benefit-to-Cost Ratio (BCR) for a city.

    BCR = total_claims_paid / total_premiums_collected

    - BCR < 1.0 means profitable (collecting more than paying out)
    - BCR > 1.0 means losing money
    - BCR > 1.2 triggers reinsurance (120% hard cap)

    Loss ratio is BCR expressed as percentage.
    """
    return calculate_city_bcr(city, db, days)


@router.get("/{zone_id}/coverage", response_model=ZoneCoverageMetadataResponse)
def get_zone_coverage(zone_id: int, db: Session = Depends(get_db)):
    """Get pin-code coverage and density metadata for a zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    return ZoneCoverageMetadataResponse(**get_zone_coverage_metadata(zone_id, db))


@router.put("/{zone_id}/coverage", response_model=ZoneCoverageMetadataResponse)
def update_zone_coverage(
    zone_id: int,
    request: ZoneCoverageMetadataRequest,
    db: Session = Depends(get_db),
):
    """Update ward/pin-code coverage and density metadata for a zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    if request.density_weight is not None and not 0 <= request.density_weight <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="density_weight must be between 0 and 1",
        )

    metadata = upsert_zone_coverage_metadata(
        zone_id,
        db,
        pin_codes=request.pin_codes,
        density_weight=request.density_weight,
        ward_name=request.ward_name,
    )
    return ZoneCoverageMetadataResponse(**metadata)


@router.get("/partners/{partner_id}/availability", response_model=PartnerAvailabilityResponse)
def get_partner_availability(partner_id: int, db: Session = Depends(get_db)):
    """Get runtime availability controls for a partner."""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    return PartnerAvailabilityResponse(**get_partner_runtime_metadata(partner_id, db))


@router.put("/partners/{partner_id}/availability", response_model=PartnerAvailabilityResponse)
def update_partner_availability(
    partner_id: int,
    request: PartnerAvailabilityRequest,
    db: Session = Depends(get_db),
):
    """Update runtime availability controls for a partner."""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    metadata = upsert_partner_runtime_metadata(
        partner_id,
        db,
        **{
            field: getattr(request, field)
            for field in request.model_fields_set
        },
    )
    return PartnerAvailabilityResponse(**metadata)


@router.post("/reassign", response_model=ZoneReassignmentResponse)
def reassign_partner_zone(
    reassignment: ZoneReassignmentRequest,
    db: Session = Depends(get_db),
):
    """
    Reassign a partner to a new zone mid-week.

    When Zepto/Blinkit reassigns a partner to a new dark store:
    - Recalculates premium for remaining days based on new zone's risk
    - Computes credit/debit adjustment for next renewal
    - Logs reassignment history in partner record

    Returns adjustment details for frontend display.
    """
    from app.services.premium import calculate_premium

    # Get partner
    partner = db.query(Partner).filter(Partner.id == reassignment.partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    # Get new zone
    new_zone = db.query(Zone).filter(Zone.id == reassignment.new_zone_id).first()
    if not new_zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    old_zone_id = partner.zone_id

    # Get current active policy
    now = datetime.utcnow()
    active_policy = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > now,
        )
        .first()
    )

    premium_adjustment = 0.0
    new_weekly_premium = 0.0
    days_remaining = 0
    policy_id = None

    if active_policy:
        policy_id = active_policy.id

        # Calculate days remaining in current policy
        days_remaining = max(0, (active_policy.expires_at - now).days)

        # Get old zone for comparison
        old_zone = db.query(Zone).filter(Zone.id == old_zone_id).first() if old_zone_id else None

        # Calculate new premium based on new zone
        new_quote = calculate_premium(active_policy.tier, new_zone)
        old_daily_rate = active_policy.weekly_premium / 7
        new_daily_rate = new_quote.final_premium / 7

        # Premium adjustment = (old_rate - new_rate) * days_remaining
        # Positive = credit to partner (new zone is cheaper)
        # Negative = debit from partner (new zone is more expensive)
        premium_adjustment = round((old_daily_rate - new_daily_rate) * days_remaining, 2)
        new_weekly_premium = new_quote.final_premium

    # Update partner's zone
    zone_history = list(partner.zone_history or [])
    zone_history.append({
        "old_zone_id": old_zone_id,
        "new_zone_id": reassignment.new_zone_id,
        "effective_at": now.isoformat(),
        "policy_id": policy_id,
        "premium_adjustment": premium_adjustment,
        "new_weekly_premium": new_weekly_premium,
        "days_remaining": days_remaining,
    })
    partner.zone_history = zone_history[-50:]
    partner.zone_id = reassignment.new_zone_id
    db.commit()
    db.refresh(partner)

    return ZoneReassignmentResponse(
        partner_id=partner.id,
        old_zone_id=old_zone_id,
        new_zone_id=reassignment.new_zone_id,
        premium_adjustment=premium_adjustment,
        new_weekly_premium=new_weekly_premium,
        days_remaining=days_remaining,
        policy_id=policy_id,
        reassignment_logged=True,
    )



# =============================================================================
# PLATFORM ACTIVITY ENDPOINTS (Feature 3)
# =============================================================================

class PartnerPlatformActivityResponse(BaseModel):
    partner_id: int
    platform_logged_in: bool
    active_shift: bool
    orders_accepted_recent: int
    orders_completed_recent: int
    last_app_ping: str
    zone_dwell_minutes: int
    suspicious_inactivity: bool
    platform: str
    updated_at: str
    source: str


class PartnerPlatformActivityRequest(BaseModel):
    platform_logged_in: Optional[bool] = None
    active_shift: Optional[bool] = None
    orders_accepted_recent: Optional[int] = None
    orders_completed_recent: Optional[int] = None
    last_app_ping: Optional[str] = None
    zone_dwell_minutes: Optional[int] = None
    suspicious_inactivity: Optional[bool] = None
    platform: Optional[str] = None


class PartnerPlatformEligibilityResponse(BaseModel):
    partner_id: int
    eligible: bool
    score: float
    reasons: list[dict]
    activity: dict


@router.get(
    "/partners/{partner_id}/activity",
    response_model=PartnerPlatformActivityResponse,
    tags=["zones"],
)
def get_partner_activity(partner_id: int, db: Session = Depends(get_db)):
    """
    GET /zones/partners/{partner_id}/activity

    Return current simulated platform activity for a delivery partner.
    Shows Zomato/Swiggy/Zepto/Blinkit login state, shift, orders, and ping.
    """
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Partner {partner_id} not found")

    from app.services.claims_processor import get_db_partner_platform_activity
    activity = get_db_partner_platform_activity(partner_id, db)
    return PartnerPlatformActivityResponse(**activity)


@router.put(
    "/partners/{partner_id}/activity",
    response_model=PartnerPlatformActivityResponse,
    tags=["zones"],
)
def update_partner_activity(
    partner_id: int,
    request: PartnerPlatformActivityRequest,
    db: Session = Depends(get_db),
):
    """
    PUT /zones/partners/{partner_id}/activity

    Admin control: toggle partner platform activity state.
    Set active_shift=false to simulate partner being offline.
    Set suspicious_inactivity=true to simulate fraud signal.
    Claim approval logic reads this data before authorising payout.
    """
    from fastapi import HTTPException
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail=f"Partner {partner_id} not found")

    from app.services.claims_processor import upsert_db_partner_platform_activity
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    activity = upsert_db_partner_platform_activity(partner_id, db, **updates)
    return PartnerPlatformActivityResponse(**activity)


@router.get(
    "/partners/{partner_id}/activity/eligibility",
    response_model=PartnerPlatformEligibilityResponse,
    tags=["zones"],
)
def get_partner_activity_eligibility(partner_id: int, db: Session = Depends(get_db)):
    """
    GET /zones/partners/{partner_id}/activity/eligibility

    Evaluate whether this partner's platform activity qualifies them for payout.
    Returns check-by-check breakdown (logged in, active shift, recent orders, ping).
    """
    from fastapi import HTTPException
    from app.services.external_apis import evaluate_partner_platform_eligibility

    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail=f"Partner {partner_id} not found")

    result = evaluate_partner_platform_eligibility(partner_id)
    return PartnerPlatformEligibilityResponse(**result)


@router.get("/partners/activity/bulk", tags=["zones"])
def get_all_partners_activity(
    zone_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    GET /zones/partners/activity/bulk

    Return platform activity for all partners (optionally filtered by zone).
    Used by admin LiveDataPanel to show fleet-wide activity at a glance.
    """
    from app.services.claims_processor import get_db_partner_platform_activity
    from app.services.external_apis import evaluate_partner_platform_eligibility

    query = db.query(Partner).filter(Partner.is_active == True)
    if zone_id:
        query = query.filter(Partner.zone_id == zone_id)
    partners = query.limit(200).all()

    results = []
    for p in partners:
        activity = get_db_partner_platform_activity(p.id, db)
        eligibility = evaluate_partner_platform_eligibility(p.id)
        results.append({
            "partner_id": p.id,
            "partner_name": p.name,
            "zone_id": p.zone_id,
            "activity": activity,
            "platform_eligible": eligibility["eligible"],
            "platform_score": eligibility["score"],
        })

    return {
        "total": len(results),
        "zone_id": zone_id,
        "partners": results,
    }