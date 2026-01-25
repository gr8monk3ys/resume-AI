'use client'

import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Plus } from 'lucide-react'
import { memo, useCallback, useMemo, useRef } from 'react'

import { cn, getStatusColor } from '@/lib/utils'

import { SortableJobCard } from './SortableJobCard'

import type { JobApplication, JobStatus, CompanyFilter } from '@/types'

// Card height constant for virtualization (approximate height including margins)
const CARD_HEIGHT = 160
const CARD_GAP = 12

export interface KanbanColumnProps {
  status: JobStatus
  jobs: JobApplication[]
  onAddJob: (status: JobStatus) => void
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  companyFilters?: CompanyFilter[]
}

export const KanbanColumn = memo(function KanbanColumn({
  status,
  jobs,
  onAddJob,
  onEditJob,
  onDeleteJob,
  onStatusChange,
  companyFilters = [],
}: KanbanColumnProps) {
  const statusColors = useMemo(() => getStatusColor(status), [status])

  // Ref for the scrollable container
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Memoize the add job handler to prevent recreation on each render
  const handleAddJob = useCallback(() => {
    onAddJob(status)
  }, [onAddJob, status])

  // Memoize job IDs for SortableContext to prevent unnecessary recalculations
  const jobIds = useMemo(() => jobs.map((j) => j.id), [jobs])

  // Set up virtualizer for the column items
  // Only virtualize if there are more than 10 items to avoid overhead for small lists
  const shouldVirtualize = jobs.length > 10

  const virtualizer = useVirtualizer({
    count: jobs.length,
    getScrollElement: () => scrollContainerRef.current,
    estimateSize: () => CARD_HEIGHT + CARD_GAP,
    overscan: shouldVirtualize ? 3 : jobs.length,
    getItemKey: (index) => jobs[index]?.id ?? index,
  })

  const virtualItems = virtualizer.getVirtualItems()
  const totalSize = virtualizer.getTotalSize()

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
              onClick={handleAddJob}
              className={cn('p-1 rounded hover:bg-white/50', statusColors.text)}
              aria-label={`Add job to ${status}`}
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-3"
      >
        {/* SortableContext needs all IDs to support drag-and-drop properly */}
        <SortableContext
          items={jobIds}
          strategy={verticalListSortingStrategy}
        >
          {shouldVirtualize ? (
            // Virtualized rendering for large lists
            <div
              style={{
                height: totalSize,
                position: 'relative',
                width: '100%',
              }}
            >
              {virtualItems.map((virtualItem) => {
                const job = jobs[virtualItem.index]
                if (!job) return null
                return (
                  <div
                    key={job.id}
                    data-index={virtualItem.index}
                    style={{
                      position: 'absolute',
                      top: virtualItem.start,
                      left: 0,
                      width: '100%',
                      paddingBottom: CARD_GAP,
                    }}
                  >
                    <SortableJobCard
                      job={job}
                      onEdit={onEditJob}
                      onDelete={onDeleteJob}
                      onStatusChange={onStatusChange}
                      companyFilters={companyFilters}
                    />
                  </div>
                )
              })}
            </div>
          ) : (
            // Standard rendering for small lists (better drag-and-drop UX)
            <div className="space-y-3">
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
            </div>
          )}
        </SortableContext>

        {jobs.length === 0 && (
          <div className="text-center py-8 text-gray-400 text-sm">
            No jobs in this stage
          </div>
        )}
      </div>
    </div>
  )
})
