'use client'

/**
 * List view component for displaying job applications in a sortable table.
 * Supports filtering, bulk actions, and sorting by multiple fields.
 * @module jobs/components/ListView
 */

import { useState, useMemo } from 'react'
import type { JobApplication, JobStatus } from '@/types'
import { cn, getStatusColor, formatDate } from '@/lib/utils'
import {
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  Trash2,
  Edit2,
  ExternalLink,
  ArrowUpDown,
} from 'lucide-react'
import { JOB_STATUSES, SortField, SortDirection, calculateMatchScore } from './types'

// ============================================================================
// Props Interface
// ============================================================================

export interface ListViewProps {
  jobs: JobApplication[]
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  onBulkDelete: (ids: number[]) => void
  onBulkStatusChange: (ids: number[], status: JobStatus) => void
}

// ============================================================================
// SortIcon Component
// ============================================================================

interface SortIconProps {
  field: SortField
  currentField: SortField
  direction: SortDirection
}

function SortIcon({ field, currentField, direction }: SortIconProps) {
  if (currentField !== field) {
    return <ArrowUpDown className="w-4 h-4 text-gray-400" />
  }
  return direction === 'asc' ? (
    <ChevronUp className="w-4 h-4" />
  ) : (
    <ChevronDown className="w-4 h-4" />
  )
}

// ============================================================================
// ListView Component
// ============================================================================

/**
 * Table-based list view for job applications with sorting and bulk operations.
 * Provides search, status filtering, and multi-select capabilities.
 */
export function ListView({
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
                  <SortIcon field="company" currentField={sortField} direction={sortDirection} />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('position')}
              >
                <div className="flex items-center gap-2">
                  Position
                  <SortIcon field="position" currentField={sortField} direction={sortDirection} />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('status')}
              >
                <div className="flex items-center gap-2">
                  Status
                  <SortIcon field="status" currentField={sortField} direction={sortDirection} />
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
                  <SortIcon field="application_date" currentField={sortField} direction={sortDirection} />
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
