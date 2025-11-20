"""
STAR story schemas.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StarStoryCreate(BaseModel):
    """Schema for creating a STAR story."""

    title: str = Field(..., min_length=1, max_length=255)
    situation: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    tags: Optional[List[str]] = None


class StarStoryUpdate(BaseModel):
    """Schema for updating a STAR story."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    situation: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    tags: Optional[List[str]] = None


class StarStoryResponse(BaseModel):
    """Schema for STAR story response."""

    id: int
    profile_id: int
    title: str
    situation: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
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
            situation=entry.situation,
            task=entry.task,
            action=entry.action,
            result=entry.result,
            tags=tags_list,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
