'use client'

import {
  FileText,
  Briefcase,
  FileEdit,
  Mic,
  Award,
  Settings,
  ArrowRight,
  TrendingUp,
  Clock,
} from 'lucide-react'
import Link from 'next/link'
import { useState, useEffect } from 'react'

import { jobsApi, resumesApi, coverLettersApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

import type { JobApplication, Resume, CoverLetter, JobStats } from '@/types'

/**
 * Core features of the application
 * Used for both landing page feature cards and dashboard quick actions
 */
const features = [
  {
    name: 'Resume Hub',
    description: 'Get ATS scores and AI-powered optimization suggestions for your resumes',
    href: '/resumes',
    icon: FileText,
    color: 'bg-blue-500',
    hoverColor: 'hover:bg-blue-600',
  },
  {
    name: 'Job Pipeline',
    description: 'Kanban board to track and manage your job applications',
    href: '/jobs',
    icon: Briefcase,
    color: 'bg-green-500',
    hoverColor: 'hover:bg-green-600',
  },
  {
    name: 'Interview Center',
    description: 'Prepare for interviews with AI-powered STAR method responses',
    href: '/interview',
    icon: Mic,
    color: 'bg-purple-500',
    hoverColor: 'hover:bg-purple-600',
  },
  {
    name: 'Document Generator',
    description: 'Generate personalized cover letters and professional documents',
    href: '/documents',
    icon: FileEdit,
    color: 'bg-orange-500',
    hoverColor: 'hover:bg-orange-600',
  },
  {
    name: 'Career Tools',
    description: 'Track your career journal, goals, and professional growth',
    href: '/career',
    icon: Award,
    color: 'bg-pink-500',
    hoverColor: 'hover:bg-pink-600',
  },
  {
    name: 'Account & Settings',
    description: 'Manage your profile, preferences, and account settings',
    href: '/settings',
    icon: Settings,
    color: 'bg-gray-500',
    hoverColor: 'hover:bg-gray-600',
  },
]

/**
 * Dashboard statistics interface
 */
interface DashboardStats {
  totalResumes: number
  totalApplications: number
  totalCoverLetters: number
  jobStats: JobStats | null
}

interface DashboardState {
  stats: DashboardStats
  recentApplications: JobApplication[]
  isLoadingStats: boolean
}

const EMPTY_DASHBOARD_STATS: DashboardStats = {
  totalResumes: 0,
  totalApplications: 0,
  totalCoverLetters: 0,
  jobStats: null,
}

/**
 * Dashboard component for authenticated users
 */
function Dashboard({
  user,
  stats,
  recentApplications,
  isLoadingStats,
}: {
  user: { full_name: string | null; username: string }
  stats: DashboardStats
  recentApplications: JobApplication[]
  isLoadingStats: boolean
}) {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user.full_name || user.username}!
        </h1>
        <p className="mt-2 text-gray-500">
          Here is an overview of your job search progress
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatsCard
          title="Resumes"
          value={isLoadingStats ? '-' : stats.totalResumes.toString()}
          icon={FileText}
          color="bg-blue-500"
          href="/resumes"
        />
        <StatsCard
          title="Applications"
          value={isLoadingStats ? '-' : stats.totalApplications.toString()}
          icon={Briefcase}
          color="bg-green-500"
          href="/jobs"
        />
        <StatsCard
          title="Cover Letters"
          value={isLoadingStats ? '-' : stats.totalCoverLetters.toString()}
          icon={FileEdit}
          color="bg-purple-500"
          href="/documents"
        />
        <StatsCard
          title="Response Rate"
          value={
            isLoadingStats || !stats.jobStats
              ? '-'
              : `${Math.round(stats.jobStats.response_rate)}%`
          }
          icon={TrendingUp}
          color="bg-orange-500"
          href="/jobs"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Activity */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">
                Recent Applications
              </h2>
              <Link
                href="/jobs"
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                View All
              </Link>
            </div>
            {isLoadingStats ? (
              <div className="flex items-center justify-center py-8">
                <div
                  className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"
                  role="status"
                  aria-label="Loading"
                />
              </div>
            ) : recentApplications.length > 0 ? (
              <ul className="divide-y divide-gray-100">
                {recentApplications.map((job) => (
                  <li key={job.id} className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {job.position}
                        </p>
                        <p className="text-sm text-gray-500 truncate">
                          {job.company}
                          {job.location && ` - ${job.location}`}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusBadge status={job.status} />
                        <span className="text-xs text-gray-400 flex items-center">
                          <Clock className="w-3 h-3 mr-1" aria-hidden="true" />
                          {formatDate(job.updated_at)}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-center py-8">
                <Briefcase
                  className="w-12 h-12 text-gray-300 mx-auto mb-4"
                  aria-hidden="true"
                />
                <p className="text-gray-500">No applications yet</p>
                <Link
                  href="/jobs"
                  className="mt-4 inline-flex items-center text-sm text-primary-600 hover:text-primary-700 font-medium"
                >
                  Add your first application
                  <ArrowRight className="ml-1 w-4 h-4" aria-hidden="true" />
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div>
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              Quick Actions
            </h2>
            <nav className="space-y-3" aria-label="Quick actions">
              {features.map((feature) => (
                <Link
                  key={feature.name}
                  href={feature.href}
                  className="flex items-center p-3 rounded-lg hover:bg-gray-50 transition-colors group"
                >
                  <div
                    className={`${feature.color} w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0`}
                  >
                    <feature.icon
                      className="w-5 h-5 text-white"
                      aria-hidden="true"
                    />
                  </div>
                  <div className="ml-4 flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      {feature.name}
                    </p>
                  </div>
                  <ArrowRight
                    className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors"
                    aria-hidden="true"
                  />
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Stats card component for displaying metrics
 */
function StatsCard({
  title,
  value,
  icon: Icon,
  color,
  href,
}: {
  title: string
  value: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  href: string
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-xl shadow-md p-6 border border-gray-100 hover:shadow-lg transition-shadow group"
    >
      <div className="flex items-center">
        <div
          className={`${color} w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0`}
        >
          <Icon className="w-6 h-6 text-white" aria-hidden="true" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 group-hover:text-primary-600 transition-colors">
            {value}
          </p>
        </div>
      </div>
    </Link>
  )
}

/**
 * Status badge component for job application status
 */
function StatusBadge({ status }: { status: string }) {
  const statusColors: Record<string, string> = {
    Bookmarked: 'bg-gray-100 text-gray-700',
    Applied: 'bg-blue-100 text-blue-700',
    'Phone Screen': 'bg-yellow-100 text-yellow-700',
    Interview: 'bg-purple-100 text-purple-700',
    Offer: 'bg-green-100 text-green-700',
    Rejected: 'bg-red-100 text-red-700',
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        statusColors[status] || 'bg-gray-100 text-gray-700'
      }`}
    >
      {status}
    </span>
  )
}

/**
 * Format date string to relative or short format
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return 'Today'
  } else if (diffDays === 1) {
    return 'Yesterday'
  } else if (diffDays < 7) {
    return `${diffDays}d ago`
  } else {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
  }
}

function DashboardAuthFallback() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-gray-900">Sign in to view your dashboard</h1>
      <p className="mt-4 text-lg text-gray-500">
        Your session is not active, so the dashboard data could not be loaded.
      </p>
      <div className="mt-8 flex flex-col justify-center gap-4 sm:flex-row">
        <Link
          href="/login"
          className="inline-flex items-center justify-center rounded-md bg-primary-600 px-6 py-3 text-white hover:bg-primary-700"
        >
          Sign In
        </Link>
        <Link
          href="/register"
          className="inline-flex items-center justify-center rounded-md border border-primary-600 px-6 py-3 text-primary-600 hover:bg-primary-50"
        >
          Create Account
        </Link>
      </div>
    </div>
  )
}

/**
 * Main DashboardClient component
 * Shows landing page for unauthenticated users, dashboard for authenticated users
 */
export function DashboardClient() {
  const { user, isAuthenticated } = useAuth()
  const [dashboardState, setDashboardState] = useState<DashboardState>({
    stats: EMPTY_DASHBOARD_STATS,
    recentApplications: [],
    isLoadingStats: true,
  })

  useEffect(() => {
    let isMounted = true

    async function fetchDashboardData() {
      let nextState: DashboardState = {
        stats: EMPTY_DASHBOARD_STATS,
        recentApplications: [],
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

          // Sort jobs by updated_at and take the 5 most recent
          const sortedJobs = [...jobs].sort(
            (a, b) =>
              new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          )
          nextState = {
            stats: {
              totalResumes: resumes.length,
              totalApplications: jobs.length,
              totalCoverLetters: coverLetters.length,
              jobStats,
            },
            recentApplications: sortedJobs.slice(0, 5),
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

  // Show dashboard for authenticated users
  return (
    <Dashboard
      user={user}
      stats={dashboardState.stats}
      recentApplications={dashboardState.recentApplications}
      isLoadingStats={dashboardState.isLoadingStats}
    />
  )
}
