"""
Alembic environment configuration for ResuBoost AI.

This module configures Alembic to work with the application's
SQLAlchemy models and database settings.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, event, pool

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the application's Base and models
from app.database import Base

# Import all models to ensure they are registered with Base.metadata
# This is critical for autogenerate to work correctly
from app.models.career_journal import CareerJournalEntry
from app.models.cover_letter import CoverLetter
from app.models.job_alert import JobAlert
from app.models.job_application import JobApplication
from app.models.job_filters import ApplicationQuestion, CompanyFilter, KeywordFilter
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User

# This is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Get the database URL from environment or settings.

    Priority:
    1. DATABASE_URL environment variable
    2. App settings (from .env file)
    3. Default SQLite database
    """
    # Try environment variable first
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Try to load from app settings
    try:
        # Set TESTING or DEBUG to avoid secret key validation issues during migrations
        if not os.getenv("SECRET_KEY"):
            os.environ["TESTING"] = "true"

        from app.config import get_settings

        settings = get_settings()
        return settings.database_url
    except Exception:
        pass

    # Default fallback
    return "sqlite:///./data/resume_ai.db"


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare types for more accurate autogenerate
        compare_type=True,
        # Render NULL/NOT NULL changes
        compare_server_default=True,
        # Include schema for PostgreSQL
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    url = get_database_url()

    # Handle SQLite-specific configuration
    if url.startswith("sqlite"):
        connectable = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=pool.StaticPool,
        )

        # Enable foreign keys for SQLite
        @event.listens_for(connectable, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        # PostgreSQL or other databases
        connectable = create_engine(
            url,
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare types for more accurate autogenerate
            compare_type=True,
            # Render NULL/NOT NULL changes
            compare_server_default=True,
            # Include schema for PostgreSQL
            include_schemas=True,
            # Batch mode for SQLite (required for some operations)
            render_as_batch=url.startswith("sqlite"),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
