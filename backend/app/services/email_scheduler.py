"""
Email scheduler service for automated email delivery.

Uses APScheduler to run periodic email jobs:
- Nudge emails (every 6 hours)
- Weekly digest (Sunday 18:00 UTC)
- Re-engagement emails (daily 10:00 UTC)

Guarded by settings.enable_email — when False, jobs log instead of sending.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.models.interview_event import InterviewEvent
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)


class EmailScheduler:
    """
    Background scheduler for automated email delivery.

    Separate from the job-scraping scheduler to keep concerns isolated.
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 60 * 30,
            }
        )
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the email scheduler with all registered jobs."""
        if self._running:
            logger.warning("Email scheduler is already running")
            return

        self._scheduler.add_job(
            check_and_send_nudge_emails,
            trigger=IntervalTrigger(hours=6),
            id="email_nudges",
            name="Nudge email check",
            replace_existing=True,
        )

        self._scheduler.add_job(
            send_weekly_digest,
            trigger=CronTrigger(day_of_week="sun", hour=18, minute=0),
            id="email_weekly_digest",
            name="Weekly digest",
            replace_existing=True,
        )

        self._scheduler.add_job(
            check_inactive_users,
            trigger=CronTrigger(hour=10, minute=0),
            id="email_reengagement",
            name="Re-engagement check",
            replace_existing=True,
        )

        self._scheduler.start()
        self._running = True
        logger.info("Email scheduler started with 3 jobs")

    def stop(self) -> None:
        """Stop the email scheduler gracefully."""
        if not self._running:
            return

        self._scheduler.shutdown(wait=True)
        self._running = False
        logger.info("Email scheduler stopped")


def _get_eligible_users(db, *, require_nudges: bool = False,
                        require_digest: bool = False,
                        require_reengagement: bool = False) -> list[User]:
    """Query users with master email toggle ON and the specific preference enabled."""
    query = db.query(User).filter(
        User.is_active == True,  # noqa: E712
        User.email_notifications == True,  # noqa: E712
    )
    if require_nudges:
        query = query.filter(User.email_nudges == True)  # noqa: E712
    if require_digest:
        query = query.filter(User.email_weekly_digest == True)  # noqa: E712
    if require_reengagement:
        query = query.filter(User.email_reengagement == True)  # noqa: E712
    return query.all()


def check_and_send_nudge_emails() -> None:
    """
    Check for actionable nudges and send email summaries.

    Runs every 6 hours. Sends the top 3 nudges per eligible user.
    """
    settings = get_settings()
    email_service = get_email_service()

    if not settings.enable_email:
        logger.debug("Email disabled — skipping nudge email check")
        return

    db = SessionLocal()
    try:
        users = _get_eligible_users(db, require_nudges=True)
        logger.info("Nudge email check: %d eligible users", len(users))

        for user in users:
            try:
                _send_nudge_email_for_user(db, user, email_service, settings.app_url)
            except Exception:
                logger.exception("Error sending nudge email for user %d", user.id)
    finally:
        db.close()


def _send_nudge_email_for_user(db, user: User, email_service, app_url: str) -> None:
    """Compute nudges for a single user and send an email if any exist."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return

    today = date.today()

    # Find stale applications (Applied > 7 days, no response)
    seven_days_ago = today - timedelta(days=7)
    stale_apps = (
        db.query(JobApplication)
        .filter(
            JobApplication.profile_id == profile.id,
            JobApplication.status == "Applied",
            JobApplication.application_date != None,  # noqa: E711
            JobApplication.application_date <= seven_days_ago,
            JobApplication.response_date == None,  # noqa: E711
        )
        .limit(3)
        .all()
    )

    if not stale_apps:
        return

    name = user.full_name or user.username
    for app in stale_apps:
        days = (today - app.application_date).days
        job_url = f"{app_url}/jobs"
        html = email_service.render_nudge(
            name=name,
            company=app.company,
            position=app.position,
            days_since_update=days,
            job_url=job_url,
        )
        email_service.send(
            to=user.email,
            subject=f"Follow up with {app.company} — {days} days since you applied",
            html=html,
        )

    logger.info("Sent %d nudge emails to user %d", len(stale_apps), user.id)


