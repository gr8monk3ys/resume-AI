"""
Authentication database module for multi-user support
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import bcrypt

# Use separate auth database or same database as main app
AUTH_DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "auth.db")


def init_auth_database():
    """Initialize authentication database with users table."""
    os.makedirs(os.path.dirname(AUTH_DATABASE_PATH), exist_ok=True)

    conn = sqlite3.connect(AUTH_DATABASE_PATH)
    cursor = conn.cursor()

    # Enable foreign keys immediately on connection
    cursor.execute("PRAGMA foreign_keys=ON")

    # Users table for authentication
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """
    )

    # Create index for faster lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON users(email)")

    conn.commit()
    conn.close()


@contextmanager
def get_auth_db_connection():
    """
    Context manager for auth database connections with optimizations.

    Optimizations:
    - WAL mode for better concurrency
    - Busy timeout to handle concurrent access
    - Foreign keys enabled
    """
    conn = sqlite3.connect(AUTH_DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")

    # Set busy timeout (10 seconds)
    conn.execute("PRAGMA busy_timeout=10000")

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


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# Reserved usernames that cannot be registered (enforced at database layer)
RESERVED_USERNAMES = frozenset(
    [
        "admin",
        "root",
        "system",
        "api",
        "test",
        "demo",
        "null",
        "undefined",
        "administrator",
        "superuser",
        "support",
        "help",
        "info",
        "contact",
        "webmaster",
        "postmaster",
        "hostmaster",
        "abuse",
        "noreply",
        "no-reply",
        "mailer-daemon",
        "nobody",
        "www",
        "ftp",
        "mail",
        "email",
    ]
)


def create_user(
    username: str, email: str, password: str, full_name: str = None, is_admin: bool = False
) -> int:
    """
    Create a new user.

    Returns:
        user_id if successful

    Raises:
        ValueError if username or email already exists, or if username is reserved
    """
    # Normalize username
    username = username.lower().strip()

    # Enforce reserved username check at database layer (defense in depth)
    if username in RESERVED_USERNAMES:
        raise ValueError(f"Username '{username}' is reserved and cannot be used")

    password_hash = hash_password(password)

    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        # Check if username or email already exists
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            raise ValueError("Username or email already exists")

        # Create user
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name, is_admin)
            VALUES (?, ?, ?, ?, ?)
        """,
            (username, email, password_hash, full_name, is_admin),
        )

        user_id = cursor.lastrowid

    return user_id


def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate a user by username and password.

    Returns:
        User dict if authentication successful, None otherwise.
        Note: password_hash is explicitly excluded from the returned dict
        to prevent accidental exposure in session state or logs.
    """
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            # Perform dummy password check to prevent timing attacks
            bcrypt.checkpw(b"dummy_password", bcrypt.gensalt())
            return None

        if not user["is_active"]:
            return None

        if not verify_password(password, user["password_hash"]):
            return None

        # Update last login
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now(), user["id"]))

        # Convert to dict and remove sensitive fields before returning
        user_dict = dict(user)
        user_dict.pop("password_hash", None)
        return user_dict


def _sanitize_user_dict(user_row) -> dict:
    """Remove sensitive fields from user dict before returning."""
    if not user_row:
        return None
    user_dict = dict(user_row)
    user_dict.pop("password_hash", None)
    return user_dict


def get_user_by_id(user_id: int) -> dict:
    """Get user by ID (excludes password_hash for security)."""
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return _sanitize_user_dict(user)


def get_user_by_username(username: str) -> dict:
    """Get user by username (excludes password_hash for security)."""
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return _sanitize_user_dict(user)


def get_all_users() -> list:
    """Get all users (admin only)."""
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, full_name, is_active, is_admin, created_at, last_login FROM users ORDER BY created_at DESC"
        )
        users = cursor.fetchall()
        return [dict(user) for user in users]


def update_user(user_id: int, **kwargs) -> bool:
    """Update user information."""
    allowed_fields = ["email", "full_name", "is_active", "is_admin"]

    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f"{field} = ?")
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(user_id)

    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        return cursor.rowcount > 0


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change user password."""
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()

        # Fetch password hash directly (internal use only)
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            return False

        if not verify_password(old_password, result["password_hash"]):
            return False

        new_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    """Delete a user (soft delete by deactivating)."""
    with get_auth_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        return cursor.rowcount > 0
