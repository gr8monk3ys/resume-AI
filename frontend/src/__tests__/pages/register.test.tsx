import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import RegisterPage from '@/app/register/page'
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
  usePathname: () => '/register',
  useSearchParams: () => new URLSearchParams(),
}))

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

/**
 * Helper to render register page with auth context
 */
function renderRegisterPage(authContextOverrides: Partial<AuthContextType> = {}) {
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
        <RegisterPage />
      </AuthContext.Provider>
    ),
    mockRegister: defaultContext.register,
  }
}

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render registration form', () => {
      renderRegisterPage()

      expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument()
      expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^username$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    })

    it('should render link to login page', () => {
      renderRegisterPage()

      const loginLink = screen.getByRole('link', { name: /sign in/i })
      expect(loginLink).toBeInTheDocument()
      expect(loginLink).toHaveAttribute('href', '/login')
    })

    it('should show optional label for full name', () => {
      renderRegisterPage()

      expect(screen.getByText(/\(optional\)/i)).toBeInTheDocument()
    })

    it('should show loading spinner when auth is loading', () => {
      renderRegisterPage({ isLoading: true })

      expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument()
      expect(screen.queryByLabelText(/username/i)).not.toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('should show error when username is empty', async () => {
      const user = userEvent.setup()
      const { mockRegister } = renderRegisterPage()

      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/username is required/i)).toBeInTheDocument()
      })

      expect(mockRegister).not.toHaveBeenCalled()
    })

    it('should show error when username is too short', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'ab')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/username must be at least 3 characters/i)).toBeInTheDocument()
      })
    })

    it('should show error when username contains invalid characters', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'user@name')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/username can only contain letters, numbers, and underscores/i)).toBeInTheDocument()
      })
    })

    it('should show error when email is empty', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      })
    })

    it('should show error when email is invalid', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'invalid-email')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument()
      })
    })

    it('should show error when password is empty', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      })
    })

    it('should show error when password is too short', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), '12345')
      await user.type(screen.getByLabelText(/confirm password/i), '12345')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/password must be at least 6 characters/i)).toBeInTheDocument()
      })
    })

    it('should show error when passwords do not match', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'differentpassword')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
      })
    })

    it('should show error when confirm password is empty', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/please confirm your password/i)).toBeInTheDocument()
      })
    })
  })

  describe('Password Strength', () => {
    it('should show password strength indicator', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      const passwordInput = screen.getByLabelText(/^password$/i)

      // Focus and type to trigger requirements display
      await user.click(passwordInput)
      await user.type(passwordInput, 'pass')

      await waitFor(() => {
        expect(screen.getByText(/password strength/i)).toBeInTheDocument()
      })
    })

    it('should show password requirements on focus', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      const passwordInput = screen.getByLabelText(/^password$/i)
      await user.click(passwordInput)
      await user.type(passwordInput, 'test')

      await waitFor(() => {
        expect(screen.getByText(/password requirements/i)).toBeInTheDocument()
        expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument()
        expect(screen.getByText(/contains uppercase letter/i)).toBeInTheDocument()
        expect(screen.getByText(/contains lowercase letter/i)).toBeInTheDocument()
        expect(screen.getByText(/contains a number/i)).toBeInTheDocument()
        expect(screen.getByText(/contains special character/i)).toBeInTheDocument()
      })
    })

    it('should indicate weak password', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.click(screen.getByLabelText(/^password$/i))
      await user.type(screen.getByLabelText(/^password$/i), 'abc')

      await waitFor(() => {
        expect(screen.getByText(/weak/i)).toBeInTheDocument()
      })
    })

    it('should indicate strong password', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.click(screen.getByLabelText(/^password$/i))
      await user.type(screen.getByLabelText(/^password$/i), 'StrongP@ss123')

      await waitFor(() => {
        expect(screen.getByText(/strong/i)).toBeInTheDocument()
      })
    })

    it('should show password match indicator', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')

      await waitFor(() => {
        expect(screen.getByText(/passwords match/i)).toBeInTheDocument()
      })
    })

    it('should show password mismatch indicator', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password456')

      await waitFor(() => {
        expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
      })
    })
  })

  describe('Form Submission', () => {
    it('should call register with correct data', async () => {
      const user = userEvent.setup()
      const mockRegister = vi.fn().mockResolvedValue(undefined)
      renderRegisterPage({ register: mockRegister })

      await user.type(screen.getByLabelText(/full name/i), 'Test User')
      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith({
          username: 'testuser',
          email: 'test@example.com',
          password: 'password123',
          full_name: 'Test User',
        })
      })
    })

    it('should not include full_name if empty', async () => {
      const user = userEvent.setup()
      const mockRegister = vi.fn().mockResolvedValue(undefined)
      renderRegisterPage({ register: mockRegister })

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith({
          username: 'testuser',
          email: 'test@example.com',
          password: 'password123',
          full_name: undefined,
        })
      })
    })

    it('should show loading state during submission', async () => {
      const user = userEvent.setup()
      const mockRegister = vi.fn().mockImplementation(() => new Promise(() => {}))
      renderRegisterPage({ register: mockRegister })

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      expect(screen.getByText(/creating account/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /creating account/i })).toBeDisabled()
    })

    it('should disable form fields during submission', async () => {
      const user = userEvent.setup()
      const mockRegister = vi.fn().mockImplementation(() => new Promise(() => {}))
      renderRegisterPage({ register: mockRegister })

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      expect(screen.getByLabelText(/full name/i)).toBeDisabled()
      expect(screen.getByLabelText(/^username$/i)).toBeDisabled()
      expect(screen.getByLabelText(/^email$/i)).toBeDisabled()
      expect(screen.getByLabelText(/^password$/i)).toBeDisabled()
      expect(screen.getByLabelText(/confirm password/i)).toBeDisabled()
    })
  })

  describe('Error Handling', () => {
    it('should show error when username is taken', async () => {
      const user = userEvent.setup()
      const mockRegister = vi.fn().mockRejectedValue(new ApiError('Username already exists', 400))
      renderRegisterPage({ register: mockRegister })

      await user.type(screen.getByLabelText(/^username$/i), 'existinguser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/username already exists/i)).toBeInTheDocument()
      })
    })

    it('should show error when email is taken', async () => {
      const user = userEvent.setup()
      const mockRegister = vi.fn().mockRejectedValue(new ApiError('Email already registered', 400))
      renderRegisterPage({ register: mockRegister })

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'existing@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/email already registered/i)).toBeInTheDocument()
      })
    })

    it('should show generic error for unexpected failures', async () => {
      const user = userEvent.setup()
      const mockRegister = vi.fn().mockRejectedValue(new Error('Network error'))
      renderRegisterPage({ register: mockRegister })

      await user.type(screen.getByLabelText(/^username$/i), 'testuser')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/unexpected error/i)
      })
    })

    it('should clear field errors when typing', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      // Submit with short username
      await user.type(screen.getByLabelText(/^username$/i), 'ab')
      await user.type(screen.getByLabelText(/^email$/i), 'test@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'password123')
      await user.type(screen.getByLabelText(/confirm password/i), 'password123')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/username must be at least 3 characters/i)).toBeInTheDocument()
      })

      // Start typing in username field - error should clear
      await user.type(screen.getByLabelText(/^username$/i), 'c')

      await waitFor(() => {
        expect(screen.queryByText(/username must be at least 3 characters/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Password Visibility', () => {
    it('should toggle password visibility', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      const passwordInput = screen.getByLabelText(/^password$/i)
      const toggleButtons = screen.getAllByRole('button', { name: /show password/i })

      expect(passwordInput).toHaveAttribute('type', 'password')

      await user.click(toggleButtons[0]!)
      expect(passwordInput).toHaveAttribute('type', 'text')

      await user.click(screen.getAllByRole('button', { name: /hide password/i })[0]!)
      expect(passwordInput).toHaveAttribute('type', 'password')
    })

    it('should toggle confirm password visibility independently', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      const confirmPasswordInput = screen.getByLabelText(/confirm password/i)
      const toggleButtons = screen.getAllByRole('button', { name: /show password/i })

      expect(confirmPasswordInput).toHaveAttribute('type', 'password')

      // Toggle confirm password (second toggle button)
      await user.click(toggleButtons[1]!)
      expect(confirmPasswordInput).toHaveAttribute('type', 'text')
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

      renderRegisterPage({ user: mockUser, isLoading: false })

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/')
      })
    })
  })

  describe('Accessibility', () => {
    it('should have accessible form labels', () => {
      renderRegisterPage()

      expect(screen.getByLabelText(/full name/i)).toHaveAccessibleName()
      expect(screen.getByLabelText(/^username$/i)).toHaveAccessibleName()
      expect(screen.getByLabelText(/^email$/i)).toHaveAccessibleName()
      expect(screen.getByLabelText(/^password$/i)).toHaveAccessibleName()
      expect(screen.getByLabelText(/confirm password/i)).toHaveAccessibleName()
    })

    it('should mark invalid fields with aria-invalid', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'ab')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByLabelText(/^username$/i)).toHaveAttribute('aria-invalid', 'true')
      })
    })

    it('should have proper aria-describedby for error messages', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/^username$/i), 'ab')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        const usernameInput = screen.getByLabelText(/^username$/i)
        expect(usernameInput).toHaveAttribute('aria-describedby', 'username-error')
      })
    })
  })
})
