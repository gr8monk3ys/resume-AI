# Backend Dockerfile for ResuBoost AI API
# Multi-stage build with uv for fast, reproducible installs

FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies including PostgreSQL client libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# =============================================================================
# Dependencies Stage
# =============================================================================
FROM base AS deps

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (production only, no dev deps)
# Use --link-mode=copy to make the venv relocatable
RUN uv sync --frozen --no-dev --no-install-project --link-mode=copy

# =============================================================================
# Production Stage
# =============================================================================
FROM base AS production

# Copy installed dependencies from deps stage
COPY --from=deps /app/.venv /app/.venv

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data /app/logs \
    && chown -R appuser:appuser /app

USER appuser

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
