"""
AI service router for LLM-powered features.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    GrammarCorrectionRequest,
    GrammarCorrectionResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    JobMatchScoreRequest,
    JobMatchScoreResponse,
    KeywordSuggestionsRequest,
    KeywordSuggestionsResponse,
    NetworkingEmailRequest,
    NetworkingEmailResponse,
    TailorResumeRequest,
    TailorResumeResponse,
)
from app.schemas.ats import (
    ATSAnalysisRequest,
    ATSAnalysisResponse,
    ExperienceMatch,
    ExperienceMatchRequest,
    ExperienceMatchResponse,
    ExtractedKeywords,
    ExtractKeywordsRequest,
    ExtractKeywordsResponse,
    KeywordBreakdown,
)
from app.schemas.ats import KeywordSuggestion as ATSKeywordSuggestion
from app.schemas.ats import KeywordSuggestionsRequest as ATSKeywordSuggestionsRequest
from app.schemas.ats import KeywordSuggestionsResponse as ATSKeywordSuggestionsResponse
from app.schemas.ats import (
    SectionScores,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Services"])


def _handle_ai_error(e: Exception, operation: str, user_id: int) -> HTTPException:
    """
    Handle AI service errors with appropriate logging and error messages.

    In production, returns generic error messages to avoid exposing internal details.
    In debug mode, includes the actual error message for debugging.
    """
    settings = get_settings()
    logger.error(f"{operation} failed for user {user_id}: {str(e)}")

    if settings.debug:
        return HTTPException(status_code=500, detail=f"{operation} failed: {str(e)}")
    else:
        return HTTPException(status_code=500, detail=f"{operation} failed. Please try again later.")


@router.post("/tailor-resume", response_model=TailorResumeResponse)
async def tailor_resume(
    request: TailorResumeRequest,
    current_user: User = Depends(get_current_user),
):
    """Tailor a resume for a specific job description."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        result = await asyncio.to_thread(
            llm_service.tailor_resume,
            resume=request.resume_content,
            job_description=request.job_description,
        )

        return TailorResumeResponse(
            tailored_resume=result,
            changes_made=["Tailored content for job requirements"],
            keywords_added=[],
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to tailor resume", current_user.id)


@router.post("/answer-question", response_model=AnswerQuestionResponse)
async def answer_question(
    request: AnswerQuestionRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate an answer for an application question."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        answer = await asyncio.to_thread(
            llm_service.answer_application_question,
            question=request.question,
            question_type=request.question_type,
            resume=request.resume_content or "",
            job_description=request.job_description or "",
        )

        return AnswerQuestionResponse(
            answer=answer,
            tips=["Personalize further with specific examples", "Keep response concise"],
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to generate answer", current_user.id)


@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def interview_prep(
    request: InterviewPrepRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate interview answer using STAR method."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        answer = await asyncio.to_thread(
            llm_service.generate_interview_answer,
            question=request.question,
            resume=request.resume_content or "",
            job_description=request.job_description or "",
        )

        # Parse STAR components if available
        response = InterviewPrepResponse(
            answer=answer,
            tips=[
                "Practice delivering this answer out loud",
                "Prepare follow-up examples",
                "Adjust specifics based on the company",
            ],
        )

        return response
    except Exception as e:
        raise _handle_ai_error(e, "Failed to generate interview answer", current_user.id)


@router.post("/grammar-check", response_model=GrammarCorrectionResponse)
async def grammar_check(
    request: GrammarCorrectionRequest,
    current_user: User = Depends(get_current_user),
):
    """Check and correct grammar in text."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        corrected = await asyncio.to_thread(
            llm_service.correct_grammar,
            request.text,
        )

        return GrammarCorrectionResponse(
            corrected_text=corrected,
            corrections_made=[],
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to check grammar", current_user.id)


@router.post("/optimize-resume")
async def optimize_resume(
    resume_content: str,
    job_description: str = "",
    current_user: User = Depends(get_current_user),
):
    """Get AI-powered resume optimization suggestions."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        suggestions = await asyncio.to_thread(
            llm_service.optimize_resume,
            resume=resume_content,
            job_description=job_description,
        )

        return {"suggestions": suggestions}
    except Exception as e:
        raise _handle_ai_error(e, "Failed to optimize resume", current_user.id)


@router.post("/networking-email", response_model=NetworkingEmailResponse)
async def generate_networking_email(
    request: NetworkingEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a professional networking email."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        full_email = await asyncio.to_thread(
            llm_service.generate_networking_email,
            recipient=request.recipient_name,
            company=request.company,
            purpose=request.purpose,
            background=request.background,
        )

        # Parse subject and body from the generated email
        lines = full_email.strip().split("\n")
        subject = ""
        body_lines = []
        body_started = False

        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line[8:].strip()
            elif subject and not body_started:
                # Skip empty lines between subject and body
                if line.strip():
                    body_started = True
                    body_lines.append(line)
            elif body_started:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        # Fallback if parsing fails
        if not subject:
            subject = f"Introduction - Interest in {request.company}"
        if not body:
            body = full_email

        return NetworkingEmailResponse(
            subject=subject,
            body=body,
            full_email=full_email,
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to generate networking email", current_user.id)


@router.post("/keyword-suggestions", response_model=KeywordSuggestionsResponse)
async def get_keyword_suggestions(
    request: KeywordSuggestionsRequest,
    current_user: User = Depends(get_current_user),
):
    """Get AI-powered suggestions for adding missing keywords to a resume."""
    from app.services.llm_service import get_llm_service
    from app.services.resume_analyzer import ATSAnalyzer

    try:
        # Analyze resume to find missing keywords if not provided
        analyzer = ATSAnalyzer()
        analysis = await asyncio.to_thread(
            analyzer.analyze_resume,
            request.resume_content,
            request.job_description,
        )

        missing_keywords = request.missing_keywords or analysis.get("missing_keywords", [])
        matched_keywords = analysis.get("keyword_matches", [])

        # Get AI suggestions for incorporating keywords
        llm_service = get_llm_service()
        suggestions = await asyncio.to_thread(
            llm_service.suggest_keyword_additions,
            resume=request.resume_content,
            job_description=request.job_description,
            missing_keywords=missing_keywords,
        )

        return KeywordSuggestionsResponse(
            suggestions=suggestions,
            missing_keywords=missing_keywords,
            matched_keywords=matched_keywords,
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to get keyword suggestions", current_user.id)


@router.post("/job-match-score", response_model=JobMatchScoreResponse)
async def calculate_job_match_score(
    request: JobMatchScoreRequest,
    current_user: User = Depends(get_current_user),
):
    """Calculate how well a resume matches a job description."""
    from app.services.resume_analyzer import ATSAnalyzer

    try:
        analyzer = ATSAnalyzer()
        analysis = await asyncio.to_thread(
            analyzer.analyze_resume,
            request.resume_content,
            request.job_description,
        )

        return JobMatchScoreResponse(
            score=analysis.get("ats_score", 0),
            score_breakdown=analysis.get("score_breakdown", {}),
            missing_keywords=analysis.get("missing_keywords", []),
            matched_keywords=analysis.get("keyword_matches", []),
            suggestions=analysis.get("suggestions", []),
            found_skills=analysis.get("found_skills", {}),
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to calculate job match score", current_user.id)


# =============================================================================
# ATS Analyzer Endpoints (Algorithmic - No LLM Required)
# =============================================================================


@router.post("/ats-analyze", response_model=ATSAnalysisResponse)
async def ats_analyze(
    request: ATSAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Perform comprehensive ATS analysis of a resume against a job description.

    This endpoint uses algorithmic analysis (no LLM required) to:
    - Calculate overall ATS compatibility score
    - Identify matching and missing keywords
    - Score different resume sections
    - Analyze experience level match
    - Generate actionable improvement suggestions

    The analysis is purely algorithmic and works without any external API calls,
    making it fast and reliable.
    """
    from app.services.ats_analyzer import get_ats_analyzer

    try:
        analyzer = get_ats_analyzer(use_llm=request.use_llm_suggestions)
        result = analyzer.analyze_resume(
            resume=request.resume_content,
            job_description=request.job_description,
        )

        return ATSAnalysisResponse(
            overall_score=result.overall_score,
            keyword_match_score=result.keyword_match_score,
            formatting_score=result.formatting_score,
            section_scores=SectionScores(**result.section_scores),
            missing_keywords=result.missing_keywords,
            matched_keywords=result.matched_keywords,
            suggestions=result.suggestions,
            experience_match=ExperienceMatch(**result.experience_match),
            keyword_breakdown=KeywordBreakdown(**result.keyword_breakdown),
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to analyze resume", current_user.id)


@router.post("/extract-keywords", response_model=ExtractKeywordsResponse)
async def extract_keywords(
    request: ExtractKeywordsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Extract and categorize keywords from text (typically a job description).

    Keywords are categorized into:
    - technical_skills: Programming languages, frameworks, tools
    - soft_skills: Interpersonal and professional skills
    - certifications: Professional certifications
    - education: Educational requirements
    - experience_years: Experience level requirements

    This is useful for understanding what a job posting is looking for
    and identifying keywords to target in your resume.
    """
    from app.services.ats_analyzer import get_ats_analyzer

    try:
        analyzer = get_ats_analyzer()
        keywords = analyzer.extract_keywords(request.text)

        total = sum(len(v) if isinstance(v, list) else 0 for v in keywords.values())

        return ExtractKeywordsResponse(
            keywords=ExtractedKeywords(**keywords),
            total_keywords=total,
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to extract keywords", current_user.id)


@router.post("/ats-keyword-suggestions", response_model=ATSKeywordSuggestionsResponse)
async def ats_keyword_suggestions(
    request: ATSKeywordSuggestionsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Get actionable suggestions for adding missing keywords to a resume.

    For each missing keyword, provides:
    - Category (technical skill, soft skill, certification, etc.)
    - Priority level (high, medium, low)
    - Specific suggestion for how to add the keyword naturally
    - Recommended resume section for the keyword

    This endpoint provides algorithmic suggestions. For AI-enhanced suggestions
    that consider context more deeply, use the /keyword-suggestions endpoint
    with LLM integration.
    """
    from app.services.ats_analyzer import get_ats_analyzer

    try:
        analyzer = get_ats_analyzer()

        # Get missing keywords if not provided
        if request.missing_keywords:
            missing = request.missing_keywords
        else:
            missing = analyzer.get_missing_keywords(request.resume_content, request.job_description)

        # Get suggestions for missing keywords
        suggestions = analyzer.get_keyword_suggestions(missing[: request.max_suggestions])

        # Also get matched keywords for reference
        result = analyzer.analyze_resume(request.resume_content, request.job_description)

        # Calculate match percentage
        total_keywords = len(missing) + len(result.matched_keywords)
        match_percentage = (
            (len(result.matched_keywords) / total_keywords * 100) if total_keywords > 0 else 0
        )

        return ATSKeywordSuggestionsResponse(
            suggestions=[
                ATSKeywordSuggestion(
                    keyword=s.keyword,
                    category=s.category,
                    priority=s.priority,
                    suggestion=s.suggestion,
                    section_recommendation=s.section_recommendation,
                )
                for s in suggestions
            ],
            missing_keywords=missing,
            matched_keywords=result.matched_keywords,
            match_percentage=round(match_percentage, 1),
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to get keyword suggestions", current_user.id)


@router.post("/experience-match", response_model=ExperienceMatchResponse)
async def calculate_experience_match(
    request: ExperienceMatchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Calculate how well a resume's experience matches a job's requirements.

    Analyzes:
    - Years of experience mentioned in job description
    - Experience level (entry, mid, senior, executive)
    - Years of experience evident in resume
    - Position history and duration

    Returns a match level (strong, moderate, weak, undetermined) with
    recommendations for how to present your experience effectively.
    """
    from app.services.ats_analyzer import get_ats_analyzer

    try:
        analyzer = get_ats_analyzer()

        experience_match = analyzer.calculate_experience_match(
            request.resume_content, request.job_description
        )

        # Also get the raw requirements for detailed view
        jd_requirements, resume_experience = analyzer.extract_experience_details(
            request.resume_content, request.job_description
        )

        return ExperienceMatchResponse(
            match=ExperienceMatch(**experience_match),
            job_requirements=jd_requirements,
            resume_experience=resume_experience,
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to calculate experience match", current_user.id)
