/**
 * Shared types, constants, and utility functions for job pipeline components.
 * @module jobs/components/types
 */

import type {
  JobApplication,
  JobStatus,
  InterviewEventType,
  FollowUpUrgency,
} from '@/types'

// ============================================================================
// Constants
// ============================================================================

/** Available job statuses in pipeline order */
export const JOB_STATUSES: JobStatus[] = [
  'Bookmarked',
  'Applied',
  'Phone Screen',
  'Interview',
  'Offer',
  'Rejected',
]

/** Interview event types with display labels */
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

/** Tab types for job pipeline view */
export type TabType = 'kanban' | 'list' | 'analytics' | 'timeline'

/** Sort fields for list view */
export type SortField = 'company' | 'position' | 'status' | 'application_date' | 'created_at'

/** Sort direction */
export type SortDirection = 'asc' | 'desc'

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Returns Tailwind CSS classes for interview event type badges.
 * @param type - The interview event type
 * @returns CSS class string for background and text color
 */
export function getEventTypeColor(type: InterviewEventType): string {
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

/**
 * Returns Tailwind CSS classes for follow-up urgency indicators.
 * @param urgency - The urgency level
 * @returns CSS class string for background, text, and border color
 */
export function getUrgencyColor(urgency: FollowUpUrgency): string {
  const colors: Record<FollowUpUrgency, string> = {
    low: 'bg-green-100 text-green-800 border-green-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    high: 'bg-orange-100 text-orange-800 border-orange-200',
    overdue: 'bg-red-100 text-red-800 border-red-200',
  }
  return colors[urgency]
}

/**
 * Calculates the urgency level based on follow-up date.
 * @param followUpDate - ISO date string for the follow-up
 * @returns Urgency level based on days until follow-up
 */
export function calculateUrgency(followUpDate: string): FollowUpUrgency {
  const now = new Date()
  const date = new Date(followUpDate)
  const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays < 0) return 'overdue'
  if (diffDays === 0) return 'high'
  if (diffDays <= 2) return 'medium'
  return 'low'
}

/**
 * Calculates a match score for a job application based on completeness.
 * @param job - The job application to score
 * @returns Score from 0-100 based on filled fields
 */
export function calculateMatchScore(job: JobApplication): number {
  let score = 50
  if (job.job_description) score += 20
  if (job.location) score += 10
  if (job.job_url) score += 10
  if (job.notes) score += 10
  return Math.min(score, 100)
}
