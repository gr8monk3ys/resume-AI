"""
ATS (Applicant Tracking System) Analyzer Schemas.

Pydantic models for ATS analysis requests and responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Request Schemas
# =============================================================================


class ATSAnalysisRequest(BaseModel):
    """Request schema for full ATS analysis."""

    resume_content: str = Field(
        ...,
        description="The resume content to analyze",
        min_length=50,
    )
    job_description: str = Field(
        ...,
        description="The job description to match against",
        min_length=50,
    )
    use_llm_suggestions: bool = Field(
        default=False,
        description="Whether to use LLM for enhanced suggestions (optional)",
    )


class ExtractKeywordsRequest(BaseModel):
    """Request schema for keyword extraction."""

    text: str = Field(
        ...,
        description="The text to extract keywords from (typically a job description)",
        min_length=20,
    )


class KeywordSuggestionsRequest(BaseModel):
    """Request schema for keyword addition suggestions."""

    resume_content: str = Field(
        ...,
        description="The resume content",
        min_length=50,
    )
    job_description: str = Field(
        ...,
        description="The job description",
        min_length=50,
    )
    missing_keywords: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific missing keywords to get suggestions for",
    )
    max_suggestions: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of suggestions to return",
    )


class ExperienceMatchRequest(BaseModel):
    """Request schema for experience match calculation."""

    resume_content: str = Field(
        ...,
        description="The resume content",
        min_length=50,
    )
    job_description: str = Field(
        ...,
        description="The job description",
        min_length=50,
    )


# =============================================================================
# Response Schemas
# =============================================================================


class KeywordBreakdown(BaseModel):
    """Breakdown of keywords found in resume."""

    technical_skills_found: List[str] = Field(
        default_factory=list,
        description="Technical skills identified in the resume",
    )
    soft_skills_found: List[str] = Field(
        default_factory=list,
        description="Soft skills identified in the resume",
    )
    certifications_found: List[str] = Field(
        default_factory=list,
        description="Certifications identified in the resume",
    )
    action_verbs_found: List[str] = Field(
        default_factory=list,
        description="Action verbs identified in the resume",
    )


class SectionScores(BaseModel):
    """Scores for different resume sections."""

    sections: int = Field(
        default=0,
        ge=0,
        le=20,
        description="Score for having standard resume sections (0-20)",
    )
    technical_skills: int = Field(
        default=0,
        ge=0,
        le=25,
        description="Score for technical skills match (0-25)",
    )
    soft_skills: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Score for soft skills match (0-15)",
    )
    action_verbs: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Score for action verb usage (0-15)",
    )
    quantifiable_results: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Score for quantifiable achievements (0-15)",
    )
    length: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Score for appropriate resume length (0-10)",
    )


class ExperienceRequirement(BaseModel):
    """Experience requirement extracted from text."""

    type: str = Field(
        ...,
        description="Type of requirement: years, range, minimum, or level",
    )
    value: Optional[int] = Field(
        default=None,
        description="Years value (for years/minimum types)",
    )
    min: Optional[int] = Field(
        default=None,
        description="Minimum years (for range type)",
    )
    max: Optional[int] = Field(
        default=None,
        description="Maximum years (for range type)",
    )
    level: Optional[str] = Field(
        default=None,
        description="Experience level: entry, mid, senior, executive, intern",
    )
    text: str = Field(
        ...,
        description="Original text matched",
    )


class ExperienceMatch(BaseModel):
    """Experience match analysis result."""

    job_requires: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Experience requirements from job description",
    )
    resume_shows: Dict[str, Any] = Field(
        default_factory=dict,
        description="Experience information from resume",
    )
    match_level: str = Field(
        ...,
        description="Match level: strong, moderate, weak, undetermined",
    )
    recommendation: str = Field(
        default="",
        description="Recommendation based on experience match",
    )


class ATSAnalysisResponse(BaseModel):
    """Response schema for full ATS analysis."""

    overall_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall ATS compatibility score (0-100)",
    )
    keyword_match_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Score based on keyword matches (0-100)",
    )
    formatting_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Score based on resume formatting (0-100)",
    )
    section_scores: SectionScores = Field(
        ...,
        description="Detailed scores for each resume section",
    )
    missing_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords from job description missing in resume",
    )
    matched_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords that match between resume and job description",
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Actionable suggestions for improvement",
    )
    experience_match: ExperienceMatch = Field(
        ...,
        description="Experience level match analysis",
    )
    keyword_breakdown: KeywordBreakdown = Field(
        ...,
        description="Detailed breakdown of keywords found",
    )


class ExtractedKeywords(BaseModel):
    """Extracted keywords categorized by type."""

    technical_skills: List[str] = Field(
        default_factory=list,
        description="Technical skills (languages, frameworks, tools)",
    )
    soft_skills: List[str] = Field(
        default_factory=list,
        description="Soft skills (communication, leadership, etc.)",
    )
    tools: List[str] = Field(
        default_factory=list,
        description="Software tools and platforms",
    )
    certifications: List[str] = Field(
        default_factory=list,
        description="Professional certifications",
    )
    education: List[str] = Field(
        default_factory=list,
        description="Education-related keywords",
    )
    experience_years: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Experience requirements extracted",
    )


class ExtractKeywordsResponse(BaseModel):
    """Response schema for keyword extraction."""

    keywords: ExtractedKeywords = Field(
        ...,
        description="Extracted keywords categorized by type",
    )
    total_keywords: int = Field(
        ...,
        ge=0,
        description="Total number of keywords extracted",
    )


class KeywordSuggestion(BaseModel):
    """Suggestion for adding a missing keyword."""

    keyword: str = Field(
        ...,
        description="The missing keyword",
    )
    category: str = Field(
        ...,
        description="Category: technical_skill, soft_skill, certification, education",
    )
    priority: str = Field(
        ...,
        description="Priority level: high, medium, low",
    )
    suggestion: str = Field(
        ...,
        description="Actionable suggestion for adding this keyword",
    )
    section_recommendation: str = Field(
        ...,
        description="Recommended resume section for this keyword",
    )


class KeywordSuggestionsResponse(BaseModel):
    """Response schema for keyword suggestions."""

    suggestions: List[KeywordSuggestion] = Field(
        default_factory=list,
        description="List of keyword suggestions",
    )
    missing_keywords: List[str] = Field(
        default_factory=list,
        description="All missing keywords identified",
    )
    matched_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords already present in resume",
    )
    match_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of job keywords found in resume",
    )


class ExperienceMatchResponse(BaseModel):
    """Response schema for experience match calculation."""

    match: ExperienceMatch = Field(
        ...,
        description="Experience match analysis",
    )
    job_requirements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Parsed experience requirements from job description",
    )
    resume_experience: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parsed experience from resume",
    )
