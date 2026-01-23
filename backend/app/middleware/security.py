"""
Security middleware for FastAPI.

Provides:
- Input sanitization middleware
- XSS protection headers
- Security headers (HSTS, CSP, etc.)
- CORS configuration
- Request ID middleware for tracing
"""

import html
import re
import uuid
from typing import Callable, Dict, List, Optional, Set

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Request ID header name
REQUEST_ID_HEADER = "X-Request-ID"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy (configurable)
    - Strict-Transport-Security (for HTTPS)
    - Permissions-Policy
    """

    def __init__(
        self,
        app,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        content_security_policy: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.custom_headers = custom_headers or {}

        # Default CSP for API (restrictive)
        self.csp = content_security_policy or "default-src 'none'; frame-ancestors 'none'"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)

        # XSS Protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp

        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # HSTS (only for HTTPS)
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            )

        # Cache control for API responses
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        # Add custom headers
        for header_name, header_value in self.custom_headers.items():
            response.headers[header_name] = header_value

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID to each request.

    The request ID is:
    - Generated if not provided in the request headers
    - Added to request.state for use in logging
    - Included in the response headers
    """

    def __init__(self, app, header_name: str = REQUEST_ID_HEADER):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request and response."""
        # Get or generate request ID
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Validate request ID format (prevent header injection)
        if not self._is_valid_request_id(request_id):
            request_id = str(uuid.uuid4())

        # Store in request state for logging
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers[self.header_name] = request_id

        return response

    @staticmethod
    def _is_valid_request_id(request_id: str) -> bool:
        """Validate request ID format."""
        # Allow UUIDs and common request ID formats
        # Max length 64, alphanumeric with dashes
        if len(request_id) > 64:
            return False
        return bool(re.match(r"^[a-zA-Z0-9\-_]+$", request_id))


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to sanitize potentially dangerous input.

    Note: This is defense-in-depth. Primary validation should happen
    in Pydantic models and endpoint handlers.

    Sanitizes:
    - Query parameters
    - Headers (specific dangerous patterns)
    - Request path (prevent path traversal)
    """

    # Patterns that indicate potential attacks
    DANGEROUS_PATTERNS = [
        r"<script",  # XSS
        r"javascript:",  # XSS
        r"onerror\s*=",  # XSS
        r"onload\s*=",  # XSS
        r"onclick\s*=",  # XSS
        r"eval\s*\(",  # Code injection
        r"expression\s*\(",  # IE expression
        r"\.\.\/",  # Path traversal
        r"\.\.\\",  # Path traversal (Windows)
        r";\s*--",  # SQL comment
        r"'\s*or\s*'",  # SQL injection
        r'"\s*or\s*"',  # SQL injection
        r"union\s+select",  # SQL injection
        r"<iframe",  # HTML injection
    ]

    def __init__(
        self,
        app,
        enabled: bool = True,
        log_violations: bool = True,
        block_on_violation: bool = False,
        skip_paths: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.log_violations = log_violations
        self.block_on_violation = block_on_violation
        self.skip_paths = skip_paths or {"/health", "/docs", "/openapi.json"}
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request for dangerous patterns."""
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        if path in self.skip_paths:
            return await call_next(request)

        violations = []

        # Check path for traversal attempts
        if ".." in path or "\\" in path:
            violations.append(f"Path traversal attempt in URL: {path[:100]}")

        # Check query parameters
        for key, value in request.query_params.items():
            if self._contains_dangerous_pattern(value):
                violations.append(f"Dangerous pattern in query param '{key}'")

        # Check specific headers
        dangerous_headers = ["referer", "origin", "x-forwarded-host"]
        for header_name in dangerous_headers:
            header_value = request.headers.get(header_name, "")
            if self._contains_dangerous_pattern(header_value):
                violations.append(f"Dangerous pattern in header '{header_name}'")

        if violations:
            # Log violations
            if self.log_violations:
                request_id = getattr(request.state, "request_id", "unknown")
                client_ip = self._get_client_ip(request)
                print(
                    f"[SECURITY] Input validation violations - "
                    f"request_id={request_id}, ip={client_ip}, "
                    f"path={path}, violations={violations}"
                )

            # Optionally block the request
            if self.block_on_violation:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid request",
                        "detail": "Request blocked by security filter",
                    },
                )

            # Store violations in request state for audit logging
            request.state.security_violations = violations

        return await call_next(request)

    def _contains_dangerous_pattern(self, value: str) -> bool:
        """Check if a string contains dangerous patterns."""
        if not value:
            return False

        for pattern in self._compiled_patterns:
            if pattern.search(value):
                return True
        return False

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Get client IP address."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


def sanitize_string(text: str, max_length: int = 1000, escape_html: bool = True) -> str:
    """
    Sanitize a string for safe storage/display.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        escape_html: Whether to escape HTML characters

    Returns:
        Sanitized string
    """
    if not text:
        return ""

    # Limit length
    text = text[:max_length]

    # Remove null bytes
    text = text.replace("\x00", "")

    # Escape HTML if requested
    if escape_html:
        text = html.escape(text, quote=True)

    # Strip whitespace
    text = text.strip()

    return text


def escape_html_string(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text
    """
    return html.escape(text, quote=True)


def strip_html_tags(text: str) -> str:
    """
    Strip HTML tags from text.

    Note: For security, prefer escape_html_string() over stripping.

    Args:
        text: Text containing HTML tags

    Returns:
        Text with HTML tags removed
    """
    if not text:
        return ""

    # Decode HTML entities first
    text = html.unescape(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"<[^>]*$", "", text)  # Handle unclosed tags

    return text.strip()


def configure_cors(
    app,
    origins: Optional[List[str]] = None,
    allow_credentials: bool = True,
    allow_methods: Optional[List[str]] = None,
    allow_headers: Optional[List[str]] = None,
    expose_headers: Optional[List[str]] = None,
    max_age: int = 600,
):
    """
    Configure CORS middleware with security best practices.

    Args:
        app: FastAPI application instance
        origins: List of allowed origins (default: localhost only)
        allow_credentials: Whether to allow credentials
        allow_methods: Allowed HTTP methods
        allow_headers: Allowed request headers
        expose_headers: Headers to expose to the browser
        max_age: How long the results of a preflight request can be cached
    """
    # Default to restrictive origins
    if origins is None:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Default allowed methods
    if allow_methods is None:
        allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

    # Default allowed headers
    if allow_headers is None:
        allow_headers = [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Requested-With",
        ]

    # Default exposed headers
    if expose_headers is None:
        expose_headers = [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        expose_headers=expose_headers,
        max_age=max_age,
    )


def get_client_ip(request: Request) -> str:
    """
    Get the client IP address from a request.

    Handles X-Forwarded-For header for reverse proxy setups.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address string
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Get the first (client) IP in the chain
        return forwarded.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def get_user_agent(request: Request) -> str:
    """
    Get the User-Agent from a request.

    Args:
        request: FastAPI request object

    Returns:
        User-Agent string or "unknown"
    """
    return request.headers.get("User-Agent", "unknown")[:500]  # Limit length


# Export all security utilities
__all__ = [
    "SecurityHeadersMiddleware",
    "RequestIDMiddleware",
    "InputSanitizationMiddleware",
    "sanitize_string",
    "escape_html_string",
    "strip_html_tags",
    "configure_cors",
    "get_client_ip",
    "get_user_agent",
    "REQUEST_ID_HEADER",
]
