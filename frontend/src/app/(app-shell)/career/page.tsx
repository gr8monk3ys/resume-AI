import CareerToolsPageClient from './CareerToolsPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Career Tools',
  description: 'Track achievements, research compensation, and build better application stories.',
}

export default function CareerToolsPage() {
  return <CareerToolsPageClient />
}
