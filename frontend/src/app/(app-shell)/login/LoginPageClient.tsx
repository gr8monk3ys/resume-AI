'use client'

import { AlertCircle, Eye, EyeOff, Info, LogIn } from 'lucide-react'
import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'

interface DemoCredentials {
  username: string
  password: string
}

interface LoginFormState {
  username: string
  password: string
  showPassword: boolean
  error: string
  isSubmitting: boolean
}

interface DemoState {
  showDemoCredentials: boolean
  demoCredentials: DemoCredentials | null
}

const INITIAL_LOGIN_FORM_STATE: LoginFormState = {
  username: '',
  password: '',
  showPassword: false,
  error: '',
  isSubmitting: false,
}

const INITIAL_DEMO_STATE: DemoState = {
  showDemoCredentials: false,
  demoCredentials: null,
}

function shouldShowDemoCredentials(): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  const envValue = process.env.NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS
  return envValue === 'true' || envValue === '1'
}

function getDemoCredentials(): DemoCredentials | null {
  const username = process.env.NEXT_PUBLIC_DEMO_USERNAME
  const password = process.env.NEXT_PUBLIC_DEMO_PASSWORD

  if (username && password) {
    return { username, password }
  }

  return null
}

function PageLoadingState() {
  return (
    <div
      className="flex min-h-[80vh] items-center justify-center"
      role="status"
      aria-label="Loading"
    >
      <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-[var(--accent)]" />
    </div>
  )
}

function DemoCredentialsNotice({
  demoCredentials,
  onUseDemoCredentials,
}: {
  demoCredentials: DemoCredentials
  onUseDemoCredentials: () => void
}) {
  return (
    <div
      className="glass-alert glass-alert-info"
      role="note"
      aria-label="Demo account information"
    >
      <Info
        className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--status-info-text)]"
        aria-hidden="true"
      />
      <div>
        <h2 className="text-sm font-medium text-[var(--status-info-text)]">Demo Account Available</h2>
        <p className="mt-1 text-sm text-[var(--status-info-text)]">
          Try the app with our demo account:
        </p>
        <div className="mt-2 text-sm text-[var(--status-info-text)]">
          <p>
            <strong>Username:</strong> {demoCredentials.username}
          </p>
          <p>
            <strong>Password:</strong> {demoCredentials.password}
          </p>
        </div>
        <button
          type="button"
          onClick={onUseDemoCredentials}
          className="glass-button-secondary mt-3 px-3 py-1.5 text-sm"
        >
          Use Demo Credentials
        </button>
      </div>
    </div>
  )
}

function useLoginPageController() {
  const { login, user, isLoading: authLoading } = useAuth()
  const [formState, setFormState] = useState<LoginFormState>(INITIAL_LOGIN_FORM_STATE)
  const [demoState, setDemoState] = useState<DemoState>(INITIAL_DEMO_STATE)
  const { showDemoCredentials, demoCredentials } = demoState
  const { username, password, showPassword, error, isSubmitting } = formState

  useEffect(() => {
    const credentials = getDemoCredentials()
    setDemoState({
      showDemoCredentials: shouldShowDemoCredentials() && credentials !== null,
      demoCredentials: credentials,
    })
  }, [])

  const setFieldValue = useCallback(
    (field: keyof Pick<LoginFormState, 'username' | 'password'>, value: string) => {
      setFormState((prev) => ({ ...prev, [field]: value }))
    },
    []
  )

  const togglePasswordVisibility = useCallback(() => {
    setFormState((prev) => ({ ...prev, showPassword: !prev.showPassword }))
  }, [])

  const handleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault()

      const trimmedUsername = username.trim()
      if (!trimmedUsername) {
        setFormState((prev) => ({ ...prev, error: 'Username is required' }))
        return
      }

      if (!password) {
        setFormState((prev) => ({ ...prev, error: 'Password is required' }))
        return
      }

      setFormState((prev) => ({
        ...prev,
        error: '',
        isSubmitting: true,
      }))

      try {
        await login(trimmedUsername, password)
      } catch (submissionError) {
        let nextError = 'An unexpected error occurred. Please try again.'

        if (submissionError instanceof ApiError) {
          if (submissionError.status === 401) {
            nextError = 'Invalid username or password'
          } else if (submissionError.status === 429) {
            nextError = 'Too many login attempts. Please try again later.'
          } else {
            nextError = submissionError.message || 'Login failed. Please try again.'
          }
        }

        setFormState((prev) => ({
          ...prev,
          error: nextError,
          isSubmitting: false,
        }))
        return
      }

      setFormState((prev) => ({ ...prev, isSubmitting: false }))
    },
    [login, password, username]
  )

  const fillDemoCredentials = useCallback(() => {
    if (!demoCredentials) {
      return
    }

    setFormState((prev) => ({
      ...prev,
      username: demoCredentials.username,
      password: demoCredentials.password,
      error: '',
    }))
  }, [demoCredentials])

  return {
    user,
    authLoading,
    username,
    password,
    showPassword,
    error,
    isSubmitting,
    showDemoCredentials,
    demoCredentials,
    setFieldValue,
    togglePasswordVisibility,
    handleSubmit,
    fillDemoCredentials,
  }
}

