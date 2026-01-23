'use client'

import { useEffect, useState, useMemo, useCallback } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { jobsApi, resumesApi, analyticsApi } from '@/lib/api'
import type {
  JobApplication,
  JobStatus,
  JobStats,
  Resume,
  DateRangeOption,
  TimelinePeriod,
  AnalyticsFilters,
  AnalyticsOverview,
  TimelineDataPoint,
  ConversionFunnelStage,
  SourcePerformance,
  CompanyStats,
  ResumePerformance,
  ActivityLogEntry,
} from '@/types'
import { cn, formatDate, getStatusColor, formatPercentage } from '@/lib/utils'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Users,
  Clock,
  Target,
  CheckCircle,
  AlertCircle,
  Download,
  Filter,
  Calendar,
  ChevronDown,
  ChevronUp,
  FileText,
  Briefcase,
  ArrowRight,
  Activity,
  PieChart,
  LineChart,
  RefreshCw,
} from 'lucide-react'

// ============================================================================
// Constants
// ============================================================================

const DATE_RANGE_OPTIONS: { value: DateRangeOption; label: string }[] = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'all', label: 'All time' },
  { value: 'custom', label: 'Custom range' },
]

const TIMELINE_PERIOD_OPTIONS: { value: TimelinePeriod; label: string }[] = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
]

const JOB_STATUSES: JobStatus[] = [
  'Bookmarked',
  'Applied',
  'Phone Screen',
  'Interview',
  'Offer',
  'Rejected',
]

const APPLICATION_SOURCES = [
  'LinkedIn',
  'Indeed',
  'Company Website',
  'Referral',
  'Glassdoor',
  'Other',
]

// ============================================================================
// Helper Functions
// ============================================================================

function getDateRangeFromOption(
  option: DateRangeOption,
  customStart?: string,
  customEnd?: string
): { start: Date; end: Date } {
  const now = new Date()
  const end = new Date(now)
  let start = new Date(now)

  switch (option) {
    case '7d':
      start.setDate(start.getDate() - 7)
      break
    case '30d':
      start.setDate(start.getDate() - 30)
      break
    case '90d':
      start.setDate(start.getDate() - 90)
      break
    case 'custom':
      if (customStart) start = new Date(customStart)
      if (customEnd) end.setTime(new Date(customEnd).getTime())
      break
    case 'all':
    default:
      start = new Date('2020-01-01')
      break
  }

  return { start, end }
}

function filterJobsByDateRange(
  jobs: JobApplication[],
  dateRange: DateRangeOption,
  customStart?: string,
  customEnd?: string
): JobApplication[] {
  const { start, end } = getDateRangeFromOption(dateRange, customStart, customEnd)

  return jobs.filter((job) => {
    const jobDate = new Date(job.created_at)
    return jobDate >= start && jobDate <= end
  })
}

function calculateOverviewMetrics(
  jobs: JobApplication[],
  previousPeriodJobs: JobApplication[]
): AnalyticsOverview {
  const total = jobs.length
  const prevTotal = previousPeriodJobs.length

  const responded = jobs.filter((j) =>
    ['Phone Screen', 'Interview', 'Offer', 'Rejected'].includes(j.status)
  ).length
  const prevResponded = previousPeriodJobs.filter((j) =>
    ['Phone Screen', 'Interview', 'Offer', 'Rejected'].includes(j.status)
  ).length

  const interviewed = jobs.filter((j) =>
    ['Interview', 'Offer'].includes(j.status)
  ).length
  const prevInterviewed = previousPeriodJobs.filter((j) =>
    ['Interview', 'Offer'].includes(j.status)
  ).length

  const offers = jobs.filter((j) => j.status === 'Offer').length
  const prevOffers = previousPeriodJobs.filter((j) => j.status === 'Offer').length

  const responseRate = total > 0 ? (responded / total) * 100 : 0
  const prevResponseRate = prevTotal > 0 ? (prevResponded / prevTotal) * 100 : 0

  const interviewRate = total > 0 ? (interviewed / total) * 100 : 0
  const prevInterviewRate = prevTotal > 0 ? (prevInterviewed / prevTotal) * 100 : 0

  const offerRate = total > 0 ? (offers / total) * 100 : 0
  const prevOfferRate = prevTotal > 0 ? (prevOffers / prevTotal) * 100 : 0

  // Calculate average response time for jobs with application dates
  const jobsWithResponseTime = jobs.filter(
    (j) =>
      j.application_date &&
      ['Phone Screen', 'Interview', 'Offer', 'Rejected'].includes(j.status)
  )
  let avgResponseTime = 0
  if (jobsWithResponseTime.length > 0) {
    const totalDays = jobsWithResponseTime.reduce((sum, job) => {
      const applied = new Date(job.application_date!)
      const updated = new Date(job.updated_at)
      return sum + Math.ceil((updated.getTime() - applied.getTime()) / (1000 * 60 * 60 * 24))
    }, 0)
    avgResponseTime = Math.round(totalDays / jobsWithResponseTime.length)
  }

  const activeJobs = jobs.filter((j) =>
    ['Bookmarked', 'Applied', 'Phone Screen', 'Interview'].includes(j.status)
  ).length

  return {
    total_applications: total,
    response_rate: responseRate,
    response_rate_trend: responseRate - prevResponseRate,
    interview_rate: interviewRate,
    interview_rate_trend: interviewRate - prevInterviewRate,
    offer_rate: offerRate,
    offer_rate_trend: offerRate - prevOfferRate,
    avg_response_time_days: avgResponseTime,
    active_applications: activeJobs,
  }
}

