import os
import sys

import streamlit as st

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.auth_database import init_auth_database
from services.llm_service import get_llm_service
from utils.auth import init_session_state, is_authenticated, show_auth_sidebar

st.set_page_config(page_title="Salary Negotiation", page_icon="💰", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("💰 Salary Negotiation Helper")
st.markdown("Navigate salary discussions with confidence using data and AI-powered strategies")

# Initialize services
llm_service = get_llm_service()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Salary Research", "💬 Negotiation Scripts", "📝 Email Templates", "💡 Tips & Strategies"]
)

with tab1:
    st.header("Salary Research & Analysis")
    st.markdown("Determine your market value and target compensation")

    col1, col2 = st.columns(2)

    with col1:
        position = st.text_input("Position Title", placeholder="e.g., Senior Software Engineer")
        location = st.text_input("Location", placeholder="e.g., San Francisco, CA")
        years_exp = st.number_input("Years of Experience", min_value=0, max_value=50, value=5)

    with col2:
        education = st.selectbox(
            "Education Level", ["High School", "Associate", "Bachelor's", "Master's", "PhD"]
        )
        company_size = st.selectbox(
            "Company Size",
            ["Startup (1-50)", "Small (51-200)", "Medium (201-1000)", "Large (1000+)"],
        )
        industry = st.text_input("Industry", placeholder="e.g., Technology, Finance")

    if st.button("🔍 Get Salary Insights", type="primary"):
        if position and location:
            st.subheader("Salary Research Checklist")

            # Resources to check
            st.markdown(
                """
            **Recommended Salary Resources:**

            1. **Glassdoor** - [glassdoor.com/Salaries](https://www.glassdoor.com/Salaries)
               - Company-specific salaries
               - Interview reviews
               - Employee insights

            2. **Levels.fyi** - [levels.fyi](https://www.levels.fyi)
               - Tech industry focus
               - Detailed compensation breakdowns
               - Stock options and bonuses

            3. **Payscale** - [payscale.com](https://www.payscale.com)
               - Salary reports by job title
               - Location adjustments
               - Skills-based data

            4. **LinkedIn Salary** - [linkedin.com/salary](https://www.linkedin.com/salary)
               - Industry comparisons
               - Career path insights

            5. **Bureau of Labor Statistics** - [bls.gov/oes](https://www.bls.gov/oes)
               - Official government data
               - Regional wage data
            """
            )

            st.markdown("---")

            with st.spinner("Generating personalized insights..."):
                try:
                    from langchain import LLMChain, OpenAI, PromptTemplate

                    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
                    template = """
                    Position: {position}
                    Location: {location}
                    Years of Experience: {years_exp}
                    Education: {education}
                    Company Size: {company_size}
                    Industry: {industry}

                    Based on this information, provide:
                    1. Estimated salary range (be realistic and cite general market trends)
                    2. Key factors that could increase compensation
                    3. Benefits and perks to negotiate beyond base salary
                    4. Questions to ask about compensation package

                    Analysis:
                    """
                    prompt = PromptTemplate(
                        input_variables=[
                            "position",
                            "location",
                            "years_exp",
                            "education",
                            "company_size",
                            "industry",
                        ],
                        template=template,
                    )
                    chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
                    insights = chain.predict(
                        position=position,
                        location=location,
                        years_exp=years_exp,
                        education=education,
                        company_size=company_size,
                        industry=industry,
                    )

                    st.subheader("📊 Personalized Analysis")
                    st.info(insights)

                except Exception as e:
                    st.error(f"Error generating insights: {str(e)}")

        else:
            st.warning("Please provide at least position and location.")

    # Calculator
    st.markdown("---")
    st.subheader("💵 Salary Calculator")

    col1, col2, col3 = st.columns(3)

    with col1:
        base_salary = st.number_input("Base Salary ($)", min_value=0, value=100000, step=5000)

    with col2:
        bonus = st.number_input("Annual Bonus ($)", min_value=0, value=15000, step=1000)

    with col3:
        stock_value = st.number_input(
            "Stock/Equity (Annual Value $)", min_value=0, value=20000, step=5000
        )

    total_comp = base_salary + bonus + stock_value

    st.metric("**Total Annual Compensation**", f"${total_comp:,}")

    # Benefits value
    with st.expander("➕ Add Benefits Value"):
        col1, col2 = st.columns(2)

        with col1:
            health_insurance = st.number_input(
                "Health Insurance Value ($)", min_value=0, value=0, step=500
            )
            retirement_match = st.number_input("401k Match ($)", min_value=0, value=0, step=1000)

        with col2:
            pto_value = st.number_input("PTO/Vacation Value ($)", min_value=0, value=0, step=500)
            other_benefits = st.number_input("Other Benefits ($)", min_value=0, value=0, step=500)

        total_package = (
            total_comp + health_insurance + retirement_match + pto_value + other_benefits
        )
        st.metric("**Total Compensation Package**", f"${total_package:,}")

