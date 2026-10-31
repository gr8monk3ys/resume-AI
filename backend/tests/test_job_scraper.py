"""
Tests for the job scraper service (app/services/job_scraper.py).

Covers the logic that decides what a user is alerted about: criteria filtering,
"new job" de-duplication, cache TTL behaviour and the per-source rate limiter.
The JobImporter collaborator is replaced by a small in-memory fake so no
network access happens; everything under test is the real scraper code.
"""

from datetime import datetime, timedelta
from typing import Optional

import pytest

from app.schemas.job_import import GitHubRepoFilter, JobData
from app.schemas.scheduler import ScrapeCriteria, ScrapeSource
from app.services import job_scraper as job_scraper_module
from app.services.job_scraper import (
    JobScraper,
    JobScraperCache,
    RateLimiter,
    get_job_scraper,
    reset_job_scraper,
)


def _job(title: str = "Software Engineer", company: str = "Acme", **kwargs) -> JobData:
    return JobData(title=title, company=company, **kwargs)


class FakeImporter:
    """Stand-in for JobImporter that records calls and returns canned jobs."""

    def __init__(self, repo_jobs: Optional[list[JobData]] = None, url_job: JobData = None):
        self.repo_jobs = repo_jobs or []
        self.url_job = url_job
        self.repo_calls: list[dict] = []
        self.url_calls: list[str] = []
        self.fail_with: Optional[Exception] = None

    async def import_from_github_repo(self, repo_url, filters=None, max_jobs=100):
        self.repo_calls.append({"repo_url": repo_url, "filters": filters, "max_jobs": max_jobs})
        if self.fail_with:
            raise self.fail_with
        return list(self.repo_jobs)

    async def import_from_url(self, url):
        self.url_calls.append(url)
        if self.fail_with:
            raise self.fail_with
        return self.url_job


class _Clock:
    """Controllable replacement for the module's datetime (only utcnow is used)."""

    now = datetime(2026, 1, 1, 12, 0, 0)

    @classmethod
    def utcnow(cls) -> datetime:
        return cls.now


@pytest.fixture
def clock(monkeypatch):
    _Clock.now = datetime(2026, 1, 1, 12, 0, 0)
    monkeypatch.setattr(job_scraper_module, "datetime", _Clock)
    return _Clock


# ---------------------------------------------------------------------------
# _filter_jobs_by_criteria
# ---------------------------------------------------------------------------


class TestFilterJobsByCriteria:
    def setup_method(self):
        self.scraper = JobScraper(job_importer=FakeImporter())

    def test_no_criteria_returns_jobs_unchanged(self):
        jobs = [_job("A"), _job("B")]
        assert self.scraper._filter_jobs_by_criteria(jobs, None) is jobs

    def test_keywords_match_title_case_insensitively(self):
        jobs = [_job("Senior BACKEND Engineer"), _job("Product Designer")]
        criteria = ScrapeCriteria(keywords=["backend"])
        result = self.scraper._filter_jobs_by_criteria(jobs, criteria)
        assert [j.title for j in result] == ["Senior BACKEND Engineer"]

    def test_keywords_are_ored(self):
        jobs = [_job("Data Scientist"), _job("ML Engineer"), _job("Recruiter")]
        criteria = ScrapeCriteria(keywords=["data", "ml"])
        result = self.scraper._filter_jobs_by_criteria(jobs, criteria)
        assert [j.title for j in result] == ["Data Scientist", "ML Engineer"]

    def test_keywords_only_match_title_not_description(self):
        jobs = [_job("Recruiter", description="work with python engineers")]
        criteria = ScrapeCriteria(keywords=["python"])
        assert self.scraper._filter_jobs_by_criteria(jobs, criteria) == []

    def test_exclude_keywords_drop_matching_titles(self):
        jobs = [_job("Senior Engineer"), _job("Engineer I")]
        criteria = ScrapeCriteria(exclude_keywords=["SENIOR"])
        result = self.scraper._filter_jobs_by_criteria(jobs, criteria)
        assert [j.title for j in result] == ["Engineer I"]

    def test_exclude_wins_over_include(self):
        jobs = [_job("Senior Backend Engineer"), _job("Backend Engineer")]
        criteria = ScrapeCriteria(keywords=["backend"], exclude_keywords=["senior"])
        result = self.scraper._filter_jobs_by_criteria(jobs, criteria)
        assert [j.title for j in result] == ["Backend Engineer"]

    def test_remote_only_accepts_remote_flag_or_remote_location(self):
        jobs = [
            _job("Flagged", remote=True, location="NYC"),
            _job("By location", remote=None, location="Remote - US"),
            _job("Onsite", remote=False, location="Austin, TX"),
            _job("No location", remote=None, location=None),
        ]
        criteria = ScrapeCriteria(remote_only=True)
        result = self.scraper._filter_jobs_by_criteria(jobs, criteria)
        assert [j.title for j in result] == ["Flagged", "By location"]

    def test_empty_criteria_object_keeps_everything(self):
        jobs = [_job("A", remote=False), _job("B")]
        assert self.scraper._filter_jobs_by_criteria(jobs, ScrapeCriteria()) == jobs


