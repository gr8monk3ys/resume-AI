"""
Job alert schemas for request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class JobType(str, Enum):
    """Valid job types for alerts."""

    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"
    TEMPORARY = "Temporary"
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ON_SITE = "On-site"


class AlertCriteria(BaseModel):
    """Alert matching criteria."""

    keywords: Optional[List[str]] = Field(
        default=None, description="Keywords to match in job titles/descriptions"
    )
    companies: Optional[List[str]] = Field(default=None, description="Target company names")
    locations: Optional[List[str]] = Field(default=None, description="Desired job locations")
    job_types: Optional[List[JobType]] = Field(default=None, description="Job types to match")
    min_salary: Optional[int] = Field(default=None, ge=0, description="Minimum salary requirement")
    exclude_keywords: Optional[List[str]] = Field(
        default=None, description="Keywords to exclude from matches"
    )

    @field_validator("keywords", "companies", "locations", "exclude_keywords")
    @classmethod
    def validate_list_items(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Ensure list items are non-empty strings."""
        if v is not None:
            return [item.strip() for item in v if item and item.strip()]
        return v


class JobAlertCreate(BaseModel):
    """Schema for creating a job alert."""

    name: str = Field(..., min_length=1, max_length=100, description="Alert name")
    keywords: Optional[List[str]] = None
    companies: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    job_types: Optional[List[JobType]] = None
    min_salary: Optional[int] = Field(default=None, ge=0)
    exclude_keywords: Optional[List[str]] = None
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty."""
        return v.strip()


class JobAlertUpdate(BaseModel):
    """Schema for updating a job alert."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    keywords: Optional[List[str]] = None
    companies: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    job_types: Optional[List[JobType]] = None
    min_salary: Optional[int] = Field(default=None, ge=0)
    exclude_keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not empty if provided."""
        if v is not None:
            return v.strip()
        return v


class JobAlertResponse(BaseModel):
    """Schema for job alert response."""

    id: int
    user_id: int
    name: str
    keywords: Optional[List[str]] = None
    companies: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    job_types: Optional[List[str]] = None
    min_salary: Optional[int] = None
    exclude_keywords: Optional[List[str]] = None
    is_active: bool
    last_checked: Optional[datetime] = None
    last_notified: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobMatch(BaseModel):
    """Schema for a job that matches an alert."""

    job_id: int
    company: str
    position: str
    location: Optional[str] = None
    job_url: Optional[str] = None
    match_score: float = Field(
        ge=0, le=1, description="How well the job matches the alert criteria"
    )
    matched_criteria: List[str] = Field(default_factory=list, description="Which criteria matched")


class AlertNotification(BaseModel):
    """Schema for alert notification sent via WebSocket."""

    alert_id: int
    alert_name: str
    matches: List[JobMatch]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: str


class AlertTestResult(BaseModel):
    """Schema for testing an alert against recent jobs."""

    alert_id: int
    total_jobs_checked: int
    matching_jobs: List[JobMatch]
    match_count: int


class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages."""

    type: str = Field(..., description="Message type: notification, ping, pong, error")
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
