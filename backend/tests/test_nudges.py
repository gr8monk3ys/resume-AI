"""
Tests for the nudges router.

Tests cover:
- Each of the six nudge types (overdue_followup, interview_prep, thank_you,
  stale_followup, application_velocity, resume_freshness) firing and not
  firing based on their trigger conditions
- Empty state (application_velocity always fires with zero applications) and
  auth requirements
- User data isolation (one profile's events never produce another's nudges)
- AI draft generation, unknown nudge type, and LLM failure handling
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.interview_event import InterviewEvent
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.resume import Resume
from app.services.llm_service import LLMServerError, get_llm_service, reset_llm_service


def _create_interview_event(db: Session, profile_id: int, **overrides) -> InterviewEvent:
    """Helper to create an interview event directly via ORM."""
    defaults = dict(
        company="Stripe",
        position="Backend Engineer",
        event_type="Technical Interview",
        scheduled_date=date.today().isoformat(),
        is_completed=False,
    )
    defaults.update(overrides)
    event = InterviewEvent(profile_id=profile_id, **defaults)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _create_job_application(db: Session, profile_id: int, **overrides) -> JobApplication:
    """Helper to create a job application directly via ORM."""
    defaults = dict(
        company="Acme Corp",
        position="Senior Developer",
        status="Applied",
    )
    defaults.update(overrides)
    job = JobApplication(profile_id=profile_id, **defaults)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _types(nudges: list[dict]) -> list[str]:
    return [n["nudge_type"] for n in nudges]


def _by_type(nudges: list[dict], nudge_type: str) -> list[dict]:
    return [n for n in nudges if n["nudge_type"] == nudge_type]


class TestListNudgesEmptyAndAuth:
    """Tests for GET /api/nudges base behaviour."""

    @pytest.mark.asyncio
    async def test_empty_state_only_has_velocity_nudge(
        self, client: AsyncClient, auth_headers: dict, test_profile: Profile
    ):
        # With no interview events, job applications or resumes, the only
        # nudge that can fire is application_velocity (0 < 5 this week).
        response = await client.get("/api/nudges", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "generated_at" in body
        assert _types(body["nudges"]) == ["application_velocity"]
        assert "0 applications" in body["nudges"][0]["description"]

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/nudges")
        assert response.status_code == 401


class TestOverdueFollowupNudge:
    @pytest.mark.asyncio
    async def test_overdue_followup_fires(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        overdue_date = (date.today() - timedelta(days=3)).isoformat()
        _create_interview_event(
            db,
            test_profile.id,
            company="Stripe",
            position="Backend Engineer",
            follow_up_date=overdue_date,
            follow_up_done=False,
        )

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]

        matches = _by_type(nudges, "overdue_followup")
        assert len(matches) == 1
        nudge = matches[0]
        assert nudge["entity_type"] == "interview_event"
        assert nudge["company"] == "Stripe"
        assert nudge["days_ago"] == 3

    @pytest.mark.asyncio
    async def test_completed_followup_does_not_fire(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        overdue_date = (date.today() - timedelta(days=3)).isoformat()
        _create_interview_event(
            db,
            test_profile.id,
            follow_up_date=overdue_date,
            follow_up_done=True,
        )

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]
        assert _by_type(nudges, "overdue_followup") == []


class TestInterviewPrepNudge:
    @pytest.mark.asyncio
    async def test_upcoming_interview_fires(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        soon = (date.today() + timedelta(days=1)).isoformat()
        _create_interview_event(
            db,
            test_profile.id,
            company="Netflix",
            position="Platform Engineer",
            event_type="onsite_interview",
            scheduled_date=soon,
            is_completed=False,
        )

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]

        matches = _by_type(nudges, "interview_prep")
        assert len(matches) == 1
        assert matches[0]["scheduled_date"] == soon

    @pytest.mark.asyncio
    async def test_far_future_interview_does_not_fire(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        far = (date.today() + timedelta(days=10)).isoformat()
        _create_interview_event(db, test_profile.id, scheduled_date=far)

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]
        assert _by_type(nudges, "interview_prep") == []


class TestThankYouNudge:
    @pytest.mark.asyncio
    async def test_recently_completed_interview_fires(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        _create_interview_event(
            db,
            test_profile.id,
            company="Figma",
            position="Designer",
            is_completed=True,
        )

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]

        matches = _by_type(nudges, "thank_you")
        assert len(matches) == 1
        assert matches[0]["company"] == "Figma"

    @pytest.mark.asyncio
    async def test_incomplete_interview_does_not_fire(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        _create_interview_event(db, test_profile.id, is_completed=False)

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]
        assert _by_type(nudges, "thank_you") == []


class TestStaleFollowupNudge:
    @pytest.mark.asyncio
    async def test_stale_application_fires(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        application_date = date.today() - timedelta(days=10)
        _create_job_application(
            db,
            test_profile.id,
            company="Acme Corp",
            position="Engineer",
            application_date=application_date,
            response_date=None,
            recruiter_name="Jane Doe",
            recruiter_email="jane@acme.com",
        )

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]

        matches = _by_type(nudges, "stale_followup")
        assert len(matches) == 1
        nudge = matches[0]
        assert nudge["days_ago"] == 10
        assert nudge["recruiter_name"] == "Jane Doe"
        assert nudge["recruiter_email"] == "jane@acme.com"

    @pytest.mark.asyncio
    async def test_recent_application_does_not_fire(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        application_date = date.today() - timedelta(days=2)
        _create_job_application(db, test_profile.id, application_date=application_date)

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]
        assert _by_type(nudges, "stale_followup") == []

    @pytest.mark.asyncio
    async def test_responded_application_does_not_fire(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        application_date = date.today() - timedelta(days=10)
        _create_job_application(
            db,
            test_profile.id,
            application_date=application_date,
            response_date=datetime.now(timezone.utc),
        )

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]
        assert _by_type(nudges, "stale_followup") == []


class TestApplicationVelocityNudge:
    @pytest.mark.asyncio
    async def test_low_weekly_volume_fires(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        _create_job_application(db, test_profile.id, application_date=date.today())

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]

        matches = _by_type(nudges, "application_velocity")
        assert len(matches) == 1
        assert matches[0]["entity_type"] == "metric"
        assert "1 application" in matches[0]["description"]

    @pytest.mark.asyncio
    async def test_high_weekly_volume_does_not_fire(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        for i in range(5):
            _create_job_application(
                db,
                test_profile.id,
                company=f"Company {i}",
                application_date=date.today(),
            )

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]
        assert _by_type(nudges, "application_velocity") == []


class TestResumeFreshnessNudge:
    @pytest.mark.asyncio
    async def test_stale_resume_fires(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        stale_updated_at = datetime.now(timezone.utc) - timedelta(days=45)
        resume = Resume(
            profile_id=test_profile.id,
            version_name="Old Resume",
            content="Stale content",
            updated_at=stale_updated_at,
        )
        db.add(resume)
        db.commit()

        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]

        matches = _by_type(nudges, "resume_freshness")
        assert len(matches) == 1
        assert matches[0]["entity_type"] == "resume"
        assert matches[0]["days_ago"] == 45

    @pytest.mark.asyncio
    async def test_fresh_resume_does_not_fire(
        self, client: AsyncClient, auth_headers: dict, test_resume: Resume
    ):
        response = await client.get("/api/nudges", headers=auth_headers)
        nudges = response.json()["nudges"]
        assert _by_type(nudges, "resume_freshness") == []


class TestNudgeUserIsolation:
    @pytest.mark.asyncio
    async def test_other_users_events_are_not_nudged(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        second_user_auth_headers: dict,
    ):
        overdue_date = (date.today() - timedelta(days=3)).isoformat()
        _create_interview_event(
            db,
            test_profile.id,
            follow_up_date=overdue_date,
            follow_up_done=False,
        )

        response = await client.get("/api/nudges", headers=second_user_auth_headers)
        assert response.status_code == 200
        # The second user gets their own (empty) data's velocity nudge only;
        # the first user's overdue interview event must never leak across.
        assert _types(response.json()["nudges"]) == ["application_velocity"]


class TestGenerateDraft:
    """Tests for POST /api/nudges/draft."""

    @pytest.fixture(autouse=True)
    def reset_llm(self):
        reset_llm_service()
        yield
        reset_llm_service()

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/nudges/draft",
            json={"nudge_type": "stale_followup", "entity_type": "job"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_nudge_type_returns_400(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/nudges/draft",
            json={"nudge_type": "not_a_real_type", "entity_type": "job"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_stale_followup_draft(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/nudges/draft",
            json={
                "nudge_type": "stale_followup",
                "entity_type": "job",
                "company": "Acme Corp",
                "position": "Engineer",
                "recruiter_name": "Jane Doe",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["content"]) > 0
        assert body["tips"] == [
            "Personalize with a detail from the job posting",
            "Send between Tuesday and Thursday for best response rates",
        ]

    @pytest.mark.asyncio
    async def test_interview_prep_draft(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/nudges/draft",
            json={
                "nudge_type": "interview_prep",
                "entity_type": "interview_event",
                "company": "Netflix",
                "position": "Platform Engineer",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["content"]) > 0
        assert body["tips"] == [
            "Practice answers out loud before the interview",
            "Research recent company news",
        ]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_500(self, client: AsyncClient, auth_headers: dict):
        llm_service = get_llm_service(provider_name="mock")
        llm_service.provider.set_failure_mode(
            fail_until=10, error=LLMServerError("boom", status_code=500)
        )
        try:
            response = await client.post(
                "/api/nudges/draft",
                json={
                    "nudge_type": "stale_followup",
                    "entity_type": "job",
                    "company": "Acme Corp",
                    "position": "Engineer",
                },
                headers=auth_headers,
            )
            assert response.status_code == 500
            assert "Please try again later" in response.json()["detail"]
        finally:
            llm_service.provider.clear_failure_mode()
