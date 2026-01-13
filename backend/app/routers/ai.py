"""
AI service router for LLM-powered features.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.schemas.ai import (
    TailorResumeRequest,
    TailorResumeResponse,
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    GrammarCorrectionRequest,
    GrammarCorrectionResponse,
)
from app.middleware.auth import get_current_user

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
        raise HTTPException(status_code=500, detail=f"Failed to generate interview answer: {str(e)}")


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
