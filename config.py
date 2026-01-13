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
OPENAI_REQUEST_TIMEOUT = int(os.getenv('OPENAI_REQUEST_TIMEOUT', '60'))  # Timeout in seconds

# Database Settings
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'resume_ai.db')

# Application Settings
APP_VERSION = '1.0.0'
APP_NAME = 'ResuBoost AI'
SHOW_DEMO_CREDENTIALS = os.getenv('SHOW_DEMO_CREDENTIALS', 'true').lower() == 'true'  # Show demo account info

# Rate Limiting (requests per minute)
RATE_LIMIT_AI_CALLS = 20  # AI generation requests per minute
RATE_LIMIT_WINDOW = 60  # Window in seconds

# Authentication Rate Limiting
AUTH_MAX_RECENT_FAILURES = int(os.getenv('AUTH_MAX_RECENT_FAILURES', '5'))  # Max failures per window
AUTH_RATE_LIMIT_WINDOW_MINUTES = int(os.getenv('AUTH_RATE_LIMIT_WINDOW_MINUTES', '15'))  # Window in minutes
AUTH_LOCKOUT_THRESHOLD = int(os.getenv('AUTH_LOCKOUT_THRESHOLD', '10'))  # Total failures before lockout
AUTH_CLEANUP_DAYS = int(os.getenv('AUTH_CLEANUP_DAYS', '30'))  # Days to keep failed attempts

# Input Validation
MAX_RESUME_LENGTH = int(os.getenv('MAX_RESUME_LENGTH', '100000'))  # Max resume size in characters (100KB)
MAX_JOB_DESCRIPTION_LENGTH = int(os.getenv('MAX_JOB_DESCRIPTION_LENGTH', '50000'))  # Max job description size

# UI Settings
PAGINATION_SIZE = 20  # Items per page for lists
