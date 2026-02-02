import type { JobStatus, InterviewEventType } from '@/types'

/**
 * Available job statuses in order of pipeline progression
 */
export const JOB_STATUSES: JobStatus[] = [
  'Bookmarked',
  'Applied',
  'Phone Screen',
  'Interview',
  'Offer',
  'Rejected',
]

/**
 * Interview event types with display labels
 */
export const EVENT_TYPES: { value: InterviewEventType; label: string }[] = [
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

/**
 * Tab types for the jobs page
 */
export type TabType = 'kanban' | 'list' | 'analytics' | 'timeline'

/**
 * Sort field options for list view
 */
export type SortField = 'company' | 'position' | 'status' | 'application_date' | 'created_at'

/**
 * Sort direction options
 */
export type SortDirection = 'asc' | 'desc'
