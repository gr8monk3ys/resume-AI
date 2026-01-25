"""
Tests for security middleware and utilities.

Tests:
- Rate limiting (token bucket algorithm, endpoint classification)
- Security headers (XSS protection, CSP, HSTS)
- Input sanitization (XSS, SQL injection, path traversal)
- Request ID middleware
- CORS configuration
- Utility functions (sanitize_string, escape_html, etc.)
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.middleware.rate_limiter import (
    DEFAULT_RATE_LIMITS,
    InMemoryStorage,
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimitType,
    RateLimiterDependency,
    TokenBucket,
    classify_endpoint,
    get_client_identifier,
)
from app.middleware.security import (
    InputSanitizationMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    escape_html_string,
    get_client_ip,
    get_user_agent,
    sanitize_string,
    strip_html_tags,
)


# =============================================================================
# Token Bucket Unit Tests
# =============================================================================


class TestTokenBucket:
    """Tests for TokenBucket class."""

    def test_create_from_config(self):
        """Test creating a token bucket from config."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        bucket = TokenBucket.create(config)

        assert bucket.max_tokens == 10
        assert bucket.tokens == 10
        assert bucket.refill_rate == 10 / 60  # tokens per second

    def test_consume_success(self):
        """Test successful token consumption."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        bucket = TokenBucket.create(config)

        allowed, retry_after = bucket.consume(1)
        assert allowed is True
        assert retry_after == 0.0
        assert bucket.tokens == 9

    def test_consume_multiple_tokens(self):
        """Test consuming multiple tokens at once."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        bucket = TokenBucket.create(config)

        allowed, retry_after = bucket.consume(5)
        assert allowed is True
        assert bucket.tokens == 5

    def test_consume_exceeds_limit(self):
        """Test consumption when not enough tokens."""
        config = RateLimitConfig(max_requests=2, window_seconds=60)
        bucket = TokenBucket.create(config)

        # Consume all tokens
        bucket.consume(2)
        allowed, retry_after = bucket.consume(1)

        assert allowed is False
        assert retry_after > 0

    def test_token_refill_over_time(self):
        """Test that tokens refill over time."""
        config = RateLimitConfig(max_requests=10, window_seconds=10)
        bucket = TokenBucket.create(config)

        # Consume all tokens
        bucket.consume(10)
        assert bucket.tokens == 0

        # Simulate time passing (1 second should refill 1 token)
        bucket.last_update -= 1  # Move last_update back 1 second

        allowed, _ = bucket.consume(1)
        assert allowed is True

    def test_get_remaining_tokens(self):
        """Test getting remaining token count."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        bucket = TokenBucket.create(config)

        bucket.consume(3)
        remaining = bucket.get_remaining()
        assert remaining == 7


# =============================================================================
# Rate Limit Storage Tests
# =============================================================================


class TestInMemoryStorage:
    """Tests for InMemoryStorage class."""

    @pytest.mark.asyncio
    async def test_get_bucket_creates_new(self):
        """Test that get_bucket creates a new bucket if none exists."""
        storage = InMemoryStorage()
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        bucket = await storage.get_bucket("test_key", config)
        assert bucket is not None
        assert bucket.max_tokens == 10

    @pytest.mark.asyncio
    async def test_get_bucket_returns_existing(self):
        """Test that get_bucket returns existing bucket."""
        storage = InMemoryStorage()
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        bucket1 = await storage.get_bucket("test_key", config)
        bucket1.consume(3)
        await storage.update_bucket("test_key", bucket1)

        bucket2 = await storage.get_bucket("test_key", config)
        assert bucket2.tokens == 7

    @pytest.mark.asyncio
    async def test_update_bucket(self):
        """Test updating a bucket."""
        storage = InMemoryStorage()
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        bucket = await storage.get_bucket("test_key", config)
        bucket.tokens = 5
        await storage.update_bucket("test_key", bucket)

        retrieved = await storage.get_bucket("test_key", config)
        assert retrieved.tokens == 5

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired buckets."""
        storage = InMemoryStorage(cleanup_interval=0)  # Allow immediate cleanup
        config = RateLimitConfig(max_requests=10, window_seconds=60)

        # Create a bucket
        bucket = await storage.get_bucket("old_key", config)
        # Make it appear old
        bucket.last_update = time.time() - 4000

        # Run cleanup
        removed = await storage.cleanup_expired(max_age_seconds=3600)
        assert removed == 1

    def test_get_stats(self):
        """Test getting storage statistics."""
        storage = InMemoryStorage()
        stats = storage.get_stats()

        assert "total_buckets" in stats
        assert "total_locks" in stats