with tab2:
    st.header("Negotiation Scripts")
    st.markdown("Practice your negotiation conversations with AI-generated scripts")

    scenario = st.selectbox(
        "Negotiation Scenario",
        [
            "Initial Offer - Too Low",
            "Initial Offer - Requesting Higher",
            "Counter Offer",
            "Discussing Benefits",
            "Asking for More Time",
            "Multiple Offers - Leveraging",
            "Internal Promotion/Raise",
            "Custom Scenario",
        ],
    )

    if scenario == "Custom Scenario":
        custom_scenario = st.text_area("Describe your scenario:", height=100)
        scenario_description = custom_scenario
    else:
        scenario_description = scenario

    col1, col2 = st.columns(2)

    with col1:
        current_offer = st.number_input(
            "Current Offer/Salary ($)", min_value=0, value=100000, step=5000
        )

    with col2:
        target_salary = st.number_input("Target Salary ($)", min_value=0, value=120000, step=5000)

    additional_context = st.text_area(
        "Additional Context (Optional)",
        height=100,
        placeholder="e.g., I have another offer at $X, I bring Y years of experience in Z...",
    )

    if st.button("💬 Generate Script", type="primary"):
        with st.spinner("Generating negotiation script..."):
            try:
                from langchain import LLMChain, OpenAI, PromptTemplate

                llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
                template = """
                Scenario: {scenario}
                Current Offer: ${current_offer:,}
                Target Salary: ${target_salary:,}
                Additional Context: {context}

                Create a professional, confident negotiation script for this scenario.
                Include:
                1. Opening statement
                2. Key talking points
                3. Supporting arguments
                4. Closing/next steps

                The tone should be professional, appreciative, and data-driven.

                Negotiation Script:
                """
                prompt = PromptTemplate(
                    input_variables=["scenario", "current_offer", "target_salary", "context"],
                    template=template,
                )
                chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
                script = chain.predict(
                    scenario=scenario_description,
                    current_offer=current_offer,
                    target_salary=target_salary,
                    context=additional_context or "None provided",
                )

                st.subheader("💬 Your Negotiation Script")
                st.success(script)

                st.download_button(
                    label="📥 Download Script",
                    data=script,
                    file_name="negotiation_script.txt",
                    mime="text/plain",
                )

            except Exception as e:
                st.error(f"Error generating script: {str(e)}")

with tab3:
    st.header("Email Templates")
    st.markdown("Professional email templates for salary discussions")

    email_type = st.selectbox(
        "Email Type",
        [
            "Accepting Offer with Negotiation",
            "Counter Offer Email",
            "Declining Offer (Too Low)",
            "Requesting Time to Decide",
            "Thank You After Negotiation",
            "Following Up on Salary Discussion",
        ],
    )

    company_name = st.text_input("Company Name", placeholder="e.g., TechCorp")
    hiring_manager = st.text_input("Hiring Manager Name", placeholder="e.g., Sarah Johnson")

    col1, col2 = st.columns(2)
    with col1:
        current_offer_val = st.number_input(
            "Offer Amount ($)", min_value=0, value=100000, step=5000, key="email_current"
        )
    with col2:
        requested_val = st.number_input(
            "Requested Amount ($)", min_value=0, value=120000, step=5000, key="email_target"
        )

    if st.button("✉️ Generate Email", type="primary"):
        if company_name and hiring_manager:
            with st.spinner("Generating email..."):
                try:
                    from langchain import LLMChain, OpenAI, PromptTemplate

                    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
                    template = """
                    Email Type: {email_type}
                    Company: {company}
                    Hiring Manager: {manager}
                    Current Offer: ${current_offer:,}
                    Requested Amount: ${requested:,}

                    Create a professional email for this situation.
                    Include:
                    - Subject line
                    - Proper greeting and closing
                    - Professional, grateful tone
                    - Clear, specific request
                    - Justification for request

                    Email:
                    """
                    prompt = PromptTemplate(
                        input_variables=[
                            "email_type",
                            "company",
                            "manager",
                            "current_offer",
                            "requested",
                        ],
                        template=template,
                    )
                    chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
                    email = chain.predict(
                        email_type=email_type,
                        company=company_name,
                        manager=hiring_manager,
                        current_offer=current_offer_val,
                        requested=requested_val,
                    )

                    st.subheader("✉️ Your Email")
                    st.code(email, language=None)

                    st.download_button(
                        label="📥 Download Email",
                        data=email,
                        file_name=f"salary_email_{email_type.lower().replace(' ', '_')}.txt",
                        mime="text/plain",
                    )

                except Exception as e:
                    st.error(f"Error generating email: {str(e)}")
        else:
            st.warning("Please provide company name and hiring manager name.")

