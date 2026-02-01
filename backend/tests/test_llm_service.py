"""
Tests for the LLM service and multi-provider support.

Tests:
- Provider factory function
- Mock provider responses
- LLM service methods (tailor_resume, generate_cover_letter, etc.)
- Caching behavior
- Error handling
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_service import (
    _PROVIDERS,
    BaseLLMProvider,
    LLMConfigurationError,
    LLMError,
    LLMProviderError,
    LLMService,
    MockProvider,
    clear_llm_cache,
    get_llm_cache_stats,
    get_llm_provider,
    get_llm_service,
    reset_llm_service,
)

# =============================================================================
# Mock Provider Tests
# =============================================================================


class TestMockProvider:
    """Tests for the MockProvider class."""

    def test_mock_provider_creates_successfully(self):
        """Test that MockProvider initializes without API key."""
        provider = MockProvider()
        assert provider.name == "mock"
        assert provider.model == "mock-model"

    def test_mock_provider_tracks_calls(self):
        """Test that MockProvider tracks invocation count."""
        provider = MockProvider()
        assert provider.call_count == 0

        provider.invoke("Test prompt")
        assert provider.call_count == 1

        provider.invoke("Another prompt")
        assert provider.call_count == 2

    def test_mock_provider_stores_last_prompt(self):
        """Test that MockProvider stores the last prompt."""
        provider = MockProvider()
        provider.invoke("My test prompt")
        assert provider.last_prompt == "My test prompt"

    def test_mock_provider_cover_letter_response(self):
        """Test MockProvider returns appropriate cover letter response."""
        provider = MockProvider()
        result = provider.invoke("Generate a cover letter for this position")

        assert "Dear Hiring Manager" in result
        assert len(result) > 50

    def test_mock_provider_tailor_resume_response(self):
        """Test MockProvider returns appropriate tailored resume response."""
        provider = MockProvider()
        result = provider.invoke("Tailor this resume for the job")

        assert "PROFESSIONAL SUMMARY" in result or "EXPERIENCE" in result

    def test_mock_provider_interview_response(self):
        """Test MockProvider returns STAR-formatted interview response."""
        provider = MockProvider()
        result = provider.invoke("Prepare for this interview question")

        assert "Situation" in result
        assert "Task" in result or "Action" in result or "Result" in result

    def test_mock_provider_grammar_response(self):
        """Test MockProvider handles grammar correction prompts."""
        provider = MockProvider()
        result = provider.invoke("Check grammar: The quick brown fox.")

        assert len(result) > 0

    def test_mock_provider_keyword_response(self):
        """Test MockProvider returns keyword suggestions."""
        provider = MockProvider()
        result = provider.invoke("Suggest keywords to add to this resume")

        assert "Add" in result or "Include" in result or "python" in result.lower()

    def test_mock_provider_networking_email_response(self):
        """Test MockProvider returns networking email."""
        provider = MockProvider()
        result = provider.invoke("Write a networking email to reach out")

        assert "Subject:" in result
        assert "Dear" in result

    def test_mock_provider_generic_response(self):
        """Test MockProvider returns generic response for unknown prompts."""
        provider = MockProvider()
        result = provider.invoke("Some random prompt that doesn't match patterns")

        assert "Mock response" in result


# =============================================================================
# Provider Factory Tests
# =============================================================================


class TestProviderFactory:
    """Tests for get_llm_provider factory function."""

    def test_get_mock_provider(self):
        """Test getting mock provider explicitly."""
        provider = get_llm_provider("mock")
        assert isinstance(provider, MockProvider)
        assert provider.name == "mock"

    def test_unknown_provider_raises_error(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_llm_provider("unknown_provider")

        assert "Unknown provider" in str(exc_info.value)
        assert "unknown_provider" in str(exc_info.value)

    def test_provider_registry_contains_expected_providers(self):
        """Test that provider registry has expected providers."""
        expected_providers = ["openai", "anthropic", "google", "ollama", "mock"]
        for provider_name in expected_providers:
            assert provider_name in _PROVIDERS

    def test_custom_model_name(self):
        """Test creating provider with custom model name."""
        provider = get_llm_provider("mock", model_name="custom-model")
        assert provider.model == "custom-model"

    def test_custom_temperature(self):
        """Test creating provider with custom temperature."""
        provider = get_llm_provider("mock", temperature=0.5)
        assert provider._temperature == 0.5


# =============================================================================
# LLM Service Tests
# =============================================================================


class TestLLMService:
    """Tests for the LLMService class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset LLM service and cache before each test."""
        reset_llm_service()
        clear_llm_cache()
        yield
        reset_llm_service()
        clear_llm_cache()

    def test_service_creates_with_mock_provider(self):
        """Test that LLMService creates with mock provider."""
        service = LLMService(provider_name="mock")
        assert service.provider.name == "mock"

    def test_service_singleton(self):
        """Test that get_llm_service returns singleton."""
        service1 = get_llm_service(provider_name="mock")
        service2 = get_llm_service()

        # Should be the same instance
        assert service1 is service2

    def test_reset_service_clears_singleton(self):
        """Test that reset_llm_service clears the singleton."""
        service1 = get_llm_service(provider_name="mock")
        reset_llm_service()
        service2 = get_llm_service(provider_name="mock")

        # Should be different instances
        assert service1 is not service2


class TestLLMServiceMethods:
    """Tests for LLMService methods using mock provider."""

    @pytest.fixture
    def service(self):
        """Create a fresh LLM service with mock provider."""
        reset_llm_service()
        clear_llm_cache()
        return LLMService(provider_name="mock", enable_cache=False)

    def test_correct_grammar(self, service: LLMService):
        """Test grammar correction method."""
        result = service.correct_grammar("This are a test sentance.")
        assert len(result) > 0

    def test_optimize_resume(self, service: LLMService):
        """Test resume optimization suggestions."""
        result = service.optimize_resume(
            resume="John Doe\nSoftware Engineer\n5 years experience",
            job_description="Looking for Python developer with AWS experience",
        )
        assert len(result) > 0
        # Mock provider returns a generic response, just verify we get something back
        assert isinstance(result, str)

    def test_tailor_resume(self, service: LLMService):
        """Test resume tailoring."""
        result = service.tailor_resume(
            resume="John Doe\nDeveloper\nExperience: Built web apps",
            job_description="Senior Python Developer needed",
            company_name="Tech Corp",
            position="Senior Developer",
        )
        assert len(result) > 0
        # Mock returns a tailored resume format
        assert "PROFESSIONAL" in result or "EXPERIENCE" in result

    def test_enhance_achievement(self, service: LLMService):
        """Test achievement enhancement."""
        result = service.enhance_achievement("Led a project that improved sales")
        assert len(result) > 0

    def test_suggest_keyword_additions(self, service: LLMService):
        """Test keyword suggestion method."""
        result = service.suggest_keyword_additions(
            resume="Python developer with web experience",
            job_description="Need AWS and Docker skills",
            missing_keywords=["AWS", "Docker", "Kubernetes"],
        )
        assert len(result) > 0
        # Should contain suggestions
        assert "Add" in result or "Include" in result or "python" in result.lower()

    def test_generate_cover_letter(self, service: LLMService):
        """Test cover letter generation."""
        result = service.generate_cover_letter(
            resume="John Doe\nSoftware Engineer",
            job_description="Python developer role",
            company_name="Acme Inc",
            position="Developer",
        )
        assert len(result) > 0
        assert "Dear" in result or "Hiring Manager" in result

    def test_generate_networking_email(self, service: LLMService):
        """Test networking email generation."""
        result = service.generate_networking_email(
            recipient="Jane Smith",
            company="Tech Corp",
            purpose="Learn about engineering opportunities",
            background="I'm a software engineer with 5 years experience",
        )
        assert len(result) > 0
        assert "Subject:" in result

    def test_answer_application_question(self, service: LLMService):
        """Test application question answering."""
        result = service.answer_application_question(
            question="Why do you want to work here?",
            resume="Experienced developer",
            job_description="Python developer role",
            question_type="motivation",
        )
        assert len(result) > 0

    def test_generate_interview_answer(self, service: LLMService):
        """Test interview answer generation with STAR method."""
        result = service.generate_interview_answer(
            question="Tell me about a challenging project",
            resume="Led multiple projects as team lead",
            job_description="Senior developer position",
        )
        assert len(result) > 0
        # Mock returns STAR format
        assert "Situation" in result or "Action" in result or "Result" in result


# =============================================================================
# Caching Tests
# =============================================================================


class TestLLMServiceCaching:
    """Tests for LLM response caching."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear cache before and after each test."""
        clear_llm_cache()
        reset_llm_service()
        yield
        clear_llm_cache()
        reset_llm_service()

    def test_cache_stats_initially_empty(self):
        """Test that cache starts empty."""
        clear_llm_cache()
        stats = get_llm_cache_stats()
        assert stats["current_size"] == 0

    def test_cache_stores_response(self):
        """Test that responses are cached."""
        service = LLMService(provider_name="mock", enable_cache=True)

        # First call
        service.correct_grammar("Test text")

        # Check cache
        stats = get_llm_cache_stats()
        assert stats["current_size"] == 1

    def test_cache_returns_same_response(self):
        """Test that cached responses are returned for same input."""
        service = LLMService(provider_name="mock", enable_cache=True)

        result1 = service.correct_grammar("Same test text")
        result2 = service.correct_grammar("Same test text")

        assert result1 == result2

    def test_cache_different_for_different_input(self):
        """Test that different inputs get different cache entries."""
        service = LLMService(provider_name="mock", enable_cache=True)

        service.correct_grammar("First text")
        service.correct_grammar("Second text")

        stats = get_llm_cache_stats()
        assert stats["current_size"] == 2

    def test_clear_cache(self):
        """Test that clear_llm_cache empties the cache."""
        service = LLMService(provider_name="mock", enable_cache=True)

        service.correct_grammar("Test")
        assert get_llm_cache_stats()["current_size"] > 0

        clear_llm_cache()
        assert get_llm_cache_stats()["current_size"] == 0

    def test_cache_disabled(self):
        """Test that cache can be disabled."""
        service = LLMService(provider_name="mock", enable_cache=False)

        # Call multiple times
        service.correct_grammar("Test")
        service.correct_grammar("Test")

        # Each call should invoke the provider (tracked by call_count)
        assert service.provider.call_count == 2


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestLLMErrorHandling:
    """Tests for LLM error handling."""

    def test_llm_error_base_class(self):
        """Test LLMError base exception."""
        error = LLMError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_llm_configuration_error(self):
        """Test LLMConfigurationError exception."""
        error = LLMConfigurationError("Missing API key")
        assert str(error) == "Missing API key"
        assert isinstance(error, LLMError)

    def test_llm_provider_error(self):
        """Test LLMProviderError exception."""
        error = LLMProviderError("API returned 500")
        assert str(error) == "API returned 500"
        assert isinstance(error, LLMError)


