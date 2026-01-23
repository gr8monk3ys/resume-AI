"""
AI service router for LLM-powered features.
"""

from fastapi import APIRouter, Depends, HTTPException

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

router = APIRouter(prefix="/api/ai", tags=["AI Services"])


@router.post("/tailor-resume", response_model=TailorResumeResponse)
async def tailor_resume(
    request: TailorResumeRequest,
    current_user: User = Depends(get_current_user),
):
    """Tailor a resume for a specific job description."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        result = llm_service.tailor_resume(
            resume=request.resume_content,
            job_description=request.job_description,
        )

        return TailorResumeResponse(
            tailored_resume=result,
            changes_made=["Tailored content for job requirements"],
            keywords_added=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to tailor resume: {str(e)}")


@router.post("/answer-question", response_model=AnswerQuestionResponse)
async def answer_question(
    request: AnswerQuestionRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate an answer for an application question."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        answer = llm_service.answer_application_question(
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
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def interview_prep(
    request: InterviewPrepRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate interview answer using STAR method."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        answer = llm_service.generate_interview_answer(
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
        raise HTTPException(
            status_code=500, detail=f"Failed to generate interview answer: {str(e)}"
        )


@router.post("/grammar-check", response_model=GrammarCorrectionResponse)
async def grammar_check(
    request: GrammarCorrectionRequest,
    current_user: User = Depends(get_current_user),
):
    """Check and correct grammar in text."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        corrected = llm_service.correct_grammar(request.text)

        return GrammarCorrectionResponse(
            corrected_text=corrected,
            corrections_made=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check grammar: {str(e)}")


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
        suggestions = llm_service.optimize_resume(
            resume=resume_content,
            job_description=job_description,
        )

        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to optimize resume: {str(e)}")


@router.post("/networking-email", response_model=NetworkingEmailResponse)
async def generate_networking_email(
    request: NetworkingEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a professional networking email."""
    from app.services.llm_service import get_llm_service

    try:
        llm_service = get_llm_service()
        full_email = llm_service.generate_networking_email(
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
        raise HTTPException(
            status_code=500, detail=f"Failed to generate networking email: {str(e)}"
        )


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
        analysis = analyzer.analyze_resume(request.resume_content, request.job_description)

        missing_keywords = request.missing_keywords or analysis.get("missing_keywords", [])
        matched_keywords = analysis.get("keyword_matches", [])

        # Get AI suggestions for incorporating keywords
        llm_service = get_llm_service()
        suggestions = llm_service.suggest_keyword_additions(
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
        raise HTTPException(
            status_code=500, detail=f"Failed to get keyword suggestions: {str(e)}"
        )


@router.post("/job-match-score", response_model=JobMatchScoreResponse)
async def calculate_job_match_score(
    request: JobMatchScoreRequest,
    current_user: User = Depends(get_current_user),
):
    """Calculate how well a resume matches a job description."""
    from app.services.resume_analyzer import ATSAnalyzer

    try:
        analyzer = ATSAnalyzer()
        analysis = analyzer.analyze_resume(request.resume_content, request.job_description)

        return JobMatchScoreResponse(
            score=analysis.get("ats_score", 0),
            score_breakdown=analysis.get("score_breakdown", {}),
            missing_keywords=analysis.get("missing_keywords", []),
            matched_keywords=analysis.get("keyword_matches", []),
            suggestions=analysis.get("suggestions", []),
            found_skills=analysis.get("found_skills", {}),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate job match score: {str(e)}"
        )
