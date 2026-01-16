"""
Profile model for user information.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Profile(Base):
    """User profile with personal information."""

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    name = Column(String, nullable=False, default="New User")
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)
    portfolio = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="profile")
    resumes = relationship("Resume", back_populates="profile", cascade="all, delete-orphan")
    job_applications = relationship(
        "JobApplication", back_populates="profile", cascade="all, delete-orphan"
    )
    cover_letters = relationship(
        "CoverLetter", back_populates="profile", cascade="all, delete-orphan"
    )
    journal_entries = relationship(
        "CareerJournalEntry", back_populates="profile", cascade="all, delete-orphan"
    )
