"""
Shared FastAPI dependencies for common operations.

These dependencies reduce code duplication and ensure consistent behavior
across routers.
"""

from typing import Tuple

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.profile import Profile
from app.models.user import User
from fastapi import Depends
from sqlalchemy.orm import Session


async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    """
    Get or create user profile for the current user.

    This is a shared dependency that ensures users always have a profile.
    Uses a single database query and creates a profile if one doesn't exist.

    Returns:
        Profile: The user's profile (existing or newly created)
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if not profile:
        profile = Profile(
            user_id=current_user.id,
            name=current_user.full_name or current_user.username,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile


async def get_user_with_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tuple[User, Profile]:
    """
    Get current user along with their profile.

    Useful when you need both the user and profile in a single endpoint.

    Returns:
        Tuple of (User, Profile)
    """
    profile = await get_user_profile(current_user, db)
    return current_user, profile
