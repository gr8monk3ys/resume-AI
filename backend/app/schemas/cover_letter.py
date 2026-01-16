"""
Cover letter schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CoverLetterCreate(BaseModel):
    """Schema for creating a cover letter."""

    job_application_id: Optional[int] = None
    content: str


class CoverLetterGenerate(BaseModel):
    """Schema for generating a cover letter with AI."""

    resume_content: str
    job_description: str
    company_name: str
    position: str
    tone: Optional[str] = "professional"  # professional, enthusiastic, formal


class CoverLetterResponse(BaseModel):
    """Schema for cover letter response."""

    id: int
    profile_id: int
    job_application_id: Optional[int] = None
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
