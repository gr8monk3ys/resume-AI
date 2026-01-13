"""
Resumes router.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.models.resume import Resume
from app.schemas.resume import (
    ResumeCreate,
    ResumeUpdate,
    ResumeResponse,
    ATSAnalysisRequest,
    ATSAnalysisResponse,
)
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])


def get_user_profile(user: User, db: Session) -> Profile:
    """Get or create user profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, name=user.full_name or user.username)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=List[ResumeResponse])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all resumes for current user."""
    profile = get_user_profile(current_user, db)
    resumes = db.query(Resume).filter(Resume.profile_id == profile.id).order_by(Resume.updated_at.desc()).all()
    return resumes


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    resume_data: ResumeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new resume."""
    profile = get_user_profile(current_user, db)

    resume = Resume(
        profile_id=profile.id,
        version_name=resume_data.version_name,
        content=resume_data.content,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return resume


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific resume."""
    profile = get_user_profile(current_user, db)

    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.profile_id == profile.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return resume


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: int,
    resume_data: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a resume."""
    profile = get_user_profile(current_user, db)

    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.profile_id == profile.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    update_data = resume_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resume, field, value)

    db.commit()
    db.refresh(resume)

    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a resume."""
    profile = get_user_profile(current_user, db)

    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.profile_id == profile.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    db.delete(resume)
    db.commit()


@router.post("/analyze", response_model=ATSAnalysisResponse)
async def analyze_resume(
    request: ATSAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze resume for ATS compatibility."""
    from app.services.resume_analyzer import ATSAnalyzer

    analyzer = ATSAnalyzer()
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
    from app.services.file_parser import parse_file

    # Validate file type
    allowed_types = ["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: txt, pdf, docx"
        )

    # Read file content
    content = await file.read()

    # Determine file type
    if file.content_type == "text/plain":
        file_type = "txt"
    elif file.content_type == "application/pdf":
        file_type = "pdf"
    else:
        file_type = "docx"

    # Parse file
    try:
        parsed_content = parse_file(content, file_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    return {
        "filename": file.filename,
        "content": parsed_content,
    }
