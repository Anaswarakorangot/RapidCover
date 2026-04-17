"""
Drill System Tests
==================
Tests for the Admin Drill & Verification System.

Run with: pytest tests/test_drills.py -v
"""

import sys
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from app.utils.time_utils import utcnow

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDrillSession:
    """Tests for DrillSession model and enums."""

    def test_drill_type_enum_values(self):
        """Verify DrillType enum has all expected values."""
        from app.models.drill_session import DrillType

        expected = [
            'flash_flood',
            'aqi_spike',
            'heatwave',
            'store_closure',
            'curfew',
            'monsoon_14day',
            'multi_city_aqi',
            'cyclone',
            'bandh',
            'collusion_fraud',
        ]
        actual = [dt.value for dt in DrillType]

        assert set(expected) == set(actual), f"Missing drill types: {set(expected) - set(actual)}"
        print("[PASS] DrillType enum values")

    def test_drill_status_enum_values(self):
        """Verify DrillStatus enum has all expected values."""
        from app.models.drill_session import DrillStatus

        expected = ['started', 'running', 'completed', 'failed']
        actual = [ds.value for ds in DrillStatus]

        assert set(expected) == set(actual), f"Missing statuses: {set(expected) - set(actual)}"
        print("[PASS] DrillStatus enum values")

    def test_drill_session_model_fields(self):
        """Verify DrillSession model has all required fields."""
        from app.models.drill_session import DrillSession

        required_fields = [
            'id', 'drill_id', 'drill_type', 'zone_id', 'zone_code', 'preset',
            'status', 'started_at', 'completed_at', 'pipeline_events',
            'trigger_event_id', 'affected_partners', 'eligible_partners',
            'claims_created', 'claims_paid', 'claims_pending', 'payouts_total',
            'skipped_reasons', 'trigger_latency_ms', 'claim_creation_latency_ms',
            'payout_latency_ms', 'total_latency_ms', 'errors', 'force_mode'
        ]

        # Get column names from model
        columns = [col.key for col in DrillSession.__table__.columns]

        for field in required_fields:
            assert field in columns, f"Missing field: {field}"

        print("[PASS] DrillSession model fields")


class TestDrillSchemas:
    """Tests for Pydantic drill schemas."""

    def test_drill_run_request_schema(self):
        """Verify DrillRunRequest schema structure."""
        from app.schemas.drill import DrillRunRequest
        from app.models.drill_session import DrillType

        # Should accept valid data
        request = DrillRunRequest(
            drill_type=DrillType.FLASH_FLOOD,
            zone_code="BLR-047",
            force=True,
        )
        assert request.drill_type == DrillType.FLASH_FLOOD
        assert request.zone_code == "BLR-047"
        assert request.force == True

        print("[PASS] DrillRunRequest schema")

    def test_drill_impact_response_schema(self):
        """Verify DrillImpactResponse schema structure."""
        from app.schemas.drill import DrillImpactResponse, LatencyMetrics
        from app.models.drill_session import DrillStatus

        impact = DrillImpactResponse(
            drill_id="test-123",
            status=DrillStatus.COMPLETED,
            affected_partners=50,
            eligible_partners=30,
            claims_created=25,
            claims_paid=20,
            claims_pending=5,
            payouts_total=10000.0,
            skipped_partners={"no_policy": 20},
            latency_metrics=LatencyMetrics(
                trigger_latency_ms=100,
                claim_creation_latency_ms=200,
                payout_latency_ms=50,
                total_latency_ms=350,
            ),
        )

        assert impact.affected_partners == 50
        assert impact.claims_created == 25
        assert impact.latency_metrics.total_latency_ms == 350

        print("[PASS] DrillImpactResponse schema")

    def test_verification_check_schema(self):
        """Verify VerificationCheck schema structure."""
        from app.schemas.drill import VerificationCheck

        check = VerificationCheck(
            name="database",
            status="pass",
            message="Database connection healthy",
            latency_ms=15,
        )

        assert check.name == "database"
        assert check.status == "pass"
        assert check.latency_ms == 15

        print("[PASS] VerificationCheck schema")


