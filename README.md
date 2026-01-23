# ResuBoost AI

ResuBoost AI is a comprehensive job search toolkit with multi-provider LLM support, designed as an open-source alternative to Simplify.jobs. Built with a modern FastAPI backend and Next.js frontend, it provides an all-in-one platform to optimize resumes, generate cover letters, track applications, and prepare for interviews.

**Supported LLM Providers:** OpenAI, Anthropic (Claude), Google (Gemini), Ollama (local models)

## Features

### Resume Hub
- **ATS Score Analysis** - Get a detailed score (0-100) showing how well your resume passes Applicant Tracking Systems
- **AI-Powered Optimization** - Receive personalized suggestions to improve your resume for specific jobs
- **Resume Tailoring** - Generate job-specific resume versions with optimized keywords
- **Version Management** - Save and manage multiple resume versions for different applications
- **Multi-Format Support** - Upload resumes in TXT, PDF, or DOCX formats

### Job Pipeline
- **Kanban Board** - Visual job tracking with drag-and-drop status updates
- **6-Stage Workflow** - Bookmarked, Applied, Phone Screen, Interview, Offer, Rejected
- **Application Analytics** - Track response rates, conversion metrics, and weekly goals
- **Deadline Management** - Never miss important application deadlines
- **CSV Export** - Export applications for backup or external analysis

### Interview Center
- **Question Bank** - 50+ common interview questions across multiple categories
- **AI Practice Partner** - Get real-time feedback on your interview answers
- **STAR Story Builder** - Create compelling behavioral interview stories
- **Company Research** - Generate talking points and research questions

### Document Generator
- **Cover Letters** - AI-generated personalized cover letters for each application
- **Email Templates** - Professional networking, follow-up, and thank-you emails
- **Negotiation Scripts** - Salary negotiation scripts and counter-offer templates

### Career Tools
- **Career Journal** - Document achievements with AI enhancement
- **Keyword Gap Analysis** - Identify missing keywords from job descriptions
- **Salary Research** - Links to market data and compensation calculators

### Account and Settings
- **Multi-User Support** - Secure authentication with data isolation
- **Profile Management** - Store contact details, LinkedIn, GitHub, portfolio
- **Data Export** - Export all your data in standard formats

## Installation

### Prerequisites
- Python 3.10+
- Node.js 20+
- An LLM API key (OpenAI, Anthropic, Google, or Ollama running locally)

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/resume-AI.git
cd resume-AI
```

2. Set up the backend:
```bash
cd backend
pip install -r requirements.txt
```

3. Set up the frontend:
```bash
cd frontend
npm install
```

4. Create a `.env` file in the root directory (see [Environment Variables](#environment-variables)):
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Start the application:
```bash
# Terminal 1 - Backend (from backend directory)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend (from frontend directory)
npm run dev
```

6. Open your browser to `http://localhost:3000`

### Using Make Commands

The project includes a Makefile for convenience:

```bash
make help       # Show available commands
make backend    # Start FastAPI backend server (port 8000)
make frontend   # Start Next.js frontend server (port 3000)
make dev        # Start both backend and frontend
make test       # Run all tests (backend + frontend)
make lint       # Run linting on all code
make clean      # Remove cache and build files
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

### Required - Choose One LLM Provider

```bash
# Provider selection (default: openai)
LLM_PROVIDER=openai  # Options: openai, anthropic, google, ollama, mock

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Anthropic (Claude)
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Google (Gemini)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_MODEL=gemini-1.5-flash

# Ollama (local - no API key needed)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Application Settings

```bash
# Security (CHANGE IN PRODUCTION)
SECRET_KEY=your-secret-key-change-in-production

# Database
DATABASE_URL=sqlite:///./data/resume_ai.db

# CORS (frontend URL)
CORS_ORIGINS=["http://localhost:3000"]

# Debug mode
DEBUG=false
```

### Optional Settings

```bash
# JWT Token Expiration
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
AUTH_RATE_LIMIT_REQUESTS=5
AI_RATE_LIMIT_REQUESTS=20

# Brute Force Protection
AUTH_MAX_RECENT_FAILURES=5
AUTH_LOCKOUT_THRESHOLD=10

# File Uploads
MAX_FILE_SIZE_MB=10
MAX_RESUME_LENGTH=100000
```

## Technology Stack

### Backend
- **Framework:** FastAPI
- **Database:** SQLAlchemy with SQLite (PostgreSQL ready)
- **Authentication:** JWT tokens with bcrypt password hashing
- **AI Integration:** Multi-provider LLM support via LangChain
- **File Processing:** PyPDF2, python-docx

### Frontend
- **Framework:** Next.js 15 with App Router
- **UI Library:** React 19
- **Styling:** Tailwind CSS 4
- **State Management:** TanStack Query
- **Forms:** React Hook Form with Zod validation
- **Drag and Drop:** dnd-kit

## API Documentation

Once the backend is running, access the interactive API documentation:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Demo Account

A demo account is available for testing:
- **Username:** `demo`
- **Password:** `demo123`

## Security Features

- JWT-based authentication with refresh tokens
- Bcrypt password hashing
- Rate limiting on all endpoints
- Brute force protection with account lockout
- Input sanitization and validation
- CORS configuration
- Security headers (XSS protection, HSTS, CSP)
- Audit logging for security events

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.
