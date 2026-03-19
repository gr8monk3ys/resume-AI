"""
Tests for the email service with Resend integration.

Covers:
- Template rendering methods produce correct HTML
- send() returns False when email is disabled
- send() calls resend when enabled (mocked)
- generate_verification_token() returns a UUID-like string
- get_email_service() factory function
"""

import os
import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest

# Ensure test env is set before app imports
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENABLE_EMAIL", "false")

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.email_service import EmailService, get_email_service


# =============================================================================
# Template Tests
# =============================================================================


class TestEmailServiceTemplates:
    """Tests that each render_* method produces expected HTML content."""

    def setup_method(self):
        """Create a disabled EmailService for template tests."""
        self.service = EmailService(
            enabled=False,
            api_key="test-key",
            from_email="Test <test@example.com>",
            app_url="https://example.com",
        )

    def test_render_welcome_contains_name(self):
        html = self.service.render_welcome(
            name="Alice",
            email="alice@example.com",
            verify_url="https://example.com/verify?token=abc",
        )
        assert "Alice" in html
        assert "Verify Email" in html
        assert "https://example.com/verify?token=abc" in html

    def test_render_welcome_contains_resuboost_branding(self):
        html = self.service.render_welcome(
            name="Bob",
            email="bob@example.com",
            verify_url="https://example.com/verify?token=xyz",
        )
        assert "ResuBoost" in html

    def test_render_verification_contains_verify_url(self):
        html = self.service.render_verification(
            name="Carol",
            verify_url="https://example.com/verify?token=def",
        )
        assert "Carol" in html
        assert "https://example.com/verify?token=def" in html
        assert "verify" in html.lower()

    def test_render_upgrade_prompt_contains_pro_info(self):
        html = self.service.render_upgrade_prompt(
            name="Dave",
            feature="AI Resume Tailoring",
            upgrade_url="https://example.com/upgrade",
        )
        assert "Dave" in html
        assert "AI Resume Tailoring" in html
        assert "https://example.com/upgrade" in html

    def test_render_nudge_contains_job_info(self):
        html = self.service.render_nudge(
            name="Eve",
            company="Acme Corp",
            position="Engineer",
            days_since_update=5,
            job_url="https://example.com/jobs/1",
        )
        assert "Eve" in html
        assert "Acme Corp" in html
        assert "Engineer" in html
        assert "5" in html

    def test_render_payment_failed_contains_name_and_update_url(self):
        html = self.service.render_payment_failed(
            name="Frank",
            update_url="https://example.com/billing",
        )
        assert "Frank" in html
        assert "https://example.com/billing" in html
        assert "payment" in html.lower() or "billing" in html.lower()

    def test_render_weekly_digest_contains_stats(self):
        html = self.service.render_weekly_digest(
            name="Grace",
            jobs_applied=3,
            interviews_scheduled=1,
            app_url="https://example.com",
        )
        assert "Grace" in html
        assert "3" in html
        assert "1" in html

    def test_all_templates_return_strings(self):
        """All render methods must return non-empty strings."""
        templates = [
            self.service.render_welcome("X", "x@x.com", "https://x.com/v"),
            self.service.render_verification("X", "https://x.com/v"),
            self.service.render_upgrade_prompt("X", "Feature", "https://x.com/u"),
            self.service.render_nudge("X", "Co", "Role", 7, "https://x.com/j"),
            self.service.render_payment_failed("X", "https://x.com/b"),
            self.service.render_weekly_digest("X", 2, 0, "https://x.com"),
        ]
        for html in templates:
            assert isinstance(html, str)
            assert len(html) > 20


# =============================================================================
# Sending Tests
# =============================================================================


class TestEmailServiceSending:
    """Tests for the send() method and factory function."""

    def test_send_disabled_returns_false(self, caplog):
        """When email is disabled, send() should log and return False."""
        import logging

        service = EmailService(
            enabled=False,
            api_key="test-key",
            from_email="Test <test@example.com>",
            app_url="https://example.com",
        )
        with caplog.at_level(logging.DEBUG):
            result = service.send(
                to="recipient@example.com",
                subject="Test Subject",
                html="<p>Hello</p>",
            )
        assert result is False

    def test_send_enabled_calls_resend(self):
        """When email is enabled, send() should call resend.Emails.send."""
        service = EmailService(
            enabled=True,
            api_key="re_test_key",
            from_email="Test <test@example.com>",
            app_url="https://example.com",
        )

        mock_response = MagicMock()
        mock_resend_emails = MagicMock()
        mock_resend_emails.send.return_value = mock_response

        with patch("app.services.email_service.resend") as mock_resend_module:
            mock_resend_module.Emails = mock_resend_emails
            mock_resend_module.api_key = None  # attribute access

            result = service.send(
                to="recipient@example.com",
                subject="Test Subject",
                html="<p>Hello</p>",
            )

        assert result is True
        mock_resend_emails.send.assert_called_once()

    def test_send_enabled_but_resend_unavailable_returns_false(self, caplog):
        """When resend module is None (not installed), send() returns False."""
        import logging

        service = EmailService(
            enabled=True,
            api_key="re_test_key",
            from_email="Test <test@example.com>",
            app_url="https://example.com",
        )

        with patch("app.services.email_service.resend", None):
            with caplog.at_level(logging.WARNING):
                result = service.send(
                    to="recipient@example.com",
                    subject="Test Subject",
                    html="<p>Hello</p>",
                )
        assert result is False

    def test_send_handles_exception_gracefully(self):
        """When resend raises, send() returns False without propagating."""
        service = EmailService(
            enabled=True,
            api_key="re_test_key",
            from_email="Test <test@example.com>",
            app_url="https://example.com",
        )

        mock_resend_emails = MagicMock()
        mock_resend_emails.send.side_effect = Exception("API error")

        with patch("app.services.email_service.resend") as mock_resend_module:
            mock_resend_module.Emails = mock_resend_emails

            result = service.send(
                to="recipient@example.com",
                subject="Test Subject",
                html="<p>Hello</p>",
            )

        assert result is False


# =============================================================================
# Token Generation Tests
# =============================================================================


class TestGenerateVerificationToken:
    """Tests for generate_verification_token()."""

    def setup_method(self):
        self.service = EmailService(enabled=False, api_key=None, from_email="x", app_url="y")

    def test_returns_string(self):
        token = self.service.generate_verification_token()
        assert isinstance(token, str)

    def test_is_valid_uuid(self):
        token = self.service.generate_verification_token()
        # Should be parseable as UUID
        parsed = uuid.UUID(token)
        assert str(parsed) == token

    def test_tokens_are_unique(self):
        tokens = {self.service.generate_verification_token() for _ in range(20)}
        assert len(tokens) == 20


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestGetEmailService:
    """Tests for the get_email_service() factory."""

    def test_returns_email_service_instance(self):
        service = get_email_service()
        assert isinstance(service, EmailService)

    def test_disabled_by_default_in_test_env(self):
        """ENABLE_EMAIL=false in test env means service is disabled."""
        service = get_email_service()
        assert service.enabled is False
