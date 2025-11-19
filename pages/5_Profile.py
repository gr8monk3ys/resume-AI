import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.database import get_db_connection
from models.auth_database import init_auth_database
from utils.auth import init_session_state, is_authenticated, get_current_profile, show_auth_sidebar
from utils.validators import (
    validate_email,
    validate_linkedin_url,
    validate_github_url,
    validate_url,
    validate_phone
)

st.set_page_config(page_title="Profile", page_icon="👤", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("👤 Profile Management")
st.markdown("Manage your personal information and preferences")

# Get current profile
profile = get_current_profile()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["✏️ Edit Profile", "📊 Statistics", "🔐 Change Password", "⚙️ Settings"])

with tab1:
    st.header("Personal Information")
    st.markdown("Keep your information up to date for better cover letter and email generation")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Full Name*",
                value=profile.get('name', ''),
                placeholder="John Doe"
            )

            email = st.text_input(
                "Email",
                value=profile.get('email', ''),
                placeholder="john.doe@example.com"
            )

            phone = st.text_input(
                "Phone",
                value=profile.get('phone', ''),
                placeholder="+1 (555) 123-4567"
            )

        with col2:
            linkedin = st.text_input(
                "LinkedIn URL",
                value=profile.get('linkedin', ''),
                placeholder="https://linkedin.com/in/johndoe"
            )

            github = st.text_input(
                "GitHub URL",
                value=profile.get('github', ''),
                placeholder="https://github.com/johndoe"
            )

            portfolio = st.text_input(
                "Portfolio/Website",
                value=profile.get('portfolio', ''),
                placeholder="https://johndoe.com"
            )

        submitted = st.form_submit_button("💾 Update Profile", type="primary")

        if submitted:
            from utils.input_sanitizer import (
                sanitize_text_input,
                sanitize_email as sanitize_email_input,
                sanitize_phone as sanitize_phone_input,
                sanitize_url
            )

            # Sanitize inputs first
            name = sanitize_text_input(name, max_length=100)
            email = sanitize_text_input(email, max_length=254) if email else ""
            phone = sanitize_text_input(phone, max_length=20) if phone else ""
            linkedin = sanitize_text_input(linkedin, max_length=200) if linkedin else ""
            github = sanitize_text_input(github, max_length=200) if github else ""
            portfolio = sanitize_text_input(portfolio, max_length=200) if portfolio else ""

            # Validate inputs
            validation_errors = []

            if not name:
                validation_errors.append("Name is required")

            if email:
                # Use new sanitizer validation
                is_valid, error_msg = sanitize_email_input(email)
                if not is_valid:
                    validation_errors.append(f"Email: {error_msg}")
                else:
                    # Also use old validation for backwards compatibility
                    is_valid, error_msg = validate_email(email)
                    if not is_valid:
                        validation_errors.append(f"Email: {error_msg}")

            if phone:
                # Use new sanitizer validation
                is_valid, error_msg = sanitize_phone_input(phone)
                if not is_valid:
                    validation_errors.append(f"Phone: {error_msg}")

            if linkedin:
                # Use new sanitizer validation
                is_valid, error_msg = sanitize_url(linkedin)
                if not is_valid:
                    validation_errors.append(f"LinkedIn: {error_msg}")
                else:
                    # Also use old validation
                    is_valid, error_msg = validate_linkedin_url(linkedin)
                    if not is_valid:
                        validation_errors.append(f"LinkedIn: {error_msg}")

            if github:
                is_valid, error_msg = sanitize_url(github)
                if not is_valid:
                    validation_errors.append(f"GitHub: {error_msg}")
                else:
                    is_valid, error_msg = validate_github_url(github)
                    if not is_valid:
                        validation_errors.append(f"GitHub: {error_msg}")

            if portfolio:
                is_valid, error_msg = sanitize_url(portfolio)
                if not is_valid:
                    validation_errors.append(f"Portfolio: {error_msg}")
                else:
                    is_valid, error_msg = validate_url(portfolio, allow_empty=False)
                    if not is_valid:
                        validation_errors.append(f"Portfolio: {error_msg}")

            # Show errors or save
            if validation_errors:
                for error in validation_errors:
                    st.error(f"❌ {error}")
            else:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE profiles
                            SET name = ?, email = ?, phone = ?, linkedin = ?, github = ?, portfolio = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (name, email, phone, linkedin, github, portfolio, profile['id']))
                        conn.commit()

                    st.success("✅ Profile updated successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error updating profile: {str(e)}")

    # Quick copy section
    st.markdown("---")
    st.subheader("📋 Quick Copy")
    st.markdown("Copy your information for quick pasting into forms")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Copy Email"):
            if profile.get('email'):
                st.code(profile['email'])
            else:
                st.info("No email set")

        if st.button("Copy LinkedIn"):
            if profile.get('linkedin'):
                st.code(profile['linkedin'])
            else:
                st.info("No LinkedIn URL set")

    with col2:
        if st.button("Copy Phone"):
            if profile.get('phone'):
                st.code(profile['phone'])
            else:
                st.info("No phone set")

        if st.button("Copy GitHub"):
            if profile.get('github'):
                st.code(profile['github'])
            else:
                st.info("No GitHub URL set")

