/**
 * Create a mock job application
 */
export function createMockJobApplication(overrides?: Partial<import('@/types').JobApplication>) {
  return {
    id: 1,
    profile_id: 1,
    company: 'Test Company',
    position: 'Software Engineer',
    job_description: 'A great job',
    status: 'Applied' as const,
    application_date: '2024-01-15',
    deadline: '2024-02-01',
    location: 'Remote',
    job_url: 'https://example.com/job',
    notes: 'Test notes',
    created_at: '2024-01-15T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    ...overrides,
  }
}
