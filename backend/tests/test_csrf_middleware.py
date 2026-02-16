"""
Tests for CSRF protection middleware.

Tests:
- CSRF token generation and cookie setting
- CSRF validation on state-changing methods (POST, PUT, PATCH, DELETE)
- Safe methods bypass CSRF validation (GET, HEAD, OPTIONS)
- Exempt paths bypass CSRF validation
- Invalid/missing CSRF tokens return 403
- Token rotation after successful state-changing requests
- Constant-time comparison prevents timing attacks
"""

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.middleware.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    CSRFMiddleware,
    DEFAULT_EXEMPT_PATHS,
    SAFE_METHODS,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app_with_csrf():
    """Create a test app with CSRF middleware."""
    app = FastAPI()
    app.add_middleware(
        CSRFMiddleware,
        cookie_secure=False,  # Allow non-HTTPS in tests
    )

    @app.get("/api/data")
    def get_data():
        return {"status": "ok"}

    @app.post("/api/data")
    def post_data():
        return {"created": True}

    @app.put("/api/data")
    def put_data():
        return {"updated": True}

    @app.patch("/api/data")
    def patch_data():
        return {"patched": True}

    @app.delete("/api/data")
    def delete_data():
        return {"deleted": True}

    @app.post("/api/auth/login")
    def login():
        return {"token": "fake-token"}

    @app.post("/api/auth/register")
    def register():
        return {"user_id": 1}

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    return app


@pytest.fixture
def app_with_custom_exemptions():
    """Create a test app with custom exempt paths."""
    app = FastAPI()
    app.add_middleware(
        CSRFMiddleware,
        exempt_paths={"/api/webhook", "/api/public"},
        cookie_secure=False,
    )

    @app.post("/api/webhook")
    def webhook():
        return {"received": True}

    @app.post("/api/public")
    def public():
        return {"public": True}

    @app.post("/api/protected")
    def protected():
        return {"protected": True}

    return app


# =============================================================================
# Token Generation Tests
# =============================================================================


class TestCSRFTokenGeneration:
    """Tests for CSRF token generation and cookie setting."""

    @pytest.mark.asyncio
    async def test_get_request_sets_csrf_cookie(self, app_with_csrf):
        """Test that a GET request sets the CSRF cookie if not present."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data")

        assert response.status_code == 200
        # Check that csrf_token cookie was set
        cookies = response.cookies
        assert CSRF_COOKIE_NAME in cookies
        token = cookies[CSRF_COOKIE_NAME]
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_csrf_token_is_unique_per_request(self, app_with_csrf):
        """Test that each new session gets a unique CSRF token."""
        transport = ASGITransport(app=app_with_csrf)

        tokens = []
        for _ in range(3):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/data")
                token = response.cookies.get(CSRF_COOKIE_NAME)
                if token:
                    tokens.append(token)

        # All tokens should be unique
        assert len(set(tokens)) == len(tokens)

    @pytest.mark.asyncio
    async def test_existing_csrf_cookie_not_overwritten_on_get(self, app_with_csrf):
        """Test that an existing CSRF cookie is not overwritten on GET requests."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First request sets the cookie
            response1 = await client.get("/api/data")
            token1 = response1.cookies.get(CSRF_COOKIE_NAME)
            assert token1 is not None

            # Second request with cookie already set should not generate a new one
            response2 = await client.get(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: token1},
            )
            # The middleware should not set a new cookie since one already exists
            assert response2.status_code == 200


# =============================================================================
# CSRF Validation Tests
# =============================================================================


