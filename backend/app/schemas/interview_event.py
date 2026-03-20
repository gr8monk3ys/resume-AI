"""
Interview event schemas.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class InterviewEventCreate(BaseModel):
    """Schema for creating an interview event."""

    job_application_id: Optional[int] = None
    company: str = Field(..., min_length=1, max_length=255)
    position: str = Field(..., min_length=1, max_length=255)
    event_type: str = Field(..., min_length=1, max_length=100)
    scheduled_date: str = Field(..., min_length=1)
    scheduled_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    interviewer_names: Optional[List[str]] = None
    notes: Optional[str] = None
    is_completed: Optional[bool] = False
    follow_up_date: Optional[str] = None
    follow_up_done: Optional[bool] = False


class InterviewEventUpdate(BaseModel):
    """Schema for updating an interview event."""

    job_application_id: Optional[int] = None
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    position: Optional[str] = Field(None, min_length=1, max_length=255)
    event_type: Optional[str] = Field(None, min_length=1, max_length=100)
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    interviewer_names: Optional[List[str]] = None
    notes: Optional[str] = None
    is_completed: Optional[bool] = None
    follow_up_date: Optional[str] = None
    follow_up_done: Optional[bool] = None


class InterviewEventResponse(BaseModel):
    """Schema for interview event response."""

    id: int
    profile_id: int
    job_application_id: Optional[int] = None
    company: str
    position: str
    event_type: str
    scheduled_date: str
    scheduled_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    interviewer_names: Optional[List[str]] = None
    notes: Optional[str] = None
    is_completed: bool
    follow_up_date: Optional[str] = None
    follow_up_done: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_json(cls, entry):
        """Convert ORM object to response with parsed interviewer_names."""
        names_list = None
        if entry.interviewer_names:
            if entry.interviewer_names.startswith("["):
                import json

                try:
                    names_list = json.loads(entry.interviewer_names)
                except json.JSONDecodeError:
                    names_list = [n.strip() for n in entry.interviewer_names.split(",") if n.strip()]
            else:
                names_list = [n.strip() for n in entry.interviewer_names.split(",") if n.strip()]

        return cls(
            id=entry.id,
            profile_id=entry.profile_id,
            job_application_id=entry.job_application_id,
            company=entry.company,
            position=entry.position,
            event_type=entry.event_type,
            scheduled_date=entry.scheduled_date,
            scheduled_time=entry.scheduled_time,
            duration_minutes=entry.duration_minutes,
            location=entry.location,
            meeting_link=entry.meeting_link,
            interviewer_names=names_list,
            notes=entry.notes,
            is_completed=entry.is_completed,
            follow_up_date=entry.follow_up_date,
            follow_up_done=entry.follow_up_done,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
