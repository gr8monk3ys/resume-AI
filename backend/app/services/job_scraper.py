"""
Job scraper service for fetching jobs from various sources.

Supports:
- SimplifyJobs GitHub repositories (New-Grad-Positions, Summer Internships)
- Custom URLs with configurable filters
- Rate limiting and caching to prevent blocking
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from app.schemas.job_import import GitHubRepoFilter, JobData, JobSource
from app.schemas.scheduler import ScrapeCriteria, ScrapeSource
from app.services.job_importer import JobImporter, get_job_importer

logger = logging.getLogger(__name__)


class JobScraperCache:
    """
    Simple in-memory cache to avoid duplicate fetches and reduce API calls.

    Stores scraped job data with TTL to prevent excessive requests.
    """

    def __init__(self, ttl_minutes: int = 30):
        """
        Initialize the cache.

        Args:
            ttl_minutes: Time-to-live for cache entries in minutes.
        """
        self._cache: dict[str, tuple[datetime, list[JobData]]] = {}
        self._job_hashes: set[str] = set()
        self._ttl = timedelta(minutes=ttl_minutes)

    def _generate_cache_key(self, source: str, criteria: Optional[ScrapeCriteria]) -> str:
        """Generate a unique cache key based on source and criteria."""
        criteria_str = ""
        if criteria:
            criteria_str = str(criteria.model_dump(exclude_none=True))
        return hashlib.md5(f"{source}:{criteria_str}".encode()).hexdigest()

    def _generate_job_hash(self, job: JobData) -> str:
        """Generate a unique hash for a job to detect duplicates."""
        unique_str = f"{job.company}:{job.title}:{job.location or ''}"
        return hashlib.md5(unique_str.lower().encode()).hexdigest()

    def get(self, source: str, criteria: Optional[ScrapeCriteria]) -> Optional[list[JobData]]:
        """
        Get cached jobs if available and not expired.

        Args:
            source: The scrape source identifier.
            criteria: The filtering criteria used.

        Returns:
            Cached job list or None if cache miss/expired.
        """
        key = self._generate_cache_key(source, criteria)
        if key in self._cache:
            timestamp, jobs = self._cache[key]
            if datetime.utcnow() - timestamp < self._ttl:
                logger.debug(f"Cache hit for {source}")
                return jobs
            else:
                # Expired, remove from cache
                del self._cache[key]
        return None

    def set(self, source: str, criteria: Optional[ScrapeCriteria], jobs: list[JobData]) -> None:
        """
        Store jobs in cache.

        Args:
            source: The scrape source identifier.
            criteria: The filtering criteria used.
            jobs: The list of jobs to cache.
        """
        key = self._generate_cache_key(source, criteria)
        self._cache[key] = (datetime.utcnow(), jobs)
        logger.debug(f"Cached {len(jobs)} jobs for {source}")

    def is_new_job(self, job: JobData) -> bool:
        """
        Check if a job is new (not seen before).

        Args:
            job: The job to check.

        Returns:
            True if the job is new, False if already seen.
        """
        job_hash = self._generate_job_hash(job)
        return job_hash not in self._job_hashes

    def mark_job_seen(self, job: JobData) -> None:
        """Mark a job as seen to avoid duplicates."""
        job_hash = self._generate_job_hash(job)
        self._job_hashes.add(job_hash)

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._job_hashes.clear()
        logger.info("Job scraper cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed.
        """
        now = datetime.utcnow()
        expired_keys = [
            key for key, (timestamp, _) in self._cache.items() if now - timestamp >= self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


class RateLimiter:
    """
    Rate limiter to prevent getting blocked by job sources.

    Implements a sliding window rate limit per source.
    """

    def __init__(self):
        """Initialize rate limiter with default limits per source."""
        self._requests: dict[str, list[datetime]] = {}
        # Requests per minute limits by source
        self._limits: dict[str, int] = {
            "github": 30,
            "default": 10,
        }
        self._window = timedelta(minutes=1)

    def can_request(self, source: str) -> bool:
        """
        Check if a request can be made to the source.

        Args:
            source: The source identifier.

        Returns:
            True if within rate limits, False otherwise.
        """
        now = datetime.utcnow()
        limit = self._limits.get(source, self._limits["default"])

        if source not in self._requests:
            self._requests[source] = []

        # Clean up old requests outside the window
        self._requests[source] = [ts for ts in self._requests[source] if now - ts < self._window]

        return len(self._requests[source]) < limit

    def record_request(self, source: str) -> None:
        """Record a request to the source."""
        if source not in self._requests:
            self._requests[source] = []
        self._requests[source].append(datetime.utcnow())

    async def wait_if_needed(self, source: str) -> None:
        """
        Wait if rate limit would be exceeded.

        Args:
            source: The source identifier.
        """
        while not self.can_request(source):
            logger.debug(f"Rate limit reached for {source}, waiting...")
            await asyncio.sleep(2)


class JobScraper:
    """
    Service for scraping job listings from various sources.

    Provides:
    - Scraping from SimplifyJobs GitHub repos
    - Custom URL scraping
    - Rate limiting to avoid blocks
    - Caching to reduce redundant requests
    - Filtering based on user criteria
    """

    # GitHub repo URLs for SimplifyJobs
    GITHUB_REPOS = {
        ScrapeSource.GITHUB_NEW_GRAD: "https://github.com/SimplifyJobs/New-Grad-Positions",
        ScrapeSource.GITHUB_INTERNSHIPS: "https://github.com/SimplifyJobs/Summer2025-Internships",
    }

    def __init__(
        self,
        cache_ttl_minutes: int = 30,
        job_importer: Optional[JobImporter] = None,
    ):
        """
        Initialize the job scraper.

        Args:
            cache_ttl_minutes: Cache time-to-live in minutes.
            job_importer: Optional JobImporter instance (uses singleton if not provided).
        """
        self._cache = JobScraperCache(ttl_minutes=cache_ttl_minutes)
        self._rate_limiter = RateLimiter()
        self._job_importer = job_importer or get_job_importer()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if scraper is currently running a job."""
        return self._is_running

    def _criteria_to_github_filter(
        self, criteria: Optional[ScrapeCriteria]
    ) -> Optional[GitHubRepoFilter]:
        """Convert ScrapeCriteria to GitHubRepoFilter."""
        if not criteria:
            return None

        return GitHubRepoFilter(
            locations=criteria.locations,
            companies=criteria.companies,
            exclude_companies=criteria.exclude_companies,
            sponsorship=criteria.sponsorship_required,
        )

    def _filter_jobs_by_criteria(
        self, jobs: list[JobData], criteria: Optional[ScrapeCriteria]
    ) -> list[JobData]:
        """
        Apply additional filtering criteria to jobs.

        Args:
            jobs: List of jobs to filter.
            criteria: Filtering criteria to apply.

        Returns:
            Filtered list of jobs.
        """
        if not criteria:
            return jobs

        filtered = []
        for job in jobs:
            # Keyword filtering
            if criteria.keywords:
                title_lower = job.title.lower()
                if not any(kw.lower() in title_lower for kw in criteria.keywords):
                    continue

            # Exclude keyword filtering
            if criteria.exclude_keywords:
                title_lower = job.title.lower()
                if any(kw.lower() in title_lower for kw in criteria.exclude_keywords):
                    continue

            # Remote only filtering
            if criteria.remote_only:
                location_lower = (job.location or "").lower()
                if not job.remote and "remote" not in location_lower:
                    continue

            filtered.append(job)

        return filtered

    async def scrape_github_repos(
        self,
        source: ScrapeSource,
        criteria: Optional[ScrapeCriteria] = None,
        max_jobs: int = 100,
    ) -> list[JobData]:
        """
        Scrape jobs from SimplifyJobs GitHub repositories.

        Args:
            source: The GitHub repo source to scrape.
            criteria: Optional filtering criteria.
            max_jobs: Maximum number of jobs to return.

        Returns:
            List of scraped JobData objects.

        Raises:
            ValueError: If source is not a GitHub source.
            Exception: If scraping fails.
        """
        if source not in self.GITHUB_REPOS:
            raise ValueError(f"Invalid GitHub source: {source}")

        repo_url = self.GITHUB_REPOS[source]
        logger.info(f"Scraping GitHub repo: {repo_url}")

        # Check cache first
        cached = self._cache.get(source.value, criteria)
        if cached is not None:
            logger.info(f"Returning {len(cached)} cached jobs for {source.value}")
            return cached[:max_jobs]

        # Rate limiting
        await self._rate_limiter.wait_if_needed("github")

        self._is_running = True
        try:
            self._rate_limiter.record_request("github")

            # Convert criteria to GitHub filter format
            github_filter = self._criteria_to_github_filter(criteria)

            # Use the job importer to fetch from GitHub
            jobs = await self._job_importer.import_from_github_repo(
                repo_url=repo_url,
                filters=github_filter,
                max_jobs=max_jobs * 2,  # Fetch more to allow for filtering
            )

            # Apply additional criteria filtering
            jobs = self._filter_jobs_by_criteria(jobs, criteria)

            # Cache the results
            self._cache.set(source.value, criteria, jobs)

            logger.info(f"Scraped {len(jobs)} jobs from {source.value}")
            return jobs[:max_jobs]

        except Exception as e:
            logger.error(f"Error scraping {source.value}: {e}")
            raise
        finally:
            self._is_running = False

    async def scrape_custom_url(
        self,
        url: str,
        criteria: Optional[ScrapeCriteria] = None,
    ) -> Optional[JobData]:
        """
        Scrape a single job from a custom URL.

        Args:
            url: The job posting URL.
            criteria: Optional filtering criteria (applied after scraping).

        Returns:
            JobData if successful and matches criteria, None otherwise.
        """
        logger.info(f"Scraping custom URL: {url}")

        # Rate limiting
        await self._rate_limiter.wait_if_needed("default")

        self._is_running = True
        try:
            self._rate_limiter.record_request("default")

            job = await self._job_importer.import_from_url(url)

            # Apply filtering
            if criteria:
                filtered = self._filter_jobs_by_criteria([job], criteria)
                if not filtered:
                    logger.info(f"Job from {url} filtered out by criteria")
                    return None
                job = filtered[0]

            return job

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            raise
        finally:
            self._is_running = False

    async def check_for_new_jobs(
        self,
        user_id: int,
        source: ScrapeSource,
        criteria: Optional[ScrapeCriteria] = None,
        custom_url: Optional[str] = None,
    ) -> tuple[list[JobData], list[JobData]]:
        """
        Check for new jobs matching user's alert criteria.

        Args:
            user_id: The user ID to check for.
            source: The source to check.
            criteria: Filtering criteria.
            custom_url: Custom URL if source is CUSTOM_URL.

        Returns:
            Tuple of (all_jobs, new_jobs) where new_jobs are jobs not seen before.
        """
        logger.info(f"Checking for new jobs for user {user_id} from {source.value}")

        all_jobs: list[JobData] = []

        if source == ScrapeSource.CUSTOM_URL:
            if not custom_url:
                logger.error("Custom URL required for CUSTOM_URL source")
                return [], []
            job = await self.scrape_custom_url(custom_url, criteria)
            if job:
                all_jobs = [job]
        else:
            all_jobs = await self.scrape_github_repos(source, criteria)

        # Filter for new jobs only
        new_jobs = []
        for job in all_jobs:
            if self._cache.is_new_job(job):
                new_jobs.append(job)
                self._cache.mark_job_seen(job)

        logger.info(f"Found {len(all_jobs)} total jobs, {len(new_jobs)} new for user {user_id}")
        return all_jobs, new_jobs

    def clear_cache(self) -> None:
        """Clear the scraper cache."""
        self._cache.clear()

    def cleanup(self) -> int:
        """
        Perform cache cleanup.

        Returns:
            Number of expired entries removed.
        """
        return self._cache.cleanup_expired()


# Singleton instance
_job_scraper: Optional[JobScraper] = None


def get_job_scraper() -> JobScraper:
    """Get or create the JobScraper singleton."""
    global _job_scraper
    if _job_scraper is None:
        _job_scraper = JobScraper()
    return _job_scraper


def reset_job_scraper() -> None:
    """Reset the JobScraper singleton (useful for testing)."""
    global _job_scraper
    _job_scraper = None
