"""
Job application schemas.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class JobStatus(str, Enum):
    """Valid job application statuses."""

    BOOKMARKED = "Bookmarked"
    APPLIED = "Applied"
    PHONE_SCREEN = "Phone Screen"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"


class ApplicationSource(str, Enum):
    """Valid application sources."""

    LINKEDIN = "LinkedIn"
    INDEED = "Indeed"
    GLASSDOOR = "Glassdoor"
    COMPANY_SITE = "Company Site"
    REFERRAL = "Referral"
    RECRUITER = "Recruiter"
    JOB_FAIR = "Job Fair"
    NETWORKING = "Networking"
    OTHER = "Other"


class JobCreate(BaseModel):
    """Schema for creating a job application."""

    company: str
    position: str
    job_description: Optional[str] = None
    status: JobStatus = JobStatus.BOOKMARKED
    application_date: Optional[date] = None
    deadline: Optional[date] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None

    # HR Contact fields
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_linkedin: Optional[str] = None
    recruiter_phone: Optional[str] = None

    # Referral fields
    referral_name: Optional[str] = None
    referral_relationship: Optional[str] = None

    # Source and response tracking
    application_source: Optional[ApplicationSource] = None
    response_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Resume version used
    resume_id: Optional[int] = None

    @field_validator("recruiter_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is not None and v != "":
            # Basic email validation
            if "@" not in v or "." not in v:
                raise ValueError("Invalid email format")
        return v


class JobUpdate(BaseModel):
    """Schema for updating a job application."""

    company: Optional[str] = None
    position: Optional[str] = None
    job_description: Optional[str] = None
    status: Optional[JobStatus] = None
    application_date: Optional[date] = None
    deadline: Optional[date] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None

    # HR Contact fields
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_linkedin: Optional[str] = None
    recruiter_phone: Optional[str] = None

    # Referral fields
    referral_name: Optional[str] = None
    referral_relationship: Optional[str] = None

    # Source and response tracking
    application_source: Optional[ApplicationSource] = None
    response_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Resume version used
    resume_id: Optional[int] = None

    @field_validator("recruiter_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is not None and v != "":
            if "@" not in v or "." not in v:
                raise ValueError("Invalid email format")
        return v


class JobResponse(BaseModel):
    """Schema for job application response."""

    id: int
    profile_id: int
    company: str
    position: str
    job_description: Optional[str] = None
    status: str
    application_date: Optional[date] = None
    deadline: Optional[date] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # HR Contact fields
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_linkedin: Optional[str] = None
    recruiter_phone: Optional[str] = None

    # Referral fields
    referral_name: Optional[str] = None
    referral_relationship: Optional[str] = None

    # Source and response tracking
    application_source: Optional[str] = None
    response_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Resume version used
    resume_id: Optional[int] = None

    class Config:
        from_attributes = True
