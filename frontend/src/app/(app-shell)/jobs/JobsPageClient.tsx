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
import { useCallback, useEffect, useState } from 'react'

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
  KeywordFilter,
} from '@/types'

const KanbanBoard = dynamic(
  () => import('@/components/jobs/KanbanBoard').then((mod) => ({ default: mod.KanbanBoard })),
  {
    loading: () => <TabLoadingSkeleton />,
    ssr: false,
  }
)

const ListView = dynamic(
  () => import('@/components/jobs/ListView').then((mod) => ({ default: mod.ListView })),
  {
    loading: () => <TabLoadingSkeleton />,
    ssr: false,
  }
)

const AnalyticsTab = dynamic(
  () => import('@/components/jobs/AnalyticsTab').then((mod) => ({ default: mod.AnalyticsTab })),
  {
    loading: () => <TabLoadingSkeleton />,
    ssr: false,
  }
)

const TimelineTab = dynamic(
  () => import('@/components/jobs/TimelineTab').then((mod) => ({ default: mod.TimelineTab })),
  {
    loading: () => <TabLoadingSkeleton />,
    ssr: false,
  }
)

const JOB_TABS: Array<{
  id: TabType
  label: string
  icon: typeof Kanban
}> = [
  { id: 'kanban', label: 'Kanban Board', icon: Kanban },
  { id: 'list', label: 'List View', icon: List },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'timeline', label: 'Timeline', icon: Calendar },
]

interface JobsPageState {
  jobs: JobApplication[]
  stats: JobStats | null
  events: InterviewEvent[]
  companyFilters: CompanyFilter[]
  keywordFilters: KeywordFilter[]
  isLoading: boolean
  activeTab: TabType
  showJobModal: boolean
  editingJob: JobApplication | null
  addJobStatus: JobStatus | undefined
}

const INITIAL_JOBS_PAGE_STATE: JobsPageState = {
  jobs: [],
  stats: null,
  events: [],
  companyFilters: [],
  keywordFilters: [],
  isLoading: true,
  activeTab: 'kanban',
  showJobModal: false,
  editingJob: null,
  addJobStatus: undefined,
}

function readInterviewEvents(): InterviewEvent[] {
  const storedEvents = localStorage.getItem('interview_events')
  if (!storedEvents) {
    return []
  }

  try {
    return JSON.parse(storedEvents) as InterviewEvent[]
  } catch (error) {
    console.error('Failed to parse stored interview events:', error)
    return []
  }
}

function persistInterviewEvents(events: InterviewEvent[]) {
  localStorage.setItem('interview_events', JSON.stringify(events))
}

function TabLoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 w-1/4 rounded bg-gray-200" />
      <div className="h-64 rounded bg-gray-200" />
      <div className="h-48 rounded bg-gray-200" />
    </div>
  )
}

function PageLoadingState() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary-600" />
    </div>
  )
}

function JobsPageHeader({
  filterCount,
  onAddJob,
}: {
  filterCount: number
  onAddJob: () => void
}) {
  return (
    <div className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Job Pipeline</h1>
        <p className="text-gray-500">
          Track applications, interviews, and your job search progress
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Link
          href="/jobs/filters"
          className="inline-flex items-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-700 shadow-sm hover:bg-gray-50"
        >
          <Settings className="mr-2 h-4 w-4" />
          Filters
          {filterCount > 0 && (
            <span className="ml-2 rounded-full bg-primary-100 px-2 py-0.5 text-xs text-primary-700">
              {filterCount}
            </span>
          )}
        </Link>
        <button
          onClick={onAddJob}
          className="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-white shadow-sm hover:bg-primary-700"
        >
          <Plus className="mr-2 h-4 w-4" />
          Add Job
        </button>
      </div>
    </div>
  )
}

function JobsTabNavigation({
  activeTab,
  onTabChange,
}: {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
}) {
  return (
    <div className="mb-6 border-b border-gray-200">
      <nav className="-mb-px flex gap-4" aria-label="Tabs">
        {JOB_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            )}
            aria-current={activeTab === tab.id ? 'page' : undefined}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  )
}

function JobsTabContent({
  activeTab,
  jobs,
  stats,
  events,
  companyFilters,
  onAddJob,
  onEditJob,
  onDeleteJob,
  onStatusChange,
  onReorder,
  onBulkDelete,
  onBulkStatusChange,
  onAddEvent,
  onUpdateEvent,
  onDeleteEvent,
}: {
  activeTab: TabType
  jobs: JobApplication[]
  stats: JobStats | null
  events: InterviewEvent[]
  companyFilters: CompanyFilter[]
  onAddJob: (status: JobStatus) => void
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  onReorder: (newJobs: JobApplication[]) => void
  onBulkDelete: (ids: number[]) => void
  onBulkStatusChange: (ids: number[], status: JobStatus) => void
  onAddEvent: (event: Omit<InterviewEvent, 'id' | 'created_at'>) => void
  onUpdateEvent: (id: string, updates: Partial<InterviewEvent>) => void
  onDeleteEvent: (id: string) => void
}) {
  if (activeTab === 'kanban') {
    return (
      <KanbanBoard
        jobs={jobs}
        onAddJob={onAddJob}
        onEditJob={onEditJob}
        onDeleteJob={onDeleteJob}
        onStatusChange={onStatusChange}
        onReorder={onReorder}
        companyFilters={companyFilters}
      />
    )
  }

  if (activeTab === 'list') {
    return (
      <ListView
        jobs={jobs}
        onEditJob={onEditJob}
        onDeleteJob={onDeleteJob}
        onStatusChange={onStatusChange}
        onBulkDelete={onBulkDelete}
        onBulkStatusChange={onBulkStatusChange}
      />
    )
  }

  if (activeTab === 'analytics') {
    return <AnalyticsTab jobs={jobs} stats={stats} />
  }

  return (
    <TimelineTab
      jobs={jobs}
      events={events}
      onAddEvent={onAddEvent}
      onUpdateEvent={onUpdateEvent}
      onDeleteEvent={onDeleteEvent}
    />
  )
}

