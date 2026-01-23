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

    # Database
    database_url: str = "sqlite:///./data/resume_ai.db"

    # JWT Authentication - No default, must be explicitly set or auto-generated
    secret_key: str = _DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # LLM Provider Configuration
    llm_provider: str = "openai"  # openai, anthropic, google, ollama, mock
    llm_request_timeout: int = 60

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
    if settings.secret_key == _DEFAULT_SECRET_KEY:
        if settings.debug or os.getenv("TESTING", "false").lower() == "true":
            # Generate a random key for development/testing if not set
            warnings.warn(
                "Using auto-generated secret key for development. "
                "Set SECRET_KEY environment variable for production!",
                UserWarning,
                stacklevel=2,
            )
            # Override with a secure random key for this session
            object.__setattr__(settings, "secret_key", secrets.token_urlsafe(32))
        else:
            raise ValueError(
                "SECURITY ERROR: SECRET_KEY environment variable must be set in production! "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

    return settings


def clear_settings_cache() -> None:
    """
    Clear the settings cache.

    This is useful for testing when you need to reload settings
    with different environment variables.
    """
    get_settings.cache_clear()
