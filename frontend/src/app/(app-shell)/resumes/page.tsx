import { ResumesPageClient } from './ResumesPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Resume Hub',
  description: 'Manage resumes, analyze ATS fit, and optimize application materials for target roles.',
}

/**
 * Resumes page - Server Component wrapper
 * Renders the resume hub with list, ATS analysis, keyword gap, and templates tabs
 */
export default function ResumesPage() {
  return <ResumesPageClient />
}
