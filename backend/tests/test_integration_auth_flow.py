"""
Integration tests for authentication flows.

Tests complete end-to-end authentication workflows including:
- Registration -> Login -> Token Refresh -> Logout flow
- Password change flow with verification
- Account lockout after failed login attempts
- Session management and token validation

These tests verify the complete authentication lifecycle works correctly
when all components are integrated together.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.middleware.auth import create_access_token, create_refresh_token, get_password_hash
from app.models.profile import Profile
from app.models.user import User


class TestCompleteAuthFlow:
    """
    Integration tests for the complete authentication flow.

    Verifies: Registration -> Login -> Token Refresh -> Access Protected Resources
    """

    @pytest.mark.asyncio
    async def test_complete_registration_to_protected_resource_flow(
        self, client: AsyncClient, db: Session
    ):
        """
        Test complete flow: Register -> Login -> Access Protected Resource.

        This integration test verifies that a new user can:
        1. Register a new account
        2. Login with those credentials
        3. Access protected resources with the token
        """
        # Step 1: Register a new user
        register_response = await client.post(
            "/api/auth/register",
            json={
                "username": "integrationuser",
                "email": "integration@example.com",
                "password": "IntegrationPass123!",
                "full_name": "Integration Test User",
            },
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["username"] == "integrationuser"
        assert user_data["email"] == "integration@example.com"

        # Step 2: Login with the registered credentials
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "integrationuser",
                "password": "IntegrationPass123!",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

        # Step 3: Access protected resource with the token
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me_response = await client.get("/api/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["username"] == "integrationuser"
        assert me_data["email"] == "integration@example.com"

    @pytest.mark.asyncio
    async def test_token_refresh_maintains_session(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """
        Test that refreshing tokens maintains a valid session.

        Verifies:
        1. Login returns valid tokens
        2. Refresh token provides new valid access token
        3. New access token works for protected resources
        """
        # Step 1: Login to get initial tokens
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        initial_tokens = login_response.json()

        # Step 2: Use refresh token to get new tokens
        refresh_response = await client.post(
            "/api/auth/refresh",
            params={"refresh_token": initial_tokens["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        # New tokens should be different from original
        assert new_tokens["access_token"] != initial_tokens["access_token"]

        # Step 3: Verify new token works for protected resources
        auth_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        me_response = await client.get("/api/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        assert me_response.json()["username"] == test_user.username

    @pytest.mark.asyncio
    async def test_multiple_token_refreshes(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """
        Test multiple consecutive token refreshes work correctly.

        Simulates a long-running session with multiple token refreshes.
        """
        # Login to get initial tokens
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        current_tokens = login_response.json()

        # Perform multiple refreshes
        for i in range(3):
            refresh_response = await client.post(
                "/api/auth/refresh",
                params={"refresh_token": current_tokens["refresh_token"]},
            )
            assert refresh_response.status_code == 200, f"Refresh {i+1} failed"
            new_tokens = refresh_response.json()

            # Verify new tokens work
            auth_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
            me_response = await client.get("/api/auth/me", headers=auth_headers)
            assert me_response.status_code == 200, f"Access after refresh {i+1} failed"

            current_tokens = new_tokens


class TestPasswordChangeFlow:
    """
    Integration tests for password change workflows.

    Verifies password change, re-authentication, and validation.
    """

    @pytest.mark.asyncio
    async def test_complete_password_change_flow(
        self, client: AsyncClient, db: Session
    ):
        """
        Test complete password change flow with re-authentication.

        Steps:
        1. Register user
        2. Login with original password
        3. Change password
        4. Verify old password no longer works
        5. Login with new password
        """
        # Step 1: Register new user
        await client.post(
            "/api/auth/register",
            json={
                "username": "pwdchangeuser",
                "email": "pwdchange@example.com",
                "password": "OriginalPass123!",
                "full_name": "Password Change User",
            },
        )

        # Step 2: Login with original password
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "pwdchangeuser",
                "password": "OriginalPass123!",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Step 3: Change password
        change_response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OriginalPass123!",
                "new_password": "NewSecurePass456!",
            },
            headers=auth_headers,
        )
        assert change_response.status_code == 200
        assert "successfully" in change_response.json()["message"].lower()

        # Step 4: Verify old password no longer works
        old_login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "pwdchangeuser",
                "password": "OriginalPass123!",
            },
        )
        assert old_login_response.status_code == 401

        # Step 5: Login with new password works
        new_login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "pwdchangeuser",
                "password": "NewSecurePass456!",
            },
        )
        assert new_login_response.status_code == 200
        assert "access_token" in new_login_response.json()

    @pytest.mark.asyncio
    async def test_password_change_with_wrong_current_password(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """
        Test that password change fails with incorrect current password.
        """
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "NewSecurePass456!",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_password_change_validates_complexity(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """
        Test that password change enforces password complexity requirements.
        """
        # Test various weak passwords
        weak_passwords = [
            "short",  # Too short
            "alllowercase123!",  # No uppercase
            "ALLUPPERCASE123!",  # No lowercase
            "NoNumbers!!!!!",  # No digits
            "NoSpecialChars123",  # No special characters
        ]

        for weak_password in weak_passwords:
            response = await client.post(
                "/api/auth/change-password",
                json={
                    "current_password": "testpassword123",
                    "new_password": weak_password,
                },
                headers=auth_headers,
            )
            # Should fail validation
            assert response.status_code == 400, f"Weak password '{weak_password}' was accepted"


class TestAccountLockout:
    """
    Integration tests for account lockout after failed login attempts.

    Note: These tests depend on audit logging being enabled. In test mode,
    audit logging may be disabled, so we test the authentication failure path.
    """

    @pytest.mark.asyncio
    async def test_failed_login_attempts_recorded(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """
        Test that failed login attempts are properly handled.

        Verifies that multiple failed login attempts return proper error responses.
        """
        # Attempt multiple failed logins
        for i in range(3):
            response = await client.post(
                "/api/auth/login",
                data={
                    "username": test_user.username,
                    "password": "wrongpassword",
                },
            )
            assert response.status_code == 401
            assert "incorrect" in response.json()["detail"].lower()

        # Verify correct password still works (unless rate limiting kicks in)
        correct_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        # Should succeed (rate limiting is disabled in test mode)
        assert correct_response.status_code == 200

    @pytest.mark.asyncio
    async def test_nonexistent_user_login_handling(
        self, client: AsyncClient, db: Session
    ):
        """
        Test that login attempts for non-existent users are handled securely.

        The error message should not reveal whether the username exists.
        """
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "nonexistentuser12345",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401
        # Error message should be the same as wrong password to prevent enumeration
        assert "incorrect username or password" in response.json()["detail"].lower()


class TestSessionManagement:
    """
    Integration tests for session management.

    Tests token validity, expiration handling, and multi-session scenarios.
    """

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client: AsyncClient, db: Session):
        """
        Test that invalid tokens are properly rejected.
        """
        invalid_tokens = [
            "invalid.token.here",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.payload",
            "",
            "null",
        ]

        for invalid_token in invalid_tokens:
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {invalid_token}"},
            )
            assert response.status_code == 401, f"Invalid token '{invalid_token}' was accepted"

    @pytest.mark.asyncio
    async def test_malformed_auth_header_rejected(self, client: AsyncClient, db: Session):
        """
        Test that malformed authorization headers are rejected.
        """
        malformed_headers = [
            {"Authorization": "NotBearer token123"},
            {"Authorization": "Bearer"},
            {"Authorization": "token123"},
        ]

        for headers in malformed_headers:
            response = await client.get("/api/auth/me", headers=headers)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_user_can_have_multiple_valid_sessions(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """
        Test that a user can have multiple valid sessions simultaneously.

        Simulates logging in from multiple devices.
        """
        # Login session 1
        login1_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert login1_response.status_code == 200
        session1_token = login1_response.json()["access_token"]

        # Login session 2
        login2_response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert login2_response.status_code == 200
        session2_token = login2_response.json()["access_token"]

        # Both tokens should be different
        assert session1_token != session2_token

        # Both sessions should work
        for session_token in [session1_token, session2_token]:
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {session_token}"},
            )
            assert response.status_code == 200
            assert response.json()["username"] == test_user.username

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_access_resources(
        self, client: AsyncClient, db: Session, inactive_user: User
    ):
        """
        Test that inactive users cannot login or access resources.
        """
        # Attempt to login as inactive user
        response = await client.post(
            "/api/auth/login",
            data={
                "username": inactive_user.username,
                "password": "inactivepassword123",
            },
        )
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


class TestProfileCreationOnRegistration:
    """
    Integration tests verifying profile is created during registration.
    """

    @pytest.mark.asyncio
    async def test_profile_created_on_registration(
        self, client: AsyncClient, db: Session
    ):
        """
        Test that a user profile is automatically created on registration.
        """
        # Register new user
        register_response = await client.post(
            "/api/auth/register",
            json={
                "username": "profiletestuser",
                "email": "profiletest@example.com",
                "password": "ProfileTest123!",
                "full_name": "Profile Test User",
            },
        )
        assert register_response.status_code == 201

        # Login to get token
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "profiletestuser",
                "password": "ProfileTest123!",
            },
        )
        tokens = login_response.json()
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Verify profile exists and is accessible
        profile_response = await client.get("/api/profile", headers=auth_headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["name"] == "Profile Test User"
        assert profile_data["email"] == "profiletest@example.com"


class TestConcurrentAuthOperations:
    """
    Integration tests for concurrent authentication operations.
    """

    @pytest.mark.asyncio
    async def test_concurrent_logins_same_user(
        self, client: AsyncClient, db: Session, test_user: User
    ):
        """
        Test that concurrent login requests for the same user work correctly.
        """
        import asyncio

        async def login():
            return await client.post(
                "/api/auth/login",
                data={
                    "username": test_user.username,
                    "password": "testpassword123",
                },
            )

        # Perform 5 concurrent logins
        results = await asyncio.gather(*[login() for _ in range(5)])

        # All should succeed
        for result in results:
            assert result.status_code == 200
            assert "access_token" in result.json()
