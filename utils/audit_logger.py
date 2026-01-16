"""
Audit logging for security-sensitive user actions.

This module tracks:
- Login/logout events
- Failed login attempts
- User registration
- Password changes
- Admin actions
- User management
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

# Use same auth database
AUTH_DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "auth.db")


@contextmanager
def get_auth_db_connection():
    """Context manager for auth database connections."""
    conn = sqlite3.connect(AUTH_DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_audit_log_table():
    """Initialize the audit_logs table."""
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        # Create audit logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                user_id INTEGER,
                username TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN NOT NULL DEFAULT 1
            )
        """
        )

        # Create indices for common queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON audit_logs(timestamp DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_event_type
            ON audit_logs(event_type, timestamp DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON audit_logs(user_id, timestamp DESC)
        """
        )

        conn.commit()


# Event types
EVENT_LOGIN = "login"
EVENT_LOGOUT = "logout"
EVENT_LOGIN_FAILED = "login_failed"
EVENT_REGISTER = "register"
EVENT_PASSWORD_CHANGE = "password_change"
EVENT_ACCOUNT_LOCKED = "account_locked"
EVENT_ACCOUNT_UNLOCKED = "account_unlocked"
EVENT_USER_CREATED = "user_created"
EVENT_USER_DELETED = "user_deleted"
EVENT_USER_UPDATED = "user_updated"
EVENT_ADMIN_ACTION = "admin_action"


def log_event(
    event_type: str,
    action: str,
    user_id: int = None,
    username: str = None,
    details: dict = None,
    ip_address: str = None,
    user_agent: str = None,
    success: bool = True,
):
    """
    Log an audit event.

    Args:
        event_type: Type of event (use EVENT_* constants)
        action: Description of the action
        user_id: User ID (if applicable)
        username: Username (if applicable)
        details: Additional details as dict (will be JSON serialized)
        ip_address: IP address of the request
        user_agent: User agent string
        success: Whether the action succeeded
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        # Serialize details to JSON
        details_json = json.dumps(details) if details else None

        cursor.execute(
            """
            INSERT INTO audit_logs (
                timestamp, event_type, user_id, username, action,
                details, ip_address, user_agent, success
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.now(),
                event_type,
                user_id,
                username,
                action,
                details_json,
                ip_address,
                user_agent,
                success,
            ),
        )

        conn.commit()


def log_login(user_id: int, username: str, ip_address: str = None, user_agent: str = None):
    """Log a successful login."""
    log_event(
        EVENT_LOGIN,
        f"User {username} logged in",
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
    )


def log_logout(user_id: int, username: str):
    """Log a logout event."""
    log_event(
        EVENT_LOGOUT,
        f"User {username} logged out",
        user_id=user_id,
        username=username,
        success=True,
    )


def log_login_failed(username: str, reason: str, ip_address: str = None, user_agent: str = None):
    """Log a failed login attempt."""
    log_event(
        EVENT_LOGIN_FAILED,
        f"Failed login attempt for {username}",
        username=username,
        details={"reason": reason},
        ip_address=ip_address,
        user_agent=user_agent,
        success=False,
    )


def log_registration(user_id: int, username: str, email: str):
    """Log a new user registration."""
    log_event(
        EVENT_REGISTER,
        f"New user registered: {username}",
        user_id=user_id,
        username=username,
        details={"email": email},
        success=True,
    )


def log_password_change(user_id: int, username: str):
    """Log a password change."""
    log_event(
        EVENT_PASSWORD_CHANGE,
        f"Password changed for {username}",
        user_id=user_id,
        username=username,
        success=True,
    )


def log_account_locked(username: str, reason: str):
    """Log an account lockout."""
    log_event(
        EVENT_ACCOUNT_LOCKED,
        f"Account locked: {username}",
        username=username,
        details={"reason": reason},
        success=True,
    )


def log_account_unlocked(username: str, admin_user_id: int = None):
    """Log an account unlock."""
    log_event(
        EVENT_ACCOUNT_UNLOCKED,
        f"Account unlocked: {username}",
        username=username,
        details={"unlocked_by": admin_user_id} if admin_user_id else None,
        success=True,
    )


def log_admin_action(
    admin_user_id: int, action: str, target_user: str = None, details: dict = None
):
    """Log an administrative action."""
    log_event(
        EVENT_ADMIN_ACTION,
        action,
        user_id=admin_user_id,
        details={"target_user": target_user, **(details or {})},
        success=True,
    )


def get_recent_logs(limit: int = 100, event_type: str = None, user_id: int = None) -> list:
    """
    Get recent audit logs.

    Args:
        limit: Maximum number of logs to return
        event_type: Filter by event type
        user_id: Filter by user ID

    Returns:
        List of audit log dicts
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        logs = cursor.fetchall()

        return [dict(log) for log in logs]


def get_failed_login_stats(hours: int = 24) -> dict:
    """
    Get failed login statistics for the last N hours.

    Args:
        hours: Number of hours to look back

    Returns:
        Dict with statistics
    """
    from datetime import timedelta

    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Total failed logins
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM audit_logs
            WHERE event_type = ? AND timestamp > ?
        """,
            (EVENT_LOGIN_FAILED, cutoff_time),
        )

        total_failures = cursor.fetchone()["count"]

        # Unique users with failures
        cursor.execute(
            """
            SELECT COUNT(DISTINCT username) as count
            FROM audit_logs
            WHERE event_type = ? AND timestamp > ?
        """,
            (EVENT_LOGIN_FAILED, cutoff_time),
        )

        unique_users = cursor.fetchone()["count"]

        # Top failed usernames
        cursor.execute(
            """
            SELECT username, COUNT(*) as attempts
            FROM audit_logs
            WHERE event_type = ? AND timestamp > ?
            GROUP BY username
            ORDER BY attempts DESC
            LIMIT 10
        """,
            (EVENT_LOGIN_FAILED, cutoff_time),
        )

        top_failures = [dict(row) for row in cursor.fetchall()]

        return {
            "total_failures": total_failures,
            "unique_users": unique_users,
            "top_failures": top_failures,
            "period_hours": hours,
        }


def cleanup_old_logs(days: int = 90):
    """
    Clean up old audit logs.

    Args:
        days: Keep logs newer than this many days

    Returns:
        Number of logs deleted
    """
    from datetime import timedelta

    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(days=days)

        cursor.execute(
            """
            DELETE FROM audit_logs
            WHERE timestamp < ?
        """,
            (cutoff_time,),
        )

        deleted = cursor.rowcount
        conn.commit()

        return deleted


# Initialize table on import
try:
    init_audit_log_table()
except Exception:
    pass  # Table may already exist
