import sys
import os
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.partner import Partner
from app.models.policy import Policy, PolicyTier, PolicyStatus

db = SessionLocal()
partner = db.query(Partner).filter(Partner.phone == "3636363636").first()

if not partner:
    print("Partner with phone 3636363636 not found!")
    sys.exit(1)

print(f"Applying to {partner.name} - ID {partner.id}")

# Delete old policies just in case
db.query(Policy).filter(Policy.partner_id == partner.id).delete()
db.commit()

p1 = Policy(
    partner_id=partner.id,
    tier=PolicyTier.FLEX,
    starts_at=datetime.utcnow() - timedelta(days=20),
    expires_at=datetime.utcnow() - timedelta(days=13),
    weekly_premium=22.0,
    max_days_per_week=2,
    max_daily_payout=250.0,
    is_active=False,
    status=PolicyStatus.LAPSED
)
p2 = Policy(
    partner_id=partner.id,
    tier=PolicyTier.STANDARD,
    starts_at=datetime.utcnow() - timedelta(days=2),
    expires_at=datetime.utcnow() + timedelta(days=5),
    weekly_premium=33.0,
    max_days_per_week=3,
    max_daily_payout=400.0,
    is_active=True,
    status=PolicyStatus.ACTIVE
)

db.add(p1)
db.add(p2)
db.commit()

final_count = db.query(Policy).filter(Policy.partner_id == partner.id).count()
print(f"Done! Partner {partner.id} now has {final_count} policies.")
