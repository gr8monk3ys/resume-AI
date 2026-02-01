"""
Authentication router with brute force protection.

Includes:
- Login attempt tracking
- Account lockout after too many failed attempts
- Audit logging for security events
"""

import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from app.config import get_settings


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength with complexity requirements.

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, 'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)'

    # Check for common weak patterns
    common_patterns = ["password", "123456", "qwerty", "admin", "letmein"]
    password_lower = password.lower()
    for pattern in common_patterns:
        if pattern in password_lower:
            return False, f"Password contains a common weak pattern: {pattern}"

    return True, ""


from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

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


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Set HTTP-only authentication cookies with security flags.

    Security considerations:
    - HttpOnly: Prevents JavaScript access (XSS protection)
    - Secure: Only sent over HTTPS (enabled in production)
    - SameSite=Lax: Prevents CSRF while allowing top-level navigation
    - Path restrictions: access_token for API, refresh_token only for refresh endpoint
    """
    # Access token cookie - used for API requests
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path=settings.cookie_path,
        domain=settings.cookie_domain,
    )

    # Refresh token cookie - only accessible at refresh endpoint for security
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/auth",  # Restrict refresh token to auth endpoints only
        domain=settings.cookie_domain,
    )


def clear_auth_cookies(response: Response) -> None:
    """
    Clear authentication cookies by setting them to expire immediately.
    """
    response.delete_cookie(
        key="access_token",
        path=settings.cookie_path,
        domain=settings.cookie_domain,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        domain=settings.cookie_domain,
    )


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
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login and get access token.

    Sets HTTP-only cookies for browser-based authentication while also returning
    tokens in the response body for backward compatibility with API clients.

    Includes brute force protection:
    - Tracks failed login attempts
    - Rate limits login attempts per username
    - Locks account after too many failures

    Security:
    - Tokens are set as HTTP-only cookies (prevents XSS token theft)
    - Secure flag enabled in production (HTTPS only)
    - SameSite=Lax prevents CSRF attacks
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
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Create tokens with token_version for invalidation support
    # Note: 'sub' must be a string per JWT spec (jose library enforces this)
    token_data = {"sub": str(user.id), "username": user.username}
    access_token = create_access_token(token_data, token_version=user.token_version)
    refresh_token = create_refresh_token(token_data, token_version=user.token_version)

    # Set HTTP-only cookies for browser-based authentication
    set_auth_cookies(response, access_token, refresh_token)

    # Also return tokens in body for backward compatibility with API clients
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


class RefreshTokenRequest(BaseModel):
    """Request model for refresh token - used when token is passed in body."""

    refresh_token: Optional[str] = None


@router.post("/refresh", response_model=Token)
async def refresh_tokens(
    request: Request,
    response: Response,
    body: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Accepts refresh token from:
    1. HTTP-only cookie (preferred for browser clients)
    2. Request body (for API clients without cookie support)

    Sets new HTTP-only cookies on successful refresh.

    Security validations:
        - Token must be a valid refresh token (not an access token)
        - Token version must match user's current token_version
    """
    # Try to get refresh token from cookie first, then from body
    refresh_token_value = request.cookies.get("refresh_token")
    if not refresh_token_value and body and body.refresh_token:
        refresh_token_value = body.refresh_token

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not provided",
        )

    # Decode with expected_type="refresh" to prevent access tokens from being used
    token_data = decode_token(refresh_token_value, expected_type="refresh", validate_type=True)

    if token_data is None:
        # Clear cookies on invalid token
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    # Validate token version to ensure refresh token hasn't been invalidated
    if token_data.token_version != user.token_version:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been invalidated. Please log in again.",
        )

    # Create new tokens with current token_version
    # Note: 'sub' must be a string per JWT spec (jose library enforces this)
    new_token_data = {"sub": str(user.id), "username": user.username}
    new_access_token = create_access_token(new_token_data, token_version=user.token_version)
    new_refresh_token = create_refresh_token(new_token_data, token_version=user.token_version)

    # Set new HTTP-only cookies
    set_auth_cookies(response, new_access_token, new_refresh_token)

    return Token(
        access_token=new_access_token, refresh_token=new_refresh_token, token_type="bearer"
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Logout and clear authentication cookies.

    This endpoint:
    1. Clears HTTP-only authentication cookies
    2. Returns success even if not authenticated (idempotent)

    Note: This does not invalidate the JWT tokens themselves.
    For full session invalidation, use the password change endpoint
    which increments token_version.
    """
    ip_address = get_client_ip(request)
    request_id = getattr(request.state, "request_id", None)

    # Log logout event if user was authenticated
    if current_user:
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            AuditEventType.LOGOUT,
            f"User {current_user.username} logged out",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=ip_address,
            request_id=request_id,
            success=True,
        )

    # Clear authentication cookies
    clear_auth_cookies(response)

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.get("/lockout-status/{username}", response_model=LockoutStatusResponse)
async def check_lockout_status(
    username: str,
    current_user: User = Depends(get_current_user),
):
    """
    Check the lockout status for a username.

    Requires authentication to prevent username enumeration.
    Users can only check their own status unless they are admins.

    Returns information about:
    - Whether the account is locked
    - Number of recent failed attempts
    - Whether login attempts are currently allowed
    """
    # Security: Only allow users to check their own status (or admin can check any)
    if current_user.username != username and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check your own lockout status",
        )

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

    # Validate new password with complexity requirements
    is_valid, error_message = validate_password_strength(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    # Update password and increment token_version to invalidate all existing tokens
    # This forces all sessions to re-authenticate after a password change
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()

    # Log successful password change
    audit_logger.log_password_change(
        user_id=current_user.id,
        username=current_user.username,
        ip_address=ip_address,
        request_id=request_id,
    )

    return {
        "message": "Password changed successfully. All existing sessions have been invalidated."
    }
