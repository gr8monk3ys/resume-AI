"""
Tests for app.middleware.rate_limiter beyond the unit basics in test_middleware.py.

Tests:
- TokenBucket invariants under a deterministic clock (randomised op sequences)
- InMemoryStorage cleanup interval gating and lock eviction
- RateLimitMiddleware dispatch: headers, 429 response, exclusions, per-type buckets
- RedisStorage fail-open behaviour, bucket deserialisation, credential redaction
- create_rate_limit_storage and RateLimiterDependency storage selection
"""

import random
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware import rate_limiter
from app.middleware.rate_limiter import (
    InMemoryStorage,
    RateLimitConfig,
    RateLimiterDependency,
    RateLimitMiddleware,
    RateLimitType,
    RedisStorage,
    TokenBucket,
    create_rate_limit_storage,
)

# Port 1 is never a Redis server; connecting to it is refused immediately.
UNREACHABLE_REDIS_URL = "redis://user:s3cret@127.0.0.1:1/0"


class FakeClock:
    """Deterministic stand-in for the ``time`` module used by rate_limiter."""

    def __init__(self, start: float = 1_000_000.0):
        self.now = start

    def time(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(rate_limiter, "time", fake)
    return fake


# =============================================================================
# TokenBucket invariants
# =============================================================================


class TestTokenBucketInvariants:
    """Randomised sequences checked against an independent reference model."""

    @pytest.mark.parametrize("seed", range(25))
    def test_matches_reference_model(self, clock, seed):
        rng = random.Random(seed)
        max_requests = rng.randint(1, 50)
        window = rng.randint(1, 120)
        config = RateLimitConfig(max_requests=max_requests, window_seconds=window)
        bucket = TokenBucket.create(config)

        rate = max_requests / window
        model_tokens = float(max_requests)

        for _ in range(200):
            elapsed = rng.choice([0.0, rng.uniform(0, 2), rng.uniform(0, window * 2)])
            clock.advance(elapsed)
            model_tokens = min(max_requests, model_tokens + elapsed * rate)

            wanted = rng.randint(1, max(1, max_requests // 2 + 1))
            allowed, retry_after = bucket.consume(wanted)

            if model_tokens >= wanted:
                assert allowed is True
                assert retry_after == 0.0
                model_tokens -= wanted
            else:
                assert allowed is False
                assert retry_after == pytest.approx((wanted - model_tokens) / rate)

            assert bucket.tokens == pytest.approx(model_tokens)
            assert 0.0 <= bucket.tokens <= bucket.max_tokens
            assert bucket.last_update == clock.now

    def test_retry_after_is_exactly_enough_to_succeed(self, clock):
        config = RateLimitConfig(max_requests=3, window_seconds=30)
        bucket = TokenBucket.create(config)
        bucket.consume(3)

        allowed, retry_after = bucket.consume(1)
        assert allowed is False
        assert retry_after == pytest.approx(10.0)

        clock.advance(retry_after)
        allowed, _ = bucket.consume(1)
        assert allowed is True

    def test_refill_is_capped_at_bucket_size(self, clock):
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        bucket = TokenBucket.create(config)
        bucket.consume(5)

        clock.advance(10_000)
        assert bucket.get_remaining() == 5

        allowed, _ = bucket.consume(6)
        assert allowed is False
        assert bucket.tokens == 5

    def test_get_remaining_does_not_mutate_state(self, clock):
        config = RateLimitConfig(max_requests=10, window_seconds=10)
        bucket = TokenBucket.create(config)
        bucket.consume(10)
        clock.advance(2.5)

        assert bucket.get_remaining() == 2
        assert bucket.tokens == 0
        assert bucket.last_update == clock.now - 2.5

    def test_explicit_bucket_size_allows_larger_burst(self):
        config = RateLimitConfig(max_requests=2, window_seconds=60, bucket_size=7)
        bucket = TokenBucket.create(config)

        assert bucket.max_tokens == 7
        assert bucket.refill_rate == pytest.approx(2 / 60)
        allowed, _ = bucket.consume(7)
        assert allowed is True


# =============================================================================
# InMemoryStorage cleanup
# =============================================================================


class TestInMemoryStorageCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_skipped_until_interval_elapses(self, clock):
        storage = InMemoryStorage(cleanup_interval=300)
        config = RateLimitConfig(max_requests=1, window_seconds=1)
        await storage.get_bucket("stale", config)

        clock.advance(299)
        assert await storage.cleanup_expired(max_age_seconds=10) == 0
        assert storage.get_stats()["total_buckets"] == 1

        clock.advance(2)
        assert await storage.cleanup_expired(max_age_seconds=10) == 1
        assert storage.get_stats() == {"total_buckets": 0, "total_locks": 0}

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent_buckets(self, clock):
        storage = InMemoryStorage(cleanup_interval=0)
        config = RateLimitConfig(max_requests=1, window_seconds=1)
        await storage.get_bucket("old", config)
        clock.advance(100)
        await storage.get_bucket("fresh", config)
        clock.advance(1)

        removed = await storage.cleanup_expired(max_age_seconds=50)

        assert removed == 1
        assert set(storage._buckets) == {"fresh"}
        assert set(storage._locks) == {"fresh"}


# =============================================================================
# RateLimitMiddleware dispatch
# =============================================================================


def _build_app(**middleware_kwargs) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, **middleware_kwargs)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/api/auth/login")
    async def login():
        return {"ok": True}

    @app.get("/api/ai/analyze")
    async def analyze():
        return {"ok": True}

    @app.get("/api/jobs")
    async def jobs():
        return {"ok": True}

    return app


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_success_response_carries_rate_limit_headers(self):
        app = _build_app()
        async with _client(app) as client:
            response = await client.get("/api/jobs")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "99"
        assert response.headers["X-RateLimit-Type"] == "general"

    @pytest.mark.asyncio
    async def test_auth_endpoint_returns_429_after_bucket_exhausted(self):
        app = _build_app()
        async with _client(app) as client:
            remaining = [
                (await client.post("/api/auth/login")).headers["X-RateLimit-Remaining"]
                for _ in range(5)
            ]
            blocked = await client.post("/api/auth/login")

        assert remaining == ["4", "3", "2", "1", "0"]
        assert blocked.status_code == 429
        body = blocked.json()
        assert body["error"] == "Too many requests"
        assert body["limit_type"] == "auth"
        assert body["detail"] == "Rate limit exceeded for auth endpoints"
        # 5 per 60s => one token every 12s; int(~12) + 1 rounds up
        assert body["retry_after"] in (12, 13)
        assert blocked.headers["Retry-After"] == str(body["retry_after"])
        assert blocked.headers["X-RateLimit-Limit"] == "5"
        assert blocked.headers["X-RateLimit-Remaining"] == "0"
        assert "X-RateLimit-Type" not in blocked.headers

    @pytest.mark.asyncio
    async def test_limit_types_use_independent_buckets(self):
        limits = {
            RateLimitType.AUTH: RateLimitConfig(max_requests=1, window_seconds=60),
            RateLimitType.AI: RateLimitConfig(max_requests=1, window_seconds=60),
            RateLimitType.GENERAL: RateLimitConfig(max_requests=1, window_seconds=60),
        }
        app = _build_app(rate_limits=limits)
        async with _client(app) as client:
            assert (await client.post("/api/auth/login")).status_code == 200
            assert (await client.post("/api/auth/login")).status_code == 429
            ai = await client.get("/api/ai/analyze")
            general = await client.get("/api/jobs")

        assert ai.status_code == 200
        assert ai.headers["X-RateLimit-Type"] == "ai"
        assert general.status_code == 200
        assert general.headers["X-RateLimit-Type"] == "general"

    @pytest.mark.asyncio
    async def test_missing_type_config_falls_back_to_general(self):
        limits = {RateLimitType.GENERAL: RateLimitConfig(max_requests=1, window_seconds=60)}
        app = _build_app(rate_limits=limits)
        async with _client(app) as client:
            first = await client.get("/api/ai/analyze")
            second = await client.get("/api/ai/analyze")

        assert first.headers["X-RateLimit-Limit"] == "1"
        assert first.headers["X-RateLimit-Type"] == "ai"
        assert second.status_code == 429

    @pytest.mark.asyncio
    async def test_excluded_path_and_trailing_slash_bypass_limits(self):
        limits = {RateLimitType.GENERAL: RateLimitConfig(max_requests=1, window_seconds=60)}
        app = _build_app(rate_limits=limits)
        async with _client(app) as client:
            responses = [await client.get("/health") for _ in range(3)]

        assert [r.status_code for r in responses] == [200, 200, 200]
        assert all("X-RateLimit-Limit" not in r.headers for r in responses)

    @pytest.mark.asyncio
    async def test_disabled_middleware_never_limits(self):
        limits = {RateLimitType.GENERAL: RateLimitConfig(max_requests=1, window_seconds=60)}
        app = _build_app(rate_limits=limits, enabled=False)
        async with _client(app) as client:
            responses = [await client.get("/api/jobs") for _ in range(3)]

        assert [r.status_code for r in responses] == [200, 200, 200]
        assert "X-RateLimit-Limit" not in responses[-1].headers

    @pytest.mark.asyncio
    async def test_unreachable_redis_storage_fails_open(self):
        limits = {RateLimitType.GENERAL: RateLimitConfig(max_requests=1, window_seconds=60)}
        storage = RedisStorage(UNREACHABLE_REDIS_URL, connection_timeout=1, socket_timeout=1)
        app = _build_app(rate_limits=limits, storage=storage)
        async with _client(app) as client:
            responses = [await client.get("/api/jobs") for _ in range(3)]

        assert [r.status_code for r in responses] == [200, 200, 200]
        assert responses[0].headers["X-RateLimit-Remaining"] == "1"


# =============================================================================
# RedisStorage
# =============================================================================


class FakeRedisHash:
    """Minimal async client exposing only ``hgetall``, for deserialisation tests."""

    def __init__(self, data=None, error: Exception | None = None):
        self.data = data or {}
        self.error = error
        self.requested_keys: list[str] = []

    async def hgetall(self, key):
        self.requested_keys.append(key)
        if self.error:
            raise self.error
        return self.data


def _connected_storage(client) -> RedisStorage:
    storage = RedisStorage("redis://localhost:6379/0", key_prefix="rl")
    storage._redis = client
    storage._connected = True
    return storage


class TestRedisStorage:
    @pytest.mark.asyncio
    async def test_unreachable_server_fails_open_everywhere(self, clock):
        storage = RedisStorage(UNREACHABLE_REDIS_URL, connection_timeout=1, socket_timeout=1)
        config = RateLimitConfig(max_requests=4, window_seconds=60)

        bucket = await storage.get_bucket("k", config)
        assert bucket.tokens == 4
        assert bucket.last_update == clock.now

        assert await storage.consume_token_atomic("k", config) == (True, 0.0, 4)
        assert await storage.update_bucket("k", bucket) is None
        assert storage.get_stats()["connected"] is False

    @pytest.mark.asyncio
    async def test_reconnect_attempts_are_throttled(self, clock, monkeypatch):
        attempts = []

        def failing_from_url(*args, **kwargs):
            attempts.append(args)
            raise ConnectionError("down")

        import redis.asyncio

        monkeypatch.setattr(redis.asyncio, "from_url", failing_from_url)
        storage = RedisStorage("redis://localhost:6379/0")

        assert await storage._get_redis() is None
        clock.advance(4.9)
        assert await storage._get_redis() is None
        assert len(attempts) == 1

        clock.advance(0.2)
        assert await storage._get_redis() is None
        assert len(attempts) == 2

    @pytest.mark.asyncio
    async def test_get_bucket_deserialises_stored_hash(self):
        client = FakeRedisHash(
            {"tokens": "2.5", "last_update": "123.0", "max_tokens": "9", "refill_rate": "0.25"}
        )
        storage = _connected_storage(client)

        bucket = await storage.get_bucket("user:1", RateLimitConfig(5, 60))

        assert client.requested_keys == ["rl:user:1"]
        assert bucket == TokenBucket(tokens=2.5, last_update=123.0, max_tokens=9, refill_rate=0.25)

    @pytest.mark.asyncio
    async def test_get_bucket_fills_missing_fields_from_config(self, clock):
        storage = _connected_storage(FakeRedisHash({"tokens": "1"}))

        bucket = await storage.get_bucket("k", RateLimitConfig(max_requests=6, window_seconds=3))

        assert bucket.tokens == 1.0
        assert bucket.last_update == clock.now
        assert bucket.max_tokens == 6
        assert bucket.refill_rate == pytest.approx(2.0)

    @pytest.mark.asyncio
    async def test_get_bucket_empty_hash_creates_fresh_bucket(self):
        storage = _connected_storage(FakeRedisHash({}))

        bucket = await storage.get_bucket("k", RateLimitConfig(max_requests=3, window_seconds=60))

        assert bucket.tokens == 3
        assert storage._connected is True

    @pytest.mark.asyncio
    async def test_get_bucket_error_returns_fresh_bucket_and_marks_disconnected(self):
        storage = _connected_storage(FakeRedisHash(error=RuntimeError("boom")))

        bucket = await storage.get_bucket("k", RateLimitConfig(max_requests=3, window_seconds=60))

        assert bucket.tokens == 3
        assert storage._connected is False

    @pytest.mark.asyncio
    async def test_cleanup_is_a_noop(self):
        storage = RedisStorage("redis://localhost:6379/0")
        assert await storage.cleanup_expired() == 0

    @pytest.mark.asyncio
    async def test_close_without_connection_is_safe(self):
        storage = RedisStorage("redis://localhost:6379/0")
        await storage.close()
        assert storage._redis is None
        assert storage._connected is False

    @pytest.mark.parametrize(
        ("url", "shown"),
        [
            ("redis://user:pw@cache.internal:6379/0", "cache.internal:6379/0"),
            ("redis://cache.internal:6379/0", "redis://cache.internal:6379/0"),
        ],
    )
    def test_stats_never_expose_credentials(self, url, shown):
        stats = RedisStorage(url).get_stats()
        assert stats == {"backend": "redis", "connected": False, "redis_url": shown}

    def test_make_key_uses_prefix(self):
        assert RedisStorage("redis://x", key_prefix="p")._make_key("ai:user:1") == "p:ai:user:1"


# =============================================================================
# Storage factory and dependency storage selection
# =============================================================================


class TestStorageSelection:
    @pytest.mark.parametrize("redis_url", [None, ""])
    def test_factory_defaults_to_in_memory(self, redis_url):
        assert isinstance(create_rate_limit_storage(redis_url=redis_url), InMemoryStorage)

    def test_factory_builds_redis_storage_with_settings(self):
        storage = create_rate_limit_storage(
            redis_url="redis://h:1/0", key_prefix="x", connection_timeout=2, socket_timeout=3
        )
        assert isinstance(storage, RedisStorage)
        assert storage._key_prefix == "x"
        assert storage._connection_timeout == 2
        assert storage._socket_timeout == 3

    def test_initialize_storage_only_applies_once(self, monkeypatch):
        monkeypatch.setattr(RateLimiterDependency, "_storage", None)
        monkeypatch.setattr(RateLimiterDependency, "_storage_initialized", False)

        RateLimiterDependency.initialize_storage(redis_url="redis://h:1/0")
        first = RateLimiterDependency.get_storage()
        RateLimiterDependency.initialize_storage(redis_url=None)

        assert isinstance(first, RedisStorage)
        assert first._key_prefix == "rate_limit:dep"
        assert RateLimiterDependency.get_storage() is first

    def test_get_storage_lazily_defaults_to_in_memory(self, monkeypatch):
        monkeypatch.setattr(RateLimiterDependency, "_storage", None)
        monkeypatch.setattr(RateLimiterDependency, "_storage_initialized", False)

        storage = RateLimiterDependency.get_storage()

        assert isinstance(storage, InMemoryStorage)
        assert RateLimiterDependency._storage_initialized is True
        assert RateLimiterDependency.get_storage() is storage

    @pytest.mark.asyncio
    async def test_dependency_with_unreachable_redis_fails_open(self, monkeypatch):
        storage = RedisStorage(UNREACHABLE_REDIS_URL, connection_timeout=1, socket_timeout=1)
        monkeypatch.setattr(RateLimiterDependency, "_storage", storage)
        limiter = RateLimiterDependency(max_requests=1, window_seconds=60)
        request = SimpleNamespace(
            state=SimpleNamespace(user_id=7), url=SimpleNamespace(path="/api/x")
        )

        for _ in range(3):
            assert await limiter(request) is None