export function LoginPageClient() {
  const controller = useLoginPageController()

  if (controller.authLoading) {
    return <PageLoadingState />
  }

  if (controller.user) {
    return null
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <div className="surface-card-strong w-full max-w-[28rem] space-y-8 p-8 sm:p-10">
        <div className="text-center">
          <h1 className="font-display text-3xl font-bold tracking-[-0.03em] text-[var(--ink)]">Sign in to your account</h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Or{' '}
            <Link
              href="/register"
              className="font-medium text-[var(--accent)] hover:text-[var(--accent-strong)] focus:outline-none focus:underline"
            >
              create a new account
            </Link>
          </p>
        </div>

        {controller.showDemoCredentials && controller.demoCredentials && (
          <DemoCredentialsNotice
            demoCredentials={controller.demoCredentials}
            onUseDemoCredentials={controller.fillDemoCredentials}
          />
        )}

        <form
          className="mt-8 space-y-6"
          onSubmit={(event) => {
            void controller.handleSubmit(event)
          }}
          noValidate
        >
          {controller.error && (
            <div
              className="glass-alert glass-alert-error"
              role="alert"
              aria-live="polite"
            >
              <AlertCircle
                className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--status-error-text)]"
                aria-hidden="true"
              />
              <p id="login-error" className="text-sm text-[var(--status-error-text)]">
                {controller.error}
              </p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="glass-label">
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                value={controller.username}
                onChange={(event) => controller.setFieldValue('username', event.target.value)}
                disabled={controller.isSubmitting}
                className="mt-1 glass-input"
                placeholder="Enter your username"
                aria-describedby={controller.error ? 'login-error' : undefined}
              />
            </div>

            <div>
              <label htmlFor="password" className="glass-label">
                Password
              </label>
              <div className="relative mt-1">
                <input
                  id="password"
                  name="password"
                  type={controller.showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={controller.password}
                  onChange={(event) => controller.setFieldValue('password', event.target.value)}
                  disabled={controller.isSubmitting}
                  className="glass-input pr-10"
                  placeholder="Enter your password"
                  aria-describedby={controller.error ? 'login-error' : undefined}
                />
                <button
                  type="button"
                  onClick={controller.togglePasswordVisibility}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-[var(--muted-soft)] hover:text-[var(--muted)] focus:outline-none"
                  aria-label={controller.showPassword ? 'Hide password' : 'Show password'}
                >
                  {controller.showPassword ? (
                    <EyeOff className="h-5 w-5" aria-hidden="true" />
                  ) : (
                    <Eye className="h-5 w-5" aria-hidden="true" />
                  )}
                </button>
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={controller.isSubmitting}
            className="glass-button-primary w-full"
          >
            {controller.isSubmitting ? (
              <>
                <span
                  className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-[var(--accent)]"
                  aria-hidden="true"
                />
                Signing in...
              </>
            ) : (
              <>
                <LogIn className="mr-2 h-4 w-4" aria-hidden="true" />
                Sign in
              </>
            )}
          </button>
        </form>

        <div className="text-center text-sm text-[var(--muted)]">
          <p>
            By signing in, you agree to our{' '}
            <Link
              href="/terms"
              className="text-[var(--accent)] hover:text-[var(--accent-strong)] focus:outline-none focus:underline"
            >
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link
              href="/privacy"
              className="text-[var(--accent)] hover:text-[var(--accent-strong)] focus:outline-none focus:underline"
            >
              Privacy Policy
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
