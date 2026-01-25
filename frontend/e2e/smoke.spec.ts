import { test, expect } from '@playwright/test'

test.describe('Smoke Tests', () => {
  test('should load the login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveTitle(/resuboost ai/i)
  })

  test('should load the application', async ({ page }) => {
    const response = await page.goto('/')
    expect(response?.status()).toBeLessThan(400)
  })
})
