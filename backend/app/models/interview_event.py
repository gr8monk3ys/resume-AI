"""
Interview event model for tracking interview schedules and follow-ups.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class InterviewEvent(Base):
    """Interview event for tracking scheduled interviews."""

    __tablename__ = "interview_events"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    job_application_id = Column(
        Integer, ForeignKey("job_applications.id", ondelete="SET NULL"), nullable=True
    )
    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    scheduled_date = Column(String, nullable=False)
    scheduled_time = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    meeting_link = Column(String, nullable=True)
    interviewer_names = Column(Text, nullable=True)  # JSON array
    notes = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    follow_up_date = Column(String, nullable=True)
    follow_up_done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    profile = relationship("Profile", back_populates="interview_events")
