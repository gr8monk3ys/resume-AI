"""
Clerk JWT authentication middleware.

Verifies Clerk-issued JWTs using JWKS (JSON Web Key Set) for signature validation.
Supports both:
1. __session cookie (Clerk's default cookie name for browser clients)
2. Authorization: Bearer <token> header (for API clients)

User records are auto-provisioned on first authentication if they do not yet
exist in the local database (just-in-time provisioning).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import jwt as pyjwt
from cachetools import TTLCache
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

settings = get_settings()

# Bearer token scheme - optional so we can fall back to cookies
bearer_scheme = HTTPBearer(auto_error=False)

# Cache for Clerk JWKS keys (1-hour TTL)
_jwks_cache: TTLCache = TTLCache(maxsize=4, ttl=3600)

# Cache key constant
_JWKS_CACHE_KEY = "clerk_jwks_client"


def _get_clerk_issuer() -> str:
    """
    Derive the Clerk issuer URL from the publishable key or secret key.

    Clerk publishable keys follow the format: pk_test_<base64-encoded-instance>.
    The issuer is https://<instance-slug>.clerk.accounts.dev for dev
    or https://<custom-domain> for production.

    Falls back to constructing from CLERK_SECRET_KEY if publishable key is not set.
    """
    publishable_key = getattr(settings, "clerk_publishable_key", None) or ""

    if publishable_key.startswith("pk_"):
        # Extract the instance identifier from the publishable key.
        # Clerk publishable keys embed the frontend API domain in base64 after the prefix.
        import base64

        try:
            # Strip prefix like "pk_test_" or "pk_live_"
            parts = publishable_key.split("_", 2)
            if len(parts) == 3:
                encoded = parts[2]
                # Add padding if necessary
                padding = 4 - len(encoded) % 4
                if padding != 4:
                    encoded += "=" * padding
                decoded = base64.b64decode(encoded).decode("utf-8").rstrip("$")
                return f"https://{decoded}"
        except Exception:
            logger.warning("Failed to decode Clerk publishable key, using fallback issuer.")

    # Fallback: if CLERK_INSTANCE_ID or similar is set, use it
    clerk_instance = getattr(settings, "clerk_instance_id", None)
    if clerk_instance:
        return f"https://{clerk_instance}.clerk.accounts.dev"

    # Last resort: do not enforce issuer validation
    return ""


def _get_jwks_url() -> str:
    """
    Build the Clerk JWKS endpoint URL.

    Uses the issuer URL derived from the publishable key, or falls back to
    the Clerk Frontend API URL pattern.
    """
    issuer = _get_clerk_issuer()
    if issuer:
        return f"{issuer}/.well-known/jwks.json"

    # Fallback if we cannot determine the issuer
    # Clerk's JWKS can also be fetched from the Backend API
    return ""


def _get_jwks_client() -> Optional[PyJWKClient]:
    """
    Get or create a cached PyJWKClient for Clerk's JWKS endpoint.

    The client is cached for 1 hour to avoid repeated HTTP requests.
    Returns None if the JWKS URL cannot be determined.
    """
    cached = _jwks_cache.get(_JWKS_CACHE_KEY)
    if cached is not None:
        return cached

    jwks_url = _get_jwks_url()
    if not jwks_url:
        return None

    try:
        client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        _jwks_cache[_JWKS_CACHE_KEY] = client
        return client
    except Exception as e:
        logger.error("Failed to create JWKS client for Clerk: %s", e)
        return None


def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a Clerk-issued JWT.

    Attempts verification in the following order:
    1. JWKS-based RS256 verification (preferred, fetches public keys from Clerk)
    2. Fallback to CLERK_SECRET_KEY HS256 verification if JWKS is unavailable

    Args:
        token: The raw JWT string from the request.

    Returns:
        The decoded JWT payload dictionary containing at minimum:
        - sub: The Clerk user ID (e.g., "user_2abc123")
        - iat, exp: Issued-at and expiration timestamps

    Raises:
        HTTPException 401: If the token is invalid, expired, or verification fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Attempt 1: JWKS-based verification (RS256)
    jwks_client = _get_jwks_client()
    if jwks_client is not None:
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            issuer = _get_clerk_issuer()

            decode_options = {}
            decode_kwargs: Dict[str, Any] = {
                "jwt": token,
                "key": signing_key.key,
                "algorithms": ["RS256"],
                "options": decode_options,
            }

            # Only validate issuer if we know it
            if issuer:
                decode_kwargs["issuer"] = issuer

            payload = pyjwt.decode(**decode_kwargs)

            if not payload.get("sub"):
                raise credentials_exception

            return payload

        except pyjwt.ExpiredSignatureError:
            logger.debug("Clerk JWT has expired (JWKS verification).")
            raise credentials_exception
        except pyjwt.InvalidTokenError as e:
            logger.debug("Clerk JWT invalid (JWKS verification): %s", e)
            # Fall through to secret key verification
        except PyJWKClientError as e:
            logger.warning("JWKS client error, falling back to secret key: %s", e)
            # Fall through to secret key verification

    # Attempt 2: Fallback to CLERK_SECRET_KEY (HS256)
    clerk_secret = getattr(settings, "clerk_secret_key", None) or ""
    if not clerk_secret:
        logger.error(
            "No JWKS available and CLERK_SECRET_KEY is not configured. "
            "Cannot verify Clerk tokens."
        )
        raise credentials_exception

    try:
        # Clerk secret keys start with "sk_" -- use the PEM key if available,
        # otherwise use the raw secret for HS256 verification.
        payload = pyjwt.decode(
            token,
            clerk_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

        if not payload.get("sub"):
            raise credentials_exception

        return payload

    except pyjwt.ExpiredSignatureError:
        logger.debug("Clerk JWT has expired (secret key verification).")
        raise credentials_exception
    except pyjwt.InvalidTokenError as e:
        logger.debug("Clerk JWT invalid (secret key verification): %s", e)
        raise credentials_exception


def get_token_from_request(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """
    Extract the Clerk session token from the request.

    Priority order:
    1. __session cookie (Clerk's default browser cookie)
    2. Authorization: Bearer header (for API clients)

    Args:
        request: The FastAPI request object.
        bearer: Credentials extracted by HTTPBearer dependency (if present).

    Returns:
        The JWT token string, or None if not found.
    """
    # Clerk sets session tokens in a cookie named __session
    cookie_token = request.cookies.get("__session")
    if cookie_token:
        return cookie_token

    # Fallback to Authorization header
    if bearer and bearer.credentials:
        return bearer.credentials

    # Also check raw Authorization header in case HTTPBearer didn't parse it
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


async def get_current_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from a Clerk JWT.

    Extracts the token from the __session cookie or Authorization header,
    verifies it against Clerk's JWKS, then looks up or auto-creates the
    corresponding local User record.

    Just-in-time provisioning:
        If a valid Clerk token is presented but no local User record exists,
        a basic user record is created automatically. The Clerk webhook
        (user.created) will fill in additional details asynchronously.

    Raises:
        HTTPException 401: If no valid token is present.
        HTTPException 403: If the user account is deactivated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = get_token_from_request(request, bearer)
    if not token:
        raise credentials_exception

    # Verify the Clerk-issued JWT
    payload = verify_clerk_token(token)
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise credentials_exception

    # Look up the user by clerk_id
    user = db.query(User).filter(User.clerk_id == clerk_user_id).first()

    if user is None:
        # Just-in-time provisioning: create a basic user record.
        # The webhook handler will update with full profile data later.
        email = payload.get("email", f"{clerk_user_id}@clerk.placeholder")
        username = payload.get("username") or clerk_user_id

        # Check if username or email already exists (from a different auth method)
        existing_by_email = db.query(User).filter(User.email == email).first()
        if existing_by_email:
            # Link existing user to Clerk
            existing_by_email.clerk_id = clerk_user_id
            db.commit()
            db.refresh(existing_by_email)
            user = existing_by_email
        else:
            # Ensure username uniqueness
            base_username = username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User(
                clerk_id=clerk_user_id,
                username=username,
                email=email,
                full_name=payload.get("name"),
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(
                "Auto-provisioned local user record for Clerk user %s (local id=%d)",
                clerk_user_id,
                user.id,
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.commit()

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
