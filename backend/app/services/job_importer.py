"""
Job import service for scraping job details from URLs and GitHub repos.

Supports:
- LinkedIn Jobs
- Indeed
- Glassdoor
- Lever (ATS)
- Greenhouse (ATS)
- Workday (ATS)
- Company career pages
- SimplifyJobs GitHub repos (New-Grad-Positions, Summer2025-Internships)
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.schemas.job_import import (
    BulkImportResponse,
    GitHubRepoFilter,
    GitHubRepoImportResponse,
    ImportError,
    ImportResult,
    JobData,
    JobImportResponse,
    JobPreviewResponse,
    JobSource,
    JobType,
)

logger = logging.getLogger(__name__)


class JobImportError(Exception):
    """Base exception for job import errors."""

    def __init__(self, message: str, error_code: str = "IMPORT_ERROR", recoverable: bool = False):
        self.message = message
        self.error_code = error_code
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitError(JobImportError):
    """Raised when rate limited by source."""

    def __init__(self, message: str = "Rate limited by source"):
        super().__init__(message, "RATE_LIMITED", recoverable=True)


class AccessDeniedError(JobImportError):
    """Raised when access is denied."""

    def __init__(self, message: str = "Access denied by source"):
        super().__init__(message, "ACCESS_DENIED", recoverable=False)


class ParseError(JobImportError):
    """Raised when parsing fails."""

    def __init__(self, message: str = "Failed to parse job data"):
        super().__init__(message, "PARSE_ERROR", recoverable=False)


class JobImporter:
    """
    Service for importing job listings from various sources.

    Supports URL scraping, GitHub repo parsing, and bulk imports.
    Implements rate limiting and graceful error handling.
    """

    # Default headers for HTTP requests
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    }

    # URL patterns for detecting job sources
    URL_PATTERNS = {
        JobSource.LINKEDIN: [
            r"linkedin\.com/jobs/",
            r"linkedin\.com/job/",
        ],
        JobSource.INDEED: [
            r"indeed\.com/viewjob",
            r"indeed\.com/job/",
            r"indeed\.com/rc/",
        ],
        JobSource.GLASSDOOR: [
            r"glassdoor\.com/job-listing/",
            r"glassdoor\.com/Job/",
        ],
        JobSource.LEVER: [
            r"lever\.co/",
            r"jobs\.lever\.co/",
        ],
        JobSource.GREENHOUSE: [
            r"greenhouse\.io/",
            r"boards\.greenhouse\.io/",
        ],
        JobSource.WORKDAY: [
            r"myworkdayjobs\.com/",
            r"\.wd\d+\.myworkdayjobs\.com/",
        ],
    }

    # Rate limiting settings (requests per source per minute)
    RATE_LIMITS = {
        JobSource.LINKEDIN: 5,
        JobSource.INDEED: 10,
        JobSource.GLASSDOOR: 5,
        JobSource.LEVER: 20,
        JobSource.GREENHOUSE: 20,
        JobSource.WORKDAY: 10,
        JobSource.GITHUB_SIMPLIFY: 30,
        JobSource.COMPANY_SITE: 15,
        JobSource.UNKNOWN: 10,
    }

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the job importer.

        Args:
            timeout: HTTP request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            retry_delay: Base delay between retries in seconds.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._request_timestamps: dict[JobSource, list[datetime]] = {}

    def _detect_source(self, url: str) -> JobSource:
        """
        Detect the job source from a URL.

        Args:
            url: The job URL to analyze.

        Returns:
            The detected JobSource enum value.
        """
        url_lower = url.lower()

        for source, patterns in self.URL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return source

        return JobSource.COMPANY_SITE

    def _check_rate_limit(self, source: JobSource) -> bool:
        """
        Check if we're within rate limits for a source.

        Args:
            source: The job source to check.

        Returns:
            True if within limits, False if rate limited.
        """
        now = datetime.utcnow()
        limit = self.RATE_LIMITS.get(source, 10)

        if source not in self._request_timestamps:
            self._request_timestamps[source] = []

        # Remove timestamps older than 1 minute
        self._request_timestamps[source] = [
            ts for ts in self._request_timestamps[source]
            if (now - ts).total_seconds() < 60
        ]

        if len(self._request_timestamps[source]) >= limit:
            return False

        self._request_timestamps[source].append(now)
        return True

    async def _fetch_url(self, url: str, headers: Optional[dict] = None) -> str:
        """
        Fetch content from a URL with retry logic.

        Args:
            url: The URL to fetch.
            headers: Optional custom headers.

        Returns:
            The response text content.

        Raises:
            JobImportError: If the request fails after retries.
        """
        request_headers = {**self.DEFAULT_HEADERS, **(headers or {})}

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(url, headers=request_headers)

                    if response.status_code == 429:
                        raise RateLimitError(
                            f"Rate limited by {urlparse(url).netloc}"
                        )

                    if response.status_code == 403:
                        raise AccessDeniedError(
                            f"Access denied by {urlparse(url).netloc}"
                        )

                    if response.status_code == 404:
                        raise JobImportError(
                            "Job posting not found (404)",
                            "NOT_FOUND",
                            recoverable=False,
                        )

                    response.raise_for_status()
                    return response.text

            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise JobImportError(
                    "Request timed out",
                    "TIMEOUT",
                    recoverable=True,
                )
            except httpx.HTTPStatusError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise JobImportError(
                    f"HTTP error: {e.response.status_code}",
                    "HTTP_ERROR",
                    recoverable=True,
                )
            except (RateLimitError, AccessDeniedError, JobImportError):
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                raise JobImportError(
                    f"Failed to fetch URL: {str(e)}",
                    "FETCH_ERROR",
                    recoverable=False,
                )

    def _parse_salary(self, salary_text: str) -> tuple[Optional[int], Optional[int], str]:
        """
        Parse salary information from text.

        Args:
            salary_text: Raw salary text (e.g., "$80,000 - $120,000/year").

        Returns:
            Tuple of (min_salary, max_salary, currency).
        """
        if not salary_text:
            return None, None, "USD"

        # Clean and normalize the text
        text = salary_text.replace(",", "").lower()

        # Detect currency
        currency = "USD"
        if "gbp" in text or chr(163) in text:  # pound sign
            currency = "GBP"
        elif "eur" in text or chr(8364) in text:  # euro sign
            currency = "EUR"
        elif "cad" in text:
            currency = "CAD"

        # Extract numbers
        numbers = re.findall(r"\d+\.?\d*k?", text)

        parsed_numbers = []
        for num in numbers:
            if "k" in num:
                parsed_numbers.append(int(float(num.replace("k", "")) * 1000))
            else:
                val = float(num)
                # Likely hourly rate if small number
                if val < 500:
                    val = val * 2080  # Approximate annual
                parsed_numbers.append(int(val))

        if len(parsed_numbers) >= 2:
            return min(parsed_numbers[:2]), max(parsed_numbers[:2]), currency
        elif len(parsed_numbers) == 1:
            return parsed_numbers[0], parsed_numbers[0], currency

        return None, None, currency

    def _parse_job_type(self, text: str) -> JobType:
        """
        Parse job type from text.

        Args:
            text: Raw text containing job type info.

        Returns:
            The detected JobType enum value.
        """
        if not text:
            return JobType.UNKNOWN

        text_lower = text.lower()

        if "intern" in text_lower:
            return JobType.INTERNSHIP
        elif "contract" in text_lower or "contractor" in text_lower:
            return JobType.CONTRACT
        elif "part-time" in text_lower or "part time" in text_lower:
            return JobType.PART_TIME
        elif "temporary" in text_lower or "temp " in text_lower:
            return JobType.TEMPORARY
        elif "remote" in text_lower:
            return JobType.REMOTE
        elif "hybrid" in text_lower:
            return JobType.HYBRID
        elif "full-time" in text_lower or "full time" in text_lower:
            return JobType.FULL_TIME

        return JobType.UNKNOWN

    def _extract_json_ld(self, html: str) -> Optional[dict]:
        """
        Extract JSON-LD structured data from HTML.

        Args:
            html: The HTML content.

        Returns:
            Parsed JSON-LD data or None.
        """
        import json

        # Find JSON-LD script tags
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            try:
                data = json.loads(match.strip())

                # Handle array format
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "JobPosting":
                            return item
                elif data.get("@type") == "JobPosting":
                    return data

            except json.JSONDecodeError:
                continue

        return None

    def _extract_meta_tags(self, html: str) -> dict:
        """
        Extract Open Graph and other meta tags.

        Args:
            html: The HTML content.

        Returns:
            Dictionary of extracted meta values.
        """
        meta = {}

        # Open Graph tags
        og_patterns = {
            "title": r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
            "description": r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
            "site_name": r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)["\']',
        }

        for key, pattern in og_patterns.items():
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                meta[key] = match.group(1).strip()

        # Standard meta tags
        title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
        if title_match and "title" not in meta:
            meta["title"] = title_match.group(1).strip()

        return meta

    def parse_job_listing_page(self, html: str, source: JobSource) -> JobData:
        """
        Parse job details from HTML content.

        Args:
            html: The HTML content of the job page.
            source: The job source for source-specific parsing.

        Returns:
            Extracted JobData.

        Raises:
            ParseError: If parsing fails.
        """
        # Try JSON-LD first (most reliable)
        json_ld = self._extract_json_ld(html)

        if json_ld:
            return self._parse_json_ld_job(json_ld, source)

        # Fall back to source-specific parsing
        if source == JobSource.LEVER:
            return self._parse_lever_page(html)
        elif source == JobSource.GREENHOUSE:
            return self._parse_greenhouse_page(html)
        elif source == JobSource.LINKEDIN:
            return self._parse_linkedin_page(html)
        elif source == JobSource.INDEED:
            return self._parse_indeed_page(html)
        elif source == JobSource.GLASSDOOR:
            return self._parse_glassdoor_page(html)
        else:
            return self._parse_generic_page(html, source)

    def _parse_json_ld_job(self, data: dict, source: JobSource) -> JobData:
        """Parse job data from JSON-LD structured data."""
        title = data.get("title", "")

        # Extract company name
        company = ""
        hiring_org = data.get("hiringOrganization", {})
        if isinstance(hiring_org, dict):
            company = hiring_org.get("name", "")
        elif isinstance(hiring_org, str):
            company = hiring_org

        # Extract location
        location = ""
        job_location = data.get("jobLocation", {})
        if isinstance(job_location, list) and job_location:
            job_location = job_location[0]
        if isinstance(job_location, dict):
            address = job_location.get("address", {})
            if isinstance(address, dict):
                parts = [
                    address.get("addressLocality", ""),
                    address.get("addressRegion", ""),
                    address.get("addressCountry", ""),
                ]
                location = ", ".join(p for p in parts if p)

        # Extract salary
        salary_min = None
        salary_max = None
        salary_currency = "USD"
        base_salary = data.get("baseSalary", {})
        if isinstance(base_salary, dict):
            value = base_salary.get("value", {})
            if isinstance(value, dict):
                salary_min = value.get("minValue")
                salary_max = value.get("maxValue")
                if salary_min:
                    salary_min = int(salary_min)
                if salary_max:
                    salary_max = int(salary_max)
            salary_currency = base_salary.get("currency", "USD")

        # Extract description
        description = data.get("description", "")
        # Clean HTML from description
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

        # Extract job type
        employment_type = data.get("employmentType", "")
        if isinstance(employment_type, list):
            employment_type = employment_type[0] if employment_type else ""
        job_type = self._parse_job_type(employment_type)

        # Extract dates
        posted_date = None
        date_posted = data.get("datePosted")
        if date_posted:
            try:
                posted_date = datetime.fromisoformat(date_posted.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Check for remote
        remote = None
        job_location_type = data.get("jobLocationType", "")
        if "remote" in str(job_location_type).lower():
            remote = True

        return JobData(
            title=title,
            company=company,
            location=location,
            description=description,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            job_type=job_type,
            source=source,
            posted_date=posted_date,
            remote=remote,
            raw_data=data,
        )

    def _parse_lever_page(self, html: str) -> JobData:
        """Parse Lever job page."""
        meta = self._extract_meta_tags(html)

        # Title is usually in the posting-headline
        title_match = re.search(
            r'<h2[^>]*class=["\'][^"\']*posting-headline[^"\']*["\'][^>]*>.*?'
            r'<span[^>]*>([^<]+)</span>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        title = title_match.group(1).strip() if title_match else meta.get("title", "")

        # Company from site name or URL
        company = meta.get("site_name", "")
        if not company:
            company_match = re.search(r"jobs\.lever\.co/([^/]+)", html)
            if company_match:
                company = company_match.group(1).replace("-", " ").title()

        # Location
        location_match = re.search(
            r'<div[^>]*class=["\'][^"\']*location[^"\']*["\'][^>]*>([^<]+)</div>',
            html,
            re.IGNORECASE,
        )
        location = location_match.group(1).strip() if location_match else ""

        # Description
        desc_match = re.search(
            r'<div[^>]*class=["\'][^"\']*section-wrapper[^"\']*["\'][^>]*>(.*?)</div>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        description = ""
        if desc_match:
            description = re.sub(r"<[^>]+>", " ", desc_match.group(1))
            description = re.sub(r"\s+", " ", description).strip()

        return JobData(
            title=title,
            company=company,
            location=location,
            description=description[:5000] if description else None,
            source=JobSource.LEVER,
        )

    def _parse_greenhouse_page(self, html: str) -> JobData:
        """Parse Greenhouse job page."""
        meta = self._extract_meta_tags(html)

        # Title
        title_match = re.search(
            r'<h1[^>]*class=["\'][^"\']*app-title[^"\']*["\'][^>]*>([^<]+)</h1>',
            html,
            re.IGNORECASE,
        )
        title = title_match.group(1).strip() if title_match else meta.get("title", "")

        # Company
        company_match = re.search(
            r'<span[^>]*class=["\'][^"\']*company-name[^"\']*["\'][^>]*>([^<]+)</span>',
            html,
            re.IGNORECASE,
        )
        company = company_match.group(1).strip() if company_match else ""

        # Location
        location_match = re.search(
            r'<div[^>]*class=["\'][^"\']*location[^"\']*["\'][^>]*>([^<]+)</div>',
            html,
            re.IGNORECASE,
        )
        location = location_match.group(1).strip() if location_match else ""

        # Description
        desc_match = re.search(
            r'<div[^>]*id=["\']content["\'][^>]*>(.*?)</div>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        description = ""
        if desc_match:
            description = re.sub(r"<[^>]+>", " ", desc_match.group(1))
            description = re.sub(r"\s+", " ", description).strip()

        return JobData(
            title=title,
            company=company,
            location=location,
            description=description[:5000] if description else None,
            source=JobSource.GREENHOUSE,
        )

    def _parse_linkedin_page(self, html: str) -> JobData:
        """Parse LinkedIn job page."""
        meta = self._extract_meta_tags(html)

        # LinkedIn often blocks scraping, use meta tags primarily
        title = meta.get("title", "")
        if " | " in title:
            title = title.split(" | ")[0].strip()

        # Company is often in the title
        company = ""
        company_match = re.search(
            r'<a[^>]*class=["\'][^"\']*topcard[^"\']*company[^"\']*["\'][^>]*>([^<]+)</a>',
            html,
            re.IGNORECASE,
        )
        if company_match:
            company = company_match.group(1).strip()

        # Location
        location_match = re.search(
            r'<span[^>]*class=["\'][^"\']*topcard[^"\']*location[^"\']*["\'][^>]*>([^<]+)</span>',
            html,
            re.IGNORECASE,
        )
        location = location_match.group(1).strip() if location_match else ""

        description = meta.get("description", "")

        return JobData(
            title=title,
            company=company,
            location=location,
            description=description[:5000] if description else None,
            source=JobSource.LINKEDIN,
        )

    def _parse_indeed_page(self, html: str) -> JobData:
        """Parse Indeed job page."""
        meta = self._extract_meta_tags(html)

        # Title
        title_match = re.search(
            r'<h1[^>]*class=["\'][^"\']*jobsearch-JobInfoHeader-title[^"\']*["\'][^>]*>'
            r'<span[^>]*>([^<]+)</span>',
            html,
            re.IGNORECASE,
        )
        title = title_match.group(1).strip() if title_match else meta.get("title", "")

        # Company
        company_match = re.search(
            r'<div[^>]*data-company-name[^>]*>.*?<a[^>]*>([^<]+)</a>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        company = company_match.group(1).strip() if company_match else ""

        # Location
        location_match = re.search(
            r'<div[^>]*class=["\'][^"\']*jobsearch-JobInfoHeader-subtitle[^"\']*["\'][^>]*>'
            r'.*?<div[^>]*>([^<]+)</div>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        location = location_match.group(1).strip() if location_match else ""

        # Description
        desc_match = re.search(
            r'<div[^>]*id=["\']jobDescriptionText["\'][^>]*>(.*?)</div>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        description = ""
        if desc_match:
            description = re.sub(r"<[^>]+>", " ", desc_match.group(1))
            description = re.sub(r"\s+", " ", description).strip()

        return JobData(
            title=title,
            company=company,
            location=location,
            description=description[:5000] if description else None,
            source=JobSource.INDEED,
        )

    def _parse_glassdoor_page(self, html: str) -> JobData:
        """Parse Glassdoor job page."""
        meta = self._extract_meta_tags(html)

        title = meta.get("title", "")
        if " - " in title:
            parts = title.split(" - ")
            title = parts[0].strip()

        description = meta.get("description", "")

        return JobData(
            title=title,
            company="",
            location="",
            description=description[:5000] if description else None,
            source=JobSource.GLASSDOOR,
        )

    def _parse_generic_page(self, html: str, source: JobSource) -> JobData:
        """Parse generic job page using common patterns."""
        meta = self._extract_meta_tags(html)

        title = meta.get("title", "")
        description = meta.get("description", "")

        # Try to find company in common patterns
        company = ""
        for pattern in [
            r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']+)["\']',
            r'"company":\s*["\']([^"\']+)["\']',
            r'"employer":\s*["\']([^"\']+)["\']',
        ]:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                break

        # Try to find location
        location = ""
        for pattern in [
            r'"location":\s*["\']([^"\']+)["\']',
            r'"jobLocation":\s*["\']([^"\']+)["\']',
        ]:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                break

        return JobData(
            title=title,
            company=company,
            location=location,
            description=description[:5000] if description else None,
            source=source,
        )

    async def import_from_url(self, url: str, source: Optional[JobSource] = None) -> JobData:
        """
        Import job details from a URL.

        Args:
            url: The job posting URL.
            source: Optional source hint (auto-detected if not provided).

        Returns:
            Extracted JobData.

        Raises:
            JobImportError: If import fails.
        """
        detected_source = source or self._detect_source(url)

        if not self._check_rate_limit(detected_source):
            raise RateLimitError(
                f"Rate limit exceeded for {detected_source.value}. "
                "Please wait before making more requests."
            )

        html = await self._fetch_url(url)

        job_data = self.parse_job_listing_page(html, detected_source)
        job_data.job_url = url
        job_data.source = detected_source

        if not job_data.title:
            raise ParseError("Could not extract job title from page")

        return job_data

    async def import_from_github_repo(
        self,
        repo_url: str,
        filters: Optional[GitHubRepoFilter] = None,
        max_jobs: int = 100,
    ) -> list[JobData]:
        """
        Import jobs from a SimplifyJobs-style GitHub repository.

        Supports repos like:
        - SimplifyJobs/New-Grad-Positions
        - SimplifyJobs/Summer2025-Internships

        Args:
            repo_url: GitHub repository URL.
            filters: Optional filters for the import.
            max_jobs: Maximum number of jobs to return.

        Returns:
            List of extracted JobData objects.

        Raises:
            JobImportError: If import fails.
        """
        # Convert repo URL to raw README URL
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")

        if len(path_parts) < 2:
            raise JobImportError(
                "Invalid GitHub repo URL",
                "INVALID_URL",
                recoverable=False,
            )

        owner = path_parts[0]
        repo = path_parts[1]

        # Try different README locations
        readme_urls = [
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/dev/README.md",
        ]

        content = None
        for readme_url in readme_urls:
            try:
                content = await self._fetch_url(readme_url)
                break
            except JobImportError:
                continue

        if not content:
            raise JobImportError(
                "Could not find README in repository",
                "README_NOT_FOUND",
                recoverable=False,
            )

        return self._parse_simplify_markdown(content, filters, max_jobs)

    def _parse_simplify_markdown(
        self,
        content: str,
        filters: Optional[GitHubRepoFilter] = None,
        max_jobs: int = 100,
    ) -> list[JobData]:
        """
        Parse SimplifyJobs markdown table format.

        Expected format:
        | Company | Role | Location | Application/Link | Date Posted |
        | --- | --- | --- | --- | --- |
        | Company Name | Position | City, State | [Apply](url) | Jan 01 |
        """
        jobs: list[JobData] = []

        # Find markdown tables
        lines = content.split("\n")
        in_table = False
        headers: list[str] = []
        header_map: dict[str, int] = {}

        for line in lines:
            line = line.strip()

            if not line.startswith("|"):
                in_table = False
                headers = []
                continue

            # Parse table row
            cells = [c.strip() for c in line.split("|")[1:-1]]

            if not cells:
                continue

            # Check if this is a header row
            if not in_table:
                # Detect header row
                is_header = any(
                    h.lower() in ["company", "role", "location", "link", "date", "application"]
                    for h in cells
                )

                if is_header:
                    headers = [h.lower() for h in cells]
                    header_map = {h: i for i, h in enumerate(headers)}
                    in_table = True
                continue

            # Skip separator row
            if all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
                continue

            if len(jobs) >= max_jobs:
                break

            # Parse data row
            try:
                job = self._parse_simplify_row(cells, header_map, filters)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse row: {e}")
                continue

        return jobs

    def _parse_simplify_row(
        self,
        cells: list[str],
        header_map: dict[str, int],
        filters: Optional[GitHubRepoFilter] = None,
    ) -> Optional[JobData]:
        """Parse a single row from SimplifyJobs markdown table."""

        def get_cell(key: str) -> str:
            """Get cell value by header key."""
            idx = header_map.get(key, -1)
            if idx >= 0 and idx < len(cells):
                return cells[idx].strip()
            return ""

        # Extract company
        company = get_cell("company")
        if not company:
            return None

        # Clean up company name (remove emojis, badges)
        company = re.sub(r"[^\w\s&,.-]", "", company).strip()

        # Check company filters
        if filters:
            if filters.exclude_companies:
                if any(ex.lower() in company.lower() for ex in filters.exclude_companies):
                    return None
            if filters.companies:
                if not any(c.lower() in company.lower() for c in filters.companies):
                    return None

        # Extract role/title
        title = get_cell("role") or get_cell("title") or get_cell("position")
        if not title:
            return None

        # Extract location
        location = get_cell("location") or get_cell("locations")

        # Check location filters
        if filters and filters.locations and location:
            location_lower = location.lower()
            if not any(loc.lower() in location_lower for loc in filters.locations):
                return None

        # Extract application URL
        application_url = None
        link_cell = get_cell("application") or get_cell("link") or get_cell("apply")
        if link_cell:
            url_match = re.search(r"\[.*?\]\((https?://[^\)]+)\)", link_cell)
            if url_match:
                application_url = url_match.group(1)

        # Check if job is closed (common markers)
        if link_cell:
            link_lower = link_cell.lower()
            if "closed" in link_lower or "n/a" in link_lower or "x]" in link_cell:
                return None

        # Extract date
        date_str = get_cell("date") or get_cell("date posted")
        posted_date = None
        if date_str:
            try:
                # Handle formats like "Jan 01" or "2024-01-01"
                date_str = re.sub(r"[^\w\s-]", "", date_str).strip()
                for fmt in ["%b %d", "%B %d", "%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        parsed = datetime.strptime(date_str, fmt)
                        # Add current year if not present
                        if parsed.year == 1900:
                            parsed = parsed.replace(year=datetime.now().year)
                        posted_date = parsed
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Check date filter
        if filters and filters.min_posted_date and posted_date:
            if posted_date < filters.min_posted_date:
                return None

        # Check sponsorship
        sponsorship = None
        notes = get_cell("notes") or get_cell("sponsorship")
        if notes:
            notes_lower = notes.lower()
            if "sponsor" in notes_lower:
                sponsorship = "yes" in notes_lower or "available" in notes_lower

        if filters and filters.sponsorship is not None:
            if sponsorship is not None and sponsorship != filters.sponsorship:
                return None

        # Determine job type from title/location
        job_type = self._parse_job_type(f"{title} {location}")
        if "intern" in title.lower():
            job_type = JobType.INTERNSHIP

        # Check for remote
        remote = None
        if location:
            if "remote" in location.lower():
                remote = True
            elif "on-site" in location.lower() or "onsite" in location.lower():
                remote = False

        return JobData(
            title=title,
            company=company,
            location=location,
            application_url=application_url,
            job_url=application_url,
            source=JobSource.GITHUB_SIMPLIFY,
            posted_date=posted_date,
            job_type=job_type,
            remote=remote,
        )

    async def bulk_import(
        self,
        urls: list[str],
        save_callback=None,
    ) -> BulkImportResponse:
        """
        Import multiple jobs from URLs.

        Args:
            urls: List of job URLs to import.
            save_callback: Optional async callback to save each job.

        Returns:
            BulkImportResponse with results for each URL.
        """
        results: list[ImportResult] = []
        errors: list[str] = []
        warnings: list[str] = []

        # Process with controlled concurrency to respect rate limits
        semaphore = asyncio.Semaphore(5)

        async def process_url(url: str) -> ImportResult:
            async with semaphore:
                try:
                    job_data = await self.import_from_url(url)
                    job_id = None

                    if save_callback:
                        try:
                            job_id = await save_callback(job_data)
                        except Exception as e:
                            logger.error(f"Failed to save job: {e}")
                            warnings.append(f"Imported but failed to save: {url}")

                    return ImportResult(
                        url=url,
                        success=True,
                        job_data=job_data,
                        job_id=job_id,
                    )

                except JobImportError as e:
                    return ImportResult(
                        url=url,
                        success=False,
                        error=ImportError(
                            url=url,
                            error_code=e.error_code,
                            message=e.message,
                            recoverable=e.recoverable,
                        ),
                    )
                except Exception as e:
                    logger.error(f"Unexpected error importing {url}: {e}")
                    return ImportResult(
                        url=url,
                        success=False,
                        error=ImportError(
                            url=url,
                            error_code="UNKNOWN_ERROR",
                            message=str(e),
                            recoverable=False,
                        ),
                    )

        # Process all URLs concurrently
        tasks = [process_url(url) for url in urls]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count

        return BulkImportResponse(
            success=success_count > 0,
            results=results,
            success_count=success_count,
            error_count=error_count,
            total_requested=len(urls),
            errors=errors,
            warnings=warnings,
        )

    async def preview_job(self, url: str) -> JobPreviewResponse:
        """
        Preview job data from URL without saving.

        Args:
            url: The job URL to preview.

        Returns:
            JobPreviewResponse with extracted data.
        """
        try:
            source = self._detect_source(url)
            job_data = await self.import_from_url(url, source)

            # Calculate confidence based on data completeness
            confidence = 0.0
            if job_data.title:
                confidence += 0.3
            if job_data.company:
                confidence += 0.3
            if job_data.description:
                confidence += 0.2
            if job_data.location:
                confidence += 0.1
            if job_data.salary_min or job_data.salary_max:
                confidence += 0.1

            return JobPreviewResponse(
                success=True,
                job_data=job_data,
                source_detected=source,
                confidence=min(confidence, 1.0),
            )

        except JobImportError as e:
            return JobPreviewResponse(
                success=False,
                source_detected=self._detect_source(url),
                errors=[e.message],
            )
        except Exception as e:
            logger.error(f"Preview failed for {url}: {e}")
            return JobPreviewResponse(
                success=False,
                errors=[str(e)],
            )


# Singleton instance
_job_importer: Optional[JobImporter] = None


def get_job_importer() -> JobImporter:
    """Get or create the JobImporter singleton."""
    global _job_importer
    if _job_importer is None:
        _job_importer = JobImporter()
    return _job_importer


def reset_job_importer() -> None:
    """Reset the JobImporter singleton (useful for testing)."""
    global _job_importer
    _job_importer = None
