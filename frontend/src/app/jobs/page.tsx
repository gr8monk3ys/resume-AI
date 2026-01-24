'use client'

/**
 * Job Pipeline page component.
 * Provides a comprehensive view of job applications with Kanban, List, Analytics, and Timeline views.
 * @module jobs/page
 */

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { jobsApi, filtersApi } from '@/lib/api'
import type {
  JobApplication,
  JobStatus,
  JobStats,
  InterviewEvent,
  CompanyFilter,
} from '@/types'
import { cn, generateId } from '@/lib/utils'
import {
  Plus,
  Calendar,
  BarChart3,
  List,
  Kanban,
  Settings,
} from 'lucide-react'
import {
  KanbanBoard,
  ListView,
  AnalyticsTab,
  TimelineTab,
  JobModal,
  TabType,
} from './components'

// ============================================================================
// JobsPage Component
// ============================================================================

/**
 * Main page component for the job pipeline feature.
 * Handles data fetching, state management, and tab navigation.
 */
export default function JobsPage() {
  const { user, tokens, isLoading: authLoading } = useAuth()
  const router = useRouter()

  // Data state
  const [jobs, setJobs] = useState<JobApplication[]>([])
  const [stats, setStats] = useState<JobStats | null>(null)
  const [events, setEvents] = useState<InterviewEvent[]>([])
  const [companyFilters, setCompanyFilters] = useState<CompanyFilter[]>([])
  const [keywordFilters, setKeywordFilters] = useState<{ id: string; keyword: string; filter_type: string }[]>([])

  // UI state
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabType>('kanban')
  const [showJobModal, setShowJobModal] = useState(false)
  const [editingJob, setEditingJob] = useState<JobApplication | null>(null)
  const [addJobStatus, setAddJobStatus] = useState<JobStatus | undefined>(undefined)

  // Auth redirect
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  // Data loading
  const loadData = useCallback(async () => {
    if (!tokens?.access_token) return

    try {
      const [jobsData, statsData, companyFiltersData, keywordFiltersData] = await Promise.all([
        jobsApi.list(tokens.access_token),
        jobsApi.getStats(tokens.access_token).catch(() => null),
        filtersApi.getCompanyFilters(),
        filtersApi.getKeywordFilters(),
      ])

      setJobs(jobsData as JobApplication[])
      setStats(statsData)
      setCompanyFilters(companyFiltersData)
      setKeywordFilters(keywordFiltersData)

      // Load events from localStorage (in real app, would be from API)
      const storedEvents = localStorage.getItem('interview_events')
      if (storedEvents) {
        setEvents(JSON.parse(storedEvents))
      }
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [tokens])

  useEffect(() => {
    if (tokens?.access_token) {
      loadData()
    }
  }, [tokens, loadData])

  // ============================================================================
  // Job CRUD Operations
  // ============================================================================

  const handleAddJob = async (data: Partial<JobApplication>) => {
    if (!tokens?.access_token) return

    try {
      const newJob = await jobsApi.create(tokens.access_token, {
        company: data.company || '',
        position: data.position || '',
        job_description: data.job_description || undefined,
        status: data.status || 'Bookmarked',
        application_date: data.application_date || undefined,
        deadline: data.deadline || undefined,
        location: data.location || undefined,
        job_url: data.job_url || undefined,
        notes: data.notes || undefined,
      })

      setJobs([newJob as JobApplication, ...jobs])
      setShowJobModal(false)
      setAddJobStatus(undefined)
    } catch (error) {
      console.error('Failed to add job:', error)
    }
  }

  const handleUpdateJob = async (data: Partial<JobApplication>) => {
    if (!tokens?.access_token || !editingJob) return

    try {
      const updatedJob = await jobsApi.update(tokens.access_token, editingJob.id, {
        company: data.company,
        position: data.position,
        job_description: data.job_description || undefined,
        status: data.status,
        application_date: data.application_date || undefined,
        deadline: data.deadline || undefined,
        location: data.location || undefined,
        job_url: data.job_url || undefined,
        notes: data.notes || undefined,
      })

      setJobs(jobs.map((j) => (j.id === editingJob.id ? (updatedJob as JobApplication) : j)))
      setEditingJob(null)
    } catch (error) {
      console.error('Failed to update job:', error)
    }
  }

  const handleDeleteJob = async (id: number) => {
    if (!tokens?.access_token) return

    if (!confirm('Are you sure you want to delete this job application?')) return

    try {
      await jobsApi.delete(tokens.access_token, id)
      setJobs(jobs.filter((j) => j.id !== id))
      setEditingJob(null)
    } catch (error) {
      console.error('Failed to delete job:', error)
    }
  }

  const handleStatusChange = async (id: number, status: JobStatus) => {
    if (!tokens?.access_token) return

    try {
      await jobsApi.updateStatus(tokens.access_token, id, status)
      setJobs(jobs.map((j) => (j.id === id ? { ...j, status } : j)))
    } catch (error) {
      console.error('Failed to update job status:', error)
    }
  }

  const handleBulkDelete = async (ids: number[]) => {
    if (!tokens?.access_token) return

    try {
      await Promise.all(ids.map((id) => jobsApi.delete(tokens.access_token, id)))
      setJobs(jobs.filter((j) => !ids.includes(j.id)))
    } catch (error) {
      console.error('Failed to delete jobs:', error)
    }
  }

  const handleBulkStatusChange = async (ids: number[], status: JobStatus) => {
    if (!tokens?.access_token) return

    try {
      await Promise.all(
        ids.map((id) => jobsApi.updateStatus(tokens.access_token, id, status))
      )
      setJobs(jobs.map((j) => (ids.includes(j.id) ? { ...j, status } : j)))
    } catch (error) {
      console.error('Failed to update job statuses:', error)
    }
  }

  // ============================================================================
  // Event Operations (localStorage for now)
  // ============================================================================

  const handleAddEvent = (event: Omit<InterviewEvent, 'id' | 'created_at'>) => {
    const newEvent: InterviewEvent = {
      ...event,
      id: generateId(),
      created_at: new Date().toISOString(),
    }

    const updatedEvents = [...events, newEvent]
    setEvents(updatedEvents)
    localStorage.setItem('interview_events', JSON.stringify(updatedEvents))
  }

  const handleUpdateEvent = (id: string, updates: Partial<InterviewEvent>) => {
    const updatedEvents = events.map((e) =>
      e.id === id ? { ...e, ...updates } : e
    )
    setEvents(updatedEvents)
    localStorage.setItem('interview_events', JSON.stringify(updatedEvents))
  }

  const handleDeleteEvent = (id: string) => {
    if (!confirm('Are you sure you want to delete this event?')) return

    const updatedEvents = events.filter((e) => e.id !== id)
    setEvents(updatedEvents)
    localStorage.setItem('interview_events', JSON.stringify(updatedEvents))
  }

  // ============================================================================
  // Loading State
  // ============================================================================

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  // ============================================================================
  // Tab Configuration
  // ============================================================================

  const tabs = [
    { id: 'kanban' as const, label: 'Kanban Board', icon: Kanban },
    { id: 'list' as const, label: 'List View', icon: List },
    { id: 'analytics' as const, label: 'Analytics', icon: BarChart3 },
    { id: 'timeline' as const, label: 'Timeline', icon: Calendar },
  ]

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Pipeline</h1>
          <p className="text-gray-500">
            Track applications, interviews, and your job search progress
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/jobs/filters"
            className="inline-flex items-center px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 shadow-sm"
          >
            <Settings className="w-4 h-4 mr-2" />
            Filters
            {(companyFilters.length > 0 || keywordFilters.length > 0) && (
              <span className="ml-2 px-2 py-0.5 text-xs bg-primary-100 text-primary-700 rounded-full">
                {companyFilters.length + keywordFilters.length}
              </span>
            )}
          </Link>
          <button
            onClick={() => {
              setAddJobStatus(undefined)
              setShowJobModal(true)
            }}
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 shadow-sm"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Job
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-4 -mb-px" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'kanban' && (
        <KanbanBoard
          jobs={jobs}
          onAddJob={(status) => {
            setAddJobStatus(status)
            setShowJobModal(true)
          }}
          onEditJob={(job) => setEditingJob(job)}
          onDeleteJob={handleDeleteJob}
          onStatusChange={handleStatusChange}
          onReorder={setJobs}
          companyFilters={companyFilters}
        />
      )}

      {activeTab === 'list' && (
        <ListView
          jobs={jobs}
          onEditJob={(job) => setEditingJob(job)}
          onDeleteJob={handleDeleteJob}
          onStatusChange={handleStatusChange}
          onBulkDelete={handleBulkDelete}
          onBulkStatusChange={handleBulkStatusChange}
        />
      )}

      {activeTab === 'analytics' && <AnalyticsTab jobs={jobs} stats={stats} />}

      {activeTab === 'timeline' && (
        <TimelineTab
          jobs={jobs}
          events={events}
          onAddEvent={handleAddEvent}
          onUpdateEvent={handleUpdateEvent}
          onDeleteEvent={handleDeleteEvent}
        />
      )}

      {/* Add Job Modal */}
      {showJobModal && (
        <JobModal
          initialStatus={addJobStatus}
          onClose={() => {
            setShowJobModal(false)
            setAddJobStatus(undefined)
          }}
          onSave={handleAddJob}
        />
      )}

      {/* Edit Job Modal */}
      {editingJob && (
        <JobModal
          job={editingJob}
          onClose={() => setEditingJob(null)}
          onSave={handleUpdateJob}
          onDelete={handleDeleteJob}
        />
      )}
    </div>
  )
}
