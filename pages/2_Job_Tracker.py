import streamlit as st
import sys
import os
import csv
import io
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
st.markdown("Keep track of all your job applications with a visual Kanban board")

# Get profile
profile = get_current_profile()

# Define status columns for Kanban
KANBAN_STATUSES = ["Bookmarked", "Applied", "Phone Screen", "Interview", "Offer", "Rejected"]
STATUS_COLORS = {
    "Bookmarked": "🔖",
    "Applied": "📤",
    "Phone Screen": "📞",
    "Interview": "🎯",
    "Offer": "🎉",
    "Rejected": "❌"
}

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
            # Create CSV using csv module
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_ALL)
            writer.writerow(["Company", "Position", "Status", "Application Date", "Deadline", "Location", "Job URL", "Notes"])
            for app in export_apps:
                writer.writerow([
                    app["company"], app["position"], app["status"],
                    app["application_date"], app["deadline"] or "",
                    app["location"] or "", app["job_url"] or "", app["notes"] or ""
                ])
            csv_content = output.getvalue()

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
tab1, tab2, tab3, tab4 = st.tabs(["📋 Kanban Board", "➕ Add Application", "📝 List View", "📈 Analytics"])

with tab1:
    st.header("Kanban Board")
    st.caption("Drag mentally, click to move! Select a new status to move applications between columns.")

    # Get all applications
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM job_applications
                WHERE profile_id = ?
                ORDER BY updated_at DESC
            ''', (profile['id'],))
            all_applications = cursor.fetchall()

        # Group applications by status
        apps_by_status = {status: [] for status in KANBAN_STATUSES}
        for app in all_applications:
            status = app['status']
            # Map old statuses to new ones
            if status == "Interview Scheduled" or status == "Interviewed":
                status = "Interview"
            elif status == "Withdrawn":
                status = "Rejected"
            if status in apps_by_status:
                apps_by_status[status].append(app)

        # Create Kanban columns
        cols = st.columns(len(KANBAN_STATUSES))

        for idx, status in enumerate(KANBAN_STATUSES):
            with cols[idx]:
                # Column header with count
                count = len(apps_by_status[status])
                st.markdown(f"### {STATUS_COLORS[status]} {status}")
                st.caption(f"{count} job{'s' if count != 1 else ''}")
                st.markdown("---")

                # Display cards for this status
                for app in apps_by_status[status]:
                    with st.container():
                        # Card styling using markdown
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {'#ff6b6b' if status == 'Rejected' else '#4CAF50' if status == 'Offer' else '#2196F3'};">
                            <strong>{app['company']}</strong><br>
                            <small>{app['position']}</small><br>
                            <small style="color: #666;">{app['application_date'] or 'No date'}</small>
                        </div>
                        """, unsafe_allow_html=True)

                        # Quick actions in expander
                        with st.expander("Actions", expanded=False):
                            # Move to different status
                            new_status = st.selectbox(
                                "Move to",
                                KANBAN_STATUSES,
                                index=KANBAN_STATUSES.index(status) if status in KANBAN_STATUSES else 0,
                                key=f"kanban_status_{app['id']}"
                            )

                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("Move", key=f"kanban_move_{app['id']}", use_container_width=True):
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            'UPDATE job_applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                                            (new_status, app['id'])
                                        )
                                        conn.commit()
                                    st.rerun()

                            with col_b:
                                if st.button("🗑️", key=f"kanban_del_{app['id']}", use_container_width=True):
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('DELETE FROM job_applications WHERE id = ?', (app['id'],))
                                        conn.commit()
                                    st.rerun()

                            # Show details
                            if app['location']:
                                st.caption(f"📍 {app['location']}")
                            if app['job_url']:
                                st.markdown(f"[🔗 View Job]({app['job_url']})")
                            if app['notes']:
                                st.caption(f"📝 {app['notes'][:50]}...")

                # Add new to this column button
                if st.button(f"+ Add to {status}", key=f"add_to_{status}", use_container_width=True):
                    st.session_state['prefill_status'] = status
                    st.switch_page("pages/2_Job_Tracker.py")

    except Exception as e:
        st.error(f"Error loading Kanban board: {str(e)}")

with tab2:
    st.header("Add New Job Application")

    # Check if we have a prefilled status
    prefill_status = st.session_state.get('prefill_status', 'Applied')
    if 'prefill_status' in st.session_state:
        del st.session_state['prefill_status']

    with st.form("add_application_form"):
        col1, col2 = st.columns(2)

        with col1:
            company = st.text_input("Company Name*", placeholder="e.g., Google")
            position = st.text_input("Position Title*", placeholder="e.g., Software Engineer")
            location = st.text_input("Location", placeholder="e.g., San Francisco, CA")

        with col2:
            status = st.selectbox(
                "Application Status",
                KANBAN_STATUSES,
                index=KANBAN_STATUSES.index(prefill_status) if prefill_status in KANBAN_STATUSES else 1
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
                    st.rerun()

                except Exception as e:
                    st.error(f"Error adding application: {str(e)}")
            else:
                st.warning("Please fill in Company Name and Position Title.")

    # Quick bookmark section
    st.markdown("---")
    st.subheader("🔖 Quick Bookmark")
    st.caption("Save a job for later - just need company and position")

    with st.form("quick_bookmark_form"):
        col1, col2 = st.columns(2)
        with col1:
            bm_company = st.text_input("Company*", placeholder="Company name", key="bm_company")
        with col2:
            bm_position = st.text_input("Position*", placeholder="Position title", key="bm_position")

        bm_url = st.text_input("Job URL (optional)", placeholder="https://...", key="bm_url")

        if st.form_submit_button("🔖 Bookmark", type="secondary"):
            if bm_company and bm_position:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO job_applications
                            (profile_id, company, position, status, job_url)
                            VALUES (?, ?, ?, 'Bookmarked', ?)
                        ''', (profile['id'], bm_company, bm_position, bm_url))
                        conn.commit()
                    st.success(f"✅ Bookmarked {bm_company} - {bm_position}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter company and position")

