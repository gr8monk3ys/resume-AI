import os
import sys
from datetime import date, datetime, timedelta

import streamlit as st

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.auth_database import init_auth_database
from models.database import get_db_connection, init_database
from utils.auth import get_current_profile, init_session_state, is_authenticated, show_auth_sidebar

st.set_page_config(page_title="Interview Timeline", page_icon="📅", layout="wide")

# Initialize auth and database
init_auth_database()
init_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("Please log in to access this page")
    st.info("Use the Login page from the sidebar")
    st.stop()

st.title("📅 Interview Notes & Timeline")
st.markdown("Track interview events, interviewers, and follow-ups for your job applications")

profile = get_current_profile()

# Event types for interviews
EVENT_TYPES = [
    "Application Submitted",
    "Recruiter Call",
    "Phone Screen",
    "Technical Interview",
    "Behavioral Interview",
    "Panel Interview",
    "Hiring Manager Call",
    "On-site Interview",
    "Take-home Assignment",
    "Final Round",
    "Offer Discussion",
    "Follow-up Sent",
    "Thank You Sent",
    "Other",
]

EVENT_ICONS = {
    "Application Submitted": "📤",
    "Recruiter Call": "📞",
    "Phone Screen": "📱",
    "Technical Interview": "💻",
    "Behavioral Interview": "🗣️",
    "Panel Interview": "👥",
    "Hiring Manager Call": "👔",
    "On-site Interview": "🏢",
    "Take-home Assignment": "📝",
    "Final Round": "🎯",
    "Offer Discussion": "💰",
    "Follow-up Sent": "📧",
    "Thank You Sent": "🙏",
    "Other": "📋",
}

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📅 Timeline", "➕ Add Event", "⏰ Follow-ups", "👤 Contacts"])

with tab1:
    st.header("Interview Timeline")

    # Filter by application
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, company, position FROM job_applications
            WHERE profile_id = ?
            ORDER BY updated_at DESC
        """,
            (profile["id"],),
        )
        applications = cursor.fetchall()

    app_options = {f"{app['company']} - {app['position']}": app["id"] for app in applications}
    app_options = {"All Applications": None, **app_options}

    selected_app = st.selectbox("Filter by Application", list(app_options.keys()))
    selected_app_id = app_options[selected_app]

    st.divider()

    # Get events
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if selected_app_id:
                cursor.execute(
                    """
                    SELECT ie.*, ja.company, ja.position
                    FROM interview_events ie
                    JOIN job_applications ja ON ie.job_application_id = ja.id
                    WHERE ja.profile_id = ? AND ie.job_application_id = ?
                    ORDER BY ie.event_date DESC, ie.created_at DESC
                """,
                    (profile["id"], selected_app_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT ie.*, ja.company, ja.position
                    FROM interview_events ie
                    JOIN job_applications ja ON ie.job_application_id = ja.id
                    WHERE ja.profile_id = ?
                    ORDER BY ie.event_date DESC, ie.created_at DESC
                """,
                    (profile["id"],),
                )

            events = cursor.fetchall()

        if events:
            # Group events by date
            events_by_date = {}
            for event in events:
                event_date = event["event_date"] or "No Date"
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event)

            # Display timeline
            for event_date, date_events in events_by_date.items():
                st.subheader(f"📆 {event_date}")

                for event in date_events:
                    icon = EVENT_ICONS.get(event["event_type"], "📋")

                    with st.container():
                        col1, col2 = st.columns([4, 1])

                        with col1:
                            st.markdown(
                                f"""
                            **{icon} {event['event_type']}** at **{event['company']}** - {event['position']}
                            """
                            )

                            if event["event_time"]:
                                st.caption(f"Time: {event['event_time']}")

                            if event["interviewer_name"]:
                                interviewer_info = f"**Interviewer:** {event['interviewer_name']}"
                                if event["interviewer_title"]:
                                    interviewer_info += f" ({event['interviewer_title']})"
                                st.write(interviewer_info)

                            if event["notes"]:
                                with st.expander("View Notes"):
                                    st.write(event["notes"])

                            if event["follow_up_date"]:
                                status = "Done" if event["follow_up_done"] else "Pending"
                                color = "green" if event["follow_up_done"] else "orange"
                                st.markdown(
                                    f"**Follow-up:** {event['follow_up_date']} (:{color}[{status}])"
                                )

                        with col2:
                            if st.button("🗑️", key=f"del_event_{event['id']}"):
                                with get_db_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "DELETE FROM interview_events WHERE id = ?", (event["id"],)
                                    )
                                    conn.commit()
                                st.rerun()

                        st.divider()
        else:
            st.info("No interview events yet. Add your first event in the 'Add Event' tab!")

    except Exception as e:
        st.error(f"Error loading timeline: {str(e)}")

