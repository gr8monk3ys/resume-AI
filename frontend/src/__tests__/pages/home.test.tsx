import { render, screen, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { DashboardClient } from '@/app/DashboardClient'
import { LandingPage } from '@/app/LandingPage'
import { jobsApi, resumesApi, coverLettersApi } from '@/lib/api'
import { AuthContext, AuthContextType } from '@/lib/auth'

import type { User, JobApplication, Resume, CoverLetter, JobStats } from '@/types'

// Mock the API module
vi.mock('@/lib/api', () => ({
  jobsApi: {
    list: vi.fn(),
    getStats: vi.fn(),
  },
  resumesApi: {
    list: vi.fn(),
  },
  coverLettersApi: {
    list: vi.fn(),
  },
}))

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}))

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

/**
 * Mock user data
 */
const mockUser: User = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  full_name: 'Test User',
  is_active: true,
  is_admin: false,
  created_at: '2024-01-01T00:00:00Z',
  last_login: '2024-01-15T12:00:00Z',
}


/**
 * Mock job applications
 */
const mockJobs: JobApplication[] = [
  {
    id: 1,
    profile_id: 1,
    company: 'Tech Corp',
    position: 'Senior Developer',
    job_description: 'Great job',
    status: 'Applied',
    application_date: '2024-01-15',
    deadline: null,
    location: 'Remote',
    job_url: 'https://example.com',
    notes: null,
    created_at: '2024-01-15T00:00:00Z',
    updated_at: '2024-01-15T12:00:00Z',
  },
  {
    id: 2,
    profile_id: 1,
    company: 'Startup Inc',
    position: 'Full Stack Engineer',
    job_description: null,
    status: 'Interview',
    application_date: '2024-01-10',
    deadline: null,
    location: 'New York',
    job_url: null,
    notes: null,
    created_at: '2024-01-10T00:00:00Z',
    updated_at: '2024-01-14T00:00:00Z',
  },
  {
    id: 3,
    profile_id: 1,
    company: 'Big Company',
    position: 'Software Engineer',
    job_description: null,
    status: 'Phone Screen',
    application_date: '2024-01-05',
    deadline: null,
    location: null,
    job_url: null,
    notes: null,
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-13T00:00:00Z',
  },
]

/**
 * Mock resumes
 */
const mockResumes: Resume[] = [
  {
    id: 1,
    profile_id: 1,
    version_name: 'Main Resume',
    content: 'Resume content',
    ats_score: 85,
    keywords: 'javascript,react',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
  },
  {
    id: 2,
    profile_id: 1,
    version_name: 'Tech Resume',
    content: 'Tech resume content',
    ats_score: 90,
    keywords: 'python,aws',
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
  },
]

/**
 * Mock cover letters
 */
const mockCoverLetters: CoverLetter[] = [
  {
    id: 1,
    profile_id: 1,
    job_application_id: 1,
    content: 'Cover letter content',
    created_at: '2024-01-15T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
  },
]

/**
 * Mock job stats
 */
