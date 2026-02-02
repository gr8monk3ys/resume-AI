"""
Job alert model for real-time job notifications.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class JobAlert(Base):
    """Job alert for tracking job search criteria and notifications."""

    __tablename__ = "job_alerts"

    id: Column[int] = Column(Integer, primary_key=True, index=True)
    user_id: Column[int] = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Column[str] = Column(String, nullable=False)

    # Alert criteria stored as JSON strings
    keywords: Column[str] = Column(Text, nullable=True)  # JSON array of keywords
    companies: Column[str] = Column(Text, nullable=True)  # JSON array of company names
    locations: Column[str] = Column(Text, nullable=True)  # JSON array of locations
    job_types: Column[str] = Column(Text, nullable=True)  # JSON array: Full-time, Part-time, etc.
    min_salary: Column[int] = Column(Integer, nullable=True)
    exclude_keywords: Column[str] = Column(Text, nullable=True)  # JSON array of keywords to exclude

    # Alert status
    is_active: Column[bool] = Column(Boolean, default=True, index=True)
    last_checked: Column[datetime] = Column(DateTime, nullable=True)
    last_notified: Column[datetime] = Column(DateTime, nullable=True)

    # Timestamps
    created_at: Column[datetime] = Column(DateTime, default=datetime.utcnow)
    updated_at: Column[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="job_alerts")
