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
from app.schemas.job_import import (
    BulkImportResponse,
    BulkJobImportRequest,
    GitHubRepoFilter,
    GitHubRepoImportRequest,
    GitHubRepoImportResponse,
    ImportError,
    ImportResult,
    JobData,
    JobImportRequest,
    JobImportResponse,
    JobPreviewResponse,
    JobSource,
    JobType,
)
from app.schemas.pagination import (
    PaginatedResponse,
    PaginationParams,
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
from app.schemas.scheduler import (
    JobAlertCreate,
    JobAlertResponse,
    JobSchedulerStatus,
    ScheduledJobCreate,
    ScheduledJobResponse,
    ScheduledJobStatus,
    ScheduledJobUpdate,
    SchedulerStatusResponse,
    ScrapeCriteria,
    ScrapeSource,
    TriggerJobResponse,
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
    # Job Import
    "JobImportRequest",
    "JobImportResponse",
    "BulkJobImportRequest",
    "BulkImportResponse",
    "GitHubRepoImportRequest",
    "GitHubRepoImportResponse",
    "GitHubRepoFilter",
    "JobData",
    "JobSource",
    "JobType",
    "ImportResult",
    "ImportError",
    "JobPreviewResponse",
    # Pagination
    "PaginatedResponse",
    "PaginationParams",
    # Scheduler
    "ScheduledJobCreate",
    "ScheduledJobUpdate",
    "ScheduledJobResponse",
    "SchedulerStatusResponse",
    "TriggerJobResponse",
    "JobSchedulerStatus",
    "ScheduledJobStatus",
    "ScrapeSource",
    "ScrapeCriteria",
    "JobAlertCreate",
    "JobAlertResponse",
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
