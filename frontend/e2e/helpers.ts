import { Page } from '@playwright/test'

export async function loginAsDemo(page: Page) {
  await page.goto('/login')
  await page.fill('input[name="username"]', 'demo')
  await page.fill('input[name="password"]', 'demo123')
  await page.click('button[type="submit"]')
  await page.waitForURL('/')
}

export async function logout(page: Page) {
  const logoutButton = page.getByRole('button', { name: /logout/i })
  await logoutButton.click()
  await page.waitForURL('/login')
}

export async function createJobApplication(
  page: Page,
  job: {
    company: string
    position: string
    location: string
    description: string
  }
) {
  await page.goto('/jobs')
  await page.getByRole('button', { name: /add job/i }).click()

  await page.fill('input[name="company"]', job.company)
  await page.fill('input[name="position"]', job.position)
  await page.fill('input[name="location"]', job.location)
  await page.fill('textarea[name="description"]', job.description)

  await page.click('button[type="submit"]')
}

export async function waitForAPIResponse(page: Page, urlPattern: string) {
  return page.waitForResponse((response) =>
    response.url().includes(urlPattern) && response.status() === 200
  )
}
