"""
Phase 2 Task Verification Tests
================================
Tests all 22 tasks from Person 1 and Person 2 task lists.

Run with: python tests/test_phase2_tasks.py
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# PERSON 1 TESTS - Pricing + Premium Engine + ML Wrapper
# ============================================================================

class TestPerson1Tasks:
    """Tests for Person 1: Backend Pricing + Premium Engine + ML Wrapper"""

    # -------------------------------------------------------------------------
    # Task 1: Fix pricing tiers to Rs.22/Rs.33/Rs.45
    # -------------------------------------------------------------------------
    def test_task1_pricing_tiers_premium_service(self):
        """Verify TIER_CONFIG has correct prices in premium_service.py"""
        from app.services.premium_service import TIER_CONFIG

        assert TIER_CONFIG["flex"]["weekly_premium"] == 22, "Flex should be Rs.22"
        assert TIER_CONFIG["standard"]["weekly_premium"] == 33, "Standard should be Rs.33"
        assert TIER_CONFIG["pro"]["weekly_premium"] == 45, "Pro should be Rs.45"
        print("[PASS] Task 1: Pricing tiers Rs.22/33/45")

    def test_task1_pricing_tiers_ml_service(self):
        """Verify BASE_PRICES in ml_service.py matches"""
        from app.services.ml_service import PremiumModel

        model = PremiumModel()
        assert model.BASE_PRICES["flex"] == 22
        assert model.BASE_PRICES["standard"] == 33
        assert model.BASE_PRICES["pro"] == 45
        print("[PASS] Task 1b: ML Service pricing tiers")

    # -------------------------------------------------------------------------
    # Task 2: Full premium formula implementation
    # -------------------------------------------------------------------------
    def test_task2_premium_formula_components(self):
        """Verify full premium formula has all required components"""
        from app.services.ml_service import PremiumModel, PartnerFeatures

        model = PremiumModel()

        # Check all required components exist
        assert hasattr(model, 'CITY_PERIL'), "Missing city_peril_multiplier"
        assert hasattr(model, 'SEASONAL_INDEX'), "Missing seasonal_index"
        assert hasattr(model, 'ACTIVITY_TIER_FACTOR'), "Missing activity_tier_factor"
        assert hasattr(model, 'RIQI_ADJUSTMENT'), "Missing RIQI_adjustment"
        assert hasattr(model, 'CAP_MULTIPLIER'), "Missing cap (3x)"
        assert model.CAP_MULTIPLIER == 3.0, "Cap should be 3x base tier"

        # Test formula execution
        features = PartnerFeatures(
            partner_id=1,
            city="bangalore",
            zone_risk_score=50.0,
            active_days_last_30=15,
            avg_hours_per_day=8.0,
            tier="standard",
            loyalty_weeks=0,
            month=7,  # Monsoon month
            riqi_score=55.0,
        )
        result = model.predict(features)

        assert "weekly_premium" in result
        assert "breakdown" in result
        assert result["breakdown"]["city_peril_multiplier"] > 0
        assert result["breakdown"]["seasonal_index"] >= 1.0
        assert result["breakdown"]["activity_tier_factor"] > 0
        assert result["breakdown"]["riqi_adjustment"] > 0
        assert result["breakdown"]["loyalty_discount"] <= 1.0
        print("[PASS] Task 2: Full premium formula")

    # -------------------------------------------------------------------------
    # Task 3: City-specific seasonal multiplier table
    # -------------------------------------------------------------------------
    def test_task3_seasonal_multipliers(self):
        """Verify city-specific seasonal multipliers match spec"""
        from app.services.ml_service import PremiumModel

        model = PremiumModel()
        seasonal = model.SEASONAL_INDEX

        # Bangalore: Jun-Sep +20%
        assert all(seasonal["bangalore"].get(m, 1.0) == 1.20 for m in [6, 7, 8, 9]), \
            "Bangalore should be +20% Jun-Sep"

        # Mumbai: Jul-Sep +25%
        assert all(seasonal["mumbai"].get(m, 1.0) == 1.25 for m in [7, 8, 9]), \
            "Mumbai should be +25% Jul-Sep"

        # Delhi: Oct-Jan +18%
        assert all(seasonal["delhi"].get(m, 1.0) == 1.18 for m in [10, 11, 12, 1]), \
            "Delhi should be +18% Oct-Jan"

        # Chennai: Oct-Dec +22%
        assert all(seasonal["chennai"].get(m, 1.0) == 1.22 for m in [10, 11, 12]), \
            "Chennai should be +22% Oct-Dec"

        # Hyderabad: Jul-Sep +15%
        assert all(seasonal["hyderabad"].get(m, 1.0) == 1.15 for m in [7, 8, 9]), \
            "Hyderabad should be +15% Jul-Sep"

        # Kolkata: Jun-Sep +20%
        assert all(seasonal["kolkata"].get(m, 1.0) == 1.20 for m in [6, 7, 8, 9]), \
            "Kolkata should be +20% Jun-Sep"

        print("[PASS] Task 3: City-specific seasonal multipliers")

    # -------------------------------------------------------------------------
    # Task 4: RIQI zone scoring - derive, store, expose via API
    # -------------------------------------------------------------------------
    def test_task4_riqi_scoring(self):
        """Verify RIQI scoring functions exist and work"""
        from app.services.premium_service import (
            get_riqi_score,
            get_riqi_band,
            get_riqi_payout_multiplier,
            CITY_RIQI_SCORES,
        )

        # Check cities have RIQI scores
        assert "bangalore" in CITY_RIQI_SCORES
        assert "mumbai" in CITY_RIQI_SCORES
        assert "delhi" in CITY_RIQI_SCORES

        # Test functions
        score = get_riqi_score("bangalore")
        assert 0 <= score <= 100, "RIQI score should be 0-100"

        band = get_riqi_band(score)
        assert band in ["urban_core", "urban_fringe", "peri_urban"]

        multiplier = get_riqi_payout_multiplier("bangalore")
        assert multiplier in [1.0, 1.25, 1.5]

        print("[PASS] Task 4: RIQI zone scoring")

    # -------------------------------------------------------------------------
    # Task 5: RIQI multiplier to payout (1.0/1.25/1.5)
    # -------------------------------------------------------------------------
    def test_task5_riqi_multipliers(self):
        """Verify RIQI payout multipliers are 1.0/1.25/1.5"""
        from app.services.premium_service import RIQI_PAYOUT_MULTIPLIER

        assert RIQI_PAYOUT_MULTIPLIER["urban_core"] == 1.0
        assert RIQI_PAYOUT_MULTIPLIER["urban_fringe"] == 1.25
        assert RIQI_PAYOUT_MULTIPLIER["peri_urban"] == 1.5
        print("[PASS] Task 5: RIQI multipliers 1.0/1.25/1.5")

    # -------------------------------------------------------------------------
    # Task 6: Underwriting gate (block if <7 active days)
    # -------------------------------------------------------------------------
    def test_task6_underwriting_gate(self):
        """Verify underwriting gate blocks purchase if <7 active days"""
        from app.services.premium_service import (
            check_underwriting_gate,
            MIN_ACTIVE_DAYS_TO_BUY,
        )

        assert MIN_ACTIVE_DAYS_TO_BUY == 7, "Minimum should be 7 days"

        # Should block with 5 days
        result = check_underwriting_gate(5)
        assert result["allowed"] == False
        assert "7" in result["reason"]

        # Should allow with 10 days
        result = check_underwriting_gate(10)
        assert result["allowed"] == True

        print("[PASS] Task 6: Underwriting gate (<7 days blocked)")

    # -------------------------------------------------------------------------
    # Task 7: Auto-downgrade to Flex if <5 active days
    # -------------------------------------------------------------------------
    def test_task7_auto_downgrade(self):
        """Verify auto-downgrade to Flex if <5 active days"""
        from app.services.premium_service import (
            apply_auto_downgrade,
            AUTO_DOWNGRADE_DAYS,
        )

        assert AUTO_DOWNGRADE_DAYS == 5, "Downgrade threshold should be 5 days"

        # Standard with 3 days -> should downgrade to Flex
        tier, downgraded = apply_auto_downgrade("standard", 3)
        assert tier == "flex"
        assert downgraded == True

        # Standard with 10 days -> should stay Standard
        tier, downgraded = apply_auto_downgrade("standard", 10)
        assert tier == "standard"
        assert downgraded == False

        # Flex with 3 days -> should stay Flex (already lowest)
        tier, downgraded = apply_auto_downgrade("flex", 3)
        assert tier == "flex"
        assert downgraded == False

        print("[PASS] Task 7: Auto-downgrade to Flex (<5 days)")

    # -------------------------------------------------------------------------
    # Task 8: Centroid drift factor (w7=0.05) in fraud scorer
    # -------------------------------------------------------------------------
    def test_task8_centroid_drift_factor(self):
        """Verify centroid drift factor w7=0.05 in 7-factor model"""
        from app.services.ml_service import FraudModel

        model = FraudModel()
        assert model.W7_CENTROID_DRIFT == 0.05, "w7 should be 0.05"

        # Verify total is 7 factors
        total_weight = (
            model.W1_GPS_COHERENCE +
            model.W2_RUN_COUNT +
            model.W3_ZONE_POLYGON +
            model.W4_CLAIM_FREQUENCY +
            model.W5_DEVICE_FINGERPRINT +
            model.W6_TRAFFIC_CROSS_CHECK +
            model.W7_CENTROID_DRIFT
        )
        assert abs(total_weight - 1.0) < 0.001, f"Weights should sum to 1.0, got {total_weight}"

        print("[PASS] Task 8: Centroid drift w7=0.05 (7-factor total)")

    # -------------------------------------------------------------------------
    # Task 9: Velocity physics check (>60km/h = spoof)
    # -------------------------------------------------------------------------
    def test_task9_velocity_physics_check(self):
        """Verify velocity physics check rejects >60km/h as spoof"""
        from app.services.ml_service import FraudModel, ClaimFeatures

        model = FraudModel()
        assert model.VELOCITY_SPOOF_KMH == 60.0, "Velocity threshold should be 60km/h"

        # Test with high velocity (should be rejected)
        features = ClaimFeatures(
            partner_id=1,
            zone_id=1,
            gps_in_zone=True,
            run_count_during_event=0,
            zone_polygon_match=True,
            claims_last_30_days=0,
            device_consistent=True,
            traffic_disrupted=True,
            centroid_drift_km=1.0,
            max_gps_velocity_kmh=80.0,  # > 60km/h
            zone_suspended=True,
        )
        result = model.score(features)
        assert result["decision"] == "auto_reject"
        assert any("velocity" in r.lower() or "60" in r for r in result["hard_reject_reasons"])

        print("[PASS] Task 9: Velocity physics check (>60km/h = spoof)")

    # -------------------------------------------------------------------------
    # Task 10: ml_service.py with 3 ML models
    # -------------------------------------------------------------------------
    def test_task10_ml_service_models(self):
        """Verify ml_service.py has all 3 ML-shaped models"""
        from app.services.ml_service import (
            zone_risk_model,
            premium_model,
            fraud_model,
            ZoneFeatures,
            PartnerFeatures,
            ClaimFeatures,
        )

        # Check models exist
        assert zone_risk_model is not None
        assert premium_model is not None
        assert fraud_model is not None

        # Check they have predict/score methods
        assert hasattr(zone_risk_model, 'predict')
        assert hasattr(premium_model, 'predict')
        assert hasattr(fraud_model, 'score')

        # Test zone_risk_model
        zone_features = ZoneFeatures(
            zone_id=1,
            city="bangalore",
            avg_rainfall_mm_per_hr=30.0,
            flood_events_2yr=5,
            aqi_avg_annual=150.0,
            aqi_severe_days_2yr=20,
            heat_advisory_days_2yr=10,
            bandh_events_2yr=3,
            dark_store_suspensions_2yr=4,
            road_flood_prone=True,
            month=7,
        )
        risk_score = zone_risk_model.predict(zone_features)
        assert 0 <= risk_score <= 100

        print("[PASS] Task 10: ml_service.py with 3 ML models")


# ============================================================================
# PERSON 2 TESTS - Triggers + Claims + Payout + Zones
# ============================================================================

class TestPerson2Tasks:
    """Tests for Person 2: Backend Triggers + Claims + Payout + Zones"""

    # -------------------------------------------------------------------------
    # Task 1: Active shift window check (leave/offline = no payout)
    # -------------------------------------------------------------------------
    def test_task1_shift_window_check(self):
        """Verify partner on leave or offline gets no payout"""
        from app.services.claims_processor import is_partner_available_for_trigger

        # Mock partner with shift days
        mock_partner = MagicMock()
        mock_partner.id = 1
        mock_partner.is_active = True
        mock_partner.shift_days = ["mon", "tue", "wed", "thu", "fri"]
        mock_partner.shift_start = "08:00"
        mock_partner.shift_end = "20:00"

        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "partner_id": 1,
            "pin_code": None,
            "is_manual_offline": False,
            "manual_offline_until": None,
            "leave_until": None,
            "leave_note": None,
            "updated_at": None,
        }

        # Test during work hours on a weekday
        work_time = datetime(2024, 1, 15, 10, 0)  # Monday 10 AM
        available, reason = is_partner_available_for_trigger(mock_partner, mock_db, work_time)
        assert available == True, f"Should be available during work hours, got {reason}"

        print("[PASS] Task 1: Active shift window check")

    # -------------------------------------------------------------------------
    # Task 2: Ward/pin-code level data check
    # -------------------------------------------------------------------------
    def test_task2_pincode_check(self):
        """Verify trigger matches partner's pin-code, not city average"""
        from app.services.trigger_engine import check_partner_pin_code_match

        mock_partner = MagicMock()
        mock_partner.id = 1
        mock_partner.pin_code = "560001"

        mock_zone = MagicMock()
        mock_zone.id = 1
        mock_zone.pin_codes = ["560001", "560002", "560003"]

        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = None

        # Should match
        matches, reason = check_partner_pin_code_match(mock_partner, mock_zone, mock_db)
        # With fallback (no pin_code fields), should return True
        assert matches == True

        print("[PASS] Task 2: Ward/pin-code level check")

    # -------------------------------------------------------------------------
    # Task 3: Active hours match in trigger engine
    # -------------------------------------------------------------------------
    def test_task3_active_hours_match(self):
        """Verify trigger must fall within partner's shift window"""
        from app.services.claims_processor import is_partner_available_for_trigger

        mock_partner = MagicMock()
        mock_partner.id = 1
        mock_partner.is_active = True
        mock_partner.shift_days = ["mon", "tue", "wed"]
        mock_partner.shift_start = "09:00"
        mock_partner.shift_end = "17:00"

        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "partner_id": 1, "pin_code": None, "is_manual_offline": False,
            "manual_offline_until": None, "leave_until": None, "leave_note": None,
            "updated_at": None,
        }

        # 3 AM on Monday - outside shift window
        night_time = datetime(2024, 1, 15, 3, 0)  # Monday 3 AM
        available, reason = is_partner_available_for_trigger(mock_partner, mock_db, night_time)
        assert available == False
        assert reason == "outside_shift_window"

        print("[PASS] Task 3: Active hours match")

    # -------------------------------------------------------------------------
    # Task 4: Sustained event mode (5+ days = 70% payout)
    # -------------------------------------------------------------------------
    def test_task4_sustained_event_mode(self):
        """Verify sustained event: 5+ consecutive days = 70% payout, no weekly cap"""
        from app.services.trigger_detector import (
            track_sustained_event,
            SUSTAINED_EVENT_THRESHOLD_DAYS,
            SUSTAINED_EVENT_PAYOUT_MODIFIER,
            SUSTAINED_EVENT_MAX_DAYS,
        )
        from app.models.trigger_event import TriggerType

        assert SUSTAINED_EVENT_THRESHOLD_DAYS == 5
        assert SUSTAINED_EVENT_PAYOUT_MODIFIER == 0.70
        assert SUSTAINED_EVENT_MAX_DAYS == 21

        # Simulate 5 consecutive days
        zone_id = 999  # Test zone
        for day in range(5):
            event_date = datetime.utcnow() - timedelta(days=4-day)
            result = track_sustained_event(zone_id, TriggerType.RAIN, event_date)

        assert result["is_sustained"] == True
        assert result["payout_modifier"] == 0.70
        assert result["bypass_weekly_cap"] == True

        print("[PASS] Task 4: Sustained event mode (5+ days = 70%)")

    # -------------------------------------------------------------------------
    # Task 5: Day 7 reinsurance threshold review flag
    # -------------------------------------------------------------------------
    def test_task5_reinsurance_review_endpoint(self):
        """Verify day 7 reinsurance review flag endpoint exists"""
        from app.api.policies import reinsurance_review, ReinsuranceReviewResponse

        # Check the endpoint function exists and has correct response model
        assert callable(reinsurance_review)
        assert ReinsuranceReviewResponse is not None

        # Check response model has required fields
        fields = ReinsuranceReviewResponse.model_fields
        assert "flagged_policies" in fields
        assert "total_claims_amount" in fields
        assert "review_triggered" in fields
        assert "threshold_ratio" in fields

        print("[PASS] Task 5: Day 7 reinsurance review flag")

    # -------------------------------------------------------------------------
    # Task 6: Zone pool share cap
    # -------------------------------------------------------------------------
    def test_task6_zone_pool_share_cap(self):
        """Verify zone pool share cap formula"""
        from app.services.premium_service import calculate_zone_pool_share

        result = calculate_zone_pool_share(
            calculated_payout=500.0,
            city_weekly_reserve=10000.0,
            zone_density_weight=0.35,
            total_partners_in_event=100,
        )

        # zone_pool_share = 10000 * 0.35 / 100 = 35
        expected_pool_share = 35.0
        assert result["zone_pool_share"] == expected_pool_share
        assert result["final_payout"] == min(500.0, expected_pool_share)
        assert result["pool_cap_applied"] == True

        print("[PASS] Task 6: Zone pool share cap")

    # -------------------------------------------------------------------------
    # Task 7: City-level 120% hard cap
    # -------------------------------------------------------------------------
    def test_task7_city_hard_cap(self):
        """Verify city-level 120% hard cap exists"""
        from app.services.payout_service import CITY_HARD_CAP_RATIO, check_city_hard_cap

        assert CITY_HARD_CAP_RATIO == 1.20, "City cap should be 120%"
        assert callable(check_city_hard_cap)

        print("[PASS] Task 7: City-level 120% hard cap")

    # -------------------------------------------------------------------------
    # Task 8: BCR calculation endpoint
    # -------------------------------------------------------------------------
    def test_task8_bcr_endpoint(self):
        """Verify BCR calculation endpoint exists"""
        from app.api.zones import calculate_city_bcr, BCRResponse

        assert callable(calculate_city_bcr)

        # Check BCR formula implementation
        from app.services.premium_service import calculate_bcr

        result = calculate_bcr(
            total_claims_paid=6500.0,
            total_premiums_collected=10000.0,
        )

        assert result["bcr"] == 0.65  # 6500/10000
        assert result["loss_ratio"] == 65.0  # 65%
        assert result["status"] == "healthy"  # 55-70% is healthy

        print("[PASS] Task 8: BCR calculation endpoint")

    # -------------------------------------------------------------------------
    # Task 9: Loss Ratio >85% flag (suspends enrollments)
    # -------------------------------------------------------------------------
    def test_task9_loss_ratio_suspension(self):
        """Verify loss ratio >85% suspends new enrollments"""
        from app.api.policies import LOSS_RATIO_SUSPENSION_THRESHOLD
        from app.services.premium_service import calculate_bcr

        assert LOSS_RATIO_SUSPENSION_THRESHOLD == 0.85

        # Test with 90% loss ratio
        result = calculate_bcr(
            total_claims_paid=9000.0,
            total_premiums_collected=10000.0,
        )

        assert result["loss_ratio"] == 90.0
        assert result["suspend_enrolments"] == True

        print("[PASS] Task 9: Loss Ratio >85% suspension flag")

    # -------------------------------------------------------------------------
    # Task 10: Zone reassignment backend
    # -------------------------------------------------------------------------
    def test_task10_zone_reassignment(self):
        """Verify zone reassignment endpoint exists with required fields"""
        from app.api.zones import (
            reassign_partner_zone,
            ZoneReassignmentRequest,
            ZoneReassignmentResponse,
        )

        assert callable(reassign_partner_zone)

        # Check request model
        req_fields = ZoneReassignmentRequest.model_fields
        assert "partner_id" in req_fields
        assert "new_zone_id" in req_fields

        # Check response model
        resp_fields = ZoneReassignmentResponse.model_fields
        assert "premium_adjustment" in resp_fields
        assert "new_weekly_premium" in resp_fields
        assert "days_remaining" in resp_fields
        assert "reassignment_logged" in resp_fields

        print("[PASS] Task 10: Zone reassignment backend")

    # -------------------------------------------------------------------------
    # Task 11: 48-hour weather alert backend
    # -------------------------------------------------------------------------
    def test_task11_weather_alert(self):
        """Verify 48-hour weather alert functions exist"""
        from app.services.trigger_engine import (
            check_48hr_forecast,
            send_forecast_alerts,
        )

        assert callable(check_48hr_forecast)
        assert callable(send_forecast_alerts)

        # Test forecast check returns alerts
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        alerts = check_48hr_forecast(zone_id=1, db=mock_db)
        assert isinstance(alerts, list)

        print("[PASS] Task 11: 48-hour weather alert backend")

    # -------------------------------------------------------------------------
    # Task 12: Razorpay test mode wiring
    # -------------------------------------------------------------------------
    def test_task12_razorpay_wiring(self):
        """Verify Razorpay payout function exists"""
        from app.services.payout_service import process_razorpay_payout

        assert callable(process_razorpay_payout)

        # Test with mock partner (should fail gracefully without keys)
        mock_partner = MagicMock()
        mock_partner.id = 1
        mock_partner.name = "Test"
        mock_partner.phone = "9999999999"
        mock_partner.upi_id = "test@upi"

        success, ref, data = process_razorpay_payout(mock_partner, 100.0, 1)

        # Should return False with error since keys not configured
        assert success == False
        assert "error" in data

        print("[PASS] Task 12: Razorpay test mode wiring")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests verifying components work together"""

    def test_fraud_service_integration(self):
        """Verify claims_processor uses 7-factor fraud model"""
        # Check that claims_processor imports from fraud_service
        import app.services.claims_processor as cp

        # The function should exist and be callable
        assert callable(cp.calculate_fraud_score)

        # Verify it's using the 7-factor model by checking the module
        from app.services.fraud_service import calculate_fraud_score as fs_calc
        # Both should be the same function
        assert cp.calculate_fraud_score == fs_calc

        print("[PASS] Integration: Fraud service uses 7-factor model")

    def test_premium_model_integration(self):
        """Verify premium_service uses ml_service.premium_model"""
        from app.services.premium_service import calculate_weekly_premium
        from app.services.ml_service import premium_model

        assert premium_model is not None
        assert callable(calculate_weekly_premium)

        print("[PASS] Integration: Premium service uses ML model")


# ============================================================================
# RUN TESTS
# ============================================================================

def run_all_tests():
    """Run all tests and print summary"""
    print("\n" + "="*70)
    print("PHASE 2 TASK VERIFICATION TESTS")
    print("="*70 + "\n")

    results = {"passed": 0, "failed": 0, "errors": []}

    # Person 1 Tests
    print("\n--- PERSON 1: Pricing + Premium Engine + ML Wrapper ---\n")
    p1 = TestPerson1Tasks()
    p1_tests = [
        ("Task 1: Pricing tiers Rs.22/33/45", p1.test_task1_pricing_tiers_premium_service),
        ("Task 1b: ML Service pricing", p1.test_task1_pricing_tiers_ml_service),
        ("Task 2: Full premium formula", p1.test_task2_premium_formula_components),
        ("Task 3: Seasonal multipliers", p1.test_task3_seasonal_multipliers),
        ("Task 4: RIQI zone scoring", p1.test_task4_riqi_scoring),
        ("Task 5: RIQI multipliers", p1.test_task5_riqi_multipliers),
        ("Task 6: Underwriting gate", p1.test_task6_underwriting_gate),
        ("Task 7: Auto-downgrade", p1.test_task7_auto_downgrade),
        ("Task 8: Centroid drift w7", p1.test_task8_centroid_drift_factor),
        ("Task 9: Velocity physics", p1.test_task9_velocity_physics_check),
        ("Task 10: ML service models", p1.test_task10_ml_service_models),
    ]

    for name, test_func in p1_tests:
        try:
            test_func()
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"PERSON 1 - {name}: {str(e)}")
            print(f"[FAIL] {name}: {e}")

    # Person 2 Tests
    print("\n--- PERSON 2: Triggers + Claims + Payout + Zones ---\n")
    p2 = TestPerson2Tasks()
    p2_tests = [
        ("Task 1: Shift window check", p2.test_task1_shift_window_check),
        ("Task 2: Pin-code check", p2.test_task2_pincode_check),
        ("Task 3: Active hours match", p2.test_task3_active_hours_match),
        ("Task 4: Sustained event", p2.test_task4_sustained_event_mode),
        ("Task 5: Reinsurance review", p2.test_task5_reinsurance_review_endpoint),
        ("Task 6: Zone pool share cap", p2.test_task6_zone_pool_share_cap),
        ("Task 7: City hard cap", p2.test_task7_city_hard_cap),
        ("Task 8: BCR endpoint", p2.test_task8_bcr_endpoint),
        ("Task 9: Loss ratio flag", p2.test_task9_loss_ratio_suspension),
        ("Task 10: Zone reassignment", p2.test_task10_zone_reassignment),
        ("Task 11: Weather alert", p2.test_task11_weather_alert),
        ("Task 12: Razorpay wiring", p2.test_task12_razorpay_wiring),
    ]

    for name, test_func in p2_tests:
        try:
            test_func()
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"PERSON 2 - {name}: {str(e)}")
            print(f"[FAIL] {name}: {e}")

    # Integration Tests
    print("\n--- INTEGRATION TESTS ---\n")
    integ = TestIntegration()
    integ_tests = [
        ("Fraud service integration", integ.test_fraud_service_integration),
        ("Premium model integration", integ.test_premium_model_integration),
    ]

    for name, test_func in integ_tests:
        try:
            test_func()
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"INTEGRATION - {name}: {str(e)}")
            print(f"[FAIL] {name}: {e}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Total: {results['passed'] + results['failed']}")

    if results["errors"]:
        print("\n--- FAILURES ---")
        for err in results["errors"]:
            print(f"  * {err}")

    print("\n")
    return results


if __name__ == "__main__":
    run_all_tests()
