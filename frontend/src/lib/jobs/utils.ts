import type { InterviewEventType, FollowUpUrgency, JobApplication } from '@/types'

/**
 * Get color classes for an interview event type
 * @param type - The interview event type
 * @returns Tailwind CSS classes for the event type badge
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
 * Get color classes for follow-up urgency level
 * @param urgency - The urgency level
 * @returns Tailwind CSS classes for the urgency badge
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
 * Calculate urgency level based on follow-up date
 * @param followUpDate - The follow-up date string
 * @returns The urgency level
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
 * Calculate a match score for a job application based on completeness
 * @param job - The job application
 * @returns A score from 0-100
 */
export function calculateMatchScore(job: JobApplication): number {
  // Simple mock match score calculation based on completeness
  let score = 50
  if (job.job_description) score += 20
  if (job.location) score += 10
  if (job.job_url) score += 10
  if (job.notes) score += 10
  return Math.min(score, 100)
}
