"""
Job import router for importing jobs from URLs and GitHub repos.
"""

import logging
from typing import Optional

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User
from app.schemas.job import ApplicationSource
from app.schemas.job_import import (
    BulkImportResponse,
    BulkJobImportRequest,
    GitHubRepoImportRequest,
    GitHubRepoImportResponse,
    ImportResult,
    JobData,
    JobImportRequest,
    JobImportResponse,
    JobPreviewResponse,
    JobSource,
)
from app.services.job_importer import (
    JobImporter,
    JobImportError,
    get_job_importer,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs/import", tags=["Job Import"])


def get_user_profile(user: User, db: Session) -> Profile:
    """Get or create user profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, name=user.full_name or user.username)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _source_to_application_source(source: JobSource) -> Optional[str]:
    """Map JobSource to ApplicationSource string."""
    mapping = {
        JobSource.LINKEDIN: ApplicationSource.LINKEDIN.value,
        JobSource.INDEED: ApplicationSource.INDEED.value,
        JobSource.GLASSDOOR: ApplicationSource.GLASSDOOR.value,
        JobSource.COMPANY_SITE: ApplicationSource.COMPANY_SITE.value,
    }
    return mapping.get(source, ApplicationSource.OTHER.value)


def _save_job_to_db(
    job_data: JobData,
    profile_id: int,
    db: Session,
) -> int:
    """
    Save imported job data to database.

    Args:
        job_data: Extracted job data.
        profile_id: User's profile ID.
        db: Database session.

    Returns:
        Created job application ID.
    """
    job = JobApplication(
        profile_id=profile_id,
        company=job_data.company,
        position=job_data.title,
        job_description=job_data.description,
        status="Bookmarked",
        location=job_data.location,
        job_url=job_data.job_url or job_data.application_url,
        application_source=_source_to_application_source(job_data.source),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job.id


@router.post("/url", response_model=JobImportResponse, status_code=status.HTTP_201_CREATED)
async def import_job_from_url(
    request: JobImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    importer: JobImporter = Depends(get_job_importer),
):
    """
    Import a single job from a URL.

    Supports job postings from:
    - LinkedIn Jobs
    - Indeed
    - Glassdoor
    - Lever (ATS)
    - Greenhouse (ATS)
    - Workday (ATS)
    - Most company career pages

    The job will be added to your pipeline with status "Bookmarked".
    """
    profile = get_user_profile(current_user, db)
    errors: list[str] = []
    warnings: list[str] = []

    try:
        # Detect source
        detected_source = request.source or importer._detect_source(request.url)

        # Import job data
        job_data = await importer.import_from_url(request.url, detected_source)
        job_id = None

        # Save to database if requested
        if request.save_to_pipeline:
            try:
                job_id = _save_job_to_db(job_data, profile.id, db)
            except Exception as e:
                logger.error(f"Failed to save job to database: {e}")
                warnings.append("Job imported but could not be saved to pipeline")

        return JobImportResponse(
            success=True,
            job_data=job_data,
            job_id=job_id,
            source_detected=detected_source,
            warnings=warnings,
        )

    except JobImportError as e:
        logger.warning(f"Job import failed for {request.url}: {e.message}")
        return JobImportResponse(
            success=False,
            errors=[e.message],
            source_detected=request.source or importer._detect_source(request.url),
        )
    except Exception as e:
        logger.error(f"Unexpected error importing job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while importing the job",
        )


@router.post("/bulk", response_model=BulkImportResponse)
async def import_jobs_bulk(
    request: BulkJobImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    importer: JobImporter = Depends(get_job_importer),
):
    """
    Import multiple jobs from URLs.

    Accepts up to 50 URLs at once. Jobs are processed concurrently
    with rate limiting to avoid being blocked by job sites.

    Each successfully imported job will be added to your pipeline
    with status "Bookmarked".
    """
    profile = get_user_profile(current_user, db)

    # Define save callback for each job
    async def save_callback(job_data: JobData) -> int:
        return _save_job_to_db(job_data, profile.id, db)

    # Perform bulk import
    if request.save_to_pipeline:
        result = await importer.bulk_import(request.urls, save_callback)
    else:
        result = await importer.bulk_import(request.urls)

    return result


@router.post("/github", response_model=GitHubRepoImportResponse)
async def import_jobs_from_github(
    request: GitHubRepoImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    importer: JobImporter = Depends(get_job_importer),
):
    """
    Import jobs from a SimplifyJobs-style GitHub repository.

    Supported repositories:
    - https://github.com/SimplifyJobs/New-Grad-Positions
    - https://github.com/SimplifyJobs/Summer2025-Internships
    - Similar formatted repos

    You can filter jobs by:
    - Location (e.g., "Remote", "New York")
    - Company name
    - Sponsorship availability
    - Posted date
    """
    profile = get_user_profile(current_user, db)
    errors: list[str] = []
    warnings: list[str] = []
    results: list[ImportResult] = []

    try:
        # Import jobs from GitHub repo
        jobs = await importer.import_from_github_repo(
            request.repo_url,
            request.filters,
            request.max_jobs,
        )

        total_found = len(jobs)
        total_imported = 0
        total_filtered_out = 0

        # Save each job if requested
        for job_data in jobs:
            job_id = None

            if request.save_to_pipeline:
                try:
                    job_id = _save_job_to_db(job_data, profile.id, db)
                    total_imported += 1
                except Exception as e:
                    logger.error(f"Failed to save job {job_data.title}: {e}")
                    warnings.append(f"Could not save: {job_data.company} - {job_data.title}")

            results.append(
                ImportResult(
                    url=job_data.job_url or job_data.application_url or "",
                    success=True,
                    job_data=job_data,
                    job_id=job_id,
                )
            )

        # Extract repo name from URL
        repo_name = request.repo_url.split("/")[-1] if "/" in request.repo_url else None

        return GitHubRepoImportResponse(
            success=True,
            repo_url=request.repo_url,
            repo_name=repo_name,
            total_found=total_found,
            total_imported=total_imported if request.save_to_pipeline else 0,
            total_filtered_out=total_filtered_out,
            results=results,
            warnings=warnings,
        )

    except JobImportError as e:
        logger.warning(f"GitHub import failed for {request.repo_url}: {e.message}")
        return GitHubRepoImportResponse(
            success=False,
            repo_url=request.repo_url,
            total_found=0,
            total_imported=0,
            total_filtered_out=0,
            results=[],
            errors=[e.message],
        )
    except Exception as e:
        logger.error(f"Unexpected error importing from GitHub: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while importing from GitHub",
        )


@router.get("/preview", response_model=JobPreviewResponse)
async def preview_job_from_url(
    url: str = Query(..., description="URL of the job posting to preview"),
    current_user: User = Depends(get_current_user),
    importer: JobImporter = Depends(get_job_importer),
):
    """
    Preview job data from a URL without saving.

    Use this endpoint to verify what data will be extracted
    before committing to an import. Returns a confidence score
    indicating how complete the extracted data is.
    """
    try:
        return await importer.preview_job(url)
    except Exception as e:
        logger.error(f"Preview failed for {url}: {e}")
        return JobPreviewResponse(
            success=False,
            errors=[str(e)],
        )


@router.get("/sources")
async def list_supported_sources(
    current_user: User = Depends(get_current_user),
):
    """
    List all supported job sources and their URL patterns.

    Returns information about which job sites are supported
    for automatic import.
    """
    return {
        "sources": [
            {
                "name": "LinkedIn",
                "slug": JobSource.LINKEDIN.value,
                "url_patterns": ["linkedin.com/jobs/", "linkedin.com/job/"],
                "notes": "May have limited data due to site restrictions",
            },
            {
                "name": "Indeed",
                "slug": JobSource.INDEED.value,
                "url_patterns": ["indeed.com/viewjob", "indeed.com/job/"],
                "notes": "Full job details typically available",
            },
            {
                "name": "Glassdoor",
                "slug": JobSource.GLASSDOOR.value,
                "url_patterns": ["glassdoor.com/job-listing/", "glassdoor.com/Job/"],
                "notes": "May have limited data due to site restrictions",
            },
            {
                "name": "Lever",
                "slug": JobSource.LEVER.value,
                "url_patterns": ["lever.co/", "jobs.lever.co/"],
                "notes": "Full job details typically available",
            },
            {
                "name": "Greenhouse",
                "slug": JobSource.GREENHOUSE.value,
                "url_patterns": ["greenhouse.io/", "boards.greenhouse.io/"],
                "notes": "Full job details typically available",
            },
            {
                "name": "Workday",
                "slug": JobSource.WORKDAY.value,
                "url_patterns": ["myworkdayjobs.com/"],
                "notes": "Full job details typically available",
            },
            {
                "name": "GitHub (SimplifyJobs)",
                "slug": JobSource.GITHUB_SIMPLIFY.value,
                "url_patterns": ["github.com/SimplifyJobs/"],
                "notes": "Bulk import from New-Grad-Positions, Summer Internships repos",
            },
            {
                "name": "Company Career Pages",
                "slug": JobSource.COMPANY_SITE.value,
                "url_patterns": ["Any other URL"],
                "notes": "Best-effort parsing using structured data",
            },
        ],
        "rate_limits": {
            "per_source_per_minute": {
                JobSource.LINKEDIN.value: 5,
                JobSource.INDEED.value: 10,
                JobSource.GLASSDOOR.value: 5,
                JobSource.LEVER.value: 20,
                JobSource.GREENHOUSE.value: 20,
                JobSource.WORKDAY.value: 10,
                JobSource.GITHUB_SIMPLIFY.value: 30,
                JobSource.COMPANY_SITE.value: 15,
            }
        },
        "bulk_import_limit": 50,
    }
