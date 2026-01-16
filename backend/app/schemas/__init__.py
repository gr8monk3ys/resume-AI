"""
Pydantic schemas for request/response validation.
"""

from app.schemas.ai import (
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    TailorResumeRequest,
    TailorResumeResponse,
)
from app.schemas.cover_letter import (
    CoverLetterCreate,
    CoverLetterResponse,
)
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobStatus,
    JobUpdate,
)
from app.schemas.profile import (
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.resume import (
    ATSAnalysisRequest,
    ATSAnalysisResponse,
    ResumeCreate,
    ResumeResponse,
    ResumeUpdate,
)
from app.schemas.user import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
)

__all__ = [
    # User
    "UserCreate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenData",
    # Profile
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    # Resume
    "ResumeCreate",
    "ResumeUpdate",
    "ResumeResponse",
    "ATSAnalysisRequest",
    "ATSAnalysisResponse",
    # Job
    "JobCreate",
    "JobUpdate",
    "JobResponse",
    "JobStatus",
    # Cover Letter
    "CoverLetterCreate",
    "CoverLetterResponse",
    # AI
    "TailorResumeRequest",
    "TailorResumeResponse",
    "AnswerQuestionRequest",
    "AnswerQuestionResponse",
    "InterviewPrepRequest",
    "InterviewPrepResponse",
]
