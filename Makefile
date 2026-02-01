.PHONY: backend frontend dev test test-e2e lint clean help \
        docker-up docker-down docker-build docker-logs docker-clean \
        db-migrate db-upgrade db-downgrade install

# =============================================================================
# Help
# =============================================================================

help:
	@echo "ResuBoost AI - Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install    - Install all dependencies (backend + frontend)"
	@echo "  make backend    - Start FastAPI backend server (port 8000)"
	@echo "  make frontend   - Start Next.js frontend server (port 3000)"
	@echo "  make dev        - Start both backend and frontend"
	@echo ""
	@echo "Testing:"
	@echo "  make test       - Run all tests"
	@echo "  make test-e2e   - Run E2E tests with Playwright"
	@echo "  make lint       - Run linting on all code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up    - Start all services with Docker Compose"
	@echo "  make docker-down  - Stop all Docker services"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-logs  - Follow Docker logs"
	@echo "  make docker-clean - Remove Docker volumes and images"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate   - Create new migration from model changes"
	@echo "  make db-upgrade   - Apply all pending migrations"
	@echo "  make db-downgrade - Rollback one migration"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      - Remove cache and build files"

# =============================================================================
# Installation
# =============================================================================

install:
	@echo "Installing backend dependencies..."
	cd backend && uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && bun install
	@echo "Done! Run 'make dev' to start development servers."

# =============================================================================
# Development
# =============================================================================

backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && bun run dev

dev:
	@echo "Starting backend and frontend..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@make -j2 backend frontend

# =============================================================================
# Testing
# =============================================================================

test:
	@echo "Running backend tests..."
	cd backend && uv run pytest tests/ -v
	@echo ""
	@echo "Running frontend tests..."
	cd frontend && bun test

test-e2e:
	@echo "Running E2E tests with Playwright..."
	cd frontend && bun run test:e2e

test-coverage:
	@echo "Running tests with coverage..."
	cd backend && uv run pytest tests/ -v --cov=app --cov-report=html
	@echo "Coverage report: backend/htmlcov/index.html"

# =============================================================================
# Linting & Formatting
# =============================================================================

lint:
	@echo "=== Backend ==="
	@echo "Checking formatting with Black..."
	cd backend && uv run black --check app/ tests/
	@echo "Checking imports with isort..."
	cd backend && uv run isort --check-only app/ tests/
	@echo "Running Pylint..."
	cd backend && uv run pylint app/ --fail-under=8.0
	@echo ""
	@echo "=== Frontend ==="
	cd frontend && bun run lint
	cd frontend && bun run typecheck

format:
	@echo "Formatting backend code..."
	cd backend && uv run black app/ tests/
	cd backend && uv run isort app/ tests/
	@echo "Done!"

# =============================================================================
# Docker
# =============================================================================

docker-up:
	docker compose up -d
	@echo ""
	@echo "Services starting..."
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Postgres: localhost:5432"
	@echo "  Redis:    localhost:6379"
	@echo ""
	@echo "Run 'make docker-logs' to follow logs"

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

docker-clean:
	docker compose down -v --rmi local
	@echo "Removed Docker volumes and images"

docker-shell-backend:
	docker compose exec backend bash

docker-shell-db:
	docker compose exec db psql -U resuboost -d resuboost_dev

# =============================================================================
# Database Migrations
# =============================================================================

db-migrate:
	@read -p "Migration message: " msg; \
	cd backend && uv run alembic revision --autogenerate -m "$$msg"

db-upgrade:
	cd backend && uv run alembic upgrade head

db-downgrade:
	cd backend && uv run alembic downgrade -1

db-history:
	cd backend && uv run alembic history

# =============================================================================
# Cleanup
# =============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	cd frontend && rm -rf .next node_modules/.cache 2>/dev/null || true
	@echo "Cleaned cache files"
