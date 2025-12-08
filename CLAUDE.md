# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ResuBoost AI is an AI-powered job search toolkit built with Python and Streamlit. It provides resume optimization with ATS scoring, cover letter generation, job application tracking, interview prep, career journaling, and salary negotiation tools.

## Common Commands

```bash
# Run the application
streamlit run app.py

# Run all tests
python test_app.py

# Run specific test suites
python scripts/test_multiuser.py      # Multi-user auth tests (19 tests)
python scripts/test_rate_limiting.py  # Rate limiting tests (8 tests)

# Code quality (run before commits)
black . --line-length=100
isort . --profile black --line-length 100
pylint . --rcfile=.pylintrc
mypy . --ignore-missing-imports
bandit -r . -c pyproject.toml

# Setup pre-commit hooks
pre-commit install

# Initialize databases and test accounts
python setup_multiuser.py

# Database health check
python scripts/database_health_check.py
```

## Architecture

### Two-Database Design
- `data/auth.db` - Authentication only (users, login_attempts, audit_logs)
- `data/resume_ai.db` - Application data (profiles, resumes, jobs, letters, journal entries)

All queries are filtered by `profile_id` or `user_id` for multi-user data isolation.

### Layer Structure
```
pages/           # Streamlit UI pages (0_Login.py through 8_Health_Check.py)
models/          # Data access layer (auth_database.py, database.py)
services/        # Business logic (llm_service.py, resume_analyzer.py)
utils/           # Cross-cutting: auth, validation, rate limiting, logging
scripts/         # Test and utility scripts
```

### Key Patterns

**Page Authentication**: Use `@require_authentication` decorator from `utils/page_auth.py`:
```python
from utils.page_auth import require_authentication

@require_authentication
def my_page():
    st.title("Protected Page")
    # ... page content

if __name__ == "__main__":
    my_page()
```

**Database Connections**: Always use context managers:
```python
from models.database import get_db_connection
from models.auth_database import get_auth_db_connection

with get_db_connection() as conn:
    cursor = conn.cursor()
    # queries auto-commit on success
```

**LLM Calls**: Use `services/llm_service.py` which handles OpenAI integration via LangChain.

### Entry Point Flow (app.py)
1. `load_dotenv()` - Load environment
2. `init_database()` / `init_auth_database()` - Initialize DBs
3. `init_session_state()` - Initialize Streamlit session
4. `show_auth_sidebar()` - Display auth controls
5. Check `is_authenticated()` - Show dashboard or landing page

## Code Style

- Line length: 100 characters
- Formatting: Black + isort
- Type hints on all function signatures
- Google-style docstrings
- Conventional Commits: `type(scope): subject` (feat, fix, docs, style, refactor, test, chore)

## Environment

Requires `OPENAI_API_KEY` in `.env`. Optional: `OPENAI_MODEL` (default: gpt-3.5-turbo), `OPENAI_TEMPERATURE`.

## Test Accounts

Created by `setup_multiuser.py`: demo/demo123, alice/alice123, bob/bob123
