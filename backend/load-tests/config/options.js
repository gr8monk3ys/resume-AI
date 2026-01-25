/**
 * Shared k6 configuration options for ResuBoost AI load tests
 *
 * This file contains reusable configuration objects for different test scenarios.
 */

// Performance thresholds that define pass/fail criteria
export const thresholds = {
  // HTTP request duration thresholds
  http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95th percentile < 500ms, 99th < 1s
  http_req_failed: ['rate<0.01'], // Less than 1% request failure rate

  // Custom thresholds for specific endpoint types
  'http_req_duration{endpoint:health}': ['p(95)<100'], // Health check < 100ms
  'http_req_duration{endpoint:auth}': ['p(95)<300'], // Auth endpoints < 300ms
  'http_req_duration{endpoint:jobs}': ['p(95)<500'], // Jobs CRUD < 500ms
  'http_req_duration{endpoint:resumes}': ['p(95)<500'], // Resume operations < 500ms
  'http_req_duration{endpoint:ai}': ['p(95)<5000'], // AI endpoints < 5s (LLM calls)
  'http_req_duration{endpoint:ats}': ['p(95)<1000'], // ATS analysis < 1s (algorithmic)

  // Rate thresholds
  http_reqs: ['rate>10'], // Minimum 10 requests per second
}

// Stricter thresholds for critical endpoints
export const criticalThresholds = {
  http_req_duration: ['p(95)<300', 'p(99)<500'],
  http_req_failed: ['rate<0.001'], // Less than 0.1% failure
  'http_req_duration{endpoint:health}': ['p(95)<50'],
  'http_req_duration{endpoint:auth}': ['p(95)<200'],
}

// Relaxed thresholds for stress testing (expect some failures)
export const stressThresholds = {
  http_req_duration: ['p(95)<2000', 'p(99)<5000'],
  http_req_failed: ['rate<0.10'], // Allow up to 10% failure under stress
}

// Smoke test options (quick validation)
export const smokeOptions = {
  vus: 1,
  duration: '30s',
  thresholds: criticalThresholds,
}

// Load test options (normal load simulation)
export const loadOptions = {
  stages: [
    { duration: '1m', target: 20 }, // Ramp up to 20 users
    { duration: '3m', target: 50 }, // Ramp up to 50 users
    { duration: '5m', target: 50 }, // Maintain 50 users
    { duration: '3m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 100 }, // Maintain 100 users
    { duration: '2m', target: 0 }, // Ramp down
  ],
  thresholds: thresholds,
}

// Stress test options (find breaking point)
export const stressOptions = {
  stages: [
    { duration: '2m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 100 }, // Maintain
    { duration: '2m', target: 200 }, // Ramp up to 200 users
    { duration: '5m', target: 200 }, // Maintain
    { duration: '2m', target: 300 }, // Ramp up to 300 users
    { duration: '5m', target: 300 }, // Maintain
    { duration: '2m', target: 500 }, // Ramp up to 500 users
    { duration: '5m', target: 500 }, // Maintain and find breaking point
    { duration: '5m', target: 0 }, // Ramp down
  ],
  thresholds: stressThresholds,
}

// Spike test options (sudden traffic spike)
export const spikeOptions = {
  stages: [
    { duration: '30s', target: 10 }, // Baseline: 10 users
    { duration: '1m', target: 10 }, // Maintain baseline
    { duration: '10s', target: 200 }, // Spike to 200 users
    { duration: '3m', target: 200 }, // Maintain spike
    { duration: '10s', target: 10 }, // Drop back to baseline
    { duration: '2m', target: 10 }, // Recover
    { duration: '10s', target: 200 }, // Second spike
    { duration: '3m', target: 200 }, // Maintain
    { duration: '30s', target: 0 }, // Ramp down
  ],
  thresholds: thresholds,
}

// Soak test options (extended duration)
export const soakOptions = {
  stages: [
    { duration: '5m', target: 50 }, // Ramp up
    { duration: '60m', target: 50 }, // Maintain for 1 hour
    { duration: '5m', target: 0 }, // Ramp down
  ],
  thresholds: {
    ...thresholds,
    // Additional memory leak detection thresholds
    iteration_duration: ['p(95)<5000'],
    checks: ['rate>0.99'], // 99% of checks should pass
  },
}

// Short soak test for CI/CD (15 minutes)
export const shortSoakOptions = {
  stages: [
    { duration: '2m', target: 30 }, // Ramp up
    { duration: '15m', target: 30 }, // Maintain
    { duration: '2m', target: 0 }, // Ramp down
  ],
  thresholds: thresholds,
}

// Export base URL configuration
export function getBaseUrl() {
  return __ENV.BASE_URL || 'http://localhost:8000'
}

// Export common HTTP params
export function getHttpParams(token = null) {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    timeout: '30s',
  }

  if (token) {
    params.headers['Authorization'] = `Bearer ${token}`
  }

  return params
}
