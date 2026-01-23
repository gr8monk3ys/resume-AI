'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { jobsApi } from '@/lib/api'
import type {
  JobApplication,
  JobStatus,
  JobStats,
  InterviewEvent,
  InterviewEventType,
  FollowUpUrgency,
  WeeklyApplicationData,
  JobGoals,
} from '@/types'
import { cn, getStatusColor, formatDate, truncate, generateId } from '@/lib/utils'
import {
  Plus,
  ExternalLink,
  Trash2,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  Calendar,
  Clock,
  MapPin,
  Link as LinkIcon,
  Users,
  CheckCircle,
  AlertCircle,
  Bell,
  BarChart3,
  List,
  Kanban,
  X,
  GripVertical,
  Edit2,
  ArrowUpDown,
  Target,
  TrendingUp,
  PieChart,
} from 'lucide-react'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  DragOverEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

// ============================================================================
// Constants
// ============================================================================

const JOB_STATUSES: JobStatus[] = [
  'Bookmarked',
  'Applied',
  'Phone Screen',
  'Interview',
  'Offer',
  'Rejected',
]

const EVENT_TYPES: { value: InterviewEventType; label: string }[] = [
  { value: 'phone_screen', label: 'Phone Screen' },
  { value: 'technical', label: 'Technical Interview' },
  { value: 'behavioral', label: 'Behavioral Interview' },
  { value: 'onsite', label: 'Onsite Interview' },
  { value: 'panel', label: 'Panel Interview' },
  { value: 'hr', label: 'HR Interview' },
  { value: 'final', label: 'Final Round' },
  { value: 'follow_up', label: 'Follow Up' },
  { value: 'other', label: 'Other' },
]

type TabType = 'kanban' | 'list' | 'analytics' | 'timeline'

// ============================================================================
// Utility Functions
// ============================================================================

function getEventTypeColor(type: InterviewEventType): string {
  const colors: Record<InterviewEventType, string> = {
    phone_screen: 'bg-purple-100 text-purple-800',
    technical: 'bg-blue-100 text-blue-800',
    behavioral: 'bg-amber-100 text-amber-800',
    onsite: 'bg-green-100 text-green-800',
    panel: 'bg-indigo-100 text-indigo-800',
    hr: 'bg-pink-100 text-pink-800',
    final: 'bg-emerald-100 text-emerald-800',
    follow_up: 'bg-orange-100 text-orange-800',
    other: 'bg-gray-100 text-gray-800',
  }
  return colors[type]
}

function getUrgencyColor(urgency: FollowUpUrgency): string {
  const colors: Record<FollowUpUrgency, string> = {
    low: 'bg-green-100 text-green-800 border-green-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    high: 'bg-orange-100 text-orange-800 border-orange-200',
    overdue: 'bg-red-100 text-red-800 border-red-200',
  }
  return colors[urgency]
}

function calculateUrgency(followUpDate: string): FollowUpUrgency {
  const now = new Date()
  const date = new Date(followUpDate)
  const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays < 0) return 'overdue'
  if (diffDays === 0) return 'high'
  if (diffDays <= 2) return 'medium'
  return 'low'
}

function calculateMatchScore(job: JobApplication): number {
  // Simple mock match score calculation based on completeness
  let score = 50
  if (job.job_description) score += 20
  if (job.location) score += 10
  if (job.job_url) score += 10
  if (job.notes) score += 10
  return Math.min(score, 100)
}

// ============================================================================
// Sortable Job Card Component
// ============================================================================

interface SortableJobCardProps {
  job: JobApplication
  onEdit: (job: JobApplication) => void
  onDelete: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
}

