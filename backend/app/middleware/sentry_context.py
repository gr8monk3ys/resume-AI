"""
Sentry user context middleware.

Attaches authenticated user information to Sentry events for better debugging.
Only attaches user_id (not PII like email) by default for privacy.
"""

import logging
from typing import Optional

import sentry_sdk
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings
from app.middleware.auth import decode_token, get_token_from_request

logger = logging.getLogger(__name__)

settings = get_settings()


class SentryUserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to attach user context to Sentry events.

    Extracts user information from JWT token and sets it as Sentry user context.
    This helps with debugging by showing which user experienced an error.

    Privacy considerations:
    - Only user_id and username are attached by default
    - Email and other PII are not included unless SENTRY_SEND_DEFAULT_PII=True
    - User data is only attached if authentication is successful
    """

    def __init__(
        self,
        app,
        include_username: bool = True,
        include_ip_address: bool = False,
    ):
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            include_username: Whether to include username in Sentry context
            include_ip_address: Whether to include IP address (privacy consideration)
        """
        super().__init__(app)
        self.include_username = include_username
        self.include_ip_address = include_ip_address

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and attach user context to Sentry.

        Attempts to extract user information from the JWT token and
        set it as Sentry user context for error tracking.
        """
        # Clear any previous user context
        sentry_sdk.set_user(None)

        # Try to extract user info from token
        user_context = self._extract_user_context(request)

        if user_context:
            sentry_sdk.set_user(user_context)

            # Add request ID if available (for correlation)
            request_id = request.headers.get("X-Request-ID")
            if request_id:
                sentry_sdk.set_tag("request_id", request_id)

        try:
            response = await call_next(request)
            return response
        finally:
            # Clear user context after request to prevent leakage
            sentry_sdk.set_user(None)

    def _extract_user_context(self, request: Request) -> Optional[dict]:
        """
        Extract user context from request JWT token.

        Returns:
            dict with user context if authenticated, None otherwise
        """
        try:
            # Get token from cookie or header
            token = get_token_from_request(request)
            if not token:
                return None

            # Decode token without hitting the database
            token_data = decode_token(token, expected_type="access", validate_type=True)
            if not token_data or not token_data.user_id:
                return None

            # Build user context
            user_context = {
                "id": str(token_data.user_id),
            }

            # Optionally include username
            if self.include_username and token_data.username:
                user_context["username"] = token_data.username

            # Optionally include IP address (consider privacy implications)
            if self.include_ip_address:
                client_ip = self._get_client_ip(request)
                if client_ip:
                    user_context["ip_address"] = client_ip

            return user_context

        except Exception as e:
            # Don't let user context extraction break the request
            logger.debug(f"Failed to extract user context for Sentry: {e}")
            return None

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Get client IP address from request, handling proxies.

        Checks X-Forwarded-For header first for proxied requests,
        then falls back to direct client IP.
        """
        # Check for forwarded IP (when behind a proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return None


def set_sentry_user_context(user_id: int, username: Optional[str] = None) -> None:
    """
    Manually set Sentry user context.

    Utility function for setting user context outside of middleware,
    for example in background tasks or WebSocket handlers.

    Args:
        user_id: The user's database ID
        username: Optional username
    """
    user_context = {"id": str(user_id)}
    if username:
        user_context["username"] = username
    sentry_sdk.set_user(user_context)


def clear_sentry_user_context() -> None:
    """Clear the current Sentry user context."""
    sentry_sdk.set_user(None)


def add_sentry_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: Optional[dict] = None,
) -> None:
    """
    Add a breadcrumb to the current Sentry scope.

    Breadcrumbs are trail of events that happened before an error,
    helping with debugging.

    Args:
        message: Description of the event
        category: Category for grouping (e.g., "auth", "database", "api")
        level: Severity level ("debug", "info", "warning", "error", "critical")
        data: Optional additional data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )
