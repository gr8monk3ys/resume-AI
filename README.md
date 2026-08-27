# resume-AI

A resume and job-search toolkit: ATS scoring, resume tailoring, cover letters and a
job-tracking board, served by a FastAPI backend and a Next.js frontend.

The part worth reading is the LLM layer. `backend/app/services/llm_service.py` wraps five
providers (OpenAI, Anthropic, Google, Ollama, and a mock) behind one interface, maps each
SDK's failures onto an eight-class `LLMError` hierarchy that carries a `retryable` flag, retries
only those with tenacity (3 attempts, exponential backoff from 1 s to 30 s with jitter), and
caches responses in a 100-entry, one-hour `TTLCache` keyed by provider, prompt and user so
two users never share a cached answer. The ATS score is deliberately *not* an LLM call:
`backend/app/services/ats_analyzer.py` does keyword, section and formatting scoring
algorithmically, so it is deterministic, free, and testable without a key; the LLM is only
consulted for wording suggestions when the caller opts in (`use_llm_suggestions`). The
tradeoff is documented in `backend/app/routers/ai.py` next to the `/api/ai/ats-analyze`
endpoint. Real ATS systems are keyword matchers, so matching them algorithmically is more
honest than asking a model to guess a number.

This runs locally. It is not deployed anywhere. `LLM_PROVIDER` defaults to `mock`, so
everything works with no API key; set a provider in `.env` for real generations.

## Run

Requires Python 3.10+, [uv](https://docs.astral.sh/uv/), and [Bun](https://bun.sh).

```bash
git clone https://github.com/gr8monk3ys/resume-AI.git && cd resume-AI
make setup      # writes .env (LLM_PROVIDER=mock, SQLite), installs backend + frontend deps
make dev        # backend on :8000, frontend on :3000
```

Or by hand:

```bash
cd backend  && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd frontend && bun install && bun run dev
```

API docs at http://localhost:8000/docs once the backend is up. `docker-compose.yml` starts
the same two services plus Postgres if you prefer containers.

## Configure

Copy `.env.example` to `.env`. The variables that matter:

```bash
LLM_PROVIDER=mock            # openai | anthropic | google | ollama | mock
OPENAI_API_KEY=...           # or ANTHROPIC_API_KEY / GOOGLE_API_KEY / OLLAMA_BASE_URL
SECRET_KEY=...               # JWT signing key; `make setup` generates one
DATABASE_URL=sqlite:///./data/resume_ai.db   # any SQLAlchemy URL; Postgres is tested in CI
MAX_FILE_SIZE_MB=10          # resume upload limit
```

Retry and cache behaviour is tunable through `LLM_MAX_RETRIES`, `LLM_RETRY_DELAY`,
`LLM_RETRY_MAX_DELAY`; see `backend/app/config.py` for the full list.

## Test

```bash
cd backend  && uv sync --group dev && uv run pytest tests/ -q     # SQLite in-memory, mock LLM
cd frontend && bun run lint && bun run typecheck && bun run test:ci && bun run build
cd frontend && bun run test:e2e                                    # Playwright, needs both servers
```

CI (`.github/workflows/ci.yml`) runs the backend suite against SQLite and Postgres, the
frontend lint/typecheck/test/build, and boots both servers for a health check. The
oversized-upload case generates its 10 MB file in a fixture (`oversized_upload` in
`backend/tests/conftest.py`) rather than committing one.

## Layout

```
backend/app/routers/     one file per API area; ai.py is the LLM + ATS surface
backend/app/services/    llm_service.py, ats_analyzer.py, file_parser.py, job_importer.py
backend/alembic/         migrations
frontend/src/            Next.js App Router pages, components, lib/api.ts client
extension/               Chrome extension that captures job posts into the tracker (unpackaged)
```

## License

MIT
