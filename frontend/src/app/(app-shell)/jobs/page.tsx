import { JobsPageClient } from './JobsPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Job Pipeline',
  description: 'Track your applications, interviews, offers, and job search activity in one pipeline.',
}

/**
 * Jobs page - Server Component wrapper
 * Renders the job pipeline with Kanban board, list view, analytics, and timeline
 */
export default function JobsPage() {
  return <JobsPageClient />
}
