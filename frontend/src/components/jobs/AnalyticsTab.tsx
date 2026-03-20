'use client'

import {
  BarChart3,
  TrendingUp,
  CheckCircle,
  Target,
  PieChart,
} from 'lucide-react'
import { useMemo, memo } from 'react'

import { JOB_STATUSES } from '@/lib/jobs'
import { cn, getStatusColor } from '@/lib/utils'

import type { JobApplication, JobStats, WeeklyApplicationData, JobGoals } from '@/types'

interface AnalyticsTabProps {
  jobs: JobApplication[]
  stats: JobStats | null
}

export const AnalyticsTab = memo(function AnalyticsTab({ jobs, stats }: AnalyticsTabProps) {
  // Calculate weekly applications data
  const weeklyData = useMemo((): WeeklyApplicationData[] => {
    const weeks: Record<string, number> = {}
    const now = new Date()

    // Initialize last 8 weeks
    for (let i = 7; i >= 0; i--) {
      const weekStart = new Date(now)
      weekStart.setDate(weekStart.getDate() - i * 7)
      const weekKey = weekStart.toISOString().slice(0, 10)
      weeks[weekKey] = 0
    }

    // Count applications per week
    jobs.forEach((job) => {
      const date = new Date(job.created_at)
      const weekStart = new Date(date)
      weekStart.setDate(weekStart.getDate() - weekStart.getDay())
      const weekKey = weekStart.toISOString().slice(0, 10)
      if (weeks[weekKey] !== undefined) {
        weeks[weekKey]++
      }
    })

    return Object.entries(weeks).map(([week, count]) => ({
      week: new Date(week).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      count,
    }))
  }, [jobs])

  // Calculate status breakdown for pie chart
  const statusBreakdown = useMemo(() => {
    const breakdown: Record<string, number> = {}
    JOB_STATUSES.forEach((status) => {
      breakdown[status] = jobs.filter((j) => j.status === status).length
    })
    return breakdown
  }, [jobs])

  // Calculate funnel data
  const funnelData = useMemo(() => {
    const applied = jobs.filter((j) => j.status !== 'Bookmarked').length
    const phoneScreen = jobs.filter((j) =>
      ['Phone Screen', 'Interview', 'Offer'].includes(j.status)
    ).length
    const interview = jobs.filter((j) => ['Interview', 'Offer'].includes(j.status)).length
    const offer = jobs.filter((j) => j.status === 'Offer').length

    return [
      { stage: 'Applied', count: applied, percentage: 100 },
      {
        stage: 'Phone Screen',
        count: phoneScreen,
        percentage: applied ? Math.round((phoneScreen / applied) * 100) : 0,
      },
      {
        stage: 'Interview',
        count: interview,
        percentage: applied ? Math.round((interview / applied) * 100) : 0,
      },
      {
        stage: 'Offer',
        count: offer,
        percentage: applied ? Math.round((offer / applied) * 100) : 0,
      },
    ]
  }, [jobs])

  // Goals (mock data - in real app would come from API/storage)
  const goals: JobGoals = useMemo(() => {
    const now = new Date()
    const startOfWeek = new Date(now)
    startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay())
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

    const weeklyCount = jobs.filter(
      (j) => new Date(j.created_at) >= startOfWeek
    ).length
    const monthlyCount = jobs.filter(
      (j) => new Date(j.created_at) >= startOfMonth
    ).length

    return {
      weekly_target: 10,
      monthly_target: 40,
      weekly_current: weeklyCount,
      monthly_current: monthlyCount,
    }
  }, [jobs])

  const maxWeeklyCount = Math.max(...weeklyData.map((d) => d.count), 1)

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[var(--surface-strong)] rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-lg">
              <BarChart3 className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-[var(--muted)]">Total Applications</p>
              <p className="text-2xl font-bold text-[var(--ink)]">{stats?.total || jobs.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-[var(--surface-strong)] rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-[var(--muted)]">Response Rate</p>
              <p className="text-2xl font-bold text-[var(--ink)]">
                {stats ? `${Math.round(stats.response_rate)}%` : '0%'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-[var(--surface-strong)] rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-green-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-[var(--muted)]">Offer Rate</p>
              <p className="text-2xl font-bold text-[var(--ink)]">
                {stats ? `${Math.round(stats.offer_rate)}%` : '0%'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-[var(--surface-strong)] rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-amber-100 rounded-lg">
              <Target className="w-6 h-6 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-[var(--muted)]">Active Applications</p>
              <p className="text-2xl font-bold text-[var(--ink)]">
                {jobs.filter((j) => !['Rejected', 'Offer'].includes(j.status)).length}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Application Funnel */}
        <div className="bg-[var(--surface-strong)] rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold font-display tracking-[-0.02em] text-[var(--ink)] mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            Application Funnel
          </h3>
          <div className="space-y-4">
            {funnelData.map((item, index) => (
              <div key={item.stage}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-[var(--ink-secondary)]">{item.stage}</span>
                  <span className="text-[var(--muted)]">
                    {item.count} ({item.percentage}%)
                  </span>
                </div>
                <div className="w-full bg-[var(--surface)] rounded-full h-6 overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all duration-500',
                      index === 0
                        ? 'bg-blue-500'
                        : index === 1
                        ? 'bg-purple-500'
                        : index === 2
                        ? 'bg-amber-500'
                        : 'bg-green-500'
                    )}
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Status Breakdown */}
        <div className="bg-[var(--surface-strong)] rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold font-display tracking-[-0.02em] text-[var(--ink)] mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-primary-600" />
            Status Breakdown
          </h3>
          <div className="space-y-3">
            {JOB_STATUSES.map((status) => {
              const count = statusBreakdown[status] ?? 0
              const percentage = jobs.length
                ? Math.round((count / jobs.length) * 100)
                : 0
              const colors = getStatusColor(status)

              return (
                <div key={status} className="flex items-center gap-3">
                  <div className={cn('w-3 h-3 rounded-full', colors.bg, colors.border, 'border')} />
                  <div className="flex-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-[var(--ink-secondary)]">{status}</span>
                      <span className="text-[var(--muted)]">
                        {count} ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-[var(--surface)] rounded-full h-2 mt-1">
                      <div
                        className={cn('h-full rounded-full', colors.bg.replace('50', '500'))}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Applications Per Week */}
        <div className="bg-[var(--surface-strong)] rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold font-display tracking-[-0.02em] text-[var(--ink)] mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary-600" />
            Applications Per Week
          </h3>
          <div className="flex items-end gap-2 h-40">
            {weeklyData.map((item) => (
              <div
                key={item.week}
                className="flex-1 flex flex-col items-center justify-end"
              >
                <div
                  className="w-full bg-primary-500 rounded-t transition-all duration-300 hover:bg-primary-600"
                  style={{
                    height: `${(item.count / maxWeeklyCount) * 100}%`,
                    minHeight: item.count > 0 ? '8px' : '2px',
                  }}
                />
                <span className="text-xs text-[var(--muted)] mt-2 transform -rotate-45 origin-top-left">
                  {item.week}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Goals Progress */}
        <div className="bg-[var(--surface-strong)] rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold font-display tracking-[-0.02em] text-[var(--ink)] mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-primary-600" />
            Goals Progress
          </h3>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-[var(--ink-secondary)]">Weekly Goal</span>
                <span className="text-[var(--muted)]">
                  {goals.weekly_current} / {goals.weekly_target}
                </span>
              </div>
              <div className="w-full bg-[var(--surface)] rounded-full h-4">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500',
                    goals.weekly_current >= goals.weekly_target
                      ? 'bg-green-500'
                      : 'bg-primary-500'
                  )}
                  style={{
                    width: `${Math.min(
                      (goals.weekly_current / goals.weekly_target) * 100,
                      100
                    )}%`,
                  }}
                />
              </div>
              {goals.weekly_current >= goals.weekly_target && (
                <p className="text-sm text-green-600 mt-1 flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" />
                  Weekly goal achieved!
                </p>
              )}
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-[var(--ink-secondary)]">Monthly Goal</span>
                <span className="text-[var(--muted)]">
                  {goals.monthly_current} / {goals.monthly_target}
                </span>
              </div>
              <div className="w-full bg-[var(--surface)] rounded-full h-4">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500',
                    goals.monthly_current >= goals.monthly_target
                      ? 'bg-green-500'
                      : 'bg-amber-500'
                  )}
                  style={{
                    width: `${Math.min(
                      (goals.monthly_current / goals.monthly_target) * 100,
                      100
                    )}%`,
                  }}
                />
              </div>
              {goals.monthly_current >= goals.monthly_target && (
                <p className="text-sm text-green-600 mt-1 flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" />
                  Monthly goal achieved!
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
})
