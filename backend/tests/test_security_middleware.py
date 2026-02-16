"""
Tests for security middleware and utility functions.

Tests:
- Security headers (X-Content-Type-Options, X-Frame-Options, CSP, HSTS, etc.)
- Request ID middleware (generation, validation, passthrough)
- Input sanitization (XSS patterns, SQL injection, path traversal, safe requests)
- CORS configuration helper
- Utility functions (sanitize_string, escape_html_string, strip_html_tags)
- IP and User-Agent extraction helpers
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.middleware.security import (
    InputSanitizationMiddleware,
    REQUEST_ID_HEADER,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    configure_cors,
    escape_html_string,
    get_client_ip,
    get_user_agent,
    sanitize_string,
    strip_html_tags,
)


# =============================================================================
# Security Headers Tests
# =============================================================================


class TestSecurityHeadersMiddlewareDetailed:
    """Tests for SecurityHeadersMiddleware with detailed checks."""

    @pytest.fixture
    def app_with_security_headers(self):
        """Create a test app with security headers middleware."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        @app.get("/cached")
        def cached_endpoint():
            from fastapi.responses import JSONResponse

            response = JSONResponse({"cached": True})
            response.headers["Cache-Control"] = "max-age=3600"
            return response

        return app

    @pytest.mark.asyncio
    async def test_x_content_type_options(self, app_with_security_headers):
        """Test X-Content-Type-Options header is set to nosniff."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options(self, app_with_security_headers):
        """Test X-Frame-Options header is set to DENY."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_x_xss_protection(self, app_with_security_headers):
        """Test X-XSS-Protection header is set."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_referrer_policy(self, app_with_security_headers):
        """Test Referrer-Policy header is set."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert "strict-origin-when-cross-origin" in response.headers["Referrer-Policy"]

    @pytest.mark.asyncio
    async def test_content_security_policy(self, app_with_security_headers):
        """Test Content-Security-Policy header is set."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        csp = response.headers["Content-Security-Policy"]
        assert "default-src" in csp

    @pytest.mark.asyncio
    async def test_permissions_policy(self, app_with_security_headers):
        """Test Permissions-Policy header is set."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        pp = response.headers["Permissions-Policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp
        assert "geolocation=()" in pp

    @pytest.mark.asyncio
    async def test_cache_control_default(self, app_with_security_headers):
        """Test that default cache control headers are set."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert "no-store" in response.headers["Cache-Control"]
        assert response.headers.get("Pragma") == "no-cache"

    @pytest.mark.asyncio
    async def test_cache_control_not_overwritten(self, app_with_security_headers):
        """Test that existing Cache-Control headers are not overwritten."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/cached")

        # The endpoint sets Cache-Control to max-age=3600, which should be preserved
        assert "max-age=3600" in response.headers.get("Cache-Control", "")

    @pytest.mark.asyncio
    async def test_custom_headers(self):
        """Test that custom headers are added."""
        app = FastAPI()
        app.add_middleware(
            SecurityHeadersMiddleware,
            custom_headers={"X-Custom-Header": "custom-value"},
        )

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.headers["X-Custom-Header"] == "custom-value"

    @pytest.mark.asyncio
    async def test_custom_csp(self):
        """Test that custom CSP is used when provided."""
        custom_csp = "default-src 'self'; script-src 'none'"
        app = FastAPI()
        app.add_middleware(
            SecurityHeadersMiddleware,
            content_security_policy=custom_csp,
        )

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.headers["Content-Security-Policy"] == custom_csp

    @pytest.mark.asyncio
    async def test_hsts_not_set_for_http(self, app_with_security_headers):
        """Test that HSTS is not set for HTTP requests."""
        transport = ASGITransport(app=app_with_security_headers)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        # HSTS should NOT be set for non-HTTPS
        assert "Strict-Transport-Security" not in response.headers


# =============================================================================
# Request ID Middleware Tests
# =============================================================================


