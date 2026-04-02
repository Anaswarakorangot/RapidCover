import sys
import os
from datetime import datetime, timedelta

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.partner import Partner
from app.models.policy import Policy, PolicyTier, PolicyStatus

db = SessionLocal()

# Specifically target the user who logged in as 'Test' (ID 4)
partner = db.query(Partner).filter(Partner.name == 'Test').first()
if not partner:
    partner = db.query(Partner).filter(Partner.id == 4).first()

if not partner:
    print("No partner 'Test' found.")
    sys.exit(1)

print(f"Modifying partner: {partner.name} (Phone: {partner.phone}, ID: {partner.id})")

old_policy = Policy(
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
db.add(old_policy)

active_policy = Policy(
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
db.add(active_policy)

db.commit()
print("Successfully granted active policy and active days to Test (ID 4)!")
