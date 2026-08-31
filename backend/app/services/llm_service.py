"""
Multi-provider LLM Service for ResuBoost AI Backend.

Supports: OpenAI, Anthropic (Claude), Google (Gemini), Ollama (local models), Mock (testing)

Provider dispatch, SDK calls, retry with exponential backoff and the exception
hierarchy all come from the shared ``llm_client`` package. What stays here is
what is specific to this application: the prompts, and the user-isolated
response cache that keys on the calling method and the requesting user.
"""

import hashlib
import logging
import os
from functools import partial
from typing import Callable, Optional

from cachetools import TTLCache
from llm_client import LLMClient
from llm_client import LLMConfigurationError as LLMConfigurationError
from llm_client import LLMError as LLMError
from llm_client import LLMProviderError as LLMProviderError
from llm_client import LLMRateLimitError as LLMRateLimitError
from llm_client import LLMServerError as LLMServerError
from llm_client import LLMTimeoutError as LLMTimeoutError
from llm_client import is_retryable as is_retryable_error

from app.config import get_settings

logger = logging.getLogger(__name__)

# Application-level response cache: 100 items max, 1 hour TTL.
# This is NOT llm_client's cache. It keys on the calling method and the
# requesting user so one user's answer is never served to another, which is a
# policy decision the client library has no business making.
_llm_response_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)


class BaseLLMProvider:
    """The provider contract the rest of this backend depends on.

    ``llm_client`` returns a rich ``Completion``; this backend has only ever
    wanted the text, so the adapter below flattens it and nothing else changes.
    """

    def invoke(self, prompt: str) -> str:
        """Send a prompt and return the generated text."""
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def model(self) -> str:
        raise NotImplementedError


class _ClientProvider(BaseLLMProvider):
    """Adapts ``llm_client.LLMClient`` to :class:`BaseLLMProvider`.

    One class replaces the four hand-written provider classes that used to
    live here. Retry lives in the client; so does turning a vendor SDK
    exception into an ``LLMProviderError``.
    """

    def __init__(
        self,
        provider_name: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 60,
    ):
        settings = get_settings()
        self._name = provider_name
        self._temperature = temperature
        self._client = LLMClient(
            provider_name,
            model_name or _configured_model(provider_name),
            timeout=timeout,
            max_retries=settings.llm_max_retries,
            retry_initial_delay=settings.llm_retry_delay,
            retry_max_delay=settings.llm_retry_max_delay,
        )

    def invoke(self, prompt: str) -> str:
        return self._client.complete(prompt, temperature=self._temperature).text

    @property
    def name(self) -> str:
        # The name this backend uses, not llm_client's ("google" -> "gemini").
        return self._name

    @property
    def model(self) -> str:
        return self._client.model


def _configured_model(provider_name: str) -> Optional[str]:
    """The model this deployment configured for ``provider_name``, if any."""
    settings = get_settings()
    return {
        "openai": settings.openai_model,
        "anthropic": settings.anthropic_model,
        "google": settings.google_model,
        "ollama": settings.ollama_model,
    }.get(provider_name)