with tab3:
    st.header("All Applications (List View)")

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            KANBAN_STATUSES,
            default=KANBAN_STATUSES
        )

    with col2:
        search_company = st.text_input("Search Company/Position", placeholder="Search...")

    with col3:
        sort_by = st.selectbox("Sort By", ["Application Date (Newest)", "Application Date (Oldest)", "Company", "Status"])

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
                query += ' ORDER BY status ASC'

            cursor.execute(query, params)
            applications = cursor.fetchall()

        if applications:
            st.write(f"**Showing {len(applications)} application(s)**")

            for app in applications:
                status_emoji = STATUS_COLORS.get(app['status'], "📋")
                with st.expander(f"{status_emoji} **{app['company']}** - {app['position']} ({app['status']})"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**Company:** {app['company']}")
                        st.write(f"**Position:** {app['position']}")
                        st.write(f"**Location:** {app['location'] or 'N/A'}")

                    with col2:
                        st.write(f"**Status:** {app['status']}")
                        st.write(f"**Applied:** {app['application_date'] or 'N/A'}")
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
                    st.markdown("---")
                    col1, col2, col3 = st.columns([2, 1, 3])

                    with col1:
                        new_status = st.selectbox(
                            "Update Status",
                            KANBAN_STATUSES,
                            index=KANBAN_STATUSES.index(app['status']) if app['status'] in KANBAN_STATUSES else 0,
                            key=f"status_{app['id']}"
                        )

                        if st.button("Update Status", key=f"update_{app['id']}"):
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    'UPDATE job_applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                                    (new_status, app['id'])
                                )
                                conn.commit()
                            st.success("Status updated!")
                            st.rerun()

                    with col2:
                        if st.button("🗑️ Delete", key=f"delete_{app['id']}"):
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute('DELETE FROM job_applications WHERE id = ?', (app['id'],))
                                conn.commit()
                            st.success("Deleted!")
                            st.rerun()

        else:
            st.info("No applications found. Add your first application in the 'Add Application' tab!")

    except Exception as e:
        st.error(f"Error loading applications: {str(e)}")

