"""
Job filter schemas for CRUD operations.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# Enums matching the model enums
class CompanyFilterType(str, Enum):
    """Company filter type."""

    BLACKLIST = "blacklist"
    WHITELIST = "whitelist"


class KeywordFilterType(str, Enum):
    """Keyword filter type."""

    EXCLUDE = "exclude"
    REQUIRE = "require"


class KeywordAppliesTo(str, Enum):
    """Where keyword filter applies."""

    TITLE = "title"
    DESCRIPTION = "description"
    BOTH = "both"


class QuestionType(str, Enum):
    """Application question type."""

    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    BOOLEAN = "boolean"


# Company Filter Schemas
class CompanyFilterCreate(BaseModel):
    """Schema for creating a company filter."""

    company_name: str = Field(..., min_length=1, max_length=255)
    filter_type: CompanyFilterType = CompanyFilterType.BLACKLIST
    reason: Optional[str] = None


class CompanyFilterResponse(BaseModel):
    """Schema for company filter response."""

    id: int
    user_id: int
    company_name: str
    filter_type: CompanyFilterType
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Keyword Filter Schemas
class KeywordFilterCreate(BaseModel):
    """Schema for creating a keyword filter."""

    keyword: str = Field(..., min_length=1, max_length=255)
    filter_type: KeywordFilterType = KeywordFilterType.EXCLUDE
    applies_to: KeywordAppliesTo = KeywordAppliesTo.BOTH


class KeywordFilterResponse(BaseModel):
    """Schema for keyword filter response."""

    id: int
    user_id: int
    keyword: str
    filter_type: KeywordFilterType
    applies_to: KeywordAppliesTo
    created_at: datetime

    class Config:
        from_attributes = True


# Application Question Schemas
class ApplicationQuestionCreate(BaseModel):
    """Schema for creating an application question template."""

    question_pattern: str = Field(..., min_length=1, max_length=500)
    answer: str
    question_type: QuestionType = QuestionType.TEXT
    category: Optional[str] = Field(None, max_length=100)


class ApplicationQuestionUpdate(BaseModel):
    """Schema for updating an application question template."""

    question_pattern: Optional[str] = Field(None, min_length=1, max_length=500)
    answer: Optional[str] = None
    question_type: Optional[QuestionType] = None
    category: Optional[str] = Field(None, max_length=100)


class ApplicationQuestionResponse(BaseModel):
    """Schema for application question response."""

    id: int
    user_id: int
    question_pattern: str
    answer: str
    question_type: QuestionType
    category: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Job Check Schemas
class JobCheckRequest(BaseModel):
    """Schema for checking if a job matches filters."""

    title: str
    company: str
    description: Optional[str] = None


class FilterMatch(BaseModel):
    """Schema for a single filter match result."""

    filter_type: str
    filter_id: int
    matched_value: str
    action: str  # 'block' or 'require'
    reason: Optional[str] = None


class JobCheckResponse(BaseModel):
    """Schema for job check response."""

    passes_filters: bool
    company_filter_match: Optional[FilterMatch] = None
    keyword_matches: List[FilterMatch] = []
    matching_questions: List[ApplicationQuestionResponse] = []
    summary: str


# Import Defaults Response
class ImportDefaultsResponse(BaseModel):
    """Schema for import defaults response."""

    success: bool
    imported_count: int
    skipped_count: int
    message: str


# List Response Schemas (for pagination support)
class CompanyFilterListResponse(BaseModel):
    """Schema for company filter list response."""

    items: List[CompanyFilterResponse]
    total: int


class KeywordFilterListResponse(BaseModel):
    """Schema for keyword filter list response."""

    items: List[KeywordFilterResponse]
    total: int


class ApplicationQuestionListResponse(BaseModel):
    """Schema for application question list response."""

    items: List[ApplicationQuestionResponse]
    total: int
