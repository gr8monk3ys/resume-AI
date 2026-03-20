# Security Policy

**ResuBoost AI - Security Policy and Vulnerability Reporting**

**Version:** 1.0.0
**Last Updated:** 2025-11-18

---

## Table of Contents

1. [Supported Versions](#supported-versions)
2. [Security Features](#security-features)
3. [Reporting a Vulnerability](#reporting-a-vulnerability)
4. [Security Best Practices](#security-best-practices)
5. [Known Limitations](#known-limitations)
6. [Security Roadmap](#security-roadmap)

---

## Supported Versions

| Version | Supported          | Notes |
| ------- | ------------------ | ----- |
| 1.0.x   | :white_check_mark: | Current release |
| < 1.0   | :x:                | Pre-production versions not supported |

---

## Security Features

### Authentication & Access Control

**Password Security**
- ✅ Bcrypt password hashing with salt (cost factor: 12)
- ✅ Password strength enforcement (8+ chars, complexity requirements)
- ✅ Common password blacklist
- ✅ No plaintext password storage
- ✅ Secure password reset workflow

**Rate Limiting**
- ✅ Login rate limiting: 5 attempts per 15 minutes
- ✅ Account lockout after 10 failed attempts
- ✅ Automatic cleanup of old attempts (>24 hours)
- ✅ Admin unlock functionality

**Session Management**
- ✅ Streamlit secure session state
- ✅ Session cleared on logout
- ✅ No session tokens in URLs
- ✅ Automatic session expiration on browser close

### Data Protection

**Data Isolation**
- ✅ Complete user data isolation by user_id/profile_id
- ✅ All queries filtered by current user
- ✅ No cross-user data leakage
- ✅ Foreign key constraints enforced

**Audit Logging**
- ✅ Comprehensive security event logging
- ✅ Login/logout tracking
- ✅ Failed login attempts logged
- ✅ Password changes logged
- ✅ Immutable audit trail
- ✅ IP address tracking (when available)

### Database Security

**SQLite Hardening**
- ✅ WAL mode for better concurrency
- ✅ Foreign keys enabled
- ✅ Parameterized queries (SQL injection prevention)
- ✅ File permissions: 600 (owner read/write only)
- ✅ Directory permissions: 700 (owner access only)

**Backup & Recovery**
- ✅ Database backup procedures documented
- ✅ Restore procedures tested
- ✅ Backup integrity checking

### Input Validation

**Current Protections**
- ✅ Password strength validation
- ✅ Email format validation
- ✅ Username uniqueness checks
- ✅ SQL injection prevention (parameterized queries)
- ✅ File upload validation (PDF/DOCX only)

### API Security

**OpenAI API**
- ✅ API key stored in environment variables
- ✅ No API key in code or version control
- ✅ API error handling
- ✅ Rate limit awareness

---

## Reporting a Vulnerability

### How to Report

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, please report security vulnerabilities by:

1. **Email:** Send details to [your-security-email@example.com]
   - Use subject line: `[SECURITY] Brief description`
   - Include detailed description of vulnerability
   - Include steps to reproduce
   - Include potential impact assessment

2. **Encrypted Communication (preferred):**
   - PGP Key: [Your PGP Key ID or link to public key]
   - Or use GitHub Security Advisories (Private vulnerability reporting)

### What to Include

When reporting a vulnerability, please provide:

1. **Description:** Clear description of the vulnerability
2. **Type:** Category (e.g., SQL injection, XSS, authentication bypass)
3. **Impact:** What an attacker could accomplish
4. **Affected Components:** Which files/modules are affected
5. **Steps to Reproduce:** Detailed reproduction steps
6. **Proof of Concept:** Code or screenshots (if applicable)
7. **Suggested Fix:** If you have one (optional but appreciated)

### Example Report Template

```
**Title:** [Brief description]

**Severity:** [Critical / High / Medium / Low]

**Vulnerability Type:** [e.g., SQL Injection, XSS, etc.]

**Description:**
[Detailed description of the vulnerability]

**Affected Components:**
- File: path/to/file.py
- Function: function_name()
- Line: 123

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Impact:**
[What can an attacker do with this vulnerability?]

**Proof of Concept:**
[Code, screenshots, or example exploit]

**Suggested Fix:**
[Your suggestion, if any]
```

### Response Timeline

- **Initial Response:** Within 48 hours
- **Triage & Assessment:** Within 7 days
- **Fix Development:** Depends on severity
  - Critical: 1-3 days
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Next release cycle
- **Public Disclosure:** After fix is deployed and users have time to update

### Coordinated Disclosure

We follow responsible disclosure practices:

1. We will work with you to understand and verify the vulnerability
2. We will develop and test a fix
3. We will release a security update
4. We will coordinate public disclosure with you
5. We will credit you in the security advisory (if desired)

---

## Security Best Practices

### For Administrators

**Initial Setup**
- [ ] Change default admin password immediately
- [ ] Use strong, unique password (16+ characters)
- [ ] Store admin credentials in password manager
- [ ] Delete demo accounts before production deployment
- [ ] Set up HTTPS in production (never use HTTP)

**Environment Configuration**
- [ ] Use environment variables for secrets (never hardcode)
- [ ] Set strong `SECRET_KEY` for sessions
- [ ] Restrict file permissions on .env file (chmod 600)
- [ ] Never commit .env file to version control

**Network Security**
- [ ] Deploy behind reverse proxy (nginx, Caddy)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure security headers (see nginx example below)
- [ ] Restrict access to production server (firewall rules)

**Ongoing Operations**
- [ ] Review audit logs weekly
- [ ] Monitor failed login attempts
- [ ] Keep dependencies updated
- [ ] Backup databases daily
- [ ] Test restore procedure monthly
- [ ] Monitor disk space
- [ ] Review user accounts monthly

### For Users

**Password Security**
- [ ] Use unique password (not reused from other sites)
- [ ] Use password manager
- [ ] Enable password strength meter
- [ ] Change password if suspicious activity detected

**Account Security**
- [ ] Log out when finished
- [ ] Don't share account credentials
- [ ] Report suspicious activity immediately
- [ ] Use strong full name and email

### For Developers

**Code Security**
- [ ] Never commit secrets or API keys
- [ ] Always use parameterized SQL queries
- [ ] Validate all user inputs
- [ ] Use type hints for better safety
- [ ] Follow principle of least privilege
- [ ] Log security events
- [ ] Write security tests

**Review Checklist**
- [ ] No hardcoded credentials
- [ ] No SQL injection vulnerabilities
- [ ] Proper input validation
- [ ] Proper error handling (no stack traces to users)
- [ ] Audit logging for sensitive operations
- [ ] Data isolation enforced
- [ ] HTTPS enforced in production

---

## Known Limitations

### Current Security Gaps

**CSRF Protection**
- ⚠️ **Status:** Not implemented
- **Risk:** Medium
- **Mitigation:** Streamlit provides some protection, but not comprehensive
- **Roadmap:** Planned for v1.1

**XSS Protection**
- ⚠️ **Status:** Partial (Streamlit provides some escaping)
- **Risk:** Low-Medium
- **Mitigation:** Avoid rendering user content as HTML
- **Roadmap:** Add Content Security Policy headers

**DDoS Protection**
- ⚠️ **Status:** Limited (rate limiting on logins only)
- **Risk:** Medium (for public deployments)
- **Mitigation:** Deploy behind reverse proxy with rate limiting
- **Roadmap:** Add application-level rate limiting for API calls

**Man-in-the-Middle (MITM)**
- ⚠️ **Status:** Requires HTTPS deployment
- **Risk:** High if HTTP used
- **Mitigation:** ALWAYS use HTTPS in production
- **Roadmap:** Add HTTPS enforcement

### Deployment Constraints

**Concurrent Users**
- **SQLite Limit:** ~5-10 concurrent users
- **Risk:** Database locks with >10 users
- **Mitigation:** Migrate to PostgreSQL for larger deployments
- **Roadmap:** PostgreSQL support in v1.2

**Email Verification**
- **Status:** Not implemented
- **Risk:** Low (account takeover via email)
- **Mitigation:** Manual email verification by admin
- **Roadmap:** Planned for v1.1

**Two-Factor Authentication**
- **Status:** Not implemented
- **Risk:** Medium (account compromise if password leaked)
- **Mitigation:** Use strong passwords, monitor audit logs
- **Roadmap:** Planned for v1.2

---

## Security Roadmap

### Version 1.1 (Next Release)

**Planned Security Enhancements:**
- [ ] CSRF token implementation
- [ ] Content Security Policy headers
- [ ] Email verification system
- [ ] Enhanced input sanitization
- [ ] Security headers configuration
- [ ] Automated security scanning in CI/CD

### Version 1.2 (Future)

**Planned Features:**
- [ ] Two-factor authentication (TOTP)
- [ ] PostgreSQL support for better concurrency
- [ ] API rate limiting (beyond login)
- [ ] Advanced audit logging with retention policies
- [ ] Security dashboard for admins
- [ ] Automated vulnerability scanning

### Long-term Goals

- [ ] OAuth2/SAML support for enterprise
- [ ] Hardware security key support (WebAuthn)
- [ ] Penetration testing report
- [ ] SOC 2 compliance (for enterprise)
- [ ] GDPR compliance tools (data export/deletion)

---

## Security Configuration Examples

### nginx Security Headers

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Content Security Policy
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self';" always;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Database File Permissions

```bash
# Secure database files
chmod 600 data/*.db

# Secure data directory
chmod 700 data/

# Verify permissions
ls -la data/
# Should show: drwx------ (directory)
#             -rw------- (database files)
```

### Environment Variables

```bash
# .env file (NEVER commit this)
OPENAI_API_KEY="sk-your-key-here"
SECRET_KEY="your-long-random-secret-key"

# Set strict permissions
chmod 600 .env
```

---

## Security Checklist

### Before Production Deployment

**Critical** (Must Do)
- [ ] Change admin password from default
- [ ] Delete demo accounts
- [ ] Enable HTTPS
- [ ] Set strong SECRET_KEY
- [ ] Configure security headers (nginx)
- [ ] Set database file permissions (chmod 600)
- [ ] Set .env file permissions (chmod 600)
- [ ] Review all user accounts

**Important** (Should Do)
- [ ] Set up automated backups
- [ ] Test restore procedure
- [ ] Configure firewall rules
- [ ] Set up monitoring/alerting
- [ ] Review audit logs
- [ ] Update all dependencies
- [ ] Run security tests

**Recommended** (Nice to Have)
- [ ] Set up intrusion detection
- [ ] Configure log aggregation
- [ ] Set up uptime monitoring
- [ ] Document security procedures
- [ ] Create incident response plan
- [ ] Schedule security reviews

---

## Contact Information

**Security Team:** [your-security-email@example.com]

**PGP Key:** [Link to public key or fingerprint]

**Response Time:** Within 48 hours

**Alternative Contact:** [Alternative secure contact method]

---

## Acknowledgments

We appreciate the security research community and will acknowledge researchers who report valid vulnerabilities (with their permission):

- [Researcher Name] - [Vulnerability Type] - [Date]

---

## Updates to This Policy

This security policy is reviewed and updated quarterly. Last update: 2025-11-18

**Changelog:**
- 2025-11-18: Initial security policy created (v1.0.0)

---

**Last Updated:** 2025-11-18
**Version:** 1.0.0
