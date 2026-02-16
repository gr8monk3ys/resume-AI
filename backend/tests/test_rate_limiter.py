"""
Tests for rate limiting middleware.

Tests:
- Token bucket algorithm (create, consume, refill, remaining)
- InMemoryStorage (get, update, cleanup, stats)
- RateLimitMiddleware (allowed requests, 429 responses, headers)
- Endpoint classification (auth, AI, general)
- Client identifier extraction (user, IP, X-Forwarded-For)
- RateLimiterDependency (per-endpoint limiting)
- Rate limit configuration (defaults, custom, bucket sizing)
- Storage factory function
- RedisStorage error handling
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.middleware.rate_limiter import (
    AUTH_PATHS,
    DEFAULT_RATE_LIMITS,
    InMemoryStorage,
    RateLimitConfig,
    RateLimiterDependency,
    RateLimitMiddleware,
    RateLimitType,
    TokenBucket,
    classify_endpoint,
    create_rate_limit_storage,
    get_client_identifier,
    rate_limit,
)


# =============================================================================
# Token Bucket Unit Tests
# =============================================================================


class TestTokenBucketAlgorithm:
    """Tests for the token bucket rate limiting algorithm."""

    def test_create_bucket_with_default_size(self):
        """Test creating a bucket with default bucket_size."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        bucket = TokenBucket.create(config)

        assert bucket.max_tokens == 10
        assert bucket.tokens == 10
        assert bucket.refill_rate == pytest.approx(10 / 60)

    def test_create_bucket_with_custom_size(self):
        """Test creating a bucket with custom bucket_size."""
        config = RateLimitConfig(max_requests=10, window_seconds=60, bucket_size=20)
        bucket = TokenBucket.create(config)

        assert bucket.max_tokens == 20
        assert bucket.tokens == 20

    def test_consume_single_token(self):
        """Test consuming a single token."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        bucket = TokenBucket.create(config)

        allowed, retry_after = bucket.consume(1)

        assert allowed is True
        assert retry_after == 0.0
        assert bucket.tokens == 9

    def test_consume_multiple_tokens(self):
        """Test consuming multiple tokens in one call."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        bucket = TokenBucket.create(config)

        allowed, retry_after = bucket.consume(5)

        assert allowed is True
        assert retry_after == 0.0
        assert bucket.tokens == 5

    def test_consume_all_tokens(self):
        """Test consuming all available tokens."""
        config = RateLimitConfig(max_requests=3, window_seconds=60)
        bucket = TokenBucket.create(config)

        for i in range(3):
            allowed, _ = bucket.consume(1)
            assert allowed is True

        # Should be effectively empty now (may have tiny refill from elapsed time)
        assert bucket.tokens < 0.01

    def test_consume_exceeds_available_tokens(self):
        """Test that consuming more than available returns False."""
        config = RateLimitConfig(max_requests=2, window_seconds=60)
        bucket = TokenBucket.create(config)

        # Exhaust tokens
        bucket.consume(2)

        allowed, retry_after = bucket.consume(1)

        assert allowed is False
        assert retry_after > 0

    def test_retry_after_calculation(self):
        """Test that retry_after is correctly calculated."""
        config = RateLimitConfig(max_requests=10, window_seconds=10)
        bucket = TokenBucket.create(config)

        # Exhaust tokens
        bucket.consume(10)

        # Need 1 token, refill rate is 1/sec
        _, retry_after = bucket.consume(1)

        # Should be approximately 1 second (within tolerance for time elapsed)
        assert retry_after > 0
        assert retry_after <= 2.0

    def test_token_refill_over_time(self):
        """Test that tokens refill based on elapsed time."""
        config = RateLimitConfig(max_requests=10, window_seconds=10)
        bucket = TokenBucket.create(config)

        # Exhaust all tokens
        bucket.consume(10)
        assert bucket.tokens == 0

        # Simulate 2 seconds passing
        bucket.last_update -= 2

        # Should have ~2 tokens refilled (rate is 1/sec)
        allowed, _ = bucket.consume(1)
        assert allowed is True

    def test_tokens_do_not_exceed_max(self):
        """Test that tokens never exceed max_tokens after refill."""
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        bucket = TokenBucket.create(config)

        # Simulate long time passing
        bucket.last_update -= 1000

        allowed, _ = bucket.consume(1)
        assert allowed is True
        # After refill capped at max, consuming 1 should leave max - 1
        assert bucket.tokens <= bucket.max_tokens

    def test_get_remaining_tokens(self):
        """Test getting remaining token count with time elapsed."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        bucket = TokenBucket.create(config)

        bucket.consume(7)
        remaining = bucket.get_remaining()

        assert remaining == 3

    def test_get_remaining_includes_refill(self):
        """Test that get_remaining accounts for token refill."""
        config = RateLimitConfig(max_requests=10, window_seconds=10)
        bucket = TokenBucket.create(config)

        bucket.consume(10)
        # Simulate 5 seconds (should refill 5 tokens)
        bucket.last_update -= 5

        remaining = bucket.get_remaining()
        assert remaining == 5


# =============================================================================
# InMemoryStorage Tests
# =============================================================================


class TestInMemoryStorageOperations:
    """Tests for in-memory rate limit storage."""

    @pytest.mark.asyncio
    async def test_get_bucket_creates_new(self):
        """Test that a new bucket is created for unknown keys."""
        storage = InMemoryStorage()
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        bucket = await storage.get_bucket("new-key", config)

        assert bucket is not None
        assert bucket.max_tokens == 10
        assert bucket.tokens == 10

    @pytest.mark.asyncio
    async def test_get_bucket_returns_existing(self):
        """Test that an existing bucket is returned for known keys."""
        storage = InMemoryStorage()
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        bucket = await storage.get_bucket("key1", config)
        bucket.consume(3)
        await storage.update_bucket("key1", bucket)

        # Retrieve same key
        retrieved = await storage.get_bucket("key1", config)
        assert retrieved.tokens == 7

    @pytest.mark.asyncio
    async def test_update_bucket_persists(self):
        """Test that bucket updates are persisted."""
        storage = InMemoryStorage()
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        bucket = await storage.get_bucket("persist-key", config)
        bucket.tokens = 3
        await storage.update_bucket("persist-key", bucket)

        retrieved = await storage.get_bucket("persist-key", config)
        assert retrieved.tokens == 3

    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_old_buckets(self):
        """Test that cleanup removes old buckets."""
        storage = InMemoryStorage(cleanup_interval=0)
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        bucket = await storage.get_bucket("old-bucket", config)
        # Make it appear old
        bucket.last_update = time.time() - 7200  # 2 hours ago

        removed = await storage.cleanup_expired(max_age_seconds=3600)
        assert removed == 1

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent_buckets(self):
        """Test that cleanup keeps recently accessed buckets."""
        storage = InMemoryStorage(cleanup_interval=0)
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        # Create a fresh bucket
        await storage.get_bucket("fresh-bucket", config)

        removed = await storage.cleanup_expired(max_age_seconds=3600)
        assert removed == 0

    @pytest.mark.asyncio
    async def test_cleanup_respects_interval(self):
        """Test that cleanup only runs at configured intervals."""
        storage = InMemoryStorage(cleanup_interval=300)
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        bucket = await storage.get_bucket("test", config)
        bucket.last_update = time.time() - 7200

        # Cleanup should be skipped because interval has not passed
        removed = await storage.cleanup_expired(max_age_seconds=3600)
        assert removed == 0

    def test_get_stats_returns_counts(self):
        """Test that storage stats include bucket and lock counts."""
        storage = InMemoryStorage()
        stats = storage.get_stats()

        assert "total_buckets" in stats
        assert "total_locks" in stats
        assert stats["total_buckets"] == 0
        assert stats["total_locks"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_after_operations(self):
        """Test stats reflect storage state after operations."""
        storage = InMemoryStorage()
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        await storage.get_bucket("key1", config)
        await storage.get_bucket("key2", config)

        stats = storage.get_stats()
        assert stats["total_buckets"] == 2

    @pytest.mark.asyncio
    async def test_isolation_between_keys(self):
        """Test that different keys have independent buckets."""
        storage = InMemoryStorage()
        config = RateLimitConfig(max_requests=5, window_seconds=60)

        bucket1 = await storage.get_bucket("user:1", config)
        bucket2 = await storage.get_bucket("user:2", config)

        bucket1.consume(5)
        await storage.update_bucket("user:1", bucket1)

        # User 2 should still have all tokens
        bucket2_check = await storage.get_bucket("user:2", config)
        assert bucket2_check.tokens == 5


# =============================================================================
# Endpoint Classification Tests
# =============================================================================


class TestEndpointClassificationDetailed:
    """Tests for endpoint type classification."""

    def test_classify_login(self):
        """Test login endpoint classification."""
        assert classify_endpoint("/api/auth/login") == RateLimitType.AUTH

    def test_classify_register(self):
        """Test register endpoint classification."""
        assert classify_endpoint("/api/auth/register") == RateLimitType.AUTH

    def test_classify_refresh(self):
        """Test refresh endpoint classification."""
        assert classify_endpoint("/api/auth/refresh") == RateLimitType.AUTH

    def test_classify_ai_tailor(self):
        """Test AI tailor endpoint classification."""
        assert classify_endpoint("/api/ai/tailor-resume") == RateLimitType.AI

    def test_classify_ai_root(self):
        """Test AI root endpoint classification."""
        assert classify_endpoint("/api/ai") == RateLimitType.AI

    def test_classify_ai_grammar(self):
        """Test AI grammar check classification."""
        assert classify_endpoint("/api/ai/grammar-check") == RateLimitType.AI

    def test_classify_resumes(self):
        """Test resumes endpoint classification."""
        assert classify_endpoint("/api/resumes") == RateLimitType.GENERAL

    def test_classify_jobs(self):
        """Test jobs endpoint classification."""
        assert classify_endpoint("/api/jobs") == RateLimitType.GENERAL

    def test_classify_profile(self):
        """Test profile endpoint classification."""
        assert classify_endpoint("/api/profile") == RateLimitType.GENERAL

    def test_classify_trailing_slash(self):
        """Test classification with trailing slash."""
        assert classify_endpoint("/api/auth/login/") == RateLimitType.AUTH
        assert classify_endpoint("/api/ai/") == RateLimitType.AI

    def test_classify_unknown_path(self):
        """Test classification of unknown path."""
        assert classify_endpoint("/unknown/path") == RateLimitType.GENERAL

    def test_auth_paths_constant(self):
        """Test that AUTH_PATHS contains expected paths."""
        assert "/api/auth/login" in AUTH_PATHS
        assert "/api/auth/register" in AUTH_PATHS
        assert "/api/auth/refresh" in AUTH_PATHS


# =============================================================================
# Client Identifier Tests
# =============================================================================


class TestClientIdentifierExtraction:
    """Tests for client identifier extraction."""

    def test_authenticated_user_identifier(self):
        """Test identifier for authenticated user."""
        request = MagicMock()
        request.state.user_id = 42

        result = get_client_identifier(request)
        assert result == "user:42"

    def test_ip_identifier_fallback(self):
        """Test identifier falls back to IP when no user."""
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        result = get_client_identifier(request)
        assert result == "ip:10.0.0.1"

    def test_x_forwarded_for_identifier(self):
        """Test identifier uses X-Forwarded-For when present."""
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {"X-Forwarded-For": "203.0.113.50, 70.41.3.18"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = get_client_identifier(request)
        assert result == "ip:203.0.113.50"

    def test_no_client_info_identifier(self):
        """Test identifier when no client info available."""
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {}
        request.client = None

        result = get_client_identifier(request)
        assert result == "ip:unknown"


# =============================================================================
# Rate Limit Middleware Tests
# =============================================================================


class TestRateLimitMiddlewareIntegration:
    """Tests for the rate limit middleware integration."""

    @pytest.fixture
    def rate_limited_app(self):
        """Create an app with rate limiting enabled."""
        app = FastAPI()
        storage = InMemoryStorage()
        rate_limits = {
            RateLimitType.AUTH: RateLimitConfig(max_requests=2, window_seconds=60),
            RateLimitType.AI: RateLimitConfig(max_requests=3, window_seconds=60),
            RateLimitType.GENERAL: RateLimitConfig(max_requests=5, window_seconds=60),
        }
        app.add_middleware(
            RateLimitMiddleware,
            storage=storage,
            rate_limits=rate_limits,
            enabled=True,
        )

        @app.get("/api/test")
        def test_endpoint():
            return {"status": "ok"}

        @app.post("/api/auth/login")
        def login():
            return {"token": "abc"}

        @app.post("/api/ai/tailor-resume")
        def tailor():
            return {"result": "tailored"}

        @app.get("/health")
        def health():
            return {"status": "healthy"}

        return app

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, rate_limited_app):
        """Test that requests within the rate limit are allowed."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/test")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_429_when_limit_exceeded(self, rate_limited_app):
        """Test that 429 is returned when limit is exceeded."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Exhaust the 5-request general limit
            for _ in range(5):
                await client.get("/api/test")

            # This should be rate limited
            response = await client.get("/api/test")

        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_429_response_includes_retry_after(self, rate_limited_app):
        """Test that 429 response includes Retry-After header."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(5):
                await client.get("/api/test")

            response = await client.get("/api/test")

        assert response.status_code == 429
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_429_response_includes_rate_limit_headers(self, rate_limited_app):
        """Test that 429 response includes rate limit headers."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(5):
                await client.get("/api/test")

            response = await client.get("/api/test")

        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_successful_response_includes_rate_limit_headers(self, rate_limited_app):
        """Test that successful responses include rate limit headers."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/test")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Type" in response.headers

    @pytest.mark.asyncio
    async def test_excluded_paths_bypass_rate_limit(self, rate_limited_app):
        """Test that excluded paths are not rate limited."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Health endpoint should always work
            for _ in range(20):
                response = await client.get("/health")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_endpoint_has_lower_limit(self, rate_limited_app):
        """Test that auth endpoints have a lower rate limit (2 requests)."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Auth limit is 2
            for _ in range(2):
                await client.post("/api/auth/login")

            response = await client.post("/api/auth/login")

        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_429_response_body_format(self, rate_limited_app):
        """Test the structure of the 429 error response body."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(5):
                await client.get("/api/test")

            response = await client.get("/api/test")

        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "retry_after" in data
        assert "limit_type" in data

    @pytest.mark.asyncio
    async def test_disabled_middleware_allows_all(self):
        """Test that disabled middleware allows all requests."""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, enabled=False)

        @app.get("/api/test")
        def test_endpoint():
            return {"ok": True}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(100):
                response = await client.get("/api/test")
                assert response.status_code == 200


# =============================================================================
# Rate Limit Configuration Tests
# =============================================================================


class TestRateLimitConfigurationDetailed:
    """Tests for rate limit configuration objects."""

    def test_default_configs_exist_for_all_types(self):
        """Test that default configs exist for all rate limit types."""
        for limit_type in RateLimitType:
            assert limit_type in DEFAULT_RATE_LIMITS

    def test_auth_is_most_restrictive(self):
        """Test that auth limits are the most restrictive."""
        auth = DEFAULT_RATE_LIMITS[RateLimitType.AUTH]
        ai = DEFAULT_RATE_LIMITS[RateLimitType.AI]
        general = DEFAULT_RATE_LIMITS[RateLimitType.GENERAL]

        assert auth.max_requests < ai.max_requests
        assert ai.max_requests < general.max_requests

    def test_config_defaults_bucket_size_to_max_requests(self):
        """Test that bucket_size defaults to max_requests."""
        config = RateLimitConfig(max_requests=50, window_seconds=60)
        assert config.bucket_size == 50

    def test_config_custom_bucket_size(self):
        """Test that custom bucket_size is preserved."""
        config = RateLimitConfig(max_requests=50, window_seconds=60, bucket_size=100)
        assert config.bucket_size == 100

    def test_rate_limit_type_enum_values(self):
        """Test that RateLimitType enum has expected values."""
        assert RateLimitType.AUTH.value == "auth"
        assert RateLimitType.AI.value == "ai"
        assert RateLimitType.GENERAL.value == "general"


# =============================================================================
# Rate Limiter Dependency Tests
# =============================================================================


class TestRateLimiterDependencyDetailed:
    """Tests for per-endpoint rate limiter dependency."""

    @pytest.fixture(autouse=True)
    def reset_storage(self):
        """Reset shared storage between tests."""
        RateLimiterDependency._storage = None
        RateLimiterDependency._storage_initialized = False
        yield
        RateLimiterDependency._storage = None
        RateLimiterDependency._storage_initialized = False

    @pytest.fixture
    def app_with_dependency_limiter(self):
        """Create an app with rate-limited endpoint via dependency."""
        app = FastAPI()

        limiter = RateLimiterDependency(max_requests=3, window_seconds=60)

        @app.get("/limited")
        async def limited(request: Request, _: None = Depends(limiter)):
            return {"status": "ok"}

        @app.get("/unlimited")
        async def unlimited():
            return {"status": "ok"}

        return app

    @pytest.mark.asyncio
    async def test_dependency_allows_within_limit(self, app_with_dependency_limiter):
        """Test that dependency allows requests within limit."""
        transport = ASGITransport(app=app_with_dependency_limiter)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/limited")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dependency_blocks_over_limit(self, app_with_dependency_limiter):
        """Test that dependency returns 429 over limit."""
        transport = ASGITransport(app=app_with_dependency_limiter)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(3):
                await client.get("/limited")

            response = await client.get("/limited")

        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_dependency_does_not_affect_other_endpoints(
        self, app_with_dependency_limiter
    ):
        """Test that rate limiting on one endpoint does not affect others."""
        transport = ASGITransport(app=app_with_dependency_limiter)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Exhaust limited endpoint
            for _ in range(3):
                await client.get("/limited")

            # Unlimited endpoint should still work
            response = await client.get("/unlimited")
            assert response.status_code == 200

    def test_get_storage_initializes_in_memory(self):
        """Test that get_storage creates InMemoryStorage by default."""
        storage = RateLimiterDependency.get_storage()
        assert isinstance(storage, InMemoryStorage)

    def test_rate_limit_convenience_function(self):
        """Test the rate_limit convenience function."""
        limiter = rate_limit(max_requests=5, window_seconds=30)
        assert isinstance(limiter, RateLimiterDependency)
        assert limiter.config.max_requests == 5
        assert limiter.config.window_seconds == 30


# =============================================================================
# Storage Factory Tests
# =============================================================================


class TestStorageFactory:
    """Tests for the storage factory function."""

    def test_create_in_memory_storage_without_redis(self):
        """Test that InMemoryStorage is created when no Redis URL is provided."""
        storage = create_rate_limit_storage()
        assert isinstance(storage, InMemoryStorage)

    def test_create_in_memory_storage_with_none_redis(self):
        """Test that InMemoryStorage is created when Redis URL is None."""
        storage = create_rate_limit_storage(redis_url=None)
        assert isinstance(storage, InMemoryStorage)

    def test_create_redis_storage_with_url(self):
        """Test that RedisStorage is created when Redis URL is provided."""
        from app.middleware.rate_limiter import RedisStorage

        storage = create_rate_limit_storage(redis_url="redis://localhost:6379/0")
        assert isinstance(storage, RedisStorage)
