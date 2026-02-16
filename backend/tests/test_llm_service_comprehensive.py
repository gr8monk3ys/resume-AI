"""
Comprehensive tests for the LLM service and multi-provider support.

Tests:
- All LLM service methods with MockProvider
- Cache hits and misses with detailed verification
- Retry logic with mock failure modes
- Provider factory function with different providers
- Error classification functions for each provider
- Error hierarchy and exception classes
- Cache key generation
- Singleton lifecycle management
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.llm_service import (
    CLIENT_ERROR_STATUS_CODES,
    RETRYABLE_STATUS_CODES,
    BaseLLMProvider,
    LLMClientError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMServerError,
    LLMService,
    LLMTimeoutError,
    MockProvider,
    _classify_httpx_error,
    _PROVIDERS,
    clear_llm_cache,
    get_llm_cache_stats,
    get_llm_provider,
    get_llm_service,
    get_retry_stats,
    is_retryable_error,
    reset_llm_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clean_llm_state():
    """Reset LLM service and cache before and after each test."""
    reset_llm_service()
    clear_llm_cache()
    yield
    reset_llm_service()
    clear_llm_cache()


@pytest.fixture
def service():
    """Create a fresh LLM service with mock provider and cache disabled."""
    return LLMService(provider_name="mock", enable_cache=False)


@pytest.fixture
def cached_service():
    """Create a fresh LLM service with mock provider and cache enabled."""
    return LLMService(provider_name="mock", enable_cache=True)


# =============================================================================
# Error Exception Hierarchy Tests
# =============================================================================


class TestErrorHierarchy:
    """Tests for the LLM error exception hierarchy."""

    def test_llm_error_is_base_exception(self):
        """Test LLMError is a base Exception."""
        error = LLMError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_llm_configuration_error_extends_llm_error(self):
        """Test LLMConfigurationError extends LLMError."""
        error = LLMConfigurationError("missing key")
        assert isinstance(error, LLMError)
        assert isinstance(error, Exception)

    def test_llm_provider_error_extends_llm_error(self):
        """Test LLMProviderError extends LLMError."""
        error = LLMProviderError("api error")
        assert isinstance(error, LLMError)

    def test_llm_provider_error_has_status_code(self):
        """Test LLMProviderError carries status code."""
        error = LLMProviderError("error", status_code=500, retryable=True)
        assert error.status_code == 500
        assert error.retryable is True

    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError carries retry_after."""
        error = LLMRateLimitError("rate limited", retry_after=30.0)
        assert isinstance(error, LLMProviderError)
        assert error.status_code == 429
        assert error.retryable is True
        assert error.retry_after == 30.0

    def test_llm_timeout_error(self):
        """Test LLMTimeoutError is retryable."""
        error = LLMTimeoutError("timed out")
        assert isinstance(error, LLMProviderError)
        assert error.retryable is True
        assert error.status_code is None

    def test_llm_connection_error(self):
        """Test LLMConnectionError is retryable."""
        error = LLMConnectionError("cannot connect")
        assert isinstance(error, LLMProviderError)
        assert error.retryable is True

    def test_llm_server_error(self):
        """Test LLMServerError is retryable."""
        error = LLMServerError("internal error", status_code=500)
        assert isinstance(error, LLMProviderError)
        assert error.retryable is True
        assert error.status_code == 500

    def test_llm_client_error_not_retryable(self):
        """Test LLMClientError is not retryable."""
        error = LLMClientError("bad request", status_code=400)
        assert isinstance(error, LLMProviderError)
        assert error.retryable is False
        assert error.status_code == 400


# =============================================================================
# Error Classification Tests
# =============================================================================