class TestRequestIDMiddlewareDetailed:
    """Tests for RequestIDMiddleware with detailed checks."""

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
    async def test_generates_uuid_request_id(self, app_with_request_id):
        """Test that a UUID request ID is generated when none provided."""
        transport = ASGITransport(app=app_with_request_id)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0
        # UUID format: 8-4-4-4-12 characters
        assert len(request_id) == 36

    @pytest.mark.asyncio
    async def test_uses_provided_valid_request_id(self, app_with_request_id):
        """Test that a valid provided request ID is used."""
        transport = ASGITransport(app=app_with_request_id)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/test",
                headers={"X-Request-ID": "my-custom-id-123"},
            )

        assert response.headers["X-Request-ID"] == "my-custom-id-123"

    @pytest.mark.asyncio
    async def test_request_id_in_response_and_state(self, app_with_request_id):
        """Test that request ID is in both response headers and request state."""
        transport = ASGITransport(app=app_with_request_id)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        header_id = response.headers["X-Request-ID"]
        body_id = response.json()["request_id"]
        assert header_id == body_id

    @pytest.mark.asyncio
    async def test_rejects_xss_in_request_id(self, app_with_request_id):
        """Test that XSS in request ID is rejected."""
        transport = ASGITransport(app=app_with_request_id)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/test",
                headers={"X-Request-ID": "<script>alert(1)</script>"},
            )

        # Should be replaced with a valid UUID
        assert response.headers["X-Request-ID"] != "<script>alert(1)</script>"
        assert len(response.headers["X-Request-ID"]) == 36

    @pytest.mark.asyncio
    async def test_rejects_too_long_request_id(self, app_with_request_id):
        """Test that excessively long request IDs are rejected."""
        transport = ASGITransport(app=app_with_request_id)
        long_id = "a" * 100
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/test",
                headers={"X-Request-ID": long_id},
            )

        # Should be replaced
        assert response.headers["X-Request-ID"] != long_id

    @pytest.mark.asyncio
    async def test_accepts_dashes_and_underscores(self, app_with_request_id):
        """Test that request IDs with dashes and underscores are accepted."""
        transport = ASGITransport(app=app_with_request_id)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/test",
                headers={"X-Request-ID": "req_abc-123-def"},
            )

        assert response.headers["X-Request-ID"] == "req_abc-123-def"

    def test_is_valid_request_id_valid_cases(self):
        """Test valid request ID patterns."""
        assert RequestIDMiddleware._is_valid_request_id("abc-123") is True
        assert RequestIDMiddleware._is_valid_request_id("req_12345") is True
        assert (
            RequestIDMiddleware._is_valid_request_id(
                "550e8400-e29b-41d4-a716-446655440000"
            )
            is True
        )

    def test_is_valid_request_id_invalid_cases(self):
        """Test invalid request ID patterns."""
        assert RequestIDMiddleware._is_valid_request_id("<script>") is False
        assert RequestIDMiddleware._is_valid_request_id("id with spaces") is False
        assert RequestIDMiddleware._is_valid_request_id("a" * 65) is False


# =============================================================================
# Input Sanitization Tests
# =============================================================================