with tab4:
    st.header("Negotiation Tips & Strategies")

    # Key principles
    st.subheader("🎯 Key Principles")
    st.markdown(
        """
    1. **Do Your Research** - Know the market rate for your position and location
    2. **Know Your Worth** - Quantify your value with specific achievements
    3. **Never Accept the First Offer** - Companies expect negotiation
    4. **Be Professional** - Stay positive and collaborative
    5. **Think Total Compensation** - Consider benefits, equity, bonuses, etc.
    6. **Get it in Writing** - Verbal offers aren't binding
    7. **Be Prepared to Walk Away** - But only if you mean it
    """
    )

    # Timing
    st.subheader("⏰ Timing Matters")
    st.markdown(
        """
    **When to Negotiate:**
    - ✅ After receiving a written offer
    - ✅ Before accepting the offer
    - ✅ After demonstrating your value
    - ✅ During annual review cycles
    - ✅ When taking on new responsibilities

    **When NOT to Negotiate:**
    - ❌ During the first interview
    - ❌ Before receiving an offer
    - ❌ When you haven't researched market rates
    - ❌ If you're desperate for the job (they can sense it)
    """
    )

    # What to negotiate
    st.subheader("💼 What to Negotiate Beyond Salary")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
        **Compensation:**
        - Base salary
        - Signing bonus
        - Performance bonuses
        - Stock options/RSUs
        - Profit sharing

        **Time Off:**
        - Vacation days
        - Sick leave
        - Parental leave
        - Sabbaticals
        - Flexible schedule
        """
        )

    with col2:
        st.markdown(
            """
        **Benefits:**
        - Health insurance
        - 401k match
        - Education/training budget
        - Conference attendance
        - Gym membership
        - Relocation assistance

        **Work Arrangements:**
        - Remote work options
        - Flexible hours
        - Equipment budget
        - Home office setup
        """
        )

    # Common mistakes
    st.subheader("⚠️ Common Mistakes to Avoid")
    st.markdown(
        """
    1. **Sharing salary history** - Focus on market value, not past pay
    2. **Giving a specific number first** - Let them make the first offer
    3. **Accepting immediately** - Take time to review and consider
    4. **Being aggressive or demanding** - Stay collaborative
    5. **Making it personal** - Keep it professional and data-driven
    6. **Forgetting to negotiate benefits** - Total comp matters
    7. **Not getting the offer in writing** - Always get it documented
    """
    )

    # Scripts for common situations
    st.subheader("💬 Quick Response Templates")

    with st.expander('"What are your salary expectations?"'):
        st.markdown(
            """
        **Option 1 (Deflect):**
        > "I'd prefer to learn more about the role and responsibilities first. Could you share the budgeted range for this position?"

        **Option 2 (Range):**
        > "Based on my research and experience, I'm targeting roles in the $X-Y range, but I'm open to discussion based on the full compensation package."

        **Option 3 (Flexible):**
        > "I'm focused on finding the right fit. If this role is a match, I'm confident we can agree on fair compensation."
        """
        )

    with st.expander('"What\'s your current salary?"'):
        st.markdown(
            """
        **Option 1 (Deflect):**
        > "I prefer to focus on the value I can bring to this role rather than my current compensation. What's the budgeted range?"

        **Option 2 (Broader Context):**
        > "My total compensation includes various components. I'm more interested in discussing what this role offers."

        **Option 3 (Polite Redirect):**
        > "I'd rather not share that, as I'm looking for a position that aligns with my current market value and the responsibilities of this role."
        """
        )

    with st.expander("Offer is lower than expected"):
        st.markdown(
            """
        **Response Template:**
        > "Thank you so much for the offer! I'm excited about the opportunity to join [Company]. Based on my research of market rates for this role and my X years of experience in [specific skills], I was expecting a base salary in the range of $X-Y. Is there flexibility in the offer?"

        **Follow-up if they say no:**
        > "I understand. Would it be possible to explore other components of the compensation package, such as signing bonus, additional equity, or performance-based increases?"
        """
        )

# Sidebar
with st.sidebar:
    st.header("💡 Quick Tips")
    st.markdown(
        """
    **Golden Rules:**
    1. Always negotiate
    2. Be data-driven
    3. Stay professional
    4. Know your minimum
    5. Get it in writing

    **Power Phrases:**
    - "Based on my research..."
    - "Given my experience..."
    - "I'm confident we can find..."
    - "What's the budgeted range?"
    - "Can we explore options?"

    **Red Flags:**
    - Pressure to decide quickly
    - Unwillingness to negotiate
    - Vague compensation details
    - No written offer
    """
    )
