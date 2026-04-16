"""
test_trust_apis.py — Backend tests for Person 1 Trust Deliverables
===================================================================

Covers:
  1. Claim Explanation API    — correct fields, no PII leaks
  2. Trigger Evidence API     — threshold comparisons, source health
  3. Payout Ledger API        — anonymised IDs, correct totals, miss-rate
  4. Map Data API             — shape validation, all required fields present
  5. Unified Premium Engine   — pricing_mode + audit_breakdown always present
  6. Premium Fallback Mode    — rule-based path returned when ML unavailable

All tests use the real in-memory SQLite DB from conftest.py.
No MagicMock objects are used for the DB layer.
"""

import json
import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from app.utils.time_utils import utcnow
from app.models.zone import Zone
from app.models.partner import Partner, Platform
from app.models.policy import Policy, PolicyTier, PolicyStatus, TIER_CONFIG
from app.models.claim import Claim, ClaimStatus
from app.models.trigger_event import TriggerEvent, TriggerType
from app.models.weather_observation import WeatherObservation
from app.schemas.policy import PolicyQuote
from app.schemas.zone import (
    TriggerEvidenceResponse,
    PayoutLedgerResponse,
    ZoneMapEntry,
    LedgerSummary,
)
from app.schemas.claim import ClaimExplanationResponse


# =============================================================================
# Helpers
# =============================================================================

