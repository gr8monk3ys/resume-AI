"""
User schemas for authentication.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=12)
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength with complexity requirements.

        Requirements:
        - Minimum 12 characters (enforced by Field)
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        - No common weak patterns
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError(
                'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)'
            )

        # Check for common weak patterns
        common_patterns = ["password", "123456", "qwerty", "admin", "letmein"]
        password_lower = v.lower()
        for pattern in common_patterns:
            if pattern in password_lower:
                raise ValueError(f"Password contains a common weak pattern: {pattern}")

        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response (excludes password)."""

    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data encoded in JWT token."""

    user_id: Optional[int] = None
    username: Optional[str] = None
    token_type: Optional[str] = None
    token_version: Optional[int] = None
