"""
AI service schemas.
"""

from typing import List, Optional

from pydantic import BaseModel


class TailorResumeRequest(BaseModel):
    """Schema for resume tailoring request."""

    resume_content: str
    job_description: str
    focus_areas: Optional[List[str]] = None


class TailorResumeResponse(BaseModel):
    """Schema for resume tailoring response."""

    tailored_resume: str
    changes_made: List[str]
    keywords_added: List[str]


class AnswerQuestionRequest(BaseModel):
    """Schema for answering application questions."""

    question: str
    question_type: Optional[str] = (
        "general"  # general, behavioral, motivation, salary, weakness, strength
    )
    resume_content: Optional[str] = None
    job_description: Optional[str] = None
    max_length: Optional[int] = 300


class AnswerQuestionResponse(BaseModel):
    """Schema for question answer response."""

    answer: str
    tips: Optional[List[str]] = None


class InterviewPrepRequest(BaseModel):
    """Schema for interview preparation request."""

    question: str
    resume_content: Optional[str] = None
    job_description: Optional[str] = None
    use_star_method: bool = True


class InterviewPrepResponse(BaseModel):
    """Schema for interview prep response."""

    answer: str
    situation: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    tips: List[str]


class GrammarCorrectionRequest(BaseModel):
    """Schema for grammar correction request."""

    text: str


class GrammarCorrectionResponse(BaseModel):
    """Schema for grammar correction response."""

    corrected_text: str
    corrections_made: List[str]


class NetworkingEmailRequest(BaseModel):
    """Schema for networking email generation request."""

    recipient_name: str
    company: str
    purpose: str
    background: Optional[str] = None


class NetworkingEmailResponse(BaseModel):
    """Schema for networking email response."""

    subject: str
    body: str
    full_email: str


class KeywordSuggestionsRequest(BaseModel):
    """Schema for keyword suggestions request."""

    resume_content: str
    job_description: str
    missing_keywords: Optional[List[str]] = None


class KeywordSuggestionsResponse(BaseModel):
    """Schema for keyword suggestions response."""

    suggestions: str
    missing_keywords: List[str]
    matched_keywords: List[str]


class JobMatchScoreRequest(BaseModel):
    """Schema for job match score calculation request."""

    resume_content: str
    job_description: str


class JobMatchScoreResponse(BaseModel):
    """Schema for job match score response."""

    score: int
    score_breakdown: dict
    missing_keywords: List[str]
    matched_keywords: List[str]
    suggestions: List[str]
    found_skills: dict
