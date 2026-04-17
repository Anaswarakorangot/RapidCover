"""
Admin Schemas - Pydantic models for admin authentication
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class AdminRegister(BaseModel):
    """Schema for admin registration."""
    email: EmailStr
    password: str
    full_name: str


class AdminLogin(BaseModel):
    """Schema for admin login."""
    email: EmailStr
    password: str


class AdminResponse(BaseModel):
    """Schema for admin profile response."""
    id: int
    email: str
    full_name: str
    is_active: bool
    is_superadmin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminToken(BaseModel):
    """Schema for admin authentication token response."""
    access_token: str
    token_type: str = "bearer"
    admin: AdminResponse
