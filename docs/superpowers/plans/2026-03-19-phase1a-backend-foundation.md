# Phase 1A: Backend Foundation — Subscriptions, Feature Gating, Email, Stripe

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add subscription management, usage-based feature gating, email sending (Resend), and Stripe billing to the existing FastAPI backend so that free/pro tier limits can be enforced and users can upgrade.

**Architecture:** New SQLAlchemy models (Subscription, UsageRecord) + new middleware (feature_gate) + new services (billing_service, email_service) + new router (/api/billing). All behind `ENABLE_BILLING` and `ENABLE_EMAIL` feature flags that default to off.

**Tech Stack:** FastAPI, SQLAlchemy, Stripe Python SDK, Resend Python SDK, Pydantic, pytest

**Spec:** `docs/superpowers/specs/2026-03-19-phase1-resuboost-pro-design.md` (Sections 3, 4, 7)

**Depends on:** Nothing (this is the foundation)
**Blocks:** Phase 1B (Frontend Features), Phase 1C (Email Automation)

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/app/models/subscription.py` | Subscription + UsageRecord SQLAlchemy models |
| Create | `backend/app/schemas/billing.py` | Pydantic schemas for billing endpoints + UsageLimitError |
| Create | `backend/app/middleware/feature_gate.py` | `check_usage_limit` FastAPI dependency |
| Create | `backend/app/services/billing_service.py` | Stripe checkout, portal, webhook processing |
| Create | `backend/app/services/email_service.py` | Resend wrapper with inline HTML templates |
| Create | `backend/app/routers/billing.py` | `/api/billing` endpoints |
| Create | `backend/tests/test_billing.py` | Tests for billing router + webhook handling |
| Create | `backend/tests/test_feature_gate.py` | Tests for usage limit enforcement |
| Create | `backend/tests/test_email_service.py` | Tests for email service template rendering |
| Modify | `backend/app/models/user.py` | Add email_verified, email_notifications, onboarding fields |
| Modify | `backend/app/models/__init__.py` | Register Subscription, UsageRecord |
| Modify | `backend/app/config.py` | Add Stripe, Resend, feature flag settings |
| Modify | `backend/app/main.py` | Register billing router |
| Modify | `backend/app/routers/auth.py` | Add verify-email, resend-verification, onboarding endpoints |
| Modify | `backend/app/routers/ai.py` | Add feature_gate dependency |
| Modify | `backend/app/routers/job_import.py` | Add feature_gate + deduplication |
| Modify | `backend/app/routers/jobs.py` | Add active job count check |
| Modify | `backend/app/routers/resumes.py` | Add feature_gate dependency |
| Modify | `backend/app/routers/company_research.py` | Add feature_gate dependency |
| Modify | `backend/app/routers/interview_events.py` | Add feature_gate dependency |
| Modify | `backend/tests/conftest.py` | Add subscription fixtures |

---

## Task 1: Add Feature Flag + Stripe + Resend Settings to Config

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example` (if exists)

- [ ] **Step 1: Add settings to config.py**

Add these fields to the `Settings` class in `backend/app/config.py`, after the existing scheduler settings block (~line 149):

```python
    # Feature flags for Phase 1 rollout
    enable_billing: bool = False  # Stripe checkout, feature gating enforcement
    enable_email: bool = False  # All outbound email sending

    # Stripe settings
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_pro_monthly_price_id: Optional[str] = None
    stripe_pro_annual_price_id: Optional[str] = None

    # Email settings (Resend)
    resend_api_key: Optional[str] = None
    from_email: str = "ResuBoost <noreply@resuboost.com>"
    app_url: str = "http://localhost:3000"  # For email links
```

- [ ] **Step 2: Update .env.example**

Add to the project root `.env.example` file (or `backend/.env.example` if that's where it lives):

```bash
# Feature flags for Phase 1 rollout
ENABLE_BILLING=false
ENABLE_EMAIL=false

# Stripe settings (get from Stripe Dashboard → Test mode)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_MONTHLY_PRICE_ID=price_...
STRIPE_PRO_ANNUAL_PRICE_ID=price_...

# Email settings (get from Resend Dashboard)
RESEND_API_KEY=re_...
FROM_EMAIL=ResuBoost <noreply@resuboost.com>
APP_URL=http://localhost:3000
```

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `cd backend && uv run pytest tests/test_auth.py -v -x`
Expected: All tests pass (settings additions are backwards-compatible)

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add Stripe, Resend, and feature flag settings to config"
```

---

## Task 2: Add User Model Fields

**Files:**
- Modify: `backend/app/models/user.py`

- [ ] **Step 1: Add new columns to User model**

Add these columns to the `User` class in `backend/app/models/user.py`, after the `token_version` column (~line 29):

```python
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_notifications = Column(Boolean, default=True)
    email_verification_token = Column(String, nullable=True)

    # Activity tracking
    last_active_at = Column(DateTime, nullable=True)

    # Onboarding
    onboarding_completed = Column(Boolean, default=False)
    onboarding_dismissed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=0)
```

- [ ] **Step 2: Run tests to verify model change doesn't break anything**

Run: `cd backend && uv run pytest tests/test_auth.py -v -x`
Expected: All tests pass (new columns have defaults, so existing code unaffected)

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/user.py
git commit -m "feat: add email verification, onboarding, and activity tracking fields to User model"
```

---

## Task 3: Create Subscription and UsageRecord Models

