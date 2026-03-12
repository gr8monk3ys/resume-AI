'use client'

import {
  AlertCircle,
  Check,
  Eye,
  EyeOff,
  UserPlus,
  X,
} from 'lucide-react'
import Link from 'next/link'
import { useCallback, useMemo, useState } from 'react'

import { ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'

type PasswordStrength = 'weak' | 'fair' | 'good' | 'strong'

interface PasswordRequirement {
  label: string
  test: (password: string) => boolean
}

interface RegisterFormData {
  username: string
  email: string
  password: string
  confirmPassword: string
  full_name: string
}

interface RegisterPageState {
  formData: RegisterFormData
  showPassword: boolean
  showConfirmPassword: boolean
  error: string
  fieldErrors: Record<string, string>
  isSubmitting: boolean
  showRequirements: boolean
}

const PASSWORD_REQUIREMENTS: PasswordRequirement[] = [
  { label: 'At least 8 characters', test: (password) => password.length >= 8 },
  { label: 'Contains uppercase letter', test: (password) => /[A-Z]/.test(password) },
  { label: 'Contains lowercase letter', test: (password) => /[a-z]/.test(password) },
  { label: 'Contains a number', test: (password) => /\d/.test(password) },
  {
    label: 'Contains special character',
    test: (password) => /[!@#$%^&*(),.?":{}|<>]/.test(password),
  },
]

const MIN_PASSWORD_LENGTH = 6

const INITIAL_REGISTER_PAGE_STATE: RegisterPageState = {
  formData: {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  },
  showPassword: false,
  showConfirmPassword: false,
  error: '',
  fieldErrors: {},
  isSubmitting: false,
  showRequirements: false,
}

function calculatePasswordStrength(password: string): PasswordStrength {
  if (!password) return 'weak'

  const requirementsMet = PASSWORD_REQUIREMENTS.filter((requirement) =>
    requirement.test(password)
  ).length

  if (requirementsMet <= 1) return 'weak'
  if (requirementsMet <= 2) return 'fair'
  if (requirementsMet <= 4) return 'good'
  return 'strong'
}

function getStrengthColor(strength: PasswordStrength): string {
  const colors: Record<PasswordStrength, string> = {
    weak: 'bg-red-500',
    fair: 'bg-orange-500',
    good: 'bg-yellow-500',
    strong: 'bg-green-500',
  }
  return colors[strength]
}

function getStrengthTextColor(strength: PasswordStrength): string {
  const colors: Record<PasswordStrength, string> = {
    weak: 'text-red-600',
    fair: 'text-orange-600',
    good: 'text-yellow-600',
    strong: 'text-green-600',
  }
  return colors[strength]
}

function getStrengthWidth(strength: PasswordStrength): string {
  const widths: Record<PasswordStrength, string> = {
    weak: 'w-1/4',
    fair: 'w-2/4',
    good: 'w-3/4',
    strong: 'w-full',
  }
  return widths[strength]
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
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

function FieldErrorMessage({
  id,
  message,
}: {
  id: string
  message?: string
}) {
  if (!message) {
    return null
  }

  return (
    <p id={id} className="mt-1 text-sm text-red-600" role="alert">
      {message}
    </p>
  )
}

function PasswordRequirementsList({
  requirementsMet,
}: {
  requirementsMet: Array<PasswordRequirement & { met: boolean }>
}) {
  return (
    <div id="password-requirements" className="mt-3 space-y-1">
      <p className="mb-2 text-xs text-gray-500">Password requirements:</p>
      {requirementsMet.map((requirement) => (
        <div key={requirement.label} className="flex items-center text-xs">
          {requirement.met ? (
            <Check className="mr-2 h-3.5 w-3.5 flex-shrink-0 text-green-500" />
          ) : (
            <X className="mr-2 h-3.5 w-3.5 flex-shrink-0 text-gray-300" />
          )}
          <span className={requirement.met ? 'text-green-600' : 'text-gray-500'}>
            {requirement.label}
          </span>
        </div>
      ))}
    </div>
  )
}

function PasswordStrengthIndicator({
  passwordStrength,
}: {
  passwordStrength: PasswordStrength
}) {
  return (
    <div className="mt-2" aria-live="polite">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs text-gray-500">Password strength</span>
        <span
          className={cn(
            'text-xs font-medium',
            getStrengthTextColor(passwordStrength)
          )}
        >
          {capitalize(passwordStrength)}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className={cn(
            'h-full transition-all duration-300',
            getStrengthColor(passwordStrength),
            getStrengthWidth(passwordStrength)
          )}
          role="progressbar"
          aria-valuenow={
            { weak: 25, fair: 50, good: 75, strong: 100 }[passwordStrength]
          }
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Password strength: ${passwordStrength}`}
        />
      </div>
    </div>
  )
}

function useRegisterPageController() {
  const { register, user, isLoading: authLoading } = useAuth()
  const [pageState, setPageState] = useState<RegisterPageState>(
    INITIAL_REGISTER_PAGE_STATE
  )
  const {
    formData,
    showPassword,
    showConfirmPassword,
    error,
    fieldErrors,
    isSubmitting,
    showRequirements,
  } = pageState

  const passwordStrength = useMemo(
    () => calculatePasswordStrength(formData.password),
    [formData.password]
  )

  const requirementsMet = useMemo(
    () =>
      PASSWORD_REQUIREMENTS.map((requirement) => ({
        ...requirement,
        met: requirement.test(formData.password),
      })),
    [formData.password]
  )

  const setFormField = useCallback(
    (field: keyof RegisterFormData, value: string) => {
      setPageState((prev) => {
        const nextFieldErrors = { ...prev.fieldErrors }
        delete nextFieldErrors[field]

        return {
          ...prev,
          formData: {
            ...prev.formData,
            [field]: value,
          },
          fieldErrors: nextFieldErrors,
        }
      })
    },
    []
  )

  const setPasswordVisibility = useCallback(
    (field: 'showPassword' | 'showConfirmPassword') => {
      setPageState((prev) => ({ ...prev, [field]: !prev[field] }))
    },
    []
  )

  const showPasswordRequirements = useCallback(() => {
    setPageState((prev) => ({ ...prev, showRequirements: true }))
  }, [])

  const validateForm = useCallback(() => {
    const nextErrors: Record<string, string> = {}

    if (!formData.username.trim()) {
      nextErrors.username = 'Username is required'
    } else if (formData.username.length < 3) {
      nextErrors.username = 'Username must be at least 3 characters'
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      nextErrors.username =
        'Username can only contain letters, numbers, and underscores'
    }

    if (!formData.email.trim()) {
      nextErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      nextErrors.email = 'Please enter a valid email address'
    }

    if (!formData.password) {
      nextErrors.password = 'Password is required'
    } else if (formData.password.length < MIN_PASSWORD_LENGTH) {
      nextErrors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters`
    }

    if (!formData.confirmPassword) {
      nextErrors.confirmPassword = 'Please confirm your password'
    } else if (formData.password !== formData.confirmPassword) {
      nextErrors.confirmPassword = 'Passwords do not match'
    }

    setPageState((prev) => ({ ...prev, fieldErrors: nextErrors }))
    return Object.keys(nextErrors).length === 0
  }, [formData.confirmPassword, formData.email, formData.password, formData.username])

  const handleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault()

      if (!validateForm()) {
        return
      }

      setPageState((prev) => ({
        ...prev,
        error: '',
        isSubmitting: true,
      }))

      try {
        await register({
          username: formData.username.trim(),
          email: formData.email.trim(),
          password: formData.password,
          full_name: formData.full_name.trim() || undefined,
        })
      } catch (submissionError) {
        if (submissionError instanceof ApiError) {
          if (submissionError.message.toLowerCase().includes('username')) {
            setPageState((prev) => ({
              ...prev,
              isSubmitting: false,
              fieldErrors: {
                ...prev.fieldErrors,
                username: submissionError.message,
              },
            }))
            return
          }

          if (submissionError.message.toLowerCase().includes('email')) {
            setPageState((prev) => ({
              ...prev,
              isSubmitting: false,
              fieldErrors: {
                ...prev.fieldErrors,
                email: submissionError.message,
              },
            }))
            return
          }

          setPageState((prev) => ({
            ...prev,
            isSubmitting: false,
            error: submissionError.message || 'Registration failed. Please try again.',
          }))
          return
        }

        setPageState((prev) => ({
          ...prev,
          isSubmitting: false,
          error: 'An unexpected error occurred. Please try again.',
        }))
        return
      }

      setPageState((prev) => ({ ...prev, isSubmitting: false }))
    },
    [formData, register, validateForm]
  )

  return {
    user,
    authLoading,
    formData,
    showPassword,
    showConfirmPassword,
    error,
    fieldErrors,
    isSubmitting,
    showRequirements,
    passwordStrength,
    requirementsMet,
    setFormField,
    setPasswordVisibility,
    showPasswordRequirements,
    handleSubmit,
  }
}