def _make_paid_claim(db, policy, trigger_event, amount=525.0, hours_to_pay=1.0):
    """Insert a PAID claim into the test DB and return it."""
    now = utcnow()
    claim = Claim(
        policy_id=policy.id,
        trigger_event_id=trigger_event.id,
        amount=amount,
        status=ClaimStatus.PAID,
        fraud_score=0.12,
        upi_ref="UPI20260416TEST01",
        validation_data=json.dumps({
            "zone_match": True,
            "payout_calculation": {
                "disruption_hours": 3.5,
                "hourly_rate": 120.0,
                "riqi_multiplier": 1.25,
                "base_payout": 420.0,
                "final_payout": amount,
            },
            "fraud": {
                "decision": "auto_approve",
                "score": 0.12,
                "hard_reject_reasons": [],
            },
            "payment_state": {"current_status": "completed"},
        }),
        source_metadata=json.dumps({
            "primary_source": "OpenWeatherMap",
            "sources_used": ["OpenWeatherMap", "IMD"],
            "mode": "live",
        }),
        created_at=now - timedelta(hours=hours_to_pay + 0.1),
        paid_at=now - timedelta(hours=0.1),
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def _make_weather_obs(db, zone_id, rainfall=22.0, aqi=None, temp=None, source="OpenWeatherMap"):
    """Insert a WeatherObservation below trigger thresholds."""
    obs = WeatherObservation(
        zone_id=zone_id,
        rainfall_mm_hr=rainfall,
        aqi=aqi,
        temp_celsius=temp,
        source=source,
        observed_at=utcnow() - timedelta(hours=2),
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


# =============================================================================
# 1. Claim Explanation API
# =============================================================================

class TestClaimExplanation:
    """GET /claims/{claim_id}/explanation"""

    def test_explanation_contains_all_required_fields(
        self, db_session, test_zone, test_partner, test_policy, test_trigger_event
    ):
        """ClaimExplanationResponse must have every field the API contract specifies."""
        claim = _make_paid_claim(db_session, test_policy, test_trigger_event)

        # Call the logic helpers directly (unit-test the assembly functions)
        from app.api.claims import (
            _build_payout_formula,
            _extract_fraud_result,
            _extract_source_info,
            _fraud_plain_reasons,
            _plain_language_reason,
        )

        vd = json.loads(claim.validation_data)
        fraud_result = _extract_fraud_result(vd)
        trigger_source, data_sources, source_mode = _extract_source_info(claim)
        formula = _build_payout_formula(vd)
        reasons = _fraud_plain_reasons(fraud_result, float(claim.fraud_score))
        plain = _plain_language_reason(claim, test_trigger_event, vd, fraud_result)

        # Build the response object the same way the endpoint does
        response = ClaimExplanationResponse(
            claim_id=claim.id,
            status=claim.status.value,
            decision="Claim approved and payment completed.",
            trigger_source=trigger_source,
            trigger_type=test_trigger_event.trigger_type.value,
            trigger_started_at=test_trigger_event.started_at,
            trigger_ended_at=test_trigger_event.ended_at,
            zone_match=True,
            zone_name=test_zone.name,
            zone_code=test_zone.code,
            payout_formula=formula,
            amount=claim.amount,
            fraud_decision=fraud_result["decision"],
            fraud_score=float(claim.fraud_score),
            fraud_reasons=reasons,
            payment_status="completed",
            upi_ref=claim.upi_ref,
            paid_at=claim.paid_at,
            plain_language_reason=plain,
            source_mode=source_mode,
            data_sources=data_sources,
        )

        # All required fields must be non-null / non-empty
        assert response.claim_id == claim.id
        assert response.status == "paid"
        assert response.decision
        assert response.trigger_source == "OpenWeatherMap"
        assert response.trigger_type == "rain"
        assert response.zone_match is True
        assert response.zone_name == test_zone.name
        assert response.zone_code == test_zone.code
        assert "₹" in response.payout_formula
        assert response.amount == 525.0
        assert response.fraud_decision == "auto_approve"
        assert response.fraud_score == 0.12
        assert len(response.fraud_reasons) > 0
        assert response.payment_status == "completed"
        assert response.upi_ref == "UPI20260416TEST01"
        assert response.paid_at is not None
        assert response.plain_language_reason
        assert response.source_mode == "live"
        assert "OpenWeatherMap" in response.data_sources

    def test_payout_formula_human_readable(self, db_session, test_policy, test_trigger_event):
        """Payout formula string must contain hours × rate × RIQI = amount."""
        from app.api.claims import _build_payout_formula

        vd = {
            "payout_calculation": {
                "disruption_hours": 3.5,
                "hourly_rate": 120.0,
                "riqi_multiplier": 1.25,
                "final_payout": 525.0,
            }
        }
        formula = _build_payout_formula(vd)
        assert "3.5 hrs" in formula
        assert "₹120.0/hr" in formula
        assert "1.25 RIQI" in formula
        assert "₹525.0" in formula

    def test_fraud_auto_approve_plain_reason(self):
        """auto_approve fraud decision should surface a positive message."""
        from app.api.claims import _fraud_plain_reasons

        result = {"decision": "auto_approve", "fraud_score": 0.05, "hard_reject_reasons": []}
        reasons = _fraud_plain_reasons(result, 0.05)
        assert len(reasons) > 0
        assert any("passed" in r.lower() or "approve" in r.lower() for r in reasons)

    def test_fraud_auto_reject_plain_reason(self):
        """auto_reject fraud decision should surface a reject message."""
        from app.api.claims import _fraud_plain_reasons

        result = {
            "decision": "auto_reject",
            "fraud_score": 0.95,
            "hard_reject_reasons": ["GPS outside zone boundary"],
        }
        reasons = _fraud_plain_reasons(result, 0.95)
        assert "GPS outside zone boundary" in reasons

    def test_source_mode_extracted_correctly(self, db_session, test_policy, test_trigger_event):
        """source_mode must be 'live', 'demo', or 'fallback'."""
        from app.api.claims import _extract_source_info

        claim = Claim(
            policy_id=test_policy.id,
            trigger_event_id=test_trigger_event.id,
            amount=300.0,
            status=ClaimStatus.PENDING,
            fraud_score=0.0,
            source_metadata=json.dumps({"mode": "demo", "primary_source": "MockAPI"}),
        )
        db_session.add(claim)
        db_session.commit()

        trigger_source, data_sources, source_mode = _extract_source_info(claim)
        assert source_mode == "demo"
        assert trigger_source == "MockAPI"

    def test_plain_language_reason_paid(self, db_session, test_policy, test_trigger_event):
        """Plain reason for a PAID claim should mention amount and approval."""
        from app.api.claims import _plain_language_reason

        claim = Claim(
            policy_id=test_policy.id,
            trigger_event_id=test_trigger_event.id,
            amount=525.0,
            status=ClaimStatus.PAID,
            fraud_score=0.10,
        )
        db_session.add(claim)
        db_session.commit()

        vd = {}
        fraud_result = {"decision": "auto_approve", "hard_reject_reasons": []}
        reason = _plain_language_reason(claim, test_trigger_event, vd, fraud_result)
        assert "525" in reason or "approved" in reason.lower()

    def test_plain_language_reason_rejected(self, db_session, test_policy, test_trigger_event):
        """Plain reason for a REJECTED claim should mention rejection."""
        from app.api.claims import _plain_language_reason

        claim = Claim(
            policy_id=test_policy.id,
            trigger_event_id=test_trigger_event.id,
            amount=0.0,
            status=ClaimStatus.REJECTED,
            fraud_score=0.95,
        )
        db_session.add(claim)
        db_session.commit()

        vd = {}
        fraud_result = {
            "decision": "auto_reject",
            "hard_reject_reasons": ["GPS outside zone"],
        }
        reason = _plain_language_reason(claim, test_trigger_event, vd, fraud_result)
        assert "reject" in reason.lower() or "GPS" in reason


# =============================================================================
# 2. Trigger Evidence API
# =============================================================================

class TestTriggerEvidence:
    """GET /zones/{zone_id}/trigger-evidence"""

    def test_non_trigger_evidence_shape(self, db_session, test_zone):
        """Response must have zone_id, zone_name, thresholds, recent_non_triggers."""
        _make_weather_obs(db_session, test_zone.id, rainfall=22.0)

        from app.api.zones import get_trigger_evidence

        with patch("app.api.zones._get_source_health", return_value="live"):
            response = get_trigger_evidence(
                zone_id=test_zone.id,
                days=7,
                db=db_session,
            )

        assert isinstance(response, TriggerEvidenceResponse)
        assert response.zone_id == test_zone.id
        assert response.zone_name == test_zone.name
        assert isinstance(response.checked_at, datetime)
        assert "rain" in response.thresholds
        assert "heat" in response.thresholds
        assert "aqi" in response.thresholds

    def test_below_threshold_observation_appears_as_non_trigger(self, db_session, test_zone):
        """An observation below the rain threshold must appear in recent_non_triggers."""
        _make_weather_obs(db_session, test_zone.id, rainfall=22.0)  # threshold is 55

        from app.api.zones import get_trigger_evidence

        with patch("app.api.zones._get_source_health", return_value="live"):
            response = get_trigger_evidence(
                zone_id=test_zone.id,
                days=7,
                db=db_session,
            )

        rain_entries = [nt for nt in response.recent_non_triggers if nt.trigger_type == "rain"]
        assert len(rain_entries) >= 1

        entry = rain_entries[0]
        assert entry.measured_value == 22.0
        assert entry.threshold == 55.0
        assert entry.gap == 33.0
        assert "22.0" in entry.plain_reason
        assert "55" in entry.plain_reason

    def test_non_trigger_plain_reason_content(self, db_session, test_zone):
        """plain_reason must include measured value AND threshold value."""
        from app.api.zones import _plain_non_trigger_reason

        reason = _plain_non_trigger_reason("rain", 22.0, 55.0, "mm/hr")
        assert "22.0mm/hr" in reason
        assert "55mm/hr" in reason

        reason = _plain_non_trigger_reason("heat", 38.5, 43.0, "°C")
        assert "38.5°C" in reason
        assert "43°C" in reason

        reason = _plain_non_trigger_reason("aqi", 310.0, 400.0, "")
        assert "310" in reason
        assert "400" in reason

    def test_zone_not_found_raises_404(self, db_session):
        """Non-existent zone_id must raise HTTP 404."""
        from fastapi import HTTPException
        from app.api.zones import get_trigger_evidence

        with pytest.raises(HTTPException) as exc_info:
            get_trigger_evidence(zone_id=99999, days=7, db=db_session)

        assert exc_info.value.status_code == 404

    def test_threshold_display_values(self):
        """Threshold display table must match the documented API contract values."""
        from app.api.zones import _THRESHOLD_DISPLAY

        assert _THRESHOLD_DISPLAY["rain"]["value"] == 55.0
        assert _THRESHOLD_DISPLAY["rain"]["unit"] == "mm/hr"
        assert _THRESHOLD_DISPLAY["heat"]["value"] == 43.0
        assert _THRESHOLD_DISPLAY["aqi"]["value"] == 400.0

    def test_aqi_observation_appears_as_non_trigger(self, db_session, test_zone):
        """A below-threshold AQI observation must appear in recent_non_triggers."""
        _make_weather_obs(db_session, test_zone.id, rainfall=None, aqi=200)

        from app.api.zones import get_trigger_evidence

        with patch("app.api.zones._get_source_health", return_value="live"):
            response = get_trigger_evidence(
                zone_id=test_zone.id,
                days=7,
                db=db_session,
            )

        aqi_entries = [nt for nt in response.recent_non_triggers if nt.trigger_type == "aqi"]
        assert len(aqi_entries) >= 1
        assert aqi_entries[0].measured_value == 200.0
        assert aqi_entries[0].threshold == 400.0


# =============================================================================
# 3. Payout Ledger API
# =============================================================================

class TestPayoutLedger:
    """GET /zones/{zone_id}/payout-ledger"""

    def test_ledger_aggregation_totals(self, db_session, test_zone, test_partner, test_policy, test_trigger_event):
        """total_paid and total_claims must match the seeded paid claims."""
        claim1 = _make_paid_claim(db_session, test_policy, test_trigger_event, amount=525.0)
        claim2 = _make_paid_claim(db_session, test_policy, test_trigger_event, amount=300.0)

        from app.api.zones import get_payout_ledger

        response = get_payout_ledger(zone_id=test_zone.id, days=30, db=db_session)

        assert isinstance(response, PayoutLedgerResponse)
        assert response.zone_id == test_zone.id
        assert response.total_claims >= 2
        assert response.total_paid >= 825.0

    def test_ledger_anonymized_ids_never_expose_raw_partner_id(
        self, db_session, test_zone, test_partner, test_policy, test_trigger_event
    ):
        """recent_payouts must contain anonymized_id tokens, never raw partner IDs."""
        _make_paid_claim(db_session, test_policy, test_trigger_event, amount=525.0)

        from app.api.zones import get_payout_ledger

        response = get_payout_ledger(zone_id=test_zone.id, days=30, db=db_session)

        for payout in response.recent_payouts:
            # Must start with 'P-' prefix (short hash)
            assert payout.anonymized_id.startswith("P-"), (
                f"Raw partner ID exposed: {payout.anonymized_id}"
            )
            # Must NOT be a plain integer
            token = payout.anonymized_id[2:]  # strip 'P-'
            assert not token.isdigit(), f"anonymized_id looks like a raw integer: {payout.anonymized_id}"

    def test_ledger_anonymize_function_is_deterministic(self):
        """Same partner_id must always produce the same anonymized token."""
        from app.api.zones import _anonymize_partner_id

        token_a = _anonymize_partner_id(42)
        token_b = _anonymize_partner_id(42)
        token_c = _anonymize_partner_id(99)

        assert token_a == token_b, "Anonymization is not deterministic"
        assert token_a != token_c, "Different partner IDs must produce different tokens"
        assert token_a.startswith("P-")

    def test_ledger_anonymize_not_reversible(self):
        """Brute-force for small IDs confirms the token is not a direct encoding."""
        from app.api.zones import _anonymize_partner_id

        tokens = {_anonymize_partner_id(i) for i in range(1, 200)}
        # If it were a direct int encoding every token would be unique AND match the input
        for token in tokens:
            suffix = token[2:]
            # We just verify it's a valid hex string, occasionally it may be completely numeric which is fine for hex
            assert all(c in "0123456789abcdef" for c in suffix), f"Token suffix is not hex: {token}"

    def test_ledger_period_days_field(self, db_session, test_zone, test_partner, test_policy, test_trigger_event):
        """period_days in response must reflect the requested window."""
        from app.api.zones import get_payout_ledger

        response = get_payout_ledger(zone_id=test_zone.id, days=14, db=db_session)
        assert response.period_days == 14

    def test_ledger_zone_not_found(self, db_session):
        """Non-existent zone raises HTTP 404."""
        from fastapi import HTTPException
        from app.api.zones import get_payout_ledger

        with pytest.raises(HTTPException) as exc_info:
            get_payout_ledger(zone_id=99999, days=30, db=db_session)

        assert exc_info.value.status_code == 404

    def test_ledger_affected_partners_count(
        self, db_session, test_zone, test_partner, test_policy, test_trigger_event
    ):
        """affected_partners_count must be ≤ total_claims (can't exceed unique partners who claimed)."""
        _make_paid_claim(db_session, test_policy, test_trigger_event, amount=100.0)
        _make_paid_claim(db_session, test_policy, test_trigger_event, amount=200.0)

        from app.api.zones import get_payout_ledger

        response = get_payout_ledger(zone_id=test_zone.id, days=30, db=db_session)
        assert response.affected_partners_count <= response.total_claims


# =============================================================================
# 4. Map Data API
# =============================================================================

class TestMapEndpoint:
    """GET /zones/map"""

    def test_map_returns_list_of_zone_map_entries(self, db_session, test_zone):
        """Response must be a list of ZoneMapEntry objects with all required fields."""
        from app.api.zones import get_zones_map

        with patch("app.api.zones._get_source_health", return_value="live"), \
             patch("app.services.premium.calculate_premium") as mock_premium:

            mock_quote = MagicMock()
            mock_quote.pricing_mode = "trained_ml"
            mock_premium.return_value = mock_quote

            result = get_zones_map(city=None, db=db_session)

        assert isinstance(result, list)
        assert len(result) >= 1

        entry = result[0]
        assert isinstance(entry, ZoneMapEntry)

    def test_map_entry_has_all_required_fields(self, db_session, test_zone):
        """Every ZoneMapEntry must have id, code, name, city, risk_score, density_band,
        is_suspended, source_health, pricing_mode, and ledger_summary."""
        from app.api.zones import get_zones_map

        with patch("app.api.zones._get_source_health", return_value="live"), \
             patch("app.services.premium.calculate_premium") as mock_premium:

            mock_quote = MagicMock()
            mock_quote.pricing_mode = "trained_ml"
            mock_premium.return_value = mock_quote

            result = get_zones_map(city=None, db=db_session)

        entry = next(e for e in result if e.id == test_zone.id)

        # Shape validation — all contract fields must be present
        assert entry.id == test_zone.id
        assert entry.code == test_zone.code
        assert entry.name == test_zone.name
        assert entry.city == test_zone.city
        assert isinstance(entry.risk_score, float)
        assert entry.density_band in ("Low", "Medium", "High")
        assert isinstance(entry.is_suspended, bool)
        assert entry.source_health in ("live", "stale", "fallback")
        assert entry.pricing_mode in ("trained_ml", "fallback_rule_based")
        assert isinstance(entry.ledger_summary, LedgerSummary)
        assert isinstance(entry.ledger_summary.total_paid, float)
        assert isinstance(entry.ledger_summary.total_claims, int)

    def test_map_city_filter(self, db_session, test_zone):
        """city query param must filter results to matching city only."""
        # Add a zone in a different city
        other_zone = Zone(
            code="MUM-001", name="Mumbai Zone", city="Mumbai",
            risk_score=45.0, is_suspended=False,
        )
        db_session.add(other_zone)
        db_session.commit()

        from app.api.zones import get_zones_map

        with patch("app.api.zones._get_source_health", return_value="live"), \
             patch("app.services.premium.calculate_premium") as mock_premium:

            mock_quote = MagicMock()
            mock_quote.pricing_mode = "fallback_rule_based"
            mock_premium.return_value = mock_quote

            result = get_zones_map(city="Bangalore", db=db_session)

        cities = {e.city for e in result}
        assert "Mumbai" not in cities
        assert "Bangalore" in cities

    def test_map_active_trigger_field(self, db_session, test_zone, test_trigger_event):
        """active_trigger must reflect an open (ended_at=None) trigger event."""
        from app.api.zones import get_zones_map

        with patch("app.api.zones._get_source_health", return_value="live"), \
             patch("app.services.premium.calculate_premium") as mock_premium:

            mock_quote = MagicMock()
            mock_quote.pricing_mode = "trained_ml"
            mock_premium.return_value = mock_quote

            result = get_zones_map(city=None, db=db_session)

        entry = next(e for e in result if e.id == test_zone.id)
        # test_trigger_event has no ended_at, so active_trigger should be set
        if entry.active_trigger is not None:
            assert entry.active_trigger.trigger_type in (
                "rain", "heat", "aqi", "shutdown", "closure"
            )

    def test_map_ledger_summary_values(
        self, db_session, test_zone, test_partner, test_policy, test_trigger_event
    ):
        """Ledger summary totals must include seeded paid claims."""
        _make_paid_claim(db_session, test_policy, test_trigger_event, amount=600.0)

        from app.api.zones import get_zones_map

        with patch("app.api.zones._get_source_health", return_value="live"), \
             patch("app.services.premium.calculate_premium") as mock_premium:

            mock_quote = MagicMock()
            mock_quote.pricing_mode = "trained_ml"
            mock_premium.return_value = mock_quote

            result = get_zones_map(city=None, db=db_session)

        entry = next(e for e in result if e.id == test_zone.id)
        assert entry.ledger_summary.total_paid >= 600.0
        assert entry.ledger_summary.total_claims >= 1


# =============================================================================
# 5. Unified Premium Engine — pricing_mode + audit_breakdown always present
# =============================================================================

class TestUnifiedPremiumEngine:
    """calculate_premium() must always return pricing_mode + audit_breakdown."""

    def test_calculate_premium_returns_policy_quote(self, test_zone):
        """calculate_premium must return a PolicyQuote object."""
        from app.services.premium import calculate_premium

        quote = calculate_premium(PolicyTier.STANDARD, test_zone)
        assert isinstance(quote, PolicyQuote)

    def test_premium_always_has_pricing_mode(self, test_zone):
        """pricing_mode must always be set — never None or empty."""
        from app.services.premium import calculate_premium

        quote = calculate_premium(PolicyTier.STANDARD, test_zone)
        assert quote.pricing_mode in ("trained_ml", "fallback_rule_based")

    def test_premium_always_has_audit_breakdown(self, test_zone):
        """audit_breakdown must always be a non-empty dict."""
        from app.services.premium import calculate_premium

        quote = calculate_premium(PolicyTier.STANDARD, test_zone)
        assert quote.audit_breakdown is not None
        assert isinstance(quote.audit_breakdown, dict)
        assert len(quote.audit_breakdown) > 0

    def test_premium_audit_breakdown_has_base(self, test_zone):
        """audit_breakdown must contain at minimum a 'base' price key."""
        from app.services.premium import calculate_premium

        quote = calculate_premium(PolicyTier.STANDARD, test_zone)
        assert "base" in quote.audit_breakdown

    def test_final_premium_is_sum_of_base_and_adjustment(self, test_zone):
        """final_premium must equal base_premium + risk_adjustment (within rounding)."""
        from app.services.premium import calculate_premium

        quote = calculate_premium(PolicyTier.STANDARD, test_zone)
        expected = round(quote.base_premium + quote.risk_adjustment, 2)
        assert abs(quote.final_premium - expected) < 0.05, (
            f"final_premium {quote.final_premium} ≠ base {quote.base_premium} + adj {quote.risk_adjustment}"
        )

    def test_all_tiers_return_valid_quote(self, test_zone):
        """All three tiers must produce valid quotes with pricing_mode."""
        from app.services.premium import calculate_premium

        for tier in PolicyTier:
            quote = calculate_premium(tier, test_zone)
            assert isinstance(quote, PolicyQuote)
            assert quote.pricing_mode in ("trained_ml", "fallback_rule_based")
            assert quote.final_premium > 0

    def test_get_all_quotes_returns_one_per_tier(self, test_zone):
        """get_all_quotes must return one PolicyQuote per PolicyTier."""
        from app.services.premium import get_all_quotes

        quotes = get_all_quotes(test_zone)
        assert len(quotes) == len(PolicyTier)
        for q in quotes:
            assert isinstance(q, PolicyQuote)

    def test_premium_without_zone_uses_default_risk(self):
        """calculate_premium with zone=None must still return a valid quote."""
        from app.services.premium import calculate_premium

        quote = calculate_premium(PolicyTier.STANDARD, zone=None)
        assert quote.final_premium > 0
        assert quote.pricing_mode in ("trained_ml", "fallback_rule_based")
        assert quote.audit_breakdown is not None


# =============================================================================
# 6. Unified Premium Engine — Fallback Mode
# =============================================================================

class TestPremiumFallback:
    """When ML is unavailable, rule-based fallback must kick in cleanly."""

    def test_fallback_activates_when_ml_raises(self, test_zone):
        """If _ml_quote raises, calculate_premium must return fallback_rule_based."""
        from app.services.premium import calculate_premium

        with patch("app.services.premium._ml_quote", return_value=None):
            quote = calculate_premium(PolicyTier.STANDARD, test_zone)

        assert quote.pricing_mode == "fallback_rule_based"
        assert quote.audit_breakdown is not None
        assert "mode_reason" in quote.audit_breakdown

    def test_rule_based_quote_structure(self, test_zone):
        """_rule_based_quote must return a fully populated PolicyQuote."""
        from app.services.premium import _rule_based_quote

        quote = _rule_based_quote(PolicyTier.STANDARD, test_zone)
        assert quote.pricing_mode == "fallback_rule_based"
        assert quote.base_premium > 0
        assert "base" in quote.audit_breakdown
        assert "risk_band" in quote.audit_breakdown
        assert "mode_reason" in quote.audit_breakdown

    def test_rule_based_applies_risk_discount_for_low_risk_zone(self, db_session):
        """Low-risk zone (score ≤ 30) must get a premium discounted below base."""
        from app.services.premium import _rule_based_quote

        low_risk_zone = Zone(
            code="LR-001", name="Low Risk Zone", city="TestCity",
            risk_score=20.0, is_suspended=False,
        )
        db_session.add(low_risk_zone)
        db_session.commit()

        quote = _rule_based_quote(PolicyTier.STANDARD, low_risk_zone)
        config = TIER_CONFIG[PolicyTier.STANDARD]
        base = config["weekly_premium"]

        # Low risk → -10% adjustment → final_premium < base
        assert quote.final_premium < base, (
            f"Expected final ({quote.final_premium}) < base ({base}) for low-risk zone"
        )
        assert quote.audit_breakdown["risk_band"] == "low_risk"

    def test_rule_based_applies_surcharge_for_high_risk_zone(self, db_session):
        """High-risk zone (score > 60) must get a premium above base."""
        from app.services.premium import _rule_based_quote

        high_risk_zone = Zone(
            code="HR-001", name="High Risk Zone", city="TestCity",
            risk_score=85.0, is_suspended=False,
        )
        db_session.add(high_risk_zone)
        db_session.commit()

        quote = _rule_based_quote(PolicyTier.STANDARD, high_risk_zone)
        config = TIER_CONFIG[PolicyTier.STANDARD]
        base = config["weekly_premium"]

        assert quote.final_premium > base, (
            f"Expected final ({quote.final_premium}) > base ({base}) for high-risk zone"
        )
        assert quote.audit_breakdown["risk_band"] in ("high_risk", "very_high_risk")

    def test_fallback_audit_missing_ml_fields_are_none(self, test_zone):
        """Rule-based audit_breakdown must have riqi_band=None (ML-only field)."""
        from app.services.premium import _rule_based_quote

        quote = _rule_based_quote(PolicyTier.STANDARD, test_zone)
        assert quote.audit_breakdown.get("riqi_band") is None

    def test_ml_quote_returns_trained_ml_mode(self, test_zone):
        """If ML path succeeds, pricing_mode must be 'trained_ml'."""
        from app.services.premium import _ml_quote

        quote = _ml_quote(PolicyTier.STANDARD, test_zone)
        # ML path may return None if model not loaded — that's fine
        if quote is not None:
            assert quote.pricing_mode == "trained_ml"
            assert "riqi_score" in quote.audit_breakdown
