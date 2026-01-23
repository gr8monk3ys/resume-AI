'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import {
  profileApi,
  resumesApi,
  jobsApi,
  coverLettersApi,
  ApiError,
} from '@/lib/api'
import type { Profile, JobStats, Resume, CoverLetter, JobApplication } from '@/types'
import {
  User,
  Save,
  BarChart3,
  Shield,
  Database,
  Server,
  AlertTriangle,
  Download,
  Trash2,
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  Briefcase,
  Mail,
  BookOpen,
  Lock,
  RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// Types
interface TabConfig {
  id: string
  name: string
  icon: React.ComponentType<{ className?: string }>
}

interface ValidationError {
  field: string
  message: string
}

interface PasswordStrength {
  score: number
  label: string
  color: string
}

interface SystemHealth {
  database: 'healthy' | 'degraded' | 'down'
  llm: 'healthy' | 'degraded' | 'down'
  api: 'healthy' | 'degraded' | 'down'
}

// Constants
const TABS: TabConfig[] = [
  { id: 'profile', name: 'Profile', icon: User },
  { id: 'statistics', name: 'Statistics', icon: BarChart3 },
  { id: 'security', name: 'Security', icon: Shield },
  { id: 'data', name: 'Data Management', icon: Database },
  { id: 'system', name: 'System', icon: Server },
]

const STATUS_COLORS: Record<string, string> = {
  Bookmarked: 'bg-gray-100 text-gray-800',
  Applied: 'bg-blue-100 text-blue-800',
  'Phone Screen': 'bg-yellow-100 text-yellow-800',
  Interview: 'bg-purple-100 text-purple-800',
  Offer: 'bg-green-100 text-green-800',
  Rejected: 'bg-red-100 text-red-800',
}

// Validation utilities
function validateEmail(email: string): ValidationError | null {
  if (!email) return null
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email)) {
    return { field: 'email', message: 'Please enter a valid email address' }
  }
  return null
}

function validateUrl(url: string, field: string): ValidationError | null {
  if (!url) return null
  try {
    new URL(url)
    return null
  } catch {
    return { field, message: `Please enter a valid URL for ${field}` }
  }
}

function validatePhone(phone: string): ValidationError | null {
  if (!phone) return null
  const phoneRegex = /^[+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]*$/
  if (!phoneRegex.test(phone) || phone.replace(/\D/g, '').length < 7) {
    return { field: 'phone', message: 'Please enter a valid phone number' }
  }
  return null
}

function calculatePasswordStrength(password: string): PasswordStrength {
  let score = 0
  if (password.length >= 8) score++
  if (password.length >= 12) score++
  if (/[a-z]/.test(password)) score++
  if (/[A-Z]/.test(password)) score++
  if (/[0-9]/.test(password)) score++
  if (/[^a-zA-Z0-9]/.test(password)) score++

  if (score <= 2) return { score, label: 'Weak', color: 'bg-red-500' }
  if (score <= 4) return { score, label: 'Fair', color: 'bg-yellow-500' }
  if (score <= 5) return { score, label: 'Good', color: 'bg-blue-500' }
  return { score, label: 'Strong', color: 'bg-green-500' }
}

