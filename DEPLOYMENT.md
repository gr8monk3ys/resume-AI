# Deployment Guide - ResuBoost AI

Complete guide for deploying ResuBoost AI to production.

---

## Quick Deployment Options

### Option 1: Streamlit Cloud (Recommended - FREE)
**Best for:** Personal use, portfolio demos, single-user
**Cost:** FREE
**Setup Time:** 10 minutes

### Option 2: Heroku
**Best for:** Custom domain, more control
**Cost:** $7/month (Hobby tier)
**Setup Time:** 30 minutes

### Option 3: AWS/GCP/Azure
**Best for:** Enterprise, custom infrastructure
**Cost:** Variable
**Setup Time:** 1-2 hours

---

## Option 1: Streamlit Cloud (Easiest)

### Prerequisites
- GitHub account
- OpenAI API key
- Your code in a GitHub repository

### Steps

#### 1. Prepare Your Repository
```bash
# Make sure all files are committed
git add .
git commit -m "Prepare for deployment"
git push origin main
```

#### 2. Go to Streamlit Cloud
1. Visit https://streamlit.io/cloud
2. Sign in with GitHub
3. Click "New app"

#### 3. Configure Your App
- **Repository:** Select your `resume-AI` repo
- **Branch:** `main`
- **Main file path:** `app.py`
- **App URL:** Choose your custom subdomain (e.g., `myresume-ai`)

#### 4. Add Secrets
Click "Advanced settings" → "Secrets"

```toml
# Add this to secrets:
OPENAI_API_KEY = "sk-your-openai-api-key-here"
```

#### 5. Deploy!
Click "Deploy!" and wait 2-3 minutes.

Your app will be live at: `https://your-app-name.streamlit.app`

### Streamlit Cloud - Troubleshooting

**App won't start?**
- Check logs in Streamlit Cloud dashboard
- Verify `requirements.txt` is in root directory
- Ensure Python version compatibility

**"Module not found" error?**
- Make sure all dependencies in `requirements.txt`
- Try adding `python-version = "3.10"` to `.streamlit/config.toml`

**Slow performance?**
- Streamlit Cloud has resource limits
- Consider caching with `@st.cache_data`
- Reduce file size limits in `config.py`

---

## Option 2: Heroku Deployment

### Prerequisites
- Heroku account (free tier OK)
- Heroku CLI installed
- Git repository

### Steps

#### 1. Create Required Files

**Procfile** (create in root):
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

**runtime.txt** (create in root):
```
python-3.10.12
```

**setup.sh** (create in root):
```bash
mkdir -p ~/.streamlit/
echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
```

#### 2. Create Heroku App
```bash
# Login to Heroku
heroku login

# Create new app
heroku create your-resume-ai

# Add buildpack
heroku buildpacks:set heroku/python
```

#### 3. Set Environment Variables
```bash
heroku config:set OPENAI_API_KEY=sk-your-key-here
```

#### 4. Deploy
```bash
git add .
git commit -m "Add Heroku config"
git push heroku main
```

#### 5. Open Your App
```bash
heroku open
```

### Heroku - Troubleshooting

**H10 error (app crashed)?**
- Check logs: `heroku logs --tail`
- Verify Procfile is correct
- Ensure all dependencies installed

**Timeout errors?**
- Heroku free tier has 30s timeout
- Consider upgrading to Hobby tier ($7/month)

---

## Option 3: Docker Deployment

### Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Build and Run
```bash
# Build image
docker build -t resume-ai .

# Run container
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=your-key-here \
  resume-ai
```

### Deploy to Cloud

**AWS ECS:**
```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com
docker tag resume-ai:latest your-account.dkr.ecr.us-east-1.amazonaws.com/resume-ai:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/resume-ai:latest
```

**Google Cloud Run:**
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/your-project/resume-ai
gcloud run deploy resume-ai --image gcr.io/your-project/resume-ai --platform managed
```

---

## Security Checklist

Before deploying to production:

### Environment Variables
- [ ] OPENAI_API_KEY stored securely (not in code)
- [ ] .env file in .gitignore
- [ ] No secrets in git history

### API Protection
- [ ] Rate limiting enabled
- [ ] File size limits configured
- [ ] Input validation active

### Access Control
- [ ] Consider adding authentication for public deployment
- [ ] Use Streamlit's built-in auth (if available)
- [ ] Or use reverse proxy with auth (nginx + basic auth)

### Monitoring
- [ ] Check Streamlit Cloud logs regularly
- [ ] Set up error alerting
- [ ] Monitor API usage/costs

---

## Performance Optimization

### For Better Performance:

#### 1. Enable Caching
Add to functions that don't change:
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def expensive_function():
    return result
```

#### 2. Reduce File Sizes
Edit `config.py`:
```python
MAX_FILE_SIZE_MB = 5  # Reduce from 10MB
```

#### 3. Add Loading States
Ensure all AI calls have spinners:
```python
with st.spinner("Processing..."):
    result = slow_function()
```

#### 4. Optimize Database
For large datasets:
```python
# Add indexes
CREATE INDEX idx_company ON job_applications(company);
CREATE INDEX idx_date ON job_applications(application_date);
```

---

## Cost Estimation

