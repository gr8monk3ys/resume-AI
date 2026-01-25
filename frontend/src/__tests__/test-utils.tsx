import { render, RenderOptions } from '@testing-library/react'
import { ReactElement, ReactNode } from 'react'

import { AuthContext, AuthContextType } from '@/lib/auth'

import type { User } from '@/types'

/**
 * Create a mock user for testing
 */
export function createMockUser(overrides?: Partial<User>): User {
  return {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    full_name: 'Test User',
    is_active: true,
    is_admin: false,
    created_at: '2024-01-01T00:00:00Z',
    last_login: '2024-01-15T12:00:00Z',
    ...overrides,
  }
}


/**
 * Default mock auth context for unauthenticated state
 */
export const mockAuthContextUnauthenticated: AuthContextType = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  authError: null,
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  refreshAuth: vi.fn().mockResolvedValue(false),
}

/**
 * Default mock auth context for authenticated state
 */
export const mockAuthContextAuthenticated: AuthContextType = {
  user: createMockUser(),
  isAuthenticated: true,
  isLoading: false,
  authError: null,
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  refreshAuth: vi.fn().mockResolvedValue(true),
}

/**
 * Default mock auth context for loading state
 */
export const mockAuthContextLoading: AuthContextType = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  authError: null,
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  refreshAuth: vi.fn().mockResolvedValue(false),
}

/**
 * Create a wrapper component with providers
 */
function createWrapper(authContext: AuthContextType = mockAuthContextUnauthenticated) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <AuthContext.Provider value={authContext}>
        {children}
      </AuthContext.Provider>
    )
  }
}

/**
 * Custom render function that includes providers
 */
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  authContext?: AuthContextType
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { authContext = mockAuthContextUnauthenticated, ...renderOptions } = options

  return {
    ...render(ui, {
      wrapper: createWrapper(authContext),
      ...renderOptions,
    }),
    // Return mock functions for assertions
    mockLogin: authContext.login,
    mockLogout: authContext.logout,
    mockRegister: authContext.register,
  }
}

/**
 * Wait for loading to complete
 */
export async function waitForLoadingToComplete() {
  // Helper to wait for loading spinners to disappear
  await new Promise((resolve) => setTimeout(resolve, 0))
}

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

/**
 * Create a mock resume
 */
export function createMockResume(overrides?: Partial<import('@/types').Resume>) {
  return {
    id: 1,
    profile_id: 1,
    version_name: 'Main Resume',
    content: 'Test resume content',
    ats_score: 85,
    keywords: 'javascript,react,typescript',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    ...overrides,
  }
}

/**
 * Create a mock cover letter
 */
export function createMockCoverLetter(overrides?: Partial<import('@/types').CoverLetter>) {
  return {
    id: 1,
    profile_id: 1,
    job_application_id: 1,
    content: 'Test cover letter content',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    ...overrides,
  }
}

/**
 * Create mock job stats
 */
export function createMockJobStats(): import('@/types').JobStats {
  return {
    total: 10,
    status_breakdown: {
      Bookmarked: 2,
      Applied: 4,
      'Phone Screen': 1,
      Interview: 2,
      Offer: 1,
      Rejected: 0,
    },
    response_rate: 40,
    offer_rate: 10,
  }
}