const mockJobStats: JobStats = {
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

/**
 * Helper to render home page with auth context
 */
function renderHomePage(authContextOverrides: Partial<AuthContextType> = {}) {
  const defaultContext: AuthContextType = {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    authError: null,
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    refreshAuth: vi.fn().mockResolvedValue(false),
    ...authContextOverrides,
  }

  const isAuth = defaultContext.user && defaultContext.isAuthenticated

  return render(
    <AuthContext.Provider value={defaultContext}>
      {isAuth ? (
        <DashboardClient />
      ) : (
        <main id="main-content">
          <LandingPage />
        </main>
      )}
    </AuthContext.Provider>
  )
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset all API mocks
    vi.mocked(jobsApi.list).mockResolvedValue(mockJobs)
    vi.mocked(jobsApi.getStats).mockResolvedValue(mockJobStats)
    vi.mocked(resumesApi.list).mockResolvedValue(mockResumes)
    vi.mocked(coverLettersApi.list).mockResolvedValue(mockCoverLetters)
  })

  describe('Loading State', () => {
    it('should keep rendering the landing page while auth bootstrap is loading', () => {
      renderHomePage({ isLoading: true })

      expect(screen.getByRole('heading', { name: /resuboost ai/i })).toBeInTheDocument()
      expect(screen.queryByRole('status', { name: /loading/i })).not.toBeInTheDocument()
    })
  })

  describe('Landing Page (Unauthenticated)', () => {
    it('should render landing page for unauthenticated users', () => {
      renderHomePage({ user: null, isLoading: false })

      expect(screen.getByRole('heading', { name: /resuboost ai/i })).toBeInTheDocument()
      expect(screen.getByText(/stop rebuilding context every time you open a new tab/i)).toBeInTheDocument()
    })

    it('should render call-to-action buttons', () => {
      renderHomePage({ user: null, isLoading: false })

      expect(screen.getByRole('link', { name: /build your search system/i })).toHaveAttribute('href', '/register')
      expect(screen.getAllByRole('link', { name: /sign in/i })[0]).toHaveAttribute('href', '/login')
    })

    it('should render feature cards', () => {
      renderHomePage({ user: null, isLoading: false })

      expect(screen.getByText(/search briefs that stay focused/i)).toBeInTheDocument()
      expect(screen.getByText(/a pipeline that remembers the details/i)).toBeInTheDocument()
      expect(screen.getByText(/resume versions tied to the opportunity/i)).toBeInTheDocument()
      expect(screen.getByText(/interview prep from the same context/i)).toBeInTheDocument()
    })

    it('should render value propositions', () => {
      renderHomePage({ user: null, isLoading: false })

      expect(screen.getByRole('heading', { level: 3, name: /search with intent/i })).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 3, name: /run the application loop cleanly/i })).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 3, name: /keep materials ready/i })).toBeInTheDocument()
    })

    it('should render bottom CTA section', () => {
      renderHomePage({ user: null, isLoading: false })

      expect(screen.getByText(/build a tighter job search loop/i)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /create your workspace/i })).toHaveAttribute('href', '/register')
    })
  })

  describe('Dashboard (Authenticated)', () => {
    it('should render dashboard for authenticated users', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        expect(screen.getByText(/welcome back, test user/i)).toBeInTheDocument()
      })
    })

    it('should show username if full_name is not set', async () => {
      const userWithoutName = { ...mockUser, full_name: null }
      renderHomePage({ user: userWithoutName, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        expect(screen.getByText(/welcome back, testuser/i)).toBeInTheDocument()
      })
    })

    it('should render stats cards', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        expect(screen.getByText('Active pipeline')).toBeInTheDocument()
        expect(screen.getByText('Response rate')).toBeInTheDocument()
        expect(screen.getByText('Resume average')).toBeInTheDocument()
        expect(screen.getByText('Cover letter drafts')).toBeInTheDocument()
      })
    })

    it('should display correct stats values', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        const pipelineCard = screen.getByText('Active pipeline').closest('a')
        expect(within(pipelineCard!).getByText('3')).toBeInTheDocument()
      })

      await waitFor(() => {
        const resumeAverageCard = screen.getByText('Resume average').closest('a')
        expect(within(resumeAverageCard!).getByText('88')).toBeInTheDocument()
      })

      await waitFor(() => {
        const coverLettersCard = screen.getByText('Cover letter drafts').closest('a')
        expect(within(coverLettersCard!).getByText('1')).toBeInTheDocument()
      })

      await waitFor(() => {
        const responseRateCard = screen.getByText('Response rate').closest('a')
        expect(within(responseRateCard!).getByText('40%')).toBeInTheDocument()
      })
    })

    it('should render recent applications', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        expect(screen.getByText('Recent applications')).toBeInTheDocument()
      })

      // The applications are loaded async and sorted by updated_at
      await waitFor(() => {
        expect(screen.getByText('Senior Developer')).toBeInTheDocument()
      })

      // Company name is part of a truncated text block
      await waitFor(() => {
        expect(screen.getByText(/Tech Corp/)).toBeInTheDocument()
      })
    })

    it('should show application statuses', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        expect(screen.getAllByText('Applied').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Interview').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Phone Screen').length).toBeGreaterThan(0)
      })
    })

    it('should render quick actions', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        expect(screen.getByText('Open the right workspace')).toBeInTheDocument()
      })

      const nav = screen.getByRole('navigation', { name: /quick actions/i })
      expect(within(nav).getByRole('link', { name: /tune search filters/i })).toHaveAttribute('href', '/jobs/filters')
      expect(within(nav).getByRole('link', { name: /review pipeline/i })).toHaveAttribute('href', '/jobs')
    })

    it('should show empty state when no applications', async () => {
      vi.mocked(jobsApi.list).mockResolvedValue([])

      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        expect(screen.getByText(/no applications tracked yet/i)).toBeInTheDocument()
        expect(screen.getByRole('link', { name: /add your first application/i })).toBeInTheDocument()
      })
    })

    it('should show loading state for stats', () => {
      // Make the API call hang
      vi.mocked(jobsApi.list).mockImplementation(() => new Promise(() => {}))
      vi.mocked(resumesApi.list).mockImplementation(() => new Promise(() => {}))
      vi.mocked(coverLettersApi.list).mockImplementation(() => new Promise(() => {}))
      vi.mocked(jobsApi.getStats).mockImplementation(() => new Promise(() => {}))

      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      const activePipelineCard = screen.getByText('Active pipeline').closest('a')
      expect(within(activePipelineCard!).getByText('-')).toBeInTheDocument()
    })

    it('should link stats cards to correct pages', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        expect(screen.getByText('Active pipeline').closest('a')).toHaveAttribute('href', '/jobs')
        expect(screen.getByText('Resume average').closest('a')).toHaveAttribute('href', '/resumes')
        expect(screen.getByText('Cover letter drafts').closest('a')).toHaveAttribute('href', '/documents')
        expect(screen.getByText('Response rate').closest('a')).toHaveAttribute('href', '/analytics')
      })
    })
  })

  describe('API Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      vi.mocked(jobsApi.list).mockRejectedValue(new Error('API Error'))
      vi.mocked(resumesApi.list).mockRejectedValue(new Error('API Error'))
      vi.mocked(coverLettersApi.list).mockRejectedValue(new Error('API Error'))
      vi.mocked(jobsApi.getStats).mockRejectedValue(new Error('API Error'))

      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      // Should still render dashboard without crashing
      await waitFor(() => {
        expect(screen.getByText(/welcome back/i)).toBeInTheDocument()
      })

      await waitFor(() => {
        const pipelineCard = screen.getByText('Active pipeline').closest('a')
        expect(within(pipelineCard!).getByText('0')).toBeInTheDocument()
      })
    })

    it('should handle partial API failures', async () => {
      vi.mocked(jobsApi.list).mockResolvedValue(mockJobs)
      vi.mocked(resumesApi.list).mockRejectedValue(new Error('API Error'))
      vi.mocked(coverLettersApi.list).mockResolvedValue(mockCoverLetters)
      vi.mocked(jobsApi.getStats).mockResolvedValue(mockJobStats)

      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      await waitFor(() => {
        const activePipelineCard = screen.getByText('Active pipeline').closest('a')
        expect(within(activePipelineCard!).getByText('3')).toBeInTheDocument()
      })

      await waitFor(() => {
        const resumeAverageCard = screen.getByText('Resume average').closest('a')
        expect(within(resumeAverageCard!).getByText('No score')).toBeInTheDocument()
      })
    })
  })

  describe('Date Formatting', () => {
    it('should display relative date text for applications', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      // Just verify that the date formatting function produces some output
      // The exact format depends on current date, so we just verify structure
      await waitFor(() => {
        // Check that the recent applications section loads
        expect(screen.getByText('Recent applications')).toBeInTheDocument()
      })

      // Applications have date text rendered (Today, Yesterday, Xd ago, or MMM DD)
      // We check for the Clock icon which accompanies date text
      await waitFor(() => {
        const clockIcons = document.querySelectorAll('.lucide-clock-3')
        expect(clockIcons.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper heading structure on landing page', () => {
      renderHomePage({ user: null, isLoading: false })

      const h1 = screen.getByRole('heading', { level: 1 })
      expect(h1).toBeInTheDocument()
    })

    it('should have proper heading structure on dashboard', () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      const h1 = screen.getByRole('heading', { level: 1 })
      expect(h1).toHaveTextContent(/welcome back/i)
    })

    it('should have accessible status badges', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      // Wait for the applications to load and render status badges
      await waitFor(() => {
        const appliedBadges = screen.getAllByText('Applied')
        expect(appliedBadges.length).toBeGreaterThan(0)
      })
    })

    it('should not introduce a blocking loading status on the public landing page', () => {
      renderHomePage({ isLoading: true })

      expect(screen.queryByRole('status')).not.toBeInTheDocument()
      expect(screen.getByRole('main')).toHaveAttribute('id', 'main-content')
    })
  })

  describe('API calls', () => {
    it('should fetch data when authenticated', async () => {
      renderHomePage({ user: mockUser, isAuthenticated: true, isLoading: false })

      // API calls are made in useEffect, so we need to wait for them
      await waitFor(() => {
        expect(resumesApi.list).toHaveBeenCalled()
      })

      expect(jobsApi.list).toHaveBeenCalled()
      expect(coverLettersApi.list).toHaveBeenCalled()
      expect(jobsApi.getStats).toHaveBeenCalled()
    })

    it('should not fetch data without authentication', () => {
      renderHomePage({ user: mockUser, isAuthenticated: false, isLoading: false })

      // API calls should not be made synchronously when there are no tokens
      expect(resumesApi.list).not.toHaveBeenCalled()
      expect(jobsApi.list).not.toHaveBeenCalled()
    })

    it('should not fetch data for unauthenticated users', () => {
      renderHomePage({ user: null, isAuthenticated: false, isLoading: false })

      // API calls should not be made for unauthenticated users
      expect(resumesApi.list).not.toHaveBeenCalled()
      expect(jobsApi.list).not.toHaveBeenCalled()
    })
  })
})
