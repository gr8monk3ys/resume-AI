'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { ApiError } from '@/lib/api'
import { Eye, EyeOff, AlertCircle, Info, LogIn } from 'lucide-react'

/**
 * Check if demo credentials should be shown
 * Controlled via NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS environment variable
 */
function shouldShowDemoCredentials(): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  const envValue = process.env.NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS
  return envValue === 'true' || envValue === '1'
}

/**
 * Demo credentials configuration
 */
const DEMO_CREDENTIALS = {
  username: 'demo',
  password: 'demo123',
}

/**
 * Login page component
 * Handles user authentication with form validation and error handling
 */
export default function LoginPage() {
  const router = useRouter()
  const { login, user, isLoading: authLoading } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showDemoCredentials, setShowDemoCredentials] = useState(false)

  // Check if demo credentials should be shown on mount
  useEffect(() => {
    setShowDemoCredentials(shouldShowDemoCredentials())
  }, [])

  // Redirect if already authenticated
  useEffect(() => {
    if (user && !authLoading) {
      router.push('/')
    }
  }, [user, authLoading, router])

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Basic validation
    if (!username.trim()) {
      setError('Username is required')
      return
    }

    if (!password) {
      setError('Password is required')
      return
    }

    setIsSubmitting(true)

    try {
      await login(username.trim(), password)
      // Redirect is handled by AuthProvider
    } catch (err) {
      if (err instanceof ApiError) {
        // Handle specific error cases
        if (err.status === 401) {
          setError('Invalid username or password')
        } else if (err.status === 429) {
          setError('Too many login attempts. Please try again later.')
        } else {
          setError(err.message || 'Login failed. Please try again.')
        }
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  /**
   * Fill in demo credentials
   */
  const fillDemoCredentials = () => {
    setUsername(DEMO_CREDENTIALS.username)
    setPassword(DEMO_CREDENTIALS.password)
    setError('')
  }

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div
        className="min-h-[80vh] flex items-center justify-center"
        role="status"
        aria-label="Loading"
      >
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">
            Sign in to your account
          </h1>
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

        {/* Demo Credentials Notice */}
        {showDemoCredentials && (
          <div
            className="bg-blue-50 border border-blue-200 rounded-lg p-4"
            role="note"
            aria-label="Demo account information"
          >
            <div className="flex items-start">
              <Info
                className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0"
                aria-hidden="true"
              />
              <div className="ml-3">
                <h2 className="text-sm font-medium text-blue-800">
                  Demo Account Available
                </h2>
                <p className="mt-1 text-sm text-blue-700">
                  Try the app with our demo account:
                </p>
                <div className="mt-2 text-sm text-blue-700">
                  <p>
                    <strong>Username:</strong> {DEMO_CREDENTIALS.username}
                  </p>
                  <p>
                    <strong>Password:</strong> {DEMO_CREDENTIALS.password}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={fillDemoCredentials}
                  className="mt-3 inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  Use Demo Credentials
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Login Form */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit} noValidate>
          {/* Error Message */}
          {error && (
            <div
              className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start"
              role="alert"
              aria-live="polite"
            >
              <AlertCircle
                className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0"
                aria-hidden="true"
              />
              <p className="ml-3 text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            {/* Username Field */}
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-gray-700"
              >
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isSubmitting}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
                placeholder="Enter your username"
                aria-describedby={error ? 'login-error' : undefined}
              />
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700"
              >
                Password
              </label>
              <div className="mt-1 relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  className="block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
                  placeholder="Enter your password"
                  aria-describedby={error ? 'login-error' : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" aria-hidden="true" />
                  ) : (
                    <Eye className="w-5 h-5" aria-hidden="true" />
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex items-center justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? (
              <>
                <span
                  className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"
                  aria-hidden="true"
                />
                Signing in...
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4 mr-2" aria-hidden="true" />
                Sign in
              </>
            )}
          </button>
        </form>

        {/* Footer Links */}
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
