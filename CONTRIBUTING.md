# Contributing to ResuBoost AI

Thank you for considering contributing to ResuBoost AI! This document provides guidelines and instructions for developers.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Code Style Guide](#code-style-guide)
4. [Testing Guidelines](#testing-guidelines)
5. [Adding New Features](#adding-new-features)
6. [Database Changes](#database-changes)
7. [Security Guidelines](#security-guidelines)
8. [Documentation](#documentation)
9. [Pull Request Process](#pull-request-process)

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- OpenAI API key
- Basic knowledge of Streamlit

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/resume-AI.git
   cd resume-AI
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment**
   ```bash
   # Create .env file
   echo "OPENAI_API_KEY=your-key-here" > .env
   ```

5. **Initialize Databases**
   ```bash
   python setup_multiuser.py
   ```

6. **Run Application**
   ```bash
   streamlit run app.py
   ```

7. **Run Tests**
   ```bash
   python scripts/test_multiuser.py
   python scripts/test_rate_limiting.py
   ```

### Project Structure

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture.

```
resume-AI/
├── app.py                  # Main dashboard
├── pages/                  # Streamlit pages (9 pages)
├── models/                 # Database models
├── utils/                  # Utility modules
├── services/               # Business logic
└── scripts/                # Test scripts
```

---

## Development Workflow

### Branch Naming

- **Features:** `feature/short-description`
- **Bug Fixes:** `fix/short-description`
- **Documentation:** `docs/short-description`
- **Tests:** `test/short-description`

**Examples:**
- `feature/add-email-verification`
- `fix/profile-update-bug`
- `docs/improve-readme`
- `test/cover-letter-service`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic changes)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(auth): add email verification

Added email verification flow with token-based verification.
Users must verify email before accessing protected pages.

Closes #123
```

```
fix(profile): prevent duplicate email addresses

Check for existing email before update to prevent database
constraint violations.

Fixes #456
```

### Development Cycle

1. **Create branch from main**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature
   ```

2. **Make changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run tests**
   ```bash
   python scripts/test_multiuser.py
   python scripts/test_rate_limiting.py
   ```

4. **Commit changes**
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature
   ```

6. **Create Pull Request**
   - Go to GitHub
   - Create PR from your branch to main
   - Fill out PR template

---

## Code Style Guide

### Python Style

Follow [PEP 8](https://pep8.org/) with these specific guidelines:

**Indentation:** 4 spaces (no tabs)

**Line Length:** 100 characters max

**Imports:**
```python
# Standard library
import os
from datetime import datetime

# Third-party
import streamlit as st
import bcrypt

# Local
from models.auth_database import get_user_by_id
from utils.auth import login, logout
```

**Naming Conventions:**
- **Functions/Variables:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private functions:** `_leading_underscore`

**Examples:**
```python
# Good
def calculate_ats_score(resume_text: str) -> int:
    """Calculate ATS score for resume."""
    pass

class UserProfile:
    """User profile model."""
    pass

MAX_LOGIN_ATTEMPTS = 5

# Bad
def CalculateATSScore(resumeText):  # Wrong naming
    pass

max_login_attempts = 5  # Should be constant
```

### Docstrings

Use Google-style docstrings:

```python
def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate a user by username and password.

    Args:
        username: The username to authenticate
        password: The plaintext password

    Returns:
        User dict if authentication successful, None otherwise

    Raises:
        ValueError: If username is empty

    Example:
        >>> user = authenticate_user('alice', 'password123')
        >>> print(user['username'])
        'alice'
    """
    pass
```

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Dict, Optional, Tuple

def get_user_jobs(user_id: int) -> List[Dict[str, any]]:
    """Get all jobs for a user."""
    pass

def validate_password(password: str) -> Tuple[bool, List[str], int]:
    """Validate password strength."""
    pass
```

### Comments

**Good Comments:**
```python
# Calculate ATS score using keyword density and formatting
score = calculate_score(keywords, formatting_score)

# Lock account after 10 failed attempts to prevent brute force
if failed_attempts >= 10:
    lock_account(username)
```

**Bad Comments:**
```python
# Add 1 to counter
counter += 1  # This is obvious

# TODO: Fix this later
# FIXME: This is broken  # Don't commit these
```

### Error Handling

**Always handle exceptions explicitly:**

```python
# Good
try:
    user = authenticate_user(username, password)
    if not user:
        st.error("Invalid credentials")
        return
except sqlite3.DatabaseError as e:
    st.error("Database error occurred")
    logger.error(f"DB error: {e}")
    return
except Exception as e:
    st.error("An unexpected error occurred")
    logger.error(f"Unexpected error: {e}")
    return

# Bad
try:
    user = authenticate_user(username, password)
except:  # Never use bare except
    pass  # Never silently ignore errors
```

---

## Testing Guidelines

### Running Tests

```bash
# All tests
python scripts/test_multiuser.py && python scripts/test_rate_limiting.py

# Individual test files
python scripts/test_multiuser.py
python scripts/test_rate_limiting.py
```

### Writing Tests

**Test File Structure:**
```python
import unittest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestFeatureName(unittest.TestCase):
    """Test suite for feature."""

    def setUp(self):
        """Set up test fixtures."""
        pass

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_specific_behavior(self):
        """Test that specific behavior works correctly."""
        # Arrange
        expected = "value"

        # Act
        result = function_under_test()

        # Assert
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main()
```

### Test Coverage Requirements

- **New features:** Must include tests
- **Bug fixes:** Must include regression test
- **Critical paths:** 100% coverage required (auth, payment, data access)
- **Overall target:** 80% coverage

### Test Naming

```python
def test_<function>_<scenario>_<expected_result>(self):
    """Test that function does something when scenario occurs."""
    pass

# Examples
def test_authenticate_user_valid_credentials_returns_user(self):
    """Test that authenticate_user returns user with valid credentials."""
    pass

def test_authenticate_user_invalid_password_returns_none(self):
    """Test that authenticate_user returns None with invalid password."""
    pass
```

---

## Adding New Features

### 1. Add New Page

**File:** `pages/N_Feature_Name.py`

```python
"""
Feature Name page for ResuBoost AI.

This page allows users to [description].
"""

import streamlit as st
from utils.page_auth import require_authentication
from models.database import get_db_connection

@require_authentication
def main():
    """Main function for Feature Name page."""
    st.title("🎯 Feature Name")

    # Get current user
    user = st.session_state.user
    profile = st.session_state.profile

    # Page content here
    st.write(f"Welcome, {user['username']}!")

    # Example: Load user-specific data
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM table WHERE profile_id = ?',
            (profile['id'],)
        )
        data = cursor.fetchall()

    # Display data
    for item in data:
        st.write(item)

if __name__ == "__main__":
    main()
```

**Page Numbering:**
- Count existing pages in `pages/` directory
- New page number = highest number + 1
- Example: If highest is `8_Health_Check.py`, new page is `9_Feature_Name.py`

### 2. Add Database Table

**File:** `models/database.py`

```python
# In init_database() function
cursor.execute('''
    CREATE TABLE IF NOT EXISTS new_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        data TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (profile_id) REFERENCES profiles(id)
    )
''')

# Add index for performance
cursor.execute('CREATE INDEX IF NOT EXISTS idx_profile_id ON new_table(profile_id)')
```

**Migration for existing databases:**
```python
# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='new_table'")
table_exists = cursor.fetchone() is not None

if table_exists:
    # Check if new column exists
    cursor.execute("PRAGMA table_info(new_table)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'new_column' not in columns:
        # Add new column
        cursor.execute('ALTER TABLE new_table ADD COLUMN new_column TEXT')
```

### 3. Add AI Service

**File:** `services/new_service.py`

```python
"""
New AI service for ResuBoost AI.

This service provides [description].
"""

import openai
import os
from typing import Dict, Optional

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_content(profile: Dict, context: str, model: str = "gpt-3.5-turbo") -> Optional[str]:
    """
    Generate AI content based on profile and context.

    Args:
        profile: User profile dict
        context: Context for generation
        model: OpenAI model to use (default: gpt-3.5-turbo)

    Returns:
        Generated content string, or None if error

    Raises:
        openai.error.OpenAIError: If API call fails
    """
    try:
        prompt = f"""
        Generate [content type] for:
        Name: {profile['name']}
        Context: {context}

        [Additional instructions]
        """

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()

    except openai.error.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

### 4. Add Utility Function

**File:** `utils/your_utility.py`

```python
"""
Utility functions for [purpose].
"""

from typing import List, Dict, Optional

def utility_function(param: str) -> Optional[Dict]:
    """
    Brief description of what this function does.

    Args:
        param: Description of parameter

    Returns:
        Description of return value

    Example:
        >>> result = utility_function("test")
        >>> print(result['key'])
        'value'
    """
    # Implementation
    pass
```

---

## Database Changes

### Adding Columns

**1. Update schema in `models/database.py`**
```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS table_name (
        ...,
        new_column TEXT DEFAULT 'default_value'
    )
''')
```

**2. Add migration logic**
```python
# Check if column exists
cursor.execute("PRAGMA table_info(table_name)")
columns = [col[1] for col in cursor.fetchall()]

if 'new_column' not in columns:
    cursor.execute('ALTER TABLE table_name ADD COLUMN new_column TEXT DEFAULT "default"')
```

**3. Test migration**
```bash
# Backup existing database
cp data/resume_ai.db data/resume_ai.db.backup

# Run migration
python setup_multiuser.py

# Verify
sqlite3 data/resume_ai.db "PRAGMA table_info(table_name);"
```

### Data Isolation

**ALWAYS filter by user/profile:**

```python
# Good - User can only see their own data
cursor.execute(
    'SELECT * FROM jobs WHERE profile_id = ?',
    (profile['id'],)
)

# Bad - User can see all data (security vulnerability)
cursor.execute('SELECT * FROM jobs')
```

---

## Security Guidelines

### Authentication

**ALWAYS use @require_authentication decorator:**

```python
from utils.page_auth import require_authentication

@require_authentication
def main():
    # Page content
    pass
```

### Password Handling

**NEVER store plaintext passwords:**

```python
# Good
from models.auth_database import hash_password
password_hash = hash_password(password)

# Bad
password_stored = password  # NEVER DO THIS
```

**ALWAYS validate password strength:**

```python
from utils.password_validator import validate_password_strength

is_valid, errors, strength = validate_password_strength(password)
if not is_valid:
    st.error("Password too weak: " + ", ".join(errors))
    return
```

### SQL Injection Prevention

**ALWAYS use parameterized queries:**

```python
# Good
cursor.execute('SELECT * FROM users WHERE username = ?', (username,))

# Bad - SQL injection vulnerability
cursor.execute(f'SELECT * FROM users WHERE username = "{username}"')
```

### Rate Limiting

**For sensitive operations, use rate limiting:**

```python
from utils.rate_limiter_auth import check_login_allowed

allowed, reason, wait_seconds = check_login_allowed(username)
if not allowed:
    st.error(reason)
    return
```

### Audit Logging

**Log security events:**

```python
from utils.audit_logger import log_event

log_event(
    event_type='sensitive_action',
    action='User performed sensitive action',
    user_id=user['id'],
    username=user['username'],
    details={'key': 'value'}
)
```

---

## Documentation

### Code Documentation

**Every module should have:**
- Module docstring explaining purpose
- Function docstrings with Args/Returns/Raises
- Type hints for all parameters
- Examples in docstrings for complex functions

### README Updates

When adding features, update:
- `README.md` - High-level overview
- `QUICK_START.md` - Quick start guide
- `ARCHITECTURE.md` - System architecture
- `TODO.md` - Remove completed items

### API Documentation

Document external APIs used:
- OpenAI API endpoints
- Any third-party services
- Rate limits
- Error handling

---

## Pull Request Process

### Before Creating PR

1. **Run all tests**
   ```bash
   python scripts/test_multiuser.py
   python scripts/test_rate_limiting.py
   ```

2. **Check code style**
   - Follow PEP 8
   - Use type hints
   - Add docstrings

3. **Update documentation**
   - Update relevant .md files
   - Add code comments
   - Update CHANGELOG if exists

4. **Test manually**
   - Run application locally
   - Test new feature
   - Test edge cases

### PR Template

```markdown
## Description
[Brief description of changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new features
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No security vulnerabilities introduced
- [ ] Database migrations tested (if applicable)

## Screenshots (if applicable)
[Add screenshots]

## Related Issues
Closes #[issue number]
```

### PR Review Process

1. **Automated checks** (if configured)
   - Tests must pass
   - Code style checks

2. **Manual review**
   - Code quality
   - Security review
   - Documentation review

3. **Approval required** before merge

4. **Squash and merge** to keep history clean

---

## Common Tasks

### Reset Development Database

```bash
rm -rf data/*.db
python setup_multiuser.py
```

### Unlock Test Account

```python
python -c "from utils.rate_limiter_auth import unlock_account; unlock_account('username')"
```

### Check Audit Logs

```bash
sqlite3 data/auth.db "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"
```

### Backup Databases

```bash
mkdir -p backups
cp data/auth.db backups/auth_$(date +%Y%m%d).db
cp data/resume_ai.db backups/resume_$(date +%Y%m%d).db
```

---

## Getting Help

- **Documentation:** See `README.md`, `ARCHITECTURE.md`, `QUICK_START.md`
- **Issues:** Create GitHub issue with detailed description
- **Questions:** Use GitHub Discussions

---

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on improving the codebase
- Help others learn and grow

---

**Last Updated:** 2025-11-18
**Version:** 1.0.0
