import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"]', 'demo')
    await page.fill('input[name="password"]', 'demo123')
    await page.click('button[type="submit"]')
    await page.waitForURL('/')
  })

  test('should display dashboard', async ({ page }) => {
    await expect(page.getByText(/dashboard/i)).toBeVisible()
  })

  test('should navigate to all main pages', async ({ page }) => {
    const navigationTests = [
      { path: '/resumes', heading: /resume hub/i },
      { path: '/jobs', heading: /job pipeline/i },
      { path: '/interview', heading: /interview center/i },
      { path: '/documents', heading: /document generator/i },
      { path: '/cover-letters', heading: /cover letters/i },
      { path: '/career', heading: /career tools/i },
      { path: '/ai-assistant', heading: /ai assistant/i },
    ]

    for (const { path, heading } of navigationTests) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: heading })).toBeVisible()
    }
  })

  test('should navigate via sidebar links', async ({ page }) => {
    await page.goto('/')

    const resumesLink = page.getByRole('link', { name: /resumes/i })
    if (await resumesLink.isVisible()) {
      await resumesLink.click()
      await expect(page).toHaveURL('/resumes')
    }

    const jobsLink = page.getByRole('link', { name: /jobs/i })
    if (await jobsLink.isVisible()) {
      await jobsLink.click()
      await expect(page).toHaveURL('/jobs')
    }
  })

  test('should navigate back to dashboard', async ({ page }) => {
    await page.goto('/resumes')

    const dashboardLink = page.getByRole('link', { name: /dashboard/i })
    if (await dashboardLink.isVisible()) {
      await dashboardLink.click()
      await expect(page).toHaveURL('/')
    }
  })

  test('should navigate to profile page', async ({ page }) => {
    await page.goto('/')

    const profileLink = page.getByRole('link', { name: /profile/i })
    if (await profileLink.isVisible()) {
      await profileLink.click()
      await expect(page).toHaveURL('/profile')
    }
  })

  test('should navigate to settings page', async ({ page }) => {
    await page.goto('/')

    const settingsLink = page.getByRole('link', { name: /settings/i })
    if (await settingsLink.isVisible()) {
      await settingsLink.click()
      await expect(page).toHaveURL('/settings')
    }
  })
})
