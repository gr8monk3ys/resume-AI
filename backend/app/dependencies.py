"""
Shared FastAPI dependencies for the application.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db, safe_commit
from app.middleware.auth import get_current_user
from app.models.profile import Profile
from app.models.user import User


def get_user_profile(user: User, db: Session) -> Profile:
    """Get or create user profile.

    Args:
        user: The authenticated user
        db: Database session

    Returns:
        The user's profile, creating one if it doesn't exist
    """
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(
            user_id=user.id,
            name=user.full_name or user.username,
            email=user.email,
        )
        db.add(profile)
        safe_commit(db, "create profile")
        db.refresh(profile)
    return profile


def get_current_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    """FastAPI dependency that returns the current user's profile.

    This is a convenience dependency that combines authentication
    and profile retrieval into a single dependency.

    Args:
        current_user: The authenticated user (from get_current_user)
        db: Database session

    Returns:
        The current user's profile

    Example:
        @router.get("/items")
        async def get_items(profile: Profile = Depends(get_current_profile)):
            return db.query(Item).filter(Item.profile_id == profile.id).all()
    """
    return get_user_profile(current_user, db)
