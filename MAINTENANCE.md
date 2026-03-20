# Maintenance Runbook

**ResuBoost AI - Operations & Maintenance Guide**

**Version:** 1.0.0
**Last Updated:** 2025-11-18

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [User Management](#user-management)
3. [Database Operations](#database-operations)
4. [Troubleshooting](#troubleshooting)
5. [Performance Monitoring](#performance-monitoring)
6. [Security Operations](#security-operations)
7. [Backup & Restore](#backup--restore)
8. [Updates & Patches](#updates--patches)

---

## Daily Operations

### Check Application Status

```bash
# Check if application is running
ps aux | grep streamlit

# Check systemd status (if using systemd)
sudo systemctl status resuboost-ai

# Check logs for errors
tail -f ~/.streamlit/logs/*.log

# Or journalctl if using systemd
sudo journalctl -u resuboost-ai -f
```

### Health Check

```bash
# Access health check page
curl http://localhost:8501/Health_Check

# Or visit in browser
# http://localhost:8501/Health_Check
```

### Monitor Failed Logins

```bash
# Check failed logins in last 24 hours
sqlite3 data/auth.db <<EOF
SELECT
    timestamp,
    username,
    details
FROM audit_logs
WHERE event_type = 'login_failed'
AND timestamp > datetime('now', '-1 day')
ORDER BY timestamp DESC;
EOF
```

### Check Active Users

```bash
# Count active users
sqlite3 data/auth.db <<EOF
SELECT
    COUNT(*) as active_users
FROM users
WHERE is_active = 1;
EOF
```

---

## User Management

### Add New User

**Option 1: Through Application**
1. Go to Login page
2. Click "Register" tab
3. Fill out form
4. Submit

**Option 2: Via Python Script**

```python
# add_user.py
from models.auth_database import create_user

username = input("Username: ")
email = input("Email: ")
password = input("Password: ")
full_name = input("Full Name: ")
is_admin = input("Make admin? (y/n): ").lower() == 'y'

try:
    user_id = create_user(
        username=username,
        email=email,
        password=password,
        full_name=full_name,
        is_admin=is_admin
    )
    print(f"✅ User created successfully! ID: {user_id}")
except ValueError as e:
    print(f"❌ Error: {e}")
```

### List All Users

```bash
sqlite3 data/auth.db <<EOF
SELECT
    id,
    username,
    email,
    full_name,
    is_active,
    is_admin,
    last_login
FROM users
ORDER BY created_at DESC;
EOF
```

### Deactivate User

```bash
# Via SQL
sqlite3 data/auth.db "UPDATE users SET is_active = 0 WHERE username = 'username';"

# Or via Python
python -c "
from models.auth_database import delete_user, get_user_by_username
user = get_user_by_username('username')
if user:
    delete_user(user['id'])
    print('User deactivated')
"
```

### Reactivate User

```bash
sqlite3 data/auth.db "UPDATE users SET is_active = 1 WHERE username = 'username';"
```

### Reset User Password (Admin)

```python
# reset_password.py
from models.auth_database import get_user_by_username, hash_password, get_auth_db_connection

username = input("Username: ")
new_password = input("New password: ")

user = get_user_by_username(username)
if not user:
    print("User not found")
    exit(1)

new_hash = hash_password(new_password)

with get_auth_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user['id']))
    print("✅ Password reset successfully")
```

### Unlock Locked Account

```bash
# Via Python
python -c "
from utils.rate_limiter_auth import unlock_account
unlock_account('username')
print('Account unlocked')
"
```

### Make User Admin

```bash
sqlite3 data/auth.db "UPDATE users SET is_admin = 1 WHERE username = 'username';"
```

---

## Database Operations

### Check Database Size

```bash
# Check size of databases
ls -lh data/*.db

# Detailed breakdown
sqlite3 data/auth.db "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();" | numfmt --to=iec

sqlite3 data/resume_ai.db "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();" | numfmt --to=iec
```

### Vacuum Databases (Reclaim Space)

```bash
# Vacuum auth database
sqlite3 data/auth.db "VACUUM;"

# Vacuum application database
sqlite3 data/resume_ai.db "VACUUM;"

# Check new size
ls -lh data/*.db
```

### Analyze Database Performance

```bash
# Check table sizes
sqlite3 data/resume_ai.db <<EOF
SELECT
    name,
    (SELECT COUNT(*) FROM sqlite_master sm WHERE sm.name = m.name) as row_count
FROM sqlite_master m
WHERE type = 'table'
ORDER BY name;
EOF

# Check indexes
sqlite3 data/resume_ai.db <<EOF
SELECT name, tbl_name
FROM sqlite_master
WHERE type = 'index'
ORDER BY tbl_name;
EOF
```

### Clean Old Audit Logs

```python
# cleanup_logs.py
from utils.audit_logger import cleanup_old_logs

# Keep 90 days
days_to_keep = 90
cleanup_old_logs(days=days_to_keep)
print(f"✅ Cleaned audit logs older than {days_to_keep} days")
```

### Clean Old Login Attempts

```python
# cleanup_attempts.py
from utils.rate_limiter_auth import cleanup_old_attempts

cleanup_old_attempts()
print("✅ Cleaned old login attempts (>24 hours)")
```

### Check Database Integrity

```bash
# Check auth database
sqlite3 data/auth.db "PRAGMA integrity_check;"

# Check application database
sqlite3 data/resume_ai.db "PRAGMA integrity_check;"
```

### Export Database to CSV

```bash
# Export users table
sqlite3 -header -csv data/auth.db "SELECT id, username, email, is_active, is_admin, created_at, last_login FROM users;" > users_export.csv

# Export job applications
sqlite3 -header -csv data/resume_ai.db "SELECT * FROM job_applications;" > jobs_export.csv
```

---

## Troubleshooting

### Application Won't Start

**Symptom:** `streamlit run app.py` fails

**Diagnosis:**
```bash
# Check Python version
python --version  # Should be 3.8+

# Check if port is already in use
lsof -i :8501

# Check for missing dependencies
pip list | grep streamlit
pip list | grep openai

# Check environment variables
echo $OPENAI_API_KEY  # Should not be empty
```

**Solutions:**
```bash
# Kill process on port 8501
kill -9 $(lsof -t -i:8501)

# Reinstall dependencies
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY="your-key"

# Try running again
streamlit run app.py
```

### Database Locked Errors

**Symptom:** `sqlite3.OperationalError: database is locked`

**Diagnosis:**
```bash
# Check for processes accessing database
lsof data/auth.db
lsof data/resume_ai.db

# Check WAL mode (should be enabled)
sqlite3 data/auth.db "PRAGMA journal_mode;"
```

**Solutions:**
```bash
# Close all connections
kill -9 $(lsof -t data/auth.db)
kill -9 $(lsof -t data/resume_ai.db)

# Ensure WAL mode is enabled
sqlite3 data/auth.db "PRAGMA journal_mode=WAL;"
sqlite3 data/resume_ai.db "PRAGMA journal_mode=WAL;"

# Restart application
streamlit run app.py
```

### Users Can't Login

**Symptom:** Valid credentials rejected

**Diagnosis:**
```bash
# Check if user exists and is active
sqlite3 data/auth.db "SELECT username, is_active FROM users WHERE username = 'username';"

# Check if account is locked
python -c "
from utils.rate_limiter_auth import is_account_locked
print('Locked:', is_account_locked('username'))
"

# Check recent failed attempts
sqlite3 data/auth.db "SELECT * FROM login_attempts WHERE username = 'username' ORDER BY timestamp DESC LIMIT 10;"
```

**Solutions:**
```bash
# Unlock account
python -c "from utils.rate_limiter_auth import unlock_account; unlock_account('username')"

# Reactivate user
sqlite3 data/auth.db "UPDATE users SET is_active = 1 WHERE username = 'username';"

# Reset password (if forgotten)
# See "Reset User Password" in User Management section
```

### High Memory Usage

**Symptom:** Application consuming excessive RAM

**Diagnosis:**
```bash
# Check memory usage
ps aux | grep streamlit | awk '{print $6}'

# Check for memory leaks
top -p $(pgrep -f streamlit)
```

**Solutions:**
```bash
# Restart application
sudo systemctl restart resuboost-ai

# Or manually
kill -9 $(pgrep -f streamlit)
streamlit run app.py

# Add memory limits to systemd service
sudo systemctl edit resuboost-ai
# Add: MemoryLimit=512M
```

### OpenAI API Errors

**Symptom:** AI features not working

**Diagnosis:**
```bash
# Check API key
echo $OPENAI_API_KEY

# Test API connection
python -c "
import openai
import os
openai.api_key = os.getenv('OPENAI_API_KEY')
try:
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': 'Hello'}]
    )
    print('✅ API working')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

**Solutions:**
```bash
# Set correct API key
export OPENAI_API_KEY="sk-..."

# Check quota/billing at platform.openai.com

# Try different model
# In code, change model='gpt-4' to model='gpt-3.5-turbo'
```

### Slow Performance

**Symptom:** Pages loading slowly

**Diagnosis:**
```bash
# Check database size
ls -lh data/*.db

# Check number of records
sqlite3 data/resume_ai.db "SELECT COUNT(*) FROM job_applications;"

# Check concurrent users
lsof data/resume_ai.db | wc -l
```

**Solutions:**
```bash
# Vacuum databases
sqlite3 data/auth.db "VACUUM;"
sqlite3 data/resume_ai.db "VACUUM;"

# Clean old data
python -c "from utils.audit_logger import cleanup_old_logs; cleanup_old_logs(90)"

# Consider PostgreSQL migration if >10 concurrent users
```

---

## Performance Monitoring

### Monitor Response Times

```bash
# Check Streamlit metrics
tail -f ~/.streamlit/logs/*.log | grep "GET /"
```

### Monitor Database Queries

```bash
# Enable query logging (SQLite 3.26+)
sqlite3 data/resume_ai.db <<EOF
PRAGMA query_only = OFF;
PRAGMA optimize;
EOF
```

### Monitor Concurrent Users

```bash
# Count active database connections
lsof data/resume_ai.db | wc -l

# Should be < 10 for SQLite
```

### Monitor Disk Usage

```bash
# Check data directory size
du -sh data/

# Check individual files
du -h data/*.db

# Set up alert if > 1GB
```

---

## Security Operations

### Review Audit Logs

```bash
# Recent security events
sqlite3 data/auth.db <<EOF
SELECT
    event_type,
    username,
    action,
    timestamp
FROM audit_logs
WHERE timestamp > datetime('now', '-7 days')
ORDER BY timestamp DESC
LIMIT 50;
EOF
```

### Find Suspicious Activity

```bash
# Multiple failed logins from same user
sqlite3 data/auth.db <<EOF
SELECT
    username,
    COUNT(*) as failed_attempts
FROM audit_logs
WHERE event_type = 'login_failed'
AND timestamp > datetime('now', '-1 day')
GROUP BY username
HAVING COUNT(*) > 5
ORDER BY failed_attempts DESC;
EOF

# Locked accounts
sqlite3 data/auth.db <<EOF
SELECT
    username,
    COUNT(*) as total_failures
FROM login_attempts
WHERE success = 0
GROUP BY username
HAVING COUNT(*) >= 10;
EOF
```

### Generate Security Report

```bash
# security_report.sh
echo "=== Security Report ==="
echo "Generated: $(date)"
echo

echo "Users:"
sqlite3 data/auth.db "SELECT COUNT(*) FROM users WHERE is_active = 1;" | xargs echo "  Active:"
sqlite3 data/auth.db "SELECT COUNT(*) FROM users WHERE is_active = 0;" | xargs echo "  Inactive:"
sqlite3 data/auth.db "SELECT COUNT(*) FROM users WHERE is_admin = 1;" | xargs echo "  Admins:"
echo

echo "Failed Logins (24h):"
sqlite3 data/auth.db "SELECT COUNT(*) FROM audit_logs WHERE event_type = 'login_failed' AND timestamp > datetime('now', '-1 day');"
echo

echo "Locked Accounts:"
sqlite3 data/auth.db "SELECT COUNT(DISTINCT username) FROM login_attempts WHERE success = 0 GROUP BY username HAVING COUNT(*) >= 10;"
echo

echo "Recent Logins (24h):"
sqlite3 data/auth.db "SELECT COUNT(*) FROM audit_logs WHERE event_type = 'login' AND timestamp > datetime('now', '-1 day');"
```

---

## Backup & Restore

### Manual Backup

```bash
# Create backup directory
mkdir -p backups

# Backup with timestamp
DATE=$(date +%Y%m%d_%H%M%S)
cp data/auth.db "backups/auth_${DATE}.db"
cp data/resume_ai.db "backups/resume_${DATE}.db"

echo "✅ Backup created: $DATE"
```

### Automated Backup

```bash
# Add to crontab (daily at 2 AM)
crontab -e

# Add this line:
0 2 * * * /path/to/resume-AI/backup.sh
```

**backup.sh:**
```bash
#!/bin/bash
BACKUP_DIR="/path/to/resume-AI/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup databases
cp /path/to/resume-AI/data/auth.db "$BACKUP_DIR/auth_${DATE}.db"
cp /path/to/resume-AI/data/resume_ai.db "$BACKUP_DIR/resume_${DATE}.db"

# Keep only last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "$(date): Backup completed" >> /var/log/resuboost-backup.log
```

### Restore from Backup

```bash
# Stop application
sudo systemctl stop resuboost-ai

# Restore databases
cp backups/auth_YYYYMMDD_HHMMSS.db data/auth.db
cp backups/resume_YYYYMMDD_HHMMSS.db data/resume_ai.db

# Verify integrity
sqlite3 data/auth.db "PRAGMA integrity_check;"
sqlite3 data/resume_ai.db "PRAGMA integrity_check;"

# Start application
sudo systemctl start resuboost-ai

# Verify functionality
curl http://localhost:8501
```

### Test Restore Procedure

```bash
# Monthly restore test
# 1. Create test directory
mkdir -p test_restore
cd test_restore

# 2. Copy latest backup
cp ../backups/auth_*.db ./auth.db
cp ../backups/resume_*.db ./resume_ai.db

# 3. Verify integrity
sqlite3 auth.db "PRAGMA integrity_check;"
sqlite3 resume_ai.db "PRAGMA integrity_check;"

# 4. Verify data
sqlite3 auth.db "SELECT COUNT(*) FROM users;"
sqlite3 resume_ai.db "SELECT COUNT(*) FROM profiles;"

# 5. Clean up
cd ..
rm -rf test_restore

echo "✅ Restore test successful"
```

---

## Updates & Patches

### Update Python Dependencies

```bash
# Backup current environment
pip freeze > requirements_backup.txt

# Update packages
pip install --upgrade -r requirements.txt

# Test application
python scripts/test_multiuser.py
python scripts/test_rate_limiting.py

# If tests fail, rollback
pip install -r requirements_backup.txt
```

### Update Application Code

```bash
# Backup current version
git stash

# Pull latest changes
git pull origin main

# Install any new dependencies
pip install -r requirements.txt

# Run migrations if needed
python setup_multiuser.py

# Run tests
python scripts/test_multiuser.py
python scripts/test_rate_limiting.py

# Restart application
sudo systemctl restart resuboost-ai
```

### Apply Security Patches

```bash
# Check for security updates
pip list --outdated

# Update specific package
pip install --upgrade package-name

# Verify application still works
python scripts/test_multiuser.py

# Restart
sudo systemctl restart resuboost-ai
```

---

## Emergency Procedures

### Complete System Failure

1. **Stop the service**
   ```bash
   sudo systemctl stop resuboost-ai
   ```

2. **Check logs**
   ```bash
   sudo journalctl -u resuboost-ai -n 100
   ```

3. **Restore from backup**
   ```bash
   cp backups/auth_LATEST.db data/auth.db
   cp backups/resume_LATEST.db data/resume_ai.db
   ```

4. **Restart service**
   ```bash
   sudo systemctl start resuboost-ai
   ```

5. **Verify functionality**
   ```bash
   curl http://localhost:8501
   ```

### Data Corruption

1. **Stop application immediately**
2. **Create backup of corrupted DB**
   ```bash
   cp data/auth.db data/auth_corrupted.db
   ```
3. **Restore from last known good backup**
4. **Run integrity check**
5. **Restart application**

### Security Breach

1. **Lock all accounts**
   ```bash
   sqlite3 data/auth.db "UPDATE users SET is_active = 0;"
   ```

2. **Review audit logs**
   ```bash
   sqlite3 data/auth.db "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100;"
   ```

3. **Change admin password**
4. **Reset all user passwords**
5. **Review and fix vulnerability**
6. **Notify users**

---

## Contact Information

**Emergency Contact:** [Your Phone/Email]

**Documentation:**
- `README.md` - General overview
- `ARCHITECTURE.md` - System architecture
- `CONTRIBUTING.md` - Development guide
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Deployment guide

**Support Channels:**
- GitHub Issues: [Your Repo Issues]
- Email: [Your Email]

---

**Last Updated:** 2025-11-18
**Version:** 1.0.0
