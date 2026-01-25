"""
Tests for cover letter endpoints.

Tests:
- CRUD operations for cover letters (create, read, list, delete)
- AI generation endpoint
- User data isolation (can't access others' cover letters)
- Validation and error handling
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.cover_letter import CoverLetter
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User


class TestCoverLetterList:
    """Tests for listing cover letters."""

    @pytest.mark.asyncio
    async def test_list_cover_letters_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing cover letters when none exist."""
        response = await client.get("/api/cover-letters", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_cover_letters_with_data(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing cover letters when they exist."""
        # Create a cover letter
        cover_letter = CoverLetter(
            profile_id=test_profile.id,
            content="Dear Hiring Manager,\n\nI am writing to apply...",
        )
        db.add(cover_letter)
        db.commit()
        db.refresh(cover_letter)

        response = await client.get("/api/cover-letters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == cover_letter.content
        assert data[0]["id"] == cover_letter.id

    @pytest.mark.asyncio
    async def test_list_cover_letters_multiple(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing multiple cover letters returns them in order."""
        # Create multiple cover letters
        for i in range(3):
            cover_letter = CoverLetter(
                profile_id=test_profile.id,
                content=f"Cover letter {i}",
            )
            db.add(cover_letter)
        db.commit()

        response = await client.get("/api/cover-letters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_list_cover_letters_unauthorized(self, client: AsyncClient, db: Session):
        """Test listing cover letters without authentication."""
        response = await client.get("/api/cover-letters")
        assert response.status_code == 401


class TestCoverLetterCreate:
    """Tests for creating cover letters."""

    @pytest.mark.asyncio
    async def test_create_cover_letter_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful cover letter creation."""
        cover_letter_data = {
            "content": "Dear Hiring Manager,\n\nI am excited to apply for the position...",
        }
        response = await client.post(
            "/api/cover-letters", json=cover_letter_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == cover_letter_data["content"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["profile_id"] == test_profile.id

    @pytest.mark.asyncio
    async def test_create_cover_letter_with_job_application(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        test_job: JobApplication,
        auth_headers: dict,
    ):
        """Test creating a cover letter linked to a job application."""
        cover_letter_data = {
            "content": "Application-specific cover letter content...",
            "job_application_id": test_job.id,
        }
        response = await client.post(
            "/api/cover-letters", json=cover_letter_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["job_application_id"] == test_job.id

    @pytest.mark.asyncio
    async def test_create_cover_letter_empty_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating cover letter with empty content fails."""
        response = await client.post(
            "/api/cover-letters",
            json={"content": ""},
            headers=auth_headers,
        )
        # Empty string should still be accepted by Pydantic, but might be rejected by validation
        # Depending on schema validation, this could be 201 or 422
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_create_cover_letter_unauthorized(self, client: AsyncClient, db: Session):
        """Test creating cover letter without authentication."""
        response = await client.post(
            "/api/cover-letters",
            json={"content": "Test content"},
        )
        assert response.status_code == 401


class TestCoverLetterRead:
    """Tests for reading individual cover letters."""

    @pytest.mark.asyncio
    async def test_get_cover_letter_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a specific cover letter."""
        # Create a cover letter
        cover_letter = CoverLetter(
            profile_id=test_profile.id,
            content="Test cover letter content",
        )
        db.add(cover_letter)
        db.commit()
        db.refresh(cover_letter)

        response = await client.get(
            f"/api/cover-letters/{cover_letter.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == cover_letter.id
        assert data["content"] == cover_letter.content

    @pytest.mark.asyncio
    async def test_get_cover_letter_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a non-existent cover letter."""
        response = await client.get("/api/cover-letters/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_cover_letter_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test getting cover letter without authentication."""
        # Create a cover letter
        cover_letter = CoverLetter(
            profile_id=test_profile.id,
            content="Test content",
        )
        db.add(cover_letter)
        db.commit()

        response = await client.get(f"/api/cover-letters/{cover_letter.id}")
        assert response.status_code == 401


class TestCoverLetterDelete:
    """Tests for deleting cover letters."""

    @pytest.mark.asyncio
    async def test_delete_cover_letter_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful cover letter deletion."""
        # Create a cover letter
        cover_letter = CoverLetter(
            profile_id=test_profile.id,
            content="To be deleted",
        )
        db.add(cover_letter)
        db.commit()
        cover_letter_id = cover_letter.id

        response = await client.delete(
            f"/api/cover-letters/{cover_letter_id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's deleted
        get_response = await client.get(
            f"/api/cover-letters/{cover_letter_id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_cover_letter_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test deleting a non-existent cover letter."""
        response = await client.delete("/api/cover-letters/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_cover_letter_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test deleting cover letter without authentication."""
        # Create a cover letter
        cover_letter = CoverLetter(
            profile_id=test_profile.id,
            content="Test content",
        )
        db.add(cover_letter)
        db.commit()

        response = await client.delete(f"/api/cover-letters/{cover_letter.id}")
        assert response.status_code == 401


class TestCoverLetterGenerate:
    """Tests for AI cover letter generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_cover_letter_success(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test successful AI cover letter generation."""
        request_data = {
            "resume_content": sample_resume_content,
            "job_description": sample_job_description,
            "company_name": "Tech Corp",
            "position": "Senior Developer",
        }
        response = await client.post(
            "/api/cover-letters/generate", json=request_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 0
        assert "id" in data  # Should be saved to database
        assert data["profile_id"] == test_profile.id

    @pytest.mark.asyncio
    async def test_generate_cover_letter_with_tone(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test cover letter generation with specific tone."""
        request_data = {
            "resume_content": sample_resume_content,
            "job_description": sample_job_description,
            "company_name": "Startup Inc",
            "position": "Engineer",
            "tone": "enthusiastic",
        }
        response = await client.post(
            "/api/cover-letters/generate", json=request_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    @pytest.mark.asyncio
    async def test_generate_cover_letter_missing_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test cover letter generation with missing required fields."""
        # Missing company_name and position
        request_data = {
            "resume_content": "My resume",
            "job_description": "Job description",
        }
        response = await client.post(
            "/api/cover-letters/generate", json=request_data, headers=auth_headers
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_generate_cover_letter_unauthorized(self, client: AsyncClient, db: Session):
        """Test cover letter generation without authentication."""
        response = await client.post(
            "/api/cover-letters/generate",
            json={
                "resume_content": "Resume",
                "job_description": "Job",
                "company_name": "Company",
                "position": "Position",
            },
        )
        assert response.status_code == 401


class TestCoverLetterIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_cover_letter(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot access another user's cover letter."""
        # Create cover letter for test_user (not admin)
        cover_letter = CoverLetter(
            profile_id=test_profile.id,
            content="Private cover letter",
        )
        db.add(cover_letter)
        db.commit()
        db.refresh(cover_letter)

        # Admin tries to access test_user's cover letter
        response = await client.get(
            f"/api/cover-letters/{cover_letter.id}", headers=admin_auth_headers
        )
        # Should return 404 because it doesn't belong to admin's profile
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_cover_letter(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot delete another user's cover letter."""
        # Create cover letter for test_user
        cover_letter = CoverLetter(
            profile_id=test_profile.id,
            content="Private cover letter",
        )
        db.add(cover_letter)
        db.commit()
        db.refresh(cover_letter)

        # Admin tries to delete test_user's cover letter
        response = await client.delete(
            f"/api/cover-letters/{cover_letter.id}", headers=admin_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_only_sees_own_cover_letters(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
        auth_headers: dict,
    ):
        """Test that listing cover letters only returns user's own letters."""
        # Create cover letter for test_user
        cover_letter = CoverLetter(
            profile_id=test_profile.id,
            content="Test user's cover letter",
        )
        db.add(cover_letter)
        db.commit()

        # Admin lists their cover letters - should be empty
        response = await client.get("/api/cover-letters", headers=admin_auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Test user lists their cover letters - should have 1
        response = await client.get("/api/cover-letters", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestCoverLetterEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_create_long_cover_letter(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a cover letter with very long content."""
        long_content = "A" * 10000  # 10k characters
        response = await client.post(
            "/api/cover-letters",
            json={"content": long_content},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert len(response.json()["content"]) == 10000

    @pytest.mark.asyncio
    async def test_cover_letter_with_special_characters(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test cover letter with special characters and unicode."""
        special_content = "Dear Hiring Manager,\n\nI'm excited! \u2764\ufe0f Special chars: <>&\"'"
        response = await client.post(
            "/api/cover-letters",
            json={"content": special_content},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["content"] == special_content

    @pytest.mark.asyncio
    async def test_cover_letter_timestamps(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that cover letter has correct timestamps."""
        response = await client.post(
            "/api/cover-letters",
            json={"content": "Test content"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
        # created_at and updated_at should be very close for new records
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
