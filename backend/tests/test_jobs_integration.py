"""
Comprehensive integration tests for job application endpoints.

Tests the complete job application management flow including:
- CRUD operations (Create, Read, Update, Delete)
- Filtering and search functionality
- Status transitions (Kanban workflow)
- Statistics and analytics endpoints
- User isolation and security boundaries
- Edge cases and error handling

These tests verify end-to-end behavior with the database and all middleware.
"""

import pytest
from datetime import date, datetime
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User


class TestJobCRUDOperations:
    """Integration tests for job application CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_job_with_all_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a job application with all available fields."""
        job_data = {
            "company": "Tech Innovators Inc",
            "position": "Senior Software Engineer",
            "job_description": "We are looking for an experienced engineer to lead our backend team.",
            "status": "Bookmarked",
            "location": "San Francisco, CA (Remote)",
            "job_url": "https://techinnovators.com/careers/senior-engineer",
            "notes": "Referred by John from networking event",
            "application_date": "2024-01-15",
            "deadline": "2024-02-15",
            "recruiter_name": "Jane Smith",
            "recruiter_email": "jane.smith@techinnovators.com",
            "recruiter_linkedin": "https://linkedin.com/in/janesmith",
            "recruiter_phone": "+1-555-123-4567",
            "referral_name": "John Doe",
            "referral_relationship": "Former colleague",
            "application_source": "LinkedIn",
        }
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()

        # Verify all fields were saved
        assert data["company"] == job_data["company"]
        assert data["position"] == job_data["position"]
        assert data["job_description"] == job_data["job_description"]
        assert data["status"] == job_data["status"]
        assert data["location"] == job_data["location"]
        assert data["job_url"] == job_data["job_url"]
        assert data["notes"] == job_data["notes"]
        assert data["application_date"] == job_data["application_date"]
        assert data["deadline"] == job_data["deadline"]
        assert data["recruiter_name"] == job_data["recruiter_name"]
        assert data["recruiter_email"] == job_data["recruiter_email"]
        assert data["referral_name"] == job_data["referral_name"]
        assert data["application_source"] == job_data["application_source"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_job_minimal_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a job with only required fields."""
        job_data = {
            "company": "Minimal Corp",
            "position": "Developer",
        }
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["company"] == "Minimal Corp"
        assert data["position"] == "Developer"
        assert data["status"] == "Bookmarked"  # Default status
        assert data["job_description"] is None
        assert data["location"] is None

    @pytest.mark.asyncio
    async def test_create_job_creates_profile_if_missing(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that creating a job creates profile if it doesn't exist."""
        # Delete any existing profile for test_user
        profile = db.query(Profile).filter(Profile.user_id == test_user.id).first()
        if profile:
            db.delete(profile)
            db.commit()

        # Create job - should auto-create profile
        job_data = {"company": "Auto Profile Corp", "position": "Developer"}
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201

        # Verify profile was created
        profile = db.query(Profile).filter(Profile.user_id == test_user.id).first()
        assert profile is not None

    @pytest.mark.asyncio
    async def test_read_job_success(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test reading a specific job application."""
        response = await client.get(f"/api/jobs/{test_job.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_job.id
        assert data["company"] == test_job.company
        assert data["position"] == test_job.position
        assert data["status"] == test_job.status

    @pytest.mark.asyncio
    async def test_read_job_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test reading a non-existent job returns 404."""
        response = await client.get("/api/jobs/999999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_job_all_fields(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test updating all fields of a job application."""
        update_data = {
            "company": "Updated Corp",
            "position": "Staff Engineer",
            "job_description": "Updated description",
            "status": "Applied",
            "location": "New York, NY",
            "job_url": "https://updated.com/job",
            "notes": "Updated notes with more details",
            "recruiter_name": "Updated Recruiter",
            "recruiter_email": "updated@example.com",
        }
        response = await client.put(
            f"/api/jobs/{test_job.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company"] == update_data["company"]
        assert data["position"] == update_data["position"]
        assert data["status"] == update_data["status"]
        assert data["location"] == update_data["location"]
        assert data["notes"] == update_data["notes"]

    @pytest.mark.asyncio
    async def test_update_job_partial(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test partial update of a job application."""
        original_company = test_job.company
        update_data = {"notes": "Only updating notes"}

        response = await client.put(
            f"/api/jobs/{test_job.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Only updating notes"
        assert data["company"] == original_company  # Unchanged

    @pytest.mark.asyncio
    async def test_update_job_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating a non-existent job returns 404."""
        response = await client.put(
            "/api/jobs/999999",
            json={"company": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job_success(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test successful deletion of a job application."""
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
        """Test deleting a non-existent job returns 404."""
        response = await client.delete("/api/jobs/999999", headers=auth_headers)
        assert response.status_code == 404


class TestJobListAndFiltering:
    """Integration tests for job listing and filtering."""

    @pytest.mark.asyncio
    async def test_list_jobs_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing jobs when none exist."""
        response = await client.get("/api/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_jobs_returns_all(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing all jobs for a user."""
        # Create multiple jobs
        companies = ["Company A", "Company B", "Company C"]
        for company in companies:
            await client.post(
                "/api/jobs",
                json={"company": company, "position": "Developer"},
                headers=auth_headers,
            )

        response = await client.get("/api/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_jobs_ordered_by_updated_at(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that jobs are ordered by updated_at descending."""
        # Create jobs
        for i in range(3):
            await client.post(
                "/api/jobs",
                json={"company": f"Company {i}", "position": "Developer"},
                headers=auth_headers,
            )

        response = await client.get("/api/jobs", headers=auth_headers)
        data = response.json()

        # Most recently updated should be first
        assert len(data["items"]) == 3
        # Verify ordering by checking timestamps are descending
        for i in range(len(data["items"]) - 1):
            assert data["items"][i]["updated_at"] >= data["items"][i + 1]["updated_at"]

    @pytest.mark.asyncio
    async def test_filter_by_status_bookmarked(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test filtering jobs by Bookmarked status."""
        await client.post(
            "/api/jobs",
            json={"company": "Bookmarked Co", "position": "Dev", "status": "Bookmarked"},
            headers=auth_headers,
        )
        await client.post(
            "/api/jobs",
            json={"company": "Applied Co", "position": "Dev", "status": "Applied"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?status=Bookmarked", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "Bookmarked"

    @pytest.mark.asyncio
    async def test_filter_by_status_applied(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test filtering jobs by Applied status."""
        await client.post(
            "/api/jobs",
            json={"company": "Bookmarked Co", "position": "Dev", "status": "Bookmarked"},
            headers=auth_headers,
        )
        await client.post(
            "/api/jobs",
            json={"company": "Applied Co", "position": "Dev", "status": "Applied"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?status=Applied", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "Applied"

    @pytest.mark.asyncio
    async def test_filter_by_all_statuses(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test filtering by each valid status."""
        statuses = ["Bookmarked", "Applied", "Phone Screen", "Interview", "Offer", "Rejected"]

        for i, status in enumerate(statuses):
            await client.post(
                "/api/jobs",
                json={"company": f"Company {i}", "position": "Dev", "status": status},
                headers=auth_headers,
            )

        for status in statuses:
            response = await client.get(f"/api/jobs?status={status}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["status"] == status

    @pytest.mark.asyncio
    async def test_search_by_company_name(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching jobs by company name."""
        await client.post(
            "/api/jobs",
            json={"company": "Google Inc", "position": "Engineer"},
            headers=auth_headers,
        )
        await client.post(
            "/api/jobs",
            json={"company": "Microsoft Corp", "position": "Developer"},
            headers=auth_headers,
        )
        await client.post(
            "/api/jobs",
            json={"company": "Alphabet (Google)", "position": "SRE"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?search=Google", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2  # Both Google and Alphabet (Google)
        for job in data["items"]:
            assert "Google" in job["company"]

    @pytest.mark.asyncio
    async def test_search_by_position(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching jobs by position title."""
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
        await client.post(
            "/api/jobs",
            json={"company": "Company C", "position": "Backend Engineer"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?search=Engineer", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2  # Software Engineer and Backend Engineer
        for job in data["items"]:
            assert "Engineer" in job["position"]

    @pytest.mark.asyncio
    async def test_search_case_insensitive(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that search is case-insensitive."""
        await client.post(
            "/api/jobs",
            json={"company": "GOOGLE", "position": "Engineer"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?search=google", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_combined_filter_and_search(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test combining status filter and search."""
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
        await client.post(
            "/api/jobs",
            json={"company": "Microsoft", "position": "Engineer", "status": "Applied"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/jobs?status=Applied&search=Google", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["company"] == "Google"
        assert data["items"][0]["status"] == "Applied"


class TestJobStatusTransitions:
    """Integration tests for job status transitions (Kanban workflow)."""

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
    async def test_status_transition_full_pipeline(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test complete status pipeline: Bookmarked -> Applied -> Interview -> Offer."""
        # Create job
        create_response = await client.post(
            "/api/jobs",
            json={"company": "Pipeline Corp", "position": "Dev", "status": "Bookmarked"},
            headers=auth_headers,
        )
        job_id = create_response.json()["id"]

        # Transition through pipeline
        transitions = ["Applied", "Phone Screen", "Interview", "Offer"]
        for new_status in transitions:
            response = await client.patch(
                f"/api/jobs/{job_id}/status?new_status={new_status}", headers=auth_headers
            )
            assert response.status_code == 200
            assert response.json()["status"] == new_status

    @pytest.mark.asyncio
    async def test_status_transition_to_rejected(
        self, client: AsyncClient, db: Session, test_job: JobApplication, auth_headers: dict
    ):
        """Test transitioning to Rejected status."""
        response = await client.patch(
            f"/api/jobs/{test_job.id}/status?new_status=Rejected", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Rejected"

    @pytest.mark.asyncio
    async def test_status_transition_backwards(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that status can be changed backwards (e.g., Interview -> Applied)."""
        # Create job with Interview status
        create_response = await client.post(
            "/api/jobs",
            json={"company": "Backward Corp", "position": "Dev", "status": "Interview"},
            headers=auth_headers,
        )
        job_id = create_response.json()["id"]

        # Change back to Applied
        response = await client.patch(
            f"/api/jobs/{job_id}/status?new_status=Applied", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Applied"

    @pytest.mark.asyncio
    async def test_status_update_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test status update on non-existent job returns 404."""
        response = await client.patch(
            "/api/jobs/999999/status?new_status=Applied", headers=auth_headers
        )
        assert response.status_code == 404


class TestJobStatistics:
    """Integration tests for job statistics endpoint."""

    @pytest.mark.asyncio
    async def test_stats_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test statistics when no jobs exist."""
        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["status_breakdown"] == {}
        assert data["response_rate"] == 0
        assert data["offer_rate"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_jobs(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test statistics with multiple jobs."""
        jobs = [
            {"company": "A", "position": "Dev", "status": "Bookmarked"},
            {"company": "B", "position": "Dev", "status": "Applied"},
            {"company": "C", "position": "Dev", "status": "Applied"},
            {"company": "D", "position": "Dev", "status": "Interview"},
            {"company": "E", "position": "Dev", "status": "Offer"},
            {"company": "F", "position": "Dev", "status": "Rejected"},
        ]
        for job in jobs:
            await client.post("/api/jobs", json=job, headers=auth_headers)

        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 6
        assert data["status_breakdown"]["Bookmarked"] == 1
        assert data["status_breakdown"]["Applied"] == 2
        assert data["status_breakdown"]["Interview"] == 1
        assert data["status_breakdown"]["Offer"] == 1
        assert data["status_breakdown"]["Rejected"] == 1

    @pytest.mark.asyncio
    async def test_stats_response_rate_calculation(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test response rate calculation (interviews / applied)."""
        # 10 Applied, 3 Interview = 30% response rate
        for i in range(10):
            await client.post(
                "/api/jobs",
                json={"company": f"Applied {i}", "position": "Dev", "status": "Applied"},
                headers=auth_headers,
            )
        for i in range(3):
            await client.post(
                "/api/jobs",
                json={"company": f"Interview {i}", "position": "Dev", "status": "Interview"},
                headers=auth_headers,
            )

        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["response_rate"] == 30.0

    @pytest.mark.asyncio
    async def test_stats_offer_rate_calculation(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test offer rate calculation (offers / total)."""
        # 8 total jobs, 2 offers = 25% offer rate
        for i in range(5):
            await client.post(
                "/api/jobs",
                json={"company": f"Applied {i}", "position": "Dev", "status": "Applied"},
                headers=auth_headers,
            )
        for i in range(1):
            await client.post(
                "/api/jobs",
                json={"company": f"Interview {i}", "position": "Dev", "status": "Interview"},
                headers=auth_headers,
            )
        for i in range(2):
            await client.post(
                "/api/jobs",
                json={"company": f"Offer {i}", "position": "Dev", "status": "Offer"},
                headers=auth_headers,
            )

        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 8
        assert data["offer_rate"] == 25.0

    @pytest.mark.asyncio
    async def test_stats_phone_screen_counts_as_response(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that Phone Screen counts toward response rate."""
        for i in range(10):
            await client.post(
                "/api/jobs",
                json={"company": f"Applied {i}", "position": "Dev", "status": "Applied"},
                headers=auth_headers,
            )
        # 2 Phone Screen + 3 Interview = 5 responses
        for i in range(2):
            await client.post(
                "/api/jobs",
                json={"company": f"Phone {i}", "position": "Dev", "status": "Phone Screen"},
                headers=auth_headers,
            )
        for i in range(3):
            await client.post(
                "/api/jobs",
                json={"company": f"Interview {i}", "position": "Dev", "status": "Interview"},
                headers=auth_headers,
            )

        response = await client.get("/api/jobs/stats", headers=auth_headers)
        data = response.json()
        # Response rate = (2 + 3) / 10 * 100 = 50%
        assert data["response_rate"] == 50.0


class TestJobUserIsolation:
    """Integration tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_see_other_users_jobs(
        self, client: AsyncClient, db: Session,
        test_job: JobApplication, auth_headers: dict,
        second_user: User, second_user_auth_headers: dict
    ):
        """Test that users cannot see each other's jobs."""
        # test_job belongs to test_user
        # second_user should get empty list
        response = await client.get("/api/jobs", headers=second_user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_job(
        self, client: AsyncClient, db: Session,
        test_job: JobApplication,
        second_user: User, second_user_auth_headers: dict
    ):
        """Test that user cannot access another user's specific job."""
        response = await client.get(
            f"/api/jobs/{test_job.id}", headers=second_user_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_job(
        self, client: AsyncClient, db: Session,
        test_job: JobApplication,
        second_user: User, second_user_auth_headers: dict
    ):
        """Test that user cannot update another user's job."""
        response = await client.put(
            f"/api/jobs/{test_job.id}",
            json={"company": "Hacked Corp"},
            headers=second_user_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_job(
        self, client: AsyncClient, db: Session,
        test_job: JobApplication,
        second_user: User, second_user_auth_headers: dict
    ):
        """Test that user cannot delete another user's job."""
        response = await client.delete(
            f"/api/jobs/{test_job.id}", headers=second_user_auth_headers
        )
        assert response.status_code == 404

        # Verify job still exists for original user
        job = db.query(JobApplication).filter(JobApplication.id == test_job.id).first()
        assert job is not None

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_job_status(
        self, client: AsyncClient, db: Session,
        test_job: JobApplication,
        second_user: User, second_user_auth_headers: dict
    ):
        """Test that user cannot update status of another user's job."""
        response = await client.patch(
            f"/api/jobs/{test_job.id}/status?new_status=Rejected",
            headers=second_user_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stats_only_show_own_jobs(
        self, client: AsyncClient, db: Session,
        test_profile: Profile, auth_headers: dict,
        second_user: User, second_user_auth_headers: dict
    ):
        """Test that stats only include user's own jobs."""
        # Create jobs for test_user
        for i in range(5):
            await client.post(
                "/api/jobs",
                json={"company": f"Company {i}", "position": "Dev", "status": "Applied"},
                headers=auth_headers,
            )

        # second_user should see empty stats
        response = await client.get("/api/jobs/stats", headers=second_user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestJobAuthorizationRequired:
    """Integration tests for authorization requirements."""

    @pytest.mark.asyncio
    async def test_list_jobs_requires_auth(self, client: AsyncClient, db: Session):
        """Test that listing jobs requires authentication."""
        response = await client.get("/api/jobs")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_job_requires_auth(self, client: AsyncClient, db: Session):
        """Test that creating a job requires authentication."""
        response = await client.post(
            "/api/jobs",
            json={"company": "Test", "position": "Dev"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_job_requires_auth(self, client: AsyncClient, db: Session):
        """Test that getting a job requires authentication."""
        response = await client.get("/api/jobs/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_job_requires_auth(self, client: AsyncClient, db: Session):
        """Test that updating a job requires authentication."""
        response = await client.put("/api/jobs/1", json={"company": "Updated"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_job_requires_auth(self, client: AsyncClient, db: Session):
        """Test that deleting a job requires authentication."""
        response = await client.delete("/api/jobs/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_status_update_requires_auth(self, client: AsyncClient, db: Session):
        """Test that status update requires authentication."""
        response = await client.patch("/api/jobs/1/status?new_status=Applied")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_requires_auth(self, client: AsyncClient, db: Session):
        """Test that stats endpoint requires authentication."""
        response = await client.get("/api/jobs/stats")
        assert response.status_code == 401


class TestJobEdgeCases:
    """Integration tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_create_job_with_dates(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a job with application and deadline dates."""
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
    async def test_create_job_with_resume_reference(
        self, client: AsyncClient, db: Session,
        test_profile: Profile, test_resume, auth_headers: dict
    ):
        """Test creating a job with a resume ID reference."""
        job_data = {
            "company": "Resume Corp",
            "position": "Developer",
            "resume_id": test_resume.id,
        }
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["resume_id"] == test_resume.id

    @pytest.mark.asyncio
    async def test_search_with_special_characters(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test search with special characters in company name."""
        await client.post(
            "/api/jobs",
            json={"company": "O'Reilly & Associates", "position": "Dev"},
            headers=auth_headers,
        )

        response = await client.get("/api/jobs?search=O'Reilly", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_long_job_description(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a job with a long description."""
        long_description = "Lorem ipsum " * 1000  # Very long description
        job_data = {
            "company": "Long Corp",
            "position": "Developer",
            "job_description": long_description,
        }
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["job_description"] == long_description

    @pytest.mark.asyncio
    async def test_invalid_recruiter_email(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that invalid recruiter email is rejected."""
        job_data = {
            "company": "Email Corp",
            "position": "Developer",
            "recruiter_email": "not-valid-email",
        }
        response = await client.post("/api/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 422