class TestDrillPresets:
    """Tests for drill preset configurations."""

    def test_drill_presets_exist(self):
        """Verify all drill presets are defined."""
        from app.services.drill_service import DRILL_PRESETS

        expected = ['flash_flood', 'aqi_spike', 'heatwave', 'store_closure', 'curfew']

        for preset in expected:
            assert preset in DRILL_PRESETS, f"Missing preset: {preset}"
            assert 'conditions' in DRILL_PRESETS[preset]
            assert 'trigger_type' in DRILL_PRESETS[preset]

        print("[PASS] All drill presets defined")

    def test_flash_flood_preset(self):
        """Verify flash flood preset configuration."""
        from app.services.drill_service import DRILL_PRESETS

        preset = DRILL_PRESETS['flash_flood']

        assert preset['trigger_type'] == 'rain'
        assert preset['conditions']['weather']['rainfall_mm_hr'] == 72
        assert preset['conditions']['weather']['humidity'] == 95

        print("[PASS] Flash flood preset configuration")

    def test_aqi_spike_preset(self):
        """Verify AQI spike preset configuration."""
        from app.services.drill_service import DRILL_PRESETS

        preset = DRILL_PRESETS['aqi_spike']

        assert preset['trigger_type'] == 'aqi'
        assert preset['conditions']['aqi']['aqi'] == 450
        assert preset['conditions']['aqi']['pm25'] == 280

        print("[PASS] AQI spike preset configuration")

    def test_heatwave_preset(self):
        """Verify heatwave preset configuration."""
        from app.services.drill_service import DRILL_PRESETS

        preset = DRILL_PRESETS['heatwave']

        assert preset['trigger_type'] == 'heat'
        assert preset['conditions']['weather']['temp_celsius'] == 46

        print("[PASS] Heatwave preset configuration")

    def test_apply_preset_conditions(self):
        """Verify preset conditions are applied to mock APIs."""
        from app.services.drill_service import apply_preset_conditions
        from app.services.external_apis import _get_zone_conditions

        result = apply_preset_conditions(zone_id=999, preset_name='flash_flood')

        assert 'applied' in result
        assert result['applied'] == 'flash_flood'
        assert 'conditions' in result

        # Verify conditions were set in internal storage
        # (get_current may use live API if configured, so check internal state)
        zone_cond = _get_zone_conditions(999)
        assert zone_cond['weather']['rainfall'] == 72
        assert zone_cond['weather']['humidity'] == 95

        print("[PASS] Apply preset conditions")


