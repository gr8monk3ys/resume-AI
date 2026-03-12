import { RegisterPageClient } from './RegisterPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Create Account',
  description: 'Create a ResuBoost AI account to manage resumes, applications, and AI job search tools.',
}

/**
 * Register page - Server Component wrapper
 * Renders the registration form with password strength validation
 */
export default function RegisterPage() {
  return <RegisterPageClient />
}
