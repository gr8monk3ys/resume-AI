import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.file_parser import extract_text_from_upload
from services.llm_service import get_llm_service
from services.resume_analyzer import ATSAnalyzer, extract_keywords
from models.database import get_db_connection
from models.auth_database import init_auth_database
from utils.rate_limiter import check_rate_limit
from utils.auth import init_session_state, is_authenticated, get_current_profile, show_auth_sidebar

st.set_page_config(page_title="Resume Optimizer", page_icon="📄", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("📄 Resume Optimizer")
st.markdown("Optimize your resume with AI-powered suggestions and ATS scoring")

# Initialize services
llm_service = get_llm_service()
ats_analyzer = ATSAnalyzer()

# Create tabs for different features
tab1, tab2, tab3 = st.tabs(["📊 ATS Analysis", "✨ Optimize Resume", "💾 Save Resume"])

with tab1:
    st.header("ATS Compatibility Analysis")
    st.markdown("Upload your resume to get an ATS (Applicant Tracking System) compatibility score")

    col1, col2 = st.columns(2)

    with col1:
        resume_file = st.file_uploader(
            "Upload Resume",
            type=['txt', 'pdf', 'docx'],
            key="ats_resume"
        )

    with col2:
        job_desc_file = st.file_uploader(
            "Upload Job Description (Optional)",
            type=['txt', 'pdf', 'docx'],
            key="ats_job_desc"
        )

    if st.button("Analyze ATS Score", type="primary"):
        if resume_file:
            with st.spinner("Analyzing your resume..."):
                try:
                    resume_text = extract_text_from_upload(resume_file)
                    job_desc_text = extract_text_from_upload(job_desc_file) if job_desc_file else ""

                    # Perform ATS analysis
                    analysis = ats_analyzer.analyze_resume(resume_text, job_desc_text)

                    # Display ATS Score
                    st.subheader("ATS Score")
                    score = analysis['ats_score']

                    # Color code the score
                    if score >= 80:
                        score_color = "green"
                        score_message = "Excellent! Your resume is well-optimized for ATS."
                    elif score >= 60:
                        score_color = "orange"
                        score_message = "Good, but there's room for improvement."
                    else:
                        score_color = "red"
                        score_message = "Needs improvement to pass ATS screening."

                    st.markdown(f"## :{score_color}[{score}/100]")
                    st.info(score_message)

                    # Score breakdown
                    st.subheader("Score Breakdown")
                    breakdown = analysis['score_breakdown']

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Formatting", f"{breakdown['formatting']}/20")
                        st.metric("Keywords", f"{breakdown['keywords']}/25")

                    with col2:
                        st.metric("Action Verbs", f"{breakdown['action_verbs']}/15")
                        st.metric("Metrics", f"{breakdown['quantifiable_results']}/20")

                    with col3:
                        st.metric("Length", f"{breakdown['length']}/10")
                        if job_desc_file:
                            st.metric("Job Match", f"{breakdown['job_match']}/20")

                    # Suggestions
                    st.subheader("💡 Improvement Suggestions")
                    for idx, suggestion in enumerate(analysis['suggestions'], 1):
                        st.write(f"{idx}. {suggestion}")

                    # Found Skills
                    st.subheader("✅ Skills Found in Your Resume")
                    skills = analysis['found_skills']

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Technical Skills:**")
                        if skills['technical_skills']:
                            for skill in skills['technical_skills']:
                                st.write(f"- {skill}")
                        else:
                            st.write("No technical skills identified")

                    with col2:
                        st.write("**Soft Skills:**")
                        if skills['soft_skills']:
                            for skill in skills['soft_skills']:
                                st.write(f"- {skill}")
                        else:
                            st.write("No soft skills identified")

                    # Missing Keywords
                    if job_desc_file and analysis['missing_keywords']:
                        st.subheader("🔍 Missing Keywords from Job Description")
                        st.write("Consider adding these keywords to your resume:")
                        cols = st.columns(5)
                        for idx, keyword in enumerate(analysis['missing_keywords']):
                            cols[idx % 5].write(f"• {keyword}")

                except Exception as e:
                    st.error(f"Error analyzing resume: {str(e)}")
        else:
            st.warning("Please upload a resume to analyze.")

with tab2:
    st.header("AI-Powered Resume Optimization")
    st.markdown("Get personalized suggestions to improve your resume for a specific job")

    col1, col2 = st.columns(2)

    with col1:
        resume_file_opt = st.file_uploader(
            "Upload Resume",
            type=['txt', 'pdf', 'docx'],
            key="opt_resume"
        )

    with col2:
        job_desc_file_opt = st.file_uploader(
            "Upload Job Description",
            type=['txt', 'pdf', 'docx'],
            key="opt_job_desc"
        )

    if st.button("Optimize Resume", type="primary"):
        if resume_file_opt and job_desc_file_opt:
            # Check rate limit before making expensive API calls
            if not check_rate_limit(max_requests=20, window_seconds=60):
                st.stop()

            with st.spinner("Generating optimization suggestions..."):
                try:
                    resume_text = extract_text_from_upload(resume_file_opt)
                    job_desc_text = extract_text_from_upload(job_desc_file_opt)

                    # Get grammar correction
                    st.subheader("1️⃣ Grammar Check")
                    with st.spinner("Checking grammar..."):
                        corrected_resume = llm_service.correct_grammar(resume_text)
                        st.success("Grammar check complete!")

                    # Get optimization suggestions
                    st.subheader("2️⃣ Optimization Suggestions")
                    with st.spinner("Analyzing job match and generating suggestions..."):
                        suggestions = llm_service.optimize_resume(corrected_resume, job_desc_text)
                        st.write(suggestions)

                    # Display corrected resume
                    st.subheader("3️⃣ Grammar-Corrected Resume")
                    st.text_area(
                        "Corrected Resume",
                        value=corrected_resume,
                        height=300,
                        key="corrected_resume_display"
                    )

                    st.download_button(
                        label="📥 Download Corrected Resume",
                        data=corrected_resume,
                        file_name="corrected_resume.txt",
                        mime="text/plain"
                    )

                except Exception as e:
                    st.error(f"Error optimizing resume: {str(e)}")
        else:
            st.warning("Please upload both resume and job description.")

with tab3:
    st.header("Save Resume Version")
    st.markdown("Save different versions of your resume for different job applications")

    version_name = st.text_input("Version Name (e.g., 'Software Engineer - Google')")
    resume_content = st.text_area("Resume Content", height=300)

    if st.button("💾 Save Resume", type="primary"):
        if version_name and resume_content:
            try:
                profile = get_current_profile()

                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO resumes (profile_id, version_name, content)
                        VALUES (?, ?, ?)
                    ''', (profile['id'], version_name, resume_content))
                    conn.commit()

                st.success(f"✅ Resume version '{version_name}' saved successfully!")

            except Exception as e:
                st.error(f"Error saving resume: {str(e)}")
        else:
            st.warning("Please provide both version name and resume content.")

    # Display saved resumes
    st.subheader("📚 Saved Resume Versions")

    try:
        profile = get_current_profile()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, version_name, created_at, ats_score
                FROM resumes
                WHERE profile_id = ?
                ORDER BY created_at DESC
            ''', (profile['id'],))
            resumes = cursor.fetchall()

        if resumes:
            for resume in resumes:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{resume['version_name']}**")
                with col2:
                    st.write(f"Created: {resume['created_at'][:10]}")
                with col3:
                    if st.button("View", key=f"view_{resume['id']}"):
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT content FROM resumes WHERE id = ?', (resume['id'],))
                            content = cursor.fetchone()['content']
                            st.text_area("Resume Content", value=content, height=200, key=f"content_{resume['id']}")
        else:
            st.info("No saved resumes yet. Save your first resume above!")

    except Exception as e:
        st.error(f"Error loading resumes: {str(e)}")

# Sidebar with tips
with st.sidebar:
    st.header("💡 Resume Tips")
    st.markdown("""
    **ATS Best Practices:**
    - Use standard section headers
    - Include relevant keywords
    - Use strong action verbs
    - Add quantifiable results
    - Keep formatting simple
    - Avoid images and graphics
    - Use common fonts

    **Optimal Length:**
    - Entry-level: 1 page
    - Mid-level: 1-2 pages
    - Senior: 2 pages max
    """)
