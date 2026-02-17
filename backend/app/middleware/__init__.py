"""
Security and rate limiting middleware for FastAPI.

This package provides:
- CSRF protection (double-submit cookie pattern)
- Rate limiting with token bucket algorithm
- Security headers (XSS, HSTS, CSP)
- Request ID tracing
- Input sanitization
- Audit logging for security events
- Brute force protection for authentication
- Prometheus-compatible metrics collection
"""

from app.middleware.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    CSRFMiddleware,
)
from app.middleware.metrics import (
    MetricsCollector,
    MetricsMiddleware,
    get_metrics,
)
from app.middleware.audit import (
    AuditEventType,
    AuditLogger,
    AuditMiddleware,
    get_audit_logger,
    init_audit_logger,
)
from app.middleware.auth import (
    get_current_active_user,
    get_current_admin_user,
    get_current_user,
    get_token_from_request,
    verify_clerk_token,
)
from app.middleware.rate_limiter import (
    DEFAULT_RATE_LIMITS,
    RateLimitConfig,
    RateLimiterDependency,
    RateLimitMiddleware,
    RateLimitType,
    ai_rate_limit,
    auth_rate_limit,
    file_upload_rate_limit,
    rate_limit,
)
from app.middleware.security import (
    InputSanitizationMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    configure_cors,
    escape_html_string,
    get_client_ip,
    get_user_agent,
    sanitize_string,
    strip_html_tags,
)

__all__ = [
    # CSRF
    "CSRF_COOKIE_NAME",
    "CSRF_HEADER_NAME",
    "CSRFMiddleware",
    # Auth (Clerk-based)
    "get_current_active_user",
    "get_current_admin_user",
    "get_current_user",
    "get_token_from_request",
    "verify_clerk_token",
    # Rate limiting
    "DEFAULT_RATE_LIMITS",
    "RateLimitConfig",
    "RateLimiterDependency",
    "RateLimitMiddleware",
    "RateLimitType",
    "ai_rate_limit",
    "auth_rate_limit",
    "file_upload_rate_limit",
    "rate_limit",
    # Security
    "InputSanitizationMiddleware",
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
    "configure_cors",
    "escape_html_string",
    "get_client_ip",
    "get_user_agent",
    "sanitize_string",
    "strip_html_tags",
    # Audit
    "AuditEventType",
    "AuditLogger",
    "AuditMiddleware",
    "get_audit_logger",
    "init_audit_logger",
    # Metrics
    "MetricsCollector",
    "MetricsMiddleware",
    "get_metrics",
]
