import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for ResuBoost AI E2E tests
 *
 * Configured to run against the real backend for true integration testing.
 * Uses webServer to start both backend and frontend automatically.
 */

// Environment configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'
const API_URL = process.env.API_URL || 'http://localhost:8000'
const CI = !!process.env.CI

export default defineConfig({
  testDir: './e2e',

  // Run tests in parallel for faster execution
  fullyParallel: true,

  // Fail fast in CI to save time
  forbidOnly: CI,

  // Retry failed tests in CI for stability
  retries: CI ? 2 : 1,

  // Limit workers in CI for stability
  workers: CI ? 2 : undefined,

  // Reporters
  reporter: CI
    ? [
        ['github'],
        ['html', { outputFolder: 'playwright-report', open: 'never' }],
        ['junit', { outputFile: 'test-results/junit.xml' }],
      ]
    : [
        ['html', { outputFolder: 'playwright-report', open: 'on-failure' }],
        ['list'],
      ],

  // Global test settings
  use: {
    baseURL: BASE_URL,

    // Capture trace on first retry for debugging
    trace: 'on-first-retry',

    // Screenshot on failure for debugging
    screenshot: 'only-on-failure',

    // Video recording on failure
    video: 'retain-on-failure',

    // Timeouts
    actionTimeout: 15000,
    navigationTimeout: 30000,

    // Extra HTTP headers for API requests
    extraHTTPHeaders: {
      'Accept': 'application/json',
    },
  },

  // Global timeout for each test
  timeout: 60000,

  // Expect timeout
  expect: {
    timeout: 10000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.1,
    },
  },

  // Output directory for test artifacts
  outputDir: 'test-results/',

  // Test projects for different browsers
  projects: [
    // Setup project for authentication state
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    // Desktop Chrome - primary
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Use stored authentication state
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    // Desktop Firefox
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    // Desktop Safari (WebKit)
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    // Mobile Chrome
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    // Mobile Safari
    {
      name: 'mobile-safari',
      use: {
        ...devices['iPhone 12'],
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    // Tests that don't require authentication
    {
      name: 'chromium-no-auth',
      testMatch: /.*\.(auth|smoke)\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],

  // Web servers to start before tests
  webServer: [
    // Backend server (FastAPI)
    {
      command: CI
        ? 'cd ../backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000'
        : 'cd ../backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000',
      url: `${API_URL}/health`,
      reuseExistingServer: !CI,
      timeout: 120000,
      env: {
        LLM_PROVIDER: 'mock',
        TESTING: 'true',
        SECRET_KEY: 'test-secret-key-for-e2e-tests',
        DATABASE_URL: 'sqlite:///./data/test_e2e.db',
      },
    },
    // Frontend server (Next.js)
    {
      command: CI ? 'npm run build && npm run start' : 'npm run dev',
      url: BASE_URL,
      reuseExistingServer: !CI,
      timeout: 120000,
      env: {
        NEXT_PUBLIC_API_URL: API_URL,
        NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS: 'true',
        NEXT_PUBLIC_DEMO_USERNAME: 'demo',
        NEXT_PUBLIC_DEMO_PASSWORD: 'demo123',
      },
    },
  ],

  // Global setup/teardown
  globalSetup: './e2e/global-setup.ts',
  globalTeardown: './e2e/global-teardown.ts',
})
