"""
Tests for the background JobScheduler service (app/services/scheduler.py).

The scheduler wraps a real APScheduler AsyncIOScheduler; only the job scraper
(the network boundary) is replaced with a small in-process fake so the
scheduler's own bookkeeping, authorization and error handling are exercised.
"""

from datetime import datetime, timedelta, timezone

import pytest
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent

from app.schemas.scheduler import (
    JobSchedulerStatus,
    ScheduledJobCreate,
    ScheduledJobStatus,
    ScrapeCriteria,
    ScrapeSource,
)
from app.services import scheduler as scheduler_module
from app.services.scheduler import JobScheduler, get_job_scheduler, reset_job_scheduler


class FakeScraper:
    """Records calls and returns canned (all_jobs, new_jobs) results."""

    def __init__(self, all_jobs=None, new_jobs=None, error=None):
        self.all_jobs = all_jobs if all_jobs is not None else []
        self.new_jobs = new_jobs if new_jobs is not None else []
        self.error = error
        self.calls = []

    async def check_for_new_jobs(self, user_id, source, criteria=None, custom_url=None):
        self.calls.append(
            {"user_id": user_id, "source": source, "criteria": criteria, "custom_url": custom_url}
        )
        if self.error is not None:
            raise self.error
        return self.all_jobs, self.new_jobs


def _job_data(**overrides):
    data = {
        "name": "New grad roles",
        "source": ScrapeSource.GITHUB_NEW_GRAD,
        "interval_minutes": 30,
    }
    data.update(overrides)
    return ScheduledJobCreate(**data)


@pytest.fixture
def scraper():
    return FakeScraper(all_jobs=["a", "b", "c"], new_jobs=["c"])


@pytest.fixture
async def make_sched():
    """Build started schedulers (APScheduler needs a running event loop)."""
    created = []

    def _make(job_scraper):
        instance = JobScheduler(job_scraper=job_scraper)
        instance.start()
        created.append(instance)
        return instance

    yield _make
    for instance in created:
        if instance.status != JobSchedulerStatus.STOPPED:
            instance.stop()


@pytest.fixture
async def sched(make_sched, scraper):
    return make_sched(scraper)


class TestJobRegistry:
    async def test_running_scheduler_reports_status(self, sched):
        status = sched.get_status()
        assert status.status == JobSchedulerStatus.RUNNING
        assert status.total_jobs == 0
        assert status.uptime_seconds >= 0

    async def test_add_job_registers_and_returns_response(self, sched):
        criteria = ScrapeCriteria(keywords=["python"], remote_only=True)
        resp = sched.add_scrape_job(user_id=7, job_data=_job_data(criteria=criteria))

        assert resp.id.startswith("scrape_7_")
        assert len(resp.id) == len("scrape_7_") + 8
        assert resp.user_id == 7
        assert resp.name == "New grad roles"
        assert resp.interval_minutes == 30
        assert resp.status == ScheduledJobStatus.ACTIVE
        assert resp.enabled is True
        assert resp.criteria.keywords == ["python"]
        assert resp.total_jobs_found == 0
        assert sched.get_job(resp.id) == resp

    async def test_add_disabled_job_is_paused(self, sched):
        resp = sched.add_scrape_job(user_id=1, job_data=_job_data(enabled=False))

        assert resp.enabled is False
        assert resp.status == ScheduledJobStatus.PAUSED
        assert sched.get_status().active_jobs == 0
        assert sched.get_status().total_jobs == 1

    async def test_get_jobs_filters_by_owner(self, sched):
        a = sched.add_scrape_job(user_id=1, job_data=_job_data(name="one"))
        b = sched.add_scrape_job(user_id=2, job_data=_job_data(name="two"))
        c = sched.add_scrape_job(user_id=1, job_data=_job_data(name="three"))

        assert {j.id for j in sched.get_jobs(user_id=1)} == {a.id, c.id}
        assert [j.id for j in sched.get_jobs(user_id=2)] == [b.id]
        assert len(sched.get_jobs()) == 3
        assert sched.get_jobs(user_id=99) == []

    async def test_get_job_hides_other_users_jobs(self, sched):
        resp = sched.add_scrape_job(user_id=1, job_data=_job_data())

        assert sched.get_job(resp.id, user_id=1) is not None
        assert sched.get_job(resp.id, user_id=2) is None
        assert sched.get_job("scrape_missing") is None

    async def test_remove_job_enforces_owner(self, sched):
        resp = sched.add_scrape_job(user_id=1, job_data=_job_data())

        assert sched.remove_job(resp.id, user_id=2) is False
        assert sched.get_job(resp.id) is not None

        assert sched.remove_job(resp.id, user_id=1) is True
        assert sched.get_job(resp.id) is None
        assert sched._scheduler.get_job(resp.id) is None

    async def test_remove_unknown_job_returns_false(self, sched):
        assert sched.remove_job("does-not-exist") is False

    async def test_remove_job_tolerates_apscheduler_desync(self, sched):
        resp = sched.add_scrape_job(user_id=1, job_data=_job_data())
        # Drop it from APScheduler behind the registry's back.
        sched._scheduler.remove_job(resp.id)

        assert sched.remove_job(resp.id) is True
        assert sched.get_jobs() == []


