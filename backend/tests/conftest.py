"""
Pytest configuration and fixtures for backend tests.

Provides:
- Test database setup (SQLite in-memory)
- Test client fixture with async support
- Authentication fixtures (test user, test token)
- Cleanup after tests

IMPORTANT: Environment variables MUST be set before any app imports.
This file is loaded by pytest before tests run.
"""

import os
import sys

# ==============================================================================
# CRITICAL: Set test environment variables BEFORE any app imports
# This must happen at module level before imports below
# ==============================================================================

os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ENABLE_RATE_LIMITING"] = "false"
os.environ["ENABLE_AUDIT_LOGGING"] = "false"
os.environ["ENABLE_SECURITY_HEADERS"] = "false"
os.environ["ENABLE_INPUT_SANITIZATION"] = "false"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["DEBUG"] = "false"

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# ==============================================================================
# Now we can safely import from the app
# ==============================================================================

from datetime import datetime
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Clear settings cache BEFORE importing app modules to ensure test settings are used
from app.config import clear_settings_cache, get_settings

clear_settings_cache()

# Now import app modules - they will pick up the test environment variables
from app.database import Base, get_db
from app.main import app
from app.middleware import audit as audit_module
from app.middleware.auth import create_access_token, get_password_hash
from app.models.career_journal import CareerJournalEntry
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User

# ==============================================================================
# Test Database Setup
# ==============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db() -> Generator[Session, None, None]:
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# Pytest Fixtures
# ==============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Session-scoped fixture to ensure test environment is properly configured.

    This runs once at the start of the test session.
    """
    # Verify environment variables are set
    assert os.environ.get("LLM_PROVIDER") == "mock"
    assert os.environ.get("DATABASE_URL") == "sqlite:///:memory:"

    # Clear settings cache to ensure fresh settings
    clear_settings_cache()

    # Verify settings
    settings = get_settings()
    assert settings.llm_provider == "mock"
    assert settings.enable_rate_limiting is False
    assert settings.enable_scheduler is False

    yield

    # Cleanup after all tests
    clear_settings_cache()


@pytest.fixture(scope="function", autouse=True)
def reset_audit_logger(tmp_path):
    """
    Reset the global audit logger before each test to prevent
    failed login attempts from previous tests affecting lockout state.

    Uses a temp directory for the audit database so each test gets a fresh state.
    """
    # Clear any existing global audit logger
    audit_module._audit_logger = None

    # Initialize a fresh audit logger with a temp database for this test
    temp_db = tmp_path / "audit.db"
    audit_module.init_audit_logger(
        database_path=str(temp_db),
        enable_file_logging=False,
    )

    yield

    # Clean up after test
    audit_module._audit_logger = None


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.

    Creates all tables before the test and drops them after.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def app_with_db(db: Session) -> FastAPI:
    """
    Create FastAPI app with test database override.
    """
    app.dependency_overrides[get_db] = lambda: db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app_with_db: FastAPI, db: Session) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client.

    Uses httpx.AsyncClient for async testing with FastAPI.
    """

    # Override the get_db dependency to use our test session
    def get_test_db():
        try:
            yield db
        finally:
            pass

    app_with_db.dependency_overrides[get_db] = get_test_db

    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user_data() -> dict:
    """Test user registration data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    }


@pytest.fixture
def test_user(db: Session) -> User:
    """
    Create a test user in the database.

    Returns the created User object.
    """
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_profile(db: Session, test_user: User) -> Profile:
    """
    Create a test profile for the test user.

    Returns the created Profile object.
    """
    profile = Profile(
        user_id=test_user.id,
        name=test_user.full_name or test_user.username,
        email=test_user.email,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def test_token(test_user: User) -> str:
    """
    Create a valid JWT token for the test user.

    Returns the access token string.
    """
    token_data = {"sub": str(test_user.id), "username": test_user.username}
    return create_access_token(token_data)


@pytest.fixture
def auth_headers(test_token: str) -> dict:
    """
    Create authorization headers with test token.

    Returns a dict with the Authorization header.
    """
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def test_resume(db: Session, test_profile: Profile) -> Resume:
    """
    Create a test resume in the database.

    Returns the created Resume object.
    """
    resume = Resume(
        profile_id=test_profile.id,
        version_name="Main Resume",
        content="John Doe\nSoftware Engineer\n\nExperience:\n- 5 years Python development\n- Team lead at Tech Corp",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@pytest.fixture
def test_job(db: Session, test_profile: Profile) -> JobApplication:
    """
    Create a test job application in the database.

    Returns the created JobApplication object.
    """
    job = JobApplication(
        profile_id=test_profile.id,
        company="Tech Company",
        position="Senior Developer",
        job_description="Looking for an experienced developer...",
        status="Bookmarked",
        location="Remote",
        job_url="https://example.com/job",
        notes="Great opportunity",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def test_journal_entry(db: Session, test_profile: Profile) -> CareerJournalEntry:
    """
    Create a test career journal entry in the database.

    Returns the created CareerJournalEntry object.
    """
    import json

    entry = CareerJournalEntry(
        profile_id=test_profile.id,
        title="Completed Major Project",
        description="Led team to deliver project on time",
        achievement_date=datetime.utcnow().date(),
        tags=json.dumps(["leadership", "project management"]),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@pytest.fixture
def admin_user(db: Session) -> User:
    """
    Create an admin test user in the database.

    Returns the created admin User object.
    """
    user = User(
        username="adminuser",
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_admin=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create a valid JWT token for the admin user."""
    token_data = {"sub": str(admin_user.id), "username": admin_user.username}
    return create_access_token(token_data)


