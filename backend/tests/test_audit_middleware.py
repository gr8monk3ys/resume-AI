"""
Tests for audit logging middleware and utilities.

Tests:
- AuditEventType enum values
- AuditLogger core functionality (log events, database storage)
- Failed login tracking and rate limiting
- Account lockout logic
- Audit query methods
- AuditMiddleware request/response logging
"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.middleware.audit import (
    AccountLockout,
    AuditEventType,
    AuditLog,
    AuditLogger,
    AuditMiddleware,
    FailedLoginAttempt,
    get_audit_logger,
    init_audit_logger,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_audit_db():
    """Create a temporary database for audit testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_audit.db")
        yield db_path


@pytest.fixture
def audit_logger(temp_audit_db):
    """Create an AuditLogger with temporary database."""
    logger = AuditLogger(
        database_path=temp_audit_db,
        enable_file_logging=False,
    )
    return logger


@pytest.fixture
def audit_logger_with_file_logging(temp_audit_db):
    """Create an AuditLogger with file logging enabled."""
    with tempfile.TemporaryDirectory() as log_dir:
        log_path = os.path.join(log_dir, "audit.log")
        logger = AuditLogger(
            database_path=temp_audit_db,
            enable_file_logging=True,
            log_file_path=log_path,
        )
        yield logger, log_path


# =============================================================================
# AuditEventType Tests
# =============================================================================


class TestAuditEventType:
    """Tests for AuditEventType enum."""

    def test_authentication_events_exist(self):
        """Test that authentication event types exist."""
        assert AuditEventType.LOGIN_SUCCESS == "login_success"
        assert AuditEventType.LOGIN_FAILED == "login_failed"
        assert AuditEventType.LOGOUT == "logout"
        assert AuditEventType.TOKEN_REFRESH == "token_refresh"

    def test_account_events_exist(self):
        """Test that account event types exist."""
        assert AuditEventType.REGISTER == "register"
        assert AuditEventType.PASSWORD_CHANGE == "password_change"
        assert AuditEventType.PASSWORD_RESET == "password_reset"
        assert AuditEventType.ACCOUNT_LOCKED == "account_locked"
        assert AuditEventType.ACCOUNT_UNLOCKED == "account_unlocked"

    def test_data_events_exist(self):
        """Test that data event types exist."""
        assert AuditEventType.DATA_CREATED == "data_created"
        assert AuditEventType.DATA_UPDATED == "data_updated"
        assert AuditEventType.DATA_DELETED == "data_deleted"
        assert AuditEventType.DATA_EXPORTED == "data_exported"

    def test_security_events_exist(self):
        """Test that security event types exist."""
        assert AuditEventType.RATE_LIMITED == "rate_limited"
        assert AuditEventType.SECURITY_VIOLATION == "security_violation"
        assert AuditEventType.SUSPICIOUS_ACTIVITY == "suspicious_activity"

    def test_api_events_exist(self):
        """Test that API event types exist."""
        assert AuditEventType.API_ACCESS == "api_access"
        assert AuditEventType.API_ERROR == "api_error"


# =============================================================================
# AuditLogger Core Tests
# =============================================================================