function useJobsPageController() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const [pageState, setPageState] = useState<JobsPageState>(INITIAL_JOBS_PAGE_STATE)
  const {
    jobs,
    stats,
    events,
    companyFilters,
    keywordFilters,
    isLoading,
    activeTab,
    showJobModal,
    editingJob,
    addJobStatus,
  } = pageState

  useEffect(() => {
    let isMounted = true

    async function hydrateJobsPage() {
      if (authLoading) {
        return
      }

      let nextState: Partial<JobsPageState> = { isLoading: false }

      try {
        if (isAuthenticated) {
          const [jobsData, statsData, companyFiltersData, keywordFiltersData] =
            await Promise.all([
              jobsApi.list(),
              jobsApi.getStats().catch(() => null),
              filtersApi.getCompanyFilters(),
              filtersApi.getKeywordFilters(),
            ])

          nextState = {
            jobs: jobsData,
            stats: statsData,
            companyFilters: companyFiltersData,
            keywordFilters: keywordFiltersData,
            events: readInterviewEvents(),
            isLoading: false,
          }
        }
      } catch (error) {
        console.error('Failed to load data:', error)
      }

      if (isMounted) {
        setPageState((prev) => ({ ...prev, ...nextState }))
      }
    }

    void hydrateJobsPage()

    return () => {
      isMounted = false
    }
  }, [authLoading, isAuthenticated])

  const handleAddJob = useCallback(
    async (data: Partial<JobApplication>) => {
      if (!isAuthenticated) {
        return
      }

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

        setPageState((prev) => ({
          ...prev,
          jobs: [newJob, ...prev.jobs],
          showJobModal: false,
          addJobStatus: undefined,
        }))
      } catch (error) {
        console.error('Failed to add job:', error)
      }
    },
    [isAuthenticated]
  )

  const handleUpdateJob = useCallback(
    async (data: Partial<JobApplication>) => {
      if (!isAuthenticated || !editingJob) {
        return
      }

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

        setPageState((prev) => ({
          ...prev,
          jobs: prev.jobs.map((job) =>
            job.id === editingJob.id ? updatedJob : job
          ),
          editingJob: null,
        }))
      } catch (error) {
        console.error('Failed to update job:', error)
      }
    },
    [editingJob, isAuthenticated]
  )

  const handleDeleteJob = useCallback(
    async (id: number) => {
      if (!isAuthenticated || !confirm('Are you sure you want to delete this job application?')) {
        return
      }

      try {
        await jobsApi.delete(id)
        setPageState((prev) => ({
          ...prev,
          jobs: prev.jobs.filter((job) => job.id !== id),
          editingJob: prev.editingJob?.id === id ? null : prev.editingJob,
        }))
      } catch (error) {
        console.error('Failed to delete job:', error)
      }
    },
    [isAuthenticated]
  )

  const handleStatusChange = useCallback(
    async (id: number, status: JobStatus) => {
      if (!isAuthenticated) {
        return
      }

      try {
        await jobsApi.updateStatus(id, status)
        setPageState((prev) => ({
          ...prev,
          jobs: prev.jobs.map((job) =>
            job.id === id ? { ...job, status } : job
          ),
        }))
      } catch (error) {
        console.error('Failed to update job status:', error)
      }
    },
    [isAuthenticated]
  )

  const handleBulkDelete = useCallback(
    async (ids: number[]) => {
      if (!isAuthenticated) {
        return
      }

      try {
        await Promise.all(ids.map((id) => jobsApi.delete(id)))
        setPageState((prev) => ({
          ...prev,
          jobs: prev.jobs.filter((job) => !ids.includes(job.id)),
        }))
      } catch (error) {
        console.error('Failed to delete jobs:', error)
      }
    },
    [isAuthenticated]
  )

  const handleBulkStatusChange = useCallback(
    async (ids: number[], status: JobStatus) => {
      if (!isAuthenticated) {
        return
      }

      try {
        await Promise.all(ids.map((id) => jobsApi.updateStatus(id, status)))
        setPageState((prev) => ({
          ...prev,
          jobs: prev.jobs.map((job) =>
            ids.includes(job.id) ? { ...job, status } : job
          ),
        }))
      } catch (error) {
        console.error('Failed to update job statuses:', error)
      }
    },
    [isAuthenticated]
  )

  const handleAddEvent = useCallback(
    (event: Omit<InterviewEvent, 'id' | 'created_at'>) => {
      setPageState((prev) => {
        const updatedEvents = [
          ...prev.events,
          {
            ...event,
            id: generateId(),
            created_at: new Date().toISOString(),
          },
        ]
        persistInterviewEvents(updatedEvents)
        return { ...prev, events: updatedEvents }
      })
    },
    []
  )

  const handleUpdateEvent = useCallback(
    (id: string, updates: Partial<InterviewEvent>) => {
      setPageState((prev) => {
        const updatedEvents = prev.events.map((event) =>
          event.id === id ? { ...event, ...updates } : event
        )
        persistInterviewEvents(updatedEvents)
        return { ...prev, events: updatedEvents }
      })
    },
    []
  )

  const handleDeleteEvent = useCallback((id: string) => {
    if (!confirm('Are you sure you want to delete this event?')) {
      return
    }

    setPageState((prev) => {
      const updatedEvents = prev.events.filter((event) => event.id !== id)
      persistInterviewEvents(updatedEvents)
      return { ...prev, events: updatedEvents }
    })
  }, [])

  const handleTabChange = useCallback((tab: TabType) => {
    setPageState((prev) => ({ ...prev, activeTab: tab }))
  }, [])

  const handleAddJobButtonClick = useCallback(() => {
    setPageState((prev) => ({
      ...prev,
      addJobStatus: undefined,
      showJobModal: true,
    }))
  }, [])

  const handleKanbanAddJob = useCallback((status: JobStatus) => {
    setPageState((prev) => ({
      ...prev,
      addJobStatus: status,
      showJobModal: true,
    }))
  }, [])

  const handleEditJob = useCallback((job: JobApplication) => {
    setPageState((prev) => ({ ...prev, editingJob: job }))
  }, [])

  const handleReorder = useCallback((newJobs: JobApplication[]) => {
    setPageState((prev) => ({ ...prev, jobs: newJobs }))
  }, [])

  const handleCloseAddModal = useCallback(() => {
    setPageState((prev) => ({
      ...prev,
      showJobModal: false,
      addJobStatus: undefined,
    }))
  }, [])

  const handleCloseEditModal = useCallback(() => {
    setPageState((prev) => ({ ...prev, editingJob: null }))
  }, [])

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

  return {
    user,
    isAuthenticated,
    authLoading,
    jobs,
    stats,
    events,
    companyFilters,
    keywordFilters,
    isLoading,
    activeTab,
    showJobModal,
    editingJob,
    addJobStatus,
    handleAddJobButtonClick,
    handleTabChange,
    handleKanbanAddJob,
    handleEditJob,
    handleDeleteJobSync,
    handleStatusChangeSync,
    handleReorder,
    handleBulkDeleteSync,
    handleBulkStatusChangeSync,
    handleAddEvent,
    handleUpdateEvent,
    handleDeleteEvent,
    handleCloseAddModal,
    handleAddJobSync,
    handleCloseEditModal,
    handleUpdateJobSync,
  }
}

