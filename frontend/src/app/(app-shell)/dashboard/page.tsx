import { DashboardClient } from '@/app/DashboardClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Job Search Command Center',
  description:
    'Run your search from one command center for applications, filters, resumes, and interview prep.',
}

export default function DashboardPage() {
  return <DashboardClient />
}
