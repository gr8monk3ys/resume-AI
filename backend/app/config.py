"""
Application configuration using Pydantic Settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "ResuBoost AI"
    app_version: str = "2.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./data/resume_ai.db"

    # JWT Authentication
    secret_key: str = "your-secret-key-change-in-production"
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

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
