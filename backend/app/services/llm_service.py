"""
Multi-provider LLM Service for ResuBoost AI Backend.

Supports: OpenAI, Anthropic (Claude), Google (Gemini), Ollama (local models), Mock (testing)

Uses direct SDK calls without LangChain for simplicity and control.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from app.config import get_settings


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM is misconfigured (missing API key, etc.)."""

    pass


class LLMProviderError(LLMError):
    """Raised when the LLM provider returns an error."""

    pass


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """
        Invoke the LLM with a prompt and return the response.

        Args:
            prompt: The text prompt to send to the LLM.

        Returns:
            The generated text response.

        Raises:
            LLMProviderError: If the provider returns an error.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the model name being used."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider using direct SDK calls."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 60,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMConfigurationError(
                "openai package is required for OpenAI support. " "Install with: pip install openai"
            )

        settings = get_settings()
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )

        self._model = model_name or settings.openai_model
        self._temperature = temperature
        self._timeout = timeout
        self._client = OpenAI(api_key=api_key, timeout=timeout)

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMProviderError(f"OpenAI API error: {str(e)}") from e

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider using direct SDK calls."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 60,
    ):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise LLMConfigurationError(
                "anthropic package is required for Anthropic support. "
                "Install with: pip install anthropic"
            )

        settings = get_settings()
        api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise LLMConfigurationError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )

        self._model = model_name or settings.anthropic_model
        self._temperature = temperature
        self._timeout = timeout
        self._client = Anthropic(api_key=api_key, timeout=timeout)

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._temperature,
            )
            # Handle the response content blocks
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return ""
        except Exception as e:
            raise LLMProviderError(f"Anthropic API error: {str(e)}") from e

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider using direct SDK calls."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 60,
    ):
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise LLMConfigurationError(
                "google-genai package is required for Google support. "
                "Install with: pip install google-genai"
            )

        settings = get_settings()
        api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise LLMConfigurationError(
                "GOOGLE_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )

        self._model = model_name or settings.google_model
        self._temperature = temperature
        self._timeout = timeout
        self._client = genai.Client(api_key=api_key)
        self._types = types

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=self._temperature,
                ),
            )
            return response.text or ""
        except Exception as e:
            raise LLMProviderError(f"Google API error: {str(e)}") from e

    @property
    def name(self) -> str:
        return "google"

    @property
    def model(self) -> str:
        return self._model


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider using httpx REST API calls."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 60,
    ):
        settings = get_settings()
        self._base_url = settings.ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self._model = model_name or settings.ollama_model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self._temperature = temperature
        self._timeout = timeout

    def invoke(self, prompt: str) -> str:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self._temperature,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.HTTPStatusError as e:
            raise LLMProviderError(f"Ollama API error: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise LLMProviderError(
                f"Ollama connection error: {str(e)}. " f"Is Ollama running at {self._base_url}?"
            ) from e
        except Exception as e:
            raise LLMProviderError(f"Ollama error: {str(e)}") from e

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model


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

    def invoke(self, prompt: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt
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


# Provider registry
_PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "ollama": OllamaProvider,
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

    timeout = settings.llm_request_timeout

    return _PROVIDERS[provider](
        model_name=model_name,
        temperature=temperature,
        timeout=timeout,
    )


class LLMService:
    """
    Service for managing LLM interactions with multi-provider support.

    This service provides high-level methods for common AI-powered features
    like resume optimization, cover letter generation, and interview prep.
    """

    def __init__(
        self,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """
        Initialize LLM service.

        Args:
            provider_name: LLM provider (openai, anthropic, google, ollama, mock)
            model_name: Model to use (provider-specific)
            temperature: Temperature for response generation (0.0 to 1.0)
        """
        self.provider = get_llm_provider(provider_name, model_name, temperature)
        self.temperature = temperature

    def _invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt and return cleaned response."""
        result = self.provider.invoke(prompt)
        return result.strip() if isinstance(result, str) else str(result).strip()

    # -------------------------------------------------------------------------
    # Grammar and Text Improvement
    # -------------------------------------------------------------------------

    def correct_grammar(self, text: str) -> str:
        """
        Correct grammatical errors in text.

        Args:
            text: The text to proofread and correct.

        Returns:
            The corrected text with grammar, spelling, and punctuation fixed.
        """
        prompt = f"""{text}

You are an expert proofreader. Please correct any grammatical errors in the text above.
Maintain the original formatting and structure. Only fix grammar, spelling, and punctuation.
Return only the corrected text without any explanations."""
        return self._invoke(prompt)

    # -------------------------------------------------------------------------
    # Resume Methods
    # -------------------------------------------------------------------------

    def optimize_resume(self, resume: str, job_description: str) -> str:
        """
        Analyze and provide optimization suggestions for a resume.

        Args:
            resume: The current resume text.
            job_description: The target job description.

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
        return self._invoke(prompt)

    def tailor_resume(
        self,
        resume: str,
        job_description: str,
        company_name: str = "",
        position: str = "",
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
        return self._invoke(prompt)

    def enhance_achievement(self, raw_achievement: str) -> str:
        """
        Enhance an achievement description with impact-focused language.

        Args:
            raw_achievement: The original achievement description.

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
        return self._invoke(prompt)

    def suggest_keyword_additions(
        self,
        resume: str,
        job_description: str,
        missing_keywords: list[str],
    ) -> str:
        """
        Generate AI-powered suggestions for naturally incorporating missing keywords.

        Args:
            resume: The current resume text.
            job_description: The target job description.
            missing_keywords: List of keywords missing from the resume.

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
        return self._invoke(prompt)

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
    ) -> str:
        """
        Generate a personalized cover letter.

        Args:
            resume: The applicant's resume text.
            job_description: The target job description.
            company_name: Name of the company.
            position: Title of the position.
            user_name: Optional name of the applicant.

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
        return self._invoke(prompt)

    def generate_networking_email(
        self,
        recipient: str,
        company: str,
        purpose: str,
        background: Optional[str] = None,
    ) -> str:
        """
        Generate a professional networking email.

        Args:
            recipient: Name of the recipient.
            company: Name of the company.
            purpose: Purpose of reaching out.
            background: Optional background information about the sender.

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
        return self._invoke(prompt)

    # -------------------------------------------------------------------------
    # Application and Interview
    # -------------------------------------------------------------------------

    def answer_application_question(
        self,
        question: str,
        resume: str,
        job_description: str,
        question_type: str = "general",
    ) -> str:
        """
        Generate an answer for common job application questions.

        Args:
            question: The application question to answer.
            resume: The applicant's resume text.
            job_description: The target job description.
            question_type: Type of question (general, behavioral, motivation,
                          salary, weakness, strength).

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
        return self._invoke(prompt)

    def generate_interview_answer(
        self,
        question: str,
        resume: str,
        job_description: str,
    ) -> str:
        """
        Generate a sample interview answer using STAR method.

        Args:
            question: The interview question to answer.
            resume: The candidate's resume text.
            job_description: The job description for context.

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
        return self._invoke(prompt)


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
