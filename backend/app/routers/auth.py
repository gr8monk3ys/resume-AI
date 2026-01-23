"""
Authentication router with brute force protection.

Includes:
- Login attempt tracking
- Account lockout after too many failed attempts
- Audit logging for security events
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.middleware.audit import AuditEventType, get_audit_logger
from app.middleware.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.middleware.security import get_client_ip, get_user_agent
from app.models.profile import Profile
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LockoutStatusResponse(BaseModel):
    """Response model for lockout status check."""

    username: str
    is_locked: bool
    lockout_reason: Optional[str] = None
    recent_failures: int
    max_failures_before_lockout: int
    can_attempt_login: bool
    wait_seconds: int = 0


class PasswordChangeRequest(BaseModel):
    """Request model for password change."""

    current_password: str
    new_password: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
        )

    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create profile for user
    profile = Profile(
        user_id=user.id,
        name=user_data.full_name or user_data.username,
        email=user_data.email,
    )
    db.add(profile)
    db.commit()

    return user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login and get access token.

    Includes brute force protection:
    - Tracks failed login attempts
    - Rate limits login attempts per username
    - Locks account after too many failures
    """
    username = form_data.username
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    request_id = getattr(request.state, "request_id", None)

    # Get audit logger
    audit_logger = get_audit_logger()

    # Check if login is allowed (brute force protection)
    allowed, reason, wait_seconds = audit_logger.check_login_allowed(
        username=username,
        max_recent_failures=settings.auth_max_recent_failures,
        rate_limit_window_minutes=settings.auth_rate_limit_window_minutes,
        lockout_threshold=settings.auth_lockout_threshold,
    )

    if not allowed:
        # Log the blocked attempt
        audit_logger.log_event(
            AuditEventType.LOGIN_FAILED,
            f"Login blocked for {username}: {reason}",
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            details={"reason": reason, "blocked": True},
            success=False,
        )

        if wait_seconds > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reason,
                headers={"Retry-After": str(wait_seconds)},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=reason,
            )

    # Attempt to authenticate
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        # Log failed login
        audit_logger.log_login_failed(
            username=username,
            reason="Invalid username or password",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        # Log failed login due to inactive account
        audit_logger.log_login_failed(
            username=username,
            reason="Account deactivated",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Successful login - log and clear failed attempts
    audit_logger.log_login_success(
        user_id=user.id,
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    token_data = {"sub": user.id, "username": user.username}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    token_data = decode_token(refresh_token)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    # Create new tokens
    new_token_data = {"sub": user.id, "username": user.username}
    new_access_token = create_access_token(new_token_data)
    new_refresh_token = create_refresh_token(new_token_data)

    return Token(
        access_token=new_access_token, refresh_token=new_refresh_token, token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.get("/lockout-status/{username}", response_model=LockoutStatusResponse)
async def check_lockout_status(username: str):
    """
    Check the lockout status for a username.

    Returns information about:
    - Whether the account is locked
    - Number of recent failed attempts
    - Whether login attempts are currently allowed
    """
    audit_logger = get_audit_logger()

    # Check if account is locked
    is_locked, lock_reason = audit_logger.is_account_locked(username)

    # Get recent failure count
    recent_failures = audit_logger.get_recent_failed_attempts(
        username, minutes=settings.auth_rate_limit_window_minutes
    )

    # Check if login is allowed
    allowed, reason, wait_seconds = audit_logger.check_login_allowed(
        username=username,
        max_recent_failures=settings.auth_max_recent_failures,
        rate_limit_window_minutes=settings.auth_rate_limit_window_minutes,
        lockout_threshold=settings.auth_lockout_threshold,
    )

    return LockoutStatusResponse(
        username=username,
        is_locked=is_locked,
        lockout_reason=lock_reason,
        recent_failures=recent_failures,
        max_failures_before_lockout=settings.auth_lockout_threshold,
        can_attempt_login=allowed,
        wait_seconds=wait_seconds,
    )


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change the current user's password.

    Requires the current password for verification.
    """
    ip_address = get_client_ip(request)
    request_id = getattr(request.state, "request_id", None)
    audit_logger = get_audit_logger()

    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        # Log failed password change attempt
        audit_logger.log_event(
            AuditEventType.PASSWORD_CHANGE,
            f"Failed password change attempt for {current_user.username}",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=ip_address,
            request_id=request_id,
            details={"reason": "Invalid current password"},
            success=False,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password (basic validation)
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long",
        )

    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()

    # Log successful password change
    audit_logger.log_password_change(
        user_id=current_user.id,
        username=current_user.username,
        ip_address=ip_address,
        request_id=request_id,
    )

    return {"message": "Password changed successfully"}