with tab2:
    st.header("Your Activity Statistics")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get comprehensive stats
            # Resumes
            cursor.execute('''
                SELECT COUNT(*) as total,
                       AVG(ats_score) as avg_score,
                       MAX(ats_score) as max_score
                FROM resumes
                WHERE profile_id = ?
            ''', (profile['id'],))
            resume_stats = cursor.fetchone()

            # Applications by status
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM job_applications
                WHERE profile_id = ?
                GROUP BY status
            ''', (profile['id'],))
            app_status = cursor.fetchall()

            # Recent activity
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM job_applications
                WHERE profile_id = ? AND date(application_date) >= date('now', '-7 days')
            ''', (profile['id'],))
            recent_apps = cursor.fetchone()['count']

            # Cover letters
            cursor.execute('SELECT COUNT(*) as count FROM cover_letters WHERE profile_id = ?', (profile['id'],))
            letter_count = cursor.fetchone()['count']

            # Career journal
            cursor.execute('SELECT COUNT(*) as count FROM career_journal WHERE profile_id = ?', (profile['id'],))
            journal_count = cursor.fetchone()['count']

        # Display metrics
        st.subheader("Overview")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_resumes = resume_stats['total'] or 0
            st.metric("Resume Versions", total_resumes)

        with col2:
            total_apps = sum(row['count'] for row in app_status)
            st.metric("Total Applications", total_apps)

        with col3:
            st.metric("Cover Letters", letter_count)

        with col4:
            st.metric("Journal Entries", journal_count)

        # Resume stats
        if total_resumes > 0:
            st.markdown("---")
            st.subheader("Resume Analytics")
            col1, col2 = st.columns(2)

            with col1:
                avg_score = resume_stats['avg_score'] or 0
                st.metric("Average ATS Score", f"{avg_score:.1f}")

            with col2:
                max_score = resume_stats['max_score'] or 0
                st.metric("Best ATS Score", f"{max_score}")

        # Application stats
        if app_status:
            st.markdown("---")
            st.subheader("Application Breakdown")

            for status in app_status:
                percentage = (status['count'] / total_apps * 100) if total_apps > 0 else 0
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{status['status']}**")
                    st.progress(percentage / 100)
                with col2:
                    st.write(f"{status['count']} ({percentage:.1f}%)")

        # Recent activity
        st.markdown("---")
        st.subheader("Recent Activity")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Applications (Last 7 Days)", recent_apps)

        with col2:
            if total_apps > 0:
                success_rate = sum(row['count'] for row in app_status if row['status'] in ['Offer', 'Interviewed']) / total_apps * 100
                st.metric("Success Rate", f"{success_rate:.1f}%", help="Percentage of applications that reached interview or offer stage")

        # Account info
        st.markdown("---")
        st.subheader("Account Information")
        st.write(f"**Profile Created:** {profile.get('created_at', 'Unknown')[:10]}")
        st.write(f"**Last Updated:** {profile.get('updated_at', 'Unknown')[:10]}")

    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")

with tab3:
    st.header("🔐 Change Password")
    st.markdown("Update your account password for better security")

    from utils.auth import get_current_user
    from models.auth_database import change_password
    from utils.password_validator import (
        validate_password_strength,
        validate_password_confirmation,
        get_password_strength_label,
        suggest_password_improvements,
        generate_password_requirements_text
    )
    from utils.audit_logger import log_password_change

    user = get_current_user()

    # Show password requirements
    with st.expander("📋 Password Requirements", expanded=False):
        st.markdown(generate_password_requirements_text())

    with st.form("password_change_form"):
        st.markdown("**All fields are required**")

        current_password = st.text_input(
            "Current Password",
            type="password",
            placeholder="Enter your current password"
        )

        new_password = st.text_input(
            "New Password",
            type="password",
            placeholder="Enter your new password"
        )

        confirm_new_password = st.text_input(
            "Confirm New Password",
            type="password",
            placeholder="Re-enter your new password"
        )

        submit_password = st.form_submit_button("🔒 Change Password", type="primary")

        if submit_password:
            errors = []

            # Validate all fields filled
            if not current_password:
                errors.append("Current password is required")

            if not new_password:
                errors.append("New password is required")

            if not confirm_new_password:
                errors.append("Please confirm your new password")

            # Validate new password strength
            if new_password:
                is_valid, password_errors, strength = validate_password_strength(new_password)
                if not is_valid:
                    errors.extend(password_errors)
                else:
                    # Show password strength
                    label, color = get_password_strength_label(strength)
                    st.info(f"New Password Strength: **{label}** ({strength}/100)")

                    # Show suggestions if not very strong
                    if strength < 80:
                        suggestions = suggest_password_improvements(new_password)
                        if suggestions:
                            for suggestion in suggestions:
                                st.warning(suggestion)

            # Validate confirmation
            conf_valid, conf_error = validate_password_confirmation(new_password, confirm_new_password)
            if not conf_valid:
                errors.append(conf_error)

            # Check if new password is same as current
            if new_password and current_password and new_password == current_password:
                errors.append("New password must be different from current password")

            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Attempt password change
                try:
                    success = change_password(user['id'], current_password, new_password)

                    if success:
                        # Log password change
                        log_password_change(user['id'], user['username'])

                        st.success("✅ Password changed successfully!")
                        st.info("👉 Please use your new password the next time you log in")
                        st.balloons()
                    else:
                        st.error("❌ Current password is incorrect. Please try again.")

                except Exception as e:
                    st.error(f"❌ Error changing password: {str(e)}")

    st.markdown("---")
    st.markdown("### Password Security Tips")
    st.markdown("""
    - Use a unique password for each account
    - Consider using a password manager
    - Change your password regularly (every 90 days recommended)
    - Never share your password with anyone
    - Use two-factor authentication when available (coming soon!)
    """)

