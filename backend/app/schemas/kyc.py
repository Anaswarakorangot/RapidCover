
from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum


class KYCStatus(str, Enum):
    pending  = "pending"
    verified = "verified"
    failed   = "failed"
    skipped  = "skipped"


class KYCSchema(BaseModel):
    aadhaar_number: Optional[str] = None
    pan_number:     Optional[str] = None
    kyc_status:     KYCStatus = KYCStatus.skipped

    @validator("aadhaar_number")
    def validate_aadhaar(cls, v):
        if v is None:
            return v
        if v.startswith("UID-"):
            return v
        digits = v.replace(" ", "")
        if not digits.isdigit() or len(digits) != 12:
            raise ValueError("Aadhaar must be 12 digits")
        return digits

    @validator("pan_number")
    def validate_pan(cls, v):
        if v is None:
            return v
        if v.startswith("PAN-"):
            return v
        import re
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v.strip().upper()):
            raise ValueError("Invalid PAN format (e.g. ABCDE1234F)")
        return v.strip().upper()

    class Config:
        use_enum_values = True