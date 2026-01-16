"""
Multi-provider LLM Service for ResuBoost AI.

Supports: OpenAI, Anthropic (Claude), Google (Gemini), Ollama (local models)
"""
import os
from abc import ABC, abstractmethod
from typing import Optional
from dotenv import load_dotenv
from utils.cache import cached

load_dotenv()

# Import timeout config with fallback
try:
    from config import OPENAI_REQUEST_TIMEOUT
except ImportError:
    OPENAI_REQUEST_TIMEOUT = 60


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt and return the response."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.7):
        try:
            from langchain_openai import OpenAI
        except ImportError:
            try:
                from langchain_community.llms import OpenAI
            except ImportError:
                from langchain.llms import OpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )

        self.llm = OpenAI(
            model_name=model_name,
            temperature=temperature,
            request_timeout=OPENAI_REQUEST_TIMEOUT
        )

    def invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt)

    @property
    def name(self) -> str:
        return "openai"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, model_name: str = "claude-3-haiku-20240307", temperature: float = 0.7):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "langchain-anthropic is required for Anthropic support. "
                "Install with: pip install langchain-anthropic"
            )

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )

        self.llm = ChatAnthropic(
            model=model_name,
            temperature=temperature,
            timeout=OPENAI_REQUEST_TIMEOUT
        )

    def invoke(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    @property
    def name(self) -> str:
        return "anthropic"


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider."""

    def __init__(self, model_name: str = "gemini-1.5-flash", temperature: float = 0.7):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain-google-genai is required for Google support. "
                "Install with: pip install langchain-google-genai"
            )

        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )

        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key
        )

    def invoke(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    @property
    def name(self) -> str:
        return "google"


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider."""

    def __init__(self, model_name: str = "llama3.2", temperature: float = 0.7):
        try:
            from langchain_ollama import OllamaLLM
        except ImportError:
            try:
                from langchain_community.llms import Ollama as OllamaLLM
            except ImportError:
                raise ImportError(
                    "langchain-ollama is required for Ollama support. "
                    "Install with: pip install langchain-ollama"
                )

        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

        self.llm = OllamaLLM(
            model=model_name,
            temperature=temperature,
            base_url=base_url
        )

    def invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt)

    @property
    def name(self) -> str:
        return "ollama"


class MockProvider(BaseLLMProvider):
    """Mock provider for testing (no API key required)."""

    def __init__(self, **kwargs):
        self.call_count = 0

    def invoke(self, prompt: str) -> str:
        self.call_count += 1
        # Return reasonable mock responses based on prompt content
        if "cover letter" in prompt.lower():
            return "Dear Hiring Manager,\n\nI am writing to express my interest in this position. With my background and skills, I believe I would be an excellent fit for your team.\n\nSincerely,\nCandidate"
        elif "resume" in prompt.lower() and "tailor" in prompt.lower():
            return "PROFESSIONAL SUMMARY\nExperienced professional with relevant skills.\n\nEXPERIENCE\n- Achieved results in previous roles\n- Led initiatives that improved outcomes"
        elif "interview" in prompt.lower():
            return "Situation: In my previous role...\nTask: I was responsible for...\nAction: I implemented...\nResult: This led to a 20% improvement."
        elif "keyword" in prompt.lower():
            return "1. Add 'Python' to your skills section\n2. Include 'project management' in your experience\n3. Mention 'data analysis' in your summary"
        elif "grammar" in prompt.lower():
            return prompt.split("You are an expert")[0].strip()
        else:
            return f"Mock response for prompt ({len(prompt)} chars)"

    @property
    def name(self) -> str:
        return "mock"


def get_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.7
) -> BaseLLMProvider:
    """
    Factory function to get an LLM provider.

    Args:
        provider_name: Provider to use (openai, anthropic, google, ollama, mock).
                      Defaults to LLM_PROVIDER env var or 'openai'.
        model_name: Model name (provider-specific). Defaults to provider's default.
        temperature: Temperature for generation.

    Returns:
        An LLM provider instance.
    """
    provider = provider_name or os.getenv('LLM_PROVIDER', 'openai').lower()

    providers = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'google': GoogleProvider,
        'ollama': OllamaProvider,
        'mock': MockProvider,
    }

    if provider not in providers:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Available: {', '.join(providers.keys())}"
        )

    kwargs = {'temperature': temperature}
    if model_name:
        kwargs['model_name'] = model_name

    return providers[provider](**kwargs)


# Default model names per provider
DEFAULT_MODELS = {
    'openai': 'gpt-3.5-turbo',
    'anthropic': 'claude-3-haiku-20240307',
    'google': 'gemini-1.5-flash',
    'ollama': 'llama3.2',
    'mock': 'mock',
}


