"""
API Routers.
"""

from app.routers import (
    ai,
    analytics,
    auth,
    career_journal,
    cover_letters,
    job_filters,
    job_import,
    jobs,
    profile,
    resumes,
)

__all__ = [
    "auth",
    "profile",
    "resumes",
    "jobs",
    "job_filters",
    "job_import",
    "cover_letters",
    "career_journal",
    "ai",
    "analytics",
]
