"""Pydantic schemas for the nudge system."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NudgeItem(BaseModel):
    nudge_type: str  # stale_followup, interview_prep, overdue_followup, thank_you, application_velocity, resume_freshness
    entity_type: str  # job, interview_event, resume, metric
    entity_id: int | None = None
    company: str | None = None
    position: str | None = None
    title: str
    description: str
    color: str  # hex color
    days_ago: int | None = None
    scheduled_date: str | None = None
    recruiter_name: str | None = None
    recruiter_email: str | None = None


class NudgeResponse(BaseModel):
    nudges: list[NudgeItem]
    generated_at: datetime


class DraftRequest(BaseModel):
    nudge_type: str
    entity_id: int | None = None
    entity_type: str
    company: str | None = None
    position: str | None = None
    recruiter_name: str | None = None
    additional_context: str | None = None


class DraftResponse(BaseModel):
    content: str
    subject: str | None = None
    tips: list[str]
