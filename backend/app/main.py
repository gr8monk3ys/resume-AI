"""
FastAPI main application entry point.

Includes security middleware:
- Rate limiting (token bucket algorithm)
- Security headers (XSS protection, HSTS, CSP)
- Request ID tracing
- Input sanitization
- Audit logging

Background services:
- Job scheduler for automated job scraping
"""

import logging
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
from fastapi import FastAPI

logger = logging.getLogger(__name__)

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

    # Start the job scheduler for background scraping tasks
    if settings.enable_scheduler:
        try:
            job_scheduler = get_job_scheduler()
            job_scheduler.start()
            logger.info("Job scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start job scheduler: {e}")

    yield

    # Shutdown - graceful cleanup
    logger.info("Starting graceful shutdown...")

    # Stop the job scheduler gracefully
    if settings.enable_scheduler:
        try:
            job_scheduler = get_job_scheduler()
            job_scheduler.stop()
            logger.info("Job scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping job scheduler: {e}")

    # Close database connections gracefully
    try:
        from app.database import engine

        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

    # Close audit logger connections
    if settings.enable_audit_logging:
        try:
            audit_logger = get_audit_logger()
            if hasattr(audit_logger, "close"):
                audit_logger.close()
            logger.info("Audit logger closed")
        except Exception as e:
            logger.error(f"Error closing audit logger: {e}")

    logger.info("Graceful shutdown complete")


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
async def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check endpoint.

    Checks:
    - Database connectivity
    - LLM service availability (if configured)
    - Scheduler status (if enabled)

    Returns:
        Health status with component-level details
    """
    from sqlalchemy import text

    checks = {}
    all_healthy = True

    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False

    # Check LLM service (only if configured)
    try:
        from app.services.llm_service import get_llm_service

        llm = get_llm_service()
        provider = getattr(llm, "provider_name", "unknown")
        checks["llm"] = {"status": "configured", "provider": provider}
    except Exception as e:
        checks["llm"] = {"status": "not_configured", "message": str(e)}

    # Check scheduler (only if enabled)
    if settings.enable_scheduler:
        try:
            from app.services.scheduler import get_job_scheduler

            scheduler = get_job_scheduler()
            is_running = scheduler.running if hasattr(scheduler, "running") else False
            checks["scheduler"] = {
                "status": "running" if is_running else "stopped",
            }
        except Exception as e:
            checks["scheduler"] = {"status": "error", "message": str(e)}
    else:
        checks["scheduler"] = {"status": "disabled"}

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": settings.app_version,
        "checks": checks,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
