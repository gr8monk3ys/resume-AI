# ResuBoost-AI
ResuBoost-AI is a resume correction and updating tool that leverages the power of OpenAI's language model GPT-3.5-turbo. The tool is built with Python and the Streamlit library, making it accessible via a web-based user interface.

## Features
Resume and Job Description Upload: Users can upload their resume and a job description text file.
Resume Correction: The tool corrects any grammatical errors in the uploaded resume using the OpenAI language model.
Resume Update: The tool compares the resume with the job description and suggests updates to include any missing key skills or qualifications identified from the job description.
## Usage
The tool can be accessed via a web interface. Users are required to upload two text files: their current resume and a job description. After the files are uploaded, the tool will correct the resume and suggest updates based on the job description.

## Installation
To install and run ResuBoost-AI, clone the repository and install the required dependencies listed in the requirements.txt file. The required dependencies are:

openai
streamlit
python-dotenv
langchain
Please note that an OpenAI API key is required to use this tool. The API key should be stored as an environment variable.

## License
This project is licensed under the MIT License.

