from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.partner import Platform, Language


class PartnerCreate(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$", description="Phone number")
    name: str = Field(..., min_length=2, max_length=100)
    platform: Platform
    partner_id: Optional[str] = None
    zone_id: Optional[int] = None
    language_pref: Language = Language.ENGLISH


class PartnerLogin(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")


class OTPVerify(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    otp: str = Field(..., min_length=6, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PartnerResponse(BaseModel):
    id: int
    phone: str
    name: str
    platform: Platform
    partner_id: Optional[str] = None
    zone_id: Optional[int] = None
    language_pref: Language
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PartnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    zone_id: Optional[int] = None
    language_pref: Optional[Language] = None
