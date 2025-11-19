import os
import streamlit as st
from dotenv import load_dotenv
from models.database import init_database
from models.auth_database import init_auth_database
from utils.auth import init_session_state, is_authenticated, get_current_profile, show_auth_sidebar

# Load environment variables
load_dotenv()

# Initialize databases
init_database()
init_auth_database()
init_session_state()

# Page configuration
st.set_page_config(
    page_title="ResuBoost AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Show auth sidebar
show_auth_sidebar()

# Check authentication
if not is_authenticated():
    st.title("🚀 ResuBoost AI")
    st.markdown("### Your AI-Powered Career Toolkit")

    st.warning("⚠️ Please log in to access ResuBoost AI")
    st.info("👉 Use the **Login** page from the sidebar to sign in or create an account")

    st.markdown("---")
    st.header("🎯 Features")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 📄 Resume Optimizer
        - ATS Score Analysis
        - AI Optimization
        - Keyword Matching
        - Version Management
        """)

    with col2:
        st.markdown("""
        ### 📝 Cover Letter Generator
        - Personalized Letters
        - Professional Tone
        - Quick Customization
        - Save & Reuse
        """)

    with col3:
        st.markdown("""
        ### 📊 Job Tracker
        - Application Management
        - Status Updates
        - Deadline Tracking
        - Analytics
        """)

    st.stop()

# Main page (authenticated users only)
st.title("🚀 ResuBoost AI")
st.markdown("### Your AI-Powered Career Toolkit")

st.markdown("""
Welcome to ResuBoost AI - a comprehensive suite of tools to supercharge your job search!
""")

# Feature cards
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📄 Resume Optimizer
    - **ATS Score Analysis** - See how well your resume passes applicant tracking systems
    - **AI Optimization** - Get personalized suggestions to improve your resume
    - **Keyword Matching** - Identify missing keywords from job descriptions
    - **Version Management** - Save and manage multiple resume versions
    """)

with col2:
    st.markdown("""
    ### 📝 Cover Letter Generator
    - **Personalized Letters** - AI-generated cover letters tailored to each job
    - **Professional Tone** - Compelling and professional writing
    - **Quick Customization** - Easy editing and refinement
    - **Save & Reuse** - Store templates for future applications
    """)

with col3:
    st.markdown("""
    ### 📊 Job Tracker
    - **Application Management** - Track all your job applications in one place
    - **Status Updates** - Monitor application progress
    - **Deadline Tracking** - Never miss an important date
    - **Analytics** - Insights into your job search performance
    """)

# Getting Started section
st.markdown("---")
st.header("🎯 Getting Started")

st.markdown("""
1. **Set up your profile** - Add your basic information in the Profile page
2. **Optimize your resume** - Upload your resume and get instant ATS feedback
3. **Track applications** - Log your job applications and stay organized
4. **Generate documents** - Create tailored cover letters and networking emails
""")

# Quick tips
with st.expander("💡 Pro Tips for Job Hunting"):
    st.markdown("""
    - **Tailor each resume** - Customize your resume for each job application
    - **Use keywords** - Include relevant keywords from the job description
    - **Quantify achievements** - Use numbers and metrics to show impact
    - **Keep it concise** - Aim for 1-2 pages maximum
    - **Proofread** - Always check for grammar and spelling errors
    - **Follow up** - Send a thank-you note after interviews
    """)

# Statistics (if available)
st.markdown("---")
st.header("📈 Your Progress")

try:
    from models.database import get_db_connection

    profile = get_current_profile()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Count resumes
        cursor.execute('SELECT COUNT(*) as count FROM resumes WHERE profile_id = ?', (profile['id'],))
        resume_count = cursor.fetchone()['count']

        # Count applications
        cursor.execute('SELECT COUNT(*) as count FROM job_applications WHERE profile_id = ?', (profile['id'],))
        app_count = cursor.fetchone()['count']

        # Count cover letters
        cursor.execute('SELECT COUNT(*) as count FROM cover_letters WHERE profile_id = ?', (profile['id'],))
        letter_count = cursor.fetchone()['count']

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Resume Versions", resume_count)

    with col2:
        st.metric("Job Applications", app_count)

    with col3:
        st.metric("Cover Letters", letter_count)

    with col4:
        st.metric("Profile", "✅ Active" if profile else "❌ Not Set")

except Exception as e:
    st.info("Start using the tools to see your progress here!")

# Footer
st.markdown("---")
try:
    from config import APP_VERSION
    version_text = f"v{APP_VERSION}"
except ImportError:
    version_text = "v1.0.0"

st.markdown(f"""
<div style='text-align: center'>
    <p>ResuBoost AI {version_text} - Powered by OpenAI GPT-3.5</p>
    <p>Navigate using the sidebar to access different tools →</p>
</div>
""", unsafe_allow_html=True)
