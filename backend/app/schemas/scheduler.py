"""
Scheduler schemas for job scraping background tasks.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class JobSchedulerStatus(str, Enum):
    """Scheduler operational status."""

    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"


class ScheduledJobStatus(str, Enum):
    """Status of a scheduled job."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapeSource(str, Enum):
    """Supported scraping sources."""

    GITHUB_NEW_GRAD = "github_new_grad"
    GITHUB_INTERNSHIPS = "github_internships"
    CUSTOM_URL = "custom_url"


class ScrapeCriteria(BaseModel):
    """Criteria for filtering scraped jobs."""

    locations: Optional[list[str]] = Field(
        None, description="Filter by locations (e.g., ['Remote', 'San Francisco'])"
    )
    companies: Optional[list[str]] = Field(None, description="Filter by company names to include")
    exclude_companies: Optional[list[str]] = Field(
        None, description="Companies to exclude from results"
    )
    keywords: Optional[list[str]] = Field(None, description="Keywords to match in job titles")
    exclude_keywords: Optional[list[str]] = Field(
        None, description="Keywords to exclude from job titles"
    )
    sponsorship_required: Optional[bool] = Field(
        None, description="Filter for jobs with sponsorship"
    )
    remote_only: Optional[bool] = Field(False, description="Only include remote positions")


class ScheduledJobCreate(BaseModel):
    """Schema for creating a new scheduled scrape job."""

    name: str = Field(..., min_length=1, max_length=100, description="Name for this scheduled job")
    source: ScrapeSource = Field(..., description="Source to scrape from")
    interval_minutes: int = Field(
        60,
        ge=5,
        le=1440,
        description="Scrape interval in minutes (min 5, max 1440)",
    )
    criteria: Optional[ScrapeCriteria] = Field(None, description="Optional filtering criteria")
    enabled: bool = Field(True, description="Whether the job is enabled")
    custom_url: Optional[str] = Field(None, description="Custom URL for CUSTOM_URL source type")

    @field_validator("custom_url")
    @classmethod
    def validate_custom_url(cls, v: Optional[str], info) -> Optional[str]:
        """Validate custom URL is provided when source is CUSTOM_URL."""
        if info.data.get("source") == ScrapeSource.CUSTOM_URL and not v:
            raise ValueError("custom_url is required when source is CUSTOM_URL")
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("custom_url must start with http:// or https://")
        return v


class ScheduledJobUpdate(BaseModel):
    """Schema for updating a scheduled job."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated name")
    interval_minutes: Optional[int] = Field(
        None, ge=5, le=1440, description="Updated interval in minutes"
    )
    criteria: Optional[ScrapeCriteria] = Field(None, description="Updated filtering criteria")
    enabled: Optional[bool] = Field(None, description="Enable or disable the job")


class ScheduledJobResponse(BaseModel):
    """Response schema for a scheduled job."""

    id: str = Field(..., description="Unique job identifier")
    name: str = Field(..., description="Job name")
    source: ScrapeSource = Field(..., description="Scraping source")
    interval_minutes: int = Field(..., description="Scrape interval in minutes")
    criteria: Optional[ScrapeCriteria] = Field(None, description="Filtering criteria")
    enabled: bool = Field(..., description="Whether the job is enabled")
    status: ScheduledJobStatus = Field(..., description="Current job status")
    user_id: int = Field(..., description="Owner user ID")
    custom_url: Optional[str] = Field(None, description="Custom URL if applicable")
    created_at: datetime = Field(..., description="When the job was created")
    last_run: Optional[datetime] = Field(None, description="Last execution time")
    next_run: Optional[datetime] = Field(None, description="Next scheduled execution")
    last_result: Optional[str] = Field(None, description="Result of last execution")
    jobs_found_last_run: int = Field(0, description="Jobs found in last run")
    total_jobs_found: int = Field(0, description="Total jobs found across all runs")
    error_count: int = Field(0, description="Number of consecutive errors")

    class Config:
        from_attributes = True


class SchedulerStatusResponse(BaseModel):
    """Response schema for scheduler status."""

    status: JobSchedulerStatus = Field(..., description="Scheduler operational status")
    active_jobs: int = Field(..., description="Number of active scheduled jobs")
    total_jobs: int = Field(..., description="Total number of scheduled jobs")
    uptime_seconds: Optional[float] = Field(None, description="Scheduler uptime in seconds")
    last_error: Optional[str] = Field(None, description="Last scheduler error if any")
    version: str = Field("1.0.0", description="Scheduler version")


class TriggerJobResponse(BaseModel):
    """Response schema for manually triggering a job."""

    success: bool = Field(..., description="Whether the trigger was successful")
    job_id: str = Field(..., description="The triggered job ID")
    message: str = Field(..., description="Status message")
    jobs_found: int = Field(0, description="Number of jobs found")
    new_jobs: int = Field(0, description="Number of new jobs added to pipeline")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")


class JobAlertCreate(BaseModel):
    """Schema for creating a job alert based on scrape criteria."""

    name: str = Field(..., min_length=1, max_length=100, description="Alert name")
    source: ScrapeSource = Field(..., description="Source to monitor")
    criteria: ScrapeCriteria = Field(..., description="Matching criteria for alerts")
    notify_email: bool = Field(False, description="Send email notifications")
    check_interval_minutes: int = Field(
        60, ge=15, le=1440, description="How often to check for new jobs"
    )


class JobAlertResponse(BaseModel):
    """Response schema for job alert."""

    id: str = Field(..., description="Alert ID")
    name: str = Field(..., description="Alert name")
    source: ScrapeSource = Field(..., description="Monitored source")
    criteria: ScrapeCriteria = Field(..., description="Alert criteria")
    notify_email: bool = Field(..., description="Email notifications enabled")
    user_id: int = Field(..., description="Owner user ID")
    created_at: datetime = Field(..., description="Creation time")
    last_check: Optional[datetime] = Field(None, description="Last check time")
    matches_found: int = Field(0, description="Total matches found")

    class Config:
        from_attributes = True
