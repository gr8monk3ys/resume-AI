"""
Analytics router for job application insights and reporting.

Provides comprehensive analytics including:
- Dashboard overview statistics
- Application timeline trends
- Conversion funnel analysis
- Source performance metrics
- Company-level statistics
- Response time analysis
- Resume performance tracking
- Data export capabilities
"""

import csv
import io
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# --------------------------------------------------------------------------
# Pydantic Response Schemas
# --------------------------------------------------------------------------


class OverviewStats(BaseModel):
    """Dashboard overview statistics."""

    total_applications: int
    status_breakdown: Dict[str, int]
    response_rate: float
    interview_rate: float
    offer_rate: float
    avg_time_to_response_days: Optional[float]
    applications_this_week: int
    applications_this_month: int


class TimelineDataPoint(BaseModel):
    """Single data point in timeline."""

    date: str
    count: int
    status_breakdown: Dict[str, int]


class TimelineResponse(BaseModel):
    """Timeline response with aggregated data."""

    period: str
    data: List[TimelineDataPoint]
    total: int


class FunnelStage(BaseModel):
    """Single stage in conversion funnel."""

    stage: str
    count: int
    percentage: float
    conversion_rate: Optional[float] = None


class ConversionFunnelResponse(BaseModel):
    """Conversion funnel response."""

    stages: List[FunnelStage]
    overall_conversion_rate: float


class SourcePerformance(BaseModel):
    """Performance metrics for a single source."""

    source: str
    total_applications: int
    response_count: int
    interview_count: int
    offer_count: int
    response_rate: float
    interview_rate: float
    offer_rate: float


class SourcePerformanceResponse(BaseModel):
    """Source performance response."""

    sources: List[SourcePerformance]
    best_performing_source: Optional[str]


class CompanyStats(BaseModel):
    """Statistics for a single company."""

    company: str
    total_applications: int
    status_breakdown: Dict[str, int]
    avg_response_time_days: Optional[float]
    latest_status: str
    latest_application_date: Optional[date]


class CompanyStatsResponse(BaseModel):
    """Company statistics response."""

    companies: List[CompanyStats]
    total_companies: int


class ResponseTimeStats(BaseModel):
    """Response time statistics."""

    category: str
    avg_response_time_days: float
    min_response_time_days: Optional[float]
    max_response_time_days: Optional[float]
    sample_size: int


class ResponseTimeResponse(BaseModel):
    """Response time analysis response."""

    overall_avg_days: Optional[float]
    by_status: List[ResponseTimeStats]
    by_company: List[ResponseTimeStats]


class ResumePerformance(BaseModel):
    """Performance metrics for a resume version."""

    resume_id: int
    version_name: str
    total_applications: int
    response_count: int
    interview_count: int
    offer_count: int
    response_rate: float
    interview_rate: float
    offer_rate: float


class ResumePerformanceResponse(BaseModel):
    """Resume performance response."""

    resumes: List[ResumePerformance]
    best_performing_resume: Optional[str]


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"


class ExportRequest(BaseModel):
    """Export request parameters."""

    format: ExportFormat = ExportFormat.JSON
    include_fields: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------


