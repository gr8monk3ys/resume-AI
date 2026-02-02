"""
Audit logging middleware for FastAPI.

Provides comprehensive audit logging for security-sensitive events:
- Login attempts (success/fail)
- Password changes
- Data deletions
- Admin actions
- Rate limit violations
- Security violations

Stores audit logs in SQLite with option for file-based logging.
"""

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request, Response
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.security import get_client_ip, get_user_agent

# Create a separate base for audit models
class AuditBase(DeclarativeBase):
    """Base class for audit SQLAlchemy models."""

    pass


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"

    # Account events
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ACCOUNT_DELETED = "account_deleted"

    # Data events
    DATA_CREATED = "data_created"
    DATA_UPDATED = "data_updated"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"

    # Admin events
    ADMIN_ACTION = "admin_action"
    PERMISSION_CHANGE = "permission_change"

    # Security events
    RATE_LIMITED = "rate_limited"
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

    # API events
    API_ACCESS = "api_access"
    API_ERROR = "api_error"


class AuditLog(AuditBase):
    """SQLAlchemy model for audit logs."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    action = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(64), nullable=True, index=True)
    request_path = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)
    response_status = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)  # JSON serialized details
    success = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("idx_audit_user_time", "user_id", "timestamp"),
        Index("idx_audit_type_time", "event_type", "timestamp"),
        Index("idx_audit_ip_time", "ip_address", "timestamp"),
    )


class FailedLoginAttempt(AuditBase):
    """SQLAlchemy model for tracking failed login attempts."""

    __tablename__ = "failed_login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, index=True)
    attempt_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    __table_args__ = (Index("idx_failed_username_time", "username", "attempt_time"),)


class AccountLockout(AuditBase):
    """SQLAlchemy model for account lockouts."""

    __tablename__ = "account_lockouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    locked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    lockout_reason = Column(String(255), nullable=True)
    unlocked_at = Column(DateTime, nullable=True)


class AuditLogger:
    """
    Centralized audit logging service.

    Handles both SQLite storage and optional file-based logging.
    """

    def __init__(
        self,
        database_path: str = "data/audit.db",
        enable_file_logging: bool = False,
        log_file_path: str = "logs/audit.log",
    ):
        self.database_path = database_path
        self.enable_file_logging = enable_file_logging
        self.log_file_path = log_file_path

        # Ensure directories exist
        os.makedirs(os.path.dirname(database_path), exist_ok=True)

        # Initialize database
        self._init_database()

        # Initialize file logger if enabled
        if enable_file_logging:
            self._init_file_logger()

    def _init_database(self):
        """Initialize the audit database."""
        db_url = f"sqlite:///{self.database_path}"

        self.engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Enable foreign keys and WAL mode for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        # Create tables
        AuditBase.metadata.create_all(bind=self.engine)

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def _init_file_logger(self):
        """Initialize file-based logger with rotation."""
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)

        self.file_logger = logging.getLogger("audit")
        self.file_logger.setLevel(logging.INFO)

        # RotatingFileHandler: max 10MB per file, keep 5 backup files (50MB total)
        handler = RotatingFileHandler(
            self.log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.file_logger.addHandler(handler)

    @contextmanager
    def get_session(self):
        """Get a database session."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
        response_status: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ):
        """
        Log an audit event.

        Args:
            event_type: Type of event (use AuditEventType enum)
            action: Description of the action
            user_id: User ID (if applicable)
            username: Username (if applicable)
            ip_address: IP address of the request
            user_agent: User agent string
            request_id: Unique request ID for tracing
            request_path: Request URL path
            request_method: HTTP method
            response_status: HTTP response status code
            details: Additional details as dict (JSON serialized)
            success: Whether the action succeeded
        """
        # Serialize details to JSON
        details_json = json.dumps(details) if details else None

        # Create audit log entry
        log_entry = AuditLog(
            timestamp=datetime.utcnow(),
            event_type=event_type.value,
            action=action,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            request_id=request_id,
            request_path=request_path[:500] if request_path else None,
            request_method=request_method,
            response_status=response_status,
            details=details_json,
            success=success,
        )

        with self.get_session() as session:
            session.add(log_entry)

        # Also log to file if enabled
        if self.enable_file_logging:
            log_msg = (
                f"event={event_type.value} action='{action}' "
                f"user_id={user_id} username={username} "
                f"ip={ip_address} success={success}"
            )
            if success:
                self.file_logger.info(log_msg)
            else:
                self.file_logger.warning(log_msg)

    # Convenience methods for common events
    def log_login_success(
        self,
        user_id: int,
        username: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ):
        """Log a successful login."""
        self.log_event(
            AuditEventType.LOGIN_SUCCESS,
            f"User {username} logged in successfully",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
        )

        # Clear failed attempts on successful login
        self.clear_failed_login_attempts(username)

    def log_login_failed(
        self,
        username: str,
        reason: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ):
        """Log a failed login attempt."""
        self.log_event(
            AuditEventType.LOGIN_FAILED,
            f"Failed login attempt for {username}",
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            details={"reason": reason},
            success=False,
        )

        # Record failed attempt for rate limiting
        self.record_failed_login_attempt(username, ip_address, user_agent)

    def log_logout(
        self,
        user_id: int,
        username: str,
        request_id: str | None = None,
    ):
        """Log a logout event."""
        self.log_event(
            AuditEventType.LOGOUT,
            f"User {username} logged out",
            user_id=user_id,
            username=username,
            request_id=request_id,
            success=True,
        )

    def log_password_change(
        self,
        user_id: int,
        username: str,
        ip_address: str | None = None,
        request_id: str | None = None,
    ):
        """Log a password change."""
        self.log_event(
            AuditEventType.PASSWORD_CHANGE,
            f"Password changed for {username}",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            request_id=request_id,
            success=True,
        )

    def log_data_deletion(
        self,
        user_id: int,
        username: str,
        resource_type: str,
        resource_id: int,
        ip_address: str | None = None,
        request_id: str | None = None,
    ):
        """Log a data deletion event."""
        self.log_event(
            AuditEventType.DATA_DELETED,
            f"User {username} deleted {resource_type} (id={resource_id})",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            request_id=request_id,
            details={"resource_type": resource_type, "resource_id": resource_id},
            success=True,
        )

    def log_account_locked(
        self,
        username: str,
        reason: str,
        ip_address: str | None = None,
    ):
        """Log an account lockout."""
        self.log_event(
            AuditEventType.ACCOUNT_LOCKED,
            f"Account locked: {username}",
            username=username,
            ip_address=ip_address,
            details={"reason": reason},
            success=True,
        )

    def log_security_violation(
        self,
        violation_type: str,
        details: Dict[str, Any],
        ip_address: str | None = None,
        request_id: str | None = None,
    ):
        """Log a security violation."""
        self.log_event(
            AuditEventType.SECURITY_VIOLATION,
            f"Security violation: {violation_type}",
            ip_address=ip_address,
            request_id=request_id,
            details=details,
            success=False,
        )

    # Failed login tracking methods
    def record_failed_login_attempt(
        self,
        username: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        """Record a failed login attempt."""
        with self.get_session() as session:
            attempt = FailedLoginAttempt(
                username=username,
                attempt_time=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,
            )
            session.add(attempt)

    def get_recent_failed_attempts(
        self,
        username: str,
        minutes: int = 15,
    ) -> int:
        """Get the number of failed attempts in the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)

        with self.get_session() as session:
            count = (
                session.query(FailedLoginAttempt)
                .filter(
                    FailedLoginAttempt.username == username,
                    FailedLoginAttempt.attempt_time > cutoff,
                )
                .count()
            )
            return count

    def get_total_failed_attempts(self, username: str) -> int:
        """Get total failed attempts for a username."""
        with self.get_session() as session:
            count = (
                session.query(FailedLoginAttempt)
                .filter(FailedLoginAttempt.username == username)
                .count()
            )
            return count

    def clear_failed_login_attempts(self, username: str):
        """Clear failed login attempts after successful login."""
        with self.get_session() as session:
            session.query(FailedLoginAttempt).filter(
                FailedLoginAttempt.username == username
            ).delete()

    # Account lockout methods
    def is_account_locked(self, username: str) -> tuple:
        """
        Check if an account is locked.

        Returns:
            tuple: (is_locked: bool, reason: str or None)
        """
        with self.get_session() as session:
            lockout = (
                session.query(AccountLockout)
                .filter(
                    AccountLockout.username == username,
                    AccountLockout.unlocked_at.is_(None),
                )
                .first()
            )

            if lockout:
                return True, lockout.lockout_reason
            return False, None

    def lock_account(self, username: str, reason: str):
        """Lock an account."""
        with self.get_session() as session:
            # Check if already locked
            existing = (
                session.query(AccountLockout)
                .filter(
                    AccountLockout.username == username,
                    AccountLockout.unlocked_at.is_(None),
                )
                .first()
            )

            if existing:
                return  # Already locked

            lockout = AccountLockout(
                username=username,
                locked_at=datetime.utcnow(),
                lockout_reason=reason,
            )
            session.add(lockout)

        # Log the lockout
        self.log_account_locked(username, reason)

    def unlock_account(self, username: str):
        """Unlock an account."""
        with self.get_session() as session:
            session.query(AccountLockout).filter(
                AccountLockout.username == username,
                AccountLockout.unlocked_at.is_(None),
            ).update({"unlocked_at": datetime.utcnow()})

    def check_login_allowed(
        self,
        username: str,
        max_recent_failures: int = 5,
        rate_limit_window_minutes: int = 15,
        lockout_threshold: int = 10,
    ) -> tuple:
        """
        Check if a login attempt is allowed.

        Returns:
            tuple: (allowed: bool, reason: str, wait_seconds: int)
        """
        # Check account lockout
        is_locked, lock_reason = self.is_account_locked(username)
        if is_locked:
            return False, f"Account locked: {lock_reason}", 0

        # Check total failures for permanent lockout
        total_failures = self.get_total_failed_attempts(username)
        if total_failures >= lockout_threshold:
            self.lock_account(username, f"{lockout_threshold}+ failed login attempts")
            return False, "Account locked due to too many failed attempts", 0

        # Check recent failures for rate limiting
        recent_failures = self.get_recent_failed_attempts(
            username, minutes=rate_limit_window_minutes
        )
        if recent_failures >= max_recent_failures:
            wait_seconds = rate_limit_window_minutes * 60
            return (
                False,
                f"Too many failed attempts. Please try again later.",
                wait_seconds,
            )

        return True, "", 0

    # Query methods
    def get_recent_logs(
        self,
        limit: int = 100,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict]:
        """Get recent audit logs."""
        with self.get_session() as session:
            query = session.query(AuditLog)

            if event_type:
                query = query.filter(AuditLog.event_type == event_type.value)

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)

            logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

            return [
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "event_type": log.event_type,
                    "action": log.action,
                    "user_id": log.user_id,
                    "username": log.username,
                    "ip_address": log.ip_address,
                    "request_id": log.request_id,
                    "success": log.success,
                    "details": json.loads(log.details) if log.details else None,
                }
                for log in logs
            ]

    def get_failed_login_stats(self, hours: int = 24) -> Dict:
        """Get failed login statistics."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        with self.get_session() as session:
            # Total failed logins
            total = (
                session.query(AuditLog)
                .filter(
                    AuditLog.event_type == AuditEventType.LOGIN_FAILED.value,
                    AuditLog.timestamp > cutoff,
                )
                .count()
            )

            # Unique usernames
            from sqlalchemy import func

            unique_users = (
                session.query(func.count(func.distinct(AuditLog.username)))
                .filter(
                    AuditLog.event_type == AuditEventType.LOGIN_FAILED.value,
                    AuditLog.timestamp > cutoff,
                )
                .scalar()
            )

            return {
                "total_failures": total,
                "unique_users": unique_users,
                "period_hours": hours,
            }

    def cleanup_old_logs(self, days: int = 90) -> int:
        """Clean up old audit logs."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        with self.get_session() as session:
            deleted = session.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
            return deleted

    def cleanup_old_failed_attempts(self, days: int = 30) -> int:
        """Clean up old failed login attempts."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        with self.get_session() as session:
            deleted = (
                session.query(FailedLoginAttempt)
                .filter(FailedLoginAttempt.attempt_time < cutoff)
                .delete()
            )
            return deleted


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def init_audit_logger(
    database_path: str = "data/audit.db",
    enable_file_logging: bool = False,
    log_file_path: str = "logs/audit.log",
) -> AuditLogger:
    """Initialize the global audit logger with custom settings."""
    global _audit_logger
    _audit_logger = AuditLogger(
        database_path=database_path,
        enable_file_logging=enable_file_logging,
        log_file_path=log_file_path,
    )
    return _audit_logger


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log API access for auditing.

    Logs:
    - Request path and method
    - Response status code
    - Request ID for tracing
    - Client IP and user agent
    """

    def __init__(
        self,
        app,
        audit_logger: Optional[AuditLogger] = None,
        log_all_requests: bool = False,
        log_paths: Optional[set] = None,
        skip_paths: Optional[set] = None,
    ):
        super().__init__(app)
        self.audit_logger = audit_logger or get_audit_logger()
        self.log_all_requests = log_all_requests
        self.log_paths = log_paths or set()
        self.skip_paths = skip_paths or {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request/response for auditing."""
        path = request.url.path
        method = request.method

        # Skip excluded paths
        if path in self.skip_paths:
            return await call_next(request)

        # Get request metadata
        request_id = getattr(request.state, "request_id", None)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)

        # Process request
        response = await call_next(request)

        # Determine if we should log this request
        should_log = self.log_all_requests or path in self.log_paths

        # Always log errors (4xx, 5xx)
        if response.status_code >= 400:
            should_log = True

        # Check for security violations stored in request state
        security_violations = getattr(request.state, "security_violations", None)
        if security_violations:
            self.audit_logger.log_security_violation(
                violation_type="input_validation",
                details={"violations": security_violations, "path": path},
                ip_address=ip_address,
                request_id=request_id,
            )

        if should_log:
            self.audit_logger.log_event(
                (
                    AuditEventType.API_ACCESS
                    if response.status_code < 400
                    else AuditEventType.API_ERROR
                ),
                f"{method} {path}",
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                request_path=path,
                request_method=method,
                response_status=response.status_code,
                success=response.status_code < 400,
            )

        return response


# Export all audit utilities
__all__ = [
    "AuditEventType",
    "AuditLog",
    "FailedLoginAttempt",
    "AccountLockout",
    "AuditLogger",
    "AuditMiddleware",
    "get_audit_logger",
    "init_audit_logger",
]
