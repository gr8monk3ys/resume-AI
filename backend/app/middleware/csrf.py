"""
CSRF protection middleware for FastAPI.

Provides double-submit cookie pattern for CSRF protection.
This is defense-in-depth on top of SameSite=Lax cookies and CORS.

How it works:
1. On safe requests (GET, HEAD, OPTIONS, TRACE), a CSRF token cookie is set
   if not already present. The cookie is non-HttpOnly so JavaScript can read it.
2. On state-changing requests (POST, PUT, PATCH, DELETE), the middleware
   validates that the X-CSRF-Token header matches the csrf_token cookie.
3. After a successful state-changing request, the token is rotated to prevent
   replay attacks.
4. Certain paths (login, register, health, docs) are exempt from CSRF checks
   because they either don't modify state or are pre-authentication.

Security properties:
- Uses secrets.compare_digest for constant-time comparison (timing attack safe)
- Uses secrets.token_urlsafe for cryptographically secure token generation
- Token rotation after state-changing requests limits replay window
"""

import secrets
from typing import Callable, Optional, Set

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Default paths exempt from CSRF validation.
# Login and register are exempt because:
# - They are pre-authentication (no session to hijack yet)
# - Login uses form-encoded POST which cannot carry custom headers from CSRF attacks
# - Register creates a new account (no existing session compromise)
DEFAULT_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/webhook",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/",
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection using the double-submit cookie pattern.

    For safe methods (GET, HEAD, OPTIONS):
    - Sets a CSRF token cookie if not already present

    For state-changing methods (POST, PUT, PATCH, DELETE):
    - Validates that X-CSRF-Token header matches the csrf_token cookie
    - Returns 403 if tokens don't match or are missing
    - Rotates the token after successful validation
    """

    def __init__(
        self,
        app,
        exempt_paths: Optional[Set[str]] = None,
        cookie_secure: bool = True,
        cookie_samesite: str = "lax",
        cookie_domain: Optional[str] = None,
        token_length: int = 32,
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths if exempt_paths is not None else DEFAULT_EXEMPT_PATHS
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite
        self.cookie_domain = cookie_domain
        self.token_length = token_length

    def _generate_token(self) -> str:
        """Generate a cryptographically secure CSRF token."""
        return secrets.token_urlsafe(self.token_length)

    def _is_exempt(self, path: str) -> bool:
        """Check if the request path is exempt from CSRF validation."""
        normalized = path.rstrip("/") or "/"
        return normalized in self.exempt_paths

    def _set_csrf_cookie(self, response: Response, token: str) -> None:
        """Set the CSRF token cookie on the response."""
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=token,
            httponly=False,  # Must be readable by JavaScript for header submission
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            domain=self.cookie_domain,
            path="/",
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with CSRF validation."""
        # Skip CSRF for exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # For safe methods, pass through and ensure CSRF cookie exists
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            if CSRF_COOKIE_NAME not in request.cookies:
                token = self._generate_token()
                self._set_csrf_cookie(response, token)
            return response

        # For state-changing methods, validate CSRF token
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "CSRF validation failed",
                    "detail": "Missing CSRF token. Ensure the csrf_token cookie is set "
                    "and the X-CSRF-Token header is included in the request.",
                },
            )

        if not secrets.compare_digest(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "CSRF validation failed",
                    "detail": "CSRF token mismatch. The X-CSRF-Token header does not "
                    "match the csrf_token cookie.",
                },
            )

        # CSRF valid - process request
        response = await call_next(request)

        # Rotate CSRF token after successful state-changing request
        # This limits the window for token replay attacks
        new_token = self._generate_token()
        self._set_csrf_cookie(response, new_token)

        return response
