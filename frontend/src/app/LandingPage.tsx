import {
  ArrowRight,
  Briefcase,
  CheckCircle2,
  FileText,
  Filter,
  MessagesSquare,
  Radar,
} from 'lucide-react'
import Link from 'next/link'

import { BrandMark } from '@/components/BrandMark'
import { PricingComparison } from '@/components/PricingComparison'

const landingStats = [
  { label: 'Role briefs', value: 'Target roles, locations, and exclusions' },
  { label: 'Resume tuning', value: 'ATS scoring, keyword gaps, and version control' },
  { label: 'Follow-through', value: 'Application memory and interview context in one loop' },
]

const productCards = [
  {
    icon: Filter,
    title: 'Search briefs that stay focused',
    description:
      'Define roles, seniority, locations, and company rules once so the rest of the search starts from signal instead of noise.',
  },
  {
    icon: Briefcase,
    title: 'A pipeline that remembers the details',
    description:
      'Track where each application stands, what changed last, and which companies need follow-up before momentum slips.',
  },
  {
    icon: FileText,
    title: 'Resume versions tied to the opportunity',
    description:
      'Keep tailored resumes, ATS feedback, and document drafts close to the jobs they are meant to win.',
  },
  {
    icon: MessagesSquare,
    title: 'Interview prep from the same context',
    description:
      'Prepare answers, notes, and follow-ups without losing the trail of the application that led there.',
  },
]

const workflowPanels = [
  {
    title: 'Search with intent',
    description:
      'Capture the job families you actually want, set company rules, and keep the week aligned around a short target list.',
    bullets: ['Role priorities stay visible', 'Filters reduce wasted tabs', 'Focus shifts are easy to update'],
  },
  {
    title: 'Run the application loop cleanly',
    description:
      'Move from bookmarked leads to applied, interview, and offer without scattering notes across docs and browser tabs.',
    bullets: ['Recent movement is obvious', 'Follow-ups stop slipping', 'Pipeline health is visible at a glance'],
  },
  {
    title: 'Keep materials ready',
    description:
      'Tune resumes, generate documents, and prepare interviews from the same source material so every step compounds.',
    bullets: ['Resume versions stay organized', 'Documents stay on-message', 'Interview prep pulls from real job context'],
  },
]

