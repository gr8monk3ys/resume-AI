# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ResuBoost AI is a Streamlit-based job search toolkit powered by OpenAI, designed as an open-source alternative to Simplify.jobs. Features include resume optimization, job tracking (Kanban board), cover letter generation, interview prep, and multi-user authentication.

## Commands

```bash
# Run the application
streamlit run app.py

# Run tests (no Streamlit required)
python test_app.py

# Setup multi-user auth (creates demo accounts)
python setup_multiuser.py

# Database utilities
python scripts/database_health_check.py
python scripts/backup_databases.py

# Code quality (optional)
black .
pylint services/ utils/ models/
```

## Architecture

### Request Flow
1. User authenticates via `pages/0_Login.py` → `utils/auth.py` → `models/auth_database.py`
2. Auth state stored in `st.session_state` (authenticated, user_id, profile)
3. Pages use `@require_auth` decorator to enforce login
4. Profile/user data linked: `user_id` → `profile_id` → all user data (resumes, jobs, etc.)

### Data Layer (`models/`)
- **database.py** - Main SQLite DB (`data/resume_ai.db`): profiles, resumes, job_applications, cover_letters, career_journal. Uses WAL mode, foreign keys with CASCADE DELETE.
- **auth_database.py** - Auth DB (`data/auth.db`): users table with bcrypt hashing.

### Services Layer (`services/`)
- **llm_service.py** - `LLMService` class wrapping LangChain/OpenAI. Get singleton via `get_llm_service()`. Methods: `tailor_resume()`, `answer_application_question()`, `generate_interview_answer()`, `optimize_resume()`, `generate_cover_letter()`, `correct_grammar()`
- **resume_analyzer.py** - `ATSAnalyzer` class for resume scoring (0-100). Use `extract_keywords()` for keyword extraction.

### Utilities (`utils/`)
- **auth.py** - `login()`, `logout()`, `@require_auth` decorator, `init_session_state()`
- **rate_limiter.py** / **rate_limiter_auth.py** - Token bucket rate limiting for API calls and login attempts
- **cache.py** - `@cached(ttl_hours=N)` decorator using SQLite (`data/cache.db`)
- **validators.py** - `validate_email()`, `validate_url()`, `validate_phone()`, etc. Return `(bool, error_msg)`
- **file_parser.py** - `parse_file(content, file_type)` for txt/pdf/docx
- **audit_logger.py** - `log_login()`, `log_login_failed()` for security auditing
- **input_sanitizer.py** - Sanitize user inputs before storage/display

### Key Patterns
```python
# Database access - always use context manager
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))

# Auth state check in pages
if not st.session_state.get('authenticated'):
    st.warning("Please login")
    st.stop()

# LLM service usage with caching
service = get_llm_service()
result = service.tailor_resume(resume, job_description)
```

### Kanban Statuses
`Bookmarked` → `Applied` → `Phone Screen` → `Interview` → `Offer` → `Rejected`

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=your_key_here
```

Optional:
```
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_REQUEST_TIMEOUT=60
AUTH_MAX_RECENT_FAILURES=5
AUTH_LOCKOUT_THRESHOLD=10
MAX_RESUME_LENGTH=100000
SHOW_DEMO_CREDENTIALS=true
```

## Demo Account

Username: `demo` | Password: `demo123`