class TestAuditLogger:
    """Tests for AuditLogger core functionality."""

    def test_init_creates_database(self, temp_audit_db):
        """Test that initializing AuditLogger creates the database."""
        logger = AuditLogger(database_path=temp_audit_db)
        assert os.path.exists(temp_audit_db)

    def test_log_event_stores_in_database(self, audit_logger):
        """Test that log_event stores entries in the database."""
        audit_logger.log_event(
            AuditEventType.API_ACCESS,
            "Test action",
            user_id=1,
            username="testuser",
        )

        logs = audit_logger.get_recent_logs(limit=10)
        assert len(logs) == 1
        assert logs[0]["event_type"] == "api_access"
        assert logs[0]["action"] == "Test action"
        assert logs[0]["user_id"] == 1
        assert logs[0]["username"] == "testuser"

    def test_log_event_with_all_fields(self, audit_logger):
        """Test log_event with all optional fields."""
        audit_logger.log_event(
            AuditEventType.DATA_CREATED,
            "Created resource",
            user_id=42,
            username="admin",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test",
            request_id="req-12345",
            request_path="/api/resources",
            request_method="POST",
            response_status=201,
            details={"resource_id": 123, "type": "resume"},
            success=True,
        )

        logs = audit_logger.get_recent_logs(limit=1)
        assert len(logs) == 1
        log = logs[0]

        assert log["event_type"] == "data_created"
        assert log["user_id"] == 42
        assert log["username"] == "admin"
        assert log["ip_address"] == "192.168.1.100"
        assert log["request_id"] == "req-12345"
        assert log["success"] is True
        assert log["details"]["resource_id"] == 123

    def test_log_event_truncates_long_fields(self, audit_logger):
        """Test that long fields are truncated."""
        long_user_agent = "x" * 1000
        long_path = "/api/" + "x" * 1000

        audit_logger.log_event(
            AuditEventType.API_ACCESS,
            "Test",
            user_agent=long_user_agent,
            request_path=long_path,
        )

        # Should not raise an error - fields are truncated internally

    def test_log_event_with_file_logging(self, audit_logger_with_file_logging):
        """Test that file logging writes to log file."""
        logger, log_path = audit_logger_with_file_logging

        logger.log_event(
            AuditEventType.LOGIN_SUCCESS,
            "User logged in",
            username="testuser",
            success=True,
        )

        # Check log file was written
        assert os.path.exists(log_path)
        with open(log_path, "r") as f:
            content = f.read()
            assert "login_success" in content
            assert "testuser" in content


# =============================================================================
# Login Tracking Tests
# =============================================================================


class TestLoginTracking:
    """Tests for failed login tracking and rate limiting."""

    def test_log_login_success_clears_failed_attempts(self, audit_logger):
        """Test that successful login clears failed attempts."""
        # Create some failed attempts first
        audit_logger.record_failed_login_attempt("testuser", "192.168.1.1")
        audit_logger.record_failed_login_attempt("testuser", "192.168.1.1")
        audit_logger.record_failed_login_attempt("testuser", "192.168.1.1")

        assert audit_logger.get_total_failed_attempts("testuser") == 3

        # Log successful login
        audit_logger.log_login_success(
            user_id=1,
            username="testuser",
            ip_address="192.168.1.1",
        )

        # Failed attempts should be cleared
        assert audit_logger.get_total_failed_attempts("testuser") == 0

    def test_log_login_failed_records_attempt(self, audit_logger):
        """Test that failed login records an attempt."""
        audit_logger.log_login_failed(
            username="baduser",
            reason="Invalid password",
            ip_address="10.0.0.1",
        )

        assert audit_logger.get_total_failed_attempts("baduser") == 1

        # Check audit log was created
        logs = audit_logger.get_recent_logs(event_type=AuditEventType.LOGIN_FAILED)
        assert len(logs) == 1
        assert logs[0]["username"] == "baduser"
        assert logs[0]["details"]["reason"] == "Invalid password"

    def test_record_failed_login_attempt(self, audit_logger):
        """Test recording failed login attempts."""
        audit_logger.record_failed_login_attempt(
            username="user1",
            ip_address="1.2.3.4",
            user_agent="Test Browser",
        )

        assert audit_logger.get_total_failed_attempts("user1") == 1

    def test_get_recent_failed_attempts_time_filter(self, audit_logger):
        """Test that recent failed attempts uses time window."""
        # Record an attempt
        audit_logger.record_failed_login_attempt("timetest", "1.1.1.1")

        # Should find 1 in last 15 minutes
        assert audit_logger.get_recent_failed_attempts("timetest", minutes=15) == 1

        # Manually update the attempt time to be old
        with audit_logger.get_session() as session:
            attempt = session.query(FailedLoginAttempt).filter(
                FailedLoginAttempt.username == "timetest"
            ).first()
            attempt.attempt_time = datetime.utcnow() - timedelta(hours=1)

        # Should find 0 in last 15 minutes now
        assert audit_logger.get_recent_failed_attempts("timetest", minutes=15) == 0

    def test_get_total_failed_attempts(self, audit_logger):
        """Test getting total failed attempts for a user."""
        for i in range(5):
            audit_logger.record_failed_login_attempt("multiuser", f"ip{i}")

        assert audit_logger.get_total_failed_attempts("multiuser") == 5
        assert audit_logger.get_total_failed_attempts("otheruser") == 0

    def test_clear_failed_login_attempts(self, audit_logger):
        """Test clearing failed login attempts."""
        audit_logger.record_failed_login_attempt("clearme", "1.1.1.1")
        audit_logger.record_failed_login_attempt("clearme", "2.2.2.2")

        assert audit_logger.get_total_failed_attempts("clearme") == 2

        audit_logger.clear_failed_login_attempts("clearme")

        assert audit_logger.get_total_failed_attempts("clearme") == 0


