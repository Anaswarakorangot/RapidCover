"""
Tests for RIQI (Road Infrastructure Quality Index) provenance system.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestRiqiProvenance:
    """Tests for RIQI data provenance tracking."""

    @pytest.fixture
    def mock_zone_risk_profile(self):
        """Create a mock zone risk profile."""
        profile = MagicMock()
        profile.id = 1
        profile.zone_id = 1
        profile.riqi_score = 65.0
        profile.riqi_band = "urban_fringe"
        profile.historical_suspensions = 2
        profile.closure_frequency = 0.8
        profile.weather_severity_freq = 1.2
        profile.aqi_severity_freq = 0.5
        profile.zone_density = 75.0
        profile.calculated_from = "seeded"
        profile.last_updated_at = datetime.utcnow()
        return profile

    def test_riqi_reads_from_db_first(self, mock_db, mock_zone, mock_zone_risk_profile):
        """Test that RIQI service reads from database first."""
        from app.services.riqi_service import get_riqi_for_zone

        # Mock the ensure table call
        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,  # Zone lookup
                mock_zone_risk_profile,  # Profile lookup
            ]

            result = get_riqi_for_zone(1, mock_db)

            assert result.riqi_score == 65.0
            assert result.calculated_from == "seeded"
            assert result.zone_code == mock_zone.code

    def test_riqi_falls_back_to_city_default(self, mock_db, mock_zone):
        """Test that RIQI falls back to city default when no DB profile."""
        from app.services.riqi_service import get_riqi_for_zone
        from app.services.premium_service import CITY_RIQI_SCORES

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,  # Zone lookup
                None,  # No profile in DB
            ]

            result = get_riqi_for_zone(1, mock_db)

            # Should use city default for Bangalore
            expected_score = CITY_RIQI_SCORES.get(mock_zone.city.lower(), 55.0)
            assert result.riqi_score == expected_score
            assert result.calculated_from == "fallback_city_default"

    def test_riqi_provenance_includes_source(self, mock_db, mock_zone, mock_zone_risk_profile):
        """Test that RIQI response includes calculated_from field."""
        from app.services.riqi_service import get_riqi_for_zone

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,
                mock_zone_risk_profile,
            ]

            result = get_riqi_for_zone(1, mock_db)

            assert hasattr(result, "calculated_from")
            assert result.calculated_from in ["seeded", "computed", "manual", "fallback_city_default"]

    def test_riqi_endpoint_returns_all_zones(self, mock_db, mock_zone):
        """Test that get_all_riqi_profiles returns data for all zones."""
        from app.services.riqi_service import get_all_riqi_profiles
        from app.schemas.riqi import RiqiProvenanceResponse, RiqiInputMetrics

        # Create multiple mock zones
        zone1 = MagicMock()
        zone1.id = 1
        zone1.code = "BLR-047"
        zone1.name = "Koramangala"
        zone1.city = "Bangalore"

        zone2 = MagicMock()
        zone2.id = 2
        zone2.code = "BLR-048"
        zone2.name = "Indiranagar"
        zone2.city = "Bangalore"

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            with patch("app.services.riqi_service.get_riqi_for_zone") as mock_get:
                # Return proper Pydantic models
                mock_response1 = RiqiProvenanceResponse(
                    zone_id=1,
                    zone_code="BLR-047",
                    zone_name="Koramangala",
                    city="Bangalore",
                    riqi_score=65.0,
                    riqi_band="urban_fringe",
                    payout_multiplier=1.25,
                    premium_adjustment=1.15,
                    input_metrics=RiqiInputMetrics(
                        historical_suspensions=0,
                        closure_frequency=1.0,
                        weather_severity_freq=1.0,
                        aqi_severity_freq=1.0,
                        zone_density=50.0,
                    ),
                    calculated_from="seeded",
                )

                mock_response2 = RiqiProvenanceResponse(
                    zone_id=2,
                    zone_code="BLR-048",
                    zone_name="Indiranagar",
                    city="Bangalore",
                    riqi_score=62.0,
                    riqi_band="urban_fringe",
                    payout_multiplier=1.25,
                    premium_adjustment=1.15,
                    input_metrics=RiqiInputMetrics(
                        historical_suspensions=0,
                        closure_frequency=1.0,
                        weather_severity_freq=1.0,
                        aqi_severity_freq=1.0,
                        zone_density=50.0,
                    ),
                    calculated_from="fallback_city_default",
                )

                mock_get.side_effect = [mock_response1, mock_response2]
                mock_db.query.return_value.order_by.return_value.all.return_value = [zone1, zone2]

                result = get_all_riqi_profiles(mock_db)

                assert result.total == 2
                assert len(result.zones) == 2
                assert result.data_source in ["database", "mixed"]

    def test_riqi_zone_endpoint_returns_metrics(self, mock_db, mock_zone, mock_zone_risk_profile):
        """Test that zone RIQI endpoint returns input metrics."""
        from app.services.riqi_service import get_riqi_for_zone

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,
                mock_zone_risk_profile,
            ]

            result = get_riqi_for_zone(1, mock_db)

            # Check input metrics are present
            assert hasattr(result, "input_metrics")
            metrics = result.input_metrics
            assert hasattr(metrics, "historical_suspensions")
            assert hasattr(metrics, "closure_frequency")
            assert hasattr(metrics, "weather_severity_freq")
            assert hasattr(metrics, "aqi_severity_freq")
            assert hasattr(metrics, "zone_density")

    def test_riqi_band_calculation(self):
        """Test RIQI band calculation from score."""
        from app.services.premium_service import get_riqi_band

        # urban_core: > 70
        assert get_riqi_band(75.0) == "urban_core"
        assert get_riqi_band(100.0) == "urban_core"

        # urban_fringe: 40-70
        assert get_riqi_band(70.0) == "urban_fringe"
        assert get_riqi_band(55.0) == "urban_fringe"
        assert get_riqi_band(40.0) == "urban_fringe"

        # peri_urban: < 40
        assert get_riqi_band(39.9) == "peri_urban"
        assert get_riqi_band(0.0) == "peri_urban"

    def test_riqi_payout_multipliers(self):
        """Test that RIQI bands have correct payout multipliers."""
        from app.services.premium_service import RIQI_PAYOUT_MULTIPLIER

        assert RIQI_PAYOUT_MULTIPLIER["urban_core"] == 1.00
        assert RIQI_PAYOUT_MULTIPLIER["urban_fringe"] == 1.25
        assert RIQI_PAYOUT_MULTIPLIER["peri_urban"] == 1.50

    def test_riqi_premium_adjustments(self):
        """Test that RIQI bands have correct premium adjustments."""
        from app.services.premium_service import RIQI_PREMIUM_ADJUSTMENT

        assert RIQI_PREMIUM_ADJUSTMENT["urban_core"] == 1.00
        assert RIQI_PREMIUM_ADJUSTMENT["urban_fringe"] == 1.15
        assert RIQI_PREMIUM_ADJUSTMENT["peri_urban"] == 1.30

    def test_seed_zone_risk_profiles(self, mock_db, mock_zone):
        """Test seeding zone risk profiles."""
        from app.services.riqi_service import seed_zone_risk_profiles

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.all.return_value = [mock_zone]
            mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing profile

            created = seed_zone_risk_profiles(mock_db)

            assert mock_db.add.called
            assert mock_db.commit.called

    def test_recompute_riqi_updates_profile(self, mock_db, mock_zone, mock_zone_risk_profile):
        """Test that recompute updates the profile in DB."""
        from app.services.riqi_service import recompute_riqi_for_zone

        with patch("app.services.riqi_service._ensure_zone_risk_profiles_table"):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_zone,
                mock_zone_risk_profile,
            ]

            result = recompute_riqi_for_zone("BLR-047", mock_db)

            assert result is not None
            assert result.zone_code == "BLR-047"
            assert hasattr(result, "old_riqi_score")
            assert hasattr(result, "new_riqi_score")
            assert mock_zone_risk_profile.calculated_from == "computed"
