import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { AuthProvider } from '@/components/AuthProvider'
import { authApi, ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'

// Mock the API module
vi.mock('@/lib/api', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.name = 'ApiError'
      this.status = status
    }
  },
}))

// Mock next/navigation
const mockPush = vi.fn()
const mockPathname = vi.fn(() => '/')

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => mockPathname(),
  useSearchParams: () => new URLSearchParams(),
}))

/**
 * Test component that consumes auth context
 */
function TestConsumer() {
  const { user, isLoading, authError, login, logout, register } = useAuth()

  if (isLoading) {
    return <div data-testid="loading">Loading...</div>
  }

  return (
    <div>
      <div data-testid="user-status">
        {user ? `Logged in as ${user.username}` : 'Not logged in'}
      </div>
      {authError && <div data-testid="auth-error">{authError}</div>}
      <button
        data-testid="login-btn"
        onClick={() => {
          login('testuser', 'password123').catch(console.error)
        }}
      >
        Login
      </button>
      <button data-testid="logout-btn" onClick={() => void logout()}>
        Logout
      </button>
      <button
        data-testid="register-btn"
        onClick={() => {
          register({
            username: 'newuser',
            email: 'new@example.com',
            password: 'password123',
          }).catch(console.error)
        }}
      >
        Register
      </button>
    </div>
  )
}

