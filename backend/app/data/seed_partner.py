"""
Seed data for a default test partner to simplify development after DB resets.
"""

from sqlalchemy.orm import Session
from app.models.partner import Partner, Platform, Language
from app.models.zone import Zone


def seed_partners(db: Session) -> list[Partner]:
    """
    Seed the database with a default test partner.
    """
    # Define test partner data
    test_phone = "9988776655"
    
    # Check if partner already exists
    existing = db.query(Partner).filter(Partner.phone == test_phone).first()
    if existing:
        return [existing]

    # Get a default zone (BLR-001)
    default_zone = db.query(Zone).filter(Zone.code == "BLR-001").first()
    zone_id = default_zone.id if default_zone else None

    # Create the test partner
    test_partner = Partner(
        phone=test_phone,
        name="Test Manoj (Auto-Seeded)",
        platform=Platform.ZEPTO,
        partner_id="ZPT123456",
        zone_id=zone_id,
        language_pref=Language.KANNADA,
        upi_id="manoj@okaxis",
        is_active=True,
        platform_engagement_days=100, # Pass SS Code 90-day rule
        engagement_start_date=utcnow() - timedelta(days=150), # Ensure SS Code algorithm calculates days correctly
        kyc={
            "aadhaar_number": "123456789012",
            "pan_number": "ABCDE1234F",
            "kyc_status": "verified",
            "verified_at": utcnow().isoformat(),
        }
    )

    db.add(test_partner)
    db.flush() # flush to get the partner.id

    # Add 7 days of mock GPS Pings to pass the "7 active days" underwriting gate
    from app.models.fraud import PartnerGPSPing
    
    now = utcnow()
    for i in range(7):
        ping = PartnerGPSPing(
            partner_id=test_partner.id,
            lat=12.9279,
            lng=77.6271,
            device_id="seed_device_123",
            source="app_heartbeat",
            created_at=now - timedelta(days=i)
        )
        db.add(ping)

    db.commit()
    db.refresh(test_partner)

    print(f"Seeded test partner: {test_phone} with 7 active days")
    return [test_partner]
