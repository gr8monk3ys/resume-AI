"""
Career journal router for tracking achievements and milestones.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db, safe_commit
from app.middleware.auth import get_current_user
from app.models.career_journal import CareerJournalEntry
from app.models.profile import Profile
from app.models.user import User
from app.schemas.career_journal import (
    CareerJournalCreate,
    CareerJournalResponse,
    CareerJournalUpdate,
    EnhanceAchievementRequest,
    EnhanceAchievementResponse,
)

router = APIRouter(prefix="/api/career-journal", tags=["Career Journal"])


def get_user_profile(user: User, db: Session) -> Profile:
    """Get or create user profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, name=user.full_name or user.username)
        db.add(profile)
        safe_commit(db, "create profile")
        db.refresh(profile)
    return profile


def serialize_tags(tags: Optional[List[str]]) -> Optional[str]:
    """Serialize tags list to JSON string for storage."""
    if tags is None:
        return None
    return json.dumps(tags)


def entry_to_response(entry: CareerJournalEntry) -> CareerJournalResponse:
    """Convert database entry to response schema with parsed tags."""
    return CareerJournalResponse.from_orm_with_tags(entry)


@router.get("", response_model=List[CareerJournalResponse])
async def list_entries(
    search: Optional[str] = Query(None, description="Search in title and description"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all career journal entries for current user with optional search/tag filter."""
    profile = get_user_profile(current_user, db)

    query = db.query(CareerJournalEntry).filter(CareerJournalEntry.profile_id == profile.id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (CareerJournalEntry.title.ilike(search_term))
            | (CareerJournalEntry.description.ilike(search_term))
        )

    if tag:
        # Search for tag in JSON or comma-separated format
        tag_pattern = f"%{tag}%"
        query = query.filter(CareerJournalEntry.tags.ilike(tag_pattern))

    entries = query.order_by(CareerJournalEntry.created_at.desc()).all()

    return [entry_to_response(entry) for entry in entries]


@router.post("", response_model=CareerJournalResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry_data: CareerJournalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new career journal entry."""
    profile = get_user_profile(current_user, db)

    entry = CareerJournalEntry(
        profile_id=profile.id,
        title=entry_data.title,
        description=entry_data.description,
        achievement_date=entry_data.achievement_date,
        tags=serialize_tags(entry_data.tags),
    )
    db.add(entry)
    safe_commit(db, "create journal entry")
    db.refresh(entry)

    return entry_to_response(entry)


@router.get("/{entry_id}", response_model=CareerJournalResponse)
async def get_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific career journal entry."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(CareerJournalEntry)
        .filter(
            CareerJournalEntry.id == entry_id,
            CareerJournalEntry.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Career journal entry not found")

    return entry_to_response(entry)


@router.put("/{entry_id}", response_model=CareerJournalResponse)
async def update_entry(
    entry_id: int,
    entry_data: CareerJournalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a career journal entry."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(CareerJournalEntry)
        .filter(
            CareerJournalEntry.id == entry_id,
            CareerJournalEntry.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Career journal entry not found")

    update_data = entry_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "tags" and value is not None:
            setattr(entry, field, serialize_tags(value))
        else:
            setattr(entry, field, value)

    safe_commit(db, "update journal entry")
    db.refresh(entry)

    return entry_to_response(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a career journal entry."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(CareerJournalEntry)
        .filter(
            CareerJournalEntry.id == entry_id,
            CareerJournalEntry.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Career journal entry not found")

    db.delete(entry)
    safe_commit(db, "delete journal entry")


@router.post("/{entry_id}/enhance", response_model=EnhanceAchievementResponse)
async def enhance_achievement(
    entry_id: int,
    request: Optional[EnhanceAchievementRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI-enhance an achievement description to be more impactful."""
    from app.services.llm_service import get_llm_service

    profile = get_user_profile(current_user, db)

    entry = (
        db.query(CareerJournalEntry)
        .filter(
            CareerJournalEntry.id == entry_id,
            CareerJournalEntry.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Career journal entry not found")

    # Use provided text or the entry description
    original_text = (
        request.achievement_text if request and request.achievement_text else entry.description
    )

    try:
        llm_service = get_llm_service()
        enhanced_text = llm_service.enhance_achievement(original_text)

        return EnhanceAchievementResponse(
            original=original_text,
            enhanced=enhanced_text,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enhance achievement: {str(e)}",
        )
