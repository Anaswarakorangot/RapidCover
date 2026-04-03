"""
Pytest fixtures for RapidCover backend tests.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.rollback = MagicMock()
    db.close = MagicMock()
    return db


@pytest.fixture
def mock_zone():
    """Create a mock zone object."""
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
    return zone


@pytest.fixture
def mock_partner():
    """Create a mock partner object."""
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
    return partner


@pytest.fixture
def mock_policy():
    """Create a mock policy object."""
    from datetime import datetime, timedelta
    from app.models.policy import PolicyTier

    policy = MagicMock()
    policy.id = 1
    policy.partner_id = 1
    policy.tier = PolicyTier.STANDARD
    policy.weekly_premium = 33.0
    policy.max_daily_payout = 400.0
    policy.max_weekly_claims = 3
    policy.is_active = True
    policy.starts_at = datetime.utcnow() - timedelta(days=3)
    policy.expires_at = datetime.utcnow() + timedelta(days=4)
    policy.auto_renew = True
    return policy


@pytest.fixture
def mock_claim():
    """Create a mock claim object."""
    from datetime import datetime
    from app.models.claim import ClaimStatus

    claim = MagicMock()
    claim.id = 1
    claim.policy_id = 1
    claim.trigger_event_id = 1
    claim.amount = 300.0
    claim.status = ClaimStatus.PENDING
    claim.fraud_score = 0.15
    claim.upi_ref = None
    claim.created_at = datetime.utcnow()
    claim.paid_at = None
    return claim


@pytest.fixture
def mock_trigger_event():
    """Create a mock trigger event object."""
    from datetime import datetime
    from app.models.trigger_event import TriggerType

    event = MagicMock()
    event.id = 1
    event.zone_id = 1
    event.trigger_type = TriggerType.RAIN
    event.started_at = datetime.utcnow()
    event.ended_at = None
    event.severity = 3
    event.source_data = '{"rainfall_mm_hr": 72}'
    event.created_at = datetime.utcnow()
    return event
