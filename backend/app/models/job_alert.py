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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name = Column(String, nullable=False)

    # Alert criteria stored as JSON strings
    keywords = Column(Text, nullable=True)  # JSON array of keywords
    companies = Column(Text, nullable=True)  # JSON array of company names
    locations = Column(Text, nullable=True)  # JSON array of locations
    job_types = Column(Text, nullable=True)  # JSON array: Full-time, Part-time, Contract, etc.
    min_salary = Column(Integer, nullable=True)
    exclude_keywords = Column(Text, nullable=True)  # JSON array of keywords to exclude

    # Alert status
    is_active = Column(Boolean, default=True, index=True)
    last_checked = Column(DateTime, nullable=True)
    last_notified = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="job_alerts")