function generateTimelineData(
  jobs: JobApplication[],
  period: TimelinePeriod,
  dateRange: DateRangeOption,
  customStart?: string,
  customEnd?: string
): TimelineDataPoint[] {
  const { start, end } = getDateRangeFromOption(dateRange, customStart, customEnd)
  const dataMap = new Map<string, number>()

  // Generate date keys based on period
  const current = new Date(start)
  while (current <= end) {
    let key: string
    let label: string

    if (period === 'daily') {
      key = current.toISOString().slice(0, 10)
      label = current.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } else if (period === 'weekly') {
      const weekStart = new Date(current)
      weekStart.setDate(weekStart.getDate() - weekStart.getDay())
      key = weekStart.toISOString().slice(0, 10)
      label = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } else {
      key = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}`
      label = current.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
    }

    if (!dataMap.has(key)) {
      dataMap.set(key, 0)
    }

    if (period === 'daily') {
      current.setDate(current.getDate() + 1)
    } else if (period === 'weekly') {
      current.setDate(current.getDate() + 7)
    } else {
      current.setMonth(current.getMonth() + 1)
    }
  }

  // Count jobs per period
  jobs.forEach((job) => {
    const jobDate = new Date(job.created_at)
    let key: string

    if (period === 'daily') {
      key = jobDate.toISOString().slice(0, 10)
    } else if (period === 'weekly') {
      const weekStart = new Date(jobDate)
      weekStart.setDate(weekStart.getDate() - weekStart.getDay())
      key = weekStart.toISOString().slice(0, 10)
    } else {
      key = `${jobDate.getFullYear()}-${String(jobDate.getMonth() + 1).padStart(2, '0')}`
    }

    if (dataMap.has(key)) {
      dataMap.set(key, (dataMap.get(key) || 0) + 1)
    }
  })

  return Array.from(dataMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12) // Last 12 data points
    .map(([date, count]) => {
      const dateObj = new Date(date)
      let label: string
      if (period === 'daily') {
        label = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      } else if (period === 'weekly') {
        label = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      } else {
        label = dateObj.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
      }
      return { date, count, label }
    })
}

function calculateConversionFunnel(jobs: JobApplication[]): ConversionFunnelStage[] {
  const applied = jobs.filter((j) => j.status !== 'Bookmarked').length
  const responded = jobs.filter((j) =>
    ['Phone Screen', 'Interview', 'Offer', 'Rejected'].includes(j.status)
  ).length
  const interviewed = jobs.filter((j) =>
    ['Interview', 'Offer'].includes(j.status)
  ).length
  const offers = jobs.filter((j) => j.status === 'Offer').length

  const stages = [
    { stage: 'Applied', count: applied },
    { stage: 'Response', count: responded },
    { stage: 'Interview', count: interviewed },
    { stage: 'Offer', count: offers },
  ]

  return stages.map((stage, index) => {
    const prevCount = index === 0 ? stage.count : stages[index - 1].count
    return {
      ...stage,
      percentage: applied > 0 ? Math.round((stage.count / applied) * 100) : 0,
      dropoff_rate:
        prevCount > 0 ? Math.round(((prevCount - stage.count) / prevCount) * 100) : 0,
    }
  })
}

function calculateSourcePerformance(jobs: JobApplication[]): SourcePerformance[] {
  // Mock source data since jobs don't have a source field
  // In a real app, this would come from the job data
  const sources = APPLICATION_SOURCES.map((source) => {
    const sourceJobs = jobs.filter(() => Math.random() > 0.7) // Mock assignment
    const responses = sourceJobs.filter((j) =>
      ['Phone Screen', 'Interview', 'Offer', 'Rejected'].includes(j.status)
    ).length
    const interviews = sourceJobs.filter((j) =>
      ['Interview', 'Offer'].includes(j.status)
    ).length
    const offers = sourceJobs.filter((j) => j.status === 'Offer').length

    return {
      source,
      applications: sourceJobs.length,
      responses,
      interviews,
      offers,
      response_rate: sourceJobs.length > 0 ? (responses / sourceJobs.length) * 100 : 0,
    }
  })

  // Distribute jobs more realistically for demo
  const totalJobs = jobs.length
  const distribution = [0.35, 0.25, 0.15, 0.1, 0.1, 0.05] // LinkedIn, Indeed, etc.

  return APPLICATION_SOURCES.map((source, index) => {
    const count = Math.round(totalJobs * distribution[index])
    const responses = Math.round(count * (0.2 + Math.random() * 0.15))
    const interviews = Math.round(responses * (0.3 + Math.random() * 0.2))
    const offers = Math.round(interviews * (0.1 + Math.random() * 0.1))

    return {
      source,
      applications: count,
      responses,
      interviews,
      offers,
      response_rate: count > 0 ? (responses / count) * 100 : 0,
    }
  }).sort((a, b) => b.response_rate - a.response_rate)
}

function calculateCompanyStats(jobs: JobApplication[]): CompanyStats[] {
  const companyMap = new Map<string, JobApplication[]>()

  jobs.forEach((job) => {
    const existing = companyMap.get(job.company) || []
    companyMap.set(job.company, [...existing, job])
  })

  const stats: CompanyStats[] = []

  companyMap.forEach((companyJobs, company) => {
    const responses = companyJobs.filter((j) =>
      ['Phone Screen', 'Interview', 'Offer', 'Rejected'].includes(j.status)
    ).length
    const interviews = companyJobs.filter((j) =>
      ['Interview', 'Offer'].includes(j.status)
    ).length
    const offers = companyJobs.filter((j) => j.status === 'Offer').length

    // Calculate average response time
    const jobsWithResponse = companyJobs.filter(
      (j) =>
        j.application_date &&
        ['Phone Screen', 'Interview', 'Offer', 'Rejected'].includes(j.status)
    )
    let avgResponseTime: number | null = null
    if (jobsWithResponse.length > 0) {
      const totalDays = jobsWithResponse.reduce((sum, job) => {
        const applied = new Date(job.application_date!)
        const updated = new Date(job.updated_at)
        return sum + Math.ceil((updated.getTime() - applied.getTime()) / (1000 * 60 * 60 * 24))
      }, 0)
      avgResponseTime = Math.round(totalDays / jobsWithResponse.length)
    }

    stats.push({
      company,
      applications: companyJobs.length,
      responses,
      interviews,
      offers,
      response_rate: companyJobs.length > 0 ? (responses / companyJobs.length) * 100 : 0,
      avg_response_time_days: avgResponseTime,
    })
  })

  return stats.sort((a, b) => b.response_rate - a.response_rate).slice(0, 10)
}

function calculateResumePerformance(
  jobs: JobApplication[],
  resumes: Resume[]
): ResumePerformance[] {
  // Mock resume assignment for demo purposes
  // In a real app, jobs would have a resume_id field
  return resumes.map((resume, index) => {
    const assignedJobs = jobs.filter((_, i) => i % resumes.length === index)
    const interviews = assignedJobs.filter((j) =>
      ['Interview', 'Offer'].includes(j.status)
    ).length
    const offers = assignedJobs.filter((j) => j.status === 'Offer').length

    return {
      resume_id: resume.id,
      version_name: resume.version_name,
      applications: assignedJobs.length,
      interviews,
      offers,
      interview_rate:
        assignedJobs.length > 0 ? (interviews / assignedJobs.length) * 100 : 0,
      ats_score: resume.ats_score,
    }
  }).sort((a, b) => b.interview_rate - a.interview_rate)
}

function generateActivityLog(jobs: JobApplication[]): ActivityLogEntry[] {
  const activities: ActivityLogEntry[] = jobs
    .slice(0, 20)
    .map((job) => ({
      id: job.id,
      timestamp: job.updated_at,
      type: job.status === 'Offer' ? 'offer' : job.status === 'Interview' ? 'interview' : job.status === 'Applied' ? 'application' : 'status_change',
      description: `${job.status === 'Applied' ? 'Applied to' : `Status changed to ${job.status} for`} ${job.position}`,
      company: job.company,
      position: job.position,
    }))
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

  return activities
}

function exportToCSV(
  jobs: JobApplication[],
  filters: AnalyticsFilters
): void {
  const filteredJobs = filterJobsByDateRange(
    jobs,
    filters.dateRange,
    filters.customStartDate,
    filters.customEndDate
  ).filter((job) => {
    if (filters.status && job.status !== filters.status) return false
    return true
  })

  const headers = [
    'Company',
    'Position',
    'Status',
    'Application Date',
    'Location',
    'Job URL',
    'Created At',
    'Updated At',
  ]

  const rows = filteredJobs.map((job) => [
    job.company,
    job.position,
    job.status,
    job.application_date || '',
    job.location || '',
    job.job_url || '',
    job.created_at,
    job.updated_at,
  ])

  const csvContent = [
    headers.join(','),
    ...rows.map((row) =>
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    ),
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `analytics_export_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
}

function exportToJSON(
  jobs: JobApplication[],
  filters: AnalyticsFilters
): void {
  const filteredJobs = filterJobsByDateRange(
    jobs,
    filters.dateRange,
    filters.customStartDate,
    filters.customEndDate
  ).filter((job) => {
    if (filters.status && job.status !== filters.status) return false
    return true
  })

  const data = {
    exportedAt: new Date().toISOString(),
    filters,
    totalRecords: filteredJobs.length,
    jobs: filteredJobs,
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `analytics_export_${new Date().toISOString().slice(0, 10)}.json`
  link.click()
}

// ============================================================================
// Components
// ============================================================================

interface MetricCardProps {
  title: string
  value: string | number
  trend?: number
  icon: React.ComponentType<{ className?: string }>
  iconBgColor: string
  subtitle?: string
}

function MetricCard({
  title,
  value,
  trend,
  icon: Icon,
  iconBgColor,
  subtitle,
}: MetricCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
          )}
          {trend !== undefined && (
            <div className="mt-2 flex items-center gap-1">
              {trend >= 0 ? (
                <TrendingUp className="w-4 h-4 text-green-500" aria-hidden="true" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500" aria-hidden="true" />
              )}
              <span
                className={cn(
                  'text-sm font-medium',
                  trend >= 0 ? 'text-green-600' : 'text-red-600'
                )}
              >
                {trend >= 0 ? '+' : ''}
                {trend.toFixed(1)}%
              </span>
              <span className="text-sm text-gray-400">vs previous</span>
            </div>
          )}
        </div>
        <div
          className={cn('p-3 rounded-xl', iconBgColor)}
        >
          <Icon className="w-6 h-6 text-white" aria-hidden="true" />
        </div>
      </div>
    </div>
  )
}