# =============================================================================
# Account Lockout Tests
# =============================================================================


class TestAccountLockout:
    """Tests for account lockout functionality."""

    def test_is_account_locked_returns_false_when_not_locked(self, audit_logger):
        """Test that unlocked accounts return False."""
        is_locked, reason = audit_logger.is_account_locked("notlocked")
        assert is_locked is False
        assert reason is None

    def test_is_account_locked_returns_true_when_locked(self, audit_logger):
        """Test that locked accounts return True with reason."""
        audit_logger.lock_account("lockeduser", "Too many failures")

        is_locked, reason = audit_logger.is_account_locked("lockeduser")
        assert is_locked is True
        assert "Too many failures" in reason

    def test_lock_account_creates_lockout(self, audit_logger):
        """Test that lock_account creates a lockout record."""
        audit_logger.lock_account("newlock", "Brute force detected")

        is_locked, _ = audit_logger.is_account_locked("newlock")
        assert is_locked is True

        # Check audit log
        logs = audit_logger.get_recent_logs(event_type=AuditEventType.ACCOUNT_LOCKED)
        assert len(logs) == 1
        assert logs[0]["username"] == "newlock"

    def test_lock_account_is_idempotent(self, audit_logger):
        """Test that locking an already locked account doesn't create duplicates."""
        audit_logger.lock_account("idempotent", "First lock")
        audit_logger.lock_account("idempotent", "Second lock")

        with audit_logger.get_session() as session:
            lockouts = session.query(AccountLockout).filter(
                AccountLockout.username == "idempotent",
                AccountLockout.unlocked_at.is_(None),
            ).all()
            assert len(lockouts) == 1

    def test_unlock_account(self, audit_logger):
        """Test unlocking an account."""
        audit_logger.lock_account("unlockme", "Test lock")
        is_locked, _ = audit_logger.is_account_locked("unlockme")
        assert is_locked is True

        audit_logger.unlock_account("unlockme")

        is_locked, _ = audit_logger.is_account_locked("unlockme")
        assert is_locked is False

    def test_check_login_allowed_when_locked(self, audit_logger):
        """Test check_login_allowed returns False for locked accounts."""
        audit_logger.lock_account("checklock", "Manual lock")

        allowed, reason, wait = audit_logger.check_login_allowed("checklock")
        assert allowed is False
        assert "locked" in reason.lower()

    def test_check_login_allowed_rate_limited(self, audit_logger):
        """Test check_login_allowed rate limits after too many recent failures."""
        # Record 5 recent failures
        for _ in range(5):
            audit_logger.record_failed_login_attempt("ratelimit", "1.1.1.1")

        allowed, reason, wait = audit_logger.check_login_allowed(
            "ratelimit",
            max_recent_failures=5,
        )
        assert allowed is False
        assert "too many" in reason.lower()
        assert wait > 0

    def test_check_login_allowed_triggers_lockout_at_threshold(self, audit_logger):
        """Test that check_login_allowed triggers lockout at threshold."""
        # Record 10 failures (lockout threshold)
        for _ in range(10):
            audit_logger.record_failed_login_attempt("threshold", "1.1.1.1")

        allowed, reason, _ = audit_logger.check_login_allowed(
            "threshold",
            lockout_threshold=10,
        )
        assert allowed is False

        # Account should now be locked
        is_locked, _ = audit_logger.is_account_locked("threshold")
        assert is_locked is True

    def test_check_login_allowed_returns_true_when_clear(self, audit_logger):
        """Test check_login_allowed returns True for clean accounts."""
        allowed, reason, wait = audit_logger.check_login_allowed("cleanuser")
        assert allowed is True
        assert reason == ""
        assert wait == 0


# =============================================================================
# Audit Query Tests
# =============================================================================


