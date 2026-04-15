"""
Social Security Code (SS Code) Compliance Service.

Implements the Indian Social Security Code, 2020 eligibility rules for gig workers:
- Single-platform workers: ≥90 days of engagement in a financial year
- Multi-platform workers: ≥120 days of engagement in a financial year

This service checks eligibility during policy purchase/renewal flows and
prevents workers who don't meet the minimum engagement threshold from
being enrolled in the insurance scheme.

Reference: Section 2(35) of the Social Security Code, 2020
"""

import logging
from datetime import timedelta
from typing import Tuple
from sqlalchemy.orm import Session

from app.models.partner import Partner
from app.utils.time_utils import utcnow

logger = logging.getLogger("ss_code_service")

# Minimum engagement days required
SINGLE_PLATFORM_MIN_DAYS = 90
MULTI_PLATFORM_MIN_DAYS = 120

# Platform detection: partners on more than one platform count as multi-platform
# For now, we use a simple heuristic based on partner data
MULTI_PLATFORM_THRESHOLD = 2


def check_ss_code_eligibility(partner: Partner) -> Tuple[bool, str]:
    """
    Check if a partner meets SS Code eligibility for insurance enrollment.

    Rules:
    - Single-platform workers: must have ≥90 days of platform engagement
    - Multi-platform workers: must have ≥120 days of platform engagement

    Args:
        partner: The Partner object to check

    Returns:
        (eligible, reason) tuple:
        - (True, "SS Code eligibility met: X days of engagement")
        - (False, "Ineligible: only X/Y days of required platform engagement")
    """
    engagement_days = partner.platform_engagement_days or 0

    # Determine threshold based on platform type
    # Simple heuristic: partner.platform is a single enum value,
    # so all current partners are single-platform
    min_days = SINGLE_PLATFORM_MIN_DAYS
    platform_type = "single-platform"

    if engagement_days >= min_days:
        return (
            True,
            f"SS Code eligibility met: {engagement_days} days of {platform_type} engagement "
            f"(minimum: {min_days} days)",
        )

    return (
        False,
        f"Ineligible under Social Security Code: {engagement_days}/{min_days} days of "
        f"required {platform_type} engagement. Workers must complete at least "
        f"{min_days} days of platform work before enrolling in insurance coverage.",
    )


def update_engagement_days(partner: Partner, db: Session) -> int:
    """
    Recalculate and update the partner's engagement days.

    In a production system, this would query the platform API for actual
    delivery/work history. For now, it uses a time-based heuristic from
    the engagement_start_date field.

    Args:
        partner: The Partner to update
        db: Database session

    Returns:
        Updated engagement days count
    """
    if not partner.engagement_start_date:
        # Default: use created_at as engagement start
        partner.engagement_start_date = partner.created_at
        if not partner.engagement_start_date:
            partner.platform_engagement_days = 0
            partner.ss_code_eligible = False
            db.commit()
            return 0

    # Calculate days since engagement start
    now = utcnow()
    start = partner.engagement_start_date
    # Handle timezone comparison
    if start.tzinfo is None:
        from datetime import timezone
        start = start.replace(tzinfo=timezone.utc)

    days_since_start = (now - start).days

    # In production, this would be actual working days from platform API.
    # For now, we assume ~70% of calendar days are working days (conservative).
    estimated_engagement_days = max(0, int(days_since_start * 0.7))

    partner.platform_engagement_days = estimated_engagement_days

    # Update cached eligibility
    eligible, _ = check_ss_code_eligibility(partner)
    partner.ss_code_eligible = eligible

    db.commit()

    logger.info(
        f"[ss_code] Partner {partner.id}: {estimated_engagement_days} engagement days "
        f"(eligible={eligible})"
    )

    return estimated_engagement_days
