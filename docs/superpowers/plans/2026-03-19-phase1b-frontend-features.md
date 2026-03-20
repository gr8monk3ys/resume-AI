# Phase 1B: Frontend Features — Onboarding, Import, Nudges, Pricing, Upgrade

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Phase 1A backend (billing, feature gating, email) to the frontend with an onboarding wizard, job import modal, nudge bar, pricing page, upgrade modal, and settings billing tab.

**Architecture:** New React components + API bindings + modifications to existing pages. All components use existing design system (glass-button-*, surface-card, lucide-react icons). Stripe Checkout redirect (no embedded forms).

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS 4, @stripe/stripe-js, lucide-react

**Spec:** `docs/superpowers/specs/2026-03-19-phase1-resuboost-pro-design.md` (Sections 2, 3, 5, 6, 7)

**Depends on:** Phase 1A (backend foundation) — must be merged first
**Blocks:** Phase 1C (Email Automation)

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `frontend/src/components/OnboardingWizard.tsx` | 3-step onboarding overlay |
| Create | `frontend/src/components/JobImportModal.tsx` | URL paste → preview → save modal |
| Create | `frontend/src/components/NudgeBar.tsx` | Dashboard nudge cards |
| Create | `frontend/src/components/UpgradeModal.tsx` | Contextual upgrade prompt |
| Create | `frontend/src/components/PricingComparison.tsx` | Shared free/pro comparison table |
| Create | `frontend/src/components/EmailVerificationBanner.tsx` | Banner for unverified email |
| Create | `frontend/src/app/(app-shell)/pricing/page.tsx` | Pricing page (server) |
| Create | `frontend/src/app/(app-shell)/pricing/PricingPageClient.tsx` | Pricing page (client) |
| Create | `frontend/src/app/(app-shell)/verify-email/page.tsx` | Email verification landing |
| Modify | `frontend/src/lib/api.ts` | Add billingApi bindings |
| Modify | `frontend/src/types/index.ts` | Add billing/subscription types |
| Modify | `frontend/src/app/DashboardClient.tsx` | Add NudgeBar + onboarding check |
| Modify | `frontend/src/app/LandingPage.tsx` | Add pricing section |
| Modify | `frontend/src/app/(app-shell)/jobs/JobsPageClient.tsx` | Add import button + modal |
| Modify | `frontend/src/app/(app-shell)/settings/page.tsx` | Add billing tab |
| Modify | `frontend/package.json` | Add @stripe/stripe-js |

---

## Task 1: Add Types and API Bindings

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: Install Stripe JS**

Run: `cd frontend && npm install @stripe/stripe-js`

- [ ] **Step 2: Add billing types to types/index.ts**

Read `frontend/src/types/index.ts`, then append:

```typescript
// Billing & Subscription
export interface BillingStatus {
  plan: 'free' | 'pro_monthly' | 'pro_annual'
  status: 'active' | 'past_due' | 'canceled'
  current_period_end: string | null
  usage: UsageInfo[]
}

export interface UsageInfo {
  feature: string
  used: number
  limit: number | null
  reset_at: string | null
}

export interface UsageLimitError {
  error: 'limit_reached'
  feature: string
  limit: number
  used: number
  reset_at: string | null
  upgrade_url: string
}

// Onboarding
export interface OnboardingState {
  onboarding_completed: boolean
  onboarding_dismissed: boolean
  onboarding_step: number
}

// Job Import
export interface JobPreview {
  company: string
  title: string
  description: string
  location: string
  job_url: string
  source: string
}

export interface JobImportResult {
  id: number
  duplicate: boolean
  status?: string
}
```

- [ ] **Step 3: Add billingApi to api.ts**

Read `frontend/src/lib/api.ts`, then add after the last API export (nudgesApi):

```typescript
// Billing API
export const billingApi = {
  getStatus: async (): Promise<BillingStatus> => {
    const response = await fetchWithRetry(`${API_BASE}/api/billing/status`)
    return response.json()
  },

  createCheckout: async (priceId: string): Promise<{ checkout_url: string }> => {
    const response = await fetchWithRetry(`${API_BASE}/api/billing/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ price_id: priceId }),
    })
    return response.json()
  },

  createPortal: async (): Promise<{ portal_url: string }> => {
    const response = await fetchWithRetry(`${API_BASE}/api/billing/portal`, {
      method: 'POST',
    })
    return response.json()
  },
}

