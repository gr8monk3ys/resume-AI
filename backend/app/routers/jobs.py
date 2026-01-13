"""
Jobs router for job application tracking.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.models.job_application import JobApplication
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobStatus
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def get_user_profile(user: User, db: Session) -> Profile:
    """Get or create user profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, name=user.full_name or user.username)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all job applications for current user."""
    profile = get_user_profile(current_user, db)

    query = db.query(JobApplication).filter(JobApplication.profile_id == profile.id)

    if status_filter:
        query = query.filter(JobApplication.status == status_filter.value)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (JobApplication.company.ilike(search_term)) |
            (JobApplication.position.ilike(search_term))
        )

    jobs = query.order_by(JobApplication.updated_at.desc()).all()
    return jobs


@router.get("/stats")
async def get_job_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job application statistics."""
    profile = get_user_profile(current_user, db)

    jobs = db.query(JobApplication).filter(JobApplication.profile_id == profile.id).all()

    # Status breakdown
    status_counts = {}
    for job in jobs:
        status_counts[job.status] = status_counts.get(job.status, 0) + 1

    # Calculate response rate (interviews / applications)
    total = len(jobs)
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
    db: Session = Depends(get_db)
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
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific job application."""
    profile = get_user_profile(current_user, db)

    job = db.query(JobApplication).filter(
        JobApplication.id == job_id,
        JobApplication.profile_id == profile.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a job application."""
    profile = get_user_profile(current_user, db)

    job = db.query(JobApplication).filter(
        JobApplication.id == job_id,
        JobApplication.profile_id == profile.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    update_data = job_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(job, field, value.value)
        else:
            setattr(job, field, value)

    db.commit()
    db.refresh(job)

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a job application."""
    profile = get_user_profile(current_user, db)

    job = db.query(JobApplication).filter(
        JobApplication.id == job_id,
        JobApplication.profile_id == profile.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    db.delete(job)
    db.commit()


@router.patch("/{job_id}/status", response_model=JobResponse)
async def update_job_status(
    job_id: int,
    new_status: JobStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Quick status update for a job application."""
    profile = get_user_profile(current_user, db)

    job = db.query(JobApplication).filter(
        JobApplication.id == job_id,
        JobApplication.profile_id == profile.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")

    job.status = new_status.value
    db.commit()
    db.refresh(job)

    return job