class TestAuditQueries:
    """Tests for audit query methods."""

    def test_get_recent_logs_default(self, audit_logger):
        """Test getting recent logs with default parameters."""
        # Create some logs
        for i in range(5):
            audit_logger.log_event(
                AuditEventType.API_ACCESS,
                f"Action {i}",
                user_id=i,
            )

        logs = audit_logger.get_recent_logs()
        assert len(logs) == 5
        # Should be in reverse chronological order
        assert logs[0]["action"] == "Action 4"

    def test_get_recent_logs_with_limit(self, audit_logger):
        """Test getting recent logs with limit."""
        for i in range(10):
            audit_logger.log_event(AuditEventType.API_ACCESS, f"Action {i}")

        logs = audit_logger.get_recent_logs(limit=3)
        assert len(logs) == 3

    def test_get_recent_logs_filtered_by_type(self, audit_logger):
        """Test filtering logs by event type."""
        audit_logger.log_event(AuditEventType.API_ACCESS, "Access")
        audit_logger.log_event(AuditEventType.API_ERROR, "Error")
        audit_logger.log_event(AuditEventType.LOGIN_SUCCESS, "Login")

        logs = audit_logger.get_recent_logs(event_type=AuditEventType.API_ACCESS)
        assert len(logs) == 1
        assert logs[0]["event_type"] == "api_access"

    def test_get_recent_logs_filtered_by_user(self, audit_logger):
        """Test filtering logs by user ID."""
        audit_logger.log_event(AuditEventType.API_ACCESS, "User 1", user_id=1)
        audit_logger.log_event(AuditEventType.API_ACCESS, "User 2", user_id=2)
        audit_logger.log_event(AuditEventType.API_ACCESS, "User 1 again", user_id=1)

        logs = audit_logger.get_recent_logs(user_id=1)
        assert len(logs) == 2
        for log in logs:
            assert log["user_id"] == 1

    def test_get_failed_login_stats(self, audit_logger):
        """Test getting failed login statistics."""
        audit_logger.log_login_failed("user1", "bad password", "1.1.1.1")
        audit_logger.log_login_failed("user2", "bad password", "2.2.2.2")
        audit_logger.log_login_failed("user1", "bad password again", "1.1.1.1")

        stats = audit_logger.get_failed_login_stats(hours=24)
        assert stats["total_failures"] == 3
        assert stats["unique_users"] == 2

    def test_cleanup_old_logs(self, audit_logger):
        """Test cleaning up old audit logs."""
        # Create a log
        audit_logger.log_event(AuditEventType.API_ACCESS, "Old log")

        # Make it old
        with audit_logger.get_session() as session:
            log = session.query(AuditLog).first()
            log.timestamp = datetime.utcnow() - timedelta(days=100)

        # Cleanup logs older than 90 days
        deleted = audit_logger.cleanup_old_logs(days=90)
        assert deleted == 1

        logs = audit_logger.get_recent_logs()
        assert len(logs) == 0

    def test_cleanup_old_failed_attempts(self, audit_logger):
        """Test cleaning up old failed login attempts."""
        audit_logger.record_failed_login_attempt("olduser", "1.1.1.1")

        # Make it old
        with audit_logger.get_session() as session:
            attempt = session.query(FailedLoginAttempt).first()
            attempt.attempt_time = datetime.utcnow() - timedelta(days=60)

        # Cleanup attempts older than 30 days
        deleted = audit_logger.cleanup_old_failed_attempts(days=30)
        assert deleted == 1


# =============================================================================
# Convenience Method Tests
# =============================================================================


class TestConvenienceMethods:
    """Tests for convenience logging methods."""

    def test_log_logout(self, audit_logger):
        """Test logout logging."""
        audit_logger.log_logout(user_id=1, username="testuser", request_id="req-123")

        logs = audit_logger.get_recent_logs(event_type=AuditEventType.LOGOUT)
        assert len(logs) == 1
        assert logs[0]["username"] == "testuser"

    def test_log_password_change(self, audit_logger):
        """Test password change logging."""
        audit_logger.log_password_change(
            user_id=1,
            username="testuser",
            ip_address="192.168.1.1",
        )

        logs = audit_logger.get_recent_logs(event_type=AuditEventType.PASSWORD_CHANGE)
        assert len(logs) == 1
        assert logs[0]["username"] == "testuser"

    def test_log_data_deletion(self, audit_logger):
        """Test data deletion logging."""
        audit_logger.log_data_deletion(
            user_id=1,
            username="testuser",
            resource_type="resume",
            resource_id=42,
        )

        logs = audit_logger.get_recent_logs(event_type=AuditEventType.DATA_DELETED)
        assert len(logs) == 1
        assert logs[0]["details"]["resource_type"] == "resume"
        assert logs[0]["details"]["resource_id"] == 42

    def test_log_security_violation(self, audit_logger):
        """Test security violation logging."""
        audit_logger.log_security_violation(
            violation_type="xss_attempt",
            details={"input": "<script>alert(1)</script>"},
            ip_address="10.0.0.1",
        )

        logs = audit_logger.get_recent_logs(event_type=AuditEventType.SECURITY_VIOLATION)
        assert len(logs) == 1
        assert logs[0]["success"] is False


