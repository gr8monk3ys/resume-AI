# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ResuBoost AI is a job search toolkit with multi-provider LLM support, designed as an open-source alternative to Simplify.jobs. The application uses a FastAPI backend with a Next.js frontend architecture. Features include resume optimization, job tracking (Kanban board), cover letter generation, interview prep, and multi-user authentication.

**Supported LLM Providers:** OpenAI, Anthropic (Claude), Google (Gemini), Ollama (local models)

## Commands

```bash
# Development - using Makefile
make help       # Show all available commands
make backend    # Start FastAPI backend (port 8000)
make frontend   # Start Next.js frontend (port 3000)
make dev        # Start both backend and frontend
make test       # Run all tests
make lint       # Run linting (black, isort, pylint, eslint)
make clean      # Remove cache and build files

# Backend commands (from backend/ directory)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python -m pytest tests/ -v
black .
isort .

# Frontend commands (from frontend/ directory)
npm run dev         # Start development server
npm run build       # Production build
npm run lint        # Run ESLint
npm test            # Run Vitest tests
npm run typecheck   # TypeScript type checking
```

## Architecture

### System Overview
- **Backend:** FastAPI REST API (Python 3.10+)
- **Frontend:** Next.js 15 with React 19 and Tailwind CSS 4
- **Database:** SQLite with SQLAlchemy ORM (PostgreSQL ready)
- **Authentication:** JWT tokens (access + refresh)
- **AI Integration:** Multi-provider LLM via LangChain

### Request Flow
1. Frontend makes API request to `/api/*` endpoints
2. Request passes through middleware chain (CORS, rate limiting, security headers, audit logging)
3. JWT token validated in `middleware/auth.py`
4. Router handles request, interacts with SQLAlchemy models
5. Response returned with appropriate headers

### Backend Structure (`backend/`)
```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Pydantic settings
│   ├── database.py          # SQLAlchemy setup
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py          # User model
│   │   ├── profile.py       # Profile model
│   │   ├── resume.py        # Resume model
│   │   ├── job_application.py
│   │   ├── cover_letter.py
│   │   └── career_journal.py
│   ├── routers/             # API route handlers
│   │   ├── auth.py          # /api/auth/*
│   │   ├── profile.py       # /api/profile/*
│   │   ├── resumes.py       # /api/resumes/*
│   │   ├── jobs.py          # /api/jobs/*
│   │   ├── cover_letters.py # /api/cover-letters/*
│   │   ├── career_journal.py
│   │   └── ai.py            # /api/ai/*
│   ├── schemas/             # Pydantic request/response models
│   ├── services/            # Business logic
│   │   ├── llm_service.py   # Multi-provider LLM
│   │   ├── resume_analyzer.py
│   │   └── file_parser.py
│   └── middleware/          # Security middleware
│       ├── auth.py          # JWT authentication
│       ├── rate_limiter.py  # Token bucket rate limiting
│       ├── security.py      # CORS, headers, sanitization
│       └── audit.py         # Audit logging
└── tests/                   # Pytest tests
```

### Frontend Structure (`frontend/`)
```
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── page.tsx         # Dashboard
│   │   ├── login/           # Login page
│   │   ├── register/        # Registration page
│   │   ├── resumes/         # Resume Hub
│   │   ├── jobs/            # Job Pipeline (Kanban)
│   │   ├── interview/       # Interview Center
│   │   ├── documents/       # Document Generator
│   │   ├── cover-letters/   # Cover Letters
│   │   ├── career/          # Career Tools
│   │   ├── ai-assistant/    # AI Assistant
│   │   ├── profile/         # Profile Management
│   │   └── settings/        # Account Settings
│   └── lib/                 # Shared utilities
│       ├── auth.ts          # Auth helpers
│       └── utils.ts         # Utility functions
├── package.json
└── tailwind.config.ts
```

### API Endpoints

| Prefix | Description |
|--------|-------------|
| `/api/auth/*` | Authentication (login, register, refresh, change-password) |
| `/api/profile/*` | User profile CRUD |
| `/api/resumes/*` | Resume management and analysis |
| `/api/jobs/*` | Job application tracking |
| `/api/cover-letters/*` | Cover letter generation |
| `/api/career-journal/*` | Career journal entries |
| `/api/ai/*` | AI-powered features (tailor resume, answer questions) |

### Key Patterns

```python
# FastAPI dependency injection
from fastapi import Depends
from app.database import get_db
from app.middleware.auth import get_current_user

@router.get("/items")
async def get_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Item).filter(Item.user_id == current_user.id).all()

# Pydantic schemas for validation
from pydantic import BaseModel

class ItemCreate(BaseModel):
    name: str
    description: str | None = None

# LLM service usage
from app.services.llm_service import get_llm_service

service = get_llm_service()
result = await service.tailor_resume(resume_content, job_description)
```

### Kanban Statuses
`Bookmarked` -> `Applied` -> `Phone Screen` -> `Interview` -> `Offer` -> `Rejected`

## Environment Variables

**LLM Provider Configuration** (choose one):
```bash
# Provider selection (default: openai)
LLM_PROVIDER=openai  # Options: openai, anthropic, google, ollama, mock

# OpenAI
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini

# Anthropic (Claude)
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Google (Gemini)
GOOGLE_API_KEY=your_key_here
GOOGLE_MODEL=gemini-1.5-flash

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

**Security Settings:**
```bash
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=sqlite:///./data/resume_ai.db
CORS_ORIGINS=["http://localhost:3000"]
DEBUG=false
```

**Rate Limiting:**
```bash
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
AUTH_RATE_LIMIT_REQUESTS=5
AUTH_LOCKOUT_THRESHOLD=10
```

## Demo Account

Username: `demo` | Password: `demo123`

## Testing

```bash
# Run backend tests
cd backend && python -m pytest tests/ -v

# Run frontend tests
cd frontend && npm test

# Run all tests via Makefile
make test
```
