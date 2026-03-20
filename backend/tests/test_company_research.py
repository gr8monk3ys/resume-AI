"""
Tests for company research endpoints.

Tests:
- CRUD operations for company research (create, read, list, update, delete)
- Search filtering
- User data isolation (can't access others' research)
- Validation and error handling
- Edge cases (special characters, unicode, complex checklists)
"""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.company_research import CompanyResearch
from app.models.profile import Profile
from app.models.user import User


def _create_company_research(
    db: Session,
    profile_id: int,
    company_name: str = "Stripe",
    talking_points: list | None = None,
    notes: str | None = "Global payments infrastructure company founded in 2010",
    checklist: list | None = None,
) -> CompanyResearch:
    """Helper to create a company research entry directly via ORM."""
    entry = CompanyResearch(
        profile_id=profile_id,
        company_name=company_name,
        talking_points=json.dumps(talking_points) if talking_points is not None else None,
        notes=notes,
        checklist=json.dumps(checklist) if checklist is not None else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


class TestCompanyResearchList:
    """Tests for listing company research entries."""

    @pytest.mark.asyncio
    async def test_list_research_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing company research when none exist."""
        response = await client.get("/api/company-research", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_list_research_with_items(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing company research when entries exist."""
        entry = _create_company_research(db, test_profile.id)

        response = await client.get("/api/company-research", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company_name"] == entry.company_name
        assert data[0]["id"] == entry.id

    @pytest.mark.asyncio
    async def test_list_research_multiple_ordered_by_created_at_desc(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that multiple entries are returned in reverse chronological order."""
        _create_company_research(db, test_profile.id, company_name="Google")
        _create_company_research(db, test_profile.id, company_name="Netflix")
        _create_company_research(db, test_profile.id, company_name="Datadog")

        response = await client.get("/api/company-research", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Most recently created should be first (desc order)
        assert data[0]["company_name"] == "Datadog"

    @pytest.mark.asyncio
    async def test_list_research_unauthorized(self, client: AsyncClient, db: Session):
        """Test listing company research without authentication."""
        response = await client.get("/api/company-research")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_research_search_by_company_name(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching research entries by company name."""
        _create_company_research(db, test_profile.id, company_name="Cloudflare")
        _create_company_research(db, test_profile.id, company_name="Snowflake")

        response = await client.get(
            "/api/company-research", params={"search": "cloud"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company_name"] == "Cloudflare"


class TestCompanyResearchCreate:
    """Tests for creating company research entries."""

    @pytest.mark.asyncio
    async def test_create_research_minimal_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a company research entry with only the required field."""
        research_data = {"company_name": "Vercel"}
        response = await client.post(
            "/api/company-research", json=research_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "Vercel"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["profile_id"] == test_profile.id
        assert data["talking_points"] is None
        assert data["notes"] is None
        assert data["checklist"] is None

    @pytest.mark.asyncio
    async def test_create_research_all_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a company research entry with all fields populated."""
        research_data = {
            "company_name": "Anthropic",
            "talking_points": [
                "Pioneer in AI safety research",
                "Developed Constitutional AI alignment technique",
                "Series C funding valued at $18B",
            ],
            "notes": "Known for thoughtful approach to AI development. Strong engineering culture with emphasis on research rigor.",
            "checklist": [
                {"text": "Review recent publications on Constitutional AI", "done": True},
                {"text": "Prepare questions about safety evaluation methodology", "done": False},
                {"text": "Research the Claude model family roadmap", "done": False},
            ],
        }
        response = await client.post(
            "/api/company-research", json=research_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "Anthropic"
        assert len(data["talking_points"]) == 3
        assert data["talking_points"][0] == "Pioneer in AI safety research"
        assert data["notes"].startswith("Known for thoughtful approach")
        assert len(data["checklist"]) == 3
        assert data["checklist"][0]["text"] == "Review recent publications on Constitutional AI"
        assert data["checklist"][0]["done"] is True
        assert data["checklist"][1]["done"] is False

    @pytest.mark.asyncio
    async def test_create_research_unauthorized(self, client: AsyncClient, db: Session):
        """Test creating a company research entry without authentication."""
        response = await client.post(
            "/api/company-research",
            json={"company_name": "Unauthorized Corp"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_research_missing_required_field(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a company research entry without the required company_name."""
        response = await client.post(
            "/api/company-research",
            json={"notes": "Some notes without a company name"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_research_company_name_too_long(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating a company research entry with company name exceeding 255 characters."""
        response = await client.post(
            "/api/company-research",
            json={"company_name": "X" * 256},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestCompanyResearchGet:
    """Tests for reading individual company research entries."""

    @pytest.mark.asyncio
    async def test_get_research_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a specific company research entry by ID."""
        entry = _create_company_research(
            db,
            test_profile.id,
            company_name="Figma",
            talking_points=["Collaborative design tool", "Acquired by Adobe then deal unwound"],
        )

        response = await client.get(f"/api/company-research/{entry.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry.id
        assert data["company_name"] == "Figma"
        assert len(data["talking_points"]) == 2

    @pytest.mark.asyncio
    async def test_get_research_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test getting a company research entry without authentication."""
        entry = _create_company_research(db, test_profile.id)
        response = await client.get(f"/api/company-research/{entry.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_research_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a non-existent company research entry."""
        response = await client.get("/api/company-research/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCompanyResearchUpdate:
    """Tests for updating company research entries."""

    @pytest.mark.asyncio
    async def test_update_research_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating all fields of a company research entry."""
        entry = _create_company_research(db, test_profile.id, company_name="Notion")

        update_data = {
            "company_name": "Notion Labs",
            "talking_points": ["All-in-one workspace", "Strong template ecosystem"],
            "notes": "Recently expanded into enterprise market with Notion AI features",
        }
        response = await client.put(
            f"/api/company-research/{entry.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Notion Labs"
        assert data["talking_points"] == ["All-in-one workspace", "Strong template ecosystem"]
        assert "enterprise market" in data["notes"]

    @pytest.mark.asyncio
    async def test_update_research_partial(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating only a subset of fields leaves other fields unchanged."""
        entry = _create_company_research(
            db,
            test_profile.id,
            company_name="Linear",
            notes="Issue tracking tool focused on speed",
        )

        response = await client.put(
            f"/api/company-research/{entry.id}",
            json={"notes": "Fast, opinionated project management for engineering teams"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Linear"
        assert data["notes"] == "Fast, opinionated project management for engineering teams"

    @pytest.mark.asyncio
    async def test_update_research_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test updating a company research entry without authentication."""
        entry = _create_company_research(db, test_profile.id)
        response = await client.put(
            f"/api/company-research/{entry.id}",
            json={"company_name": "Unauthorized Update"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_research_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating a non-existent company research entry."""
        response = await client.put(
            "/api/company-research/99999",
            json={"company_name": "Ghost Company"},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_research_checklist(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating the checklist field specifically."""
        entry = _create_company_research(
            db,
            test_profile.id,
            company_name="Databricks",
            checklist=[{"text": "Review lakehouse architecture whitepaper", "done": False}],
        )

        updated_checklist = [
            {"text": "Review lakehouse architecture whitepaper", "done": True},
            {"text": "Understand Unity Catalog governance features", "done": False},
            {"text": "Prepare questions about Delta Live Tables", "done": False},
        ]
        response = await client.put(
            f"/api/company-research/{entry.id}",
            json={"checklist": updated_checklist},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["checklist"]) == 3
        assert data["checklist"][0]["done"] is True
        assert data["checklist"][2]["text"] == "Prepare questions about Delta Live Tables"

    @pytest.mark.asyncio
    async def test_update_research_clear_optional_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test clearing optional fields by setting them to None."""
        entry = _create_company_research(
            db,
            test_profile.id,
            company_name="Palantir",
            notes="Government and commercial data analytics",
        )

        response = await client.put(
            f"/api/company-research/{entry.id}",
            json={"notes": None},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] is None
        assert data["company_name"] == "Palantir"


class TestCompanyResearchDelete:
    """Tests for deleting company research entries."""

    @pytest.mark.asyncio
    async def test_delete_research_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful company research deletion."""
        entry = _create_company_research(db, test_profile.id, company_name="WeWork")
        entry_id = entry.id

        response = await client.delete(f"/api/company-research/{entry_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it is deleted
        get_response = await client.get(f"/api/company-research/{entry_id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_research_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test deleting a company research entry without authentication."""
        entry = _create_company_research(db, test_profile.id)
        response = await client.delete(f"/api/company-research/{entry.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_research_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test deleting a non-existent company research entry."""
        response = await client.delete("/api/company-research/99999", headers=auth_headers)
        assert response.status_code == 404


class TestCompanyResearchIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_read_other_users_research(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot access another user's research entry."""
        entry = _create_company_research(
            db, test_profile.id, company_name="Confidential Target Acquisition Corp"
        )

        response = await client.get(f"/api/company-research/{entry.id}", headers=admin_auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_research(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot update another user's research entry."""
        entry = _create_company_research(db, test_profile.id)

        response = await client.put(
            f"/api/company-research/{entry.id}",
            json={"company_name": "Hijacked Company"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_research(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot delete another user's research entry."""
        entry = _create_company_research(db, test_profile.id)

        response = await client.delete(
            f"/api/company-research/{entry.id}", headers=admin_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_only_sees_own_research(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
        auth_headers: dict,
    ):
        """Test that listing research only returns the user's own entries."""
        _create_company_research(db, test_profile.id, company_name="Test User's Target Company")

        # Admin lists research - should see nothing
        response = await client.get("/api/company-research", headers=admin_auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Test user lists research - should see their own
        response = await client.get("/api/company-research", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestCompanyResearchEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_research_with_special_characters(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating research with special characters in company name and notes."""
        research_data = {
            "company_name": "McKinsey & Company",
            "notes": "Known for the 7-S framework. Revenue > $15B. Offices in 130+ cities.",
        }
        response = await client.post(
            "/api/company-research", json=research_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "McKinsey & Company"
        assert ">" in data["notes"]

    @pytest.mark.asyncio
    async def test_research_with_unicode_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating research with unicode and multilingual content."""
        research_data = {
            "company_name": "Rakuten (\u697d\u5929\u682a\u5f0f\u4f1a\u793e)",
            "notes": "Japanese e-commerce giant. \u201cIchi-go ichi-e\u201d (\u4e00\u671f\u4e00\u4f1a) culture of treasuring encounters.",
            "talking_points": [
                "Global expansion strategy through acquisitions",
                "Rakuten Mobile 5G rollout \u2014 bold infrastructure play",
            ],
        }
        response = await client.post(
            "/api/company-research", json=research_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert "\u697d\u5929" in data["company_name"]
        assert "\u4e00\u671f\u4e00\u4f1a" in data["notes"]

    @pytest.mark.asyncio
    async def test_research_with_empty_optional_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating research where optional fields are explicitly null."""
        research_data = {
            "company_name": "Minimal Research Entry Inc",
            "talking_points": None,
            "notes": None,
            "checklist": None,
        }
        response = await client.post(
            "/api/company-research", json=research_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["talking_points"] is None
        assert data["notes"] is None
        assert data["checklist"] is None

    @pytest.mark.asyncio
    async def test_research_with_complex_checklist(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating research with a large, detailed checklist."""
        checklist = [
            {"text": "Review 10-K annual report for revenue trends", "done": True},
            {"text": "Analyze Glassdoor reviews for engineering culture signals", "done": True},
            {"text": "Read CEO's latest shareholder letter", "done": False},
            {"text": "Map organizational structure from LinkedIn", "done": False},
            {"text": "Identify key competitors and market positioning", "done": False},
            {"text": "Review recent press releases for product launches", "done": True},
            {"text": "Prepare 3 insightful questions for each interviewer", "done": False},
        ]
        research_data = {
            "company_name": "Confluent",
            "checklist": checklist,
        }
        response = await client.post(
            "/api/company-research", json=research_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["checklist"]) == 7
        done_count = sum(1 for item in data["checklist"] if item["done"])
        assert done_count == 3
