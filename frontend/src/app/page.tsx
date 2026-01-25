import { DashboardClient } from './DashboardClient'

/**
 * Home page - Server Component wrapper
 * Renders either landing page or dashboard based on auth state
 */
export default function HomePage() {
  return <DashboardClient />
}
