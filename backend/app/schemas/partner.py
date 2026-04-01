from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from app.models.partner import Platform, Language
from app.schemas.kyc import KYCSchema   

class PartnerCreate(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$", description="Phone number")
    name: str = Field(..., min_length=2, max_length=100)
    platform: Platform
    partner_id: Optional[str] = None
    zone_id: Optional[int] = None
    language_pref: Language = Language.ENGLISH
    upi_id: Optional[str] = None
    kyc:    Optional[KYCSchema] = None
    @validator("upi_id")
    def validate_upi(cls, v):
        if v is None:
            return v
        import re
        if not re.match(r"^[\w.\-]{3,}@[\w]{3,}$", v.strip()):
            raise ValueError("Invalid UPI ID format (e.g. name@okaxis)")
        return v.strip()

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
    upi_id: Optional[str] = None
    kyc:    Optional[KYCSchema] = None
    model_config = {"from_attributes": True}


class PartnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    zone_id: Optional[int] = None
    language_pref: Optional[Language] = None
    upi_id: Optional[str] = None
    kyc:    Optional[KYCSchema] = None