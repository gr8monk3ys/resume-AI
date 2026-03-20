"""
Company research schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    """Schema for a checklist item."""

    text: str
    done: bool = False


class CompanyResearchCreate(BaseModel):
    """Schema for creating a company research entry."""

    company_name: str = Field(..., min_length=1, max_length=255)
    talking_points: Optional[List[str]] = None
    notes: Optional[str] = None
    checklist: Optional[List[ChecklistItem]] = None


class CompanyResearchUpdate(BaseModel):
    """Schema for updating a company research entry."""

    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    talking_points: Optional[List[str]] = None
    notes: Optional[str] = None
    checklist: Optional[List[ChecklistItem]] = None


class CompanyResearchResponse(BaseModel):
    """Schema for company research response."""

    id: int
    profile_id: int
    company_name: str
    talking_points: Optional[List[str]] = None
    notes: Optional[str] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_json(cls, entry):
        """Convert ORM object to response with parsed JSON fields."""
        import json

        talking_points_list = None
        if entry.talking_points:
            if entry.talking_points.startswith("["):
                try:
                    talking_points_list = json.loads(entry.talking_points)
                except json.JSONDecodeError:
                    talking_points_list = [t.strip() for t in entry.talking_points.split(",") if t.strip()]
            else:
                talking_points_list = [t.strip() for t in entry.talking_points.split(",") if t.strip()]

        checklist_list = None
        if entry.checklist:
            try:
                checklist_list = json.loads(entry.checklist)
            except json.JSONDecodeError:
                checklist_list = None

        return cls(
            id=entry.id,
            profile_id=entry.profile_id,
            company_name=entry.company_name,
            talking_points=talking_points_list,
            notes=entry.notes,
            checklist=checklist_list,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
