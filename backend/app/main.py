"""
FastAPI main application entry point.

Includes security middleware:
- Rate limiting (token bucket algorithm)
- Security headers (XSS protection, HSTS, CSP)
- Request ID tracing
- Input sanitization
- Audit logging
- Sentry error monitoring (optional)

Background services:
- Job scheduler for automated job scraping
"""

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.config import get_settings
from app.database import init_db
from app.middleware.audit import AuditMiddleware, init_audit_logger
from app.middleware.rate_limiter import (
    DEFAULT_RATE_LIMITS,
    RateLimitConfig,
    RateLimiterDependency,
    RateLimitMiddleware,
    RateLimitType,
    create_rate_limit_storage,
)
from app.middleware.security import (
    InputSanitizationMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    configure_cors,
)
from app.middleware.sentry_context import SentryUserContextMiddleware
from app.routers import (
    ai,
    analytics,
    auth,
    career_journal,
    cover_letters,
    job_alerts,
    job_filters,
    job_import,
    jobs,
    profile,
    resumes,
    scheduler,
    websocket,
)
from app.services.scheduler import get_job_scheduler

logger = logging.getLogger(__name__)

settings = get_settings()


def _filter_sensitive_data(event, hint):
    """
    Filter sensitive data from Sentry events before sending.

    Removes passwords, tokens, API keys, and other sensitive information
    from request bodies, headers, and other event data.
    """
    # List of sensitive field names to redact
    sensitive_fields = {
        "password",
        "new_password",
        "current_password",
        "confirm_password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "secret",
        "secret_key",
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
    }

    def redact_dict(data):
        """Recursively redact sensitive fields from a dictionary."""
        if not isinstance(data, dict):
            return data
        redacted = {}
        for key, value in data.items():
            lower_key = key.lower() if isinstance(key, str) else key
            if lower_key in sensitive_fields:
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    redact_dict(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                redacted[key] = value
        return redacted

    # Redact request data
    if "request" in event:
        request = event["request"]
        if "data" in request and isinstance(request["data"], dict):
            request["data"] = redact_dict(request["data"])
        if "headers" in request and isinstance(request["headers"], dict):
            request["headers"] = redact_dict(request["headers"])
        if "cookies" in request:
            request["cookies"] = "[REDACTED]"

    # Redact extra context
    if "extra" in event and isinstance(event["extra"], dict):
        event["extra"] = redact_dict(event["extra"])

    # Redact breadcrumb data
    if "breadcrumbs" in event and isinstance(event["breadcrumbs"], dict):
        values = event["breadcrumbs"].get("values", [])
        for breadcrumb in values:
            if "data" in breadcrumb and isinstance(breadcrumb["data"], dict):
                breadcrumb["data"] = redact_dict(breadcrumb["data"])

    return event


def init_sentry():
    """
    Initialize Sentry error monitoring if configured.

    Only initializes if SENTRY_DSN is set. Configures:
    - FastAPI and Starlette integrations for request tracing
    - SQLAlchemy integration for database query tracing
    - Sensitive data filtering
    - Performance monitoring with configurable sample rates
    """
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not configured, error monitoring disabled")
        return False

    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            release=f"{settings.app_name}@{settings.app_version}",
            # Performance Monitoring
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            # Privacy and Security
            send_default_pii=settings.sentry_send_default_pii,
            before_send=_filter_sensitive_data,
            # Behavior
            attach_stacktrace=settings.sentry_attach_stacktrace,
            max_breadcrumbs=settings.sentry_max_breadcrumbs,
            debug=settings.sentry_debug,
            # Integrations
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            # Enable tracing for slow endpoint detection
            enable_tracing=True,
        )
        logger.info(
            f"Sentry initialized for environment '{settings.sentry_environment}' "
            f"with {settings.sentry_traces_sample_rate * 100}% trace sampling"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


# Initialize Sentry before creating the FastAPI app
sentry_enabled = init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    init_db()

    # Initialize audit logger with settings
    if settings.enable_audit_logging:
        init_audit_logger(
            database_path=settings.audit_database_path,
            enable_file_logging=settings.enable_file_audit_logging,
            log_file_path=settings.audit_log_file_path,
        )

    # Start the job scheduler for background scraping tasks
    if settings.enable_scheduler:
        try:
            job_scheduler = get_job_scheduler()
            job_scheduler.start()
            logger.info("Job scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start job scheduler: {e}")

    yield

    # Shutdown
    # Stop the job scheduler gracefully
    if settings.enable_scheduler:
        try:
            job_scheduler = get_job_scheduler()
            job_scheduler.stop()
            logger.info("Job scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping job scheduler: {e}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered job search toolkit API",
    lifespan=lifespan,
)

# Configure CORS with security best practices
# Note: CORS middleware should be added first (outermost)
configure_cors(
    app,
    origins=settings.cors_origins,
    allow_credentials=True,
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ],
)

