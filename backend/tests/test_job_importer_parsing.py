"""
Tests for the pure parsing/detection logic in app.services.job_importer.JobImporter.

These exercise real HTML/markdown parsing behavior directly (no network calls),
covering source detection, rate limiting, salary/job-type extraction, JSON-LD and
per-ATS HTML parsing, and the SimplifyJobs markdown table importer.
"""

from datetime import datetime, timedelta

import pytest

from app.schemas.job_import import GitHubRepoFilter, JobSource, JobType
from app.services.job_importer import JobImporter


@pytest.fixture
def importer(monkeypatch: pytest.MonkeyPatch) -> JobImporter:
    monkeypatch.delenv("JOB_IMPORT_ALLOWED_HOSTS", raising=False)
    return JobImporter()


class TestDetectSource:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.linkedin.com/jobs/view/12345", JobSource.LINKEDIN),
            ("https://www.indeed.com/viewjob?jk=abc", JobSource.INDEED),
            ("https://www.glassdoor.com/job-listing/engineer-JV_IC1.htm", JobSource.GLASSDOOR),
            ("https://jobs.lever.co/acme/1234", JobSource.LEVER),
            ("https://boards.greenhouse.io/acme/jobs/1234", JobSource.GREENHOUSE),
            ("https://acme.wd5.myworkdayjobs.com/en-US/careers/job/123", JobSource.WORKDAY),
            ("https://careers.example.com/jobs/backend-engineer", JobSource.COMPANY_SITE),
        ],
    )
    def test_detects_known_and_unknown_sources(self, importer, url, expected):
        assert importer._detect_source(url) == expected

    def test_detection_is_case_insensitive(self, importer):
        assert importer._detect_source("https://WWW.LINKEDIN.COM/JOBS/view/1") == JobSource.LINKEDIN


class TestCheckRateLimit:
    def test_allows_requests_under_the_limit(self, importer):
        for _ in range(importer.RATE_LIMITS[JobSource.LEVER]):
            assert importer._check_rate_limit(JobSource.LEVER) is True

    def test_blocks_requests_once_limit_is_hit(self, importer):
        limit = importer.RATE_LIMITS[JobSource.LINKEDIN]
        for _ in range(limit):
            assert importer._check_rate_limit(JobSource.LINKEDIN) is True
        assert importer._check_rate_limit(JobSource.LINKEDIN) is False

    def test_old_timestamps_roll_off_the_window(self, importer):
        limit = importer.RATE_LIMITS[JobSource.GREENHOUSE]
        stale = datetime.utcnow() - timedelta(seconds=61)
        importer._request_timestamps[JobSource.GREENHOUSE] = [stale] * limit

        assert importer._check_rate_limit(JobSource.GREENHOUSE) is True

    def test_unknown_source_uses_default_limit(self, importer):
        assert importer._check_rate_limit(JobSource.UNKNOWN) is True


class TestGetAuthorizedHost:
    def test_known_source_host_is_canonicalized(self, importer):
        assert importer._get_authorized_host("linkedin.com", JobSource.LINKEDIN) == "www.linkedin.com"

    def test_unmapped_host_for_known_source_returns_none(self, importer):
        assert importer._get_authorized_host("evil.com", JobSource.LINKEDIN) is None

    def test_company_site_requires_allowlist(self, importer):
        assert importer._get_authorized_host("careers.example.com", JobSource.COMPANY_SITE) is None

    def test_company_site_allowlisted_host_is_permitted(self, monkeypatch):
        monkeypatch.setenv("JOB_IMPORT_ALLOWED_HOSTS", "careers.example.com, other.example.com")
        importer = JobImporter()
        assert (
            importer._get_authorized_host("careers.example.com", JobSource.COMPANY_SITE)
            == "careers.example.com"
        )

    def test_hostname_is_normalized_before_lookup(self, importer):
        assert importer._get_authorized_host("LinkedIn.com.", JobSource.LINKEDIN) == "www.linkedin.com"


