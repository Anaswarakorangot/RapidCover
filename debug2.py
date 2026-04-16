import sys, os
sys.path.append(os.getcwd() + '/backend')
os.chdir('backend')
from app.database import SessionLocal
from app.models.partner import Partner
from app.models.policy import Policy
from app.services.claims_processor import process_trigger_event
from app.models.trigger_event import TriggerEvent, TriggerType
from app.models.zone import Zone
import json
from datetime import datetime

db = SessionLocal()

partner = db.query(Partner).filter(Partner.name == 'Anaswara').first()
if not partner:
    print("Partner not found")
    sys.exit(1)

# create a proper trigger event in the DB to avoid IntegrityError
try:
    trigger = TriggerEvent(
        zone_id=partner.zone_id,
        trigger_type=TriggerType.RAIN,
        started_at=datetime.utcnow(),
        severity=3,
        source_data=json.dumps({"force_fired": True})
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    
    res = process_trigger_event(trigger, db, disruption_hours=4.0)
    print("Claims created:", len(res))
    for c in res:
        print(c.id, c.status, c.amount)
        
except Exception as e:
    import traceback
    traceback.print_exc()