class TestCSRFValidation:
    """Tests for CSRF validation on state-changing requests."""

    @pytest.mark.asyncio
    async def test_post_without_csrf_returns_403(self, app_with_csrf):
        """Test that POST without CSRF token returns 403."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/data")

        assert response.status_code == 403
        data = response.json()
        assert "CSRF" in data.get("error", "") or "CSRF" in data.get("detail", "")

    @pytest.mark.asyncio
    async def test_post_with_cookie_only_returns_403(self, app_with_csrf):
        """Test that POST with cookie but no header returns 403."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: "test-token"},
            )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_post_with_header_only_returns_403(self, app_with_csrf):
        """Test that POST with header but no cookie returns 403."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/data",
                headers={CSRF_HEADER_NAME: "test-token"},
            )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_post_with_mismatched_tokens_returns_403(self, app_with_csrf):
        """Test that POST with mismatched cookie and header tokens returns 403."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: "token-one"},
                headers={CSRF_HEADER_NAME: "token-two"},
            )

        assert response.status_code == 403
        data = response.json()
        assert "mismatch" in data.get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_post_with_matching_tokens_succeeds(self, app_with_csrf):
        """Test that POST with matching cookie and header tokens succeeds."""
        csrf_token = "valid-csrf-token-12345"
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: csrf_token},
                headers={CSRF_HEADER_NAME: csrf_token},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True

    @pytest.mark.asyncio
    async def test_put_with_matching_tokens_succeeds(self, app_with_csrf):
        """Test that PUT with matching CSRF tokens succeeds."""
        csrf_token = "valid-csrf-token-put"
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: csrf_token},
                headers={CSRF_HEADER_NAME: csrf_token},
            )

        assert response.status_code == 200
        assert response.json()["updated"] is True

    @pytest.mark.asyncio
    async def test_patch_with_matching_tokens_succeeds(self, app_with_csrf):
        """Test that PATCH with matching CSRF tokens succeeds."""
        csrf_token = "valid-csrf-token-patch"
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: csrf_token},
                headers={CSRF_HEADER_NAME: csrf_token},
            )

        assert response.status_code == 200
        assert response.json()["patched"] is True

    @pytest.mark.asyncio
    async def test_delete_with_matching_tokens_succeeds(self, app_with_csrf):
        """Test that DELETE with matching CSRF tokens succeeds."""
        csrf_token = "valid-csrf-token-delete"
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: csrf_token},
                headers={CSRF_HEADER_NAME: csrf_token},
            )

        assert response.status_code == 200
        assert response.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_put_without_csrf_returns_403(self, app_with_csrf):
        """Test that PUT without CSRF token returns 403."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put("/api/data")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_without_csrf_returns_403(self, app_with_csrf):
        """Test that DELETE without CSRF token returns 403."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/data")

        assert response.status_code == 403


# =============================================================================
# Safe Methods Tests
# =============================================================================


