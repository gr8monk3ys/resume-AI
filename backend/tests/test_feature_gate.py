"""
Tests for feature gate middleware.

Covers:
- get_usage_count: no records, existing records, different periods
- increment_usage: creates record, increments existing
- Free tier limits: no subscription = free, billing disabled = no limits
- Pro tier: unlimited
- Subscription edge cases: canceled, past_due, free plan
"""

import os
import sys
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Ensure test env is set before app imports
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENABLE_BILLING", "false")

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.middleware.feature_gate import (
    FREE_TIER_LIMITS,
    check_usage_limit,
    get_period_reset,
    get_period_start,
    get_usage_count,
    get_user_subscription,
    increment_usage,
    is_pro_user,
)
from app.models.subscription import Subscription, UsageRecord
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_subscription(
    db: Session,
    user_id: int,
    plan: str = "pro_monthly",
    status: str = "active",
    current_period_end: datetime | None = None,
) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        plan=plan,
        status=status,
        current_period_end=current_period_end,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def make_usage_record(
    db: Session,
    user_id: int,
    feature: str,
    period_start: date,
    count: int = 1,
) -> UsageRecord:
    record = UsageRecord(
        user_id=user_id,
        feature=feature,
        period_start=period_start,
        count=count,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# TestGetUsageCount
# ---------------------------------------------------------------------------


class TestGetUsageCount:
    def test_no_records_returns_zero(self, db: Session, test_user: User):
        period_start = get_period_start("monthly")
        count = get_usage_count(db, test_user.id, "ai_generation", period_start)
        assert count == 0

    def test_existing_record_returns_count(self, db: Session, test_user: User):
        period_start = get_period_start("monthly")
        make_usage_record(db, test_user.id, "ai_generation", period_start, count=5)
        count = get_usage_count(db, test_user.id, "ai_generation", period_start)
        assert count == 5

    def test_different_period_returns_zero(self, db: Session, test_user: User):
        # Record is in a past period; querying current period returns 0
        past_period = date.today() - timedelta(days=35)
        make_usage_record(db, test_user.id, "ai_generation", past_period, count=10)
        current_period = get_period_start("monthly")
        count = get_usage_count(db, test_user.id, "ai_generation", current_period)
        assert count == 0

    def test_different_feature_returns_zero(self, db: Session, test_user: User):
        period_start = get_period_start("monthly")
        make_usage_record(db, test_user.id, "ai_generation", period_start, count=3)
        count = get_usage_count(db, test_user.id, "job_import", period_start)
        assert count == 0

    def test_different_user_returns_zero(self, db: Session, test_user: User, second_user: User):
        period_start = get_period_start("monthly")
        make_usage_record(db, test_user.id, "ai_generation", period_start, count=7)
        count = get_usage_count(db, second_user.id, "ai_generation", period_start)
        assert count == 0


# ---------------------------------------------------------------------------
# TestIncrementUsage
# ---------------------------------------------------------------------------


class TestIncrementUsage:
    def test_creates_record_if_none(self, db: Session, test_user: User):
        period_start = get_period_start("monthly")
        result = increment_usage(db, test_user.id, "ai_generation", period_start)
        assert result == 1
        count = get_usage_count(db, test_user.id, "ai_generation", period_start)
        assert count == 1

    def test_increments_existing_record(self, db: Session, test_user: User):
        period_start = get_period_start("monthly")
        make_usage_record(db, test_user.id, "ai_generation", period_start, count=4)
        result = increment_usage(db, test_user.id, "ai_generation", period_start)
        assert result == 5
        count = get_usage_count(db, test_user.id, "ai_generation", period_start)
        assert count == 5

    def test_increment_isolated_per_feature(self, db: Session, test_user: User):
        period_start = get_period_start("monthly")
        increment_usage(db, test_user.id, "ai_generation", period_start)
        increment_usage(db, test_user.id, "ai_generation", period_start)
        increment_usage(db, test_user.id, "job_import", period_start)
        assert get_usage_count(db, test_user.id, "ai_generation", period_start) == 2
        assert get_usage_count(db, test_user.id, "job_import", period_start) == 1


# ---------------------------------------------------------------------------
# TestFreeTierLimits
# ---------------------------------------------------------------------------


class TestFreeTierLimits:
    def test_no_subscription_treated_as_free(self, db: Session, test_user: User):
        sub = get_user_subscription(db, test_user.id)
        assert sub is None
        assert is_pro_user(sub) is False

    def test_billing_disabled_means_no_limits(self, db: Session, test_user: User):
        """When ENABLE_BILLING=false the dependency is a no-op and never raises."""
        # billing is disabled in the test environment (ENABLE_BILLING=false)
        dep = check_usage_limit("ai_generation")
        # The returned dependency should not raise even with no subscription
        # We call it directly with the db and test_user
        try:
            dep(current_user=test_user, db=db)
        except HTTPException:
            pytest.fail("check_usage_limit raised HTTPException with billing disabled")

    def test_free_plan_subscription_is_not_pro(self, db: Session, test_user: User):
        make_subscription(db, test_user.id, plan="free", status="active")
        sub = get_user_subscription(db, test_user.id)
        assert is_pro_user(sub) is False

    def test_free_tier_limit_enforced_when_billing_enabled(self, db: Session, test_user: User):
        """When billing is enabled, exceeding the limit raises HTTP 429."""
        feature = "ai_generation"
        limit_info = FREE_TIER_LIMITS[feature]
        period = limit_info["period"]
        limit = limit_info["limit"]
        period_start = get_period_start(period)

        # Fill usage up to the limit
        make_usage_record(db, test_user.id, feature, period_start, count=limit)

        dep = check_usage_limit(feature)

        with patch("app.middleware.feature_gate.get_settings") as mock_settings:
            mock_settings.return_value.enable_billing = True
            with pytest.raises(HTTPException) as exc_info:
                dep(current_user=test_user, db=db)
        assert exc_info.value.status_code == 429

    def test_free_tier_under_limit_does_not_raise(self, db: Session, test_user: User):
        """Under the limit, billing-enabled gate should pass and increment."""
        feature = "ai_generation"
        limit_info = FREE_TIER_LIMITS[feature]
        period = limit_info["period"]
        limit = limit_info["limit"]
        period_start = get_period_start(period)

        # One below the limit
        make_usage_record(db, test_user.id, feature, period_start, count=limit - 1)

        dep = check_usage_limit(feature)

        with patch("app.middleware.feature_gate.get_settings") as mock_settings:
            mock_settings.return_value.enable_billing = True
            try:
                dep(current_user=test_user, db=db)
            except HTTPException:
                pytest.fail("check_usage_limit raised unexpectedly under the limit")


# ---------------------------------------------------------------------------
# TestProTierNoLimits
# ---------------------------------------------------------------------------


class TestProTierNoLimits:
    def test_pro_monthly_active_is_pro(self, db: Session, test_user: User):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        make_subscription(
            db, test_user.id, plan="pro_monthly", status="active", current_period_end=future
        )
        sub = get_user_subscription(db, test_user.id)
        assert is_pro_user(sub) is True

    def test_pro_annual_active_is_pro(self, db: Session, test_user: User):
        future = datetime.now(timezone.utc) + timedelta(days=365)
        make_subscription(
            db, test_user.id, plan="pro_annual", status="active", current_period_end=future
        )
        sub = get_user_subscription(db, test_user.id)
        assert is_pro_user(sub) is True

    def test_pro_user_no_limit_even_at_cap(self, db: Session, test_user: User):
        """Pro users are never blocked regardless of usage count."""
        feature = "ai_generation"
        limit_info = FREE_TIER_LIMITS[feature]
        period = limit_info["period"]
        limit = limit_info["limit"]
        period_start = get_period_start(period)

        # Give the user an active pro subscription
        future = datetime.now(timezone.utc) + timedelta(days=30)
        make_subscription(
            db, test_user.id, plan="pro_monthly", status="active", current_period_end=future
        )

        # Exceed the free limit
        make_usage_record(db, test_user.id, feature, period_start, count=limit + 100)

        dep = check_usage_limit(feature)

        with patch("app.middleware.feature_gate.get_settings") as mock_settings:
            mock_settings.return_value.enable_billing = True
            try:
                dep(current_user=test_user, db=db)
            except HTTPException:
                pytest.fail("Pro user was blocked by feature gate")


# ---------------------------------------------------------------------------
# TestSubscriptionEdgeCases
# ---------------------------------------------------------------------------


class TestSubscriptionEdgeCases:
    def test_canceled_before_period_end_is_pro(self, db: Session, test_user: User):
        """Canceled subscription retains pro access until period_end."""
        future = datetime.now(timezone.utc) + timedelta(days=5)
        sub = make_subscription(
            db, test_user.id, plan="pro_monthly", status="canceled", current_period_end=future
        )
        assert is_pro_user(sub) is True

    def test_canceled_after_period_end_is_not_pro(self, db: Session, test_user: User):
        """Canceled subscription after period_end loses pro access."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        sub = make_subscription(
            db, test_user.id, plan="pro_monthly", status="canceled", current_period_end=past
        )
        assert is_pro_user(sub) is False

    def test_past_due_within_grace_period_is_pro(self, db: Session, test_user: User):
        """Past-due subscription within 7-day grace period is still pro."""
        # period ended 3 days ago → within 7-day grace
        period_end = datetime.now(timezone.utc) - timedelta(days=3)
        sub = make_subscription(
            db, test_user.id, plan="pro_monthly", status="past_due", current_period_end=period_end
        )
        assert is_pro_user(sub) is True

    def test_past_due_beyond_grace_period_is_not_pro(self, db: Session, test_user: User):
        """Past-due subscription beyond 7-day grace period loses pro access."""
        # period ended 10 days ago → beyond 7-day grace
        period_end = datetime.now(timezone.utc) - timedelta(days=10)
        sub = make_subscription(
            db, test_user.id, plan="pro_monthly", status="past_due", current_period_end=period_end
        )
        assert is_pro_user(sub) is False

    def test_free_plan_active_is_not_pro(self, db: Session, test_user: User):
        sub = make_subscription(db, test_user.id, plan="free", status="active")
        assert is_pro_user(sub) is False

    def test_none_subscription_is_not_pro(self):
        assert is_pro_user(None) is False

    def test_get_user_subscription_returns_subscription(self, db: Session, test_user: User):
        make_subscription(db, test_user.id, plan="pro_monthly", status="active")
        sub = get_user_subscription(db, test_user.id)
        assert sub is not None
        assert sub.user_id == test_user.id
        assert sub.plan == "pro_monthly"

    def test_get_user_subscription_no_subscription_returns_none(self, db: Session, test_user: User):
        sub = get_user_subscription(db, test_user.id)
        assert sub is None


# ---------------------------------------------------------------------------
# TestPeriodHelpers
# ---------------------------------------------------------------------------


class TestPeriodHelpers:
    def test_get_period_start_monthly(self):
        start = get_period_start("monthly")
        today = date.today()
        assert start == date(today.year, today.month, 1)

    def test_get_period_start_weekly(self):
        start = get_period_start("weekly")
        today = date.today()
        # Should be Monday of the current week
        expected = today - timedelta(days=today.weekday())
        assert start == expected

    def test_get_period_start_daily(self):
        start = get_period_start("daily")
        assert start == date.today()

    def test_get_period_reset_monthly_is_future(self):
        reset = get_period_reset("monthly")
        assert reset > datetime.now(timezone.utc)

    def test_get_period_reset_weekly_is_future(self):
        reset = get_period_reset("weekly")
        assert reset > datetime.now(timezone.utc)

    def test_get_period_reset_daily_is_next_day(self):
        """Daily reset is midnight UTC of the next day."""
        reset = get_period_reset("daily")
        today = date.today()
        tomorrow = today + timedelta(days=1)
        expected = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)
        assert reset == expected
