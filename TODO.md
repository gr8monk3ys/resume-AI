# TODO.md - Brutally Honest Codebase Issues

This document captures the real issues in this codebase that need to be addressed.

---

## 🚨 CRITICAL (Must Fix)

### Security

- [ ] **Hardcoded demo credentials exposed in UI** - `pages/0_Login.py:66` displays `demo/demo123` to anyone
- [ ] **Hardcoded credentials in setup script** - `setup_multiuser.py:71-77` has plaintext passwords
- [ ] **CSV injection vulnerability** - `pages/2_Job_Tracker.py:52` uses manual `chr(34)` quoting instead of csv module
- [ ] **No API key validation at startup** - `app.py` starts without checking `OPENAI_API_KEY`, fails at runtime

### Scalability

- [ ] **SQLite not suitable for multi-user Streamlit** - Will cause "database is locked" errors with 5-10 concurrent users
- [ ] **Session-based rate limiting easily bypassed** - `utils/rate_limiter.py:26-30` uses `st.session_state` which resets on server restart

---

## 🔴 HIGH PRIORITY

### Code Quality

- [ ] **Silent exception handling** - `models/database.py:51-52`, `utils/rate_limiter_auth.py:285-288` use `except Exception: pass`
- [ ] **Redundant `raise e` pattern** - Found in `models/database.py:148`, `models/auth_database.py:72`, `utils/cache.py:73`, `utils/rate_limiter_auth.py:32`, `utils/audit_logger.py:36`
- [ ] **Redundant explicit `conn.commit()` inside context managers** - `models/database.py:30,174`, `models/auth_database.py:42,69`, `pages/3_Cover_Letter.py:142,260` - context managers auto-commit

### Architecture

- [ ] **Pages access database directly** - All page files have `cursor.execute()` instead of using service layer (e.g., `pages/1_Resume_Optimizer.py:226`)
- [ ] **DEPRECATED function still in use** - `models/database.py:180-201` `get_or_create_default_profile()` is deprecated but used in `test_app.py:88`
- [ ] **Repeated auth boilerplate in every page** - All 9 pages duplicate init code; should use `@require_authentication` decorator consistently
- [ ] **Singleton LLM service not thread-safe** - `services/llm_service.py:224-232` has no synchronization
- [ ] **`@cached` decorator broken on instance methods** - `services/resume_analyzer.py:37-74` cache key includes `self`
- [ ] **In-memory cache not thread-safe** - `utils/cache.py:358-415` `MemoryCache` class has no locks
- [ ] **Duplicate `get_auth_db_connection()` code** - `utils/rate_limiter_auth.py:18-34` and `utils/audit_logger.py:22-38`

### Configuration

- [ ] **Hardcoded model name in pages** - `pages/6_Interview_Prep.py` and `pages/7_Salary_Negotiation.py` have 5+ instances of `"gpt-3.5-turbo"` instead of using config
- [ ] **Footer hardcodes "GPT-3.5"** - `app.py:180` says "Powered by OpenAI GPT-3.5" but `OPENAI_MODEL` can differ

### Testing

- [ ] **Minimal actual test coverage** - `test_app.py` only tests imports and basic DB init; no tests for:
  - Authentication flows / edge cases
  - Page implementations
  - Cover letter generation
  - Job tracking
  - Profile management
  - Cache decorator behavior
  - Concurrent user scenarios
  - Account lockout (10 failed attempts)
  - Rate limiting (5 attempts per 15 min)

### Performance

- [ ] **Potential N+1 queries** - 145 database execute calls across pages; `pages/5_Profile.py:569-577` does 3 separate COUNT queries
- [ ] **No database connection pooling** - 55+ context managers each open new connections
- [ ] **No query result caching** - Repeated `get_current_profile()` calls hit DB each time

---

## 🟡 MEDIUM PRIORITY

### Code Quality

- [ ] **196 print statements for production code** - Should use logging module instead
- [ ] **Generic exception messages expose internals** - `pages/2_Job_Tracker.py:64` shows `str(e)` to users
- [ ] **Large page files mixing concerns** - `pages/5_Profile.py` (586 lines), `pages/6_Interview_Prep.py` (471 lines), `pages/7_Salary_Negotiation.py` (467 lines)

### Security

- [ ] **Incomplete input sanitization** - Not all pages use `input_sanitizer` (e.g., `pages/1_Resume_Optimizer.py` doesn't sanitize file upload metadata)
- [ ] **Audit logging not comprehensive** - Missing audit for: resume upload/deletion, application status changes, data exports
- [ ] **No rate limiting on AI API calls** - Pages call LLM service without checking rate limiter

### Performance

- [ ] **Missing database indices** - `career_journal` and `cover_letters` queries filter by `profile_id` but missing indices

### Configuration

- [ ] **Missing configuration for sensitive parameters** - No config for: DB timeout, cache TTL defaults, password strength minimums, rate limit thresholds

### Error Handling

- [ ] **Inconsistent error handling across pages** - Some use try/except, others don't
- [ ] **No retry logic for failed API calls** - Single failure causes immediate error

---

## 📝 DOCUMENTATION LIES

- [ ] **`ARCHITECTURE.md` claims "Comprehensive test coverage (27 tests)"** - Only basic tests exist
- [ ] **`FINAL_VERIFIED_GRADE_A.md` claims Grade A code** - Many issues contradict this
- [ ] **`SECURITY.md` claims comprehensive audit logging** - Resume ops, data mods not actually audited
- [ ] **ATS analyzer scoring algorithm not documented** - Black box scoring with no explanation

---

## 💡 ARCHITECTURAL IMPROVEMENTS NEEDED

1. **Move database access out of pages** - Create proper repository/service pattern
2. **Add connection pooling** - Consider SQLAlchemy or similar
3. **Replace SQLite for production** - Use PostgreSQL for concurrent access
4. **Make rate limiting persistent** - Store in database, not session state
5. **Add proper retry/circuit breaker for API calls**
6. **Implement proper logging instead of print statements**
7. **Add comprehensive integration tests**

---

## ESTIMATED EFFORT

| Priority | Hours |
|----------|-------|
| Critical | 40-60 |
| High | 30-40 |
| Medium | 20-30 |
| **Total** | **~100+** |

---

*Generated from honest codebase analysis. This is technical debt that exists, not a wish list.*