class TestDrillForcedPayoutRegression:
    """
    Forced admin drills call _fire_trigger with duration_min=0. Claim creation must pass
    disruption_hours=None so calculate_payout_amount uses DEFAULT_DISRUPTION_HOURS;
    passing 0.0 would zero out base_payout and create no claims.
    """

    def test_zero_disruption_hours_vs_none_for_payout(self):
        from datetime import datetime, timedelta
        from app.models.trigger_event import TriggerEvent, TriggerType
        from app.models.policy import Policy, PolicyTier, PolicyStatus
        from app.services.claims_processor import calculate_payout_amount

        now = utcnow()
        trigger = TriggerEvent(
            zone_id=1,
            trigger_type=TriggerType.RAIN,
            severity=3,
            started_at=now,
            source_data="{}",
        )
        policy = Policy(
            partner_id=1,
            tier=PolicyTier.STANDARD,
            weekly_premium=33.0,
            max_daily_payout=400.0,
            max_days_per_week=3,
            starts_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=6),
            is_active=True,
            status=PolicyStatus.ACTIVE,
        )

        payout_zero, _ = calculate_payout_amount(trigger, policy, disruption_hours=0.0)
        payout_default, _ = calculate_payout_amount(trigger, policy, disruption_hours=None)

        assert payout_zero == 0.0
        assert payout_default > 0.0

    def test_drill_mock_conditions_override_live_sources(self, monkeypatch):
        from app.services.external_apis import MockWeatherAPI

        MockWeatherAPI.set_conditions(321, rainfall_mm_hr=72, humidity=95)

        def fake_live(*args, **kwargs):
            return type("LiveWeather", (), {
                "zone_id": 321,
                "temp_celsius": 28.0,
                "rainfall_mm_hr": 3.0,
                "humidity": 55.0,
                "timestamp": None,
                "source": "live",
            })()

        monkeypatch.setattr(MockWeatherAPI, "_fetch_live", staticmethod(fake_live))

        # Test with demo_mode disabled (should use live data)
        from app.config import get_settings
        settings = get_settings()
        original_demo_mode = settings.demo_mode

        settings.demo_mode = False
        live_first = MockWeatherAPI.get_current(321)
        assert live_first.source == "live"
        assert live_first.rainfall_mm_hr == 3.0

        # Test with demo_mode enabled (should use mock data)
        settings.demo_mode = True
        mock_first = MockWeatherAPI.get_current(321)
        assert mock_first.source == "mock"
        assert mock_first.rainfall_mm_hr == 72

        # Restore original demo mode
        settings.demo_mode = original_demo_mode


class TestZonePoolShareRegression:
    def test_zone_pool_share_with_zero_reserve_does_not_zero_payout(self):
        from app.services.premium_service import calculate_zone_pool_share

        res = calculate_zone_pool_share(
            calculated_payout=100.0,
            city_weekly_reserve=0.0,
            zone_density_weight=0.15,
            total_partners_in_event=3,
        )

        assert res["final_payout"] == 100.0
        assert res["pool_cap_applied"] is False


class TestDrillService:
    """Tests for drill service functions."""

    def test_create_drill_session(self):
        """Verify drill session creation."""
        from app.services.drill_service import create_drill_session
        from app.models.drill_session import DrillType, DrillStatus

        # Mock database
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        session = create_drill_session(
            drill_type=DrillType.FLASH_FLOOD,
            zone_id=1,
            zone_code="BLR-047",
            preset="flash_flood",
            force=True,
            db=mock_db,
        )

        assert session is not None
        assert session.drill_type == DrillType.FLASH_FLOOD
        assert session.zone_code == "BLR-047"
        assert session.status == DrillStatus.STARTED
        assert session.force_mode == True

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        print("[PASS] Create drill session")

    def test_get_preset_for_drill_type(self):
        """Verify drill type to preset mapping."""
        from app.services.drill_service import get_preset_for_drill_type
        from app.models.drill_session import DrillType

        preset = get_preset_for_drill_type(DrillType.AQI_SPIKE)

        assert preset['trigger_type'] == 'aqi'
        assert 'conditions' in preset

        print("[PASS] Get preset for drill type")


