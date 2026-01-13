"""
Caching utilities for ResuBoost AI.

This module provides caching mechanisms to improve performance by reducing
redundant API calls and expensive computations.
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any, Callable
from functools import wraps
import sqlite3
from contextlib import contextmanager


# Cache database path
CACHE_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'data',
    'cache.db'
)


def init_cache_database():
    """Initialize the cache database."""
    os.makedirs(os.path.dirname(CACHE_DB_PATH), exist_ok=True)

    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()

    # Enable foreign keys (for consistency, though not used in cache)
    cursor.execute('PRAGMA foreign_keys=ON')

    # Cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    ''')

    # Index for faster cleanup
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON cache(category)')

    conn.commit()
    conn.close()


@contextmanager
def get_cache_db_connection():
    """Context manager for cache database connections."""
    conn = sqlite3.connect(CACHE_DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrency
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=10000')

    # Enable foreign keys (for consistency, though not used in cache)
    conn.execute('PRAGMA foreign_keys=ON')

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def _make_serializable(obj):
    """
    Convert an object to a JSON-serializable form.
    For non-serializable objects, use type name and id.
    """
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        # For non-serializable objects (like self), use type name
        return f"<{type(obj).__name__}:{id(obj)}>"


def generate_cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        MD5 hash of arguments as cache key

    Example:
        >>> key = generate_cache_key("resume text", job_id=123)
        'a1b2c3d4e5f6...'
    """
    # Convert arguments to serializable form
    serializable_args = tuple(_make_serializable(arg) for arg in args)
    serializable_kwargs = {k: _make_serializable(v) for k, v in kwargs.items()}

    # Create a string representation of all arguments
    key_data = {
        'args': serializable_args,
        'kwargs': serializable_kwargs
    }

    # Convert to JSON string (sorted for consistency)
    key_string = json.dumps(key_data, sort_keys=True)

    # Generate MD5 hash
    return hashlib.md5(key_string.encode()).hexdigest()


def cache_get(key: str, category: str = 'general') -> Optional[Any]:
    """
    Retrieve value from cache.

    Args:
        key: Cache key
        category: Cache category (e.g., 'ai_response', 'ats_score')

    Returns:
        Cached value or None if not found/expired

    Example:
        >>> value = cache_get('resume_123_ats_score', category='ats')
        >>> if value:
        ...     return value
    """
    init_cache_database()

    try:
        with get_cache_db_connection() as conn:
            cursor = conn.cursor()

            # Get cached value if not expired
            cursor.execute('''
                SELECT value FROM cache
                WHERE key = ? AND category = ? AND expires_at > datetime('now')
            ''', (key, category))

            result = cursor.fetchone()

            if result:
                # Deserialize value
                return json.loads(result['value'])

            return None

    except Exception as e:
        # Cache errors should not break the application
        print(f"Cache get error: {e}")
        return None