**Files:**
- Create: `backend/app/models/subscription.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create subscription.py model file**

Create `backend/app/models/subscription.py`:

```python
"""
Subscription and usage tracking models for billing.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Subscription(Base):
    """User subscription for billing tier management."""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    plan = Column(String, nullable=False, default="free")  # free, pro_monthly, pro_annual
    status = Column(String, nullable=False, default="active")  # active, past_due, canceled
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", backref="subscription", uselist=False)


class UsageRecord(Base):
    """Tracks feature usage per user per period for tier limit enforcement."""

    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    feature = Column(String, nullable=False)  # ai_generation, job_import, interview_prep
    period_start = Column(Date, nullable=False)
    count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_usage_user_feature_period", "user_id", "feature", "period_start"),
    )
```

- [ ] **Step 2: Register models in __init__.py**

Add to `backend/app/models/__init__.py`:

```python
from app.models.subscription import Subscription, UsageRecord
```

And add `"Subscription"` and `"UsageRecord"` to the `__all__` list.

- [ ] **Step 3: Run tests to verify models create properly**

Run: `cd backend && uv run pytest tests/test_auth.py::TestLogin::test_login_success -v`
Expected: PASS (SQLAlchemy creates all tables including new ones in test setup)

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/subscription.py backend/app/models/__init__.py
git commit -m "feat: add Subscription and UsageRecord models"
```

---

## Task 4: Create Billing Schemas

**Files:**
- Create: `backend/app/schemas/billing.py`

- [ ] **Step 1: Create billing schemas**

Create `backend/app/schemas/billing.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/billing.py
git commit -m "feat: add billing Pydantic schemas"
```

---

## Task 5: Create Feature Gate Middleware

**Files:**
- Create: `backend/app/middleware/feature_gate.py`
- Create: `backend/tests/test_feature_gate.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_feature_gate.py`:

```python
"""
Tests for feature gating middleware.
"""

import os
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from app.middleware.feature_gate import (
    FREE_TIER_LIMITS,
    get_usage_count,
    increment_usage,
    check_usage_limit,
)
from app.models.subscription import Subscription, UsageRecord
from app.models.user import User


class TestGetUsageCount:
    """Tests for usage count retrieval."""

    def test_no_records_returns_zero(self, db: Session, test_user: User):
        """Usage count is 0 when no records exist."""
        count = get_usage_count(db, test_user.id, "ai_generation", date.today())
        assert count == 0

    def test_returns_existing_count(self, db: Session, test_user: User):
        """Returns the count from an existing usage record."""
        record = UsageRecord(
            user_id=test_user.id,
            feature="ai_generation",
            period_start=date.today(),
            count=2,
        )
        db.add(record)
        db.commit()

        count = get_usage_count(db, test_user.id, "ai_generation", date.today())
        assert count == 2

    def test_different_period_returns_zero(self, db: Session, test_user: User):
        """Usage from a different period doesn't count."""
        record = UsageRecord(
            user_id=test_user.id,
            feature="ai_generation",
            period_start=date(2025, 1, 1),
            count=5,
        )
        db.add(record)
        db.commit()

        count = get_usage_count(db, test_user.id, "ai_generation", date.today())
        assert count == 0


class TestIncrementUsage:
    """Tests for usage increment."""

    def test_creates_record_if_none_exists(self, db: Session, test_user: User):
        """Creates a new usage record when none exists for the period."""
        increment_usage(db, test_user.id, "ai_generation", date.today())
        count = get_usage_count(db, test_user.id, "ai_generation", date.today())
        assert count == 1

    def test_increments_existing_record(self, db: Session, test_user: User):
        """Increments an existing usage record."""
        record = UsageRecord(
            user_id=test_user.id,
            feature="ai_generation",
            period_start=date.today(),
            count=2,
        )
        db.add(record)
        db.commit()

        increment_usage(db, test_user.id, "ai_generation", date.today())
        count = get_usage_count(db, test_user.id, "ai_generation", date.today())
        assert count == 3


class TestFreeTierLimits:
    """Tests for free tier limit enforcement via API."""

    @pytest.mark.asyncio
    async def test_no_subscription_treated_as_free(
        self, client: AsyncClient, auth_headers: dict, test_profile
    ):
        """User with no subscription record is treated as free tier."""
        # Make AI requests until limit hit (3/day for free)
        for i in range(3):
            response = await client.post(
                "/api/ai/answer-question",
                json={
                    "resume_content": "Software Engineer with 5 years experience",
                    "question": f"Test question {i}",
                },
                headers=auth_headers,
            )
            # Should succeed (mock LLM provider)
            assert response.status_code in (200, 201), f"Request {i} failed: {response.text}"

    @pytest.mark.asyncio
    async def test_billing_disabled_no_limits(
        self, client: AsyncClient, auth_headers: dict, test_profile
    ):
        """When ENABLE_BILLING=false, no limits are enforced."""
        # With billing disabled (default in tests), all requests should succeed
        for i in range(5):
            response = await client.post(
                "/api/ai/answer-question",
                json={
                    "resume_content": "Software Engineer with 5 years experience",
                    "question": f"Test question {i}",
                },
                headers=auth_headers,
            )
            assert response.status_code in (200, 201)


class TestProTierNoLimits:
    """Tests that Pro users have no limits."""

    @pytest.mark.asyncio
    async def test_pro_user_unlimited(
        self, client: AsyncClient, auth_headers: dict, test_user: User, test_profile, db: Session
    ):
        """Pro subscription user has no usage limits."""
        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="active",
        )
        db.add(sub)
        db.commit()

        for i in range(5):
            response = await client.post(
                "/api/ai/answer-question",
                json={
                    "resume_content": "Software Engineer with 5 years experience",
                    "question": f"Test question {i}",
                },
                headers=auth_headers,
            )
            assert response.status_code in (200, 201)


