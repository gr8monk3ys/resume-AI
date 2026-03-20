"""
STAR stories router for tracking behavioral interview stories.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db, safe_commit
from app.dependencies import get_user_profile
from app.middleware.auth import get_current_user
from app.models.star_story import StarStory
from app.models.user import User
from app.schemas.star_story import (
    StarStoryCreate,
    StarStoryResponse,
    StarStoryUpdate,
)

router = APIRouter(prefix="/api/star-stories", tags=["STAR Stories"])


def serialize_tags(tags: Optional[List[str]]) -> Optional[str]:
    """Serialize tags list to JSON string for storage."""
    if tags is None:
        return None
    return json.dumps(tags)


def entry_to_response(entry: StarStory) -> StarStoryResponse:
    """Convert database entry to response schema with parsed tags."""
    return StarStoryResponse.from_orm_with_tags(entry)


@router.get("", response_model=List[StarStoryResponse])
def list_stories(
    search: Optional[str] = Query(None, description="Search in title and STAR fields"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all STAR stories for current user with optional search/tag filter."""
    profile = get_user_profile(current_user, db)

    query = db.query(StarStory).filter(StarStory.profile_id == profile.id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (StarStory.title.ilike(search_term))
            | (StarStory.situation.ilike(search_term))
            | (StarStory.task.ilike(search_term))
            | (StarStory.action.ilike(search_term))
            | (StarStory.result.ilike(search_term))
        )

    if tag:
        tag_pattern = f"%{tag}%"
        query = query.filter(StarStory.tags.ilike(tag_pattern))

    entries = query.order_by(StarStory.created_at.desc()).all()

    return [entry_to_response(entry) for entry in entries]


@router.post("", response_model=StarStoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(
    story_data: StarStoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new STAR story."""
    profile = get_user_profile(current_user, db)

    entry = StarStory(
        profile_id=profile.id,
        title=story_data.title,
        situation=story_data.situation,
        task=story_data.task,
        action=story_data.action,
        result=story_data.result,
        tags=serialize_tags(story_data.tags),
    )
    db.add(entry)
    safe_commit(db, "create STAR story")
    db.refresh(entry)

    return entry_to_response(entry)


@router.get("/{story_id}", response_model=StarStoryResponse)
def get_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific STAR story."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(StarStory)
        .filter(
            StarStory.id == story_id,
            StarStory.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="STAR story not found")

    return entry_to_response(entry)


@router.put("/{story_id}", response_model=StarStoryResponse)
def update_story(
    story_id: int,
    story_data: StarStoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a STAR story."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(StarStory)
        .filter(
            StarStory.id == story_id,
            StarStory.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="STAR story not found")

    update_data = story_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "tags" and value is not None:
            setattr(entry, field, serialize_tags(value))
        else:
            setattr(entry, field, value)

    safe_commit(db, "update STAR story")
    db.refresh(entry)

    return entry_to_response(entry)


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a STAR story."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(StarStory)
        .filter(
            StarStory.id == story_id,
            StarStory.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="STAR story not found")

    db.delete(entry)
    safe_commit(db, "delete STAR story")