class TestCriteriaToGithubFilter:
    def test_none_criteria_gives_none(self):
        assert JobScraper(job_importer=FakeImporter())._criteria_to_github_filter(None) is None

    def test_maps_fields(self):
        criteria = ScrapeCriteria(
            locations=["Remote"],
            companies=["Acme"],
            exclude_companies=["Evil Corp"],
            sponsorship_required=True,
            keywords=["ignored here"],
        )
        result = JobScraper(job_importer=FakeImporter())._criteria_to_github_filter(criteria)
        assert isinstance(result, GitHubRepoFilter)
        assert result.locations == ["Remote"]
        assert result.companies == ["Acme"]
        assert result.exclude_companies == ["Evil Corp"]
        assert result.sponsorship is True
        assert result.min_posted_date is None


# ---------------------------------------------------------------------------
# JobScraperCache
# ---------------------------------------------------------------------------


class TestJobScraperCache:
    def test_get_miss_returns_none(self, clock):
        assert JobScraperCache().get("github_new_grad", None) is None

    def test_set_then_get_within_ttl(self, clock):
        cache = JobScraperCache(ttl_minutes=30)
        jobs = [_job()]
        cache.set("src", None, jobs)
        clock.now += timedelta(minutes=29, seconds=59)
        assert cache.get("src", None) == jobs

    def test_entry_expires_at_ttl_and_is_evicted(self, clock):
        cache = JobScraperCache(ttl_minutes=30)
        cache.set("src", None, [_job()])
        clock.now += timedelta(minutes=30)
        assert cache.get("src", None) is None
        assert cache._cache == {}

    def test_key_depends_on_source_and_criteria(self, clock):
        cache = JobScraperCache()
        cache.set("src", ScrapeCriteria(keywords=["python"]), [_job("Python Dev")])
        assert cache.get("other", ScrapeCriteria(keywords=["python"])) is None
        assert cache.get("src", ScrapeCriteria(keywords=["go"])) is None
        assert cache.get("src", None) is None
        assert cache.get("src", ScrapeCriteria(keywords=["python"]))[0].title == "Python Dev"

    def test_job_identity_is_company_title_location_case_insensitive(self):
        cache = JobScraperCache()
        cache.mark_job_seen(_job("Engineer", "Acme", location="NYC"))
        assert not cache.is_new_job(_job("ENGINEER", "acme", location="nyc"))
        assert cache.is_new_job(_job("Engineer", "Acme", location="SF"))
        assert cache.is_new_job(_job("Engineer", "Acme"))  # no location differs from NYC

    def test_cleanup_expired_counts_and_removes_only_expired(self, clock):
        cache = JobScraperCache(ttl_minutes=10)
        cache.set("old", None, [])
        clock.now += timedelta(minutes=6)
        cache.set("fresh", None, [])
        clock.now += timedelta(minutes=5)  # old is 11 min, fresh is 5 min
        assert cache.cleanup_expired() == 1
        assert cache.get("fresh", None) == []
        assert cache.get("old", None) is None

    def test_clear_resets_cache_and_seen_jobs(self, clock):
        cache = JobScraperCache()
        job = _job()
        cache.set("src", None, [job])
        cache.mark_job_seen(job)
        cache.clear()
        assert cache.get("src", None) is None
        assert cache.is_new_job(job)


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_github_limit_is_30_per_minute(self, clock):
        limiter = RateLimiter()
        for _ in range(29):
            limiter.record_request("github")
        assert limiter.can_request("github")
        limiter.record_request("github")
        assert not limiter.can_request("github")

    def test_unknown_source_uses_default_limit_of_10(self, clock):
        limiter = RateLimiter()
        for _ in range(10):
            limiter.record_request("somewhere")
        assert not limiter.can_request("somewhere")
        assert limiter.can_request("github")  # sources are tracked independently

    def test_window_slides_after_one_minute(self, clock):
        limiter = RateLimiter()
        for _ in range(10):
            limiter.record_request("default")
        clock.now += timedelta(seconds=59)
        assert not limiter.can_request("default")
        clock.now += timedelta(seconds=1)
        assert limiter.can_request("default")
        assert limiter._requests["default"] == []

    async def test_wait_if_needed_returns_immediately_when_under_limit(self, clock, monkeypatch):
        async def _no_sleep(_):  # pragma: no cover - must not be reached
            raise AssertionError("should not sleep")

        monkeypatch.setattr(job_scraper_module.asyncio, "sleep", _no_sleep)
        await RateLimiter().wait_if_needed("github")

    async def test_wait_if_needed_sleeps_until_window_frees(self, clock, monkeypatch):
        limiter = RateLimiter()
        for _ in range(10):
            limiter.record_request("default")
        sleeps: list[float] = []

        async def _advance(seconds):
            sleeps.append(seconds)
            clock.now += timedelta(seconds=seconds)

        monkeypatch.setattr(job_scraper_module.asyncio, "sleep", _advance)
        await limiter.wait_if_needed("default")
        assert sleeps == [2] * 30  # 60s window / 2s polls