@pytest.fixture
def admin_auth_headers(admin_token: str) -> dict:
    """Create authorization headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def inactive_user(db: Session) -> User:
    """
    Create an inactive test user in the database.

    Returns the created User object with is_active=False.
    """
    user = User(
        username="inactiveuser",
        email="inactive@example.com",
        password_hash=get_password_hash("inactivepassword123"),
        full_name="Inactive User",
        is_active=False,
        is_admin=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_profile(db: Session, admin_user: User) -> Profile:
    """
    Create a profile for the admin user.

    Returns the created Profile object.
    """
    profile = Profile(
        user_id=admin_user.id,
        name=admin_user.full_name or admin_user.username,
        email=admin_user.email,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def second_user(db: Session) -> User:
    """
    Create a second test user (for isolation tests).

    Returns the created User object.
    """
    user = User(
        username="seconduser",
        email="second@example.com",
        password_hash=get_password_hash("secondpassword123"),
        full_name="Second User",
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def second_user_token(second_user: User) -> str:
    """Create a valid JWT token for the second user."""
    token_data = {"sub": str(second_user.id), "username": second_user.username}
    return create_access_token(token_data)


@pytest.fixture
def second_user_auth_headers(second_user_token: str) -> dict:
    """Create authorization headers with second user token."""
    return {"Authorization": f"Bearer {second_user_token}"}


# ==============================================================================
# Sample Data for Testing
# ==============================================================================

SAMPLE_RESUME_CONTENT = """
John Doe
Software Engineer

SUMMARY
Experienced software engineer with 5+ years of experience in Python, JavaScript, and cloud technologies.

EXPERIENCE
Senior Software Engineer | Tech Corp | 2020-Present
- Led development of microservices architecture using Python and FastAPI
- Reduced deployment time by 60% through CI/CD improvements
- Mentored junior developers and conducted code reviews

Software Engineer | StartupXYZ | 2018-2020
- Developed RESTful APIs serving 1M+ daily requests
- Implemented automated testing, achieving 95% code coverage
- Collaborated with cross-functional teams on product features

SKILLS
Python, JavaScript, TypeScript, FastAPI, Django, React, AWS, Docker, PostgreSQL, Git

EDUCATION
B.S. Computer Science | State University | 2018
"""

SAMPLE_JOB_DESCRIPTION = """
Senior Python Developer

We are looking for an experienced Python developer to join our team.

Requirements:
- 5+ years of Python development experience
- Experience with FastAPI or Django
- Strong knowledge of REST API design
- Experience with AWS or similar cloud platforms
- Excellent communication skills

Nice to have:
- Experience with microservices architecture
- Knowledge of Docker and Kubernetes
- CI/CD experience
"""


@pytest.fixture
def sample_resume_content() -> str:
    """Return sample resume content for testing."""
    return SAMPLE_RESUME_CONTENT


@pytest.fixture
def sample_job_description() -> str:
    """Return sample job description for testing."""
    return SAMPLE_JOB_DESCRIPTION