interface LineChartComponentProps {
  data: TimelineDataPoint[]
  period: TimelinePeriod
  onPeriodChange: (period: TimelinePeriod) => void
}

function LineChartComponent({ data, period, onPeriodChange }: LineChartComponentProps) {
  const maxCount = Math.max(...data.map((d) => d.count), 1)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <LineChart className="w-5 h-5 text-primary-600" aria-hidden="true" />
          Application Timeline
        </h3>
        <div className="flex items-center gap-2">
          {TIMELINE_PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => onPeriodChange(option.value)}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded-lg transition-colors',
                period === option.value
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-500 hover:bg-gray-100'
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {data.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-gray-400">
          No data available for the selected period
        </div>
      ) : (
        <div className="relative">
          {/* Y-axis labels */}
          <div className="absolute left-0 top-0 bottom-8 w-8 flex flex-col justify-between text-xs text-gray-400">
            <span>{maxCount}</span>
            <span>{Math.round(maxCount / 2)}</span>
            <span>0</span>
          </div>

          {/* Chart area */}
          <div className="ml-10">
            <div className="flex items-end gap-1 h-48">
              {data.map((point, index) => (
                <div
                  key={point.date}
                  className="flex-1 flex flex-col items-center group"
                >
                  <div className="relative w-full flex justify-center">
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 hidden group-hover:block z-10">
                      <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
                        {point.count} applications
                      </div>
                    </div>

                    {/* Bar */}
                    <div
                      className="w-full max-w-[40px] bg-primary-500 rounded-t transition-all duration-300 hover:bg-primary-600 cursor-pointer"
                      style={{
                        height: `${(point.count / maxCount) * 180}px`,
                        minHeight: point.count > 0 ? '4px' : '2px',
                      }}
                    />

                    {/* Line connector */}
                    {index < data.length - 1 && (
                      <div
                        className="absolute right-0 top-0 w-full h-0.5 bg-primary-300 opacity-50"
                        style={{
                          transform: `translateY(-${(point.count / maxCount) * 180}px)`,
                        }}
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* X-axis labels */}
            <div className="flex gap-1 mt-2">
              {data.map((point) => (
                <div
                  key={point.date}
                  className="flex-1 text-center"
                >
                  <span className="text-xs text-gray-400 transform -rotate-45 inline-block origin-top-left">
                    {point.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface DonutChartProps {
  data: { label: string; value: number; color: string }[]
  title: string
}

function DonutChart({ data, title }: DonutChartProps) {
  const total = data.reduce((sum, item) => sum + item.value, 0)

  // Calculate stroke dash values for each segment
  const circumference = 2 * Math.PI * 45 // radius = 45
  let accumulatedOffset = 0

  const segments = data.map((item) => {
    const percentage = total > 0 ? item.value / total : 0
    const dashLength = percentage * circumference
    const offset = accumulatedOffset
    accumulatedOffset += dashLength
    return {
      ...item,
      percentage: percentage * 100,
      dashLength,
      dashOffset: circumference - offset,
    }
  })

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <PieChart className="w-5 h-5 text-primary-600" aria-hidden="true" />
        {title}
      </h3>

      <div className="flex items-center gap-8">
        {/* Donut */}
        <div className="relative">
          <svg width="140" height="140" viewBox="0 0 100 100">
            {/* Background circle */}
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="#f3f4f6"
              strokeWidth="10"
            />
            {/* Segments */}
            {segments.map((segment, index) => (
              <circle
                key={segment.label}
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke={segment.color}
                strokeWidth="10"
                strokeDasharray={`${segment.dashLength} ${circumference}`}
                strokeDashoffset={segment.dashOffset}
                transform="rotate(-90 50 50)"
                className="transition-all duration-500"
              />
            ))}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-gray-900">{total}</span>
            <span className="text-xs text-gray-500">Total</span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-1 space-y-2">
          {segments.map((segment) => (
            <div key={segment.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: segment.color }}
                />
                <span className="text-sm text-gray-600">{segment.label}</span>
              </div>
              <div className="text-sm">
                <span className="font-medium text-gray-900">{segment.value}</span>
                <span className="text-gray-400 ml-1">
                  ({segment.percentage.toFixed(0)}%)
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

interface FunnelChartProps {
  data: ConversionFunnelStage[]
}

function FunnelChart({ data }: FunnelChartProps) {
  const maxCount = Math.max(...data.map((d) => d.count), 1)

  const colors = ['bg-blue-500', 'bg-purple-500', 'bg-amber-500', 'bg-green-500']

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <Target className="w-5 h-5 text-primary-600" aria-hidden="true" />
        Conversion Funnel
      </h3>

      <div className="space-y-4">
        {data.map((stage, index) => (
          <div key={stage.stage}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">{stage.stage}</span>
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-gray-900">{stage.count}</span>
                <span className="text-gray-400">({stage.percentage}%)</span>
                {index > 0 && stage.dropoff_rate > 0 && (
                  <span className="text-red-500 text-xs">
                    -{stage.dropoff_rate}% drop
                  </span>
                )}
              </div>
            </div>
            <div className="relative">
              <div className="w-full bg-gray-100 rounded-full h-8 overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500 flex items-center justify-end pr-2',
                    colors[index]
                  )}
                  style={{ width: `${Math.max(stage.percentage, 5)}%` }}
                >
                  {stage.percentage > 15 && (
                    <span className="text-xs font-medium text-white">
                      {stage.percentage}%
                    </span>
                  )}
                </div>
              </div>
              {index < data.length - 1 && (
                <ArrowRight className="absolute -right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300" />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

interface SourceBarChartProps {
  data: SourcePerformance[]
}

function SourceBarChart({ data }: SourceBarChartProps) {
  const maxRate = Math.max(...data.map((d) => d.response_rate), 1)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-primary-600" aria-hidden="true" />
        Source Performance
      </h3>

      <div className="space-y-4">
        {data.map((source) => (
          <div key={source.source}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">{source.source}</span>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-500">{source.applications} apps</span>
                <span className="font-medium text-gray-900">
                  {source.response_rate.toFixed(0)}% response
                </span>
              </div>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary-400 to-primary-600 rounded-full transition-all duration-500"
                style={{ width: `${(source.response_rate / maxRate) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

interface CompanyTableProps {
  data: CompanyStats[]
}

function CompanyTable({ data }: CompanyTableProps) {
  const [expanded, setExpanded] = useState(false)
  const displayData = expanded ? data : data.slice(0, 5)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <Briefcase className="w-5 h-5 text-primary-600" aria-hidden="true" />
        Top Performing Companies
      </h3>

      {data.length === 0 ? (
        <p className="text-gray-500 text-center py-8">No company data available</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                    Company
                  </th>
                  <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                    Apps
                  </th>
                  <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                    Responses
                  </th>
                  <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                    Interviews
                  </th>
                  <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                    Response Rate
                  </th>
                  <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                    Avg Time
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {displayData.map((company) => (
                  <tr key={company.company} className="hover:bg-gray-50">
                    <td className="py-3 text-sm font-medium text-gray-900">
                      {company.company}
                    </td>
                    <td className="py-3 text-sm text-gray-500 text-right">
                      {company.applications}
                    </td>
                    <td className="py-3 text-sm text-gray-500 text-right">
                      {company.responses}
                    </td>
                    <td className="py-3 text-sm text-gray-500 text-right">
                      {company.interviews}
                    </td>
                    <td className="py-3 text-right">
                      <span
                        className={cn(
                          'inline-flex px-2 py-0.5 text-xs font-medium rounded-full',
                          company.response_rate >= 50
                            ? 'bg-green-100 text-green-700'
                            : company.response_rate >= 25
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-gray-100 text-gray-700'
                        )}
                      >
                        {company.response_rate.toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 text-sm text-gray-500 text-right">
                      {company.avg_response_time_days !== null
                        ? `${company.avg_response_time_days}d`
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.length > 5 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-4 w-full text-center text-sm text-primary-600 hover:text-primary-700 font-medium flex items-center justify-center gap-1"
            >
              {expanded ? (
                <>
                  Show less <ChevronUp className="w-4 h-4" />
                </>
              ) : (
                <>
                  Show all {data.length} companies <ChevronDown className="w-4 h-4" />
                </>
              )}
            </button>
          )}
        </>
      )}
    </div>
  )
}

interface ResumeTableProps {
  data: ResumePerformance[]
}

function ResumeTable({ data }: ResumeTableProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <FileText className="w-5 h-5 text-primary-600" aria-hidden="true" />
        Resume Version Performance
      </h3>

      {data.length === 0 ? (
        <p className="text-gray-500 text-center py-8">No resume data available</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                  Version
                </th>
                <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                  ATS Score
                </th>
                <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                  Applications
                </th>
                <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                  Interviews
                </th>
                <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider pb-3">
                  Interview Rate
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.map((resume) => (
                <tr key={resume.resume_id} className="hover:bg-gray-50">
                  <td className="py-3 text-sm font-medium text-gray-900">
                    {resume.version_name}
                  </td>
                  <td className="py-3 text-right">
                    {resume.ats_score !== null ? (
                      <span
                        className={cn(
                          'inline-flex px-2 py-0.5 text-xs font-medium rounded-full',
                          resume.ats_score >= 80
                            ? 'bg-green-100 text-green-700'
                            : resume.ats_score >= 60
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-red-100 text-red-700'
                        )}
                      >
                        {resume.ats_score}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                  <td className="py-3 text-sm text-gray-500 text-right">
                    {resume.applications}
                  </td>
                  <td className="py-3 text-sm text-gray-500 text-right">
                    {resume.interviews}
                  </td>
                  <td className="py-3 text-right">
                    <span
                      className={cn(
                        'inline-flex px-2 py-0.5 text-xs font-medium rounded-full',
                        resume.interview_rate >= 30
                          ? 'bg-green-100 text-green-700'
                          : resume.interview_rate >= 15
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {resume.interview_rate.toFixed(0)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

interface ActivityLogProps {
  data: ActivityLogEntry[]
}

function ActivityLog({ data }: ActivityLogProps) {
  const getActivityIcon = (type: ActivityLogEntry['type']) => {
    switch (type) {
      case 'offer':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'interview':
        return <Users className="w-4 h-4 text-purple-500" />
      case 'application':
        return <Briefcase className="w-4 h-4 text-blue-500" />
      default:
        return <Activity className="w-4 h-4 text-gray-500" />
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <Activity className="w-5 h-5 text-primary-600" aria-hidden="true" />
        Recent Activity
      </h3>

      {data.length === 0 ? (
        <p className="text-gray-500 text-center py-8">No recent activity</p>
      ) : (
        <div className="space-y-4 max-h-[400px] overflow-y-auto">
          {data.map((entry) => (
            <div
              key={`${entry.id}-${entry.timestamp}`}
              className="flex items-start gap-3 pb-4 border-b border-gray-50 last:border-0"
            >
              <div className="mt-0.5">{getActivityIcon(entry.type)}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-900">{entry.description}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {entry.company} - {formatDate(entry.timestamp, 'relative')}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function AnalyticsPage() {
  const { user, tokens, isLoading: authLoading } = useAuth()
  const router = useRouter()

  // Data state
  const [jobs, setJobs] = useState<JobApplication[]>([])
  const [resumes, setResumes] = useState<Resume[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Filter state
  const [filters, setFilters] = useState<AnalyticsFilters>({
    dateRange: '30d',
    status: '',
    source: '',
  })
  const [timelinePeriod, setTimelinePeriod] = useState<TimelinePeriod>('weekly')
  const [showFilters, setShowFilters] = useState(false)

  // Auth redirect
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  // Load data
  const loadData = useCallback(async () => {
    if (!tokens?.access_token) return

    try {
      const [jobsData, resumesData] = await Promise.all([
        jobsApi.list(tokens.access_token),
        resumesApi.list(tokens.access_token),
      ])

      setJobs(jobsData as JobApplication[])
      setResumes(resumesData as Resume[])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [tokens])

  useEffect(() => {
    if (tokens?.access_token) {
      loadData()
    }
  }, [tokens, loadData])

  const handleRefresh = () => {
    setIsRefreshing(true)
    loadData()
  }

  // Filter jobs based on current filters
  const filteredJobs = useMemo(() => {
    let result = filterJobsByDateRange(
      jobs,
      filters.dateRange,
      filters.customStartDate,
      filters.customEndDate
    )

    if (filters.status) {
      result = result.filter((job) => job.status === filters.status)
    }

    return result
  }, [jobs, filters])

  // Calculate previous period for trends
  const previousPeriodJobs = useMemo(() => {
    const { start, end } = getDateRangeFromOption(
      filters.dateRange,
      filters.customStartDate,
      filters.customEndDate
    )
    const periodLength = end.getTime() - start.getTime()
    const prevStart = new Date(start.getTime() - periodLength)
    const prevEnd = new Date(start.getTime())

    return jobs.filter((job) => {
      const jobDate = new Date(job.created_at)
      return jobDate >= prevStart && jobDate < prevEnd
    })
  }, [jobs, filters])

  // Calculate all metrics
  const overview = useMemo(
    () => calculateOverviewMetrics(filteredJobs, previousPeriodJobs),
    [filteredJobs, previousPeriodJobs]
  )

  const timelineData = useMemo(
    () =>
      generateTimelineData(
        filteredJobs,
        timelinePeriod,
        filters.dateRange,
        filters.customStartDate,
        filters.customEndDate
      ),
    [filteredJobs, timelinePeriod, filters]
  )

  const statusBreakdown = useMemo(() => {
    const colors: Record<JobStatus, string> = {
      Bookmarked: '#6b7280',
      Applied: '#3b82f6',
      'Phone Screen': '#8b5cf6',
      Interview: '#f59e0b',
      Offer: '#22c55e',
      Rejected: '#ef4444',
    }

    return JOB_STATUSES.map((status) => ({
      label: status,
      value: filteredJobs.filter((j) => j.status === status).length,
      color: colors[status],
    }))
  }, [filteredJobs])

  const conversionFunnel = useMemo(
    () => calculateConversionFunnel(filteredJobs),
    [filteredJobs]
  )

  const sourcePerformance = useMemo(
    () => calculateSourcePerformance(filteredJobs),
    [filteredJobs]
  )

  const companyStats = useMemo(
    () => calculateCompanyStats(filteredJobs),
    [filteredJobs]
  )

  const resumePerformance = useMemo(
    () => calculateResumePerformance(filteredJobs, resumes),
    [filteredJobs, resumes]
  )

  const activityLog = useMemo(
    () => generateActivityLog(filteredJobs),
    [filteredJobs]
  )

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-gray-500 mt-1">
            Track your job search performance and identify trends
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            aria-label="Refresh data"
          >
            <RefreshCw
              className={cn('w-4 h-4 mr-2', isRefreshing && 'animate-spin')}
            />
            Refresh
          </button>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
              showFilters
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </button>

          <div className="relative">
            <button
              className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
              onClick={() => {
                const dropdown = document.getElementById('export-dropdown')
                dropdown?.classList.toggle('hidden')
              }}
            >
              <Download className="w-4 h-4 mr-2" />
              Export
              <ChevronDown className="w-4 h-4 ml-1" />
            </button>
            <div
              id="export-dropdown"
              className="hidden absolute right-0 mt-2 w-40 bg-white rounded-lg shadow-lg border border-gray-100 z-10"
            >
              <button
                onClick={() => {
                  exportToCSV(jobs, filters)
                  document.getElementById('export-dropdown')?.classList.add('hidden')
                }}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-t-lg"
              >
                Export as CSV
              </button>
              <button
                onClick={() => {
                  exportToJSON(jobs, filters)
                  document.getElementById('export-dropdown')?.classList.add('hidden')
                }}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-b-lg"
              >
                Export as JSON
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Date Range
              </label>
              <select
                value={filters.dateRange}
                onChange={(e) =>
                  setFilters({ ...filters, dateRange: e.target.value as DateRangeOption })
                }
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {DATE_RANGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {filters.dateRange === 'custom' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={filters.customStartDate || ''}
                    onChange={(e) =>
                      setFilters({ ...filters, customStartDate: e.target.value })
                    }
                    className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={filters.customEndDate || ''}
                    onChange={(e) =>
                      setFilters({ ...filters, customEndDate: e.target.value })
                    }
                    className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Status
              </label>
              <select
                value={filters.status || ''}
                onChange={(e) =>
                  setFilters({ ...filters, status: e.target.value as JobStatus | '' })
                }
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All Statuses</option>
                {JOB_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Source
              </label>
              <select
                value={filters.source || ''}
                onChange={(e) => setFilters({ ...filters, source: e.target.value })}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All Sources</option>
                {APPLICATION_SOURCES.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </div>

            <div className="ml-auto">
              <button
                onClick={() =>
                  setFilters({
                    dateRange: '30d',
                    status: '',
                    source: '',
                    customStartDate: undefined,
                    customEndDate: undefined,
                  })
                }
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Reset filters
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Overview Section */}
      <section className="mb-8" aria-labelledby="overview-heading">
        <h2 id="overview-heading" className="sr-only">
          Overview Metrics
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard
            title="Total Applications"
            value={overview.total_applications}
            icon={Briefcase}
            iconBgColor="bg-blue-500"
          />
          <MetricCard
            title="Response Rate"
            value={`${overview.response_rate.toFixed(0)}%`}
            trend={overview.response_rate_trend}
            icon={TrendingUp}
            iconBgColor="bg-purple-500"
          />
          <MetricCard
            title="Interview Rate"
            value={`${overview.interview_rate.toFixed(0)}%`}
            trend={overview.interview_rate_trend}
            icon={Users}
            iconBgColor="bg-amber-500"
          />
          <MetricCard
            title="Offer Rate"
            value={`${overview.offer_rate.toFixed(0)}%`}
            trend={overview.offer_rate_trend}
            icon={CheckCircle}
            iconBgColor="bg-green-500"
          />
          <MetricCard
            title="Avg Response Time"
            value={overview.avg_response_time_days > 0 ? `${overview.avg_response_time_days}d` : '-'}
            icon={Clock}
            iconBgColor="bg-gray-500"
            subtitle="days to hear back"
          />
        </div>
      </section>

      {/* Charts Section */}
      <section className="mb-8 space-y-6" aria-labelledby="charts-heading">
        <h2 id="charts-heading" className="sr-only">
          Analytics Charts
        </h2>

        {/* Timeline Chart */}
        <LineChartComponent
          data={timelineData}
          period={timelinePeriod}
          onPeriodChange={setTimelinePeriod}
        />

        {/* Two Column Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DonutChart data={statusBreakdown} title="Status Breakdown" />
          <FunnelChart data={conversionFunnel} />
        </div>

        {/* Source Performance */}
        <SourceBarChart data={sourcePerformance} />
      </section>

      {/* Tables Section */}
      <section className="mb-8 space-y-6" aria-labelledby="tables-heading">
        <h2 id="tables-heading" className="sr-only">
          Detailed Analytics Tables
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CompanyTable data={companyStats} />
          <ResumeTable data={resumePerformance} />
        </div>

        {/* Activity Log */}
        <ActivityLog data={activityLog} />
      </section>
    </div>
  )
}
