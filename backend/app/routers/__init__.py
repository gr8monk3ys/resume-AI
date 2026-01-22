"""
API Routers.
"""

from app.routers import (
    ai,
    analytics,
    auth,
    billing,
    career_journal,
    cover_letters,
    job_alerts,
    job_filters,
    job_import,
    jobs,
    profile,
    resumes,
    scheduler,
    websocket,
)

__all__ = [
    "auth",
    "billing",
    "profile",
    "resumes",
    "jobs",
    "job_alerts",
    "job_filters",
    "job_import",
    "cover_letters",
    "career_journal",
    "ai",
    "analytics",
    "scheduler",
    "websocket",
]
