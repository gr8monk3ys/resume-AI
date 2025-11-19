import streamlit as st
import sys
import os
from datetime import date

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.database import get_db_connection
from models.auth_database import init_auth_database
from services.llm_service import get_llm_service
from utils.auth import init_session_state, is_authenticated, get_current_profile, show_auth_sidebar

st.set_page_config(page_title="Career Journal", page_icon="📓", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("📓 Career Journal")
st.markdown("Document your achievements and build a library of accomplishments for future applications")

# Initialize services
llm_service = get_llm_service()
profile = get_current_profile()

# Tabs
tab1, tab2, tab3 = st.tabs(["➕ Add Achievement", "📚 All Achievements", "✨ Enhance with AI"])

with tab1:
    st.header("Document a New Achievement")

    st.markdown("""
    Keep a record of your accomplishments, projects, and wins. This journal helps you:
    - Remember specific achievements during interviews
    - Build compelling resume bullet points
    - Track your professional growth over time
    """)

    with st.form("add_achievement_form"):
        title = st.text_input(
            "Achievement Title*",
            placeholder="e.g., Led migration to microservices architecture"
        )

        achievement_date = st.date_input(
            "Date",
            value=date.today(),
            help="When did this achievement occur?"
        )

        description = st.text_area(
            "Description*",
            height=200,
            placeholder="Describe what you did, how you did it, and what the impact was. Include specific metrics and outcomes if possible.\n\nExample:\nLed the migration of monolithic application to microservices architecture, reducing deployment time by 60% and improving system reliability to 99.9% uptime. Coordinated with 5 cross-functional teams and delivered the project 2 weeks ahead of schedule."
        )

        tags = st.text_input(
            "Tags (comma-separated)",
            placeholder="e.g., leadership, python, aws, cost-reduction",
            help="Add tags to make achievements easier to find and categorize"
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("💾 Save Achievement", type="primary")

        if submitted:
            if title and description:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO career_journal (profile_id, title, description, achievement_date, tags)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (profile['id'], title, description, achievement_date.isoformat(), tags))
                        conn.commit()

                    st.success("✅ Achievement saved successfully!")
                    st.balloons()

                except Exception as e:
                    st.error(f"Error saving achievement: {str(e)}")
            else:
                st.warning("Please provide both title and description.")

with tab2:
    st.header("Your Achievement Library")

    # Filter and search
    col1, col2, col3 = st.columns(3)

    with col1:
        search_query = st.text_input("🔍 Search", placeholder="Search achievements...")

    with col2:
        tag_filter = st.text_input("🏷️ Filter by Tag", placeholder="e.g., leadership")

    with col3:
        sort_by = st.selectbox(
            "Sort By",
            ["Date (Newest)", "Date (Oldest)", "Title"]
        )

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Build query
            query = 'SELECT * FROM career_journal WHERE profile_id = ?'
            params = [profile['id']]

            if search_query:
                query += ' AND (title LIKE ? OR description LIKE ?)'
                params.extend([f'%{search_query}%', f'%{search_query}%'])

            if tag_filter:
                query += ' AND tags LIKE ?'
                params.append(f'%{tag_filter}%')

            # Add sorting
            if sort_by == "Date (Newest)":
                query += ' ORDER BY achievement_date DESC'
            elif sort_by == "Date (Oldest)":
                query += ' ORDER BY achievement_date ASC'
            else:
                query += ' ORDER BY title ASC'

            cursor.execute(query, params)
            achievements = cursor.fetchall()

        if achievements:
            st.write(f"**{len(achievements)} achievement(s) found**")

            for achievement in achievements:
                with st.expander(f"**{achievement['title']}** ({achievement['achievement_date']})"):

                    # Display tags if available
                    if achievement['tags']:
                        tags_list = [tag.strip() for tag in achievement['tags'].split(',')]
                        tag_html = ' '.join([f'<span style="background-color: #e1f5ff; padding: 2px 8px; border-radius: 4px; margin: 2px; display: inline-block;">{tag}</span>' for tag in tags_list])
                        st.markdown(tag_html, unsafe_allow_html=True)
                        st.write("")

                    st.write("**Description:**")
                    st.write(achievement['description'])

                    st.write(f"**Date:** {achievement['achievement_date']}")

                    # Action buttons
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

                    with col1:
                        if st.button("📋 Copy", key=f"copy_{achievement['id']}"):
                            st.code(achievement['description'])
                            st.info("Text displayed above - copy manually")

                    with col2:
                        if st.button("✨ Enhance", key=f"enhance_{achievement['id']}"):
                            st.session_state[f'enhance_{achievement["id"]}'] = True

                    with col3:
                        # Delete with confirmation
                        delete_key = f"confirm_delete_achievement_{achievement['id']}"

                        if st.session_state.get(delete_key, False):
                            st.warning(f"⚠️ Delete '{achievement['title']}'?")
                            col_a, col_b = st.columns(2)

                            with col_a:
                                if st.button("✅ Yes", key=f"yes_delete_ach_{achievement['id']}", use_container_width=True):
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('DELETE FROM career_journal WHERE id = ?', (achievement['id'],))
                                        conn.commit()
                                    st.session_state[delete_key] = False
                                    st.success("Achievement deleted!")
                                    st.rerun()

                            with col_b:
                                if st.button("❌ No", key=f"no_delete_ach_{achievement['id']}", use_container_width=True):
                                    st.session_state[delete_key] = False
                                    st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"delete_{achievement['id']}"):
                                st.session_state[delete_key] = True
                                st.rerun()

                    # Show enhanced version if requested
                    if st.session_state.get(f'enhance_{achievement["id"]}', False):
                        with st.spinner("Enhancing achievement with AI..."):
                            try:
                                enhanced = llm_service.enhance_achievement(achievement['description'])
                                st.write("**✨ AI-Enhanced Version:**")
                                st.info(enhanced)

                                if st.button("💾 Update with Enhanced", key=f"update_enhanced_{achievement['id']}"):
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('''
                                            UPDATE career_journal
                                            SET description = ?
                                            WHERE id = ?
                                        ''', (enhanced, achievement['id']))
                                        conn.commit()
                                    st.success("Achievement updated!")
                                    st.session_state[f'enhance_{achievement["id"]}'] = False
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error enhancing achievement: {str(e)}")

        else:
            st.info("No achievements found. Start documenting your wins!")

    except Exception as e:
        st.error(f"Error loading achievements: {str(e)}")

