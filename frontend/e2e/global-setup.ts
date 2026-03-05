import type { FullConfig } from '@playwright/test'

const API_URL = process.env.API_URL || 'http://localhost:8000'

/**
 * Global setup for Playwright E2E tests.
 *
 * Runs once before all test projects. Verifies that required services
 * are reachable and creates the shared test user used by authenticated
 * test projects.
 */
async function globalSetup(_config: FullConfig): Promise<void> {
  console.log('[e2e] Global setup starting...')

  // 1. Verify backend is reachable
  const maxRetries = 10
  const retryDelay = 2000

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(`${API_URL}/health`)
      if (response.ok) {
        console.log(`[e2e] Backend is healthy (attempt ${attempt})`)
        break
      }
      throw new Error(`Health check returned ${response.status}`)
    } catch (error) {
      if (attempt === maxRetries) {
        throw new Error(
          `[e2e] Backend not reachable at ${API_URL}/health after ${maxRetries} attempts: ${String(error)}`
        )
      }
      console.log(`[e2e] Waiting for backend (attempt ${attempt}/${maxRetries})...`)
      await new Promise((resolve) => setTimeout(resolve, retryDelay))
    }
  }

  // 2. Create the demo/test user used by E2E tests.
  //    The backend may already have the user from a previous run —
  //    a 409 (conflict / already exists) is fine.
  try {
    const registerResponse = await fetch(`${API_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: 'demo',
        email: 'demo@resuboost.test',
        password: 'demo123',
      }),
    })

    if (registerResponse.ok) {
      console.log('[e2e] Test user "demo" created')
    } else if (registerResponse.status === 409 || registerResponse.status === 400) {
      console.log('[e2e] Test user "demo" already exists — reusing')
    } else {
      const body = await registerResponse.text()
      console.warn(`[e2e] Unexpected register response (${registerResponse.status}): ${body}`)
    }
  } catch (error) {
    console.warn(`[e2e] Could not register test user (non-fatal): ${String(error)}`)
  }

  // 3. Create the .auth directory for storage state files
  const fs = await import('fs')
  const path = await import('path')
  const authDir = path.join(path.dirname(new URL(import.meta.url).pathname), '.auth')
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true })
    console.log('[e2e] Created .auth directory for storage state')
  }

  console.log('[e2e] Global setup complete')
}

export default globalSetup