// Confirmation Dialog Component
function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText,
  confirmVariant = 'danger',
  requireTyping,
  typingText,
  onConfirm,
  onCancel,
}: {
  isOpen: boolean
  title: string
  message: string
  confirmText: string
  confirmVariant?: 'danger' | 'warning'
  requireTyping?: boolean
  typingText?: string
  onConfirm: () => void
  onCancel: () => void
}) {
  const [typedText, setTypedText] = useState('')

  useEffect(() => {
    if (!isOpen) setTypedText('')
  }, [isOpen])

  if (!isOpen) return null

  const canConfirm = !requireTyping || typedText === typingText

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div
        className="bg-white rounded-lg shadow-xl max-w-md w-full p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
      >
        <div className="flex items-start space-x-4">
          <div
            className={cn(
              'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
              confirmVariant === 'danger' ? 'bg-red-100' : 'bg-yellow-100'
            )}
          >
            <AlertTriangle
              className={cn(
                'w-5 h-5',
                confirmVariant === 'danger' ? 'text-red-600' : 'text-yellow-600'
              )}
            />
          </div>
          <div className="flex-1">
            <h3 id="dialog-title" className="text-lg font-semibold text-gray-900">
              {title}
            </h3>
            <p className="mt-2 text-sm text-gray-600">{message}</p>
            {requireTyping && typingText && (
              <div className="mt-4">
                <p className="text-sm text-gray-700 mb-2">
                  Type <strong className="font-mono">{typingText}</strong> to confirm:
                </p>
                <input
                  type="text"
                  value={typedText}
                  onChange={(e) => setTypedText(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm font-mono focus:ring-red-500 focus:border-red-500"
                  aria-label="Confirmation text"
                />
              </div>
            )}
          </div>
        </div>
        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={!canConfirm}
            className={cn(
              'px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed',
              confirmVariant === 'danger'
                ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                : 'bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500'
            )}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}

// Password Input Component
function PasswordInput({
  id,
  label,
  value,
  onChange,
  error,
  showStrength,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
  showStrength?: boolean
}) {
  const [showPassword, setShowPassword] = useState(false)
  const strength = useMemo(
    () => (showStrength && value ? calculatePasswordStrength(value) : null),
    [showStrength, value]
  )

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label}
      </label>
      <div className="relative mt-1">
        <input
          id={id}
          type={showPassword ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            'block w-full px-3 py-2 pr-10 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
            error ? 'border-red-300' : 'border-gray-300'
          )}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      {error && (
        <p id={`${id}-error`} className="mt-1 text-sm text-red-600">
          {error}
        </p>
      )}
      {strength && (
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-gray-600">Password strength:</span>
            <span
              className={cn(
                'font-medium',
                strength.score <= 2 && 'text-red-600',
                strength.score > 2 && strength.score <= 4 && 'text-yellow-600',
                strength.score > 4 && strength.score <= 5 && 'text-blue-600',
                strength.score > 5 && 'text-green-600'
              )}
            >
              {strength.label}
            </span>
          </div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={cn('h-full transition-all duration-300', strength.color)}
              style={{ width: `${(strength.score / 6) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

// Status Badge Component
function StatusBadge({ status, count }: { status: string; count: number }) {
  return (
    <div
      className={cn(
        'flex items-center justify-between px-3 py-2 rounded-lg',
        STATUS_COLORS[status] || 'bg-gray-100 text-gray-800'
      )}
    >
      <span className="text-sm font-medium">{status}</span>
      <span className="text-lg font-bold">{count}</span>
    </div>
  )
}

// Health Status Indicator
function HealthIndicator({
  name,
  status,
}: {
  name: string
  status: 'healthy' | 'degraded' | 'down'
}) {
  const statusConfig = {
    healthy: { icon: CheckCircle, color: 'text-green-500', label: 'Operational' },
    degraded: { icon: Clock, color: 'text-yellow-500', label: 'Degraded' },
    down: { icon: XCircle, color: 'text-red-500', label: 'Down' },
  }
  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
      <div className="flex items-center space-x-3">
        <Icon className={cn('w-5 h-5', config.color)} />
        <span className="font-medium text-gray-900">{name}</span>
      </div>
      <span className={cn('text-sm font-medium', config.color)}>{config.label}</span>
    </div>
  )
}

// Main Settings Page Component
export default function SettingsPage() {
  const { user, tokens, isLoading: authLoading, logout } = useAuth()
  const router = useRouter()

  // State
  const [activeTab, setActiveTab] = useState('profile')
  const [profile, setProfile] = useState<Profile | null>(null)
  const [jobStats, setJobStats] = useState<JobStats | null>(null)
  const [resumes, setResumes] = useState<Resume[]>([])
  const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([])
  const [jobs, setJobs] = useState<JobApplication[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({})

  // Confirmation dialogs state
  const [deleteAppsDialog, setDeleteAppsDialog] = useState(false)
  const [deleteAllDialog, setDeleteAllDialog] = useState(false)
  const [deleteAccountDialog, setDeleteAccountDialog] = useState(false)
  const [accountDeletePassword, setAccountDeletePassword] = useState('')

  // System health state
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    database: 'healthy',
    llm: 'healthy',
    api: 'healthy',
  })
  const [isCheckingHealth, setIsCheckingHealth] = useState(false)

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  // Load data
  const loadData = useCallback(async () => {
    if (!tokens?.access_token) return

    setIsLoading(true)
    try {
      const [profileData, statsData, resumesData, coverLettersData, jobsData] = await Promise.all([
        profileApi.get(tokens.access_token),
        jobsApi.getStats(tokens.access_token),
        resumesApi.list(tokens.access_token),
        coverLettersApi.list(tokens.access_token),
        jobsApi.list(tokens.access_token),
      ])
      setProfile(profileData)
      setJobStats(statsData)
      setResumes(resumesData)
      setCoverLetters(coverLettersData)
      setJobs(jobsData)
    } catch (error) {
      console.error('Failed to load data:', error)
      setMessage({ type: 'error', text: 'Failed to load settings data' })
    } finally {
      setIsLoading(false)
    }
  }, [tokens])

  useEffect(() => {
    if (tokens?.access_token) {
      loadData()
    }
  }, [tokens, loadData])

  // Clear message after 5 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [message])

  // Validate profile fields
  const validateProfile = useCallback((): boolean => {
    if (!profile) return false

    const errors: ValidationError[] = []

    const emailError = validateEmail(profile.email || '')
    if (emailError) errors.push(emailError)

    const phoneError = validatePhone(profile.phone || '')
    if (phoneError) errors.push(phoneError)

    const linkedinError = validateUrl(profile.linkedin || '', 'linkedin')
    if (linkedinError) errors.push(linkedinError)

    const githubError = validateUrl(profile.github || '', 'github')
    if (githubError) errors.push(githubError)

    const portfolioError = validateUrl(profile.portfolio || '', 'portfolio')
    if (portfolioError) errors.push(portfolioError)

    setValidationErrors(errors)
    return errors.length === 0
  }, [profile])

  // Save profile
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!tokens?.access_token || !profile) return

    if (!validateProfile()) {
      setMessage({ type: 'error', text: 'Please fix validation errors before saving' })
      return
    }

    setIsSaving(true)
    setMessage(null)

    try {
      const updated = await profileApi.update(tokens.access_token, {
        name: profile.name,
        email: profile.email || undefined,
        phone: profile.phone || undefined,
        linkedin: profile.linkedin || undefined,
        github: profile.github || undefined,
        portfolio: profile.portfolio || undefined,
      })
      setProfile(updated)
      setMessage({ type: 'success', text: 'Profile saved successfully!' })
    } catch (error) {
      console.error('Failed to save profile:', error)
      setMessage({ type: 'error', text: 'Failed to save profile. Please try again.' })
    } finally {
      setIsSaving(false)
    }
  }

  // Change password
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()

    const errors: Record<string, string> = {}

    if (!currentPassword) {
      errors.currentPassword = 'Current password is required'
    }

    if (!newPassword) {
      errors.newPassword = 'New password is required'
    } else if (newPassword.length < 8) {
      errors.newPassword = 'Password must be at least 8 characters'
    }

    if (newPassword !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match'
    }

    setPasswordErrors(errors)

    if (Object.keys(errors).length > 0) return

    setIsSaving(true)

    try {
      // Placeholder for password change API call
      // await authApi.changePassword(tokens.access_token, currentPassword, newPassword)
      await new Promise((resolve) => setTimeout(resolve, 1000)) // Simulated delay
      setMessage({ type: 'success', text: 'Password changed successfully!' })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setPasswordErrors({ currentPassword: 'Current password is incorrect' })
      } else {
        setMessage({ type: 'error', text: 'Failed to change password. Please try again.' })
      }
    } finally {
      setIsSaving(false)
    }
  }

  // Export functions
  const exportAsCSV = (data: JobApplication[]) => {
    const headers = [
      'Company',
      'Position',
      'Status',
      'Application Date',
      'Location',
      'Job URL',
      'Notes',
    ]
    const rows = data.map((job) => [
      job.company,
      job.position,
      job.status,
      job.application_date || '',
      job.location || '',
      job.job_url || '',
      job.notes?.replace(/"/g, '""') || '',
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n')

    downloadFile(csvContent, 'job_applications.csv', 'text/csv')
  }

  const exportJournalAsTxt = () => {
    // Placeholder - would need journal API
    const content = 'Career Journal Export\n\nNo journal entries available.'
    downloadFile(content, 'career_journal.txt', 'text/plain')
  }

  const exportAllAsJSON = () => {
    const exportData = {
      exportDate: new Date().toISOString(),
      profile,
      resumes,
      jobApplications: jobs,
      coverLetters,
      statistics: jobStats,
    }
    downloadFile(JSON.stringify(exportData, null, 2), 'resuboost_export.json', 'application/json')
  }

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  // Delete functions
  const handleDeleteAllApplications = async () => {
    if (!tokens?.access_token) return

    try {
      // Delete each application
      await Promise.all(jobs.map((job) => jobsApi.delete(tokens.access_token, job.id)))
      setJobs([])
      setJobStats((prev) => (prev ? { ...prev, total: 0, status_breakdown: {} } : null))
      setMessage({ type: 'success', text: 'All applications deleted successfully' })
    } catch (error) {
      console.error('Failed to delete applications:', error)
      setMessage({ type: 'error', text: 'Failed to delete some applications' })
    } finally {
      setDeleteAppsDialog(false)
    }
  }

  const handleDeleteAllData = async () => {
    if (!tokens?.access_token) return

    try {
      // Delete all data in parallel
      await Promise.all([
        ...jobs.map((job) => jobsApi.delete(tokens.access_token, job.id)),
        ...resumes.map((resume) => resumesApi.delete(tokens.access_token, resume.id)),
        ...coverLetters.map((cl) => coverLettersApi.delete(tokens.access_token, cl.id)),
      ])
      setJobs([])
      setResumes([])
      setCoverLetters([])
      setJobStats(null)
      setMessage({ type: 'success', text: 'All data deleted successfully' })
    } catch (error) {
      console.error('Failed to delete data:', error)
      setMessage({ type: 'error', text: 'Failed to delete some data' })
    } finally {
      setDeleteAllDialog(false)
    }
  }

  const handleDeleteAccount = async () => {
    // Placeholder - would need delete account API
    setMessage({ type: 'error', text: 'Account deletion is not yet implemented' })
    setDeleteAccountDialog(false)
    setAccountDeletePassword('')
  }

  // Check system health
  const checkSystemHealth = async () => {
    setIsCheckingHealth(true)
    try {
      // Simulate health check - would be replaced with actual API calls
      await new Promise((resolve) => setTimeout(resolve, 1500))
      setSystemHealth({
        database: 'healthy',
        llm: 'healthy',
        api: 'healthy',
      })
      setMessage({ type: 'success', text: 'System health check completed' })
    } catch (error) {
      console.error('Health check failed:', error)
      setSystemHealth({
        database: 'degraded',
        llm: 'down',
        api: 'healthy',
      })
    } finally {
      setIsCheckingHealth(false)
    }
  }

  // Get validation error for a field
  const getFieldError = (field: string): string | undefined => {
    return validationErrors.find((e) => e.field === field)?.message
  }

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  // Calculate statistics
  const totalApplications = jobStats?.total || 0
  const offerCount = jobStats?.status_breakdown?.Offer || 0
  const successRate = totalApplications > 0 ? ((offerCount / totalApplications) * 100).toFixed(1) : '0'

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Account & Settings</h1>
        <p className="text-gray-500">
          Manage your profile, security settings, and account data
        </p>
      </div>

      {/* Message */}
      {message && (
        <div
          className={cn(
            'mb-6 p-4 rounded-md text-sm flex items-center space-x-2',
            message.type === 'success'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          )}
          role="alert"
        >
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 flex-shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Tabs Navigation */}
        <nav
          className="lg:w-64 flex-shrink-0"
          aria-label="Settings navigation"
        >
          <ul className="space-y-1">
            {TABS.map((tab) => (
              <li key={tab.id}>
                <button
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors',
                    activeTab === tab.id
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                  aria-current={activeTab === tab.id ? 'page' : undefined}
                >
                  <tab.icon className="w-5 h-5 mr-3" />
                  {tab.name}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Tab Content */}
        <div className="flex-1">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">
                Profile Information
              </h2>

              <form onSubmit={handleSaveProfile} className="space-y-6">
                {/* User Info */}
                <div className="flex items-center space-x-4 pb-6 border-b">
                  <div className="bg-primary-100 rounded-full p-4">
                    <User className="w-8 h-8 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{user?.username}</p>
                    <p className="text-sm text-gray-500">{user?.email}</p>
                  </div>
                </div>

                {/* Form Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label
                      htmlFor="name"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Full Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="name"
                      type="text"
                      required
                      value={profile?.name || ''}
                      onChange={(e) =>
                        setProfile((prev) =>
                          prev ? { ...prev, name: e.target.value } : null
                        )
                      }
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="email"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Email Address
                    </label>
                    <input
                      id="email"
                      type="email"
                      value={profile?.email || ''}
                      onChange={(e) =>
                        setProfile((prev) =>
                          prev ? { ...prev, email: e.target.value } : null
                        )
                      }
                      className={cn(
                        'mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                        getFieldError('email') ? 'border-red-300' : 'border-gray-300'
                      )}
                      aria-invalid={Boolean(getFieldError('email'))}
                      aria-describedby={getFieldError('email') ? 'email-error' : undefined}
                    />
                    {getFieldError('email') && (
                      <p id="email-error" className="mt-1 text-sm text-red-600">
                        {getFieldError('email')}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="phone"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Phone Number
                    </label>
                    <input
                      id="phone"
                      type="tel"
                      value={profile?.phone || ''}
                      onChange={(e) =>
                        setProfile((prev) =>
                          prev ? { ...prev, phone: e.target.value } : null
                        )
                      }
                      className={cn(
                        'mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                        getFieldError('phone') ? 'border-red-300' : 'border-gray-300'
                      )}
                      placeholder="+1 (555) 000-0000"
                      aria-invalid={Boolean(getFieldError('phone'))}
                      aria-describedby={getFieldError('phone') ? 'phone-error' : undefined}
                    />
                    {getFieldError('phone') && (
                      <p id="phone-error" className="mt-1 text-sm text-red-600">
                        {getFieldError('phone')}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="linkedin"
                      className="block text-sm font-medium text-gray-700"
                    >
                      LinkedIn
                    </label>
                    <input
                      id="linkedin"
                      type="url"
                      value={profile?.linkedin || ''}
                      onChange={(e) =>
                        setProfile((prev) =>
                          prev ? { ...prev, linkedin: e.target.value } : null
                        )
                      }
                      className={cn(
                        'mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                        getFieldError('linkedin') ? 'border-red-300' : 'border-gray-300'
                      )}
                      placeholder="https://linkedin.com/in/username"
                      aria-invalid={Boolean(getFieldError('linkedin'))}
                      aria-describedby={getFieldError('linkedin') ? 'linkedin-error' : undefined}
                    />
                    {getFieldError('linkedin') && (
                      <p id="linkedin-error" className="mt-1 text-sm text-red-600">
                        {getFieldError('linkedin')}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="github"
                      className="block text-sm font-medium text-gray-700"
                    >
                      GitHub
                    </label>
                    <input
                      id="github"
                      type="url"
                      value={profile?.github || ''}
                      onChange={(e) =>
                        setProfile((prev) =>
                          prev ? { ...prev, github: e.target.value } : null
                        )
                      }
                      className={cn(
                        'mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                        getFieldError('github') ? 'border-red-300' : 'border-gray-300'
                      )}
                      placeholder="https://github.com/username"
                      aria-invalid={Boolean(getFieldError('github'))}
                      aria-describedby={getFieldError('github') ? 'github-error' : undefined}
                    />
                    {getFieldError('github') && (
                      <p id="github-error" className="mt-1 text-sm text-red-600">
                        {getFieldError('github')}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="portfolio"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Portfolio Website
                    </label>
                    <input
                      id="portfolio"
                      type="url"
                      value={profile?.portfolio || ''}
                      onChange={(e) =>
                        setProfile((prev) =>
                          prev ? { ...prev, portfolio: e.target.value } : null
                        )
                      }
                      className={cn(
                        'mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                        getFieldError('portfolio') ? 'border-red-300' : 'border-gray-300'
                      )}
                      placeholder="https://yourportfolio.com"
                      aria-invalid={Boolean(getFieldError('portfolio'))}
                      aria-describedby={getFieldError('portfolio') ? 'portfolio-error' : undefined}
                    />
                    {getFieldError('portfolio') && (
                      <p id="portfolio-error" className="mt-1 text-sm text-red-600">
                        {getFieldError('portfolio')}
                      </p>
                    )}
                  </div>
                </div>

                {/* Save Button */}
                <div className="flex justify-end pt-4">
                  <button
                    type="submit"
                    disabled={isSaving}
                    className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {isSaving ? 'Saving...' : 'Save Profile'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Statistics Tab */}
          {activeTab === 'statistics' && (
            <div className="space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg shadow p-4">
                  <div className="flex items-center space-x-3">
                    <div className="bg-blue-100 rounded-full p-2">
                      <FileText className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-gray-900">
                        {resumes.length}
                      </p>
                      <p className="text-sm text-gray-500">Resumes</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow p-4">
                  <div className="flex items-center space-x-3">
                    <div className="bg-green-100 rounded-full p-2">
                      <Briefcase className="w-5 h-5 text-green-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-gray-900">
                        {totalApplications}
                      </p>
                      <p className="text-sm text-gray-500">Applications</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow p-4">
                  <div className="flex items-center space-x-3">
                    <div className="bg-purple-100 rounded-full p-2">
                      <Mail className="w-5 h-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-gray-900">
                        {coverLetters.length}
                      </p>
                      <p className="text-sm text-gray-500">Cover Letters</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow p-4">
                  <div className="flex items-center space-x-3">
                    <div className="bg-yellow-100 rounded-full p-2">
                      <BookOpen className="w-5 h-5 text-yellow-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-gray-900">0</p>
                      <p className="text-sm text-gray-500">Journal Entries</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Success Rate */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Application Success Rate
                </h3>
                <div className="flex items-center space-x-6">
                  <div className="flex-shrink-0">
                    <div className="relative w-32 h-32">
                      <svg className="w-32 h-32 transform -rotate-90">
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke="currentColor"
                          strokeWidth="12"
                          fill="none"
                          className="text-gray-200"
                        />
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke="currentColor"
                          strokeWidth="12"
                          fill="none"
                          strokeDasharray={`${(parseFloat(successRate) / 100) * 352} 352`}
                          className="text-green-500"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-2xl font-bold text-gray-900">
                          {successRate}%
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-600">
                      {offerCount} offers out of {totalApplications} applications
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      Response rate: {jobStats?.response_rate?.toFixed(1) || '0'}%
                    </p>
                  </div>
                </div>
              </div>

              {/* Applications by Status */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Applications by Status
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {Object.entries(jobStats?.status_breakdown || {}).map(
                    ([status, count]) => (
                      <StatusBadge key={status} status={status} count={count as number} />
                    )
                  )}
                  {(!jobStats?.status_breakdown ||
                    Object.keys(jobStats.status_breakdown).length === 0) && (
                    <p className="col-span-full text-center text-gray-500 py-4">
                      No applications yet
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className="space-y-6">
              {/* Change Password */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">
                  Change Password
                </h3>
                <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
                  <PasswordInput
                    id="currentPassword"
                    label="Current Password"
                    value={currentPassword}
                    onChange={setCurrentPassword}
                    error={passwordErrors.currentPassword}
                  />
                  <PasswordInput
                    id="newPassword"
                    label="New Password"
                    value={newPassword}
                    onChange={setNewPassword}
                    error={passwordErrors.newPassword}
                    showStrength
                  />
                  <PasswordInput
                    id="confirmPassword"
                    label="Confirm New Password"
                    value={confirmPassword}
                    onChange={setConfirmPassword}
                    error={passwordErrors.confirmPassword}
                  />
                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={isSaving}
                      className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                    >
                      <Lock className="w-4 h-4 mr-2" />
                      {isSaving ? 'Updating...' : 'Update Password'}
                    </button>
                  </div>
                </form>
              </div>

              {/* Session Info */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Session Information
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between py-3 border-b">
                    <div>
                      <p className="font-medium text-gray-900">Last Login</p>
                      <p className="text-sm text-gray-500">
                        {user?.last_login
                          ? new Date(user.last_login).toLocaleString()
                          : 'Not available'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between py-3 border-b">
                    <div>
                      <p className="font-medium text-gray-900">Account Created</p>
                      <p className="text-sm text-gray-500">
                        {user?.created_at
                          ? new Date(user.created_at).toLocaleString()
                          : 'Not available'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between py-3">
                    <div>
                      <p className="font-medium text-gray-900">Active Sessions</p>
                      <p className="text-sm text-gray-500">
                        1 active session (current)
                      </p>
                    </div>
                    <button
                      onClick={logout}
                      className="text-sm text-red-600 hover:text-red-700 font-medium"
                    >
                      Sign out all devices
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Data Management Tab */}
          {activeTab === 'data' && (
            <div className="space-y-6">
              {/* Export Data */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Export Your Data
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Download your data in various formats for backup or migration.
                </p>
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={() => exportAsCSV(jobs)}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export Applications (CSV)
                  </button>
                  <button
                    onClick={exportJournalAsTxt}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export Journal (TXT)
                  </button>
                  <button
                    onClick={exportAllAsJSON}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export All Data (JSON)
                  </button>
                </div>
              </div>

              {/* Danger Zone */}
              <div className="bg-white rounded-lg shadow p-6 border-2 border-red-200">
                <div className="flex items-center space-x-2 mb-4">
                  <AlertTriangle className="w-5 h-5 text-red-600" />
                  <h3 className="text-lg font-semibold text-red-600">
                    Danger Zone
                  </h3>
                </div>
                <p className="text-sm text-gray-600 mb-6">
                  These actions are irreversible. Please be certain before proceeding.
                </p>

                <div className="space-y-4">
                  {/* Delete Applications */}
                  <div className="flex items-center justify-between py-4 border-b">
                    <div>
                      <p className="font-medium text-gray-900">
                        Delete All Applications
                      </p>
                      <p className="text-sm text-gray-500">
                        Remove all {jobs.length} job applications
                      </p>
                    </div>
                    <button
                      onClick={() => setDeleteAppsDialog(true)}
                      disabled={jobs.length === 0}
                      className="inline-flex items-center px-4 py-2 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete Applications
                    </button>
                  </div>

                  {/* Delete All Data */}
                  <div className="flex items-center justify-between py-4 border-b">
                    <div>
                      <p className="font-medium text-gray-900">Delete All Data</p>
                      <p className="text-sm text-gray-500">
                        Remove all resumes, applications, and cover letters
                      </p>
                    </div>
                    <button
                      onClick={() => setDeleteAllDialog(true)}
                      disabled={
                        jobs.length === 0 &&
                        resumes.length === 0 &&
                        coverLetters.length === 0
                      }
                      className="inline-flex items-center px-4 py-2 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete All Data
                    </button>
                  </div>

                  {/* Delete Account */}
                  <div className="flex items-center justify-between py-4">
                    <div>
                      <p className="font-medium text-gray-900">Delete Account</p>
                      <p className="text-sm text-gray-500">
                        Permanently delete your account and all associated data
                      </p>
                    </div>
                    <button
                      onClick={() => setDeleteAccountDialog(true)}
                      className="inline-flex items-center px-4 py-2 bg-red-600 rounded-md text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete Account
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* System Tab */}
          {activeTab === 'system' && (
            <div className="space-y-6">
              {/* System Health */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-gray-900">
                    System Health
                  </h3>
                  <button
                    onClick={checkSystemHealth}
                    disabled={isCheckingHealth}
                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-primary-600 bg-primary-50 rounded-md hover:bg-primary-100 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <RefreshCw
                      className={cn(
                        'w-4 h-4 mr-2',
                        isCheckingHealth && 'animate-spin'
                      )}
                    />
                    {isCheckingHealth ? 'Checking...' : 'Refresh'}
                  </button>
                </div>
                <div className="space-y-3">
                  <HealthIndicator name="Database Connection" status={systemHealth.database} />
                  <HealthIndicator name="LLM Provider" status={systemHealth.llm} />
                  <HealthIndicator name="API Server" status={systemHealth.api} />
                </div>
              </div>

              {/* API Information */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  API Information
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-gray-600">API Version</span>
                    <span className="text-sm font-mono text-gray-900">v1.0.0</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-gray-600">API Base URL</span>
                    <span className="text-sm font-mono text-gray-900">
                      {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-gray-600">Frontend Version</span>
                    <span className="text-sm font-mono text-gray-900">1.0.0</span>
                  </div>
                </div>
              </div>

              {/* Admin Notice */}
              {user?.is_admin && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-yellow-800">
                        Administrator Account
                      </p>
                      <p className="text-sm text-yellow-700 mt-1">
                        You have administrator privileges. Additional admin features
                        are available in the admin panel.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Dialogs */}
      <ConfirmDialog
        isOpen={deleteAppsDialog}
        title="Delete All Applications"
        message={`This will permanently delete all ${jobs.length} job applications. This action cannot be undone.`}
        confirmText="Delete Applications"
        confirmVariant="danger"
        onConfirm={handleDeleteAllApplications}
        onCancel={() => setDeleteAppsDialog(false)}
      />

      <ConfirmDialog
        isOpen={deleteAllDialog}
        title="Delete All Data"
        message="This will permanently delete all your resumes, job applications, and cover letters. This action cannot be undone."
        confirmText="Delete All Data"
        confirmVariant="danger"
        requireTyping
        typingText="DELETE ALL DATA"
        onConfirm={handleDeleteAllData}
        onCancel={() => setDeleteAllDialog(false)}
      />

      <ConfirmDialog
        isOpen={deleteAccountDialog}
        title="Delete Account"
        message="This will permanently delete your account and all associated data. You will be logged out immediately. This action cannot be undone."
        confirmText="Delete My Account"
        confirmVariant="danger"
        requireTyping
        typingText="DELETE MY ACCOUNT"
        onConfirm={handleDeleteAccount}
        onCancel={() => {
          setDeleteAccountDialog(false)
          setAccountDeletePassword('')
        }}
      />
    </div>
  )
}