function LandingHeader() {
  return (
    <header className="shell-width pt-6">
      <div className="surface-card-strong flex items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <BrandMark subdued />
        <nav className="flex items-center gap-2 sm:gap-3" aria-label="Marketing navigation">
          <Link
            href="/login"
            className="rounded-full px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-white/70"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 rounded-full bg-[#10243f] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0b1728]"
          >
            Start free
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </nav>
      </div>
    </header>
  )
}

function SearchPreview() {
  return (
    <div className="surface-card-strong rise-in overflow-hidden p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
            Search Brief Preview
          </p>
          <h2 className="mt-2 font-display text-2xl font-semibold tracking-[-0.05em] text-slate-950">
            Frontend roles with clean signals
          </h2>
        </div>
        <span className="rounded-full bg-[color:var(--signal-soft)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--signal)]">
          Active
        </span>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {['Senior Frontend', 'Product-minded teams', 'Remote or NYC', 'Avoid recruiting agencies'].map((item) => (
          <span
            key={item}
            className="rounded-full border border-black/6 bg-white px-3 py-2 text-sm font-medium text-slate-700"
          >
            {item}
          </span>
        ))}
      </div>

      <div className="mt-5 grid gap-3">
        {[
          {
            company: 'Northstar',
            role: 'Staff Frontend Engineer',
            note: 'Strong design-system fit, ATS keywords aligned',
            match: '92 match',
          },
          {
            company: 'Common Atlas',
            role: 'Senior Product Engineer',
            note: 'Hybrid search + analytics workflow, follow up in 3 days',
            match: '86 match',
          },
        ].map((job) => (
          <article
            key={job.company}
            className="rounded-[1.4rem] border border-black/6 bg-[color:var(--surface-ink)] p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {job.company}
                </p>
                <h3 className="mt-1 text-lg font-semibold text-slate-950">
                  {job.role}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{job.note}</p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-strong)]">
                {job.match}
              </span>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}

export function LandingPage() {
  return (
    <div className="pb-16">
      <LandingHeader />

      <section className="shell-width py-8 sm:py-10 lg:py-14">
        <div className="surface-card relative overflow-hidden px-6 py-8 sm:px-8 sm:py-10 lg:px-10">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(circle_at_top_right,rgba(15,118,110,0.16),transparent_52%)] lg:block"
          />
          <div className="hero-grid lg:grid-cols-[1.12fr_0.88fr] lg:items-start">
            <div className="relative z-10">
              <span className="eyebrow-pill">Search-first workflow</span>
              <h1 className="mt-5 max-w-4xl font-display text-5xl font-semibold tracking-[-0.07em] text-slate-950 sm:text-6xl lg:text-[4.9rem]">
                ResuBoost AI keeps your search brief, pipeline, and prep in one operating surface.
              </h1>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
                Stop rebuilding context every time you open a new tab. Set your target roles, track real application movement, tune materials fast, and walk into interviews with the right history still attached.
              </p>

              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/register"
                  className="inline-flex min-h-14 items-center justify-center gap-2 rounded-full bg-[#10243f] px-6 text-base font-semibold text-white transition hover:bg-[#0b1728]"
                >
                  Build your search system
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex min-h-14 items-center justify-center rounded-full border border-black/8 bg-white/70 px-6 text-base font-semibold text-slate-700 transition hover:bg-white"
                >
                  Sign in
                </Link>
              </div>

              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                {landingStats.map((item) => (
                  <div
                    key={item.label}
                    className="rounded-[1.35rem] border border-black/6 bg-white/65 p-4"
                  >
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                      {item.label}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <SearchPreview />
          </div>
        </div>
      </section>

      <section
        className="shell-width py-6 sm:py-8"
        style={{ contentVisibility: 'auto', containIntrinsicSize: '900px' }}
      >
        <div className="text-center">
          <span className="eyebrow-pill">What changes</span>
          <h2 className="mt-5 font-display text-4xl font-semibold tracking-[-0.06em] text-slate-950 sm:text-5xl">
            The search feels smaller because the context stays put.
          </h2>
          <p className="mx-auto mt-4 max-w-3xl text-base leading-7 text-slate-600 sm:text-lg">
            The point is not adding more AI widgets. It is keeping your target, materials, applications, and interview prep close enough that each step improves the next one.
          </p>
        </div>

        <div className="mt-10 grid gap-4 lg:grid-cols-2">
          {productCards.map((card) => (
            <article
              key={card.title}
              className="surface-card-strong rise-in p-6 sm:p-7"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
                <card.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <h3 className="mt-5 font-display text-2xl font-semibold tracking-[-0.04em] text-slate-950">
                {card.title}
              </h3>
              <p className="mt-3 text-base leading-7 text-slate-600">{card.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        className="shell-width py-6 sm:py-10"
        style={{ contentVisibility: 'auto', containIntrinsicSize: '850px' }}
      >
        <div className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="surface-card-strong flex flex-col justify-between p-6 sm:p-8">
            <div>
              <span className="eyebrow-pill">How it feels</span>
              <h2 className="mt-5 font-display text-4xl font-semibold tracking-[-0.06em] text-slate-950">
                Built for the messy middle of a real search.
              </h2>
              <p className="mt-4 text-base leading-7 text-slate-600">
                Most job hunts stall when the details spread across notes, tabs, and versions. ResuBoost AI pulls that back into one rhythm.
              </p>
            </div>
            <div className="mt-8 rounded-[1.5rem] border border-black/6 bg-[#10243f] p-5 text-white">
              <div className="flex items-center gap-3">
                <Radar className="h-5 w-5 text-[#ffba66]" aria-hidden="true" />
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-white/70">
                  Search system
                </p>
              </div>
              <p className="mt-3 text-lg font-semibold">
                Keep signal visible even when the week gets noisy.
              </p>
              <p className="mt-3 text-sm leading-6 text-white/72">
                Run your search from a short target list, not a pile of browser tabs and half-finished docs.
              </p>
            </div>
          </div>

          <div className="grid gap-4">
            {workflowPanels.map((panel) => (
              <article
                key={panel.title}
                className="surface-card-strong p-6 sm:p-7"
              >
                <h3 className="font-display text-2xl font-semibold tracking-[-0.04em] text-slate-950">
                  {panel.title}
                </h3>
                <p className="mt-3 text-base leading-7 text-slate-600">{panel.description}</p>
                <ul className="mt-5 grid gap-3">
                  {panel.bullets.map((bullet) => (
                    <li key={bullet} className="flex items-start gap-3 text-sm leading-6 text-slate-700">
                      <CheckCircle2
                        className="mt-0.5 h-4 w-4 flex-none text-[color:var(--signal)]"
                        aria-hidden="true"
                      />
                      <span>{bullet}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="shell-width py-6 sm:py-10">
        <div className="mx-auto max-w-5xl px-4">
          <h2 className="text-center font-display text-4xl font-semibold tracking-[-0.06em] text-slate-950 sm:text-5xl">
            Simple, transparent pricing
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-center text-base leading-7 text-slate-600">
            Start free and upgrade when you need more power.
          </p>
          <div className="mt-10">
            <PricingComparison
              onUpgrade={() => {
                window.location.href = '/register'
              }}
            />
          </div>
        </div>
      </section>

      <section className="shell-width pt-6">
        <div className="surface-card-strong overflow-hidden bg-[#10243f] px-6 py-8 text-white sm:px-8 sm:py-10">
          <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <span className="eyebrow-pill border-white/10 bg-white/10 text-white/70 before:bg-[#ffba66]">
                Ready when the search gets real
              </span>
              <h2 className="mt-5 font-display text-4xl font-semibold tracking-[-0.06em] text-white sm:text-5xl">
                Build a tighter job search loop.
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-7 text-white/72">
                Start with the role targets you actually care about, keep the pipeline clean, and make every resume and interview round less repetitive.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
              <Link
                href="/register"
                className="inline-flex min-h-14 items-center justify-center gap-2 rounded-full bg-white px-6 text-base font-semibold text-[#10243f] transition hover:bg-[#fff4e9]"
              >
                Create your workspace
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/login"
                className="inline-flex min-h-14 items-center justify-center rounded-full border border-white/12 bg-white/8 px-6 text-base font-semibold text-white transition hover:bg-white/14"
              >
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
