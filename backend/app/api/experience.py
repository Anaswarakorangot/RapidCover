"""
experience.py - Partner Experience State API router.
Person 1 owns this file. Do NOT edit if you are Person 2, 3, or 4.
Per No-Conflict Rules, Section 5.

Mount in router.py:
    from app.api.experience import router as experience_router
    api_router.include_router(experience_router)

Endpoints:
  GET /partners/me/experience-state  - Full dashboard state in one call
  GET /partners/me/premium-breakdown - Itemised premium factors
  GET /partners/me/eligibility       - Tier lock/unlock based on activity
  GET /partners/me/zone-history      - Real zone reassignment history
  GET /partners/me/renewal-preview   - Simplified renewal quote for profile page
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStatus
from app.models.zone import Zone
from app.models.trigger_event import TriggerEvent
from app.services.auth import get_current_partner
from app.services.premium_service import (
    get_riqi_score,
    get_riqi_band,
    RIQI_PREMIUM_ADJUSTMENT,
    TIER_CONFIG as SVC_TIER_CONFIG,
    MIN_ACTIVE_DAYS_TO_BUY,
    AUTO_DOWNGRADE_DAYS,
)

router = APIRouter(prefix="/partners", tags=["experience"])


# ---------------------------------------------------------------------------
# Internal helpers  (private – not endpoints)
# ---------------------------------------------------------------------------

def _get_partner_city(partner: Partner, db: Session) -> str:
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
        if zone and zone.city:
            return zone.city.lower()
    return "bangalore"


def _count_active_days_last_30(partner: Partner, db: Session) -> int:
    """
    Count distinct calendar days partner had at least one paid/approved claim
    in the last 30 days.  Falls back to policy-days if no claims yet.
    """
    since = datetime.utcnow() - timedelta(days=30)

    claim_days = (
        db.query(func.date(Claim.created_at))
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id == partner.id,
            Claim.created_at >= since,
            Claim.status.in_([ClaimStatus.APPROVED, ClaimStatus.PAID]),
        )
        .distinct()
        .count()
    )
    if claim_days > 0:
        return min(claim_days, 30)

    # Fallback – each policy ≈ 7 active days
    policy_count = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.starts_at >= since,
        )
        .count()
    )
    return min(policy_count * 7, 30)


def _loyalty_weeks(partner: Partner, db: Session) -> int:
    """Count consecutive policy weeks with no gap > 48 hours."""
    policies = (
        db.query(Policy)
        .filter(Policy.partner_id == partner.id)
        .order_by(Policy.expires_at.desc())
        .all()
    )
    if not policies:
        return 0
    weeks = 0
    prev_start = None
    for p in policies:
        if prev_start is None:
            weeks = 1
            prev_start = p.starts_at
            continue
        gap_hours = (prev_start - p.expires_at).total_seconds() / 3600
        if gap_hours <= 48:
            weeks += 1
            prev_start = p.starts_at
        else:
            break
    return weeks


def _get_latest_payout(partner: Partner, db: Session) -> Optional[dict]:
    claim = (
        db.query(Claim)
        .join(Policy, Claim.policy_id == Policy.id)
        .filter(
            Policy.partner_id == partner.id,
            Claim.status == ClaimStatus.PAID,
        )
        .order_by(Claim.paid_at.desc())
        .first()
    )
    if not claim:
        return None
    return {
        "claim_id": claim.id,
        "status": "paid",
        "amount": claim.amount,
        "upi_ref": claim.upi_ref or "",
        "paid_at": claim.paid_at.isoformat() if claim.paid_at else None,
    }


def _get_active_zone_alert(partner: Partner, db: Session) -> Optional[dict]:
    """Return most recent trigger fired in partner's zone within the last 6 hours."""
    if not partner.zone_id:
        return None
    since = datetime.utcnow() - timedelta(hours=6)
    trigger = (
        db.query(TriggerEvent)
        .filter(
            TriggerEvent.zone_id == partner.zone_id,
            TriggerEvent.started_at >= since,
        )
        .order_by(TriggerEvent.started_at.desc())
        .first()
    )
    if not trigger:
        return None

    severity_label = {1: "low", 2: "low", 3: "medium", 4: "high", 5: "critical"}.get(
        trigger.severity, "medium"
    )
    type_label = (
        trigger.trigger_type.value
        if hasattr(trigger.trigger_type, "value")
        else str(trigger.trigger_type)
    )
    messages = {
        "rain":     "Heavy rain alert in your zone. Disruption payouts active.",
        "heat":     "Extreme heat warning. Stay hydrated. Payout active.",
        "aqi":      "High AQI detected. Health advisory in effect.",
        "shutdown": "Civic shutdown in your area. Payout processing.",
        "closure":  "Store closure detected. Coverage active.",
    }
    return {
        "type":       type_label,
        "message":    messages.get(type_label, f"{type_label.title()} event active in your zone."),
        "severity":   severity_label,
        "trigger_id": trigger.id,
        "started_at": trigger.started_at.isoformat() if trigger.started_at else None,
    }


