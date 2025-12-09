"""
Security and rate limiting middleware for FastAPI.

This package provides:
- Rate limiting with token bucket algorithm
- Security headers (XSS, HSTS, CSP)
- Request ID tracing
- Input sanitization
- Audit logging for security events
- Brute force protection for authentication
"""

from app.middleware.audit import (
    AuditEventType,
    AuditLogger,
    AuditMiddleware,
    get_audit_logger,
    init_audit_logger,
)
from app.middleware.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_user,
    get_current_admin_user,
    get_current_user,
    get_password_hash,
    verify_password,
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
    # Auth
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_active_user",
    "get_current_admin_user",
    "get_current_user",
    "get_password_hash",
    "verify_password",
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
]
