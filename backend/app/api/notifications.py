"""
Push notification subscription API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_partner
from app.services.notifications import get_partner_subscriptions, send_push_notification
from app.models.partner import Partner
from app.models.push_subscription import PushSubscription
from app.schemas.notification import (
    PushSubscriptionCreate,
    PushSubscriptionDelete,
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
        target_subscription = existing
    else:
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
        target_subscription = new_subscription
    
    # Send welcome notification immediately (for both new and refreshed subscriptions)
    payload = {
        "title": "RapidCover Activated! 🛡️",
        "body": "Push notifications enabled. You'll be notified of payouts and claim updates.",
        "url": "/profile",
        "tag": "welcome-notification",
        "type": "welcome",
        "icon": "/icon-192.png",
    }
    send_push_notification(target_subscription, payload)

    return target_subscription


@router.post("/unsubscribe")
def unsubscribe_from_push(
    payload: PushSubscriptionDelete | None = None,
    current_partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Unsubscribe from push notifications.

    Deactivates the current endpoint if provided, otherwise all subscriptions
    for the current partner.
    """
    query = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.partner_id == current_partner.id,
            PushSubscription.is_active == True,
        )
    )

    if payload and payload.endpoint:
        query = query.filter(PushSubscription.endpoint == payload.endpoint)

    subscriptions = query.all()

    for sub in subscriptions:
        sub.is_active = False

    db.commit()

    return {"message": "Unsubscribed successfully", "count": len(subscriptions)}


@router.get("/status", response_model=NotificationStatusResponse)
def get_notification_status(
    endpoint: str | None = None,
    current_partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Get push notification subscription status for current partner.

    If an endpoint is provided, status is scoped to the current device/browser
    subscription. Otherwise, status reflects whether the partner has any active
    subscriptions.
    """
    count = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.partner_id == current_partner.id,
            PushSubscription.is_active == True,
        )
        .count()
    )

    is_subscribed = count > 0

    if endpoint:
        is_subscribed = (
            db.query(PushSubscription)
            .filter(
                PushSubscription.partner_id == current_partner.id,
                PushSubscription.endpoint == endpoint,
                PushSubscription.is_active == True,
            )
            .count()
            > 0
        )

    return NotificationStatusResponse(
        is_subscribed=is_subscribed,
        subscription_count=count,
    )


@router.post("/test")
def send_test_notification(
    current_partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """
    Send a test push notification to the current partner's active subscriptions.
    """
    subscriptions = get_partner_subscriptions(current_partner.id, db)
    if not subscriptions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active push subscriptions found for this user",
        )

    payload = {
        "title": "RapidCover Test Notification",
        "body": "Push notifications are configured correctly for this device.",
        "url": "/profile",
        "tag": f"rapidcover-test-{current_partner.id}",
        "type": "test",
        "icon": "/icon-192.png",
    }

    success_count = 0
    for subscription in subscriptions:
        if send_push_notification(subscription, payload):
            success_count += 1

    db.commit()

    return {
        "message": "Test notification sent",
        "success_count": success_count,
        "subscription_count": len(subscriptions),
    }
