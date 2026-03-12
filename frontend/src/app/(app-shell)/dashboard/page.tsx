import { DashboardClient } from '@/app/DashboardClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Job Search Dashboard',
  description:
    'Track applications, improve resumes, and manage your AI-powered job search workflow.',
}

export default function DashboardPage() {
  return <DashboardClient />
}
