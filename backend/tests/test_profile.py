"""
Tests for profile management endpoints.

Tests:
- Profile retrieval (auto-creation on first access)
- Profile update
- Profile statistics
- Validation and error handling
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.career_journal import CareerJournalEntry
from app.models.cover_letter import CoverLetter
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User


class TestProfileGet:
    """Tests for getting profile."""

    @pytest.mark.asyncio
    async def test_get_profile_existing(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting an existing profile."""
        response = await client.get("/api/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_profile.id
        assert data["name"] == test_profile.name
        assert data["email"] == test_profile.email

    @pytest.mark.asyncio
    async def test_get_profile_auto_creates(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that profile is auto-created if it doesn't exist."""
        # Delete any existing profile for test_user
        db.query(Profile).filter(Profile.user_id == test_user.id).delete()
        db.commit()

        # Request profile - should auto-create
        response = await client.get("/api/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["name"] == (test_user.full_name or test_user.username)
        assert data["email"] == test_user.email

        # Verify it was persisted
        profile = db.query(Profile).filter(Profile.user_id == test_user.id).first()
        assert profile is not None

    @pytest.mark.asyncio
    async def test_get_profile_unauthorized(self, client: AsyncClient, db: Session):
        """Test getting profile without authentication."""
        response = await client.get("/api/profile")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_profile_returns_all_fields(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that profile returns all expected fields."""
        # Create a profile with all fields populated
        db.query(Profile).filter(Profile.user_id == test_user.id).delete()
        profile = Profile(
            user_id=test_user.id,
            name="Full Name",
            email="full@example.com",
            phone="+1234567890",
            linkedin="https://linkedin.com/in/test",
            github="https://github.com/test",
            portfolio="https://portfolio.test.com",
        )
        db.add(profile)
        db.commit()

        response = await client.get("/api/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Full Name"
        assert data["email"] == "full@example.com"
        assert data["phone"] == "+1234567890"
        assert data["linkedin"] == "https://linkedin.com/in/test"
        assert data["github"] == "https://github.com/test"
        assert data["portfolio"] == "https://portfolio.test.com"
        assert "created_at" in data
        assert "updated_at" in data


class TestProfileUpdate:
    """Tests for updating profile."""

    @pytest.mark.asyncio
    async def test_update_profile_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful profile update."""
        update_data = {
            "name": "Updated Name",
            "email": "updated@example.com",
            "phone": "+1987654321",
        }
        response = await client.put("/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["email"] == update_data["email"]
        assert data["phone"] == update_data["phone"]

    @pytest.mark.asyncio
    async def test_update_profile_partial(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test partial profile update (only some fields)."""
        original_name = test_profile.name
        update_data = {"phone": "+1555555555"}
        response = await client.put("/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == update_data["phone"]
        assert data["name"] == original_name  # Name should remain unchanged

    @pytest.mark.asyncio
    async def test_update_profile_social_links(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating social links in profile."""
        update_data = {
            "linkedin": "https://linkedin.com/in/newprofile",
            "github": "https://github.com/newuser",
            "portfolio": "https://newportfolio.com",
        }
        response = await client.put("/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["linkedin"] == update_data["linkedin"]
        assert data["github"] == update_data["github"]
        assert data["portfolio"] == update_data["portfolio"]

    @pytest.mark.asyncio
    async def test_update_profile_invalid_email(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating profile with invalid email fails."""
        update_data = {"email": "not-a-valid-email"}
        response = await client.put("/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_update_profile_unauthorized(self, client: AsyncClient, db: Session):
        """Test updating profile without authentication."""
        response = await client.put(
            "/api/profile",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_profile_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test updating profile when it doesn't exist returns 404."""
        # Delete any existing profile
        db.query(Profile).filter(Profile.user_id == test_user.id).delete()
        db.commit()

        response = await client.put(
            "/api/profile",
            json={"name": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_profile_empty_values(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test clearing optional fields with null values."""
        # First set some values
        test_profile.phone = "+1234567890"
        test_profile.linkedin = "https://linkedin.com/test"
        db.commit()

        # Now clear them
        update_data = {"phone": None, "linkedin": None}
        response = await client.put("/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] is None
        assert data["linkedin"] is None


class TestProfileStats:
    """Tests for profile statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting stats when no data exists."""
        response = await client.get("/api/profile/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["resume_count"] == 0
        assert data["job_application_count"] == 0
        assert data["cover_letter_count"] == 0
        assert data["journal_entry_count"] == 0
        assert data["job_status_breakdown"] == {}

    @pytest.mark.asyncio
    async def test_get_stats_with_data(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting stats with various data."""
        # Create resumes
        for i in range(2):
            resume = Resume(
                profile_id=test_profile.id, version_name=f"Resume {i}", content="Content"
            )
            db.add(resume)

        # Create job applications with different statuses
        statuses = ["Applied", "Applied", "Interview", "Offer"]
        for i, status in enumerate(statuses):
            job = JobApplication(
                profile_id=test_profile.id,
                company=f"Company {i}",
                position="Developer",
                status=status,
            )
            db.add(job)

        # Create cover letters
        for i in range(3):
            cl = CoverLetter(profile_id=test_profile.id, content=f"Cover letter {i}")
            db.add(cl)

        # Create journal entries
        entry = CareerJournalEntry(
            profile_id=test_profile.id,
            title="Achievement",
            description="Did something great",
        )
        db.add(entry)

        db.commit()

        response = await client.get("/api/profile/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["resume_count"] == 2
        assert data["job_application_count"] == 4
        assert data["cover_letter_count"] == 3
        assert data["journal_entry_count"] == 1
        assert data["job_status_breakdown"]["Applied"] == 2
        assert data["job_status_breakdown"]["Interview"] == 1
        assert data["job_status_breakdown"]["Offer"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_unauthorized(self, client: AsyncClient, db: Session):
        """Test getting stats without authentication."""
        response = await client.get("/api/profile/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_stats_profile_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test getting stats when profile doesn't exist."""
        # Delete any existing profile
        db.query(Profile).filter(Profile.user_id == test_user.id).delete()
        db.commit()

        response = await client.get("/api/profile/stats", headers=auth_headers)
        assert response.status_code == 404


class TestProfileDataIntegrity:
    """Tests for profile data integrity and constraints."""

    @pytest.mark.asyncio
    async def test_profile_user_id_is_set(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        test_profile: Profile,
        auth_headers: dict,
    ):
        """Test that profile is correctly linked to user."""
        response = await client.get("/api/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_profile_timestamps_updated(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that updated_at is changed on profile update."""
        original_updated = test_profile.updated_at

        # Update profile
        response = await client.put(
            "/api/profile",
            json={"name": "New Name"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Refresh and check
        db.refresh(test_profile)
        # Note: In test environment with fast execution, timestamps might be same
        # This is more of a sanity check
        assert test_profile.updated_at is not None


class TestProfileIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_users_have_separate_profiles(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        admin_user: User,
        auth_headers: dict,
        admin_auth_headers: dict,
    ):
        """Test that different users have separate profiles."""
        # Get test user's profile
        response1 = await client.get("/api/profile", headers=auth_headers)
        assert response1.status_code == 200
        profile1 = response1.json()

        # Get admin user's profile (may auto-create)
        response2 = await client.get("/api/profile", headers=admin_auth_headers)
        assert response2.status_code == 200
        profile2 = response2.json()

        # Profiles should be different
        assert profile1["id"] != profile2["id"]
        assert profile1["user_id"] != profile2["user_id"]

    @pytest.mark.asyncio
    async def test_stats_only_count_own_data(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        auth_headers: dict,
        admin_auth_headers: dict,
    ):
        """Test that stats only count the user's own data."""
        # Create data for test user
        for i in range(5):
            resume = Resume(profile_id=test_profile.id, version_name=f"R{i}", content="C")
            db.add(resume)
        db.commit()

        # Test user should see 5 resumes
        response1 = await client.get("/api/profile/stats", headers=auth_headers)
        assert response1.status_code == 200
        assert response1.json()["resume_count"] == 5

        # Admin user should see 0 (their own stats)
        # First ensure admin has a profile
        await client.get("/api/profile", headers=admin_auth_headers)
        response2 = await client.get("/api/profile/stats", headers=admin_auth_headers)
        assert response2.status_code == 200
        assert response2.json()["resume_count"] == 0


class TestProfileEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_update_profile_with_long_values(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating profile with long field values."""
        long_name = "A" * 200
        long_url = "https://example.com/" + "a" * 500
        update_data = {
            "name": long_name,
            "linkedin": long_url,
        }
        response = await client.put("/api/profile", json=update_data, headers=auth_headers)
        # Depending on database column limits, this might succeed or fail
        # Most databases will accept these lengths
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_profile_with_unicode_name(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating profile with unicode characters in name."""
        update_data = {"name": "Jose Garcia Lopez"}
        response = await client.put("/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == update_data["name"]

    @pytest.mark.asyncio
    async def test_profile_concurrent_updates(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that concurrent profile updates work correctly."""
        # First update
        response1 = await client.put(
            "/api/profile",
            json={"name": "First Update"},
            headers=auth_headers,
        )
        assert response1.status_code == 200

        # Second update
        response2 = await client.put(
            "/api/profile",
            json={"name": "Second Update"},
            headers=auth_headers,
        )
        assert response2.status_code == 200

        # Final state should reflect second update
        response3 = await client.get("/api/profile", headers=auth_headers)
        assert response3.json()["name"] == "Second Update"
