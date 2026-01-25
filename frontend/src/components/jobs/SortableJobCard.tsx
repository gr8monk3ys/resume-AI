'use client'

import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  ExternalLink,
  Trash2,
  Calendar,
  MapPin,
  GripVertical,
  Ban,
  Star,
} from 'lucide-react'
import { memo, useMemo } from 'react'

import { JOB_STATUSES, calculateMatchScore } from '@/lib/jobs'
import { cn, getStatusColor, formatDate } from '@/lib/utils'

import type { JobApplication, JobStatus, CompanyFilter } from '@/types'

export interface SortableJobCardProps {
  job: JobApplication
  onEdit: (job: JobApplication) => void
  onDelete: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  companyFilters?: CompanyFilter[]
}

export const SortableJobCard = memo(function SortableJobCard({
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

  // Memoize expensive match score calculation
  const matchScore = useMemo(() => calculateMatchScore(job), [job])
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
            <button
              type="button"
              className="flex-1 min-w-0 text-left"
              onClick={() => onEdit(job)}
              aria-label={`Edit job application for ${job.position} at ${job.company}`}
            >
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
            </button>
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
})
