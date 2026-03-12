import DocumentsPageClient from './DocumentsPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Documents',
  description: 'Create cover letters, networking outreach, and professional emails from one workspace.',
}

export default function DocumentsPage() {
  return <DocumentsPageClient />
}
