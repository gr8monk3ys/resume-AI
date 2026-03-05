import { test, expect } from '@playwright/test'

test.describe('Resume Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"]', 'demo')
    await page.fill('input[name="password"]', 'demo123')
    await page.click('button[type="submit"]')
    await page.waitForURL('/')
  })

  test('should navigate to resumes page', async ({ page }) => {
    await page.goto('/resumes')

    await expect(page.getByRole('heading', { name: /resume hub/i })).toBeVisible()
  })

  test('should display upload resume button', async ({ page }) => {
    await page.goto('/resumes')

    const uploadButton = page.getByRole('button', { name: /upload resume/i })
    await expect(uploadButton).toBeVisible()
  })

  test('should open upload resume modal', async ({ page }) => {
    await page.goto('/resumes')

    await page.getByRole('button', { name: /upload resume/i }).click()

    await expect(page.getByRole('heading', { name: /upload resume/i })).toBeVisible()
  })

  test('should display resume list', async ({ page }) => {
    await page.goto('/resumes')

    const resumeList = page.getByTestId('resume-list')
    await expect(resumeList).toBeVisible()
  })

  test('should view resume details', async ({ page }) => {
    await page.goto('/resumes')

    const firstResume = page.locator('[data-testid="resume-card"]').first()
    if (await firstResume.isVisible()) {
      await firstResume.click()
      await expect(page.getByRole('heading', { name: /resume details/i })).toBeVisible()
    }
  })

  test('should navigate to AI tailor feature', async ({ page }) => {
    await page.goto('/resumes')

    const tailorButton = page.getByRole('button', { name: /tailor resume/i })
    if (await tailorButton.isVisible()) {
      await tailorButton.click()
      await expect(page.getByText(/job description/i)).toBeVisible()
    }
  })
})
