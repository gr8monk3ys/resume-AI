"""
Career journal schemas.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CareerJournalCreate(BaseModel):
    """Schema for creating a career journal entry."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    achievement_date: Optional[date] = None
    tags: Optional[List[str]] = None


class CareerJournalUpdate(BaseModel):
    """Schema for updating a career journal entry."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    achievement_date: Optional[date] = None
    tags: Optional[List[str]] = None


class CareerJournalResponse(BaseModel):
    """Schema for career journal entry response."""

    id: int
    profile_id: int
    title: str
    description: str
    achievement_date: Optional[date] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_tags(cls, entry):
        """Convert ORM object to response with parsed tags."""
        tags_list = None
        if entry.tags:
            # Parse comma-separated or JSON tags
            if entry.tags.startswith("["):
                import json

                try:
                    tags_list = json.loads(entry.tags)
                except json.JSONDecodeError:
                    tags_list = [t.strip() for t in entry.tags.split(",") if t.strip()]
            else:
                tags_list = [t.strip() for t in entry.tags.split(",") if t.strip()]

        return cls(
            id=entry.id,
            profile_id=entry.profile_id,
            title=entry.title,
            description=entry.description,
            achievement_date=entry.achievement_date,
            tags=tags_list,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )


class EnhanceAchievementRequest(BaseModel):
    """Schema for achievement enhancement request."""

    achievement_text: Optional[str] = None


class EnhanceAchievementResponse(BaseModel):
    """Schema for achievement enhancement response."""

    original: str
    enhanced: str