class TestSubscriptionEdgeCases:
    """Tests for subscription edge cases (grace periods, cancellation)."""

    def test_canceled_before_period_end_is_pro(self, db: Session, test_user: User):
        """Canceled subscription before period_end retains pro access."""
        from datetime import datetime, timedelta, timezone
        from app.middleware.feature_gate import is_pro_user

        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="canceled",
            current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
        )
        db.add(sub)
        db.commit()
        assert is_pro_user(sub) is True

    def test_canceled_after_period_end_is_free(self, db: Session, test_user: User):
        """Canceled subscription after period_end is treated as free."""
        from datetime import datetime, timedelta, timezone
        from app.middleware.feature_gate import is_pro_user

        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="canceled",
            current_period_end=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(sub)
        db.commit()
        assert is_pro_user(sub) is False

    def test_past_due_within_grace_is_pro(self, db: Session, test_user: User):
        """Past due within 7-day grace period retains pro."""
        from datetime import datetime, timedelta, timezone
        from app.middleware.feature_gate import is_pro_user

        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="past_due",
            current_period_end=datetime.now(timezone.utc) - timedelta(days=3),
        )
        db.add(sub)
        db.commit()
        assert is_pro_user(sub) is True

    def test_past_due_beyond_grace_is_free(self, db: Session, test_user: User):
        """Past due beyond 7-day grace period is treated as free."""
        from datetime import datetime, timedelta, timezone
        from app.middleware.feature_gate import is_pro_user

        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="past_due",
            current_period_end=datetime.now(timezone.utc) - timedelta(days=10),
        )
        db.add(sub)
        db.commit()
        assert is_pro_user(sub) is False

    def test_free_plan_is_not_pro(self, db: Session, test_user: User):
        """Free plan subscription is never pro."""
        from app.middleware.feature_gate import is_pro_user

        sub = Subscription(user_id=test_user.id, plan="free", status="active")
        db.add(sub)
        db.commit()
        assert is_pro_user(sub) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_feature_gate.py -v -x`
Expected: FAIL with `ImportError: cannot import name 'check_usage_limit' from 'app.middleware.feature_gate'`

- [ ] **Step 3: Create feature_gate.py**

Create `backend/app/middleware/feature_gate.py`:

```python
"""
Feature gating middleware for free/pro tier enforcement.

When ENABLE_BILLING is False (default), no limits are enforced.
When ENABLE_BILLING is True, free tier users have usage limits.
Pro tier users have no limits.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.subscription import Subscription, UsageRecord
from app.models.user import User

logger = logging.getLogger(__name__)

# Free tier limits per feature
FREE_TIER_LIMITS = {
    "ai_generation": {"limit": 3, "period": "day"},
    "job_import": {"limit": 5, "period": "month"},
    "interview_prep": {"limit": 1, "period": "week"},
    "active_jobs": {"limit": 20, "period": "total"},
    "resume_versions": {"limit": 2, "period": "total"},
    "company_research": {"limit": 3, "period": "total"},
}


def get_period_start(period: str) -> date:
    """Get the start date of the current period."""
    today = date.today()
    if period == "day":
        return today
    elif period == "week":
        return today - timedelta(days=today.weekday())  # Monday
    elif period == "month":
        return today.replace(day=1)
    else:
        return date(2000, 1, 1)  # "total" - epoch start


def get_period_reset(period: str) -> Optional[datetime]:
    """Get when the current period resets."""
    today = date.today()
    if period == "day":
        tomorrow = today + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)
    elif period == "week":
        next_monday = today + timedelta(days=(7 - today.weekday()))
        return datetime(next_monday.year, next_monday.month, next_monday.day, tzinfo=timezone.utc)
    elif period == "month":
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        return datetime(next_month.year, next_month.month, next_month.day, tzinfo=timezone.utc)
    return None  # "total" has no reset


def get_usage_count(db: Session, user_id: int, feature: str, period_start: date) -> int:
    """Get current usage count for a feature in the given period."""
    record = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.user_id == user_id,
            UsageRecord.feature == feature,
            UsageRecord.period_start == period_start,
        )
        .first()
    )
    return record.count if record else 0


def increment_usage(db: Session, user_id: int, feature: str, period_start: date) -> int:
    """Increment usage count atomically. Creates record if needed. Returns new count."""
    from sqlalchemy.exc import IntegrityError

    record = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.user_id == user_id,
            UsageRecord.feature == feature,
            UsageRecord.period_start == period_start,
        )
        .with_for_update()
        .first()
    )
    if record:
        record.count += 1
        db.commit()
        return record.count
    else:
        record = UsageRecord(
            user_id=user_id,
            feature=feature,
            period_start=period_start,
            count=1,
        )
        db.add(record)
        try:
            db.commit()
            return 1
        except IntegrityError:
            db.rollback()
            # Another request created the record first, retry
            return increment_usage(db, user_id, feature, period_start)


def get_user_subscription(db: Session, user_id: int) -> Optional[Subscription]:
    """Get a user's subscription. Returns None if no subscription exists."""
    return db.query(Subscription).filter(Subscription.user_id == user_id).first()


def is_pro_user(subscription: Optional[Subscription]) -> bool:
    """Check if user has an active pro subscription."""
    if not subscription:
        return False
    if subscription.plan == "free":
        return False
    if subscription.status not in ("active", "canceled"):
        return False
    # Canceled users retain pro until period end
    if subscription.status == "canceled" and subscription.current_period_end:
        if subscription.current_period_end < datetime.now(timezone.utc):
            return False
    # Past due with grace period (7 days)
    if subscription.status == "past_due" and subscription.current_period_end:
        grace_end = subscription.current_period_end + timedelta(days=7)
        if datetime.now(timezone.utc) > grace_end:
            return False
        return True
    return True


