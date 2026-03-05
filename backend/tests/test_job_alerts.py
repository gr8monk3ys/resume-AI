"""
Tests for the job alerts router.

Tests cover:
- CRUD operations for job alerts
- Alert activation/deactivation
- Alert testing
- Bulk alert checking
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.job_alert import JobAlert
from app.models.user import User


@pytest.fixture
def test_alert_data() -> dict:
    """Test job alert creation data."""
    return {
        "name": "Python Developer Jobs",
        "keywords": ["python", "django", "fastapi"],
        "companies": ["Google", "Meta"],
        "locations": ["Remote", "San Francisco"],
        "job_types": ["Full-time"],
        "min_salary": 100000,
        "exclude_keywords": ["senior", "lead"],
        "is_active": True,
    }


@pytest.fixture
def test_alert(db: Session, test_user: User, test_alert_data: dict) -> JobAlert:
    """Create a test job alert in the database."""
    import json

    alert = JobAlert(
        user_id=test_user.id,
        name=test_alert_data["name"],
        keywords=json.dumps(test_alert_data["keywords"]),
        companies=json.dumps(test_alert_data["companies"]),
        locations=json.dumps(test_alert_data["locations"]),
        job_types=json.dumps(test_alert_data["job_types"]),
        min_salary=test_alert_data["min_salary"],
        exclude_keywords=json.dumps(test_alert_data["exclude_keywords"]),
        is_active=True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


class TestListAlerts:
    """Tests for GET /api/alerts"""

    @pytest.mark.asyncio
    async def test_list_alerts_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing alerts when none exist."""
        response = await client.get("/api/alerts", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_alerts_with_data(
        self, client: AsyncClient, auth_headers: dict, test_alert: JobAlert
    ):
        """Test listing alerts when alerts exist."""
        response = await client.get("/api/alerts", headers=auth_headers)
        assert response.status_code == 200
        alerts = response.json()
        assert len(alerts) == 1
        assert alerts[0]["name"] == test_alert.name

    @pytest.mark.asyncio
    async def test_list_alerts_active_only(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_user: User
    ):
        """Test filtering to only active alerts."""
        import json

        # Create active and inactive alerts
        active_alert = JobAlert(
            user_id=test_user.id,
            name="Active Alert",
            keywords=json.dumps(["test"]),
            is_active=True,
        )
        inactive_alert = JobAlert(
            user_id=test_user.id,
            name="Inactive Alert",
            keywords=json.dumps(["test"]),
            is_active=False,
        )
        db.add_all([active_alert, inactive_alert])
        db.commit()

        response = await client.get(
            "/api/alerts", headers=auth_headers, params={"active_only": True}
        )
        assert response.status_code == 200
        alerts = response.json()
        assert len(alerts) == 1
        assert alerts[0]["name"] == "Active Alert"

    @pytest.mark.asyncio
    async def test_list_alerts_unauthorized(self, client: AsyncClient):
        """Test listing alerts without authentication."""
        response = await client.get("/api/alerts")
        assert response.status_code == 401


class TestCreateAlert:
    """Tests for POST /api/alerts"""

    @pytest.mark.asyncio
    async def test_create_alert_success(
        self, client: AsyncClient, auth_headers: dict, test_alert_data: dict
    ):
        """Test successful alert creation."""
        response = await client.post("/api/alerts", headers=auth_headers, json=test_alert_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == test_alert_data["name"]
        assert data["keywords"] == test_alert_data["keywords"]
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_alert_minimal(self, client: AsyncClient, auth_headers: dict):
        """Test creating alert with minimal data."""
        response = await client.post(
            "/api/alerts",
            headers=auth_headers,
            json={"name": "Minimal Alert", "keywords": ["developer"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Alert"

    @pytest.mark.asyncio
    async def test_create_alert_unauthorized(self, client: AsyncClient, test_alert_data: dict):
        """Test creating alert without authentication."""
        response = await client.post("/api/alerts", json=test_alert_data)
        assert response.status_code == 401


class TestGetAlert:
    """Tests for GET /api/alerts/{alert_id}"""

    @pytest.mark.asyncio
    async def test_get_alert_success(
        self, client: AsyncClient, auth_headers: dict, test_alert: JobAlert
    ):
        """Test getting a specific alert."""
        response = await client.get(f"/api/alerts/{test_alert.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_alert.id
        assert data["name"] == test_alert.name

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent alert."""
        response = await client.get("/api/alerts/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_alert_unauthorized(self, client: AsyncClient, test_alert: JobAlert):
        """Test getting alert without authentication."""
        response = await client.get(f"/api/alerts/{test_alert.id}")
        assert response.status_code == 401


class TestUpdateAlert:
    """Tests for PUT /api/alerts/{alert_id}"""

    @pytest.mark.asyncio
    async def test_update_alert_success(
        self, client: AsyncClient, auth_headers: dict, test_alert: JobAlert
    ):
        """Test updating an alert."""
        update_data = {"name": "Updated Alert Name", "min_salary": 150000}
        response = await client.put(
            f"/api/alerts/{test_alert.id}", headers=auth_headers, json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Alert Name"
        assert data["min_salary"] == 150000

    @pytest.mark.asyncio
    async def test_update_alert_keywords(
        self, client: AsyncClient, auth_headers: dict, test_alert: JobAlert
    ):
        """Test updating alert keywords."""
        update_data = {"keywords": ["react", "typescript", "node"]}
        response = await client.put(
            f"/api/alerts/{test_alert.id}", headers=auth_headers, json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["keywords"] == ["react", "typescript", "node"]

    @pytest.mark.asyncio
    async def test_update_alert_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test updating a non-existent alert."""
        response = await client.put(
            "/api/alerts/99999", headers=auth_headers, json={"name": "New Name"}
        )
        assert response.status_code == 404


class TestDeleteAlert:
    """Tests for DELETE /api/alerts/{alert_id}"""

    @pytest.mark.asyncio
    async def test_delete_alert_success(
        self, client: AsyncClient, auth_headers: dict, test_alert: JobAlert, db: Session
    ):
        """Test deleting an alert."""
        response = await client.delete(f"/api/alerts/{test_alert.id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify alert is deleted
        deleted = db.query(JobAlert).filter(JobAlert.id == test_alert.id).first()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_alert_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test deleting a non-existent alert."""
        response = await client.delete("/api/alerts/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_alert_unauthorized(self, client: AsyncClient, test_alert: JobAlert):
        """Test deleting alert without authentication."""
        response = await client.delete(f"/api/alerts/{test_alert.id}")
        assert response.status_code == 401


class TestToggleAlert:
    """Tests for POST /api/alerts/{alert_id}/toggle"""

    @pytest.mark.asyncio
    async def test_toggle_alert_deactivate(
        self, client: AsyncClient, auth_headers: dict, test_alert: JobAlert
    ):
        """Test toggling an active alert to inactive."""
        assert test_alert.is_active is True
        response = await client.post(f"/api/alerts/{test_alert.id}/toggle", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_toggle_alert_activate(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_user: User
    ):
        """Test toggling an inactive alert to active."""
        import json

        inactive_alert = JobAlert(
            user_id=test_user.id,
            name="Inactive Alert",
            keywords=json.dumps(["test"]),
            is_active=False,
        )
        db.add(inactive_alert)
        db.commit()
        db.refresh(inactive_alert)

        response = await client.post(
            f"/api/alerts/{inactive_alert.id}/toggle", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_toggle_alert_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test toggling a non-existent alert."""
        response = await client.post("/api/alerts/99999/toggle", headers=auth_headers)
        assert response.status_code == 404


class TestTestAlert:
    """Tests for POST /api/alerts/{alert_id}/test"""

    @pytest.mark.asyncio
    async def test_test_alert_success(
        self, client: AsyncClient, auth_headers: dict, test_alert: JobAlert
    ):
        """Test testing an alert."""
        response = await client.post(f"/api/alerts/{test_alert.id}/test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "matching_jobs" in data or "matches" in data or "match_count" in data

    @pytest.mark.asyncio
    async def test_test_alert_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test testing a non-existent alert."""
        response = await client.post("/api/alerts/99999/test", headers=auth_headers)
        assert response.status_code == 404


class TestCheckAlerts:
    """Tests for POST /api/alerts/check"""

    @pytest.mark.asyncio
    async def test_check_alerts(
        self, client: AsyncClient, auth_headers: dict, test_alert: JobAlert
    ):
        """Test checking all active alerts for matches."""
        response = await client.post("/api/alerts/check", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "notification_count" in data
        assert "notifications" in data

    @pytest.mark.asyncio
    async def test_check_alerts_no_active(
        self, client: AsyncClient, auth_headers: dict, db: Session, test_user: User
    ):
        """Test checking alerts when none are active."""
        import json

        # Create only inactive alerts
        inactive_alert = JobAlert(
            user_id=test_user.id,
            name="Inactive",
            keywords=json.dumps(["test"]),
            is_active=False,
        )
        db.add(inactive_alert)
        db.commit()

        response = await client.post("/api/alerts/check", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["notification_count"] == 0

    @pytest.mark.asyncio
    async def test_check_alerts_unauthorized(self, client: AsyncClient):
        """Test checking alerts without authentication."""
        response = await client.post("/api/alerts/check")
        assert response.status_code == 401


class TestAlertIsolation:
    """Tests for user isolation of alerts."""

    @pytest.mark.asyncio
    async def test_user_cannot_see_other_users_alerts(
        self, client: AsyncClient, auth_headers: dict, db: Session
    ):
        """Test that users can only see their own alerts."""
        import json

        from app.middleware.auth import get_password_hash

        # Create another user with an alert
        other_user = User(
            username="otheruser",
            email="other@example.com",
            password_hash=get_password_hash("password123"),
            is_active=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        other_alert = JobAlert(
            user_id=other_user.id,
            name="Other User Alert",
            keywords=json.dumps(["secret"]),
            is_active=True,
        )
        db.add(other_alert)
        db.commit()

        # Try to access other user's alert
        response = await client.get(f"/api/alerts/{other_alert.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_modify_other_users_alerts(
        self, client: AsyncClient, auth_headers: dict, db: Session
    ):
        """Test that users cannot modify other users' alerts."""
        import json

        from app.middleware.auth import get_password_hash

        # Create another user with an alert
        other_user = User(
            username="otheruser2",
            email="other2@example.com",
            password_hash=get_password_hash("password123"),
            is_active=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        other_alert = JobAlert(
            user_id=other_user.id,
            name="Other User Alert",
            keywords=json.dumps(["secret"]),
            is_active=True,
        )
        db.add(other_alert)
        db.commit()

        # Try to update other user's alert
        response = await client.put(
            f"/api/alerts/{other_alert.id}",
            headers=auth_headers,
            json={"name": "Hacked Alert"},
        )
        assert response.status_code == 404

        # Try to delete other user's alert
        response = await client.delete(f"/api/alerts/{other_alert.id}", headers=auth_headers)
        assert response.status_code == 404