with tab3:
    st.header("Bulk Enhance Achievements")
    st.markdown("Transform your raw achievement notes into polished, impact-focused bullet points")

    raw_achievement = st.text_area(
        "Enter Raw Achievement",
        height=150,
        placeholder="Example:\nWorked on improving the website performance. Made some changes to the database queries and added caching. The site is now faster."
    )

    if st.button("✨ Enhance with AI", type="primary"):
        if raw_achievement:
            with st.spinner("Enhancing your achievement..."):
                try:
                    enhanced = llm_service.enhance_achievement(raw_achievement)

                    st.subheader("Enhanced Achievement")
                    st.success(enhanced)

                    # Options to save
                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("💾 Save to Journal"):
                            # Show form to add title and tags
                            st.session_state['pending_save'] = enhanced

                    with col2:
                        st.download_button(
                            label="📥 Download",
                            data=enhanced,
                            file_name="enhanced_achievement.txt",
                            mime="text/plain"
                        )

                    # Quick save form
                    if st.session_state.get('pending_save'):
                        with st.form("quick_save_form"):
                            st.write("**Save Enhanced Achievement**")
                            title = st.text_input("Title*")
                            achievement_date = st.date_input("Date", value=date.today())
                            tags = st.text_input("Tags (comma-separated)")

                            if st.form_submit_button("Save"):
                                if title:
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('''
                                            INSERT INTO career_journal (profile_id, title, description, achievement_date, tags)
                                            VALUES (?, ?, ?, ?, ?)
                                        ''', (profile['id'], title, st.session_state['pending_save'], achievement_date.isoformat(), tags))
                                        conn.commit()
                                    st.success("✅ Saved to journal!")
                                    del st.session_state['pending_save']
                                    st.rerun()

                except Exception as e:
                    st.error(f"Error enhancing achievement: {str(e)}")
        else:
            st.warning("Please enter an achievement to enhance.")

    # Examples
    with st.expander("💡 See Examples"):
        st.markdown("""
        **Before:**
        > Worked on a project to reduce costs. Changed some cloud services and the company saved money.

        **After:**
        > Spearheaded cloud infrastructure optimization initiative, migrating 15 services to cost-effective alternatives and implementing automated resource scaling, resulting in 35% reduction in monthly AWS costs ($50K annual savings).

        ---

        **Before:**
        > Led a team that built a new feature. Users liked it and adoption was good.

        **After:**
        > Led cross-functional team of 6 engineers to deliver mobile-first payment feature, achieving 80% user adoption within first month and increasing transaction completion rate by 25%.
        """)

# Sidebar tips
with st.sidebar:
    st.header("💡 Achievement Tips")
    st.markdown("""
    **STAR Method:**
    - **S**ituation - Context
    - **T**ask - Challenge
    - **A**ction - What you did
    - **R**esult - Impact/outcome

    **Include:**
    - Specific metrics (%, $, time)
    - Technologies used
    - Team size led
    - Business impact
    - Timeframes

    **Strong Action Verbs:**
    - Led, Spearheaded
    - Implemented, Developed
    - Optimized, Improved
    - Delivered, Achieved
    - Reduced, Increased

    **Tag Suggestions:**
    - Skills: python, aws, react
    - Types: leadership, technical
    - Impact: cost-reduction, efficiency
    - Domain: backend, frontend
    """)
