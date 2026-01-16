import os
import sys

import streamlit as st

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.auth_database import init_auth_database
from models.database import get_db_connection
from services.llm_service import get_llm_service
from utils.auth import get_current_profile, init_session_state, is_authenticated, show_auth_sidebar
from utils.rate_limiter import check_rate_limit

st.set_page_config(page_title="Email Templates", page_icon="📧", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("Please log in to access this page")
    st.info("Use the Login page from the sidebar")
    st.stop()

st.title("📧 Email Templates")
st.markdown("Professional email templates for your job search communication")

profile = get_current_profile()

# Pre-built templates
EMAIL_TEMPLATES = {
    "Thank You - After Interview": {
        "subject": "Thank You - {position} Interview",
        "body": """Dear {interviewer_name},

Thank you for taking the time to speak with me today about the {position} role at {company}. I enjoyed learning more about the team and the exciting projects you're working on.

Our conversation reinforced my enthusiasm for this opportunity. I was particularly excited to hear about {specific_topic}. My experience with {relevant_experience} aligns well with the challenges you mentioned.

I'm very interested in contributing to {company}'s success and would welcome the opportunity to discuss how my skills can benefit your team.

Please don't hesitate to reach out if you need any additional information from me.

Best regards,
{your_name}""",
    },
    "Thank You - After Phone Screen": {
        "subject": "Thank You - {position} Phone Screen",
        "body": """Dear {interviewer_name},

Thank you for speaking with me today about the {position} position at {company}. I appreciated the opportunity to learn more about the role and the team.

After our conversation, I'm even more excited about the possibility of joining {company}. The {specific_aspect} you described aligns perfectly with my background and career goals.

I look forward to the next steps in the process. Please let me know if there's any additional information I can provide.

Best regards,
{your_name}""",
    },
    "Follow Up - After No Response": {
        "subject": "Following Up - {position} Application",
        "body": """Dear {hiring_manager_name},

I hope this email finds you well. I wanted to follow up on my application for the {position} role at {company}, which I submitted on {application_date}.

I remain very interested in this opportunity and believe my experience in {relevant_skills} would make me a strong contributor to your team.

I understand you're likely reviewing many qualified candidates, and I appreciate your time and consideration. If you need any additional materials or have questions about my background, please don't hesitate to reach out.

Thank you for your time, and I look forward to hearing from you.

Best regards,
{your_name}""",
    },
    "Follow Up - After Interview": {
        "subject": "Following Up - {position} Interview",
        "body": """Dear {interviewer_name},

I hope you're doing well. I wanted to follow up on our interview for the {position} position on {interview_date}.

I continue to be very enthusiastic about the opportunity to join {company} and contribute to the team. Our discussion about {specific_topic} was particularly exciting, and I've been thinking about how my experience could address the challenges we discussed.

I would be grateful for any update you might have on the timeline for next steps. Please let me know if there's any additional information I can provide.

Thank you again for your time and consideration.

Best regards,
{your_name}""",
    },
    "Networking - Cold Outreach": {
        "subject": "Connecting About Opportunities at {company}",
        "body": """Dear {recipient_name},

I came across your profile while researching {company} and was impressed by your background in {their_area}. I'm currently exploring opportunities in {your_field} and would love to learn more about your experience at {company}.

I'm particularly interested in {specific_interest} and would greatly appreciate any insights you might be willing to share about the company culture, team dynamics, or advice for someone looking to join {company}.

Would you be available for a brief 15-20 minute call or coffee chat in the coming weeks? I completely understand if your schedule doesn't permit, but I'd be grateful for any time you could spare.

Thank you for considering my request.

Best regards,
{your_name}
{your_linkedin}""",
    },
    "Networking - Warm Introduction": {
        "subject": "Introduction from {mutual_connection}",
        "body": """Dear {recipient_name},

{mutual_connection} suggested I reach out to you regarding opportunities at {company}. They spoke highly of your expertise in {their_area} and thought we might have a valuable conversation.

I'm currently a {your_role} with experience in {your_skills}, and I'm very interested in learning more about {company}'s work in {area_of_interest}.

I would love the opportunity to chat briefly about your experience and any advice you might have. Would you be available for a quick 15-minute call sometime in the next few weeks?

Thank you for your time, and I look forward to connecting.

Best regards,
{your_name}""",
    },
    "Salary Negotiation - Counter Offer": {
        "subject": "Re: {position} Offer - Discussion",
        "body": """Dear {hiring_manager_name},

Thank you so much for extending the offer for the {position} role at {company}. I'm very excited about the opportunity to join your team and contribute to {company}'s mission.

After careful consideration, I'd like to discuss the compensation package. Based on my research of market rates for similar positions and my {years} years of experience in {field}, I was hoping we could explore a base salary of {target_salary}.

I believe this reflects the value I'll bring to the team, particularly given my expertise in {key_skills} and track record of {achievement}.

I'm flexible and open to discussing creative solutions that work for both sides, such as sign-on bonuses, additional equity, or accelerated review timelines.

I'm very committed to joining {company} and look forward to finding a package that works for both of us.

Best regards,
{your_name}""",
    },
    "Accepting Offer": {
        "subject": "Offer Acceptance - {position}",
        "body": """Dear {hiring_manager_name},

I am thrilled to formally accept the offer for the {position} position at {company}. Thank you for this incredible opportunity.

As discussed, I understand my starting salary will be {salary}, and my start date will be {start_date}. I've reviewed the offer letter and am prepared to sign and return all necessary documents.

I'm genuinely excited to join the team and contribute to {company}'s continued success. Please let me know if there's anything I should prepare or complete before my start date.

Thank you again for this opportunity. I look forward to working with everyone.

Best regards,
{your_name}""",
    },
    "Declining Offer - Gracefully": {
        "subject": "Re: {position} Offer",
        "body": """Dear {hiring_manager_name},

Thank you so much for offering me the {position} role at {company}. I truly appreciate the time you and the team invested in the interview process, and I was impressed by everyone I met.

After careful consideration, I have decided to accept another opportunity that more closely aligns with my career goals at this time. This was a difficult decision, as I genuinely enjoyed learning about {company}'s work and team.

I hope our paths cross again in the future, and I wish you and the team continued success.

Thank you again for your time and consideration.

Best regards,
{your_name}""",
    },
    "Withdrawal - From Process": {
        "subject": "Withdrawing Application - {position}",
        "body": """Dear {recruiter_name},

I hope this email finds you well. I wanted to reach out regarding my application for the {position} role at {company}.

After careful consideration, I have decided to withdraw my application from the interview process. I have accepted another opportunity that aligns with my immediate career objectives.

I want to express my sincere gratitude for the time you and the team have invested in considering my candidacy. I was genuinely impressed by {company} and everyone I interacted with during the process.

I hope we might have the opportunity to connect again in the future.

Best regards,
{your_name}""",
    },
}

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Template Library", "🤖 AI Generator", "📝 Custom Email"])

with tab1:
    st.header("Email Template Library")
    st.markdown("Select a template, customize the placeholders, and copy your email")

    # Category filter
    categories = ["All", "Thank You", "Follow Up", "Networking", "Negotiation", "Other"]
    selected_category = st.selectbox("Filter by Category", categories)

    # Filter templates
    filtered_templates = {}
    for name, template in EMAIL_TEMPLATES.items():
        if selected_category == "All":
            filtered_templates[name] = template
        elif selected_category in name:
            filtered_templates[name] = template
        elif selected_category == "Negotiation" and ("Salary" in name or "Offer" in name):
            filtered_templates[name] = template
        elif selected_category == "Other" and not any(
            cat in name for cat in ["Thank You", "Follow Up", "Networking", "Salary"]
        ):
            filtered_templates[name] = template

    # Display templates
    selected_template = st.selectbox("Select Template", list(filtered_templates.keys()))

    if selected_template:
        template = filtered_templates[selected_template]

        st.subheader("Subject Line")
        st.code(template["subject"])

        st.subheader("Email Body")
        st.text_area("Template Preview", value=template["body"], height=300, disabled=True)

        st.divider()
        st.subheader("Customize Your Email")

        # Extract placeholders
        import re

        placeholders = set(re.findall(r"\{(\w+)\}", template["subject"] + template["body"]))

        # Pre-fill with profile data where applicable
        placeholder_mapping = {
            "your_name": profile.get("name", ""),
            "your_linkedin": profile.get("linkedin", ""),
            "your_email": profile.get("email", ""),
        }

        col1, col2 = st.columns(2)
        values = {}

        placeholder_list = sorted(list(placeholders))
        for i, placeholder in enumerate(placeholder_list):
            with col1 if i % 2 == 0 else col2:
                display_name = placeholder.replace("_", " ").title()
                default_value = placeholder_mapping.get(placeholder, "")
                values[placeholder] = st.text_input(
                    display_name, value=default_value, key=f"ph_{placeholder}"
                )

        # Generate customized email
        if st.button("Generate Email", type="primary"):
            customized_subject = template["subject"]
            customized_body = template["body"]

            for key, value in values.items():
                customized_subject = customized_subject.replace(f"{{{key}}}", value or f"[{key}]")
                customized_body = customized_body.replace(f"{{{key}}}", value or f"[{key}]")

            st.subheader("Your Customized Email")
            st.text_input("Subject", value=customized_subject, key="final_subject")
            final_email = st.text_area("Body", value=customized_body, height=300, key="final_body")

            # Copy button simulation
            full_email = f"Subject: {customized_subject}\n\n{customized_body}"
            st.download_button(
                "📋 Download Email",
                data=full_email,
                file_name=f"email_{selected_template.lower().replace(' ', '_')}.txt",
                mime="text/plain",
            )

with tab2:
    st.header("AI Email Generator")
    st.markdown("Generate personalized emails using AI")

    email_type = st.selectbox(
        "What type of email do you need?",
        [
            "Networking - Informational Interview Request",
            "Networking - Job Inquiry",
            "Thank You - Post Interview",
            "Follow Up - Application Status",
            "Custom Request",
        ],
    )

    col1, col2 = st.columns(2)

    with col1:
        recipient_name = st.text_input("Recipient Name*", placeholder="e.g., Jane Smith")
        company_name = st.text_input("Company Name*", placeholder="e.g., Google")

    with col2:
        position = st.text_input("Position (if applicable)", placeholder="e.g., Software Engineer")
        your_background = st.text_area(
            "Your Background (brief)",
            height=100,
            placeholder="e.g., 5 years as a backend developer, expertise in Python and cloud systems...",
        )

    additional_context = st.text_area(
        "Additional Context",
        height=100,
        placeholder="Any specific details you want included in the email...",
    )

    if st.button("Generate AI Email", type="primary"):
        if not recipient_name or not company_name:
            st.warning("Please fill in recipient name and company name")
            st.stop()

        if not check_rate_limit(max_requests=10, window_seconds=60):
            st.stop()

        with st.spinner("Generating personalized email..."):
            try:
                llm_service = get_llm_service()

                # Determine purpose based on email type
                if "Networking" in email_type:
                    purpose = (
                        "informational interview"
                        if "Informational" in email_type
                        else "job inquiry"
                    )
                    email = llm_service.generate_networking_email(
                        recipient_name=recipient_name,
                        company_name=company_name,
                        purpose=f"{purpose} for {position}" if position else purpose,
                        user_background=your_background,
                    )
                else:
                    # Use a custom prompt for other types
                    from services.llm_service import LLMService

                    service = get_llm_service()

                    prompt = f"""Generate a professional {email_type} email with the following details:
                    - Recipient: {recipient_name}
                    - Company: {company_name}
                    - Position: {position or 'N/A'}
                    - My Background: {your_background or 'Not provided'}
                    - Additional Context: {additional_context or 'None'}
                    - My Name: {profile.get('name', 'Job Seeker')}

                    Generate a concise, professional email with subject line. Keep it under 200 words."""

                    email = service._invoke_chain(prompt + "\n\nGenerated Email:")

                st.subheader("Generated Email")
                st.text_area("Your AI-Generated Email", value=email, height=300)

                st.download_button(
                    "📋 Download Email",
                    data=email,
                    file_name="ai_generated_email.txt",
                    mime="text/plain",
                )

            except Exception as e:
                st.error(f"Error generating email: {str(e)}")
                st.info("Make sure your OPENAI_API_KEY is configured")

with tab3:
    st.header("Custom Email Composer")
    st.markdown("Write and save your own email templates")

    st.subheader("Compose Email")

    custom_subject = st.text_input("Subject Line", placeholder="Your email subject...")
    custom_body = st.text_area(
        "Email Body",
        height=300,
        placeholder="Write your email here...\n\nTip: Use {placeholder} syntax for reusable fields like {company} or {position}",
    )

    col1, col2 = st.columns(2)

    with col1:
        if custom_subject and custom_body:
            full_email = f"Subject: {custom_subject}\n\n{custom_body}"
            st.download_button(
                "📋 Download Email",
                data=full_email,
                file_name="custom_email.txt",
                mime="text/plain",
            )

    st.divider()

    st.subheader("Email Writing Tips")
    st.markdown(
        """
    **Structure:**
    1. **Opening**: Personalized greeting with context
    2. **Purpose**: Clear reason for the email
    3. **Value**: What you offer or why they should respond
    4. **Call to Action**: Specific next step
    5. **Closing**: Professional sign-off

    **Best Practices:**
    - Keep it under 200 words
    - Use the recipient's name
    - Be specific about what you want
    - Make it easy to respond (suggest times, ask yes/no questions)
    - Proofread before sending
    """
    )

# Sidebar
with st.sidebar:
    st.header("Email Tips")
    st.markdown(
        """
    **Subject Lines:**
    - Be specific and clear
    - Include role/company name
    - Keep under 50 characters

    **Timing:**
    - Thank you: Within 24 hours
    - Follow-up: 1 week after
    - Second follow-up: 2 weeks

    **Tone:**
    - Professional but warm
    - Confident, not desperate
    - Grateful, not entitled

    **Common Mistakes:**
    - Too long (aim for <200 words)
    - Generic (personalize!)
    - No clear ask
    - Typos/wrong names
    """
    )
