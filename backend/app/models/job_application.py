"""
Job application model for tracking applications.
"""

from datetime import date, datetime

from app.database import Base
from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship


class JobApplication(Base):
    """Job application tracker."""

    __tablename__ = "job_applications"

    # Composite indexes for common query patterns
    __table_args__ = (
        # Index for filtering by profile and status (used in Kanban view)
        Index("ix_job_applications_profile_status", "profile_id", "status"),
        # Index for sorting by updated_at within a profile (used in list view)
        Index("ix_job_applications_profile_updated", "profile_id", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    job_description = Column(Text, nullable=True)
    status = Column(
        String, default="Bookmarked", index=True
    )  # Bookmarked, Applied, Phone Screen, Interview, Offer, Rejected
    application_date = Column(Date, nullable=True, index=True)  # Added index for date filtering
    deadline = Column(Date, nullable=True)
    location = Column(String, nullable=True)
    job_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)  # Added index

    # HR Contact tracking fields
    recruiter_name = Column(String, nullable=True)
    recruiter_email = Column(String, nullable=True)
    recruiter_linkedin = Column(String, nullable=True)
    recruiter_phone = Column(String, nullable=True)

    # Referral tracking fields
    referral_name = Column(String, nullable=True)
    referral_relationship = Column(String, nullable=True)

    # Application source and response tracking
    application_source = Column(
        String, nullable=True, index=True
    )  # LinkedIn, Indeed, Company Site, Referral, etc.
    response_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Resume version used for this application
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="job_applications")
    cover_letters = relationship("CoverLetter", back_populates="job_application")
    resume = relationship("Resume")


# Valid status values
JOB_STATUSES = [
    "Bookmarked",
    "Applied",
    "Phone Screen",
    "Interview",
    "Offer",
    "Rejected",
]
