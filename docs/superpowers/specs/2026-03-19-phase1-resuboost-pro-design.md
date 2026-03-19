# Phase 1 Design: ResuBoost Pro — From Tool to Product

**Date:** 2026-03-19
**Status:** Approved
**Target user:** Tech workers in active job search (expand to mid-career and new grads later)
**Go-to-market:** C (tech workers) → B (mid-career) → A (new grads)
**Timeline:** No hard deadline — build it right

---

## 1. Product Strategy

### Problem

ResuBoost AI is a solid engineering project (auth, Kanban tracker, multi-provider AI, resume tailoring, cover letters, interview prep, analytics, career journal, STAR stories, company research, interview events) but has no monetization, no email infrastructure, and key backend features (job import, nudges, scheduler) are not surfaced in the frontend.

The core gap: nothing prevents a user from doing the same workflow with ChatGPT + Notion. ResuBoost must create a closed-loop workflow that's genuinely harder to replicate manually.

### Strategy

**Phase 1 (this spec):** Ship the wedge — auto-import jobs from URLs, onboard users in under 5 minutes, gate features behind a freemium paywall, and add email-based nudges that keep users engaged.

**Phase 2 (future):** Smart automation — proactive follow-up drafts, interview prep triggered by calendar, weekly digest emails, re-engagement flows.

**Phase 3 (future):** Company intelligence moat — crowdsourced interview data, salary ranges, process timelines for top tech companies.

### Existing Infrastructure (leveraged, not rebuilt)

| Component | Status | Location |
|-----------|--------|----------|
| Job scraper (LinkedIn, Indeed, Glassdoor, Lever, Greenhouse, Workday, GitHub) | Mature | `backend/app/services/job_importer.py` |
| APScheduler (recurring scrape jobs) | Functional | `backend/app/services/scheduler.py` |
| WebSocket notifications (JWT auth, multi-tab) | Functional | `backend/app/routers/websocket.py` |
| Nudge system (6 types, AI draft generation) | Functional | `backend/app/routers/nudges.py` |
| Job alerts (rule matching + WebSocket push) | Functional | `backend/app/services/job_alerts.py` |
| Landing page (hero, features, CTAs) | Complete | `frontend/src/app/LandingPage.tsx` |
| Email draft generation (LLM-powered) | Functional | `backend/app/routers/nudges.py`, `ai.py` |
| Docker deployment (multi-stage, PostgreSQL, Redis) | Production-ready | `Dockerfile`, `docker-compose.yml` |

---

## 2. Onboarding: The First 5 Minutes

### Goal

New user → first "aha moment" in under 5 minutes.

### Flow

```
Landing page → Sign up → Onboarding wizard (3 steps) → Dashboard with data
```

### Step 1: "Import your first job" (the hook)

- Big text field: "Paste a job posting URL"
- Supported sources: LinkedIn, Indeed, Glassdoor, Lever, Greenhouse, Workday
- Live preview: show extracted data (company, title, description, location) before saving
- User clicks "Add to pipeline" → creates a Kanban card with status "Bookmarked"
- Uses existing `POST /api/jobs/import/preview` for preview, `POST /api/jobs/import/url` to save
- Skip button available (but discouraged via copy)

### Step 2: "Upload your resume"

- Drag-and-drop zone for PDF/DOCX
- Parse and display resume content preview
- Uses existing resume upload endpoint
- Skip button available

### Step 3: "See the magic"

- If both job AND resume were provided: immediately run AI resume tailoring
- Show side-by-side: "Your resume" vs "Optimized for [Company] [Role]"
- Uses existing `POST /api/ai/tailor-resume`
- If only one was provided: show a contextual prompt to complete the other
- This is the conversion moment — the user sees concrete value

### Post-onboarding

- Dashboard shows their imported job card and resume
- Prompt: "Import more jobs to start tracking your pipeline"
- Onboarding state tracked in `User` model:
  - `onboarding_completed: bool` (default false)
  - `onboarding_dismissed: bool` (default false)
  - `onboarding_step: int` (default 0 — tracks progress for resuming)
