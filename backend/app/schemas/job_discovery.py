"""
Pydantic schemas for the job discovery / aggregation feature.

These schemas define the request and response models for searching across
multiple external job data sources (Adzuna, RemoteOK, RSS feeds).
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class JobSearchRequest(BaseModel):
    """Request schema for searching aggregated job sources."""

    query: str = Field(..., min_length=1, max_length=200, description="Job search query")
    location: Optional[str] = Field(
        None, max_length=100, description="Location filter (city, state, or country)"
    )
    remote_only: bool = Field(False, description="Only return remote positions")
    page: int = Field(1, ge=1, le=100, description="Page number for pagination")
    resume_content: Optional[str] = Field(
        None,
        max_length=100000,
        description="Resume text for calculating keyword match scores",
    )

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Strip whitespace from the search query."""
        return v.strip()


class DiscoveredJobResponse(BaseModel):
    """A single job listing returned from an external source."""

    title: str
    company: str
    location: Optional[str] = None
    url: str
    description_snippet: Optional[str] = None
    source: str
    posted_date: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    remote: bool = False
    visa_sponsorship: Optional[str] = None
    match_score: Optional[int] = Field(
        None, ge=0, le=100, description="Keyword match score (0-100) against resume"
    )


class JobSearchResponse(BaseModel):
    """Aggregated search response from all queried job sources."""

    jobs: List[DiscoveredJobResponse]
    total_results: int
    page: int
    sources_queried: List[str]
    sources_failed: List[str]


class JobSourceStatus(BaseModel):
    """Status information for a single job data source."""

    name: str
    enabled: bool
    requires_api_key: bool
    api_key_configured: bool
    description: str


class JobSourcesResponse(BaseModel):
    """Response listing all available job data sources and their status."""

    sources: List[JobSourceStatus]
    discovery_enabled: bool