// Auth extensions (onboarding)
export const onboardingApi = {
  update: async (data: Partial<OnboardingState>): Promise<OnboardingState> => {
    const response = await fetchWithRetry(`${API_BASE}/api/auth/onboarding`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return response.json()
  },

  resendVerification: async (): Promise<{ message: string }> => {
    const response = await fetchWithRetry(`${API_BASE}/api/auth/resend-verification`, {
      method: 'POST',
    })
    return response.json()
  },
}
```

Note: Check how `fetchWithRetry` and `API_BASE` are used in the existing code and match the pattern exactly.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/lib/api.ts frontend/package.json frontend/package-lock.json
git commit -m "feat: add billing types and API bindings for subscription management"
```

---

## Task 2: Create PricingComparison Component

**Files:**
- Create: `frontend/src/components/PricingComparison.tsx`

- [ ] **Step 1: Create PricingComparison.tsx**

Shared component used by both landing page and /pricing page. Features:
- Monthly/Annual toggle with "Save 20%" badge
- Two-column comparison: Free vs Pro
- Feature rows with check/x icons
- CTA buttons: "Start Free" / "Upgrade to Pro"
- Props: `onUpgrade(priceId: string)`, `currentPlan?: string`

Use existing design system: `surface-card`, `glass-button-primary`, lucide-react `Check`, `X` icons.

Monthly: $15/mo. Annual: $144/yr ($12/mo effective).

Feature comparison table from spec Section 3 tier structure.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PricingComparison.tsx
git commit -m "feat: add PricingComparison component with free/pro tier comparison"
```

---

## Task 3: Create UpgradeModal Component

**Files:**
- Create: `frontend/src/components/UpgradeModal.tsx`

- [ ] **Step 1: Create UpgradeModal.tsx**

Triggered when free user hits a usage limit. Shows:
- "You've used X/Y [feature] today/this month"
- Feature name and limit info (passed as props)
- CTA to upgrade → calls `billingApi.createCheckout(priceId)` → redirects to Stripe Checkout URL
- Close button

Props: `feature: string`, `limit: number`, `used: number`, `resetAt: string | null`, `onClose: () => void`

Follow NudgeDraftModal pattern: fixed overlay + surface-card-strong + close button.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/UpgradeModal.tsx
git commit -m "feat: add UpgradeModal for contextual upgrade prompts"
```

---

## Task 4: Create JobImportModal Component

**Files:**
- Create: `frontend/src/components/JobImportModal.tsx`

- [ ] **Step 1: Read existing job import API bindings**

Read `frontend/src/lib/api.ts` to find job import endpoints. Look for `jobsApi` and any import-related methods. The backend endpoints are:
- `POST /api/jobs/import/url` — single job import
- `GET /api/jobs/import/preview?url=...` — preview without saving
- `POST /api/jobs/import/bulk` — multiple URLs

- [ ] **Step 2: Create JobImportModal.tsx**

Two-tab modal:
- **Tab 1: Single URL** — paste field, "Preview" button shows extracted data, "Add to Pipeline" saves
- **Tab 2: Bulk Import** — textarea for multiple URLs, progress indicator, results summary

Props: `onClose: () => void`, `onImported: () => void` (refresh job list)

Internal state: `activeTab`, `url`, `preview`, `isLoading`, `error`, `bulkUrls`, `bulkResults`

Follow existing modal pattern. Use `glass-input` for text fields, `glass-button-primary` for actions.

Handle duplicate detection: if API returns `duplicate: true`, show "Already in pipeline" message.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/JobImportModal.tsx
git commit -m "feat: add JobImportModal with URL preview and bulk import"
```

---

## Task 5: Create NudgeBar Component

**Files:**
- Create: `frontend/src/components/NudgeBar.tsx`

- [ ] **Step 1: Read nudgesApi and NudgeDraftModal**

Read `frontend/src/lib/api.ts` for nudgesApi methods and `frontend/src/components/NudgeDraftModal.tsx` for modal pattern.

- [ ] **Step 2: Create NudgeBar.tsx**

Horizontally scrollable cards showing top 3 nudges. Each card has:
- Icon + context line (e.g., "Follow up with Stripe — applied 7 days ago")
- Primary action button ("Draft Email", "Start Prep", "Review")
- Dismiss button (×)

Props: none (fetches nudges internally)

Internal state: `nudges`, `isLoading`, `dismissedIds` (stored in localStorage)

Actions:
- "Draft Email" → opens NudgeDraftModal (already exists)
- "Start Prep" → navigate to `/interview`
- "Review" → navigate to `/resumes`
- Dismiss → add to localStorage `resuboost_dismissed_nudges` with 7-day expiry

Returns null if no nudges or all dismissed.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/NudgeBar.tsx
git commit -m "feat: add NudgeBar component for dashboard nudge cards"
```

---

## Task 6: Create OnboardingWizard Component

**Files:**
- Create: `frontend/src/components/OnboardingWizard.tsx`

- [ ] **Step 1: Create OnboardingWizard.tsx**

Full-page overlay with 3 steps + progress indicator:

**Step 1: Import Your First Job**
- Big text field: "Paste a job posting URL"
- Preview button → calls job import preview API
- Shows extracted data (company, title, location)
- "Add to Pipeline" button → saves job
- Skip button

**Step 2: Upload Your Resume**
- Drag-and-drop zone for PDF/DOCX
- Uses existing resume upload endpoint
- Shows parsed content preview
- Skip button

**Step 3: See the Magic**
- If both job AND resume provided → call AI tailor-resume endpoint
- Show side-by-side: original vs optimized
- If only one provided → show prompt to complete the other
- "Go to Dashboard" button

Props: `onComplete: () => void`, `onDismiss: () => void`

Internal state: `currentStep`, `importedJob`, `uploadedResume`, `tailoredResume`, `isLoading`

Calls `onboardingApi.update({ step: N })` on each step transition.
Calls `onboardingApi.update({ completed: true })` on finish.
Calls `onboardingApi.update({ dismissed: true })` on dismiss.

Uses full-viewport overlay: `fixed inset-0 z-50 bg-[var(--surface)]`.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/OnboardingWizard.tsx
git commit -m "feat: add OnboardingWizard with 3-step first-5-minutes flow"
```

---

## Task 7: Wire Components into Existing Pages

**Files:**
- Modify: `frontend/src/app/DashboardClient.tsx` — Add NudgeBar + onboarding check
- Modify: `frontend/src/app/(app-shell)/jobs/JobsPageClient.tsx` — Add import button + modal
- Modify: `frontend/src/app/LandingPage.tsx` — Add pricing section
- Modify: `frontend/src/app/(app-shell)/settings/page.tsx` — Add billing tab

- [ ] **Step 1: Wire NudgeBar + OnboardingWizard to Dashboard**

Read `frontend/src/app/DashboardClient.tsx`.

Add state:
```typescript
const [showOnboarding, setShowOnboarding] = useState(false)
```

In the useEffect that fetches data, also check if user needs onboarding:
```typescript
// After auth check, check onboarding state
if (user && !user.onboarding_completed && !user.onboarding_dismissed) {
  setShowOnboarding(true)
}
```

Add to render, after DashboardHero section:
```tsx
{showOnboarding && (
  <OnboardingWizard
    onComplete={() => setShowOnboarding(false)}
    onDismiss={() => setShowOnboarding(false)}
  />
)}
<NudgeBar />
```

- [ ] **Step 2: Wire Import button to Jobs page**

Read `frontend/src/app/(app-shell)/jobs/JobsPageClient.tsx`.

Add state: `showImportModal` boolean.
Add import button in `JobsPageHeader` button group.
Add `<JobImportModal />` render when `showImportModal` is true.
On import complete, refresh job list.

- [ ] **Step 3: Add pricing section to Landing page**

Read `frontend/src/app/LandingPage.tsx`.

Add `<PricingComparison />` section before the final CTA. The `onUpgrade` prop navigates to `/register` (since landing page is for non-logged-in users).

- [ ] **Step 4: Add billing tab to Settings**

Read `frontend/src/app/(app-shell)/settings/page.tsx`.

Add `'billing'` to `SettingsTabId` type and `TABS` array.
Add billing section that shows:
- Current plan badge
- Usage meters (fetched from billingApi.getStatus)
- "Manage Subscription" button → billingApi.createPortal → redirect
- Email notification toggle

- [ ] **Step 5: Run TypeScript check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/DashboardClient.tsx frontend/src/app/LandingPage.tsx frontend/src/app/\(app-shell\)/jobs/JobsPageClient.tsx frontend/src/app/\(app-shell\)/settings/page.tsx
git commit -m "feat: wire onboarding, nudges, import, pricing, and billing to existing pages"
```

---

## Task 8: Create Pricing and Verify-Email Pages

**Files:**
- Create: `frontend/src/app/(app-shell)/pricing/page.tsx`
- Create: `frontend/src/app/(app-shell)/pricing/PricingPageClient.tsx`
- Create: `frontend/src/app/(app-shell)/verify-email/page.tsx`
- Create: `frontend/src/components/EmailVerificationBanner.tsx`

- [ ] **Step 1: Create pricing page**

Server component `page.tsx` that renders `PricingPageClient`.
Client component with PricingComparison, billing status check, and Stripe checkout redirect.

- [ ] **Step 2: Create verify-email page**

Simple page that reads `?token=` from URL, calls `/api/auth/verify-email?token=...`, shows success/error.

- [ ] **Step 3: Create EmailVerificationBanner**

Small banner shown when `user.email_verified === false`. Shows "Verify your email" with resend button.

- [ ] **Step 4: Run build**

Run: `cd frontend && npm run build`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(app-shell\)/pricing/ frontend/src/app/\(app-shell\)/verify-email/ frontend/src/components/EmailVerificationBanner.tsx
git commit -m "feat: add pricing page, email verification page, and verification banner"
```

---

## Task 9: Final Verification

- [ ] **Step 1: TypeScript check**
Run: `cd frontend && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 2: Build**
Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Run existing tests**
Run: `cd frontend && npx vitest run`
Expected: All existing tests pass

- [ ] **Step 4: Verify git status clean**
Run: `git status`
