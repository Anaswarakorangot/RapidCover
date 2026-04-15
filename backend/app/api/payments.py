"""
Stripe payment integration for policy premiums.

Uses Stripe TEST MODE - no real money is charged.

Endpoints:
    POST /payments/checkout - Create Stripe checkout session
    GET /payments/success - Handle successful payment, create policy
"""

import stripe
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.time_utils import utcnow
from app.config import get_settings
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.zone import Zone
from app.services.auth import get_current_partner
from app.services.premium import calculate_premium
from app.schemas.policy import PolicyResponse

router = APIRouter(prefix="/payments", tags=["payments"])

# Stripe configuration (TEST MODE)
settings = get_settings()
stripe.api_key = settings.stripe_secret_key or "sk_test_placeholder"
FRONTEND_URL = settings.frontend_url or "http://localhost:5173"


@router.post("/checkout")
def create_checkout_session(
    tier: str = Query(..., regex="^(flex|standard|pro)$"),
    auto_renew: bool = Query(default=False),
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe checkout session for policy purchase.

    Returns a checkout URL that redirects user to Stripe's hosted payment page.
    After payment, Stripe redirects to /payments/success with session_id.
    """
    # Check for existing active policy
    existing = (
        db.query(Policy)
        .filter(
            Policy.partner_id == partner.id,
            Policy.is_active == True,
            Policy.expires_at > utcnow(),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active policy.",
        )

    # Get zone for premium calculation
    zone = None
    if partner.zone_id:
        zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

    # Calculate premium
    quote = calculate_premium(tier, zone)

    # Stripe minimum for INR is ₹50, so we need to ensure amount meets this
    # For demo purposes, we'll use the actual premium but ensure Stripe gets at least ₹50
    actual_premium = quote.final_premium
    stripe_amount = max(actual_premium, 50)  # Minimum ₹50 for Stripe

    # Create Stripe checkout session
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {
                        "name": f"RapidCover {tier.capitalize()} Plan",
                        "description": f"Weekly parametric insurance - ₹{quote.max_daily_payout}/day max payout",
                    },
                    "unit_amount": int(stripe_amount * 100),  # Stripe uses paise
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{FRONTEND_URL}/policy?payment=success&session_id={{CHECKOUT_SESSION_ID}}&tier={tier}&auto_renew={auto_renew}",
            cancel_url=f"{FRONTEND_URL}/policy?payment=cancelled",
            metadata={
                "partner_id": str(partner.id),
                "tier": tier,
                "auto_renew": str(auto_renew),
                "premium": str(actual_premium),  # Store actual premium for policy
            },
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "amount": actual_premium,
            "stripe_amount": stripe_amount,
            "tier": tier,
            "currency": "INR",
        }

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment error: {str(e)}",
        )


@router.post("/confirm")
def confirm_payment_and_create_policy(
    session_id: str = Query(...),
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Confirm Stripe payment and create the policy.

    Called by frontend after Stripe redirects back with session_id.
    Verifies payment was successful before creating policy.
    """
    import traceback
    try:
        print(f"[Stripe] Confirming session: {session_id}")
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        print(f"[Stripe] Session status: {session.payment_status}")
        print(f"[Stripe] Session type: {type(session)}")
        print(f"[Stripe] Metadata type: {type(session.metadata)}")
        print(f"[Stripe] Metadata raw: {session.metadata}")

        # Verify payment was successful
        if session.payment_status != "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment not completed",
            )

        # Verify this session belongs to the current partner
        # Access Stripe metadata directly via bracket notation
        try:
            session_partner_id = session.metadata["partner_id"]
        except (KeyError, TypeError):
            session_partner_id = None

        print(f"[Stripe] Session partner_id: {session_partner_id}, Current partner: {partner.id}")

        if session_partner_id != str(partner.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Payment session does not belong to you",
            )

        # Check if policy already created for this session (idempotency)
        existing = (
            db.query(Policy)
            .filter(
                Policy.partner_id == partner.id,
                Policy.stripe_session_id == session_id,
            )
            .first()
        )

        if existing:
            return existing

        # Check for any active policy
        active = (
            db.query(Policy)
            .filter(
                Policy.partner_id == partner.id,
                Policy.is_active == True,
                Policy.expires_at > utcnow(),
            )
            .first()
        )

        if active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active policy.",
            )

        # Extract metadata using bracket notation
        try:
            tier = session.metadata["tier"]
        except (KeyError, TypeError):
            tier = "standard"

        try:
            auto_renew = session.metadata["auto_renew"].lower() == "true"
        except (KeyError, TypeError, AttributeError):
            auto_renew = False

        try:
            premium = float(session.metadata["premium"])
        except (KeyError, TypeError, ValueError):
            premium = 33.0

        # Get zone for payout calculations
        zone = None
        if partner.zone_id:
            zone = db.query(Zone).filter(Zone.id == partner.zone_id).first()

        quote = calculate_premium(tier, zone)

        # Create policy
        now = utcnow()
        policy = Policy(
            partner_id=partner.id,
            tier=tier,
            weekly_premium=premium,
            max_daily_payout=quote.max_daily_payout,
            max_days_per_week=quote.max_days_per_week,
            starts_at=now,
            expires_at=now + timedelta(days=7),
            auto_renew=auto_renew,
            stripe_session_id=session_id,
            stripe_payment_intent=session.payment_intent,
        )

        db.add(policy)
        db.commit()
        db.refresh(policy)

        print(f"[Stripe] Policy created: {policy.id}")
        return policy

    except stripe.error.StripeError as e:
        print(f"[Stripe] Stripe error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification error: {str(e)}",
        )
    except Exception as e:
        print(f"[Stripe] General error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating policy: {str(e)}",
        )
