.PHONY: backend frontend dev test lint clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make backend  - Start FastAPI backend server"
	@echo "  make frontend - Start Next.js frontend server"
	@echo "  make dev      - Start both backend and frontend"
	@echo "  make test     - Run all tests"
	@echo "  make lint     - Run linting on backend code"
	@echo "  make clean    - Remove cache and build files"

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
