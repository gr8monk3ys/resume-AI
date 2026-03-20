"""Pydantic schemas for email notification preferences."""

from pydantic import BaseModel


class EmailPreferencesResponse(BaseModel):
    email_notifications: bool
    email_nudges: bool
    email_weekly_digest: bool
    email_reengagement: bool


class EmailPreferencesUpdate(BaseModel):
    email_notifications: bool | None = None
    email_nudges: bool | None = None
    email_weekly_digest: bool | None = None
    email_reengagement: bool | None = None
