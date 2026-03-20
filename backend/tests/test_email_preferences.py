"""Tests for email preferences endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.user import User


class TestGetEmailPreferences:
    @pytest.mark.asyncio
    async def test_returns_defaults(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/email-preferences", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["email_notifications"] is True
        assert data["email_nudges"] is True
        assert data["email_weekly_digest"] is True
        assert data["email_reengagement"] is True

    @pytest.mark.asyncio
    async def test_unauthorized_returns_401(self, client: AsyncClient):
        response = await client.get("/api/email-preferences")
        assert response.status_code == 401


class TestUpdateEmailPreferences:
    @pytest.mark.asyncio
    async def test_update_single_field(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/email-preferences",
            json={"email_nudges": False},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["email_nudges"] is False
        assert data["email_notifications"] is True
        assert data["email_weekly_digest"] is True
        assert data["email_reengagement"] is True

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/email-preferences",
            json={
                "email_notifications": False,
                "email_weekly_digest": False,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["email_notifications"] is False
        assert data["email_weekly_digest"] is False
        assert data["email_nudges"] is True

    @pytest.mark.asyncio
    async def test_update_persists_on_subsequent_get(self, client: AsyncClient, auth_headers: dict):
        await client.patch(
            "/api/email-preferences",
            json={"email_reengagement": False},
            headers=auth_headers,
        )

        response = await client.get("/api/email-preferences", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email_reengagement"] is False

    @pytest.mark.asyncio
    async def test_empty_update_is_noop(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/email-preferences",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["email_notifications"] is True
        assert data["email_nudges"] is True

    @pytest.mark.asyncio
    async def test_unauthorized_returns_401(self, client: AsyncClient):
        response = await client.patch(
            "/api/email-preferences",
            json={"email_nudges": False},
        )
        assert response.status_code == 401
