.PHONY: backend frontend dev test lint clean help db-migrate db-upgrade db-downgrade db-history db-current db-stamp

# Default target
help:
	@echo "Available commands:"
	@echo "  make backend      - Start FastAPI backend server"
	@echo "  make frontend     - Start Next.js frontend server"
	@echo "  make dev          - Start both backend and frontend"
	@echo "  make test         - Run all tests"
	@echo "  make lint         - Run linting on backend code"
	@echo "  make clean        - Remove cache and build files"
	@echo ""
	@echo "Database migration commands:"
	@echo "  make db-migrate   - Create new migration (use MSG='description')"
	@echo "  make db-upgrade   - Apply all pending migrations"
	@echo "  make db-downgrade - Rollback the last migration"
	@echo "  make db-history   - Show migration history"
	@echo "  make db-current   - Show current migration revision"
	@echo "  make db-stamp     - Mark database as current (use REV='revision')"

# Start FastAPI backend
backend:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start Next.js frontend
frontend:
	cd frontend && npm run dev

# Start both backend and frontend (requires two terminals or use &)
dev:
	@echo "Starting backend and frontend..."
	@echo "Backend will run on http://localhost:8000"
	@echo "Frontend will run on http://localhost:3000"
	@make -j2 backend frontend

# Run all tests
test:
	@echo "Running backend tests..."
	cd backend && python -m pytest tests/ -v
	@echo "Running frontend tests..."
	cd frontend && npm test 2>/dev/null || echo "No frontend tests configured"

# Run linting
lint:
	@echo "Running black..."
	black backend/
	@echo "Running isort..."
	isort backend/
	@echo "Running pylint..."
	pylint backend/ --ignore=__pycache__
	@echo "Running frontend lint..."
	cd frontend && npm run lint 2>/dev/null || echo "No frontend lint configured"

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	cd frontend && rm -rf .next node_modules/.cache 2>/dev/null || true
	@echo "Cleaned cache files"

# =============================================================================
# Database Migration Commands (Alembic)
# =============================================================================

# Create a new migration with autogenerate
# Usage: make db-migrate MSG="add user preferences table"
db-migrate:
ifndef MSG
	@echo "Error: MSG is required. Usage: make db-migrate MSG='description'"
	@exit 1
endif
	cd backend && alembic revision --autogenerate -m "$(MSG)"

# Apply all pending migrations
db-upgrade:
	cd backend && alembic upgrade head

# Rollback the last migration
db-downgrade:
	cd backend && alembic downgrade -1

# Show migration history
db-history:
	cd backend && alembic history --verbose

# Show current revision
db-current:
	cd backend && alembic current

# Stamp the database with a specific revision without running migrations
# Useful for marking an existing database as migrated
# Usage: make db-stamp REV="0001" or make db-stamp REV="head"
db-stamp:
ifndef REV
	@echo "Error: REV is required. Usage: make db-stamp REV='revision'"
	@echo "  make db-stamp REV='head'  - Mark as fully migrated"
	@echo "  make db-stamp REV='0001'  - Mark at specific revision"
	@exit 1
endif
	cd backend && alembic stamp $(REV)
