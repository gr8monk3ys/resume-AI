'use client'

import { useVirtualizer } from '@tanstack/react-virtual'
import {
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Trash2,
  Edit2,
  ArrowUpDown,
} from 'lucide-react'
import { useState, useMemo, useCallback, memo, useRef } from 'react'

import { JOB_STATUSES, calculateMatchScore, type SortField, type SortDirection } from '@/lib/jobs'
import { cn, getStatusColor, formatDate } from '@/lib/utils'

import type { JobApplication, JobStatus } from '@/types'

// Row height constant for virtualization
const ROW_HEIGHT = 56

// Memoized row component for performance optimization
interface ListViewRowProps {
  job: JobApplication
  isSelected: boolean
  onSelect: (id: number) => void
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  style?: React.CSSProperties
}

const ListViewRow = memo(function ListViewRow({
  job,
  isSelected,
  onSelect,
  onEditJob,
  onDeleteJob,
  onStatusChange,
  style,
}: ListViewRowProps) {
  // Memoize expensive calculations
  const statusColors = useMemo(() => getStatusColor(job.status), [job.status])
  const matchScore = useMemo(() => calculateMatchScore(job), [job])

  // Memoize handlers
  const handleRowClick = useCallback(() => {
    onEditJob(job)
  }, [onEditJob, job])

  const handleCheckboxChange = useCallback(() => {
    onSelect(job.id)
  }, [onSelect, job.id])

  const handleStatusChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onStatusChange(job.id, e.target.value as JobStatus)
    },
    [onStatusChange, job.id]
  )

  const handleEdit = useCallback(() => {
    onEditJob(job)
  }, [onEditJob, job])

  const handleDelete = useCallback(() => {
    onDeleteJob(job.id)
  }, [onDeleteJob, job.id])

  return (
    <tr
      className="hover:bg-gray-50 cursor-pointer"
      onClick={handleRowClick}
      style={style}
    >
      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={handleCheckboxChange}
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
          onChange={handleStatusChange}
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
            onClick={handleEdit}
            className="p-1 text-gray-400 hover:text-primary-600"
            aria-label="Edit job"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleDelete}
            className="p-1 text-gray-400 hover:text-red-600"
            aria-label="Delete job"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  )
})

export interface ListViewProps {
  jobs: JobApplication[]
  onEditJob: (job: JobApplication) => void
  onDeleteJob: (id: number) => void
  onStatusChange: (id: number, status: JobStatus) => void
  onBulkDelete: (ids: number[]) => void
  onBulkStatusChange: (ids: number[], status: JobStatus) => void
}

export const ListView = memo(function ListView({
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

  // Ref for the scrollable container
  const tableContainerRef = useRef<HTMLDivElement>(null)

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

  // Set up virtualizer for table rows
  const rowVirtualizer = useVirtualizer({
    count: filteredJobs.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
    getItemKey: (index) => filteredJobs[index]?.id ?? index,
  })

  const virtualRows = rowVirtualizer.getVirtualItems()
  const totalSize = rowVirtualizer.getTotalSize()

  // Calculate padding for proper table structure
  const paddingTop = virtualRows.length > 0 ? virtualRows[0]?.start ?? 0 : 0
  const paddingBottom = virtualRows.length > 0
    ? totalSize - (virtualRows[virtualRows.length - 1]?.end ?? totalSize)
    : 0

  const handleSelectAll = () => {
    if (selectedIds.size === filteredJobs.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredJobs.map((j) => j.id)))
    }
  }

  const handleSelect = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const newSelected = new Set(prev)
      if (newSelected.has(id)) {
        newSelected.delete(id)
      } else {
        newSelected.add(id)
      }
      return newSelected
    })
  }, [])

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

  // Memoize sort handler first
  const handleSort = useCallback((field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }, [sortField, sortDirection])

  // Memoize handlers to prevent recreation on each render
  const handleCompanySort = useCallback(() => handleSort('company'), [handleSort])
  const handlePositionSort = useCallback(() => handleSort('position'), [handleSort])
  const handleStatusSort = useCallback(() => handleSort('status'), [handleSort])
  const handleDateSort = useCallback(() => handleSort('application_date'), [handleSort])

  const SortIcon = useCallback(
    ({ field }: { field: SortField }) => {
      if (sortField !== field) {
        return <ArrowUpDown className="w-4 h-4 text-gray-400" />
      }
      return sortDirection === 'asc' ? (
        <ChevronUp className="w-4 h-4" />
      ) : (
        <ChevronDown className="w-4 h-4" />
      )
    },
    [sortField, sortDirection]
  )

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

      {/* Table with virtualization */}
      <div
        ref={tableContainerRef}
        className="overflow-auto rounded-lg border border-gray-200"
        style={{ maxHeight: 'calc(100vh - 320px)', minHeight: '400px' }}
      >
        <table className="w-full">
          <thead className="bg-gray-50 sticky top-0 z-10">
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
                onClick={handleCompanySort}
              >
                <div className="flex items-center gap-2">
                  Company
                  <SortIcon field="company" />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={handlePositionSort}
              >
                <div className="flex items-center gap-2">
                  Position
                  <SortIcon field="position" />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={handleStatusSort}
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
                onClick={handleDateSort}
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
          <tbody className="divide-y divide-gray-200 bg-white">
            {/* Top padding row for virtualization */}
            {paddingTop > 0 && (
              <tr>
                <td colSpan={8} style={{ height: paddingTop, padding: 0, border: 0 }} />
              </tr>
            )}
            {virtualRows.map((virtualRow) => {
              const job = filteredJobs[virtualRow.index]
              if (!job) return null
              return (
                <ListViewRow
                  key={job.id}
                  job={job}
                  isSelected={selectedIds.has(job.id)}
                  onSelect={handleSelect}
                  onEditJob={onEditJob}
                  onDeleteJob={onDeleteJob}
                  onStatusChange={onStatusChange}
                />
              )
            })}
            {/* Bottom padding row for virtualization */}
            {paddingBottom > 0 && (
              <tr>
                <td colSpan={8} style={{ height: paddingBottom, padding: 0, border: 0 }} />
              </tr>
            )}
          </tbody>
        </table>

        {filteredJobs.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No jobs found matching your criteria
          </div>
        )}
      </div>

      {/* Item count indicator */}
      {filteredJobs.length > 0 && (
        <div className="text-sm text-gray-500 text-right">
          Showing {filteredJobs.length} job{filteredJobs.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
})
