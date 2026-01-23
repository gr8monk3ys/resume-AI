"""
Job import schemas for URL scraping and GitHub repo imports.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class JobSource(str, Enum):
    """Supported job sources for import."""

    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    LEVER = "lever"
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    GITHUB_SIMPLIFY = "github_simplify"
    COMPANY_SITE = "company_site"
    UNKNOWN = "unknown"


class JobType(str, Enum):
    """Job type categories."""

    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"
    TEMPORARY = "Temporary"
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    UNKNOWN = "Unknown"


class JobData(BaseModel):
    """Extracted job data from import."""

    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = "USD"
    job_type: Optional[JobType] = JobType.UNKNOWN
    job_url: Optional[str] = None
    application_url: Optional[str] = None
    source: JobSource = JobSource.UNKNOWN
    posted_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    requirements: Optional[list[str]] = None
    benefits: Optional[list[str]] = None
    remote: Optional[bool] = None
    experience_level: Optional[str] = None
    raw_data: Optional[dict] = None

    class Config:
        from_attributes = True


class JobImportRequest(BaseModel):
    """Request schema for importing a single job from URL."""

    url: str = Field(..., description="URL of the job posting to import")
    source: Optional[JobSource] = Field(
        None, description="Job source hint (auto-detected if not provided)"
    )
    save_to_pipeline: bool = Field(True, description="Whether to save the job to the pipeline")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.strip()


class BulkJobImportRequest(BaseModel):
    """Request schema for importing multiple jobs from URLs."""

    urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of job URLs to import (max 50)",
    )
    save_to_pipeline: bool = Field(True, description="Whether to save jobs to the pipeline")

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        """Validate all URLs in the list."""
        validated = []
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL format: {url}")
            validated.append(url.strip())
        return validated


class GitHubRepoFilter(BaseModel):
    """Filters for GitHub repo import."""

    locations: Optional[list[str]] = Field(
        None, description="Filter by locations (e.g., ['Remote', 'New York'])"
    )
    companies: Optional[list[str]] = Field(None, description="Filter by company names")
    sponsorship: Optional[bool] = Field(None, description="Filter by sponsorship availability")
    exclude_companies: Optional[list[str]] = Field(None, description="Companies to exclude")
    min_posted_date: Optional[datetime] = Field(
        None, description="Only include jobs posted after this date"
    )


class GitHubRepoImportRequest(BaseModel):
    """Request schema for importing jobs from a GitHub repo."""

    repo_url: str = Field(
        ...,
        description="GitHub repo URL (e.g., https://github.com/SimplifyJobs/New-Grad-Positions)",
    )
    filters: Optional[GitHubRepoFilter] = Field(None, description="Optional filters for the import")
    max_jobs: int = Field(100, ge=1, le=500, description="Maximum number of jobs to import")
    save_to_pipeline: bool = Field(True, description="Whether to save jobs to the pipeline")

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Validate GitHub URL format."""
        if not v.startswith("https://github.com/"):
            raise ValueError("URL must be a GitHub repository URL")
        return v.strip().rstrip("/")


class ImportError(BaseModel):
    """Error details for failed import."""

    url: str
    error_code: str
    message: str
    recoverable: bool = False


class ImportResult(BaseModel):
    """Result of a single job import attempt."""

    url: str
    success: bool
    job_data: Optional[JobData] = None
    job_id: Optional[int] = None
    error: Optional[ImportError] = None


class JobImportResponse(BaseModel):
    """Response schema for single job import."""

    success: bool
    job_data: Optional[JobData] = None
    job_id: Optional[int] = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_detected: Optional[JobSource] = None


class BulkImportResponse(BaseModel):
    """Response schema for bulk job import."""

    success: bool
    results: list[ImportResult]
    success_count: int
    error_count: int
    total_requested: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GitHubRepoImportResponse(BaseModel):
    """Response schema for GitHub repo import."""

    success: bool
    repo_url: str
    repo_name: Optional[str] = None
    total_found: int
    total_imported: int
    total_filtered_out: int
    results: list[ImportResult]
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class JobPreviewResponse(BaseModel):
    """Response schema for job preview (without saving)."""

    success: bool
    job_data: Optional[JobData] = None
    source_detected: Optional[JobSource] = None
    confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence score for extracted data"
    )
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
