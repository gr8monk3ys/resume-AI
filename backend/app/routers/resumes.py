"""
Resumes router.
"""

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, safe_commit
from app.middleware.auth import get_current_user
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.resume import (
    ATSAnalysisRequest,
    ATSAnalysisResponse,
    ResumeCreate,
    ResumeResponse,
    ResumeUpdate,
)
from app.services.file_parser import parse_file

# Module-level imports for better performance (avoid repeated lazy imports)
from app.services.resume_analyzer import ATSAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])

# Singleton ATSAnalyzer instance to avoid repeated instantiation
_ats_analyzer: Optional[ATSAnalyzer] = None


def get_ats_analyzer() -> ATSAnalyzer:
    """Get or create the singleton ATSAnalyzer instance."""
    global _ats_analyzer
    if _ats_analyzer is None:
        _ats_analyzer = ATSAnalyzer()
    return _ats_analyzer


def get_user_profile(user: User, db: Session) -> Profile:
    """Get or create user profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, name=user.full_name or user.username)
        db.add(profile)
        safe_commit(db, "create profile")
        db.refresh(profile)
    return profile


@router.get("", response_model=PaginatedResponse[ResumeResponse])
async def list_resumes(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List resumes for current user with pagination.

    Args:
        pagination: Pagination parameters (page, limit)

    Returns:
        Paginated list of resumes with metadata
    """
    profile = get_user_profile(current_user, db)

    # Build base query
    query = db.query(Resume).filter(Resume.profile_id == profile.id)

    # Get total count efficiently using SQL COUNT
    total = query.count()

    # Apply pagination and ordering
    resumes = (
        query.order_by(Resume.updated_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )

    return PaginatedResponse.create(
        items=resumes,
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    resume_data: ResumeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new resume."""
    profile = get_user_profile(current_user, db)

    resume = Resume(
        profile_id=profile.id,
        version_name=resume_data.version_name,
        content=resume_data.content,
    )
    db.add(resume)
    safe_commit(db, "create resume")
    db.refresh(resume)

    return resume


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get a specific resume."""
    profile = get_user_profile(current_user, db)

    resume = (
        db.query(Resume).filter(Resume.id == resume_id, Resume.profile_id == profile.id).first()
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return resume


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: int,
    resume_data: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a resume."""
    profile = get_user_profile(current_user, db)

    resume = (
        db.query(Resume).filter(Resume.id == resume_id, Resume.profile_id == profile.id).first()
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    update_data = resume_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resume, field, value)

    safe_commit(db, "update resume")
    db.refresh(resume)

    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete a resume."""
    profile = get_user_profile(current_user, db)

    resume = (
        db.query(Resume).filter(Resume.id == resume_id, Resume.profile_id == profile.id).first()
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    db.delete(resume)
    safe_commit(db, "delete resume")


@router.post("/analyze", response_model=ATSAnalysisResponse)
async def analyze_resume(
    request: ATSAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze resume for ATS compatibility."""
    # Use singleton analyzer to avoid repeated instantiation
    analyzer = get_ats_analyzer()
    result = analyzer.analyze_resume(request.resume_content, request.job_description)

    return ATSAnalysisResponse(
        ats_score=result.get("ats_score", 0),
        suggestions=result.get("suggestions", []),
        keyword_matches=result.get("keyword_matches", []),
        missing_keywords=result.get("missing_keywords", []),
        score_breakdown=result.get("score_breakdown", {}),
    )


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload and parse a resume file."""
    settings = get_settings()
    max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert MB to bytes

    # Validate file type
    allowed_types = [
        "text/plain",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: txt, pdf, docx")

    # Check file size before reading entire content
    # First, check Content-Length header if available
    if file.size is not None and file.size > max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb} MB.",
        )

    # Read file content with size limit
    content = await file.read()

    # Verify actual content size (in case Content-Length was missing or incorrect)
    if len(content) > max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb} MB.",
        )

    # Determine file type
    if file.content_type == "text/plain":
        file_type = "txt"
    elif file.content_type == "application/pdf":
        file_type = "pdf"
    else:
        file_type = "docx"

    # Parse file (run in thread pool to avoid blocking async event loop)
    try:
        parsed_content = await asyncio.to_thread(parse_file, content, file_type)
    except ValueError as e:
        # ValueError is raised by our security checks - safe to show
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log detailed error server-side, return generic message to client
        settings = get_settings()
        logger.error(f"Failed to parse file for user {current_user.id}: {str(e)}")
        if settings.debug:
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to parse file. Please ensure the file is valid and try again.",
            )

    return {
        "filename": file.filename,
        "content": parsed_content,
    }