class TestUpdateJob:
    async def test_update_fields_and_pause_resume(self, sched):
        resp = sched.add_scrape_job(user_id=3, job_data=_job_data())
        new_criteria = ScrapeCriteria(companies=["Acme"])

        updated = sched.update_job(
            resp.id,
            user_id=3,
            name="Renamed",
            interval_minutes=120,
            criteria=new_criteria,
            enabled=False,
        )

        assert updated.name == "Renamed"
        assert updated.interval_minutes == 120
        assert updated.criteria.companies == ["Acme"]
        assert updated.enabled is False
        assert updated.status == ScheduledJobStatus.PAUSED
        trigger = sched._scheduler.get_job(resp.id).trigger
        assert trigger.interval == timedelta(minutes=120)

        resumed = sched.update_job(resp.id, user_id=3, enabled=True)
        assert resumed.enabled is True
        assert resumed.status == ScheduledJobStatus.ACTIVE
        # Untouched fields are preserved.
        assert resumed.name == "Renamed"

    async def test_update_rejects_wrong_owner_and_unknown_job(self, sched):
        resp = sched.add_scrape_job(user_id=3, job_data=_job_data())

        assert sched.update_job(resp.id, user_id=4, name="hijack") is None
        assert sched.get_job(resp.id).name == "New grad roles"
        assert sched.update_job("nope", user_id=3, name="x") is None


class TestTriggerJob:
    async def test_trigger_success_updates_counters(self, sched, scraper):
        resp = sched.add_scrape_job(
            user_id=5,
            job_data=_job_data(source=ScrapeSource.CUSTOM_URL, custom_url="https://example.com"),
        )

        result = await sched.trigger_job(resp.id, user_id=5)

        assert result.success is True
        assert result.jobs_found == 3
        assert result.new_jobs == 1
        assert result.errors == []
        assert scraper.calls == [
            {
                "user_id": 5,
                "source": ScrapeSource.CUSTOM_URL,
                "criteria": None,
                "custom_url": "https://example.com",
            }
        ]
        job = sched.get_job(resp.id)
        assert job.jobs_found_last_run == 3
        assert job.total_jobs_found == 1
        assert job.last_result == "Found 3 jobs, 1 new"
        assert job.last_run is not None

        await sched.trigger_job(resp.id)
        assert sched.get_job(resp.id).total_jobs_found == 2

    async def test_trigger_unknown_job(self, sched, scraper):
        result = await sched.trigger_job("ghost")

        assert result.success is False
        assert result.message == "Job not found"
        assert scraper.calls == []

    async def test_trigger_wrong_owner_does_not_scrape(self, sched, scraper):
        resp = sched.add_scrape_job(user_id=5, job_data=_job_data())

        result = await sched.trigger_job(resp.id, user_id=6)

        assert result.success is False
        assert result.message == "Not authorized"
        assert scraper.calls == []

    async def test_trigger_scraper_error_is_captured(self, make_sched):
        failing = FakeScraper(error=RuntimeError("upstream 503"))
        sched = make_sched(failing)
        resp = sched.add_scrape_job(user_id=5, job_data=_job_data())

        first = await sched.trigger_job(resp.id)
        second = await sched.trigger_job(resp.id)

        assert first.success is False
        assert first.message == "Job execution failed"
        assert second.errors == ["upstream 503"]
        job = sched.get_job(resp.id)
        assert job.error_count == 2
        assert job.last_result == "Error: upstream 503"
        assert job.total_jobs_found == 0


