"""
Redis-based caching service for ResuBoost AI.

Provides a distributed caching layer for expensive operations such as
LLM responses, user profile lookups, and job statistics aggregation.
Uses redis.asyncio for non-blocking cache operations with fail-open
semantics: when Redis is unavailable, cache misses return None and
cache writes are silently dropped, allowing the application to
continue operating without interruption.

Connection pooling is managed through redis.asyncio.ConnectionPool
with configurable pool size. All keys are namespaced under the
``resuboost:cache:`` prefix to avoid collisions with rate-limiting
keys that use ``resuboost:rate_limit:``.
"""

import hashlib
import json
import logging
import time
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# Key prefix separates cache keys from rate-limit keys in the same Redis instance
_KEY_PREFIX = "resuboost:cache:"


class CacheService:
    """
    Async Redis cache with fail-open error handling.

    Every public method catches ``redis.RedisError`` and logs a warning
    rather than propagating the exception, ensuring that a Redis outage
    never blocks the request path.
    """

    def __init__(
        self,
        redis_url: str,
        pool_size: int = 10,
        connection_timeout: int = 5,
        socket_timeout: int = 5,
    ) -> None:
        self._redis_url = redis_url
        self._pool_size = pool_size
        self._connection_timeout = connection_timeout
        self._socket_timeout = socket_timeout
        self._redis = None
        self._connected = False

    async def _get_redis(self):
        """
        Lazily initialize and return the Redis client.

        Returns None if the connection cannot be established so that
        callers can implement fail-open behaviour.
        """
        if self._redis is not None and self._connected:
            return self._redis

        try:
            import redis.asyncio as aioredis

            pool = aioredis.ConnectionPool.from_url(
                self._redis_url,
                max_connections=self._pool_size,
                decode_responses=True,
                socket_connect_timeout=self._connection_timeout,
                socket_timeout=self._socket_timeout,
            )
            self._redis = aioredis.Redis(connection_pool=pool)
            await self._redis.ping()
            self._connected = True
            logger.info("Redis cache connection established")
            return self._redis
        except ImportError:
            logger.error(
                "redis package not installed. Install with: pip install redis"
            )
            return None
        except Exception as e:
            logger.warning("Failed to connect to Redis for caching: %s", e)
            self._connected = False
            return None

    def _make_key(self, key: str) -> str:
        """Prefix a key with the cache namespace."""
        return f"{_KEY_PREFIX}{key}"

    # ------------------------------------------------------------------
    # Core cache operations
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[str]:
        """
        Retrieve a string value from the cache.

        Args:
            key: The cache key (without prefix).

        Returns:
            The cached string value, or None on miss or error.
        """
        client = await self._get_redis()
        if client is None:
            return None
        try:
            return await client.get(self._make_key(key))
        except Exception as e:
            logger.warning("Cache get error for key '%s': %s", key, e)
            self._connected = False
            return None

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """
        Store a string value in the cache.

        Args:
            key: The cache key (without prefix).
            value: The string value to cache.
            ttl: Time-to-live in seconds (default 300).

        Returns:
            True if the value was stored successfully, False otherwise.
        """
        client = await self._get_redis()
        if client is None:
            return False
        try:
            await client.set(self._make_key(key), value, ex=ttl)
            return True
        except Exception as e:
            logger.warning("Cache set error for key '%s': %s", key, e)
            self._connected = False
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a single key from the cache.

        Args:
            key: The cache key (without prefix).

        Returns:
            True if the key was deleted, False otherwise.
        """
        client = await self._get_redis()
        if client is None:
            return False
        try:
            result = await client.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.warning("Cache delete error for key '%s': %s", key, e)
            self._connected = False
            return False

    async def exists(self, key: str) -> bool:
        """
        Check whether a key exists in the cache.

        Args:
            key: The cache key (without prefix).

        Returns:
            True if the key exists, False on miss or error.
        """
        client = await self._get_redis()
        if client is None:
            return False
        try:
            return bool(await client.exists(self._make_key(key)))
        except Exception as e:
            logger.warning("Cache exists error for key '%s': %s", key, e)
            self._connected = False
            return False

    async def get_json(self, key: str) -> Optional[dict]:
        """
        Retrieve and deserialize a JSON value from the cache.

        Args:
            key: The cache key (without prefix).

        Returns:
            The deserialized dictionary, or None on miss or error.
        """
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Cache JSON decode error for key '%s': %s", key, e)
            return None

    async def set_json(self, key: str, value: dict, ttl: int = 300) -> bool:
        """
        Serialize a dictionary as JSON and store it in the cache.

        Args:
            key: The cache key (without prefix).
            value: The dictionary to serialize and cache.
            ttl: Time-to-live in seconds (default 300).

        Returns:
            True if the value was stored successfully, False otherwise.
        """
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.warning("Cache JSON encode error for key '%s': %s", key, e)
            return False
        return await self.set(key, serialized, ttl=ttl)

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching the given glob pattern.

        The pattern is prefixed automatically with the cache namespace.
        Uses ``SCAN`` to avoid blocking Redis on large keyspaces.

        Args:
            pattern: A Redis glob pattern (e.g. ``user:42:*``).

        Returns:
            The number of keys deleted, or 0 on error.
        """
        client = await self._get_redis()
        if client is None:
            return 0
        try:
            full_pattern = self._make_key(pattern)
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = await client.scan(
                    cursor=cursor, match=full_pattern, count=100
                )
                if keys:
                    deleted += await client.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as e:
            logger.warning(
                "Cache invalidate_pattern error for pattern '%s': %s",
                pattern,
                e,
            )
            self._connected = False
            return 0

    # ------------------------------------------------------------------
    # Domain-specific: LLM response caching
    # ------------------------------------------------------------------

    async def cache_llm_response(
        self,
        operation: str,
        input_hash: str,
        response: dict,
        ttl: int = 3600,
    ) -> bool:
        """
        Cache an LLM response keyed by operation and input hash.

        LLM calls are the most expensive operations in the application.
        Caching them with a one-hour default TTL significantly reduces
        latency and API costs for repeated queries.

        Args:
            operation: The LLM operation name (e.g. ``tailor_resume``).
            input_hash: SHA-256 hash of the input content.
            response: The response dictionary to cache.
            ttl: Time-to-live in seconds (default 3600).

        Returns:
            True if the response was cached, False otherwise.
        """
        key = f"llm:{operation}:{input_hash}"
        return await self.set_json(key, response, ttl=ttl)

    async def get_cached_llm_response(
        self,
        operation: str,
        input_hash: str,
    ) -> Optional[dict]:
        """
        Retrieve a cached LLM response.

        Args:
            operation: The LLM operation name.
            input_hash: SHA-256 hash of the input content.

        Returns:
            The cached response dictionary, or None on miss.
        """
        key = f"llm:{operation}:{input_hash}"
        return await self.get_json(key)

    # ------------------------------------------------------------------
    # Domain-specific: user profile caching
    # ------------------------------------------------------------------

    async def cache_user_profile(
        self,
        user_id: int,
        profile: dict,
        ttl: int = 600,
    ) -> bool:
        """
        Cache a user profile for fast lookups.

        Args:
            user_id: The user's database identifier.
            profile: The serialized profile dictionary.
            ttl: Time-to-live in seconds (default 600).

        Returns:
            True if the profile was cached, False otherwise.
        """
        key = f"user:{user_id}:profile"
        return await self.set_json(key, profile, ttl=ttl)

    async def get_cached_user_profile(
        self,
        user_id: int,
    ) -> Optional[dict]:
        """
        Retrieve a cached user profile.

        Args:
            user_id: The user's database identifier.

        Returns:
            The cached profile dictionary, or None on miss.
        """
        key = f"user:{user_id}:profile"
        return await self.get_json(key)

    async def invalidate_user_cache(self, user_id: int) -> None:
        """
        Invalidate all cached data for a given user.

        This should be called whenever user data is mutated (profile
        update, resume upload, job application status change, etc.)
        to ensure stale data is never served.

        Args:
            user_id: The user's database identifier.
        """
        pattern = f"user:{user_id}:*"
        deleted = await self.invalidate_pattern(pattern)
        if deleted > 0:
            logger.debug(
                "Invalidated %d cache entries for user %d", deleted, user_id
            )

    # ------------------------------------------------------------------
    # Domain-specific: job stats caching
    # ------------------------------------------------------------------

    async def cache_job_stats(
        self,
        user_id: int,
        stats: dict,
        ttl: int = 300,
    ) -> bool:
        """
        Cache aggregated job application statistics for a user.

        Job stats involve multiple database queries (counts by status,
        date ranges, etc.) and benefit from short-lived caching.

        Args:
            user_id: The user's database identifier.
            stats: The computed statistics dictionary.
            ttl: Time-to-live in seconds (default 300).

        Returns:
            True if the stats were cached, False otherwise.
        """
        key = f"user:{user_id}:job_stats"
        return await self.set_json(key, stats, ttl=ttl)

    async def get_cached_job_stats(
        self,
        user_id: int,
    ) -> Optional[dict]:
        """
        Retrieve cached job application statistics for a user.

        Args:
            user_id: The user's database identifier.

        Returns:
            The cached statistics dictionary, or None on miss.
        """
        key = f"user:{user_id}:job_stats"
        return await self.get_json(key)

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    async def health_check(self) -> dict:
        """
        Check Redis connectivity and return status information.

        Returns:
            A dictionary with ``status``, ``connected``, and ``latency_ms``
            fields. On error the ``status`` is ``"unhealthy"`` and
            ``error`` contains the failure message.
        """
        client = await self._get_redis()
        if client is None:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": "Unable to connect to Redis",
            }
        try:
            start = time.monotonic()
            await client.ping()
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            info = await client.info(section="memory")
            return {
                "status": "healthy",
                "connected": True,
                "latency_ms": latency_ms,
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            logger.warning("Cache health check failed: %s", e)
            self._connected = False
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }

    @staticmethod
    def hash_input(content: str) -> str:
        """
        Produce a deterministic SHA-256 hex digest for cache key generation.

        Args:
            content: The input string to hash.

        Returns:
            A 64-character lowercase hex string.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def close(self) -> None:
        """
        Close the underlying Redis connection pool.

        Safe to call multiple times or when no connection was established.
        """
        if self._redis is not None:
            try:
                await self._redis.aclose()
                logger.info("Redis cache connection closed")
            except Exception as e:
                logger.warning("Error closing Redis cache connection: %s", e)
            finally:
                self._redis = None
                self._connected = False


# --------------------------------------------------------------------------
# Singleton management
# --------------------------------------------------------------------------

_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    Get or create the singleton ``CacheService`` instance.

    The Redis URL is read from ``get_settings().redis_url``.  If no URL
    is configured the service is still created but every operation will
    gracefully return None / False (fail-open).

    Returns:
        The application-wide CacheService instance.
    """
    global _cache_service
    if _cache_service is None:
        settings = get_settings()
        _cache_service = CacheService(
            redis_url=settings.redis_url or "",
            pool_size=10,
            connection_timeout=settings.redis_connection_timeout,
            socket_timeout=settings.redis_socket_timeout,
        )
    return _cache_service


async def close_cache_service() -> None:
    """
    Close the singleton Redis connection on application shutdown.

    Safe to call even when no cache service was created.
    """
    global _cache_service
    if _cache_service is not None:
        await _cache_service.close()
        _cache_service = None


# --------------------------------------------------------------------------
# FastAPI dependency
# --------------------------------------------------------------------------


async def get_cache() -> CacheService:
    """
    FastAPI dependency for injecting the cache service.

    Usage::

        @router.get("/items")
        async def list_items(
            cache: CacheService = Depends(get_cache),
        ):
            cached = await cache.get_json("items:all")
            if cached is not None:
                return cached
            ...
    """
    return get_cache_service()