- Users who skip see it again on next login until completed or dismissed
- Endpoint: `PATCH /api/auth/onboarding` accepts `{ completed, dismissed, step }`

### Component

- `frontend/src/components/OnboardingWizard.tsx` — 3-step wizard with progress indicator
- Renders as a full-page overlay after first login
- Each step is self-contained with its own loading/error states

---

## 3. Monetization: Stripe + Feature Gating

### Tier Structure

| Feature | Free | Pro ($15/mo or $144/yr) |
|---------|------|-------------------------|
| Job imports | 5/month | Unlimited |
| AI generations | 3/day | Unlimited |
| Job tracking | 20 active jobs | Unlimited |
| Resume versions | 2 total | Unlimited |
| Nudges/follow-ups | View only | AI drafts + email sending |
| Analytics | Basic (status counts) | Full (funnels, source perf, trends) |
| Interview prep | 1/week | Unlimited |
| Company research | 3 total | Unlimited |
| Scheduled imports | No | Yes (max 5 jobs, min 30-min interval) |
| Email notifications | No | Yes |

### Usage Limit Reset Rules

| Feature | Limit (Free) | Reset | Enforcement Point |
|---------|-------------|-------|-------------------|
| AI generations | 3/day | Midnight UTC | `POST /api/ai/*` |
| Job imports | 5/month | 1st of month 00:00 UTC | `POST /api/jobs/import/*` |
| Active jobs | 20 concurrent | N/A (count-based) | `POST /api/jobs` |
| Resume versions | 2 total | N/A (count-based) | `POST /api/resumes/upload` |
| Interview prep | 1/week | Monday 00:00 UTC | `POST /api/ai/interview-prep` |
| Company research | 3 total | N/A (count-based) | `POST /api/company-research` |

Usage is counted at request start time. A request starting at 23:59:59 counts against the current period even if it completes after midnight.

### Pricing Rationale

- Free tier is enough to experience the product: import a few jobs, get one AI tailoring, see the Kanban board
- The paywall hits when users are actively job searching (10+ applications) — exactly when willingness to pay is highest
- $15/mo positions against Simplify.jobs ($30/mo) and Teal ($29/mo) as the affordable alternative
- Annual discount (20%) encourages commitment and reduces churn

### Backend Architecture

**New model: `Subscription`**
```
subscription:
  id: int (PK)
  user_id: int (FK → User, unique)
  stripe_customer_id: str
  stripe_subscription_id: str (nullable — null for free tier)
  plan: enum(free, pro_monthly, pro_annual)
  status: enum(active, past_due, canceled)
  current_period_end: datetime (nullable)
  created_at: datetime
  updated_at: datetime
```

**New model: `UsageRecord`**
```
usage_record:
  id: int (PK)
  user_id: int (FK → User)
  feature: str (ai_generation, job_import, interview_prep)
  period_start: date
  count: int
  created_at: datetime

  index: (user_id, feature, period_start)
```

**New router: `/api/billing`**
- `POST /api/billing/checkout` — Create Stripe Checkout session, return URL. Rate limit: 10/min.
- `POST /api/billing/portal` — Create Stripe Customer Portal session, return URL. Rate limit: 10/min.
- `POST /api/billing/webhook` — Stripe webhook handler. No JWT auth. Verified via `stripe.Webhook.construct_event()` using `STRIPE_WEBHOOK_SECRET`. Idempotency enforced via Stripe event ID deduplication.
- `GET /api/billing/status` — Return current subscription status + usage counts. Rate limit: 60/min.

**Webhook events handled:**
- `checkout.session.completed` → create/update Subscription, set plan to pro
- `customer.subscription.updated` → update status, period end, plan
- `customer.subscription.deleted` → set plan to free, status to canceled
- `invoice.payment_failed` → set status to past_due, send email via email_service

