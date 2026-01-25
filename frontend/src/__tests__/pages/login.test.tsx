import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import LoginPage from '@/app/login/page'
import { ApiError } from '@/lib/api'
import { AuthContext, AuthContextType } from '@/lib/auth'

// Mock next/navigation
const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/login',
  useSearchParams: () => new URLSearchParams(),
}))

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

/**
 * Helper to render login page with auth context
 */
function renderLoginPage(authContextOverrides: Partial<AuthContextType> = {}) {
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

  return {
    ...render(
      <AuthContext.Provider value={defaultContext}>
        <LoginPage />
      </AuthContext.Provider>
    ),
    mockLogin: defaultContext.login,
  }
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render login form', () => {
      renderLoginPage()

      expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument()
      expect(screen.getByLabelText('Username')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('should render link to register page', () => {
      renderLoginPage()

      const registerLink = screen.getByRole('link', { name: /create a new account/i })
      expect(registerLink).toBeInTheDocument()
      expect(registerLink).toHaveAttribute('href', '/register')
    })

    it('should render terms and privacy links', () => {
      renderLoginPage()

      expect(screen.getByRole('link', { name: /terms of service/i })).toHaveAttribute('href', '/terms')
      expect(screen.getByRole('link', { name: /privacy policy/i })).toHaveAttribute('href', '/privacy')
    })

    it('should show loading spinner when auth is loading', () => {
      renderLoginPage({ isLoading: true })

      expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument()
      expect(screen.queryByLabelText(/username/i)).not.toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('should show error when username is empty', async () => {
      const user = userEvent.setup()
      const { mockLogin } = renderLoginPage()

      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/username is required/i)
      })

      expect(mockLogin).not.toHaveBeenCalled()
    })

    it('should show error when password is empty', async () => {
      const user = userEvent.setup()
      const { mockLogin } = renderLoginPage()

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/password is required/i)
      })

      expect(mockLogin).not.toHaveBeenCalled()
    })

    it('should trim whitespace from username', async () => {
      const user = userEvent.setup()
      const mockLogin = vi.fn().mockResolvedValue(undefined)
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), '  testuser  ')
      await user.type(screen.getByLabelText('Password'), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123')
      })
    })
  })

  describe('Form Submission', () => {
    it('should call login with correct credentials', async () => {
      const user = userEvent.setup()
      const mockLogin = vi.fn().mockResolvedValue(undefined)
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123')
      })
    })

    it('should show loading state during submission', async () => {
      const user = userEvent.setup()
      // Create a promise that we can control
      let resolveLogin: () => void
      const loginPromise = new Promise<void>((resolve) => {
        resolveLogin = resolve
      })
      const mockLogin = vi.fn().mockReturnValue(loginPromise)
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      // Should show loading state - button should contain "Signing in..."
      const submitButton = screen.getByRole('button', { name: /signing in/i })
      expect(submitButton).toBeInTheDocument()
      expect(submitButton).toBeDisabled()
      expect(screen.getByLabelText('Username')).toBeDisabled()
      expect(screen.getByLabelText('Password')).toBeDisabled()

      // Resolve the login promise
      resolveLogin!()
    })

    it('should disable form fields during submission', async () => {
      const user = userEvent.setup()
      const mockLogin = vi.fn().mockImplementation(() => new Promise(() => {}))
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      expect(screen.getByLabelText('Username')).toBeDisabled()
      expect(screen.getByLabelText('Password')).toBeDisabled()
    })
  })

  describe('Error Handling', () => {
    it('should show error message for invalid credentials', async () => {
      const user = userEvent.setup()
      const mockLogin = vi.fn().mockRejectedValue(new ApiError('Invalid credentials', 401))
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'wrongpassword')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/invalid username or password/i)
      })
    })

    it('should show rate limit error', async () => {
      const user = userEvent.setup()
      const mockLogin = vi.fn().mockRejectedValue(new ApiError('Too many attempts', 429))
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/too many login attempts/i)
      })
    })

    it('should show generic error for unexpected errors', async () => {
      const user = userEvent.setup()
      const mockLogin = vi.fn().mockRejectedValue(new Error('Network error'))
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/unexpected error/i)
      })
    })

    it('should clear error when form is resubmitted', async () => {
      const user = userEvent.setup()
      let callCount = 0
      const mockLogin = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.reject(new ApiError('Invalid credentials', 401))
        }
        return Promise.resolve()
      })
      renderLoginPage({ login: mockLogin })

      // First submission - should fail
      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'wrongpassword')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      // Second submission - error should be cleared during submission
      await user.clear(screen.getByLabelText('Password'))
      await user.type(screen.getByLabelText('Password'), 'correctpassword')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        expect(screen.queryByRole('alert')).not.toBeInTheDocument()
      })
    })
  })

  describe('Password Visibility', () => {
    it('should toggle password visibility', async () => {
      const user = userEvent.setup()
      renderLoginPage()

      const passwordInput = screen.getByLabelText('Password')
      const toggleButton = screen.getByRole('button', { name: /show password/i })

      // Initially password should be hidden
      expect(passwordInput).toHaveAttribute('type', 'password')

      // Click to show password
      await user.click(toggleButton)
      expect(passwordInput).toHaveAttribute('type', 'text')

      // Click to hide password again
      await user.click(screen.getByRole('button', { name: /hide password/i }))
      expect(passwordInput).toHaveAttribute('type', 'password')
    })
  })

  describe('Authentication Redirect', () => {
    it('should redirect authenticated users to home', async () => {
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

      renderLoginPage({ user: mockUser, isLoading: false })

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/')
      })
    })
  })

  describe('Accessibility', () => {
    it('should have accessible form labels', () => {
      renderLoginPage()

      const usernameInput = screen.getByLabelText('Username')
      const passwordInput = screen.getByLabelText('Password')

      expect(usernameInput).toHaveAccessibleName()
      expect(passwordInput).toHaveAccessibleName()
    })

    it('should have accessible error messages', async () => {
      const user = userEvent.setup()
      renderLoginPage()

      await user.click(screen.getByRole('button', { name: /sign in/i }))

      await waitFor(() => {
        const alert = screen.getByRole('alert')
        expect(alert).toBeInTheDocument()
        expect(alert).toHaveAttribute('aria-live', 'polite')
      })
    })

    it('should have accessible submit button during loading', async () => {
      const user = userEvent.setup()
      const mockLogin = vi.fn().mockImplementation(() => new Promise(() => {}))
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'password123')
      await user.click(screen.getByRole('button', { name: /sign in/i }))

      const button = screen.getByRole('button', { name: /signing in/i })
      expect(button).toBeDisabled()
    })
  })

  describe('Keyboard Navigation', () => {
    it('should submit form on Enter key', async () => {
      const user = userEvent.setup()
      const mockLogin = vi.fn().mockResolvedValue(undefined)
      renderLoginPage({ login: mockLogin })

      await user.type(screen.getByLabelText('Username'), 'testuser')
      await user.type(screen.getByLabelText('Password'), 'password123{enter}')

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123')
      })
    })
  })
})
