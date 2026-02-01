"""
JWT Authentication middleware and utilities.

Supports both:
1. HTTP-only cookie-based authentication (preferred for browser clients)
2. Bearer token authentication (for API clients)

Cookie-based auth provides XSS protection by preventing JavaScript access to tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenData
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme - used for Authorization header fallback
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None, token_version: int = 0
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Token payload data (must include 'sub' for user_id)
        expires_delta: Optional custom expiration time
        token_version: User's current token version for invalidation support

    Returns:
        Encoded JWT access token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access", "token_version": token_version})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict, token_version: int = 0) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Token payload data (must include 'sub' for user_id)
        token_version: User's current token version for invalidation support

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh", "token_version": token_version})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(
    token: str, expected_type: str = "access", validate_type: bool = True
) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode
        expected_type: Expected token type ("access" or "refresh")
        validate_type: Whether to validate the token type claim

    Returns:
        TokenData if valid, None if invalid

    Security:
        - Validates token signature and expiration
        - Validates token type to prevent refresh tokens from being used as access tokens
        - Extracts token_version for invalidation checking
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        # 'sub' is stored as string per JWT spec, convert to int for user_id
        sub = payload.get("sub")
        user_id: int = int(sub) if sub is not None else None
        username: str = payload.get("username")
        token_type: str = payload.get("type")
        token_version: int = payload.get("token_version", 0)

        if user_id is None:
            return None

        # Validate token type to prevent token confusion attacks
        # This prevents refresh tokens from being used for API authentication
        if validate_type and token_type != expected_type:
            return None

        return TokenData(
            user_id=user_id,
            username=username,
            token_type=token_type,
            token_version=token_version,
        )
    except JWTError:
        return None


def get_token_from_request(request: Request, bearer_token: Optional[str] = None) -> Optional[str]:
    """
    Extract access token from request.

    Priority order (for security, prefer cookies for browser requests):
    1. HTTP-only cookie (preferred - prevents XSS token theft)
    2. Authorization Bearer header (fallback for API clients)

    Args:
        request: The FastAPI request object
        bearer_token: Token from OAuth2PasswordBearer dependency (Authorization header)

    Returns:
        The access token string or None if not found
    """
    # First, try to get token from HTTP-only cookie (most secure for browsers)
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    # Fall back to Authorization header for API clients
    if bearer_token:
        return bearer_token

    return None


async def get_current_user(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token.

    Supports both cookie-based and header-based authentication:
    1. HTTP-only cookie (preferred for browser clients - XSS protection)
    2. Authorization Bearer header (for API clients)

    Security validations:
        - Token signature and expiration
        - Token type must be "access" (rejects refresh tokens)
        - Token version must match user's current token_version (for invalidation)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Get token from cookie or header
    token = get_token_from_request(request, bearer_token)
    if not token:
        raise credentials_exception

    # Decode token with type validation (must be access token, not refresh)
    token_data = decode_token(token, expected_type="access", validate_type=True)
    if token_data is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Validate token version to ensure token hasn't been invalidated
    # This catches tokens issued before a password change
    if token_data.token_version != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify they are active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify they are an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user
