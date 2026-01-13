import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.file_parser import extract_text_from_upload
from services.llm_service import get_llm_service
from models.database import get_db_connection
from models.auth_database import init_auth_database
from utils.rate_limiter import check_rate_limit
from utils.auth import init_session_state, is_authenticated, get_current_profile, show_auth_sidebar
from config import MAX_RESUME_LENGTH, MAX_JOB_DESCRIPTION_LENGTH

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("🤖 AI Application Assistant")
st.markdown("Get AI-powered help with resume tailoring and application questions")

# Initialize services
try:
    llm_service = get_llm_service()
except ValueError as e:
    st.error(f"⚠️ {str(e)}")
    st.stop()

profile = get_current_profile()

# Create tabs
tab1, tab2, tab3 = st.tabs(["✨ Resume Tailor", "❓ Question Answerer", "🎤 Interview Prep"])

with tab1:
    st.header("✨ AI Resume Tailor")
    st.markdown("""
    Generate a tailored version of your resume for a specific job.
    The AI will rewrite your resume to better match the job description while keeping all your information accurate.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Your Resume")

        # Option to load saved resume
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, version_name, content FROM resumes
                WHERE profile_id = ?
                ORDER BY created_at DESC
            ''', (profile['id'],))
            saved_resumes = cursor.fetchall()

        resume_source = st.radio(
            "Resume Source",
            ["Upload File", "Paste Text", "Use Saved Resume"],
            horizontal=True
        )

        resume_text = ""
        if resume_source == "Upload File":
            resume_file = st.file_uploader("Upload Resume", type=['txt', 'pdf', 'docx'], key="tailor_resume")
            if resume_file:
                resume_text = extract_text_from_upload(resume_file)
        elif resume_source == "Paste Text":
            resume_text = st.text_area("Paste your resume", height=300, key="tailor_resume_text")
        else:
            if saved_resumes:
                selected_resume = st.selectbox(
                    "Select saved resume",
                    options=saved_resumes,
                    format_func=lambda x: x['version_name']
                )
                if selected_resume:
                    resume_text = selected_resume['content']
                    st.text_area("Resume content", value=resume_text[:500] + "...", height=150, disabled=True)
            else:
                st.info("No saved resumes found. Upload or paste your resume.")

    with col2:
        st.subheader("Target Job")
        company_name = st.text_input("Company Name*", placeholder="e.g., Google")
        position = st.text_input("Position Title*", placeholder="e.g., Software Engineer")

        job_desc_source = st.radio(
            "Job Description Source",
            ["Paste Text", "Upload File"],
            horizontal=True
        )

        job_description = ""
        if job_desc_source == "Upload File":
            job_file = st.file_uploader("Upload Job Description", type=['txt', 'pdf', 'docx'], key="tailor_job")
            if job_file:
                job_description = extract_text_from_upload(job_file)
        else:
            job_description = st.text_area("Paste job description", height=200, key="tailor_job_text")

    # Generate button
    if st.button("✨ Generate Tailored Resume", type="primary", use_container_width=True):
        if not resume_text:
            st.error("Please provide your resume")
        elif not job_description:
            st.error("Please provide the job description")
        elif not company_name or not position:
            st.error("Please enter company name and position")
        elif len(resume_text) > MAX_RESUME_LENGTH:
            st.error(f"Resume is too large ({len(resume_text):,} chars). Max: {MAX_RESUME_LENGTH:,}")
        elif len(job_description) > MAX_JOB_DESCRIPTION_LENGTH:
            st.error(f"Job description is too large ({len(job_description):,} chars). Max: {MAX_JOB_DESCRIPTION_LENGTH:,}")
        else:
            if not check_rate_limit(max_requests=10, window_seconds=60):
                st.stop()

            with st.spinner("🤖 Tailoring your resume... This may take a minute."):
                try:
                    tailored_resume = llm_service.tailor_resume(
                        resume=resume_text,
                        job_description=job_description,
                        company_name=company_name,
                        position=position
                    )

                    st.success("✅ Tailored resume generated!")

                    # Display result
                    st.subheader("📄 Your Tailored Resume")
                    st.text_area("Tailored Resume", value=tailored_resume, height=400)

                    # Action buttons
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.download_button(
                            "📥 Download",
                            data=tailored_resume,
                            file_name=f"resume_{company_name.replace(' ', '_')}_{position.replace(' ', '_')}.txt",
                            mime="text/plain"
                        )

                    with col2:
                        # Save as new version
                        if st.button("💾 Save as New Version"):
                            version_name = f"{company_name} - {position}"
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    INSERT INTO resumes (profile_id, version_name, content)
                                    VALUES (?, ?, ?)
                                ''', (profile['id'], version_name, tailored_resume))
                                conn.commit()
                            st.success(f"Saved as '{version_name}'!")

                    with col3:
                        st.button("📋 Copy to Clipboard", on_click=lambda: st.write("Use Ctrl+A, Ctrl+C in the text area above"))

                except Exception as e:
                    st.error(f"Error generating tailored resume: {str(e)}")

with tab2:
    st.header("❓ Application Question Answerer")
    st.markdown("""
    Get AI-generated answers for common job application questions.
    The AI uses your resume and the job description to create personalized, relevant answers.
    """)

    # Common questions
    common_questions = [
        "Custom question...",
        "Why do you want to work at [Company]?",
        "Why are you interested in this position?",
        "What makes you a good fit for this role?",
        "Describe a challenging project you worked on.",
        "Tell us about a time you showed leadership.",
        "What is your greatest professional achievement?",
        "Where do you see yourself in 5 years?",
        "What are your salary expectations?",
        "Why are you leaving your current job?",
        "What is your biggest weakness?",
        "What is your greatest strength?",
        "Describe a time you failed and what you learned.",
        "How do you handle tight deadlines?",
        "Tell us about a time you resolved a conflict."
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Context")

        # Resume input
        qa_resume_source = st.radio(
            "Your Resume",
            ["Use Saved Resume", "Paste Text"],
            horizontal=True,
            key="qa_resume_source"
        )

        qa_resume = ""
        if qa_resume_source == "Use Saved Resume" and saved_resumes:
            qa_selected = st.selectbox(
                "Select resume",
                options=saved_resumes,
                format_func=lambda x: x['version_name'],
                key="qa_resume_select"
            )
            if qa_selected:
                qa_resume = qa_selected['content']
        else:
            qa_resume = st.text_area("Your resume", height=150, key="qa_resume_text")

        # Job description
        qa_job_desc = st.text_area("Job Description", height=150, key="qa_job_desc",
                                   placeholder="Paste the job description for context...")

    with col2:
        st.subheader("Question")

        selected_question = st.selectbox("Common Questions", common_questions)

        if selected_question == "Custom question...":
            question = st.text_area("Enter your question", height=100)
        else:
            question = st.text_input("Question", value=selected_question)

        question_type = st.selectbox(
            "Question Type",
            ["general", "behavioral", "motivation", "salary", "weakness", "strength"],
            help="This helps the AI format the answer appropriately"
        )

    if st.button("💡 Generate Answer", type="primary", use_container_width=True):
        if not question:
            st.error("Please enter a question")
        elif not qa_resume:
            st.error("Please provide your resume for context")
        else:
            if not check_rate_limit(max_requests=15, window_seconds=60):
                st.stop()

            with st.spinner("🤖 Generating answer..."):
                try:
                    answer = llm_service.answer_application_question(
                        question=question,
                        resume=qa_resume,
                        job_description=qa_job_desc or "General position",
                        question_type=question_type
                    )

                    st.success("✅ Answer generated!")

                    st.subheader("📝 Suggested Answer")
                    st.text_area("Answer", value=answer, height=250)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "📥 Download Answer",
                            data=f"Question: {question}\n\nAnswer:\n{answer}",
                            file_name="application_answer.txt",
                            mime="text/plain"
                        )
                    with col2:
                        word_count = len(answer.split())
                        st.metric("Word Count", word_count)

                except Exception as e:
                    st.error(f"Error generating answer: {str(e)}")

with tab3:
    st.header("🎤 Interview Prep")
    st.markdown("""
    Practice your interview answers with AI-generated sample responses using the STAR method.
    """)

    # Common interview questions
    interview_questions = [
        "Tell me about yourself.",
        "Why do you want this job?",
        "What are your strengths and weaknesses?",
        "Tell me about a time you faced a challenge at work.",
        "Describe a situation where you showed leadership.",
        "How do you handle pressure and tight deadlines?",
        "Tell me about a time you made a mistake.",
        "Where do you see yourself in 5 years?",
        "Why should we hire you?",
        "Do you have any questions for us?",
        "Tell me about a time you disagreed with a coworker.",
        "Describe your ideal work environment.",
        "How do you prioritize your work?",
        "Tell me about a time you went above and beyond."
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Your Background")

        int_resume_source = st.radio(
            "Resume",
            ["Use Saved", "Paste"],
            horizontal=True,
            key="int_resume_source"
        )

        int_resume = ""
        if int_resume_source == "Use Saved" and saved_resumes:
            int_selected = st.selectbox(
                "Select",
                options=saved_resumes,
                format_func=lambda x: x['version_name'],
                key="int_resume_select"
            )
            if int_selected:
                int_resume = int_selected['content']
        else:
            int_resume = st.text_area("Resume", height=150, key="int_resume_text")

        int_job_desc = st.text_area("Job Description", height=150, key="int_job_desc")

    with col2:
        st.subheader("Practice Question")

        int_question = st.selectbox("Select Question", interview_questions)
        custom_question = st.text_input("Or enter custom question")

        if custom_question:
            int_question = custom_question

    if st.button("🎯 Generate Sample Answer", type="primary", use_container_width=True):
        if not int_resume:
            st.error("Please provide your resume")
        elif not int_question:
            st.error("Please select or enter a question")
        else:
            if not check_rate_limit(max_requests=15, window_seconds=60):
                st.stop()

            with st.spinner("🤖 Generating STAR-format answer..."):
                try:
                    answer = llm_service.generate_interview_answer(
                        question=int_question,
                        resume=int_resume,
                        job_description=int_job_desc or "General position"
                    )

                    st.success("✅ Sample answer generated!")

                    st.subheader(f"💬 Question: {int_question}")
                    st.text_area("Sample Answer (STAR Method)", value=answer, height=300)

                    st.info("""
                    **STAR Method Reminder:**
                    - **S**ituation: Set the scene
                    - **T**ask: Describe your responsibility
                    - **A**ction: Explain what you did
                    - **R**esult: Share the outcome
                    """)

                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Sidebar
with st.sidebar:
    st.header("💡 Tips")
    st.markdown("""
    **Resume Tailor:**
    - Use your base resume as a starting point
    - The AI preserves your facts while optimizing for the job
    - Review and personalize the output

    **Question Answerer:**
    - Select the right question type for better formatting
    - Provide job description for more relevant answers
    - Use as a starting point, then personalize

    **Interview Prep:**
    - Practice answering out loud
    - Time yourself (aim for 1-2 minutes per answer)
    - Prepare 2-3 stories for behavioral questions
    """)
