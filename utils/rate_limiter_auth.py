"""
Authentication rate limiting to prevent brute force attacks.

This module tracks failed login attempts and implements:
- Rate limiting: Configurable max attempts per time window per username
- Account lockout: Account locked after configurable total failed attempts
- Cooldown periods: Exponential backoff for repeated failures

Configuration (via config.py or environment variables):
- AUTH_MAX_RECENT_FAILURES: Max failures per window (default: 5)
- AUTH_RATE_LIMIT_WINDOW_MINUTES: Window in minutes (default: 15)
- AUTH_LOCKOUT_THRESHOLD: Total failures before lockout (default: 10)
- AUTH_CLEANUP_DAYS: Days to keep failed attempts (default: 30)
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

# Import config settings with fallbacks
try:
    from config import (
        AUTH_CLEANUP_DAYS,
        AUTH_LOCKOUT_THRESHOLD,
        AUTH_MAX_RECENT_FAILURES,
        AUTH_RATE_LIMIT_WINDOW_MINUTES,
    )
except ImportError:
    AUTH_MAX_RECENT_FAILURES = 5
    AUTH_RATE_LIMIT_WINDOW_MINUTES = 15
    AUTH_LOCKOUT_THRESHOLD = 10
    AUTH_CLEANUP_DAYS = 30

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


def init_rate_limiting_table():
    """Initialize the failed_login_attempts table."""
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        # Create failed login attempts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS failed_login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                attempt_time TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT
            )
        """
        )

        # Create index for faster lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_username_time
            ON failed_login_attempts(username, attempt_time)
        """
        )

        # Create account lockout table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS account_lockouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                locked_at TIMESTAMP NOT NULL,
                lockout_reason TEXT,
                unlocked_at TIMESTAMP
            )
        """
        )

        conn.commit()


def record_failed_login(username: str, ip_address: str = None, user_agent: str = None):
    """
    Record a failed login attempt.

    Args:
        username: Username that failed to authenticate
        ip_address: Optional IP address of the attempt
        user_agent: Optional user agent string
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO failed_login_attempts (username, attempt_time, ip_address, user_agent)
            VALUES (?, ?, ?, ?)
        """,
            (username, datetime.now(), ip_address, user_agent),
        )
        conn.commit()


def get_recent_failed_attempts(username: str, minutes: int = 15) -> int:
    """
    Get number of failed attempts for a username in the last N minutes.

    Args:
        username: Username to check
        minutes: Time window in minutes (default: 15)

    Returns:
        Number of failed attempts in the time window
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM failed_login_attempts
            WHERE username = ? AND attempt_time > ?
        """,
            (username, cutoff_time),
        )

        result = cursor.fetchone()
        return result["count"] if result else 0


def get_total_failed_attempts(username: str) -> int:
    """
    Get total number of failed attempts for a username (all time).

    Args:
        username: Username to check

    Returns:
        Total number of failed attempts
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM failed_login_attempts
            WHERE username = ?
        """,
            (username,),
        )

        result = cursor.fetchone()
        return result["count"] if result else 0


def is_account_locked(username: str) -> tuple:
    """
    Check if an account is locked.

    Args:
        username: Username to check

    Returns:
        tuple: (is_locked: bool, reason: str, locked_until: datetime or None)
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT locked_at, lockout_reason, unlocked_at
            FROM account_lockouts
            WHERE username = ? AND unlocked_at IS NULL
        """,
            (username,),
        )

        result = cursor.fetchone()
        if result:
            return (True, result["lockout_reason"], None)  # Permanent lock
        return (False, None, None)


