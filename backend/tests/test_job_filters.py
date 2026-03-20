"""
Tests for job filters endpoints.

Tests cover:
- Company filter CRUD operations
- Keyword filter CRUD operations
- Application question CRUD operations
- Job check endpoint (filter matching)
- Import defaults
- Validation and error handling
- User data isolation
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.job_filters import (
    ApplicationQuestion,
    CompanyFilter,
    CompanyFilterType,
    KeywordAppliesTo,
    KeywordFilter,
    KeywordFilterType,
)
from app.models.user import User


class TestListCompanyFilters:
    """Tests for GET /api/filters/companies"""

    @pytest.mark.asyncio
    async def test_list_company_filters_empty(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test listing company filters when none exist."""
        response = await client.get("/api/filters/companies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_company_filters_with_data(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test listing company filters when they exist."""
        cf = CompanyFilter(
            user_id=test_user.id,
            company_name="Bad Corp",
            filter_type=CompanyFilterType.BLACKLIST,
            reason="Poor culture",
        )
        db.add(cf)
        db.commit()

        response = await client.get("/api/filters/companies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["company_name"] == "Bad Corp"
        assert data["items"][0]["filter_type"] == "blacklist"

    @pytest.mark.asyncio
    async def test_list_company_filters_filter_by_type(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test filtering company filters by type."""
        db.add(
            CompanyFilter(
                user_id=test_user.id,
                company_name="Bad Corp",
                filter_type=CompanyFilterType.BLACKLIST,
            )
        )
        db.add(
            CompanyFilter(
                user_id=test_user.id,
                company_name="Good Corp",
                filter_type=CompanyFilterType.WHITELIST,
            )
        )
        db.commit()

        response = await client.get(
            "/api/filters/companies",
            headers=auth_headers,
            params={"filter_type": "whitelist"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["company_name"] == "Good Corp"

    @pytest.mark.asyncio
    async def test_list_company_filters_search(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test searching company filters by name."""
        db.add(
            CompanyFilter(
                user_id=test_user.id,
                company_name="Google",
                filter_type=CompanyFilterType.WHITELIST,
            )
        )
        db.add(
            CompanyFilter(
                user_id=test_user.id,
                company_name="Meta",
                filter_type=CompanyFilterType.BLACKLIST,
            )
        )
        db.commit()

        response = await client.get(
            "/api/filters/companies",
            headers=auth_headers,
            params={"search": "Google"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["company_name"] == "Google"

    @pytest.mark.asyncio
    async def test_list_company_filters_unauthorized(self, client: AsyncClient):
        """Test listing company filters without authentication."""
        response = await client.get("/api/filters/companies")
        assert response.status_code == 401


class TestCreateCompanyFilter:
    """Tests for POST /api/filters/companies"""

    @pytest.mark.asyncio
    async def test_create_company_filter_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful company filter creation."""
        filter_data = {
            "company_name": "Bad Corp",
            "filter_type": "blacklist",
            "reason": "Poor reviews",
        }
        response = await client.post(
            "/api/filters/companies", json=filter_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "Bad Corp"
        assert data["filter_type"] == "blacklist"
        assert data["reason"] == "Poor reviews"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_company_filter_whitelist(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test creating a whitelist company filter."""
        filter_data = {
            "company_name": "Dream Company",
            "filter_type": "whitelist",
        }
        response = await client.post(
            "/api/filters/companies", json=filter_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filter_type"] == "whitelist"

    @pytest.mark.asyncio
    async def test_create_company_filter_duplicate(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test creating a duplicate company filter returns 409."""
        filter_data = {
            "company_name": "Duplicate Corp",
            "filter_type": "blacklist",
        }
        # First creation should succeed
        response = await client.post(
            "/api/filters/companies", json=filter_data, headers=auth_headers
        )
        assert response.status_code == 201

        # Second creation should fail with 409
        response = await client.post(
            "/api/filters/companies", json=filter_data, headers=auth_headers
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_company_filter_unauthorized(self, client: AsyncClient):
        """Test creating company filter without authentication."""
        response = await client.post(
            "/api/filters/companies",
            json={"company_name": "Test", "filter_type": "blacklist"},
        )
        assert response.status_code == 401


class TestGetCompanyFilter:
    """Tests for GET /api/filters/companies/{filter_id}"""

    @pytest.mark.asyncio
    async def test_get_company_filter_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test getting a specific company filter."""
        cf = CompanyFilter(
            user_id=test_user.id,
            company_name="Test Corp",
            filter_type=CompanyFilterType.BLACKLIST,
        )
        db.add(cf)
        db.commit()
        db.refresh(cf)

        response = await client.get(
            f"/api/filters/companies/{cf.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == cf.id
        assert data["company_name"] == "Test Corp"

    @pytest.mark.asyncio
    async def test_get_company_filter_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test getting a non-existent company filter."""
        response = await client.get(
            "/api/filters/companies/99999", headers=auth_headers
        )
        assert response.status_code == 404


class TestDeleteCompanyFilter:
    """Tests for DELETE /api/filters/companies/{filter_id}"""

    @pytest.mark.asyncio
    async def test_delete_company_filter_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful company filter deletion."""
        cf = CompanyFilter(
            user_id=test_user.id,
            company_name="Delete Me",
            filter_type=CompanyFilterType.BLACKLIST,
        )
        db.add(cf)
        db.commit()
        db.refresh(cf)

        response = await client.delete(
            f"/api/filters/companies/{cf.id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's deleted
        deleted = db.query(CompanyFilter).filter(CompanyFilter.id == cf.id).first()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_company_filter_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test deleting a non-existent company filter."""
        response = await client.delete(
            "/api/filters/companies/99999", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_all_company_filters(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test deleting all company filters for a user."""
        for i in range(3):
            db.add(
                CompanyFilter(
                    user_id=test_user.id,
                    company_name=f"Company {i}",
                    filter_type=CompanyFilterType.BLACKLIST,
                )
            )
        db.commit()

        response = await client.delete("/api/filters/companies", headers=auth_headers)
        assert response.status_code == 204

        # Verify all are deleted
        remaining = (
            db.query(CompanyFilter)
            .filter(CompanyFilter.user_id == test_user.id)
            .count()
        )
        assert remaining == 0


class TestKeywordFilters:
    """Tests for keyword filter CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_keyword_filters_empty(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test listing keyword filters when none exist."""
        response = await client.get("/api/filters/keywords", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_keyword_filter_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful keyword filter creation."""
        filter_data = {
            "keyword": "unpaid",
            "filter_type": "exclude",
            "applies_to": "both",
        }
        response = await client.post(
            "/api/filters/keywords", json=filter_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["keyword"] == "unpaid"
        assert data["filter_type"] == "exclude"
        assert data["applies_to"] == "both"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_keyword_filter_require(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test creating a require keyword filter."""
        filter_data = {
            "keyword": "python",
            "filter_type": "require",
            "applies_to": "title",
        }
        response = await client.post(
            "/api/filters/keywords", json=filter_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filter_type"] == "require"
        assert data["applies_to"] == "title"

    @pytest.mark.asyncio
    async def test_create_keyword_filter_duplicate(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test creating a duplicate keyword filter returns 409."""
        filter_data = {"keyword": "internship", "filter_type": "exclude"}
        response = await client.post(
            "/api/filters/keywords", json=filter_data, headers=auth_headers
        )
        assert response.status_code == 201

        response = await client.post(
            "/api/filters/keywords", json=filter_data, headers=auth_headers
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_get_keyword_filter_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test getting a specific keyword filter."""
        kf = KeywordFilter(
            user_id=test_user.id,
            keyword="remote",
            filter_type=KeywordFilterType.REQUIRE,
            applies_to=KeywordAppliesTo.BOTH,
        )
        db.add(kf)
        db.commit()
        db.refresh(kf)

        response = await client.get(
            f"/api/filters/keywords/{kf.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["keyword"] == "remote"

    @pytest.mark.asyncio
    async def test_get_keyword_filter_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test getting a non-existent keyword filter."""
        response = await client.get(
            "/api/filters/keywords/99999", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_keyword_filter_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful keyword filter deletion."""
        kf = KeywordFilter(
            user_id=test_user.id,
            keyword="delete-me",
            filter_type=KeywordFilterType.EXCLUDE,
            applies_to=KeywordAppliesTo.BOTH,
        )
        db.add(kf)
        db.commit()
        db.refresh(kf)

        response = await client.delete(
            f"/api/filters/keywords/{kf.id}", headers=auth_headers
        )
        assert response.status_code == 204

        deleted = db.query(KeywordFilter).filter(KeywordFilter.id == kf.id).first()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_keyword_filter_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test deleting a non-existent keyword filter."""
        response = await client.delete(
            "/api/filters/keywords/99999", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_keyword_filters_filter_by_type(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test filtering keyword filters by type."""
        db.add(
            KeywordFilter(
                user_id=test_user.id,
                keyword="unpaid",
                filter_type=KeywordFilterType.EXCLUDE,
                applies_to=KeywordAppliesTo.BOTH,
            )
        )
        db.add(
            KeywordFilter(
                user_id=test_user.id,
                keyword="python",
                filter_type=KeywordFilterType.REQUIRE,
                applies_to=KeywordAppliesTo.TITLE,
            )
        )
        db.commit()

        response = await client.get(
            "/api/filters/keywords",
            headers=auth_headers,
            params={"filter_type": "require"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["keyword"] == "python"

    @pytest.mark.asyncio
    async def test_list_keyword_filters_unauthorized(self, client: AsyncClient):
        """Test listing keyword filters without authentication."""
        response = await client.get("/api/filters/keywords")
        assert response.status_code == 401


class TestApplicationQuestions:
    """Tests for application question CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_questions_empty(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test listing questions when none exist."""
        response = await client.get("/api/filters/questions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_question_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful question template creation."""
        question_data = {
            "question_pattern": "years of experience",
            "answer": "5 years",
            "question_type": "text",
            "category": "experience",
        }
        response = await client.post(
            "/api/filters/questions", json=question_data, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["question_pattern"] == "years of experience"
        assert data["answer"] == "5 years"
        assert data["question_type"] == "text"
        assert data["category"] == "experience"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_question_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test getting a specific question."""
        q = ApplicationQuestion(
            user_id=test_user.id,
            question_pattern="salary expectations",
            answer="$120,000",
            question_type="text",
            category="compensation",
        )
        db.add(q)
        db.commit()
        db.refresh(q)

        response = await client.get(
            f"/api/filters/questions/{q.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question_pattern"] == "salary expectations"
        assert data["answer"] == "$120,000"

    @pytest.mark.asyncio
    async def test_get_question_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test getting a non-existent question."""
        response = await client.get(
            "/api/filters/questions/99999", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_question_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful question update."""
        q = ApplicationQuestion(
            user_id=test_user.id,
            question_pattern="willing to relocate",
            answer="No",
            question_type="boolean",
            category="relocation",
        )
        db.add(q)
        db.commit()
        db.refresh(q)

        update_data = {"answer": "Yes", "category": "preferences"}
        response = await client.put(
            f"/api/filters/questions/{q.id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Yes"
        assert data["category"] == "preferences"
        # Original fields should remain unchanged
        assert data["question_pattern"] == "willing to relocate"

    @pytest.mark.asyncio
    async def test_update_question_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test updating a non-existent question."""
        response = await client.put(
            "/api/filters/questions/99999",
            json={"answer": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_question_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful question deletion."""
        q = ApplicationQuestion(
            user_id=test_user.id,
            question_pattern="delete me",
            answer="goodbye",
            question_type="text",
        )
        db.add(q)
        db.commit()
        db.refresh(q)

        response = await client.delete(
            f"/api/filters/questions/{q.id}", headers=auth_headers
        )
        assert response.status_code == 204

        deleted = (
            db.query(ApplicationQuestion)
            .filter(ApplicationQuestion.id == q.id)
            .first()
        )
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_question_not_found(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test deleting a non-existent question."""
        response = await client.delete(
            "/api/filters/questions/99999", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_questions_filter_by_category(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test filtering questions by category."""
        db.add(
            ApplicationQuestion(
                user_id=test_user.id,
                question_pattern="experience",
                answer="5 years",
                question_type="text",
                category="experience",
            )
        )
        db.add(
            ApplicationQuestion(
                user_id=test_user.id,
                question_pattern="salary",
                answer="$100k",
                question_type="text",
                category="compensation",
            )
        )
        db.commit()

        response = await client.get(
            "/api/filters/questions",
            headers=auth_headers,
            params={"category": "compensation"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "compensation"

    @pytest.mark.asyncio
    async def test_list_questions_unauthorized(self, client: AsyncClient):
        """Test listing questions without authentication."""
        response = await client.get("/api/filters/questions")
        assert response.status_code == 401


class TestJobCheck:
    """Tests for GET and POST /api/filters/check-job"""

    @pytest.mark.asyncio
    async def test_check_job_no_filters(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test checking a job when no filters exist (should pass)."""
        response = await client.get(
            "/api/filters/check-job",
            headers=auth_headers,
            params={"title": "Software Engineer", "company": "Google"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passes_filters"] is True

    @pytest.mark.asyncio
    async def test_check_job_blacklisted_company(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test checking a job with a blacklisted company."""
        db.add(
            CompanyFilter(
                user_id=test_user.id,
                company_name="Evil Corp",
                filter_type=CompanyFilterType.BLACKLIST,
                reason="Unethical practices",
            )
        )
        db.commit()

        response = await client.get(
            "/api/filters/check-job",
            headers=auth_headers,
            params={"title": "Developer", "company": "Evil Corp"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passes_filters"] is False
        assert data["company_filter_match"] is not None
        assert data["company_filter_match"]["action"] == "block"

    @pytest.mark.asyncio
    async def test_check_job_whitelisted_company(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test checking a job with a whitelisted company."""
        db.add(
            CompanyFilter(
                user_id=test_user.id,
                company_name="Dream Corp",
                filter_type=CompanyFilterType.WHITELIST,
            )
        )
        db.commit()

        response = await client.get(
            "/api/filters/check-job",
            headers=auth_headers,
            params={"title": "Developer", "company": "Dream Corp"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passes_filters"] is True
        assert data["company_filter_match"] is not None
        assert data["company_filter_match"]["action"] == "allow"

    @pytest.mark.asyncio
    async def test_check_job_excluded_keyword(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test checking a job with an excluded keyword in the title."""
        db.add(
            KeywordFilter(
                user_id=test_user.id,
                keyword="unpaid",
                filter_type=KeywordFilterType.EXCLUDE,
                applies_to=KeywordAppliesTo.BOTH,
            )
        )
        db.commit()

        response = await client.get(
            "/api/filters/check-job",
            headers=auth_headers,
            params={
                "title": "Unpaid Internship",
                "company": "Some Corp",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passes_filters"] is False
        assert len(data["keyword_matches"]) >= 1

    @pytest.mark.asyncio
    async def test_check_job_post_endpoint(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test the POST version of check-job for longer descriptions."""
        db.add(
            KeywordFilter(
                user_id=test_user.id,
                keyword="machine learning",
                filter_type=KeywordFilterType.REQUIRE,
                applies_to=KeywordAppliesTo.DESCRIPTION,
            )
        )
        db.commit()

        request_data = {
            "title": "Data Scientist",
            "company": "AI Corp",
            "description": "We need someone skilled in machine learning and NLP.",
        }
        response = await client.post(
            "/api/filters/check-job",
            json=request_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passes_filters"] is True

    @pytest.mark.asyncio
    async def test_check_job_required_keyword_missing(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test checking a job where a required keyword is missing."""
        db.add(
            KeywordFilter(
                user_id=test_user.id,
                keyword="python",
                filter_type=KeywordFilterType.REQUIRE,
                applies_to=KeywordAppliesTo.BOTH,
            )
        )
        db.commit()

        response = await client.get(
            "/api/filters/check-job",
            headers=auth_headers,
            params={
                "title": "Java Developer",
                "company": "Java Corp",
                "description": "Looking for Java experts",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passes_filters"] is False

    @pytest.mark.asyncio
    async def test_check_job_unauthorized(self, client: AsyncClient):
        """Test checking a job without authentication."""
        response = await client.get(
            "/api/filters/check-job",
            params={"title": "Developer", "company": "Test"},
        )
        assert response.status_code == 401


class TestImportDefaults:
    """Tests for POST /api/filters/import-defaults"""

    @pytest.mark.asyncio
    async def test_import_defaults_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test importing default question templates."""
        response = await client.post(
            "/api/filters/import-defaults", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["imported_count"] > 0
        assert data["skipped_count"] == 0

    @pytest.mark.asyncio
    async def test_import_defaults_skip_existing(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that importing defaults skips existing templates."""
        # Import once
        await client.post("/api/filters/import-defaults", headers=auth_headers)

        # Import again - should skip all
        response = await client.post(
            "/api/filters/import-defaults", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skipped_count"] > 0
        assert data["imported_count"] == 0

    @pytest.mark.asyncio
    async def test_import_defaults_overwrite(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that importing defaults with overwrite replaces existing."""
        # Import once
        await client.post("/api/filters/import-defaults", headers=auth_headers)

        # Import again with overwrite
        response = await client.post(
            "/api/filters/import-defaults",
            headers=auth_headers,
            params={"overwrite": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] > 0
        assert data["skipped_count"] == 0

    @pytest.mark.asyncio
    async def test_import_defaults_unauthorized(self, client: AsyncClient):
        """Test importing defaults without authentication."""
        response = await client.post("/api/filters/import-defaults")
        assert response.status_code == 401


class TestFilterIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_see_other_users_company_filters(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that users can only see their own company filters."""
        from app.middleware.auth import get_password_hash

        # Create another user with a filter
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=get_password_hash("password123"),
            is_active=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        other_filter = CompanyFilter(
            user_id=other_user.id,
            company_name="Secret Corp",
            filter_type=CompanyFilterType.BLACKLIST,
        )
        db.add(other_filter)
        db.commit()
        db.refresh(other_filter)

        # Try to access other user's filter
        response = await client.get(
            f"/api/filters/companies/{other_filter.id}", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_keyword_filter(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that users cannot delete other users' keyword filters."""
        from app.middleware.auth import get_password_hash

        other_user = User(
            username="otheruser3",
            email="other3@example.com",
            password_hash=get_password_hash("password123"),
            is_active=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        other_filter = KeywordFilter(
            user_id=other_user.id,
            keyword="private",
            filter_type=KeywordFilterType.EXCLUDE,
            applies_to=KeywordAppliesTo.BOTH,
        )
        db.add(other_filter)
        db.commit()
        db.refresh(other_filter)

        response = await client.delete(
            f"/api/filters/keywords/{other_filter.id}", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_questions(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that users cannot access other users' application questions."""
        from app.middleware.auth import get_password_hash

        other_user = User(
            username="otheruser4",
            email="other4@example.com",
            password_hash=get_password_hash("password123"),
            is_active=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        other_question = ApplicationQuestion(
            user_id=other_user.id,
            question_pattern="secret question",
            answer="secret answer",
            question_type="text",
        )
        db.add(other_question)
        db.commit()
        db.refresh(other_question)

        response = await client.get(
            f"/api/filters/questions/{other_question.id}", headers=auth_headers
        )
        assert response.status_code == 404
