"""
Cover letters router.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db, safe_commit
from app.dependencies import get_user_profile
from app.middleware.auth import get_current_user
from app.models.cover_letter import CoverLetter
from app.models.profile import Profile
from app.models.user import User
from app.schemas.cover_letter import CoverLetterCreate, CoverLetterGenerate, CoverLetterResponse

router = APIRouter(prefix="/api/cover-letters", tags=["Cover Letters"])


@router.get("", response_model=List[CoverLetterResponse])
async def list_cover_letters(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all cover letters for current user."""
    profile = get_user_profile(current_user, db)
    cover_letters = (
        db.query(CoverLetter)
        .filter(CoverLetter.profile_id == profile.id)
        .order_by(CoverLetter.updated_at.desc())
        .all()
    )
    return cover_letters


@router.post("", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED)
async def create_cover_letter(
    data: CoverLetterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new cover letter."""
    profile = get_user_profile(current_user, db)

    cover_letter = CoverLetter(
        profile_id=profile.id,
        job_application_id=data.job_application_id,
        content=data.content,
    )
    db.add(cover_letter)
    safe_commit(db, "create cover letter")
    db.refresh(cover_letter)

    return cover_letter


@router.post("/generate", response_model=CoverLetterResponse)
async def generate_cover_letter(
    data: CoverLetterGenerate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a cover letter using AI."""
    from app.services.llm_service import get_llm_service

    profile = get_user_profile(current_user, db)

    # Get LLM service and generate cover letter
    llm_service = get_llm_service()
    generated_content = llm_service.generate_cover_letter(
        resume=data.resume_content,
        job_description=data.job_description,
        company_name=data.company_name,
        position=data.position,
    )

    # Save to database
    cover_letter = CoverLetter(
        profile_id=profile.id,
        content=generated_content,
    )
    db.add(cover_letter)
    safe_commit(db, "generate cover letter")
    db.refresh(cover_letter)

    return cover_letter


@router.get("/{cover_letter_id}", response_model=CoverLetterResponse)
async def get_cover_letter(
    cover_letter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific cover letter."""
    profile = get_user_profile(current_user, db)

    cover_letter = (
        db.query(CoverLetter)
        .filter(CoverLetter.id == cover_letter_id, CoverLetter.profile_id == profile.id)
        .first()
    )

    if not cover_letter:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    return cover_letter


@router.delete("/{cover_letter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cover_letter(
    cover_letter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a cover letter."""
    profile = get_user_profile(current_user, db)

    cover_letter = (
        db.query(CoverLetter)
        .filter(CoverLetter.id == cover_letter_id, CoverLetter.profile_id == profile.id)
        .first()
    )

    if not cover_letter:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    db.delete(cover_letter)
    safe_commit(db, "delete cover letter")