def check_usage_limit(feature: str):
    """
    FastAPI dependency factory for checking usage limits.

    Usage:
        @router.post("/endpoint")
        def my_endpoint(
            _limit=Depends(check_usage_limit("ai_generation")),
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db),
        ):
    """

    def _check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        settings = get_settings()

        # If billing is disabled, no limits
        if not settings.enable_billing:
            return

        # Check subscription
        subscription = get_user_subscription(db, current_user.id)
        if is_pro_user(subscription):
            return

        # Check feature limit
        if feature not in FREE_TIER_LIMITS:
            return

        limit_config = FREE_TIER_LIMITS[feature]
        limit = limit_config["limit"]
        period = limit_config["period"]
        period_start = get_period_start(period)

        # For count-based limits (total), check current count of resources
        # These are handled differently - they check actual resource counts
        # not usage records. Skip here - handled by individual routers.
        if period == "total":
            return

        usage = get_usage_count(db, current_user.id, feature, period_start)
        if usage >= limit:
            reset_at = get_period_reset(period)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "limit_reached",
                    "feature": feature,
                    "limit": limit,
                    "used": usage,
                    "reset_at": reset_at.isoformat() if reset_at else None,
                    "upgrade_url": "/pricing",
                },
            )

        # Increment usage
        increment_usage(db, current_user.id, feature, period_start)

    return _check
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_feature_gate.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/middleware/feature_gate.py backend/tests/test_feature_gate.py
git commit -m "feat: add feature gating middleware with free tier limits"
```

---

## Task 6: Create Email Service

**Files:**
- Create: `backend/app/services/email_service.py`
- Create: `backend/tests/test_email_service.py`

- [ ] **Step 1: Install resend dependency**

Run: `cd backend && uv add resend`

- [ ] **Step 2: Write failing test**

Create `backend/tests/test_email_service.py`:

```python
"""
Tests for email service.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import EmailService


class TestEmailServiceTemplates:
    """Test email template rendering."""

    def setup_method(self):
        """Create email service with email disabled (logs only)."""
        self.service = EmailService()

    def test_welcome_email_contains_username(self):
        """Welcome email includes the user's name."""
        html = self.service.render_welcome("Jane Doe", "jane@example.com", "http://verify-link")
        assert "Jane Doe" in html
        assert "http://verify-link" in html

    def test_verification_email_contains_link(self):
        """Verification email includes the verification link."""
        html = self.service.render_verification("http://localhost:3000/verify-email?token=abc123")
        assert "verify-email?token=abc123" in html

    def test_upgrade_prompt_contains_feature(self):
        """Upgrade prompt email mentions the blocked feature."""
        html = self.service.render_upgrade_prompt("AI generations", 3)
        assert "AI generations" in html
        assert "3" in html

    def test_nudge_email_contains_company(self):
        """Nudge email includes the company name and action."""
        html = self.service.render_nudge(
            nudge_type="follow_up",
            company="Stripe",
            context="Applied 7 days ago",
            draft_content="Hi, I wanted to follow up...",
            app_url="http://localhost:3000",
        )
        assert "Stripe" in html
        assert "follow up" in html.lower()

    def test_payment_failed_email(self):
        """Payment failed email includes portal link."""
        html = self.service.render_payment_failed("http://portal-link")
        assert "http://portal-link" in html
        assert "payment" in html.lower()


class TestEmailServiceSending:
    """Test email sending logic."""

    def test_send_disabled_logs_only(self):
        """When ENABLE_EMAIL=false, emails are logged not sent."""
        service = EmailService()
        # Should not raise, just log
        result = service.send("test@example.com", "Test Subject", "<p>Test</p>")
        assert result is False  # Not actually sent

    @patch("app.services.email_service.resend")
    def test_send_enabled_calls_resend(self, mock_resend):
        """When ENABLE_EMAIL=true and API key set, calls Resend API."""
        mock_resend.Emails.send.return_value = {"id": "test-id"}
        service = EmailService(enabled=True, api_key="re_test_key", from_email="test@test.com")
        result = service.send("user@example.com", "Test", "<p>Body</p>")
        assert result is True
        mock_resend.Emails.send.assert_called_once()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_email_service.py -v -x`
Expected: FAIL with `ImportError`

- [ ] **Step 4: Create email_service.py**

Create `backend/app/services/email_service.py`:

```python
"""
Email service using Resend.

When ENABLE_EMAIL is False (default), emails are logged to console.
When ENABLE_EMAIL is True, emails are sent via Resend API.
"""

import logging
import uuid
from typing import Optional

try:
    import resend
