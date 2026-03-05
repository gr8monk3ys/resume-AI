"""
Tests for the analytics router.

Tests cover:
- Overview statistics
- Timeline aggregation
- Conversion funnel
- Source performance
- Company statistics
- Response time analysis
- Resume performance
- Data export
"""

from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.resume import Resume


class TestOverviewStats:
    """Tests for GET /api/analytics/overview"""

    @pytest.mark.asyncio
    async def test_overview_empty(self, client: AsyncClient, auth_headers: dict):
        """Test overview stats with no job applications."""
        response = await client.get("/api/analytics/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_applications"] == 0
        assert data["status_breakdown"] == {}
        assert data["response_rate"] == 0.0
        assert data["interview_rate"] == 0.0
        assert data["offer_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_overview_with_data(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test overview stats with job applications."""
        # Create jobs with various statuses
        statuses = ["Bookmarked", "Applied", "Phone Screen", "Interview", "Offer", "Rejected"]
        for i, status in enumerate(statuses):
            job = JobApplication(
                profile_id=test_profile.id,
                company=f"Company {i}",
                position="Developer",
                status=status,
                created_at=datetime.utcnow(),
            )
            db.add(job)
        db.commit()

        response = await client.get("/api/analytics/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_applications"] == 6
        assert len(data["status_breakdown"]) > 0
        assert "Applied" in data["status_breakdown"]

    @pytest.mark.asyncio
    async def test_overview_unauthorized(self, client: AsyncClient):
        """Test overview without authentication."""
        response = await client.get("/api/analytics/overview")
        assert response.status_code == 401


class TestTimeline:
    """Tests for GET /api/analytics/timeline"""

    @pytest.mark.asyncio
    async def test_timeline_weekly(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test weekly timeline aggregation."""
        # Create jobs spread across weeks
        for i in range(10):
            job = JobApplication(
                profile_id=test_profile.id,
                company=f"Company {i}",
                position="Developer",
                status="Applied",
                created_at=datetime.utcnow() - timedelta(days=i * 3),
            )
            db.add(job)
        db.commit()

        response = await client.get(
            "/api/analytics/timeline", headers=auth_headers, params={"period": "weekly"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "weekly"
        assert data["total"] == 10
        assert len(data["data"]) > 0

    @pytest.mark.asyncio
    async def test_timeline_daily(self, client: AsyncClient, auth_headers: dict):
        """Test daily timeline aggregation."""
        response = await client.get(
            "/api/analytics/timeline", headers=auth_headers, params={"period": "daily"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "daily"

    @pytest.mark.asyncio
    async def test_timeline_monthly(self, client: AsyncClient, auth_headers: dict):
        """Test monthly timeline aggregation."""
        response = await client.get(
            "/api/analytics/timeline", headers=auth_headers, params={"period": "monthly"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "monthly"

    @pytest.mark.asyncio
    async def test_timeline_date_filter(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test timeline with date filter."""
        # Create a job
        job = JobApplication(
            profile_id=test_profile.id,
            company="Company",
            position="Developer",
            status="Applied",
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()

        today = date.today()
        response = await client.get(
            "/api/analytics/timeline",
            headers=auth_headers,
            params={"start_date": str(today), "end_date": str(today)},
        )
        assert response.status_code == 200


class TestConversionFunnel:
    """Tests for GET /api/analytics/conversion-funnel"""

    @pytest.mark.asyncio
    async def test_funnel_empty(self, client: AsyncClient, auth_headers: dict):
        """Test conversion funnel with no data."""
        response = await client.get("/api/analytics/conversion-funnel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["overall_conversion_rate"] == 0.0
        assert len(data["stages"]) == 5  # 5 stages in funnel

    @pytest.mark.asyncio
    async def test_funnel_with_data(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test conversion funnel with applications at various stages."""
        # Create jobs progressing through funnel
        for status in ["Bookmarked", "Applied", "Interview", "Offer"]:
            job = JobApplication(
                profile_id=test_profile.id,
                company=f"Company {status}",
                position="Developer",
                status=status,
                created_at=datetime.utcnow(),
            )
            db.add(job)
        db.commit()

        response = await client.get("/api/analytics/conversion-funnel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["overall_conversion_rate"] > 0  # We have 1 offer out of 4


class TestSourcePerformance:
    """Tests for GET /api/analytics/source-performance"""

    @pytest.mark.asyncio
    async def test_source_performance_empty(self, client: AsyncClient, auth_headers: dict):
        """Test source performance with no data."""
        response = await client.get("/api/analytics/source-performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == []
        assert data["best_performing_source"] is None

    @pytest.mark.asyncio
    async def test_source_performance_with_data(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test source performance with applications from various sources."""
        sources = ["LinkedIn", "Indeed", "Referral", "Company Site"]
        for i, source in enumerate(sources):
            job = JobApplication(
                profile_id=test_profile.id,
                company=f"Company {i}",
                position="Developer",
                status="Applied",
                application_source=source,
                created_at=datetime.utcnow(),
            )
            db.add(job)
        db.commit()

        response = await client.get("/api/analytics/source-performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 4


class TestCompanyStats:
    """Tests for GET /api/analytics/company-stats"""

    @pytest.mark.asyncio
    async def test_company_stats_empty(self, client: AsyncClient, auth_headers: dict):
        """Test company stats with no data."""
        response = await client.get("/api/analytics/company-stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["companies"] == []
        assert data["total_companies"] == 0

    @pytest.mark.asyncio
    async def test_company_stats_with_data(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test company stats with applications to multiple companies."""
        # Create multiple applications to same company
        for i in range(3):
            job = JobApplication(
                profile_id=test_profile.id,
                company="Google",
                position=f"Developer L{i+3}",
                status="Applied" if i < 2 else "Interview",
                created_at=datetime.utcnow(),
            )
            db.add(job)
        db.commit()

        response = await client.get("/api/analytics/company-stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["companies"]) == 1
        assert data["companies"][0]["company"] == "Google"
        assert data["companies"][0]["total_applications"] == 3

    @pytest.mark.asyncio
    async def test_company_stats_limit(self, client: AsyncClient, auth_headers: dict):
        """Test company stats with limit parameter."""
        response = await client.get(
            "/api/analytics/company-stats", headers=auth_headers, params={"limit": 5}
        )
        assert response.status_code == 200


class TestResponseTime:
    """Tests for GET /api/analytics/response-time"""

    @pytest.mark.asyncio
    async def test_response_time_empty(self, client: AsyncClient, auth_headers: dict):
        """Test response time with no data."""
        response = await client.get("/api/analytics/response-time", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["overall_avg_days"] is None
        assert data["by_status"] == []
        assert data["by_company"] == []

    @pytest.mark.asyncio
    async def test_response_time_with_data(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test response time with applications that have response dates."""
        job = JobApplication(
            profile_id=test_profile.id,
            company="Fast Company",
            position="Developer",
            status="Interview",
            application_date=date.today() - timedelta(days=5),
            response_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()

        response = await client.get("/api/analytics/response-time", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["overall_avg_days"] is not None
        assert data["overall_avg_days"] >= 0


class TestResumePerformance:
    """Tests for GET /api/analytics/resume-performance"""

    @pytest.mark.asyncio
    async def test_resume_performance_empty(self, client: AsyncClient, auth_headers: dict):
        """Test resume performance with no data."""
        response = await client.get("/api/analytics/resume-performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["resumes"] == []
        assert data["best_performing_resume"] is None

    @pytest.mark.asyncio
    async def test_resume_performance_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db: Session,
        test_profile: Profile,
        test_resume: Resume,
    ):
        """Test resume performance with applications linked to resumes."""
        # Create jobs linked to the test resume
        for i in range(3):
            job = JobApplication(
                profile_id=test_profile.id,
                company=f"Company {i}",
                position="Developer",
                status="Interview" if i == 0 else "Applied",
                resume_id=test_resume.id,
                created_at=datetime.utcnow(),
            )
            db.add(job)
        db.commit()

        response = await client.get("/api/analytics/resume-performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["resumes"]) == 1
        assert data["resumes"][0]["total_applications"] == 3


class TestExport:
    """Tests for POST /api/analytics/export"""

    @pytest.mark.asyncio
    async def test_export_json(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test JSON export."""
        # Create a job
        job = JobApplication(
            profile_id=test_profile.id,
            company="Export Test Co",
            position="Developer",
            status="Applied",
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()

        response = await client.post(
            "/api/analytics/export", headers=auth_headers, json={"format": "json"}
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_csv(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_profile: Profile
    ):
        """Test CSV export."""
        # Create a job
        job = JobApplication(
            profile_id=test_profile.id,
            company="Export Test Co",
            position="Developer",
            status="Applied",
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()

        response = await client.post(
            "/api/analytics/export", headers=auth_headers, json={"format": "csv"}
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_with_date_filter(self, client: AsyncClient, auth_headers: dict):
        """Test export with date range filter."""
        today = date.today()
        response = await client.post(
            "/api/analytics/export",
            headers=auth_headers,
            json={
                "format": "json",
                "start_date": str(today - timedelta(days=30)),
                "end_date": str(today),
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_with_field_selection(self, client: AsyncClient, auth_headers: dict):
        """Test export with specific fields selected."""
        response = await client.post(
            "/api/analytics/export",
            headers=auth_headers,
            json={"format": "json", "include_fields": ["company", "position", "status"]},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_unauthorized(self, client: AsyncClient):
        """Test export without authentication."""
        response = await client.post("/api/analytics/export", json={"format": "json"})
        assert response.status_code == 401
