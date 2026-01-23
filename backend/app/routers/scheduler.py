"""
Scheduler router for managing scheduled job scraping tasks.

Provides REST endpoints for:
- Creating and managing scheduled scrape jobs
- Viewing scheduler status
- Manually triggering jobs
"""

from typing import List

from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.scheduler import (
    ScheduledJobCreate,
    ScheduledJobResponse,
    ScheduledJobUpdate,
    SchedulerStatusResponse,
    TriggerJobResponse,
)
from app.services.scheduler import get_job_scheduler
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(
    current_user: User = Depends(get_current_user),
) -> SchedulerStatusResponse:
    """
    Get the current status of the job scheduler.

    Returns scheduler status including:
    - Running/stopped/paused state
    - Number of active and total jobs
    - Uptime information
    - Last error if any
    """
    scheduler = get_job_scheduler()
    return scheduler.get_status()


@router.get("/jobs", response_model=List[ScheduledJobResponse])
async def list_scheduled_jobs(
    current_user: User = Depends(get_current_user),
) -> List[ScheduledJobResponse]:
    """
    List all scheduled jobs for the current user.

    Returns a list of scheduled jobs including:
    - Job configuration (source, criteria, interval)
    - Execution status and history
    - Next scheduled run time
    """
    scheduler = get_job_scheduler()
    return scheduler.get_jobs(user_id=current_user.id)


@router.post(
    "/jobs",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scheduled_job(
    job_data: ScheduledJobCreate,
    current_user: User = Depends(get_current_user),
) -> ScheduledJobResponse:
    """
    Create a new scheduled scraping job.

    The job will automatically run at the specified interval to:
    - Scrape jobs from the configured source
    - Apply filtering criteria
    - Track new jobs found

    Sources:
    - github_new_grad: SimplifyJobs New-Grad-Positions repo
    - github_internships: SimplifyJobs Summer Internships repo
    - custom_url: Custom job posting URL

    Interval must be between 5 and 1440 minutes (24 hours).
    """
    scheduler = get_job_scheduler()

    # Check if scheduler is running
    if not scheduler.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler is not running. Please try again later.",
        )

    try:
        job = scheduler.add_scrape_job(
            user_id=current_user.id,
            job_data=job_data,
        )
        return job
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scheduled job: {str(e)}",
        )


@router.get("/jobs/{job_id}", response_model=ScheduledJobResponse)
async def get_scheduled_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> ScheduledJobResponse:
    """
    Get details of a specific scheduled job.

    Returns job configuration and execution history.
    """
    scheduler = get_job_scheduler()
    job = scheduler.get_job(job_id=job_id, user_id=current_user.id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled job not found",
        )

    return job


@router.put("/jobs/{job_id}", response_model=ScheduledJobResponse)
async def update_scheduled_job(
    job_id: str,
    update_data: ScheduledJobUpdate,
    current_user: User = Depends(get_current_user),
) -> ScheduledJobResponse:
    """
    Update an existing scheduled job.

    Allows updating:
    - Job name
    - Scraping interval
    - Filtering criteria
    - Enabled/disabled status
    """
    scheduler = get_job_scheduler()

    job = scheduler.update_job(
        job_id=job_id,
        user_id=current_user.id,
        name=update_data.name,
        interval_minutes=update_data.interval_minutes,
        criteria=update_data.criteria,
        enabled=update_data.enabled,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled job not found or not authorized",
        )

    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a scheduled job.

    Removes the job from the scheduler and stops all future executions.
    """
    scheduler = get_job_scheduler()
    success = scheduler.remove_job(job_id=job_id, user_id=current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled job not found or not authorized",
        )


@router.post("/trigger/{job_id}", response_model=TriggerJobResponse)
async def trigger_scheduled_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> TriggerJobResponse:
    """
    Manually trigger a scheduled job.

    Executes the job immediately regardless of its schedule.
    Returns the results of the execution including:
    - Number of jobs found
    - Number of new jobs added
    - Any errors encountered
    """
    scheduler = get_job_scheduler()

    result = await scheduler.trigger_job(job_id=job_id, user_id=current_user.id)

    if not result.success and "not found" in result.message.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled job not found",
        )

    if not result.success and "not authorized" in result.message.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to trigger this job",
        )

    return result


@router.post("/jobs/{job_id}/pause", response_model=ScheduledJobResponse)
async def pause_scheduled_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> ScheduledJobResponse:
    """
    Pause a scheduled job.

    Stops automatic execution until resumed.
    """
    scheduler = get_job_scheduler()

    job = scheduler.update_job(
        job_id=job_id,
        user_id=current_user.id,
        enabled=False,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled job not found or not authorized",
        )

    return job


@router.post("/jobs/{job_id}/resume", response_model=ScheduledJobResponse)
async def resume_scheduled_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> ScheduledJobResponse:
    """
    Resume a paused scheduled job.

    Re-enables automatic execution at the configured interval.
    """
    scheduler = get_job_scheduler()

    job = scheduler.update_job(
        job_id=job_id,
        user_id=current_user.id,
        enabled=True,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled job not found or not authorized",
        )

    return job
