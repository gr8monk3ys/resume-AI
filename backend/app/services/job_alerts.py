"""
Job alert service for managing job alerts and matching jobs.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.job_alert import JobAlert
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.schemas.job_alert import (
    AlertCriteria,
    AlertNotification,
    JobAlertCreate,
    JobAlertUpdate,
    JobMatch,
)

logger = logging.getLogger(__name__)


class JobAlertService:
    """Service for managing job alerts and matching jobs against criteria."""

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db

    def _serialize_list(self, items: Optional[List[Any]]) -> Optional[str]:
        """Serialize a list to JSON string for storage."""
        if items is None:
            return None
        # Convert enums to their values if needed
        serialized = [item.value if hasattr(item, "value") else item for item in items]
        return json.dumps(serialized)

    def _deserialize_list(self, data: Optional[str]) -> Optional[List[str]]:
        """Deserialize a JSON string to a list."""
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None

    def create_alert(self, user_id: int, alert_data: JobAlertCreate) -> JobAlert:
        """
        Create a new job alert for a user.

        Args:
            user_id: The ID of the user creating the alert
            alert_data: The alert creation data

        Returns:
            The created JobAlert instance
        """
        alert = JobAlert(
            user_id=user_id,
            name=alert_data.name,
            keywords=self._serialize_list(alert_data.keywords),
            companies=self._serialize_list(alert_data.companies),
            locations=self._serialize_list(alert_data.locations),
            job_types=self._serialize_list(alert_data.job_types),
            min_salary=alert_data.min_salary,
            exclude_keywords=self._serialize_list(alert_data.exclude_keywords),
            is_active=alert_data.is_active,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        logger.info(f"Created job alert {alert.id} for user {user_id}")
        return alert

    def get_alerts(self, user_id: int, active_only: bool = False) -> List[JobAlert]:
        """
        Get all alerts for a user.

        Args:
            user_id: The ID of the user
            active_only: If True, only return active alerts

        Returns:
            List of JobAlert instances
        """
        query = self.db.query(JobAlert).filter(JobAlert.user_id == user_id)
        if active_only:
            query = query.filter(JobAlert.is_active == True)
        return query.order_by(JobAlert.created_at.desc()).all()

    def get_alert(self, alert_id: int, user_id: int) -> Optional[JobAlert]:
        """
        Get a specific alert by ID, ensuring it belongs to the user.

        Args:
            alert_id: The ID of the alert
            user_id: The ID of the user

        Returns:
            JobAlert instance or None if not found
        """
        return (
            self.db.query(JobAlert)
            .filter(JobAlert.id == alert_id, JobAlert.user_id == user_id)
            .first()
        )

    def update_alert(
        self, alert_id: int, user_id: int, update_data: JobAlertUpdate
    ) -> Optional[JobAlert]:
        """
        Update an existing job alert.

        Args:
            alert_id: The ID of the alert to update
            user_id: The ID of the user (for ownership verification)
            update_data: The update data

        Returns:
            Updated JobAlert instance or None if not found
        """
        alert = self.get_alert(alert_id, user_id)
        if not alert:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field in ("keywords", "companies", "locations", "job_types", "exclude_keywords"):
                setattr(alert, field, self._serialize_list(value))
            else:
                setattr(alert, field, value)

        self.db.commit()
        self.db.refresh(alert)
        logger.info(f"Updated job alert {alert_id}")
        return alert

    def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """
        Delete a job alert.

        Args:
            alert_id: The ID of the alert to delete
            user_id: The ID of the user (for ownership verification)

        Returns:
            True if deleted, False if not found
        """
        alert = self.get_alert(alert_id, user_id)
        if not alert:
            return False

        self.db.delete(alert)
        self.db.commit()
        logger.info(f"Deleted job alert {alert_id}")
        return True

    def _calculate_match_score(
        self, job: JobApplication, criteria: AlertCriteria
    ) -> tuple[float, List[str]]:
        """
        Calculate how well a job matches the alert criteria.

        Args:
            job: The job application to check
            criteria: The alert criteria

        Returns:
            Tuple of (match_score, matched_criteria_list)
        """
        matched_criteria = []
        total_criteria = 0
        matches = 0

        job_text = (
            f"{job.company} {job.position} {job.job_description or ''} {job.location or ''}".lower()
        )

        # Check keywords
        if criteria.keywords:
            total_criteria += 1
            keyword_matches = [kw for kw in criteria.keywords if kw.lower() in job_text]
            if keyword_matches:
                matches += 1
                matched_criteria.append(f"Keywords: {', '.join(keyword_matches)}")

        # Check companies
        if criteria.companies:
            total_criteria += 1
            company_lower = job.company.lower()
            company_matches = [c for c in criteria.companies if c.lower() in company_lower]
            if company_matches:
                matches += 1
                matched_criteria.append(f"Company: {job.company}")

        # Check locations
        if criteria.locations and job.location:
            total_criteria += 1
            location_lower = job.location.lower()
            location_matches = [loc for loc in criteria.locations if loc.lower() in location_lower]
            if location_matches:
                matches += 1
                matched_criteria.append(f"Location: {job.location}")

        # Check exclude keywords (negative match)
        if criteria.exclude_keywords:
            exclude_matches = [kw for kw in criteria.exclude_keywords if kw.lower() in job_text]
            if exclude_matches:
                # If excluded keywords are found, reduce score significantly
                return 0.0, []

        # Calculate score
        if total_criteria == 0:
            return 0.0, []

        score = matches / total_criteria
        return score, matched_criteria

    def check_alerts(self, user_id: int) -> List[AlertNotification]:
        """
        Check all active alerts for a user and find matching jobs.

        Args:
            user_id: The ID of the user

        Returns:
            List of AlertNotification for alerts with matches
        """
        notifications = []
        alerts = self.get_alerts(user_id, active_only=True)

        # Get user's profile to access their jobs
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            return notifications

        # Get recent jobs (last 7 days or since last check)
        for alert in alerts:
            criteria = AlertCriteria(
                keywords=self._deserialize_list(alert.keywords),
                companies=self._deserialize_list(alert.companies),
                locations=self._deserialize_list(alert.locations),
                job_types=self._deserialize_list(alert.job_types),
                min_salary=alert.min_salary,
                exclude_keywords=self._deserialize_list(alert.exclude_keywords),
            )

            # Query jobs that were added after the last check
            query = self.db.query(JobApplication).filter(JobApplication.profile_id == profile.id)

            if alert.last_checked:
                query = query.filter(JobApplication.created_at > alert.last_checked)

            jobs = query.all()
            matches = []

            for job in jobs:
                score, matched_criteria = self._calculate_match_score(job, criteria)
                if score > 0:
                    matches.append(
                        JobMatch(
                            job_id=job.id,
                            company=job.company,
                            position=job.position,
                            location=job.location,
                            job_url=job.job_url,
                            match_score=score,
                            matched_criteria=matched_criteria,
                        )
                    )

            if matches:
                notification = AlertNotification(
                    alert_id=alert.id,
                    alert_name=alert.name,
                    matches=matches,
                    message=f"Found {len(matches)} new job(s) matching your alert '{alert.name}'",
                )
                notifications.append(notification)

            # Update last_checked timestamp
            alert.last_checked = datetime.utcnow()
            if matches:
                alert.last_notified = datetime.utcnow()

        self.db.commit()
        return notifications

    def test_alert(self, alert_id: int, user_id: int, limit: int = 50) -> Optional[Dict[str, Any]]:
        """
        Test an alert against recent jobs to see what would match.

        Args:
            alert_id: The ID of the alert to test
            user_id: The ID of the user
            limit: Maximum number of jobs to check

        Returns:
            Test result dictionary or None if alert not found
        """
        alert = self.get_alert(alert_id, user_id)
        if not alert:
            return None

        # Get user's profile
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            return {
                "alert_id": alert_id,
                "total_jobs_checked": 0,
                "matching_jobs": [],
                "match_count": 0,
            }

        criteria = AlertCriteria(
            keywords=self._deserialize_list(alert.keywords),
            companies=self._deserialize_list(alert.companies),
            locations=self._deserialize_list(alert.locations),
            job_types=self._deserialize_list(alert.job_types),
            min_salary=alert.min_salary,
            exclude_keywords=self._deserialize_list(alert.exclude_keywords),
        )

        # Get recent jobs
        jobs = (
            self.db.query(JobApplication)
            .filter(JobApplication.profile_id == profile.id)
            .order_by(JobApplication.created_at.desc())
            .limit(limit)
            .all()
        )

        matches = []
        for job in jobs:
            score, matched_criteria = self._calculate_match_score(job, criteria)
            if score > 0:
                matches.append(
                    JobMatch(
                        job_id=job.id,
                        company=job.company,
                        position=job.position,
                        location=job.location,
                        job_url=job.job_url,
                        match_score=score,
                        matched_criteria=matched_criteria,
                    )
                )

        # Sort by match score descending
        matches.sort(key=lambda x: x.match_score, reverse=True)

        return {
            "alert_id": alert_id,
            "total_jobs_checked": len(jobs),
            "matching_jobs": [m.model_dump() for m in matches],
            "match_count": len(matches),
        }

    def alert_to_response(self, alert: JobAlert) -> Dict[str, Any]:
        """
        Convert a JobAlert model to a response dictionary.

        Args:
            alert: The JobAlert instance

        Returns:
            Dictionary suitable for API response
        """
        return {
            "id": alert.id,
            "user_id": alert.user_id,
            "name": alert.name,
            "keywords": self._deserialize_list(alert.keywords),
            "companies": self._deserialize_list(alert.companies),
            "locations": self._deserialize_list(alert.locations),
            "job_types": self._deserialize_list(alert.job_types),
            "min_salary": alert.min_salary,
            "exclude_keywords": self._deserialize_list(alert.exclude_keywords),
            "is_active": alert.is_active,
            "last_checked": alert.last_checked,
            "last_notified": alert.last_notified,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at,
        }


def get_job_alert_service(db: Session) -> JobAlertService:
    """Factory function to create a JobAlertService instance."""
    return JobAlertService(db)