class TestVerificationService:
    """Tests for verification service health checks."""

    def test_health_checks_defined(self):
        """Verify all health checks are defined."""
        from app.services.verification_service import HEALTH_CHECKS

        expected = [
            'database', 'auth_endpoint', 'zone_list', 'trigger_engine',
            'simulation', 'claim_creation', 'payout_service', 'push_notifications',
            'data_sources', 'insurer_intelligence'
        ]

        check_names = [name for name, _ in HEALTH_CHECKS]

        for expected_check in expected:
            assert expected_check in check_names, f"Missing check: {expected_check}"

        print("[PASS] All health checks defined")

    def test_check_simulation(self):
        """Verify simulation check works."""
        from app.services.verification_service import check_simulation

        mock_db = MagicMock()
        success, message = check_simulation(mock_db)

        assert success == True
        assert "injectable" in message.lower() or "working" in message.lower()

        print("[PASS] Check simulation")

    def test_check_claim_creation(self):
        """Verify claim creation check works."""
        from app.services.verification_service import check_claim_creation

        mock_db = MagicMock()
        success, message = check_claim_creation(mock_db)

        assert success == True
        assert "available" in message.lower()

        print("[PASS] Check claim creation")

    def test_run_all_checks(self):
        """Verify run_all_checks returns all check results."""
        from app.services.verification_service import run_all_checks, HEALTH_CHECKS

        mock_db = MagicMock()
        mock_db.query.return_value.limit.return_value.count.return_value = 1
        mock_db.query.return_value.all.return_value = [MagicMock()]
        mock_db.execute.return_value.scalar.return_value = 1

        results = run_all_checks(mock_db)

        assert len(results) == len(HEALTH_CHECKS)

        for result in results:
            assert result.name in [name for name, _ in HEALTH_CHECKS]
            assert result.status in ['pass', 'fail', 'skip']
            assert result.message is not None

        print("[PASS] Run all checks")


class TestAdminDrillsAPI:
    """Tests for admin drills API endpoints."""

    def test_drills_router_registered(self):
        """Verify drills router is registered."""
        from app.api.router import api_router
        from app.api.admin_drills import router as drills_router

        # Check router is included
        route_paths = [route.path for route in api_router.routes]

        # Should have drill endpoints
        assert any('drills' in path for path in route_paths), "Drills router not registered"

        print("[PASS] Drills router registered")

    def test_drill_presets_endpoint_exists(self):
        """Verify drill presets endpoint exists."""
        from app.api.admin_drills import get_drill_presets

        result = get_drill_presets()

        assert 'presets' in result
        assert len(result['presets']) == 10

        for preset in result['presets']:
            assert 'name' in preset
            assert 'trigger_type' in preset
            assert 'conditions' in preset

        print("[PASS] Drill presets endpoint")


class TestDrillIntegration:
    """Integration tests for drill system."""

    def test_drill_pipeline_event_flow(self):
        """Verify pipeline events are generated correctly."""
        from app.services.drill_service import add_pipeline_event
        from app.models.drill_session import DrillSession, DrillType, DrillStatus
        import json

        # Create mock session
        session = DrillSession(
            drill_id="test-123",
            drill_type=DrillType.FLASH_FLOOD,
            zone_id=1,
            zone_code="BLR-047",
            preset="flash_flood",
            status=DrillStatus.RUNNING,
            force_mode=True,
            pipeline_events="[]",
        )

        # Add events
        event1 = add_pipeline_event(session, "injected", "Conditions applied")
        event2 = add_pipeline_event(session, "trigger_fired", "Trigger created", {"trigger_id": 1})

        # Verify events recorded
        events = json.loads(session.pipeline_events)
        assert len(events) == 2
        assert events[0]['step'] == 'injected'
        assert events[1]['step'] == 'trigger_fired'
        assert events[1]['metadata']['trigger_id'] == 1

        print("[PASS] Drill pipeline event flow")

    def test_drill_impact_collection(self):
        """Verify impact metrics are collected correctly."""
        from app.services.drill_service import get_drill_impact
        from app.models.drill_session import DrillSession, DrillType, DrillStatus

        mock_db = MagicMock()

        # Create mock session with impact data
        mock_session = MagicMock()
        mock_session.drill_id = "test-123"
        mock_session.status = DrillStatus.COMPLETED
        mock_session.affected_partners = 50
        mock_session.eligible_partners = 30
        mock_session.claims_created = 25
        mock_session.claims_paid = 20
        mock_session.claims_pending = 5
        mock_session.payouts_total = 10000.0
        mock_session.skipped_reasons = '{"no_policy": 20}'
        mock_session.trigger_latency_ms = 100
        mock_session.claim_creation_latency_ms = 200
        mock_session.payout_latency_ms = 50
        mock_session.total_latency_ms = 350

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        impact = get_drill_impact("test-123", mock_db)

        assert impact is not None
        assert impact.affected_partners == 50
        assert impact.claims_created == 25
        assert impact.payouts_total == 10000.0
        assert impact.skipped_partners['no_policy'] == 20
        assert impact.latency_metrics.total_latency_ms == 350

        print("[PASS] Drill impact collection")


        print("[PASS] Drill impact collection")


