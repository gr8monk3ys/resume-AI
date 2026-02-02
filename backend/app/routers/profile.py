"""
Profile router.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db, safe_commit
from app.middleware.auth import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user's profile."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if not profile:
        # Create profile if it doesn't exist
        profile = Profile(
            user_id=current_user.id,
            name=current_user.full_name or current_user.username,
            email=current_user.email,
        )
        db.add(profile)
        safe_commit(db, "create profile")
        db.refresh(profile)

    return profile


@router.put("", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    # Update fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    safe_commit(db, "update profile")
    db.refresh(profile)

    return profile


@router.get("/stats")
async def get_profile_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get profile statistics."""
    from app.models.career_journal import CareerJournalEntry
    from app.models.cover_letter import CoverLetter
    from app.models.job_application import JobApplication
    from app.models.resume import Resume

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    resume_count = db.query(Resume).filter(Resume.profile_id == profile.id).count()
    cover_letter_count = db.query(CoverLetter).filter(CoverLetter.profile_id == profile.id).count()
    journal_count = (
        db.query(CareerJournalEntry).filter(CareerJournalEntry.profile_id == profile.id).count()
    )

    # Use SQL GROUP BY for job status breakdown instead of loading all jobs into memory
    status_counts_query = (
        db.query(JobApplication.status, func.count(JobApplication.id))
        .filter(JobApplication.profile_id == profile.id)
        .group_by(JobApplication.status)
        .all()
    )
    status_counts = dict(status_counts_query)
    job_count = sum(status_counts.values())

    return {
        "resume_count": resume_count,
        "job_application_count": job_count,
        "cover_letter_count": cover_letter_count,
        "journal_entry_count": journal_count,
        "job_status_breakdown": status_counts,
    }
