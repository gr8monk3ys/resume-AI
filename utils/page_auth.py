"""
Page authentication decorator to reduce code duplication.

This module provides a simple decorator for Streamlit pages that:
- Initializes authentication databases
- Initializes session state
- Shows authentication sidebar
- Checks if user is authenticated
- Redirects to login if not authenticated
"""

import streamlit as st
from functools import wraps
from models.auth_database import init_auth_database
from utils.auth import init_session_state, is_authenticated, show_auth_sidebar


def require_authentication(page_function):
    """
    Decorator to require authentication for a Streamlit page.

    This decorator handles all the boilerplate code for authentication:
    - Initializes auth database
    - Initializes session state
    - Shows auth sidebar
    - Checks authentication
    - Redirects to login if not authenticated

    Usage:
        @require_authentication
        def my_page():
            st.title("My Protected Page")
            # ... page content

        if __name__ == "__main__":
            my_page()

    Args:
        page_function: The function to wrap with authentication

    Returns:
        Wrapped function that requires authentication
    """
    @wraps(page_function)
    def wrapper(*args, **kwargs):
        # Initialize authentication
        init_auth_database()
        init_session_state()
        show_auth_sidebar()

        # Check if user is authenticated
        if not is_authenticated():
            st.warning("⚠️ Please log in to access this page")
            st.info("👉 Use the **Login** page from the sidebar")
            st.stop()

        # User is authenticated, run the page function
        return page_function(*args, **kwargs)

    return wrapper


def public_page(page_function):
    """
    Decorator for public pages that don't require authentication.

    Still initializes auth system and shows sidebar for convenience.

    Usage:
        @public_page
        def landing_page():
            st.title("Welcome!")
            # ... public content

    Args:
        page_function: The function to wrap

    Returns:
        Wrapped function with auth initialized but not required
    """
    @wraps(page_function)
    def wrapper(*args, **kwargs):
        # Initialize authentication (but don't require it)
        init_auth_database()
        init_session_state()
        show_auth_sidebar()

        # Run the page function
        return page_function(*args, **kwargs)

    return wrapper


# Example usage (for documentation):
if __name__ == "__main__":
    # Example 1: Protected page
    @require_authentication
    def protected_page():
        st.title("Protected Page")
        st.write("This page requires authentication")

    # Example 2: Public page
    @public_page
    def public_landing_page():
        st.title("Public Page")
        st.write("Anyone can see this")
        if is_authenticated():
            st.success("You are logged in!")
        else:
            st.info("Log in to access more features")

    # Use the decorated functions
    # protected_page()
    # public_landing_page()
