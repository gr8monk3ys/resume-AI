# Deployment Guide

This guide explains how to set up the CI/CD pipeline for deploying ResuBoost AI to Railway.

## Prerequisites

1. A [Railway](https://railway.app) account
2. Two Railway projects: one for staging, one for production
3. GitHub repository with Actions enabled

## Railway Setup

### 1. Create Railway Projects

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Create a new project for **staging** (e.g., `resuboost-staging`)
3. Create a new project for **production** (e.g., `resuboost-production`)

### 2. Configure Services in Each Project

For each project, add the following services:

#### Backend Service
- Click "New" → "GitHub Repo" → Select this repo
- Set the **Root Directory** to `backend`
- Add environment variables (see below)

#### Frontend Service
- Click "New" → "GitHub Repo" → Select this repo
- Set the **Root Directory** to `frontend`
- Add environment variables (see below)

#### PostgreSQL Database
- Click "New" → "Database" → "PostgreSQL"
- Railway will automatically set `DATABASE_URL`

#### Redis (Optional, for rate limiting)
- Click "New" → "Database" → "Redis"
- Railway will automatically set `REDIS_URL`

### 3. Get Railway API Token

1. Go to [Railway Account Settings](https://railway.app/account/tokens)
2. Create a new API token
3. Copy the token for GitHub Secrets

### 4. Get Project IDs

For each project:
1. Open the project in Railway
2. Go to Settings
3. Copy the **Project ID** (visible in URL or settings)

## GitHub Configuration

### Repository Secrets

Go to: Settings → Secrets and variables → Actions → Secrets

| Secret | Description |
|--------|-------------|
| `RAILWAY_TOKEN` | Your Railway API token |

### Repository Variables

Go to: Settings → Secrets and variables → Actions → Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RAILWAY_STAGING_PROJECT_ID` | Staging project ID | `abc123-def456-...` |
| `RAILWAY_PRODUCTION_PROJECT_ID` | Production project ID | `xyz789-ghi012-...` |
| `STAGING_URL` | Staging frontend URL | `https://resuboost-staging.up.railway.app` |
| `STAGING_API_URL` | Staging backend URL | `https://resuboost-staging-api.up.railway.app` |
| `PRODUCTION_URL` | Production frontend URL | `https://resuboost.ai` |

### Environment Protection Rules (Recommended)

1. Go to: Settings → Environments
2. Create `staging` environment (no restrictions)
3. Create `production` environment with:
   - Required reviewers (add yourself)
   - Deployment branches: `main` only

## Environment Variables

### Backend Environment Variables

Set these in Railway for the backend service:

```bash
# Required
SECRET_KEY=<generate-with-python-secrets>
DATABASE_URL=<auto-set-by-railway>
LLM_PROVIDER=openai  # or anthropic, google, ollama

# LLM API Keys (at least one required)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# Optional
REDIS_URL=<auto-set-by-railway>
SENTRY_DSN=<your-sentry-dsn>
CORS_ORIGINS=["https://your-frontend-domain.com"]

# Security
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
ENABLE_RATE_LIMITING=true
```

### Frontend Environment Variables

Set these in Railway for the frontend service:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-domain.up.railway.app
NEXT_PUBLIC_SENTRY_DSN=<your-sentry-dsn>
```

## Deployment Workflow

### Automatic Staging Deployment

Every push to `main` branch triggers:
1. CI pipeline (lint, type check, tests)
2. Docker image builds
3. Deploy to staging
4. Health checks and smoke tests

### Manual Production Deployment

1. Go to: Actions → CD - Build & Deploy
2. Click "Run workflow"
3. Select `production` environment
4. Wait for staging tests to pass
5. Approve the production deployment (if protection rules enabled)

## Monitoring Deployments

### Railway Dashboard
- View logs: Project → Service → Logs
- View metrics: Project → Service → Metrics
- View deployments: Project → Service → Deployments

### Health Endpoints
- Backend: `GET /health` - Returns service health status
- Frontend: Root page loads successfully

## Rollback Procedure

If a deployment fails:

1. Go to Railway Dashboard
2. Select the affected service
3. Click "Deployments" tab
4. Find the last successful deployment
5. Click "Redeploy" on that deployment

## Troubleshooting

### Build Failures
- Check Railway build logs
- Ensure Dockerfile is correct
- Verify all dependencies are listed

### Health Check Failures
- Check service logs in Railway
- Verify DATABASE_URL is set correctly
- Check CORS_ORIGINS includes the frontend domain

### Database Migrations
Migrations run automatically during deployment. If issues occur:
```bash
# Connect to Railway service
railway run --service backend -- alembic upgrade head
```

## Security Notes

1. **Never commit secrets** - Use Railway/GitHub environment variables
2. **Rotate secrets regularly** - Especially after any exposure
3. **Use production protection** - Require approvals for production deploys
4. **Monitor Sentry** - Watch for errors after deployments
