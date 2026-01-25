'use client'

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
import { arrayMove, sortableKeyboardCoordinates } from '@dnd-kit/sortable'
import { useState, useCallback, useMemo, memo } from 'react'

import { JOB_STATUSES } from '@/lib/jobs'

import { KanbanColumn } from './KanbanColumn'

import type { JobApplication, JobStatus, CompanyFilter } from '@/types'

export interface KanbanBoardProps {
  jobs: JobApplication[]
  onAddJob: (status: JobStatus) => void
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  onReorder: (jobs: JobApplication[]) => void
  companyFilters?: CompanyFilter[]
}

export const KanbanBoard = memo(function KanbanBoard({
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
})
