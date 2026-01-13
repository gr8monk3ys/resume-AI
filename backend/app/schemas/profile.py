"""
Profile schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class ProfileCreate(BaseModel):
    """Schema for creating a profile."""

    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Schema for updating a profile."""

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class ProfileResponse(BaseModel):
    """Schema for profile response."""

    id: int
    user_id: Optional[int] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