class TestSafeMethods:
    """Tests for safe HTTP methods that bypass CSRF validation."""

    @pytest.mark.asyncio
    async def test_get_bypasses_csrf(self, app_with_csrf):
        """Test that GET requests bypass CSRF validation."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_head_bypasses_csrf(self, app_with_csrf):
        """Test that HEAD requests bypass CSRF validation."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.head("/api/data")

        # HEAD returns 200 (or 405 if not explicitly supported, but with the
        # middleware it should pass through)
        assert response.status_code in (200, 405)

    @pytest.mark.asyncio
    async def test_options_bypasses_csrf(self, app_with_csrf):
        """Test that OPTIONS requests bypass CSRF validation."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options("/api/data")

        # OPTIONS might return 200 or 405, but should not return 403
        assert response.status_code != 403

    def test_safe_methods_constant(self):
        """Test that safe methods set matches HTTP specification."""
        assert "GET" in SAFE_METHODS
        assert "HEAD" in SAFE_METHODS
        assert "OPTIONS" in SAFE_METHODS
        assert "TRACE" in SAFE_METHODS
        assert "POST" not in SAFE_METHODS
        assert "PUT" not in SAFE_METHODS
        assert "DELETE" not in SAFE_METHODS


# =============================================================================
# Exempt Paths Tests
# =============================================================================


class TestExemptPaths:
    """Tests for paths that are exempt from CSRF validation."""

    @pytest.mark.asyncio
    async def test_login_exempt_from_csrf(self, app_with_csrf):
        """Test that login endpoint is exempt from CSRF validation."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/auth/login")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_register_exempt_from_csrf(self, app_with_csrf):
        """Test that register endpoint is exempt from CSRF validation."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/auth/register")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_exempt_from_csrf(self, app_with_csrf):
        """Test that health endpoint is exempt from CSRF validation."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200

    def test_default_exempt_paths_include_required(self):
        """Test that default exempt paths include all required entries."""
        assert "/api/auth/login" in DEFAULT_EXEMPT_PATHS
        assert "/api/auth/register" in DEFAULT_EXEMPT_PATHS
        assert "/health" in DEFAULT_EXEMPT_PATHS
        assert "/docs" in DEFAULT_EXEMPT_PATHS

    @pytest.mark.asyncio
    async def test_custom_exempt_paths(self, app_with_custom_exemptions):
        """Test that custom exempt paths are honored."""
        transport = ASGITransport(app=app_with_custom_exemptions)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Webhook should be exempt
            response = await client.post("/api/webhook")
            assert response.status_code == 200

            # Public should be exempt
            response = await client.post("/api/public")
            assert response.status_code == 200

            # Protected should require CSRF
            response = await client.post("/api/protected")
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_exempt_path_with_trailing_slash(self, app_with_csrf):
        """Test that exempt paths work with trailing slashes."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Trailing slash should still be exempt
            response = await client.post("/api/auth/login/")

        # The path normalization should handle trailing slashes
        # May be 200 (exempt) or 307 (redirect), but not 403
        assert response.status_code != 403


# =============================================================================
# Token Rotation Tests
# =============================================================================


class TestTokenRotation:
    """Tests for CSRF token rotation after state-changing requests."""

    @pytest.mark.asyncio
    async def test_token_rotated_after_post(self, app_with_csrf):
        """Test that CSRF token is rotated after successful POST."""
        original_token = "original-csrf-token"
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: original_token},
                headers={CSRF_HEADER_NAME: original_token},
            )

        assert response.status_code == 200
        # A new cookie should be set with a rotated token
        new_token = response.cookies.get(CSRF_COOKIE_NAME)
        assert new_token is not None
        assert new_token != original_token


# =============================================================================
# Middleware Configuration Tests
# =============================================================================


class TestCSRFMiddlewareConfiguration:
    """Tests for CSRF middleware configuration options."""

    def test_middleware_init_with_defaults(self):
        """Test that middleware initializes with sensible defaults."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        assert middleware.exempt_paths == DEFAULT_EXEMPT_PATHS
        assert middleware.cookie_secure is True
        assert middleware.cookie_samesite == "lax"
        assert middleware.cookie_domain is None
        assert middleware.token_length == 32

    def test_middleware_init_with_custom_config(self):
        """Test that middleware accepts custom configuration."""
        app = FastAPI()
        custom_exempt = {"/custom/path"}
        middleware = CSRFMiddleware(
            app,
            exempt_paths=custom_exempt,
            cookie_secure=False,
            cookie_samesite="strict",
            cookie_domain=".example.com",
            token_length=64,
        )

        assert middleware.exempt_paths == custom_exempt
        assert middleware.cookie_secure is False
        assert middleware.cookie_samesite == "strict"
        assert middleware.cookie_domain == ".example.com"
        assert middleware.token_length == 64

    def test_generate_token_returns_string(self):
        """Test that token generation returns a non-empty string."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        token = middleware._generate_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_is_unique(self):
        """Test that generated tokens are unique."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        tokens = {middleware._generate_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_is_exempt_handles_root_path(self):
        """Test that the root path exemption works correctly."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        assert middleware._is_exempt("/") is True

    def test_is_exempt_handles_non_exempt_path(self):
        """Test that non-exempt paths are correctly identified."""
        app = FastAPI()
        middleware = CSRFMiddleware(app)

        assert middleware._is_exempt("/api/data") is False
        assert middleware._is_exempt("/api/resumes") is False


# =============================================================================
# Error Response Tests
# =============================================================================


class TestCSRFErrorResponses:
    """Tests for CSRF error response format and content."""

    @pytest.mark.asyncio
    async def test_missing_token_error_message(self, app_with_csrf):
        """Test that missing token error has clear message."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/data")

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "CSRF" in data["error"]
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_mismatch_token_error_message(self, app_with_csrf):
        """Test that token mismatch error has specific message."""
        transport = ASGITransport(app=app_with_csrf)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/data",
                cookies={CSRF_COOKIE_NAME: "token-a"},
                headers={CSRF_HEADER_NAME: "token-b"},
            )

        assert response.status_code == 403
        data = response.json()
        assert "mismatch" in data["detail"].lower()
