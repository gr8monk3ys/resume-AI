import os
import sys

import streamlit as st

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.auth_database import init_auth_database
from models.database import get_db_connection
from services.llm_service import get_llm_service
from utils.auth import get_current_profile, init_session_state, is_authenticated, show_auth_sidebar

st.set_page_config(page_title="Interview Prep", page_icon="🎯", layout="wide")

# Initialize auth
init_auth_database()
init_session_state()
show_auth_sidebar()

# Require authentication
if not is_authenticated():
    st.warning("⚠️ Please log in to access this page")
    st.info("👉 Use the Login page from the sidebar")
    st.stop()

st.title("🎯 Interview Preparation")
st.markdown("Prepare for your interviews with AI-powered practice and common questions")

# Initialize services
llm_service = get_llm_service()
profile = get_current_profile()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["📝 Question Bank", "🤖 AI Practice", "💡 STAR Stories", "📊 Company Research"]
)

with tab1:
    st.header("Common Interview Questions")
    st.markdown("Browse and prepare answers for frequently asked interview questions")

    # Question categories
    question_bank = {
        "Behavioral": [
            "Tell me about yourself.",
            "What are your greatest strengths?",
            "What are your weaknesses?",
            "Why do you want to work here?",
            "Where do you see yourself in 5 years?",
            "Tell me about a time you failed.",
            "Describe a time you showed leadership.",
            "How do you handle conflict in a team?",
            "Tell me about a challenging project.",
            "Why are you leaving your current job?",
        ],
        "Technical": [
            "Explain [specific technology] and when you'd use it.",
            "How would you design [system/feature]?",
            "What's your approach to debugging?",
            "Explain the difference between [concept A] and [concept B].",
            "Walk me through a recent technical problem you solved.",
            "How do you stay current with technology trends?",
            "What's your experience with [specific tool/framework]?",
            "How do you ensure code quality?",
            "Describe your development workflow.",
            "What testing strategies do you use?",
        ],
        "Leadership": [
            "Describe your management style.",
            "How do you motivate a team?",
            "Tell me about a time you had to make a difficult decision.",
            "How do you handle underperforming team members?",
            "Describe a time you influenced without authority.",
            "How do you prioritize competing projects?",
            "Tell me about a time you disagreed with a manager.",
            "How do you build team culture?",
            "Describe your approach to mentoring.",
            "How do you handle team conflicts?",
        ],
        "Problem-Solving": [
            "How would you approach [hypothetical scenario]?",
            "Tell me about a creative solution you developed.",
            "How do you make decisions with incomplete information?",
            "Describe a time you had to learn something quickly.",
            "How do you handle tight deadlines?",
            "Tell me about a time you improved a process.",
            "How do you prioritize your work?",
            "Describe a situation where you had to adapt quickly.",
            "How do you handle ambiguity?",
            "Tell me about a complex problem you solved.",
        ],
        "Questions to Ask": [
            "What does success look like in this role?",
            "What are the biggest challenges facing the team?",
            "How do you measure performance?",
            "What's the team culture like?",
            "What opportunities are there for growth?",
            "What's the onboarding process?",
            "How does the company support professional development?",
            "What are the next steps in the process?",
            "What do you enjoy most about working here?",
            "How has the company/team evolved recently?",
        ],
    }

    category = st.selectbox("Select Category", list(question_bank.keys()))

    st.subheader(f"{category} Questions")

    for idx, question in enumerate(question_bank[category], 1):
        with st.expander(f"{idx}. {question}"):
            # User's answer
            answer_key = f"answer_{category}_{idx}"

            st.text_area(
                "Your Answer", key=answer_key, height=150, placeholder="Write your answer here..."
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💡 Get Tips", key=f"tips_{category}_{idx}"):
                    with st.spinner("Generating tips..."):
                        try:
                            from langchain.chains import LLMChain
                            from langchain.prompts import PromptTemplate
                            from langchain_community.llms import OpenAI

                            llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
                            template = """
                            Interview Question: {question}

                            Provide 3-5 concise tips for answering this question effectively.
                            Focus on what interviewers are looking for and key points to include.

                            Tips:
                            """
                            prompt = PromptTemplate(input_variables=["question"], template=template)
                            chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
                            tips = chain.predict(question=question)

                            st.info(tips)

                        except Exception as e:
                            st.error(f"Error generating tips: {str(e)}")

            with col2:
                if st.button("✨ Get Example", key=f"example_{category}_{idx}"):
                    with st.spinner("Generating example answer..."):
                        try:
                            from langchain.chains import LLMChain
                            from langchain.prompts import PromptTemplate
                            from langchain_community.llms import OpenAI

                            llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
                            template = """
                            Interview Question: {question}

                            Provide a strong example answer to this question.
                            Use the STAR method if applicable (Situation, Task, Action, Result).
                            Keep it concise and impactful.

                            Example Answer:
                            """
                            prompt = PromptTemplate(input_variables=["question"], template=template)
                            chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
                            example = chain.predict(question=question)

                            st.success(example)

                        except Exception as e:
                            st.error(f"Error generating example: {str(e)}")

with tab2:
    st.header("AI Interview Practice")
    st.markdown("Practice answering questions and get AI-powered feedback")

    practice_type = st.selectbox(
        "Interview Type", ["General Behavioral", "Technical", "Leadership", "Custom Question"]
    )

    if practice_type == "Custom Question":
        custom_question = st.text_input("Enter your question:")
        question_to_practice = custom_question
    else:
        # Get a random question from the category
        if practice_type == "General Behavioral":
            questions = question_bank["Behavioral"]
        elif practice_type == "Technical":
            questions = question_bank["Technical"]
        else:
            questions = question_bank["Leadership"]

        question_to_practice = st.selectbox("Select a question:", questions)

    st.subheader("Question")
    st.info(question_to_practice)

    your_answer = st.text_area(
        "Your Answer", height=200, placeholder="Type your answer as if you were in an interview..."
    )

    if st.button("🎯 Get Feedback", type="primary"):
        if your_answer and question_to_practice:
            with st.spinner("Analyzing your answer..."):
                try:
                    from langchain.chains import LLMChain
                    from langchain.prompts import PromptTemplate
                    from langchain_community.llms import OpenAI

                    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
                    template = """
                    Interview Question: {question}

                    Candidate's Answer: {answer}

                    As an expert interview coach, provide constructive feedback on this answer:

                    1. **Strengths** - What was done well
                    2. **Areas for Improvement** - Specific suggestions
                    3. **Structure** - How to better organize the response
                    4. **Impact** - How to make it more compelling
                    5. **Score** - Rate the answer out of 10 with justification

                    Feedback:
                    """
                    prompt = PromptTemplate(
                        input_variables=["question", "answer"], template=template
                    )
                    chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
                    feedback = chain.predict(question=question_to_practice, answer=your_answer)

                    st.subheader("📊 Feedback")
                    st.write(feedback)

                except Exception as e:
                    st.error(f"Error generating feedback: {str(e)}")
        else:
            st.warning("Please provide both a question and your answer.")

with tab3:
    st.header("STAR Story Builder")
    st.markdown("Build compelling stories using the STAR (Situation, Task, Action, Result) method")

    st.info(
        """
    **STAR Method:**
    - **S**ituation: Set the context
    - **T**ask: Describe the challenge
    - **A**ction: Explain what you did
    - **R**esult: Share the outcome and impact
    """
    )

    # Option to import from career journal
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Create a STAR Story")

    with col2:
        if st.button("📓 Import from Journal"):
            st.session_state["show_journal_import"] = True

    # Show journal import
    if st.session_state.get("show_journal_import", False):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, description
                    FROM career_journal
                    WHERE profile_id = ?
                    ORDER BY achievement_date DESC
                """,
                    (profile["id"],),
                )
                achievements = cursor.fetchall()

            if achievements:
                selected = st.selectbox(
                    "Select Achievement",
                    [(a["id"], a["title"]) for a in achievements],
                    format_func=lambda x: x[1],
                )

                if st.button("Load"):
                    selected_achievement = next(a for a in achievements if a["id"] == selected[0])
                    st.session_state["star_description"] = selected_achievement["description"]
                    st.session_state["show_journal_import"] = False
                    st.rerun()
            else:
                st.info("No journal entries found")

        except Exception as e:
            st.error(f"Error loading journal: {str(e)}")

    # STAR form
    with st.form("star_form"):
        situation = st.text_area(
            "**Situation** - What was the context?",
            value=st.session_state.get("star_situation", ""),
            height=100,
            placeholder="Example: Our company's mobile app was experiencing high crash rates (15%) causing user frustration...",
        )

        task = st.text_area(
            "**Task** - What was your responsibility?",
            value=st.session_state.get("star_task", ""),
            height=100,
            placeholder="Example: I was tasked with identifying the root cause and reducing crash rates to under 2% within one month...",
        )

        action = st.text_area(
            "**Action** - What did you do?",
            value=st.session_state.get("star_action", ""),
            height=150,
            placeholder="Example: I analyzed crash logs, identified 3 critical bugs in the payment module, implemented fixes, added comprehensive error handling, and set up automated testing...",
        )

        result = st.text_area(
            "**Result** - What was the outcome?",
            value=st.session_state.get("star_result", ""),
            height=100,
            placeholder="Example: Reduced crash rate to 1.5%, improved app store rating from 3.8 to 4.5 stars, increased user retention by 25%...",
        )

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("✨ Generate Story", type="primary")

        with col2:
            clear = st.form_submit_button("🗑️ Clear")

        if clear:
            for key in ["star_situation", "star_task", "star_action", "star_result"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        if submitted:
            if situation and task and action and result:
                combined = f"Situation: {situation}\n\nTask: {task}\n\nAction: {action}\n\nResult: {result}"

                with st.spinner("Crafting your story..."):
                    try:
                        from langchain.chains import LLMChain
                        from langchain.prompts import PromptTemplate
                        from langchain_community.llms import OpenAI

                        llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
                        template = """
                        Based on the following STAR components, create a polished, concise story suitable for an interview:

                        {star_components}

                        Create a compelling narrative that:
                        1. Flows naturally
                        2. Highlights impact with specific metrics
                        3. Is concise (2-3 sentences per section)
                        4. Uses strong action verbs

                        Polished Story:
                        """
                        prompt = PromptTemplate(
                            input_variables=["star_components"], template=template
                        )
                        chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
                        polished_story = chain.predict(star_components=combined)

                        st.subheader("✨ Your Polished Story")
                        st.success(polished_story)

                        st.download_button(
                            label="📥 Download Story",
                            data=polished_story,
                            file_name="star_story.txt",
                            mime="text/plain",
                        )

                    except Exception as e:
                        st.error(f"Error generating story: {str(e)}")
            else:
                st.warning("Please fill in all STAR components.")

with tab4:
    st.header("Company Research Helper")
    st.markdown("Get insights and talking points for your target company")

    company_name = st.text_input("Company Name", placeholder="e.g., Google")
    position = st.text_input("Position", placeholder="e.g., Software Engineer")

    if st.button("🔍 Generate Research Questions", type="primary"):
        if company_name:
            st.subheader("Key Research Areas")

            research_areas = {
                "Company Background": [
                    f"What is {company_name}'s mission and values?",
                    f"What are {company_name}'s main products/services?",
                    f"Who are {company_name}'s main competitors?",
                    f"What's {company_name}'s market position?",
                ],
                "Recent News": [
                    f"What are recent news articles about {company_name}?",
                    f"What new products has {company_name} launched recently?",
                    f"What challenges is {company_name} facing?",
                    f"What are {company_name}'s growth areas?",
                ],
                "Culture & People": [
                    f"What is the culture like at {company_name}?",
                    f"What do employees say about working at {company_name}?",
                    f"What are the company's diversity initiatives?",
                    f"What's the work-life balance like?",
                ],
                "Technical Insights": [
                    f"What technologies does {company_name} use?",
                    f"What's {company_name}'s tech stack?",
                    f"What engineering blogs or talks has {company_name} published?",
                    f"What's innovative about {company_name}'s technical approach?",
                ],
            }

            for area, questions in research_areas.items():
                with st.expander(f"📌 {area}"):
                    for q in questions:
                        st.write(f"• {q}")

            st.markdown("---")
            st.subheader("💡 Conversation Starters")

            with st.spinner("Generating talking points..."):
                try:
                    from langchain.chains import LLMChain
                    from langchain.prompts import PromptTemplate
                    from langchain_community.llms import OpenAI

                    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
                    template = """
                    Company: {company}
                    Position: {position}

                    Generate 5 insightful talking points or questions to bring up during an interview.
                    These should demonstrate genuine interest and research about the company.

                    Talking Points:
                    """
                    prompt = PromptTemplate(
                        input_variables=["company", "position"], template=template
                    )
                    chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
                    talking_points = chain.predict(
                        company=company_name, position=position or "the position"
                    )

                    st.info(talking_points)

                except Exception as e:
                    st.error(f"Error generating talking points: {str(e)}")

        else:
            st.warning("Please enter a company name.")

# Sidebar
with st.sidebar:
    st.header("💡 Interview Tips")
    st.markdown(
        """
    **Before:**
    - Research the company
    - Review your resume
    - Prepare STAR stories
    - Prepare questions to ask
    - Practice out loud

    **During:**
    - Listen carefully
    - Take a moment to think
    - Be specific and concise
    - Use the STAR method
    - Show enthusiasm
    - Ask clarifying questions

    **After:**
    - Send thank-you email within 24h
    - Note what went well
    - Note areas to improve
    - Follow up appropriately
    """
    )
