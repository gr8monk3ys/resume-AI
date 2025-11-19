import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.file_parser import extract_text_from_upload
from services.llm_service import get_llm_service
from models.database import get_db_connection
from models.auth_database import init_auth_database
from utils.auth import init_session_state, is_authenticated, get_current_profile, show_auth_sidebar

st.set_page_config(page_title="Cover Letter Generator", page_icon="📝", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("📝 Cover Letter Generator")
st.markdown("Generate personalized, professional cover letters in seconds")

# Initialize services
llm_service = get_llm_service()
profile = get_current_profile()

# Tabs
tab1, tab2, tab3 = st.tabs(["✨ Generate Letter", "📧 Email Templates", "💾 Saved Letters"])

with tab1:
    st.header("Generate Cover Letter")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Your Information")
        user_name = st.text_input("Your Name", value=profile.get('name', ''))
        resume_file = st.file_uploader(
            "Upload Resume (Optional)",
            type=['txt', 'pdf', 'docx'],
            help="Upload your resume for better personalization"
        )

        resume_text_input = st.text_area(
            "Or paste your resume/key achievements",
            height=200,
            placeholder="Key achievements and skills..."
        )

    with col2:
        st.subheader("Job Information")
        company_name = st.text_input("Company Name*", placeholder="e.g., Google")
        position = st.text_input("Position Title*", placeholder="e.g., Software Engineer")

        job_desc_file = st.file_uploader(
            "Upload Job Description",
            type=['txt', 'pdf', 'docx']
        )

        job_desc_text = st.text_area(
            "Or paste job description",
            height=200,
            placeholder="Paste the job description here..."
        )

    if st.button("✨ Generate Cover Letter", type="primary"):
        if company_name and position:
            with st.spinner("Generating your personalized cover letter..."):
                try:
                    # Get resume text
                    if resume_file:
                        resume_text = extract_text_from_upload(resume_file)
                    elif resume_text_input:
                        resume_text = resume_text_input
                    else:
                        resume_text = "Professional with relevant experience"

                    # Get job description
                    if job_desc_file:
                        job_description = extract_text_from_upload(job_desc_file)
                    elif job_desc_text:
                        job_description = job_desc_text
                    else:
                        job_description = f"Position at {company_name}"

                    # Generate cover letter
                    cover_letter = llm_service.generate_cover_letter(
                        resume=resume_text,
                        job_description=job_description,
                        company_name=company_name,
                        position=position,
                        user_name=user_name if user_name else None
                    )

                    st.success("✅ Cover letter generated!")

                    # Display result
                    st.subheader("Your Cover Letter")
                    st.text_area(
                        "",
                        value=cover_letter,
                        height=400,
                        key="generated_letter"
                    )

                    # Action buttons
                    col1, col2 = st.columns(2)

                    with col1:
                        st.download_button(
                            label="📥 Download Cover Letter",
                            data=cover_letter,
                            file_name=f"cover_letter_{company_name.replace(' ', '_')}.txt",
                            mime="text/plain"
                        )

                    with col2:
                        if st.button("💾 Save to Database"):
                            # Get job application ID if exists
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    SELECT id FROM job_applications
                                    WHERE profile_id = ? AND company = ? AND position = ?
                                    ORDER BY created_at DESC LIMIT 1
                                ''', (profile['id'], company_name, position))
                                job_app = cursor.fetchone()

                                job_app_id = job_app['id'] if job_app else None

                                cursor.execute('''
                                    INSERT INTO cover_letters (profile_id, job_application_id, content)
                                    VALUES (?, ?, ?)
                                ''', (profile['id'], job_app_id, cover_letter))
                                conn.commit()

                            st.success("Cover letter saved!")

                except Exception as e:
                    st.error(f"Error generating cover letter: {str(e)}")
        else:
            st.warning("Please provide at least Company Name and Position.")

with tab2:
    st.header("Email Templates")
    st.markdown("Generate professional networking and follow-up emails")

    email_type = st.selectbox(
        "Email Type",
        ["Networking/Informational Interview", "Job Inquiry", "Follow-up After Application", "Thank You After Interview"]
    )

    col1, col2 = st.columns(2)

    with col1:
        recipient_name = st.text_input("Recipient Name", placeholder="e.g., John Smith")
        recipient_company = st.text_input("Company", placeholder="e.g., Google")

    with col2:
        your_background = st.text_area(
            "Brief Background (Optional)",
            height=100,
            placeholder="e.g., Software engineer with 5 years experience in Python..."
        )

    if st.button("Generate Email", type="primary"):
        if recipient_name and recipient_company:
            with st.spinner("Generating email..."):
                try:
                    # Map email type to purpose
                    purpose_map = {
                        "Networking/Informational Interview": "informational interview",
                        "Job Inquiry": "job inquiry",
                        "Follow-up After Application": "follow-up on application",
                        "Thank You After Interview": "thank you for interview"
                    }

                    purpose = purpose_map.get(email_type, "networking")

                    email = llm_service.generate_networking_email(
                        recipient_name=recipient_name,
                        company_name=recipient_company,
                        purpose=purpose,
                        user_background=your_background if your_background else None
                    )

                    st.success("✅ Email generated!")

                    st.subheader("Your Email")
                    st.text_area("", value=email, height=300, key="generated_email")

                    st.download_button(
                        label="📥 Download Email",
                        data=email,
                        file_name=f"email_{email_type.replace(' ', '_').lower()}.txt",
                        mime="text/plain"
                    )

                except Exception as e:
                    st.error(f"Error generating email: {str(e)}")
        else:
            st.warning("Please provide Recipient Name and Company.")

with tab3:
    st.header("Saved Cover Letters")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT cl.*, ja.company, ja.position
                FROM cover_letters cl
                LEFT JOIN job_applications ja ON cl.job_application_id = ja.id
                WHERE cl.profile_id = ?
                ORDER BY cl.created_at DESC
            ''', (profile['id'],))
            letters = cursor.fetchall()

        if letters:
            st.write(f"**{len(letters)} saved cover letter(s)**")

            for letter in letters:
                company = letter['company'] if letter['company'] else "Unknown Company"
                position = letter['position'] if letter['position'] else "Unknown Position"

                with st.expander(f"{company} - {position} (Created: {letter['created_at'][:10]})"):
                    st.text_area("", value=letter['content'], height=300, key=f"letter_{letter['id']}", disabled=True)

                    col1, col2, col3 = st.columns([1, 1, 4])

                    with col1:
                        st.download_button(
                            label="📥 Download",
                            data=letter['content'],
                            file_name=f"cover_letter_{company.replace(' ', '_')}.txt",
                            mime="text/plain",
                            key=f"download_{letter['id']}"
                        )

                    with col2:
                        # Delete with confirmation
                        delete_key = f"confirm_delete_letter_{letter['id']}"

                        if st.session_state.get(delete_key, False):
                            st.warning(f"⚠️ Delete cover letter?")
                            col_a, col_b = st.columns(2)

                            with col_a:
                                if st.button("✅ Yes", key=f"yes_delete_letter_{letter['id']}", use_container_width=True):
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('DELETE FROM cover_letters WHERE id = ?', (letter['id'],))
                                        conn.commit()
                                    st.session_state[delete_key] = False
                                    st.success("Cover letter deleted!")
                                    st.rerun()

                            with col_b:
                                if st.button("❌ No", key=f"no_delete_letter_{letter['id']}", use_container_width=True):
                                    st.session_state[delete_key] = False
                                    st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"delete_letter_{letter['id']}"):
                                st.session_state[delete_key] = True
                                st.rerun()

        else:
            st.info("No saved cover letters yet. Generate your first one in the 'Generate Letter' tab!")

    except Exception as e:
        st.error(f"Error loading cover letters: {str(e)}")

# Sidebar
with st.sidebar:
    st.header("💡 Cover Letter Tips")
    st.markdown("""
    **Structure:**
    1. Opening paragraph - Express interest
    2. Middle paragraphs - Highlight relevant experience
    3. Closing - Call to action

    **Best Practices:**
    - Keep it concise (3-4 paragraphs)
    - Customize for each job
    - Show enthusiasm
    - Highlight achievements
    - Proofread carefully
    - Use professional tone

    **Common Mistakes:**
    - Generic templates
    - Repeating resume verbatim
    - Focusing on what you want
    - Typos and errors
    - Too long (>1 page)
    """)
