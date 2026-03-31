from math import radians, sin, cos, sqrt, atan2

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.zone import Zone
from app.schemas.zone import ZoneResponse, ZoneCreate, ZoneRiskUpdate


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates in km using Haversine formula."""
    R = 6371  # Earth's radius in km
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

router = APIRouter(prefix="/zones", tags=["zones"])


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
