"""
User model for authentication.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)
    # Token version for invalidating all existing tokens on password change
    # Incrementing this value invalidates all previously issued tokens for this user
    token_version = Column(Integer, default=0, nullable=False)

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

    # Relationship to profile
    profile = relationship("Profile", back_populates="user", uselist=False)