class MockProvider(BaseLLMProvider):
    """Mock provider for testing (no API key required)."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 60,
    ):
        self._model = model_name or "mock-model"
        self._temperature = temperature
        self.call_count = 0
        self.last_prompt: Optional[str] = None
        # For testing retry logic
        self.fail_count = 0
        self.fail_until = 0
        self.fail_with: Optional[Exception] = None

    def set_failure_mode(self, fail_until: int, error: Optional[Exception] = None):
        """
        Configure the mock to fail for testing retry logic.

        Args:
            fail_until: Number of calls to fail before succeeding.
            error: Exception to raise (defaults to LLMServerError).
        """
        self.fail_count = 0
        self.fail_until = fail_until
        self.fail_with = error or LLMServerError("Mock server error", status_code=500)

    def clear_failure_mode(self):
        """Clear any configured failure mode."""
        self.fail_count = 0
        self.fail_until = 0
        self.fail_with = None

    def invoke(self, prompt: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt

        # Handle failure mode for testing retries
        if self.fail_until > 0 and self.fail_count < self.fail_until and self.fail_with is not None:
            self.fail_count += 1
            logger.info("Mock provider simulating failure %d/%d", self.fail_count, self.fail_until)
            raise self.fail_with

        prompt_lower = prompt.lower()

        # Return reasonable mock responses based on prompt content
        if "cover letter" in prompt_lower:
            return (
                "Dear Hiring Manager,\n\n"
                "I am writing to express my interest in this position. "
                "With my background and skills, I believe I would be an excellent fit for your team.\n\n"
                "Throughout my career, I have developed strong expertise that aligns with your requirements. "
                "I am excited about the opportunity to contribute to your organization.\n\n"
                "Thank you for considering my application. I look forward to discussing how I can contribute to your team.\n\n"
                "Sincerely,\nCandidate"
            )
        elif "tailor" in prompt_lower and "resume" in prompt_lower:
            return (
                "PROFESSIONAL SUMMARY\n"
                "Experienced professional with relevant skills tailored to this position.\n\n"
                "EXPERIENCE\n"
                "- Achieved measurable results aligned with job requirements\n"
                "- Led initiatives that improved key business outcomes\n"
                "- Collaborated with cross-functional teams on strategic projects\n\n"
                "SKILLS\n"
                "- Relevant technical skills\n"
                "- Industry-specific expertise"
            )
        elif "interview" in prompt_lower:
            return (
                "Situation: In my previous role at a technology company, we faced a critical deadline "
                "for a major product launch.\n\n"
                "Task: I was responsible for coordinating the development team and ensuring "
                "we met our deliverables on time.\n\n"
                "Action: I implemented a daily stand-up process, created a shared tracking dashboard, "
                "and proactively identified and resolved blockers.\n\n"
                "Result: We successfully launched on time, which led to a 20% increase in user adoption "
                "and positive feedback from stakeholders."
            )
        elif "keyword" in prompt_lower:
            return (
                "1. Add 'Python' to your skills section - this is a key requirement in the job description\n"
                "2. Include 'project management' in your experience bullets - rephrase existing achievements\n"
                "3. Mention 'data analysis' in your summary - connect it to your quantitative achievements\n"
                "4. Add 'cross-functional collaboration' - you can highlight team projects\n"
                "5. Include 'Agile methodology' if you have experience with iterative development"
            )
        elif "grammar" in prompt_lower or "proofread" in prompt_lower:
            # Extract the text before the instruction
            lines = prompt.split("\n")
            text_lines = []
            for line in lines:
                if "you are an expert" in line.lower():
                    break
                text_lines.append(line)
            return "\n".join(text_lines).strip()
        elif "networking" in prompt_lower and "email" in prompt_lower:
            return (
                "Subject: Introduction and Interest in Connecting\n\n"
                "Dear [Recipient],\n\n"
                "I hope this message finds you well. I am reaching out because I am very interested "
                "in learning more about your work at [Company].\n\n"
                "I would greatly appreciate the opportunity to connect briefly to learn from your experience. "
                "Would you have 15-20 minutes for a quick call?\n\n"
                "Thank you for your time.\n\n"
                "Best regards"
            )
        elif "enhance" in prompt_lower and "achievement" in prompt_lower:
            return (
                "Spearheaded a strategic initiative that drove 25% improvement in key metrics, "
                "resulting in $500K annual cost savings and enhanced operational efficiency across the organization."
            )
        elif "optimize" in prompt_lower and "resume" in prompt_lower:
            return (
                "SUGGESTIONS FOR RESUME OPTIMIZATION:\n\n"
                "1. Missing Keywords: Add 'Python', 'data analysis', and 'project management'\n"
                "2. Quantify Achievements: Add metrics to your bullet points\n"
                "3. Action Verbs: Replace 'responsible for' with 'led', 'drove', 'implemented'\n"
                "4. ATS Optimization: Use standard section headers and remove graphics"
            )
        elif "application question" in prompt_lower or "answer" in prompt_lower:
            return (
                "Based on my experience, I believe I am well-suited for this role because "
                "I have consistently delivered results in similar positions. "
                "For example, in my previous role, I successfully managed projects that "
                "directly align with the requirements outlined in this job description."
            )
        else:
            return f"Mock response for prompt ({len(prompt)} characters)"

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return self._model


# Provider registry: name -> factory. "mock" is a real class because the tests
# assert on it; the rest are the one adapter, bound to a provider name.
_PROVIDERS: dict[str, Callable[..., BaseLLMProvider]] = {
    "openai": partial(_ClientProvider, "openai"),
    "anthropic": partial(_ClientProvider, "anthropic"),
    "google": partial(_ClientProvider, "google"),
    "ollama": partial(_ClientProvider, "ollama"),
    "mock": MockProvider,
}


def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.7,
) -> BaseLLMProvider:
    """
    Factory function to get an LLM provider instance.

    Args:
        provider_name: Provider to use (openai, anthropic, google, ollama, mock).
                      Defaults to LLM_PROVIDER env var or settings, then 'openai'.
        model_name: Model name (provider-specific). Defaults to provider's default.
        temperature: Temperature for generation (0.0 to 1.0).

    Returns:
        An initialized LLM provider instance.

    Raises:
        ValueError: If an unknown provider is specified.
        LLMConfigurationError: If required configuration is missing.
    """
    settings = get_settings()
    provider = (
        provider_name or os.getenv("LLM_PROVIDER") or settings.llm_provider or "openai"
    ).lower()

    if provider not in _PROVIDERS:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(f"Unknown provider: {provider}. Available: {available}")

    return _PROVIDERS[provider](
        model_name=model_name,
        temperature=temperature,
        timeout=settings.llm_request_timeout,
    )


class LLMService:
    """
    Service for managing LLM interactions with multi-provider support.

    This service provides high-level methods for common AI-powered features
    like resume optimization, cover letter generation, and interview prep.
    Includes response caching for improved performance on repeated requests.
    Retry logic is handled at the provider level for production reliability.
    """

    def __init__(
        self,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        enable_cache: bool = True,
    ):
        """
        Initialize LLM service.

        Args:
            provider_name: LLM provider (openai, anthropic, google, ollama, mock)
            model_name: Model to use (provider-specific)
            temperature: Temperature for response generation (0.0 to 1.0)
            enable_cache: Whether to enable response caching (default: True)
        """
        self.provider = get_llm_provider(provider_name, model_name, temperature)
        self.temperature = temperature
        self.enable_cache = enable_cache

    def _get_cache_key(self, method_name: str, prompt: str, user_id: Optional[int] = None) -> str:
        """
        Generate a cache key from method name, prompt, and user identity.

        Args:
            method_name: Name of the calling method
            prompt: The prompt being sent to the LLM
            user_id: The requesting user's ID for cache isolation

        Returns:
            A hash string to use as cache key
        """
        # Include provider, model, and user_id in the key to prevent
        # cross-provider and cross-user cache hits
        user_segment = str(user_id) if user_id is not None else "anonymous"
        key_content = (
            f"{self.provider.name}:{self.provider.model}:" f"{user_segment}:{method_name}:{prompt}"
        )
        return hashlib.sha256(key_content.encode()).hexdigest()

    def _invoke_cached(self, method_name: str, prompt: str, user_id: Optional[int] = None) -> str:
        """
        Invoke the LLM with caching support.

        Args:
            method_name: Name of the calling method (for cache key)
            prompt: The prompt to send to the LLM
            user_id: The requesting user's ID for cache isolation

        Returns:
            The LLM response (from cache if available)
        """
        if self.enable_cache:
            cache_key = self._get_cache_key(method_name, prompt, user_id=user_id)

            # Check cache first
            if cache_key in _llm_response_cache:
                logger.debug("Cache hit for %s", method_name)
                return _llm_response_cache[cache_key]

            # Not in cache, invoke LLM (retry logic is in the provider)
            logger.debug("Cache miss for %s, invoking LLM", method_name)
            result = self.provider.invoke(prompt)
            cleaned_result = result.strip() if isinstance(result, str) else str(result).strip()

            # Store in cache
            _llm_response_cache[cache_key] = cleaned_result
            return cleaned_result
        else:
            # Cache disabled, invoke directly
            result = self.provider.invoke(prompt)
            return result.strip() if isinstance(result, str) else str(result).strip()

    def _invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt and return cleaned response."""
        result = self.provider.invoke(prompt)
        return result.strip() if isinstance(result, str) else str(result).strip()

    # -------------------------------------------------------------------------
    # Grammar and Text Improvement
    # -------------------------------------------------------------------------

    def correct_grammar(self, text: str, user_id: Optional[int] = None) -> str:
        """
        Correct grammatical errors in text.

        Args:
            text: The text to proofread and correct.
            user_id: The requesting user's ID for cache isolation.

        Returns:
            The corrected text with grammar, spelling, and punctuation fixed.
        """
        prompt = f"""{text}

You are an expert proofreader. Please correct any grammatical errors in the text above.
Maintain the original formatting and structure. Only fix grammar, spelling, and punctuation.
Return only the corrected text without any explanations."""
        return self._invoke_cached("correct_grammar", prompt, user_id=user_id)

    # -------------------------------------------------------------------------
    # Resume Methods
    # -------------------------------------------------------------------------

    def optimize_resume(
        self, resume: str, job_description: str, user_id: Optional[int] = None
    ) -> str:
        """
        Analyze and provide optimization suggestions for a resume.

        Args:
            resume: The current resume text.
            job_description: The target job description.
            user_id: The requesting user's ID for cache isolation.

        Returns:
            Actionable suggestions for improving the resume.
        """
        prompt = f"""Job Description:
{job_description}

Current Resume:
{resume}

As a career advisor and ATS expert, please:
1. Identify key skills and qualifications in the job description that are missing from the resume
2. Suggest specific improvements to better match the job requirements
3. Recommend impactful action verbs and quantifiable achievements
4. Ensure the resume is ATS-friendly

Provide your suggestions in a clear, actionable format."""
        return self._invoke_cached("optimize_resume", prompt, user_id=user_id)

    def tailor_resume(
        self,
        resume: str,
        job_description: str,
        company_name: str = "",
        position: str = "",
        user_id: Optional[int] = None,
    ) -> str:
        """
        Generate a tailored version of the resume for a specific job.

        Unlike optimize_resume which gives suggestions, this actually rewrites
        the resume to better match the job description.

        Args:
            resume: The original resume text.
            job_description: The target job description.
            company_name: Name of the target company.
            position: Title of the target position.
            user_id: The requesting user's ID for cache isolation.

        Returns:
            A rewritten resume tailored to the job.
        """
        prompt = f"""You are an expert resume writer specializing in ATS optimization.

ORIGINAL RESUME:
{resume}

TARGET JOB:
Company: {company_name or "Target Company"}
Position: {position or "Target Position"}

JOB DESCRIPTION:
{job_description}

TASK: Rewrite the resume to be tailored for this specific job while maintaining truthfulness.

Guidelines:
1. Keep all factual information (dates, companies, titles) exactly the same
2. Reorder and emphasize experiences most relevant to the job
3. Incorporate keywords from the job description naturally
4. Quantify achievements where possible
5. Use action verbs that match the job requirements
6. Ensure ATS-friendly formatting (no tables, graphics, or special characters)
7. Keep the same general structure but optimize content
8. Make the summary/objective specific to this role

Output the complete tailored resume:"""
        return self._invoke_cached("tailor_resume", prompt, user_id=user_id)

    def enhance_achievement(self, raw_achievement: str, user_id: Optional[int] = None) -> str:
        """
        Enhance an achievement description with impact-focused language.

        Args:
            raw_achievement: The original achievement description.
            user_id: The requesting user's ID for cache isolation.

        Returns:
            An enhanced version with stronger verbs and quantified impact.
        """
        prompt = f"""Original achievement:
{raw_achievement}

Rewrite this achievement to be more impactful by:
1. Using strong action verbs
2. Adding quantifiable metrics where possible
3. Highlighting the business impact
4. Keeping it concise (1-2 sentences)

Enhanced achievement:"""
        return self._invoke_cached("enhance_achievement", prompt, user_id=user_id)

    def suggest_keyword_additions(
        self,
        resume: str,
        job_description: str,
        missing_keywords: list[str],
        user_id: Optional[int] = None,
    ) -> str:
        """
        Generate AI-powered suggestions for naturally incorporating missing keywords.

        Args:
            resume: The current resume text.
            job_description: The target job description.
            missing_keywords: List of keywords missing from the resume.
            user_id: The requesting user's ID for cache isolation.

        Returns:
            Specific suggestions for adding keywords naturally.
        """
        keywords_str = ", ".join(missing_keywords[:15])

        prompt = f"""You are an expert resume writer and ATS optimization specialist.

CURRENT RESUME:
{resume}

TARGET JOB DESCRIPTION:
{job_description}

MISSING KEYWORDS TO ADD:
{keywords_str}

TASK: Provide specific, actionable suggestions for naturally incorporating these missing keywords into the resume.

For each major keyword or group of related keywords:
1. Identify WHERE in the resume it should be added (which section, which bullet point)
2. Provide an EXAMPLE of how to word it naturally
3. Explain WHY this placement makes sense

Important guidelines:
- Keywords should flow naturally, not feel forced
- Only suggest adding keywords the candidate can truthfully claim
- Suggest rephrasing existing bullet points when possible
- For technical skills, recommend the Skills section first
- For soft skills, show how to demonstrate them through achievements
- Keep suggestions realistic and professional

Provide 5-7 specific suggestions:"""
        return self._invoke_cached("suggest_keyword_additions", prompt, user_id=user_id)

    # -------------------------------------------------------------------------
    # Cover Letter and Communication
    # -------------------------------------------------------------------------

    def generate_cover_letter(
        self,
        resume: str,
        job_description: str,
        company_name: str,
        position: str,
        user_name: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """
        Generate a personalized cover letter.

        Args:
            resume: The applicant's resume text.
            job_description: The target job description.
            company_name: Name of the company.
            position: Title of the position.
            user_name: Optional name of the applicant.
            user_id: The requesting user's ID for cache isolation.

        Returns:
            A complete, professional cover letter.
        """
        name_line = f"My name is {user_name} and I am" if user_name else "I am"

        prompt = f"""Resume:
{resume}

Job Description:
{job_description}

Company: {company_name}
Position: {position}

As an expert cover letter writer, create a compelling, professional cover letter for this position.

Requirements:
- Start with: "{name_line} writing to express my interest in the {position} position at {company_name}"
- Highlight relevant experience and skills from the resume that match the job requirements
- Show enthusiasm for the company and role
- Keep it concise (3-4 paragraphs)
- Use a professional but warm tone
- End with a call to action

Generate the complete cover letter:"""
        return self._invoke_cached("generate_cover_letter", prompt, user_id=user_id)

    def generate_networking_email(
        self,
        recipient: str,
        company: str,
        purpose: str,
        background: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """
        Generate a professional networking email.

        Args:
            recipient: Name of the recipient.
            company: Name of the company.
            purpose: Purpose of reaching out.
            background: Optional background information about the sender.
            user_id: The requesting user's ID for cache isolation.

        Returns:
            A complete networking email with subject line.
        """
        background_text = f"\n\nMy Background:\n{background}" if background else ""

        prompt = f"""Create a professional networking email with the following details:

Recipient: {recipient}
Company: {company}
Purpose: {purpose}{background_text}

Requirements:
- Professional and respectful tone
- Concise and to the point
- Clear call to action
- Express genuine interest
- Keep it under 150 words

Generate the email (include subject line):"""
        return self._invoke_cached("generate_networking_email", prompt, user_id=user_id)

    # -------------------------------------------------------------------------
    # Application and Interview
    # -------------------------------------------------------------------------

    def answer_application_question(
        self,
        question: str,
        resume: str,
        job_description: str,
        question_type: str = "general",
        user_id: Optional[int] = None,
    ) -> str:
        """
        Generate an answer for common job application questions.

        Args:
            question: The application question to answer.
            resume: The applicant's resume text.
            job_description: The target job description.
            question_type: Type of question (general, behavioral, motivation,
                          salary, weakness, strength).
            user_id: The requesting user's ID for cache isolation.

        Returns:
            A well-crafted answer to the question.
        """
        type_instructions = {
            "general": "Provide a clear, concise answer that highlights relevant experience.",
            "behavioral": "Use the STAR method (Situation, Task, Action, Result) to structure the answer.",
            "motivation": "Express genuine enthusiasm while connecting your background to the role.",
            "salary": "Provide a diplomatic response that shows flexibility while knowing your worth.",
            "weakness": "Give an honest weakness with clear steps you're taking to improve.",
            "strength": "Highlight a relevant strength with specific examples from your experience.",
        }

        instruction = type_instructions.get(question_type, type_instructions["general"])

        prompt = f"""You are helping a job applicant answer an application question.

APPLICANT'S RESUME:
{resume}

JOB DESCRIPTION:
{job_description}

APPLICATION QUESTION:
{question}

INSTRUCTIONS:
{instruction}

Guidelines:
- Be authentic and professional
- Keep the answer concise (150-250 words unless the question requires more)
- Use specific examples from the resume when relevant
- Align the answer with the job requirements
- Avoid generic responses - make it personal and specific

ANSWER:"""
        return self._invoke_cached("answer_application_question", prompt, user_id=user_id)

    def generate_interview_answer(
        self,
        question: str,
        resume: str,
        job_description: str,
        user_id: Optional[int] = None,
    ) -> str:
        """
        Generate a sample interview answer using STAR method.

        Args:
            question: The interview question to answer.
            resume: The candidate's resume text.
            job_description: The job description for context.
            user_id: The requesting user's ID for cache isolation.

        Returns:
            A STAR-formatted interview answer.
        """
        prompt = f"""You are an interview coach helping prepare for a job interview.

CANDIDATE'S RESUME:
{resume}

JOB THEY'RE INTERVIEWING FOR:
{job_description}

INTERVIEW QUESTION:
{question}

Generate a strong answer using the STAR method:
- Situation: Set the context
- Task: Describe the challenge or responsibility
- Action: Explain what you did
- Result: Share the outcome with metrics if possible

Make the answer specific, using details from the resume where applicable.
Keep it conversational but professional (about 200-300 words).

SAMPLE ANSWER:"""
        return self._invoke_cached("generate_interview_answer", prompt, user_id=user_id)


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
) -> LLMService:
    """
    Get or create the LLM service singleton.

    Args:
        provider_name: Optional provider override.
        model_name: Optional model override.

    Returns:
        The LLMService singleton instance.
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(provider_name, model_name)
    return _llm_service


def reset_llm_service() -> None:
    """Reset the LLM service singleton (useful for testing)."""
    global _llm_service
    _llm_service = None


def clear_llm_cache() -> None:
    """Clear the LLM response cache."""
    _llm_response_cache.clear()


def get_llm_cache_stats() -> dict:
    """
    Get cache statistics for monitoring.

    Returns:
        Dictionary with cache size, max size, and TTL info.
    """
    return {
        "current_size": len(_llm_response_cache),
        "max_size": _llm_response_cache.maxsize,
        "ttl_seconds": _llm_response_cache.ttl,
    }


def get_retry_stats() -> dict:
    """
    Get retry configuration for monitoring.

    Returns:
        Dictionary with retry configuration settings.
    """
    settings = get_settings()
    return {
        "max_retries": settings.llm_max_retries,
        "initial_delay_seconds": settings.llm_retry_delay,
        "max_delay_seconds": settings.llm_retry_max_delay,
        "exponential_base": settings.llm_retry_exponential_base,
        # llm_client always jitters its backoff, so this is no longer a switch.
        "jitter_enabled": True,
    }
