"""
Job filters router for managing company filters, keyword filters, and application questions.
"""

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.job_filters import (
    ApplicationQuestion,
    CompanyFilter,
    CompanyFilterType,
    DEFAULT_QUESTION_TEMPLATES,
    KeywordAppliesTo,
    KeywordFilter,
    KeywordFilterType,
)
from app.models.user import User
from app.schemas.job_filters import (
    ApplicationQuestionCreate,
    ApplicationQuestionListResponse,
    ApplicationQuestionResponse,
    ApplicationQuestionUpdate,
    CompanyFilterCreate,
    CompanyFilterListResponse,
    CompanyFilterResponse,
    FilterMatch,
    ImportDefaultsResponse,
    JobCheckRequest,
    JobCheckResponse,
    KeywordFilterCreate,
    KeywordFilterListResponse,
    KeywordFilterResponse,
)

router = APIRouter(prefix="/api/filters", tags=["Job Filters"])


# ============================================================================
# Company Filter Endpoints
# ============================================================================


@router.get("/companies", response_model=CompanyFilterListResponse)
async def list_company_filters(
    filter_type: Optional[CompanyFilterType] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all company filters for current user."""
    query = db.query(CompanyFilter).filter(CompanyFilter.user_id == current_user.id)

    if filter_type:
        query = query.filter(CompanyFilter.filter_type == filter_type)

    if search:
        search_term = f"%{search}%"
        query = query.filter(CompanyFilter.company_name.ilike(search_term))

    total = query.count()
    items = query.order_by(CompanyFilter.created_at.desc()).offset(skip).limit(limit).all()

    return CompanyFilterListResponse(items=items, total=total)


@router.post(
    "/companies", response_model=CompanyFilterResponse, status_code=status.HTTP_201_CREATED
)
async def create_company_filter(
    filter_data: CompanyFilterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new company filter."""
    # Check for duplicate
    existing = (
        db.query(CompanyFilter)
        .filter(
            CompanyFilter.user_id == current_user.id,
            CompanyFilter.company_name.ilike(filter_data.company_name),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company filter for '{filter_data.company_name}' already exists",
        )

    company_filter = CompanyFilter(
        user_id=current_user.id,
        company_name=filter_data.company_name,
        filter_type=filter_data.filter_type,
        reason=filter_data.reason,
    )
    db.add(company_filter)
    db.commit()
    db.refresh(company_filter)

    return company_filter


@router.get("/companies/{filter_id}", response_model=CompanyFilterResponse)
async def get_company_filter(
    filter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific company filter."""
    company_filter = (
        db.query(CompanyFilter)
        .filter(CompanyFilter.id == filter_id, CompanyFilter.user_id == current_user.id)
        .first()
    )

    if not company_filter:
        raise HTTPException(status_code=404, detail="Company filter not found")

    return company_filter


@router.delete("/companies/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_filter(
    filter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a company filter."""
    company_filter = (
        db.query(CompanyFilter)
        .filter(CompanyFilter.id == filter_id, CompanyFilter.user_id == current_user.id)
        .first()
    )

    if not company_filter:
        raise HTTPException(status_code=404, detail="Company filter not found")

    db.delete(company_filter)
    db.commit()


@router.delete("/companies", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_company_filters(
    filter_type: Optional[CompanyFilterType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all company filters for current user (optionally filtered by type)."""
    query = db.query(CompanyFilter).filter(CompanyFilter.user_id == current_user.id)

    if filter_type:
        query = query.filter(CompanyFilter.filter_type == filter_type)

    query.delete(synchronize_session=False)
    db.commit()


# ============================================================================
# Keyword Filter Endpoints
# ============================================================================


@router.get("/keywords", response_model=KeywordFilterListResponse)
async def list_keyword_filters(
    filter_type: Optional[KeywordFilterType] = None,
    applies_to: Optional[KeywordAppliesTo] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all keyword filters for current user."""
    query = db.query(KeywordFilter).filter(KeywordFilter.user_id == current_user.id)

    if filter_type:
        query = query.filter(KeywordFilter.filter_type == filter_type)

    if applies_to:
        query = query.filter(KeywordFilter.applies_to == applies_to)

    if search:
        search_term = f"%{search}%"
        query = query.filter(KeywordFilter.keyword.ilike(search_term))

    total = query.count()
    items = query.order_by(KeywordFilter.created_at.desc()).offset(skip).limit(limit).all()

    return KeywordFilterListResponse(items=items, total=total)


@router.post(
    "/keywords", response_model=KeywordFilterResponse, status_code=status.HTTP_201_CREATED
)
async def create_keyword_filter(
    filter_data: KeywordFilterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new keyword filter."""
    # Check for duplicate
    existing = (
        db.query(KeywordFilter)
        .filter(
            KeywordFilter.user_id == current_user.id,
            KeywordFilter.keyword.ilike(filter_data.keyword),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Keyword filter for '{filter_data.keyword}' already exists",
        )

    keyword_filter = KeywordFilter(
        user_id=current_user.id,
        keyword=filter_data.keyword,
        filter_type=filter_data.filter_type,
        applies_to=filter_data.applies_to,
    )
    db.add(keyword_filter)
    db.commit()
    db.refresh(keyword_filter)

    return keyword_filter


@router.get("/keywords/{filter_id}", response_model=KeywordFilterResponse)
async def get_keyword_filter(
    filter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific keyword filter."""
    keyword_filter = (
        db.query(KeywordFilter)
        .filter(KeywordFilter.id == filter_id, KeywordFilter.user_id == current_user.id)
        .first()
    )

    if not keyword_filter:
        raise HTTPException(status_code=404, detail="Keyword filter not found")

    return keyword_filter


@router.delete("/keywords/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword_filter(
    filter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a keyword filter."""
    keyword_filter = (
        db.query(KeywordFilter)
        .filter(KeywordFilter.id == filter_id, KeywordFilter.user_id == current_user.id)
        .first()
    )

    if not keyword_filter:
        raise HTTPException(status_code=404, detail="Keyword filter not found")

    db.delete(keyword_filter)
    db.commit()


@router.delete("/keywords", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_keyword_filters(
    filter_type: Optional[KeywordFilterType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all keyword filters for current user (optionally filtered by type)."""
    query = db.query(KeywordFilter).filter(KeywordFilter.user_id == current_user.id)

    if filter_type:
        query = query.filter(KeywordFilter.filter_type == filter_type)

    query.delete(synchronize_session=False)
    db.commit()


# ============================================================================
# Application Question Endpoints
# ============================================================================


@router.get("/questions", response_model=ApplicationQuestionListResponse)
async def list_application_questions(
    category: Optional[str] = None,
    question_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all application question templates for current user."""
    query = db.query(ApplicationQuestion).filter(ApplicationQuestion.user_id == current_user.id)

    if category:
        query = query.filter(ApplicationQuestion.category == category)

    if question_type:
        query = query.filter(ApplicationQuestion.question_type == question_type)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (ApplicationQuestion.question_pattern.ilike(search_term))
            | (ApplicationQuestion.answer.ilike(search_term))
        )

    total = query.count()
    items = query.order_by(ApplicationQuestion.category, ApplicationQuestion.created_at.desc()).offset(skip).limit(limit).all()

    return ApplicationQuestionListResponse(items=items, total=total)


@router.post(
    "/questions", response_model=ApplicationQuestionResponse, status_code=status.HTTP_201_CREATED
)
async def create_application_question(
    question_data: ApplicationQuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new application question template."""
    question = ApplicationQuestion(
        user_id=current_user.id,
        question_pattern=question_data.question_pattern,
        answer=question_data.answer,
        question_type=question_data.question_type,
        category=question_data.category,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return question


@router.get("/questions/{question_id}", response_model=ApplicationQuestionResponse)
async def get_application_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific application question template."""
    question = (
        db.query(ApplicationQuestion)
        .filter(ApplicationQuestion.id == question_id, ApplicationQuestion.user_id == current_user.id)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="Application question not found")

    return question


@router.put("/questions/{question_id}", response_model=ApplicationQuestionResponse)
async def update_application_question(
    question_id: int,
    question_data: ApplicationQuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an application question template."""
    question = (
        db.query(ApplicationQuestion)
        .filter(ApplicationQuestion.id == question_id, ApplicationQuestion.user_id == current_user.id)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="Application question not found")

    update_data = question_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)

    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an application question template."""
    question = (
        db.query(ApplicationQuestion)
        .filter(ApplicationQuestion.id == question_id, ApplicationQuestion.user_id == current_user.id)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="Application question not found")

    db.delete(question)
    db.commit()


@router.delete("/questions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_application_questions(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all application questions for current user (optionally filtered by category)."""
    query = db.query(ApplicationQuestion).filter(ApplicationQuestion.user_id == current_user.id)

    if category:
        query = query.filter(ApplicationQuestion.category == category)

    query.delete(synchronize_session=False)
    db.commit()


# ============================================================================
# Job Check Endpoint
# ============================================================================


@router.get("/check-job", response_model=JobCheckResponse)
async def check_job_filters(
    title: str,
    company: str,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if a job matches the user's filters.

    Returns whether the job passes all filters and details about any matches.
    """
    passes_filters = True
    company_filter_match = None
    keyword_matches = []
    matching_questions = []
    summary_parts = []

    # Check company filters
    company_filters = (
        db.query(CompanyFilter).filter(CompanyFilter.user_id == current_user.id).all()
    )

    for cf in company_filters:
        if cf.company_name.lower() in company.lower() or company.lower() in cf.company_name.lower():
            company_filter_match = FilterMatch(
                filter_type="company",
                filter_id=cf.id,
                matched_value=cf.company_name,
                action="block" if cf.filter_type == CompanyFilterType.BLACKLIST else "allow",
                reason=cf.reason,
            )

            if cf.filter_type == CompanyFilterType.BLACKLIST:
                passes_filters = False
                summary_parts.append(f"Company '{company}' is blacklisted")
            else:
                summary_parts.append(f"Company '{company}' is whitelisted")
            break

    # Check keyword filters
    keyword_filters = (
        db.query(KeywordFilter).filter(KeywordFilter.user_id == current_user.id).all()
    )

    for kf in keyword_filters:
        text_to_check = ""
        if kf.applies_to == KeywordAppliesTo.TITLE:
            text_to_check = title.lower()
        elif kf.applies_to == KeywordAppliesTo.DESCRIPTION:
            text_to_check = (description or "").lower()
        else:  # BOTH
            text_to_check = f"{title} {description or ''}".lower()

        # Use regex for pattern matching (supports | for OR)
        try:
            pattern = re.compile(kf.keyword.lower())
            match = pattern.search(text_to_check)
        except re.error:
            # If not a valid regex, do simple substring match
            match = kf.keyword.lower() in text_to_check

        if match:
            action = "block" if kf.filter_type == KeywordFilterType.EXCLUDE else "require"
            keyword_matches.append(
                FilterMatch(
                    filter_type="keyword",
                    filter_id=kf.id,
                    matched_value=kf.keyword,
                    action=action,
                    reason=None,
                )
            )

            if kf.filter_type == KeywordFilterType.EXCLUDE:
                passes_filters = False
                summary_parts.append(f"Excluded keyword '{kf.keyword}' found")
            else:
                summary_parts.append(f"Required keyword '{kf.keyword}' found")

    # Check for required keywords that are missing
    required_keywords = (
        db.query(KeywordFilter)
        .filter(
            KeywordFilter.user_id == current_user.id,
            KeywordFilter.filter_type == KeywordFilterType.REQUIRE,
        )
        .all()
    )

    for rk in required_keywords:
        text_to_check = ""
        if rk.applies_to == KeywordAppliesTo.TITLE:
            text_to_check = title.lower()
        elif rk.applies_to == KeywordAppliesTo.DESCRIPTION:
            text_to_check = (description or "").lower()
        else:  # BOTH
            text_to_check = f"{title} {description or ''}".lower()

        try:
            pattern = re.compile(rk.keyword.lower())
            match = pattern.search(text_to_check)
        except re.error:
            match = rk.keyword.lower() in text_to_check

        if not match:
            passes_filters = False
            summary_parts.append(f"Required keyword '{rk.keyword}' not found")

    # Find matching application questions
    questions = (
        db.query(ApplicationQuestion).filter(ApplicationQuestion.user_id == current_user.id).all()
    )

    full_text = f"{title} {description or ''}".lower()
    for q in questions:
        try:
            pattern = re.compile(q.question_pattern.lower())
            if pattern.search(full_text):
                matching_questions.append(q)
        except re.error:
            if q.question_pattern.lower() in full_text:
                matching_questions.append(q)

    # Generate summary
    if passes_filters:
        summary = "Job passes all filters."
        if summary_parts:
            summary += " " + "; ".join(summary_parts) + "."
        if matching_questions:
            summary += f" {len(matching_questions)} question template(s) may be relevant."
    else:
        summary = "Job blocked by filters: " + "; ".join(summary_parts) + "."

    return JobCheckResponse(
        passes_filters=passes_filters,
        company_filter_match=company_filter_match,
        keyword_matches=keyword_matches,
        matching_questions=matching_questions,
        summary=summary,
    )


@router.post("/check-job", response_model=JobCheckResponse)
async def check_job_filters_post(
    request: JobCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if a job matches the user's filters (POST version for longer descriptions).

    Returns whether the job passes all filters and details about any matches.
    """
    return await check_job_filters(
        title=request.title,
        company=request.company,
        description=request.description,
        current_user=current_user,
        db=db,
    )


# ============================================================================
# Import Defaults Endpoint
# ============================================================================


@router.post("/import-defaults", response_model=ImportDefaultsResponse)
async def import_default_questions(
    overwrite: bool = Query(False, description="Overwrite existing questions with same pattern"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import common default question templates.

    These templates help auto-fill common application questions like:
    - Years of experience
    - Salary expectations
    - Notice period
    - Work authorization
    - Relocation willingness
    - Sponsorship requirements
    - Remote work preference
    - Start date availability
    """
    imported_count = 0
    skipped_count = 0

    for template in DEFAULT_QUESTION_TEMPLATES:
        # Check if similar pattern exists
        existing = (
            db.query(ApplicationQuestion)
            .filter(
                ApplicationQuestion.user_id == current_user.id,
                ApplicationQuestion.question_pattern == template["question_pattern"],
            )
            .first()
        )

        if existing:
            if overwrite:
                existing.answer = template["answer"]
                existing.question_type = template["question_type"]
                existing.category = template["category"]
                imported_count += 1
            else:
                skipped_count += 1
        else:
            question = ApplicationQuestion(
                user_id=current_user.id,
                question_pattern=template["question_pattern"],
                answer=template["answer"],
                question_type=template["question_type"],
                category=template["category"],
            )
            db.add(question)
            imported_count += 1

    db.commit()

    return ImportDefaultsResponse(
        success=True,
        imported_count=imported_count,
        skipped_count=skipped_count,
        message=f"Imported {imported_count} question templates"
        + (f", skipped {skipped_count} existing" if skipped_count > 0 else ""),
    )


# ============================================================================
# Categories Endpoint
# ============================================================================


@router.get("/questions/categories")
async def get_question_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all unique question categories for the current user."""
    categories = (
        db.query(ApplicationQuestion.category)
        .filter(
            ApplicationQuestion.user_id == current_user.id,
            ApplicationQuestion.category.isnot(None),
        )
        .distinct()
        .all()
    )

    return {"categories": [c[0] for c in categories if c[0]]}
