import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.auth import init_session_state, login, logout, is_authenticated, register_user, get_current_user
from models.auth_database import init_auth_database

# Import config with fallback
try:
    from config import SHOW_DEMO_CREDENTIALS
except ImportError:
    SHOW_DEMO_CREDENTIALS = True

st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")

# Initialize databases
init_auth_database()
init_session_state()

st.title("🔐 ResuBoost AI - Login")

# Check if already logged in
if is_authenticated():
    user = get_current_user()
    st.success(f"✅ Already logged in as **{user['username']}**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🏠 Go to Home", type="primary", use_container_width=True):
            st.switch_page("app.py")

    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()

    st.stop()

# Create tabs for login and register
tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    st.header("Login to Your Account")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        submitted = st.form_submit_button("🔓 Login", type="primary", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("❌ Please enter both username and password")
            else:
                with st.spinner("Authenticating..."):
                    success, message = login(username, password)
                    if success:
                        st.success(f"✅ {message} Redirecting...")
                        st.balloons()
                        # Wait a moment before redirecting
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")

    st.markdown("---")
    if SHOW_DEMO_CREDENTIALS:
        st.info("💡 **Demo Account:** username: `demo`, password: `demo123`")
    st.caption("Don't have an account? Use the **Register** tab above")

with tab2:
    st.header("Create New Account")

    # Show password requirements
    with st.expander("📋 Password Requirements", expanded=False):
        from utils.password_validator import generate_password_requirements_text
        st.markdown(generate_password_requirements_text())

    with st.form("register_form"):
        new_username = st.text_input("Username*", placeholder="Choose a username")
        new_email = st.text_input("Email*", placeholder="your.email@example.com")
        new_full_name = st.text_input("Full Name", placeholder="John Doe (optional)")
        new_password = st.text_input("Password*", type="password", placeholder="Choose a strong password")
        confirm_password = st.text_input("Confirm Password*", type="password", placeholder="Re-enter password")

        register_submitted = st.form_submit_button("📝 Create Account", type="primary", use_container_width=True)

        if register_submitted:
            from utils.password_validator import (
                validate_password_strength,
                validate_password_confirmation,
                get_password_strength_label,
                suggest_password_improvements
            )
            from utils.input_sanitizer import sanitize_username, sanitize_email, sanitize_text_input

            # Validation
            errors = []

            # Sanitize and validate username
            new_username = sanitize_text_input(new_username, max_length=30)
            if not new_username:
                errors.append("Username is required")
            else:
                username_valid, username_error = sanitize_username(new_username)
                if not username_valid:
                    errors.append(username_error)

            # Sanitize and validate email
            new_email = sanitize_text_input(new_email, max_length=254)
            if not new_email:
                errors.append("Email is required")
            else:
                email_valid, email_error = sanitize_email(new_email)
                if not email_valid:
                    errors.append(email_error)

            # Sanitize full name
            new_full_name = sanitize_text_input(new_full_name, max_length=100) if new_full_name else None

            if not new_password:
                errors.append("Password is required")
            else:
                # Validate password strength
                is_valid, password_errors, strength = validate_password_strength(new_password)
                if not is_valid:
                    errors.extend(password_errors)
                else:
                    # Show password strength
                    label, color = get_password_strength_label(strength)
                    st.info(f"Password Strength: **{label}** ({strength}/100)")

                    # Show suggestions if not very strong
                    if strength < 80:
                        suggestions = suggest_password_improvements(new_password)
                        if suggestions:
                            for suggestion in suggestions:
                                st.warning(suggestion)

            # Validate password confirmation
            conf_valid, conf_error = validate_password_confirmation(new_password, confirm_password)
            if not conf_valid:
                errors.append(conf_error)

            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Try to register
                success, message = register_user(new_username, new_email, new_password, new_full_name or None)

                if success:
                    st.success(f"✅ {message}")
                    st.info("👉 Please use the **Login** tab to sign in")
                else:
                    st.error(f"❌ {message}")

    st.markdown("---")
    st.caption("Already have an account? Use the **Login** tab above")

# Sidebar
with st.sidebar:
    st.header("🔐 Authentication")
    st.markdown("""
    **ResuBoost AI** now supports multiple users!

    **Features:**
    - 🔒 Secure login system
    - 👤 Personal data isolation
    - 📊 Individual resumes & applications
    - 🎯 Private career journal

    **Getting Started:**
    1. Create an account using the Register tab
    2. Log in with your credentials
    3. Start optimizing your job search!
    """)

    st.markdown("---")
    st.caption("Need help? Check the documentation")
