"""
Tests for authentication endpoints.

Tests:
- User registration (success, duplicate username, duplicate email, invalid email)
- Login (success, wrong password, non-existent user)
- Token refresh
- Protected endpoint access without token
- Current user info endpoint
- Password change
- Inactive user handling
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.middleware.auth import create_access_token, create_refresh_token, get_password_hash
from app.models.user import User


class TestUserRegistration:
    """Tests for user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, db: Session):
        """Test successful user registration."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!",  # 12+ chars, upper, lower, digit, special
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert data["is_admin"] is False
        assert "password" not in data
        assert "password_hash" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test registration with duplicate username."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": test_user.username,  # Same username
                "email": "different@example.com",
                "password": "SecurePass123!",  # Valid password
            },
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """Test registration with duplicate email."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "differentuser",
                "email": test_user.email,  # Same email
                "password": "SecurePass123!",  # Valid password
            },
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient, db: Session):
        """Test registration with invalid email format."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "invalid-email",  # Invalid email
                "password": "password123",
            },
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_username(self, client: AsyncClient, db: Session):
        """Test registration with too short username."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "ab",  # Too short (min 3)
                "email": "valid@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient, db: Session):
        """Test registration with too short password."""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "validuser",
                "email": "valid@example.com",
                "password": "short",  # Too short (min 6)
            },
        )
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Tests for user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, db: Session, test_user: User):
        """Test successful login."""
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

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, db: Session, test_user: User):
        """Test login with wrong password."""
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
    async def test_login_nonexistent_user(self, client: AsyncClient, db: Session):
        """Test login with non-existent user."""
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
    async def test_login_inactive_user(self, client: AsyncClient, db: Session, inactive_user: User):
        """Test login with inactive user account."""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": inactive_user.username,
                "password": "inactivepassword123",
            },
        )
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, db: Session, test_user: User):
        """Test successful token refresh."""
        # Create a valid refresh token with token_version
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
    async def test_refresh_token_invalid(self, client: AsyncClient, db: Session):
        """Test token refresh with invalid token."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, client: AsyncClient, db: Session, test_user: User):
        """Test token refresh with tampered/invalid token."""
        # Create a tampered token
        token_data = {"sub": str(test_user.id), "username": test_user.username}
        valid_token = create_refresh_token(token_data)
        # Tamper with the token
        tampered_token = valid_token[:-5] + "xxxxx"

        response = await client.post(
            "/api/auth/refresh",
            params={"refresh_token": tampered_token},
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Tests for protected endpoint access."""

    @pytest.mark.asyncio
    async def test_access_protected_without_token(self, client: AsyncClient, db: Session):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_access_protected_with_invalid_token(self, client: AsyncClient, db: Session):
        """Test accessing protected endpoint with invalid token."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_with_valid_token(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test accessing protected endpoint with valid token."""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_access_protected_with_malformed_header(self, client: AsyncClient, db: Session):
        """Test accessing protected endpoint with malformed authorization header."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "InvalidFormat token123"},
        )
        assert response.status_code == 401


class TestCurrentUser:
    """Tests for current user info endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_info(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test getting current user information."""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert data["is_active"] is True
        assert "password" not in data
        assert "password_hash" not in data


class TestPasswordChange:
    """Tests for password change endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test successful password change."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecurePass456!",  # 12+ chars, upper, lower, digit, special
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

        # Verify can login with new password
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "NewSecurePass456!",
            },
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test password change with wrong current password."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_too_short(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test password change with too short new password."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "Short1!",  # Less than 12 characters
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "12 characters" in response.json()["detail"]


class TestLockoutStatus:
    """Tests for lockout status endpoint."""

    @pytest.mark.asyncio
    async def test_check_lockout_status_own_account(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Test checking lockout status for own account (requires auth)."""
        response = await client.get(
            f"/api/auth/lockout-status/{test_user.username}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["is_locked"] is False
        assert data["recent_failures"] == 0
        assert data["can_attempt_login"] is True


class TestHealthAndRoot:
    """Tests for health and root endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient, db: Session):
        """Test root endpoint returns app info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient, db: Session):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