class TestParseSalary:
    def test_parses_range_with_commas(self, importer):
        assert importer._parse_salary("$80,000 - $120,000/year") == (80000, 120000, "USD")

    def test_parses_single_value(self, importer):
        assert importer._parse_salary("$95,000") == (95000, 95000, "USD")

    def test_parses_k_notation_range(self, importer):
        assert importer._parse_salary("80k-120k") == (80000, 120000, "USD")

    def test_converts_small_numbers_as_hourly_to_annual(self, importer):
        min_sal, max_sal, currency = importer._parse_salary("$25 - $40 per hour")
        assert min_sal == int(25 * 2080)
        assert max_sal == int(40 * 2080)
        assert currency == "USD"

    def test_detects_gbp_currency(self, importer):
        _, _, currency = importer._parse_salary("£50,000 - £70,000")
        assert currency == "GBP"

    def test_detects_eur_currency(self, importer):
        _, _, currency = importer._parse_salary("EUR 50000")
        assert currency == "EUR"

    def test_detects_cad_currency(self, importer):
        _, _, currency = importer._parse_salary("CAD 90,000")
        assert currency == "CAD"

    def test_empty_text_returns_none_none_usd(self, importer):
        assert importer._parse_salary("") == (None, None, "USD")

    def test_no_numbers_returns_none_none(self, importer):
        assert importer._parse_salary("Competitive salary") == (None, None, "USD")


class TestParseJobType:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Summer Internship", JobType.INTERNSHIP),
            ("6-month Contract role", JobType.CONTRACT),
            ("Part-time position", JobType.PART_TIME),
            ("Temporary temp role", JobType.TEMPORARY),
            ("100% Remote", JobType.REMOTE),
            ("Hybrid schedule", JobType.HYBRID),
            ("Full-time employee", JobType.FULL_TIME),
            ("Some other text", JobType.UNKNOWN),
            ("", JobType.UNKNOWN),
        ],
    )
    def test_classifies_job_type(self, importer, text, expected):
        assert importer._parse_job_type(text) == expected

    def test_first_matching_category_wins_for_intern(self, importer):
        # "intern" should win over "full-time" since it's checked first.
        assert importer._parse_job_type("Full-time Internship") == JobType.INTERNSHIP


