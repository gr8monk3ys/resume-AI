"""
Tests for career journal endpoints.

Tests:
- CRUD operations for career journal entries
- Search functionality
- Tag filtering
- Achievement enhancement endpoint
"""

import json
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.career_journal import CareerJournalEntry
from app.models.profile import Profile
from app.models.user import User


class TestCareerJournalList:
    """Tests for listing career journal entries."""

    @pytest.mark.asyncio
    async def test_list_entries_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing entries when none exist."""
        response = await client.get("/api/career-journal", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_entries_with_data(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        auth_headers: dict,
    ):
        """Test listing entries when they exist."""
        response = await client.get("/api/career-journal", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == test_journal_entry.title
        assert data[0]["description"] == test_journal_entry.description

    @pytest.mark.asyncio
    async def test_list_entries_unauthorized(self, client: AsyncClient, db: Session):
        """Test listing entries without authentication."""
        response = await client.get("/api/career-journal")
        assert response.status_code == 401


class TestCareerJournalSearch:
    """Tests for searching career journal entries."""

    @pytest.mark.asyncio
    async def test_search_by_title(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching entries by title."""
        # Create entries
        await client.post(
            "/api/career-journal",
            json={"title": "Promotion to Senior", "description": "Got promoted"},
            headers=auth_headers,
        )
        await client.post(
            "/api/career-journal",
            json={"title": "Completed Certification", "description": "AWS certified"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/career-journal?search=Promotion", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Promotion" in data[0]["title"]

    @pytest.mark.asyncio
    async def test_search_by_description(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching entries by description."""
        # Create entries
        await client.post(
            "/api/career-journal",
            json={"title": "Achievement 1", "description": "Led a team of 5 engineers"},
            headers=auth_headers,
        )
        await client.post(
            "/api/career-journal",
            json={"title": "Achievement 2", "description": "Completed solo project"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/career-journal?search=team", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "team" in data[0]["description"].lower()

    @pytest.mark.asyncio
    async def test_filter_by_tag(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test filtering entries by tag."""
        # Create entries with different tags
        await client.post(
            "/api/career-journal",
            json={
                "title": "Leadership Award",
                "description": "Received award",
                "tags": ["leadership", "recognition"],
            },
            headers=auth_headers,
        )
        await client.post(
            "/api/career-journal",
            json={
                "title": "Technical Achievement",
                "description": "Built new system",
                "tags": ["technical", "development"],
            },
            headers=auth_headers,
        )

        response = await client.get(
            "/api/career-journal?tag=leadership", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "leadership" in data[0]["tags"]

    @pytest.mark.asyncio
    async def test_combined_search_and_tag(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test combining search and tag filter."""
        # Create entries
        await client.post(
            "/api/career-journal",
            json={
                "title": "Leadership Project A",
                "description": "Led project A",
                "tags": ["leadership"],
            },
            headers=auth_headers,
        )
        await client.post(
            "/api/career-journal",
            json={
                "title": "Leadership Project B",
                "description": "Led project B",
                "tags": ["leadership"],
            },
            headers=auth_headers,
        )
        await client.post(
            "/api/career-journal",
            json={
                "title": "Technical Project A",
                "description": "Built project A",
                "tags": ["technical"],
            },
            headers=auth_headers,
        )

        response = await client.get(
            "/api/career-journal?search=Project%20A&tag=leadership", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Project A" in data[0]["title"]
        assert "leadership" in data[0]["tags"]


class TestCareerJournalCreate:
    """Tests for creating career journal entries."""

    @pytest.mark.asyncio
    async def test_create_entry_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful entry creation."""
        entry_data = {
            "title": "New Achievement",
            "description": "Accomplished something great",
            "achievement_date": str(date.today()),
            "tags": ["achievement", "milestone"],
        }
        response = await client.post(
            "/api/career-journal", json=entry_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == entry_data["title"]
        assert data["description"] == entry_data["description"]
        assert data["tags"] == entry_data["tags"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_entry_minimal(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating entry with minimal required fields."""
        entry_data = {
            "title": "Minimal Entry",
            "description": "Just the basics",
        }
        response = await client.post(
            "/api/career-journal", json=entry_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == entry_data["title"]
        assert data["achievement_date"] is None
        assert data["tags"] is None

    @pytest.mark.asyncio
    async def test_create_entry_with_tags(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating entry with various tags."""
        tags = ["leadership", "technical", "communication", "problem-solving"]
        entry_data = {
            "title": "Multi-tag Entry",
            "description": "Entry with many tags",
            "tags": tags,
        }
        response = await client.post(
            "/api/career-journal", json=entry_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == tags

    @pytest.mark.asyncio
    async def test_create_entry_empty_title(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating entry with empty title (should fail)."""
        response = await client.post(
            "/api/career-journal",
            json={"title": "", "description": "Valid description"},
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_entry_unauthorized(self, client: AsyncClient, db: Session):
        """Test creating entry without authentication."""
        response = await client.post(
            "/api/career-journal",
            json={"title": "Test", "description": "Test"},
        )
        assert response.status_code == 401


class TestCareerJournalRead:
    """Tests for reading individual career journal entries."""

    @pytest.mark.asyncio
    async def test_get_entry_success(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        auth_headers: dict,
    ):
        """Test getting a specific entry."""
        response = await client.get(
            f"/api/career-journal/{test_journal_entry.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_journal_entry.id
        assert data["title"] == test_journal_entry.title

    @pytest.mark.asyncio
    async def test_get_entry_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a non-existent entry."""
        response = await client.get("/api/career-journal/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCareerJournalUpdate:
    """Tests for updating career journal entries."""

    @pytest.mark.asyncio
    async def test_update_entry_success(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        auth_headers: dict,
    ):
        """Test successful entry update."""
        update_data = {
            "title": "Updated Title",
            "description": "Updated description with more details",
            "tags": ["updated", "improved"],
        }
        response = await client.put(
            f"/api/career-journal/{test_journal_entry.id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert data["tags"] == update_data["tags"]

    @pytest.mark.asyncio
    async def test_update_entry_partial(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        auth_headers: dict,
    ):
        """Test partial entry update (only title)."""
        original_description = test_journal_entry.description
        update_data = {"title": "Only Title Updated"}
        response = await client.put(
            f"/api/career-journal/{test_journal_entry.id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == original_description

    @pytest.mark.asyncio
    async def test_update_entry_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating a non-existent entry."""
        response = await client.put(
            "/api/career-journal/99999",
            json={"title": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestCareerJournalDelete:
    """Tests for deleting career journal entries."""

    @pytest.mark.asyncio
    async def test_delete_entry_success(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        auth_headers: dict,
    ):
        """Test successful entry deletion."""
        entry_id = test_journal_entry.id
        response = await client.delete(
            f"/api/career-journal/{entry_id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify entry is deleted
        get_response = await client.get(
            f"/api/career-journal/{entry_id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_entry_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test deleting a non-existent entry."""
        response = await client.delete("/api/career-journal/99999", headers=auth_headers)
        assert response.status_code == 404


class TestEnhanceAchievement:
    """Tests for achievement enhancement endpoint."""

    @pytest.mark.asyncio
    async def test_enhance_achievement_success(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        auth_headers: dict,
    ):
        """Test successful achievement enhancement."""
        response = await client.post(
            f"/api/career-journal/{test_journal_entry.id}/enhance",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "original" in data
        assert "enhanced" in data
        assert data["original"] == test_journal_entry.description
        assert len(data["enhanced"]) > 0

    @pytest.mark.asyncio
    async def test_enhance_achievement_with_custom_text(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        auth_headers: dict,
    ):
        """Test enhancement with custom achievement text."""
        custom_text = "Increased sales by 50%"
        response = await client.post(
            f"/api/career-journal/{test_journal_entry.id}/enhance",
            json={"achievement_text": custom_text},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["original"] == custom_text
        assert "enhanced" in data

    @pytest.mark.asyncio
    async def test_enhance_achievement_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test enhancement on non-existent entry."""
        response = await client.post(
            "/api/career-journal/99999/enhance",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_enhance_achievement_unauthorized(
        self, client: AsyncClient, db: Session, test_journal_entry: CareerJournalEntry
    ):
        """Test enhancement without authentication."""
        response = await client.post(
            f"/api/career-journal/{test_journal_entry.id}/enhance"
        )
        assert response.status_code == 401


class TestCareerJournalIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_entry(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot access another user's entry."""
        response = await client.get(
            f"/api/career-journal/{test_journal_entry.id}", headers=admin_auth_headers
        )
        # Should return 404 because the entry doesn't belong to admin's profile
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_entry(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot update another user's entry."""
        response = await client.put(
            f"/api/career-journal/{test_journal_entry.id}",
            json={"title": "Hacked Title"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_entry(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot delete another user's entry."""
        response = await client.delete(
            f"/api/career-journal/{test_journal_entry.id}", headers=admin_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_enhance_other_users_entry(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot enhance another user's entry."""
        response = await client.post(
            f"/api/career-journal/{test_journal_entry.id}/enhance",
            headers=admin_auth_headers,
        )
        assert response.status_code == 404


class TestTagParsing:
    """Tests for tag parsing functionality."""

    @pytest.mark.asyncio
    async def test_tags_returned_as_list(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that tags are returned as a list."""
        entry_data = {
            "title": "Tagged Entry",
            "description": "Entry with tags",
            "tags": ["tag1", "tag2", "tag3"],
        }
        create_response = await client.post(
            "/api/career-journal", json=entry_data, headers=auth_headers
        )
        assert create_response.status_code == 201

        entry_id = create_response.json()["id"]
        get_response = await client.get(
            f"/api/career-journal/{entry_id}", headers=auth_headers
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert isinstance(data["tags"], list)
        assert data["tags"] == ["tag1", "tag2", "tag3"]

    @pytest.mark.asyncio
    async def test_empty_tags(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test entry with empty tags list."""
        entry_data = {
            "title": "No Tags Entry",
            "description": "Entry without tags",
            "tags": [],
        }
        response = await client.post(
            "/api/career-journal", json=entry_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        # Empty list might be stored as null or empty
        assert data["tags"] is None or data["tags"] == []

    @pytest.mark.asyncio
    async def test_update_tags(
        self,
        client: AsyncClient,
        db: Session,
        test_journal_entry: CareerJournalEntry,
        auth_headers: dict,
    ):
        """Test updating tags on an entry."""
        new_tags = ["new_tag1", "new_tag2"]
        response = await client.put(
            f"/api/career-journal/{test_journal_entry.id}",
            json={"tags": new_tags},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == new_tags
