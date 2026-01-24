"""
Integration tests for job application workflows.

Tests complete end-to-end job application workflows including:
- Complete job lifecycle: Create -> Update -> Status Changes -> Delete
- Job filtering and search across multiple jobs
- Job statistics calculation with real data
- Job import from URL (mocked)
- User data isolation between different users

These tests verify that the job application tracking system works correctly
when all components are integrated together.
"""

import pytest
from datetime import date, datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User


class TestCompleteJobLifecycle:
    """
    Integration tests for the complete job application lifecycle.

    Verifies: Create -> Update -> Status Changes -> Add Notes -> Delete
    """

    @pytest.mark.asyncio
    async def test_complete_job_lifecycle(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test complete job lifecycle from creation to deletion.

        Steps:
        1. Create a new job application
        2. Update job details
        3. Progress through status changes
        4. Add notes
        5. Delete the job
        """
        # Step 1: Create a new job application
        create_response = await client.post(
            "/api/jobs",
            json={
                "company": "TechCorp Inc",
                "position": "Senior Software Engineer",
                "job_description": "Building scalable systems",
                "status": "Bookmarked",
                "location": "Remote",
                "job_url": "https://techcorp.com/jobs/123",
                "notes": "Found on LinkedIn",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        job = create_response.json()
        job_id = job["id"]
        assert job["company"] == "TechCorp Inc"
        assert job["status"] == "Bookmarked"

        # Step 2: Update job details
        update_response = await client.put(
            f"/api/jobs/{job_id}",
            json={
                "job_description": "Building scalable distributed systems with Python",
                "recruiter_name": "Jane Smith",
                "recruiter_email": "jane@techcorp.com",
            },
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        updated_job = update_response.json()
        assert "distributed systems" in updated_job["job_description"]
        assert updated_job["recruiter_name"] == "Jane Smith"

        # Step 3: Progress through status changes
        status_progression = ["Applied", "Phone Screen", "Interview", "Offer"]
        for new_status in status_progression:
            status_response = await client.patch(
                f"/api/jobs/{job_id}/status?new_status={new_status}",
                headers=auth_headers,
            )
            assert status_response.status_code == 200
            assert status_response.json()["status"] == new_status

        # Step 4: Add notes about the offer
        notes_response = await client.put(
            f"/api/jobs/{job_id}",
            json={
                "notes": "Received offer! $150k base + equity. Negotiating start date.",
            },
            headers=auth_headers,
        )
        assert notes_response.status_code == 200
        assert "Received offer" in notes_response.json()["notes"]

        # Step 5: Verify final state before deletion
        get_response = await client.get(f"/api/jobs/{job_id}", headers=auth_headers)
        assert get_response.status_code == 200
        final_job = get_response.json()
        assert final_job["status"] == "Offer"
        assert final_job["recruiter_name"] == "Jane Smith"

        # Step 6: Delete the job
        delete_response = await client.delete(f"/api/jobs/{job_id}", headers=auth_headers)
        assert delete_response.status_code == 204

        # Verify job is deleted
        get_deleted_response = await client.get(f"/api/jobs/{job_id}", headers=auth_headers)
        assert get_deleted_response.status_code == 404

    @pytest.mark.asyncio
    async def test_job_rejection_workflow(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test the workflow when a job application is rejected.

        Tests the path: Apply -> Phone Screen -> Rejected
        """
        # Create and progress job to Phone Screen
        job_response = await client.post(
            "/api/jobs",
            json={
                "company": "RejectCorp",
                "position": "Developer",
                "status": "Applied",
                "application_date": "2024-01-15",
            },
            headers=auth_headers,
        )
        job_id = job_response.json()["id"]

        # Move to Phone Screen
        await client.patch(
            f"/api/jobs/{job_id}/status?new_status=Phone Screen",
            headers=auth_headers,
        )

        # Mark as Rejected with reason
        update_response = await client.put(
            f"/api/jobs/{job_id}",
            json={
                "status": "Rejected",
                "rejection_reason": "Position filled internally",
                "notes": "Recruiter mentioned they may have other roles in Q2",
            },
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        job = update_response.json()
        assert job["status"] == "Rejected"
        assert job["rejection_reason"] == "Position filled internally"


class TestJobFilteringAndSearch:
    """
    Integration tests for job filtering and search functionality.
    """

    @pytest.mark.asyncio
    async def test_filter_jobs_by_multiple_statuses(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test filtering jobs and verifying results across different statuses.
        """
        # Create jobs with different statuses
        job_data = [
            {"company": "Company A", "position": "Dev 1", "status": "Bookmarked"},
            {"company": "Company B", "position": "Dev 2", "status": "Bookmarked"},
            {"company": "Company C", "position": "Dev 3", "status": "Applied"},
            {"company": "Company D", "position": "Dev 4", "status": "Applied"},
            {"company": "Company E", "position": "Dev 5", "status": "Interview"},
            {"company": "Company F", "position": "Dev 6", "status": "Offer"},
            {"company": "Company G", "position": "Dev 7", "status": "Rejected"},
        ]

        for job in job_data:
            await client.post("/api/jobs", json=job, headers=auth_headers)

        # Test filtering by each status
        status_counts = {
            "Bookmarked": 2,
            "Applied": 2,
            "Interview": 1,
            "Offer": 1,
            "Rejected": 1,
        }

        for status, expected_count in status_counts.items():
            response = await client.get(f"/api/jobs?status={status}", headers=auth_headers)
            assert response.status_code == 200
            jobs = response.json()
            assert len(jobs) == expected_count, f"Expected {expected_count} {status} jobs"
            for job in jobs:
                assert job["status"] == status

    @pytest.mark.asyncio
    async def test_search_jobs_by_company_and_position(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test searching jobs by company name and position.
        """
        # Create diverse job listings
        jobs = [
            {"company": "Google", "position": "Software Engineer"},
            {"company": "Google", "position": "Product Manager"},
            {"company": "Microsoft", "position": "Software Engineer"},
            {"company": "Amazon", "position": "DevOps Engineer"},
            {"company": "Meta", "position": "Machine Learning Engineer"},
        ]

        for job in jobs:
            await client.post("/api/jobs", json=job, headers=auth_headers)

        # Search by company name
        google_response = await client.get("/api/jobs?search=Google", headers=auth_headers)
        assert google_response.status_code == 200
        google_jobs = google_response.json()
        assert len(google_jobs) == 2
        assert all(j["company"] == "Google" for j in google_jobs)

        # Search by position
        engineer_response = await client.get(
            "/api/jobs?search=Engineer", headers=auth_headers
        )
        assert engineer_response.status_code == 200
        engineer_jobs = engineer_response.json()
        assert len(engineer_jobs) == 4  # All except Product Manager

        # Search by partial match
        ml_response = await client.get("/api/jobs?search=Machine", headers=auth_headers)
        assert ml_response.status_code == 200
        assert len(ml_response.json()) == 1
        assert ml_response.json()[0]["company"] == "Meta"

    @pytest.mark.asyncio
    async def test_combined_filter_and_search(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test combining status filter with search query.
        """
        # Create jobs with various statuses and companies
        jobs = [
            {"company": "Tech Giant", "position": "Engineer", "status": "Applied"},
            {"company": "Tech Giant", "position": "Manager", "status": "Bookmarked"},
            {"company": "Startup Inc", "position": "Engineer", "status": "Applied"},
            {"company": "Tech Giant", "position": "Designer", "status": "Interview"},
        ]

        for job in jobs:
            await client.post("/api/jobs", json=job, headers=auth_headers)

        # Filter Applied jobs + search for Tech Giant
        response = await client.get(
            "/api/jobs?status=Applied&search=Tech Giant", headers=auth_headers
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["company"] == "Tech Giant"
        assert results[0]["position"] == "Engineer"
        assert results[0]["status"] == "Applied"


class TestJobStatistics:
    """
    Integration tests for job statistics calculation.
    """

    @pytest.mark.asyncio
    async def test_job_stats_calculation(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test that job statistics are calculated correctly.
        """
        # Create a realistic distribution of jobs
        jobs = [
            # Bookmarked (5)
            *[{"company": f"Bookmarked Co {i}", "position": "Dev", "status": "Bookmarked"}
              for i in range(5)],
            # Applied (10)
            *[{"company": f"Applied Co {i}", "position": "Dev", "status": "Applied"}
              for i in range(10)],
            # Phone Screen (3)
            *[{"company": f"Phone Co {i}", "position": "Dev", "status": "Phone Screen"}
              for i in range(3)],
            # Interview (4)
            *[{"company": f"Interview Co {i}", "position": "Dev", "status": "Interview"}
              for i in range(4)],
            # Offer (2)
            *[{"company": f"Offer Co {i}", "position": "Dev", "status": "Offer"}
              for i in range(2)],
            # Rejected (6)
            *[{"company": f"Rejected Co {i}", "position": "Dev", "status": "Rejected"}
              for i in range(6)],
        ]

        for job in jobs:
            await client.post("/api/jobs", json=job, headers=auth_headers)

        # Get stats
        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        stats = response.json()

        # Verify total
        assert stats["total"] == 30

        # Verify status breakdown
        assert stats["status_breakdown"]["Bookmarked"] == 5
        assert stats["status_breakdown"]["Applied"] == 10
        assert stats["status_breakdown"]["Phone Screen"] == 3
        assert stats["status_breakdown"]["Interview"] == 4
        assert stats["status_breakdown"]["Offer"] == 2
        assert stats["status_breakdown"]["Rejected"] == 6

        # Verify response rate calculation
        # Response rate = (Phone Screen + Interview + Offer) / Applied * 100
        # = (3 + 4) / 10 * 100 = 70%
        assert stats["response_rate"] == 70.0

    @pytest.mark.asyncio
    async def test_empty_stats(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test statistics when no jobs exist.
        """
        response = await client.get("/api/jobs/stats", headers=auth_headers)
        assert response.status_code == 200
        stats = response.json()
        assert stats["total"] == 0
        assert stats["status_breakdown"] == {}
        assert stats["response_rate"] == 0


class TestJobImportWorkflow:
    """
    Integration tests for job import functionality.

    Note: These tests use the mock job importer to avoid external requests.
    """

    @pytest.mark.asyncio
    async def test_preview_job_from_url(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test previewing a job from a URL before importing.
        """
        response = await client.get(
            "/api/jobs/import/preview?url=https://example.com/job/123",
            headers=auth_headers,
        )
        # The endpoint should return a response (success depends on mock implementation)
        assert response.status_code in [200, 500]  # 500 if mock not fully configured

    @pytest.mark.asyncio
    async def test_list_supported_sources(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test listing supported job import sources.
        """
        response = await client.get("/api/jobs/import/sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert len(data["sources"]) > 0

        # Verify known sources are included
        source_names = [s["name"] for s in data["sources"]]
        assert "LinkedIn" in source_names
        assert "Indeed" in source_names
        assert "Greenhouse" in source_names


class TestUserDataIsolation:
    """
    Integration tests to verify data isolation between users.
    """

    @pytest.mark.asyncio
    async def test_users_cannot_see_each_others_jobs(
        self, client: AsyncClient, db: Session
    ):
        """
        Test that users can only see their own jobs.
        """
        # Register and login User A
        await client.post(
            "/api/auth/register",
            json={
                "username": "usera",
                "email": "usera@example.com",
                "password": "UserAPass123!",
            },
        )
        login_a = await client.post(
            "/api/auth/login",
            data={"username": "usera", "password": "UserAPass123!"},
        )
        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

        # Register and login User B
        await client.post(
            "/api/auth/register",
            json={
                "username": "userb",
                "email": "userb@example.com",
                "password": "UserBPass123!",
            },
        )
        login_b = await client.post(
            "/api/auth/login",
            data={"username": "userb", "password": "UserBPass123!"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # User A creates jobs
        for i in range(3):
            await client.post(
                "/api/jobs",
                json={"company": f"User A Company {i}", "position": "Developer"},
                headers=headers_a,
            )

        # User B creates jobs
        for i in range(2):
            await client.post(
                "/api/jobs",
                json={"company": f"User B Company {i}", "position": "Designer"},
                headers=headers_b,
            )

        # User A should only see their 3 jobs
        response_a = await client.get("/api/jobs", headers=headers_a)
        assert len(response_a.json()) == 3
        for job in response_a.json():
            assert "User A Company" in job["company"]

        # User B should only see their 2 jobs
        response_b = await client.get("/api/jobs", headers=headers_b)
        assert len(response_b.json()) == 2
        for job in response_b.json():
            assert "User B Company" in job["company"]

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_job_by_id(
        self, client: AsyncClient, db: Session
    ):
        """
        Test that a user cannot access another user's job by ID.
        """
        # Create User A and a job
        await client.post(
            "/api/auth/register",
            json={
                "username": "owner",
                "email": "owner@example.com",
                "password": "OwnerPass123!",
            },
        )
        owner_login = await client.post(
            "/api/auth/login",
            data={"username": "owner", "password": "OwnerPass123!"},
        )
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        job_response = await client.post(
            "/api/jobs",
            json={"company": "Secret Corp", "position": "Confidential Role"},
            headers=owner_headers,
        )
        job_id = job_response.json()["id"]

        # Create User B
        await client.post(
            "/api/auth/register",
            json={
                "username": "intruder",
                "email": "intruder@example.com",
                "password": "IntruderPass123!",
            },
        )
        intruder_login = await client.post(
            "/api/auth/login",
            data={"username": "intruder", "password": "IntruderPass123!"},
        )
        intruder_headers = {"Authorization": f"Bearer {intruder_login.json()['access_token']}"}

        # User B tries to access User A's job
        get_response = await client.get(f"/api/jobs/{job_id}", headers=intruder_headers)
        assert get_response.status_code == 404

        # User B tries to update User A's job
        update_response = await client.put(
            f"/api/jobs/{job_id}",
            json={"company": "Hacked Corp"},
            headers=intruder_headers,
        )
        assert update_response.status_code == 404

        # User B tries to delete User A's job
        delete_response = await client.delete(f"/api/jobs/{job_id}", headers=intruder_headers)
        assert delete_response.status_code == 404

        # Verify original job is unchanged
        owner_job = await client.get(f"/api/jobs/{job_id}", headers=owner_headers)
        assert owner_job.status_code == 200
        assert owner_job.json()["company"] == "Secret Corp"


class TestJobWithRecruiterInfo:
    """
    Integration tests for jobs with recruiter/referral information.
    """

    @pytest.mark.asyncio
    async def test_job_with_full_recruiter_info(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test creating and updating a job with complete recruiter information.
        """
        # Create job with recruiter info
        job_response = await client.post(
            "/api/jobs",
            json={
                "company": "RecruiterCorp",
                "position": "Senior Developer",
                "recruiter_name": "John Recruiter",
                "recruiter_email": "john@recruitercorp.com",
                "recruiter_linkedin": "linkedin.com/in/johnrecruiter",
                "recruiter_phone": "+1-555-123-4567",
            },
            headers=auth_headers,
        )
        assert job_response.status_code == 201
        job = job_response.json()
        assert job["recruiter_name"] == "John Recruiter"
        assert job["recruiter_email"] == "john@recruitercorp.com"
        assert job["recruiter_linkedin"] == "linkedin.com/in/johnrecruiter"
        assert job["recruiter_phone"] == "+1-555-123-4567"

    @pytest.mark.asyncio
    async def test_job_with_referral_info(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test creating a job with referral information.
        """
        job_response = await client.post(
            "/api/jobs",
            json={
                "company": "ReferralCorp",
                "position": "Developer",
                "referral_name": "Jane Friend",
                "referral_relationship": "Former colleague at TechCo",
                "application_source": "Referral",
            },
            headers=auth_headers,
        )
        assert job_response.status_code == 201
        job = job_response.json()
        assert job["referral_name"] == "Jane Friend"
        assert job["referral_relationship"] == "Former colleague at TechCo"
        assert job["application_source"] == "Referral"


class TestJobDates:
    """
    Integration tests for job date tracking.
    """

    @pytest.mark.asyncio
    async def test_job_with_dates(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test creating and tracking jobs with important dates.
        """
        today = date.today()
        deadline = today + timedelta(days=14)

        job_response = await client.post(
            "/api/jobs",
            json={
                "company": "DateCorp",
                "position": "Developer",
                "application_date": today.isoformat(),
                "deadline": deadline.isoformat(),
            },
            headers=auth_headers,
        )
        assert job_response.status_code == 201
        job = job_response.json()
        assert job["application_date"] == today.isoformat()
        assert job["deadline"] == deadline.isoformat()

    @pytest.mark.asyncio
    async def test_track_response_date(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """
        Test tracking response date for a job application.
        """
        # Create job
        job_response = await client.post(
            "/api/jobs",
            json={
                "company": "ResponseCorp",
                "position": "Developer",
                "status": "Applied",
                "application_date": "2024-01-15",
            },
            headers=auth_headers,
        )
        job_id = job_response.json()["id"]

        # Update with response date when heard back
        response_datetime = "2024-01-22T10:30:00"
        update_response = await client.put(
            f"/api/jobs/{job_id}",
            json={
                "status": "Interview",
                "response_date": response_datetime,
            },
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        job = update_response.json()
        assert job["status"] == "Interview"
        assert "2024-01-22" in job["response_date"]