# Request ID middleware (for tracing)
# Should be early in the chain so other middleware can use it
app.add_middleware(RequestIDMiddleware)

# Security headers middleware
if settings.enable_security_headers:
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=settings.enable_hsts,
        hsts_max_age=settings.hsts_max_age,
    )

# Input sanitization middleware
if settings.enable_input_sanitization:
    app.add_middleware(
        InputSanitizationMiddleware,
        enabled=True,
        log_violations=True,
        block_on_violation=True,  # Block requests with malicious input patterns
    )

# Rate limiting middleware
if settings.enable_rate_limiting:
    # Create rate limit storage (Redis if configured, otherwise in-memory)
    rate_limit_storage = create_rate_limit_storage(
        redis_url=settings.redis_url,
        key_prefix=settings.redis_key_prefix,
        connection_timeout=settings.redis_connection_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )

    # Initialize RateLimiterDependency with the same storage backend
    RateLimiterDependency.initialize_storage(
        redis_url=settings.redis_url,
        key_prefix=f"{settings.redis_key_prefix}:dep",
        connection_timeout=settings.redis_connection_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )

    # Configure rate limits from settings
    rate_limits = {
        RateLimitType.AUTH: RateLimitConfig(
            max_requests=settings.auth_rate_limit_requests,
            window_seconds=settings.auth_rate_limit_window,
        ),
        RateLimitType.AI: RateLimitConfig(
            max_requests=settings.ai_rate_limit_requests,
            window_seconds=settings.ai_rate_limit_window,
        ),
        RateLimitType.GENERAL: RateLimitConfig(
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window,
        ),
    }
    app.add_middleware(
        RateLimitMiddleware,
        storage=rate_limit_storage,
        rate_limits=rate_limits,
        enabled=True,
    )

# Audit logging middleware
if settings.enable_audit_logging:
    app.add_middleware(
        AuditMiddleware,
        log_all_requests=False,  # Only log specific paths and errors
        log_paths={
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/api/profile",
        },
    )

# Sentry user context middleware - attaches user info to error reports
# Should be added after authentication-related middleware
if sentry_enabled:
    app.add_middleware(
        SentryUserContextMiddleware,
        include_username=True,
        include_ip_address=False,  # Privacy: don't include IP by default
    )


# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(job_alerts.router)
app.include_router(job_filters.router)
app.include_router(job_import.router)
app.include_router(cover_letters.router)
app.include_router(career_journal.router)
app.include_router(ai.router)
app.include_router(analytics.router)
app.include_router(scheduler.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "sentry_enabled": sentry_enabled}


# Debug endpoints - only available when DEBUG=True
if settings.debug:

    @app.get("/api/debug/sentry-test")
    async def sentry_test():
        """
        Test endpoint to verify Sentry error reporting is working.

        Only available in debug mode. Raises an intentional error
        that should appear in Sentry dashboard if configured correctly.

        Returns:
            Never returns - always raises an exception
        """
        if not sentry_enabled:
            raise HTTPException(
                status_code=503,
                detail="Sentry is not configured. Set SENTRY_DSN environment variable.",
            )

        # Add extra context for debugging
        sentry_sdk.set_context(
            "debug_test",
            {
                "purpose": "Testing Sentry integration",
                "environment": settings.sentry_environment,
                "triggered_by": "Manual test via /api/debug/sentry-test",
            },
        )

        # Capture a message before the error
        sentry_sdk.capture_message("Sentry test triggered - error will follow", level="info")

        # Raise a test error
        raise RuntimeError(
            "This is a test error from /api/debug/sentry-test. "
            "If you see this in Sentry, the integration is working correctly!"
        )

    @app.get("/api/debug/sentry-status")
    async def sentry_status():
        """
        Check Sentry configuration status without triggering an error.

        Only available in debug mode.

        Returns:
            dict: Sentry configuration status
        """
        return {
            "sentry_enabled": sentry_enabled,
            "sentry_dsn_configured": bool(settings.sentry_dsn),
            "environment": settings.sentry_environment,
            "traces_sample_rate": settings.sentry_traces_sample_rate,
            "profiles_sample_rate": settings.sentry_profiles_sample_rate,
            "release": f"{settings.app_name}@{settings.app_version}",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
