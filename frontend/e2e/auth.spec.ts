import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('should login with demo credentials', async ({ page }) => {
    await page.goto('/login')

    await expect(page.getByRole('heading', { name: /login/i })).toBeVisible()

    await page.fill('input[name="username"]', 'demo')
    await page.fill('input[name="password"]', 'demo123')

    await page.click('button[type="submit"]')

    await page.waitForURL('/')

    await expect(page.getByText(/dashboard/i)).toBeVisible()
  })

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[name="username"]', 'invalid')
    await page.fill('input[name="password"]', 'wrongpass')

    await page.click('button[type="submit"]')

    await expect(page.getByText(/invalid credentials/i)).toBeVisible()
  })

  test('should navigate to register page', async ({ page }) => {
    await page.goto('/login')

    await page.click('a[href="/register"]')

    await expect(page).toHaveURL('/register')
    await expect(page.getByRole('heading', { name: /register/i })).toBeVisible()
  })

  test('should logout successfully', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[name="username"]', 'demo')
    await page.fill('input[name="password"]', 'demo123')
    await page.click('button[type="submit"]')

    await page.waitForURL('/')

    const logoutButton = page.getByRole('button', { name: /logout/i })
    await expect(logoutButton).toBeVisible()
    await logoutButton.click()

    await page.waitForURL('/login')
  })

  test('should redirect to login when accessing protected route', async ({ page }) => {
    await page.goto('/resumes')

    await expect(page).toHaveURL('/login')
  })
})