**Feature gating middleware: `check_usage_limit(feature: str)`**
- FastAPI dependency that checks subscription tier and usage counts
- Steps: (1) load subscription for current_user.id, (2) verify subscription.status is active, (3) check usage count vs tier limit
- Returns `UsageLimitError` response (see schemas) with status 429
- If no Subscription record found, treat as free tier (defensive default)

**Response schema for limit errors:**
```python
class UsageLimitError(BaseModel):
    error: Literal["limit_reached"]
    feature: str       # "AI generations", "Job imports", etc.
    limit: int
    used: int
    reset_at: datetime  # When limit resets (null for count-based limits)
    upgrade_url: str    # "/pricing"
```

### Billing Edge Cases

**Downgrade (Pro → Free):**
- User retains Pro access until `current_period_end`
- After period ends: soft limit enforcement (show upgrade modal, don't delete data)
- Jobs beyond 20-limit: read-only, can't add new until under limit
- Resume versions beyond 2: read-only, can't upload new until deleted

**Payment Failed:**
- Grace period: 7 days past_due before feature lockout
- Email sent immediately on failure, reminders at day 3 and day 6
- After 7 days: treat as free tier (soft limits, no data loss)
- Stripe handles retry logic (3 attempts over 3 weeks)

**Cancellation:**
- Set status to 'canceled' but keep Pro features until `current_period_end`
- At period end: downgrade to free tier via `customer.subscription.deleted` webhook

**Past Due Upgrade:**
- Block new checkout, show "Update payment method first" → redirect to Stripe Customer Portal

### Frontend Architecture

**Pricing section on landing page:**
- Toggle: Monthly / Annual (with "Save 20%" badge)
- Two-column: Free vs Pro comparison
- CTA: "Start Free" / "Upgrade to Pro"

**Dedicated pricing page (`/pricing`):**
- Same comparison component as landing page, for logged-in upgrade flow
- Both use shared `PricingComparison` component for consistency

**Upgrade modal (`UpgradeModal.tsx`):**
- Triggered when user hits a limit
- Contextual: "You've used 3/3 AI generations today. Upgrade to Pro for unlimited."
- Shows the specific feature they're blocked on
- CTA redirects to Stripe Checkout

**Settings → Billing tab:**
- Current plan display
- Usage meters (AI generations, imports, active jobs)
- "Manage subscription" → Stripe Customer Portal (handles payment methods, invoices, cancellation)
- No custom billing UI built — Stripe Customer Portal handles complexity

**Stripe integration (frontend):**
- `@stripe/stripe-js` for Checkout redirect only
- No embedded payment forms — Stripe Checkout handles PCI compliance

### Stripe Setup (Manual)

Price IDs (`STRIPE_PRO_MONTHLY_PRICE_ID`, `STRIPE_PRO_ANNUAL_PRICE_ID`) must be created manually in the Stripe Dashboard:
1. Create a Product named "ResuBoost Pro"
2. Add two Prices: $15/mo recurring, $144/yr recurring
3. Copy Price IDs to environment variables
4. Configure Customer Portal in Stripe Dashboard (allow plan changes, cancellation)
5. Set up webhook endpoint URL pointing to `/api/billing/webhook`

---

## 4. Email Integration

### Provider

**Resend.** Simplest API, Python SDK (`resend`), free tier (3,000 emails/mo), handles deliverability.

### Emails Sent

| Trigger | Email | Tier | Priority |
|---------|-------|------|----------|
| Registration | Welcome + verify email link | All | Day 1 |
| After onboarding complete | "Here's what to do next" with 3 action items | All | Day 1 |
| Nudge: follow-up overdue | "Time to follow up with [Company]" with AI draft inline | Pro | Core |
| Nudge: interview in 48h | "Interview prep ready for [Company]" with link to prep page | Pro | Core |
| Weekly (Sunday evening) | "Your week ahead" digest: upcoming interviews, overdue follow-ups, pipeline stats | Pro | Retention |
| Hit free tier limit | "You've hit your limit — upgrade to keep going" with pricing link | Free | Conversion |
| Payment success | Receipt (handled by Stripe, not us) | Pro | Transactional |
| 3 days inactive | "Your job search pipeline has 2 items needing attention" | Pro | Re-engagement |
| Payment failed | "Update your payment method to keep Pro features" | Pro | Transactional |

### Backend Architecture

**New service: `email_service.py`**
- Thin wrapper around Resend Python SDK
- Methods: `send_welcome`, `send_verification`, `send_onboarding_complete`, `send_nudge`, `send_weekly_digest`, `send_upgrade_prompt`, `send_payment_failed`
- Each method accepts user + context data, renders HTML from inline f-string templates
- Templates are inline in the service methods (not separate files). Tested by asserting rendered HTML contains expected content. Preview during dev by logging to console when `DEBUG=true`.
- No template engine — add Jinja2 later if templates grow complex

**Email sending strategy:**
- Transactional emails (welcome, verify, payment): sent inline in request handler
- Nudge/digest/re-engagement emails: sent via dedicated email scheduler (see below)

**Email verification flow:**
- On registration: generate UUID token, store in `user.email_verification_token`
- Send welcome email with link: `{APP_URL}/verify-email?token={token}`
- Endpoint: `GET /api/auth/verify-email?token=...` → validate token, set `email_verified = true`
- Unverified users: allowed to use app, shown banner with "Resend verification" button
- Endpoint: `POST /api/auth/resend-verification` → regenerate token, send email
- Token expiry: 7 days (check `updated_at` + 7 days, regenerate if expired)

**New service: `email_scheduler.py`**
- Separate APScheduler instance dedicated to email tasks (existing scheduler.py stays focused on scraping)
- Registered jobs:
  - `check_and_send_nudge_emails` — runs every hour, checks Pro users with nudge conditions met
  - `send_weekly_digest` — runs Sunday 18:00 UTC (no per-user timezone in Phase 1, add in Phase 2)
  - `check_inactive_users` — runs daily 10:00 UTC, sends re-engagement if `last_active_at` > 3 days ago
- Started in `main.py` app startup alongside existing scheduler

**User model additions:**
- `email_verified: bool` (default false)
- `email_notifications: bool` (default true)
- `email_verification_token: str` (nullable)
- `last_active_at: datetime`
- `onboarding_completed: bool` (default false)
- `onboarding_dismissed: bool` (default false)
- `onboarding_step: int` (default 0)

**Unsubscribe:**
- Every email includes unsubscribe link
- Link hits `GET /api/profile/unsubscribe?token=...` → sets `email_notifications = false`
- One-click unsubscribe header (RFC 8058) for Gmail/Yahoo compliance

---

## 5. Job Import UX

### Current State

Backend scraper is mature (`job_importer.py`, 45KB). Supports LinkedIn, Indeed, Glassdoor, Lever, Greenhouse, Workday, GitHub repos. Endpoints exist for single/bulk/preview/GitHub import. Frontend has API bindings but limited UI.

### Backend Fix: Deduplication

The existing `_save_job_to_db()` function has no duplicate check. Add before `db.add(job)`:
```python
existing = db.query(JobApplication).filter(
    JobApplication.profile_id == profile_id,
    JobApplication.job_url == job_data.job_url
).first()
if existing:
    return {"duplicate": True, "existing_id": existing.id, "status": existing.status}
```

No fuzzy matching on (company, position) in Phase 1 — URL-based dedup only. Fuzzy matching is Phase 2.

### New Frontend Component: `JobImportModal.tsx`

**Triggered from:** Kanban board header "Import Job" button + onboarding wizard step 1

**Tabs:**

**Tab 1: Single URL (default)**
- Paste field with auto-detect source icon (LinkedIn, Indeed, etc.)
- "Preview" button → shows extracted data (company, title, location, description)
- "Add to Pipeline" button → saves as Bookmarked job
- If duplicate detected: show "Already in your pipeline at status [X]" with link to existing card
- Error states: invalid URL, unsupported source, scrape failed, rate limited

**Tab 2: Bulk Import**
- Textarea: paste multiple URLs, one per line
- Progress indicator: "Importing 3/5 jobs..."
- Results: success count, failed URLs with reasons, duplicates skipped
- Uses `POST /api/jobs/import/bulk`

**Tab 3: GitHub Repos (SimplifyJobs)**
- Dropdown: New Grad Positions / Internships
- Filters: location, role type
- Preview list with checkboxes → import selected
- Uses `POST /api/jobs/import/github`

**Source badges on Kanban cards:**
- Small icon (LinkedIn, Indeed, etc.) on each card imported via URL
- Stored in `source` field on `JobApplication`

---

## 6. Nudge System UX

### Current State

Backend generates 6 nudge types with AI drafts (`nudges.py`). Frontend has API bindings (`nudgesApi.list()`, `nudgesApi.draft()`). `NudgeDraftModal.tsx` already exists (144 lines, functional with draft generation, copy, regenerate).

### New Frontend Component: `NudgeBar.tsx`

**Location:** Top of Dashboard, below header

**Layout:** Horizontally scrollable cards, max 3 visible, "See all" link

**Card format:**
```
[Icon] [Context line]                    [Primary Action] [Dismiss]

Follow up with Stripe — applied 7 days ago        [Draft Email]  [x]
Interview at Google in 2 days                      [Start Prep]   [x]
ML Engineer resume not updated in 30 days          [Review]       [x]
```

**Priority ordering (from backend):**
1. Overdue follow-ups
2. Upcoming interview prep
3. Thank-you notes
4. Stale application follow-ups
5. Application velocity
6. Resume freshness

**Actions:**
- "Draft Email" → opens existing `NudgeDraftModal` with AI-generated email, copy button, and (Pro only) new "Send" button
- "Start Prep" → navigates to Interview Center with relevant company pre-loaded
- "Review" → navigates to Resumes page
- "Dismiss" → hides nudge for 7 days (tracked in localStorage — intentionally client-side for simplicity; cross-device sync is Phase 2)

**Email integration (Pro):**
- Nudges that fire also send email notification (if `email_notifications` is true)
- Email includes AI-drafted content inline
- Click-through link to app for full interaction

---

## 7. Architecture Summary

### New Files

```
backend/
├── app/models/subscription.py          # Stripe subscription + UsageRecord models
├── app/routers/billing.py              # Checkout, portal, webhooks
├── app/schemas/billing.py              # Pydantic models (checkout, status, UsageLimitError)
├── app/services/email_service.py       # Resend wrapper + inline HTML templates
├── app/services/email_scheduler.py     # Dedicated APScheduler for email jobs
├── app/services/billing_service.py     # Stripe business logic
├── app/middleware/feature_gate.py      # Usage limit checking dependency

frontend/
├── src/app/(app-shell)/pricing/page.tsx              # Pricing page (server component)
├── src/app/(app-shell)/pricing/PricingPageClient.tsx  # Pricing page (client component)
├── src/app/(app-shell)/verify-email/page.tsx          # Email verification landing page
├── src/components/OnboardingWizard.tsx                # 3-step onboarding
├── src/components/UpgradeModal.tsx                    # Contextual upgrade prompt
├── src/components/NudgeBar.tsx                        # Dashboard nudge cards
├── src/components/JobImportModal.tsx                  # Import flow modal
├── src/components/PricingComparison.tsx               # Shared pricing table component
├── src/components/EmailVerificationBanner.tsx         # Banner for unverified users
```

### Modified Files

```
backend/
├── app/models/user.py                  # email_verified, email_notifications, last_active_at, onboarding fields
├── app/models/__init__.py              # Register Subscription, UsageRecord models
├── app/main.py                         # Register billing router, start email_scheduler
├── app/config.py                       # Stripe + Resend + feature flag env vars
├── app/routers/auth.py                 # verify-email, resend-verification, onboarding endpoints
├── app/routers/ai.py                   # Add feature_gate dependency
├── app/routers/job_import.py           # Add feature_gate dependency + deduplication
├── app/routers/jobs.py                 # Add active job count check for free tier
├── app/routers/resumes.py              # Add feature_gate dependency
├── app/routers/company_research.py     # Add feature_gate dependency
├── app/routers/interview_events.py     # Add feature_gate dependency

frontend/
├── src/app/LandingPage.tsx             # Add pricing section using PricingComparison
├── src/app/DashboardClient.tsx         # Add NudgeBar, onboarding check
├── src/app/(app-shell)/jobs/JobsPageClient.tsx  # Add import button + modal trigger
├── src/app/(app-shell)/settings/page.tsx        # Add billing tab, notification prefs
├── src/lib/api.ts                      # Add billing + import API bindings
├── src/components/jobs/KanbanBoard.tsx  # Source badges on cards
├── src/components/jobs/SortableJobCard.tsx # Source badge display
├── src/components/NudgeDraftModal.tsx   # Add "Send" button (Pro only)
```

### Database Migrations

```sql
-- New tables
CREATE TABLE subscriptions (...);
CREATE TABLE usage_records (...);

-- New indexes
CREATE INDEX idx_usage_user_feature_period ON usage_records(user_id, feature, period_start);

-- Existing user migration
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN email_notifications BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN email_verification_token VARCHAR;
ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP;
ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN onboarding_dismissed BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN onboarding_step INTEGER DEFAULT 0;

-- Backfill: create free-tier subscription for all existing users
INSERT INTO subscriptions (user_id, plan, status, created_at, updated_at)
SELECT id, 'free', 'active', NOW(), NOW() FROM users
WHERE id NOT IN (SELECT user_id FROM subscriptions);
```

### New Dependencies

```
# Backend (pyproject.toml)
resend >= 2.0.0
stripe >= 8.0.0

# Frontend (package.json)
@stripe/stripe-js ^4.0.0
```

### New Environment Variables

```bash
# Stripe
STRIPE_SECRET_KEY=sk_...
STRIPE_PUBLISHABLE_KEY=pk_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_MONTHLY_PRICE_ID=price_...
STRIPE_PRO_ANNUAL_PRICE_ID=price_...

# Email
RESEND_API_KEY=re_...
FROM_EMAIL=ResuBoost <noreply@resuboost.com>

# App
APP_URL=https://resuboost.com  # For email links

# Feature flags (for safe rollout)
ENABLE_BILLING=false
ENABLE_EMAIL=false
ENABLE_ONBOARDING=false
ENABLE_NUDGE_EMAILS=false
```

### Feature Flag Strategy

All Phase 1 features are behind environment flags for safe rollout:

| Flag | Controls | Default |
|------|----------|---------|
| `ENABLE_BILLING` | Stripe checkout, feature gating enforcement | false |
| `ENABLE_EMAIL` | All outbound email sending | false |
| `ENABLE_ONBOARDING` | Onboarding wizard display | false |
| `ENABLE_NUDGE_EMAILS` | Email notifications for nudges | false |

When a flag is off, the feature degrades gracefully:
- `ENABLE_BILLING=false` → all users treated as Pro (no limits)
- `ENABLE_EMAIL=false` → email methods log to console instead of sending
- `ENABLE_ONBOARDING=false` → wizard never shows, users go straight to dashboard
- `ENABLE_NUDGE_EMAILS=false` → nudges show in UI only, no emails

**Deployment stages:**
1. Deploy with all flags OFF → verify health
2. Enable `ENABLE_BILLING` → test checkout flow with Stripe test keys
3. Enable `ENABLE_EMAIL` → test welcome emails
4. Enable `ENABLE_ONBOARDING` → test new user flow
5. Enable `ENABLE_NUDGE_EMAILS` → test Pro user emails

---

## 8. Implementation Order

Build in this sequence to unlock value incrementally:

1. **Subscription model + feature gating** — Foundation for everything else. Create Subscription and UsageRecord models, feature_gate middleware (default all users to free tier). Backfill existing users with free-tier subscriptions.
2. **Email service** — Resend integration, welcome email, verification flow. Create email_service.py and email_scheduler.py.
3. **Stripe integration** — Checkout, portal, webhooks, billing router. Now users can pay.
4. **Onboarding wizard** — The first-5-minutes flow. Wires existing import + resume + AI features.
5. **Job import modal** — Surfaces the existing scraper backend in the Jobs page. Add deduplication to backend.
6. **Nudge bar** — Surfaces the existing nudge backend on the Dashboard. Add "Send" button to existing NudgeDraftModal.
7. **Landing page pricing section** — Add pricing comparison to existing landing page + dedicated /pricing page.
8. **Upgrade modal** — Contextual prompts when hitting limits.
9. **Email nudges + weekly digest** — Wire email_scheduler jobs for Pro users.
10. **Settings billing tab** — Plan display, usage meters, manage subscription link, notification preferences.

---

## 9. Success Criteria

Phase 1 is complete when:

- [ ] New user can sign up → onboard (import job + upload resume + see AI tailoring) in under 5 minutes
- [ ] Free tier limits enforce correctly across all gated endpoints
- [ ] User can upgrade to Pro via Stripe Checkout and access unlimited features
- [ ] Stripe Customer Portal handles payment methods, invoices, cancellation
- [ ] Welcome email + verification email send on registration
- [ ] Email verification flow works (click link → verified)
- [ ] Job import modal works for single URL, bulk, and GitHub repo sources
- [ ] Duplicate job URLs detected and surfaced in import modal
- [ ] Nudge bar shows on dashboard with dismiss + action buttons
- [ ] Pro users receive email notifications for nudges
- [ ] Weekly digest email sends to Pro users with active pipelines
- [ ] Landing page has pricing section with free/pro comparison
- [ ] Upgrade modal appears when free user hits a limit
- [ ] Settings page shows billing status and usage meters
- [ ] All feature flags work (features degrade gracefully when off)
- [ ] Downgrade/cancellation/payment failure handled gracefully (no data loss)

---

## 10. Testing Requirements

### Unit Tests (backend)

- **Billing service**: subscription creation, plan changes, usage counting, limit checking
- **Feature gate middleware**: all tier limits, reset logic, edge cases (no subscription record, expired past_due)
- **Email service**: template rendering (assert HTML contains expected content), unsubscribe token generation
- **Webhook handler**: all event types, signature verification failure, idempotency (duplicate event ID)

### Integration Tests (backend)

- Stripe webhook flows: checkout complete → subscription active, payment failed → past_due → grace period → lockout
- Usage limit enforcement: hit limit → 429 response → upgrade → access granted
- Email verification: register → receive token → verify → status updated
- Onboarding state: track progress, resume from step, dismiss

### E2E Tests (frontend)

- Onboarding flow: all 3 steps, skip handling, resume from interrupted step
- Upgrade flow: hit limit → modal → Stripe Checkout (use Stripe test mode)
- Job import: URL paste → preview → save → appears in Kanban, duplicate detection
- Nudge bar: displays nudges, dismiss works, actions navigate correctly

### Test Infrastructure

- Use Stripe test mode keys (`sk_test_...`) for all billing tests
- Use Resend test API key for email tests (no real emails sent in CI)
- Seed free and pro test users in conftest.py fixtures
- Stripe webhook tests use `stripe.Webhook.construct_event()` with test signing secret

---

## 11. Out of Scope (Phase 2+)

- Chrome extension for job import
- Company interview intelligence database
- Resume A/B testing with outcome tracking
- SMS/push notifications
- Team/enterprise tier
- Referral program
- Mobile app
- OAuth sign-in (Google, GitHub)
- Advanced analytics (time-to-hire predictions)
- Per-user timezone for weekly digest
- Cross-device nudge dismissal sync
- Fuzzy job deduplication (company + position matching)
- Free trial period