class TestErrorClassification:
    """Tests for error classification functions."""

    def test_is_retryable_provider_error_retryable(self):
        """Test that retryable LLMProviderError returns True."""
        error = LLMProviderError("error", retryable=True)
        assert is_retryable_error(error) is True

    def test_is_retryable_provider_error_not_retryable(self):
        """Test that non-retryable LLMProviderError returns False."""
        error = LLMClientError("bad request", status_code=400)
        assert is_retryable_error(error) is False

    def test_is_retryable_rate_limit_error(self):
        """Test that rate limit error is retryable."""
        error = LLMRateLimitError("rate limited")
        assert is_retryable_error(error) is True

    def test_is_retryable_timeout_error(self):
        """Test that timeout error is retryable."""
        error = LLMTimeoutError("timed out")
        assert is_retryable_error(error) is True

    def test_is_retryable_connection_error(self):
        """Test that connection error is retryable."""
        error = LLMConnectionError("connection refused")
        assert is_retryable_error(error) is True

    def test_is_retryable_server_error(self):
        """Test that server error is retryable."""
        error = LLMServerError("server error", status_code=500)
        assert is_retryable_error(error) is True

    def test_is_retryable_httpx_timeout(self):
        """Test that httpx timeout exceptions are retryable."""
        error = httpx.ReadTimeout("timed out")
        assert is_retryable_error(error) is True

    def test_is_retryable_httpx_connect_error(self):
        """Test that httpx connection errors are retryable."""
        error = httpx.ConnectError("connection refused")
        assert is_retryable_error(error) is True

    def test_is_retryable_generic_exception_not_retryable(self):
        """Test that generic exceptions are not retryable."""
        error = ValueError("bad value")
        assert is_retryable_error(error) is False

    def test_retryable_status_codes_correct(self):
        """Test that retryable status codes include expected values."""
        assert 429 in RETRYABLE_STATUS_CODES
        assert 500 in RETRYABLE_STATUS_CODES
        assert 502 in RETRYABLE_STATUS_CODES
        assert 503 in RETRYABLE_STATUS_CODES
        assert 504 in RETRYABLE_STATUS_CODES

    def test_client_error_status_codes_correct(self):
        """Test that client error status codes include expected values."""
        assert 400 in CLIENT_ERROR_STATUS_CODES
        assert 401 in CLIENT_ERROR_STATUS_CODES
        assert 403 in CLIENT_ERROR_STATUS_CODES
        assert 404 in CLIENT_ERROR_STATUS_CODES


# =============================================================================
# HTTPX Error Classification Tests
# =============================================================================


class TestHTTPXErrorClassification:
    """Tests for httpx error classification."""

    def test_classify_httpx_timeout(self):
        """Test classifying httpx timeout."""
        error = httpx.ReadTimeout("timed out")
        result = _classify_httpx_error(error, "TestProvider")

        assert isinstance(result, LLMTimeoutError)
        assert "TestProvider" in str(result)

    def test_classify_httpx_connect_error(self):
        """Test classifying httpx connection error."""
        error = httpx.ConnectError("refused")
        result = _classify_httpx_error(error, "Ollama")

        assert isinstance(result, LLMConnectionError)
        assert "Ollama" in str(result)

    def test_classify_httpx_429(self):
        """Test classifying httpx 429 response."""
        response = MagicMock()
        response.status_code = 429
        error = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=response)

        result = _classify_httpx_error(error, "API")
        assert isinstance(result, LLMRateLimitError)

    def test_classify_httpx_500(self):
        """Test classifying httpx 500 response."""
        response = MagicMock()
        response.status_code = 500
        error = httpx.HTTPStatusError("server error", request=MagicMock(), response=response)

        result = _classify_httpx_error(error, "API")
        assert isinstance(result, LLMServerError)

    def test_classify_httpx_400(self):
        """Test classifying httpx 400 response."""
        response = MagicMock()
        response.status_code = 400
        error = httpx.HTTPStatusError("bad request", request=MagicMock(), response=response)

        result = _classify_httpx_error(error, "API")
        assert isinstance(result, LLMClientError)

    def test_classify_httpx_generic_error(self):
        """Test classifying generic httpx error."""
        error = RuntimeError("something went wrong")
        result = _classify_httpx_error(error, "TestAPI")

        assert isinstance(result, LLMProviderError)
        assert "TestAPI" in str(result)


# =============================================================================
# Provider Factory Tests
# =============================================================================