class TestInstantReplay:
    """Tests for the Instant Replay demo system."""

    def test_replay_scenarios_list(self):
        """Verify scenario list retrieval."""
        from app.services.replay_service import get_replay_scenarios_list
        scenarios = get_replay_scenarios_list()
        
        assert len(scenarios) > 0
        assert any(s['id'] == 'mumbai_monsoon_2024' for s in scenarios)
        assert any(s['id'] == 'fraud_attack_mumbai' for s in scenarios)
        print("[PASS] Replay scenarios list")

    def test_trigger_replay_scenario_basic(self):
        """Verify basic scenario execution."""
        from app.services.replay_service import trigger_replay_scenario
        from app.models.zone import Zone
        
        mock_db = MagicMock()
        mock_zone = Zone(id=1, code="MUM-01", city="Mumbai")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_zone
        
        # Mock claims_processor.process_trigger_event to return empty list
        with patch('app.services.replay_service.process_trigger_event', return_value=[]):
            result = trigger_replay_scenario("mumbai_monsoon_2024", mock_db)
            
            assert result['status'] == 'success'
            assert result['scenario'] == 'mumbai_monsoon_2024'
            assert result['zone_code'] == 'MUM-01'
            mock_db.add.assert_called()
        print("[PASS] Trigger replay scenario basic")

    def test_trigger_replay_with_fraud(self):
        """Verify fraud injection during replay."""
        from app.services.replay_service import trigger_replay_scenario
        from app.models.zone import Zone
        from app.models.partner import Partner
        
        mock_db = MagicMock()
        mock_zone = Zone(id=1, code="MUM-01", city="Mumbai", dark_store_lat=19.0, dark_store_lng=72.0)
        
        # Setup mocks for zone lookup and partner lookup
        def mock_query(model):
            q = MagicMock()
            if model == Zone:
                q.filter.return_value.first.return_value = mock_zone
            elif model == Partner:
                q.filter.return_value.limit.return_value.all.return_value = [Partner(id=101)]
            return q
            
        mock_db.query.side_effect = mock_query
        
        with patch('app.services.replay_service.process_trigger_event', return_value=[]):
            result = trigger_replay_scenario("fraud_attack_mumbai", mock_db)
            
            assert result['status'] == 'success'
            # Verify GPS ping was added (at least 2 add calls: 1 for trigger, 1 for ping)
            assert mock_db.add.call_count >= 2
        print("[PASS] Trigger replay with fraud injection")


# ============================================================================

# RUN TESTS
# ============================================================================

def run_all_tests():
    """Run all tests and print summary."""
    print("\n" + "=" * 70)
    print("DRILL SYSTEM TESTS")
    print("=" * 70 + "\n")

    results = {"passed": 0, "failed": 0, "errors": []}

    test_classes = [
        ("DrillSession Model", TestDrillSession()),
        ("Drill Schemas", TestDrillSchemas()),
        ("Drill Presets", TestDrillPresets()),
        ("Drill Service", TestDrillService()),
        ("Verification Service", TestVerificationService()),
        ("Admin Drills API", TestAdminDrillsAPI()),
        ("Drill Integration", TestDrillIntegration()),
    ]

    for class_name, test_instance in test_classes:
        print(f"\n--- {class_name} ---\n")

        # Get all test methods
        test_methods = [m for m in dir(test_instance) if m.startswith('test_')]

        for method_name in test_methods:
            try:
                getattr(test_instance, method_name)()
                results["passed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{class_name} - {method_name}: {str(e)}")
                print(f"[FAIL] {method_name}: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
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
