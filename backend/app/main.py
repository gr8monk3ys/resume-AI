"""
FastAPI main application entry point.

Includes security middleware:
- Rate limiting (token bucket algorithm)
- Security headers (XSS protection, HSTS, CSP)
- Request ID tracing
- Input sanitization
- Audit logging
"""

from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db
from app.middleware.audit import AuditMiddleware, init_audit_logger
from app.middleware.rate_limiter import (
    DEFAULT_RATE_LIMITS,
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimitType,
)
from app.middleware.security import (
    InputSanitizationMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    configure_cors,
)
from app.routers import (
    ai,
    analytics,
    auth,
    career_journal,
    cover_letters,
    job_filters,
    job_import,
    jobs,
    profile,
    resumes,
)
from fastapi import FastAPI

settings = get_settings()


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

    yield
    # Shutdown
    pass


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
        block_on_violation=False,  # Log but don't block (defense-in-depth)
    )

# Rate limiting middleware
if settings.enable_rate_limiting:
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


# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(job_filters.router)
app.include_router(job_import.router)
app.include_router(cover_letters.router)
app.include_router(career_journal.router)
app.include_router(ai.router)
app.include_router(analytics.router)


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
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
