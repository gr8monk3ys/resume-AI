"""
Rate limiting middleware for FastAPI.

Implements token bucket algorithm with configurable rates per endpoint type:
- Auth endpoints: 5 requests/minute
- AI endpoints: 20 requests/minute
- General API: 100 requests/minute

Supports both in-memory storage (single instance) and Redis storage (horizontal scaling).
Set REDIS_URL environment variable to enable Redis-based rate limiting.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Optional, Protocol, Tuple, TYPE_CHECKING

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Endpoint rate limit types."""

    AUTH = "auth"
    AI = "ai"
    GENERAL = "general"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit type."""

    max_requests: int
    window_seconds: int
    bucket_size: int = 0  # Max burst size (0 = same as max_requests)

    def __post_init__(self):
        if self.bucket_size == 0:
            self.bucket_size = self.max_requests


# Default rate limit configurations
DEFAULT_RATE_LIMITS: Dict[RateLimitType, RateLimitConfig] = {
    RateLimitType.AUTH: RateLimitConfig(max_requests=5, window_seconds=60),
    RateLimitType.AI: RateLimitConfig(max_requests=20, window_seconds=60),
    RateLimitType.GENERAL: RateLimitConfig(max_requests=100, window_seconds=60),
}


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    tokens: float
    last_update: float
    max_tokens: int
    refill_rate: float  # tokens per second

    @classmethod
    def create(cls, config: RateLimitConfig) -> "TokenBucket":
        """Create a new token bucket from config."""
        return cls(
            tokens=config.bucket_size,
            last_update=time.time(),
            max_tokens=config.bucket_size,
            refill_rate=config.max_requests / config.window_seconds,
        )

    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens from the bucket.

        Returns:
            Tuple of (success: bool, retry_after_seconds: float)
        """
        now = time.time()
        elapsed = now - self.last_update

        # Refill tokens based on elapsed time
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0

        # Calculate retry after time
        tokens_needed = tokens - self.tokens
        retry_after = tokens_needed / self.refill_rate
        return False, retry_after

    def get_remaining(self) -> int:
        """Get remaining tokens."""
        now = time.time()
        elapsed = now - self.last_update
        current_tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        return int(current_tokens)


class RateLimitStorage(Protocol):
    """Protocol for rate limit storage backends."""

    async def get_bucket(self, key: str, config: RateLimitConfig) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        ...

    async def update_bucket(self, key: str, bucket: TokenBucket) -> None:
        """Update a token bucket."""
        ...

    async def cleanup_expired(self) -> int:
        """Clean up expired buckets. Returns count of removed buckets."""
        ...


class InMemoryStorage:
    """
    In-memory rate limit storage.

    Thread-safe implementation using asyncio locks.
    Suitable for single-instance deployments.
    """

    def __init__(self, cleanup_interval: int = 300):
        self._buckets: Dict[str, TokenBucket] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for a key."""
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def get_bucket(self, key: str, config: RateLimitConfig) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        lock = await self._get_lock(key)
        async with lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket.create(config)
            return self._buckets[key]

    async def update_bucket(self, key: str, bucket: TokenBucket) -> None:
        """Update a token bucket."""
        lock = await self._get_lock(key)
        async with lock:
            self._buckets[key] = bucket

    async def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """Clean up buckets that haven't been accessed recently."""
        now = time.time()

        # Only cleanup periodically
        if now - self._last_cleanup < self._cleanup_interval:
            return 0

        self._last_cleanup = now
        expired_keys = []

        async with self._global_lock:
            for key, bucket in self._buckets.items():
                if now - bucket.last_update > max_age_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._buckets[key]
                if key in self._locks:
                    del self._locks[key]

        return len(expired_keys)

    def get_stats(self) -> Dict:
        """Get storage statistics."""
        return {
            "total_buckets": len(self._buckets),
            "total_locks": len(self._locks),
        }