with tab4:
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

            # Applications this week
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM job_applications
                WHERE profile_id = ? AND application_date >= date('now', '-7 days')
            ''', (profile['id'],))
            this_week = cursor.fetchone()['count']

        # Display metrics
        st.subheader("Overview")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Applications", total_apps)

        with col2:
            st.metric("This Week", this_week)

        with col3:
            st.metric("This Month", this_month)

        with col4:
            active = sum(row['count'] for row in status_counts if row['status'] not in ['Rejected', 'Offer'])
            st.metric("Active", active)

        # Funnel metrics
        st.subheader("Application Funnel")
        col1, col2, col3, col4 = st.columns(4)

        status_data = {row['status']: row['count'] for row in status_counts}

        with col1:
            applied = status_data.get('Applied', 0) + status_data.get('Bookmarked', 0)
            st.metric("📤 Applied/Saved", applied)

        with col2:
            screens = status_data.get('Phone Screen', 0)
            rate = f"{(screens/applied*100):.0f}%" if applied > 0 else "0%"
            st.metric("📞 Phone Screens", screens, rate)

        with col3:
            interviews = status_data.get('Interview', 0)
            rate = f"{(interviews/applied*100):.0f}%" if applied > 0 else "0%"
            st.metric("🎯 Interviews", interviews, rate)

        with col4:
            offers = status_data.get('Offer', 0)
            rate = f"{(offers/applied*100):.0f}%" if applied > 0 else "0%"
            st.metric("🎉 Offers", offers, rate)

        # Status breakdown with visual bars
        st.subheader("Status Breakdown")

        if status_counts:
            for status in KANBAN_STATUSES:
                count = status_data.get(status, 0)
                percentage = (count / total_apps * 100) if total_apps > 0 else 0
                emoji = STATUS_COLORS.get(status, "📋")

                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"{emoji} **{status}:** {count}")
                with col2:
                    st.progress(percentage / 100)
        else:
            st.info("No data to display yet. Start adding applications!")

        # Recent activity
        st.subheader("Recent Activity")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT company, position, application_date, status
                FROM job_applications
                WHERE profile_id = ?
                ORDER BY updated_at DESC
                LIMIT 10
            ''', (profile['id'],))
            recent = cursor.fetchall()

        if recent:
            for app in recent:
                emoji = STATUS_COLORS.get(app['status'], "📋")
                st.write(f"{emoji} **{app['company']}** - {app['position']} | {app['application_date'] or 'No date'} | {app['status']}")
        else:
            st.info("No applications yet.")

        # Weekly goal tracker
        st.subheader("Weekly Goal")
        weekly_goal = st.slider("Set your weekly application goal", 1, 50, 10)
        progress = min(this_week / weekly_goal, 1.0)
        st.progress(progress)
        if this_week >= weekly_goal:
            st.success(f"🎉 Goal achieved! {this_week}/{weekly_goal} applications this week!")
        else:
            st.info(f"📊 {this_week}/{weekly_goal} applications this week. Keep going!")

    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")

# Sidebar tips
with st.sidebar:
    st.header("💡 Tracker Tips")
    st.markdown("""
    **Kanban Workflow:**
    1. 🔖 **Bookmark** jobs you find interesting
    2. 📤 Move to **Applied** when you submit
    3. 📞 Update to **Phone Screen** when scheduled
    4. 🎯 Track **Interviews** as they happen
    5. 🎉 Celebrate **Offers**!

    **Pro Tips:**
    - Use Quick Bookmark for fast saves
    - Keep job descriptions for interview prep
    - Add notes after each interaction
    - Export data for backup
    """)