with tab4:
    st.header("Settings & Data Management")

    st.subheader("🗄️ Data Export")
    st.markdown("Export your data for backup or portability")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Export All Applications (CSV)", type="primary"):
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT company, position, status, application_date, deadline, location, job_url, notes
                        FROM job_applications
                        WHERE profile_id = ?
                        ORDER BY application_date DESC
                    ''', (profile['id'],))
                    apps = cursor.fetchall()

                if apps:
                    # Create CSV
                    csv_lines = ["Company,Position,Status,Application Date,Deadline,Location,Job URL,Notes"]
                    for app in apps:
                        csv_lines.append(f'"{app["company"]}","{app["position"]}","{app["status"]}","{app["application_date"]}","{app["deadline"] or ""}","{app["location"] or ""}","{app["job_url"] or ""}","{app["notes"] or ""}"')

                    csv_content = '\n'.join(csv_lines)

                    st.download_button(
                        label="Download CSV",
                        data=csv_content,
                        file_name="job_applications.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No applications to export")

            except Exception as e:
                st.error(f"Error exporting applications: {str(e)}")

    with col2:
        if st.button("📥 Export Career Journal"):
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT title, description, achievement_date, tags
                        FROM career_journal
                        WHERE profile_id = ?
                        ORDER BY achievement_date DESC
                    ''', (profile['id'],))
                    achievements = cursor.fetchall()

                if achievements:
                    # Create formatted text
                    content = "CAREER JOURNAL\n" + "="*50 + "\n\n"
                    for ach in achievements:
                        content += f"Title: {ach['title']}\n"
                        content += f"Date: {ach['achievement_date']}\n"
                        if ach['tags']:
                            content += f"Tags: {ach['tags']}\n"
                        content += f"\n{ach['description']}\n"
                        content += "\n" + "-"*50 + "\n\n"

                    st.download_button(
                        label="Download Journal",
                        data=content,
                        file_name="career_journal.txt",
                        mime="text/plain"
                    )
                else:
                    st.info("No journal entries to export")

            except Exception as e:
                st.error(f"Error exporting journal: {str(e)}")

    st.markdown("---")
    st.subheader("⚠️ Danger Zone")

    with st.expander("🗑️ Delete All Data"):
        st.warning("This action cannot be undone!")

        st.markdown("""
        This will permanently delete:
        - All resume versions
        - All job applications
        - All cover letters
        - All career journal entries
        - Your profile information will be reset

        **Your profile will remain, but all data will be cleared.**
        """)

        confirm_text = st.text_input("Type 'DELETE ALL DATA' to confirm:")

        if st.button("🗑️ Permanently Delete All Data", type="secondary"):
            if confirm_text == "DELETE ALL DATA":
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()

                        # Delete all user data
                        cursor.execute('DELETE FROM resumes WHERE profile_id = ?', (profile['id'],))
                        cursor.execute('DELETE FROM job_applications WHERE profile_id = ?', (profile['id'],))
                        cursor.execute('DELETE FROM cover_letters WHERE profile_id = ?', (profile['id'],))
                        cursor.execute('DELETE FROM career_journal WHERE profile_id = ?', (profile['id'],))

                        # Reset profile
                        cursor.execute('''
                            UPDATE profiles
                            SET name = 'Default User', email = '', phone = '', linkedin = '', github = '', portfolio = ''
                            WHERE id = ?
                        ''', (profile['id'],))

                        conn.commit()

                    st.success("All data has been deleted.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error deleting data: {str(e)}")
            else:
                st.error("Please type 'DELETE ALL DATA' exactly to confirm.")

# Sidebar
with st.sidebar:
    st.header("📊 Quick Stats")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get counts
            cursor.execute('SELECT COUNT(*) as count FROM resumes WHERE profile_id = ?', (profile['id'],))
            resumes = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM job_applications WHERE profile_id = ?', (profile['id'],))
            apps = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM career_journal WHERE profile_id = ?', (profile['id'],))
            journal = cursor.fetchone()['count']

        st.metric("Resume Versions", resumes)
        st.metric("Applications", apps)
        st.metric("Journal Entries", journal)

    except Exception as e:
        st.error("Error loading stats")

    st.markdown("---")
    st.markdown("**Profile ID:** " + str(profile['id']))