class LLMService:
    """Service for managing LLM interactions with multi-provider support."""

    def __init__(
        self,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Initialize LLM service.

        Args:
            provider_name: LLM provider (openai, anthropic, google, ollama, mock)
            model_name: Model to use (provider-specific)
            temperature: Temperature for response generation
        """
        self.provider = get_provider(provider_name, model_name, temperature)
        self.temperature = temperature

    def _invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt."""
        result = self.provider.invoke(prompt)
        return result if isinstance(result, str) else str(result)

    @cached(category='llm_grammar', ttl_seconds=7200)
    def correct_grammar(self, text: str) -> str:
        """
        Correct grammatical errors in text.

        Note: Results are cached for 2 hours to save API calls.
        """
        prompt = f"""
        {text}

        You are an expert proofreader. Please correct any grammatical errors in the text above.
        Maintain the original formatting and structure. Only fix grammar, spelling, and punctuation.
        """
        return self._invoke(prompt)

    @cached(category='llm_resume_opt', ttl_seconds=3600)
    def optimize_resume(self, resume: str, job_description: str) -> str:
        """
        Optimize resume based on job description.

        Note: Results are cached for 1 hour to save API calls.
        """
        prompt = f"""
        Job Description:
        {job_description}

        Current Resume:
        {resume}

        As a career advisor and ATS expert, please:
        1. Identify key skills and qualifications in the job description that are missing from the resume
        2. Suggest specific improvements to better match the job requirements
        3. Recommend impactful action verbs and quantifiable achievements
        4. Ensure the resume is ATS-friendly

        Provide your suggestions in a clear, actionable format.
        """
        return self._invoke(prompt)

    def generate_cover_letter(
        self,
        resume: str,
        job_description: str,
        company_name: str,
        position: str,
        user_name: Optional[str] = None
    ) -> str:
        """Generate a personalized cover letter."""
        name_line = f"My name is {user_name} and I am" if user_name else "I am"

        prompt = f"""
        Resume:
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

        Generate the complete cover letter:
        """
        return self._invoke(prompt)

    def generate_networking_email(
        self,
        recipient_name: str,
        company_name: str,
        purpose: str,
        user_background: Optional[str] = None
    ) -> str:
        """Generate a networking email."""
        background_text = f"\n\nMy Background:\n{user_background}" if user_background else ""

        prompt = f"""
        Create a professional networking email with the following details:

        Recipient: {recipient_name}
        Company: {company_name}
        Purpose: {purpose}{background_text}

        Requirements:
        - Professional and respectful tone
        - Concise and to the point
        - Clear call to action
        - Express genuine interest
        - Keep it under 150 words

        Generate the email (include subject line):
        """
        return self._invoke(prompt)

    def enhance_achievement(self, achievement: str) -> str:
        """Enhance an achievement description with impact-focused language."""
        prompt = f"""
        Original achievement:
        {achievement}

        Rewrite this achievement to be more impactful by:
        1. Using strong action verbs
        2. Adding quantifiable metrics where possible
        3. Highlighting the business impact
        4. Keeping it concise (1-2 sentences)

        Enhanced achievement:
        """
        return self._invoke(prompt)

    @cached(category='llm_tailor', ttl_seconds=3600)
    def tailor_resume(self, resume: str, job_description: str, company_name: str, position: str) -> str:
        """
        Generate a tailored version of the resume for a specific job.

        Unlike optimize_resume which gives suggestions, this actually rewrites
        the resume to better match the job description.
        """
        prompt = f"""
        You are an expert resume writer specializing in ATS optimization.

        ORIGINAL RESUME:
        {resume}

        TARGET JOB:
        Company: {company_name}
        Position: {position}

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

        Output the complete tailored resume:
        """
        return self._invoke(prompt)

    def answer_application_question(
        self,
        question: str,
        resume: str,
        job_description: str,
        question_type: str = "general"
    ) -> str:
        """Generate an answer for common job application questions."""
        type_instructions = {
            "general": "Provide a clear, concise answer that highlights relevant experience.",
            "behavioral": "Use the STAR method (Situation, Task, Action, Result) to structure the answer.",
            "motivation": "Express genuine enthusiasm while connecting your background to the role.",
            "salary": "Provide a diplomatic response that shows flexibility while knowing your worth.",
            "weakness": "Give an honest weakness with clear steps you're taking to improve.",
            "strength": "Highlight a relevant strength with specific examples from your experience."
        }

        instruction = type_instructions.get(question_type, type_instructions["general"])

        prompt = f"""
        You are helping a job applicant answer an application question.

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

        ANSWER:
        """
        return self._invoke(prompt)

    def generate_interview_answer(
        self,
        question: str,
        resume: str,
        job_description: str
    ) -> str:
        """Generate a sample interview answer using STAR method."""
        prompt = f"""
        You are an interview coach helping prepare for a job interview.

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

        SAMPLE ANSWER:
        """
        return self._invoke(prompt)

    @cached(category='llm_keyword_suggestions', ttl_seconds=3600)
    def suggest_keyword_additions(
        self,
        resume: str,
        job_description: str,
        missing_keywords: list
    ) -> str:
        """Generate AI-powered suggestions for naturally incorporating missing keywords."""
        keywords_str = ", ".join(missing_keywords[:15])

        prompt = f"""
        You are an expert resume writer and ATS optimization specialist.

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

        Provide 5-7 specific suggestions:
        """
        return self._invoke(prompt)


# Singleton instance
_llm_service = None


def get_llm_service(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None
) -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(provider_name, model_name)
    return _llm_service


def reset_llm_service():
    """Reset the singleton (useful for testing)."""
    global _llm_service
    _llm_service = None
