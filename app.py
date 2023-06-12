import os
import openai
import streamlit as st
from dotenv import load_dotenv
from langchain import OpenAI, LLMChain, PromptTemplate

def load_documents():
    resume_file = st.file_uploader("Upload Resume", type=['txt'])
    job_description_file = st.file_uploader("Upload Job Description", type=['txt'])

    if resume_file and job_description_file:
        resume_text = resume_file.getvalue().decode()
        job_description_text = job_description_file.getvalue().decode()
        return resume_text, job_description_text
    else:
        return None, None


def correct_resume(resume):
    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.9)
    template = """
    {resume}

    You are an expert proofreader. Please correct any grammatical errors in the text above.
    """
    prompt_template = PromptTemplate(input_variables=["resume"], template=template)
    correction_chain = LLMChain(llm=llm, prompt=prompt_template, verbose=True)
    corrected_resume = correction_chain.predict(resume=resume)
    return corrected_resume


def compare_and_update_resume(resume, job_description):
    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.9)
    template = """
    Job Description:
    {job_description}

    Resume:
    {resume}

    As a career advisor, please identify any key skills or qualifications in the job description that are not mentioned in the resume, and suggest how to include them in the resume.
    """
    prompt_template = PromptTemplate(input_variables=["job_description", "resume"], template=template)
    resume_updater_chain = LLMChain(llm=llm, prompt=prompt_template, verbose=True)
    updated_resume = resume_updater_chain.predict(job_description=job_description, resume=resume)
    return updated_resume


def main():
    load_dotenv()

    openai.api_key = os.getenv("OPENAI_API_KEY")

    st.set_page_config(page_title="Resume Corrector and Updater", page_icon="📄")

    st.header("Resume Corrector and Updater 📄")

    resume, job_description = load_documents()

    if resume and job_description:
        try:
            st.write("Correcting resume...")
            corrected_resume = correct_resume(resume)
            st.write("Updating resume...")
            updated_resume = compare_and_update_resume(corrected_resume, job_description)
            st.write("Updated Resume:")
            st.text_area("", value=updated_resume, height=400)
            st.download_button(label="Download Updated Resume", data=updated_resume, file_name="updated_resume.txt")
        except Exception as e:
            st.write("An error occurred while processing the resume. Please try again.")
            st.write(str(e))
    else:
        st.write("Please upload both the resume and job description in .txt format.")

if __name__ == '__main__':
    main()
