"""
Seed data for dark store zones across Bangalore, Mumbai, and Delhi.
Each zone represents a dark store fulfillment center for Q-Commerce operations.
"""

import random
from sqlalchemy.orm import Session
from app.models.zone import Zone


# Real coordinates for dark store locations
ZONE_DATA = [
    # Bangalore zones
    {
        "code": "BLR-001",
        "name": "Koramangala",
        "city": "Bangalore",
        "dark_store_lat": 12.9352,
        "dark_store_lng": 77.6245,
    },
    {
        "code": "BLR-002",
        "name": "Indiranagar",
        "city": "Bangalore",
        "dark_store_lat": 12.9784,
        "dark_store_lng": 77.6408,
    },
    {
        "code": "BLR-003",
        "name": "HSR Layout",
        "city": "Bangalore",
        "dark_store_lat": 12.9116,
        "dark_store_lng": 77.6389,
    },
    {
        "code": "BLR-004",
        "name": "Whitefield",
        "city": "Bangalore",
        "dark_store_lat": 12.9698,
        "dark_store_lng": 77.7500,
    },
    {
        "code": "BLR-005",
        "name": "Bellandur",
        "city": "Bangalore",
        "dark_store_lat": 12.9260,
        "dark_store_lng": 77.6762,
    },
    # Mumbai zones
    {
        "code": "MUM-001",
        "name": "Andheri",
        "city": "Mumbai",
        "dark_store_lat": 19.1136,
        "dark_store_lng": 72.8697,
    },
    {
        "code": "MUM-002",
        "name": "Bandra",
        "city": "Mumbai",
        "dark_store_lat": 19.0596,
        "dark_store_lng": 72.8295,
    },
    {
        "code": "MUM-003",
        "name": "Powai",
        "city": "Mumbai",
        "dark_store_lat": 19.1176,
        "dark_store_lng": 72.9060,
    },
    # Delhi zones
    {
        "code": "DEL-001",
        "name": "Connaught Place",
        "city": "Delhi",
        "dark_store_lat": 28.6315,
        "dark_store_lng": 77.2167,
    },
    {
        "code": "DEL-002",
        "name": "Saket",
        "city": "Delhi",
        "dark_store_lat": 28.5244,
        "dark_store_lng": 77.2065,
    },
    {
        "code": "DEL-003",
        "name": "Dwarka",
        "city": "Delhi",
        "dark_store_lat": 28.5921,
        "dark_store_lng": 77.0460,
    },
    # Hyderabad zones (MANDATORY)
    {
        "code": "HYD-001",
        "name": "Chanda Nagar West",
        "city": "Hyderabad",
        "dark_store_lat": 17.4923,
        "dark_store_lng": 78.3308,
        "polygon": "[[17.4993, 78.3228], [17.4993, 78.3388], [17.4853, 78.3388], [17.4853, 78.3228], [17.4993, 78.3228]]"
    },
    {
        "code": "HYD-002",
        "name": "Kukatpally KPHB",
        "city": "Hyderabad",
        "dark_store_lat": 17.4816,
        "dark_store_lng": 78.3940,
        "polygon": "[[17.4886, 78.3860], [17.4886, 78.4020], [17.4746, 78.4020], [17.4746, 78.3860], [17.4886, 78.3860]]"
    },
    {
        "code": "HYD-003",
        "name": "Ramachandrapuram",
        "city": "Hyderabad",
        "dark_store_lat": 17.4987,
        "dark_store_lng": 78.3153,
        "polygon": "[[17.5057, 78.3073], [17.5057, 78.3233], [17.4917, 78.3233], [17.4917, 78.3073], [17.5057, 78.3073]]"
    },
    {
        "code": "HYD-004",
        "name": "Himayatnagar",
        "city": "Hyderabad",
        "dark_store_lat": 17.3994,
        "dark_store_lng": 78.4883,
        "polygon": "[[17.4064, 78.4803], [17.4064, 78.4963], [17.3924, 78.4963], [17.3924, 78.4803], [17.4064, 78.4803]]"
    },
    # More Bangalore expansion
    {
        "code": "BLR-006",
        "name": "Hebbal",
        "city": "Bangalore",
        "dark_store_lat": 13.0354,
        "dark_store_lng": 77.5988,
    },
    {
        "code": "BLR-007",
        "name": "Jayanagar",
        "city": "Bangalore",
        "dark_store_lat": 12.9250,
        "dark_store_lng": 77.5938,
    },
]


def seed_zones(db: Session, randomize_risk: bool = True) -> list[Zone]:
    """
    Seed the database with dark store zones.

    Args:
        db: Database session
        randomize_risk: If True, assign random risk scores (20-80) for demo

    Returns:
        List of created Zone objects
    """
    created_zones = []

    for zone_data in ZONE_DATA:
        # Check if zone already exists
        existing = db.query(Zone).filter(Zone.code == zone_data["code"]).first()
        if existing:
            continue

        # Assign risk score
        if randomize_risk:
            risk_score = random.uniform(20, 80)
        else:
            risk_score = 50.0

        zone = Zone(
            code=zone_data["code"],
            name=zone_data["name"],
            city=zone_data["city"],
            dark_store_lat=zone_data["dark_store_lat"],
            dark_store_lng=zone_data["dark_store_lng"],
            polygon=zone_data.get("polygon"),
            risk_score=round(risk_score, 1),
        )

        db.add(zone)
        created_zones.append(zone)

    db.commit()

    # Refresh to get IDs
    for zone in created_zones:
        db.refresh(zone)

    return created_zones


def get_zone_count(db: Session) -> int:
    """Get the total number of zones in the database."""
    return db.query(Zone).count()
