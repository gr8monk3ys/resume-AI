"""Tests for the email scheduler service."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.middleware.auth import get_password_hash
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User
from app.services.email_scheduler import (
    EmailScheduler,
    _get_eligible_users,
    _send_nudge_email_for_user,
    check_and_send_nudge_emails,
    check_inactive_users,
    send_weekly_digest,
)


def _create_user(
    db,
    *,
    username="emailtest",
    email_notifications=True,
    email_nudges=True,
    email_weekly_digest=True,
    email_reengagement=True,
    last_active_at=None,
):
    """Helper to create a user with email preferences set."""
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=get_password_hash("TestPass123!"),
        is_active=True,
        email_notifications=email_notifications,
        email_nudges=email_nudges,
        email_weekly_digest=email_weekly_digest,
        email_reengagement=email_reengagement,
        last_active_at=last_active_at,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_profile(db, user):
    """Create a profile for a user."""
    profile = Profile(user_id=user.id, name=user.username, email=user.email)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _create_stale_application(db, profile, *, days_ago=10):
    """Create a stale 'Applied' job application."""
    app = JobApplication(
        profile_id=profile.id,
        company="TestCorp",
        position="Engineer",
        status="Applied",
        application_date=date.today() - timedelta(days=days_ago),
    )
    db.add(app)
    db.commit()
    return app


class TestGetEligibleUsers:
    def test_returns_users_with_master_toggle_on(self, db: Session):
        user = _create_user(db, username="eligible")
        result = _get_eligible_users(db)
        assert any(u.id == user.id for u in result)

    def test_excludes_users_with_master_toggle_off(self, db: Session):
        user = _create_user(db, username="nomail", email_notifications=False)
        result = _get_eligible_users(db)
        assert not any(u.id == user.id for u in result)

    def test_filters_by_nudge_preference(self, db: Session):
        user = _create_user(db, username="nonudge", email_nudges=False)
        result = _get_eligible_users(db, require_nudges=True)
        assert not any(u.id == user.id for u in result)

    def test_filters_by_digest_preference(self, db: Session):
        user = _create_user(db, username="nodigest", email_weekly_digest=False)
        result = _get_eligible_users(db, require_digest=True)
        assert not any(u.id == user.id for u in result)

    def test_filters_by_reengagement_preference(self, db: Session):
        user = _create_user(db, username="noreengage", email_reengagement=False)
        result = _get_eligible_users(db, require_reengagement=True)
        assert not any(u.id == user.id for u in result)


class TestSendNudgeEmailForUser:
    def test_sends_email_for_stale_apps(self, db: Session):
        user = _create_user(db, username="nudgeuser")
        profile = _create_profile(db, user)
        _create_stale_application(db, profile, days_ago=10)

        mock_service = MagicMock()
        mock_service.render_nudge.return_value = "<html>nudge</html>"

        _send_nudge_email_for_user(db, user, mock_service, "http://localhost:3000")

        mock_service.render_nudge.assert_called_once()
        mock_service.send.assert_called_once()
        call_kwargs = mock_service.send.call_args
        assert user.email in str(call_kwargs)

    def test_no_email_when_no_stale_apps(self, db: Session):
        user = _create_user(db, username="noupdateuser")
        _create_profile(db, user)

        mock_service = MagicMock()
        _send_nudge_email_for_user(db, user, mock_service, "http://localhost:3000")

        mock_service.send.assert_not_called()

    def test_no_email_when_no_profile(self, db: Session):
        user = _create_user(db, username="noprofileuser")

        mock_service = MagicMock()
        _send_nudge_email_for_user(db, user, mock_service, "http://localhost:3000")

        mock_service.send.assert_not_called()


class TestCheckAndSendNudgeEmails:
    @patch("app.services.email_scheduler.get_email_service")
    @patch("app.services.email_scheduler.SessionLocal")
    @patch("app.services.email_scheduler.get_settings")
    def test_skips_when_email_disabled(self, mock_settings, mock_session, mock_email):
        mock_settings.return_value.enable_email = False

        check_and_send_nudge_emails()

        mock_session.assert_not_called()

    @patch("app.services.email_scheduler.get_email_service")
    @patch("app.services.email_scheduler.SessionLocal")
    @patch("app.services.email_scheduler.get_settings")
    def test_runs_when_email_enabled(self, mock_settings, mock_session, mock_email):
        mock_settings.return_value.enable_email = True
        mock_settings.return_value.app_url = "http://localhost:3000"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_session.return_value = mock_db

        check_and_send_nudge_emails()

        mock_db.close.assert_called_once()


class TestSendWeeklyDigest:
    @patch("app.services.email_scheduler.get_email_service")
    @patch("app.services.email_scheduler.SessionLocal")
    @patch("app.services.email_scheduler.get_settings")
    def test_skips_when_email_disabled(self, mock_settings, mock_session, mock_email):
        mock_settings.return_value.enable_email = False

        send_weekly_digest()

        mock_session.assert_not_called()


class TestCheckInactiveUsers:
    @patch("app.services.email_scheduler.get_email_service")
    @patch("app.services.email_scheduler.SessionLocal")
    @patch("app.services.email_scheduler.get_settings")
    def test_skips_when_email_disabled(self, mock_settings, mock_session, mock_email):
        mock_settings.return_value.enable_email = False

        check_inactive_users()

        mock_session.assert_not_called()


class TestEmailSchedulerLifecycle:
    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        scheduler = EmailScheduler()
        assert not scheduler.is_running

        scheduler.start()
        assert scheduler.is_running

        scheduler.stop()
        assert not scheduler.is_running

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self):
        scheduler = EmailScheduler()
        scheduler.start()
        scheduler.start()  # Should not raise
        assert scheduler.is_running
        scheduler.stop()

    def test_stop_when_not_running_is_safe(self):
        scheduler = EmailScheduler()
        scheduler.stop()  # Should not raise
