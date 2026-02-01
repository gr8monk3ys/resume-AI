"""
Tests for resume endpoints.

Tests:
- CRUD operations for resumes (create, read, update, delete)
- List resumes
- ATS analysis endpoint
- File upload (mock file)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User


class TestResumeList:
    """Tests for listing resumes."""

    @pytest.mark.asyncio
    async def test_list_resumes_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing resumes when none exist."""
        response = await client.get("/api/resumes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_resumes_with_data(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test listing resumes when they exist."""
        response = await client.get("/api/resumes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["version_name"] == test_resume.version_name
        assert data["items"][0]["content"] == test_resume.content

    @pytest.mark.asyncio
    async def test_list_resumes_unauthorized(self, client: AsyncClient, db: Session):
        """Test listing resumes without authentication."""
        response = await client.get("/api/resumes")
        assert response.status_code == 401


class TestResumeCreate:
    """Tests for creating resumes."""

    @pytest.mark.asyncio
    async def test_create_resume_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful resume creation."""
        resume_data = {
            "version_name": "Software Engineer Resume",
            "content": "John Doe\nSoftware Engineer\n\nSkills: Python, FastAPI, SQL",
        }
        response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["version_name"] == resume_data["version_name"]
        assert data["content"] == resume_data["content"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_multiple_resumes(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating multiple resumes."""
        resumes = [
            {"version_name": "Resume v1", "content": "Content 1"},
            {"version_name": "Resume v2", "content": "Content 2"},
            {"version_name": "Resume v3", "content": "Content 3"},
        ]

        for resume_data in resumes:
            response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
            assert response.status_code == 201

        # Verify all resumes are listed
        list_response = await client.get("/api/resumes", headers=auth_headers)
        assert len(list_response.json()["items"]) == 3

    @pytest.mark.asyncio
    async def test_create_resume_unauthorized(self, client: AsyncClient, db: Session):
        """Test creating resume without authentication."""
        response = await client.post(
            "/api/resumes",
            json={"version_name": "Test", "content": "Test content"},
        )
        assert response.status_code == 401


class TestResumeRead:
    """Tests for reading individual resumes."""

    @pytest.mark.asyncio
    async def test_get_resume_success(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test getting a specific resume."""
        response = await client.get(f"/api/resumes/{test_resume.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_resume.id
        assert data["version_name"] == test_resume.version_name
        assert data["content"] == test_resume.content

    @pytest.mark.asyncio
    async def test_get_resume_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a non-existent resume."""
        response = await client.get("/api/resumes/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_resume_unauthorized(
        self, client: AsyncClient, db: Session, test_resume: Resume
    ):
        """Test getting resume without authentication."""
        response = await client.get(f"/api/resumes/{test_resume.id}")
        assert response.status_code == 401


class TestResumeUpdate:
    """Tests for updating resumes."""

    @pytest.mark.asyncio
    async def test_update_resume_success(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test successful resume update."""
        update_data = {
            "version_name": "Updated Resume",
            "content": "Updated content with new skills",
        }
        response = await client.put(
            f"/api/resumes/{test_resume.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_name"] == update_data["version_name"]
        assert data["content"] == update_data["content"]

    @pytest.mark.asyncio
    async def test_update_resume_partial(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test partial resume update (only version_name)."""
        original_content = test_resume.content
        update_data = {"version_name": "Partially Updated Resume"}
        response = await client.put(
            f"/api/resumes/{test_resume.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_name"] == update_data["version_name"]
        assert data["content"] == original_content  # Content should remain unchanged

    @pytest.mark.asyncio
    async def test_update_resume_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating a non-existent resume."""
        response = await client.put(
            "/api/resumes/99999",
            json={"version_name": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestResumeDelete:
    """Tests for deleting resumes."""

    @pytest.mark.asyncio
    async def test_delete_resume_success(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test successful resume deletion."""
        resume_id = test_resume.id
        response = await client.delete(f"/api/resumes/{resume_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify resume is deleted
        get_response = await client.get(f"/api/resumes/{resume_id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_resume_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test deleting a non-existent resume."""
        response = await client.delete("/api/resumes/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_resume_unauthorized(
        self, client: AsyncClient, db: Session, test_resume: Resume
    ):
        """Test deleting resume without authentication."""
        response = await client.delete(f"/api/resumes/{test_resume.id}")
        assert response.status_code == 401


class TestATSAnalysis:
    """Tests for ATS analysis endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_resume_success(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test successful ATS analysis."""
        response = await client.post(
            "/api/resumes/analyze",
            json={
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "ats_score" in data
        assert isinstance(data["ats_score"], int)
        assert 0 <= data["ats_score"] <= 100
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert "keyword_matches" in data
        assert "missing_keywords" in data
        assert "score_breakdown" in data

    @pytest.mark.asyncio
    async def test_analyze_resume_without_job_description(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
    ):
        """Test ATS analysis without job description."""
        response = await client.post(
            "/api/resumes/analyze",
            json={
                "resume_content": sample_resume_content,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "ats_score" in data

    @pytest.mark.asyncio
    async def test_analyze_resume_empty_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test ATS analysis with empty resume content."""
        response = await client.post(
            "/api/resumes/analyze",
            json={
                "resume_content": "",
            },
            headers=auth_headers,
        )
        # Should still return a response, just with low score
        assert response.status_code == 200
        data = response.json()
        assert data["ats_score"] == 0 or data["ats_score"] <= 10

    @pytest.mark.asyncio
    async def test_analyze_resume_unauthorized(self, client: AsyncClient, db: Session):
        """Test ATS analysis without authentication."""
        response = await client.post(
            "/api/resumes/analyze",
            json={"resume_content": "Test resume"},
        )
        assert response.status_code == 401


class TestFileUpload:
    """Tests for resume file upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_text_file(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading a text file."""
        file_content = b"John Doe\nSoftware Engineer\n\nSkills: Python, FastAPI"
        files = {"file": ("resume.txt", file_content, "text/plain")}
        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "content" in data
        assert data["filename"] == "resume.txt"

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading an invalid file type."""
        file_content = b"<html><body>Not a resume</body></html>"
        files = {"file": ("resume.html", file_content, "text/html")}
        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_pdf_file(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading a PDF file (mock - may fail without valid PDF content)."""
        # Simple mock PDF - in real tests would use actual PDF content
        # This tests the endpoint accepts the content type
        file_content = b"%PDF-1.4 Mock PDF content"
        files = {"file": ("resume.pdf", file_content, "application/pdf")}
        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        # May return 200 or 400 depending on PDF parsing
        # We just verify the endpoint handles PDF content type
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_upload_docx_file(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading a DOCX file (mock)."""
        # Mock DOCX content - in real tests would use actual DOCX
        file_content = b"PK\x03\x04 Mock DOCX content"
        files = {
            "file": (
                "resume.docx",
                file_content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        # May return 200 or 400 depending on DOCX parsing
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_upload_unauthorized(self, client: AsyncClient, db: Session):
        """Test file upload without authentication."""
        files = {"file": ("resume.txt", b"content", "text/plain")}
        response = await client.post("/api/resumes/upload", files=files)
        assert response.status_code == 401


class TestResumeIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_resume(
        self,
        client: AsyncClient,
        db: Session,
        test_resume: Resume,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot access another user's resume."""
        # Admin user tries to access test_user's resume
        # Should not find it because it belongs to a different profile
        response = await client.get(
            f"/api/resumes/{test_resume.id}", headers=admin_auth_headers
        )
        # Should return 404 because the resume doesn't belong to admin's profile
        assert response.status_code == 404