# =============================================================================
# Endpoint Classification Tests
# =============================================================================


class TestEndpointClassification:
    """Tests for endpoint classification logic."""

    def test_classify_auth_endpoints(self):
        """Test that auth endpoints are correctly classified."""
        auth_paths = ["/api/auth/login", "/api/auth/register", "/api/auth/refresh"]

        for path in auth_paths:
            result = classify_endpoint(path)
            assert result == RateLimitType.AUTH, f"Expected AUTH for {path}"

    def test_classify_ai_endpoints(self):
        """Test that AI endpoints are correctly classified."""
        ai_paths = [
            "/api/ai/tailor-resume",
            "/api/ai/grammar-check",
            "/api/ai/interview-prep",
            "/api/ai",
        ]

        for path in ai_paths:
            result = classify_endpoint(path)
            assert result == RateLimitType.AI, f"Expected AI for {path}"

    def test_classify_general_endpoints(self):
        """Test that general endpoints are correctly classified."""
        general_paths = [
            "/api/resumes",
            "/api/jobs",
            "/api/profile",
            "/api/cover-letters",
            "/some/random/path",
        ]

        for path in general_paths:
            result = classify_endpoint(path)
            assert result == RateLimitType.GENERAL, f"Expected GENERAL for {path}"

    def test_classify_handles_trailing_slash(self):
        """Test that trailing slashes are handled correctly."""
        assert classify_endpoint("/api/auth/login/") == RateLimitType.AUTH
        assert classify_endpoint("/api/ai/") == RateLimitType.AI


# =============================================================================
# Client Identifier Tests
# =============================================================================


class TestClientIdentifier:
    """Tests for client identifier extraction."""

    def test_get_client_identifier_with_user_id(self):
        """Test identifier when user is authenticated."""
        request = MagicMock()
        request.state.user_id = 123

        result = get_client_identifier(request)
        assert result == "user:123"

    def test_get_client_identifier_with_ip(self):
        """Test identifier falls back to IP."""
        request = MagicMock()
        request.state = MagicMock(spec=[])  # No user_id
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"

        result = get_client_identifier(request)
        assert result == "ip:192.168.1.1"

    def test_get_client_identifier_with_forwarded_header(self):
        """Test identifier uses X-Forwarded-For header."""
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = get_client_identifier(request)
        assert result == "ip:10.0.0.1"


# =============================================================================
# Security Header Tests
# =============================================================================


class TestSecurityHeaders:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.fixture
    def app_with_security_headers(self):
        """Create a test app with security headers middleware."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        return app

    @pytest.mark.asyncio
    async def test_security_headers_present(self, app_with_security_headers):
        """Test that security headers are added to responses."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "strict-origin-when-cross-origin" in response.headers.get("Referrer-Policy", "")

    @pytest.mark.asyncio
    async def test_csp_header_present(self, app_with_security_headers):
        """Test that CSP header is present."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert "Content-Security-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_cache_control_headers(self, app_with_security_headers):
        """Test that cache control headers are set."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert "no-store" in response.headers.get("Cache-Control", "")


# =============================================================================
# Request ID Middleware Tests
# =============================================================================


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware."""

    @pytest.fixture
    def app_with_request_id(self):
        """Create a test app with request ID middleware."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        def test_endpoint(request: Request):
            return {"request_id": getattr(request.state, "request_id", None)}

        return app

    @pytest.mark.asyncio
    async def test_generates_request_id(self, app_with_request_id):
        """Test that request ID is generated if not provided."""
        transport = ASGITransport(app=app_with_request_id)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    @pytest.mark.asyncio
    async def test_uses_provided_request_id(self, app_with_request_id):
        """Test that provided request ID is used."""
        transport = ASGITransport(app=app_with_request_id)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/test", headers={"X-Request-ID": "my-custom-id-123"}
            )

        assert response.headers["X-Request-ID"] == "my-custom-id-123"

    @pytest.mark.asyncio
    async def test_rejects_invalid_request_id(self, app_with_request_id):
        """Test that invalid request IDs are rejected and replaced."""
        transport = ASGITransport(app=app_with_request_id)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Invalid: contains special characters
            response = await client.get(
                "/test", headers={"X-Request-ID": "invalid<script>id"}
            )

        # Should be replaced with a valid UUID
        assert response.headers["X-Request-ID"] != "invalid<script>id"
        assert len(response.headers["X-Request-ID"]) > 0


