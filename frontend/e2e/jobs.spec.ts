import { test, expect } from '@playwright/test'

test.describe('Job Tracking', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"]', 'demo')
    await page.fill('input[name="password"]', 'demo123')
    await page.click('button[type="submit"]')
    await page.waitForURL('/')
  })

  test('should navigate to jobs page', async ({ page }) => {
    await page.goto('/jobs')

    await expect(page.getByRole('heading', { name: /job pipeline/i })).toBeVisible()
  })

  test('should display kanban board columns', async ({ page }) => {
    await page.goto('/jobs')

    await expect(page.getByText(/bookmarked/i)).toBeVisible()
    await expect(page.getByText(/applied/i)).toBeVisible()
    await expect(page.getByText(/phone screen/i)).toBeVisible()
    await expect(page.getByText(/interview/i)).toBeVisible()
    await expect(page.getByText(/offer/i)).toBeVisible()
    await expect(page.getByText(/rejected/i)).toBeVisible()
  })

  test('should open create job application modal', async ({ page }) => {
    await page.goto('/jobs')

    const addButton = page.getByRole('button', { name: /add job/i })
    await expect(addButton).toBeVisible()
    await addButton.click()

    await expect(page.getByRole('heading', { name: /new job application/i })).toBeVisible()
  })

  test('should create a new job application', async ({ page }) => {
    await page.goto('/jobs')

    await page.getByRole('button', { name: /add job/i }).click()

    await page.fill('input[name="company"]', 'Test Company')
    await page.fill('input[name="position"]', 'Software Engineer')
    await page.fill('input[name="location"]', 'Remote')
    await page.fill('textarea[name="description"]', 'Test job description')

    await page.click('button[type="submit"]')

    await expect(page.getByText(/test company/i)).toBeVisible()
    await expect(page.getByText(/software engineer/i)).toBeVisible()
  })

  test('should filter jobs by search', async ({ page }) => {
    await page.goto('/jobs')

    const searchInput = page.getByPlaceholder(/search/i)
    await expect(searchInput).toBeVisible()

    await searchInput.fill('Engineer')

    await expect(page.getByText(/engineer/i)).toBeVisible()
  })

  test('should view job application details', async ({ page }) => {
    await page.goto('/jobs')

    const firstJobCard = page.locator('[data-testid="job-card"]').first()
    await expect(firstJobCard).toBeVisible()
    await firstJobCard.click()

    await expect(page.getByRole('heading', { name: /job details/i })).toBeVisible()
  })
})