with tab2:
    st.header("Add Interview Event")

    if not applications:
        st.warning("No job applications found. Add a job application first in the Job Tracker.")
        st.stop()

    with st.form("add_event_form"):
        # Select application
        app_select = st.selectbox(
            "Select Application*",
            [f"{app['company']} - {app['position']}" for app in applications],
            key="event_app_select",
        )
        selected_idx = [f"{app['company']} - {app['position']}" for app in applications].index(
            app_select
        )
        selected_job_id = applications[selected_idx]["id"]

        col1, col2 = st.columns(2)

        with col1:
            event_type = st.selectbox("Event Type*", EVENT_TYPES)
            event_date = st.date_input("Event Date", value=date.today())
            event_time = st.time_input("Event Time (Optional)", value=None)

        with col2:
            interviewer_name = st.text_input("Interviewer Name", placeholder="e.g., John Smith")
            interviewer_title = st.text_input(
                "Interviewer Title", placeholder="e.g., Engineering Manager"
            )
            interviewer_email = st.text_input(
                "Interviewer Email", placeholder="e.g., john@company.com"
            )

        notes = st.text_area(
            "Notes",
            height=150,
            placeholder="Key discussion points, questions asked, your answers...",
        )

        st.subheader("Follow-up Reminder")
        col1, col2 = st.columns(2)
        with col1:
            set_followup = st.checkbox("Set follow-up reminder")
        with col2:
            if set_followup:
                followup_date = st.date_input(
                    "Follow-up Date", value=date.today() + timedelta(days=3)
                )
            else:
                followup_date = None

        submitted = st.form_submit_button("Add Event", type="primary")

        if submitted:
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO interview_events
                        (job_application_id, event_type, event_date, event_time,
                         interviewer_name, interviewer_title, interviewer_email,
                         notes, follow_up_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            selected_job_id,
                            event_type,
                            event_date.isoformat(),
                            event_time.strftime("%H:%M") if event_time else None,
                            interviewer_name or None,
                            interviewer_title or None,
                            interviewer_email or None,
                            notes or None,
                            followup_date.isoformat() if followup_date else None,
                        ),
                    )
                    conn.commit()

                st.success(f"Added {event_type} event for {app_select}!")
                st.rerun()

            except Exception as e:
                st.error(f"Error adding event: {str(e)}")

