"""
Authentication utilities for multi-user support
"""
import streamlit as st
from models.auth_database import init_auth_database, authenticate_user, create_user, get_user_by_id
from models.database import get_or_create_profile_for_user

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

def logout():
    """Clear session state and log out user with audit logging."""
    from utils.audit_logger import log_logout

    # Log logout if user is authenticated
    if st.session_state.get('authenticated') and st.session_state.get('user'):
        user = st.session_state.user
        log_logout(user['id'], user['username'])

    # Clear session state
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.profile = None

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

    Usage:
        @require_auth
        def my_page():
            st.write("This page requires login")
    """
    def wrapper(*args, **kwargs):
        init_session_state()

        if not is_authenticated():
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
