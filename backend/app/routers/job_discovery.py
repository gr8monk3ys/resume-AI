"""
Router for the job discovery / aggregation feature.

Provides endpoints to search across multiple external job data sources
(Adzuna, RemoteOK, HN Who's Hiring) and to inspect source availability.

All endpoints require authentication and are subject to the AI rate-limiting
tier because they make external API calls.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.middleware.auth import get_current_user
from app.middleware.rate_limiter import rate_limit
from app.models.user import User
from app.schemas.job_discovery import (
    DiscoveredJobResponse,
    JobSearchRequest,
    JobSearchResponse,
    JobSourcesResponse,
    JobSourceStatus,
)
from app.services.job_discovery import get_job_discovery_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Job Discovery"])


@router.post(
    "/discover",
    response_model=JobSearchResponse,
    summary="Search aggregated job sources",
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60, key_prefix="job_discover"))],
)
async def discover_jobs(
    request: JobSearchRequest,
    current_user: User = Depends(get_current_user),
) -> JobSearchResponse:
    """
    Search for jobs across all configured external sources.

    Aggregates results from Adzuna, RemoteOK and Hacker News
    "Who is Hiring?" threads.  When ``resume_content`` is provided,
    each result receives a keyword-based ``match_score`` (0--100) and
    results are sorted by relevance.

    **Rate limit:** 20 requests per minute (AI tier).
    """
    settings = get_settings()
    if not settings.enable_job_discovery:
        raise HTTPException(
            status_code=503,
            detail="Job discovery feature is currently disabled.",
        )

    service = get_job_discovery_service()

    try:
        jobs, total, queried, failed = await service.search_jobs(
            query=request.query,
            location=request.location,
            remote_only=request.remote_only,
            page=request.page,
            resume_content=request.resume_content,
        )
    except Exception as e:
        logger.error(
            "Job discovery search failed for user %s: %s",
            current_user.id,
            str(e),
        )
        if settings.debug:
            raise HTTPException(status_code=500, detail=f"Job discovery failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Job discovery search failed. Please try again later.",
        )

    job_responses: List[DiscoveredJobResponse] = [
        DiscoveredJobResponse(
            title=j.title,
            company=j.company,
            location=j.location,
            url=j.url,
            description_snippet=j.description_snippet,
            source=j.source,
            posted_date=j.posted_date,
            salary_min=j.salary_min,
            salary_max=j.salary_max,
            remote=j.remote,
            visa_sponsorship=j.visa_sponsorship,
            match_score=j.match_score,
        )
        for j in jobs
    ]

    return JobSearchResponse(
        jobs=job_responses,
        total_results=total,
        page=request.page,
        sources_queried=queried,
        sources_failed=failed,
    )


@router.get(
    "/discover/sources",
    response_model=JobSourcesResponse,
    summary="List available job sources and their status",
)
async def list_sources(
    current_user: User = Depends(get_current_user),
) -> JobSourcesResponse:
    """
    Return metadata for each supported job data source, including
    whether it is enabled and whether its API key (if required) has
    been configured.
    """
    settings = get_settings()
    service = get_job_discovery_service()
    raw_sources = service.get_available_sources()

    sources = [
        JobSourceStatus(
            name=s["name"],
            enabled=s["enabled"],
            requires_api_key=s["requires_api_key"],
            api_key_configured=s["api_key_configured"],
            description=s["description"],
        )
        for s in raw_sources
    ]

    return JobSourcesResponse(
        sources=sources,
        discovery_enabled=settings.enable_job_discovery,
    )
