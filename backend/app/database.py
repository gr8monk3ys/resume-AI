"""
Database configuration and session management.

Supports both SQLite (development) and PostgreSQL (production).
PostgreSQL includes connection pooling and async support for enterprise scale.
"""

import os
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator

import logging

from fastapi import HTTPException, status
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

logger = logging.getLogger(__name__)

from app.config import get_settings

settings = get_settings()


def _is_sqlite() -> bool:
    """Check if using SQLite database."""
    return settings.database_url.startswith("sqlite")


def _is_postgres() -> bool:
    """Check if using PostgreSQL database."""
    return "postgresql" in settings.database_url


def _get_async_url() -> str:
    """Convert sync database URL to async URL for PostgreSQL."""
    url = settings.database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url


# Ensure data directory exists for SQLite file databases
if _is_sqlite() and ":memory:" not in settings.database_url:
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


# =============================================================================
# SYNC ENGINE (for backward compatibility and migrations)
# =============================================================================

if _is_sqlite():
    # SQLite configuration
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.db_echo,
    )

    # Enable foreign keys and WAL mode for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

elif _is_postgres():
    # PostgreSQL configuration with connection pooling
    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=settings.db_pool_pre_ping,
        echo=settings.db_echo,
    )
else:
    # Generic database configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.db_echo,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# ASYNC ENGINE (for PostgreSQL high-performance operations)
# =============================================================================

async_engine = None
AsyncSessionLocal = None

if _is_postgres():
    # Note: Async engines use AsyncAdaptedQueuePool by default when no poolclass is specified
    # Explicitly using NullPool for simplicity in containerized environments
    async_engine = create_async_engine(
        _get_async_url(),
        poolclass=NullPool,
        echo=settings.db_echo,
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# =============================================================================
# BASE MODEL
# =============================================================================


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting synchronous database session.

    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def safe_commit(db: Session, operation: str = "operation") -> None:
    """
    Safely commit a database transaction with proper error handling.

    This function wraps db.commit() with exception handling for common
    database errors, automatically rolling back on failure and raising
    appropriate HTTP exceptions.

    Args:
        db: The database session to commit
        operation: Description of the operation for error messages

    Raises:
        HTTPException: With appropriate status code and message on failure

    Usage:
        from app.database import get_db, safe_commit

        @router.post("/items")
        def create_item(item: ItemCreate, db: Session = Depends(get_db)):
            db_item = Item(**item.dict())
            db.add(db_item)
            safe_commit(db, "create item")
            return db_item
    """
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Integrity error during {operation}: {e}")
        # Check for common constraint violations
        error_msg = str(e.orig).lower() if e.orig else str(e).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A record with this data already exists",
            )
        elif "foreign key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referenced record does not exist",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database constraint violation during {operation}",
            )
    except OperationalError as e:
        db.rollback()
        logger.error(f"Database operational error during {operation}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during {operation}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during {operation}",
        )


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting asynchronous database session.

    Only available when using PostgreSQL.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Async database sessions are only available with PostgreSQL. "
            "Current database URL does not support async operations."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database session (non-dependency use).

    Usage:
        with get_db_context() as db:
            db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database session (non-dependency use).

    Only available when using PostgreSQL.

    Usage:
        async with get_async_db_context() as db:
            result = await db.execute(select(Item))
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Async database sessions are only available with PostgreSQL.")

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# =============================================================================
# HEALTH CHECKS
# =============================================================================


def check_db_health() -> dict:
    """
    Check database health and return connection info.

    Returns:
        dict with status, database type, and pool stats (if PostgreSQL)
    """
    try:
        with get_db_context() as db:
            if _is_sqlite():
                db.execute(text("SELECT 1"))
                return {
                    "status": "healthy",
                    "database": "sqlite",
                    "pool": "static",
                }
            elif _is_postgres():
                db.execute(text("SELECT 1"))
                pool = engine.pool
                # Cast to QueuePool for type checking - we know it's QueuePool for PostgreSQL
                if isinstance(pool, QueuePool):
                    return {
                        "status": "healthy",
                        "database": "postgresql",
                        "pool": {
                            "size": pool.size(),
                            "checked_in": pool.checkedin(),
                            "checked_out": pool.checkedout(),
                            "overflow": pool.overflow(),
                        },
                    }
                return {
                    "status": "healthy",
                    "database": "postgresql",
                    "pool": "unknown",
                }
            else:
                db.execute(text("SELECT 1"))
                return {
                    "status": "healthy",
                    "database": "unknown",
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_async_db_health() -> dict:
    """
    Check async database health (PostgreSQL only).

    Returns:
        dict with status and pool stats
    """
    if not _is_postgres() or async_engine is None:
        return {
            "status": "unavailable",
            "reason": "Async database only available with PostgreSQL",
        }

    try:
        async with get_async_db_context() as db:
            await db.execute(text("SELECT 1"))
            # NullPool is used for async - no pool stats available
            return {
                "status": "healthy",
                "database": "postgresql_async",
                "pool": "nullpool",  # NullPool doesn't maintain connections
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# =============================================================================
# INITIALIZATION
# =============================================================================


def init_db():
    """
    Initialize database tables directly using SQLAlchemy metadata.

    WARNING: This function is provided for DEVELOPMENT and TESTING only.

    For PRODUCTION deployments, use Alembic migrations instead:
        cd backend
        alembic upgrade head

    Why use migrations in production?
    1. Schema versioning - Track all database changes over time
    2. Rollback capability - Safely revert changes if needed
    3. Data preservation - Migrations can handle data transformations
    4. Team coordination - Everyone stays on the same schema version
    5. Audit trail - Clear history of what changed and when

    Migration commands:
        # Check current revision
        alembic current

        # Show migration history
        alembic history

        # Apply all migrations
        alembic upgrade head

        # Rollback one migration
        alembic downgrade -1

        # Generate new migration from model changes
        alembic revision --autogenerate -m "description"

    See backend/alembic/versions/ for migration files.
    """
    # Import all models to register them with Base
    from app.models import (
        CareerJournalEntry,
        CoverLetter,
        JobApplication,
        Profile,
        Resume,
        User,
    )
    from app.models.job_alert import JobAlert
    from app.models.job_filters import ApplicationQuestion, CompanyFilter, KeywordFilter

    Base.metadata.create_all(bind=engine)


async def dispose_engines():
    """
    Dispose of all database engines.

    Call this during application shutdown.
    """
    engine.dispose()
    if async_engine is not None:
        await async_engine.dispose()


def get_database_info() -> dict:
    """
    Get information about the current database configuration.

    Returns:
        dict with database type, URL (sanitized), and pool settings
    """
    # Sanitize URL to hide password
    url = settings.database_url
    if "@" in url:
        # Hide password in URL
        parts = url.split("@")
        prefix = parts[0].rsplit(":", 1)[0]
        url = f"{prefix}:***@{parts[1]}"

    info: dict[str, Any] = {
        "type": "sqlite" if _is_sqlite() else "postgresql" if _is_postgres() else "unknown",
        "url": url,
        "async_available": _is_postgres(),
    }

    if _is_postgres():
        info["pool"] = {
            "size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "timeout": settings.db_pool_timeout,
            "recycle": settings.db_pool_recycle,
            "pre_ping": settings.db_pool_pre_ping,
        }

    return info
