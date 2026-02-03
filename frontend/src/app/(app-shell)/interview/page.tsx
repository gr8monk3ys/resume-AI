import InterviewCenterPageClient from './InterviewCenterPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Interview Center',
  description: 'Practice interview questions, prepare STAR stories, and build company research notes.',
}

export default function InterviewCenterPage() {
  return <InterviewCenterPageClient />
}
