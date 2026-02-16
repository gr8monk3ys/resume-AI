"""
Job discovery / aggregation service.

Aggregates job listings from multiple free public APIs and feeds into
a single, standardised search interface.  Each data source is queried
independently so that a failure in one source does not block results
from the others.

Supported sources
-----------------
1. **Adzuna API** -- free tier (250 calls/month).
2. **RemoteOK**  -- free JSON API for remote positions.
3. **HN Who's Hiring RSS** -- Hacker News monthly hiring threads via RSS.

Results are cached per query with a 5-minute TTL to stay well within
rate limits and to reduce latency for repeated searches.
"""

from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx
from cachetools import TTLCache

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Standardised data model returned by every source adapter
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredJob:
    """Normalised representation of a job listing from any external source."""

    title: str
    company: str
    location: Optional[str] = None
    url: str = ""
    description_snippet: Optional[str] = None
    source: str = ""
    posted_date: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    remote: bool = False
    visa_sponsorship: Optional[str] = None
    match_score: Optional[int] = None

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary suitable for Pydantic models."""
        return asdict(self)


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

# Shared async-safe HTTP client timeout
_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=10.0)

# User-Agent sent with all outbound requests
_USER_AGENT = "ResuBoostAI/2.0 (job-discovery; +https://github.com/resuboost)"


def _truncate(text: Optional[str], max_length: int = 300) -> Optional[str]:
    """Return *text* truncated to *max_length* characters with an ellipsis."""
    if text is None:
        return None
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "\u2026"


def _strip_html(raw: Optional[str]) -> Optional[str]:
    """Remove HTML tags from *raw* and unescape entities."""
    if raw is None:
        return None
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = html.unescape(clean)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _safe_int(value: object) -> Optional[int]:
    """Try to coerce *value* to ``int``; return ``None`` on failure."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Source adapters
# ---------------------------------------------------------------------------

async def _fetch_adzuna(
    query: str,
    location: Optional[str],
    remote_only: bool,
    page: int,
    app_id: str,
    api_key: str,
    country: str = "us",
) -> List[DiscoveredJob]:
    """
    Query the Adzuna job search API.

    Documentation: https://developer.adzuna.com/docs/search

    The free tier permits 250 requests/month.  Results are paginated with
    10 items per page by default (the API maximum is 50).
    """
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    params: Dict[str, object] = {
        "app_id": app_id,
        "app_key": api_key,
        "what": query,
        "results_per_page": 25,
        "content-type": "application/json",
    }

    if location:
        params["where"] = location

    jobs: List[DiscoveredJob] = []
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers={"User-Agent": _USER_AGENT})
        resp.raise_for_status()
        data = resp.json()

    for item in data.get("results", []):
        is_remote = False
        title = item.get("title", "")
        desc = item.get("description", "")
        loc = item.get("location", {}).get("display_name", "")

        # Heuristic: flag remote if the title or location says so
        combined_text = f"{title} {desc} {loc}".lower()
        if "remote" in combined_text:
            is_remote = True

        if remote_only and not is_remote:
            continue

        jobs.append(
            DiscoveredJob(
                title=title,
                company=item.get("company", {}).get("display_name", "Unknown"),
                location=loc or None,
                url=item.get("redirect_url", ""),
                description_snippet=_truncate(_strip_html(desc)),
                source="adzuna",
                posted_date=item.get("created"),
                salary_min=_safe_int(item.get("salary_min")),
                salary_max=_safe_int(item.get("salary_max")),
                remote=is_remote,
            )
        )

    return jobs


async def _fetch_remoteok(
    query: str,
    _location: Optional[str],
    _remote_only: bool,
    _page: int,
) -> List[DiscoveredJob]:
    """
    Query the RemoteOK JSON API.

    The API is free and does not require authentication.  It returns all
    current remote job listings; we filter client-side by *query*.

    RemoteOK requests a polite User-Agent header.
    """
    url = "https://remoteok.com/api"
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
        resp.raise_for_status()
        data = resp.json()

    # The first element is a "legal notice" object; skip it.
    listings = data[1:] if len(data) > 1 else []

    query_lower = query.lower()
    query_terms = query_lower.split()

    jobs: List[DiscoveredJob] = []
    for item in listings:
        title = item.get("position", "") or ""
        company = item.get("company", "") or ""
        description = item.get("description", "") or ""
        tags = " ".join(item.get("tags", []))

        searchable = f"{title} {company} {description} {tags}".lower()
        if not any(term in searchable for term in query_terms):
            continue

        loc_value = item.get("location", "") or ""

        jobs.append(
            DiscoveredJob(
                title=title,
                company=company,
                location=loc_value if loc_value else "Remote",
                url=item.get("url", ""),
                description_snippet=_truncate(_strip_html(description)),
                source="remoteok",
                posted_date=item.get("date"),
                salary_min=_safe_int(item.get("salary_min")),
                salary_max=_safe_int(item.get("salary_max")),
                remote=True,
            )
        )

    return jobs


