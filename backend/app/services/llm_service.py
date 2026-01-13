"""
LLM Service for AI-powered features.
Ported from Streamlit version to work with FastAPI.
"""
import os
from typing import Optional
from functools import lru_cache

from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings

settings = get_settings()


class LLMService:
    """Service for managing LLM interactions."""

    def __init__(self, model_name: str = None, temperature: float = 0.7):
        """
        Initialize LLM service.

        Args:
            model_name: OpenAI model to use (defaults to config)
            temperature: Temperature for response generation
        """
        api_key = settings.openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )

        self.model_name = model_name or settings.openai_model
        self.temperature = temperature
        self.llm = OpenAI(
            model_name=self.model_name,
            temperature=temperature,
            request_timeout=settings.openai_request_timeout,
            api_key=api_key,
        )

    def _invoke_chain(self, template: str, **kwargs) -> str:
        """Invoke a prompt chain with the given template and variables."""
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke(kwargs)
        return result if isinstance(result, str) else str(result)

    def correct_grammar(self, text: str) -> str:
        """Correct grammatical errors in text."""
        template = """
        {text}

        You are an expert proofreader. Please correct any grammatical errors in the text above.
        Maintain the original formatting and structure. Only fix grammar, spelling, and punctuation.
        """
        return self._invoke_chain(template, text=text)

    def optimize_resume(self, resume: str, job_description: str) -> str:
        """Optimize resume based on job description."""
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
        return self._invoke_chain(template, job_description=job_description, resume=resume)

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
        return self._invoke_chain(
            template,
            resume=resume,
            job_description=job_description,
            company_name=company_name,
            position=position,
            name_line=name_line
        )

    def tailor_resume(
        self,
        resume: str,
        job_description: str,
        company_name: str = "",
        position: str = ""
    ) -> str:
        """Generate a tailored version of the resume for a specific job."""
        template = """
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
        return self._invoke_chain(
            template,
            resume=resume,
            job_description=job_description,
            company_name=company_name or "Target Company",
            position=position or "Target Position"
        )

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

        template = """
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
        return self._invoke_chain(
            template,
            question=question,
            resume=resume,
            job_description=job_description,
            instruction=instruction
        )

    def generate_interview_answer(
        self,
        question: str,
        resume: str,
        job_description: str
    ) -> str:
        """Generate a sample interview answer using STAR method."""
        template = """
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
        return self._invoke_chain(
            template,
            question=question,
            resume=resume,
            job_description=job_description
        )


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