def get_user_profile(user: User, db: Session) -> Profile:
    """Get or create user profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, name=user.full_name or user.username)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def calculate_response_rate(jobs: List[JobApplication]) -> float:
    """
    Calculate response rate.

    Response rate = (jobs with response_date or moved past Applied) / total applied
    """
    applied_jobs = [j for j in jobs if j.status != "Bookmarked"]
    if not applied_jobs:
        return 0.0

    responded = [
        j
        for j in applied_jobs
        if j.response_date is not None or j.status in ("Phone Screen", "Interview", "Offer")
    ]
    return round((len(responded) / len(applied_jobs)) * 100, 2)


def calculate_conversion_funnel(jobs: List[JobApplication]) -> List[FunnelStage]:
    """
    Calculate conversion funnel stages.

    Funnel: Bookmarked -> Applied -> Phone Screen -> Interview -> Offer
    """
    status_order = ["Bookmarked", "Applied", "Phone Screen", "Interview", "Offer"]

    # Count jobs that reached each stage (cumulative)
    stage_counts = {}
    total = len(jobs)

    for status in status_order:
        # Count jobs that are at this status or have progressed beyond it
        status_index = status_order.index(status)
        count = sum(
            1
            for j in jobs
            if status_order.index(j.status) >= status_index or j.status == "Rejected"
        )
        # For rejected, only count if they got past bookmarked
        if status != "Bookmarked":
            rejected_at_or_after = sum(
                1
                for j in jobs
                if j.status == "Rejected"
                and j.application_date is not None  # They at least applied
            )
            count = sum(1 for j in jobs if j.status == status) + sum(
                1
                for j in jobs
                if status_order.index(j.status) > status_index and j.status != "Rejected"
            )

    # Simpler approach: count how many reached each stage minimum
    stage_counts = defaultdict(int)
    status_to_min_stage = {
        "Bookmarked": 0,
        "Applied": 1,
        "Phone Screen": 2,
        "Interview": 3,
        "Offer": 4,
        "Rejected": 1,  # Rejected means at least applied
    }

    for job in jobs:
        min_stage = status_to_min_stage.get(job.status, 0)
        for i in range(min_stage + 1):
            stage_counts[status_order[i]] += 1

    stages = []
    prev_count = total
    for status in status_order:
        count = stage_counts[status]
        percentage = round((count / total) * 100, 2) if total > 0 else 0.0
        conversion = round((count / prev_count) * 100, 2) if prev_count > 0 else 0.0

        stages.append(
            FunnelStage(
                stage=status,
                count=count,
                percentage=percentage,
                conversion_rate=conversion if status != "Bookmarked" else None,
            )
        )
        prev_count = count if count > 0 else prev_count

    return stages


def calculate_avg_response_time(jobs: List[JobApplication]) -> Optional[float]:
    """
    Calculate average response time in days.

    Response time = response_date - application_date
    """
    response_times = []
    for job in jobs:
        if job.application_date and job.response_date:
            app_date = (
                datetime.combine(job.application_date, datetime.min.time())
                if isinstance(job.application_date, date)
                else job.application_date
            )
            delta = job.response_date - app_date
            response_times.append(delta.days)

    if not response_times:
        return None

    return round(sum(response_times) / len(response_times), 1)


def aggregate_by_time_period(jobs: List[JobApplication], period: str) -> List[TimelineDataPoint]:
    """
    Aggregate job applications by time period.

    Periods: daily, weekly, monthly
    """
    if not jobs:
        return []

    # Group by period
    grouped = defaultdict(lambda: {"count": 0, "status_breakdown": defaultdict(int)})

    for job in jobs:
        if not job.created_at:
            continue

        if period == "daily":
            key = job.created_at.strftime("%Y-%m-%d")
        elif period == "weekly":
            # Get start of week (Monday)
            week_start = job.created_at - timedelta(days=job.created_at.weekday())
            key = week_start.strftime("%Y-%m-%d")
        else:  # monthly
            key = job.created_at.strftime("%Y-%m")

        grouped[key]["count"] += 1
        grouped[key]["status_breakdown"][job.status] += 1

    # Convert to list and sort by date
    data_points = [
        TimelineDataPoint(
            date=key, count=value["count"], status_breakdown=dict(value["status_breakdown"])
        )
        for key, value in sorted(grouped.items())
    ]

    return data_points


# --------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get dashboard overview statistics.

    Returns total applications, status breakdown, response rate,
    average time to response, and recent application counts.
    """
    profile = get_user_profile(current_user, db)

    jobs = db.query(JobApplication).filter(JobApplication.profile_id == profile.id).all()

    if not jobs:
        return OverviewStats(
            total_applications=0,
            status_breakdown={},
            response_rate=0.0,
            interview_rate=0.0,
            offer_rate=0.0,
            avg_time_to_response_days=None,
            applications_this_week=0,
            applications_this_month=0,
        )

    # Status breakdown
    status_counts = defaultdict(int)
    for job in jobs:
        status_counts[job.status] += 1

    total = len(jobs)
    applied_total = total - status_counts.get("Bookmarked", 0)

    # Calculate rates
    interview_count = status_counts.get("Phone Screen", 0) + status_counts.get("Interview", 0)
    offer_count = status_counts.get("Offer", 0)

    response_rate = calculate_response_rate(jobs)
    interview_rate = round((interview_count / applied_total) * 100, 2) if applied_total > 0 else 0.0
    offer_rate = round((offer_count / total) * 100, 2) if total > 0 else 0.0

    # Average response time
    avg_response_time = calculate_avg_response_time(jobs)

    # Recent counts
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    applications_this_week = sum(1 for j in jobs if j.created_at and j.created_at >= week_ago)
    applications_this_month = sum(1 for j in jobs if j.created_at and j.created_at >= month_ago)

    return OverviewStats(
        total_applications=total,
        status_breakdown=dict(status_counts),
        response_rate=response_rate,
        interview_rate=interview_rate,
        offer_rate=offer_rate,
        avg_time_to_response_days=avg_response_time,
        applications_this_week=applications_this_week,
        applications_this_month=applications_this_month,
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    period: str = Query("weekly", regex="^(daily|weekly|monthly)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get applications over time.

    Aggregates application data by daily, weekly, or monthly periods.
    Optionally filter by date range.
    """
    profile = get_user_profile(current_user, db)

    query = db.query(JobApplication).filter(JobApplication.profile_id == profile.id)

    if start_date:
        query = query.filter(
            JobApplication.created_at >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        query = query.filter(
            JobApplication.created_at <= datetime.combine(end_date, datetime.max.time())
        )

    jobs = query.order_by(JobApplication.created_at).all()

    data_points = aggregate_by_time_period(jobs, period)

    return TimelineResponse(period=period, data=data_points, total=len(jobs))


@router.get("/conversion-funnel", response_model=ConversionFunnelResponse)
async def get_conversion_funnel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get conversion rates between application stages.

    Shows how many applications progress through each stage:
    Bookmarked -> Applied -> Phone Screen -> Interview -> Offer
    """
    profile = get_user_profile(current_user, db)

    jobs = db.query(JobApplication).filter(JobApplication.profile_id == profile.id).all()

    if not jobs:
        return ConversionFunnelResponse(
            stages=[
                FunnelStage(stage="Bookmarked", count=0, percentage=0.0),
                FunnelStage(stage="Applied", count=0, percentage=0.0, conversion_rate=0.0),
                FunnelStage(stage="Phone Screen", count=0, percentage=0.0, conversion_rate=0.0),
                FunnelStage(stage="Interview", count=0, percentage=0.0, conversion_rate=0.0),
                FunnelStage(stage="Offer", count=0, percentage=0.0, conversion_rate=0.0),
            ],
            overall_conversion_rate=0.0,
        )

    stages = calculate_conversion_funnel(jobs)

    # Overall conversion: offers / bookmarked
    total = len(jobs)
    offers = sum(1 for j in jobs if j.status == "Offer")
    overall_rate = round((offers / total) * 100, 2) if total > 0 else 0.0

    return ConversionFunnelResponse(stages=stages, overall_conversion_rate=overall_rate)


@router.get("/source-performance", response_model=SourcePerformanceResponse)
async def get_source_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get performance metrics by application source.

    Shows response rates, interview rates, and offer rates for each
    application source (LinkedIn, Indeed, Company Site, Referral, etc.).
    """
    profile = get_user_profile(current_user, db)

    jobs = db.query(JobApplication).filter(JobApplication.profile_id == profile.id).all()

    # Group by source
    by_source = defaultdict(list)
    for job in jobs:
        source = job.application_source or "Unknown"
        by_source[source].append(job)

    sources = []
    best_source = None
    best_rate = -1

    for source, source_jobs in by_source.items():
        total = len(source_jobs)

        # Count responses (has response_date or progressed past Applied)
        response_count = sum(
            1
            for j in source_jobs
            if j.response_date or j.status in ("Phone Screen", "Interview", "Offer")
        )

        interview_count = sum(
            1 for j in source_jobs if j.status in ("Phone Screen", "Interview", "Offer")
        )

        offer_count = sum(1 for j in source_jobs if j.status == "Offer")

        response_rate = round((response_count / total) * 100, 2) if total > 0 else 0.0
        interview_rate = round((interview_count / total) * 100, 2) if total > 0 else 0.0
        offer_rate = round((offer_count / total) * 100, 2) if total > 0 else 0.0

        sources.append(
            SourcePerformance(
                source=source,
                total_applications=total,
                response_count=response_count,
                interview_count=interview_count,
                offer_count=offer_count,
                response_rate=response_rate,
                interview_rate=interview_rate,
                offer_rate=offer_rate,
            )
        )

        # Track best performing source by interview rate
        if interview_rate > best_rate and total >= 3:  # Minimum sample size
            best_rate = interview_rate
            best_source = source

    # Sort by total applications descending
    sources.sort(key=lambda x: x.total_applications, reverse=True)

    return SourcePerformanceResponse(sources=sources, best_performing_source=best_source)


@router.get("/company-stats", response_model=CompanyStatsResponse)
async def get_company_stats(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get statistics grouped by company.

    Shows application count, status breakdown, and average response time
    for each company.
    """
    profile = get_user_profile(current_user, db)

    jobs = db.query(JobApplication).filter(JobApplication.profile_id == profile.id).all()

    # Group by company
    by_company = defaultdict(list)
    for job in jobs:
        by_company[job.company].append(job)

    companies = []
    for company, company_jobs in by_company.items():
        status_breakdown = defaultdict(int)
        for job in company_jobs:
            status_breakdown[job.status] += 1

        # Find latest application
        latest_job = max(company_jobs, key=lambda j: j.created_at or datetime.min)

        # Calculate average response time for this company
        avg_response = calculate_avg_response_time(company_jobs)

        companies.append(
            CompanyStats(
                company=company,
                total_applications=len(company_jobs),
                status_breakdown=dict(status_breakdown),
                avg_response_time_days=avg_response,
                latest_status=latest_job.status,
                latest_application_date=latest_job.application_date,
            )
        )

    # Sort by total applications descending and limit
    companies.sort(key=lambda x: x.total_applications, reverse=True)
    companies = companies[:limit]

    return CompanyStatsResponse(companies=companies, total_companies=len(by_company))


@router.get("/response-time", response_model=ResponseTimeResponse)
async def get_response_time_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get average response time analysis.

    Breaks down response time by status and by company.
    """
    profile = get_user_profile(current_user, db)

    jobs = db.query(JobApplication).filter(JobApplication.profile_id == profile.id).all()

    # Filter to jobs with both dates
    jobs_with_response = [j for j in jobs if j.application_date and j.response_date]

    # Calculate response times
    def calc_response_days(job: JobApplication) -> float:
        app_date = (
            datetime.combine(job.application_date, datetime.min.time())
            if isinstance(job.application_date, date)
            else job.application_date
        )
        return (job.response_date - app_date).days

    # Overall average
    overall_avg = None
    if jobs_with_response:
        all_times = [calc_response_days(j) for j in jobs_with_response]
        overall_avg = round(sum(all_times) / len(all_times), 1)

    # By status
    by_status = defaultdict(list)
    for job in jobs_with_response:
        by_status[job.status].append(calc_response_days(job))

    status_stats = []
    for status, times in by_status.items():
        if times:
            status_stats.append(
                ResponseTimeStats(
                    category=status,
                    avg_response_time_days=round(sum(times) / len(times), 1),
                    min_response_time_days=min(times),
                    max_response_time_days=max(times),
                    sample_size=len(times),
                )
            )

    # By company (top companies with data)
    by_company = defaultdict(list)
    for job in jobs_with_response:
        by_company[job.company].append(calc_response_days(job))

    company_stats = []
    for company, times in by_company.items():
        if times:
            company_stats.append(
                ResponseTimeStats(
                    category=company,
                    avg_response_time_days=round(sum(times) / len(times), 1),
                    min_response_time_days=min(times),
                    max_response_time_days=max(times),
                    sample_size=len(times),
                )
            )

    # Sort by sample size and limit
    company_stats.sort(key=lambda x: x.sample_size, reverse=True)
    company_stats = company_stats[:10]

    return ResponseTimeResponse(
        overall_avg_days=overall_avg, by_status=status_stats, by_company=company_stats
    )


@router.get("/resume-performance", response_model=ResumePerformanceResponse)
async def get_resume_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get performance metrics for each resume version.

    Shows which resume versions have the best response and interview rates.
    """
    profile = get_user_profile(current_user, db)

    # Get all jobs with resume_id
    jobs = db.query(JobApplication).filter(JobApplication.profile_id == profile.id).all()

    # Get all resumes for this user
    resumes = db.query(Resume).filter(Resume.profile_id == profile.id).all()
    resume_map = {r.id: r.version_name for r in resumes}

    # Group jobs by resume_id
    by_resume = defaultdict(list)
    for job in jobs:
        if job.resume_id:
            by_resume[job.resume_id].append(job)

    resume_stats = []
    best_resume = None
    best_rate = -1

    for resume_id, resume_jobs in by_resume.items():
        version_name = resume_map.get(resume_id, f"Resume #{resume_id}")
        total = len(resume_jobs)

        response_count = sum(
            1
            for j in resume_jobs
            if j.response_date or j.status in ("Phone Screen", "Interview", "Offer")
        )

        interview_count = sum(
            1 for j in resume_jobs if j.status in ("Phone Screen", "Interview", "Offer")
        )

        offer_count = sum(1 for j in resume_jobs if j.status == "Offer")

        response_rate = round((response_count / total) * 100, 2) if total > 0 else 0.0
        interview_rate = round((interview_count / total) * 100, 2) if total > 0 else 0.0
        offer_rate = round((offer_count / total) * 100, 2) if total > 0 else 0.0

        resume_stats.append(
            ResumePerformance(
                resume_id=resume_id,
                version_name=version_name,
                total_applications=total,
                response_count=response_count,
                interview_count=interview_count,
                offer_count=offer_count,
                response_rate=response_rate,
                interview_rate=interview_rate,
                offer_rate=offer_rate,
            )
        )

        # Track best performing resume by interview rate
        if interview_rate > best_rate and total >= 3:  # Minimum sample size
            best_rate = interview_rate
            best_resume = version_name

    # Sort by total applications descending
    resume_stats.sort(key=lambda x: x.total_applications, reverse=True)

    return ResumePerformanceResponse(resumes=resume_stats, best_performing_resume=best_resume)


@router.post("/export")
async def export_data(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export all application data as CSV or JSON.

    Supports filtering by date range and selecting specific fields.
    """
    profile = get_user_profile(current_user, db)

    query = db.query(JobApplication).filter(JobApplication.profile_id == profile.id)

    if export_request.start_date:
        query = query.filter(
            JobApplication.created_at
            >= datetime.combine(export_request.start_date, datetime.min.time())
        )
    if export_request.end_date:
        query = query.filter(
            JobApplication.created_at
            <= datetime.combine(export_request.end_date, datetime.max.time())
        )

    jobs = query.order_by(JobApplication.created_at.desc()).all()

    # Define exportable fields
    all_fields = [
        "id",
        "company",
        "position",
        "status",
        "application_date",
        "deadline",
        "location",
        "job_url",
        "notes",
        "recruiter_name",
        "recruiter_email",
        "recruiter_linkedin",
        "recruiter_phone",
        "referral_name",
        "referral_relationship",
        "application_source",
        "response_date",
        "rejection_reason",
        "resume_id",
        "created_at",
        "updated_at",
    ]

    # Use specified fields or all fields
    fields = export_request.include_fields or all_fields
    # Validate fields
    fields = [f for f in fields if f in all_fields]

    # Convert jobs to dictionaries
    data = []
    for job in jobs:
        row = {}
        for field in fields:
            value = getattr(job, field, None)
            # Convert datetime/date to string for serialization
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            row[field] = value
        data.append(row)

    if export_request.format == ExportFormat.JSON:
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=job_applications_{datetime.utcnow().strftime('%Y%m%d')}.json"
            },
        )
    else:
        # CSV export
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
        else:
            # Write header even for empty data
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=job_applications_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            },
        )