def lock_account(username: str, reason: str = "Too many failed login attempts"):
    """
    Lock an account due to too many failed attempts.

    Args:
        username: Username to lock
        reason: Reason for lockout
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        # Check if already locked
        cursor.execute(
            "SELECT id FROM account_lockouts WHERE username = ? AND unlocked_at IS NULL",
            (username,),
        )
        if cursor.fetchone():
            return  # Already locked

        cursor.execute(
            """
            INSERT INTO account_lockouts (username, locked_at, lockout_reason)
            VALUES (?, ?, ?)
        """,
            (username, datetime.now(), reason),
        )
        conn.commit()


def unlock_account(username: str):
    """
    Unlock a locked account (admin function).

    Args:
        username: Username to unlock
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE account_lockouts
            SET unlocked_at = ?
            WHERE username = ? AND unlocked_at IS NULL
        """,
            (datetime.now(), username),
        )
        conn.commit()


def clear_failed_attempts(username: str):
    """
    Clear failed login attempts for a username (after successful login).

    Args:
        username: Username to clear attempts for
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM failed_login_attempts
            WHERE username = ?
        """,
            (username,),
        )
        conn.commit()


def check_login_allowed(username: str) -> tuple:
    """
    Check if a login attempt is allowed for a username.

    Implements:
    - Account lockout check (AUTH_LOCKOUT_THRESHOLD+ total failures = permanent lock)
    - Rate limiting (AUTH_MAX_RECENT_FAILURES attempts per AUTH_RATE_LIMIT_WINDOW_MINUTES)

    Args:
        username: Username attempting to log in

    Returns:
        tuple: (allowed: bool, reason: str, wait_seconds: int)
    """
    # Check if account is locked
    is_locked, lock_reason, _ = is_account_locked(username)
    if is_locked:
        return (False, f"Account locked: {lock_reason}. Contact admin to unlock.", 0)

    # Check total failures (trigger permanent lock if >= threshold)
    total_failures = get_total_failed_attempts(username)
    if total_failures >= AUTH_LOCKOUT_THRESHOLD:
        lock_account(username, f"{AUTH_LOCKOUT_THRESHOLD}+ failed login attempts")
        return (False, "Account locked due to too many failed attempts. Contact admin.", 0)

    # Check recent failures (rate limiting)
    recent_failures = get_recent_failed_attempts(username, minutes=AUTH_RATE_LIMIT_WINDOW_MINUTES)
    if recent_failures >= AUTH_MAX_RECENT_FAILURES:
        # Calculate wait time
        with get_auth_db_connection() as conn:
            cursor = conn.cursor()
            cutoff_time = datetime.now() - timedelta(minutes=AUTH_RATE_LIMIT_WINDOW_MINUTES)
            cursor.execute(
                """
                SELECT attempt_time
                FROM failed_login_attempts
                WHERE username = ? AND attempt_time > ?
                ORDER BY attempt_time ASC
                LIMIT 1
            """,
                (username, cutoff_time),
            )

            oldest_attempt = cursor.fetchone()
            if oldest_attempt:
                oldest_time = datetime.fromisoformat(oldest_attempt["attempt_time"])
                wait_until = oldest_time + timedelta(minutes=AUTH_RATE_LIMIT_WINDOW_MINUTES)
                wait_seconds = int((wait_until - datetime.now()).total_seconds())
                wait_minutes = wait_seconds // 60

                return (
                    False,
                    f"Too many failed attempts. Try again in {wait_minutes} minute(s).",
                    wait_seconds,
                )

    # Login allowed
    return (True, "", 0)


def cleanup_old_attempts(days: int = None):
    """
    Clean up old failed login attempts (housekeeping).

    Args:
        days: Remove attempts older than this many days (default: AUTH_CLEANUP_DAYS)
    """
    if days is None:
        days = AUTH_CLEANUP_DAYS
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cutoff_time = datetime.now() - timedelta(days=days)

        cursor.execute(
            """
            DELETE FROM failed_login_attempts
            WHERE attempt_time < ?
        """,
            (cutoff_time,),
        )

        deleted = cursor.rowcount
        conn.commit()
        return deleted


# Initialize table on import
try:
    init_rate_limiting_table()
except Exception:
    pass  # Table may already exist