class RedisStorage:
    """
    Redis-based rate limit storage for horizontal scaling.

    Uses Redis atomic operations (INCR, EXPIRE) for thread-safe distributed rate limiting.
    Implements the same token bucket algorithm but stores state in Redis.

    Falls back to allowing requests if Redis is unavailable (fail-open).
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "rate_limit",
        connection_timeout: int = 5,
        socket_timeout: int = 5,
    ):
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._connection_timeout = connection_timeout
        self._socket_timeout = socket_timeout
        self._redis: Optional["Redis"] = None
        self._connection_lock = asyncio.Lock()
        self._connected = False
        self._last_connection_attempt = 0.0
        self._connection_retry_delay = 5.0  # seconds between reconnection attempts

    async def _get_redis(self) -> Optional["Redis"]:
        """Get Redis connection, creating one if needed."""
        if self._redis is not None and self._connected:
            return self._redis

        # Avoid hammering Redis with connection attempts
        now = time.time()
        if now - self._last_connection_attempt < self._connection_retry_delay:
            return None

        async with self._connection_lock:
            # Double-check after acquiring lock
            if self._redis is not None and self._connected:
                return self._redis

            self._last_connection_attempt = now

            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=self._connection_timeout,
                    socket_timeout=self._socket_timeout,
                )
                # Test connection
                await self._redis.ping()
                self._connected = True
                logger.info("Redis connection established for rate limiting")
                return self._redis
            except ImportError:
                logger.error(
                    "redis package not installed. Install with: pip install redis"
                )
                return None
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to allow requests.")
                self._connected = False
                return None

    def _make_key(self, key: str) -> str:
        """Create a Redis key with proper prefixing."""
        return f"{self._key_prefix}:{key}"

    async def get_bucket(self, key: str, config: RateLimitConfig) -> TokenBucket:
        """
        Get or create a token bucket for the given key.

        Uses Redis to store bucket state. If Redis is unavailable, returns
        a fresh bucket (fail-open behavior).
        """
        redis_client = await self._get_redis()
        if redis_client is None:
            # Fail open - return fresh bucket allowing the request
            return TokenBucket.create(config)

        redis_key = self._make_key(key)
        try:
            # Get existing bucket data from Redis
            bucket_data = await redis_client.hgetall(redis_key)

            if bucket_data:
                return TokenBucket(
                    tokens=float(bucket_data.get("tokens", config.bucket_size)),
                    last_update=float(bucket_data.get("last_update", time.time())),
                    max_tokens=int(bucket_data.get("max_tokens", config.bucket_size)),
                    refill_rate=float(
                        bucket_data.get(
                            "refill_rate", config.max_requests / config.window_seconds
                        )
                    ),
                )
            else:
                # Create new bucket
                return TokenBucket.create(config)
        except Exception as e:
            logger.warning(f"Redis get_bucket error: {e}. Falling back to fresh bucket.")
            self._connected = False
            return TokenBucket.create(config)

    async def update_bucket(self, key: str, bucket: TokenBucket) -> None:
        """
        Update a token bucket in Redis.

        Uses HSET for atomic update and sets TTL to auto-expire stale buckets.
        """
        redis_client = await self._get_redis()
        if redis_client is None:
            return  # Silently fail - bucket update is not critical

        redis_key = self._make_key(key)
        try:
            # Store bucket data with TTL
            # TTL = 2x the refill time to cover worst case
            ttl_seconds = int(bucket.max_tokens / bucket.refill_rate * 2) + 60

            pipe = redis_client.pipeline()
            pipe.hset(
                redis_key,
                mapping={
                    "tokens": str(bucket.tokens),
                    "last_update": str(bucket.last_update),
                    "max_tokens": str(bucket.max_tokens),
                    "refill_rate": str(bucket.refill_rate),
                },
            )
            pipe.expire(redis_key, ttl_seconds)
            await pipe.execute()
        except Exception as e:
            logger.warning(f"Redis update_bucket error: {e}. Bucket update skipped.")
            self._connected = False

    async def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired buckets.

        With Redis, TTL handles expiration automatically, so this is a no-op.
        Returns 0 as Redis handles cleanup via TTL.
        """
        # Redis TTL handles expiration - nothing to do
        return 0

    async def consume_token_atomic(
        self, key: str, config: RateLimitConfig
    ) -> Tuple[bool, float, int]:
        """
        Atomically consume a token using Redis Lua script.

        This is more efficient than get_bucket + update_bucket as it uses
        a single round-trip to Redis with a Lua script for atomicity.

        Returns:
            Tuple of (allowed: bool, retry_after: float, remaining: int)
        """
        redis_client = await self._get_redis()
        if redis_client is None:
            # Fail open - allow the request
            return True, 0.0, config.max_requests

        redis_key = self._make_key(key)

        # Lua script for atomic token bucket operation
        # Note: redis.evalsha is the recommended method for Lua scripts in Redis
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local max_tokens = tonumber(ARGV[2])
        local refill_rate = tonumber(ARGV[3])
        local ttl_seconds = tonumber(ARGV[4])

        -- Get current bucket state
        local tokens = tonumber(redis.call('HGET', key, 'tokens'))
        local last_update = tonumber(redis.call('HGET', key, 'last_update'))

        -- Initialize if not exists
        if not tokens then
            tokens = max_tokens
            last_update = now
        end

        -- Refill tokens based on elapsed time
        local elapsed = now - last_update
        tokens = math.min(max_tokens, tokens + elapsed * refill_rate)

        -- Try to consume one token
        local allowed = 0
        local retry_after = 0

        if tokens >= 1 then
            tokens = tokens - 1
            allowed = 1
        else
            -- Calculate retry time
            local tokens_needed = 1 - tokens
            retry_after = tokens_needed / refill_rate
        end

        -- Update bucket state
        redis.call('HSET', key, 'tokens', tostring(tokens))
        redis.call('HSET', key, 'last_update', tostring(now))
        redis.call('HSET', key, 'max_tokens', tostring(max_tokens))
        redis.call('HSET', key, 'refill_rate', tostring(refill_rate))
        redis.call('EXPIRE', key, ttl_seconds)

        return {allowed, retry_after, math.floor(tokens)}
        """

        try:
            now = time.time()
            refill_rate = config.max_requests / config.window_seconds
            ttl_seconds = int(config.bucket_size / refill_rate * 2) + 60

            # Use evalsha for better performance with cached scripts
            result = await redis_client.eval(
                lua_script,
                1,
                redis_key,
                str(now),
                str(config.bucket_size),
                str(refill_rate),
                str(ttl_seconds),
            )

            allowed = bool(int(result[0]))
            retry_after = float(result[1])
            remaining = int(result[2])

            return allowed, retry_after, remaining
        except Exception as e:
            logger.warning(f"Redis consume_token_atomic error: {e}. Falling back to allow.")
            self._connected = False
            return True, 0.0, config.max_requests

    def get_stats(self) -> Dict:
        """Get storage statistics."""
        return {
            "backend": "redis",
            "connected": self._connected,
            "redis_url": self._redis_url.split("@")[-1] if "@" in self._redis_url else self._redis_url,
        }

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._redis = None
                self._connected = False


def create_rate_limit_storage(
    redis_url: Optional[str] = None,
    key_prefix: str = "rate_limit",
    connection_timeout: int = 5,
    socket_timeout: int = 5,
) -> InMemoryStorage | RedisStorage:
    """
    Factory function to create the appropriate rate limit storage backend.

    If redis_url is provided, creates a RedisStorage instance for distributed
    rate limiting. Otherwise, creates an InMemoryStorage instance for
    single-instance deployments.

    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
        key_prefix: Prefix for Redis keys to avoid collisions
        connection_timeout: Redis connection timeout in seconds
        socket_timeout: Redis socket timeout in seconds

    Returns:
        Rate limit storage instance (either RedisStorage or InMemoryStorage)
    """
    if redis_url:
        logger.info("Using Redis storage for rate limiting")
        return RedisStorage(
            redis_url=redis_url,
            key_prefix=key_prefix,
            connection_timeout=connection_timeout,
            socket_timeout=socket_timeout,
        )
    else:
        logger.info("Using in-memory storage for rate limiting (single instance only)")
        return InMemoryStorage()


# Path patterns for endpoint type classification
AUTH_PATHS = {"/api/auth/login", "/api/auth/register", "/api/auth/refresh"}
AI_PATHS_PREFIX = "/api/ai/"


def classify_endpoint(path: str) -> RateLimitType:
    """Classify an endpoint to determine its rate limit type."""
    # Normalize path
    path = path.rstrip("/")

    # Check auth endpoints
    if path in AUTH_PATHS:
        return RateLimitType.AUTH

    # Check AI endpoints
    if path.startswith(AI_PATHS_PREFIX) or path == "/api/ai":
        return RateLimitType.AI

    # Default to general
    return RateLimitType.GENERAL


def get_client_identifier(request: Request) -> str:
    """
    Get a unique identifier for the client.

    Uses a combination of:
    - User ID (if authenticated)
    - IP address (fallback)
    - User agent hash (additional fingerprinting)
    """
    # Try to get user ID from state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Fall back to IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Get the first IP in the chain (client IP)
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    return f"ip:{client_ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Implements token bucket algorithm with configurable limits per endpoint type.
    """

    def __init__(
        self,
        app,
        storage: Optional[RateLimitStorage] = None,
        rate_limits: Optional[Dict[RateLimitType, RateLimitConfig]] = None,
        exclude_paths: Optional[set] = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.storage = storage or InMemoryStorage()
        self.rate_limits = rate_limits or DEFAULT_RATE_LIMITS
        self.exclude_paths = exclude_paths or {"/", "/health", "/docs", "/openapi.json", "/redoc"}
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with rate limiting."""
        # Skip if disabled
        if not self.enabled:
            return await call_next(request)

        # Skip excluded paths
        path = request.url.path.rstrip("/") or "/"
        if path in self.exclude_paths:
            return await call_next(request)

        # Classify endpoint and get config
        limit_type = classify_endpoint(path)
        config = self.rate_limits.get(limit_type, self.rate_limits[RateLimitType.GENERAL])

        # Get client identifier and bucket key
        client_id = get_client_identifier(request)
        bucket_key = f"{limit_type.value}:{client_id}"

        # Use atomic operation for Redis (more efficient), fallback to get/update for in-memory
        if isinstance(self.storage, RedisStorage):
            # Atomic Redis operation - single round trip
            allowed, retry_after, remaining = await self.storage.consume_token_atomic(
                bucket_key, config
            )
        else:
            # In-memory storage - get, consume, update
            bucket = await self.storage.get_bucket(bucket_key, config)
            allowed, retry_after = bucket.consume(1)
            remaining = bucket.get_remaining()
            await self.storage.update_bucket(bucket_key, bucket)
            # Cleanup expired buckets periodically (Redis uses TTL)
            await self.storage.cleanup_expired()

        if not allowed:
            # Return 429 Too Many Requests
            retry_after_int = int(retry_after) + 1  # Round up
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too many requests",
                    "detail": f"Rate limit exceeded for {limit_type.value} endpoints",
                    "retry_after": retry_after_int,
                    "limit_type": limit_type.value,
                },
                headers={
                    "Retry-After": str(retry_after_int),
                    "X-RateLimit-Limit": str(config.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        # Note: 'remaining' is set in both branches of the if/else above
        response.headers["X-RateLimit-Limit"] = str(config.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Type"] = limit_type.value

        return response


class RateLimiterDependency:
    """
    FastAPI dependency for fine-grained rate limiting on specific endpoints.

    Supports both in-memory and Redis storage backends. Storage is initialized
    once and shared across all instances.

    Usage:
        @router.post("/expensive-operation")
        async def expensive_op(
            _: None = Depends(RateLimiterDependency(max_requests=5, window_seconds=60))
        ):
            ...
    """

    # Shared storage across all instances
    _storage: Optional[InMemoryStorage | RedisStorage] = None
    _storage_initialized: bool = False

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        key_prefix: str = "endpoint",
    ):
        self.config = RateLimitConfig(max_requests=max_requests, window_seconds=window_seconds)
        self.key_prefix = key_prefix

    @classmethod
    def initialize_storage(
        cls,
        redis_url: Optional[str] = None,
        key_prefix: str = "rate_limit:dep",
        connection_timeout: int = 5,
        socket_timeout: int = 5,
    ) -> None:
        """
        Initialize shared storage for all RateLimiterDependency instances.

        Call this during application startup to configure Redis storage.
        If not called, in-memory storage will be used by default.
        """
        if not cls._storage_initialized:
            cls._storage = create_rate_limit_storage(
                redis_url=redis_url,
                key_prefix=key_prefix,
                connection_timeout=connection_timeout,
                socket_timeout=socket_timeout,
            )
            cls._storage_initialized = True

    @classmethod
    def get_storage(cls) -> InMemoryStorage | RedisStorage:
        """Get the shared storage instance, initializing if needed."""
        if cls._storage is None:
            cls._storage = InMemoryStorage()
            cls._storage_initialized = True
        return cls._storage

    async def __call__(self, request: Request) -> None:
        """Check rate limit for this endpoint."""
        client_id = get_client_identifier(request)
        bucket_key = f"{self.key_prefix}:{request.url.path}:{client_id}"
        storage = self.get_storage()

        # Use atomic operation if available (Redis)
        if isinstance(storage, RedisStorage):
            allowed, retry_after, _ = await storage.consume_token_atomic(
                bucket_key, self.config
            )
        else:
            bucket = await storage.get_bucket(bucket_key, self.config)
            allowed, retry_after = bucket.consume(1)
            await storage.update_bucket(bucket_key, bucket)

        if not allowed:
            retry_after_int = int(retry_after) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many requests",
                    "retry_after": retry_after_int,
                },
                headers={"Retry-After": str(retry_after_int)},
            )


# Convenience function to create rate limiter dependency
def rate_limit(max_requests: int = 10, window_seconds: int = 60, key_prefix: str = "endpoint"):
    """Create a rate limiter dependency for use with FastAPI Depends."""
    return RateLimiterDependency(
        max_requests=max_requests, window_seconds=window_seconds, key_prefix=key_prefix
    )


# Pre-configured rate limiters for common use cases
auth_rate_limit = rate_limit(max_requests=5, window_seconds=60, key_prefix="auth")
ai_rate_limit = rate_limit(max_requests=20, window_seconds=60, key_prefix="ai")
file_upload_rate_limit = rate_limit(max_requests=10, window_seconds=60, key_prefix="upload")