### OpenAI API Costs
Based on GPT-3.5-turbo pricing (~$0.002 per 1K tokens):

| Operation | Tokens | Cost | Monthly (100 uses) |
|-----------|--------|------|-------------------|
| Grammar check | ~1000 | $0.002 | $0.20 |
| Resume optimization | ~1500 | $0.003 | $0.30 |
| Cover letter | ~1000 | $0.002 | $0.20 |
| Interview feedback | ~800 | $0.0016 | $0.16 |

**Estimated monthly cost (moderate use):** $5-20

### Hosting Costs
- **Streamlit Cloud:** FREE (with limitations)
- **Heroku Hobby:** $7/month
- **AWS/GCP:** $10-50/month (depending on usage)

---

## Custom Domain Setup

### Streamlit Cloud
1. Go to app settings
2. Add custom domain
3. Update DNS:
   ```
   CNAME record: your-domain.com → your-app.streamlit.app
   ```

### Heroku
```bash
heroku domains:add www.your-domain.com
heroku domains:add your-domain.com
```

Then add DNS records:
```
CNAME www → your-app.herokuapp.com
ALIAS @ → your-app.herokuapp.com
```

---

## Backup Strategy

### Database Backups

**Automated backup script:**
```bash
#!/bin/bash
# backup.sh - Run daily via cron

DATE=$(date +%Y%m%d)
cp data/resume_ai.db backups/resume_ai_$DATE.db
```

**Cron job:**
```bash
0 2 * * * /path/to/backup.sh
```

### Manual Backup
Use the Profile page "Export Data" feature to download:
- All job applications (CSV)
- Career journal (TXT)

---

## Monitoring & Alerts

### Set Up Monitoring

1. **Uptime Monitoring**
   - Use UptimeRobot (free)
   - Check every 5 minutes
   - Alert via email/SMS

2. **Error Tracking**
   - Check Streamlit logs daily
   - Set up log aggregation (optional)

3. **API Usage**
   - Monitor OpenAI dashboard
   - Set up billing alerts

### Health Check Endpoint
The app includes a health check at `/_stcore/health` (Streamlit default)

---

## Updating Your Deployment

### Streamlit Cloud
Just push to GitHub:
```bash
git add .
git commit -m "Update feature"
git push origin main
# Streamlit Cloud auto-deploys!
```

### Heroku
```bash
git push heroku main
```

### Docker
```bash
docker build -t resume-ai:v2 .
# Then redeploy to your cloud provider
```

---

## Rollback Strategy

### Streamlit Cloud
1. Go to app settings
2. Click "Revert to previous version"
3. Select commit to rollback to

### Heroku
```bash
heroku releases
heroku rollback v123
```

### Git-Based
```bash
git revert HEAD
git push
```

---

## Scaling Considerations

### When You Need to Scale:

**Signs you need more resources:**
- App becomes slow (>5s load time)
- Frequent timeouts
- High API costs
- Many concurrent users

**Solutions:**
1. Upgrade hosting tier
2. Add caching
3. Implement pagination
4. Use serverless functions for AI calls
5. Add CDN for static assets

---

## Support & Maintenance

### Regular Maintenance Tasks

**Weekly:**
- [ ] Check error logs
- [ ] Monitor API usage
- [ ] Verify backups

**Monthly:**
- [ ] Update dependencies
- [ ] Review costs
- [ ] Check for security updates

**Quarterly:**
- [ ] Performance review
- [ ] User feedback review
- [ ] Feature planning

---

## Quick Reference

### Important URLs
- **Streamlit Cloud:** https://streamlit.io/cloud
- **Heroku Dashboard:** https://dashboard.heroku.com
- **OpenAI Usage:** https://platform.openai.com/usage

### Common Commands
```bash
# Run locally
streamlit run app.py

# Run tests
python3 test_app.py

# Check logs (Heroku)
heroku logs --tail

# Set environment variable
export OPENAI_API_KEY=your-key
```

### Support
- **Streamlit Docs:** https://docs.streamlit.io
- **This Repo Issues:** GitHub Issues
- **OpenAI Support:** https://help.openai.com

---

## Troubleshooting Guide

### Common Issues

**"OpenAI API key not found"**
```bash
# Check if set
echo $OPENAI_API_KEY

# Set in deployment platform:
# Streamlit: Secrets
# Heroku: heroku config:set
# Docker: -e flag
```

**"Database locked"**
- SQLite doesn't handle concurrent writes well
- For multi-user, consider PostgreSQL
- Or deploy separate instance per user

**"File too large"**
- Adjust MAX_FILE_SIZE_MB in config.py
- Or ask users to compress files

**"Rate limit exceeded"**
- User exceeded 20 requests/minute
- They'll see error message with countdown
- Wait 60 seconds and try again

---

## Success Checklist

Before going live:

- [ ] All tests pass (`python3 test_app.py`)
- [ ] Environment variables set
- [ ] .env not in git
- [ ] Custom domain configured (optional)
- [ ] Monitoring set up
- [ ] Backups configured
- [ ] README updated with live URL
- [ ] Tested on mobile
- [ ] Tested all features
- [ ] Error messages are user-friendly

**You're ready to deploy!** 🚀