export function JobsPageClient() {
  const controller = useJobsPageController()

  if (controller.authLoading || controller.isLoading) {
    return <PageLoadingState />
  }

  if (!controller.user || !controller.isAuthenticated) {
    return null
  }

  return (
    <div className="mx-auto max-w-full px-4 py-8 sm:px-6 lg:px-8">
      <JobsPageHeader
        filterCount={controller.companyFilters.length + controller.keywordFilters.length}
        onAddJob={controller.handleAddJobButtonClick}
      />

      <JobsTabNavigation
        activeTab={controller.activeTab}
        onTabChange={controller.handleTabChange}
      />

      <JobsTabContent
        activeTab={controller.activeTab}
        jobs={controller.jobs}
        stats={controller.stats}
        events={controller.events}
        companyFilters={controller.companyFilters}
        onAddJob={controller.handleKanbanAddJob}
        onEditJob={controller.handleEditJob}
        onDeleteJob={controller.handleDeleteJobSync}
        onStatusChange={controller.handleStatusChangeSync}
        onReorder={controller.handleReorder}
        onBulkDelete={controller.handleBulkDeleteSync}
        onBulkStatusChange={controller.handleBulkStatusChangeSync}
        onAddEvent={controller.handleAddEvent}
        onUpdateEvent={controller.handleUpdateEvent}
        onDeleteEvent={controller.handleDeleteEvent}
      />

      {controller.showJobModal && (
        <JobFormModal
          initialStatus={controller.addJobStatus}
          onClose={controller.handleCloseAddModal}
          onSave={controller.handleAddJobSync}
        />
      )}

      {controller.editingJob && (
        <JobFormModal
          job={controller.editingJob}
          onClose={controller.handleCloseEditModal}
          onSave={controller.handleUpdateJobSync}
          onDelete={controller.handleDeleteJobSync}
        />
      )}
    </div>
  )
}
