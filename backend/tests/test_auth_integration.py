"""
Comprehensive integration tests for authentication endpoints.

Tests the complete authentication flow including:
- Registration with validation
- Login with success, failure, and lockout scenarios
- Token refresh and validation
- Password change with security requirements
- Logout and token invalidation
- User isolation and security boundaries

These tests verify end-to-end behavior with the database and all middleware.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.middleware.auth import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.models.profile import Profile
from app.models.user import User


class TestRegistrationFlow:
    """Integration tests for the complete registration flow."""

    @pytest.mark.asyncio
    async def test_register_creates_user_and_profile(self, client: AsyncClient, db: Session):
        """Test that registration creates both user and profile records."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "integrationuser",
                "email": "integration@example.com",
                "password": "SecureP@ssw0rd123!",
                "full_name": "Integration Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()

        # Verify user was created
        user = db.query(User).filter(User.username == "integrationuser").first()
        assert user is not None
        assert user.email == "integration@example.com"
        assert user.full_name == "Integration Test User"
        assert user.is_active is True
        assert user.is_admin is False

        # Verify profile was created automatically
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        assert profile is not None
        assert profile.email == "integration@example.com"

    @pytest.mark.asyncio
    async def test_register_password_not_stored_in_plaintext(
        self, client: AsyncClient, db: Session
    ):
        """Test that password is hashed, not stored in plaintext."""
        password = "SecureP@ssw0rd123!"
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "secureuser",
                "email": "secure@example.com",
                "password": password,
            },
        )
        assert response.status_code == 201

        user = db.query(User).filter(User.username == "secureuser").first()
        assert user.password_hash != password
        assert user.password_hash.startswith("$2b$")  # bcrypt hash prefix

    @pytest.mark.asyncio
    async def test_register_username_case_insensitive_check(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that username uniqueness is checked."""
        # Note: This tests current behavior - username checks may or may not be case-insensitive
        response = await client.post(
            "/api/auth/register",
            json={
                "username": test_user.username,  # Exact match
                "email": "different@example.com",
                "password": "SecureP@ssw0rd123!",
            },
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_email_uniqueness(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that email must be unique."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "differentuser",
                "email": test_user.email,  # Same email
                "password": "SecureP@ssw0rd123!",
            },
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_password_complexity_uppercase(self, client: AsyncClient, db: Session):
        """Test that password requires uppercase letter."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "complexuser",
                "email": "complex@example.com",
                "password": "securep@ssw0rd123!",  # No uppercase
            },
        )
        assert response.status_code == 422
        assert "uppercase" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_register_password_complexity_lowercase(self, client: AsyncClient, db: Session):
        """Test that password requires lowercase letter."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "complexuser",
                "email": "complex@example.com",
                "password": "SECUREP@SSW0RD123!",  # No lowercase
            },
        )
        assert response.status_code == 422
        assert "lowercase" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_register_password_complexity_digit(self, client: AsyncClient, db: Session):
        """Test that password requires a digit."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "complexuser",
                "email": "complex@example.com",
                "password": "SecureP@ssword!!",  # No digit
            },
        )
        assert response.status_code == 422
        assert "digit" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_register_password_complexity_special_char(
        self, client: AsyncClient, db: Session
    ):
        """Test that password requires special character."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "complexuser",
                "email": "complex@example.com",
                "password": "SecurePassw0rd123",  # No special char
            },
        )
        assert response.status_code == 422
        assert "special character" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_register_password_common_pattern_rejected(
        self, client: AsyncClient, db: Session
    ):
        """Test that common password patterns are rejected."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "patternuser",
                "email": "pattern@example.com",
                "password": "MyPassword123!@#",  # Contains 'password'
            },
        )
        assert response.status_code == 422
        assert "common weak pattern" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email_format(self, client: AsyncClient, db: Session):
        """Test that invalid email format is rejected."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "emailuser",
                "email": "not-an-email",
                "password": "SecureP@ssw0rd123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_username_too_short(self, client: AsyncClient, db: Session):
        """Test that username must be at least 3 characters."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "ab",
                "email": "short@example.com",
                "password": "SecureP@ssw0rd123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_username_too_long(self, client: AsyncClient, db: Session):
        """Test that username must not exceed 50 characters."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "a" * 51,
                "email": "long@example.com",
                "password": "SecureP@ssw0rd123!",
            },
        )
        assert response.status_code == 422


class TestLoginFlow:
    """Integration tests for the complete login flow."""

    @pytest.mark.asyncio
    async def test_login_returns_both_tokens(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that successful login returns access and refresh tokens."""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_updates_last_login_timestamp(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that login updates the last_login timestamp."""
        original_last_login = test_user.last_login

        response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200

        # Refresh user from database
        db.refresh(test_user)
        assert test_user.last_login is not None
        if original_last_login:
            assert test_user.last_login > original_last_login

    @pytest.mark.asyncio
    async def test_login_token_can_access_protected_endpoint(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that the returned token can access protected endpoints."""
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Use token to access protected endpoint
        me_response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == test_user.username

    @pytest.mark.asyncio
    async def test_login_wrong_password_fails(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that wrong password returns 401."""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_fails(self, client: AsyncClient, db: Session):
        """Test that nonexistent user returns 401."""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_user_fails(
        self, client: AsyncClient, db: Session, inactive_user: User
    ):
        """Test that inactive user cannot login."""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": inactive_user.username,
                "password": "inactivepassword123",
            },
        )
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_uses_form_data_not_json(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that login endpoint expects form data (OAuth2 spec)."""
        # JSON body should not work for login (OAuth2 requires form data)
        response = await client.post(
            "/api/auth/login",
            json={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 422  # Validation error - expects form data


class TestTokenRefreshFlow:
    """Integration tests for token refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_tokens(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that refresh endpoint returns new access and refresh tokens."""
        token_data = {"sub": str(test_user.id), "username": test_user.username}
        refresh_token = create_refresh_token(token_data, token_version=test_user.token_version)

        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_new_token_is_valid(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that the refreshed access token can access protected endpoints."""
        token_data = {"sub": str(test_user.id), "username": test_user.username}
        refresh_token = create_refresh_token(token_data, token_version=test_user.token_version)

        refresh_response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]

        # Use new token
        me_response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_response.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_fails(self, client: AsyncClient, db: Session):
        """Test that invalid refresh token returns 401."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token-string"},
        )
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_tampered_token_fails(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that tampered refresh token returns 401."""
        token_data = {"sub": str(test_user.id), "username": test_user.username}
        refresh_token = create_refresh_token(token_data, token_version=test_user.token_version)
        # Tamper with the token
        tampered_token = refresh_token[:-10] + "xxxxxxxxxx"

        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": tampered_token},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_access_token_rejected(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that access token cannot be used as refresh token."""
        token_data = {"sub": str(test_user.id), "username": test_user.username}
        access_token = create_access_token(token_data, token_version=test_user.token_version)

        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )
        # Should fail because it's an access token, not a refresh token
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalidated_after_password_change(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test that old refresh tokens are invalidated after password change."""
        # Get initial refresh token
        token_data = {"sub": str(test_user.id), "username": test_user.username}
        old_refresh_token = create_refresh_token(token_data, token_version=test_user.token_version)

        # Change password (increments token_version)
        test_user.token_version = (test_user.token_version or 0) + 1
        test_user.password_hash = get_password_hash("NewSecureP@ss123!")
        db.commit()

        # Old refresh token should now be invalid
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert response.status_code == 401
        assert "invalidated" in response.json()["detail"].lower()


class TestPasswordChangeFlow:
    """Integration tests for password change functionality."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful password change."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecureP@ss123!",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_change_password_can_login_with_new_password(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that user can login with new password after change."""
        # Change password
        await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecureP@ss123!",
            },
            headers=auth_headers,
        )

        # Login with new password
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "NewSecureP@ss123!",
            },
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_old_password_invalid(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that old password no longer works after change."""
        # Change password
        await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecureP@ss123!",
            },
            headers=auth_headers,
        )

        # Try login with old password
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 401

    @pytest.mark.asyncio
    async def test_change_password_wrong_current_password(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that wrong current password fails."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "wrongcurrentpassword",
                "new_password": "NewSecureP@ss123!",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_weak_new_password(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that weak new password is rejected."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "weak",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "12 characters" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_change_password_invalidates_tokens(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that password change invalidates existing tokens."""
        original_token_version = test_user.token_version

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecureP@ss123!",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Refresh user from database
        db.refresh(test_user)
        assert test_user.token_version > (original_token_version or 0)

    @pytest.mark.asyncio
    async def test_change_password_requires_authentication(self, client: AsyncClient, db: Session):
        """Test that password change requires authentication."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "anypassword",
                "new_password": "NewSecureP@ss123!",
            },
        )
        assert response.status_code == 401


class TestProtectedEndpointAccess:
    """Integration tests for protected endpoint access control."""

    @pytest.mark.asyncio
    async def test_access_without_token_fails(self, client: AsyncClient, db: Session):
        """Test that protected endpoints require a token."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_access_with_invalid_token_fails(self, client: AsyncClient, db: Session):
        """Test that invalid token is rejected."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_with_malformed_header_fails(self, client: AsyncClient, db: Session):
        """Test that malformed authorization header is rejected."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer token123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_with_empty_bearer_fails(self, client: AsyncClient, db: Session):
        """Test that empty bearer token is rejected."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_with_valid_token_succeeds(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that valid token grants access."""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_current_user_excludes_sensitive_data(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that /me endpoint excludes password data."""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data


class TestLockoutStatus:
    """Integration tests for lockout status endpoint."""

    @pytest.mark.asyncio
    async def test_lockout_status_own_account(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that user can check their own lockout status."""
        response = await client.get(
            f"/api/auth/lockout-status/{test_user.username}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert "is_locked" in data
        assert "recent_failures" in data
        assert "can_attempt_login" in data

    @pytest.mark.asyncio
    async def test_lockout_status_other_account_forbidden(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test that non-admin cannot check other user's lockout status."""
        response = await client.get(
            "/api/auth/lockout-status/otherusername",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "only check your own" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_lockout_status_admin_can_check_any(
        self, client: AsyncClient, db: Session, admin_user: User, admin_auth_headers: dict
    ):
        """Test that admin can check any user's lockout status."""
        response = await client.get(
            "/api/auth/lockout-status/anyusername",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lockout_status_requires_auth(self, client: AsyncClient, db: Session):
        """Test that lockout status endpoint requires authentication."""
        response = await client.get("/api/auth/lockout-status/testuser")
        assert response.status_code == 401


class TestHealthEndpoints:
    """Integration tests for health and root endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint_returns_app_info(self, client: AsyncClient, db: Session):
        """Test that root endpoint returns application information."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_healthy(self, client: AsyncClient, db: Session):
        """Test that health endpoint returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_endpoint_no_auth_required(self, client: AsyncClient, db: Session):
        """Test that health endpoint does not require authentication."""
        # Explicitly no headers
        response = await client.get("/health")
        assert response.status_code == 200


class TestUserIsolation:
    """Integration tests for user data isolation in auth context."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_info(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
        second_user: User,
    ):
        """Test that /me endpoint only shows current user's info."""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["id"] != second_user.id

    @pytest.mark.asyncio
    async def test_tokens_are_user_specific(
        self,
        client: AsyncClient,
        db: Session,
        test_user: User,
        auth_headers: dict,
        second_user: User,
        second_user_auth_headers: dict,
    ):
        """Test that tokens are specific to each user."""
        # First user's token
        response1 = await client.get("/api/auth/me", headers=auth_headers)
        assert response1.json()["id"] == test_user.id

        # Second user's token
        response2 = await client.get("/api/auth/me", headers=second_user_auth_headers)
        assert response2.json()["id"] == second_user.id