function cn(...classes: Array<string | false | undefined>) {
  return classes.filter(Boolean).join(' ')
}

export function RegisterPageClient() {
  const controller = useRegisterPageController()

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
          <h1 className="text-3xl font-bold text-gray-900">Create your account</h1>
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
              <p className="ml-3 text-sm text-red-700">{controller.error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
                Full Name <span className="font-normal text-gray-400">(optional)</span>
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                autoComplete="name"
                value={controller.formData.full_name}
                onChange={(event) => controller.setFormField('full_name', event.target.value)}
                disabled={controller.isSubmitting}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm transition-colors placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100"
                placeholder="John Doe"
              />
            </div>

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
                value={controller.formData.username}
                onChange={(event) => controller.setFormField('username', event.target.value)}
                disabled={controller.isSubmitting}
                aria-invalid={Boolean(controller.fieldErrors.username)}
                aria-describedby={
                  controller.fieldErrors.username ? 'username-error' : undefined
                }
                className={cn(
                  'mt-1 block w-full rounded-md border px-3 py-2 shadow-sm transition-colors placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100',
                  controller.fieldErrors.username
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300'
                )}
                placeholder="johndoe"
              />
              <FieldErrorMessage
                id="username-error"
                message={controller.fieldErrors.username}
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={controller.formData.email}
                onChange={(event) => controller.setFormField('email', event.target.value)}
                disabled={controller.isSubmitting}
                aria-invalid={Boolean(controller.fieldErrors.email)}
                aria-describedby={controller.fieldErrors.email ? 'email-error' : undefined}
                className={cn(
                  'mt-1 block w-full rounded-md border px-3 py-2 shadow-sm transition-colors placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100',
                  controller.fieldErrors.email
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300'
                )}
                placeholder="john@example.com"
              />
              <FieldErrorMessage
                id="email-error"
                message={controller.fieldErrors.email}
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
                  autoComplete="new-password"
                  required
                  value={controller.formData.password}
                  onChange={(event) => controller.setFormField('password', event.target.value)}
                  onFocus={controller.showPasswordRequirements}
                  disabled={controller.isSubmitting}
                  aria-invalid={Boolean(controller.fieldErrors.password)}
                  aria-describedby={
                    controller.fieldErrors.password
                      ? 'password-error'
                      : 'password-requirements'
                  }
                  className={cn(
                    'block w-full rounded-md border px-3 py-2 pr-10 shadow-sm transition-colors placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100',
                    controller.fieldErrors.password
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300'
                  )}
                  placeholder="Create a strong password"
                />
                <button
                  type="button"
                  onClick={() => controller.setPasswordVisibility('showPassword')}
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

              <FieldErrorMessage
                id="password-error"
                message={controller.fieldErrors.password}
              />

              {controller.formData.password && (
                <PasswordStrengthIndicator
                  passwordStrength={controller.passwordStrength}
                />
              )}

              {controller.showRequirements && controller.formData.password && (
                <PasswordRequirementsList requirementsMet={controller.requirementsMet} />
              )}
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-gray-700"
              >
                Confirm Password
              </label>
              <div className="relative mt-1">
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={controller.showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  value={controller.formData.confirmPassword}
                  onChange={(event) =>
                    controller.setFormField('confirmPassword', event.target.value)
                  }
                  disabled={controller.isSubmitting}
                  aria-invalid={Boolean(controller.fieldErrors.confirmPassword)}
                  aria-describedby={
                    controller.fieldErrors.confirmPassword
                      ? 'confirm-password-error'
                      : undefined
                  }
                  className={cn(
                    'block w-full rounded-md border px-3 py-2 pr-10 shadow-sm transition-colors placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100',
                    controller.fieldErrors.confirmPassword
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300'
                  )}
                  placeholder="Repeat your password"
                />
                <button
                  type="button"
                  onClick={() =>
                    controller.setPasswordVisibility('showConfirmPassword')
                  }
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none"
                  aria-label={
                    controller.showConfirmPassword ? 'Hide password' : 'Show password'
                  }
                >
                  {controller.showConfirmPassword ? (
                    <EyeOff className="h-5 w-5" aria-hidden="true" />
                  ) : (
                    <Eye className="h-5 w-5" aria-hidden="true" />
                  )}
                </button>
              </div>
              <FieldErrorMessage
                id="confirm-password-error"
                message={controller.fieldErrors.confirmPassword}
              />

              {controller.formData.confirmPassword &&
                controller.formData.password &&
                !controller.fieldErrors.confirmPassword && (
                  <div className="mt-1 flex items-center text-xs">
                    {controller.formData.password ===
                    controller.formData.confirmPassword ? (
                      <>
                        <Check className="mr-1 h-3.5 w-3.5 text-green-500" />
                        <span className="text-green-600">Passwords match</span>
                      </>
                    ) : (
                      <>
                        <X className="mr-1 h-3.5 w-3.5 text-red-500" />
                        <span className="text-red-600">Passwords do not match</span>
                      </>
                    )}
                  </div>
                )}
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
                Creating account...
              </>
            ) : (
              <>
                <UserPlus className="mr-2 h-4 w-4" aria-hidden="true" />
                Create account
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