# ---------------------------------------------------------------------------
# JobScraper orchestration
# ---------------------------------------------------------------------------


class TestScrapeGithubRepos:
    async def test_rejects_non_github_source(self):
        scraper = JobScraper(job_importer=FakeImporter())
        with pytest.raises(ValueError, match="Invalid GitHub source"):
            await scraper.scrape_github_repos(ScrapeSource.CUSTOM_URL)

    async def test_fetches_filters_and_truncates(self, clock):
        importer = FakeImporter(
            repo_jobs=[_job(f"Backend {i}") for i in range(5)] + [_job("Designer")]
        )
        scraper = JobScraper(job_importer=importer)
        criteria = ScrapeCriteria(keywords=["backend"], companies=["Acme"])

        jobs = await scraper.scrape_github_repos(ScrapeSource.GITHUB_NEW_GRAD, criteria, max_jobs=3)

        assert [j.title for j in jobs] == ["Backend 0", "Backend 1", "Backend 2"]
        call = importer.repo_calls[0]
        assert call["repo_url"] == JobScraper.GITHUB_REPOS[ScrapeSource.GITHUB_NEW_GRAD]
        assert call["max_jobs"] == 6  # over-fetches 2x to leave room for filtering
        assert call["filters"].companies == ["Acme"]
        assert not scraper.is_running

    async def test_second_call_is_served_from_cache(self, clock):
        importer = FakeImporter(repo_jobs=[_job("A"), _job("B")])
        scraper = JobScraper(job_importer=importer)

        await scraper.scrape_github_repos(ScrapeSource.GITHUB_INTERNSHIPS)
        again = await scraper.scrape_github_repos(ScrapeSource.GITHUB_INTERNSHIPS, max_jobs=1)

        assert len(importer.repo_calls) == 1
        assert [j.title for j in again] == ["A"]

    async def test_importer_error_propagates_and_resets_running(self, clock):
        importer = FakeImporter()
        importer.fail_with = RuntimeError("github down")
        scraper = JobScraper(job_importer=importer)

        with pytest.raises(RuntimeError, match="github down"):
            await scraper.scrape_github_repos(ScrapeSource.GITHUB_NEW_GRAD)

        assert not scraper.is_running
        # A failure must not poison the cache.
        assert scraper._cache.get(ScrapeSource.GITHUB_NEW_GRAD.value, None) is None