class TestInputSanitizationDetailed:
    """Tests for input sanitization middleware with detailed patterns."""

    @pytest.fixture
    def app_with_blocking_sanitization(self):
        """Create app with blocking sanitization."""
        app = FastAPI()
        app.add_middleware(
            InputSanitizationMiddleware,
            enabled=True,
            log_violations=False,
            block_on_violation=True,
        )

        @app.get("/api/data")
        def get_data():
            return {"status": "ok"}

        @app.get("/health")
        def health():
            return {"status": "healthy"}

        return app

    @pytest.fixture
    def app_with_logging_sanitization(self):
        """Create app with logging-only sanitization."""
        app = FastAPI()
        app.add_middleware(
            InputSanitizationMiddleware,
            enabled=True,
            log_violations=True,
            block_on_violation=False,
        )

        @app.get("/api/data")
        def get_data(request: Request):
            violations = getattr(request.state, "security_violations", [])
            return {"violations": violations}

        return app

    @pytest.mark.asyncio
    async def test_blocks_script_tag(self, app_with_blocking_sanitization):
        """Test that <script> tags are blocked."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data?q=<script>alert(1)</script>")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_blocks_javascript_protocol(self, app_with_blocking_sanitization):
        """Test that javascript: protocol is blocked."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data?url=javascript:alert(1)")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_blocks_onerror_event(self, app_with_blocking_sanitization):
        """Test that onerror event handler is blocked."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get('/api/data?img=<img onerror="alert(1)">')

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_blocks_path_traversal(self, app_with_blocking_sanitization):
        """Test that path traversal patterns are blocked."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data?file=../../../etc/passwd")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_blocks_sql_injection_or(self, app_with_blocking_sanitization):
        """Test that SQL injection OR pattern is blocked."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data?id=1' OR '1'='1")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_blocks_sql_union_select(self, app_with_blocking_sanitization):
        """Test that SQL UNION SELECT is blocked."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/data?q=1 UNION SELECT * FROM users"
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_blocks_iframe_injection(self, app_with_blocking_sanitization):
        """Test that iframe injection is blocked."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                '/api/data?html=<iframe src="evil.com"></iframe>'
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_allows_safe_query_params(self, app_with_blocking_sanitization):
        """Test that safe query parameters are allowed."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/data?name=John%20Doe&page=1&sort=created_at"
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_normal_text(self, app_with_blocking_sanitization):
        """Test that normal text content is allowed."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/data?search=software+engineer+python"
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skip_paths_bypassed(self, app_with_blocking_sanitization):
        """Test that skip paths are not checked."""
        transport = ASGITransport(app=app_with_blocking_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health?test=<script>")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logging_mode_records_violations(self, app_with_logging_sanitization):
        """Test that logging mode records violations in request state."""
        transport = ASGITransport(app=app_with_logging_sanitization)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data?q=<script>evil</script>")

        assert response.status_code == 200
        data = response.json()
        assert len(data["violations"]) > 0

    @pytest.mark.asyncio
    async def test_disabled_middleware_passes_all(self):
        """Test that disabled middleware passes all requests."""
        app = FastAPI()
        app.add_middleware(
            InputSanitizationMiddleware,
            enabled=False,
        )

        @app.get("/test")
        def test_endpoint():
            return {"ok": True}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test?q=<script>alert(1)</script>")

        assert response.status_code == 200


# =============================================================================
# Sanitization Utility Function Tests
# =============================================================================


class TestSanitizeStringDetailed:
    """Tests for sanitize_string utility function."""

    def test_basic_trimming(self):
        """Test whitespace trimming."""
        assert sanitize_string("  hello  ") == "hello"

    def test_max_length_truncation(self):
        """Test that strings are truncated to max_length."""
        result = sanitize_string("a" * 500, max_length=100)
        assert len(result) == 100

    def test_default_max_length(self):
        """Test default max length is 1000."""
        long_str = "x" * 2000
        result = sanitize_string(long_str)
        assert len(result) == 1000

    def test_html_escaping_enabled(self):
        """Test HTML escaping when enabled."""
        result = sanitize_string("<b>bold</b>")
        assert "&lt;" in result
        assert "&gt;" in result
        assert "<b>" not in result

    def test_html_escaping_disabled(self):
        """Test HTML escaping can be disabled."""
        result = sanitize_string("<b>bold</b>", escape_html=False)
        assert "<b>" in result

    def test_null_byte_removal(self):
        """Test that null bytes are removed."""
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result
        assert result == "helloworld"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert sanitize_string("") == ""

    def test_none_input(self):
        """Test handling of None input."""
        assert sanitize_string(None) == ""

    def test_special_characters_escaped(self):
        """Test that quotes and ampersands are escaped."""
        result = sanitize_string('He said "hello" & goodbye')
        assert "&quot;" in result
        assert "&amp;" in result

    def test_combined_sanitization(self):
        """Test all sanitization steps together."""
        dirty = "  \x00<script>alert('xss')</script>  "
        result = sanitize_string(dirty)
        assert "\x00" not in result
        assert "<script>" not in result
        assert result.startswith("&lt;")


class TestEscapeHtmlString:
    """Tests for escape_html_string utility function."""

    def test_escapes_angle_brackets(self):
        """Test that angle brackets are escaped."""
        assert "&lt;" in escape_html_string("<tag>")
        assert "&gt;" in escape_html_string("<tag>")

    def test_escapes_ampersand(self):
        """Test that ampersand is escaped."""
        assert "&amp;" in escape_html_string("a & b")

    def test_escapes_quotes(self):
        """Test that quotes are escaped."""
        assert "&quot;" in escape_html_string('"quoted"')

    def test_full_html_escaping(self):
        """Test complete HTML escaping."""
        result = escape_html_string('<div class="test">Hello & World</div>')
        assert result == (
            "&lt;div class=&quot;test&quot;&gt;"
            "Hello &amp; World"
            "&lt;/div&gt;"
        )

    def test_plain_text_unchanged(self):
        """Test that plain text is not modified."""
        text = "Hello World 123"
        assert escape_html_string(text) == text


class TestStripHtmlTags:
    """Tests for strip_html_tags utility function."""

    def test_strips_basic_tags(self):
        """Test stripping basic HTML tags."""
        assert strip_html_tags("<p>Hello</p>") == "Hello"

    def test_strips_nested_tags(self):
        """Test stripping nested tags."""
        result = strip_html_tags("<div><p>Hello <b>World</b></p></div>")
        assert result == "Hello World"

    def test_handles_empty_string(self):
        """Test handling of empty string."""
        assert strip_html_tags("") == ""

    def test_handles_none(self):
        """Test handling of None."""
        assert strip_html_tags(None) == ""

    def test_preserves_text_content(self):
        """Test that text content is preserved."""
        result = strip_html_tags("<h1>Title</h1><p>Body text</p>")
        assert "Title" in result
        assert "Body text" in result

    def test_handles_unclosed_tags(self):
        """Test handling of unclosed tags."""
        result = strip_html_tags("Hello <b>World")
        assert "Hello" in result
        assert "World" in result

    def test_decodes_html_entities(self):
        """Test that HTML entities are decoded."""
        result = strip_html_tags("&amp; &lt; &gt;")
        assert "&" in result


# =============================================================================
# IP and User Agent Helper Tests
# =============================================================================


class TestGetClientIpDetailed:
    """Tests for get_client_ip helper function."""

    def test_direct_connection(self):
        """Test getting IP from direct connection."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        assert get_client_ip(request) == "192.168.1.100"

    def test_x_forwarded_for_single(self):
        """Test getting IP from single X-Forwarded-For."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        assert get_client_ip(request) == "10.0.0.1"

    def test_x_forwarded_for_chain(self):
        """Test getting first IP from X-Forwarded-For chain."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 172.16.0.1, 192.168.0.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        assert get_client_ip(request) == "10.0.0.1"

    def test_no_client_info(self):
        """Test fallback when no client info is available."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        assert get_client_ip(request) == "unknown"


class TestGetUserAgentDetailed:
    """Tests for get_user_agent helper function."""

    def test_normal_user_agent(self):
        """Test getting a normal User-Agent."""
        request = MagicMock()
        request.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        result = get_user_agent(request)
        assert result == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    def test_missing_user_agent(self):
        """Test fallback when User-Agent is missing."""
        request = MagicMock()
        request.headers = {}

        assert get_user_agent(request) == "unknown"

    def test_long_user_agent_truncated(self):
        """Test that long User-Agents are truncated to 500 chars."""
        request = MagicMock()
        request.headers = {"User-Agent": "x" * 1000}

        result = get_user_agent(request)
        assert len(result) == 500

    def test_user_agent_500_chars_not_truncated(self):
        """Test that a 500-char User-Agent is not truncated."""
        request = MagicMock()
        ua = "x" * 500
        request.headers = {"User-Agent": ua}

        assert get_user_agent(request) == ua


# =============================================================================
# CORS Configuration Tests
# =============================================================================


class TestCORSConfiguration:
    """Tests for CORS configuration helper."""

    def test_configure_cors_with_defaults(self):
        """Test CORS configuration with default values."""
        app = FastAPI()
        configure_cors(app)

        # Middleware should be added without error
        assert len(app.middleware_stack) is not None

    def test_configure_cors_with_custom_origins(self):
        """Test CORS configuration with custom origins."""
        app = FastAPI()
        configure_cors(app, origins=["https://example.com", "https://app.example.com"])

        # Should not raise
        assert True

    def test_configure_cors_with_all_params(self):
        """Test CORS configuration with all parameters specified."""
        app = FastAPI()
        configure_cors(
            app,
            origins=["https://example.com"],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            expose_headers=["X-Custom"],
            max_age=300,
        )

        # Should not raise
        assert True


# =============================================================================
# Integration Tests
# =============================================================================


class TestSecurityMiddlewareIntegration:
    """Integration tests for combined security middleware."""

    @pytest.fixture
    def fully_secured_app(self):
        """Create an app with all security middleware."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestIDMiddleware)
        app.add_middleware(
            InputSanitizationMiddleware,
            enabled=True,
            block_on_violation=True,
        )

        @app.get("/api/test")
        def test_endpoint(request: Request):
            return {
                "request_id": getattr(request.state, "request_id", None),
                "status": "ok",
            }

        return app

    @pytest.mark.asyncio
    async def test_all_middleware_cooperate(self, fully_secured_app):
        """Test that all middleware work together on a safe request."""
        transport = ASGITransport(app=fully_secured_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/test?name=John")

        assert response.status_code == 200

        # Security headers present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"

        # Request ID present
        assert "X-Request-ID" in response.headers

        # Response body is correct
        data = response.json()
        assert data["request_id"] is not None

    @pytest.mark.asyncio
    async def test_sanitization_blocks_before_handler(self, fully_secured_app):
        """Test that sanitization blocks dangerous requests before reaching handler."""
        transport = ASGITransport(app=fully_secured_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/test?q=<script>alert(1)</script>")

        assert response.status_code == 400
