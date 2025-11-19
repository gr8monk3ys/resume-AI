import streamlit as st
import sys
import os
from datetime import datetime, date

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.database import get_db_connection
from models.auth_database import init_auth_database
from utils.auth import init_session_state, is_authenticated, get_current_profile, show_auth_sidebar

st.set_page_config(page_title="Job Tracker", page_icon="📊", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("📊 Job Application Tracker")
st.markdown("Keep track of all your job applications in one centralized dashboard")

# Get profile
profile = get_current_profile()

# Header actions
col1, col2 = st.columns([4, 1])
with col2:
    # Export button at the top
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT company, position, status, application_date, deadline, location, job_url, notes
                FROM job_applications
                WHERE profile_id = ?
                ORDER BY application_date DESC
            ''', (profile['id'],))
            export_apps = cursor.fetchall()

        if export_apps:
            # Create CSV
            csv_lines = ["Company,Position,Status,Application Date,Deadline,Location,Job URL,Notes"]
            for app in export_apps:
                # Escape quotes in fields
                csv_lines.append(f'"{app["company"]}","{app["position"]}","{app["status"]}","{app["application_date"]}","{app["deadline"] or ""}","{app["location"] or ""}","{app["job_url"] or ""}","{(app["notes"] or "").replace(chr(34), chr(34)+chr(34))}"')

            csv_content = '\n'.join(csv_lines)

            st.download_button(
                label="📥 Export CSV",
                data=csv_content,
                file_name=f"job_applications_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                help="Export all applications to CSV"
            )
    except Exception as e:
        st.error(f"Export error: {str(e)}")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["➕ Add Application", "📋 All Applications", "📈 Analytics"])

with tab1:
    st.header("Add New Job Application")

    with st.form("add_application_form"):
        col1, col2 = st.columns(2)

        with col1:
            company = st.text_input("Company Name*", placeholder="e.g., Google")
            position = st.text_input("Position Title*", placeholder="e.g., Software Engineer")
            location = st.text_input("Location", placeholder="e.g., San Francisco, CA")

        with col2:
            status = st.selectbox(
                "Application Status",
                ["Applied", "Phone Screen", "Interview Scheduled", "Interviewed", "Offer", "Rejected", "Withdrawn"]
            )
            application_date = st.date_input("Application Date", value=date.today())
            deadline = st.date_input("Deadline (Optional)", value=None)

        job_url = st.text_input("Job Posting URL", placeholder="https://...")
        job_description = st.text_area("Job Description", height=150, placeholder="Paste the job description here...")
        notes = st.text_area("Notes", height=100, placeholder="Any additional notes about this application...")

        submitted = st.form_submit_button("➕ Add Application", type="primary")

        if submitted:
            if company and position:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO job_applications
                            (profile_id, company, position, job_description, status, application_date, deadline, location, job_url, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            profile['id'], company, position, job_description, status,
                            application_date.isoformat(), deadline.isoformat() if deadline else None,
                            location, job_url, notes
                        ))
                        conn.commit()

                    st.success(f"✅ Application to {company} for {position} added successfully!")

                except Exception as e:
                    st.error(f"Error adding application: {str(e)}")
            else:
                st.warning("Please fill in Company Name and Position Title.")

with tab2:
    st.header("All Applications")

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            ["Applied", "Phone Screen", "Interview Scheduled", "Interviewed", "Offer", "Rejected", "Withdrawn"],
            default=["Applied", "Phone Screen", "Interview Scheduled", "Interviewed", "Offer"]
        )

    with col2:
        search_company = st.text_input("Search Company", placeholder="Search...")

    with col3:
        sort_by = st.selectbox("Sort By", ["Application Date (Newest)", "Application Date (Oldest)", "Company", "Position"])

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Build query with filters
            query = 'SELECT * FROM job_applications WHERE profile_id = ?'
            params = [profile['id']]

            if status_filter:
                placeholders = ','.join('?' * len(status_filter))
                query += f' AND status IN ({placeholders})'
                params.extend(status_filter)

            if search_company:
                query += ' AND (company LIKE ? OR position LIKE ?)'
                params.extend([f'%{search_company}%', f'%{search_company}%'])

            # Add sorting
            if sort_by == "Application Date (Newest)":
                query += ' ORDER BY application_date DESC'
            elif sort_by == "Application Date (Oldest)":
                query += ' ORDER BY application_date ASC'
            elif sort_by == "Company":
                query += ' ORDER BY company ASC'
            else:
                query += ' ORDER BY position ASC'

            cursor.execute(query, params)
            applications = cursor.fetchall()

        if applications:
            st.write(f"**Showing {len(applications)} application(s)**")

            for app in applications:
                with st.expander(f"**{app['company']}** - {app['position']} ({app['status']})"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**Company:** {app['company']}")
                        st.write(f"**Position:** {app['position']}")
                        st.write(f"**Location:** {app['location'] or 'N/A'}")

                    with col2:
                        st.write(f"**Status:** {app['status']}")
                        st.write(f"**Applied:** {app['application_date']}")
                        if app['deadline']:
                            st.write(f"**Deadline:** {app['deadline']}")

                    with col3:
                        if app['job_url']:
                            st.markdown(f"[View Job Posting]({app['job_url']})")

                    if app['job_description']:
                        st.write("**Job Description:**")
                        st.text_area("", value=app['job_description'], height=150, key=f"jd_{app['id']}", disabled=True)

                    if app['notes']:
                        st.write("**Notes:**")
                        st.write(app['notes'])

                    # Action buttons
                    col1, col2, col3 = st.columns([1, 1, 4])

                    with col1:
                        new_status = st.selectbox(
                            "Update Status",
                            ["Applied", "Phone Screen", "Interview Scheduled", "Interviewed", "Offer", "Rejected", "Withdrawn"],
                            index=["Applied", "Phone Screen", "Interview Scheduled", "Interviewed", "Offer", "Rejected", "Withdrawn"].index(app['status']),
                            key=f"status_{app['id']}"
                        )

                        if st.button("Update", key=f"update_{app['id']}"):
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute('UPDATE job_applications SET status = ? WHERE id = ?', (new_status, app['id']))
                                conn.commit()
                            st.success("Status updated!")
                            st.rerun()

                    with col2:
                        # Delete with confirmation
                        delete_key = f"confirm_delete_app_{app['id']}"

                        if st.session_state.get(delete_key, False):
                            st.warning(f"⚠️ Delete {app['company']} - {app['position']}?")
                            col_a, col_b = st.columns(2)

                            with col_a:
                                if st.button("✅ Yes", key=f"yes_delete_{app['id']}", use_container_width=True):
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('DELETE FROM job_applications WHERE id = ?', (app['id'],))
                                        conn.commit()
                                    st.session_state[delete_key] = False
                                    st.success("Application deleted!")
                                    st.rerun()

                            with col_b:
                                if st.button("❌ No", key=f"no_delete_{app['id']}", use_container_width=True):
                                    st.session_state[delete_key] = False
                                    st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"delete_{app['id']}"):
                                st.session_state[delete_key] = True
                                st.rerun()

        else:
            st.info("No applications found. Add your first application in the 'Add Application' tab!")

    except Exception as e:
        st.error(f"Error loading applications: {str(e)}")

with tab3:
    st.header("Application Analytics")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Total applications
            cursor.execute('SELECT COUNT(*) as count FROM job_applications WHERE profile_id = ?', (profile['id'],))
            total_apps = cursor.fetchone()['count']

            # Applications by status
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM job_applications
                WHERE profile_id = ?
                GROUP BY status
            ''', (profile['id'],))
            status_counts = cursor.fetchall()

            # Applications this month
            current_month = datetime.now().strftime('%Y-%m')
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM job_applications
                WHERE profile_id = ? AND application_date LIKE ?
            ''', (profile['id'], f'{current_month}%'))
            this_month = cursor.fetchone()['count']

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Applications", total_apps)

        with col2:
            st.metric("This Month", this_month)

        with col3:
            offers = sum(row['count'] for row in status_counts if row['status'] == 'Offer')
            st.metric("Offers", offers)

        with col4:
            interviews = sum(row['count'] for row in status_counts if 'Interview' in row['status'])
            st.metric("Interviews", interviews)

        # Status breakdown
        st.subheader("Applications by Status")

        if status_counts:
            status_data = {row['status']: row['count'] for row in status_counts}

            # Create a simple bar chart visualization
            for status, count in sorted(status_data.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_apps * 100) if total_apps > 0 else 0
                st.write(f"**{status}:** {count} ({percentage:.1f}%)")
                st.progress(percentage / 100)
        else:
            st.info("No data to display yet. Start adding applications!")

        # Recent activity
        st.subheader("Recent Applications (Last 5)")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT company, position, application_date, status
                FROM job_applications
                WHERE profile_id = ?
                ORDER BY application_date DESC
                LIMIT 5
            ''', (profile['id'],))
            recent = cursor.fetchall()

        if recent:
            for app in recent:
                st.write(f"• **{app['company']}** - {app['position']} | {app['application_date']} | {app['status']}")
        else:
            st.info("No applications yet.")

    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")

# Sidebar tips
with st.sidebar:
    st.header("💡 Application Tips")
    st.markdown("""
    **Stay Organized:**
    - Update status regularly
    - Set deadline reminders
    - Keep detailed notes
    - Track follow-ups

    **Status Guide:**
    - **Applied** - Just submitted
    - **Phone Screen** - Initial call scheduled
    - **Interview Scheduled** - In-person/video upcoming
    - **Interviewed** - Waiting for response
    - **Offer** - Received offer
    - **Rejected** - Not selected
    - **Withdrawn** - You withdrew
    """)
