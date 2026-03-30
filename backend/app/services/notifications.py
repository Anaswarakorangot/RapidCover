"""
Push notification service for RapidCover.

Sends Web Push notifications to partners when claims are created, approved, or paid.
"""

import json
import logging
from typing import Optional
from sqlalchemy.orm import Session

from pywebpush import webpush, WebPushException

from app.models.push_subscription import PushSubscription
from app.models.claim import Claim
from app.models.policy import Policy
from app.models.partner import Partner
from app.models.trigger_event import TriggerEvent, TriggerType
from app.config import get_settings

logger = logging.getLogger(__name__)

# Notification templates
NOTIFICATION_TEMPLATES = {
    "claim_created": {
        "title": "Claim Created - RapidCover",
        "body": "A claim of Rs. {amount} has been created for {trigger_type}.",
        "url": "/claims",
        "tag": "claim-created-{claim_id}",
    },
    "claim_approved": {
        "title": "Claim Approved! - RapidCover",
        "body": "Your claim of Rs. {amount} has been approved!",
        "url": "/claims",
        "tag": "claim-approved-{claim_id}",
    },
    "claim_paid": {
        "title": "Payment Received! - RapidCover",
        "body": "Rs. {amount} has been credited. Ref: {upi_ref}",
        "url": "/claims",
        "tag": "claim-paid-{claim_id}",
    },
    "claim_rejected": {
        "title": "Claim Update - RapidCover",
        "body": "Your claim of Rs. {amount} could not be processed.",
        "url": "/claims",
        "tag": "claim-rejected-{claim_id}",
    },
}

TRIGGER_TYPE_LABELS = {
    TriggerType.RAIN: "Heavy Rain",
    TriggerType.HEAT: "Extreme Heat",
    TriggerType.AQI: "High AQI",
    TriggerType.SHUTDOWN: "Civic Shutdown",
    TriggerType.CLOSURE: "Store Closure",
}


def get_partner_subscriptions(partner_id: int, db: Session) -> list[PushSubscription]:
    """Get all active push subscriptions for a partner."""
    return (
        db.query(PushSubscription)
        .filter(
            PushSubscription.partner_id == partner_id,
            PushSubscription.is_active == True,
        )
        .all()
    )


def send_push_notification(
    subscription: PushSubscription,
    payload: dict,
) -> bool:
    """
    Send a push notification to a single subscription.

    Returns True if successful, False otherwise.
    """
    settings = get_settings()

    if not settings.vapid_private_key or not settings.vapid_public_key:
        logger.warning("VAPID keys not configured, skipping push notification")
        return False

    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh_key,
            "auth": subscription.auth_key,
        },
    }

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_claim_email},
        )
        return True
    except WebPushException as e:
        logger.error(f"Push notification failed: {e}")
        # If subscription is expired/invalid, mark as inactive
        if e.response and e.response.status_code in [404, 410]:
            subscription.is_active = False
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending push: {e}")
        return False


def send_notification_to_partner(
    partner_id: int,
    notification_type: str,
    claim: Claim,
    db: Session,
) -> int:
    """
    Send a notification to all of a partner's subscriptions.

    Returns number of successful sends.
    """
    template = NOTIFICATION_TEMPLATES.get(notification_type)
    if not template:
        logger.error(f"Unknown notification type: {notification_type}")
        return 0

    # Get trigger info for label
    trigger = db.query(TriggerEvent).filter(TriggerEvent.id == claim.trigger_event_id).first()
    trigger_label = TRIGGER_TYPE_LABELS.get(trigger.trigger_type, "Disruption") if trigger else "Disruption"

    # Build payload
    payload = {
        "title": template["title"],
        "body": template["body"].format(
            amount=int(claim.amount),
            trigger_type=trigger_label,
            upi_ref=claim.upi_ref or "N/A",
        ),
        "url": template["url"],
        "tag": template["tag"].format(claim_id=claim.id),
        "type": notification_type,
        "claim_id": claim.id,
        "icon": "/icon-192.png",
    }

    subscriptions = get_partner_subscriptions(partner_id, db)
    success_count = 0

    for subscription in subscriptions:
        if send_push_notification(subscription, payload):
            success_count += 1

    # Commit any subscription status changes
    db.commit()

    logger.info(
        f"Sent {notification_type} notification to partner {partner_id}: "
        f"{success_count}/{len(subscriptions)} successful"
    )

    return success_count


def notify_claim_created(claim: Claim, db: Session) -> int:
    """Notify partner that a claim was created."""
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy:
        return 0
    return send_notification_to_partner(policy.partner_id, "claim_created", claim, db)


def notify_claim_approved(claim: Claim, db: Session) -> int:
    """Notify partner that a claim was approved."""
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy:
        return 0
    return send_notification_to_partner(policy.partner_id, "claim_approved", claim, db)


def notify_claim_paid(claim: Claim, db: Session) -> int:
    """Notify partner that a claim was paid."""
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy:
        return 0
    return send_notification_to_partner(policy.partner_id, "claim_paid", claim, db)


def notify_claim_rejected(claim: Claim, db: Session) -> int:
    """Notify partner that a claim was rejected."""
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    if not policy:
        return 0
    return send_notification_to_partner(policy.partner_id, "claim_rejected", claim, db)
