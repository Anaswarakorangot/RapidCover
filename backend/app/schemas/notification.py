from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh_key: str
    auth_key: str


class PushSubscriptionDelete(BaseModel):
    endpoint: Optional[str] = None


class PushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationStatusResponse(BaseModel):
    is_subscribed: bool
    subscription_count: int


class NotificationPayload(BaseModel):
    title: str
    body: str
    icon: Optional[str] = "/icon-192.png"
    url: Optional[str] = "/"
    tag: Optional[str] = "rapidcover-notification"
    type: Optional[str] = None
    claim_id: Optional[int] = None
