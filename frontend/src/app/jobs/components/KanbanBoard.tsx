'use client'

/**
 * Kanban board component for visualizing job applications by status.
 * Includes drag-and-drop functionality for reordering and status changes.
 * @module jobs/components/KanbanBoard
 */

import { useState, useCallback, useMemo } from 'react'
import type { JobApplication, JobStatus, CompanyFilter } from '@/types'
import { cn, getStatusColor, formatDate } from '@/lib/utils'
import {
  Plus,
  ExternalLink,
  Trash2,
  Calendar,
  MapPin,
  GripVertical,
  Ban,
  Star,
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
import { JOB_STATUSES, calculateMatchScore } from './types'

// ============================================================================
// Props Interfaces
// ============================================================================

interface SortableJobCardProps {
  job: JobApplication
  onEdit: (job: JobApplication) => void
  onDelete: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  companyFilters?: CompanyFilter[]
}

interface KanbanColumnProps {
  status: JobStatus
  jobs: JobApplication[]
  onAddJob: (status: JobStatus) => void
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  companyFilters?: CompanyFilter[]
}

export interface KanbanBoardProps {
  jobs: JobApplication[]
  onAddJob: (status: JobStatus) => void
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  onReorder: (jobs: JobApplication[]) => void
  companyFilters?: CompanyFilter[]
}

// ============================================================================
// SortableJobCard Component
// ============================================================================

/**
 * Draggable job card for use within Kanban columns.
 * Displays job details with match score and quick actions.
 */
function SortableJobCard({
  job,
  onEdit,
  onDelete,
  onStatusChange,
  companyFilters = [],
}: SortableJobCardProps) {
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

  // Find matching company filter
  const matchedCompanyFilter = useMemo(() => {
    const companyLower = job.company.toLowerCase()
    return companyFilters.find(
      (f) =>
        companyLower.includes(f.company_name.toLowerCase()) ||
        f.company_name.toLowerCase().includes(companyLower)
    )
  }, [job.company, companyFilters])

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
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-gray-900 truncate">{job.position}</h4>
                {matchedCompanyFilter && (
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 text-xs font-medium px-1.5 py-0.5 rounded',
                      matchedCompanyFilter.filter_type === 'blacklist'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-green-100 text-green-700'
                    )}
                    title={matchedCompanyFilter.reason || undefined}
                  >
                    {matchedCompanyFilter.filter_type === 'blacklist' ? (
                      <Ban className="w-3 h-3" />
                    ) : (
                      <Star className="w-3 h-3" />
                    )}
                  </span>
                )}
              </div>
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
// KanbanColumn Component
// ============================================================================

/**
 * Column component representing a single job status in the Kanban board.
 * Contains sortable job cards and an add button.
 */
function KanbanColumn({
  status,
  jobs,
  onAddJob,
  onEditJob,
  onDeleteJob,
  onStatusChange,
  companyFilters = [],
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
              companyFilters={companyFilters}
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
// KanbanBoard Component
// ============================================================================

/**
 * Main Kanban board component with drag-and-drop support.
 * Organizes jobs into columns by status and handles reordering.
 */
export function KanbanBoard({
  jobs,
  onAddJob,
  onEditJob,
  onDeleteJob,
  onStatusChange,
  onReorder,
  companyFilters = [],
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
            companyFilters={companyFilters}
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
