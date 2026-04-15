"""
Pytest fixtures for RapidCover backend tests.

Uses a REAL in-memory SQLite database instead of MagicMock objects.
This ensures tests exercise actual database integration (ORM, constraints,
relationships) rather than giving a false sense of security.
"""

import sys
import os
import json
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.utils.time_utils import utcnow

# Import ALL models so they register with Base.metadata
from app.models.partner import Partner, Platform, Language
from app.models.zone import Zone
from app.models.policy import Policy, PolicyTier, PolicyStatus, TIER_CONFIG
from app.models.trigger_event import TriggerEvent, TriggerType, SustainedEvent
from app.models.claim import Claim, ClaimStatus
from app.models.zone_reassignment import ZoneReassignment
from app.models.zone_risk_profile import ZoneRiskProfile
from app.models.push_subscription import PushSubscription
from app.models.drill_session import DrillSession
from app.models.prediction import WeeklyPrediction, CityRiskProfile
from app.models.fraud import PartnerGPSPing, PartnerDevice
from app.models.weather_observation import WeatherObservation


# ─── Database fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_engine():
    """Create an in-memory SQLite engine for the test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """
    Provide a real database session for each test.

    Uses a nested transaction so each test runs in isolation —
    all changes are rolled back after the test completes.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ─── Backward-compatible mock_db (delegates to real session) ────────────────

@pytest.fixture
def mock_db(db_session):
    """
    Backward-compatible fixture.

    Returns a REAL database session (not a MagicMock).
    Tests that previously used mock_db will now exercise actual DB logic.
    """
    return db_session


# ─── Seed data fixtures ────────────────────────────────────────────────────

@pytest.fixture
def test_zone(db_session) -> Zone:
    """Create a real zone in the test database."""
    zone = Zone(
        code="BLR-047",
        name="Koramangala",
        city="Bangalore",
        dark_store_lat=12.9352,
        dark_store_lng=77.6245,
        risk_score=50.0,
        is_suspended=False,
    )
    db_session.add(zone)
    db_session.commit()
    db_session.refresh(zone)
    return zone


@pytest.fixture
def test_partner(db_session, test_zone) -> Partner:
    """Create a real partner in the test database."""
    partner = Partner(
        phone="9999999999",
        name="Test Partner",
        platform=Platform.ZEPTO,
        zone_id=test_zone.id,
        is_active=True,
        upi_id="test@upi",
        shift_days=["mon", "tue", "wed", "thu", "fri"],
        shift_start="08:00",
        shift_end="20:00",
    )
    db_session.add(partner)
    db_session.commit()
    db_session.refresh(partner)
    return partner


@pytest.fixture
def test_policy(db_session, test_partner) -> Policy:
    """Create a real policy in the test database."""
    now = utcnow()
    policy = Policy(
        partner_id=test_partner.id,
        tier=PolicyTier.STANDARD,
        weekly_premium=33.0,
        max_daily_payout=400.0,
        max_days_per_week=3,
        is_active=True,
        starts_at=now - timedelta(days=3),
        expires_at=now + timedelta(days=4),
        auto_renew=True,
        status=PolicyStatus.ACTIVE,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def test_trigger_event(db_session, test_zone) -> TriggerEvent:
    """Create a real trigger event in the test database."""
    event = TriggerEvent(
        zone_id=test_zone.id,
        trigger_type=TriggerType.RAIN,
        started_at=utcnow(),
        severity=3,
        source_data='{"rainfall_mm_hr": 72}',
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


@pytest.fixture
def test_claim(db_session, test_policy, test_trigger_event) -> Claim:
    """Create a real claim in the test database."""
    claim = Claim(
        policy_id=test_policy.id,
        trigger_event_id=test_trigger_event.id,
        amount=300.0,
        status=ClaimStatus.PENDING,
        fraud_score=0.15,
        validation_data=json.dumps({
            "aggregation": {
                "group_id": "AGG-TESTFIXTURE",
                "is_aggregated": False,
                "primary_trigger_id": test_trigger_event.id,
                "triggers_in_window": [{"id": test_trigger_event.id, "payout": 300.0}],
            }
        }),
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim


# ─── Legacy mock fixtures (for tests that still need MagicMock objects) ─────
# These are kept for backward compatibility with tests that test service-layer
# logic in isolation (without DB). New tests should use the real DB fixtures.

from unittest.mock import MagicMock


@pytest.fixture
def mock_zone():
    """Create a mock zone object (legacy — prefer test_zone)."""
    zone = MagicMock()
    zone.id = 1
    zone.code = "BLR-047"
    zone.name = "Koramangala"
    zone.city = "Bangalore"
    zone.dark_store_lat = 12.9352
    zone.dark_store_lng = 77.6245
    zone.risk_score = 50.0
    zone.is_suspended = False
    zone.density_band = "High"
    zone.pin_codes = None
    zone.density_weight = None
    return zone


@pytest.fixture
def mock_partner():
    """Create a mock partner object (legacy — prefer test_partner)."""
    partner = MagicMock()
    partner.id = 1
    partner.name = "Test Partner"
    partner.phone = "9999999999"
    partner.email = "test@example.com"
    partner.zone_id = 1
    partner.is_active = True
    partner.upi_id = "test@upi"
    partner.shift_days = ["mon", "tue", "wed", "thu", "fri"]
    partner.shift_start = "08:00"
    partner.shift_end = "20:00"
    partner.pin_code = None
    partner.zone_history = []
    partner.platform = MagicMock()
    partner.platform.value = "zepto"
    partner.created_at = utcnow() - timedelta(days=60)
    return partner


@pytest.fixture
def mock_policy():
    """Create a mock policy object (legacy — prefer test_policy)."""
    policy = MagicMock()
    policy.id = 1
    policy.partner_id = 1
    policy.tier = PolicyTier.STANDARD
    policy.weekly_premium = 33.0
    policy.max_daily_payout = 400.0
    policy.max_days_per_week = 3
    policy.max_weekly_claims = 3
    policy.is_active = True
    policy.starts_at = utcnow() - timedelta(days=3)
    policy.expires_at = utcnow() + timedelta(days=4)
    policy.auto_renew = True
    policy.stripe_session_id = None
    return policy


@pytest.fixture
def mock_claim():
    """Create a mock claim object (legacy — prefer test_claim)."""
    claim = MagicMock()
    claim.id = 1
    claim.policy_id = 1
    claim.trigger_event_id = 1
    claim.amount = 300.0
    claim.status = ClaimStatus.PENDING
    claim.fraud_score = 0.15
    claim.upi_ref = None
    claim.created_at = utcnow()
    claim.paid_at = None
    claim.validation_data = json.dumps({
        "aggregation": {
            "group_id": "AGG-TESTFIXTURE",
            "is_aggregated": False,
            "primary_trigger_id": 1,
            "triggers_in_window": [{"id": 1, "payout": 300.0}],
        }
    })
    return claim


@pytest.fixture
def mock_trigger_event():
    """Create a mock trigger event object (legacy — prefer test_trigger_event)."""
    event = MagicMock()
    event.id = 1
    event.zone_id = 1
    event.trigger_type = TriggerType.RAIN
    event.started_at = utcnow()
    event.ended_at = None
    event.severity = 3
    event.source_data = '{"rainfall_mm_hr": 72}'
    event.created_at = utcnow()
    event.zone = None
    return event