# =============================================================================
# Input Sanitization Tests
# =============================================================================


class TestInputSanitization:
    """Tests for input sanitization middleware and utilities."""

    @pytest.fixture
    def app_with_sanitization(self):
        """Create a test app with input sanitization middleware."""
        app = FastAPI()
        app.add_middleware(
            InputSanitizationMiddleware,
            enabled=True,
            log_violations=False,
            block_on_violation=True,
        )

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        return app

    @pytest.mark.asyncio
    async def test_blocks_xss_in_query_params(self, app_with_sanitization):
        """Test that XSS in query params is blocked."""
        transport = ASGITransport(app=app_with_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test?input=<script>alert(1)</script>")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_blocks_sql_injection_patterns(self, app_with_sanitization):
        """Test that SQL injection patterns are blocked."""
        transport = ASGITransport(app=app_with_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test?id=1' OR '1'='1")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_blocks_path_traversal(self, app_with_sanitization):
        """Test that path traversal is blocked."""
        transport = ASGITransport(app=app_with_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test?file=../../../etc/passwd")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_allows_safe_requests(self, app_with_sanitization):
        """Test that safe requests are allowed."""
        transport = ASGITransport(app=app_with_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test?name=John&age=30")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skips_excluded_paths(self):
        """Test that excluded paths are not checked."""
        app = FastAPI()
        app.add_middleware(
            InputSanitizationMiddleware,
            enabled=True,
            block_on_violation=True,
            skip_paths={"/health"},
        )

        @app.get("/health")
        def health():
            return {"status": "ok"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Should be allowed even with dangerous pattern
            response = await client.get("/health?test=<script>")

        assert response.status_code == 200


# =============================================================================
# Sanitization Utility Function Tests
# =============================================================================


class TestSanitizationUtilities:
    """Tests for sanitization utility functions."""

    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        result = sanitize_string("  hello world  ")
        assert result == "hello world"

    def test_sanitize_string_max_length(self):
        """Test string truncation to max length."""
        long_string = "a" * 2000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100

    def test_sanitize_string_escapes_html(self):
        """Test that HTML is escaped by default."""
        result = sanitize_string("<script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result
        assert "&lt;" in result

    def test_sanitize_string_removes_null_bytes(self):
        """Test that null bytes are removed."""
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result
        assert result == "helloworld"

    def test_escape_html_string(self):
        """Test HTML escaping."""
        result = escape_html_string('<div class="test">Hello & World</div>')
        assert result == "&lt;div class=&quot;test&quot;&gt;Hello &amp; World&lt;/div&gt;"

    def test_strip_html_tags(self):
        """Test HTML tag stripping."""
        result = strip_html_tags("<p>Hello <b>World</b></p>")
        assert result == "Hello World"

    def test_strip_html_handles_empty(self):
        """Test strip_html_tags with empty string."""
        assert strip_html_tags("") == ""
        assert strip_html_tags(None) == ""


# =============================================================================
# IP and User Agent Extraction Tests
# =============================================================================


class TestRequestHelpers:
    """Tests for request helper functions."""

    def test_get_client_ip_direct(self):
        """Test getting direct client IP."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        result = get_client_ip(request)
        assert result == "192.168.1.100"

    def test_get_client_ip_forwarded(self):
        """Test getting IP from X-Forwarded-For."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1, 127.0.0.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = get_client_ip(request)
        assert result == "10.0.0.1"

    def test_get_client_ip_no_client(self):
        """Test getting IP when no client info."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        result = get_client_ip(request)
        assert result == "unknown"

    def test_get_user_agent(self):
        """Test getting user agent."""
        request = MagicMock()
        request.headers = {"User-Agent": "Mozilla/5.0 Test Browser"}

        result = get_user_agent(request)
        assert result == "Mozilla/5.0 Test Browser"

    def test_get_user_agent_truncates_long(self):
        """Test that long user agents are truncated."""
        request = MagicMock()
        request.headers = {"User-Agent": "x" * 1000}

        result = get_user_agent(request)
        assert len(result) == 500

    def test_get_user_agent_missing(self):
        """Test getting user agent when missing."""
        request = MagicMock()
        request.headers = {}

        result = get_user_agent(request)
        assert result == "unknown"


# =============================================================================
# Rate Limit Configuration Tests
# =============================================================================


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_default_configs_exist(self):
        """Test that default configs exist for all types."""
        assert RateLimitType.AUTH in DEFAULT_RATE_LIMITS
        assert RateLimitType.AI in DEFAULT_RATE_LIMITS
        assert RateLimitType.GENERAL in DEFAULT_RATE_LIMITS

    def test_auth_limits_are_restrictive(self):
        """Test that auth limits are more restrictive."""
        auth_config = DEFAULT_RATE_LIMITS[RateLimitType.AUTH]
        general_config = DEFAULT_RATE_LIMITS[RateLimitType.GENERAL]

        assert auth_config.max_requests < general_config.max_requests

    def test_ai_limits_are_moderate(self):
        """Test that AI limits are between auth and general."""
        auth_config = DEFAULT_RATE_LIMITS[RateLimitType.AUTH]
        ai_config = DEFAULT_RATE_LIMITS[RateLimitType.AI]
        general_config = DEFAULT_RATE_LIMITS[RateLimitType.GENERAL]

        assert auth_config.max_requests < ai_config.max_requests < general_config.max_requests

    def test_config_bucket_size_defaults_to_max_requests(self):
        """Test that bucket_size defaults to max_requests."""
        config = RateLimitConfig(max_requests=50, window_seconds=60)
        assert config.bucket_size == 50


# =============================================================================
# Rate Limiter Dependency Tests
# =============================================================================


class TestRateLimiterDependency:
    """Tests for RateLimiterDependency."""

    @pytest.fixture
    def app_with_rate_limited_endpoint(self):
        """Create app with rate-limited endpoint."""
        from fastapi import Depends

        app = FastAPI()

        limiter = RateLimiterDependency(max_requests=2, window_seconds=60)

        @app.get("/limited")
        async def limited_endpoint(request: Request, _: None = Depends(limiter)):
            return {"status": "ok"}

        return app

    @pytest.mark.asyncio
    async def test_allows_within_limit(self, app_with_rate_limited_endpoint):
        """Test that requests within limit are allowed."""
        transport = ASGITransport(app=app_with_rate_limited_endpoint)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/limited")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_blocks_exceeding_limit(self, app_with_rate_limited_endpoint):
        """Test that requests exceeding limit are blocked."""
        transport = ASGITransport(app=app_with_rate_limited_endpoint)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Make requests up to limit
            for _ in range(2):
                await client.get("/limited")

            # This should be blocked
            response = await client.get("/limited")

        assert response.status_code == 429


# =============================================================================
# Integration Tests
# =============================================================================


class TestMiddlewareIntegration:
    """Integration tests for middleware chain."""

    @pytest.fixture
    def fully_configured_app(self):
        """Create app with all middleware."""
        app = FastAPI()

        # Add middleware in order
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestIDMiddleware)
        app.add_middleware(
            InputSanitizationMiddleware,
            enabled=True,
            block_on_violation=False,  # Don't block, just log
        )

        @app.get("/api/test")
        def test_endpoint(request: Request):
            return {
                "request_id": getattr(request.state, "request_id", None),
                "violations": getattr(request.state, "security_violations", []),
            }

        return app

    @pytest.mark.asyncio
    async def test_middleware_chain_works(self, fully_configured_app):
        """Test that all middleware work together."""
        transport = ASGITransport(app=fully_configured_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/test")

        assert response.status_code == 200

        # Security headers present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

        # Request ID present
        assert "X-Request-ID" in response.headers

        # Response body has request_id
        data = response.json()
        assert data["request_id"] is not None

    @pytest.mark.asyncio
    async def test_violations_recorded_in_state(self, fully_configured_app):
        """Test that security violations are recorded in request state."""
        transport = ASGITransport(app=fully_configured_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Request with dangerous pattern (but not blocked)
            response = await client.get("/api/test?input=<script>test</script>")

        # Request should succeed (not blocking)
        assert response.status_code == 200

        # Violations should be recorded
        data = response.json()
        assert len(data["violations"]) > 0