class TestScrapeCustomUrl:
    async def test_returns_job_when_it_matches(self, clock):
        importer = FakeImporter(url_job=_job("Remote Engineer", remote=True))
        scraper = JobScraper(job_importer=importer)
        job = await scraper.scrape_custom_url(
            "https://example.com/job/1", ScrapeCriteria(remote_only=True)
        )
        assert job.title == "Remote Engineer"
        assert importer.url_calls == ["https://example.com/job/1"]

    async def test_returns_none_when_filtered_out(self, clock):
        importer = FakeImporter(url_job=_job("Senior Engineer"))
        scraper = JobScraper(job_importer=importer)
        job = await scraper.scrape_custom_url(
            "https://example.com/job/1", ScrapeCriteria(exclude_keywords=["senior"])
        )
        assert job is None

    async def test_error_propagates(self, clock):
        importer = FakeImporter()
        importer.fail_with = ValueError("bad page")
        scraper = JobScraper(job_importer=importer)
        with pytest.raises(ValueError, match="bad page"):
            await scraper.scrape_custom_url("https://example.com/x")
        assert not scraper.is_running


class TestCheckForNewJobs:
    async def test_custom_url_without_url_returns_empty(self, clock):
        importer = FakeImporter(url_job=_job())
        scraper = JobScraper(job_importer=importer)
        assert await scraper.check_for_new_jobs(1, ScrapeSource.CUSTOM_URL) == ([], [])
        assert importer.url_calls == []

    async def test_custom_url_filtered_out_gives_no_jobs(self, clock):
        importer = FakeImporter(url_job=_job("Senior Engineer"))
        scraper = JobScraper(job_importer=importer)
        all_jobs, new_jobs = await scraper.check_for_new_jobs(
            1,
            ScrapeSource.CUSTOM_URL,
            ScrapeCriteria(exclude_keywords=["senior"]),
            custom_url="https://example.com/job",
        )
        assert all_jobs == [] and new_jobs == []

    async def test_jobs_are_only_new_once(self, clock):
        importer = FakeImporter(repo_jobs=[_job("A"), _job("B")])
        scraper = JobScraper(job_importer=importer)

        all1, new1 = await scraper.check_for_new_jobs(1, ScrapeSource.GITHUB_NEW_GRAD)
        assert [j.title for j in all1] == ["A", "B"]
        assert [j.title for j in new1] == ["A", "B"]

        importer.repo_jobs = [_job("A"), _job("B"), _job("C")]
        scraper.clear_cache()  # drop the TTL cache AND the seen set
        all2, new2 = await scraper.check_for_new_jobs(1, ScrapeSource.GITHUB_NEW_GRAD)
        assert [j.title for j in new2] == ["A", "B", "C"]

        scraper._cache._cache.clear()  # expire listing cache only, keep seen set
        all3, new3 = await scraper.check_for_new_jobs(1, ScrapeSource.GITHUB_NEW_GRAD)
        assert [j.title for j in all3] == ["A", "B", "C"]
        assert new3 == []

    async def test_duplicates_within_one_batch_counted_once(self, clock):
        importer = FakeImporter(repo_jobs=[_job("A", location="NYC"), _job("a", location="nyc")])
        scraper = JobScraper(job_importer=importer)
        all_jobs, new_jobs = await scraper.check_for_new_jobs(1, ScrapeSource.GITHUB_NEW_GRAD)
        assert len(all_jobs) == 2
        assert len(new_jobs) == 1

    def test_cleanup_delegates_to_cache_expiry(self, clock):
        scraper = JobScraper(cache_ttl_minutes=1, job_importer=FakeImporter())
        scraper._cache.set("x", None, [])
        clock.now += timedelta(minutes=2)
        assert scraper.cleanup() == 1


def test_singleton_get_and_reset(monkeypatch):
    monkeypatch.setattr(job_scraper_module, "get_job_importer", FakeImporter)
    reset_job_scraper()
    try:
        first = get_job_scraper()
        assert get_job_scraper() is first
        reset_job_scraper()
        assert get_job_scraper() is not first
    finally:
        reset_job_scraper()
