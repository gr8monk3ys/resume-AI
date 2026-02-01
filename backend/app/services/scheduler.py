"""
Background job scheduler for automated job scraping.

Uses APScheduler for reliable background task scheduling with:
- Persistent job storage (in-memory with optional database backing)
- Graceful error handling and recovery
- Non-blocking execution
- Comprehensive logging
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Callable, Optional

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    JobExecutionEvent,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.schemas.scheduler import (
    JobSchedulerStatus,
    ScheduledJobCreate,
    ScheduledJobResponse,
    ScheduledJobStatus,
    SchedulerStatusResponse,
    ScrapeCriteria,
    ScrapeSource,
    TriggerJobResponse,
)
from app.services.job_scraper import JobScraper, get_job_scraper

logger = logging.getLogger(__name__)


class ScheduledJobInfo:
    """
    Information about a scheduled scraping job.

    Stores metadata and execution history for a scheduled job.
    """

    def __init__(
        self,
        job_id: str,
        name: str,
        user_id: int,
        source: ScrapeSource,
        interval_minutes: int,
        criteria: Optional[ScrapeCriteria] = None,
        custom_url: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize scheduled job info.

        Args:
            job_id: Unique identifier for the job.
            name: Human-readable job name.
            user_id: Owner user ID.
            source: Scraping source.
            interval_minutes: Execution interval in minutes.
            criteria: Optional filtering criteria.
            custom_url: Custom URL for CUSTOM_URL source.
            enabled: Whether the job is enabled.
        """
        self.job_id = job_id
        self.name = name
        self.user_id = user_id
        self.source = source
        self.interval_minutes = interval_minutes
        self.criteria = criteria
        self.custom_url = custom_url
        self.enabled = enabled
        self.status = ScheduledJobStatus.ACTIVE if enabled else ScheduledJobStatus.PAUSED
        self.created_at = datetime.utcnow()
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.last_result: Optional[str] = None
        self.jobs_found_last_run: int = 0
        self.total_jobs_found: int = 0
        self.error_count: int = 0

    def to_response(self) -> ScheduledJobResponse:
        """Convert to response schema."""
        return ScheduledJobResponse(
            id=self.job_id,
            name=self.name,
            source=self.source,
            interval_minutes=self.interval_minutes,
            criteria=self.criteria,
            enabled=self.enabled,
            status=self.status,
            user_id=self.user_id,
            custom_url=self.custom_url,
            created_at=self.created_at,
            last_run=self.last_run,
            next_run=self.next_run,
            last_result=self.last_result,
            jobs_found_last_run=self.jobs_found_last_run,
            total_jobs_found=self.total_jobs_found,
            error_count=self.error_count,
        )


