"""
Tests for job application endpoints.

Tests:
- CRUD operations for job applications
- Status transitions
- Filtering by status
- Search functionality
- Job statistics endpoint
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User


class TestJobList:
    """Tests for listing job applications."""

    @pytest.mark.asyncio
    async def test_list_jobs_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing jobs when none exist."""
        response = await client.get("/api/jobs", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_jobs_with_data(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test listing jobs when they exist."""
        response = await client.get("/api/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company"] == test_job.company
        assert data[0]["position"] == test_job.position

    @pytest.mark.asyncio
    async def test_list_jobs_unauthorized(self, client: AsyncClient, db: Session):
        """Test listing jobs without authentication."""
        response = await client.get("/api/jobs")
        assert response.status_code == 401


class TestJobFiltering:
    """Tests for job filtering and search."""

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test filtering jobs by status."""
        # Create jobs with different statuses
        jobs_data = [
            {"company": "Company A", "position": "Dev", "status": "Bookmarked"},
            {"company": "Company B", "position": "Dev", "status": "Applied"},
            {"company": "Company C", "position": "Dev", "status": "Interview"},
        ]
        for job_data in jobs_data:
            await client.post("/api/jobs", json=job_data, headers=auth_headers)

        # Filter by Applied status
        response = await client.get("/api/jobs?status=Applied", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "Applied"

    @pytest.mark.asyncio
    async def test_filter_by_bookmarked(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test filtering jobs by Bookmarked status."""
        # Create jobs
        await client.post(
            "/api/jobs",
            json={"company": "Company A", "position": "Dev", "status": "Bookmarked"},
            headers=auth_headers,
        )
        await client.post(
            "/api/jobs",
            json={"company": "Company B", "position": "Dev", "status": "Applied"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?status=Bookmarked", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company"] == "Company A"

    @pytest.mark.asyncio
    async def test_search_by_company(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching jobs by company name."""
        # Create jobs
        await client.post(
            "/api/jobs",
            json={"company": "Google", "position": "Engineer"},
            headers=auth_headers,
        )
        await client.post(
            "/api/jobs",
            json={"company": "Microsoft", "position": "Developer"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?search=Google", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company"] == "Google"

    @pytest.mark.asyncio
    async def test_search_by_position(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching jobs by position."""
        # Create jobs
        await client.post(
            "/api/jobs",
            json={"company": "Company A", "position": "Software Engineer"},
            headers=auth_headers,
        )
        await client.post(
            "/api/jobs",
            json={"company": "Company B", "position": "Data Scientist"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?search=Software", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Software" in data[0]["position"]

    @pytest.mark.asyncio
    async def test_combined_filter_and_search(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test combining status filter and search."""
        # Create jobs
        await client.post(
            "/api/jobs",
            json={"company": "Google", "position": "Engineer", "status": "Applied"},
            headers=auth_headers,
        )
        await client.post(
            "/api/jobs",
            json={"company": "Google", "position": "Manager", "status": "Bookmarked"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/jobs?status=Applied&search=Google", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company"] == "Google"
        assert data[0]["status"] == "Applied"


class TestJobCreate:
    """Tests for creating job applications."""

    @pytest.mark.asyncio
    async def test_create_job_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful job creation."""
        job_data = {
            "company": "Tech Corp",
            "position": "Senior Developer",
            "job_description": "Looking for experienced developers",
            "status": "Bookmarked",
            "location": "Remote",
            "job_url": "https://example.com/job",
            "notes": "Great opportunity",
        }
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["company"] == job_data["company"]
        assert data["position"] == job_data["position"]
        assert data["status"] == job_data["status"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_job_minimal(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating job with minimal required fields."""
        job_data = {
            "company": "Minimal Corp",
            "position": "Developer",
        }
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["company"] == job_data["company"]
        assert data["status"] == "Bookmarked"  # Default status

    @pytest.mark.asyncio
    async def test_create_job_with_dates(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating job with application and deadline dates."""
        job_data = {
            "company": "Date Corp",
            "position": "Developer",
            "application_date": "2024-01-15",
            "deadline": "2024-02-15",
        }
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["application_date"] == "2024-01-15"
        assert data["deadline"] == "2024-02-15"

    @pytest.mark.asyncio
    async def test_create_job_with_all_statuses(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating jobs with all valid statuses."""
        statuses = ["Bookmarked", "Applied", "Phone Screen", "Interview", "Offer", "Rejected"]

        for i, status in enumerate(statuses):
            job_data = {
                "company": f"Company {i}",
                "position": "Developer",
                "status": status,
            }
            response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
            assert response.status_code == 201
            assert response.json()["status"] == status

    @pytest.mark.asyncio
    async def test_create_job_unauthorized(self, client: AsyncClient, db: Session):
        """Test creating job without authentication."""
        response = await client.post(
            "/api/jobs",
            json={"company": "Test", "position": "Dev"},
        )
        assert response.status_code == 401


class TestJobRead:
    """Tests for reading individual job applications."""

    @pytest.mark.asyncio
    async def test_get_job_success(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test getting a specific job."""
        response = await client.get(f"/api/jobs/{test_job.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_job.id
        assert data["company"] == test_job.company
        assert data["position"] == test_job.position

    @pytest.mark.asyncio
    async def test_get_job_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a non-existent job."""
        response = await client.get("/api/jobs/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestJobUpdate:
    """Tests for updating job applications."""

    @pytest.mark.asyncio
    async def test_update_job_success(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test successful job update."""
        update_data = {
            "company": "Updated Corp",
            "position": "Senior Developer",
            "notes": "Updated notes",
        }
        response = await client.put(
            f"/api/jobs/{test_job.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company"] == update_data["company"]
        assert data["position"] == update_data["position"]
        assert data["notes"] == update_data["notes"]

    @pytest.mark.asyncio
    async def test_update_job_status(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test updating job status."""
        update_data = {"status": "Applied"}
        response = await client.put(
            f"/api/jobs/{test_job.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Applied"

    @pytest.mark.asyncio
    async def test_update_job_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating a non-existent job."""
        response = await client.put(
            "/api/jobs/99999",
            json={"company": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestJobDelete:
    """Tests for deleting job applications."""

    @pytest.mark.asyncio
    async def test_delete_job_success(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test successful job deletion."""
        job_id = test_job.id
        response = await client.delete(f"/api/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify job is deleted
        get_response = await client.get(f"/api/jobs/{job_id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test deleting a non-existent job."""
        response = await client.delete("/api/jobs/99999", headers=auth_headers)
        assert response.status_code == 404


class TestJobStatusTransition:
    """Tests for quick status update endpoint."""

    @pytest.mark.asyncio
    async def test_quick_status_update(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test quick status update endpoint."""
        response = await client.patch(
            f"/api/jobs/{test_job.id}/status?new_status=Applied", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Applied"

    @pytest.mark.asyncio
    async def test_status_transition_bookmarked_to_applied(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test transitioning from Bookmarked to Applied."""
        # test_job starts as Bookmarked
        response = await client.patch(
            f"/api/jobs/{test_job.id}/status?new_status=Applied", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Applied"

    @pytest.mark.asyncio
    async def test_status_transition_to_interview(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test transitioning to Interview."""
        response = await client.patch(
            f"/api/jobs/{test_job.id}/status?new_status=Interview", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Interview"

    @pytest.mark.asyncio
    async def test_status_transition_to_offer(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test transitioning to Offer."""
        response = await client.patch(
            f"/api/jobs/{test_job.id}/status?new_status=Offer", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Offer"

    @pytest.mark.asyncio
    async def test_status_transition_to_rejected(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test transitioning to Rejected."""
        response = await client.patch(
            f"/api/jobs/{test_job.id}/status?new_status=Rejected", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Rejected"

    @pytest.mark.asyncio
    async def test_status_update_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test status update on non-existent job."""
        response = await client.patch(
            "/api/jobs/99999/status?new_status=Applied", headers=auth_headers
        )
        assert response.status_code == 404


class TestJobStats:
    """Tests for job statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting stats when no jobs exist."""
        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["status_breakdown"] == {}

    @pytest.mark.asyncio
    async def test_get_stats_with_jobs(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting stats with multiple jobs."""
        # Create jobs with different statuses
        statuses = ["Applied", "Applied", "Interview", "Offer", "Rejected"]
        for i, status in enumerate(statuses):
            await client.post(
                "/api/jobs",
                json={"company": f"Company {i}", "position": "Dev", "status": status},
                headers=auth_headers,
            )

        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["status_breakdown"]["Applied"] == 2
        assert data["status_breakdown"]["Interview"] == 1
        assert data["status_breakdown"]["Offer"] == 1
        assert data["status_breakdown"]["Rejected"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_response_rate(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test response rate calculation in stats."""
        # Create 10 Applied jobs and 3 Interview jobs
        for i in range(10):
            await client.post(
                "/api/jobs",
                json={"company": f"Company A{i}", "position": "Dev", "status": "Applied"},
                headers=auth_headers,
            )
        for i in range(3):
            await client.post(
                "/api/jobs",
                json={"company": f"Company B{i}", "position": "Dev", "status": "Interview"},
                headers=auth_headers,
            )

        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 13
        # Response rate = interviews / applied * 100 = 3 / 10 * 100 = 30%
        assert data["response_rate"] == 30.0


class TestJobIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_job(
        self,
        client: AsyncClient,
        db: Session,
        test_job: JobApplication,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot access another user's job."""
        response = await client.get(f"/api/jobs/{test_job.id}", headers=admin_auth_headers)
        # Should return 404 because the job doesn't belong to admin's profile
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_job(
        self,
        client: AsyncClient,
        db: Session,
        test_job: JobApplication,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot update another user's job."""
        response = await client.put(
            f"/api/jobs/{test_job.id}",
            json={"company": "Hacked Company"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_job(
        self,
        client: AsyncClient,
        db: Session,
        test_job: JobApplication,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot delete another user's job."""
        response = await client.delete(
            f"/api/jobs/{test_job.id}", headers=admin_auth_headers
        )
        assert response.status_code == 404
