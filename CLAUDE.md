# CLAUDE.md

ResuBoost AI: resume/job-search toolkit. FastAPI backend (`backend/`, Python 3.10+, uv)
plus Next.js 15 frontend (`frontend/`, Bun). Not deployed; runs locally.

## Run / test

```bash
make setup && make dev            # .env with LLM_PROVIDER=mock, backend :8000 + frontend :3000
cd backend && uv sync --group dev
  uv run pytest tests/ -q          # LLM_PROVIDER=mock TESTING=true DATABASE_URL=sqlite:///:memory:
  uv run black --check app tests && uv run isort --check-only app tests
  uv run mypy app --ignore-missing-imports && uv run pylint app --fail-under=8.0
cd frontend && bun install --frozen-lockfile
  bun run lint && bun run typecheck && bun run test:ci && bun run build
```

CI (`.github/workflows/ci.yml`) runs exactly those commands; coverage gate is 63%.

## Where things live

- `backend/app/services/llm_service.py`: provider adapters (OpenAI, Anthropic, Google, Ollama,
  Mock), typed `LLMError` hierarchy, tenacity retry, per-user TTL cache.
- `backend/app/services/ats_analyzer.py`: keyword/format scoring, algorithmic, no LLM.
- `backend/app/routers/`: one file per API area; `ai.py` is the LLM + ATS surface.
- `backend/alembic/`: migrations. `backend/tests/conftest.py`: fixtures (SQLite in-memory).
- `frontend/src/`: App Router pages, `components/`, `lib/api.ts` client.
- `extension/`: Chrome extension that captures job posts into the app (unpackaged).
- `test_files/`: small sample uploads; the oversized-file case is a generated fixture.

## Gotchas

- Frontend lockfile is `bun.lock` only; do not add `package-lock.json`.
- `LLM_PROVIDER` defaults to `mock`; real providers need a key in `.env`.
- `frontend/e2e/` (Playwright) is not in CI; run with `bun run test:e2e`.
- Root `pyproject.toml` only holds lint tooling; app deps are in `backend/pyproject.toml`.
