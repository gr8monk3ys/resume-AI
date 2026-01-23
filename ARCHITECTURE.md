# ResuBoost AI - System Architecture

**Version:** 2.0.0
**Last Updated:** 2026-01-23

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Database Schema](#database-schema)
6. [Authentication Flow](#authentication-flow)
7. [API Endpoints](#api-endpoints)
8. [Security Architecture](#security-architecture)
9. [LLM Integration](#llm-integration)

---

## Overview

ResuBoost AI is a multi-user job search application built with a modern decoupled architecture:

- **Backend:** FastAPI REST API with SQLAlchemy ORM
- **Frontend:** Next.js 15 with React 19 and Tailwind CSS 4
- **Database:** SQLite (development) / PostgreSQL (production ready)
- **Authentication:** JWT tokens with refresh token rotation
- **AI Integration:** Multi-provider LLM support via LangChain

### Design Principles

1. **Separation of Concerns:** Clear frontend/backend separation via REST API
2. **Security by Default:** JWT auth, rate limiting, input sanitization, audit logging
3. **Multi-Provider AI:** Support for OpenAI, Anthropic, Google, and Ollama
4. **Data Isolation:** Each user's data is completely isolated
5. **Type Safety:** Pydantic schemas (backend) and TypeScript (frontend)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js 15)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Dashboard│ │ Resumes  │ │   Jobs   │ │Interview │ │ Settings │  │
│  │  /       │ │ /resumes │ │  /jobs   │ │/interview│ │/settings │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Documents │ │  Cover   │ │  Career  │ │    AI    │ │ Profile  │  │
│  │/documents│ │ Letters  │ │ /career  │ │Assistant │ │ /profile │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP/REST (JSON)
                                   │ JWT Bearer Token
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI)                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     Middleware Stack                           │  │
│  │  CORS → RequestID → Security Headers → Rate Limit → Audit     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                   │                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                         Routers                              │    │
│  │  /api/auth  /api/profile  /api/resumes  /api/jobs  /api/ai  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                   │                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                        Services                              │    │
│  │    LLM Service    Resume Analyzer    File Parser            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                   │                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     SQLAlchemy ORM                           │    │
│  │   User  Profile  Resume  JobApplication  CoverLetter        │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                  │
│  ┌────────────────────────────┐  ┌─────────────────────────────┐   │
│  │   SQLite/PostgreSQL        │  │     LLM Providers           │   │
│  │   - users                  │  │  - OpenAI (GPT-4o)          │   │
│  │   - profiles               │  │  - Anthropic (Claude)       │   │
│  │   - resumes                │  │  - Google (Gemini)          │   │
│  │   - job_applications       │  │  - Ollama (local)           │   │
│  │   - cover_letters          │  │                             │   │
│  │   - career_journal         │  │                             │   │
│  └────────────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Pydantic Settings configuration
│   ├── database.py          # SQLAlchemy engine and session
│   │
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py          # User authentication model
│   │   ├── profile.py       # User profile model
│   │   ├── resume.py        # Resume storage model
│   │   ├── job_application.py
│   │   ├── cover_letter.py
│   │   └── career_journal.py
│   │
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── user.py          # UserCreate, UserResponse, Token
│   │   ├── profile.py
│   │   ├── resume.py
│   │   ├── job.py
│   │   ├── cover_letter.py
│   │   ├── career_journal.py
│   │   └── ai.py            # AI request/response schemas
│   │
│   ├── routers/             # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── profile.py       # Profile CRUD
│   │   ├── resumes.py       # Resume management
│   │   ├── jobs.py          # Job tracking
│   │   ├── cover_letters.py
│   │   ├── career_journal.py
│   │   └── ai.py            # AI-powered features
│   │
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   ├── llm_service.py   # Multi-provider LLM integration
│   │   ├── resume_analyzer.py # ATS scoring algorithm
│   │   └── file_parser.py   # PDF/DOCX parsing
│   │
│   └── middleware/          # Security and logging
│       ├── __init__.py
│       ├── auth.py          # JWT token handling
│       ├── rate_limiter.py  # Token bucket rate limiting
│       ├── security.py      # CORS, headers, sanitization
│       └── audit.py         # Security event logging
│
├── tests/                   # Pytest test suite
│   ├── __init__.py
│   ├── conftest.py          # Test fixtures
│   ├── test_auth.py
│   ├── test_resumes.py
│   ├── test_jobs.py
│   ├── test_ai.py
│   └── test_career_journal.py
│
└── requirements.txt
```

### Key Dependencies

| Package | Purpose |
|---------|---------|
| fastapi | Web framework |
| uvicorn | ASGI server |
| sqlalchemy | ORM and database |
| pydantic-settings | Configuration management |
| python-jose | JWT token handling |
| passlib + bcrypt | Password hashing |
| langchain | LLM orchestration |
| PyPDF2, python-docx | File parsing |

---

## Frontend Architecture

### Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── layout.tsx       # Root layout with providers
│   │   ├── page.tsx         # Dashboard (home)
│   │   ├── login/
│   │   │   └── page.tsx     # Login form
│   │   ├── register/
│   │   │   └── page.tsx     # Registration form
│   │   ├── resumes/
│   │   │   └── page.tsx     # Resume Hub
│   │   ├── jobs/
│   │   │   └── page.tsx     # Job Pipeline (Kanban)
│   │   ├── interview/
│   │   │   └── page.tsx     # Interview Center
│   │   ├── documents/
│   │   │   └── page.tsx     # Document Generator
│   │   ├── cover-letters/
│   │   │   └── page.tsx     # Cover Letter Generator
│   │   ├── career/
│   │   │   └── page.tsx     # Career Tools
│   │   ├── ai-assistant/
│   │   │   └── page.tsx     # AI Assistant
│   │   ├── profile/
│   │   │   └── page.tsx     # Profile Management
│   │   └── settings/
│   │       └── page.tsx     # Account Settings
│   │
│   └── lib/                 # Shared utilities
│       ├── auth.ts          # Auth context and helpers
│       ├── utils.ts         # Utility functions
│       └── index.ts         # Exports
│
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.js
```

### Key Dependencies

| Package | Purpose |
|---------|---------|
| next 15 | React framework |
| react 19 | UI library |
| tailwindcss 4 | Styling |
| @tanstack/react-query | Server state management |
| react-hook-form | Form handling |
| zod | Schema validation |
| @dnd-kit | Drag and drop (Kanban) |
| lucide-react | Icons |

---

## Database Schema

### Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐
│    users     │       │   profiles   │
├──────────────┤       ├──────────────┤
│ id (PK)      │──────<│ id (PK)      │
│ username     │       │ user_id (FK) │
│ email        │       │ name         │
│ password_hash│       │ email        │
│ full_name    │       │ phone        │
│ is_active    │       │ linkedin     │
│ is_admin     │       │ github       │
│ created_at   │       │ portfolio    │
│ last_login   │       │ created_at   │
└──────────────┘       │ updated_at   │
                       └──────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   resumes    │   │job_applications│  │career_journal│
├──────────────┤   ├──────────────┤   ├──────────────┤
│ id (PK)      │   │ id (PK)      │   │ id (PK)      │
│ profile_id   │   │ profile_id   │   │ profile_id   │
│ version_name │   │ company      │   │ title        │
│ content      │   │ position     │   │ description  │
│ ats_score    │   │ job_desc     │   │ date         │
│ keywords     │   │ status       │   │ tags         │
│ created_at   │   │ app_date     │   │ created_at   │
│ updated_at   │   │ deadline     │   │ updated_at   │
└──────────────┘   │ location     │   └──────────────┘
                   │ job_url      │
                   │ notes        │
                   │ created_at   │
                   │ updated_at   │
                   └──────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │cover_letters │
                   ├──────────────┤
                   │ id (PK)      │
                   │ profile_id   │
                   │ job_app_id   │
                   │ content      │
                   │ created_at   │
                   │ updated_at   │
                   └──────────────┘
```

### Users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### Profiles Table

```sql
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    linkedin VARCHAR(255),
    github VARCHAR(255),
    portfolio VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Job Applications Table

```sql
CREATE TABLE job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    company VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    job_description TEXT,
    status VARCHAR(20) DEFAULT 'Bookmarked',
    application_date DATE,
    deadline DATE,
    location VARCHAR(100),
    job_url VARCHAR(500),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);
```

**Status Values:** `Bookmarked`, `Applied`, `Phone Screen`, `Interview`, `Offer`, `Rejected`

---

## Authentication Flow

### JWT Token Flow

```
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│ Frontend│                    │ Backend │                    │Database │
└────┬────┘                    └────┬────┘                    └────┬────┘
     │                              │                              │
     │  POST /api/auth/login        │                              │
     │  {username, password}        │                              │
     │─────────────────────────────>│                              │
     │                              │  Verify credentials          │
     │                              │─────────────────────────────>│
     │                              │                              │
     │                              │  User record                 │
     │                              │<─────────────────────────────│
     │                              │                              │
     │  {access_token,              │  Generate JWT tokens         │
     │   refresh_token}             │                              │
     │<─────────────────────────────│                              │
     │                              │                              │
     │  Store tokens in memory      │                              │
     │                              │                              │
     │  GET /api/resumes            │                              │
     │  Authorization: Bearer <jwt> │                              │
     │─────────────────────────────>│                              │
     │                              │  Validate JWT                │
     │                              │  Extract user_id             │
     │                              │                              │
     │                              │  Query with user_id          │
     │                              │─────────────────────────────>│
     │                              │                              │
     │  {resumes: [...]}            │  User's resumes              │
     │<─────────────────────────────│<─────────────────────────────│
     │                              │                              │
```

### Token Structure

**Access Token (30 min expiry):**
```json
{
  "sub": 1,
  "username": "demo",
  "exp": 1706000000,
  "type": "access"
}
```

**Refresh Token (7 day expiry):**
```json
{
  "sub": 1,
  "username": "demo",
  "exp": 1706600000,
  "type": "refresh"
}
```

### Token Refresh Flow

1. Access token expires
2. Frontend sends refresh token to `/api/auth/refresh`
3. Backend validates refresh token
4. New access and refresh tokens issued
5. Frontend updates stored tokens

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create new user account |
| POST | `/api/auth/login` | Login and get tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Get current user info |
| POST | `/api/auth/change-password` | Change password |
| GET | `/api/auth/lockout-status/{username}` | Check account lockout |

### Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profile` | Get user profile |
| PUT | `/api/profile` | Update profile |
| DELETE | `/api/profile` | Delete profile and all data |

### Resumes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/resumes` | List all resumes |
| POST | `/api/resumes` | Create new resume |
| GET | `/api/resumes/{id}` | Get specific resume |
| PUT | `/api/resumes/{id}` | Update resume |
| DELETE | `/api/resumes/{id}` | Delete resume |
| POST | `/api/resumes/{id}/analyze` | Get ATS score |

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List all job applications |
| POST | `/api/jobs` | Create job application |
| GET | `/api/jobs/{id}` | Get specific job |
| PUT | `/api/jobs/{id}` | Update job application |
| DELETE | `/api/jobs/{id}` | Delete job application |
| PATCH | `/api/jobs/{id}/status` | Update job status |

### Cover Letters

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cover-letters` | List all cover letters |
| POST | `/api/cover-letters` | Create cover letter |
| GET | `/api/cover-letters/{id}` | Get specific cover letter |
| PUT | `/api/cover-letters/{id}` | Update cover letter |
| DELETE | `/api/cover-letters/{id}` | Delete cover letter |

### Career Journal

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/career-journal` | List journal entries |
| POST | `/api/career-journal` | Create entry |
| GET | `/api/career-journal/{id}` | Get specific entry |
| PUT | `/api/career-journal/{id}` | Update entry |
| DELETE | `/api/career-journal/{id}` | Delete entry |

### AI Features

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/tailor-resume` | Tailor resume for job |
| POST | `/api/ai/optimize-resume` | Get optimization suggestions |
| POST | `/api/ai/generate-cover-letter` | Generate cover letter |
| POST | `/api/ai/answer-question` | Answer application question |
| POST | `/api/ai/interview-answer` | Generate interview answer |
| POST | `/api/ai/correct-grammar` | Fix grammar in text |

---

## Security Architecture

### Middleware Stack

```
Request → CORS → RequestID → SecurityHeaders → InputSanitization → RateLimiter → Audit → Router
```

### Rate Limiting

**Token Bucket Algorithm:**
- General API: 100 requests / 60 seconds
- Auth endpoints: 5 requests / 60 seconds
- AI endpoints: 20 requests / 60 seconds

### Brute Force Protection

- Track failed login attempts per username
- After 5 failures in 15 minutes: temporary lockout
- After 10 total failures: account lockout (admin unlock required)
- All attempts logged to audit database

### Security Headers

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

### Input Sanitization

- HTML tag stripping
- Script injection prevention
- SQL injection prevention via parameterized queries
- File upload validation (PDF/DOCX only, size limits)

---

## LLM Integration

### Multi-Provider Architecture

```python
# services/llm_service.py

class LLMService:
    def __init__(self, provider: str):
        match provider:
            case "openai":
                self.llm = ChatOpenAI(model=settings.openai_model)
            case "anthropic":
                self.llm = ChatAnthropic(model=settings.anthropic_model)
            case "google":
                self.llm = ChatGoogleGenerativeAI(model=settings.google_model)
            case "ollama":
                self.llm = ChatOllama(model=settings.ollama_model)
            case "mock":
                self.llm = MockLLM()

    async def tailor_resume(self, resume: str, job_description: str) -> str:
        # Implementation
        pass
```

### Supported Methods

| Method | Description |
|--------|-------------|
| `tailor_resume()` | Rewrite resume for specific job |
| `optimize_resume()` | Get improvement suggestions |
| `generate_cover_letter()` | Create personalized cover letter |
| `answer_application_question()` | Answer common application questions |
| `generate_interview_answer()` | STAR method interview responses |
| `correct_grammar()` | Fix grammar and improve clarity |

### Provider Configuration

```bash
# Environment variables
LLM_PROVIDER=openai          # Provider to use
OPENAI_API_KEY=sk-...        # OpenAI API key
OPENAI_MODEL=gpt-4o-mini     # Model to use

# Or for local Ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

---

**Version:** 2.0.0
**Architecture:** FastAPI + Next.js
**Maintainer:** Development Team
