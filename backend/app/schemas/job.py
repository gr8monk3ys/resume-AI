"""
Job application schemas.
"""
from datetime import datetime, date
from typing import Optional
from enum import Enum
from pydantic import BaseModel


class JobStatus(str, Enum):
    """Valid job application statuses."""

    BOOKMARKED = "Bookmarked"
    APPLIED = "Applied"
    PHONE_SCREEN = "Phone Screen"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"


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

    class Config:
        from_attributes = True
