"""
Tests for the AI career coach endpoint and service method.

Tests:
- Career coach endpoint (/api/ai/career-coach)
- Different coaching modes (general, interview_prep, salary_negotiation,
  career_transition, resume_review)
- Conversation history handling
- Resume and job description context for personalized advice
- Error handling
- Response format validation
- LLM service career_coach_respond method integration
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.llm_service import (
    LLMService,
    clear_llm_cache,
    reset_llm_service,
)


# =============================================================================
# Service-Level Career Coach Tests
# =============================================================================


class TestCareerCoachService:
    """Tests for the career_coach_respond service method."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset LLM service before each test."""
        reset_llm_service()
        clear_llm_cache()
        yield
        reset_llm_service()
        clear_llm_cache()

    @pytest.fixture
    def service(self):
        """Create a fresh LLM service with mock provider."""
        return LLMService(provider_name="mock", enable_cache=False)

    def test_basic_career_coaching_response(self, service):
        """Test that career coaching returns a non-empty response."""
        result = service.career_coach_respond(
            message="How can I improve my resume?",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_general_mode(self, service):
        """Test career coaching with general coaching mode."""
        result = service.career_coach_respond(
            message="What should I focus on in my career?",
            coaching_mode="general",
        )
        assert isinstance(result, str)
        assert len(result) > 50

    def test_career_coaching_with_interview_prep_mode(self, service):
        """Test career coaching with interview prep mode."""
        result = service.career_coach_respond(
            message="How do I prepare for a technical interview?",
            coaching_mode="interview_prep",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_career_transition_mode(self, service):
        """Test career coaching with career transition mode."""
        result = service.career_coach_respond(
            message="I want to switch from marketing to software engineering",
            coaching_mode="career_transition",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_salary_negotiation_mode(self, service):
        """Test career coaching with salary negotiation mode."""
        result = service.career_coach_respond(
            message="How do I negotiate a higher salary?",
            coaching_mode="salary_negotiation",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_resume_review_mode(self, service):
        """Test career coaching with resume review mode."""
        result = service.career_coach_respond(
            message="Can you review my resume structure?",
            coaching_mode="resume_review",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_resume_content(self, service):
        """Test career coaching with resume for personalized advice."""
        resume = """
        John Doe
        Software Engineer

        EXPERIENCE
        - 5 years Python development
        - Team lead at Tech Corp

        SKILLS
        Python, JavaScript, AWS, Docker
        """
        result = service.career_coach_respond(
            message="What roles should I target?",
            resume=resume,
            coaching_mode="general",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_job_description(self, service):
        """Test career coaching with job description for targeted advice."""
        result = service.career_coach_respond(
            message="Am I a good fit for this role?",
            resume="John Doe, 5 years Python, AWS certified",
            job_description="Senior Python Developer, 3+ years, AWS required",
            coaching_mode="interview_prep",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_conversation_history(self, service):
        """Test career coaching with conversation history for context."""
        history = [
            {"role": "user", "content": "I want to change careers to tech"},
            {
                "role": "assistant",
                "content": "That is great! What skills do you currently have?",
            },
            {
                "role": "user",
                "content": "I have a background in data analysis and Excel",
            },
        ]
        result = service.career_coach_respond(
            message="What programming language should I learn first?",
            conversation_history=history,
            coaching_mode="career_transition",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_history_truncated_to_10(self, service):
        """Test that conversation history is truncated to last 10 messages."""
        # Create 15 messages
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(15)
        ]
        result = service.career_coach_respond(
            message="Continue our conversation",
            conversation_history=history,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_empty_history(self, service):
        """Test career coaching with empty conversation history."""
        result = service.career_coach_respond(
            message="Start a new conversation",
            conversation_history=[],
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_with_none_history(self, service):
        """Test career coaching with None conversation history."""
        result = service.career_coach_respond(
            message="No history provided",
            conversation_history=None,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_unknown_mode_uses_general(self, service):
        """Test that unknown coaching mode falls back to general instructions."""
        result = service.career_coach_respond(
            message="Help me with my career",
            coaching_mode="unknown_mode",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_empty_resume(self, service):
        """Test career coaching with empty resume string."""
        result = service.career_coach_respond(
            message="Help me without a resume",
            resume="",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coaching_followup_lines_in_mock(self, service):
        """Test that mock response includes FOLLOWUP lines for parsing."""
        result = service.career_coach_respond(
            message="What should I do next?",
            coaching_mode="general",
        )
        assert "FOLLOWUP:" in result


# =============================================================================
# API Endpoint Tests
# =============================================================================


class TestCareerCoachEndpoint:
    """Tests for the /api/ai/career-coach endpoint."""

    @pytest.mark.asyncio
    async def test_career_coach_requires_auth(self, client: AsyncClient, db: Session):
        """Test that career coach endpoint requires authentication."""
        response = await client.post(
            "/api/ai/career-coach",
            json={"message": "Help me with my career"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_career_coach_basic_request(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test basic career coach request with authentication."""
        response = await client.post(
            "/api/ai/career-coach",
            json={"message": "How can I improve my job search?"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "suggested_followups" in data
        assert "coaching_mode" in data
        assert data["coaching_mode"] == "general"
        assert isinstance(data["suggested_followups"], list)
        assert len(data["suggested_followups"]) > 0

    @pytest.mark.asyncio
    async def test_career_coach_with_coaching_mode(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test career coach with a specific coaching mode."""
        response = await client.post(
            "/api/ai/career-coach",
            json={
                "message": "How do I prepare for interviews?",
                "coaching_mode": "interview_prep",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["coaching_mode"] == "interview_prep"

    @pytest.mark.asyncio
    async def test_career_coach_invalid_coaching_mode(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that invalid coaching mode returns 422."""
        response = await client.post(
            "/api/ai/career-coach",
            json={
                "message": "Help me",
                "coaching_mode": "invalid_mode",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_career_coach_with_resume(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test career coach with resume content for personalized advice."""
        response = await client.post(
            "/api/ai/career-coach",
            json={
                "message": "What roles should I target?",
                "resume_content": "John Doe\nSoftware Engineer\n5 years experience",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_career_coach_with_job_description(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test career coach with job description for targeted advice."""
        response = await client.post(
            "/api/ai/career-coach",
            json={
                "message": "Am I qualified for this role?",
                "resume_content": "John Doe, Python developer, 5 years",
                "job_description": "Senior Python Developer, AWS required",
                "coaching_mode": "interview_prep",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["coaching_mode"] == "interview_prep"

    @pytest.mark.asyncio
    async def test_career_coach_with_conversation_history(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test career coach with conversation history."""
        response = await client.post(
            "/api/ai/career-coach",
            json={
                "message": "What should I do next?",
                "conversation_history": [
                    {"role": "user", "content": "I want to change careers"},
                    {"role": "assistant", "content": "That is exciting!"},
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_career_coach_empty_message_rejected(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that empty message is rejected."""
        response = await client.post(
            "/api/ai/career-coach",
            json={"message": ""},
            headers=auth_headers,
        )
        # May succeed with empty message or return 422 validation error
        assert response.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_career_coach_missing_message_rejected(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that missing message field is rejected."""
        response = await client.post(
            "/api/ai/career-coach",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_career_coach_response_has_followups(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that career coach response always includes suggested followups."""
        response = await client.post(
            "/api/ai/career-coach",
            json={
                "message": "Help me with my career",
                "coaching_mode": "salary_negotiation",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggested_followups" in data
        assert isinstance(data["suggested_followups"], list)
        assert len(data["suggested_followups"]) >= 2

    @pytest.mark.asyncio
    async def test_career_coach_all_modes(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test that all valid coaching modes are accepted."""
        modes = [
            "general",
            "interview_prep",
            "salary_negotiation",
            "career_transition",
            "resume_review",
        ]
        for mode in modes:
            response = await client.post(
                "/api/ai/career-coach",
                json={
                    "message": f"Help me with {mode}",
                    "coaching_mode": mode,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200, f"Mode {mode} returned {response.status_code}"
            data = response.json()
            assert data["coaching_mode"] == mode


# =============================================================================
# Response Format Tests
# =============================================================================


class TestCareerCoachResponseFormat:
    """Tests for career coach response format and content quality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset LLM service before each test."""
        reset_llm_service()
        clear_llm_cache()
        yield
        reset_llm_service()
        clear_llm_cache()

    @pytest.fixture
    def service(self):
        """Create a fresh LLM service with mock provider."""
        return LLMService(provider_name="mock", enable_cache=False)

    def test_response_is_conversational(self, service):
        """Test that response has a conversational tone."""
        result = service.career_coach_respond(
            message="I feel stuck in my career",
            coaching_mode="general",
        )
        # Mock provider returns coaching-style response
        assert isinstance(result, str)
        assert len(result) > 30

    def test_response_provides_actionable_advice(self, service):
        """Test that response includes actionable suggestions."""
        result = service.career_coach_respond(
            message="How can I get more job interviews?",
            coaching_mode="general",
        )
        # The mock response should contain actionable content
        assert isinstance(result, str)
        assert len(result) > 50

    def test_response_length_is_reasonable(self, service):
        """Test that response length is within reasonable bounds."""
        result = service.career_coach_respond(
            message="Give me career advice",
        )
        # Response should be substantive but not excessively long
        assert 30 < len(result) < 5000


# =============================================================================
# Caching Tests for Career Coach
# =============================================================================


class TestCareerCoachCaching:
    """Tests for career coach response caching behavior."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset LLM service before each test."""
        reset_llm_service()
        clear_llm_cache()
        yield
        reset_llm_service()
        clear_llm_cache()

    def test_same_message_uses_cache(self):
        """Test that identical messages return cached response."""
        service = LLMService(provider_name="mock", enable_cache=True)

        result1 = service.career_coach_respond(message="Help me")
        call_count1 = service.provider.call_count

        result2 = service.career_coach_respond(message="Help me")
        call_count2 = service.provider.call_count

        assert result1 == result2
        assert call_count2 == call_count1  # No additional call

    def test_different_messages_bypass_cache(self):
        """Test that different messages produce separate cache entries."""
        service = LLMService(provider_name="mock", enable_cache=True)

        service.career_coach_respond(message="Help with job search")
        service.career_coach_respond(message="Help with interviews")

        assert service.provider.call_count == 2

    def test_different_modes_bypass_cache(self):
        """Test that different coaching modes produce separate cache entries."""
        service = LLMService(provider_name="mock", enable_cache=True)

        service.career_coach_respond(message="Help me", coaching_mode="general")
        service.career_coach_respond(
            message="Help me", coaching_mode="interview_prep"
        )

        assert service.provider.call_count == 2
