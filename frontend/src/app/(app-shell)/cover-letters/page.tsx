import CoverLettersPageClient from './CoverLettersPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Cover Letters',
  description: 'Generate and manage tailored cover letters for your active job applications.',
}

export default function CoverLettersPage() {
  return <CoverLettersPageClient />
}