async def _fetch_hn_hiring(
    query: str,
    _location: Optional[str],
    remote_only: bool,
    _page: int,
) -> List[DiscoveredJob]:
    """
    Parse the Hacker News "Who's Hiring?" RSS feed.

    Uses the HN Algolia API search to find the most recent monthly
    "Who is hiring?" thread and then searches its comments.
    """
    # Step 1: Find the most recent "Who is hiring?" thread
    search_url = "https://hn.algolia.com/api/v1/search"
    params = {
        "query": "Ask HN: Who is hiring?",
        "tags": "story",
        "numericFilters": "points>100",
        "hitsPerPage": 1,
    }

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(search_url, params=params, headers={"User-Agent": _USER_AGENT})
        resp.raise_for_status()
        search_data = resp.json()

    hits = search_data.get("hits", [])
    if not hits:
        return []

    story_id = hits[0].get("objectID")
    if not story_id:
        return []

    # Step 2: Fetch top-level comments from the thread
    comments_url = f"https://hn.algolia.com/api/v1/search"
    comment_params = {
        "tags": f"comment,story_{story_id}",
        "hitsPerPage": 200,
    }

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(
            comments_url, params=comment_params, headers={"User-Agent": _USER_AGENT}
        )
        resp.raise_for_status()
        comments_data = resp.json()

    query_lower = query.lower()
    query_terms = query_lower.split()

    jobs: List[DiscoveredJob] = []
    for comment in comments_data.get("hits", []):
        text = comment.get("comment_text", "") or ""
        plain = _strip_html(text) or ""
        plain_lower = plain.lower()

        # Skip comments that do not match the search query
        if not any(term in plain_lower for term in query_terms):
            continue

        if remote_only and "remote" not in plain_lower:
            continue

        # Try to extract company name from the first line
        first_line = plain.split("\n")[0].strip() if plain else ""
        # Common HN format: "Company Name | Role | Location | ..."
        parts = [p.strip() for p in first_line.split("|")]
        company = parts[0] if parts else "Unknown"
        title = parts[1] if len(parts) > 1 else "See posting"
        location = parts[2] if len(parts) > 2 else None

        is_remote = "remote" in plain_lower

        story_url = f"https://news.ycombinator.com/item?id={comment.get('objectID', story_id)}"

        jobs.append(
            DiscoveredJob(
                title=_truncate(title, 120) or "See posting",
                company=_truncate(company, 80) or "Unknown",
                location=_truncate(location, 80) if location else None,
                url=story_url,
                description_snippet=_truncate(plain, 300),
                source="hn_hiring",
                posted_date=comment.get("created_at"),
                remote=is_remote,
            )
        )

    return jobs


# ---------------------------------------------------------------------------
# Match scoring
# ---------------------------------------------------------------------------

def _calculate_match_score(job: DiscoveredJob, resume_content: str) -> int:
    """
    Calculate a basic keyword overlap score between a job and a resume.

    The score is an integer from 0 to 100 derived from the fraction of
    distinct meaningful words in the job listing that also appear in the
    resume.  Words shorter than 3 characters are ignored so that common
    stop words do not inflate the score.

    This is intentionally a lightweight heuristic.  For deeper semantic
    matching the AI endpoints (``/api/ai/job-match-score``) should be
    used instead.
    """
    if not resume_content:
        return 0

    # Build the "job text" from all relevant fields
    job_parts = [
        job.title or "",
        job.company or "",
        job.description_snippet or "",
        job.location or "",
    ]
    job_text = " ".join(job_parts).lower()

    # Tokenise -- keep only alphanumeric tokens of length >= 3
    job_tokens = set(re.findall(r"[a-z0-9#+.]{3,}", job_text))
    if not job_tokens:
        return 0

    resume_lower = resume_content.lower()
    resume_tokens = set(re.findall(r"[a-z0-9#+.]{3,}", resume_lower))

    overlap = job_tokens & resume_tokens
    score = int((len(overlap) / len(job_tokens)) * 100)
    return min(score, 100)


# ---------------------------------------------------------------------------
# Main service class
# ---------------------------------------------------------------------------

