"""
Tests for STAR story endpoints.

Tests:
- CRUD operations for STAR stories (create, read, list, update, delete)
- Search and tag filtering
- User data isolation (can't access others' stories)
- Validation and error handling
- Edge cases (special characters, unicode, long content)
"""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.models.star_story import StarStory
from app.models.user import User


def _create_star_story(
    db: Session,
    profile_id: int,
    title: str = "Led Cross-Team Migration to Microservices",
    situation: str = "Our monolithic application was struggling with deployment bottlenecks",
    task: str = "I was tasked with designing and leading the migration strategy",
    action: str = "I broke the monolith into 12 bounded-context services using DDD principles",
    result: str = "Deployment frequency increased from weekly to multiple times per day",
    tags: list | None = None,
) -> StarStory:
    """Helper to create a STAR story directly via ORM."""
    story = StarStory(
        profile_id=profile_id,
        title=title,
        situation=situation,
        task=task,
        action=action,
        result=result,
        tags=json.dumps(tags) if tags is not None else None,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


class TestStarStoryList:
    """Tests for listing STAR stories."""

    @pytest.mark.asyncio
    async def test_list_stories_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing STAR stories when none exist."""
        response = await client.get("/api/star-stories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_list_stories_with_items(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing STAR stories when they exist."""
        story = _create_star_story(db, test_profile.id)

        response = await client.get("/api/star-stories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == story.title
        assert data[0]["id"] == story.id

    @pytest.mark.asyncio
    async def test_list_stories_multiple_ordered_by_created_at_desc(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that multiple stories are returned in reverse chronological order."""
        _create_star_story(db, test_profile.id, title="Resolved Production Outage Under Pressure")
        _create_star_story(db, test_profile.id, title="Mentored Junior Engineers to Promotion")
        _create_star_story(db, test_profile.id, title="Automated Manual QA Pipeline")

        response = await client.get("/api/star-stories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Most recently created should be first (desc order)
        assert data[0]["title"] == "Automated Manual QA Pipeline"

    @pytest.mark.asyncio
    async def test_list_stories_unauthorized(self, client: AsyncClient, db: Session):
        """Test listing STAR stories without authentication."""
        response = await client.get("/api/star-stories")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_stories_search_by_title(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching stories by title keyword."""
        _create_star_story(db, test_profile.id, title="Led Database Migration Project")
        _create_star_story(db, test_profile.id, title="Built Real-Time Analytics Dashboard")

        response = await client.get(
            "/api/star-stories", params={"search": "database"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Database" in data[0]["title"]

    @pytest.mark.asyncio
    async def test_list_stories_filter_by_tag(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test filtering stories by tag."""
        _create_star_story(
            db, test_profile.id,
            title="Optimized API Response Times",
            tags=["performance", "backend"],
        )
        _create_star_story(
            db, test_profile.id,
            title="Redesigned Onboarding Flow",
            tags=["frontend", "ux"],
        )

        response = await client.get(
            "/api/star-stories", params={"tag": "performance"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Optimized API Response Times"


class TestStarStoryCreate:
    """Tests for creating STAR stories."""

    @pytest.mark.asyncio
    async def test_create_story_minimal_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story with only the required title field."""
        story_data = {"title": "Delivered Critical Feature Under Tight Deadline"}
        response = await client.post("/api/star-stories", json=story_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == story_data["title"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["profile_id"] == test_profile.id
        assert data["situation"] is None
        assert data["task"] is None
        assert data["action"] is None
        assert data["result"] is None
        assert data["tags"] is None

    @pytest.mark.asyncio
    async def test_create_story_all_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story with all fields populated."""
        story_data = {
            "title": "Reduced Infrastructure Costs by 40%",
            "situation": "Cloud hosting bills were growing 15% month-over-month with no clear optimization plan",
            "task": "Audit existing infrastructure and propose a cost-reduction roadmap within 2 weeks",
            "action": "Profiled resource usage, right-sized instances, implemented auto-scaling, and moved cold storage to S3 Glacier",
            "result": "Annual savings of $180,000 while maintaining 99.95% uptime SLA",
            "tags": ["cost-optimization", "aws", "leadership"],
        }
        response = await client.post("/api/star-stories", json=story_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == story_data["title"]
        assert data["situation"] == story_data["situation"]
        assert data["task"] == story_data["task"]
        assert data["action"] == story_data["action"]
        assert data["result"] == story_data["result"]
        assert data["tags"] == story_data["tags"]

    @pytest.mark.asyncio
    async def test_create_story_unauthorized(self, client: AsyncClient, db: Session):
        """Test creating a STAR story without authentication."""
        response = await client.post(
            "/api/star-stories",
            json={"title": "Unauthorized Story Attempt"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_story_missing_required_field(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story without the required title field."""
        response = await client.post(
            "/api/star-stories",
            json={"situation": "Some situation without a title"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_story_title_too_long(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story with a title exceeding 255 characters."""
        response = await client.post(
            "/api/star-stories",
            json={"title": "A" * 256},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_story_with_tags(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story with a list of tags."""
        story_data = {
            "title": "Implemented Feature Flags System",
            "tags": ["devops", "feature-management", "risk-mitigation"],
        }
        response = await client.post("/api/star-stories", json=story_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == ["devops", "feature-management", "risk-mitigation"]

    @pytest.mark.asyncio
    async def test_create_story_empty_title(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story with an empty title string."""
        response = await client.post(
            "/api/star-stories",
            json={"title": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestStarStoryGet:
    """Tests for reading individual STAR stories."""

    @pytest.mark.asyncio
    async def test_get_story_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a specific STAR story by ID."""
        story = _create_star_story(
            db, test_profile.id,
            title="Navigated Vendor Contract Renegotiation",
            tags=["negotiation", "vendor-management"],
        )

        response = await client.get(f"/api/star-stories/{story.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == story.id
        assert data["title"] == "Navigated Vendor Contract Renegotiation"
        assert data["tags"] == ["negotiation", "vendor-management"]

    @pytest.mark.asyncio
    async def test_get_story_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test getting a STAR story without authentication."""
        story = _create_star_story(db, test_profile.id)
        response = await client.get(f"/api/star-stories/{story.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_story_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a non-existent STAR story."""
        response = await client.get("/api/star-stories/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestStarStoryUpdate:
    """Tests for updating STAR stories."""

    @pytest.mark.asyncio
    async def test_update_story_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating all fields of a STAR story."""
        story = _create_star_story(db, test_profile.id)

        update_data = {
            "title": "Led Cross-Team Migration to Event-Driven Architecture",
            "situation": "Services were tightly coupled causing cascading failures",
            "task": "Design and implement an event-driven communication layer",
            "action": "Introduced Kafka-based event bus with schema registry and dead-letter queues",
            "result": "Reduced inter-service failures by 92% and improved system resilience",
            "tags": ["architecture", "kafka", "reliability"],
        }
        response = await client.put(
            f"/api/star-stories/{story.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["situation"] == update_data["situation"]
        assert data["tags"] == update_data["tags"]

    @pytest.mark.asyncio
    async def test_update_story_partial(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating only a subset of fields leaves other fields unchanged."""
        story = _create_star_story(
            db, test_profile.id,
            title="Original Title",
            situation="Original situation description",
        )

        response = await client.put(
            f"/api/star-stories/{story.id}",
            json={"title": "Updated Title Only"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title Only"
        assert data["situation"] == "Original situation description"

    @pytest.mark.asyncio
    async def test_update_story_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test updating a STAR story without authentication."""
        story = _create_star_story(db, test_profile.id)
        response = await client.put(
            f"/api/star-stories/{story.id}",
            json={"title": "Unauthorized Update"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_story_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating a non-existent STAR story."""
        response = await client.put(
            "/api/star-stories/99999",
            json={"title": "Ghost Story"},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_story_clear_optional_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test clearing optional fields by setting them to None."""
        story = _create_star_story(
            db, test_profile.id,
            situation="Detailed situation",
            task="Specific task",
        )

        response = await client.put(
            f"/api/star-stories/{story.id}",
            json={"situation": None, "task": None},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["situation"] is None
        assert data["task"] is None


class TestStarStoryDelete:
    """Tests for deleting STAR stories."""

    @pytest.mark.asyncio
    async def test_delete_story_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful STAR story deletion."""
        story = _create_star_story(db, test_profile.id)
        story_id = story.id

        response = await client.delete(
            f"/api/star-stories/{story_id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it is deleted
        get_response = await client.get(
            f"/api/star-stories/{story_id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_story_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test deleting a STAR story without authentication."""
        story = _create_star_story(db, test_profile.id)
        response = await client.delete(f"/api/star-stories/{story.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_story_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test deleting a non-existent STAR story."""
        response = await client.delete("/api/star-stories/99999", headers=auth_headers)
        assert response.status_code == 404


class TestStarStoryIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_read_other_users_story(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot access another user's STAR story."""
        story = _create_star_story(
            db, test_profile.id, title="Confidential Story About Performance Review"
        )

        response = await client.get(
            f"/api/star-stories/{story.id}", headers=admin_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_story(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot update another user's STAR story."""
        story = _create_star_story(db, test_profile.id)

        response = await client.put(
            f"/api/star-stories/{story.id}",
            json={"title": "Hijacked Title"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_story(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot delete another user's STAR story."""
        story = _create_star_story(db, test_profile.id)

        response = await client.delete(
            f"/api/star-stories/{story.id}", headers=admin_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_only_sees_own_stories(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
        auth_headers: dict,
    ):
        """Test that listing STAR stories only returns the user's own entries."""
        _create_star_story(db, test_profile.id, title="Test User's Leadership Story")

        # Admin lists stories - should see nothing
        response = await client.get("/api/star-stories", headers=admin_auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Test user lists stories - should see their own
        response = await client.get("/api/star-stories", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestStarStoryEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_story_with_special_characters(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story with special characters."""
        story_data = {
            "title": "Resolved O'Brien & Partners' API <Integration> Issue",
            "situation": "The client's API used non-standard headers: X-Custom-Auth=\"token123\"",
            "action": "Wrote adapter layer handling edge cases: null bytes, & ampersands, 'quotes'",
        }
        response = await client.post("/api/star-stories", json=story_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == story_data["title"]
        assert data["situation"] == story_data["situation"]

    @pytest.mark.asyncio
    async def test_story_with_very_long_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story with very long text fields."""
        long_text = "Implemented comprehensive monitoring across the entire platform. " * 200
        story_data = {
            "title": "Built Enterprise Observability Platform",
            "situation": long_text,
            "task": long_text,
            "action": long_text,
            "result": long_text,
        }
        response = await client.post("/api/star-stories", json=story_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert len(data["situation"]) == len(long_text)

    @pytest.mark.asyncio
    async def test_story_with_unicode_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story with unicode and multilingual content."""
        story_data = {
            "title": "Launched Multilingual Support for APAC Markets",
            "situation": "Users in Japan (\u65e5\u672c), Korea (\ud55c\uad6d), and China (\u4e2d\u56fd) had no localized experience",
            "result": "Increased APAC user engagement by 65% \u2014 \u2705 mission accomplished",
        }
        response = await client.post("/api/star-stories", json=story_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "\u65e5\u672c" in data["situation"]
        assert "\u2705" in data["result"]

    @pytest.mark.asyncio
    async def test_story_with_empty_optional_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a STAR story where optional fields are explicitly null."""
        story_data = {
            "title": "Drove Adoption of Pair Programming Practice",
            "situation": None,
            "task": None,
            "action": None,
            "result": None,
            "tags": None,
        }
        response = await client.post("/api/star-stories", json=story_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["situation"] is None
        assert data["tags"] is None

    @pytest.mark.asyncio
    async def test_story_timestamps_present(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that created and updated timestamps are populated on new stories."""
        story_data = {"title": "Established On-Call Rotation Framework"}
        response = await client.post("/api/star-stories", json=story_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