function SortableJobCard({ job, onEdit, onDelete, onStatusChange }: SortableJobCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: job.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const matchScore = calculateMatchScore(job)
  const statusColors = getStatusColor(job.status)

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow border-l-4',
        statusColors.border,
        isDragging && 'opacity-50 shadow-lg'
      )}
    >
      <div className="flex items-start gap-2">
        <button
          {...attributes}
          {...listeners}
          className="mt-1 text-gray-400 hover:text-gray-600 cursor-grab active:cursor-grabbing"
          aria-label="Drag to reorder"
        >
          <GripVertical className="w-4 h-4" />
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <div className="flex-1 min-w-0" onClick={() => onEdit(job)}>
              <h4 className="font-medium text-gray-900 truncate">{job.position}</h4>
              <p className="text-sm text-gray-500 truncate">{job.company}</p>
            </div>
            <div className="flex items-center gap-2 ml-2">
              <span
                className={cn(
                  'text-xs font-medium px-2 py-1 rounded-full',
                  matchScore >= 80
                    ? 'bg-green-100 text-green-800'
                    : matchScore >= 60
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-100 text-gray-800'
                )}
              >
                {matchScore}%
              </span>
              {job.job_url && (
                <a
                  href={job.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-400 hover:text-primary-600"
                  onClick={(e) => e.stopPropagation()}
                  aria-label="Open job link"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
          </div>

          {job.location && (
            <p className="text-xs text-gray-400 mt-2 flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              {job.location}
            </p>
          )}

          {job.application_date && (
            <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {formatDate(job.application_date)}
            </p>
          )}

          <div className="mt-3 flex items-center justify-between">
            <select
              value={job.status}
              onChange={(e) => onStatusChange(job.id, e.target.value as JobStatus)}
              className="text-xs border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500"
              onClick={(e) => e.stopPropagation()}
              aria-label="Change job status"
            >
              {JOB_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete(job.id)
              }}
              className="text-gray-400 hover:text-red-600 p-1"
              aria-label="Delete job"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Kanban Column Component
// ============================================================================

interface KanbanColumnProps {
  status: JobStatus
  jobs: JobApplication[]
  onAddJob: (status: JobStatus) => void
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
}

function KanbanColumn({
  status,
  jobs,
  onAddJob,
  onEditJob,
  onDeleteJob,
  onStatusChange,
}: KanbanColumnProps) {
  const statusColors = getStatusColor(status)

  return (
    <div className="flex-shrink-0 w-80 bg-gray-50 rounded-lg flex flex-col max-h-[calc(100vh-280px)]">
      <div className={cn('p-4 rounded-t-lg', statusColors.bg)}>
        <div className="flex items-center justify-between">
          <h3 className={cn('font-semibold', statusColors.text)}>{status}</h3>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'text-sm font-medium px-2 py-0.5 rounded-full',
                statusColors.badge
              )}
            >
              {jobs.length}
            </span>
            <button
              onClick={() => onAddJob(status)}
              className={cn('p-1 rounded hover:bg-white/50', statusColors.text)}
              aria-label={`Add job to ${status}`}
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <SortableContext
          items={jobs.map((j) => j.id)}
          strategy={verticalListSortingStrategy}
        >
          {jobs.map((job) => (
            <SortableJobCard
              key={job.id}
              job={job}
              onEdit={onEditJob}
              onDelete={onDeleteJob}
              onStatusChange={onStatusChange}
            />
          ))}
        </SortableContext>

        {jobs.length === 0 && (
          <div className="text-center py-8 text-gray-400 text-sm">
            No jobs in this stage
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Kanban Board Tab
// ============================================================================

interface KanbanBoardProps {
  jobs: JobApplication[]
  onAddJob: (status: JobStatus) => void
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  onReorder: (jobs: JobApplication[]) => void
}

function KanbanBoard({
  jobs,
  onAddJob,
  onEditJob,
  onDeleteJob,
  onStatusChange,
  onReorder,
}: KanbanBoardProps) {
  const [activeJob, setActiveJob] = useState<JobApplication | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const jobsByStatus = useMemo(() => {
    return JOB_STATUSES.reduce((acc, status) => {
      acc[status] = jobs.filter((job) => job.status === status)
      return acc
    }, {} as Record<JobStatus, JobApplication[]>)
  }, [jobs])

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const job = jobs.find((j) => j.id === event.active.id)
      if (job) {
        setActiveJob(job)
      }
    },
    [jobs]
  )

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const { active, over } = event
      if (!over) return

      const activeJob = jobs.find((j) => j.id === active.id)
      const overJob = jobs.find((j) => j.id === over.id)

      if (!activeJob) return

      // If dropping over another job card
      if (overJob && activeJob.status !== overJob.status) {
        onStatusChange(activeJob.id, overJob.status)
      }
    },
    [jobs, onStatusChange]
  )

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      setActiveJob(null)

      if (!over) return

      if (active.id !== over.id) {
        const oldIndex = jobs.findIndex((j) => j.id === active.id)
        const newIndex = jobs.findIndex((j) => j.id === over.id)

        if (oldIndex !== -1 && newIndex !== -1) {
          const newJobs = arrayMove(jobs, oldIndex, newIndex)
          onReorder(newJobs)
        }
      }
    },
    [jobs, onReorder]
  )

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4 min-h-[500px]">
        {JOB_STATUSES.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            jobs={jobsByStatus[status]}
            onAddJob={onAddJob}
            onEditJob={onEditJob}
            onDeleteJob={onDeleteJob}
            onStatusChange={onStatusChange}
          />
        ))}
      </div>

      <DragOverlay>
        {activeJob ? (
          <div className="bg-white rounded-lg shadow-lg p-4 border-l-4 border-primary-500 w-72 rotate-3">
            <h4 className="font-medium text-gray-900 truncate">{activeJob.position}</h4>
            <p className="text-sm text-gray-500 truncate">{activeJob.company}</p>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}

// ============================================================================
// List View Tab
// ============================================================================

type SortField = 'company' | 'position' | 'status' | 'application_date' | 'created_at'
type SortDirection = 'asc' | 'desc'

interface ListViewProps {
  jobs: JobApplication[]
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  onBulkDelete: (ids: number[]) => void
  onBulkStatusChange: (ids: number[], status: JobStatus) => void
}

function ListView({
  jobs,
  onEditJob,
  onDeleteJob,
  onStatusChange,
  onBulkDelete,
  onBulkStatusChange,
}: ListViewProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<JobStatus | ''>('')
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  const filteredJobs = useMemo(() => {
    let result = [...jobs]

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (job) =>
          job.company.toLowerCase().includes(query) ||
          job.position.toLowerCase().includes(query)
      )
    }

    // Apply status filter
    if (statusFilter) {
      result = result.filter((job) => job.status === statusFilter)
    }

    // Apply sorting
    result.sort((a, b) => {
      let aValue: string | number | null = a[sortField]
      let bValue: string | number | null = b[sortField]

      // Handle null values
      if (aValue === null) aValue = ''
      if (bValue === null) bValue = ''

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue)
      }

      return 0
    })

    return result
  }, [jobs, searchQuery, statusFilter, sortField, sortDirection])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const handleSelectAll = () => {
    if (selectedIds.size === filteredJobs.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredJobs.map((j) => j.id)))
    }
  }

  const handleSelect = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const handleBulkDelete = () => {
    if (
      confirm(`Are you sure you want to delete ${selectedIds.size} job applications?`)
    ) {
      onBulkDelete(Array.from(selectedIds))
      setSelectedIds(new Set())
    }
  }

  const handleBulkStatusChange = (status: JobStatus) => {
    onBulkStatusChange(Array.from(selectedIds), status)
    setSelectedIds(new Set())
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-4 h-4 text-gray-400" />
    }
    return sortDirection === 'asc' ? (
      <ChevronUp className="w-4 h-4" />
    ) : (
      <ChevronDown className="w-4 h-4" />
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by company or position..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as JobStatus | '')}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Filter by status"
          >
            <option value="">All Statuses</option>
            {JOB_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-4 p-3 bg-primary-50 rounded-lg">
          <span className="text-sm font-medium text-primary-700">
            {selectedIds.size} selected
          </span>
          <select
            onChange={(e) => {
              if (e.target.value) {
                handleBulkStatusChange(e.target.value as JobStatus)
                e.target.value = ''
              }
            }}
            className="text-sm border border-primary-200 rounded px-2 py-1 bg-white"
            aria-label="Bulk change status"
          >
            <option value="">Change Status...</option>
            {JOB_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <button
            onClick={handleBulkDelete}
            className="text-sm text-red-600 hover:text-red-700 font-medium"
          >
            Delete Selected
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-sm text-gray-600 hover:text-gray-700"
          >
            Clear Selection
          </button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-12 px-4 py-3">
                <input
                  type="checkbox"
                  checked={selectedIds.size === filteredJobs.length && filteredJobs.length > 0}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300"
                  aria-label="Select all"
                />
              </th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('company')}
              >
                <div className="flex items-center gap-2">
                  Company
                  <SortIcon field="company" />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('position')}
              >
                <div className="flex items-center gap-2">
                  Position
                  <SortIcon field="position" />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('status')}
              >
                <div className="flex items-center gap-2">
                  Status
                  <SortIcon field="status" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Match
              </th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('application_date')}
              >
                <div className="flex items-center gap-2">
                  Applied
                  <SortIcon field="application_date" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                Location
              </th>
              <th className="w-24 px-4 py-3 text-right text-sm font-medium text-gray-700">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredJobs.map((job) => {
              const statusColors = getStatusColor(job.status)
              const matchScore = calculateMatchScore(job)

              return (
                <tr
                  key={job.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => onEditJob(job)}
                >
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(job.id)}
                      onChange={() => handleSelect(job.id)}
                      className="rounded border-gray-300"
                      aria-label={`Select ${job.company}`}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{job.company}</span>
                      {job.job_url && (
                        <a
                          href={job.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-gray-400 hover:text-primary-600"
                          aria-label="Open job link"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{job.position}</td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <select
                      value={job.status}
                      onChange={(e) => onStatusChange(job.id, e.target.value as JobStatus)}
                      className={cn(
                        'text-xs font-medium px-2 py-1 rounded-full border-0 cursor-pointer',
                        statusColors.badge
                      )}
                      aria-label="Change status"
                    >
                      {JOB_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'text-xs font-medium px-2 py-1 rounded-full',
                        matchScore >= 80
                          ? 'bg-green-100 text-green-800'
                          : matchScore >= 60
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      )}
                    >
                      {matchScore}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {job.application_date ? formatDate(job.application_date) : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {job.location || '-'}
                  </td>
                  <td
                    className="px-4 py-3 text-right"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onEditJob(job)}
                        className="p-1 text-gray-400 hover:text-primary-600"
                        aria-label="Edit job"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onDeleteJob(job.id)}
                        className="p-1 text-gray-400 hover:text-red-600"
                        aria-label="Delete job"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {filteredJobs.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No jobs found matching your criteria
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Analytics Tab
// ============================================================================

interface AnalyticsTabProps {
  jobs: JobApplication[]
  stats: JobStats | null
}

function AnalyticsTab({ jobs, stats }: AnalyticsTabProps) {
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
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-lg">
              <BarChart3 className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Applications</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.total || jobs.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Response Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats ? `${Math.round(stats.response_rate)}%` : '0%'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-green-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Offer Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats ? `${Math.round(stats.offer_rate)}%` : '0%'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-amber-100 rounded-lg">
              <Target className="w-6 h-6 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Active Applications</p>
              <p className="text-2xl font-bold text-gray-900">
                {jobs.filter((j) => !['Rejected', 'Offer'].includes(j.status)).length}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Application Funnel */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            Application Funnel
          </h3>
          <div className="space-y-4">
            {funnelData.map((item, index) => (
              <div key={item.stage}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-gray-700">{item.stage}</span>
                  <span className="text-gray-500">
                    {item.count} ({item.percentage}%)
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-6 overflow-hidden">
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
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-primary-600" />
            Status Breakdown
          </h3>
          <div className="space-y-3">
            {JOB_STATUSES.map((status) => {
              const count = statusBreakdown[status]
              const percentage = jobs.length
                ? Math.round((count / jobs.length) * 100)
                : 0
              const colors = getStatusColor(status)

              return (
                <div key={status} className="flex items-center gap-3">
                  <div className={cn('w-3 h-3 rounded-full', colors.bg, colors.border, 'border')} />
                  <div className="flex-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-700">{status}</span>
                      <span className="text-gray-500">
                        {count} ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 mt-1">
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
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary-600" />
            Applications Per Week
          </h3>
          <div className="flex items-end gap-2 h-40">
            {weeklyData.map((item, index) => (
              <div
                key={index}
                className="flex-1 flex flex-col items-center justify-end"
              >
                <div
                  className="w-full bg-primary-500 rounded-t transition-all duration-300 hover:bg-primary-600"
                  style={{
                    height: `${(item.count / maxWeeklyCount) * 100}%`,
                    minHeight: item.count > 0 ? '8px' : '2px',
                  }}
                />
                <span className="text-xs text-gray-500 mt-2 transform -rotate-45 origin-top-left">
                  {item.week}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Goals Progress */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-primary-600" />
            Goals Progress
          </h3>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-gray-700">Weekly Goal</span>
                <span className="text-gray-500">
                  {goals.weekly_current} / {goals.weekly_target}
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-4">
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
                <span className="font-medium text-gray-700">Monthly Goal</span>
                <span className="text-gray-500">
                  {goals.monthly_current} / {goals.monthly_target}
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-4">
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
}

// ============================================================================
// Timeline Tab
// ============================================================================

interface TimelineTabProps {
  jobs: JobApplication[]
  events: InterviewEvent[]
  onAddEvent: (event: Omit<InterviewEvent, 'id' | 'created_at'>) => void
  onUpdateEvent: (id: string, updates: Partial<InterviewEvent>) => void
  onDeleteEvent: (id: string) => void
}

function TimelineTab({
  jobs,
  events,
  onAddEvent,
  onUpdateEvent,
  onDeleteEvent,
}: TimelineTabProps) {
  const [showAddForm, setShowAddForm] = useState(false)
  const [filterType, setFilterType] = useState<InterviewEventType | ''>('')

  // Group events by date
  const groupedEvents = useMemo(() => {
    const filtered = filterType
      ? events.filter((e) => e.event_type === filterType)
      : events

    const groups: Record<string, InterviewEvent[]> = {}

    filtered.forEach((event) => {
      const dateKey = new Date(event.scheduled_date).toISOString().slice(0, 10)
      if (!groups[dateKey]) {
        groups[dateKey] = []
      }
      groups[dateKey].push(event)
    })

    // Sort events within each group by time
    Object.keys(groups).forEach((key) => {
      groups[key].sort((a, b) => {
        const timeA = a.scheduled_time || '00:00'
        const timeB = b.scheduled_time || '00:00'
        return timeA.localeCompare(timeB)
      })
    })

    // Sort dates
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  }, [events, filterType])

  // Get pending follow-ups
  const pendingFollowUps = useMemo(() => {
    return events
      .filter((e) => e.follow_up_date && !e.follow_up_done)
      .sort((a, b) => a.follow_up_date!.localeCompare(b.follow_up_date!))
  }, [events])

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex items-center gap-4">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as InterviewEventType | '')}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Filter by event type"
          >
            <option value="">All Event Types</option>
            {EVENT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Event
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="lg:col-span-2 space-y-6">
          {groupedEvents.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              <Calendar className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No events scheduled</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="mt-4 text-primary-600 hover:text-primary-700 font-medium"
              >
                Add your first event
              </button>
            </div>
          ) : (
            groupedEvents.map(([date, dateEvents]) => {
              const dateObj = new Date(date)
              const isToday =
                dateObj.toDateString() === new Date().toDateString()
              const isPast = dateObj < new Date() && !isToday

              return (
                <div key={date}>
                  <div
                    className={cn(
                      'sticky top-0 z-10 py-2 px-4 rounded-lg mb-3',
                      isToday
                        ? 'bg-primary-100 text-primary-800'
                        : isPast
                        ? 'bg-gray-100 text-gray-600'
                        : 'bg-blue-50 text-blue-800'
                    )}
                  >
                    <span className="font-semibold">
                      {isToday ? 'Today - ' : ''}
                      {formatDate(date, 'long')}
                    </span>
                  </div>

                  <div className="space-y-3 ml-4 border-l-2 border-gray-200 pl-4">
                    {dateEvents.map((event) => (
                      <div
                        key={event.id}
                        className={cn(
                          'bg-white rounded-lg shadow p-4 relative',
                          event.is_completed && 'opacity-60'
                        )}
                      >
                        <div className="absolute -left-6 top-4 w-3 h-3 rounded-full bg-white border-2 border-primary-500" />

                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span
                                className={cn(
                                  'text-xs font-medium px-2 py-1 rounded-full',
                                  getEventTypeColor(event.event_type)
                                )}
                              >
                                {EVENT_TYPES.find((t) => t.value === event.event_type)?.label}
                              </span>
                              {event.is_completed && (
                                <span className="text-xs text-green-600 flex items-center gap-1">
                                  <CheckCircle className="w-3 h-3" />
                                  Completed
                                </span>
                              )}
                            </div>

                            <h4 className="font-medium text-gray-900 mt-2">
                              {event.position}
                            </h4>
                            <p className="text-sm text-gray-500">{event.company}</p>

                            <div className="mt-3 space-y-1 text-sm text-gray-600">
                              {event.scheduled_time && (
                                <div className="flex items-center gap-2">
                                  <Clock className="w-4 h-4 text-gray-400" />
                                  {event.scheduled_time}
                                  {event.duration_minutes && ` (${event.duration_minutes} min)`}
                                </div>
                              )}
                              {event.location && (
                                <div className="flex items-center gap-2">
                                  <MapPin className="w-4 h-4 text-gray-400" />
                                  {event.location}
                                </div>
                              )}
                              {event.meeting_link && (
                                <div className="flex items-center gap-2">
                                  <LinkIcon className="w-4 h-4 text-gray-400" />
                                  <a
                                    href={event.meeting_link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary-600 hover:underline"
                                  >
                                    Join Meeting
                                  </a>
                                </div>
                              )}
                              {event.interviewer_names && event.interviewer_names.length > 0 && (
                                <div className="flex items-center gap-2">
                                  <Users className="w-4 h-4 text-gray-400" />
                                  {event.interviewer_names.join(', ')}
                                </div>
                              )}
                            </div>

                            {event.notes && (
                              <p className="mt-2 text-sm text-gray-500 italic">
                                {truncate(event.notes, 150)}
                              </p>
                            )}
                          </div>

                          <div className="flex items-center gap-2 ml-4">
                            {!event.is_completed && (
                              <button
                                onClick={() =>
                                  onUpdateEvent(event.id, { is_completed: true })
                                }
                                className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded"
                                aria-label="Mark as completed"
                                title="Mark as completed"
                              >
                                <CheckCircle className="w-5 h-5" />
                              </button>
                            )}
                            <button
                              onClick={() => onDeleteEvent(event.id)}
                              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                              aria-label="Delete event"
                            >
                              <Trash2 className="w-5 h-5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Follow-up Reminders Sidebar */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Bell className="w-5 h-5 text-amber-500" />
              Follow-up Reminders
            </h3>

            {pendingFollowUps.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">
                No pending follow-ups
              </p>
            ) : (
              <div className="space-y-3">
                {pendingFollowUps.map((event) => {
                  const urgency = calculateUrgency(event.follow_up_date!)

                  return (
                    <div
                      key={event.id}
                      className={cn(
                        'p-3 rounded-lg border',
                        getUrgencyColor(urgency)
                      )}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-sm">{event.company}</p>
                          <p className="text-xs opacity-75">{event.position}</p>
                          <p className="text-xs mt-1 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(event.follow_up_date)}
                          </p>
                        </div>
                        <button
                          onClick={() =>
                            onUpdateEvent(event.id, { follow_up_done: true })
                          }
                          className="p-1 hover:bg-white/50 rounded"
                          aria-label="Mark follow-up done"
                          title="Mark done"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-4">Quick Stats</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Total Events</span>
                <span className="font-medium">{events.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Upcoming</span>
                <span className="font-medium">
                  {events.filter((e) => !e.is_completed && new Date(e.scheduled_date) >= new Date()).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Completed</span>
                <span className="font-medium">
                  {events.filter((e) => e.is_completed).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Pending Follow-ups</span>
                <span className="font-medium">{pendingFollowUps.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add Event Modal */}
      {showAddForm && (
        <AddEventModal
          jobs={jobs}
          onClose={() => setShowAddForm(false)}
          onAdd={(event) => {
            onAddEvent(event)
            setShowAddForm(false)
          }}
        />
      )}
    </div>
  )
}

// ============================================================================
// Add Event Modal
// ============================================================================

interface AddEventModalProps {
  jobs: JobApplication[]
  onClose: () => void
  onAdd: (event: Omit<InterviewEvent, 'id' | 'created_at'>) => void
}

function AddEventModal({ jobs, onClose, onAdd }: AddEventModalProps) {
  const [formData, setFormData] = useState({
    job_id: 0,
    event_type: 'phone_screen' as InterviewEventType,
    scheduled_date: '',
    scheduled_time: '',
    duration_minutes: 60,
    location: '',
    meeting_link: '',
    interviewer_names: '',
    notes: '',
    follow_up_date: '',
  })

  const selectedJob = jobs.find((j) => j.id === formData.job_id)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const event: Omit<InterviewEvent, 'id' | 'created_at'> = {
      job_id: formData.job_id,
      company: selectedJob?.company || '',
      position: selectedJob?.position || '',
      event_type: formData.event_type,
      scheduled_date: formData.scheduled_date,
      scheduled_time: formData.scheduled_time || undefined,
      duration_minutes: formData.duration_minutes || undefined,
      location: formData.location || undefined,
      meeting_link: formData.meeting_link || undefined,
      interviewer_names: formData.interviewer_names
        ? formData.interviewer_names.split(',').map((n) => n.trim())
        : undefined,
      notes: formData.notes || undefined,
      is_completed: false,
      follow_up_date: formData.follow_up_date || undefined,
      follow_up_done: false,
    }

    onAdd(event)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Add Interview Event</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Job Application
            </label>
            <select
              required
              value={formData.job_id}
              onChange={(e) =>
                setFormData({ ...formData, job_id: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value={0}>Select a job...</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.company} - {job.position}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Event Type
            </label>
            <select
              value={formData.event_type}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  event_type: e.target.value as InterviewEventType,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {EVENT_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date
              </label>
              <input
                type="date"
                required
                value={formData.scheduled_date}
                onChange={(e) =>
                  setFormData({ ...formData, scheduled_date: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Time
              </label>
              <input
                type="time"
                value={formData.scheduled_time}
                onChange={(e) =>
                  setFormData({ ...formData, scheduled_time: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Duration (minutes)
            </label>
            <input
              type="number"
              min={15}
              step={15}
              value={formData.duration_minutes}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  duration_minutes: parseInt(e.target.value),
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Location
            </label>
            <input
              type="text"
              placeholder="Office address or 'Remote'"
              value={formData.location}
              onChange={(e) =>
                setFormData({ ...formData, location: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Meeting Link
            </label>
            <input
              type="url"
              placeholder="https://zoom.us/..."
              value={formData.meeting_link}
              onChange={(e) =>
                setFormData({ ...formData, meeting_link: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Interviewer Names
            </label>
            <input
              type="text"
              placeholder="John Doe, Jane Smith (comma separated)"
              value={formData.interviewer_names}
              onChange={(e) =>
                setFormData({ ...formData, interviewer_names: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Follow-up Date
            </label>
            <input
              type="date"
              value={formData.follow_up_date}
              onChange={(e) =>
                setFormData({ ...formData, follow_up_date: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              rows={3}
              placeholder="Preparation notes, questions to ask, etc."
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!formData.job_id || !formData.scheduled_date}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add Event
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ============================================================================
// Add/Edit Job Modal
// ============================================================================

interface JobModalProps {
  job?: JobApplication | null
  initialStatus?: JobStatus
  onClose: () => void
  onSave: (data: Partial<JobApplication>) => void
  onDelete?: (id: number) => void
}

function JobModal({ job, initialStatus, onClose, onSave, onDelete }: JobModalProps) {
  const [formData, setFormData] = useState({
    company: job?.company || '',
    position: job?.position || '',
    job_description: job?.job_description || '',
    status: job?.status || initialStatus || ('Bookmarked' as JobStatus),
    application_date: job?.application_date || '',
    deadline: job?.deadline || '',
    location: job?.location || '',
    job_url: job?.job_url || '',
    notes: job?.notes || '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await onSave(formData)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">
            {job ? 'Edit Job Application' : 'Add Job Application'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Company <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.company}
                onChange={(e) =>
                  setFormData({ ...formData, company: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Position <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.position}
                onChange={(e) =>
                  setFormData({ ...formData, position: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={formData.status}
                onChange={(e) =>
                  setFormData({ ...formData, status: e.target.value as JobStatus })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {JOB_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Location
              </label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) =>
                  setFormData({ ...formData, location: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Remote, New York, etc."
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Application Date
              </label>
              <input
                type="date"
                value={formData.application_date}
                onChange={(e) =>
                  setFormData({ ...formData, application_date: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Deadline
              </label>
              <input
                type="date"
                value={formData.deadline}
                onChange={(e) =>
                  setFormData({ ...formData, deadline: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Job URL
            </label>
            <input
              type="url"
              value={formData.job_url}
              onChange={(e) =>
                setFormData({ ...formData, job_url: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="https://..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Job Description
            </label>
            <textarea
              rows={4}
              value={formData.job_description}
              onChange={(e) =>
                setFormData({ ...formData, job_description: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Paste the job description here for better match scoring..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              rows={3}
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Any additional notes..."
            />
          </div>

          <div className="flex items-center justify-between pt-4 border-t">
            {job && onDelete ? (
              <button
                type="button"
                onClick={() => {
                  if (confirm('Are you sure you want to delete this job application?')) {
                    onDelete(job.id)
                  }
                }}
                className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg"
              >
                Delete
              </button>
            ) : (
              <div />
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : job ? 'Save Changes' : 'Add Job'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function JobsPage() {
  const { user, tokens, isLoading: authLoading } = useAuth()
  const router = useRouter()

  // State
  const [jobs, setJobs] = useState<JobApplication[]>([])
  const [stats, setStats] = useState<JobStats | null>(null)
  const [events, setEvents] = useState<InterviewEvent[]>([])
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

  // Load data
  useEffect(() => {
    if (tokens?.access_token) {
      loadData()
    }
  }, [tokens])

  const loadData = async () => {
    if (!tokens?.access_token) return

    try {
      const [jobsData, statsData] = await Promise.all([
        jobsApi.list(tokens.access_token),
        jobsApi.getStats(tokens.access_token).catch(() => null),
      ])

      setJobs(jobsData as JobApplication[])
      setStats(statsData)

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
  }

  // Job CRUD operations
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

  // Event operations (stored in localStorage for now)
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
          onAddJob={(status) => {
            setAddJobStatus(status)
            setShowJobModal(true)
          }}
          onEditJob={(job) => setEditingJob(job)}
          onDeleteJob={handleDeleteJob}
          onStatusChange={handleStatusChange}
          onReorder={setJobs}
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
