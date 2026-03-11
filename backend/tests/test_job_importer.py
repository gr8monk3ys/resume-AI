"""
Tests for job importer URL hardening.
"""

import pytest

from app.schemas.job_import import JobSource
from app.services.job_importer import JobImporter, JobImportError


class TestJobImporterUrlHardening:
    """Tests for SSRF protections in job imports."""

    def test_known_source_urls_are_canonicalized(self, monkeypatch: pytest.MonkeyPatch):
        """Known job-board domains should normalize to approved hosts."""
        monkeypatch.delenv("JOB_IMPORT_ALLOWED_HOSTS", raising=False)
        importer = JobImporter()

        safe_url = importer._build_safe_fetch_url(
            "https://linkedin.com/jobs/view/12345?trk=test#fragment",
            JobSource.LINKEDIN,
        )

        assert safe_url == "https://www.linkedin.com/jobs/view/12345?trk=test"

    def test_company_sites_require_allowlisted_hosts(self, monkeypatch: pytest.MonkeyPatch):
        """Generic company-site imports should be blocked by default."""
        monkeypatch.delenv("JOB_IMPORT_ALLOWED_HOSTS", raising=False)
        importer = JobImporter()

        with pytest.raises(JobImportError, match="allowlisted hostname"):
            importer._build_safe_fetch_url(
                "https://careers.example.com/jobs/backend-engineer",
                JobSource.COMPANY_SITE,
            )

    def test_allowlisted_workday_host_is_permitted(self, monkeypatch: pytest.MonkeyPatch):
        """Workday imports should work when the hostname is explicitly allowlisted."""
        monkeypatch.setenv("JOB_IMPORT_ALLOWED_HOSTS", "acme.wd5.myworkdayjobs.com")
        importer = JobImporter()

        safe_url = importer._build_safe_fetch_url(
            "https://acme.wd5.myworkdayjobs.com/en-US/careers/job/123?location=Remote#apply",
            JobSource.WORKDAY,
        )

        assert (
            safe_url == "https://acme.wd5.myworkdayjobs.com/en-US/careers/job/123?location=Remote"
        )

    def test_embedded_credentials_are_rejected(self, monkeypatch: pytest.MonkeyPatch):
        """Credential-bearing URLs should never be fetched."""
        monkeypatch.delenv("JOB_IMPORT_ALLOWED_HOSTS", raising=False)
        importer = JobImporter()

        with pytest.raises(JobImportError, match="embedded credentials"):
            importer._build_safe_fetch_url(
                "https://user:secret@www.linkedin.com/jobs/view/12345",
                JobSource.LINKEDIN,
            )
