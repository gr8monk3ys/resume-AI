"""
Jobs router for job application tracking.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db, safe_commit
from app.middleware.auth import get_current_user
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse, JobStatus, JobUpdate
from app.schemas.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def get_user_profile(user: User, db: Session) -> Profile:
    """Get or create user profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, name=user.full_name or user.username)
        db.add(profile)
        safe_commit(db, "create profile")
        db.refresh(profile)
    return profile


@router.get("", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    search: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List job applications for current user with pagination.

    Args:
        status_filter: Filter by job status (optional)
        search: Search term for company/position (optional)
        pagination: Pagination parameters (page, limit)

    Returns:
        Paginated list of job applications with metadata
    """
    profile = get_user_profile(current_user, db)

    # Build base query with filters
    query = db.query(JobApplication).filter(JobApplication.profile_id == profile.id)

    if status_filter:
        query = query.filter(JobApplication.status == status_filter.value)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (JobApplication.company.ilike(search_term))
            | (JobApplication.position.ilike(search_term))
        )

    # Get total count efficiently using SQL COUNT
    total = query.count()

    # Apply pagination and ordering
    jobs = (
        query.order_by(JobApplication.updated_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )

    return PaginatedResponse.create(
        items=jobs,
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )


@router.get("/stats")
async def get_job_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get job application statistics using SQL aggregation for performance."""
    profile = get_user_profile(current_user, db)

    # Use SQL GROUP BY for efficient aggregation instead of Python iteration
    status_counts_query = (
        db.query(JobApplication.status, func.count(JobApplication.id))
        .filter(JobApplication.profile_id == profile.id)
        .group_by(JobApplication.status)
        .all()
    )
    status_counts = dict(status_counts_query)

    # Calculate totals from aggregated data
    total = sum(status_counts.values())
    applied = status_counts.get("Applied", 0)
    interviews = status_counts.get("Interview", 0) + status_counts.get("Phone Screen", 0)
    offers = status_counts.get("Offer", 0)

    response_rate = (interviews / applied * 100) if applied > 0 else 0
    offer_rate = (offers / total * 100) if total > 0 else 0

    return {
        "total": total,
        "status_breakdown": status_counts,
        "response_rate": round(response_rate, 1),
        "offer_rate": round(offer_rate, 1),
    }


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new job application."""
    profile = get_user_profile(current_user, db)

    job = JobApplication(
        profile_id=profile.id,
        company=job_data.company,
        position=job_data.position,
        job_description=job_data.job_description,
        status=job_data.status.value,
        application_date=job_data.application_date,
        deadline=job_data.deadline,
        location=job_data.location,
        job_url=job_data.job_url,
        notes=job_data.notes,
        # HR Contact fields
        recruiter_name=job_data.recruiter_name,
        recruiter_email=job_data.recruiter_email,
        recruiter_linkedin=job_data.recruiter_linkedin,
        recruiter_phone=job_data.recruiter_phone,
        # Referral fields
        referral_name=job_data.referral_name,
        referral_relationship=job_data.referral_relationship,
        # Source and response tracking
        application_source=(
            job_data.application_source.value if job_data.application_source else None
        ),
        response_date=job_data.response_date,
        rejection_reason=job_data.rejection_reason,
        # Resume version
        resume_id=job_data.resume_id,
    )
    db.add(job)
    safe_commit(db, "create job application")
    db.refresh(job)

    return job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get a specific job application."""
    profile = get_user_profile(current_user, db)

    job = (
        db.query(JobApplication)
        .filter(JobApplication.id == job_id, JobApplication.profile_id == profile.id)
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a job application."""
    profile = get_user_profile(current_user, db)

    job = (
        db.query(JobApplication)
        .filter(JobApplication.id == job_id, JobApplication.profile_id == profile.id)
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    update_data = job_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(job, field, value.value)
        elif field == "application_source" and value:
            setattr(job, field, value.value)
        else:
            setattr(job, field, value)

    safe_commit(db, "update job application")
    db.refresh(job)

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete a job application."""
    profile = get_user_profile(current_user, db)

    job = (
        db.query(JobApplication)
        .filter(JobApplication.id == job_id, JobApplication.profile_id == profile.id)
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    db.delete(job)
    safe_commit(db, "delete job application")


@router.patch("/{job_id}/status", response_model=JobResponse)
async def update_job_status(
    job_id: int,
    new_status: JobStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Quick status update for a job application."""
    profile = get_user_profile(current_user, db)

    job = (
        db.query(JobApplication)
        .filter(JobApplication.id == job_id, JobApplication.profile_id == profile.id)
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    job.status = new_status.value
    safe_commit(db, "update job status")
    db.refresh(job)

    return job