def _get_zone_reassignment_card(partner: Partner, db: Session) -> Optional[dict]:
    """
    Return the most recent reassignment card if it happened in the last 24 hours.
    Returns None if no recent reassignment.
    """
    history = partner.zone_history or []
    if not history:
        return None
    latest = history[-1]
    effective_at_str = latest.get("effective_at")
    if not effective_at_str:
        return None
    try:
        effective_at = datetime.fromisoformat(effective_at_str)
    except ValueError:
        return None
    if datetime.utcnow() - effective_at > timedelta(hours=24):
        return None

    old_zone_id  = latest.get("old_zone_id")
    new_zone_id  = latest.get("new_zone_id")
    old_zone     = db.query(Zone).filter(Zone.id == old_zone_id).first() if old_zone_id else None
    new_zone     = db.query(Zone).filter(Zone.id == new_zone_id).first() if new_zone_id else None

    return {
        "old_zone":       old_zone.name if old_zone else f"Zone #{old_zone_id}",
        "new_zone":       new_zone.name if new_zone else f"Zone #{new_zone_id}",
        "old_zone_code":  old_zone.code if old_zone else None,
        "new_zone_code":  new_zone.code if new_zone else None,
        "premium_delta":  round(latest.get("premium_adjustment", 0), 2),
        "hours_left":     latest.get("days_remaining", 0) * 24,
        "effective_at":   effective_at_str,
    }


