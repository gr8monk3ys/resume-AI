"""
Rate limiting middleware for FastAPI.

Implements token bucket algorithm with configurable rates per endpoint type:
- Auth endpoints: 5 requests/minute
- AI endpoints: 20 requests/minute
- General API: 100 requests/minute

Uses in-memory storage with Redis-ready interface for future scaling.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional, Protocol, Tuple

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


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

        # Get or create bucket
        bucket = await self.storage.get_bucket(bucket_key, config)

        # Try to consume a token
        allowed, retry_after = bucket.consume(1)

        # Update bucket
        await self.storage.update_bucket(bucket_key, bucket)

        # Cleanup expired buckets periodically
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
        remaining = bucket.get_remaining()
        response.headers["X-RateLimit-Limit"] = str(config.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Type"] = limit_type.value

        return response


class RateLimiterDependency:
    """
    FastAPI dependency for fine-grained rate limiting on specific endpoints.

    Usage:
        @router.post("/expensive-operation")
        async def expensive_op(
            _: None = Depends(RateLimiterDependency(max_requests=5, window_seconds=60))
        ):
            ...
    """

    # Shared storage across all instances
    _storage: Optional[InMemoryStorage] = None

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        key_prefix: str = "endpoint",
    ):
        self.config = RateLimitConfig(max_requests=max_requests, window_seconds=window_seconds)
        self.key_prefix = key_prefix

        # Initialize shared storage
        if RateLimiterDependency._storage is None:
            RateLimiterDependency._storage = InMemoryStorage()

    async def __call__(self, request: Request) -> None:
        """Check rate limit for this endpoint."""
        client_id = get_client_identifier(request)
        bucket_key = f"{self.key_prefix}:{request.url.path}:{client_id}"

        bucket = await self._storage.get_bucket(bucket_key, self.config)
        allowed, retry_after = bucket.consume(1)
        await self._storage.update_bucket(bucket_key, bucket)

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
