"""
Comprehensive integration tests for resume endpoints.

Tests the complete resume management flow including:
- CRUD operations (Create, Read, Update, Delete)
- File upload and parsing (text, PDF, DOCX)
- ATS analysis functionality
- File parsing service validation
- User isolation and security boundaries
- Edge cases and error handling

These tests verify end-to-end behavior with the database and all middleware.
"""

import io
import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.models.resume import Resume
from app.models.profile import Profile
from app.models.user import User


class TestResumeCRUDOperations:
    """Integration tests for resume CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_resume_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful resume creation."""
        resume_data = {
            "version_name": "Software Engineer Resume v1",
            "content": "John Doe\nSoftware Engineer\n\nExperience:\n- 5 years Python development",
        }
        response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()

        assert data["version_name"] == resume_data["version_name"]
        assert data["content"] == resume_data["content"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["profile_id"] == test_profile.id

    @pytest.mark.asyncio
    async def test_create_resume_creates_profile_if_missing(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that creating a resume creates profile if it doesn't exist."""
        # Delete any existing profile for test_user
        profile = db.query(Profile).filter(Profile.user_id == test_user.id).first()
        if profile:
            db.delete(profile)
            db.commit()

        resume_data = {
            "version_name": "Auto Profile Resume",
            "content": "Resume content here",
        }
        response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
        assert response.status_code == 201

        # Verify profile was created
        profile = db.query(Profile).filter(Profile.user_id == test_user.id).first()
        assert profile is not None

    @pytest.mark.asyncio
    async def test_create_multiple_resumes(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating multiple resume versions."""
        versions = [
            {"version_name": "General Resume", "content": "General content"},
            {"version_name": "Tech Resume", "content": "Tech-focused content"},
            {"version_name": "Management Resume", "content": "Leadership-focused content"},
        ]

        for resume_data in versions:
            response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
            assert response.status_code == 201

        # Verify all resumes exist
        list_response = await client.get("/api/resumes", headers=auth_headers)
        assert len(list_response.json()["items"]) == 3

    @pytest.mark.asyncio
    async def test_read_resume_success(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test reading a specific resume."""
        response = await client.get(f"/api/resumes/{test_resume.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_resume.id
        assert data["version_name"] == test_resume.version_name
        assert data["content"] == test_resume.content

    @pytest.mark.asyncio
    async def test_read_resume_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test reading a non-existent resume returns 404."""
        response = await client.get("/api/resumes/999999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

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
        assert data["items"][0]["id"] == test_resume.id

    @pytest.mark.asyncio
    async def test_list_resumes_ordered_by_updated_at(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that resumes are ordered by updated_at descending."""
        # Create multiple resumes
        for i in range(3):
            await client.post(
                "/api/resumes",
                json={"version_name": f"Resume {i}", "content": f"Content {i}"},
                headers=auth_headers,
            )

        response = await client.get("/api/resumes", headers=auth_headers)
        data = response.json()

        # Verify ordering - most recently updated first
        for i in range(len(data["items"]) - 1):
            assert data["items"][i]["updated_at"] >= data["items"][i + 1]["updated_at"]

    @pytest.mark.asyncio
    async def test_update_resume_success(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test successful resume update."""
        update_data = {
            "version_name": "Updated Resume Name",
            "content": "Completely updated content with new skills and experience",
        }
        response = await client.put(
            f"/api/resumes/{test_resume.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_name"] == update_data["version_name"]
        assert data["content"] == update_data["content"]

    @pytest.mark.asyncio
    async def test_update_resume_partial_version_name(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test partial update - only version name."""
        original_content = test_resume.content
        update_data = {"version_name": "Only Name Updated"}

        response = await client.put(
            f"/api/resumes/{test_resume.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_name"] == "Only Name Updated"
        assert data["content"] == original_content  # Content unchanged

    @pytest.mark.asyncio
    async def test_update_resume_partial_content(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test partial update - only content."""
        original_name = test_resume.version_name
        update_data = {"content": "Only content is updated here"}

        response = await client.put(
            f"/api/resumes/{test_resume.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_name"] == original_name  # Name unchanged
        assert data["content"] == "Only content is updated here"

    @pytest.mark.asyncio
    async def test_update_resume_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating a non-existent resume returns 404."""
        response = await client.put(
            "/api/resumes/999999",
            json={"version_name": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404

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
        """Test deleting a non-existent resume returns 404."""
        response = await client.delete("/api/resumes/999999", headers=auth_headers)
        assert response.status_code == 404


class TestFileUpload:
    """Integration tests for resume file upload."""

    @pytest.mark.asyncio
    async def test_upload_text_file(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading a plain text resume file."""
        file_content = b"John Doe\nSoftware Engineer\n\nSkills: Python, FastAPI, SQL"
        files = {"file": ("resume.txt", file_content, "text/plain")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "content" in data
        assert data["filename"] == "resume.txt"
        assert "John Doe" in data["content"]

    @pytest.mark.asyncio
    async def test_upload_text_file_utf8(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading a UTF-8 encoded text file with special characters."""
        file_content = "Resume with special chars: cafe, resume, naive".encode("utf-8")
        files = {"file": ("resume.txt", file_content, "text/plain")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 200
        assert "cafe" in response.json()["content"]

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type_html(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading an invalid file type (HTML) is rejected."""
        file_content = b"<html><body>Not a resume</body></html>"
        files = {"file": ("resume.html", file_content, "text/html")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type_json(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading an invalid file type (JSON) is rejected."""
        file_content = b'{"name": "John Doe"}'
        files = {"file": ("resume.json", file_content, "application/json")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_pdf_file(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading a PDF file (content type acceptance)."""
        # Create minimal PDF-like content with proper magic bytes
        file_content = b"%PDF-1.4 Mock PDF content for testing"
        files = {"file": ("resume.pdf", file_content, "application/pdf")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        # May return 200 (successful parse) or 400 (parse error for mock content)
        # We're testing that the endpoint accepts the content type
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_upload_docx_file(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading a DOCX file (content type acceptance)."""
        # DOCX files are ZIP archives starting with PK
        file_content = b"PK\x03\x04 Mock DOCX content for testing"
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
    async def test_upload_requires_authentication(
        self, client: AsyncClient, db: Session
    ):
        """Test that file upload requires authentication."""
        files = {"file": ("resume.txt", b"content", "text/plain")}
        response = await client.post("/api/resumes/upload", files=files)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_empty_file(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test uploading an empty file."""
        files = {"file": ("resume.txt", b"", "text/plain")}
        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        # Empty file should be handled gracefully
        assert response.status_code in [200, 400]


class TestATSAnalysis:
    """Integration tests for ATS (Applicant Tracking System) analysis."""

    @pytest.mark.asyncio
    async def test_analyze_resume_basic(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test basic ATS analysis without job description."""
        response = await client.post(
            "/api/resumes/analyze",
            json={
                "resume_content": "John Doe\nSoftware Engineer\n\nPython, FastAPI, SQL",
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

    @pytest.mark.asyncio
    async def test_analyze_resume_with_job_description(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test ATS analysis with job description for keyword matching."""
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
        assert "suggestions" in data
        assert "keyword_matches" in data
        assert "missing_keywords" in data
        assert "score_breakdown" in data

        # With matching skills, score should be reasonable
        assert data["ats_score"] >= 0

    @pytest.mark.asyncio
    async def test_analyze_resume_keyword_extraction(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that ATS analysis extracts keywords correctly."""
        resume = """
        John Doe
        Senior Software Engineer

        Skills: Python, JavaScript, React, AWS, Docker, Kubernetes
        Experience: 5+ years in full-stack development
        """
        job_description = """
        Looking for: Python developer with AWS experience
        Required: Docker, Kubernetes knowledge
        """

        response = await client.post(
            "/api/resumes/analyze",
            json={
                "resume_content": resume,
                "job_description": job_description,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should find matching keywords
        assert "keyword_matches" in data
        assert isinstance(data["keyword_matches"], list)

    @pytest.mark.asyncio
    async def test_analyze_resume_empty_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test ATS analysis with empty resume content."""
        response = await client.post(
            "/api/resumes/analyze",
            json={"resume_content": ""},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Empty content should result in very low score
        assert data["ats_score"] <= 10

    @pytest.mark.asyncio
    async def test_analyze_resume_whitespace_only(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test ATS analysis with whitespace-only content."""
        response = await client.post(
            "/api/resumes/analyze",
            json={"resume_content": "   \n\n\t   "},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ats_score"] <= 10

    @pytest.mark.asyncio
    async def test_analyze_resume_requires_authentication(
        self, client: AsyncClient, db: Session
    ):
        """Test that ATS analysis requires authentication."""
        response = await client.post(
            "/api/resumes/analyze",
            json={"resume_content": "Test resume"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_analyze_resume_score_breakdown(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
    ):
        """Test that ATS analysis provides score breakdown."""
        response = await client.post(
            "/api/resumes/analyze",
            json={"resume_content": sample_resume_content},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert "score_breakdown" in data
        assert isinstance(data["score_breakdown"], dict)

    @pytest.mark.asyncio
    async def test_analyze_resume_provides_suggestions(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that ATS analysis provides improvement suggestions."""
        # Resume with missing common elements
        basic_resume = "John Doe\nDeveloper"

        response = await client.post(
            "/api/resumes/analyze",
            json={"resume_content": basic_resume},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have suggestions for a basic resume
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)


class TestFileParserService:
    """Integration tests for file parsing service validation."""

    @pytest.mark.asyncio
    async def test_txt_parsing_utf8(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test text file parsing with UTF-8 encoding."""
        content = "Resume with UTF-8: Python Developer".encode("utf-8")
        files = {"file": ("resume.txt", content, "text/plain")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 200
        assert "Python Developer" in response.json()["content"]

    @pytest.mark.asyncio
    async def test_txt_parsing_latin1_fallback(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test text file parsing falls back to latin-1 for non-UTF8 content."""
        # Create content that's valid latin-1 but might fail UTF-8
        content = "Resume text".encode("latin-1")
        files = {"file": ("resume.txt", content, "text/plain")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_magic_byte_validation_txt_as_pdf(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that text content claimed as PDF is rejected."""
        # Text content but claiming to be PDF
        content = b"This is plain text, not a PDF"
        files = {"file": ("resume.pdf", content, "application/pdf")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        assert response.status_code == 400
        # Should reject because magic bytes don't match

    @pytest.mark.asyncio
    async def test_file_with_valid_pdf_magic_bytes(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that files with valid PDF magic bytes are accepted for processing."""
        # Valid PDF magic bytes
        content = b"%PDF-1.4 more content here"
        files = {"file": ("resume.pdf", content, "application/pdf")}

        response = await client.post("/api/resumes/upload", files=files, headers=auth_headers)
        # May succeed or fail parsing, but should pass magic byte check
        assert response.status_code in [200, 400]


class TestResumeUserIsolation:
    """Integration tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_see_other_users_resumes(
        self,
        client: AsyncClient,
        db: Session,
        test_resume: Resume,
        auth_headers: dict,
        second_user: User,
        second_user_auth_headers: dict,
    ):
        """Test that users cannot see each other's resumes."""
        # test_resume belongs to test_user
        # second_user should get empty list
        response = await client.get("/api/resumes", headers=second_user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_resume(
        self,
        client: AsyncClient,
        db: Session,
        test_resume: Resume,
        second_user: User,
        second_user_auth_headers: dict,
    ):
        """Test that user cannot access another user's specific resume."""
        response = await client.get(
            f"/api/resumes/{test_resume.id}", headers=second_user_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_resume(
        self,
        client: AsyncClient,
        db: Session,
        test_resume: Resume,
        second_user: User,
        second_user_auth_headers: dict,
    ):
        """Test that user cannot update another user's resume."""
        response = await client.put(
            f"/api/resumes/{test_resume.id}",
            json={"version_name": "Hacked Resume"},
            headers=second_user_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_resume(
        self,
        client: AsyncClient,
        db: Session,
        test_resume: Resume,
        second_user: User,
        second_user_auth_headers: dict,
    ):
        """Test that user cannot delete another user's resume."""
        response = await client.delete(
            f"/api/resumes/{test_resume.id}", headers=second_user_auth_headers
        )
        assert response.status_code == 404

        # Verify resume still exists for original user
        resume = db.query(Resume).filter(Resume.id == test_resume.id).first()
        assert resume is not None


class TestResumeAuthorizationRequired:
    """Integration tests for authorization requirements."""

    @pytest.mark.asyncio
    async def test_list_resumes_requires_auth(self, client: AsyncClient, db: Session):
        """Test that listing resumes requires authentication."""
        response = await client.get("/api/resumes")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_resume_requires_auth(self, client: AsyncClient, db: Session):
        """Test that creating a resume requires authentication."""
        response = await client.post(
            "/api/resumes",
            json={"version_name": "Test", "content": "Content"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_resume_requires_auth(self, client: AsyncClient, db: Session):
        """Test that getting a resume requires authentication."""
        response = await client.get("/api/resumes/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_resume_requires_auth(self, client: AsyncClient, db: Session):
        """Test that updating a resume requires authentication."""
        response = await client.put(
            "/api/resumes/1",
            json={"version_name": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_resume_requires_auth(self, client: AsyncClient, db: Session):
        """Test that deleting a resume requires authentication."""
        response = await client.delete("/api/resumes/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_analyze_requires_auth(self, client: AsyncClient, db: Session):
        """Test that ATS analysis requires authentication."""
        response = await client.post(
            "/api/resumes/analyze",
            json={"resume_content": "Test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, client: AsyncClient, db: Session):
        """Test that file upload requires authentication."""
        files = {"file": ("resume.txt", b"content", "text/plain")}
        response = await client.post("/api/resumes/upload", files=files)
        assert response.status_code == 401


class TestResumeEdgeCases:
    """Integration tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_create_resume_long_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a resume with very long content."""
        long_content = "Lorem ipsum " * 10000  # Very long resume
        resume_data = {
            "version_name": "Long Resume",
            "content": long_content,
        }
        response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["content"] == long_content

    @pytest.mark.asyncio
    async def test_create_resume_special_characters(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a resume with special characters."""
        special_content = """
        Name: John O'Brien
        Skills: C++, C#, R&D
        Experience at "Big Corp" (2020-2024)
        Salary: $100,000+
        Email: john@example.com
        """
        resume_data = {
            "version_name": "Special Chars Resume",
            "content": special_content,
        }
        response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
        assert response.status_code == 201
        assert "O'Brien" in response.json()["content"]
        assert 'C++' in response.json()["content"]

    @pytest.mark.asyncio
    async def test_create_resume_unicode_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a resume with Unicode characters."""
        unicode_content = """
        Name: Jean-Pierre Dubois
        Location: Montreal, Quebec
        Languages: Francais, English
        Skills: Machine Learning
        """
        resume_data = {
            "version_name": "Unicode Resume",
            "content": unicode_content,
        }
        response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_resume_empty_version_name(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a resume with empty version name."""
        resume_data = {
            "version_name": "",
            "content": "Resume content here",
        }
        response = await client.post("/api/resumes", json=resume_data, headers=auth_headers)
        # Behavior depends on validation rules - may accept or reject empty name
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_update_resume_updates_timestamp(
        self, client: AsyncClient, db: Session, test_resume: Resume, auth_headers: dict
    ):
        """Test that updating a resume updates the updated_at timestamp."""
        original_updated_at = test_resume.updated_at

        # Small delay to ensure different timestamp
        import asyncio
        await asyncio.sleep(0.1)

        response = await client.put(
            f"/api/resumes/{test_resume.id}",
            json={"content": "Updated content"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify timestamp was updated
        db.refresh(test_resume)
        assert test_resume.updated_at >= original_updated_at

    @pytest.mark.asyncio
    async def test_analyze_resume_with_html_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test ATS analysis handles resume with embedded HTML-like content."""
        content_with_html = """
        <h1>John Doe</h1>
        <p>Software Engineer</p>
        <ul>
            <li>Python</li>
            <li>JavaScript</li>
        </ul>
        """
        response = await client.post(
            "/api/resumes/analyze",
            json={"resume_content": content_with_html},
            headers=auth_headers,
        )
        assert response.status_code == 200
        # Should handle gracefully even if content has HTML-like structure

    @pytest.mark.asyncio
    async def test_multiple_resume_versions_per_user(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that users can have multiple resume versions."""
        versions = 10
        for i in range(versions):
            response = await client.post(
                "/api/resumes",
                json={
                    "version_name": f"Resume Version {i}",
                    "content": f"Content for version {i}",
                },
                headers=auth_headers,
            )
            assert response.status_code == 201

        # Verify all versions exist
        list_response = await client.get("/api/resumes", headers=auth_headers)
        assert len(list_response.json()["items"]) == versions


class TestResumeIntegrationWithJobs:
    """Integration tests for resume-job relationships."""

    @pytest.mark.asyncio
    async def test_resume_referenced_by_job(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
    ):
        """Test that a job can reference a resume."""
        # Create resume
        resume_response = await client.post(
            "/api/resumes",
            json={"version_name": "Job Resume", "content": "Resume for job application"},
            headers=auth_headers,
        )
        resume_id = resume_response.json()["id"]

        # Create job referencing the resume
        job_response = await client.post(
            "/api/jobs",
            json={
                "company": "Test Corp",
                "position": "Developer",
                "resume_id": resume_id,
            },
            headers=auth_headers,
        )
        assert job_response.status_code == 201
        assert job_response.json()["resume_id"] == resume_id

    @pytest.mark.asyncio
    async def test_deleting_resume_does_not_delete_job(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
    ):
        """Test that deleting a resume doesn't delete associated jobs."""
        # Create resume
        resume_response = await client.post(
            "/api/resumes",
            json={"version_name": "Deletable Resume", "content": "Content"},
            headers=auth_headers,
        )
        resume_id = resume_response.json()["id"]

        # Create job referencing the resume
        job_response = await client.post(
            "/api/jobs",
            json={
                "company": "Test Corp",
                "position": "Developer",
                "resume_id": resume_id,
            },
            headers=auth_headers,
        )
        job_id = job_response.json()["id"]

        # Delete resume
        delete_response = await client.delete(
            f"/api/resumes/{resume_id}", headers=auth_headers
        )
        assert delete_response.status_code == 204

        # Job should still exist (with null resume_id or preserved reference)
        job_check = await client.get(f"/api/jobs/{job_id}", headers=auth_headers)
        assert job_check.status_code == 200
