"""
Feature gating middleware for free/pro tier enforcement.

Provides:
- FREE_TIER_LIMITS: limits per feature
- Period boundary helpers
- Usage tracking helpers
- FastAPI dependency factory for enforcing limits
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.subscription import Subscription, UsageRecord
from app.models.user import User

# ---------------------------------------------------------------------------
# Free tier limits
# ---------------------------------------------------------------------------

FREE_TIER_LIMITS: dict[str, dict] = {
    "ai_generation": {"limit": 3, "period": "daily"},
    "job_import": {"limit": 5, "period": "monthly"},
    "interview_prep": {"limit": 1, "period": "weekly"},
    # "total" period features — enforced by individual routers, not this middleware
    "active_jobs": {"limit": 20, "period": "total"},
    "resume_versions": {"limit": 2, "period": "total"},
    "company_research": {"limit": 3, "period": "total"},
}

# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------


def get_period_start(period: str) -> date:
    """
    Return the start date of the current period.

    Accepted period strings:
    - ``"daily"``   → today
    - ``"weekly"``  → Monday of the current ISO week
    - ``"monthly"`` → first day of the current month
    - ``"total"``   → epoch date (2000-01-01) shared across all time
    """
    today = date.today()
    if period == "daily":
        return today
    if period == "weekly":
        # ISO weekday: Monday == 0
        return today - timedelta(days=today.weekday())
    if period == "monthly":
        return today.replace(day=1)
    if period == "total":
        return date(2000, 1, 1)
    raise ValueError(f"Unknown period: {period!r}")


def get_period_reset(period: str) -> datetime:
    """
    Return the UTC datetime when the current period resets (start of next period).

    - ``"daily"``   → midnight UTC tomorrow
    - ``"weekly"``  → midnight UTC next Monday
    - ``"monthly"`` → midnight UTC first day of next month
    - ``"total"``   → datetime.max (sentinel: never resets)
    """
    today = date.today()
    if period == "daily":
        next_day = today + timedelta(days=1)
        return datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)
    if period == "weekly":
        monday = today - timedelta(days=today.weekday())
        next_monday = monday + timedelta(weeks=1)
        return datetime(next_monday.year, next_monday.month, next_monday.day, tzinfo=timezone.utc)
    if period == "monthly":
        if today.month == 12:
            first_next = date(today.year + 1, 1, 1)
        else:
            first_next = date(today.year, today.month + 1, 1)
        return datetime(first_next.year, first_next.month, first_next.day, tzinfo=timezone.utc)
    if period == "total":
        return datetime.max
    raise ValueError(f"Unknown period: {period!r}")


# ---------------------------------------------------------------------------
# Usage helpers
# ---------------------------------------------------------------------------


def get_usage_count(db: Session, user_id: int, feature: str, period_start: date) -> int:
    """Return the usage count for a user/feature/period, or 0 if no record exists."""
    record = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.user_id == user_id,
            UsageRecord.feature == feature,
            UsageRecord.period_start == period_start,
        )
        .first()
    )
    return int(record.count) if record else 0


def increment_usage(db: Session, user_id: int, feature: str, period_start: date) -> int:
    """
    Atomically increment the usage count for a user/feature/period.

    Uses ``SELECT FOR UPDATE`` on PostgreSQL for row-level locking.
    Falls back to a plain select on SQLite (which does not support FOR UPDATE).

    Returns the new count.
    """
    # Detect SQLite to skip FOR UPDATE (unsupported)
    is_sqlite = db.bind is not None and "sqlite" in str(db.bind.url).lower()  # type: ignore[union-attr]

    try:
        query = db.query(UsageRecord).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.feature == feature,
            UsageRecord.period_start == period_start,
        )
        if not is_sqlite:
            query = query.with_for_update()
        record = query.first()

        if record is None:
            record = UsageRecord(
                user_id=user_id,
                feature=feature,
                period_start=period_start,
                count=1,
            )
            db.add(record)
            db.flush()
        else:
            record.count = record.count + 1  # type: ignore[assignment]
            db.flush()

        db.commit()
        return int(record.count)

    except IntegrityError:
        # Race condition: another request inserted the record first.
        # Rollback and retry with an update.
        db.rollback()
        record = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.user_id == user_id,
                UsageRecord.feature == feature,
                UsageRecord.period_start == period_start,
            )
            .first()
        )
        if record:
            record.count = record.count + 1  # type: ignore[assignment]
            db.commit()
            return int(record.count)
        raise  # Should never reach here


# ---------------------------------------------------------------------------
# Subscription helpers
# ---------------------------------------------------------------------------


def get_user_subscription(db: Session, user_id: int) -> Optional[Subscription]:
    """Return the Subscription record for a user, or None if not found."""
    return db.query(Subscription).filter(Subscription.user_id == user_id).first()


def is_pro_user(subscription: Optional[Subscription]) -> bool:
    """
    Determine whether a user has active pro access.

    Rules:
    - No subscription → free (False)
    - ``plan == "free"`` → never pro (False), regardless of status
    - ``status == "active"`` → pro (True)
    - ``status == "canceled"`` → pro until ``current_period_end``, then free
    - ``status == "past_due"`` → 7-day grace period after ``current_period_end``
    - Any other status → free (False)
    """
    if subscription is None:
        return False
    if subscription.plan == "free":
        return False

    now = datetime.now(timezone.utc)

    if subscription.status == "active":
        return True

    if subscription.status == "canceled":
        if subscription.current_period_end is None:
            return False
        period_end = subscription.current_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        return bool(now <= period_end)

    if subscription.status == "past_due":
        if subscription.current_period_end is None:
            return False
        period_end = subscription.current_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        grace_deadline = period_end + timedelta(days=7)
        return bool(now <= grace_deadline)

    return False


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------


def check_usage_limit(feature: str):
    """
    FastAPI dependency factory that enforces free-tier usage limits.

    Usage::

        @router.post("/generate")
        async def generate(
            _: None = Depends(check_usage_limit("ai_generation")),
            ...
        ):
            ...

    Behaviour:
    - ``ENABLE_BILLING=false`` → no-op (always allow).
    - Pro user → no limit enforced; returns immediately.
    - Feature with ``period="total"`` → skip (handled by individual routers).
    - Unknown feature → skip.
    - Free user at or over limit → HTTP 429.
    - Free user under limit → increment usage and continue.
    """

    def dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> None:
        settings = get_settings()

        # Billing feature disabled — enforce nothing
        if not settings.enable_billing:
            return

        # Unknown feature — no restriction defined
        if feature not in FREE_TIER_LIMITS:
            return

        limit_config = FREE_TIER_LIMITS[feature]
        period = limit_config["period"]

        # "total" features are enforced by individual routers
        if period == "total":
            return

        # Check subscription tier
        subscription = get_user_subscription(db, int(current_user.id))
        if is_pro_user(subscription):
            return  # Pro users bypass all rate limits

        # Free tier enforcement
        limit = limit_config["limit"]
        period_start = get_period_start(period)
        current_count = get_usage_count(db, int(current_user.id), feature, period_start)

        if current_count >= limit:
            reset_dt = get_period_reset(period)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "free_tier_limit_reached",
                    "feature": feature,
                    "limit": limit,
                    "period": period,
                    "used": current_count,
                    "resets_at": reset_dt.isoformat(),
                    "message": (
                        f"You have used {current_count}/{limit} "
                        f"{feature.replace('_', ' ')} this {period}. "
                        "Upgrade to Pro for unlimited access."
                    ),
                },
            )

        # Under limit — increment and allow
        increment_usage(db, int(current_user.id), feature, period_start)

    return dependency
