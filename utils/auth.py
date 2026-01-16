"""
Authentication utilities for multi-user support
"""
import os
import logging
from datetime import datetime, timedelta
import streamlit as st
from models.auth_database import init_auth_database, authenticate_user, create_user, get_user_by_id
from models.database import get_or_create_profile_for_user

logger = logging.getLogger(__name__)

# Session timeout in minutes (default: 30 minutes)
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))


def init_session_state():
    """Initialize session state variables for authentication."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'profile' not in st.session_state:
        st.session_state.profile = None
    if 'session_created_at' not in st.session_state:
        st.session_state.session_created_at = None
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = None


def _update_activity():
    """Update last activity timestamp."""
    st.session_state.last_activity = datetime.now()


def _check_session_timeout() -> bool:
    """
    Check if session has timed out due to inactivity.

    Returns:
        True if session is valid, False if timed out
    """
    if not st.session_state.get('authenticated'):
        return True  # Not authenticated, no timeout check needed

    last_activity = st.session_state.get('last_activity')
    if not last_activity:
        return True  # No activity tracked yet

    timeout_delta = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    if datetime.now() - last_activity > timeout_delta:
        logger.info(
            f"Session timeout for user {st.session_state.get('user', {}).get('username', 'unknown')} "
            f"after {SESSION_TIMEOUT_MINUTES} minutes of inactivity"
        )
        return False

    return True


def check_and_refresh_session() -> bool:
    """
    Check session validity and refresh activity timestamp.

    Should be called at the start of each page to maintain session.

    Returns:
        True if session is valid, False if expired/invalid
    """
    init_session_state()

    if not st.session_state.get('authenticated'):
        return False

    # Check for session timeout
    if not _check_session_timeout():
        from utils.audit_logger import log_event
        user = st.session_state.get('user', {})
        log_event(
            event_type='session_timeout',
            action='session_expired',
            user_id=user.get('id'),
            details={'message': f"Session timed out after {SESSION_TIMEOUT_MINUTES} minutes of inactivity"}
        )
        # Set flag to show timeout message
        st.session_state._session_timed_out = True
        logout(reason="session_timeout")
        return False

    # Refresh activity timestamp
    _update_activity()
    return True

def login(username: str, password: str) -> tuple:
    """
    Authenticate user and set session state with rate limiting and audit logging.

    Args:
        username: Username to authenticate
        password: Password to check

    Returns:
        tuple: (success: bool, message: str)
    """
    from utils.rate_limiter_auth import (
        check_login_allowed,
        record_failed_login,
        clear_failed_attempts
    )
    from utils.audit_logger import log_login, log_login_failed

    # Check if login is allowed (rate limiting)
    allowed, reason, wait_seconds = check_login_allowed(username)
    if not allowed:
        log_login_failed(username, reason)
        return (False, reason)

    # Attempt authentication
    user = authenticate_user(username, password)

    if user:
        # Clear failed attempts on successful login
        clear_failed_attempts(username)

        # Log successful login
        log_login(user['id'], username)

        # Set session state
        st.session_state.authenticated = True
        st.session_state.user = user
        st.session_state.user_id = user['id']

        # Set session timestamps for timeout tracking
        st.session_state.session_created_at = datetime.now()
        st.session_state.last_activity = datetime.now()

        # Get or create profile for this user
        profile = get_or_create_profile_for_user(
            user['id'],
            name=user['full_name'] or user['username'],
            email=user['email']
        )
        st.session_state.profile = profile

        return (True, "Login successful!")
    else:
        # Record failed attempt and log it
        record_failed_login(username)
        log_login_failed(username, "Invalid credentials")
        return (False, "Invalid username or password")

def logout(reason: str = "user_initiated"):
    """
    Clear session state and log out user with audit logging.

    Args:
        reason: Reason for logout (user_initiated, session_timeout, etc.)
    """
    from utils.audit_logger import log_logout

    # Log logout if user is authenticated
    if st.session_state.get('authenticated') and st.session_state.get('user'):
        user = st.session_state.user
        log_logout(user['id'], user['username'])
        if reason != "user_initiated":
            logger.info(f"User {user['username']} logged out due to: {reason}")

    # Clear session state
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.profile = None
    st.session_state.session_created_at = None
    st.session_state.last_activity = None

def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get('authenticated', False)

def get_current_user():
    """Get current authenticated user."""
    return st.session_state.get('user', None)

def get_current_user_id():
    """Get current user ID."""
    return st.session_state.get('user_id', None)

def get_current_profile():
    """Get current user's profile."""
    return st.session_state.get('profile', None)

def require_auth(func):
    """
    Decorator to require authentication for a function/page.

    Includes session timeout checking and activity refresh.

    Usage:
        @require_auth
        def my_page():
            st.write("This page requires login")
    """
    def wrapper(*args, **kwargs):
        init_session_state()

        # Check session validity (includes timeout check)
        if not check_and_refresh_session():
            if st.session_state.get('_session_timed_out'):
                st.warning("⚠️ Your session has expired due to inactivity. Please log in again.")
                st.session_state._session_timed_out = False
            else:
                st.warning("⚠️ Please log in to access this page")
            st.info("👉 Use the Login page from the sidebar")
            st.stop()

        return func(*args, **kwargs)

    return wrapper

def show_auth_sidebar():
    """Show authentication info in sidebar."""
    init_session_state()

    with st.sidebar:
        st.markdown("---")

        if is_authenticated():
            user = get_current_user()
            st.success(f"✅ Logged in as **{user['username']}**")

            if user.get('full_name'):
                st.caption(f"👤 {user['full_name']}")

            if st.button("🚪 Logout", use_container_width=True):
                logout()
                st.rerun()
        else:
            st.info("🔒 Not logged in")
            st.caption("Use the Login page to sign in")

def register_user(username: str, email: str, password: str, full_name: str = None) -> tuple:
    """
    Register a new user with audit logging.

    Returns:
        (success: bool, message: str)
    """
    from utils.audit_logger import log_registration

    try:
        user_id = create_user(username, email, password, full_name)
        log_registration(user_id, username, email)
        return True, f"User {username} registered successfully! Please log in."
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Registration failed: {str(e)}"

def create_admin_user(username: str = "admin", password: str = None, email: str = "admin@resuboost.ai"):
    """
    Create admin user if it doesn't exist.

    Args:
        username: Admin username (default: "admin")
        password: Admin password (if None, generates secure random password)
        email: Admin email

    Returns:
        tuple: (success: bool, password: str or None)
    """
    import secrets
    import string
    import logging

    logger = logging.getLogger(__name__)

    # Generate secure password if not provided
    if password is None:
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for i in range(16))
        generated = True
    else:
        generated = False

    try:
        create_user(
            username=username,
            email=email,
            password=password,
            full_name="Administrator",
            is_admin=True
        )
        return (True, password if generated else None)
    except ValueError:
        # User already exists
        return (False, None)
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        return (False, None)
