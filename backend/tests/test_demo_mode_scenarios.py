from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.router import api_router
from app.database import Base, get_db
from app.models.partner import Language, Partner, Platform
from app.models.policy import Policy, PolicyStatus, PolicyTier
from app.models.zone import Zone
from app.services.auth import create_access_token
from app.utils.time_utils import utcnow


TEST_DB_URL = "sqlite://"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(api_router)
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


def make_zone(db, code="DMO-001", city="bangalore"):
    zone = Zone(
        code=code,
        name=f"Zone {code}",
        city=city,
        risk_score=50.0,
        dark_store_lat=12.9716,
        dark_store_lng=77.5946,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def make_partner(db, zone_id, phone="9000011111"):
    partner = Partner(
        phone=phone,
        name="Demo Partner",
        platform=Platform.ZEPTO,
        partner_id=f"ZPT{phone[-6:]}",
        zone_id=zone_id,
        language_pref=Language.ENGLISH,
        zone_history=[],
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def make_policy(db, partner_id):
    now = utcnow()
    policy = Policy(
        partner_id=partner_id,
        tier=PolicyTier.STANDARD,
        weekly_premium=33.0,
        max_daily_payout=400.0,
        max_days_per_week=3,
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=6),
        is_active=True,
        auto_renew=True,
        status=PolicyStatus.ACTIVE,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def auth_header(partner_id: int) -> dict:
    token = create_access_token(data={"sub": str(partner_id)})
    return {"Authorization": f"Bearer {token}"}


def test_list_scenarios_returns_catalog(client, db):
    zone = make_zone(db, code="DMO-CAT")
    make_partner(db, zone.id, phone="9000011112")

    res = client.get("/api/v1/admin/panel/demo-mode/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert any(item["id"] == "standard_trigger" for item in data["scenarios"])
    assert any(item["id"] == zone.id for item in data["zones"])


def test_run_and_cleanup_standard_scenario(client, db):
    zone = make_zone(db, code="DMO-RUN")
    partner = make_partner(db, zone.id, phone="9000011113")
    make_policy(db, partner.id)

    run_res = client.post(
        "/api/v1/admin/panel/demo-mode/run",
        json={
            "scenario_type": "standard_trigger",
            "zone_id": zone.id,
            "trigger_type": "rain",
            "severity": 4,
            "enforce_restrictions": True,
            "inject_sustained_days": 0,
            "auto_mark_paid": False,
        },
    )
    assert run_res.status_code == 200, run_res.text
    run_data = run_res.json()
    assert run_data["trigger"]["type"] == "rain"
    assert run_data["claims"]["summary"]["total"] >= 1
    assert run_data["visibility"]["partner_claims_history"] is True

    get_res = client.get(f"/api/v1/admin/panel/demo-mode/run/{run_data['run_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["run_id"] == run_data["run_id"]

    cleanup_res = client.post(f"/api/v1/admin/panel/demo-mode/run/{run_data['run_id']}/cleanup")
    assert cleanup_res.status_code == 200
    cleanup_data = cleanup_res.json()
    assert cleanup_data["status"] == "cleaned_up"
    assert cleanup_data["trigger"]["active"] is False
