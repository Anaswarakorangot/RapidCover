"""
Push notification subscription API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_partner
from app.models.partner import Partner
from app.models.push_subscription import PushSubscription
from app.schemas.notification import (
    PushSubscriptionCreate,
    PushSubscriptionResponse,
    NotificationStatusResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/subscribe", response_model=PushSubscriptionResponse)
def subscribe_to_push(
    subscription: PushSubscriptionCreate,
    current_partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Subscribe to push notifications.

    If the endpoint already exists, reactivates the subscription.
    """
    # Check for existing subscription with this endpoint
    existing = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == subscription.endpoint)
        .first()
    )

    if existing:
        # Update existing subscription
        existing.partner_id = current_partner.id
        existing.p256dh_key = subscription.p256dh_key
        existing.auth_key = subscription.auth_key
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    # Create new subscription
    new_subscription = PushSubscription(
        partner_id=current_partner.id,
        endpoint=subscription.endpoint,
        p256dh_key=subscription.p256dh_key,
        auth_key=subscription.auth_key,
        is_active=True,
    )
    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)

    return new_subscription


@router.post("/unsubscribe")
def unsubscribe_from_push(
    current_partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Unsubscribe from push notifications.

    Deactivates all subscriptions for the current partner.
    """
    subscriptions = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.partner_id == current_partner.id,
            PushSubscription.is_active == True,
        )
        .all()
    )

    for sub in subscriptions:
        sub.is_active = False

    db.commit()

    return {"message": "Unsubscribed successfully", "count": len(subscriptions)}


@router.get("/status", response_model=NotificationStatusResponse)
def get_notification_status(
    current_partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Get push notification subscription status for current partner.
    """
    count = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.partner_id == current_partner.id,
            PushSubscription.is_active == True,
        )
        .count()
    )

    return NotificationStatusResponse(
        is_subscribed=count > 0,
        subscription_count=count,
    )
