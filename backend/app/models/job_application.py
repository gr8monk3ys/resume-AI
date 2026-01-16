"""
Job application model for tracking applications.
"""

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class JobApplication(Base):
    """Job application tracker."""

    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    job_description = Column(Text, nullable=True)
    status = Column(
        String, default="Bookmarked", index=True
    )  # Bookmarked, Applied, Phone Screen, Interview, Offer, Rejected
    application_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    location = Column(String, nullable=True)
    job_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("Profile", back_populates="job_applications")
    cover_letters = relationship("CoverLetter", back_populates="job_application")


# Valid status values
JOB_STATUSES = [
    "Bookmarked",
    "Applied",
    "Phone Screen",
    "Interview",
    "Offer",
    "Rejected",
]
