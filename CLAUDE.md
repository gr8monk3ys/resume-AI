# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ResuBoost AI is a job search toolkit with multi-provider LLM support, designed as an open-source alternative to Simplify.jobs. The application uses a FastAPI backend with a Next.js frontend architecture. Features include resume optimization, job tracking (Kanban board), cover letter generation, interview prep, and multi-user authentication.

**Supported LLM Providers:** OpenAI, Anthropic (Claude), Google (Gemini), Ollama (local models)

### Production Infrastructure
- **Database:** Neon PostgreSQL (with SQLite fallback for development)
- **Cache/Rate Limiting:** Redis (Upstash/Railway)
- **Authentication:** Clerk (replaces custom JWT)
- **Error Monitoring:** Sentry (backend + frontend)
- **Logging:** Structured JSON logging
- **Frontend Deployment:** Vercel
- **Backend Deployment:** Railway

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
- **Authentication:** Clerk (external auth provider with webhook sync)
- **AI Integration:** Multi-provider LLM via LangChain
- **Caching:** Redis via cache_service.py (LLM responses, profiles, job stats)

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

See `.env.example` for a comprehensive example with all settings.

**Required for Production:**
```bash
# Database - Neon PostgreSQL
DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/resuboost?sslmode=require

# Redis - Upstash or Railway
REDIS_URL=redis://default:password@xxx.upstash.io:6379

# Authentication - Clerk
CLERK_SECRET_KEY=sk_live_xxxxx
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_xxxxx
CLERK_WEBHOOK_SECRET=whsec_xxxxx

# Error Monitoring - Sentry
SENTRY_DSN=https://xxxxx@o123.ingest.sentry.io/123
NEXT_PUBLIC_SENTRY_DSN=https://xxxxx@o123.ingest.sentry.io/123

# LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxx

# Security
SECRET_KEY=generate-a-secure-random-key
CORS_ORIGINS=["https://your-app.vercel.app"]
```

## Testing

```bash
# Run backend tests
cd backend && python -m pytest tests/ -v

# Run frontend tests
cd frontend && npm test

# Run all tests via Makefile
make test
```
