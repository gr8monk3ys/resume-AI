"""Email notification preferences router."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db, safe_commit
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.email_preferences import EmailPreferencesResponse, EmailPreferencesUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email-preferences", tags=["Email Preferences"])


@router.get("", response_model=EmailPreferencesResponse)
def get_email_preferences(
    current_user: User = Depends(get_current_user),
):
    """Return current email notification preferences."""
    return EmailPreferencesResponse(
        email_notifications=bool(current_user.email_notifications),
        email_nudges=bool(current_user.email_nudges),
        email_weekly_digest=bool(current_user.email_weekly_digest),
        email_reengagement=bool(current_user.email_reengagement),
    )


@router.patch("", response_model=EmailPreferencesResponse)
def update_email_preferences(
    updates: EmailPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update individual email notification toggles."""
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    safe_commit(db, "update email preferences")
    db.refresh(current_user)

    return EmailPreferencesResponse(
        email_notifications=bool(current_user.email_notifications),
        email_nudges=bool(current_user.email_nudges),
        email_weekly_digest=bool(current_user.email_weekly_digest),
        email_reengagement=bool(current_user.email_reengagement),
    )
