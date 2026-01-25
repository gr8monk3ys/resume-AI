"""
Application configuration using Pydantic Settings.

Provides configuration management with environment variable support.
Settings are cached for performance but can be cleared for testing.
"""

import os
import secrets
import warnings
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Default secret key - ONLY for development/testing
_DEFAULT_SECRET_KEY = "INSECURE-DEFAULT-KEY-CHANGE-IN-PRODUCTION"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "ResuBoost AI"
    app_version: str = "2.0.0"
    debug: bool = False

    # Database - supports both SQLite (dev) and PostgreSQL (prod)
    # SQLite: sqlite:///./data/resume_ai.db
    # PostgreSQL: postgresql://user:password@localhost:5432/resuboost
    # PostgreSQL Async: postgresql+asyncpg://user:password@localhost:5432/resuboost
    database_url: str = "sqlite:///./data/resume_ai.db"

    # PostgreSQL Connection Pool Settings (ignored for SQLite)
    db_pool_size: int = 5  # Number of connections to keep open
    db_max_overflow: int = 10  # Max additional connections beyond pool_size
    db_pool_timeout: int = 30  # Seconds to wait for a connection from pool
    db_pool_recycle: int = 1800  # Recycle connections after 30 minutes
    db_pool_pre_ping: bool = True  # Verify connections before use
    db_echo: bool = False  # Log SQL statements (useful for debugging)

    # JWT Authentication - No default, must be explicitly set or auto-generated
    secret_key: str = _DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Cookie Security Settings
    # HttpOnly cookies prevent JavaScript access (XSS protection)
    cookie_httponly: bool = True
    # Secure cookies only sent over HTTPS
    # Defaults to True (secure by default), set to False only for local development
    # This is computed after initialization based on DEBUG setting if not explicitly set
    cookie_secure: Optional[bool] = None
    # SameSite prevents CSRF attacks: "lax" allows top-level navigation, "strict" is more restrictive
    cookie_samesite: str = "lax"
    # Cookie domain (leave empty for current domain)
    cookie_domain: Optional[str] = None
    # Cookie path
    cookie_path: str = "/"

    # LLM Provider Configuration
    llm_provider: str = "openai"  # openai, anthropic, google, ollama, mock
    llm_request_timeout: int = 60

    # LLM Retry Configuration
    llm_max_retries: int = 3  # Maximum number of retry attempts
    llm_retry_delay: float = 1.0  # Initial delay in seconds before first retry
    llm_retry_max_delay: float = 30.0  # Maximum delay between retries
    llm_retry_exponential_base: float = 2.0  # Base for exponential backoff
    llm_retry_jitter: bool = True  # Add random jitter to prevent thundering herd

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-haiku-20240307"

    # Google
    google_api_key: Optional[str] = None
    google_model: str = "gemini-1.5-flash"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Redis URL for distributed rate limiting (optional)
    # If not set, in-memory rate limiting is used (single instance only)
    # Example: redis://localhost:6379/0 or redis://:password@host:6379/0
    redis_url: Optional[str] = None
    redis_key_prefix: str = "resuboost:rate_limit"
    redis_connection_timeout: int = 5  # seconds
    redis_socket_timeout: int = 5  # seconds

    # Rate limiting - General API
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Rate limiting - Auth endpoints
    auth_rate_limit_requests: int = 5
    auth_rate_limit_window: int = 60  # seconds

    # Rate limiting - AI endpoints
    ai_rate_limit_requests: int = 20
    ai_rate_limit_window: int = 60  # seconds

    # Brute force protection
    auth_max_recent_failures: int = 5
    auth_rate_limit_window_minutes: int = 15
    auth_lockout_threshold: int = 10
    auth_cleanup_days: int = 30

    # File upload limits
    max_file_size_mb: int = 10
    max_resume_length: int = 100000

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Security middleware settings
    enable_rate_limiting: bool = True
    enable_security_headers: bool = True
    enable_input_sanitization: bool = True
    enable_audit_logging: bool = True
    enable_file_audit_logging: bool = False
    audit_database_path: str = "data/audit.db"
    audit_log_file_path: str = "logs/audit.log"

    # Security headers
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year

    # Background scheduler settings
    enable_scheduler: bool = True
    scheduler_default_interval_minutes: int = 60
    scheduler_min_interval_minutes: int = 5
    scheduler_max_interval_minutes: int = 1440  # 24 hours

    # Sentry Error Monitoring
    # Leave SENTRY_DSN empty to disable Sentry (optional integration)
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "development"  # development, staging, production
    sentry_traces_sample_rate: float = 0.1  # 10% of requests traced for performance
    sentry_profiles_sample_rate: float = 0.1  # 10% of traced requests profiled
    sentry_send_default_pii: bool = False  # Don't send PII by default
    sentry_attach_stacktrace: bool = True  # Attach stack traces to messages
    sentry_max_breadcrumbs: int = 100  # Maximum breadcrumbs to capture
    sentry_debug: bool = False  # Enable Sentry SDK debug mode

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Allow environment variables to override .env file
        env_nested_delimiter="__",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Settings are loaded from environment variables and .env file.
    The result is cached for performance.

    To reset settings (e.g., for testing), call clear_settings_cache().
    """
    settings = Settings()

    # Security validation for secret key
    # SECURITY: Only allow auto-generation in explicit TESTING mode, not in debug mode
    # Debug mode should still require explicit SECRET_KEY to prevent accidental exposure
    if settings.secret_key == _DEFAULT_SECRET_KEY:
        if os.getenv("TESTING", "false").lower() == "true":
            # Generate a random key ONLY for automated testing
            warnings.warn(
                "Using auto-generated secret key for testing. "
                "This should only occur in test environments.",
                UserWarning,
                stacklevel=2,
            )
            # Override with a secure random key for this test session
            object.__setattr__(settings, "secret_key", secrets.token_urlsafe(32))
        else:
            raise ValueError(
                "SECURITY ERROR: SECRET_KEY environment variable must be set! "
                "This is required even in debug mode to prevent accidental secret exposure. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

    # SECURITY: cookie_secure defaults based on DEBUG setting if not explicitly set
    # - Production (DEBUG=False): cookie_secure=True (HTTPS-only cookies)
    # - Development (DEBUG=True): cookie_secure=False (allows HTTP for localhost)
    # This ensures cookies are secure by default in production environments
    if settings.cookie_secure is None:
        secure_value = not settings.debug
        object.__setattr__(settings, "cookie_secure", secure_value)
        if not secure_value:
            warnings.warn(
                "cookie_secure is False because DEBUG=True. "
                "Ensure DEBUG=False in production for HTTPS-only cookies.",
                UserWarning,
                stacklevel=2,
            )

    return settings


def clear_settings_cache() -> None:
    """
    Clear the settings cache.

    This is useful for testing when you need to reload settings
    with different environment variables.
    """
    get_settings.cache_clear()
