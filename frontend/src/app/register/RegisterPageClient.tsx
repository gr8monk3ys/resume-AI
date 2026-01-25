'use client'

import {
  Eye,
  EyeOff,
  AlertCircle,
  UserPlus,
  Check,
  X,
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState, useEffect, useMemo } from 'react'

import { ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'


/**
 * Password strength levels
 */
type PasswordStrength = 'weak' | 'fair' | 'good' | 'strong'

/**
 * Password requirement interface
 */
interface PasswordRequirement {
  label: string
  test: (password: string) => boolean
}

/**
 * Password requirements for validation
 */
const PASSWORD_REQUIREMENTS: PasswordRequirement[] = [
  {
    label: 'At least 8 characters',
    test: (password) => password.length >= 8,
  },
  {
    label: 'Contains uppercase letter',
    test: (password) => /[A-Z]/.test(password),
  },
  {
    label: 'Contains lowercase letter',
    test: (password) => /[a-z]/.test(password),
  },
  {
    label: 'Contains a number',
    test: (password) => /\d/.test(password),
  },
  {
    label: 'Contains special character',
    test: (password) => /[!@#$%^&*(),.?":{}|<>]/.test(password),
  },
]

/**
 * Minimum password length for form validation
 */
const MIN_PASSWORD_LENGTH = 6

/**
 * Calculate password strength based on requirements met
 * @param password - Password to evaluate
 * @returns Password strength level
 */
function calculatePasswordStrength(password: string): PasswordStrength {
  if (!password) return 'weak'

  const requirementsMet = PASSWORD_REQUIREMENTS.filter((req) =>
    req.test(password)
  ).length

  if (requirementsMet <= 1) return 'weak'
  if (requirementsMet <= 2) return 'fair'
  if (requirementsMet <= 4) return 'good'
  return 'strong'
}

/**
 * Get color class for password strength indicator
 * @param strength - Password strength level
 * @returns Tailwind color class
 */
function getStrengthColor(strength: PasswordStrength): string {
  const colors: Record<PasswordStrength, string> = {
    weak: 'bg-red-500',
    fair: 'bg-orange-500',
    good: 'bg-yellow-500',
    strong: 'bg-green-500',
  }
  return colors[strength]
}

/**
 * Get text color class for password strength label
 * @param strength - Password strength level
 * @returns Tailwind text color class
 */
function getStrengthTextColor(strength: PasswordStrength): string {
  const colors: Record<PasswordStrength, string> = {
    weak: 'text-red-600',
    fair: 'text-orange-600',
    good: 'text-yellow-600',
    strong: 'text-green-600',
  }
  return colors[strength]
}

/**
 * Get width class for password strength bar
 * @param strength - Password strength level
 * @returns Tailwind width class
 */
function getStrengthWidth(strength: PasswordStrength): string {
  const widths: Record<PasswordStrength, string> = {
    weak: 'w-1/4',
    fair: 'w-2/4',
    good: 'w-3/4',
    strong: 'w-full',
  }
  return widths[strength]
}

/**
 * Capitalize first letter of a string
 * @param str - String to capitalize
 * @returns Capitalized string
 */
function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

/**
 * Registration page component
 * Handles new user account creation with form validation
 */
export function RegisterPageClient() {
  const router = useRouter()
  const { register, user, isLoading: authLoading } = useAuth()
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showRequirements, setShowRequirements] = useState(false)

  // Calculate password strength
  const passwordStrength = useMemo(
    () => calculatePasswordStrength(formData.password),
    [formData.password]
  )

  // Check which requirements are met
  const requirementsMet = useMemo(
    () =>
      PASSWORD_REQUIREMENTS.map((req) => ({
        ...req,
        met: req.test(formData.password),
      })),
    [formData.password]
  )

  // Redirect if already authenticated
  useEffect(() => {
    if (user && !authLoading) {
      router.push('/')
    }
  }, [user, authLoading, router])

  /**
   * Handle input changes
   */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))

    // Clear field-specific error when user starts typing
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[name]
        return newErrors
      })
    }
  }

  /**
   * Validate form fields
   * @returns true if all fields are valid
   */
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    // Username validation
    if (!formData.username.trim()) {
      errors.username = 'Username is required'
    } else if (formData.username.length < 3) {
      errors.username = 'Username must be at least 3 characters'
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      errors.username = 'Username can only contain letters, numbers, and underscores'
    }

    // Email validation
    if (!formData.email.trim()) {
      errors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address'
    }

    // Password validation
    if (!formData.password) {
      errors.password = 'Password is required'
    } else if (formData.password.length < MIN_PASSWORD_LENGTH) {
      errors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters`
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      errors.confirmPassword = 'Please confirm your password'
    } else if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match'
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)

    try {
      await register({
        username: formData.username.trim(),
        email: formData.email.trim(),
        password: formData.password,
        full_name: formData.full_name.trim() || undefined,
      })
      // Redirect is handled by AuthProvider
    } catch (err) {
      if (err instanceof ApiError) {
        // Handle specific error cases
        if (err.message.toLowerCase().includes('username')) {
          setFieldErrors((prev) => ({ ...prev, username: err.message }))
        } else if (err.message.toLowerCase().includes('email')) {
          setFieldErrors((prev) => ({ ...prev, email: err.message }))
        } else {
          setError(err.message || 'Registration failed. Please try again.')
        }
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
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
            Create your account
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Already have an account?{' '}
            <Link
              href="/login"
              className="font-medium text-primary-600 hover:text-primary-500 focus:outline-none focus:underline"
            >
              Sign in
            </Link>
          </p>
        </div>

        {/* Registration Form */}
        <form className="mt-8 space-y-6" onSubmit={(e) => void handleSubmit(e)} noValidate>
          {/* General Error Message */}
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
            {/* Full Name Field (Optional) */}
            <div>
              <label
                htmlFor="full_name"
                className="block text-sm font-medium text-gray-700"
              >
                Full Name{' '}
                <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                autoComplete="name"
                value={formData.full_name}
                onChange={handleChange}
                disabled={isSubmitting}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
                placeholder="John Doe"
              />
            </div>

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
                value={formData.username}
                onChange={handleChange}
                disabled={isSubmitting}
                aria-invalid={!!fieldErrors.username}
                aria-describedby={fieldErrors.username ? 'username-error' : undefined}
                className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors ${
                  fieldErrors.username
                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="johndoe"
              />
              {fieldErrors.username && (
                <p
                  id="username-error"
                  className="mt-1 text-sm text-red-600"
                  role="alert"
                >
                  {fieldErrors.username}
                </p>
              )}
            </div>

            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700"
              >
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={handleChange}
                disabled={isSubmitting}
                aria-invalid={!!fieldErrors.email}
                aria-describedby={fieldErrors.email ? 'email-error' : undefined}
                className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors ${
                  fieldErrors.email
                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="john@example.com"
              />
              {fieldErrors.email && (
                <p
                  id="email-error"
                  className="mt-1 text-sm text-red-600"
                  role="alert"
                >
                  {fieldErrors.email}
                </p>
              )}
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
                  autoComplete="new-password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  onFocus={() => setShowRequirements(true)}
                  disabled={isSubmitting}
                  aria-invalid={!!fieldErrors.password}
                  aria-describedby={
                    fieldErrors.password
                      ? 'password-error'
                      : 'password-requirements'
                  }
                  className={`block w-full px-3 py-2 pr-10 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors ${
                    fieldErrors.password
                      ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300'
                  }`}
                  placeholder="Create a strong password"
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

              {fieldErrors.password && (
                <p
                  id="password-error"
                  className="mt-1 text-sm text-red-600"
                  role="alert"
                >
                  {fieldErrors.password}
                </p>
              )}

              {/* Password Strength Indicator */}
              {formData.password && (
                <div className="mt-2" aria-live="polite">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-500">
                      Password strength
                    </span>
                    <span
                      className={`text-xs font-medium ${getStrengthTextColor(
                        passwordStrength
                      )}`}
                    >
                      {capitalize(passwordStrength)}
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${getStrengthColor(
                        passwordStrength
                      )} ${getStrengthWidth(passwordStrength)}`}
                      role="progressbar"
                      aria-valuenow={
                        { weak: 25, fair: 50, good: 75, strong: 100 }[
                          passwordStrength
                        ]
                      }
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`Password strength: ${passwordStrength}`}
                    />
                  </div>
                </div>
              )}

              {/* Password Requirements */}
              {showRequirements && formData.password && (
                <div id="password-requirements" className="mt-3 space-y-1">
                  <p className="text-xs text-gray-500 mb-2">
                    Password requirements:
                  </p>
                  {requirementsMet.map((req, index) => (
                    <div
                      key={index}
                      className="flex items-center text-xs"
                    >
                      {req.met ? (
                        <Check
                          className="w-3.5 h-3.5 text-green-500 mr-2 flex-shrink-0"
                          aria-hidden="true"
                        />
                      ) : (
                        <X
                          className="w-3.5 h-3.5 text-gray-300 mr-2 flex-shrink-0"
                          aria-hidden="true"
                        />
                      )}
                      <span
                        className={req.met ? 'text-green-600' : 'text-gray-500'}
                      >
                        {req.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-gray-700"
              >
                Confirm Password
              </label>
              <div className="mt-1 relative">
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  disabled={isSubmitting}
                  aria-invalid={!!fieldErrors.confirmPassword}
                  aria-describedby={
                    fieldErrors.confirmPassword ? 'confirm-password-error' : undefined
                  }
                  className={`block w-full px-3 py-2 pr-10 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors ${
                    fieldErrors.confirmPassword
                      ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300'
                  }`}
                  placeholder="Repeat your password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none"
                  aria-label={
                    showConfirmPassword ? 'Hide password' : 'Show password'
                  }
                >
                  {showConfirmPassword ? (
                    <EyeOff className="w-5 h-5" aria-hidden="true" />
                  ) : (
                    <Eye className="w-5 h-5" aria-hidden="true" />
                  )}
                </button>
              </div>
              {fieldErrors.confirmPassword && (
                <p
                  id="confirm-password-error"
                  className="mt-1 text-sm text-red-600"
                  role="alert"
                >
                  {fieldErrors.confirmPassword}
                </p>
              )}

              {/* Password Match Indicator */}
              {formData.confirmPassword &&
                formData.password &&
                !fieldErrors.confirmPassword && (
                  <div className="mt-1 flex items-center text-xs">
                    {formData.password === formData.confirmPassword ? (
                      <>
                        <Check
                          className="w-3.5 h-3.5 text-green-500 mr-1"
                          aria-hidden="true"
                        />
                        <span className="text-green-600">Passwords match</span>
                      </>
                    ) : (
                      <>
                        <X
                          className="w-3.5 h-3.5 text-red-500 mr-1"
                          aria-hidden="true"
                        />
                        <span className="text-red-600">
                          Passwords do not match
                        </span>
                      </>
                    )}
                  </div>
                )}
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
                Creating account...
              </>
            ) : (
              <>
                <UserPlus className="w-4 h-4 mr-2" aria-hidden="true" />
                Create account
              </>
            )}
          </button>
        </form>

        {/* Footer Links */}
        <div className="text-center text-sm text-gray-500">
          <p>
            By creating an account, you agree to our{' '}
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
