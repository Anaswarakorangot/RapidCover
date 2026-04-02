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
        kyc={
            "aadhaar_number": "123456789012",
            "pan_number": "ABCDE1234F",
            "kyc_status": "verified",
        }
    )

    db.add(test_partner)
    db.commit()
    db.refresh(test_partner)

    print(f"Seeded test partner: {test_phone}")
    return [test_partner]