class TestExtractJsonLd:
    def test_extracts_job_posting_object(self, importer):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "JobPosting", "title": "Backend Engineer"}
        </script>
        </head></html>
        """
        data = importer._extract_json_ld(html)
        assert data == {"@type": "JobPosting", "title": "Backend Engineer"}

    def test_extracts_job_posting_from_array(self, importer):
        html = """
        <script type="application/ld+json">
        [{"@type": "Organization", "name": "Acme"}, {"@type": "JobPosting", "title": "SRE"}]
        </script>
        """
        data = importer._extract_json_ld(html)
        assert data == {"@type": "JobPosting", "title": "SRE"}

    def test_ignores_non_job_posting_json_ld(self, importer):
        html = '<script type="application/ld+json">{"@type": "Organization"}</script>'
        assert importer._extract_json_ld(html) is None

    def test_skips_malformed_json(self, importer):
        html = '<script type="application/ld+json">{not valid json</script>'
        assert importer._extract_json_ld(html) is None

    def test_returns_none_when_no_script_tag(self, importer):
        assert importer._extract_json_ld("<html><body>no data here</body></html>") is None


class TestExtractMetaTags:
    def test_extracts_open_graph_tags(self, importer):
        html = (
            '<meta property="og:title" content="Backend Engineer">'
            '<meta property="og:description" content="Build great things">'
            '<meta property="og:site_name" content="Acme Corp">'
        )
        meta = importer._extract_meta_tags(html)
        assert meta == {
            "title": "Backend Engineer",
            "description": "Build great things",
            "site_name": "Acme Corp",
        }

    def test_falls_back_to_title_tag(self, importer):
        html = "<html><head><title>Fallback Title</title></head></html>"
        assert importer._extract_meta_tags(html)["title"] == "Fallback Title"

    def test_og_title_takes_precedence_over_title_tag(self, importer):
        html = (
            '<title>Page Title</title>'
            '<meta property="og:title" content="OG Title">'
        )
        assert importer._extract_meta_tags(html)["title"] == "OG Title"

    def test_returns_empty_dict_when_nothing_found(self, importer):
        assert importer._extract_meta_tags("<html></html>") == {}


class TestParseJsonLdJob:
    def test_parses_full_job_posting(self, importer):
        data = {
            "title": "Software Engineer",
            "hiringOrganization": {"name": "Acme Corp"},
            "jobLocation": {
                "address": {
                    "addressLocality": "San Francisco",
                    "addressRegion": "CA",
                    "addressCountry": "US",
                }
            },
            "baseSalary": {"currency": "USD", "value": {"minValue": 100000, "maxValue": 150000}},
            "description": "<p>Build <b>great</b> things</p>",
            "employmentType": "FULL_TIME",
            "datePosted": "2026-01-15T00:00:00Z",
            "jobLocationType": "TELECOMMUTE_REMOTE",
        }
        job = importer._parse_json_ld_job(data, JobSource.LEVER)

        assert job.title == "Software Engineer"
        assert job.company == "Acme Corp"
        assert job.location == "San Francisco, CA, US"
        assert job.salary_min == 100000
        assert job.salary_max == 150000
        assert job.salary_currency == "USD"
        assert job.description == "Build great things"
        assert job.remote is True
        assert job.posted_date == datetime(2026, 1, 15, tzinfo=job.posted_date.tzinfo)
        assert job.raw_data == data

    def test_hiring_org_as_plain_string(self, importer):
        job = importer._parse_json_ld_job(
            {"title": "T", "hiringOrganization": "Acme Corp"}, JobSource.UNKNOWN
        )
        assert job.company == "Acme Corp"

    def test_job_location_as_list_uses_first_entry(self, importer):
        data = {
            "title": "T",
            "jobLocation": [{"address": {"addressLocality": "NYC"}}],
        }
        job = importer._parse_json_ld_job(data, JobSource.UNKNOWN)
        assert job.location == "NYC"

    def test_employment_type_as_list_uses_first_entry(self, importer):
        job = importer._parse_json_ld_job(
            {"title": "T", "employmentType": ["INTERN"]}, JobSource.UNKNOWN
        )
        assert job.job_type == JobType.INTERNSHIP

    def test_invalid_date_posted_is_ignored(self, importer):
        job = importer._parse_json_ld_job(
            {"title": "T", "datePosted": "not-a-date"}, JobSource.UNKNOWN
        )
        assert job.posted_date is None

    def test_missing_optional_fields_default_sensibly(self, importer):
        job = importer._parse_json_ld_job({"title": "T"}, JobSource.UNKNOWN)
        assert job.company == ""
        assert job.location == ""
        assert job.salary_min is None
        assert job.remote is None


class TestParseLeverPage:
    def test_parses_title_company_and_location(self, importer):
        html = """
        <meta property="og:site_name" content="Acme Corp">
        <h2 class="posting-headline"><span>Backend Engineer</span></h2>
        <div class="location">Remote - US</div>
        <div class="section-wrapper"><p>Join our <b>team</b>!</p></div>
        """
        job = importer._parse_lever_page(html)
        assert job.title == "Backend Engineer"
        assert job.company == "Acme Corp"
        assert job.location == "Remote - US"
        assert job.description == "Join our team !"
        assert job.source == JobSource.LEVER

    def test_falls_back_to_url_derived_company_name(self, importer):
        html = '<a href="https://jobs.lever.co/acme-labs/1234">Apply</a>'
        job = importer._parse_lever_page(html)
        assert job.company == "Acme Labs"

    def test_missing_fields_default_to_empty(self, importer):
        job = importer._parse_lever_page("<html></html>")
        assert job.title == ""
        assert job.company == ""
        assert job.location == ""
        assert job.description is None


class TestParseGreenhousePage:
    def test_parses_all_fields(self, importer):
        html = """
        <h1 class="app-title">Data Engineer</h1>
        <span class="company-name">Acme Corp</span>
        <div class="location">Austin, TX</div>
        <div id="content"><p>We are <em>hiring</em>.</p></div>
        """
        job = importer._parse_greenhouse_page(html)
        assert job.title == "Data Engineer"
        assert job.company == "Acme Corp"
        assert job.location == "Austin, TX"
        assert job.description == "We are hiring ."
        assert job.source == JobSource.GREENHOUSE

    def test_missing_fields_default_to_empty(self, importer):
        job = importer._parse_greenhouse_page("<html></html>")
        assert job.title == ""
        assert job.company == ""


class TestParseLinkedinPage:
    def test_splits_title_on_pipe(self, importer):
        html = '<title>Backend Engineer | Acme Corp | LinkedIn</title>'
        job = importer._parse_linkedin_page(html)
        assert job.title == "Backend Engineer"

    def test_parses_company_and_location(self, importer):
        html = (
            '<a class="topcard__company-link">Acme Corp</a>'
            '<span class="topcard__flavor--bullet location">San Francisco, CA</span>'
        )
        job = importer._parse_linkedin_page(html)
        assert job.company == "Acme Corp"
        assert job.location == "San Francisco, CA"

    def test_uses_meta_description(self, importer):
        html = '<meta property="og:description" content="Great opportunity">'
        job = importer._parse_linkedin_page(html)
        assert job.description == "Great opportunity"


class TestParseIndeedPage:
    def test_parses_all_fields(self, importer):
        html = (
            '<h1 class="jobsearch-JobInfoHeader-title"><span>QA Engineer</span></h1>'
            '<div data-company-name="true">blah<a>Acme Corp</a></div>'
            '<div class="jobsearch-JobInfoHeader-subtitle">x<div>Denver, CO</div></div>'
            '<div id="jobDescriptionText"><p>Test <i>everything</i>.</p></div>'
        )
        job = importer._parse_indeed_page(html)
        assert job.title == "QA Engineer"
        assert job.company == "Acme Corp"
        assert job.location == "Denver, CO"
        assert job.description == "Test everything ."

    def test_missing_fields_default_to_empty(self, importer):
        job = importer._parse_indeed_page("<html></html>")
        assert job.title == ""
        assert job.description is None


class TestParseGlassdoorPage:
    def test_splits_title_on_dash(self, importer):
        html = '<title>Backend Engineer - Acme Corp - Glassdoor</title>'
        job = importer._parse_glassdoor_page(html)
        assert job.title == "Backend Engineer"
        assert job.company == ""
        assert job.source == JobSource.GLASSDOOR

    def test_uses_meta_description(self, importer):
        html = '<meta property="og:description" content="Great role">'
        job = importer._parse_glassdoor_page(html)
        assert job.description == "Great role"


class TestParseGenericPage:
    def test_parses_from_json_patterns(self, importer):
        html = (
            '<title>Fallback Title</title>'
            '<meta property="og:description" content="A great job">'
            '"company": "Acme Corp"'
            '"location": "Remote"'
        )
        job = importer._parse_generic_page(html, JobSource.COMPANY_SITE)
        assert job.title == "Fallback Title"
        assert job.description == "A great job"
        assert job.company == "Acme Corp"
        assert job.location == "Remote"
        assert job.source == JobSource.COMPANY_SITE

    def test_falls_back_to_author_meta_for_company(self, importer):
        html = '<meta name="author" content="Acme Corp">'
        job = importer._parse_generic_page(html, JobSource.COMPANY_SITE)
        assert job.company == "Acme Corp"

    def test_description_is_truncated_to_5000_chars(self, importer):
        html = f'<meta property="og:description" content="{"a" * 6000}">'
        job = importer._parse_generic_page(html, JobSource.COMPANY_SITE)
        assert len(job.description) == 5000


class TestParseJobListingPage:
    def test_prefers_json_ld_when_present(self, importer):
        html = (
            '<script type="application/ld+json">'
            '{"@type": "JobPosting", "title": "From JSON-LD"}'
            "</script>"
            '<h1 class="app-title">From Greenhouse HTML</h1>'
        )
        job = importer.parse_job_listing_page(html, JobSource.GREENHOUSE)
        assert job.title == "From JSON-LD"

    def test_falls_back_to_source_specific_parser(self, importer):
        html = '<h1 class="app-title">Greenhouse Title</h1>'
        job = importer.parse_job_listing_page(html, JobSource.GREENHOUSE)
        assert job.title == "Greenhouse Title"
        assert job.source == JobSource.GREENHOUSE

    def test_unknown_source_uses_generic_parser(self, importer):
        html = '<title>Some Job</title>'
        job = importer.parse_job_listing_page(html, JobSource.COMPANY_SITE)
        assert job.title == "Some Job"
        assert job.source == JobSource.COMPANY_SITE


SIMPLIFY_TABLE = """
Some intro text.

