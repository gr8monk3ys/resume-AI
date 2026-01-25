'use client'

import {
  Plus,
  Calendar,
  BarChart3,
  List,
  Kanban,
  Settings,
} from 'lucide-react'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState, useCallback } from 'react'

import { JobFormModal } from '@/components/jobs'
import { jobsApi, filtersApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { TabType } from '@/lib/jobs'
import { cn, generateId } from '@/lib/utils'

import type {
  JobApplication,
  JobStatus,
  JobStats,
  InterviewEvent,
  CompanyFilter,
} from '@/types'

// Dynamic imports for heavy tab components (code splitting)
const KanbanBoard = dynamic(() => import('@/components/jobs').then(mod => ({ default: mod.KanbanBoard })), {
  loading: () => <TabLoadingSkeleton />,
  ssr: false,
})

const ListView = dynamic(() => import('@/components/jobs').then(mod => ({ default: mod.ListView })), {
  loading: () => <TabLoadingSkeleton />,
  ssr: false,
})

const AnalyticsTab = dynamic(() => import('@/components/jobs').then(mod => ({ default: mod.AnalyticsTab })), {
  loading: () => <TabLoadingSkeleton />,
  ssr: false,
})

const TimelineTab = dynamic(() => import('@/components/jobs').then(mod => ({ default: mod.TimelineTab })), {
  loading: () => <TabLoadingSkeleton />,
  ssr: false,
})

// Loading skeleton for lazy-loaded tabs
function TabLoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 bg-gray-200 rounded w-1/4" />
      <div className="h-64 bg-gray-200 rounded" />
      <div className="h-48 bg-gray-200 rounded" />
    </div>
  )
}

/**
 * Jobs page client component
 * Handles all interactive functionality for job pipeline
 */
