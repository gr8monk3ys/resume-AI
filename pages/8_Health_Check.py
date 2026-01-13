import streamlit as st
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.auth_database import init_auth_database
from utils.auth import init_session_state, is_authenticated, show_auth_sidebar

st.set_page_config(page_title="System Health", page_icon="🏥", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("🏥 System Health Check")
st.markdown("Monitor the health and status of ResuBoost AI")

# Status indicators
def show_status(check_name: str, is_healthy: bool, details: str = ""):
    """Display a status indicator."""
    if is_healthy:
        st.success(f"✅ {check_name}")
    else:
        st.error(f"❌ {check_name}")

    if details:
        st.caption(details)

# Run health checks
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔧 Core Systems")

    # Database check
    try:
        from models.database import get_db_connection, init_database

        init_database()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM profiles")
            profile_count = cursor.fetchone()['count']

        show_status("Database", True, f"{profile_count} profile(s)")
    except Exception as e:
        show_status("Database", False, f"Error: {str(e)}")

    # LLM Service check
    try:
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()
        show_status("LLM Service", True, f"Model: {llm_service.model_name}")
    except Exception as e:
        show_status("LLM Service", False, f"Error: {str(e)}")

    # File Parser check
    try:
        from utils.file_parser import parse_file

        test_text = parse_file(b"test", 'txt')
        show_status("File Parser", test_text == "test", "TXT, PDF, DOCX supported")
    except Exception as e:
        show_status("File Parser", False, f"Error: {str(e)}")

    # ATS Analyzer check
    try:
        from services.resume_analyzer import ATSAnalyzer

        analyzer = ATSAnalyzer()
        show_status("ATS Analyzer", True, "6-factor scoring ready")
    except Exception as e:
        show_status("ATS Analyzer", False, f"Error: {str(e)}")

with col2:
    st.subheader("⚙️ Configuration")

    # Environment variables
    try:
        import os

        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and api_key.startswith('sk-'):
            show_status("OpenAI API Key", True, "Key configured")
        else:
            show_status("OpenAI API Key", False, "Key not found or invalid")
    except Exception as e:
        show_status("OpenAI API Key", False, f"Error: {str(e)}")

    # Config file
    try:
        import config

        show_status("Config File", True, f"v{config.APP_VERSION}")
        st.caption(f"  - Max file size: {config.MAX_FILE_SIZE_MB}MB")
        st.caption(f"  - Model: {config.OPENAI_MODEL}")
        st.caption(f"  - Rate limit: {config.RATE_LIMIT_AI_CALLS}/min")
    except Exception as e:
        show_status("Config File", False, f"Error: {str(e)}")

    # Validators
    try:
        from utils.validators import validate_email, validate_url

        email_valid, _ = validate_email("test@example.com")
        url_valid, _ = validate_url("https://example.com")

        show_status("Validators", email_valid and url_valid, "All validators functional")
    except Exception as e:
        show_status("Validators", False, f"Error: {str(e)}")

# System info
st.markdown("---")
st.subheader("📊 System Information")

col1, col2, col3 = st.columns(3)

with col1:
    try:
        import sys
        st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    except:
        st.metric("Python Version", "Unknown")

with col2:
    try:
        import streamlit
        st.metric("Streamlit Version", streamlit.__version__)
    except:
        st.metric("Streamlit Version", "Unknown")

with col3:
    try:
        import config
        st.metric("App Version", config.APP_VERSION)
    except:
        st.metric("App Version", "1.0.0")

# Database statistics
st.markdown("---")
st.subheader("📈 Database Statistics")

try:
    from models.database import get_db_connection

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get counts - use whitelist to prevent SQL injection
        stats = {}
        ALLOWED_TABLES = {'profiles', 'resumes', 'job_applications', 'cover_letters', 'career_journal'}

        for table in ALLOWED_TABLES:
            # Table name is from whitelist, safe to use in query
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cursor.fetchone()['count']

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Profiles", stats['profiles'])

    with col2:
        st.metric("Resumes", stats['resumes'])

    with col3:
        st.metric("Applications", stats['job_applications'])

    with col4:
        st.metric("Cover Letters", stats['cover_letters'])

    with col5:
        st.metric("Achievements", stats['career_journal'])

except Exception as e:
    st.error(f"Could not load database statistics: {str(e)}")

# Last updated
st.markdown("---")
st.caption(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("🔄 Refresh"):
    st.rerun()

# Sidebar
with st.sidebar:
    st.header("🏥 Health Check")
    st.markdown("""
    This page monitors:
    - Core system components
    - Configuration status
    - Database health
    - API connectivity

    **All green?** You're good to go! ✅

    **Any red?** Check the error message and:
    1. Verify .env file exists
    2. Check requirements installed
    3. Run `python3 test_app.py`
    """)

    st.markdown("---")

    if st.button("🧪 Run Full Test Suite"):
        st.info("Run in terminal: `python3 test_app.py`")