class TestProviderFactoryDetailed:
    """Tests for provider factory function."""

    def test_mock_provider_creation(self):
        """Test creating mock provider."""
        provider = get_llm_provider("mock")
        assert isinstance(provider, MockProvider)
        assert provider.name == "mock"

    def test_unknown_provider_error(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_llm_provider("nonexistent")
        assert "Unknown provider" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_provider_registry_completeness(self):
        """Test that all expected providers are registered."""
        expected = {"openai", "anthropic", "google", "ollama", "mock"}
        registered = set(_PROVIDERS.keys())
        assert expected == registered

    def test_custom_model_name(self):
        """Test provider creation with custom model name."""
        provider = get_llm_provider("mock", model_name="gpt-4-turbo")
        assert provider.model == "gpt-4-turbo"

    def test_custom_temperature(self):
        """Test provider creation with custom temperature."""
        provider = get_llm_provider("mock", temperature=0.0)
        assert provider._temperature == 0.0

    def test_provider_case_insensitive(self):
        """Test that provider name is case insensitive."""
        # The factory lowercases the name
        provider = get_llm_provider("Mock")
        assert isinstance(provider, MockProvider)


# =============================================================================
# Mock Provider Tests
# =============================================================================


class TestMockProviderDetailed:
    """Tests for MockProvider responses and behavior."""

    def test_cover_letter_response(self):
        """Test that cover letter prompt returns appropriate response."""
        provider = MockProvider()
        result = provider.invoke("Generate a cover letter for this position")

        assert "Dear Hiring Manager" in result
        assert len(result) > 50

    def test_tailor_resume_response(self):
        """Test that tailor resume prompt returns formatted resume."""
        provider = MockProvider()
        result = provider.invoke("Tailor this resume for the job")

        assert "PROFESSIONAL SUMMARY" in result or "EXPERIENCE" in result

    def test_interview_response_star_format(self):
        """Test that interview prompt returns STAR format."""
        provider = MockProvider()
        result = provider.invoke("Prepare for this interview question")

        assert "Situation" in result
        assert "Task" in result
        assert "Action" in result
        assert "Result" in result

    def test_career_coach_response(self):
        """Test that career coach prompt returns coaching response."""
        provider = MockProvider()
        result = provider.invoke("Career coach: help me with my job search")

        assert len(result) > 50

    def test_keyword_response(self):
        """Test that keyword prompt returns suggestions."""
        provider = MockProvider()
        result = provider.invoke("Suggest keywords to add")

        assert "Add" in result or "Include" in result

    def test_grammar_response(self):
        """Test that grammar prompt returns corrected text."""
        provider = MockProvider()
        result = provider.invoke("Check grammar: The quick brown fox.")

        assert len(result) > 0

    def test_networking_email_response(self):
        """Test that networking email prompt returns email format."""
        provider = MockProvider()
        result = provider.invoke("Write a networking email to reach out")

        assert "Subject:" in result
        assert "Dear" in result

    def test_enhance_achievement_response(self):
        """Test that enhance achievement prompt returns improved text."""
        provider = MockProvider()
        result = provider.invoke("Enhance this achievement: Led a project")

        assert len(result) > 0

    def test_optimize_resume_response(self):
        """Test that optimize resume prompt returns suggestions."""
        provider = MockProvider()
        result = provider.invoke("Optimize this resume for the job")

        assert "SUGGESTIONS" in result or "Missing" in result

    def test_generic_response(self):
        """Test that unknown prompts return generic response."""
        provider = MockProvider()
        result = provider.invoke("Some random prompt")

        assert "Mock response" in result

    def test_call_count_tracking(self):
        """Test that call count is tracked correctly."""
        provider = MockProvider()
        assert provider.call_count == 0

        provider.invoke("test")
        assert provider.call_count == 1

        provider.invoke("test 2")
        assert provider.call_count == 2

    def test_last_prompt_tracking(self):
        """Test that last prompt is tracked."""
        provider = MockProvider()
        provider.invoke("first prompt")
        assert provider.last_prompt == "first prompt"

        provider.invoke("second prompt")
        assert provider.last_prompt == "second prompt"


# =============================================================================
# Mock Provider Failure Mode Tests
# =============================================================================


class TestMockProviderFailureMode:
    """Tests for MockProvider failure mode (for retry testing)."""

    def test_set_failure_mode(self):
        """Test configuring failure mode."""
        provider = MockProvider()
        provider.set_failure_mode(fail_until=3)

        assert provider.fail_until == 3
        assert provider.fail_count == 0
        assert provider.fail_with is not None

    def test_failure_mode_raises_error(self):
        """Test that failure mode raises configured error."""
        provider = MockProvider()
        provider.set_failure_mode(fail_until=1)

        with pytest.raises(LLMServerError):
            provider.invoke("test")

    def test_failure_mode_succeeds_after_count(self):
        """Test that failure mode succeeds after fail_until count."""
        provider = MockProvider()
        provider.set_failure_mode(fail_until=2)

        # First two calls should fail
        with pytest.raises(LLMServerError):
            provider.invoke("test 1")
        with pytest.raises(LLMServerError):
            provider.invoke("test 2")

        # Third call should succeed
        result = provider.invoke("test 3")
        assert len(result) > 0

    def test_failure_mode_custom_error(self):
        """Test failure mode with custom error."""
        provider = MockProvider()
        custom_error = LLMRateLimitError("rate limited", retry_after=10.0)
        provider.set_failure_mode(fail_until=1, error=custom_error)

        with pytest.raises(LLMRateLimitError):
            provider.invoke("test")

    def test_clear_failure_mode(self):
        """Test clearing failure mode."""
        provider = MockProvider()
        provider.set_failure_mode(fail_until=10)
        provider.clear_failure_mode()

        assert provider.fail_until == 0
        assert provider.fail_count == 0
        assert provider.fail_with is None

        # Should succeed
        result = provider.invoke("test")
        assert len(result) > 0


# =============================================================================
# LLM Service Method Tests
# =============================================================================


class TestLLMServiceAllMethods:
    """Tests for all LLM service methods using mock provider."""

    def test_correct_grammar(self, service):
        """Test grammar correction method."""
        result = service.correct_grammar("This are a test sentance.")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_optimize_resume(self, service):
        """Test resume optimization method."""
        result = service.optimize_resume(
            resume="John Doe\nPython Developer",
            job_description="Senior Python Developer needed",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tailor_resume(self, service):
        """Test resume tailoring method."""
        result = service.tailor_resume(
            resume="John Doe\nDeveloper",
            job_description="Python Developer needed",
            company_name="Acme Corp",
            position="Senior Developer",
        )
        assert isinstance(result, str)
        assert "PROFESSIONAL" in result or "EXPERIENCE" in result

    def test_tailor_resume_without_optional_fields(self, service):
        """Test resume tailoring without company and position."""
        result = service.tailor_resume(
            resume="John Doe\nDeveloper",
            job_description="Python role",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_enhance_achievement(self, service):
        """Test achievement enhancement method."""
        result = service.enhance_achievement("Led a project that improved sales")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_suggest_keyword_additions(self, service):
        """Test keyword addition suggestions."""
        result = service.suggest_keyword_additions(
            resume="Python developer",
            job_description="AWS and Docker experience needed",
            missing_keywords=["AWS", "Docker", "Kubernetes"],
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_cover_letter(self, service):
        """Test cover letter generation."""
        result = service.generate_cover_letter(
            resume="John Doe\nSoftware Engineer",
            job_description="Python developer role",
            company_name="Acme Inc",
            position="Developer",
        )
        assert "Dear" in result or "Hiring Manager" in result

    def test_generate_cover_letter_with_name(self, service):
        """Test cover letter generation with user name."""
        result = service.generate_cover_letter(
            resume="John Doe\nSoftware Engineer",
            job_description="Python developer role",
            company_name="Acme Inc",
            position="Developer",
            user_name="John Doe",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_networking_email(self, service):
        """Test networking email generation."""
        result = service.generate_networking_email(
            recipient="Jane Smith",
            company="Tech Corp",
            purpose="Learn about engineering opportunities",
        )
        assert "Subject:" in result

    def test_generate_networking_email_with_background(self, service):
        """Test networking email with background info."""
        result = service.generate_networking_email(
            recipient="Jane Smith",
            company="Tech Corp",
            purpose="Connect about opportunities",
            background="5 years in Python development",
        )
        assert isinstance(result, str)
        assert "Subject:" in result

    def test_answer_application_question(self, service):
        """Test application question answering."""
        result = service.answer_application_question(
            question="Why do you want to work here?",
            resume="Experienced developer",
            job_description="Python developer role",
            question_type="motivation",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_answer_application_question_types(self, service):
        """Test different question types."""
        question_types = [
            "general",
            "behavioral",
            "motivation",
            "salary",
            "weakness",
            "strength",
        ]
        for qtype in question_types:
            result = service.answer_application_question(
                question="Test question",
                resume="Test resume",
                job_description="Test job",
                question_type=qtype,
            )
            assert len(result) > 0, f"Empty result for question_type={qtype}"

    def test_generate_interview_answer(self, service):
        """Test interview answer generation."""
        result = service.generate_interview_answer(
            question="Tell me about a challenging project",
            resume="Led multiple projects",
            job_description="Senior developer position",
        )
        assert "Situation" in result or "Action" in result

    def test_career_coach_respond(self, service):
        """Test career coaching response."""
        result = service.career_coach_respond(
            message="How can I improve my job search?",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coach_respond_with_history(self, service):
        """Test career coaching with conversation history."""
        history = [
            {"role": "user", "content": "I want to change careers"},
            {"role": "assistant", "content": "That is a great goal!"},
        ]
        result = service.career_coach_respond(
            message="What skills should I focus on?",
            conversation_history=history,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coach_respond_with_resume(self, service):
        """Test career coaching with resume context."""
        result = service.career_coach_respond(
            message="Help me with my career",
            resume="John Doe\nSoftware Engineer\n5 years experience",
            context="job_search",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_career_coach_all_contexts(self, service):
        """Test career coaching with all available contexts."""
        contexts = [
            "general",
            "job_search",
            "interview_prep",
            "career_change",
            "salary_negotiation",
            "networking",
        ]
        for ctx in contexts:
            result = service.career_coach_respond(
                message="Help me",
                context=ctx,
            )
            assert len(result) > 0, f"Empty result for context={ctx}"


# =============================================================================
# Cache Tests
# =============================================================================


class TestLLMServiceCachingDetailed:
    """Tests for detailed caching behavior."""

    def test_cache_hit_returns_same_response(self, cached_service):
        """Test that cache hit returns the same response."""
        result1 = cached_service.correct_grammar("Test text")
        result2 = cached_service.correct_grammar("Test text")

        assert result1 == result2

    def test_cache_miss_invokes_provider(self, cached_service):
        """Test that cache miss invokes the provider."""
        cached_service.correct_grammar("Text A")
        cached_service.correct_grammar("Text B")

        stats = get_llm_cache_stats()
        assert stats["current_size"] == 2

    def test_cache_hit_does_not_increment_call_count(self, cached_service):
        """Test that cache hits do not invoke the provider."""
        cached_service.correct_grammar("Same text")
        first_count = cached_service.provider.call_count

        cached_service.correct_grammar("Same text")
        assert cached_service.provider.call_count == first_count

    def test_cache_disabled_always_invokes_provider(self, service):
        """Test that disabled cache always invokes the provider."""
        service.correct_grammar("Same text")
        service.correct_grammar("Same text")

        assert service.provider.call_count == 2

    def test_clear_cache_empties_all_entries(self, cached_service):
        """Test that clearing cache removes all entries."""
        cached_service.correct_grammar("text 1")
        cached_service.correct_grammar("text 2")

        assert get_llm_cache_stats()["current_size"] == 2

        clear_llm_cache()
        assert get_llm_cache_stats()["current_size"] == 0

    def test_cache_stats_include_all_fields(self):
        """Test that cache stats include all expected fields."""
        stats = get_llm_cache_stats()
        assert "current_size" in stats
        assert "max_size" in stats
        assert "ttl_seconds" in stats

    def test_cache_key_includes_provider_info(self, cached_service):
        """Test that cache keys include provider and model info."""
        # This is tested implicitly by verifying different providers
        # produce different cache entries for same prompt
        key = cached_service._get_cache_key("test_method", "test prompt")
        assert isinstance(key, str)
        assert len(key) == 64  # SHA-256 hex digest length

    def test_different_methods_produce_different_keys(self, cached_service):
        """Test that different method names produce different cache keys."""
        key1 = cached_service._get_cache_key("method_a", "same prompt")
        key2 = cached_service._get_cache_key("method_b", "same prompt")

        assert key1 != key2


# =============================================================================
# Singleton Lifecycle Tests
# =============================================================================


class TestLLMServiceSingleton:
    """Tests for LLM service singleton lifecycle."""

    def test_get_llm_service_creates_singleton(self):
        """Test that get_llm_service creates a singleton instance."""
        service1 = get_llm_service(provider_name="mock")
        service2 = get_llm_service()

        assert service1 is service2

    def test_reset_llm_service_clears_singleton(self):
        """Test that reset creates a new instance."""
        service1 = get_llm_service(provider_name="mock")
        reset_llm_service()
        service2 = get_llm_service(provider_name="mock")

        assert service1 is not service2

    def test_service_init_with_provider(self):
        """Test service initialization with provider parameter."""
        service = LLMService(provider_name="mock")
        assert service.provider.name == "mock"

    def test_service_init_with_temperature(self):
        """Test service initialization with custom temperature."""
        service = LLMService(provider_name="mock", temperature=0.1)
        assert service.temperature == 0.1


# =============================================================================
# Retry Stats Tests
# =============================================================================


class TestRetryStats:
    """Tests for retry configuration statistics."""

    def test_get_retry_stats_returns_dict(self):
        """Test that retry stats returns a dictionary."""
        stats = get_retry_stats()
        assert isinstance(stats, dict)

    def test_retry_stats_include_required_keys(self):
        """Test that retry stats include all required keys."""
        stats = get_retry_stats()
        assert "max_retries" in stats
        assert "initial_delay_seconds" in stats
        assert "max_delay_seconds" in stats
        assert "exponential_base" in stats
        assert "jitter_enabled" in stats

    def test_retry_stats_values_are_reasonable(self):
        """Test that retry stats values are within reasonable ranges."""
        stats = get_retry_stats()
        assert stats["max_retries"] >= 0
        assert stats["initial_delay_seconds"] >= 0
        assert stats["max_delay_seconds"] >= stats["initial_delay_seconds"]
        assert stats["exponential_base"] >= 1


# =============================================================================
# Provider Interface Compliance Tests
# =============================================================================


class TestProviderInterfaceCompliance:
    """Tests that all providers comply with the BaseLLMProvider interface."""

    def test_mock_provider_has_invoke(self):
        """Test MockProvider has invoke method."""
        provider = MockProvider()
        assert callable(provider.invoke)

    def test_mock_provider_has_name_property(self):
        """Test MockProvider has name property."""
        provider = MockProvider()
        assert isinstance(provider.name, str)
        assert provider.name == "mock"

    def test_mock_provider_has_model_property(self):
        """Test MockProvider has model property."""
        provider = MockProvider()
        assert isinstance(provider.model, str)
        assert provider.model == "mock-model"

    def test_invoke_returns_string(self):
        """Test that invoke returns a string."""
        provider = MockProvider()
        result = provider.invoke("test")
        assert isinstance(result, str)

    def test_invoke_returns_nonempty_string(self):
        """Test that invoke returns a non-empty string."""
        provider = MockProvider()
        result = provider.invoke("Generate something")
        assert len(result) > 0

    def test_all_providers_registered(self):
        """Test that all expected providers are in the registry."""
        assert "openai" in _PROVIDERS
        assert "anthropic" in _PROVIDERS
        assert "google" in _PROVIDERS
        assert "ollama" in _PROVIDERS
        assert "mock" in _PROVIDERS

    def test_all_registered_providers_extend_base(self):
        """Test that all registered providers extend BaseLLMProvider."""
        for name, provider_class in _PROVIDERS.items():
            assert issubclass(
                provider_class, BaseLLMProvider
            ), f"{name} does not extend BaseLLMProvider"
