# ResuBoost AI - System Architecture

**Version:** 1.0.0
**Last Updated:** 2025-11-18

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Database Schema](#database-schema)
4. [Authentication Flow](#authentication-flow)
5. [Data Flow](#data-flow)
6. [Security Architecture](#security-architecture)
7. [Module Organization](#module-organization)
8. [Key Design Patterns](#key-design-patterns)
9. [Dependencies](#dependencies)
10. [Extension Points](#extension-points)

---

## Overview

ResuBoost AI is a multi-user Streamlit application that helps job seekers optimize their resumes, track applications, and prepare for interviews. The application uses a multi-tier architecture with:

- **Frontend:** Streamlit web interface (9 pages)
- **Business Logic:** Python modules for authentication, AI integration, ATS scoring
- **Data Layer:** SQLite databases (auth.db, resume_ai.db)
- **External Services:** OpenAI API for AI-powered features

### Design Principles

1. **Data Isolation:** Each user's data is completely isolated
2. **Security by Default:** Rate limiting, audit logging, password enforcement
3. **Modularity:** Clear separation of concerns across modules
4. **Testability:** Comprehensive test coverage (27 tests)
5. **Production Ready:** Optimized for 5-10 concurrent users

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                       │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ app.py       │ Login        │ Optimizer    │ Job Tracker    │
│ (Dashboard)  │ (Auth)       │ (ATS)        │ (Applications) │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ Cover Letter │ Profile      │ Interview    │ Salary         │
│ (Generator)  │ (Settings)   │ (Prep)       │ (Negotiation)  │
├──────────────┴──────────────┴──────────────┴────────────────┤
│              Career Journal   │   Health Check               │
└───────────────────────────────┴──────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
├──────────────────┬──────────────────┬──────────────────────┤
│ utils/           │ models/          │ services/            │
│ - auth.py        │ - auth_database  │ - ats_scorer.py      │
│ - page_auth.py   │ - database.py    │ - ai_optimizer.py    │
│ - rate_limiter   │                  │ - cover_letter.py    │
│ - audit_logger   │                  │ - job_matcher.py     │
│ - password_val   │                  │                      │
└──────────────────┴──────────────────┴──────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
├──────────────────────────────┬──────────────────────────────┤
│  auth.db (SQLite)            │  resume_ai.db (SQLite)       │
│  - users                     │  - profiles                  │
│  - login_attempts            │  - resumes                   │
│  - audit_logs                │  - job_applications          │
│                              │  - cover_letters             │
│                              │  - career_journal            │
└──────────────────────────────┴──────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   External Services                          │
│  - OpenAI API (GPT-4/GPT-3.5)                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Authentication Database (auth.db)

#### users table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,        -- bcrypt hash
    full_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

**Indexes:**
- `idx_username` on username (for fast login lookups)
- `idx_email` on email (for registration checks)

#### login_attempts table
```sql
CREATE TABLE login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    success BOOLEAN DEFAULT 0
);
```

**Purpose:** Rate limiting and brute force prevention

#### audit_logs table
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,           -- login, logout, login_failed, etc.
    user_id INTEGER,
    username TEXT,
    action TEXT NOT NULL,
    details TEXT,                       -- JSON string with extra info
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose:** Security audit trail

### Application Database (resume_ai.db)

#### profiles table
```sql
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,             -- Foreign key to auth.db users
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    linkedin TEXT,
    github TEXT,
    portfolio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Index:** `idx_user_id` on user_id

#### resumes table
```sql
CREATE TABLE resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER,                 -- Foreign key to profiles
    version_name TEXT NOT NULL,
    content TEXT NOT NULL,
    ats_score INTEGER,
    keywords TEXT,                      -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);
```

#### job_applications table
```sql
CREATE TABLE job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER,
    company TEXT NOT NULL,
    position TEXT NOT NULL,
    job_description TEXT,
    status TEXT DEFAULT 'Applied',      -- Applied, Interview, Offer, Rejected
    application_date DATE,
    deadline DATE,
    location TEXT,
    job_url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);
```

#### cover_letters table
```sql
CREATE TABLE cover_letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER,
    job_application_id INTEGER,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id),
    FOREIGN KEY (job_application_id) REFERENCES job_applications(id)
);
```

#### career_journal table
```sql
CREATE TABLE career_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    achievement_date DATE,
    tags TEXT,                          -- Comma-separated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);
```

---

## Authentication Flow

### Registration Flow

```
User submits registration form
    │
    ▼
Validate password strength (utils/password_validator.py)
    │
    ├─ Fail → Show errors, require stronger password
    │
    ▼
Check username/email uniqueness (models/auth_database.py)
    │
    ├─ Exists → Show error
    │
    ▼
Hash password with bcrypt (bcrypt.gensalt() + bcrypt.hashpw())
    │
    ▼
Create user in auth.db (create_user())
    │
    ▼
Log event to audit_logs (utils/audit_logger.py)
    │
    ▼
Auto-login user
    │
    ▼
Create profile in resume_ai.db (get_or_create_profile_for_user())
    │
    ▼
Redirect to dashboard
```

### Login Flow

```
User submits username/password
    │
    ▼
Check rate limiting (utils/rate_limiter_auth.py)
    │
    ├─ Account locked → Show error
    ├─ Too many attempts → Show wait time
    │
    ▼
Fetch user from auth.db (get_user_by_username())
    │
    ├─ Not found → Record failed attempt, log to audit
    │
    ▼
Verify password (bcrypt.checkpw())
    │
    ├─ Invalid → Record failed attempt, log to audit
    │
    ▼
Clear failed attempts (rate_limiter_auth.py)
    │
    ▼
Update last_login timestamp
    │
    ▼
Set session state (st.session_state.user, st.session_state.authenticated)
    │
    ▼
Log successful login to audit_logs
    │
    ▼
Redirect to dashboard
```

### Session Management

**Session State Variables:**
- `st.session_state.authenticated` (bool) - Is user logged in?
- `st.session_state.user` (dict) - User info from auth.db
- `st.session_state.profile` (dict) - User profile from resume_ai.db

**Session Lifecycle:**
1. User logs in → Session state populated
2. User navigates pages → Session persists (Streamlit handles this)
3. User closes browser → Session cleared
4. User logs out → Session state cleared, rerun app

**Page Protection:**
All pages except Login use the `@require_authentication` decorator:

```python
from utils.page_auth import require_authentication

@require_authentication
def main():
    # Page content here
```

This decorator:
1. Initializes auth database
2. Initializes session state
3. Shows auth sidebar
4. Checks if authenticated, stops execution if not

---

## Data Flow

### Resume Optimization Flow

```
User uploads resume (PDF/DOCX) on Optimizer page
    │
    ▼
Extract text from file (PyPDF2 / python-docx)
    │
    ▼
Calculate ATS score (services/ats_scorer.py)
    │   ├─ Keyword extraction
    │   ├─ Formatting analysis
    │   ├─ Section detection
    │   └─ Scoring algorithm (0-100)
    │
    ▼
Generate AI suggestions (services/ai_optimizer.py)
    │   └─ Call OpenAI API with prompt
    │
    ▼
Display results to user
    │
    ▼
User saves optimized version
    │
    ▼
Store in resumes table (linked to user's profile_id)
```

### Job Application Tracking Flow

```
User creates job application on Job Tracker page
    │
    ▼
Validate required fields (company, position)
    │
    ▼
Insert into job_applications table (linked to profile_id)
    │
    ▼
User can:
    ├─ Update status (Applied → Interview → Offer)
    ├─ Add notes
    ├─ Set deadlines
    └─ Delete application
    │
    ▼
All operations filtered by profile_id (data isolation)
```

### Cover Letter Generation Flow

```
User selects job from dropdown (Cover Letter page)
    │
    ▼
Load job description from job_applications table
    │
    ▼
User provides additional context
    │
    ▼
Generate cover letter (services/cover_letter_generator.py)
    │   └─ OpenAI API call with job details + user profile
    │
    ▼
Display generated letter
    │
    ▼
User saves to cover_letters table (linked to job_application_id)
```

---

## Security Architecture

### Defense in Depth Layers

**Layer 1: Input Validation**
- Password strength enforcement (8+ chars, complexity)
- Email format validation
- SQL injection prevention (parameterized queries)
- File upload validation (PDF/DOCX only)

**Layer 2: Authentication**
- Bcrypt password hashing (salt rounds: 12)
- Session-based authentication (Streamlit session state)
- No plaintext passwords stored
- Secure password comparison (bcrypt.checkpw)

**Layer 3: Rate Limiting**
- Max 5 login attempts per 15 minutes per username
- Account lockout after 10 total failed attempts
- Cleanup of old attempts (>24 hours)
- Admin unlock functionality

**Layer 4: Authorization**
- Data isolation by user_id/profile_id
- All queries filtered by current user
- Admin-only functions protected (is_admin check)

**Layer 5: Audit Logging**
- All security events logged (login, logout, failures)
- Immutable audit trail
- Queryable for security analysis
- Includes IP address, timestamp, details

**Layer 6: Database Security**
- WAL mode for better concurrency
- Foreign keys enabled
- Transactions for data consistency
- Busy timeout to prevent locks

### Threat Model

**Threats Mitigated:**
- ✅ Brute force attacks (rate limiting + lockout)
- ✅ Password cracking (bcrypt with salt)
- ✅ SQL injection (parameterized queries)
- ✅ Data leakage (user isolation)
- ✅ Session hijacking (Streamlit secure sessions)

**Threats NOT Mitigated (require additional work):**
- ⚠️ CSRF attacks (no CSRF tokens)
- ⚠️ XSS attacks (Streamlit provides some protection, but not comprehensive)
- ⚠️ DDoS attacks (no rate limiting on API calls)
- ⚠️ Man-in-the-middle (requires HTTPS in production)

---

## Module Organization

### Project Structure

```
resume-AI/
├── app.py                      # Main dashboard
├── setup_multiuser.py          # Database initialization script
├── requirements.txt            # Python dependencies
│
├── pages/                      # Streamlit pages (9 pages)
│   ├── 0_Login.py              # Authentication page
│   ├── 1_Resume_Optimizer.py   # ATS scoring + AI optimization
│   ├── 2_Job_Tracker.py        # Job application tracking
│   ├── 3_Cover_Letter.py       # Cover letter generation
│   ├── 4_Career_Journal.py     # Achievement tracking
│   ├── 5_Profile.py            # User settings + password change
│   ├── 6_Interview_Prep.py     # Interview questions + practice
│   ├── 7_Salary_Negotiation.py # Salary research + scripts
│   └── 8_Health_Check.py       # System status + diagnostics
│
├── models/                     # Database models
│   ├── auth_database.py        # User authentication DB
│   └── database.py             # Application data DB
│
├── utils/                      # Utility modules
│   ├── auth.py                 # Authentication functions
│   ├── page_auth.py            # @require_authentication decorator
│   ├── rate_limiter_auth.py    # Login rate limiting
│   ├── audit_logger.py         # Security audit logging
│   └── password_validator.py   # Password strength validation
│
├── services/                   # Business logic services
│   ├── ats_scorer.py           # ATS scoring algorithm
│   ├── ai_optimizer.py         # AI-powered resume optimization
│   ├── cover_letter_generator.py # Cover letter generation
│   └── job_matcher.py          # Job-resume matching
│
├── scripts/                    # Utility scripts
│   ├── test_multiuser.py       # Multi-user testing (19 tests)
│   └── test_rate_limiting.py   # Rate limiting tests (8 tests)
│
└── data/                       # SQLite databases (gitignored)
    ├── auth.db                 # Authentication database
    └── resume_ai.db            # Application database
```

### Module Responsibilities

**models/** - Data Access Layer
- Database schema creation
- CRUD operations
- Connection management
- Data validation at DB level

**utils/** - Cross-cutting Concerns
- Authentication helpers
- Security utilities (rate limiting, audit logging)
- Password validation
- Decorators for DRY code

**services/** - Business Logic
- ATS scoring algorithms
- AI integration (OpenAI API)
- Cover letter generation
- Job matching algorithms

**pages/** - Presentation Layer
- Streamlit UI components
- User input handling
- Data display
- Navigation

---

## Key Design Patterns

### 1. Decorator Pattern

**@require_authentication**
- Wraps page functions to enforce authentication
- Reduces code duplication (90 lines → 1 decorator)
- Centralizes auth logic

```python
from utils.page_auth import require_authentication

@require_authentication
def main():
    st.title("Protected Page")
```

### 2. Context Manager Pattern

**Database Connections**
- Ensures proper resource cleanup
- Handles transactions automatically
- Reduces boilerplate code

```python
with get_auth_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT ...')
    # Auto-commit on success, rollback on exception
```

### 3. Repository Pattern

**Database Models**
- Abstracts database operations
- Provides clean API for CRUD operations
- Centralizes query logic

```python
# Instead of raw SQL everywhere:
user = get_user_by_username('alice')

# Not:
cursor.execute('SELECT * FROM users WHERE username = ?', ('alice',))
user = cursor.fetchone()
```

### 4. Strategy Pattern

**Password Validation**
- Multiple validation strategies (length, complexity, blacklist)
- Easy to add new validation rules
- Returns detailed feedback

```python
is_valid, errors, strength = validate_password_strength(password)
```

### 5. Facade Pattern

**Authentication Module**
- Simple interface hiding complex operations
- Combines rate limiting + auth + audit logging
- Single function call for login

```python
success, message = login(username, password)
# Internally: rate limit check, password verify, audit log, session setup
```

---

## Dependencies

### Core Dependencies

**Streamlit** (`streamlit>=1.28.0`)
- Web framework
- Session management
- UI components

**OpenAI** (`openai>=1.0.0`)
- AI-powered features
- GPT-4/GPT-3.5 integration

**bcrypt** (`bcrypt>=4.0.1`)
- Password hashing
- Secure password storage

**PyPDF2** (`PyPDF2>=3.0.0`)
- PDF resume parsing

**python-docx** (`python-docx>=0.8.11`)
- DOCX resume parsing

**python-dotenv** (`python-dotenv>=1.0.0`)
- Environment variable management

### Database

**SQLite3** (built-in)
- Authentication database
- Application database
- No external DB server required

### Testing

**unittest** (built-in)
- Test framework
- 27 automated tests

---

## Extension Points

### Adding New Features

**1. Add New Page**

```python
# pages/N_New_Feature.py
import streamlit as st
from utils.page_auth import require_authentication
from models.database import get_db_connection

@require_authentication
def main():
    st.title("New Feature")
    user = st.session_state.user
    profile = st.session_state.profile

    # Feature implementation

if __name__ == "__main__":
    main()
```

**2. Add New Database Table**

```python
# In models/database.py init_database()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS new_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER,
        data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (profile_id) REFERENCES profiles(id)
    )
''')
```

**3. Add New AI Service**

```python
# services/new_ai_service.py
import openai

def generate_something(profile, context):
    """Generate AI content."""
    prompt = f"Generate something for {profile['name']}..."

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
```

**4. Add New Validation Rule**

```python
# In utils/password_validator.py
def validate_password_strength(password):
    # Add new rule
    if len(password) > 64:
        errors.append("Password must be less than 64 characters")

    # Existing rules...
```

### Migration to PostgreSQL

For >20 concurrent users, migrate to PostgreSQL:

**1. Install psycopg2**
```bash
pip install psycopg2-binary
```

**2. Update connection managers**
```python
# models/database.py
import psycopg2
from psycopg2.extras import RealDictCursor

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        cursor_factory=RealDictCursor
    )
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
```

**3. Update schema (minor changes)**
- `AUTOINCREMENT` → `SERIAL`
- `TEXT` remains same
- `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` → `TIMESTAMP DEFAULT NOW()`

### Adding Email Verification

**1. Add email verification fields**
```sql
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN verification_token TEXT;
```

**2. Send verification email**
```python
# utils/email_sender.py
import smtplib

def send_verification_email(email, token):
    link = f"https://your-app.com/verify?token={token}"
    # Send email with link
```

**3. Add verification page**
```python
# pages/Verify_Email.py
def verify_email(token):
    # Update user email_verified = 1
```

---

## Performance Considerations

### Current Optimizations

1. **WAL Mode** - Better concurrent write performance
2. **Busy Timeout** - Prevents lock errors under load
3. **Indexes** - Fast lookups on username, email, user_id
4. **Connection Pooling** - Context managers prevent connection leaks

### Bottlenecks

1. **OpenAI API Calls** - Can take 5-10 seconds
2. **File Parsing** - Large PDFs can be slow
3. **SQLite Concurrency** - Limited to 5-10 concurrent users

### Optimization Opportunities

1. **Caching** - Cache OpenAI responses for similar requests
2. **Background Jobs** - Async processing for AI generation
3. **Database Upgrade** - PostgreSQL for >20 users
4. **Connection Pool** - SQLAlchemy for connection pooling

---

**Last Updated:** 2025-11-18
**Version:** 1.0.0
**Maintainer:** Development Team