def _build_premium_breakdown(partner: Partner, db: Session) -> dict:
    """Compute itemised premium breakdown from real partner data."""
    city       = _get_partner_city(partner, db)
    riqi       = get_riqi_score(city, partner.zone_id)
    band       = get_riqi_band(riqi)
    riqi_adj   = RIQI_PREMIUM_ADJUSTMENT[band]
    loyalty_wks = _loyalty_weeks(partner, db)
    # 1% discount per loyalty week, cap at 10%
    loyalty_discount = round(max(0.0, 1.0 - (loyalty_wks * 0.01)), 3)

    # Get tier from active policy; default to standard
    active_policy = (
        db.query(Policy)
        .filter(Policy.partner_id == partner.id, Policy.is_active == True)
        .order_by(Policy.expires_at.desc())
        .first()
    )
    tier = (
        active_policy.tier.value
        if active_policy and hasattr(active_policy.tier, "value")
        else (active_policy.tier if active_policy else "standard")
    )
    base = SVC_TIER_CONFIG.get(tier, SVC_TIER_CONFIG["standard"])["weekly_premium"]

    # Seasonal index: monsoon Jun–Sep = 1.20, else 1.00
    month          = datetime.utcnow().month
    seasonal_index = 1.20 if month in (6, 7, 8, 9) else 1.00

    # Zone risk factor from Zone.risk_score (0–100, centre at 50)
    zone_risk_factor = 1.0
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()
        if zone and zone.risk_score is not None:
            zone_risk_factor = round(1.0 + (zone.risk_score - 50) / 200, 2)

    total = round(base * zone_risk_factor * seasonal_index * riqi_adj * loyalty_discount, 2)

    return {
        "tier":             tier,
        "base":             base,
        "zone_risk":        zone_risk_factor,
        "seasonal_index":   seasonal_index,
        "riqi_adjustment":  riqi_adj,
        "activity_factor":  1.0,
        "loyalty_discount": loyalty_discount,
        "total":            total,
        "city":             city,
        "riqi_band":        band,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/me/experience-state", summary="Full dashboard state for partner app")
def get_experience_state(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Single endpoint consumed by Dashboard.jsx on load and polled every 5 s during drills.

    All fields are null-safe:
    - zone_alert is None  → do NOT show alert card
    - zone_reassignment is None → do NOT show reassignment card
    - latest_payout.status == "paid" → show payout banner near top of dashboard
    """
    zone_alert       = _get_active_zone_alert(partner, db)
    zone_reassignment = _get_zone_reassignment_card(partner, db)
    loyalty_wks      = _loyalty_weeks(partner, db)
    breakdown        = _build_premium_breakdown(partner, db)
    latest_payout    = _get_latest_payout(partner, db)

    return {
        "zone_alert":        zone_alert,
        "zone_reassignment": zone_reassignment,
        "loyalty": {
            "streak_weeks":     loyalty_wks,
            "discount_unlocked": loyalty_wks >= 4,
            "next_milestone":   max(4, ((loyalty_wks // 4) + 1) * 4),
            "discount_pct":     min(loyalty_wks, 10),
        },
        "premium_breakdown": breakdown,
        "latest_payout":     latest_payout,
        "fetched_at":        datetime.utcnow().isoformat(),
    }


@router.get("/me/premium-breakdown", summary="Itemised weekly premium for authenticated partner")
def get_premium_breakdown(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Returns full itemised premium breakdown using real partner zone, tier,
    current month, loyalty, and activity.
    Replaces all TIER_PRICES fallback math in UI.
    """
    return _build_premium_breakdown(partner, db)


@router.get("/me/eligibility", summary="Tier lock/unlock based on backend-calculated activity")
def get_eligibility(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Returns which tiers the partner may purchase.
    Frontend must use allowed_tiers / blocked_tiers / reasons directly —
    no local eligibility logic allowed.
    """
    active_days = _count_active_days_last_30(partner, db)
    loyalty_wks = _loyalty_weeks(partner, db)

    if active_days < MIN_ACTIVE_DAYS_TO_BUY:
        allowed_tiers = []
        blocked_tiers = ["flex", "standard", "pro"]
        reasons = {
            t: f"Need {MIN_ACTIVE_DAYS_TO_BUY} active days in last 30. You have {active_days}."
            for t in blocked_tiers
        }
    elif active_days < AUTO_DOWNGRADE_DAYS:
        allowed_tiers = ["flex"]
        blocked_tiers = ["standard", "pro"]
        reasons = {
            t: f"Need {AUTO_DOWNGRADE_DAYS}+ active days for {t}. You have {active_days}."
            for t in blocked_tiers
        }
    else:
        allowed_tiers = ["flex", "standard", "pro"]
        blocked_tiers = []
        reasons = {}

    return {
        "active_days_last_30": active_days,
        "loyalty_weeks":       loyalty_wks,
        "allowed_tiers":       allowed_tiers,
        "blocked_tiers":       blocked_tiers,
        "reasons":             reasons,
        "gate_blocked":        active_days < MIN_ACTIVE_DAYS_TO_BUY,
    }


@router.get("/me/zone-history", summary="Real zone reassignment history for profile page")
def get_zone_history(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Returns actual reassignment history from partner.zone_history.
    Each entry is enriched with zone name/code/city from the DB.
    Returns empty list (not an error) when no history exists.
    """
    raw = partner.zone_history or []
    enriched = []
    for entry in raw:
        old_zone_id = entry.get("old_zone_id")
        new_zone_id = entry.get("new_zone_id")
        old_zone    = db.query(Zone).filter(Zone.id == old_zone_id).first() if old_zone_id else None
        new_zone    = db.query(Zone).filter(Zone.id == new_zone_id).first() if new_zone_id else None
        enriched.append({
            "old_zone_id":          old_zone_id,
            "old_zone_name":        old_zone.name if old_zone else f"Zone #{old_zone_id}",
            "old_zone_code":        old_zone.code if old_zone else None,
            "old_zone_city":        old_zone.city if old_zone else None,
            "new_zone_id":          new_zone_id,
            "new_zone_name":        new_zone.name if new_zone else f"Zone #{new_zone_id}",
            "new_zone_code":        new_zone.code if new_zone else None,
            "new_zone_city":        new_zone.city if new_zone else None,
            "effective_at":         entry.get("effective_at"),
            "premium_adjustment":   entry.get("premium_adjustment", 0),
            "new_weekly_premium":   entry.get("new_weekly_premium", 0),
            "days_remaining":       entry.get("days_remaining", 0),
            "policy_id":            entry.get("policy_id"),
        })
    return {
        "history":     list(reversed(enriched)),   # most recent first
        "total":       len(enriched),
        "has_history": len(enriched) > 0,
    }


@router.get(
    "/me/reassignments",
    summary="List partner's zone reassignment proposals",
)
def get_my_reassignments(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Return all zone reassignment proposals for the authenticated partner,
    most-recent first.  Consumed by Dashboard.jsx to show the accept/reject card.

    Response shape:
    {
      reassignments: [ ZoneReassignmentResponse, ... ],
      total: int,
      pending_count: int,
    }
    """
    from app.services.zone_reassignment_service import list_reassignments
    from app.models.zone_reassignment import ReassignmentStatus

    return list_reassignments(db, partner_id=partner.id)


@router.post(
    "/me/reassignments/{reassignment_id}/accept",
    summary="Accept a pending zone reassignment proposal",
)
def accept_my_reassignment(
    reassignment_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Accept a proposed zone reassignment.

    - Updates partner.zone_id to the new zone
    - Appends an entry to partner.zone_history
    - Returns the updated reassignment or a 4xx error
    """
    from fastapi import HTTPException, status as http_status
    from app.services.zone_reassignment_service import (
        accept_reassignment,
        get_reassignment,
    )

    # Ownership guard
    existing = get_reassignment(reassignment_id, db)
    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Reassignment not found",
        )
    if existing.partner_id != partner.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Not your reassignment",
        )

    result, error = accept_reassignment(reassignment_id, db)
    if not result:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=error or "Could not accept reassignment",
        )
    return result


@router.post(
    "/me/reassignments/{reassignment_id}/reject",
    summary="Reject a pending zone reassignment proposal",
)
def reject_my_reassignment(
    reassignment_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Reject a proposed zone reassignment.

    - Partner stays in current zone
    - Proposal status → rejected
    """
    from fastapi import HTTPException, status as http_status
    from app.services.zone_reassignment_service import (
        reject_reassignment,
        get_reassignment,
    )

    existing = get_reassignment(reassignment_id, db)
    if not existing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Reassignment not found",
        )
    if existing.partner_id != partner.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Not your reassignment",
        )

    result, error = reject_reassignment(reassignment_id, db)
    if not result:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=error or "Could not reject reassignment",
        )
    return result


@router.get("/me/renewal-preview", summary="Simplified renewal quote for profile page")
def get_renewal_preview(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Simplified renewal quote for profile page.
    Replaces hardcoded renewal premium breakdown in Profile.jsx.
    Same structure as the full renewal-quote flow, minus partner decision fields.
    """
    policy = (
        db.query(Policy)
        .filter(Policy.partner_id == partner.id)
        .order_by(Policy.expires_at.desc())
        .first()
    )
    if not policy:
        return {
            "has_policy":        False,
            "renewal_available": False,
            "message":           "No policy found. Purchase a plan to get started.",
        }

    loyalty_wks          = _loyalty_weeks(partner, db)
    loyalty_discount_pct = min(loyalty_wks, 10)
    breakdown            = _build_premium_breakdown(partner, db)
    tier                 = (
        policy.tier.value if hasattr(policy.tier, "value") else str(policy.tier)
    )
    base_premium         = SVC_TIER_CONFIG.get(tier, SVC_TIER_CONFIG["standard"])["weekly_premium"]
    loyalty_discount_amt = round(base_premium * loyalty_discount_pct / 100, 2)
    renewal_premium      = max(round(breakdown["total"] - loyalty_discount_amt, 2), 1.0)

    return {
        "has_policy":              True,
        "renewal_available":       True,
        "current_tier":            tier,
        "current_premium":         policy.weekly_premium,
        "renewal_premium":         renewal_premium,
        "loyalty_weeks":           loyalty_wks,
        "loyalty_discount_pct":    loyalty_discount_pct,
        "loyalty_discount_amount": loyalty_discount_amt,
        "breakdown":               breakdown,
        "expires_at":              policy.expires_at.isoformat() if policy.expires_at else None,
        "auto_renew":              policy.auto_renew,
    }