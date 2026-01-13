import streamlit as st
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.database import get_db_connection
from models.auth_database import init_auth_database
from utils.auth import init_session_state, is_authenticated, get_current_profile, show_auth_sidebar

st.set_page_config(page_title="Resume Templates", page_icon="📋", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("Please log in to access this page")
    st.info("Use the Login page from the sidebar")
    st.stop()

st.title("📋 Resume Templates")
st.markdown("Professional, ATS-friendly resume templates you can customize and download")

profile = get_current_profile()

# Template definitions
TEMPLATES = {
    "Professional Classic": {
        "description": "Traditional format ideal for corporate roles. Clean sections with clear hierarchy.",
        "sections": ["contact", "summary", "experience", "education", "skills"],
        "icon": "📊"
    },
    "Technical Focus": {
        "description": "Emphasizes technical skills and projects. Great for engineering/IT roles.",
        "sections": ["contact", "summary", "skills", "experience", "projects", "education"],
        "icon": "💻"
    },
    "Modern Minimal": {
        "description": "Clean, concise format. Perfect for startups and creative tech companies.",
        "sections": ["contact", "summary", "experience", "skills", "education"],
        "icon": "✨"
    },
    "Career Changer": {
        "description": "Highlights transferable skills and relevant achievements. Good for pivoting careers.",
        "sections": ["contact", "summary", "skills", "experience", "education", "certifications"],
        "icon": "🔄"
    },
    "Entry Level": {
        "description": "Emphasizes education and potential. Ideal for recent graduates.",
        "sections": ["contact", "objective", "education", "skills", "projects", "experience"],
        "icon": "🎓"
    }
}


def generate_template(template_name: str, data: dict) -> str:
    """Generate resume text based on template and user data."""

    lines = []

    # Header - Contact Info
    lines.append("=" * 60)
    lines.append(data.get('name', 'YOUR NAME').upper().center(60))
    lines.append("=" * 60)

    contact_parts = []
    if data.get('email'):
        contact_parts.append(data['email'])
    if data.get('phone'):
        contact_parts.append(data['phone'])
    if data.get('location'):
        contact_parts.append(data['location'])
    if contact_parts:
        lines.append(" | ".join(contact_parts).center(60))

    links = []
    if data.get('linkedin'):
        links.append(f"LinkedIn: {data['linkedin']}")
    if data.get('github'):
        links.append(f"GitHub: {data['github']}")
    if data.get('portfolio'):
        links.append(f"Portfolio: {data['portfolio']}")
    if links:
        lines.append(" | ".join(links).center(60))

    lines.append("")

    template = TEMPLATES[template_name]

    for section in template['sections']:
        if section == 'contact':
            continue  # Already handled above

        elif section == 'summary':
            if data.get('summary'):
                lines.append("PROFESSIONAL SUMMARY")
                lines.append("-" * 60)
                lines.append(data['summary'])
                lines.append("")

        elif section == 'objective':
            if data.get('objective'):
                lines.append("CAREER OBJECTIVE")
                lines.append("-" * 60)
                lines.append(data['objective'])
                lines.append("")

        elif section == 'experience':
            if data.get('experiences'):
                lines.append("PROFESSIONAL EXPERIENCE")
                lines.append("-" * 60)
                for exp in data['experiences']:
                    lines.append(f"{exp.get('title', 'Position')} | {exp.get('company', 'Company')}")
                    lines.append(f"{exp.get('location', '')} | {exp.get('dates', '')}")
                    if exp.get('bullets'):
                        for bullet in exp['bullets']:
                            lines.append(f"  * {bullet}")
                    lines.append("")

        elif section == 'education':
            if data.get('education'):
                lines.append("EDUCATION")
                lines.append("-" * 60)
                for edu in data['education']:
                    lines.append(f"{edu.get('degree', 'Degree')} | {edu.get('school', 'School')}")
                    if edu.get('graduation'):
                        lines.append(f"Graduated: {edu['graduation']}")
                    if edu.get('gpa'):
                        lines.append(f"GPA: {edu['gpa']}")
                    if edu.get('honors'):
                        lines.append(f"Honors: {edu['honors']}")
                    lines.append("")

        elif section == 'skills':
            if data.get('skills'):
                lines.append("SKILLS")
                lines.append("-" * 60)
                if data.get('technical_skills'):
                    lines.append(f"Technical: {data['technical_skills']}")
                if data.get('soft_skills'):
                    lines.append(f"Soft Skills: {data['soft_skills']}")
                if data.get('tools'):
                    lines.append(f"Tools: {data['tools']}")
                if data.get('languages'):
                    lines.append(f"Languages: {data['languages']}")
                lines.append("")

        elif section == 'projects':
            if data.get('projects'):
                lines.append("PROJECTS")
                lines.append("-" * 60)
                for proj in data['projects']:
                    lines.append(f"{proj.get('name', 'Project')} | {proj.get('tech', '')}")
                    if proj.get('description'):
                        lines.append(f"  {proj['description']}")
                    if proj.get('link'):
                        lines.append(f"  Link: {proj['link']}")
                    lines.append("")

        elif section == 'certifications':
            if data.get('certifications'):
                lines.append("CERTIFICATIONS")
                lines.append("-" * 60)
                for cert in data['certifications']:
                    lines.append(f"* {cert}")
                lines.append("")

    return "\n".join(lines)


# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Choose Template", "✏️ Fill Template", "📥 Preview & Download"])

with tab1:
    st.header("Choose a Template")

    cols = st.columns(2)

    for idx, (name, info) in enumerate(TEMPLATES.items()):
        with cols[idx % 2]:
            with st.container():
                st.subheader(f"{info['icon']} {name}")
                st.write(info['description'])
                st.caption(f"Sections: {' → '.join(info['sections'][:5])}")

                if st.button(f"Use This Template", key=f"select_{name}"):
                    st.session_state['selected_template'] = name
                    st.success(f"Selected: {name}")

                st.divider()

    if 'selected_template' in st.session_state:
        st.info(f"Currently selected: **{st.session_state['selected_template']}**")
        st.write("Go to 'Fill Template' tab to enter your information.")

with tab2:
    st.header("Fill in Your Information")

    if 'selected_template' not in st.session_state:
        st.warning("Please select a template first in the 'Choose Template' tab.")
        st.stop()

    template_name = st.session_state['selected_template']
    template = TEMPLATES[template_name]

    st.info(f"Filling template: **{template_name}**")

    # Initialize form data in session state
    if 'resume_data' not in st.session_state:
        st.session_state['resume_data'] = {}

    data = st.session_state['resume_data']

    # Contact Information
    st.subheader("Contact Information")
    col1, col2 = st.columns(2)
    with col1:
        data['name'] = st.text_input("Full Name*", value=data.get('name', profile.get('name', '')))
        data['email'] = st.text_input("Email*", value=data.get('email', profile.get('email', '')))
        data['phone'] = st.text_input("Phone", value=data.get('phone', profile.get('phone', '')))
    with col2:
        data['location'] = st.text_input("Location", value=data.get('location', ''), placeholder="City, State")
        data['linkedin'] = st.text_input("LinkedIn URL", value=data.get('linkedin', profile.get('linkedin', '')))
        data['github'] = st.text_input("GitHub URL", value=data.get('github', profile.get('github', '')))

    data['portfolio'] = st.text_input("Portfolio URL", value=data.get('portfolio', profile.get('portfolio', '')))

    # Summary/Objective
    if 'summary' in template['sections']:
        st.subheader("Professional Summary")
        data['summary'] = st.text_area(
            "Summary (2-3 sentences highlighting your value proposition)",
            value=data.get('summary', ''),
            height=100,
            placeholder="Results-driven software engineer with 5+ years of experience..."
        )

    if 'objective' in template['sections']:
        st.subheader("Career Objective")
        data['objective'] = st.text_area(
            "Objective (your career goal for this role)",
            value=data.get('objective', ''),
            height=100,
            placeholder="Seeking a challenging position where I can leverage my skills..."
        )

    # Experience
    if 'experience' in template['sections']:
        st.subheader("Professional Experience")
        st.caption("Add up to 4 positions")

        if 'experiences' not in data:
            data['experiences'] = [{}]

        num_exp = st.number_input("Number of positions", 1, 4, len(data['experiences']), key="num_exp")

        while len(data['experiences']) < num_exp:
            data['experiences'].append({})
        data['experiences'] = data['experiences'][:num_exp]

        for i in range(num_exp):
            with st.expander(f"Position {i+1}", expanded=(i == 0)):
                exp = data['experiences'][i]
                col1, col2 = st.columns(2)
                with col1:
                    exp['title'] = st.text_input("Job Title", value=exp.get('title', ''), key=f"exp_title_{i}")
                    exp['company'] = st.text_input("Company", value=exp.get('company', ''), key=f"exp_company_{i}")
                with col2:
                    exp['location'] = st.text_input("Location", value=exp.get('location', ''), key=f"exp_loc_{i}")
                    exp['dates'] = st.text_input("Dates", value=exp.get('dates', ''), key=f"exp_dates_{i}",
                                                  placeholder="Jan 2020 - Present")

                bullets_text = st.text_area(
                    "Achievements (one per line, start with action verb)",
                    value="\n".join(exp.get('bullets', [])),
                    height=100,
                    key=f"exp_bullets_{i}",
                    placeholder="Developed feature X resulting in 20% increase in Y\nLed team of 5 engineers..."
                )
                exp['bullets'] = [b.strip() for b in bullets_text.split('\n') if b.strip()]

    # Education
    if 'education' in template['sections']:
        st.subheader("Education")

        if 'education' not in data:
            data['education'] = [{}]

        num_edu = st.number_input("Number of degrees", 1, 3, len(data['education']), key="num_edu")

        while len(data['education']) < num_edu:
            data['education'].append({})
        data['education'] = data['education'][:num_edu]

        for i in range(num_edu):
            with st.expander(f"Education {i+1}", expanded=(i == 0)):
                edu = data['education'][i]
                col1, col2 = st.columns(2)
                with col1:
                    edu['degree'] = st.text_input("Degree", value=edu.get('degree', ''), key=f"edu_degree_{i}",
                                                   placeholder="B.S. Computer Science")
                    edu['school'] = st.text_input("School", value=edu.get('school', ''), key=f"edu_school_{i}")
                with col2:
                    edu['graduation'] = st.text_input("Graduation Date", value=edu.get('graduation', ''), key=f"edu_grad_{i}")
                    edu['gpa'] = st.text_input("GPA (optional)", value=edu.get('gpa', ''), key=f"edu_gpa_{i}")
                edu['honors'] = st.text_input("Honors (optional)", value=edu.get('honors', ''), key=f"edu_honors_{i}")

    # Skills
    if 'skills' in template['sections']:
        st.subheader("Skills")
        data['skills'] = True
        col1, col2 = st.columns(2)
        with col1:
            data['technical_skills'] = st.text_input(
                "Technical Skills",
                value=data.get('technical_skills', ''),
                placeholder="Python, JavaScript, React, SQL, AWS..."
            )
            data['tools'] = st.text_input(
                "Tools & Platforms",
                value=data.get('tools', ''),
                placeholder="Git, Docker, Kubernetes, JIRA..."
            )
        with col2:
            data['soft_skills'] = st.text_input(
                "Soft Skills",
                value=data.get('soft_skills', ''),
                placeholder="Leadership, Communication, Problem-solving..."
            )
            data['languages'] = st.text_input(
                "Languages",
                value=data.get('languages', ''),
                placeholder="English (native), Spanish (conversational)..."
            )

    # Projects
    if 'projects' in template['sections']:
        st.subheader("Projects")

        if 'projects' not in data:
            data['projects'] = [{}]

        num_proj = st.number_input("Number of projects", 1, 4, len(data['projects']), key="num_proj")

        while len(data['projects']) < num_proj:
            data['projects'].append({})
        data['projects'] = data['projects'][:num_proj]

        for i in range(num_proj):
            with st.expander(f"Project {i+1}", expanded=(i == 0)):
                proj = data['projects'][i]
                col1, col2 = st.columns(2)
                with col1:
                    proj['name'] = st.text_input("Project Name", value=proj.get('name', ''), key=f"proj_name_{i}")
                    proj['tech'] = st.text_input("Technologies", value=proj.get('tech', ''), key=f"proj_tech_{i}")
                with col2:
                    proj['link'] = st.text_input("Link (optional)", value=proj.get('link', ''), key=f"proj_link_{i}")
                proj['description'] = st.text_area(
                    "Description",
                    value=proj.get('description', ''),
                    height=80,
                    key=f"proj_desc_{i}"
                )

    # Certifications
    if 'certifications' in template['sections']:
        st.subheader("Certifications")
        certs_text = st.text_area(
            "Certifications (one per line)",
            value="\n".join(data.get('certifications', [])),
            height=100,
            placeholder="AWS Certified Solutions Architect\nGoogle Cloud Professional..."
        )
        data['certifications'] = [c.strip() for c in certs_text.split('\n') if c.strip()]

    # Save to session state
    st.session_state['resume_data'] = data

    if st.button("Save & Preview", type="primary"):
        st.success("Data saved! Go to 'Preview & Download' tab.")

with tab3:
    st.header("Preview & Download")

    if 'selected_template' not in st.session_state:
        st.warning("Please select a template first.")
        st.stop()

    if 'resume_data' not in st.session_state or not st.session_state['resume_data'].get('name'):
        st.warning("Please fill in your information first in the 'Fill Template' tab.")
        st.stop()

    template_name = st.session_state['selected_template']
    data = st.session_state['resume_data']

    # Generate resume
    resume_text = generate_template(template_name, data)

    st.subheader("Preview")
    st.text_area("Resume Preview", value=resume_text, height=500, disabled=True)

    st.subheader("Download Options")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            label="📥 Download as TXT",
            data=resume_text,
            file_name=f"resume_{data.get('name', 'resume').replace(' ', '_').lower()}.txt",
            mime="text/plain"
        )

    with col2:
        # Markdown version
        md_resume = resume_text.replace("=" * 60, "---").replace("-" * 60, "")
        st.download_button(
            label="📥 Download as MD",
            data=md_resume,
            file_name=f"resume_{data.get('name', 'resume').replace(' ', '_').lower()}.md",
            mime="text/markdown"
        )

    with col3:
        # Save to profile
        if st.button("💾 Save to My Resumes"):
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO resumes (profile_id, version_name, content)
                        VALUES (?, ?, ?)
                    ''', (profile['id'], f"{template_name} - {datetime.now().strftime('%Y-%m-%d')}", resume_text))
                    conn.commit()
                st.success("Saved to your resume library!")
            except Exception as e:
                st.error(f"Error saving: {str(e)}")

    # ATS Tips
    st.divider()
    st.subheader("ATS Optimization Tips")
    st.markdown("""
    **This template is ATS-friendly because:**
    - Plain text format parses cleanly
    - Standard section headers recognized by ATS
    - No tables, columns, or graphics that confuse parsers
    - Clear hierarchy with consistent formatting

    **Before submitting:**
    - Customize keywords for each job posting
    - Use exact phrases from job description
    - Verify all dates and company names are accurate
    - Proofread for spelling and grammar
    """)

# Sidebar
with st.sidebar:
    st.header("Template Tips")
    st.markdown("""
    **Choose the right template:**
    - **Professional Classic**: Corporate, finance, consulting
    - **Technical Focus**: Engineering, IT, data science
    - **Modern Minimal**: Startups, tech companies
    - **Career Changer**: Pivoting industries
    - **Entry Level**: Recent graduates

    **Best Practices:**
    - Keep to 1-2 pages
    - Use bullet points, not paragraphs
    - Start bullets with action verbs
    - Include metrics when possible
    - Tailor for each application
    """)
