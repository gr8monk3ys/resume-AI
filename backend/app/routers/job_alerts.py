"""
Job alerts router for managing job alert configurations.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.job_alert import (
    AlertTestResult,
    JobAlertCreate,
    JobAlertResponse,
    JobAlertUpdate,
)
from app.services.job_alerts import get_job_alert_service

router = APIRouter(prefix="/api/alerts", tags=["Job Alerts"])


@router.get("", response_model=List[JobAlertResponse])
async def list_alerts(
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all job alerts for the current user.

    Args:
        active_only: If True, only return active alerts

    Returns:
        List of job alerts
    """
    service = get_job_alert_service(db)
    alerts = service.get_alerts(current_user.id, active_only=active_only)
    return [service.alert_to_response(alert) for alert in alerts]


@router.post("", response_model=JobAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: JobAlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new job alert.

    The alert will monitor for jobs matching the specified criteria:
    - keywords: Search terms to match in job titles/descriptions
    - companies: Target company names
    - locations: Desired job locations
    - job_types: Types of employment (Full-time, Part-time, etc.)
    - min_salary: Minimum salary requirement
    - exclude_keywords: Keywords to exclude from matches

    Returns:
        The created job alert
    """
    service = get_job_alert_service(db)
    alert = service.create_alert(current_user.id, alert_data)
    return service.alert_to_response(alert)


@router.get("/{alert_id}", response_model=JobAlertResponse)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific job alert by ID.

    Args:
        alert_id: The ID of the alert to retrieve

    Returns:
        The job alert

    Raises:
        404: If the alert is not found
    """
    service = get_job_alert_service(db)
    alert = service.get_alert(alert_id, current_user.id)

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )

    return service.alert_to_response(alert)


@router.put("/{alert_id}", response_model=JobAlertResponse)
async def update_alert(
    alert_id: int,
    update_data: JobAlertUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing job alert.

    Args:
        alert_id: The ID of the alert to update
        update_data: The fields to update

    Returns:
        The updated job alert

    Raises:
        404: If the alert is not found
    """
    service = get_job_alert_service(db)
    alert = service.update_alert(alert_id, current_user.id, update_data)

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )

    return service.alert_to_response(alert)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a job alert.

    Args:
        alert_id: The ID of the alert to delete

    Raises:
        404: If the alert is not found
    """
    service = get_job_alert_service(db)
    deleted = service.delete_alert(alert_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )


@router.post("/{alert_id}/test", response_model=AlertTestResult)
async def test_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test an alert against recent jobs to see what would match.

    This endpoint allows you to preview what jobs would match
    an alert before waiting for real notifications.

    Args:
        alert_id: The ID of the alert to test

    Returns:
        Test results including matching jobs

    Raises:
        404: If the alert is not found
    """
    service = get_job_alert_service(db)
    result = service.test_alert(alert_id, current_user.id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )

    return result


@router.post("/{alert_id}/toggle", response_model=JobAlertResponse)
async def toggle_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Toggle an alert's active status.

    Args:
        alert_id: The ID of the alert to toggle

    Returns:
        The updated job alert

    Raises:
        404: If the alert is not found
    """
    service = get_job_alert_service(db)
    alert = service.get_alert(alert_id, current_user.id)

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )

    update_data = JobAlertUpdate(is_active=not alert.is_active)
    updated_alert = service.update_alert(alert_id, current_user.id, update_data)

    return service.alert_to_response(updated_alert)


@router.post("/check", response_model=dict)
async def check_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manually check all active alerts for new matching jobs.

    This endpoint triggers an immediate check of all active alerts
    and returns any notifications.

    Returns:
        Dictionary with notifications and count
    """
    service = get_job_alert_service(db)
    notifications = service.check_alerts(current_user.id)

    return {
        "notification_count": len(notifications),
        "notifications": [n.model_dump() for n in notifications],
    }
