"""
Seed data for comprehensive test partners covering all scenarios.
Creates partners with different:
- Activity levels (< 7 days, 7-30 days, 30+ days)
- Policy states (no policy, active, expiring, expired, renewable)
- Policy durations (60, 90, 120 days)
- Zones (different cities)
"""

from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.partner import Partner, Platform, Language
from app.models.policy import Policy, PolicyTier, PolicyStatus
from app.models.zone import Zone
from app.models.fraud import PartnerGPSPing
from app.utils.time_utils import utcnow


def seed_partners(db: Session) -> list[Partner]:
    """
    Seed the database with comprehensive test partners covering all scenarios.
    """
    partners = []
    now = utcnow()

    # Get zones for different cities
    zones = db.query(Zone).all()
    if not zones:
        print("No zones found. Please seed zones first.")
        return []

    blr_zone = next((z for z in zones if z.city == "Bangalore"), zones[0])
    mum_zone = next((z for z in zones if z.city == "Mumbai"), zones[0])
    del_zone = next((z for z in zones if z.city == "Delhi"), zones[0])

    # Test data templates
    test_partners_data = [
        # ==========================================
        # NEW PARTNERS (< 7 days activity)
        # ==========================================
        {
            "phone": "9000000001",
            "name": "Rajesh New (2 days)",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100001",
            "zone": blr_zone,
            "language": Language.KANNADA,
            "activity_days": 2,
            "engagement_days": 2,
            "policy": None,
            "description": "New partner, 2 days activity, no policy - can only buy Flex"
        },
        {
            "phone": "9000000002",
            "name": "Priya New (5 days + Flex)",
            "platform": Platform.BLINKIT,
            "partner_id": "BLK100002",
            "zone": blr_zone,
            "language": Language.KANNADA,
            "activity_days": 5,
            "engagement_days": 5,
            "policy": {"tier": PolicyTier.FLEX, "days_left": 3},
            "description": "New partner with active Flex policy"
        },

        # ==========================================
        # MEDIUM ACTIVITY (7-30 days)
        # ==========================================
        {
            "phone": "9000000003",
            "name": "Amit Medium (15 days)",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100003",
            "zone": mum_zone,
            "language": Language.HINDI,
            "activity_days": 15,
            "engagement_days": 15,
            "policy": None,
            "description": "15 days activity, no policy - can buy Flex or Standard"
        },
        {
            "phone": "9000000004",
            "name": "Sneha Medium (20 days + Std)",
            "platform": Platform.BLINKIT,
            "partner_id": "BLK100004",
            "zone": mum_zone,
            "language": Language.HINDI,
            "activity_days": 20,
            "engagement_days": 20,
            "policy": {"tier": PolicyTier.STANDARD, "days_left": 10},
            "description": "20 days activity with Standard policy"
        },
        {
            "phone": "9000000005",
            "name": "Vikram Medium (25 days)",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100005",
            "zone": mum_zone,
            "language": Language.HINDI,
            "activity_days": 25,
            "engagement_days": 25,
            "policy": None,
            "description": "25 days activity, no policy - eligible for all tiers"
        },

        # ==========================================
        # ESTABLISHED PARTNERS (30+ days)
        # ==========================================
        {
            "phone": "9000000006",
            "name": "Suresh Senior (45 days)",
            "platform": Platform.BLINKIT,
            "partner_id": "BLK100006",
            "zone": del_zone,
            "language": Language.HINDI,
            "activity_days": 45,
            "engagement_days": 60,
            "policy": None,
            "description": "Established partner, no policy - eligible for all tiers"
        },
        {
            "phone": "9000000007",
            "name": "Lakshmi Senior (60 days + Pro)",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100007",
            "zone": del_zone,
            "language": Language.HINDI,
            "activity_days": 60,
            "engagement_days": 90,
            "policy": {"tier": PolicyTier.PRO, "days_left": 15},
            "description": "Established partner with Pro policy"
        },

        # ==========================================
        # EXPIRING SOON (Can Renew)
        # ==========================================
        {
            "phone": "9000000008",
            "name": "Karthik Expiring Tomorrow",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100008",
            "zone": blr_zone,
            "language": Language.KANNADA,
            "activity_days": 30,
            "engagement_days": 60,
            "policy": {"tier": PolicyTier.STANDARD, "days_left": 1},
            "description": "Policy expires tomorrow - can renew"
        },
        {
            "phone": "9000000009",
            "name": "Deepa Expiring Today",
            "platform": Platform.BLINKIT,
            "partner_id": "BLK100009",
            "zone": blr_zone,
            "language": Language.KANNADA,
            "activity_days": 40,
            "engagement_days": 90,
            "policy": {"tier": PolicyTier.PRO, "days_left": 0},
            "description": "Policy expires today - can renew"
        },

        # ==========================================
        # EXPIRED/GRACE PERIOD (Can Renew)
        # ==========================================
        {
            "phone": "9000000010",
            "name": "Ravi Grace Period (12h ago)",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100010",
            "zone": mum_zone,
            "language": Language.HINDI,
            "activity_days": 35,
            "engagement_days": 75,
            "policy": {"tier": PolicyTier.STANDARD, "days_left": -0.5},  # 12 hours ago
            "description": "Expired 12 hours ago - in grace period, can renew"
        },
        {
            "phone": "9000000011",
            "name": "Anjali Grace Period (36h ago)",
            "platform": Platform.BLINKIT,
            "partner_id": "BLK100011",
            "zone": mum_zone,
            "language": Language.HINDI,
            "activity_days": 50,
            "engagement_days": 100,
            "policy": {"tier": PolicyTier.PRO, "days_left": -1.5},  # 36 hours ago
            "description": "Expired 36 hours ago - still in grace period"
        },

        # ==========================================
        # LAPSED (Expired > 48h ago)
        # ==========================================
        {
            "phone": "9000000012",
            "name": "Manoj Lapsed (5 days ago)",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100012",
            "zone": del_zone,
            "language": Language.HINDI,
            "activity_days": 40,
            "engagement_days": 90,
            "policy": {"tier": PolicyTier.STANDARD, "days_left": -5},
            "description": "Lapsed 5 days ago - needs new policy"
        },

        # ==========================================
        # LONG-TERM POLICIES (60, 90, 120 days)
        # ==========================================
        {
            "phone": "9000000013",
            "name": "Arun 60-day Policy",
            "platform": Platform.BLINKIT,
            "partner_id": "BLK100013",
            "zone": blr_zone,
            "language": Language.KANNADA,
            "activity_days": 70,
            "engagement_days": 120,
            "policy": {"tier": PolicyTier.PRO, "days_left": 45, "total_days": 60},
            "description": "60-day policy, 45 days remaining"
        },
        {
            "phone": "9000000014",
            "name": "Pooja 90-day Policy",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100014",
            "zone": mum_zone,
            "language": Language.HINDI,
            "activity_days": 80,
            "engagement_days": 150,
            "policy": {"tier": PolicyTier.PRO, "days_left": 60, "total_days": 90},
            "description": "90-day policy, 60 days remaining"
        },
        {
            "phone": "9000000015",
            "name": "Ramesh 120-day Policy",
            "platform": Platform.BLINKIT,
            "partner_id": "BLK100015",
            "zone": del_zone,
            "language": Language.HINDI,
            "activity_days": 90,
            "engagement_days": 180,
            "policy": {"tier": PolicyTier.PRO, "days_left": 100, "total_days": 120},
            "description": "120-day policy, 100 days remaining"
        },

        # ==========================================
        # RENEWAL SCENARIOS
        # ==========================================
        {
            "phone": "9000000016",
            "name": "Sita Can Renew (1 day left)",
            "platform": Platform.ZEPTO,
            "partner_id": "ZPT100016",
            "zone": blr_zone,
            "language": Language.KANNADA,
            "activity_days": 55,
            "engagement_days": 100,
            "policy": {"tier": PolicyTier.STANDARD, "days_left": 1},
            "description": "Within renewal window - can renew now"
        },
        {
            "phone": "9000000017",
            "name": "Naveen Auto-Renew On",
            "platform": Platform.BLINKIT,
            "partner_id": "BLK100017",
            "zone": mum_zone,
            "language": Language.HINDI,
            "activity_days": 65,
            "engagement_days": 120,
            "policy": {"tier": PolicyTier.PRO, "days_left": 2, "auto_renew": True},
            "description": "Auto-renew enabled, expiring in 2 days"
        },
    ]

    # Create partners
    for data in test_partners_data:
        # Check if already exists
        existing = db.query(Partner).filter(Partner.phone == data["phone"]).first()
        if existing:
            partners.append(existing)
            continue

        # Create partner
        engagement_start = now - timedelta(days=data["engagement_days"])
        partner = Partner(
            phone=data["phone"],
            name=data["name"],
            platform=data["platform"],
            partner_id=data["partner_id"],
            zone_id=data["zone"].id,
            language_pref=data["language"],
            upi_id=f"{data['phone'][-4:]}@okaxis",
            is_active=True,
            platform_engagement_days=data["engagement_days"],
            engagement_start_date=engagement_start,
            kyc={
                "aadhaar_number": f"1234{data['phone'][-8:]}",
                "pan_number": f"ABCDE{data['phone'][-4:]}F",
                "kyc_status": "verified",
                "verified_at": now.isoformat(),
            }
        )

        db.add(partner)
        db.flush()

        # Add GPS pings for activity days
        for day_offset in range(data["activity_days"]):
            ping_time = now - timedelta(days=day_offset)
            ping = PartnerGPSPing(
                partner_id=partner.id,
                lat=data["zone"].dark_store_lat + (day_offset * 0.0001),
                lng=data["zone"].dark_store_lng + (day_offset * 0.0001),
                source="internal",
            )
            # Set created_at manually if needed (though it has server_default)
            ping.created_at = ping_time
            db.add(ping)

        # Create policy if specified
        if data["policy"]:
            policy_data = data["policy"]
            days_left = policy_data["days_left"]
            total_days = policy_data.get("total_days", 7)  # Default to 7-day policy

            # Calculate start and expiry dates
            expires_at = now + timedelta(days=days_left)
            starts_at = expires_at - timedelta(days=total_days)

            # Determine status
            if days_left < -2:  # Lapsed (> 48 hours ago)
                is_active = False
                status = PolicyStatus.LAPSED
            elif days_left < 0:  # Grace period
                is_active = True
                status = PolicyStatus.GRACE_PERIOD
            else:  # Active
                is_active = True
                status = PolicyStatus.ACTIVE

            # Calculate premium based on tier
            from app.services.premium import calculate_premium
            quote = calculate_premium(policy_data["tier"], data["zone"])

            policy = Policy(
                partner_id=partner.id,
                tier=policy_data["tier"],
                weekly_premium=quote.final_premium,
                max_daily_payout=quote.max_daily_payout,
                max_days_per_week=quote.max_days_per_week,
                starts_at=starts_at,
                expires_at=expires_at,
                auto_renew=policy_data.get("auto_renew", False),
                status=status,
                is_active=is_active,
            )
            db.add(policy)

        partners.append(partner)
        print(f"✓ Created: {data['name']} - {data['description']}")

    db.commit()
    print(f"\n✅ Seeded {len(partners)} test partners with comprehensive scenarios")
    return partners