except ImportError:
    resend = None  # type: ignore[assignment]

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Thin wrapper around Resend for sending transactional emails."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        app_url: Optional[str] = None,
    ):
        settings = get_settings()
        self.enabled = enabled if enabled is not None else settings.enable_email
        self.api_key = api_key or settings.resend_api_key
        self.from_email = from_email or settings.from_email
        self.app_url = app_url or settings.app_url

        if self.enabled and self.api_key and resend:
            resend.api_key = self.api_key

    def send(self, to: str, subject: str, html: str) -> bool:
        """Send an email. Returns True if sent, False if logged only."""
        if not self.enabled or not self.api_key or not resend:
            logger.info(f"[EMAIL-LOG] To: {to} | Subject: {subject}")
            if get_settings().debug:
                logger.debug(f"[EMAIL-HTML]\n{html}")
            return False

        try:
            resend.Emails.send(
                {
                    "from": self.from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "headers": {
                        "List-Unsubscribe": f"<{self.app_url}/api/profile/unsubscribe>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                    },
                }
            )
            logger.info(f"Email sent to {to}: {subject}")
            return True
        except Exception:
            logger.exception(f"Failed to send email to {to}: {subject}")
            return False

    def generate_verification_token(self) -> str:
        """Generate a UUID token for email verification."""
        return str(uuid.uuid4())

    # --- Template rendering methods ---

    def render_welcome(self, name: str, email: str, verify_url: str) -> str:
        """Render welcome email with verification link."""
        return f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #1a1a2e;">Welcome to ResuBoost, {name}!</h1>
            <p>You're one step closer to landing your next role.</p>
            <p>Please verify your email address to get started:</p>
            <a href="{verify_url}"
               style="display: inline-block; padding: 12px 24px; background: #6366f1;
                      color: white; text-decoration: none; border-radius: 8px;">
                Verify Email
            </a>
            <p style="color: #666; margin-top: 24px; font-size: 14px;">
                If you didn't create this account, you can ignore this email.
            </p>
        </div>
        """

    def render_verification(self, verify_url: str) -> str:
        """Render email verification reminder."""
        return f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a2e;">Verify your email</h2>
            <p>Click below to verify your email address:</p>
            <a href="{verify_url}"
               style="display: inline-block; padding: 12px 24px; background: #6366f1;
                      color: white; text-decoration: none; border-radius: 8px;">
                Verify Email
            </a>
        </div>
        """

    def render_upgrade_prompt(self, feature: str, limit: int) -> str:
        """Render upgrade prompt email when user hits a limit."""
        return f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a2e;">You've hit your limit</h2>
            <p>You've used all {limit} of your free {feature} for this period.</p>
            <p>Upgrade to ResuBoost Pro for unlimited access:</p>
            <a href="{self.app_url}/pricing"
               style="display: inline-block; padding: 12px 24px; background: #6366f1;
                      color: white; text-decoration: none; border-radius: 8px;">
                Upgrade to Pro — $15/mo
            </a>
        </div>
        """

    def render_nudge(
        self,
        nudge_type: str,
        company: str,
        context: str,
        draft_content: str,
        app_url: str,
    ) -> str:
        """Render nudge notification email."""
        type_labels = {
            "follow_up": "Time to follow up",
            "interview_prep": "Interview prep ready",
            "thank_you": "Send a thank-you note",
            "stale_application": "Application needs attention",
        }
        label = type_labels.get(nudge_type, "Action needed")
        return f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a2e;">{label}: {company}</h2>
            <p style="color: #666;">{context}</p>
            <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 16px 0;">
                <p style="white-space: pre-wrap;">{draft_content}</p>
            </div>
            <a href="{app_url}/jobs"
               style="display: inline-block; padding: 12px 24px; background: #6366f1;
                      color: white; text-decoration: none; border-radius: 8px;">
                Open in ResuBoost
            </a>
        </div>
        """

    def render_payment_failed(self, portal_url: str) -> str:
        """Render payment failed email."""
        return f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a2e;">Payment failed</h2>
            <p>We couldn't process your payment for ResuBoost Pro.</p>
            <p>Please update your payment method to keep your Pro features:</p>
            <a href="{portal_url}"
               style="display: inline-block; padding: 12px 24px; background: #6366f1;
                      color: white; text-decoration: none; border-radius: 8px;">
                Update Payment Method
            </a>
            <p style="color: #666; margin-top: 24px; font-size: 14px;">
                Your Pro features will remain active for 7 days while we retry your payment.
            </p>
        </div>
        """

    def render_weekly_digest(
        self,
        name: str,
        upcoming_interviews: list,
        overdue_followups: list,
        stats: dict,
    ) -> str:
        """Render weekly digest email."""
        interviews_html = ""
        for event in upcoming_interviews[:5]:
            interviews_html += f"<li>{event['company']} — {event['position']} on {event['date']}</li>"
        if not interviews_html:
            interviews_html = "<li>No upcoming interviews</li>"

        followups_html = ""
        for fu in overdue_followups[:5]:
            followups_html += f"<li>{fu['company']} — applied {fu['days_ago']} days ago</li>"
        if not followups_html:
            followups_html = "<li>All caught up!</li>"

        return f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #1a1a2e;">Your week ahead, {name}</h1>

            <h3>Upcoming Interviews</h3>
            <ul>{interviews_html}</ul>

            <h3>Follow-ups Needed</h3>
            <ul>{followups_html}</ul>

            <h3>Pipeline Stats</h3>
            <p>Active applications: {stats.get('active', 0)} |
               Interviews this week: {stats.get('interviews', 0)} |
               Response rate: {stats.get('response_rate', 'N/A')}</p>

            <a href="{self.app_url}"
               style="display: inline-block; padding: 12px 24px; background: #6366f1;
                      color: white; text-decoration: none; border-radius: 8px;">
                Open Dashboard
            </a>
        </div>
        """


def get_email_service() -> EmailService:
    """Get email service instance."""
    return EmailService()
```

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_email_service.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/email_service.py backend/tests/test_email_service.py backend/uv.lock backend/pyproject.toml
git commit -m "feat: add email service with Resend integration and inline templates"
```

---

## Task 7: Create Billing Service

**Files:**
- Create: `backend/app/services/billing_service.py`

- [ ] **Step 1: Install stripe dependency**

Run: `cd backend && uv add stripe`

- [ ] **Step 2: Create billing_service.py**

Create `backend/app/services/billing_service.py`:

```python
"""
Stripe billing service.

Handles checkout session creation, customer portal, and webhook processing.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[assignment]

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.subscription import Subscription
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)


class BillingService:
    """Stripe billing operations."""

    def __init__(self):
        settings = get_settings()
        self.enabled = settings.enable_billing
        if stripe and settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key

    def create_checkout_session(
        self,
        user_id: int,
        email: str,
        price_id: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> str:
        """Create a Stripe Checkout session. Returns the checkout URL."""
        if not stripe or not get_settings().stripe_secret_key:
            raise ValueError("Stripe is not configured")

        settings = get_settings()
        success = success_url or f"{settings.app_url}/settings?billing=success"
        cancel = cancel_url or f"{settings.app_url}/pricing"

        # Get or create Stripe customer
        customer_id = None
        if db:
            sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
            if sub and sub.stripe_customer_id:
                customer_id = sub.stripe_customer_id

        session_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success,
            "cancel_url": cancel,
            "client_reference_id": str(user_id),
            "metadata": {"user_id": str(user_id)},
        }

        if customer_id:
            session_params["customer"] = customer_id
        else:
            session_params["customer_email"] = email

        session = stripe.checkout.Session.create(**session_params)
        return session.url

    def create_portal_session(self, stripe_customer_id: str) -> str:
        """Create a Stripe Customer Portal session. Returns the portal URL."""
        if not stripe or not get_settings().stripe_secret_key:
            raise ValueError("Stripe is not configured")

        settings = get_settings()
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{settings.app_url}/settings",
        )
        return session.url

    def handle_webhook_event(self, payload: bytes, sig_header: str, db: Session) -> dict:
        """
        Process a Stripe webhook event.

        Verifies signature, processes event, updates subscription.
        Returns dict with event type and result.
        """
        settings = get_settings()
        if not stripe or not settings.stripe_webhook_secret:
            raise ValueError("Stripe webhook is not configured")

        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )

        event_type = event["type"]
        data = event["data"]["object"]
        result = {"event_type": event_type, "processed": False}

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data, db)
            result["processed"] = True

        elif event_type == "customer.subscription.updated":
            self._handle_subscription_updated(data, db)
            result["processed"] = True

        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(data, db)
            result["processed"] = True

        elif event_type == "invoice.payment_failed":
            self._handle_payment_failed(data, db)
            result["processed"] = True

        return result

    def _handle_checkout_completed(self, session_data: dict, db: Session):
        """Process successful checkout."""
        user_id = int(session_data.get("client_reference_id", 0) or session_data.get("metadata", {}).get("user_id", 0))
        customer_id = session_data.get("customer")
        subscription_id = session_data.get("subscription")

        if not user_id:
            logger.error("Checkout completed but no user_id found")
            return

        sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if sub:
            sub.stripe_customer_id = customer_id
            sub.stripe_subscription_id = subscription_id
            sub.plan = "pro_monthly"  # Will be updated by subscription.updated event
            sub.status = "active"
        else:
            sub = Subscription(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan="pro_monthly",
                status="active",
            )
            db.add(sub)

        db.commit()
        logger.info(f"Checkout completed for user {user_id}")

    def _handle_subscription_updated(self, subscription_data: dict, db: Session):
        """Process subscription update (plan change, renewal, etc)."""
        stripe_sub_id = subscription_data.get("id")
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub_id)
            .first()
        )
        if not sub:
            logger.warning(f"Subscription {stripe_sub_id} not found in database")
            return

        # Update plan based on price
        items = subscription_data.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id")
            settings = get_settings()
            if price_id == settings.stripe_pro_annual_price_id:
                sub.plan = "pro_annual"
            else:
                sub.plan = "pro_monthly"

        sub.status = subscription_data.get("status", sub.status)
        if sub.status == "active":
            sub.status = "active"
        elif sub.status in ("past_due", "unpaid"):
            sub.status = "past_due"

        period_end = subscription_data.get("current_period_end")
        if period_end:
            sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

        db.commit()
        logger.info(f"Subscription updated: {stripe_sub_id} -> {sub.plan}/{sub.status}")

    def _handle_subscription_deleted(self, subscription_data: dict, db: Session):
        """Process subscription cancellation."""
        stripe_sub_id = subscription_data.get("id")
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub_id)
            .first()
        )
        if not sub:
            return

        sub.plan = "free"
        sub.status = "canceled"
        db.commit()
        logger.info(f"Subscription canceled: {stripe_sub_id}")

    def _handle_payment_failed(self, invoice_data: dict, db: Session):
        """Process failed payment."""
        customer_id = invoice_data.get("customer")
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_customer_id == customer_id)
            .first()
        )
        if not sub:
            return

        sub.status = "past_due"
        db.commit()

        # Send payment failed email
        from app.models.user import User

        user = db.query(User).filter(User.id == sub.user_id).first()
        if user and user.email:
            email_service = get_email_service()
            try:
                portal_url = self.create_portal_session(sub.stripe_customer_id)
                html = email_service.render_payment_failed(portal_url)
                email_service.send(user.email, "Payment failed — update your payment method", html)
            except Exception:
                logger.exception("Failed to send payment failed email")

        logger.info(f"Payment failed for customer {customer_id}")


def get_billing_service() -> BillingService:
    """Get billing service instance."""
    return BillingService()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/billing_service.py backend/uv.lock backend/pyproject.toml
git commit -m "feat: add Stripe billing service with checkout, portal, and webhook handling"
```

---

## Task 8: Create Billing Router

**Files:**
- Create: `backend/app/routers/billing.py`
- Create: `backend/tests/test_billing.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_billing.py`:

```python
"""
Tests for billing router.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.models.user import User


class TestBillingStatus:
    """Tests for GET /api/billing/status."""

    @pytest.mark.asyncio
    async def test_status_no_subscription(
        self, client: AsyncClient, auth_headers: dict, test_profile
    ):
        """Returns free tier status when no subscription exists."""
        response = await client.get("/api/billing/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "free"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_status_with_pro_subscription(
        self, client: AsyncClient, auth_headers: dict, test_user: User, test_profile, db: Session
    ):
        """Returns pro tier status when subscription exists."""
        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="active",
            stripe_customer_id="cus_test123",
        )
        db.add(sub)
        db.commit()

        response = await client.get("/api/billing/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "pro_monthly"

    @pytest.mark.asyncio
    async def test_status_unauthorized(self, client: AsyncClient):
        """Returns 401 when not authenticated."""
        response = await client.get("/api/billing/status")
        assert response.status_code == 401


class TestCheckout:
    """Tests for POST /api/billing/checkout."""

    @pytest.mark.asyncio
    async def test_checkout_unauthorized(self, client: AsyncClient):
        """Returns 401 when not authenticated."""
        response = await client.post(
            "/api/billing/checkout",
            json={"price_id": "price_test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_checkout_stripe_not_configured(
        self, client: AsyncClient, auth_headers: dict, test_profile
    ):
        """Returns 503 when Stripe is not configured."""
        response = await client.post(
            "/api/billing/checkout",
            json={"price_id": "price_test"},
            headers=auth_headers,
        )
        # Stripe not configured in test env
        assert response.status_code == 503


class TestPortal:
    """Tests for POST /api/billing/portal."""

    @pytest.mark.asyncio
    async def test_portal_no_subscription(
        self, client: AsyncClient, auth_headers: dict, test_profile
    ):
        """Returns 404 when user has no subscription with Stripe customer."""
        response = await client.post("/api/billing/portal", headers=auth_headers)
        assert response.status_code == 404


class TestWebhook:
    """Tests for POST /api/billing/webhook."""

    @pytest.mark.asyncio
    async def test_webhook_no_signature(self, client: AsyncClient):
        """Returns 400 when webhook signature is missing."""
        response = await client.post(
            "/api/billing/webhook",
            content=b"{}",
        )
        assert response.status_code == 400
```

- [ ] **Step 2: Create billing router**

Create `backend/app/routers/billing.py`:

```python
"""
Billing router for Stripe checkout, portal, and webhooks.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing import (
    BillingStatusResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    UsageInfo,
)
from app.services.billing_service import get_billing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["Billing"])


@router.get("/status", response_model=BillingStatusResponse)
def get_billing_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current subscription status and usage."""
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()

    if not sub:
        return BillingStatusResponse(
            plan="free",
            status="active",
            usage=[],
        )

    return BillingStatusResponse(
        plan=sub.plan,
        status=sub.status,
        current_period_end=sub.current_period_end,
        usage=[],  # Usage details populated by frontend from individual endpoint responses
    )


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for upgrading to Pro."""
    billing = get_billing_service()
    try:
        url = billing.create_checkout_session(
            user_id=current_user.id,
            email=current_user.email,
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            db=db,
        )
        return CheckoutResponse(checkout_url=url)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("Failed to create checkout session")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/portal", response_model=PortalResponse)
def create_portal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing subscription."""
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No active subscription found")

    billing = get_billing_service()
    try:
        url = billing.create_portal_session(sub.stripe_customer_id)
        return PortalResponse(portal_url=url)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("Failed to create portal session")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events.

    No JWT auth — verified by Stripe signature.
    """
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    payload = await request.body()
    billing = get_billing_service()

    try:
        result = billing.handle_webhook_event(payload, sig_header, db)
        return {"received": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Webhook processing failed")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
```

- [ ] **Step 3: Register billing router in main.py**

In `backend/app/main.py`, add to imports (~line 44):

```python
from app.routers import (
    ...
    billing,  # Add this
    ...
)
```

And add after the last `app.include_router` call (~line 369):

```python
app.include_router(billing.router)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_billing.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `cd backend && uv run pytest tests/ -v --timeout=60`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/billing.py backend/tests/test_billing.py backend/app/main.py
git commit -m "feat: add billing router with checkout, portal, and webhook endpoints"
```

---

## Task 9: Add Email Verification and Onboarding Endpoints to Auth Router

**Files:**
- Modify: `backend/app/routers/auth.py`

- [ ] **Step 1: Read the current auth router to understand structure**

Read: `backend/app/routers/auth.py` (full file)

- [ ] **Step 2: Add verify-email endpoint**

Add to `backend/app/routers/auth.py` (after the existing endpoints):

```python
@router.get("/verify-email")
def verify_email(
    token: str = Query(..., description="Email verification token"),
    db: Session = Depends(get_db),
):
    """Verify email address using token from verification email."""
    user = db.query(User).filter(User.email_verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user.email_verified = True
    user.email_verification_token = None
    safe_commit(db, "verify email")

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
def resend_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resend email verification link."""
    if current_user.email_verified:
        return {"message": "Email already verified"}

    from app.services.email_service import get_email_service

    email_service = get_email_service()
    token = email_service.generate_verification_token()
    current_user.email_verification_token = token
    safe_commit(db, "update verification token")

    settings = get_settings()
    verify_url = f"{settings.app_url}/verify-email?token={token}"
    html = email_service.render_verification(verify_url)
    email_service.send(current_user.email, "Verify your email — ResuBoost", html)

    return {"message": "Verification email sent"}


class OnboardingUpdate(BaseModel):
    """Schema for updating onboarding state."""
    completed: Optional[bool] = None
    dismissed: Optional[bool] = None
    step: Optional[int] = None


@router.patch("/onboarding")
def update_onboarding(
    data: OnboardingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update onboarding progress."""
    if data.completed is not None:
        current_user.onboarding_completed = data.completed
    if data.dismissed is not None:
        current_user.onboarding_dismissed = data.dismissed
    if data.step is not None:
        current_user.onboarding_step = data.step
    safe_commit(db, "update onboarding")
    return {
        "onboarding_completed": current_user.onboarding_completed,
        "onboarding_dismissed": current_user.onboarding_dismissed,
        "onboarding_step": current_user.onboarding_step,
    }
```

Note: You'll need to add `from fastapi import Query` to the imports at the top if not already there, and ensure `safe_commit` is imported from `app.database`.

- [ ] **Step 3: Run auth tests**

Run: `cd backend && uv run pytest tests/test_auth.py -v`
Expected: All existing tests still pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/auth.py
git commit -m "feat: add email verification, resend, and onboarding endpoints to auth router"
```

---

## Task 10: Wire Feature Gates to Existing Routers

**Files:**
- Modify: `backend/app/routers/ai.py`
- Modify: `backend/app/routers/job_import.py`
- Modify: `backend/app/routers/jobs.py`
- Modify: `backend/app/routers/resumes.py`
- Modify: `backend/app/routers/company_research.py`
- Modify: `backend/app/routers/interview_events.py`

- [ ] **Step 1: Read each router file to find the exact endpoints to gate**

Read: All 6 router files listed above (focus on POST/create endpoints)

- [ ] **Step 2: Add feature gate to AI router**

In `backend/app/routers/ai.py`, add import:
```python
from app.middleware.feature_gate import check_usage_limit
```

Then add `_limit=Depends(check_usage_limit("ai_generation"))` as a parameter to each AI endpoint that generates content (tailor-resume, answer-question, interview-prep, generate cover letter, etc.).

For the interview-prep endpoint specifically, use `check_usage_limit("interview_prep")` instead.

- [ ] **Step 3: Add feature gate to job import router**

In `backend/app/routers/job_import.py`, add import:
```python
from app.middleware.feature_gate import check_usage_limit
```

Add `_limit=Depends(check_usage_limit("job_import"))` to the `import_job_from_url` and `bulk_import` endpoints.

Also add deduplication to `_save_job_to_db`:
```python
def _save_job_to_db(job_data: JobData, profile_id: int, db: Session) -> dict:
    # Check for duplicate
    job_url = job_data.job_url or job_data.application_url
    if job_url:
        existing = (
            db.query(JobApplication)
            .filter(
                JobApplication.profile_id == profile_id,
                JobApplication.job_url == job_url,
            )
            .first()
        )
        if existing:
            return {"id": existing.id, "duplicate": True, "status": existing.status}

    job = JobApplication(
        profile_id=profile_id,
        company=job_data.company,
        position=job_data.title,
        job_description=job_data.description,
        status="Bookmarked",
        location=job_data.location,
        job_url=job_url,
        application_source=_source_to_application_source(job_data.source),
    )
    db.add(job)
    safe_commit(db, "save imported job")
    db.refresh(job)
    return {"id": job.id, "duplicate": False}
```

Also update all callers of `_save_job_to_db` to handle the new dict return:

```python
# In import_job_from_url endpoint (~line 122):
# OLD: job_id = _save_job_to_db(job_data, profile.id, db)
# NEW:
result = _save_job_to_db(job_data, profile.id, db)
job_id = result["id"]
# Add "duplicate" field to response if result["duplicate"] is True

# In bulk_import endpoint: apply same pattern to each job in the loop
```

- [ ] **Step 4: Add count-based gates to jobs, resumes, company_research**

For `backend/app/routers/jobs.py` — in the create job endpoint, add imports and a check before `db.add(job)`:
```python
from app.config import get_settings
from app.middleware.feature_gate import is_pro_user, get_user_subscription

# In create endpoint, before db.add(job):
settings = get_settings()
if settings.enable_billing:
    sub = get_user_subscription(db, current_user.id)
    if not is_pro_user(sub):
        active_count = db.query(JobApplication).filter(
            JobApplication.profile_id == profile.id,
            JobApplication.status != "Rejected",
        ).count()
        if active_count >= 20:
            raise HTTPException(status_code=429, detail={
                "error": "limit_reached",
                "feature": "active_jobs",
                "limit": 20,
                "used": active_count,
                "upgrade_url": "/pricing",
            })
```

For `backend/app/routers/resumes.py` — in the upload/create endpoint, add the same imports and:
```python
# Before creating new resume:
settings = get_settings()
if settings.enable_billing:
    sub = get_user_subscription(db, current_user.id)
    if not is_pro_user(sub):
        resume_count = db.query(Resume).filter(Resume.profile_id == profile.id).count()
        if resume_count >= 2:
            raise HTTPException(status_code=429, detail={
                "error": "limit_reached",
                "feature": "resume_versions",
                "limit": 2,
                "used": resume_count,
                "upgrade_url": "/pricing",
            })
```

For `backend/app/routers/company_research.py` — in the create endpoint, add the same imports and:
```python
# Before creating new company research:
settings = get_settings()
if settings.enable_billing:
    sub = get_user_subscription(db, current_user.id)
    if not is_pro_user(sub):
        research_count = db.query(CompanyResearch).filter(
            CompanyResearch.profile_id == profile.id
        ).count()
        if research_count >= 3:
            raise HTTPException(status_code=429, detail={
                "error": "limit_reached",
                "feature": "company_research",
                "limit": 3,
                "used": research_count,
                "upgrade_url": "/pricing",
            })
```

Skip `interview_events.py` — no explicit limit in spec.

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v --timeout=60`
Expected: All tests pass (feature gates are no-ops when `ENABLE_BILLING=false`)

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/ai.py backend/app/routers/job_import.py backend/app/routers/jobs.py backend/app/routers/resumes.py backend/app/routers/company_research.py backend/app/routers/interview_events.py
git commit -m "feat: wire feature gates to AI, import, jobs, resumes, and company research routers"
```

---

## Task 11: Add Subscription Test Fixtures to conftest.py

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add subscription fixtures**

Add to `backend/tests/conftest.py` after the existing fixtures:

```python
from app.models.subscription import Subscription, UsageRecord


@pytest.fixture
def free_subscription(db: Session, test_user: User) -> Subscription:
    """Create a free tier subscription for the test user."""
    sub = Subscription(
        user_id=test_user.id,
        plan="free",
        status="active",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@pytest.fixture
def pro_subscription(db: Session, test_user: User) -> Subscription:
    """Create a pro tier subscription for the test user."""
    sub = Subscription(
        user_id=test_user.id,
        plan="pro_monthly",
        status="active",
        stripe_customer_id="cus_test_pro",
        stripe_subscription_id="sub_test_pro",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "feat: add subscription test fixtures to conftest"
```

---

## Task 12: Final Verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && uv run pytest tests/ -v --timeout=60`
Expected: All tests pass (700+ existing + ~25 new)

- [ ] **Step 2: Verify application starts**

Run: `cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &`
Then: `curl http://localhost:8000/health`
Expected: `{"status": "healthy", ...}`

Then: `curl http://localhost:8000/api/billing/status`
Expected: `401 Unauthorized` (no auth)

Then kill the server.

- [ ] **Step 3: Verify new endpoints appear in docs**

Run: `curl http://localhost:8000/openapi.json | python -m json.tool | grep billing`
Expected: Should see `/api/billing/status`, `/api/billing/checkout`, `/api/billing/portal`, `/api/billing/webhook`

- [ ] **Step 4: Final commit if any remaining changes**

```bash
git status
# If clean, done. If not, commit remaining changes.
```

---

## Summary

After completing this plan, the backend has:
- Subscription and UsageRecord models with proper indexes
- Feature gating middleware that enforces free tier limits (when `ENABLE_BILLING=true`)
- Email service with Resend integration (when `ENABLE_EMAIL=true`)
- Stripe billing service with checkout, portal, and webhook handling
- `/api/billing` router with 4 endpoints
- Email verification and onboarding endpoints on `/api/auth`
- Feature gates wired to AI, import, jobs, resumes, and company research routers
- ~25 new tests covering billing, feature gates, and email templates
- All behind feature flags that default to off (zero breaking changes)
