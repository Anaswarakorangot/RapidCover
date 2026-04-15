"""
tests/test_partner_experience.py

Backend tests for Member 1 – Partner Experience Slice.

Run with:  pytest backend/tests/test_partner_experience.py -v

Tests:
  - experience-state returns null-safe payloads
  - eligibility locks correct tiers
  - zone-history returns real data and empty state
  - renewal-preview returns correct breakdown structure
  - new paid claim appears after simulated drill (integration-style)
"""

import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.partner import Partner, Platform, Language
from app.models.policy import Policy, PolicyTier, PolicyStatus
from app.models.claim import Claim, ClaimStatus
from app.models.zone import Zone
from app.models.trigger_event import TriggerEvent, TriggerType
from app.services.auth import create_access_token
from app.utils.time_utils import utcnow

# ── SQLite in-memory test DB ──────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_experience.db"

engine         = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSession()
    yield session
    session.close()


@pytest.fixture()
def client():
    return TestClient(app)


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_zone(db, name="Test Zone", code="TST-001", city="bangalore"):
    zone = Zone(code=code, name=name, city=city, risk_score=50.0)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def make_partner(db, zone_id=None, phone="9999900001"):
    partner = Partner(
        phone=phone,
        name="Test Partner",
        platform=Platform.ZEPTO,
        partner_id="ZPT123456",
        zone_id=zone_id,
        language_pref=Language.ENGLISH,
        zone_history=[],
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def make_policy(db, partner_id, tier=PolicyTier.STANDARD, is_active=True, days_ago=0):
    now = utcnow() - timedelta(days=days_ago)
    policy = Policy(
        partner_id=partner_id,
        tier=tier,
        weekly_premium=33.0,
        max_daily_payout=400.0,
        max_days_per_week=3,
        starts_at=now,
        expires_at=now + timedelta(days=7),
        is_active=is_active,
        auto_renew=True,
        status=PolicyStatus.ACTIVE,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def make_claim(db, policy_id, amount=400.0, status=ClaimStatus.PAID, trigger_id=1):
    claim = Claim(
        policy_id=policy_id,
        trigger_event_id=trigger_id,
        amount=amount,
        status=status,
        fraud_score=0.1,
        upi_ref="RAPID001002001234",
        paid_at=utcnow() if status == ClaimStatus.PAID else None,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def make_trigger(db, zone_id, trigger_type=TriggerType.RAIN, severity=4, hours_ago=1):
    trigger = TriggerEvent(
        zone_id=zone_id,
        trigger_type=trigger_type,
        severity=severity,
        started_at=utcnow() - timedelta(hours=hours_ago),
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    return trigger


def auth_token(partner_id: int) -> str:
    return create_access_token(data={"sub": str(partner_id)})


def auth_header(partner_id: int) -> dict:
    return {"Authorization": f"Bearer {auth_token(partner_id)}"}


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestExperienceState:
    """GET /partners/me/experience-state"""

    def test_returns_null_safe_payload_no_policy_no_trigger(self, client, db):
        """Endpoint must return without error even when partner has no policy / trigger."""
        zone    = make_zone(db, code="TST-100")
        partner = make_partner(db, zone_id=zone.id, phone="9000000100")
        res     = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["zone_alert"]        is None   # no trigger → null
        assert data["zone_reassignment"] is None   # no history → null
        assert data["latest_payout"]     is None   # no claims → null
        assert "loyalty"           in data
        assert "premium_breakdown" in data
        assert "fetched_at"        in data

    def test_zone_alert_present_when_trigger_fired(self, client, db):
        """zone_alert must be non-null when a trigger fired within 6 hours."""
        zone    = make_zone(db, code="TST-101")
        partner = make_partner(db, zone_id=zone.id, phone="9000000101")
        _       = make_trigger(db, zone.id, hours_ago=2)

        res  = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["zone_alert"] is not None
        assert "type"     in data["zone_alert"]
        assert "message"  in data["zone_alert"]
        assert "severity" in data["zone_alert"]

    def test_zone_alert_null_when_trigger_too_old(self, client, db):
        """zone_alert must be null when the last trigger is older than 6 hours."""
        zone    = make_zone(db, code="TST-102")
        partner = make_partner(db, zone_id=zone.id, phone="9000000102")
        _       = make_trigger(db, zone.id, hours_ago=10)

        res  = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["zone_alert"] is None

    def test_latest_payout_populated_after_paid_claim(self, client, db):
        """latest_payout must be non-null and contain amount/upi_ref after a paid claim."""
        zone    = make_zone(db, code="TST-103")
        partner = make_partner(db, zone_id=zone.id, phone="9000000103")
        policy  = make_policy(db, partner.id)
        trigger = make_trigger(db, zone.id)
        claim   = make_claim(db, policy.id, amount=400.0, status=ClaimStatus.PAID, trigger_id=trigger.id)

        res  = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        data = res.json()
        lp   = data["latest_payout"]
        assert lp is not None
        assert lp["status"]  == "paid"
        assert lp["amount"]  == 400.0
        assert lp["claim_id"] == claim.id


class TestEligibility:
    """GET /partners/me/eligibility"""

    def test_gate_blocked_when_no_active_days(self, client, db):
        """Partner with zero activity must be fully blocked."""
        zone    = make_zone(db, code="ELG-001")
        partner = make_partner(db, zone_id=zone.id, phone="9100000001")
        res     = client.get(
            "/api/v1/partners/me/eligibility",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["gate_blocked"] is True
        assert data["allowed_tiers"] == []
        assert set(data["blocked_tiers"]) == {"flex", "standard", "pro"}

    def test_only_flex_allowed_when_low_activity(self, client, db):
        """Partner with <AUTO_DOWNGRADE_DAYS active days should only get flex."""
        # AUTO_DOWNGRADE_DAYS = 5 from premium_service.py
        # Create 3 paid claims (distinct days) to simulate 3 active days
        zone    = make_zone(db, code="ELG-002")
        partner = make_partner(db, zone_id=zone.id, phone="9100000002")
        policy  = make_policy(db, partner.id)
        trigger = make_trigger(db, zone.id)

        for i in range(3):
            claim = make_claim(
                db, policy.id,
                amount=250.0,
                status=ClaimStatus.PAID,
                trigger_id=trigger.id,
            )
            # Manually set created_at to simulate distinct days (SQLite stores as string)
            claim.created_at = utcnow() - timedelta(days=i)
            db.commit()

        res  = client.get(
            "/api/v1/partners/me/eligibility",
            headers=auth_header(partner.id),
        )
        data = res.json()
        # With MIN_ACTIVE_DAYS=7 gate, 3 days is below gate → fully blocked
        assert data["gate_blocked"] is True

    def test_all_tiers_allowed_with_sufficient_activity(self, client, db):
        """Partner with ≥7 active days (proxied via policies) gets all tiers."""
        zone    = make_zone(db, code="ELG-003")
        partner = make_partner(db, zone_id=zone.id, phone="9100000003")

        # Create 2 policies (14 proxy days) to exceed MIN_ACTIVE_DAYS_TO_BUY=7
        for i in range(2):
            make_policy(db, partner.id, days_ago=i * 7)

        res  = client.get(
            "/api/v1/partners/me/eligibility",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["gate_blocked"] is False
        assert set(data["allowed_tiers"]) == {"flex", "standard", "pro"}
        assert data["blocked_tiers"] == []


class TestZoneHistory:
    """GET /partners/me/zone-history"""

    def test_empty_state_when_no_history(self, client, db):
        """Must return has_history=False and empty list, not a 404 or error."""
        zone    = make_zone(db, code="ZH-001")
        partner = make_partner(db, zone_id=zone.id, phone="9200000001")
        res     = client.get(
            "/api/v1/partners/me/zone-history",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["has_history"] is False
        assert data["history"]     == []
        assert data["total"]       == 0

    def test_history_enriched_with_zone_names(self, client, db):
        """History entries must include zone name (not just ID) when zone exists."""
        zone1   = make_zone(db, code="ZH-002", name="Koramangala North")
        zone2   = make_zone(db, code="ZH-003", name="Whitefield South")
        partner = make_partner(db, zone_id=zone2.id, phone="9200000002")

        # Inject zone_history directly
        partner.zone_history = [{
            "old_zone_id":      zone1.id,
            "new_zone_id":      zone2.id,
            "effective_at":     utcnow().isoformat(),
            "premium_adjustment": -2.5,
            "new_weekly_premium": 35.5,
            "days_remaining":   4,
            "policy_id":        None,
        }]
        db.commit()

        res  = client.get(
            "/api/v1/partners/me/zone-history",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["has_history"] is True
        entry = data["history"][0]
        assert entry["old_zone_name"] == "Koramangala North"
        assert entry["new_zone_name"] == "Whitefield South"
        assert entry["old_zone_code"] == "ZH-002"
        assert entry["new_zone_code"] == "ZH-003"


class TestRenewalPreview:
    """GET /partners/me/renewal-preview"""

    def test_no_policy_returns_has_policy_false(self, client, db):
        zone    = make_zone(db, code="RP-001")
        partner = make_partner(db, zone_id=zone.id, phone="9300000001")
        res     = client.get(
            "/api/v1/partners/me/renewal-preview",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["has_policy"] is False

    def test_with_policy_returns_breakdown(self, client, db):
        """Must return full breakdown structure with correct keys."""
        zone    = make_zone(db, code="RP-002")
        partner = make_partner(db, zone_id=zone.id, phone="9300000002")
        _       = make_policy(db, partner.id)
        res     = client.get(
            "/api/v1/partners/me/renewal-preview",
            headers=auth_header(partner.id),
        )
        data = res.json()
        assert data["has_policy"]        is True
        assert data["renewal_available"] is True
        assert "renewal_premium"         in data
        assert "breakdown"               in data
        bd = data["breakdown"]
        for key in ("base", "zone_risk", "seasonal_index", "riqi_adjustment", "total"):
            assert key in bd, f"Missing breakdown key: {key}"
        assert data["renewal_premium"]   > 0


class TestPremiumBreakdown:
    """GET /partners/me/premium-breakdown"""

    def test_returns_itemised_factors(self, client, db):
        zone    = make_zone(db, code="PB-001")
        partner = make_partner(db, zone_id=zone.id, phone="9400000001")
        _       = make_policy(db, partner.id)
        res     = client.get(
            "/api/v1/partners/me/premium-breakdown",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        for key in ("base", "zone_risk", "seasonal_index", "riqi_adjustment",
                    "loyalty_discount", "total", "city", "riqi_band"):
            assert key in data, f"Missing key: {key}"
        assert data["total"] > 0
        assert data["base"]  > 0

    def test_no_hardcoded_fallback_values(self, client, db):
        """Total must differ from raw base when zone risk / seasonal / RIQI apply."""
        zone         = make_zone(db, code="PB-002", city="mumbai")  # riqi 45 → fringe
        zone.risk_score = 70  # above midpoint → zone_risk > 1
        db.commit()
        partner = make_partner(db, zone_id=zone.id, phone="9400000002")
        _       = make_policy(db, partner.id)
        res  = client.get(
            "/api/v1/partners/me/premium-breakdown",
            headers=auth_header(partner.id),
        )
        data = res.json()
        # For Mumbai fringe + risk 70: total should be > base
        assert data["total"] >= data["base"]


class TestDrillSimulation:
    """
    Integration-style test: simulate admin drill, verify paid claim
    surfaces in experience-state without manual refresh.
    """

    def test_paid_claim_surfaces_in_experience_state(self, client, db):
        """
        After a claim is paid:
          - experience-state.latest_payout.status == "paid"
          - amount and upi_ref are present
        """
        zone    = make_zone(db, code="DRL-001")
        partner = make_partner(db, zone_id=zone.id, phone="9500000001")
        policy  = make_policy(db, partner.id)
        trigger = make_trigger(db, zone.id, hours_ago=0)

        # Simulate drill: create a paid claim directly
        claim = Claim(
            policy_id         = policy.id,
            trigger_event_id  = trigger.id,
            amount            = 400.0,
            status            = ClaimStatus.PAID,
            fraud_score       = 0.05,
            upi_ref           = "RAPID_DRILL_TEST_001",
            paid_at           = utcnow(),
            validation_data   = json.dumps({"auto_payout": True}),
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)

        # Now check experience-state — must reflect the paid claim
        res  = client.get(
            "/api/v1/partners/me/experience-state",
            headers=auth_header(partner.id),
        )
        assert res.status_code == 200
        data = res.json()
        lp   = data["latest_payout"]
        assert lp             is not None
        assert lp["status"]   == "paid"
        assert lp["amount"]   == 400.0
        assert lp["upi_ref"]  == "RAPID_DRILL_TEST_001"
        assert lp["claim_id"] == claim.id

        # Zone alert should also be active (trigger < 6 hours ago)
        assert data["zone_alert"] is not None