def send_weekly_digest() -> None:
    """
    Send weekly activity digest to eligible users.

    Runs Sunday 18:00 UTC. Summarizes the past week's activity.
    """
    settings = get_settings()
    email_service = get_email_service()

    if not settings.enable_email:
        logger.debug("Email disabled — skipping weekly digest")
        return

    db = SessionLocal()
    try:
        users = _get_eligible_users(db, require_digest=True)
        logger.info("Weekly digest: %d eligible users", len(users))

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        week_ago_date = week_ago.date()

        for user in users:
            try:
                _send_digest_for_user(db, user, email_service, settings.app_url, week_ago_date)
            except Exception:
                logger.exception("Error sending digest for user %d", user.id)
    finally:
        db.close()


def _send_digest_for_user(db, user: User, email_service, app_url: str, since: date) -> None:
    """Gather weekly stats for a user and send the digest email."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return

    jobs_applied = (
        db.query(JobApplication)
        .filter(
            JobApplication.profile_id == profile.id,
            JobApplication.application_date != None,  # noqa: E711
            JobApplication.application_date >= since,
        )
        .count()
    )

    interviews_scheduled = (
        db.query(InterviewEvent)
        .filter(
            InterviewEvent.profile_id == profile.id,
            InterviewEvent.scheduled_date >= since.isoformat(),
        )
        .count()
    )

    name = user.full_name or user.username
    html = email_service.render_weekly_digest(
        name=name,
        jobs_applied=jobs_applied,
        interviews_scheduled=interviews_scheduled,
        app_url=app_url,
    )
    email_service.send(
        to=user.email,
        subject=f"Your week in review — {jobs_applied} applications, {interviews_scheduled} interviews",
        html=html,
    )


def check_inactive_users() -> None:
    """
    Send re-engagement emails to users inactive for 3+ days.

    Runs daily at 10:00 UTC.
    """
    settings = get_settings()
    email_service = get_email_service()

    if not settings.enable_email:
        logger.debug("Email disabled — skipping re-engagement check")
        return

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=3)

        users = (
            db.query(User)
            .filter(
                User.is_active == True,  # noqa: E712
                User.email_notifications == True,  # noqa: E712
                User.email_reengagement == True,  # noqa: E712
                User.last_active_at != None,  # noqa: E711
                User.last_active_at < cutoff,
            )
            .all()
        )

        logger.info("Re-engagement check: %d inactive users", len(users))

        for user in users:
            try:
                name = user.full_name or user.username
                html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
  <div style="background: #6366f1; padding: 32px 40px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">ResuBoost AI</h1>
  </div>
  <div style="padding: 40px;">
    <h2 style="color: #1a1a2e; margin-top: 0;">We miss you, {name}!</h2>
    <p style="color: #444; line-height: 1.6;">
      Your job search pipeline is waiting for you. Stay on top of your applications
      and keep the momentum going.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{settings.app_url}"
         style="display: inline-block; padding: 14px 28px; background: #6366f1;
                color: #ffffff; text-decoration: none; border-radius: 8px;
                font-weight: 600; font-size: 16px;">
        Open ResuBoost
      </a>
    </div>
    <p style="color: #888; font-size: 13px;">
      You can disable these emails in your
      <a href="{settings.app_url}/settings" style="color: #6366f1;">notification settings</a>.
    </p>
  </div>
</div>
"""
                email_service.send(
                    to=user.email,
                    subject="Your job search pipeline is waiting for you",
                    html=html,
                )
            except Exception:
                logger.exception("Error sending re-engagement email for user %d", user.id)
    finally:
        db.close()


# Singleton
_email_scheduler: Optional[EmailScheduler] = None


def get_email_scheduler() -> EmailScheduler:
    """Get or create the EmailScheduler singleton."""
    global _email_scheduler
    if _email_scheduler is None:
        _email_scheduler = EmailScheduler()
    return _email_scheduler


def reset_email_scheduler() -> None:
    """Reset the EmailScheduler singleton (for testing)."""
    global _email_scheduler
    if _email_scheduler is not None:
        try:
            _email_scheduler.stop()
        except Exception:
            pass
    _email_scheduler = None
