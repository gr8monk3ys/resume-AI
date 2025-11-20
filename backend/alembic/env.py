"""
Alembic migration environment configuration.

This file configures how Alembic runs migrations. It imports the application
models and database configuration to enable autogenerate support and
proper database URL handling.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the backend directory to the Python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database Base and all models for autogenerate support
from app.database import Base

# Import all models to ensure they are registered with Base.metadata
# This is required for Alembic autogenerate to detect model changes
from app.models import (
    CareerJournalEntry,
    CoverLetter,
    JobApplication,
    Profile,
    Resume,
    User,
    CompanyFilter,
    KeywordFilter,
    ApplicationQuestion,
)
from app.models.job_alert import JobAlert

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


def get_url() -> str:
    """
    Get database URL from environment or config.

    Priority:
    1. DATABASE_URL environment variable
    2. alembic.ini sqlalchemy.url setting

    This allows overriding the URL for different environments
    (development, staging, production) without modifying files.
    """
    # Try to get from environment first
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    # Try to import from app config (if available)
    try:
        from app.config import get_settings

        settings = get_settings()
        return settings.database_url
    except (ImportError, ValueError):
        # Settings may require SECRET_KEY which might not be set during migrations
        # Fall back to alembic.ini setting
        pass

    # Fall back to alembic.ini
    return config.get_main_option("sqlalchemy.url")


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for autogenerate support
# This is the MetaData object from our SQLAlchemy Base class
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Enable batch mode for SQLite ALTER TABLE support
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override the sqlalchemy.url with our computed URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Enable batch mode for SQLite ALTER TABLE support
            # This is required because SQLite has limited ALTER TABLE support
            # and Alembic uses batch mode to work around these limitations
            render_as_batch=True,
            # Compare types to detect column type changes
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
