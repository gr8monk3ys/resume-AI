"""
Email service for ResuBoost AI using Resend.

Provides:
- EmailService class with template rendering and sending
- Disabled-mode support (logs only, no network calls)
- Inline HTML templates for all transactional emails
- Factory function get_email_service()
"""

import logging
import uuid
from typing import Optional

try:
    import resend
except ImportError:
    resend = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class EmailService:
    """
    Transactional email service backed by Resend.

    When ``enabled`` is False (default in dev/test), send() is a no-op
    that logs the intent. This lets the rest of the codebase call send()
    unconditionally without worrying about environment.
    """

    def __init__(
        self,
        enabled: bool,
        api_key: Optional[str],
        from_email: str,
        app_url: str,
    ) -> None:
        self.enabled = enabled
        self.api_key = api_key
        self.from_email = from_email
        self.app_url = app_url

        if enabled and api_key and resend is not None:
            resend.api_key = api_key

    # ------------------------------------------------------------------
    # Core sending
    # ------------------------------------------------------------------

    def send(self, to: str, subject: str, html: str) -> bool:
        """
        Send a transactional email.

        Returns True on success, False when disabled or on error.
        Never raises — failures are logged instead.
        """
        if not self.enabled:
            logger.debug("Email disabled — skipping send to %s: %s", to, subject)
            return False

        if resend is None:
            logger.warning(
                "resend package not installed — cannot send email to %s: %s", to, subject
            )
            return False

        try:
            params = {
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html,
            }
            resend.Emails.send(params)
            logger.info("Email sent to %s: %s", to, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s: %s — %s", to, subject, exc)
            return False

    # ------------------------------------------------------------------
    # Token utilities
    # ------------------------------------------------------------------

    def generate_verification_token(self) -> str:
        """Return a new UUID4 string suitable for email verification links."""
        return str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def render_welcome(self, name: str, email: str, verify_url: str) -> str:
        """Welcome + email-verification email sent at registration."""
        return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
  <div style="background: #6366f1; padding: 32px 40px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">ResuBoost AI</h1>
  </div>
  <div style="padding: 40px;">
    <h2 style="color: #1a1a2e; margin-top: 0;">Welcome to ResuBoost, {name}!</h2>
    <p style="color: #444; line-height: 1.6;">
      You're one step closer to landing your next role. Please verify your email
      address so we can activate your account.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{verify_url}"
         style="display: inline-block; padding: 14px 28px; background: #6366f1;
                color: #ffffff; text-decoration: none; border-radius: 8px;
                font-weight: 600; font-size: 16px;">
        Verify Email
      </a>
    </div>
    <p style="color: #888; font-size: 13px; line-height: 1.5;">
      If you didn't create this account, you can safely ignore this email.<br>
      This link expires in 24 hours.
    </p>
  </div>
  <div style="background: #f9fafb; padding: 24px 40px; text-align: center; border-top: 1px solid #e5e7eb;">
    <p style="color: #9ca3af; font-size: 12px; margin: 0;">
      © 2026 ResuBoost AI · <a href="{self.app_url}" style="color: #6366f1;">resuboost.com</a>
    </p>
  </div>
</div>
"""

    def render_verification(self, name: str, verify_url: str) -> str:
        """Standalone email-verification email (resend on request)."""
        return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
  <div style="background: #6366f1; padding: 32px 40px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">ResuBoost AI</h1>
  </div>
  <div style="padding: 40px;">
    <h2 style="color: #1a1a2e; margin-top: 0;">Verify your email, {name}</h2>
    <p style="color: #444; line-height: 1.6;">
      Click the button below to verify your email address and complete your account setup.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{verify_url}"
         style="display: inline-block; padding: 14px 28px; background: #6366f1;
                color: #ffffff; text-decoration: none; border-radius: 8px;
                font-weight: 600; font-size: 16px;">
        Verify Email Address
      </a>
    </div>
    <p style="color: #888; font-size: 13px;">
      Link expires in 24 hours. If you didn't request this, ignore this email.
    </p>
  </div>
</div>
"""

    def render_upgrade_prompt(self, name: str, feature: str, upgrade_url: str) -> str:
        """Nudge free users to upgrade when they hit a feature gate."""
        return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
  <div style="background: #6366f1; padding: 32px 40px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">ResuBoost AI</h1>
  </div>
  <div style="padding: 40px;">
    <h2 style="color: #1a1a2e; margin-top: 0;">Unlock {feature}, {name}</h2>
    <p style="color: #444; line-height: 1.6;">
      You've reached your free-tier limit for <strong>{feature}</strong>.
      Upgrade to ResuBoost Pro for unlimited access and advanced AI features.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{upgrade_url}"
         style="display: inline-block; padding: 14px 28px; background: #f59e0b;
                color: #ffffff; text-decoration: none; border-radius: 8px;
                font-weight: 600; font-size: 16px;">
        Upgrade to Pro
      </a>
    </div>
    <p style="color: #888; font-size: 13px;">
      Questions? Reply to this email and we'll help you out.
    </p>
  </div>
</div>
"""

    def render_nudge(
        self,
        name: str,
        company: str,
        position: str,
        days_since_update: int,
        job_url: str,
    ) -> str:
        """Remind users to follow up on a stale job application."""
        return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
  <div style="background: #6366f1; padding: 32px 40px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">ResuBoost AI</h1>
  </div>
  <div style="padding: 40px;">
    <h2 style="color: #1a1a2e; margin-top: 0;">Hey {name}, time to follow up!</h2>
    <p style="color: #444; line-height: 1.6;">
      It's been <strong>{days_since_update} days</strong> since you last updated your
      application to <strong>{position}</strong> at <strong>{company}</strong>.
      A quick follow-up can set you apart from other candidates.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{job_url}"
         style="display: inline-block; padding: 14px 28px; background: #6366f1;
                color: #ffffff; text-decoration: none; border-radius: 8px;
                font-weight: 600; font-size: 16px;">
        View Application
      </a>
    </div>
  </div>
</div>
"""

    def render_payment_failed(self, name: str, update_url: str) -> str:
        """Alert the user that their payment failed and billing is at risk."""
        return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
  <div style="background: #ef4444; padding: 32px 40px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">Action Required</h1>
  </div>
  <div style="padding: 40px;">
    <h2 style="color: #1a1a2e; margin-top: 0;">Hi {name}, your payment failed</h2>
    <p style="color: #444; line-height: 1.6;">
      We were unable to process your payment for ResuBoost Pro. To avoid losing
      access to Pro features, please update your billing information as soon as possible.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{update_url}"
         style="display: inline-block; padding: 14px 28px; background: #ef4444;
                color: #ffffff; text-decoration: none; border-radius: 8px;
                font-weight: 600; font-size: 16px;">
        Update Billing
      </a>
    </div>
    <p style="color: #888; font-size: 13px;">
      Need help? Reply to this email and our support team will assist you.
    </p>
  </div>
</div>
"""

    def render_weekly_digest(
        self,
        name: str,
        jobs_applied: int,
        interviews_scheduled: int,
        app_url: str,
    ) -> str:
        """Weekly activity summary digest."""
        return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
  <div style="background: #6366f1; padding: 32px 40px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">ResuBoost AI</h1>
    <p style="color: #c7d2fe; margin: 8px 0 0; font-size: 14px;">Your weekly job search digest</p>
  </div>
  <div style="padding: 40px;">
    <h2 style="color: #1a1a2e; margin-top: 0;">Hi {name}, here's your week in review</h2>
    <div style="display: flex; gap: 16px; margin: 24px 0;">
      <div style="flex: 1; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 20px; text-align: center;">
        <div style="font-size: 36px; font-weight: 700; color: #16a34a;">{jobs_applied}</div>
        <div style="color: #166534; font-size: 14px; margin-top: 4px;">Applications Submitted</div>
      </div>
      <div style="flex: 1; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 20px; text-align: center;">
        <div style="font-size: 36px; font-weight: 700; color: #2563eb;">{interviews_scheduled}</div>
        <div style="color: #1e40af; font-size: 14px; margin-top: 4px;">Interviews Scheduled</div>
      </div>
    </div>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{app_url}"
         style="display: inline-block; padding: 14px 28px; background: #6366f1;
                color: #ffffff; text-decoration: none; border-radius: 8px;
                font-weight: 600; font-size: 16px;">
        Open ResuBoost
      </a>
    </div>
  </div>
</div>
"""


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------


def get_email_service() -> EmailService:
    """
    Return an EmailService configured from application settings.

    Uses lru_cache-style singleton pattern via the settings object.
    """
    from app.config import get_settings

    settings = get_settings()
    return EmailService(
        enabled=settings.enable_email,
        api_key=settings.resend_api_key,
        from_email=settings.from_email,
        app_url=settings.app_url,
    )
