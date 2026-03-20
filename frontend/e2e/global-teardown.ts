import type { FullConfig } from '@playwright/test'

/**
 * Global teardown for Playwright E2E tests.
 *
 * Runs once after all test projects have finished.
 * Cleans up any test artifacts created during the run.
 */
async function globalTeardown(_config: FullConfig): Promise<void> {
  console.log('[e2e] Global teardown starting...')

  // Clean up the .auth storage state directory
  const fs = await import('fs')
  const path = await import('path')
  const authDir = path.join(path.dirname(new URL(import.meta.url).pathname), '.auth')

  if (fs.existsSync(authDir)) {
    fs.rmSync(authDir, { recursive: true, force: true })
    console.log('[e2e] Cleaned up .auth directory')
  }

  console.log('[e2e] Global teardown complete')
}

export default globalTeardown