describe('AuthProvider', () => {
  const mockUser = {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    full_name: 'Test User',
    is_active: true,
    is_admin: false,
    created_at: '2024-01-01T00:00:00Z',
    last_login: null,
  }

  const mockTokens = {
    access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxOTk5OTk5OTk5fQ.test',
    refresh_token: 'mock-refresh-token',
    token_type: 'bearer',
  }

  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks()
    mockPush.mockClear()
    mockPathname.mockReturnValue('/')

    // Note: localStorage and sessionStorage are reset in vitest.setup.tsx
  })

  describe('Initial State', () => {
    it('should eventually show user status after loading', async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      // The component may show loading briefly, then resolves
      // Wait for the user status to appear (loading is complete)
      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toBeInTheDocument()
      })
    })

    it('should show not logged in when no stored tokens', async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent('Not logged in')
      })
    })

    it('should restore session from stored tokens', async () => {
      // Set up stored tokens
      localStorage.setItem('access_token', mockTokens.access_token)
      localStorage.setItem('refresh_token', mockTokens.refresh_token)
      localStorage.setItem('token_type', 'bearer')

      vi.mocked(authApi.me).mockResolvedValue(mockUser)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent(
          'Logged in as testuser'
        )
      })

      expect(authApi.me).toHaveBeenCalledWith(mockTokens.access_token)
    })
  })

  describe('Login', () => {
    it('should login successfully', async () => {
      const user = userEvent.setup()

      vi.mocked(authApi.login).mockResolvedValue(mockTokens)
      vi.mocked(authApi.me).mockResolvedValue(mockUser)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('login-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent(
          'Logged in as testuser'
        )
      })

      expect(authApi.login).toHaveBeenCalledWith('testuser', 'password123')
      expect(authApi.me).toHaveBeenCalledWith(mockTokens.access_token)
      expect(localStorage.getItem('access_token')).toBe(mockTokens.access_token)
      expect(mockPush).toHaveBeenCalledWith('/')
    })

    it('should handle login failure', async () => {
      const user = userEvent.setup()

      const apiError = new ApiError('Invalid credentials', 401)
      vi.mocked(authApi.login).mockRejectedValue(apiError)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('login-btn')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('login-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('auth-error')).toHaveTextContent(
          'Invalid credentials'
        )
      })

      expect(localStorage.getItem('access_token')).toBeNull()
    })

    it('should redirect to stored location after login', async () => {
      const user = userEvent.setup()
      sessionStorage.setItem('redirectAfterLogin', '/resumes')

      vi.mocked(authApi.login).mockResolvedValue(mockTokens)
      vi.mocked(authApi.me).mockResolvedValue(mockUser)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('login-btn')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('login-btn'))

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/resumes')
      })

      expect(sessionStorage.getItem('redirectAfterLogin')).toBeNull()
    })
  })

  describe('Logout', () => {
    it('should logout and clear state', async () => {
      const user = userEvent.setup()

      // Start with logged in state
      localStorage.setItem('access_token', mockTokens.access_token)
      localStorage.setItem('refresh_token', mockTokens.refresh_token)
      localStorage.setItem('token_type', 'bearer')

      vi.mocked(authApi.me).mockResolvedValue(mockUser)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent(
          'Logged in as testuser'
        )
      })

      await user.click(screen.getByTestId('logout-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent('Not logged in')
      })

      expect(localStorage.getItem('access_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })

  describe('Registration', () => {
    it('should register and auto-login', async () => {
      const user = userEvent.setup()

      vi.mocked(authApi.register).mockResolvedValue(mockUser)
      vi.mocked(authApi.login).mockResolvedValue(mockTokens)
      vi.mocked(authApi.me).mockResolvedValue(mockUser)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('register-btn')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('register-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent(
          'Logged in as testuser'
        )
      })

      expect(authApi.register).toHaveBeenCalledWith({
        username: 'newuser',
        email: 'new@example.com',
        password: 'password123',
      })
    })

    it('should handle registration failure', async () => {
      const user = userEvent.setup()

      const apiError = new ApiError('Username already exists', 400)
      vi.mocked(authApi.register).mockRejectedValue(apiError)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('register-btn')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('register-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('auth-error')).toHaveTextContent(
          'Username already exists'
        )
      })
    })
  })

  describe('Route Protection', () => {
    it('should redirect unauthenticated users from protected routes', async () => {
      mockPathname.mockReturnValue('/resumes')

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })

      expect(sessionStorage.getItem('redirectAfterLogin')).toBe('/resumes')
    })

    it('should redirect authenticated users from auth routes to home', async () => {
      mockPathname.mockReturnValue('/login')

      localStorage.setItem('access_token', mockTokens.access_token)
      localStorage.setItem('refresh_token', mockTokens.refresh_token)
      localStorage.setItem('token_type', 'bearer')

      vi.mocked(authApi.me).mockResolvedValue(mockUser)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent(
          'Logged in as testuser'
        )
      })

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/')
      })
    })

    it('should allow unauthenticated access to public routes', async () => {
      mockPathname.mockReturnValue('/')

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent('Not logged in')
      })

      // Should not redirect
      expect(mockPush).not.toHaveBeenCalled()
    })
  })

  describe('Token Refresh', () => {
    it('should refresh expired token on init', async () => {
      // Create an expired token
      const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.test'

      localStorage.setItem('access_token', expiredToken)
      localStorage.setItem('refresh_token', mockTokens.refresh_token)
      localStorage.setItem('token_type', 'bearer')

      vi.mocked(authApi.refresh).mockResolvedValue(mockTokens)
      vi.mocked(authApi.me).mockResolvedValue(mockUser)

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(authApi.refresh).toHaveBeenCalledWith(mockTokens.refresh_token)
      })

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent(
          'Logged in as testuser'
        )
      })
    })

    it('should logout when token refresh fails', async () => {
      const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.test'
      mockPathname.mockReturnValue('/resumes')

      localStorage.setItem('access_token', expiredToken)
      localStorage.setItem('refresh_token', mockTokens.refresh_token)
      localStorage.setItem('token_type', 'bearer')

      vi.mocked(authApi.refresh).mockRejectedValue(new Error('Refresh failed'))

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent('Not logged in')
      })

      expect(localStorage.getItem('access_token')).toBeNull()
      expect(mockPush).toHaveBeenCalledWith('/login')
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const user = userEvent.setup()

      vi.mocked(authApi.login).mockRejectedValue(new Error('Network error'))

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('login-btn')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('login-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('auth-error')).toHaveTextContent(
          'An unexpected error occurred'
        )
      })
    })

    it('should clear auth state when fetching user fails', async () => {
      localStorage.setItem('access_token', mockTokens.access_token)
      localStorage.setItem('refresh_token', mockTokens.refresh_token)
      localStorage.setItem('token_type', 'bearer')

      vi.mocked(authApi.me).mockRejectedValue(new Error('Failed to fetch user'))

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('user-status')).toHaveTextContent('Not logged in')
      })

      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })
})