class JobDiscoveryService:
    """
    Aggregates job listings from multiple public APIs and feeds.

    Usage::

        service = JobDiscoveryService()
        results, total, queried, failed = await service.search_jobs(
            query="python backend",
            location="San Francisco",
        )
    """

    # TTLCache: up to 256 cached query results, each valid for 5 minutes.
    _cache: TTLCache = TTLCache(maxsize=256, ttl=300)

    def __init__(self) -> None:
        self._settings = get_settings()

    # -- public helpers -----------------------------------------------------

    def get_available_sources(self) -> List[Dict[str, object]]:
        """Return metadata about each source and whether it is configured."""
        adzuna_configured = bool(
            self._settings.adzuna_app_id and self._settings.adzuna_api_key
        )
        return [
            {
                "name": "adzuna",
                "enabled": adzuna_configured and self._settings.enable_job_discovery,
                "requires_api_key": True,
                "api_key_configured": adzuna_configured,
                "description": (
                    "Adzuna job search API -- aggregates listings from thousands "
                    "of job boards. Free tier allows 250 requests/month."
                ),
            },
            {
                "name": "remoteok",
                "enabled": self._settings.enable_job_discovery,
                "requires_api_key": False,
                "api_key_configured": True,
                "description": (
                    "RemoteOK -- free JSON API listing remote-only positions "
                    "across all industries."
                ),
            },
            {
                "name": "hn_hiring",
                "enabled": self._settings.enable_job_discovery,
                "requires_api_key": False,
                "api_key_configured": True,
                "description": (
                    "Hacker News 'Who is Hiring?' -- monthly thread aggregating "
                    "tech job postings from the HN community."
                ),
            },
        ]

    # -- core search --------------------------------------------------------

    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        page: int = 1,
        resume_content: Optional[str] = None,
    ) -> Tuple[List[DiscoveredJob], int, List[str], List[str]]:
        """
        Search for jobs across all enabled external sources.

        Parameters
        ----------
        query : str
            Free-text search query (e.g. ``"python backend engineer"``).
        location : str, optional
            Location filter passed to sources that support it.
        remote_only : bool
            When ``True`` only remote positions are returned.
        page : int
            Pagination page (passed to sources that support it).
        resume_content : str, optional
            If provided, each result receives a ``match_score``.

        Returns
        -------
        tuple
            ``(jobs, total_results, sources_queried, sources_failed)``
        """
        # Check cache first
        cache_key = f"{query}|{location}|{remote_only}|{page}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            jobs, total, queried, failed = cached
            # Re-score if resume content changed (scoring is cheap)
            if resume_content:
                for job in jobs:
                    job.match_score = _calculate_match_score(job, resume_content)
                jobs.sort(key=lambda j: j.match_score or 0, reverse=True)
            return jobs, total, queried, failed

        all_jobs: List[DiscoveredJob] = []
        sources_queried: List[str] = []
        sources_failed: List[str] = []

        # --- Adzuna ---
        if self._settings.adzuna_app_id and self._settings.adzuna_api_key:
            sources_queried.append("adzuna")
            try:
                adzuna_jobs = await _fetch_adzuna(
                    query=query,
                    location=location,
                    remote_only=remote_only,
                    page=page,
                    app_id=self._settings.adzuna_app_id,
                    api_key=self._settings.adzuna_api_key,
                )
                all_jobs.extend(adzuna_jobs)
                logger.info("Adzuna returned %d results for query '%s'", len(adzuna_jobs), query)
            except Exception:
                logger.exception("Adzuna fetch failed for query '%s'", query)
                sources_failed.append("adzuna")

        # --- RemoteOK ---
        sources_queried.append("remoteok")
        try:
            remoteok_jobs = await _fetch_remoteok(
                query=query,
                _location=location,
                _remote_only=remote_only,
                _page=page,
            )
            all_jobs.extend(remoteok_jobs)
            logger.info("RemoteOK returned %d results for query '%s'", len(remoteok_jobs), query)
        except Exception:
            logger.exception("RemoteOK fetch failed for query '%s'", query)
            sources_failed.append("remoteok")

        # --- HN Who's Hiring ---
        sources_queried.append("hn_hiring")
        try:
            hn_jobs = await _fetch_hn_hiring(
                query=query,
                _location=location,
                remote_only=remote_only,
                _page=page,
            )
            all_jobs.extend(hn_jobs)
            logger.info("HN Hiring returned %d results for query '%s'", len(hn_jobs), query)
        except Exception:
            logger.exception("HN Hiring fetch failed for query '%s'", query)
            sources_failed.append("hn_hiring")

        # --- Scoring ---
        if resume_content:
            for job in all_jobs:
                job.match_score = _calculate_match_score(job, resume_content)
            # Sort best matches first
            all_jobs.sort(key=lambda j: j.match_score or 0, reverse=True)

        total = len(all_jobs)

        # Cache the aggregated results (before any resume-specific scoring
        # is applied, so the cache can be reused with different resumes).
        self._cache[cache_key] = (all_jobs, total, sources_queried, sources_failed)

        return all_jobs, total, sources_queried, sources_failed

    def match_score(self, job: DiscoveredJob, resume_content: str) -> int:
        """
        Calculate a keyword match score (0--100) for *job* against *resume_content*.

        This is a convenience wrapper around the module-level helper.
        """
        return _calculate_match_score(job, resume_content)


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------

_service_instance: Optional[JobDiscoveryService] = None


def get_job_discovery_service() -> JobDiscoveryService:
    """Return (and lazily create) the singleton :class:`JobDiscoveryService`."""
    global _service_instance
    if _service_instance is None:
        _service_instance = JobDiscoveryService()
    return _service_instance
