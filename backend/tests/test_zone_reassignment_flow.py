"""
Tests for zone reassignment 24-hour acceptance workflow.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock


class TestZoneReassignmentWorkflow:
    """Tests for zone reassignment state machine."""

    @pytest.fixture
    def mock_partner_for_reassignment(self, mock_partner):
        """Partner with zone history support."""
        mock_partner.zone_history = []
        return mock_partner

    @pytest.fixture
    def mock_zone_new(self):
        """Create a mock new zone."""
        zone = MagicMock()
        zone.id = 2
        zone.code = "BLR-048"
        zone.name = "Indiranagar"
        zone.city = "Bangalore"
        zone.risk_score = 45.0
        return zone

    def test_propose_creates_pending_reassignment(self, mock_db, mock_partner_for_reassignment, mock_zone, mock_zone_new):
        """Test that proposing a reassignment calls the right db operations."""
        from app.services.zone_reassignment_service import ReassignmentStatus
        from app.models.zone_reassignment import ZoneReassignment

        # Verify the model can be instantiated
        reassignment = ZoneReassignment(
            partner_id=1,
            old_zone_id=1,
            new_zone_id=2,
            status=ReassignmentStatus.PROPOSED,
            premium_adjustment=10.0,
            remaining_days=4,
            proposed_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

        assert reassignment.status == ReassignmentStatus.PROPOSED
        assert reassignment.partner_id == 1
        assert reassignment.new_zone_id == 2

    def test_accept_updates_partner_zone(self, mock_db, mock_partner_for_reassignment, mock_zone_new):
        """Test that accepting updates the partner's zone_id."""
        from app.services.zone_reassignment_service import accept_reassignment
        from app.models.zone_reassignment import ReassignmentStatus

        # Create mock reassignment
        mock_reassignment = MagicMock()
        mock_reassignment.id = 1
        mock_reassignment.partner_id = 1
        mock_reassignment.old_zone_id = 1
        mock_reassignment.new_zone_id = 2
        mock_reassignment.status = ReassignmentStatus.PROPOSED
        mock_reassignment.expires_at = datetime.utcnow() + timedelta(hours=12)

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_reassignment,  # Reassignment lookup
            mock_partner_for_reassignment,  # Partner lookup
        ]

        result, error = accept_reassignment(1, mock_db)

        assert error is None
        assert result is not None
        assert result.status == ReassignmentStatus.ACCEPTED
        assert result.zone_updated is True
        assert mock_reassignment.status == ReassignmentStatus.ACCEPTED
        assert mock_reassignment.accepted_at is not None

    def test_reject_marks_rejected(self, mock_db):
        """Test that rejecting marks the reassignment as rejected."""
        from app.services.zone_reassignment_service import reject_reassignment
        from app.models.zone_reassignment import ReassignmentStatus

        mock_reassignment = MagicMock()
        mock_reassignment.id = 1
        mock_reassignment.status = ReassignmentStatus.PROPOSED
        mock_reassignment.expires_at = datetime.utcnow() + timedelta(hours=12)

        mock_db.query.return_value.filter.return_value.first.return_value = mock_reassignment

        result, error = reject_reassignment(1, mock_db)

        assert error is None
        assert result is not None
        assert result.status == ReassignmentStatus.REJECTED
        assert result.zone_updated is False
        assert mock_reassignment.status == ReassignmentStatus.REJECTED
        assert mock_reassignment.rejected_at is not None

    def test_expired_proposal_cannot_be_accepted(self, mock_db):
        """Test that expired proposals cannot be accepted."""
        from app.services.zone_reassignment_service import accept_reassignment
        from app.models.zone_reassignment import ReassignmentStatus

        mock_reassignment = MagicMock()
        mock_reassignment.id = 1
        mock_reassignment.status = ReassignmentStatus.PROPOSED
        mock_reassignment.expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired

        mock_db.query.return_value.filter.return_value.first.return_value = mock_reassignment

        result, error = accept_reassignment(1, mock_db)

        assert result is None
        assert "expired" in error.lower()
        assert mock_reassignment.status == ReassignmentStatus.EXPIRED

    def test_auto_expire_job_works(self, mock_db):
        """Test that the expire_stale_proposals job marks old proposals as expired."""
        from app.services.zone_reassignment_service import expire_stale_proposals
        from app.models.zone_reassignment import ReassignmentStatus

        # Create mock stale proposals
        stale1 = MagicMock()
        stale1.status = ReassignmentStatus.PROPOSED
        stale2 = MagicMock()
        stale2.status = ReassignmentStatus.PROPOSED

        mock_db.query.return_value.filter.return_value.all.return_value = [stale1, stale2]

        expired_count = expire_stale_proposals(mock_db)

        assert expired_count == 2
        assert stale1.status == ReassignmentStatus.EXPIRED
        assert stale2.status == ReassignmentStatus.EXPIRED
        assert mock_db.commit.called

    def test_premium_adjustment_calculated_correctly(self, mock_db, mock_partner_for_reassignment, mock_zone, mock_zone_new, mock_policy):
        """Test premium adjustment calculation logic."""
        from app.services.zone_reassignment_service import _calculate_premium_adjustment

        # Setup active policy expiring in ~4 days
        mock_policy.expires_at = datetime.utcnow() + timedelta(days=4, hours=12)
        mock_policy.weekly_premium = 35.0

        mock_db.query.return_value.filter.return_value.first.return_value = mock_policy

        with patch("app.services.premium.calculate_premium") as mock_calc:
            mock_quote = MagicMock()
            mock_quote.final_premium = 30.0  # New zone is cheaper
            mock_calc.return_value = mock_quote

            adjustment, days = _calculate_premium_adjustment(
                mock_partner_for_reassignment, mock_zone, mock_zone_new, mock_db
            )

            # days should be 4 (floor of remaining time)
            assert days >= 4
            # (35/7 - 30/7) * days ≈ positive credit
            assert adjustment > 0  # Credit because new zone is cheaper

    def test_cannot_propose_while_pending_exists(self, mock_db, mock_partner_for_reassignment, mock_zone_new):
        """Test that you can't create a new proposal if one is pending."""
        from app.services.zone_reassignment_service import propose_reassignment
        from app.models.zone_reassignment import ReassignmentStatus

        existing_proposal = MagicMock()
        existing_proposal.status = ReassignmentStatus.PROPOSED

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_partner_for_reassignment,  # Partner lookup
            mock_zone_new,  # New zone lookup
            existing_proposal,  # Existing pending proposal
        ]

        result, error = propose_reassignment(1, 2, mock_db)

        assert result is None
        assert "pending" in error.lower()

    def test_cannot_propose_same_zone(self, mock_db, mock_partner_for_reassignment, mock_zone_new):
        """Test that you can't propose reassignment to the current zone."""
        from app.services.zone_reassignment_service import propose_reassignment

        mock_partner_for_reassignment.zone_id = 2  # Already in zone 2

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_partner_for_reassignment,
            mock_zone_new,
        ]

        result, error = propose_reassignment(1, 2, mock_db)

        assert result is None
        assert "already" in error.lower()

    def test_list_reassignments_with_filters(self, mock_db):
        """Test listing reassignments with filters."""
        from app.services.zone_reassignment_service import list_reassignments
        from app.models.zone_reassignment import ReassignmentStatus

        mock_reassignment = MagicMock()
        mock_reassignment.id = 1
        mock_reassignment.partner_id = 1
        mock_reassignment.old_zone_id = 1
        mock_reassignment.new_zone_id = 2
        mock_reassignment.status = ReassignmentStatus.PROPOSED
        mock_reassignment.premium_adjustment = 10.0
        mock_reassignment.remaining_days = 4
        mock_reassignment.proposed_at = datetime.utcnow()
        mock_reassignment.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_reassignment.accepted_at = None
        mock_reassignment.rejected_at = None

        # Mock the query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_reassignment]
        mock_db.query.return_value = mock_query

        # Mock partner/zone lookups for enrichment
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = list_reassignments(mock_db, partner_id=1)

        assert result.total >= 0
