"""
Subscription and usage tracking models for billing.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String
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