export function JobsPageClient() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()

  // State
  const [jobs, setJobs] = useState<JobApplication[]>([])
  const [stats, setStats] = useState<JobStats | null>(null)
  const [events, setEvents] = useState<InterviewEvent[]>([])
  const [companyFilters, setCompanyFilters] = useState<CompanyFilter[]>([])
  const [keywordFilters, setKeywordFilters] = useState<{ id: string; keyword: string; filter_type: string }[]>([])
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

  const loadData = useCallback(async () => {
    if (!isAuthenticated) return

    try {
      const [jobsData, statsData, companyFiltersData, keywordFiltersData] = await Promise.all([
        jobsApi.list(),
        jobsApi.getStats().catch(() => null),
        filtersApi.getCompanyFilters(),
        filtersApi.getKeywordFilters(),
      ])

      setJobs(jobsData)
      setStats(statsData)
      setCompanyFilters(companyFiltersData)
      setKeywordFilters(keywordFiltersData)

      // Load events from localStorage (in real app, would be from API)
      const storedEvents = localStorage.getItem('interview_events')
      if (storedEvents) {
        setEvents(JSON.parse(storedEvents) as InterviewEvent[])
      }
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated])

  // Load data
  useEffect(() => {
    if (isAuthenticated) {
      void loadData()
    }
  }, [isAuthenticated, loadData])

  // Job CRUD operations - wrapped in useCallback to prevent unnecessary re-renders
  const handleAddJob = useCallback(async (data: Partial<JobApplication>) => {
    if (!isAuthenticated) return

    try {
      const newJob = await jobsApi.create({
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

      setJobs((prevJobs) => [newJob, ...prevJobs])
      setShowJobModal(false)
      setAddJobStatus(undefined)
    } catch (error) {
      console.error('Failed to add job:', error)
    }
  }, [isAuthenticated])

  const handleUpdateJob = useCallback(async (data: Partial<JobApplication>) => {
    if (!isAuthenticated || !editingJob) return

    try {
      const updatedJob = await jobsApi.update(editingJob.id, {
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

      setJobs((prevJobs) => prevJobs.map((j) => (j.id === editingJob.id ? (updatedJob) : j)))
      setEditingJob(null)
    } catch (error) {
      console.error('Failed to update job:', error)
    }
  }, [isAuthenticated, editingJob])

  const handleDeleteJob = useCallback(async (id: number) => {
    if (!isAuthenticated) return

    if (!confirm('Are you sure you want to delete this job application?')) return

    try {
      await jobsApi.delete(id)
      setJobs((prevJobs) => prevJobs.filter((j) => j.id !== id))
      setEditingJob(null)
    } catch (error) {
      console.error('Failed to delete job:', error)
    }
  }, [isAuthenticated])

  const handleStatusChange = useCallback(async (id: number, status: JobStatus) => {
    if (!isAuthenticated) return

    try {
      await jobsApi.updateStatus(id, status)
      setJobs((prevJobs) => prevJobs.map((j) => (j.id === id ? { ...j, status } : j)))
    } catch (error) {
      console.error('Failed to update job status:', error)
    }
  }, [isAuthenticated])

  const handleBulkDelete = useCallback(async (ids: number[]) => {
    if (!isAuthenticated) return

    try {
      await Promise.all(ids.map((id) => jobsApi.delete(id)))
      setJobs((prevJobs) => prevJobs.filter((j) => !ids.includes(j.id)))
    } catch (error) {
      console.error('Failed to delete jobs:', error)
    }
  }, [isAuthenticated])

  const handleBulkStatusChange = useCallback(async (ids: number[], status: JobStatus) => {
    if (!isAuthenticated) return

    try {
      await Promise.all(
        ids.map((id) => jobsApi.updateStatus(id, status))
      )
      setJobs((prevJobs) => prevJobs.map((j) => (ids.includes(j.id) ? { ...j, status } : j)))
    } catch (error) {
      console.error('Failed to update job statuses:', error)
    }
  }, [isAuthenticated])

  // Callback handlers for KanbanBoard inline functions
  const handleKanbanAddJob = useCallback((status: JobStatus) => {
    setAddJobStatus(status)
    setShowJobModal(true)
  }, [])

  const handleEditJob = useCallback((job: JobApplication) => {
    setEditingJob(job)
  }, [])

  const handleReorder = useCallback((newJobs: JobApplication[]) => {
    setJobs(newJobs)
  }, [])

  // Stable callback wrappers that handle async operations without inline arrow functions
  // These prevent unnecessary re-renders in child components
  const handleDeleteJobSync = useCallback((id: number) => {
    void handleDeleteJob(id)
  }, [handleDeleteJob])

  const handleStatusChangeSync = useCallback((id: number, status: JobStatus) => {
    void handleStatusChange(id, status)
  }, [handleStatusChange])

  const handleBulkDeleteSync = useCallback((ids: number[]) => {
    void handleBulkDelete(ids)
  }, [handleBulkDelete])

  const handleBulkStatusChangeSync = useCallback((ids: number[], status: JobStatus) => {
    void handleBulkStatusChange(ids, status)
  }, [handleBulkStatusChange])

  const handleAddJobSync = useCallback((data: Partial<JobApplication>) => {
    void handleAddJob(data)
  }, [handleAddJob])

  const handleUpdateJobSync = useCallback((data: Partial<JobApplication>) => {
    void handleUpdateJob(data)
  }, [handleUpdateJob])

  // Modal close handlers
  const handleCloseAddModal = useCallback(() => {
    setShowJobModal(false)
    setAddJobStatus(undefined)
  }, [])

  const handleCloseEditModal = useCallback(() => {
    setEditingJob(null)
  }, [])

  // Add job button handler
  const handleAddJobButtonClick = useCallback(() => {
    setAddJobStatus(undefined)
    setShowJobModal(true)
  }, [])

  // Event operations (stored in localStorage for now)
  const handleAddEvent = useCallback((event: Omit<InterviewEvent, 'id' | 'created_at'>) => {
    const newEvent: InterviewEvent = {
      ...event,
      id: generateId(),
      created_at: new Date().toISOString(),
    }

    setEvents((prevEvents) => {
      const updatedEvents = [...prevEvents, newEvent]
      localStorage.setItem('interview_events', JSON.stringify(updatedEvents))
      return updatedEvents
    })
  }, [])

  const handleUpdateEvent = useCallback((id: string, updates: Partial<InterviewEvent>) => {
    setEvents((prevEvents) => {
      const updatedEvents = prevEvents.map((e) =>
        e.id === id ? { ...e, ...updates } : e
      )
      localStorage.setItem('interview_events', JSON.stringify(updatedEvents))
      return updatedEvents
    })
  }, [])

  const handleDeleteEvent = useCallback((id: string) => {
    if (!confirm('Are you sure you want to delete this event?')) return

    setEvents((prevEvents) => {
      const updatedEvents = prevEvents.filter((e) => e.id !== id)
      localStorage.setItem('interview_events', JSON.stringify(updatedEvents))
      return updatedEvents
    })
  }, [])

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

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
            onClick={handleAddJobButtonClick}
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
          {[
            { id: 'kanban' as const, label: 'Kanban Board', icon: Kanban },
            { id: 'list' as const, label: 'List View', icon: List },
            { id: 'analytics' as const, label: 'Analytics', icon: BarChart3 },
            { id: 'timeline' as const, label: 'Timeline', icon: Calendar },
          ].map((tab) => (
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
          onAddJob={handleKanbanAddJob}
          onEditJob={handleEditJob}
          onDeleteJob={handleDeleteJobSync}
          onStatusChange={handleStatusChangeSync}
          onReorder={handleReorder}
          companyFilters={companyFilters}
        />
      )}

      {activeTab === 'list' && (
        <ListView
          jobs={jobs}
          onEditJob={handleEditJob}
          onDeleteJob={handleDeleteJobSync}
          onStatusChange={handleStatusChangeSync}
          onBulkDelete={handleBulkDeleteSync}
          onBulkStatusChange={handleBulkStatusChangeSync}
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
        <JobFormModal
          initialStatus={addJobStatus}
          onClose={handleCloseAddModal}
          onSave={handleAddJobSync}
        />
      )}

      {/* Edit Job Modal */}
      {editingJob && (
        <JobFormModal
          job={editingJob}
          onClose={handleCloseEditModal}
          onSave={handleUpdateJobSync}
          onDelete={handleDeleteJobSync}
        />
      )}
    </div>
  )
}
