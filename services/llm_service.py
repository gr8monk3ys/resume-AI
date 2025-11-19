import os
from typing import Optional
from dotenv import load_dotenv
from utils.cache import cached

# Use modern LangChain imports to avoid deprecation warnings
try:
    from langchain_community.llms import OpenAI
    from langchain.chains import LLMChain
    from langchain_core.prompts import PromptTemplate
except ImportError:
    # Fallback to legacy imports if modern ones not available
    from langchain import OpenAI, LLMChain, PromptTemplate

load_dotenv()

class LLMService:
    """Service for managing LLM interactions."""

    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.7):
        """
        Initialize LLM service.

        Args:
            model_name: OpenAI model to use
            temperature: Temperature for response generation
        """
        self.model_name = model_name
        self.temperature = temperature
        self.llm = OpenAI(model_name=model_name, temperature=temperature)

    @cached(category='llm_grammar', ttl_seconds=7200)
    def correct_grammar(self, text: str) -> str:
        """
        Correct grammatical errors in text.

        Note: Results are cached for 2 hours to save API calls.

        Args:
            text: Text to correct

        Returns:
            Corrected text
        """
        template = """
        {text}

        You are an expert proofreader. Please correct any grammatical errors in the text above.
        Maintain the original formatting and structure. Only fix grammar, spelling, and punctuation.
        """
        prompt_template = PromptTemplate(input_variables=["text"], template=template)
        chain = LLMChain(llm=self.llm, prompt=prompt_template, verbose=False)
        return chain.predict(text=text)

    @cached(category='llm_resume_opt', ttl_seconds=3600)
    def optimize_resume(self, resume: str, job_description: str) -> str:
        """
        Optimize resume based on job description.

        Note: Results are cached for 1 hour to save API calls and improve performance.

        Args:
            resume: Current resume text
            job_description: Target job description

        Returns:
            Optimized resume suggestions
        """
        template = """
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
        prompt_template = PromptTemplate(
            input_variables=["job_description", "resume"],
            template=template
        )
        chain = LLMChain(llm=self.llm, prompt=prompt_template, verbose=False)
        return chain.predict(job_description=job_description, resume=resume)

    def generate_cover_letter(
        self,
        resume: str,
        job_description: str,
        company_name: str,
        position: str,
        user_name: Optional[str] = None
    ) -> str:
        """
        Generate a personalized cover letter.

        Args:
            resume: User's resume text
            job_description: Target job description
            company_name: Company name
            position: Position title
            user_name: User's name (optional)

        Returns:
            Generated cover letter
        """
        name_line = f"My name is {user_name} and I am" if user_name else "I am"

        template = """
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
        prompt_template = PromptTemplate(
            input_variables=["resume", "job_description", "company_name", "position", "name_line"],
            template=template
        )
        chain = LLMChain(llm=self.llm, prompt=prompt_template, verbose=False)
        return chain.predict(
            resume=resume,
            job_description=job_description,
            company_name=company_name,
            position=position,
            name_line=name_line
        )

    def generate_networking_email(
        self,
        recipient_name: str,
        company_name: str,
        purpose: str,
        user_background: Optional[str] = None
    ) -> str:
        """
        Generate a networking email.

        Args:
            recipient_name: Name of recipient
            company_name: Company name
            purpose: Purpose of email (e.g., "informational interview", "job inquiry")
            user_background: Brief user background (optional)

        Returns:
            Generated email
        """
        background_text = f"\n\nMy Background:\n{user_background}" if user_background else ""

        template = """
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
        prompt_template = PromptTemplate(
            input_variables=["recipient_name", "company_name", "purpose", "background_text"],
            template=template
        )
        chain = LLMChain(llm=self.llm, prompt=prompt_template, verbose=False)
        return chain.predict(
            recipient_name=recipient_name,
            company_name=company_name,
            purpose=purpose,
            background_text=background_text
        )

    def enhance_achievement(self, achievement: str) -> str:
        """
        Enhance an achievement description with impact-focused language.

        Args:
            achievement: Original achievement description

        Returns:
            Enhanced achievement description
        """
        template = """
        Original achievement:
        {achievement}

        Rewrite this achievement to be more impactful by:
        1. Using strong action verbs
        2. Adding quantifiable metrics where possible
        3. Highlighting the business impact
        4. Keeping it concise (1-2 sentences)

        Enhanced achievement:
        """
        prompt_template = PromptTemplate(input_variables=["achievement"], template=template)
        chain = LLMChain(llm=self.llm, prompt=prompt_template, verbose=False)
        return chain.predict(achievement=achievement)

# Singleton instance
_llm_service = None

def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
