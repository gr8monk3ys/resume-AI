import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.file_parser import extract_text_from_upload
from services.resume_analyzer import ATSAnalyzer
from services.llm_service import get_llm_service
from models.auth_database import init_auth_database
from utils.rate_limiter import check_rate_limit
from utils.auth import init_session_state, is_authenticated, show_auth_sidebar
from config import MAX_RESUME_LENGTH, MAX_JOB_DESCRIPTION_LENGTH

st.set_page_config(page_title="Keyword Gap Analysis", page_icon="🔍", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("Please log in to access this page")
    st.info("Use the Login page from the sidebar")
    st.stop()

st.title("🔍 Keyword Gap Analysis")
st.markdown("Compare your resume against job descriptions to identify missing keywords and improve your match rate")

# Initialize analyzer
ats_analyzer = ATSAnalyzer()

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Gap Analysis", "💡 Recommendations", "🤖 AI Suggestions"])

with tab1:
    st.header("Resume vs Job Description Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Your Resume")
        resume_file = st.file_uploader(
            "Upload Resume",
            type=['txt', 'pdf', 'docx'],
            key="gap_resume"
        )
        resume_text_input = st.text_area(
            "Or paste resume text",
            height=200,
            key="gap_resume_text",
            placeholder="Paste your resume content here..."
        )

    with col2:
        st.subheader("Job Description")
        job_file = st.file_uploader(
            "Upload Job Description",
            type=['txt', 'pdf', 'docx'],
            key="gap_job"
        )
        job_text_input = st.text_area(
            "Or paste job description",
            height=200,
            key="gap_job_text",
            placeholder="Paste the job description here..."
        )

    if st.button("Analyze Keyword Gaps", type="primary", use_container_width=True):
        # Get resume text from file or text area
        resume_text = ""
        if resume_file:
            resume_text = extract_text_from_upload(resume_file)
        elif resume_text_input:
            resume_text = resume_text_input

        # Get job description text from file or text area
        job_text = ""
        if job_file:
            job_text = extract_text_from_upload(job_file)
        elif job_text_input:
            job_text = job_text_input

        if not resume_text or not job_text:
            st.warning("Please provide both resume and job description")
            st.stop()

        # Validate input lengths
        if len(resume_text) > MAX_RESUME_LENGTH:
            st.error(f"Resume is too large ({len(resume_text):,} characters). Maximum: {MAX_RESUME_LENGTH:,}")
            st.stop()
        if len(job_text) > MAX_JOB_DESCRIPTION_LENGTH:
            st.error(f"Job description is too large ({len(job_text):,} characters). Maximum: {MAX_JOB_DESCRIPTION_LENGTH:,}")
            st.stop()

        with st.spinner("Analyzing keyword gaps..."):
            try:
                # Perform gap analysis
                analysis = ats_analyzer.analyze_keyword_gaps(resume_text, job_text)

                # Store in session state for recommendations tab and AI suggestions
                st.session_state['gap_analysis'] = analysis
                st.session_state['resume_text'] = resume_text
                st.session_state['job_text'] = job_text

                # Display Match Score
                st.divider()
                match_pct = analysis['match_percentage']

                # Color-coded match score
                if match_pct >= 70:
                    color = "green"
                    message = "Strong match! Your resume aligns well with this job."
                elif match_pct >= 50:
                    color = "orange"
                    message = "Moderate match. Consider adding some missing keywords."
                else:
                    color = "red"
                    message = "Low match. Your resume may need significant updates for this role."

                # Summary metrics
                st.subheader("Match Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Match Rate", f"{match_pct}%")
                with col2:
                    st.metric("Keywords Matched", analysis['matched_keywords'])
                with col3:
                    st.metric("Keywords Missing", analysis['missing_count'])
                with col4:
                    st.metric("Total Job Keywords", analysis['total_job_keywords'])

                st.markdown(f"### :{color}[{message}]")

                st.divider()

                # Found Keywords Section
                st.subheader("Keywords Found in Your Resume")
                found = analysis['found_keywords']

                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Technical Skills Matched:**")
                    if found['technical']:
                        for skill in found['technical']:
                            st.success(f"✓ {skill}")
                    else:
                        st.info("No technical skills matched")

                    st.write("**Action Verbs Found:**")
                    if found['action_verbs']:
                        cols = st.columns(3)
                        for idx, verb in enumerate(found['action_verbs'][:9]):
                            cols[idx % 3].write(f"• {verb}")
                    else:
                        st.info("No action verbs identified")

                with col2:
                    st.write("**Soft Skills Matched:**")
                    if found['soft_skills']:
                        for skill in found['soft_skills']:
                            st.success(f"✓ {skill}")
                    else:
                        st.info("No soft skills matched")

                    st.write("**Other Matching Keywords:**")
                    if found['other_matches']:
                        cols = st.columns(4)
                        for idx, kw in enumerate(found['other_matches'][:12]):
                            cols[idx % 4].write(f"• {kw}")

                st.divider()

                # Missing Keywords Section (THE GAPS)
                st.subheader("Missing Keywords (Gaps to Close)")
                missing = analysis['missing_keywords']

                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Missing Technical Skills:**")
                    if missing['technical']:
                        for skill in missing['technical']:
                            st.error(f"✗ {skill}")
                    else:
                        st.success("All required technical skills present!")

                    st.write("**Missing Action Verbs:**")
                    if missing['action_verbs']:
                        cols = st.columns(3)
                        for idx, verb in enumerate(missing['action_verbs'][:6]):
                            cols[idx % 3].write(f"• {verb}")
                    else:
                        st.success("Good use of action verbs!")

                with col2:
                    st.write("**Missing Soft Skills:**")
                    if missing['soft_skills']:
                        for skill in missing['soft_skills']:
                            st.error(f"✗ {skill}")
                    else:
                        st.success("All soft skills covered!")

                    st.write("**Important Job-Specific Terms Missing:**")
                    if missing['important_job_terms']:
                        cols = st.columns(3)
                        for idx, term in enumerate(missing['important_job_terms'][:9]):
                            cols[idx % 3].write(f"• {term}")
                    else:
                        st.success("Job-specific terms well covered!")

                # Unique Strengths
                if analysis['unique_strengths']:
                    st.divider()
                    st.subheader("Your Unique Strengths")
                    st.info("These keywords are in your resume but not in the job description. They could be differentiators!")
                    cols = st.columns(5)
                    for idx, strength in enumerate(analysis['unique_strengths']):
                        cols[idx % 5].write(f"• {strength}")

            except Exception as e:
                st.error(f"Error analyzing keywords: {str(e)}")

with tab2:
    st.header("Keyword Placement Recommendations")

    if 'gap_analysis' not in st.session_state:
        st.info("Run a Gap Analysis first to see personalized recommendations")
        st.stop()

    analysis = st.session_state['gap_analysis']
    suggestions = analysis['placement_suggestions']

    if suggestions:
        for suggestion in suggestions:
            with st.expander(f"**{suggestion['category']}** - {len(suggestion['keywords'])} keywords to add", expanded=True):
                st.write("**Keywords to Add:**")
                cols = st.columns(5)
                for idx, kw in enumerate(suggestion['keywords']):
                    cols[idx % 5].markdown(f"`{kw}`")

                st.write("")
                st.write("**How to Add Them:**")
                st.info(suggestion['suggestion'])

        st.divider()
        st.subheader("General Tips for Closing Keyword Gaps")
        st.markdown("""
        **1. Skills Section**
        - Add missing technical skills you genuinely possess
        - Include variations (e.g., "React" and "React.js")

        **2. Experience Section**
        - Weave keywords naturally into bullet points
        - Don't keyword-stuff - it's obvious to recruiters
        - Use the job's exact phrasing when describing similar work

        **3. Summary/Objective**
        - Mirror key requirements from the job posting
        - Include 2-3 critical missing terms here

        **4. Projects Section**
        - Highlight projects using relevant technologies
        - Describe outcomes using job-relevant terminology
        """)
    else:
        st.success("Your resume already matches most keywords from the job description!")
        st.balloons()

with tab3:
    st.header("AI-Powered Keyword Suggestions")
    st.markdown("Get personalized suggestions for naturally incorporating missing keywords into your resume")

    if 'gap_analysis' not in st.session_state:
        st.info("Run a Gap Analysis first to get AI-powered suggestions")
        st.stop()

    if 'resume_text' not in st.session_state or 'job_text' not in st.session_state:
        st.warning("Please run the Gap Analysis again to enable AI suggestions")
        st.stop()

    analysis = st.session_state['gap_analysis']
    missing = analysis['missing_keywords']

    # Collect all missing keywords
    all_missing = (
        missing.get('technical', []) +
        missing.get('soft_skills', []) +
        missing.get('important_job_terms', [])
    )

    if not all_missing:
        st.success("No missing keywords to add - your resume is well-matched!")
        st.stop()

    st.write(f"**{len(all_missing)} keywords identified for potential addition:**")
    cols = st.columns(6)
    for idx, kw in enumerate(all_missing[:18]):
        cols[idx % 6].markdown(f"`{kw}`")

    st.divider()

    if st.button("Generate AI Suggestions", type="primary", use_container_width=True):
        # Check rate limit
        if not check_rate_limit(max_requests=10, window_seconds=60):
            st.stop()

        with st.spinner("Generating personalized suggestions..."):
            try:
                llm_service = get_llm_service()
                suggestions = llm_service.suggest_keyword_additions(
                    resume=st.session_state['resume_text'],
                    job_description=st.session_state['job_text'],
                    missing_keywords=all_missing
                )

                st.subheader("Personalized Suggestions")
                st.markdown(suggestions)

                st.divider()
                st.info("These are AI-generated suggestions. Review them carefully and only add keywords that accurately represent your skills and experience.")

            except Exception as e:
                st.error(f"Error generating suggestions: {str(e)}")
                st.info("Make sure your OPENAI_API_KEY is configured in your .env file")

# Sidebar tips
with st.sidebar:
    st.header("About Keyword Analysis")
    st.markdown("""
    **Why Keywords Matter:**
    - ATS systems scan for keywords
    - Recruiters spend ~7 seconds on initial review
    - Keywords show relevant experience

    **Keyword Types:**
    - **Technical**: Programming languages, tools, frameworks
    - **Soft Skills**: Communication, leadership, teamwork
    - **Action Verbs**: Achieved, developed, implemented
    - **Industry Terms**: Domain-specific vocabulary

    **Best Practices:**
    - Match 60-80% of job keywords
    - Use exact phrases from posting
    - Be honest - only add skills you have
    - Include keyword variations
    """)
