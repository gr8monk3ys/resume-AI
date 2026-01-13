import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.file_parser import extract_text_from_upload
from services.resume_analyzer import JobMatchScorer
from models.auth_database import init_auth_database
from utils.auth import init_session_state, is_authenticated, show_auth_sidebar
from config import MAX_RESUME_LENGTH, MAX_JOB_DESCRIPTION_LENGTH

st.set_page_config(page_title="Job Match Scorer", page_icon="🎯", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("Please log in to access this page")
    st.info("Use the Login page from the sidebar")
    st.stop()

st.title("🎯 Job Match Scorer")
st.markdown("Get a comprehensive match score before you apply - know your chances!")

# Initialize scorer
scorer = JobMatchScorer()

# Input section
st.header("Upload Your Documents")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Your Resume")
    resume_file = st.file_uploader(
        "Upload Resume",
        type=['txt', 'pdf', 'docx'],
        key="match_resume"
    )
    resume_text_input = st.text_area(
        "Or paste resume text",
        height=200,
        key="match_resume_text",
        placeholder="Paste your resume content here..."
    )

with col2:
    st.subheader("Job Description")
    job_file = st.file_uploader(
        "Upload Job Description",
        type=['txt', 'pdf', 'docx'],
        key="match_job"
    )
    job_text_input = st.text_area(
        "Or paste job description",
        height=200,
        key="match_job_text",
        placeholder="Paste the job description here..."
    )

if st.button("Calculate Match Score", type="primary", use_container_width=True):
    # Get resume text
    resume_text = ""
    if resume_file:
        resume_text = extract_text_from_upload(resume_file)
    elif resume_text_input:
        resume_text = resume_text_input

    # Get job description
    job_text = ""
    if job_file:
        job_text = extract_text_from_upload(job_file)
    elif job_text_input:
        job_text = job_text_input

    if not resume_text or not job_text:
        st.warning("Please provide both resume and job description")
        st.stop()

    # Validate lengths
    if len(resume_text) > MAX_RESUME_LENGTH:
        st.error(f"Resume is too large ({len(resume_text):,} characters). Maximum: {MAX_RESUME_LENGTH:,}")
        st.stop()
    if len(job_text) > MAX_JOB_DESCRIPTION_LENGTH:
        st.error(f"Job description is too large ({len(job_text):,} characters). Maximum: {MAX_JOB_DESCRIPTION_LENGTH:,}")
        st.stop()

    with st.spinner("Analyzing your match..."):
        try:
            result = scorer.calculate_match_score(resume_text, job_text)

            # Store for display
            st.session_state['match_result'] = result

        except Exception as e:
            st.error(f"Error calculating match: {str(e)}")
            st.stop()

# Display results
if 'match_result' in st.session_state:
    result = st.session_state['match_result']

    st.divider()

    # Overall Score Display
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        score = result['overall_score']
        color = result['match_color']

        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
            <h1 style="font-size: 72px; margin: 0; color: {'#28a745' if color == 'green' else '#ffc107' if color == 'orange' else '#dc3545'};">
                {score}%
            </h1>
            <h2 style="margin: 10px 0;">{result['match_level']}</h2>
        </div>
        """, unsafe_allow_html=True)

    # Apply Recommendation
    rec = result['apply_recommendation']
    if rec['should_apply'] == True:
        st.success(f"**{rec['confidence']} Confidence**: {rec['message']}")
    elif rec['should_apply'] == 'Maybe':
        st.warning(f"**{rec['confidence']} Confidence**: {rec['message']}")
    else:
        st.error(f"**{rec['confidence']} Confidence**: {rec['message']}")

    st.divider()

    # Score Breakdown
    st.header("Score Breakdown")

    breakdown = result['breakdown']
    weights = result['weights']

    # Create metrics row
    cols = st.columns(5)

    categories = [
        ('skills', 'Technical Skills', '💻'),
        ('experience', 'Experience', '📈'),
        ('education', 'Education', '🎓'),
        ('keywords', 'Keywords', '🔑'),
        ('soft_skills', 'Soft Skills', '🤝')
    ]

    for col, (key, label, icon) in zip(cols, categories):
        with col:
            cat_score = breakdown[key]['score']
            weight_pct = int(weights[key] * 100)

            # Color based on score
            if cat_score >= 70:
                delta_color = "normal"
            elif cat_score >= 50:
                delta_color = "off"
            else:
                delta_color = "inverse"

            st.metric(
                f"{icon} {label}",
                f"{cat_score:.0f}%",
                f"Weight: {weight_pct}%",
                delta_color=delta_color
            )

    st.divider()

    # Detailed Analysis
    st.header("Detailed Analysis")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💻 Skills", "📈 Experience", "🎓 Education", "🔑 Keywords", "🤝 Soft Skills"
    ])

    with tab1:
        skills = breakdown['skills']
        st.subheader(f"Technical Skills Match: {skills['score']:.0f}%")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Matched Skills:**")
            if skills['matched']:
                for skill in skills['matched']:
                    st.success(f"✓ {skill}")
            else:
                st.info("No specific technical skills matched")

        with col2:
            st.write("**Missing Skills:**")
            if skills['missing']:
                for skill in skills['missing']:
                    st.error(f"✗ {skill}")
            else:
                st.success("All required skills present!")

        st.caption(f"Total skills required in job: {skills['total_required']}")

    with tab2:
        exp = breakdown['experience']
        st.subheader(f"Experience Match: {exp['score']:.0f}%")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Your Profile:**")
            st.write(f"- Experience Level: **{exp['resume_level'].title()}**")
            st.write(f"- Years Found: **{exp['resume_years']}** years")

        with col2:
            st.write("**Job Requirements:**")
            st.write(f"- Required Level: **{exp['job_level'].title()}**")
            st.write(f"- Required Years: **{exp['required_years']}+** years")

        if exp['resume_level'] == exp['job_level']:
            st.success("Experience level matches job requirements!")
        elif exp['score'] >= 70:
            st.info("Experience level is close to requirements")
        else:
            st.warning("Experience level may not fully match requirements")

    with tab3:
        edu = breakdown['education']
        st.subheader(f"Education Match: {edu['score']:.0f}%")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Your Education:**")
            st.write(f"Highest level detected: **{edu['resume_education'].title()}**")

        with col2:
            st.write("**Job Requirement:**")
            st.write(f"Required level: **{edu['required_education'].title()}**")

        if edu['meets_requirement']:
            st.success("Education meets or exceeds requirements!")
        elif edu['score'] >= 75:
            st.info("Education is close to requirements - may be acceptable")
        else:
            st.warning("Education may not meet stated requirements")

    with tab4:
        kw = breakdown['keywords']
        st.subheader(f"Keyword Match: {kw['score']:.0f}%")

        st.metric("Keyword Overlap", f"{kw['overlap_percentage']}%")
        st.write(f"Matched **{kw['matched_count']}** out of **{kw['total_job_keywords']}** job keywords")

        if kw['overlap_percentage'] >= 70:
            st.success("Strong keyword alignment with job description!")
        elif kw['overlap_percentage'] >= 50:
            st.info("Moderate keyword match - consider adding more job-specific terms")
        else:
            st.warning("Low keyword overlap - review job description and update resume")

    with tab5:
        soft = breakdown['soft_skills']
        st.subheader(f"Soft Skills Match: {soft['score']:.0f}%")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Matched Soft Skills:**")
            if soft['matched']:
                for skill in soft['matched']:
                    st.success(f"✓ {skill}")
            else:
                st.info("No specific soft skills matched")

        with col2:
            st.write("**Missing Soft Skills:**")
            if soft['missing']:
                for skill in soft['missing']:
                    st.warning(f"○ {skill}")
            else:
                st.success("All soft skills present!")

    st.divider()

    # Recommendations
    st.header("Recommendations")

    for i, rec in enumerate(result['recommendations'], 1):
        st.write(f"{i}. {rec}")

    # Action buttons
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔍 Run Keyword Gap Analysis", use_container_width=True):
            st.switch_page("pages/10_Keyword_Gap_Analysis.py")

    with col2:
        if st.button("✨ Tailor Resume", use_container_width=True):
            st.switch_page("pages/9_AI_Assistant.py")

    with col3:
        if st.button("📝 Generate Cover Letter", use_container_width=True):
            st.switch_page("pages/3_Cover_Letter.py")

# Sidebar
with st.sidebar:
    st.header("How Scoring Works")
    st.markdown("""
    **Score Components:**
    - **Technical Skills (30%)**: Match required technologies
    - **Experience (25%)**: Level and years alignment
    - **Keywords (20%)**: Language overlap with job
    - **Education (15%)**: Degree requirements
    - **Soft Skills (10%)**: Leadership, communication, etc.

    **Score Interpretation:**
    - **80%+**: Excellent - strong candidate
    - **65-79%**: Good - solid chance
    - **50-64%**: Moderate - highlight strengths
    - **35-49%**: Partial - stretch role
    - **<35%**: Low - consider other roles

    **Tips:**
    - Score 50%+ for most roles
    - Senior roles may accept 60%+
    - Entry roles more flexible
    """)
