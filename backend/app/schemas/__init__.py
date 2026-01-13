"""
Pydantic schemas for request/response validation.
"""
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    TokenData,
)
from app.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
)
from app.schemas.resume import (
    ResumeCreate,
    ResumeUpdate,
    ResumeResponse,
    ATSAnalysisRequest,
    ATSAnalysisResponse,
)
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobStatus,
)
from app.schemas.cover_letter import (
    CoverLetterCreate,
    CoverLetterResponse,
)
from app.schemas.ai import (
    TailorResumeRequest,
    TailorResumeResponse,
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
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