def cache_set(key: str, value: Any, category: str = 'general', ttl_seconds: int = 3600):
    """
    Store value in cache.

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        category: Cache category
        ttl_seconds: Time to live in seconds (default: 1 hour)

    Example:
        >>> cache_set('resume_123_ats_score', 85, category='ats', ttl_seconds=7200)
    """
    init_cache_database()

    try:
        # Serialize value
        value_json = json.dumps(value)

        # Calculate expiration
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        with get_cache_db_connection() as conn:
            cursor = conn.cursor()

            # Insert or replace cache entry
            cursor.execute('''
                INSERT OR REPLACE INTO cache (key, value, category, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (key, value_json, category, expires_at))

    except Exception as e:
        # Cache errors should not break the application
        print(f"Cache set error: {e}")


def cache_delete(key: str, category: str = 'general'):
    """
    Delete value from cache.

    Args:
        key: Cache key
        category: Cache category

    Example:
        >>> cache_delete('resume_123_ats_score', category='ats')
    """
    init_cache_database()

    try:
        with get_cache_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cache WHERE key = ? AND category = ?', (key, category))

    except Exception as e:
        print(f"Cache delete error: {e}")


def cache_clear(category: Optional[str] = None):
    """
    Clear all cache entries, optionally filtered by category.

    Args:
        category: Optional category to clear (None = clear all)

    Example:
        >>> cache_clear(category='ai_response')  # Clear only AI responses
        >>> cache_clear()  # Clear all cache
    """
    init_cache_database()

    try:
        with get_cache_db_connection() as conn:
            cursor = conn.cursor()

            if category:
                cursor.execute('DELETE FROM cache WHERE category = ?', (category,))
            else:
                cursor.execute('DELETE FROM cache')

    except Exception as e:
        print(f"Cache clear error: {e}")


def cleanup_expired_cache():
    """
    Remove expired cache entries.

    Should be run periodically (e.g., daily via cron job).

    Example:
        >>> cleanup_expired_cache()
    """
    init_cache_database()

    try:
        with get_cache_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache WHERE expires_at < datetime('now')")
            deleted_count = cursor.rowcount

        return deleted_count

    except Exception as e:
        print(f"Cache cleanup error: {e}")
        return 0


def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache statistics

    Example:
        >>> stats = get_cache_stats()
        >>> print(f"Total entries: {stats['total_entries']}")
    """
    init_cache_database()

    try:
        with get_cache_db_connection() as conn:
            cursor = conn.cursor()

            # Total entries
            cursor.execute('SELECT COUNT(*) as count FROM cache')
            total_entries = cursor.fetchone()['count']

            # Active entries (not expired)
            cursor.execute("SELECT COUNT(*) as count FROM cache WHERE expires_at > datetime('now')")
            active_entries = cursor.fetchone()['count']

            # Expired entries
            expired_entries = total_entries - active_entries

            # Entries by category
            cursor.execute('''
                SELECT category, COUNT(*) as count
                FROM cache
                WHERE expires_at > datetime('now')
                GROUP BY category
            ''')
            by_category = {row['category']: row['count'] for row in cursor.fetchall()}

            return {
                'total_entries': total_entries,
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'by_category': by_category
            }

    except Exception as e:
        print(f"Cache stats error: {e}")
        return {}


# Decorator for automatic caching
def cached(category: str = 'general', ttl_seconds: int = 3600, key_prefix: str = ''):
    """
    Decorator to automatically cache function results.

    Args:
        category: Cache category
        ttl_seconds: Time to live in seconds
        key_prefix: Optional prefix for cache key

    Returns:
        Decorated function with automatic caching

    Example:
        >>> @cached(category='ats', ttl_seconds=7200)
        ... def calculate_ats_score(resume_text, job_description):
        ...     # Expensive calculation
        ...     return score
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            base_key = f"{key_prefix}{func.__name__}"
            cache_key = f"{base_key}_{generate_cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = cache_get(cache_key, category=category)

            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)

            # Cache the result
            cache_set(cache_key, result, category=category, ttl_seconds=ttl_seconds)

            return result

        # Add cache control methods to function
        wrapper.cache_clear = lambda: cache_clear(category)
        wrapper.cache_delete = lambda *args, **kwargs: cache_delete(
            f"{key_prefix}{func.__name__}_{generate_cache_key(*args, **kwargs)}",
            category
        )

        return wrapper

    return decorator


# In-memory cache for very short-lived data (within same request)
class MemoryCache:
    """
    Simple in-memory cache for request-scoped caching.

    Use for very short-lived caching within a single request/session.
    Data is lost when object is destroyed.
    """

    def __init__(self):
        """Initialize memory cache."""
        self._cache = {}
        self._expiry = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from memory cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key in self._cache:
            # Check expiry
            if key in self._expiry and datetime.now() > self._expiry[key]:
                del self._cache[key]
                del self._expiry[key]
                return None

            return self._cache[key]

        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """
        Set value in memory cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        self._cache[key] = value
        self._expiry[key] = datetime.now() + timedelta(seconds=ttl_seconds)

    def delete(self, key: str):
        """Delete value from memory cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._expiry:
            del self._expiry[key]

    def clear(self):
        """Clear all memory cache."""
        self._cache.clear()
        self._expiry.clear()


# Global memory cache instance (for request-scoped caching)
_memory_cache = MemoryCache()


def memory_cache_get(key: str) -> Optional[Any]:
    """Get from memory cache."""
    return _memory_cache.get(key)


def memory_cache_set(key: str, value: Any, ttl_seconds: int = 300):
    """Set in memory cache."""
    _memory_cache.set(key, value, ttl_seconds)


def memory_cache_delete(key: str):
    """Delete from memory cache."""
    _memory_cache.delete(key)


def memory_cache_clear():
    """Clear memory cache."""
    _memory_cache.clear()


# Export all caching utilities
__all__ = [
    'init_cache_database',
    'generate_cache_key',
    'cache_get',
    'cache_set',
    'cache_delete',
    'cache_clear',
    'cleanup_expired_cache',
    'get_cache_stats',
    'cached',
    'MemoryCache',
    'memory_cache_get',
    'memory_cache_set',
    'memory_cache_delete',
    'memory_cache_clear',
]
