import { LoginPageClient } from './LoginPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Sign In',
  description: 'Sign in to access your job pipeline, resume tools, and interview prep workspace.',
}

/**
 * Login page - Server Component wrapper
 * Renders the login form with demo credentials support
 */
export default function LoginPage() {
  return <LoginPageClient />
}