# =============================================================================
# Provider Interface Tests
# =============================================================================


class TestProviderInterface:
    """Tests for BaseLLMProvider interface compliance."""

    def test_mock_provider_implements_interface(self):
        """Test that MockProvider implements the expected interface."""
        provider = MockProvider()

        # Should have all required methods/properties
        assert hasattr(provider, "invoke")
        assert hasattr(provider, "name")
        assert hasattr(provider, "model")
        assert callable(provider.invoke)

    def test_provider_invoke_returns_string(self):
        """Test that invoke returns a string."""
        provider = MockProvider()
        result = provider.invoke("Test prompt")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_provider_name_property(self):
        """Test that name property returns string."""
        provider = MockProvider()
        assert isinstance(provider.name, str)
        assert len(provider.name) > 0

    def test_provider_model_property(self):
        """Test that model property returns string."""
        provider = MockProvider()
        assert isinstance(provider.model, str)
        assert len(provider.model) > 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestLLMServiceIntegration:
    """Integration tests for LLM service with mock provider."""

    @pytest.fixture
    def service(self):
        """Create service for integration tests."""
        reset_llm_service()
        clear_llm_cache()
        return LLMService(provider_name="mock", enable_cache=False)

    def test_full_resume_workflow(self, service: LLMService):
        """Test a complete resume optimization workflow."""
        resume = """
        John Doe
        Software Engineer

        EXPERIENCE
        - Built web applications
        - Worked on databases
        """
        job_description = """
        Looking for Senior Python Developer
        - 5+ years Python experience
        - AWS cloud experience
        - Strong problem-solving skills
        """

        # Step 1: Get optimization suggestions
        suggestions = service.optimize_resume(resume, job_description)
        assert len(suggestions) > 0

        # Step 2: Get keyword suggestions
        keywords = service.suggest_keyword_additions(
            resume, job_description, ["Python", "AWS", "Docker"]
        )
        assert len(keywords) > 0

        # Step 3: Tailor the resume
        tailored = service.tailor_resume(resume, job_description, "Tech Corp", "Senior Developer")
        assert len(tailored) > 0

    def test_full_application_workflow(self, service: LLMService):
        """Test a complete job application workflow."""
        resume = "John Doe\nExperienced Developer"
        job_description = "Python Developer at Tech Corp"

        # Generate cover letter
        cover_letter = service.generate_cover_letter(
            resume, job_description, "Tech Corp", "Developer"
        )
        assert "Dear" in cover_letter

        # Answer application question
        answer = service.answer_application_question(
            "Why do you want this job?",
            resume,
            job_description,
            "motivation",
        )
        assert len(answer) > 0

        # Prepare for interview
        interview_prep = service.generate_interview_answer(
            "Tell me about yourself",
            resume,
            job_description,
        )
        assert len(interview_prep) > 0