with tab3:
    st.header("Follow-up Reminders")

    # Get pending follow-ups
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ie.*, ja.company, ja.position
                FROM interview_events ie
                JOIN job_applications ja ON ie.job_application_id = ja.id
                WHERE ja.profile_id = ? AND ie.follow_up_date IS NOT NULL
                ORDER BY ie.follow_up_done ASC, ie.follow_up_date ASC
            """,
                (profile["id"],),
            )
            followups = cursor.fetchall()

        if followups:
            # Separate pending and completed
            pending = [f for f in followups if not f["follow_up_done"]]
            completed = [f for f in followups if f["follow_up_done"]]

            # Pending follow-ups
            st.subheader(f"Pending ({len(pending)})")

            if pending:
                for fu in pending:
                    fu_date = datetime.strptime(fu["follow_up_date"], "%Y-%m-%d").date()
                    days_until = (fu_date - date.today()).days

                    if days_until < 0:
                        urgency = "red"
                        urgency_text = f"Overdue by {abs(days_until)} days!"
                    elif days_until == 0:
                        urgency = "orange"
                        urgency_text = "Due today!"
                    elif days_until <= 2:
                        urgency = "orange"
                        urgency_text = f"Due in {days_until} days"
                    else:
                        urgency = "green"
                        urgency_text = f"Due in {days_until} days"

                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        st.write(f"**{fu['company']}** - {fu['position']}")
                        st.caption(f"{fu['event_type']} on {fu['event_date']}")

                    with col2:
                        st.markdown(f":{urgency}[{urgency_text}]")
                        st.caption(f"Follow-up: {fu['follow_up_date']}")

                    with col3:
                        if st.button("Mark Done", key=f"done_{fu['id']}"):
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "UPDATE interview_events SET follow_up_done = 1 WHERE id = ?",
                                    (fu["id"],),
                                )
                                conn.commit()
                            st.rerun()

                    if fu["interviewer_name"]:
                        st.caption(
                            f"Contact: {fu['interviewer_name']} ({fu['interviewer_email'] or 'no email'})"
                        )

                    st.divider()
            else:
                st.success("No pending follow-ups! You're all caught up.")

            # Completed follow-ups
            if completed:
                with st.expander(f"Completed Follow-ups ({len(completed)})"):
                    for fu in completed:
                        st.write(
                            f"**{fu['company']}** - {fu['event_type']} - {fu['follow_up_date']}"
                        )
        else:
            st.info("No follow-up reminders set. Add follow-ups when logging interview events.")

    except Exception as e:
        st.error(f"Error loading follow-ups: {str(e)}")

with tab4:
    st.header("Interviewer Contacts")
    st.markdown("All interviewers you've met during your job search")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT
                    ie.interviewer_name,
                    ie.interviewer_title,
                    ie.interviewer_email,
                    ja.company,
                    ja.position,
                    ie.event_date,
                    ie.event_type
                FROM interview_events ie
                JOIN job_applications ja ON ie.job_application_id = ja.id
                WHERE ja.profile_id = ? AND ie.interviewer_name IS NOT NULL
                ORDER BY ja.company, ie.event_date DESC
            """,
                (profile["id"],),
            )
            contacts = cursor.fetchall()

        if contacts:
            # Group by company
            contacts_by_company = {}
            for contact in contacts:
                company = contact["company"]
                if company not in contacts_by_company:
                    contacts_by_company[company] = []
                contacts_by_company[company].append(contact)

            for company, company_contacts in contacts_by_company.items():
                with st.expander(
                    f"**{company}** ({len(company_contacts)} contacts)", expanded=True
                ):
                    for contact in company_contacts:
                        col1, col2 = st.columns([3, 2])

                        with col1:
                            st.write(f"**{contact['interviewer_name']}**")
                            if contact["interviewer_title"]:
                                st.caption(contact["interviewer_title"])

                        with col2:
                            if contact["interviewer_email"]:
                                st.markdown(
                                    f"[{contact['interviewer_email']}](mailto:{contact['interviewer_email']})"
                                )
                            st.caption(f"{contact['event_type']} - {contact['event_date']}")

                        st.divider()
        else:
            st.info(
                "No interviewer contacts recorded yet. Add interviewer details when logging events."
            )

    except Exception as e:
        st.error(f"Error loading contacts: {str(e)}")

# Sidebar
with st.sidebar:
    st.header("Timeline Tips")
    st.markdown(
        """
    **Best Practices:**
    - Log events right after they happen
    - Include interviewer names for networking
    - Set follow-up reminders for thank you emails
    - Note key questions asked for future prep

    **Event Types:**
    - **Recruiter Call**: Initial screening
    - **Phone Screen**: First technical/fit check
    - **Technical Interview**: Coding/system design
    - **Behavioral Interview**: STAR method questions
    - **Panel Interview**: Multiple interviewers

    **Follow-up Timeline:**
    - Thank you email: Within 24 hours
    - Follow-up if no response: 1 week
    - Second follow-up: 2 weeks
    """
    )
