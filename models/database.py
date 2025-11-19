import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'resume_ai.db')

def init_database():
    """Initialize the database with required tables."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Enable foreign keys immediately on connection
    cursor.execute('PRAGMA foreign_keys=ON')

    # Check if profiles table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'")
    profiles_exists = cursor.fetchone() is not None

    if profiles_exists:
        # Check if user_id column exists
        cursor.execute("PRAGMA table_info(profiles)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'user_id' not in columns:
            # Migrate: Add user_id column to existing profiles table
            cursor.execute('ALTER TABLE profiles ADD COLUMN user_id INTEGER')
            conn.commit()

    # User Profile table (linked to authentication user)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            linkedin TEXT,
            github TEXT,
            portfolio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create index for faster user_id lookups (only if not exists)
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON profiles(user_id)')
    except Exception:
        pass  # Index might already exist

    # Resumes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            version_name TEXT NOT NULL,
            content TEXT NOT NULL,
            ats_score INTEGER,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    ''')

    # Job Applications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            job_description TEXT,
            status TEXT DEFAULT 'Applied',
            application_date DATE,
            deadline DATE,
            location TEXT,
            job_url TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    ''')

    # Career Journal table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS career_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            achievement_date DATE,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    ''')

    # Cover Letters table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cover_letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            job_application_id INTEGER,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id),
            FOREIGN KEY (job_application_id) REFERENCES job_applications(id)
        )
    ''')

    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    """
    Context manager for database connections with optimizations.

    Optimizations:
    - WAL mode for better concurrency
    - Busy timeout to handle concurrent access
    - Foreign keys enabled
    """
    conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrency
    conn.execute('PRAGMA journal_mode=WAL')

    # Set busy timeout (10 seconds)
    conn.execute('PRAGMA busy_timeout=10000')

    # Enable foreign keys
    conn.execute('PRAGMA foreign_keys=ON')

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_or_create_profile_for_user(user_id: int, name: str = "New User", email: str = ""):
    """
    Get or create a profile for a specific user.

    Args:
        user_id: The authenticated user's ID
        name: Default name if creating new profile
        email: Default email if creating new profile

    Returns:
        Profile dict
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,))
        profile = cursor.fetchone()

        if not profile:
            cursor.execute('''
                INSERT INTO profiles (user_id, name, email)
                VALUES (?, ?, ?)
            ''', (user_id, name, email))
            conn.commit()
            cursor.execute('SELECT * FROM profiles WHERE id = ?', (cursor.lastrowid,))
            profile = cursor.fetchone()

        return dict(profile)

def get_or_create_default_profile():
    """
    Get the default profile or create one if it doesn't exist.

    DEPRECATED: Use get_or_create_profile_for_user() for multi-user apps.
    This function is kept for backward compatibility with single-user mode.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM profiles WHERE user_id IS NULL LIMIT 1')
        profile = cursor.fetchone()

        if not profile:
            cursor.execute('''
                INSERT INTO profiles (user_id, name, email)
                VALUES (?, ?, ?)
            ''', (None, 'Default User', ''))
            conn.commit()
            cursor.execute('SELECT * FROM profiles WHERE id = ?', (cursor.lastrowid,))
            profile = cursor.fetchone()

        return dict(profile)
