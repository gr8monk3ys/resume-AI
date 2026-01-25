# E2E Tests

End-to-end tests for ResuBoost AI using Playwright.

## Test Coverage

### Authentication (`auth.spec.ts`)
- Login with demo credentials
- Invalid credentials error handling
- Registration page navigation
- Logout functionality
- Protected route redirection

### Job Tracking (`jobs.spec.ts`)
- Navigate to jobs page
- Display kanban board columns
- Create new job application
- Search and filter jobs
- View job details

### Resume Management (`resumes.spec.ts`)
- Navigate to resumes page
- Upload resume functionality
- Display resume list
- View resume details
- AI tailor feature

### Navigation (`navigation.spec.ts`)
- Dashboard display
- Navigate to all main pages
- Sidebar navigation
- Profile and settings access

## Running Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run with UI mode
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed

# Debug specific test
npm run test:e2e:debug

# Run specific test file
npx playwright test e2e/auth.spec.ts

# Run tests with tag
npx playwright test --grep @smoke
```

## Debugging

### View Test Report
```bash
npx playwright show-report
```

### View Trace
```bash
npx playwright show-trace test-results/*/trace.zip
```

### Screenshots and Videos
Playwright automatically captures screenshots and videos on failure in the `test-results/` directory.

## Flaky Test Management

### Detect Flaky Tests
```bash
# Run each test 10 times
npx playwright test --repeat-each=10

# Run specific test multiple times
npx playwright test e2e/auth.spec.ts --repeat-each=10
```

### Quarantine Flaky Tests
```typescript
// Mark test as fixme
test.fixme(true, 'Flaky: Race condition - JIRA-123')

// Skip in CI only
test.skip(process.env.CI === 'true', 'Quarantined: Investigating timing issue')
```

## Test Helpers

Common test utilities are available in `helpers.ts`:

```typescript
import { loginAsDemo, logout, createJobApplication } from './helpers'

test('my test', async ({ page }) => {
  await loginAsDemo(page)
  // Test code
  await logout(page)
})
```

## CI/CD Integration

Tests run in CI with:
- 2 retries for flaky tests
- Single worker for reliability
- Trace/screenshot/video capture on failure

## Best Practices

1. Use stable selectors (role, test-id)
2. Wait for conditions, not fixed timeouts
3. Keep tests independent and isolated
4. Use page object pattern for complex flows
5. Mock external dependencies when needed
