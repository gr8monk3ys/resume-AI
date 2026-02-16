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


class VisaSponsorship(str, Enum):
    """Visa sponsorship availability for a job posting."""

    YES = "Yes"
    NO = "No"
    UNKNOWN = "Unknown"


class SalaryPeriod(str, Enum):
    """Salary period for compensation tracking."""

    YEARLY = "yearly"
    MONTHLY = "monthly"
    HOURLY = "hourly"


class RemoteType(str, Enum):
    """Remote work arrangement type."""

    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ON_SITE = "On-site"
    FLEXIBLE = "Flexible"


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

    # Visa sponsorship tracking
    visa_sponsorship: Optional[VisaSponsorship] = None

    # Salary tracking
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = "USD"
    salary_period: Optional[SalaryPeriod] = SalaryPeriod.YEARLY

    # Remote work type
    remote_type: Optional[RemoteType] = None

    @field_validator("recruiter_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is not None and v != "":
            # Basic email validation
            if "@" not in v or "." not in v:
                raise ValueError("Invalid email format")
        return v

    @field_validator("salary_min", "salary_max")
    @classmethod
    def validate_salary(cls, v: Optional[int]) -> Optional[int]:
        """Validate salary values are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Salary must be non-negative")
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

    # Visa sponsorship tracking
    visa_sponsorship: Optional[VisaSponsorship] = None

    # Salary tracking
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[SalaryPeriod] = None

    # Remote work type
    remote_type: Optional[RemoteType] = None

    @field_validator("recruiter_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is not None and v != "":
            if "@" not in v or "." not in v:
                raise ValueError("Invalid email format")
        return v

    @field_validator("salary_min", "salary_max")
    @classmethod
    def validate_salary(cls, v: Optional[int]) -> Optional[int]:
        """Validate salary values are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Salary must be non-negative")
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

    # Visa sponsorship tracking
    visa_sponsorship: Optional[str] = None

    # Salary tracking
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None

    # Remote work type
    remote_type: Optional[str] = None

    class Config:
        from_attributes = True