class TestExecuteScrapeJob:
    async def test_execute_invokes_callback_with_new_jobs(self, sched):
        received = []

        async def on_found(user_id, jobs):
            received.append((user_id, jobs))

        sched.set_on_jobs_found_callback(on_found)
        resp = sched.add_scrape_job(user_id=9, job_data=_job_data())

        await sched._execute_scrape_job(resp.id)

        assert received == [(9, ["c"])]
        job = sched.get_job(resp.id)
        assert job.last_result == "Found 3 jobs, 1 new"
        assert job.total_jobs_found == 1

    async def test_callback_not_called_without_new_jobs(self, make_sched):
        sched = make_sched(FakeScraper(all_jobs=["a"], new_jobs=[]))
        called = []

        async def on_found(user_id, jobs):
            called.append(jobs)

        sched.set_on_jobs_found_callback(on_found)
        resp = sched.add_scrape_job(user_id=9, job_data=_job_data())

        await sched._execute_scrape_job(resp.id)

        assert called == []
        assert sched.get_job(resp.id).last_result == "Found 1 jobs, 0 new"

    async def test_callback_failure_does_not_fail_job(self, sched):
        async def broken(user_id, jobs):
            raise ValueError("callback boom")

        sched.set_on_jobs_found_callback(broken)
        resp = sched.add_scrape_job(user_id=9, job_data=_job_data())

        await sched._execute_scrape_job(resp.id)

        assert sched.get_job(resp.id).total_jobs_found == 1

    async def test_disabled_and_unknown_jobs_are_skipped(self, sched, scraper):
        resp = sched.add_scrape_job(user_id=9, job_data=_job_data(enabled=False))

        await sched._execute_scrape_job(resp.id)
        await sched._execute_scrape_job("unknown")

        assert scraper.calls == []
        assert sched.get_job(resp.id).last_run is None

    async def test_scraper_error_is_recorded_and_reraised(self, make_sched):
        sched = make_sched(FakeScraper(error=ConnectionError("dns fail")))
        resp = sched.add_scrape_job(user_id=9, job_data=_job_data())

        with pytest.raises(ConnectionError, match="dns fail"):
            await sched._execute_scrape_job(resp.id)

        job = sched.get_job(resp.id)
        assert job.last_result == "Error: dns fail"
        assert job.last_run is not None


class TestExecutionEvents:
    def _event(self, code, job_id, exception=None):
        return JobExecutionEvent(
            code, job_id, "default", datetime.now(timezone.utc), exception=exception
        )

    async def test_error_event_marks_job_failed(self, sched):
        resp = sched.add_scrape_job(user_id=1, job_data=_job_data())

        sched._on_job_executed(self._event(EVENT_JOB_ERROR, resp.id, RuntimeError("bad")))
        sched._on_job_executed(self._event(EVENT_JOB_ERROR, resp.id, RuntimeError("bad")))

        job = sched.get_job(resp.id)
        assert job.status == ScheduledJobStatus.FAILED
        assert job.error_count == 2
        assert job.last_result == "Error: bad"
        status = sched.get_status()
        assert status.last_error == f"Job {resp.id} failed: bad"
        assert status.active_jobs == 0

    async def test_success_event_resets_error_state(self, sched):
        resp = sched.add_scrape_job(user_id=1, job_data=_job_data())
        sched._on_job_executed(self._event(EVENT_JOB_ERROR, resp.id, RuntimeError("bad")))

        sched._on_job_executed(self._event(EVENT_JOB_EXECUTED, resp.id))

        job = sched.get_job(resp.id)
        assert job.status == ScheduledJobStatus.ACTIVE
        assert job.error_count == 0

    async def test_event_for_unregistered_job_is_ignored(self, sched):
        sched._on_job_executed(self._event(EVENT_JOB_ERROR, "foreign", RuntimeError("x")))

        assert sched.get_status().last_error is None


class TestLifecycle:
    async def test_start_pause_resume_stop(self, scraper):
        sched = JobScheduler(job_scraper=scraper)
        assert sched.status == JobSchedulerStatus.STOPPED
        assert sched.get_status().uptime_seconds is None

        sched.start()
        assert sched.is_running
        resp = sched.add_scrape_job(user_id=1, job_data=_job_data(interval_minutes=15))
        # Once running, APScheduler computes a real next run ~interval from now.
        next_run = sched.get_job(resp.id).next_run
        assert next_run is not None
        delta = next_run - datetime.now(next_run.tzinfo)
        assert timedelta(minutes=14) < delta <= timedelta(minutes=15)
        assert sched.get_status().uptime_seconds >= 0

        sched.start()  # idempotent
        assert sched.is_running

        sched.pause()
        assert sched.status == JobSchedulerStatus.PAUSED
        assert not sched.is_running
        sched.pause()  # not running: no-op
        assert sched.status == JobSchedulerStatus.PAUSED

        sched.resume()
        assert sched.is_running
        sched.resume()  # not paused: no-op
        assert sched.is_running

        sched.stop()
        assert sched.status == JobSchedulerStatus.STOPPED
        sched.stop()  # already stopped: no-op
        assert sched.status == JobSchedulerStatus.STOPPED

    def test_resume_when_stopped_is_noop(self, scraper):
        sched = JobScheduler(job_scraper=scraper)
        sched.resume()
        assert sched.status == JobSchedulerStatus.STOPPED


class TestSingleton:
    def test_get_and_reset_singleton(self, monkeypatch):
        monkeypatch.setattr(scheduler_module, "_job_scheduler", None)
        monkeypatch.setattr(scheduler_module, "get_job_scraper", lambda: FakeScraper())

        first = get_job_scheduler()
        assert get_job_scheduler() is first

        reset_job_scheduler()
        assert scheduler_module._job_scheduler is None
        assert get_job_scheduler() is not first
        reset_job_scheduler()
