"""
Resume schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ResumeCreate(BaseModel):
    """Schema for creating a resume."""

    version_name: str
    content: str


class ResumeUpdate(BaseModel):
    """Schema for updating a resume."""

    version_name: Optional[str] = None
    content: Optional[str] = None


class ResumeResponse(BaseModel):
    """Schema for resume response."""

    id: int
    profile_id: int
    version_name: str
    content: str
    ats_score: Optional[int] = None
    keywords: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ATSAnalysisRequest(BaseModel):
    """Schema for ATS analysis request."""

    resume_content: str
    job_description: Optional[str] = None


class ATSAnalysisResponse(BaseModel):
    """Schema for ATS analysis response."""

    ats_score: int
    suggestions: List[str]
    keyword_matches: List[str]
    missing_keywords: List[str]
    score_breakdown: dict
