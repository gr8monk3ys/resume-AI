"""
Tests for JobAlertService matching logic (app/services/job_alerts.py).

The router tests in test_job_alerts.py exercise CRUD over HTTP; these cover the
scoring rules and the check/test flows that decide which jobs a user is told about.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.job_alert import JobAlert
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User
from app.schemas.job_alert import AlertCriteria, JobAlertCreate, JobAlertUpdate, JobType
from app.services.job_alerts import JobAlertService, get_job_alert_service


def _job(
    company: str = "Acme",
    position: str = "Engineer",
    description: str = None,
    location: str = None,
    **kwargs,
) -> JobApplication:
    """Build an unsaved JobApplication for pure scoring tests."""
    return JobApplication(
        company=company,
        position=position,
        job_description=description,
        location=location,
        **kwargs,
    )


def _add_job(db: Session, profile: Profile, **kwargs) -> JobApplication:
    job = _job(**kwargs)
    job.profile_id = profile.id
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def service(db: Session) -> JobAlertService:
    return get_job_alert_service(db)


class TestCalculateMatchScore:
    """Scoring rules: fraction of applicable criteria matched; excludes veto."""

    def test_all_criteria_match_scores_one(self, service: JobAlertService):
        job = _job(
            company="Google LLC",
            position="Backend Engineer",
            description="We use Python and FastAPI",
            location="Remote - US",
        )
        criteria = AlertCriteria(
            keywords=["python", "rust"],
            companies=["google"],
            locations=["remote"],
        )

        score, matched = service._calculate_match_score(job, criteria)

        assert score == 1.0
        assert matched == [
            "Keywords: python",
            "Company: Google LLC",
            "Location: Remote - US",
        ]

    def test_partial_match_is_fraction_of_criteria(self, service: JobAlertService):
        job = _job(company="Meta", description="Python role", location="New York")
        criteria = AlertCriteria(
            keywords=["python"], companies=["google"], locations=["san francisco"]
        )

        score, matched = service._calculate_match_score(job, criteria)

        assert score == pytest.approx(1 / 3)
        assert matched == ["Keywords: python"]

    def test_keywords_match_against_company_position_and_location(self, service: JobAlertService):
        job = _job(company="Stripe", position="Staff Engineer", location="Dublin")
        criteria = AlertCriteria(keywords=["STAFF", "dublin", "golang"])

        score, matched = service._calculate_match_score(job, criteria)

        assert score == 1.0
        assert matched == ["Keywords: STAFF, dublin"]

    def test_exclude_keyword_vetoes_otherwise_perfect_match(self, service: JobAlertService):
        job = _job(company="Google", position="Senior Python Engineer")
        criteria = AlertCriteria(
            keywords=["python"], companies=["google"], exclude_keywords=["Senior"]
        )

        assert service._calculate_match_score(job, criteria) == (0.0, [])

    def test_no_criteria_scores_zero(self, service: JobAlertService):
        job = _job(description="anything at all")

        assert service._calculate_match_score(job, AlertCriteria()) == (0.0, [])

    def test_only_exclude_keywords_scores_zero_even_without_exclusion_hit(
        self, service: JobAlertService
    ):
        job = _job(description="Python role")

        score, matched = service._calculate_match_score(
            job, AlertCriteria(exclude_keywords=["php"])
        )

        assert (score, matched) == (0.0, [])

    def test_location_criterion_skipped_when_job_has_no_location(self, service: JobAlertService):
        # A job with no location is not penalised for the location criterion:
        # it drops out of the denominator rather than counting as a miss.
        job = _job(company="Google", location=None)
        criteria = AlertCriteria(companies=["google"], locations=["remote"])

        score, matched = service._calculate_match_score(job, criteria)

        assert score == 1.0
        assert matched == ["Company: Google"]


class TestSerialization:
    def test_round_trip_converts_enums_to_values(self, service: JobAlertService):
        raw = service._serialize_list([JobType.FULL_TIME, "Contract"])

        assert raw == '["Full-time", "Contract"]'
        assert service._deserialize_list(raw) == ["Full-time", "Contract"]

    def test_none_passes_through(self, service: JobAlertService):
        assert service._serialize_list(None) is None
        assert service._deserialize_list(None) is None

    def test_corrupt_json_deserializes_to_none(self, service: JobAlertService):
        assert service._deserialize_list("not json [") is None


class TestCheckAlerts:
    def test_returns_notifications_and_stamps_timestamps(
        self, db: Session, service: JobAlertService, test_user: User, test_profile: Profile
    ):
        alert = service.create_alert(test_user.id, JobAlertCreate(name="Py", keywords=["python"]))
        hit = _add_job(db, test_profile, company="A", description="python")
        _add_job(db, test_profile, company="B", description="java only")

        notifications = service.check_alerts(test_user.id)

        assert len(notifications) == 1
        note = notifications[0]
        assert note.alert_id == alert.id
        assert note.alert_name == "Py"
        assert [m.job_id for m in note.matches] == [hit.id]
        assert note.message == "Found 1 new job(s) matching your alert 'Py'"
        db.refresh(alert)
        assert alert.last_checked is not None
        assert alert.last_notified is not None

    def test_only_jobs_created_after_last_check_are_considered(
        self, db: Session, service: JobAlertService, test_user: User, test_profile: Profile
    ):
        alert = service.create_alert(test_user.id, JobAlertCreate(name="Py", keywords=["python"]))
        now = datetime.utcnow()
        _add_job(
            db,
            test_profile,
            company="Old",
            description="python",
            created_at=now - timedelta(days=2),
        )
        new = _add_job(
            db,
            test_profile,
            company="New",
            description="python",
            created_at=now + timedelta(hours=1),
        )
        alert.last_checked = now - timedelta(days=1)
        db.commit()

        notifications = service.check_alerts(test_user.id)

        assert [m.company for m in notifications[0].matches] == ["New"]
        assert notifications[0].matches[0].job_id == new.id

    def test_no_match_updates_last_checked_but_not_last_notified(
        self, db: Session, service: JobAlertService, test_user: User, test_profile: Profile
    ):
        alert = service.create_alert(test_user.id, JobAlertCreate(name="Rust", keywords=["rust"]))
        _add_job(db, test_profile, description="python")

        assert service.check_alerts(test_user.id) == []
        db.refresh(alert)
        assert alert.last_checked is not None
        assert alert.last_notified is None

    def test_inactive_alerts_are_skipped(
        self, db: Session, service: JobAlertService, test_user: User, test_profile: Profile
    ):
        alert = service.create_alert(
            test_user.id, JobAlertCreate(name="Off", keywords=["python"], is_active=False)
        )
        _add_job(db, test_profile, description="python")

        assert service.check_alerts(test_user.id) == []
        db.refresh(alert)
        assert alert.last_checked is None

    def test_user_without_profile_gets_no_notifications(
        self, service: JobAlertService, test_user: User
    ):
        service.create_alert(test_user.id, JobAlertCreate(name="Py", keywords=["python"]))

        assert service.check_alerts(test_user.id) == []


class TestTestAlert:
    def test_matches_sorted_by_score_descending(
        self, db: Session, service: JobAlertService, test_user: User, test_profile: Profile
    ):
        alert = service.create_alert(
            test_user.id,
            JobAlertCreate(name="G", keywords=["python"], companies=["google"]),
        )
        half = _add_job(db, test_profile, company="Meta", description="python")
        full = _add_job(db, test_profile, company="Google", description="python")
        _add_job(db, test_profile, company="Meta", description="cobol")

        result = service.test_alert(alert.id, test_user.id)

        assert result["alert_id"] == alert.id
        assert result["total_jobs_checked"] == 3
        assert result["match_count"] == 2
        assert [m["job_id"] for m in result["matching_jobs"]] == [full.id, half.id]
        assert [m["match_score"] for m in result["matching_jobs"]] == [1.0, 0.5]

    def test_limit_caps_jobs_checked(
        self, db: Session, service: JobAlertService, test_user: User, test_profile: Profile
    ):
        alert = service.create_alert(test_user.id, JobAlertCreate(name="Py", keywords=["python"]))
        for i in range(3):
            _add_job(db, test_profile, company=f"C{i}", description="python")

        result = service.test_alert(alert.id, test_user.id, limit=2)

        assert result["total_jobs_checked"] == 2
        assert result["match_count"] == 2

    def test_does_not_touch_last_checked(
        self, db: Session, service: JobAlertService, test_user: User, test_profile: Profile
    ):
        alert = service.create_alert(test_user.id, JobAlertCreate(name="Py", keywords=["python"]))
        _add_job(db, test_profile, description="python")

        service.test_alert(alert.id, test_user.id)

        db.refresh(alert)
        assert alert.last_checked is None

    def test_unknown_or_foreign_alert_returns_none(
        self, service: JobAlertService, test_user: User, second_user: User
    ):
        alert = service.create_alert(test_user.id, JobAlertCreate(name="Mine"))

        assert service.test_alert(alert.id + 999, test_user.id) is None
        assert service.test_alert(alert.id, second_user.id) is None

    def test_user_without_profile_gets_empty_result(
        self, service: JobAlertService, test_user: User
    ):
        alert = service.create_alert(test_user.id, JobAlertCreate(name="Py", keywords=["py"]))

        assert service.test_alert(alert.id, test_user.id) == {
            "alert_id": alert.id,
            "total_jobs_checked": 0,
            "matching_jobs": [],
            "match_count": 0,
        }


class TestCrudOwnership:
    def test_update_reserializes_list_fields_and_sets_scalars(
        self, service: JobAlertService, test_user: User
    ):
        alert = service.create_alert(
            test_user.id, JobAlertCreate(name="Old", keywords=["a"], min_salary=10)
        )

        updated = service.update_alert(
            alert.id,
            test_user.id,
            JobAlertUpdate(name="New", job_types=[JobType.CONTRACT], min_salary=20),
        )

        resp = service.alert_to_response(updated)
        assert resp["name"] == "New"
        assert resp["keywords"] == ["a"]
        assert resp["job_types"] == ["Contract"]
        assert resp["min_salary"] == 20

    def test_other_user_cannot_update_or_delete(
        self, db: Session, service: JobAlertService, test_user: User, second_user: User
    ):
        alert = service.create_alert(test_user.id, JobAlertCreate(name="Mine"))

        assert service.update_alert(alert.id, second_user.id, JobAlertUpdate(name="x")) is None
        assert service.delete_alert(alert.id, second_user.id) is False
        assert db.query(JobAlert).filter(JobAlert.id == alert.id).one().name == "Mine"

        assert service.delete_alert(alert.id, test_user.id) is True
        assert service.get_alert(alert.id, test_user.id) is None
