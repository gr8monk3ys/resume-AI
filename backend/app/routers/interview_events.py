"""
Interview events router for tracking scheduled interviews.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db, safe_commit
from app.dependencies import get_user_profile
from app.middleware.auth import get_current_user
from app.models.interview_event import InterviewEvent
from app.models.user import User
from app.schemas.interview_event import (
    InterviewEventCreate,
    InterviewEventResponse,
    InterviewEventUpdate,
)

router = APIRouter(prefix="/api/interview-events", tags=["Interview Events"])


def serialize_json_list(items: Optional[List[str]]) -> Optional[str]:
    """Serialize list to JSON string for storage."""
    if items is None:
        return None
    return json.dumps(items)


def entry_to_response(entry: InterviewEvent) -> InterviewEventResponse:
    """Convert database entry to response schema with parsed JSON fields."""
    result: InterviewEventResponse = InterviewEventResponse.from_orm_with_json(entry)
    return result


@router.get("", response_model=List[InterviewEventResponse])
def list_events(
    search: Optional[str] = Query(None, description="Search in company and position"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all interview events for current user with optional search/type filter."""
    profile = get_user_profile(current_user, db)

    query = db.query(InterviewEvent).filter(InterviewEvent.profile_id == profile.id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (InterviewEvent.company.ilike(search_term))
            | (InterviewEvent.position.ilike(search_term))
        )

    if event_type:
        query = query.filter(InterviewEvent.event_type == event_type)

    entries = query.order_by(InterviewEvent.scheduled_date.desc()).all()

    return [entry_to_response(entry) for entry in entries]


@router.post("", response_model=InterviewEventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: InterviewEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new interview event."""
    profile = get_user_profile(current_user, db)

    entry = InterviewEvent(
        profile_id=profile.id,
        job_application_id=event_data.job_application_id,
        company=event_data.company,
        position=event_data.position,
        event_type=event_data.event_type,
        scheduled_date=event_data.scheduled_date,
        scheduled_time=event_data.scheduled_time,
        duration_minutes=event_data.duration_minutes,
        location=event_data.location,
        meeting_link=event_data.meeting_link,
        interviewer_names=serialize_json_list(event_data.interviewer_names),
        notes=event_data.notes,
        is_completed=event_data.is_completed,
        follow_up_date=event_data.follow_up_date,
        follow_up_done=event_data.follow_up_done,
    )
    db.add(entry)
    safe_commit(db, "create interview event")
    db.refresh(entry)

    return entry_to_response(entry)


@router.get("/{event_id}", response_model=InterviewEventResponse)
def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific interview event."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(InterviewEvent)
        .filter(
            InterviewEvent.id == event_id,
            InterviewEvent.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Interview event not found")

    return entry_to_response(entry)


@router.put("/{event_id}", response_model=InterviewEventResponse)
def update_event(
    event_id: int,
    event_data: InterviewEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an interview event."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(InterviewEvent)
        .filter(
            InterviewEvent.id == event_id,
            InterviewEvent.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Interview event not found")

    update_data = event_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "interviewer_names" and value is not None:
            setattr(entry, field, serialize_json_list(value))
        else:
            setattr(entry, field, value)

    safe_commit(db, "update interview event")
    db.refresh(entry)

    return entry_to_response(entry)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an interview event."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(InterviewEvent)
        .filter(
            InterviewEvent.id == event_id,
            InterviewEvent.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Interview event not found")

    db.delete(entry)
    safe_commit(db, "delete interview event")
