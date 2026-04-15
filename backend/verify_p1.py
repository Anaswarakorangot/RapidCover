import sys
import os
from datetime import datetime, timedelta
import json

# Add backend to path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.utils.time_utils import utcnow
from app.models.partner import Partner
from app.models.fraud import PartnerGPSPing, PartnerDevice
from app.models.trigger_event import SustainedEvent, TriggerType
from app.services.fraud_service import compute_max_velocity_kmh, calculate_fraud_score
from app.services.trigger_detector import track_sustained_event


def verify():
    db = SessionLocal()
    print("--- RapidCover P1 Hardening Verification ---")
    
    try:
        # 1. Check a partner
        partner = db.query(Partner).first()
        if not partner:
            print("ERROR: No partners found in DB to test with.")
            return
        print(f"Testing with Partner ID: {partner.id} ({partner.name})")

        # 2. Test Heartbeat Persistence
        print("\n[1/4] Testing GPS Ping Persistence...")
        now = utcnow()
        ping = PartnerGPSPing(
            partner_id=partner.id,
            lat=12.9716,
            lng=77.5946,
            device_id="verify_script_device",
            source="verification_test",
            created_at=now
        )
        db.add(ping)
        
        # Add a second ping 10 mins later at a different location to test velocity
        ping2 = PartnerGPSPing(
            partner_id=partner.id,
            lat=12.9816, # approx 1.1km away
            lng=77.6046,
            device_id="verify_script_device",
            source="verification_test",
            created_at=now + timedelta(minutes=10)
        )
        db.add(ping2)
        db.commit()
        print("SUCCESS: GPS pings recorded in 'partner_gps_pings' table.")

        # 3. Test Fraud Velocity Logic
        print("\n[2/4] Testing DB-backed Fraud Analysis...")
        pings = db.query(PartnerGPSPing).filter(PartnerGPSPing.partner_id == partner.id).all()
        ping_data = [{"lat": p.lat, "lng": p.lng, "ts": p.created_at.timestamp()} for p in pings]
        velocity = compute_max_velocity_kmh(ping_data)
        print(f"Calculated Max Velocity from history: {velocity} km/h")
        if velocity > 0:
            print("SUCCESS: Fraud service correctly retrieved trajectory from DB.")
        else:
            print("WARNING: Velocity 0 (maybe pings too close?). But query worked.")

        # 4. Test Sustained Event Persistence
        print("\n[3/4] Testing Sustained Event DB Migration...")
        # Clear previous for clean test
        db.query(SustainedEvent).filter(SustainedEvent.zone_id == 1).delete()
        db.commit()
        
        # Simulate 5 consecutive days
        info = None
        for i in range(5):
            event_date = utcnow() - timedelta(days=4-i)
            info = track_sustained_event(zone_id=1, trigger_type=TriggerType.RAIN, db=db, event_date=event_date)
            print(f"  Day {i+1}: consecutive_days={info['consecutive_days']}, is_sustained={info['is_sustained']}")
        
        if info and info['is_sustained']:
            print("SUCCESS: Sustained state persisted and recognized 5-day threshold.")
        else:
            print("ERROR: Sustained state logic failed.")

        # 5. Check Matrix 'Data Freshness' logic
        print("\n[4/4] Testing Validation Matrix Data Freshness...")
        from app.services.claims_processor import build_validation_matrix
        from app.models.trigger_event import TriggerEvent
        from app.models.policy import Policy, PolicyTier
        
        # Ensure partner has an active policy
        policy = db.query(Policy).filter(Policy.partner_id == partner.id).first()
        if not policy:
            policy = Policy(
                partner_id=partner.id,
                tier=PolicyTier.STANDARD,
                starts_at=utcnow() - timedelta(days=1),
                expires_at=utcnow() + timedelta(days=6),
                weekly_premium=450.0,
                max_daily_payout=500.0,
                max_days_per_week=6,
                is_active=True
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)

        dummy_trigger = TriggerEvent(zone_id=partner.zone_id, trigger_type=TriggerType.RAIN, started_at=utcnow(), severity=3)
        # Mock fraud result for the matrix call
        fraud_mock = {"score": 0.1, "decision": "auto_approve", "factors": {"w1_gps_coherence": 1.0, "w2_run_count_clean": 1.0, "w3_zone_polygon_match": 1.0, "w4_claim_frequency": 0.0, "w5_device_consistent": 1, "w6_traffic_disrupted": 1, "w7_centroid_drift_km": 0.1}, "hard_reject_reasons": []}
        
        matrix = build_validation_matrix(partner, policy, dummy_trigger, None, fraud_mock, db)
        freshness_check = next((c for c in matrix if c['check_name'] == 'data_freshness'), None)
        
        if freshness_check and freshness_check['passed']:
            print(f"SUCCESS: Data freshness passed using real Heartbeat history: {freshness_check['reason']}")
        else:
            print(f"ERROR: Data freshness failed check. Reason: {freshness_check['reason'] if freshness_check else 'Check missing'}")

    except Exception as e:
        print(f"\nCRITICAL ERROR during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify()
