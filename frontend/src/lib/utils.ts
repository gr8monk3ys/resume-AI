import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

import type { JobStatus } from '@/types'

/**
 * Utility function to merge Tailwind CSS classes
 * Combines clsx for conditional classes with tailwind-merge for proper merging
 * @param inputs - Class values to merge
 * @returns Merged class string
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

/**
 * Status color mappings for job statuses
 */
interface StatusColors {
  bg: string
  text: string
  border: string
  badge: string
}

/**
 * Get color classes for a job status
 * @param status - The job status
 * @returns Object with bg, text, border, and badge color classes
 */
export function getStatusColor(status: JobStatus): StatusColors {
  const colors: Record<JobStatus, StatusColors> = {
    Bookmarked: {
      bg: 'bg-gray-50',
      text: 'text-gray-700',
      border: 'border-gray-300',
      badge: 'bg-gray-100 text-gray-800',
    },
    Applied: {
      bg: 'bg-blue-50',
      text: 'text-blue-700',
      border: 'border-blue-300',
      badge: 'bg-blue-100 text-blue-800',
    },
    'Phone Screen': {
      bg: 'bg-purple-50',
      text: 'text-purple-700',
      border: 'border-purple-300',
      badge: 'bg-purple-100 text-purple-800',
    },
    Interview: {
      bg: 'bg-amber-50',
      text: 'text-amber-700',
      border: 'border-amber-300',
      badge: 'bg-amber-100 text-amber-800',
    },
    Offer: {
      bg: 'bg-green-50',
      text: 'text-green-700',
      border: 'border-green-300',
      badge: 'bg-green-100 text-green-800',
    },
    Rejected: {
      bg: 'bg-red-50',
      text: 'text-red-700',
      border: 'border-red-300',
      badge: 'bg-red-100 text-red-800',
    },
  }
  return colors[status]
}

/**
 * Format a date string for display
 * @param dateString - ISO date string
 * @param format - Format type: 'short', 'long', or 'relative'
 * @returns Formatted date string
 */
export function formatDate(
  dateString: string | null | undefined,
  format: 'short' | 'long' | 'relative' = 'short'
): string {
  if (!dateString) return ''

  const date = new Date(dateString)
  const now = new Date()

  if (format === 'relative') {
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
    return `${Math.floor(diffDays / 365)} years ago`
  }

  if (format === 'long') {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  // short format
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/**
 * Truncate a string to a maximum length
 * @param str - The string to truncate
 * @param maxLength - Maximum length before truncation
 * @returns Truncated string with ellipsis if needed
 */
export function truncate(str: string | null | undefined, maxLength: number): string {
  if (!str) return ''
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength) + '...'
}

/**
 * Generate a unique ID
 * @returns A unique string ID
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}
