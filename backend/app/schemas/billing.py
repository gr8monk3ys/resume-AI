"""
Billing and subscription schemas.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session."""

    price_id: str  # Stripe Price ID (monthly or annual)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response with Stripe Checkout session URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Response with Stripe Customer Portal URL."""

    portal_url: str


class UsageInfo(BaseModel):
    """Usage information for a single feature."""

    feature: str
    used: int
    limit: Optional[int] = None  # None = unlimited
    reset_at: Optional[datetime] = None


class BillingStatusResponse(BaseModel):
    """Current subscription status and usage."""

    plan: str  # free, pro_monthly, pro_annual
    status: str  # active, past_due, canceled
    current_period_end: Optional[datetime] = None
    usage: list[UsageInfo] = []


class SubscriptionResponse(BaseModel):
    """Subscription details."""

    id: int
    user_id: int
    plan: str
    status: str
    stripe_customer_id: Optional[str] = None
    current_period_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageLimitError(BaseModel):
    """Response when a usage limit is reached."""

    error: Literal["limit_reached"]
    feature: str
    limit: int
    used: int
    reset_at: Optional[datetime] = None
    upgrade_url: str = "/pricing"
