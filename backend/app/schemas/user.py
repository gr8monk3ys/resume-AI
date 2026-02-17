"""
User schemas for Clerk-based authentication.

Clerk handles user registration, login, and password management externally.
These schemas handle webhook payloads from Clerk and local user responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive fields)."""

    id: int
    clerk_id: Optional[str] = None
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserFromClerk(BaseModel):
    """Schema representing user data received from Clerk (via JWT or webhook)."""

    clerk_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    image_url: Optional[str] = None


class ClerkWebhookEvent(BaseModel):
    """Schema for Clerk webhook event payloads."""

    type: str
    data: Dict[str, Any]
    object: str = "event"


class ClerkWebhookUserData(BaseModel):
    """Schema for the user data nested inside a Clerk webhook event."""

    id: str
    email_addresses: List[Dict[str, Any]] = Field(default_factory=list)
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None

    def get_primary_email(self) -> Optional[str]:
        """Extract the primary email address from Clerk's email_addresses array."""
        for email_entry in self.email_addresses:
            if email_entry.get("id") and email_entry.get("email_address"):
                return email_entry["email_address"]
        if self.email_addresses:
            return self.email_addresses[0].get("email_address")
        return None

    def get_full_name(self) -> Optional[str]:
        """Combine first_name and last_name into a full name."""
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) if parts else None
