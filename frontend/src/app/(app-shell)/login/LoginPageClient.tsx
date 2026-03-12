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
      <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary-600" />
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
      className="rounded-lg border border-blue-200 bg-blue-50 p-4"
      role="note"
      aria-label="Demo account information"
    >
      <div className="flex items-start">
        <Info
          className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-500"
          aria-hidden="true"
        />
        <div className="ml-3">
          <h2 className="text-sm font-medium text-blue-800">Demo Account Available</h2>
          <p className="mt-1 text-sm text-blue-700">
            Try the app with our demo account:
          </p>
          <div className="mt-2 text-sm text-blue-700">
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
            className="mt-3 inline-flex items-center rounded-md bg-blue-100 px-3 py-1.5 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Use Demo Credentials
          </button>
        </div>
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
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">Sign in to your account</h1>
          <p className="mt-2 text-sm text-gray-600">
            Or{' '}
            <Link
              href="/register"
              className="font-medium text-primary-600 hover:text-primary-500 focus:outline-none focus:underline"
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
              className="flex items-start rounded-lg border border-red-200 bg-red-50 p-4"
              role="alert"
              aria-live="polite"
            >
              <AlertCircle
                className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500"
                aria-hidden="true"
              />
              <p id="login-error" className="ml-3 text-sm text-red-700">
                {controller.error}
              </p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">
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
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm transition-colors placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100"
                placeholder="Enter your username"
                aria-describedby={controller.error ? 'login-error' : undefined}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
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
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm transition-colors placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100"
                  placeholder="Enter your password"
                  aria-describedby={controller.error ? 'login-error' : undefined}
                />
                <button
                  type="button"
                  onClick={controller.togglePasswordVisibility}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none"
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
            className="flex w-full items-center justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {controller.isSubmitting ? (
              <>
                <span
                  className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white"
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

        <div className="text-center text-sm text-gray-500">
          <p>
            By signing in, you agree to our{' '}
            <Link
              href="/terms"
              className="text-primary-600 hover:text-primary-500 focus:outline-none focus:underline"
            >
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link
              href="/privacy"
              className="text-primary-600 hover:text-primary-500 focus:outline-none focus:underline"
            >
              Privacy Policy
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