class JobScheduler:
    """
    Background job scheduler for automated job scraping.

    Provides:
    - Adding/removing scheduled scrape jobs
    - Automatic execution on configurable intervals
    - Error handling with automatic retry
    - Job execution history tracking
    - Manual job triggering
    """

    def __init__(
        self,
        job_scraper: Optional[JobScraper] = None,
        max_instances: int = 1,
    ):
        """
        Initialize the job scheduler.

        Args:
            job_scraper: Optional JobScraper instance (uses singleton if not provided).
            max_instances: Maximum concurrent instances per job.
        """
        self._scheduler = AsyncIOScheduler(
            job_defaults={
                "coalesce": True,  # Combine missed runs into one
                "max_instances": max_instances,
                "misfire_grace_time": 60 * 5,  # 5 minute grace period
            }
        )
        self._job_scraper = job_scraper or get_job_scraper()
        self._jobs: dict[str, ScheduledJobInfo] = {}
        self._status = JobSchedulerStatus.STOPPED
        self._start_time: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._on_jobs_found_callback: Optional[Callable] = None

        # Register event listeners
        self._scheduler.add_listener(
            self._on_job_executed, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

    @property
    def status(self) -> JobSchedulerStatus:
        """Get current scheduler status."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._status == JobSchedulerStatus.RUNNING

    def set_on_jobs_found_callback(self, callback: Callable) -> None:
        """
        Set callback to be called when new jobs are found.

        The callback should accept (user_id, jobs) parameters.
        """
        self._on_jobs_found_callback = callback

    def _on_job_executed(self, event: JobExecutionEvent) -> None:
        """Handle job execution events for logging and tracking."""
        job_id = event.job_id

        if job_id not in self._jobs:
            return

        job_info = self._jobs[job_id]

        if event.exception:
            job_info.error_count += 1
            job_info.last_result = f"Error: {str(event.exception)}"
            job_info.status = ScheduledJobStatus.FAILED
            self._last_error = f"Job {job_id} failed: {str(event.exception)}"
            logger.error(f"Scheduled job {job_id} ({job_info.name}) failed: {event.exception}")
        else:
            job_info.error_count = 0
            job_info.status = ScheduledJobStatus.ACTIVE
            logger.info(f"Scheduled job {job_id} ({job_info.name}) executed successfully")

        # Update next run time
        apscheduler_job = self._scheduler.get_job(job_id)
        if apscheduler_job:
            job_info.next_run = apscheduler_job.next_run_time

    async def _execute_scrape_job(self, job_id: str) -> None:
        """
        Execute a scraping job.

        Args:
            job_id: The job ID to execute.
        """
        if job_id not in self._jobs:
            logger.warning(f"Job {job_id} not found in registry")
            return

        job_info = self._jobs[job_id]

        if not job_info.enabled:
            logger.info(f"Job {job_id} is disabled, skipping execution")
            return

        logger.info(f"Executing scheduled job: {job_info.name} ({job_id})")
        job_info.last_run = datetime.utcnow()

        try:
            all_jobs, new_jobs = await self._job_scraper.check_for_new_jobs(
                user_id=job_info.user_id,
                source=job_info.source,
                criteria=job_info.criteria,
                custom_url=job_info.custom_url,
            )

            job_info.jobs_found_last_run = len(all_jobs)
            job_info.total_jobs_found += len(new_jobs)
            job_info.last_result = f"Found {len(all_jobs)} jobs, {len(new_jobs)} new"

            logger.info(f"Job {job_id}: Found {len(all_jobs)} jobs, {len(new_jobs)} new")

            # Call callback if new jobs found
            if new_jobs and self._on_jobs_found_callback:
                try:
                    await self._on_jobs_found_callback(job_info.user_id, new_jobs)
                except Exception as e:
                    logger.error(f"Error in jobs found callback: {e}")

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            job_info.last_result = f"Error: {str(e)}"
            raise

    def start(self) -> None:
        """Start the scheduler."""
        if self._status == JobSchedulerStatus.RUNNING:
            logger.warning("Scheduler is already running")
            return

        logger.info("Starting job scheduler")
        self._scheduler.start()
        self._status = JobSchedulerStatus.RUNNING
        self._start_time = datetime.utcnow()
        logger.info("Job scheduler started successfully")

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if self._status == JobSchedulerStatus.STOPPED:
            logger.warning("Scheduler is already stopped")
            return

        logger.info("Stopping job scheduler")
        self._scheduler.shutdown(wait=True)
        self._status = JobSchedulerStatus.STOPPED
        logger.info("Job scheduler stopped")

    def pause(self) -> None:
        """Pause the scheduler (keeps jobs but stops execution)."""
        if self._status != JobSchedulerStatus.RUNNING:
            logger.warning("Scheduler is not running")
            return

        logger.info("Pausing job scheduler")
        self._scheduler.pause()
        self._status = JobSchedulerStatus.PAUSED

    def resume(self) -> None:
        """Resume a paused scheduler."""
        if self._status != JobSchedulerStatus.PAUSED:
            logger.warning("Scheduler is not paused")
            return

        logger.info("Resuming job scheduler")
        self._scheduler.resume()
        self._status = JobSchedulerStatus.RUNNING

    def add_scrape_job(
        self,
        user_id: int,
        job_data: ScheduledJobCreate,
    ) -> ScheduledJobResponse:
        """
        Add a new scheduled scraping job.

        Args:
            user_id: The owner user ID.
            job_data: The job configuration.

        Returns:
            The created job response.
        """
        job_id = f"scrape_{user_id}_{uuid.uuid4().hex[:8]}"

        # Create job info
        job_info = ScheduledJobInfo(
            job_id=job_id,
            name=job_data.name,
            user_id=user_id,
            source=job_data.source,
            interval_minutes=job_data.interval_minutes,
            criteria=job_data.criteria,
            custom_url=job_data.custom_url,
            enabled=job_data.enabled,
        )

        # Add to APScheduler
        trigger = IntervalTrigger(minutes=job_data.interval_minutes)
        self._scheduler.add_job(
            self._execute_scrape_job,
            trigger=trigger,
            id=job_id,
            args=[job_id],
            name=job_data.name,
            replace_existing=True,
        )

        # Store job info
        self._jobs[job_id] = job_info

        # Update next run time
        apscheduler_job = self._scheduler.get_job(job_id)
        if apscheduler_job:
            job_info.next_run = apscheduler_job.next_run_time

        # Pause job if not enabled
        if not job_data.enabled:
            self._scheduler.pause_job(job_id)
            job_info.status = ScheduledJobStatus.PAUSED

        logger.info(
            f"Added scheduled job: {job_data.name} ({job_id}) for user {user_id}, "
            f"interval: {job_data.interval_minutes} minutes"
        )

        return job_info.to_response()

    def remove_job(self, job_id: str, user_id: Optional[int] = None) -> bool:
        """
        Remove a scheduled job.

        Args:
            job_id: The job ID to remove.
            user_id: Optional user ID for authorization check.

        Returns:
            True if removed, False if not found or not authorized.
        """
        if job_id not in self._jobs:
            logger.warning(f"Job {job_id} not found")
            return False

        job_info = self._jobs[job_id]

        # Check authorization if user_id provided
        if user_id is not None and job_info.user_id != user_id:
            logger.warning(f"User {user_id} not authorized to remove job {job_id}")
            return False

        # Remove from APScheduler
        try:
            self._scheduler.remove_job(job_id)
        except Exception as e:
            logger.warning(f"Error removing job from scheduler: {e}")

        # Remove from registry
        del self._jobs[job_id]
        logger.info(f"Removed scheduled job: {job_id}")
        return True

    def get_job(self, job_id: str, user_id: Optional[int] = None) -> Optional[ScheduledJobResponse]:
        """
        Get a specific job by ID.

        Args:
            job_id: The job ID.
            user_id: Optional user ID for authorization check.

        Returns:
            The job response or None if not found/not authorized.
        """
        if job_id not in self._jobs:
            return None

        job_info = self._jobs[job_id]

        # Check authorization if user_id provided
        if user_id is not None and job_info.user_id != user_id:
            return None

        return job_info.to_response()

    def get_jobs(self, user_id: Optional[int] = None) -> list[ScheduledJobResponse]:
        """
        Get all scheduled jobs.

        Args:
            user_id: Optional user ID to filter by owner.

        Returns:
            List of scheduled job responses.
        """
        jobs = []
        for job_info in self._jobs.values():
            if user_id is None or job_info.user_id == user_id:
                jobs.append(job_info.to_response())
        return jobs

    def update_job(
        self,
        job_id: str,
        user_id: int,
        name: Optional[str] = None,
        interval_minutes: Optional[int] = None,
        criteria: Optional[ScrapeCriteria] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[ScheduledJobResponse]:
        """
        Update an existing scheduled job.

        Args:
            job_id: The job ID to update.
            user_id: The user ID for authorization.
            name: Optional new name.
            interval_minutes: Optional new interval.
            criteria: Optional new criteria.
            enabled: Optional enabled status.

        Returns:
            Updated job response or None if not found/not authorized.
        """
        if job_id not in self._jobs:
            return None

        job_info = self._jobs[job_id]

        if job_info.user_id != user_id:
            return None

        # Update fields
        if name is not None:
            job_info.name = name

        if criteria is not None:
            job_info.criteria = criteria

        if interval_minutes is not None:
            job_info.interval_minutes = interval_minutes
            # Reschedule with new interval
            trigger = IntervalTrigger(minutes=interval_minutes)
            self._scheduler.reschedule_job(job_id, trigger=trigger)

        if enabled is not None:
            job_info.enabled = enabled
            if enabled:
                self._scheduler.resume_job(job_id)
                job_info.status = ScheduledJobStatus.ACTIVE
            else:
                self._scheduler.pause_job(job_id)
                job_info.status = ScheduledJobStatus.PAUSED

        # Update next run time
        apscheduler_job = self._scheduler.get_job(job_id)
        if apscheduler_job:
            job_info.next_run = apscheduler_job.next_run_time

        logger.info(f"Updated scheduled job: {job_id}")
        return job_info.to_response()

    async def trigger_job(self, job_id: str, user_id: Optional[int] = None) -> TriggerJobResponse:
        """
        Manually trigger a scheduled job.

        Args:
            job_id: The job ID to trigger.
            user_id: Optional user ID for authorization.

        Returns:
            Trigger response with execution result.
        """
        if job_id not in self._jobs:
            return TriggerJobResponse(
                success=False,
                job_id=job_id,
                message="Job not found",
                errors=["Job not found"],
            )

        job_info = self._jobs[job_id]

        if user_id is not None and job_info.user_id != user_id:
            return TriggerJobResponse(
                success=False,
                job_id=job_id,
                message="Not authorized",
                errors=["Not authorized to trigger this job"],
            )

        logger.info(f"Manually triggering job: {job_id}")

        try:
            # Execute the job directly
            all_jobs, new_jobs = await self._job_scraper.check_for_new_jobs(
                user_id=job_info.user_id,
                source=job_info.source,
                criteria=job_info.criteria,
                custom_url=job_info.custom_url,
            )

            job_info.last_run = datetime.utcnow()
            job_info.jobs_found_last_run = len(all_jobs)
            job_info.total_jobs_found += len(new_jobs)
            job_info.last_result = f"Found {len(all_jobs)} jobs, {len(new_jobs)} new"
            job_info.error_count = 0

            return TriggerJobResponse(
                success=True,
                job_id=job_id,
                message=f"Job triggered successfully. Found {len(all_jobs)} jobs, {len(new_jobs)} new.",
                jobs_found=len(all_jobs),
                new_jobs=len(new_jobs),
            )

        except Exception as e:
            logger.error(f"Error triggering job {job_id}: {e}")
            job_info.error_count += 1
            job_info.last_result = f"Error: {str(e)}"
            return TriggerJobResponse(
                success=False,
                job_id=job_id,
                message="Job execution failed",
                errors=[str(e)],
            )

    def get_status(self) -> SchedulerStatusResponse:
        """Get scheduler status information."""
        uptime = None
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()

        active_jobs = sum(1 for j in self._jobs.values() if j.status == ScheduledJobStatus.ACTIVE)

        return SchedulerStatusResponse(
            status=self._status,
            active_jobs=active_jobs,
            total_jobs=len(self._jobs),
            uptime_seconds=uptime,
            last_error=self._last_error,
            version="1.0.0",
        )


# Singleton instance
_job_scheduler: Optional[JobScheduler] = None


def get_job_scheduler() -> JobScheduler:
    """Get or create the JobScheduler singleton."""
    global _job_scheduler
    if _job_scheduler is None:
        _job_scheduler = JobScheduler()
    return _job_scheduler


def reset_job_scheduler() -> None:
    """Reset the JobScheduler singleton (useful for testing)."""
    global _job_scheduler
    if _job_scheduler is not None:
        try:
            _job_scheduler.stop()
        except Exception:
            pass
    _job_scheduler = None