# =============================================================================
# Global Logger Tests
# =============================================================================


class TestGlobalLogger:
    """Tests for global logger functions."""

    def test_get_audit_logger_returns_instance(self, temp_audit_db):
        """Test that get_audit_logger returns an instance."""
        with patch("app.middleware.audit._audit_logger", None):
            logger = get_audit_logger()
            assert logger is not None
            assert isinstance(logger, AuditLogger)

    def test_init_audit_logger_sets_global(self, temp_audit_db):
        """Test that init_audit_logger sets the global instance."""
        with patch("app.middleware.audit._audit_logger", None):
            logger = init_audit_logger(database_path=temp_audit_db)
            assert logger is not None


# =============================================================================
# AuditMiddleware Tests
# =============================================================================


class TestAuditMiddleware:
    """Tests for AuditMiddleware."""

    @pytest.fixture
    def app_with_audit_middleware(self, audit_logger):
        """Create a test app with audit middleware."""
        app = FastAPI()
        app.add_middleware(
            AuditMiddleware,
            audit_logger=audit_logger,
            log_all_requests=True,
        )

        @app.get("/api/test")
        def test_endpoint():
            return {"status": "ok"}

        @app.get("/api/error")
        def error_endpoint():
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Test error")

        @app.get("/health")
        def health():
            return {"status": "healthy"}

        return app, audit_logger

    @pytest.mark.asyncio
    async def test_middleware_logs_requests(self, app_with_audit_middleware):
        """Test that middleware logs API requests."""
        app, logger = app_with_audit_middleware

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/test")

        logs = logger.get_recent_logs()
        assert len(logs) == 1
        assert logs[0]["event_type"] == "api_access"
        assert "/api/test" in logs[0]["action"]  # Action contains "GET /api/test"

    @pytest.mark.asyncio
    async def test_middleware_skips_health_endpoint(self, app_with_audit_middleware):
        """Test that middleware skips excluded paths like /health."""
        app, logger = app_with_audit_middleware

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/health")

        logs = logger.get_recent_logs()
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_middleware_logs_errors(self, app_with_audit_middleware):
        """Test that middleware logs error responses."""
        app, logger = app_with_audit_middleware

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/error")

        logs = logger.get_recent_logs()
        assert len(logs) == 1
        assert logs[0]["event_type"] == "api_error"
        assert logs[0]["success"] is False


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unicode_username(self, audit_logger):
        """Test handling of Unicode usernames."""
        audit_logger.log_login_failed(
            username="user\u00e9\u4e2d\u6587",
            reason="Test",
        )

        attempts = audit_logger.get_total_failed_attempts("user\u00e9\u4e2d\u6587")
        assert attempts == 1

    def test_null_optional_fields(self, audit_logger):
        """Test that null optional fields are handled."""
        audit_logger.log_event(
            AuditEventType.API_ACCESS,
            "Test with nulls",
            user_id=None,
            username=None,
            ip_address=None,
            user_agent=None,
            request_id=None,
            details=None,
        )

        logs = audit_logger.get_recent_logs()
        assert len(logs) == 1

    def test_empty_string_fields(self, audit_logger):
        """Test handling of empty string fields."""
        audit_logger.log_event(
            AuditEventType.API_ACCESS,
            "",  # Empty action
            username="",
        )

        logs = audit_logger.get_recent_logs()
        assert len(logs) == 1

    def test_special_characters_in_details(self, audit_logger):
        """Test that special characters in details are handled."""
        audit_logger.log_event(
            AuditEventType.SECURITY_VIOLATION,
            "XSS attempt",
            details={
                "input": "<script>alert('xss')</script>",
                "query": "'; DROP TABLE users; --",
            },
        )

        logs = audit_logger.get_recent_logs()
        assert len(logs) == 1
        assert "<script>" in logs[0]["details"]["input"]
