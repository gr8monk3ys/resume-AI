'use client'

import {
  ArrowRight,
  Briefcase,
  Clock3,
  FileEdit,
  FileText,
  Filter,
  MessagesSquare,
  Radar,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import Link from 'next/link'
import { useEffect, useState } from 'react'

import { coverLettersApi, jobsApi, resumesApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { cn, formatDate } from '@/lib/utils'

import type { CoverLetter, JobApplication, JobStats, Resume } from '@/types'

interface DashboardState {
  resumes: Resume[]
  jobs: JobApplication[]
  coverLetters: CoverLetter[]
  jobStats: JobStats | null
  isLoadingStats: boolean
}

const INITIAL_DASHBOARD_STATE: DashboardState = {
  resumes: [],
  jobs: [],
  coverLetters: [],
  jobStats: null,
  isLoadingStats: true,
}

const OPEN_STATUSES = ['Bookmarked', 'Applied', 'Phone Screen', 'Interview']

const DASHBOARD_ACTIONS = [
  {
    title: 'Tune search filters',
    description: 'Keep target roles, company rules, and exclusions tight.',
    href: '/jobs/filters',
    icon: Filter,
  },
  {
    title: 'Review pipeline',
    description: 'See what moved recently and what still needs follow-up.',
    href: '/jobs',
    icon: Briefcase,
  },
  {
    title: 'Polish resume versions',
    description: 'Check ATS scores, missing keywords, and ready-to-send versions.',
    href: '/resumes',
    icon: FileText,
  },
  {
    title: 'Open documents',
    description: 'Generate cover letters and keep supporting material in sync.',
    href: '/documents',
    icon: FileEdit,
  },
]

function getActiveApplications(jobs: JobApplication[]) {
  if (!Array.isArray(jobs)) return []
  return jobs.filter((job) => OPEN_STATUSES.includes(job.status))
}

function getAverageAtsScore(resumes: Resume[]) {
  const scoredResumes = resumes.filter((resume) => typeof resume.ats_score === 'number')

  if (scoredResumes.length === 0) {
    return null
  }

  const total = scoredResumes.reduce((sum, resume) => sum + (resume.ats_score || 0), 0)
  return Math.round(total / scoredResumes.length)
}

function getOldestActiveApplication(jobs: JobApplication[]) {
  return [...getActiveApplications(jobs)].sort(
    (a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
  )[0] ?? null
}

function getRecentApplications(jobs: JobApplication[]) {
  return [...jobs]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 5)
}

function getStageCount(jobs: JobApplication[], statuses: string[]) {
  return jobs.filter((job) => statuses.includes(job.status)).length
}

function StatusPill({ status }: { status: JobApplication['status'] }) {
  const tones: Record<JobApplication['status'], string> = {
    Bookmarked: 'bg-slate-100 text-slate-700',
    Applied: 'bg-sky-100 text-sky-700',
    'Phone Screen': 'bg-violet-100 text-violet-700',
    Interview: 'bg-amber-100 text-amber-700',
    Offer: 'bg-emerald-100 text-emerald-700',
    Rejected: 'bg-rose-100 text-rose-700',
  }

  return (
    <span className={cn('rounded-full px-3 py-1 text-xs font-semibold', tones[status])}>
      {status}
    </span>
  )
}

function MetricCard({
  label,
  value,
  supporting,
  href,
}: {
  label: string
  value: string
  supporting: string
  href: string
}) {
  return (
    <Link
      href={href}
      className="rounded-[1.4rem] border border-black/6 bg-white/72 p-4 transition hover:-translate-y-0.5 hover:bg-white"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
        {label}
      </p>
      <p className="mt-3 font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">
        {value}
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{supporting}</p>
    </Link>
  )
}

function PriorityCard({
  eyebrow,
  title,
  description,
  href,
}: {
  eyebrow: string
  title: string
  description: string
  href: string
}) {
  return (
    <Link
      href={href}
      className="rounded-[1.5rem] border border-black/6 bg-white/80 p-5 transition hover:-translate-y-0.5 hover:bg-white"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        {eyebrow}
      </p>
      <h3 className="mt-3 font-display text-2xl font-semibold tracking-[-0.05em] text-slate-950">
        {title}
      </h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>
      <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-[color:var(--accent-strong)]">
        Open
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </span>
    </Link>
  )
}

function DashboardAuthFallback() {
  return (
    <div className="shell-width pt-10">
      <div className="surface-card-strong px-6 py-10 text-center sm:px-8">
        <h1 className="font-display text-4xl font-semibold tracking-[-0.06em] text-slate-950">
          Sign in to open your search workspace.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-slate-600">
          Your dashboard pulls together the application pipeline, resume lab, search filters, and interview prep.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex min-h-14 items-center justify-center rounded-full bg-[#10243f] px-6 text-base font-semibold text-white transition hover:bg-[#0b1728]"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="inline-flex min-h-14 items-center justify-center rounded-full border border-black/8 bg-white px-6 text-base font-semibold text-slate-700 transition hover:bg-white/80"
          >
            Create account
          </Link>
        </div>
      </div>
    </div>
  )
}

interface DashboardPriority {
  eyebrow: string
  title: string
  description: string
  href: string
}

function DashboardHero({
  displayName,
  activeApplicationsCount,
  responseRate,
  averageAtsScore,
  coverLetterCount,
  phoneScreensAndInterviews,
  offers,
  priorityCards,
  isLoadingStats,
  jobs,
}: {
  displayName: string
  activeApplicationsCount: number
  responseRate: string
  averageAtsScore: number | null
  coverLetterCount: number
  phoneScreensAndInterviews: number
  offers: number
  priorityCards: DashboardPriority[]
  isLoadingStats: boolean
  jobs: JobApplication[]
}) {
  return (
    <section className="surface-card relative overflow-hidden px-6 py-7 sm:px-8 sm:py-8">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(circle_at_top_right,rgba(15,118,110,0.18),transparent_55%)] lg:block"
      />
      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="relative z-10">
          <span className="eyebrow-pill">Command center</span>
          <h1 className="mt-5 font-display text-4xl font-semibold tracking-[-0.06em] text-slate-950 sm:text-5xl">
            Welcome back, {displayName}.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
            Keep the search tight this week: protect application momentum, stay current on role targets, and make sure the materials are ready before the next conversation shows up.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/jobs/filters"
              className="inline-flex min-h-14 items-center justify-center gap-2 rounded-full bg-[#10243f] px-6 text-base font-semibold text-white transition hover:bg-[#0b1728]"
            >
              Tune search filters
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              href="/jobs"
              className="inline-flex min-h-14 items-center justify-center rounded-full border border-black/8 bg-white/75 px-6 text-base font-semibold text-slate-700 transition hover:bg-white"
            >
              Open pipeline
            </Link>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Active pipeline"
              value={isLoadingStats ? '-' : `${activeApplicationsCount}`}
              supporting="Open applications that still need momentum."
              href="/jobs"
            />
            <MetricCard
              label="Response rate"
              value={isLoadingStats ? '-' : responseRate}
              supporting="Reply signal across the tracked pipeline."
              href="/analytics"
            />
            <MetricCard
              label="Resume average"
              value={isLoadingStats ? '-' : averageAtsScore !== null ? `${averageAtsScore}` : 'No score'}
              supporting="Average ATS score across scored resume versions."
              href="/resumes"
            />
            <MetricCard
              label="Cover letter drafts"
              value={isLoadingStats ? '-' : `${coverLetterCount}`}
              supporting="Supporting documents ready to personalize."
              href="/documents"
            />
          </div>
        </div>

        <div className="relative z-10 grid gap-4">
          <div className="rounded-[1.6rem] border border-black/6 bg-[#10243f] p-6 text-white">
            <div className="flex items-center gap-3">
              <Radar className="h-5 w-5 text-[#ffba66]" aria-hidden="true" />
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
                Weekly focus
              </p>
            </div>
            <ul className="mt-5 grid gap-4">
              {priorityCards.map((card) => (
                <li key={card.eyebrow} className="rounded-[1.35rem] border border-white/8 bg-white/8 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/55">
                    {card.eyebrow}
                  </p>
                  <p className="mt-2 text-base font-semibold leading-6 text-white">
                    {card.title}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-white/72">
                    {card.description}
                  </p>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-[1.6rem] border border-black/6 bg-white/80 p-6">
            <div className="flex items-center gap-3">
              <TrendingUp className="h-5 w-5 text-[color:var(--accent-strong)]" aria-hidden="true" />
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Pipeline snapshot
              </p>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-3">
              {[
                { label: 'Applied', value: `${getStageCount(jobs, ['Applied'])}` },
                { label: 'Interviews', value: `${phoneScreensAndInterviews}` },
                { label: 'Offers', value: `${offers}` },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-[1.2rem] border border-black/6 bg-[color:var(--surface-ink)] p-4 text-center"
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    {item.label}
                  </p>
                  <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">
                    {isLoadingStats ? '-' : item.value}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">
              Keep the search moving by tightening filters, following up on older applications, and keeping resume versions close to the roles they support.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

function RecentApplicationsPanel({
  isLoadingStats,
  recentApplications,
}: {
  isLoadingStats: boolean
  recentApplications: JobApplication[]
}) {
  return (
    <div className="surface-card-strong p-6 sm:p-7">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            Pipeline movement
          </p>
          <h2 className="mt-2 font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">
            Recent applications
          </h2>
        </div>
        <Link
          href="/jobs"
          className="inline-flex items-center gap-2 text-sm font-semibold text-[color:var(--accent-strong)]"
        >
          View all
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>

      {isLoadingStats ? (
        <div className="mt-6 flex min-h-56 items-center justify-center">
          <div
            className="h-10 w-10 animate-spin rounded-full border-b-2 border-[color:var(--accent)]"
            role="status"
            aria-label="Loading"
          />
        </div>
      ) : recentApplications.length > 0 ? (
        <ul className="mt-6 grid gap-3">
          {recentApplications.map((job) => (
            <li
              key={job.id}
              className="rounded-[1.4rem] border border-black/6 bg-white/70 p-4"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
                    {job.company}
                  </p>
                  <h3 className="mt-1 text-lg font-semibold text-slate-950">
                    {job.position}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    {job.location || 'Location flexible'}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                  <StatusPill status={job.status} />
                  <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                    {formatDate(job.updated_at, 'relative')}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-6 rounded-[1.6rem] border border-dashed border-black/10 bg-white/60 px-6 py-10 text-center">
          <MessagesSquare
            className="mx-auto h-10 w-10 text-slate-300"
            aria-hidden="true"
          />
          <p className="mt-4 text-lg font-semibold text-slate-900">
            No applications tracked yet
          </p>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Start with a short target list and add the first applications to build a usable search history.
          </p>
          <Link
            href="/jobs"
            className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[color:var(--accent-strong)]"
          >
            Add your first application
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      )}
    </div>
  )
}

function DashboardActionPanels({
  priorityCards,
}: {
  priorityCards: DashboardPriority[]
}) {
  return (
    <div className="grid gap-6">
      <div className="surface-card-strong p-6 sm:p-7">
        <div className="flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-[color:var(--accent-strong)]" aria-hidden="true" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
              Search priorities
            </p>
            <h2 className="mt-2 font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">
              Next best moves
            </h2>
          </div>
        </div>
        <div className="mt-6 grid gap-3">
          {priorityCards.map((card) => (
            <PriorityCard
              key={card.eyebrow}
              eyebrow={card.eyebrow}
              title={card.title}
              description={card.description}
              href={card.href}
            />
          ))}
        </div>
      </div>

      <div className="surface-card-strong p-6 sm:p-7">
        <div className="flex items-center gap-3">
          <FileEdit className="h-5 w-5 text-[color:var(--accent-strong)]" aria-hidden="true" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
              Command deck
            </p>
            <h2 className="mt-2 font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">
              Open the right workspace
            </h2>
          </div>
        </div>
        <nav className="mt-6 grid gap-3" aria-label="Quick actions">
          {DASHBOARD_ACTIONS.map((action) => (
            <Link
              key={action.title}
              href={action.href}
              className="flex items-start gap-4 rounded-[1.4rem] border border-black/6 bg-white/70 p-4 transition hover:-translate-y-0.5 hover:bg-white"
            >
              <div className="flex h-11 w-11 flex-none items-center justify-center rounded-2xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
                <action.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="text-base font-semibold text-slate-950">{action.title}</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">{action.description}</p>
              </div>
            </Link>
          ))}
        </nav>
      </div>
    </div>
  )
}

function Dashboard({
  user,
  jobs,
  resumes,
  coverLetters,
  jobStats,
  isLoadingStats,
}: {
  user: { full_name: string | null; username: string }
  jobs: JobApplication[]
  resumes: Resume[]
  coverLetters: CoverLetter[]
  jobStats: JobStats | null
  isLoadingStats: boolean
}) {
  const activeApplications = getActiveApplications(jobs)
  const recentApplications = getRecentApplications(jobs)
  const oldestActiveApplication = getOldestActiveApplication(jobs)
  const phoneScreensAndInterviews = getStageCount(jobs, ['Phone Screen', 'Interview'])
  const offers = getStageCount(jobs, ['Offer'])
  const averageAtsScore = getAverageAtsScore(resumes)
  const responseRate =
    typeof jobStats?.response_rate === 'number'
      ? `${Math.round(jobStats.response_rate)}%`
      : jobs.length > 0
        ? `${Math.round((getStageCount(jobs, ['Phone Screen', 'Interview', 'Offer', 'Rejected']) / jobs.length) * 100)}%`
        : '-'

  const displayName = user.full_name || user.username

  const priorityCards = [
    {
      eyebrow: 'Pipeline',
      title:
        activeApplications.length > 0
          ? `${activeApplications.length} active applications need steady follow-through`
          : 'Set up the first wave of applications',
      description:
        oldestActiveApplication
          ? `${oldestActiveApplication.company} was last updated ${formatDate(oldestActiveApplication.updated_at, 'relative')}.`
          : 'Open the job board and start tracking your first target list.',
      href: '/jobs',
    },
    {
      eyebrow: 'Materials',
      title:
        averageAtsScore !== null
          ? `Resume average is ${averageAtsScore}, with room to sharpen role fit`
          : 'Score the first resume so the lab can start guiding improvements',
      description:
        resumes.length > 0
          ? `${resumes.length} resume ${resumes.length === 1 ? 'version' : 'versions'} and ${coverLetters.length} cover letter ${coverLetters.length === 1 ? 'draft' : 'drafts'} are already in play.`
          : 'Your search materials still need a primary version to work from.',
      href: '/resumes',
    },
    {
      eyebrow: 'Interviews',
      title:
        phoneScreensAndInterviews > 0
          ? `${phoneScreensAndInterviews} conversation ${phoneScreensAndInterviews === 1 ? 'is' : 'are'} warming up`
          : 'Keep interview prep ready before the search speeds up',
      description:
        offers > 0
          ? `${offers} offer ${offers === 1 ? 'has' : 'have'} already reached the pipeline.`
          : 'Use the interview center for STAR answers, notes, and follow-up context.',
      href: '/interview',
    },
  ]

  return (
    <div className="shell-width pt-8">
      <DashboardHero
        displayName={displayName}
        activeApplicationsCount={activeApplications.length}
        responseRate={responseRate}
        averageAtsScore={averageAtsScore}
        coverLetterCount={coverLetters.length}
        phoneScreensAndInterviews={phoneScreensAndInterviews}
        offers={offers}
        priorityCards={priorityCards}
        isLoadingStats={isLoadingStats}
        jobs={jobs}
      />

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <RecentApplicationsPanel
          isLoadingStats={isLoadingStats}
          recentApplications={recentApplications}
        />
        <DashboardActionPanels priorityCards={priorityCards} />
      </section>
    </div>
  )
}

export function DashboardClient() {
  const { user, isAuthenticated } = useAuth()
  const [dashboardState, setDashboardState] = useState<DashboardState>(INITIAL_DASHBOARD_STATE)

  useEffect(() => {
    let isMounted = true

    async function fetchDashboardData() {
      let nextState: DashboardState = {
        resumes: [],
        jobs: [],
        coverLetters: [],
        jobStats: null,
        isLoadingStats: false,
      }

      if (isAuthenticated) {
        try {
          const [resumes, jobs, coverLetters, jobStats] = await Promise.all([
            resumesApi.list().catch(() => [] as Resume[]),
            jobsApi.list().catch(() => [] as JobApplication[]),
            coverLettersApi.list().catch(() => [] as CoverLetter[]),
            jobsApi.getStats().catch(() => null),
          ])

          nextState = {
            resumes,
            jobs,
            coverLetters,
            jobStats,
            isLoadingStats: false,
          }
        } catch (error) {
          console.error('Failed to fetch dashboard data:', error)
        }
      }

      if (isMounted) {
        setDashboardState(nextState)
      }
    }

    if (user) {
      void fetchDashboardData()
    }

    return () => {
      isMounted = false
    }
  }, [user, isAuthenticated])

  if (!user) {
    return <DashboardAuthFallback />
  }

  return (
    <Dashboard
      user={user}
      jobs={dashboardState.jobs}
      resumes={dashboardState.resumes}
      coverLetters={dashboardState.coverLetters}
      jobStats={dashboardState.jobStats}
      isLoadingStats={dashboardState.isLoadingStats}
    />
  )
}
