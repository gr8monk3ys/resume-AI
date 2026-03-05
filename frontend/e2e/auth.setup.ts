import { test as setup, expect } from '@playwright/test'

const authFile = 'e2e/.auth/user.json'

/**
 * Authentication setup — runs once before browser-specific projects.
 *
 * Logs in with the demo user and saves the authenticated storage state
 * so that all subsequent tests start already logged in.
 */
setup('authenticate as demo user', async ({ page }) => {
  await page.goto('/login')

  await page.fill('input[name="username"]', 'demo')
  await page.fill('input[name="password"]', 'demo123')
  await page.click('button[type="submit"]')

  // Wait until the login completes and we land on the dashboard
  await page.waitForURL('/')
  await expect(page.getByText(/dashboard/i)).toBeVisible()

  // Save the authenticated browser state for reuse by other projects
  await page.context().storageState({ path: authFile })
})
