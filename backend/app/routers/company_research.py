"""
Company research router for tracking interview preparation notes.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, safe_commit
from app.dependencies import get_user_profile
from app.middleware.auth import get_current_user
from app.middleware.feature_gate import get_user_subscription, is_pro_user
from app.models.company_research import CompanyResearch
from app.models.user import User
from app.schemas.company_research import (
    CompanyResearchCreate,
    CompanyResearchResponse,
    CompanyResearchUpdate,
)

router = APIRouter(prefix="/api/company-research", tags=["Company Research"])


def serialize_json_list(items: Optional[List[str]]) -> Optional[str]:
    """Serialize list to JSON string for storage."""
    if items is None:
        return None
    return json.dumps(items)


def serialize_checklist(items) -> Optional[str]:
    """Serialize checklist items to JSON string for storage."""
    if items is None:
        return None
    return json.dumps([item.model_dump() for item in items])


def entry_to_response(entry: CompanyResearch) -> CompanyResearchResponse:
    """Convert database entry to response schema with parsed JSON fields."""
    return CompanyResearchResponse.from_orm_with_json(entry)


@router.get("", response_model=List[CompanyResearchResponse])
def list_research(
    search: Optional[str] = Query(None, description="Search in company name and notes"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all company research entries for current user with optional search."""
    profile = get_user_profile(current_user, db)

    query = db.query(CompanyResearch).filter(CompanyResearch.profile_id == profile.id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (CompanyResearch.company_name.ilike(search_term))
            | (CompanyResearch.notes.ilike(search_term))
        )

    entries = query.order_by(CompanyResearch.created_at.desc()).all()

    return [entry_to_response(entry) for entry in entries]


@router.post("", response_model=CompanyResearchResponse, status_code=status.HTTP_201_CREATED)
def create_research(
    research_data: CompanyResearchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new company research entry."""
    profile = get_user_profile(current_user, db)

    settings = get_settings()
    if settings.enable_billing:
        sub = get_user_subscription(db, current_user.id)
        if not is_pro_user(sub):
            research_count = (
                db.query(CompanyResearch)
                .filter(
                    CompanyResearch.profile_id == profile.id,
                )
                .count()
            )
            if research_count >= 3:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "free_tier_limit_reached",
                        "feature": "company_research",
                        "limit": 3,
                        "period": "total",
                        "used": research_count,
                        "message": (
                            "You have reached the limit of 3 company research entries on the free tier. "
                            "Upgrade to Pro for unlimited company research."
                        ),
                    },
                )

    entry = CompanyResearch(
        profile_id=profile.id,
        company_name=research_data.company_name,
        talking_points=serialize_json_list(research_data.talking_points),
        notes=research_data.notes,
        checklist=serialize_checklist(research_data.checklist),
    )
    db.add(entry)
    safe_commit(db, "create company research")
    db.refresh(entry)

    return entry_to_response(entry)


@router.get("/{research_id}", response_model=CompanyResearchResponse)
def get_research(
    research_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific company research entry."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(CompanyResearch)
        .filter(
            CompanyResearch.id == research_id,
            CompanyResearch.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Company research entry not found")

    return entry_to_response(entry)


@router.put("/{research_id}", response_model=CompanyResearchResponse)
def update_research(
    research_id: int,
    research_data: CompanyResearchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a company research entry."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(CompanyResearch)
        .filter(
            CompanyResearch.id == research_id,
            CompanyResearch.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Company research entry not found")

    update_data = research_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "talking_points" and value is not None:
            setattr(entry, field, serialize_json_list(value))
        elif field == "checklist" and value is not None:
            # Checklist items come as dicts from model_dump
            setattr(entry, field, json.dumps(value))
        else:
            setattr(entry, field, value)

    safe_commit(db, "update company research")
    db.refresh(entry)

    return entry_to_response(entry)


@router.delete("/{research_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_research(
    research_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a company research entry."""
    profile = get_user_profile(current_user, db)

    entry = (
        db.query(CompanyResearch)
        .filter(
            CompanyResearch.id == research_id,
            CompanyResearch.profile_id == profile.id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Company research entry not found")

    db.delete(entry)
    safe_commit(db, "delete company research")