| Company | Role | Location | Application | Date Posted |
| --- | --- | --- | --- | --- |
| Acme Corp | Software Engineer Intern | Remote | [Apply](https://apply.example.com/1) | Jan 05 |
| \U0001F984 Beta Inc | Backend Engineer | On-site, NYC | [Apply](https://apply.example.com/2) | Jan 10 |
| Closed Co | Data Scientist | Remote | Closed | Jan 01 |
"""


class TestParseSimplifyMarkdown:
    def test_parses_all_open_rows(self, importer):
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE)
        # The "Closed Co" row is filtered out because its link cell says "Closed".
        assert [j.company for j in jobs] == ["Acme Corp", "Beta Inc"]

    def test_internship_detected_from_title(self, importer):
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE)
        assert jobs[0].job_type == JobType.INTERNSHIP

    def test_remote_and_onsite_detected_from_location(self, importer):
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE)
        assert jobs[0].remote is True
        assert jobs[1].remote is False

    def test_application_url_extracted_from_markdown_link(self, importer):
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE)
        assert jobs[0].application_url == "https://apply.example.com/1"

    def test_date_posted_parsed_with_current_year(self, importer):
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE)
        assert jobs[0].posted_date.month == 1
        assert jobs[0].posted_date.day == 5
        assert jobs[0].posted_date.year == datetime.now().year

    def test_max_jobs_caps_results(self, importer):
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE, max_jobs=1)
        assert len(jobs) == 1

    def test_exclude_companies_filter(self, importer):
        filters = GitHubRepoFilter(exclude_companies=["Beta"])
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE, filters=filters)
        assert [j.company for j in jobs] == ["Acme Corp"]

    def test_companies_allowlist_filter(self, importer):
        filters = GitHubRepoFilter(companies=["acme"])
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE, filters=filters)
        assert [j.company for j in jobs] == ["Acme Corp"]

    def test_location_filter(self, importer):
        filters = GitHubRepoFilter(locations=["NYC"])
        jobs = importer._parse_simplify_markdown(SIMPLIFY_TABLE, filters=filters)
        assert [j.company for j in jobs] == ["Beta Inc"]

    def test_no_table_returns_empty_list(self, importer):
        assert importer._parse_simplify_markdown("Just some prose, no table here.") == []

    def test_rows_missing_company_are_skipped(self, importer):
        table = (
            "| Company | Role |\n"
            "| --- | --- |\n"
            "|  | Engineer |\n"
        )
        assert importer._parse_simplify_markdown(table) == []

    def test_rows_missing_title_are_skipped(self, importer):
        table = (
            "| Company | Role |\n"
            "| --- | --- |\n"
            "| Acme |  |\n"
        )
        assert importer._parse_simplify_markdown(table) == []


class TestParseSimplifyRow:
    def test_min_posted_date_filter_excludes_older_jobs(self, importer):
        header_map = {"company": 0, "role": 1, "location": 2, "date": 3}
        cells = ["Acme", "Engineer", "Remote", "Jan 01"]
        filters = GitHubRepoFilter(min_posted_date=datetime(datetime.now().year, 6, 1))

        assert importer._parse_simplify_row(cells, header_map, filters) is None

    def test_sponsorship_yes_is_detected(self, importer):
        header_map = {"company": 0, "role": 1, "notes": 2}
        cells = ["Acme", "Engineer", "Sponsorship available"]
        job = importer._parse_simplify_row(cells, header_map)
        assert job is not None

    def test_sponsorship_filter_excludes_mismatches(self, importer):
        header_map = {"company": 0, "role": 1, "notes": 2}
        # Deliberately avoids the substring "available" (a negated "not available"
        # would still contain it and be misread as sponsorship=True by the parser).
        cells = ["Acme", "Engineer", "No sponsorship offered"]
        filters = GitHubRepoFilter(sponsorship=True)

        assert importer._parse_simplify_row(cells, header_map, filters) is None
