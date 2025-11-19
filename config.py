"""
Configuration settings for ResuBoost AI
"""
import os

# File Upload Limits
MAX_FILE_SIZE_MB = 10  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_FILE_TYPES = ['txt', 'pdf', 'docx']

# OpenAI Settings
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
OPENAI_MAX_TOKENS = 2000
OPENAI_TEMPERATURE_DEFAULT = 0.7
OPENAI_TEMPERATURE_CREATIVE = 0.9

# Database Settings
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'resume_ai.db')

# Application Settings
APP_VERSION = '1.0.0'
APP_NAME = 'ResuBoost AI'

# Rate Limiting (requests per minute)
RATE_LIMIT_AI_CALLS = 20  # AI generation requests per minute
RATE_LIMIT_WINDOW = 60  # Window in seconds

# UI Settings
PAGINATION_SIZE = 20  # Items per page for lists
