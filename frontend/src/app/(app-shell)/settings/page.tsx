'use client'

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
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  ApiError,
  coverLettersApi,
  jobsApi,
  profileApi,
  resumesApi,
} from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { cn } from '@/lib/utils'

import type { CoverLetter, JobApplication, JobStats, Profile, User as AuthUser } from '@/types'
import type { Resume } from '@/types'

type SettingsTabId = 'profile' | 'statistics' | 'security' | 'data' | 'system'

interface TabConfig {
  id: SettingsTabId
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

interface SettingsMessage {
  type: 'success' | 'error'
  text: string
}

interface SettingsDataState {
  profile: Profile | null
  jobStats: JobStats | null
  resumes: Resume[]
  coverLetters: CoverLetter[]
  jobs: JobApplication[]
}

interface SettingsPasswordState {
  currentPassword: string
  newPassword: string
  confirmPassword: string
  errors: Record<string, string>
}

interface SettingsDialogState {
  deleteApps: boolean
  deleteAll: boolean
  deleteAccount: boolean
}

interface SettingsPageState {
  activeTab: SettingsTabId
  data: SettingsDataState
  isLoading: boolean
  isSaving: boolean
  message: SettingsMessage | null
  validationErrors: ValidationError[]
  passwords: SettingsPasswordState
  dialogs: SettingsDialogState
  systemHealth: SystemHealth
  isCheckingHealth: boolean
}

type EditableProfileField =
  | 'name'
  | 'email'
  | 'phone'
  | 'linkedin'
  | 'github'
  | 'portfolio'

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

const INITIAL_SYSTEM_HEALTH: SystemHealth = {
  database: 'healthy',
  llm: 'healthy',
  api: 'healthy',
}

const INITIAL_SETTINGS_PAGE_STATE: SettingsPageState = {
  activeTab: 'profile',
  data: {
    profile: null,
    jobStats: null,
    resumes: [],
    coverLetters: [],
    jobs: [],
  },
  isLoading: true,
  isSaving: false,
  message: null,
  validationErrors: [],
  passwords: {
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
    errors: {},
  },
  dialogs: {
    deleteApps: false,
    deleteAll: false,
    deleteAccount: false,
  },
  systemHealth: INITIAL_SYSTEM_HEALTH,
  isCheckingHealth: false,
}

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

function downloadFile(content: string, filename: string, mimeType: string) {
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

function exportApplicationsAsCsv(jobs: JobApplication[]) {
  const headers = [
    'Company',
    'Position',
    'Status',
    'Application Date',
    'Location',
    'Job URL',
    'Notes',
  ]

  const rows = jobs.map((job) => [
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

function exportCareerJournalAsTxt() {
  downloadFile(
    'Career Journal Export\n\nNo journal entries available.',
    'career_journal.txt',
    'text/plain'
  )
}

function exportAllDataAsJson(data: SettingsDataState) {
  const exportData = {
    exportDate: new Date().toISOString(),
    profile: data.profile,
    resumes: data.resumes,
    jobApplications: data.jobs,
    coverLetters: data.coverLetters,
    statistics: data.jobStats,
  }

  downloadFile(
    JSON.stringify(exportData, null, 2),
    'resuboost_export.json',
    'application/json'
  )
}

function PageLoadingState() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary-600" />
    </div>
  )
}

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
    if (!isOpen) {
      setTypedText('')
    }
  }, [isOpen])

  if (!isOpen) {
    return null
  }

  const canConfirm = !requireTyping || typedText === typingText

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
      >
        <div className="flex items-start space-x-4">
          <div
            className={cn(
              'flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full',
              confirmVariant === 'danger' ? 'bg-red-100' : 'bg-yellow-100'
            )}
          >
            <AlertTriangle
              className={cn(
                'h-5 w-5',
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
                <p className="mb-2 text-sm text-gray-700">
                  Type <strong className="font-mono">{typingText}</strong> to confirm:
                </p>
                <input
                  type="text"
                  value={typedText}
                  onChange={(e) => setTypedText(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-red-500 focus:ring-red-500"
                  aria-label="Confirmation text"
                />
              </div>
            )}
          </div>
        </div>
        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={!canConfirm}
            className={cn(
              'rounded-md px-4 py-2 text-sm font-medium text-white focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-50',
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
            'block w-full rounded-md border px-3 py-2 pr-10 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500',
            error ? 'border-red-300' : 'border-gray-300'
          )}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
        />
        <button
          type="button"
          onClick={() => setShowPassword((prev) => !prev)}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </button>
      </div>
      {error && (
        <p id={`${id}-error`} className="mt-1 text-sm text-red-600">
          {error}
        </p>
      )}
      {strength && (
        <div className="mt-2">
          <div className="mb-1 flex items-center justify-between text-xs">
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
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
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

function StatusBadge({ status, count }: { status: string; count: number }) {
  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-lg px-3 py-2',
        STATUS_COLORS[status] || 'bg-gray-100 text-gray-800'
      )}
    >
      <span className="text-sm font-medium">{status}</span>
      <span className="text-lg font-bold">{count}</span>
    </div>
  )
}

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
    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
      <div className="flex items-center space-x-3">
        <Icon className={cn('h-5 w-5', config.color)} />
        <span className="font-medium text-gray-900">{name}</span>
      </div>
      <span className={cn('text-sm font-medium', config.color)}>{config.label}</span>
    </div>
  )
}

function SettingsMessageBanner({ message }: { message: SettingsMessage | null }) {
  if (!message) {
    return null
  }

  return (
    <div
      className={cn(
        'mb-6 flex items-center space-x-2 rounded-md border p-4 text-sm',
        message.type === 'success'
          ? 'border-green-200 bg-green-50 text-green-700'
          : 'border-red-200 bg-red-50 text-red-700'
      )}
      role="alert"
    >
      {message.type === 'success' ? (
        <CheckCircle className="h-5 w-5 flex-shrink-0" />
      ) : (
        <XCircle className="h-5 w-5 flex-shrink-0" />
      )}
      <span>{message.text}</span>
    </div>
  )
}

function SettingsNavigation({
  activeTab,
  onTabChange,
}: {
  activeTab: SettingsTabId
  onTabChange: (tab: SettingsTabId) => void
}) {
  return (
    <nav className="flex-shrink-0 lg:w-64" aria-label="Settings navigation">
      <ul className="space-y-1">
        {TABS.map((tab) => (
          <li key={tab.id}>
            <button
              onClick={() => onTabChange(tab.id)}
              className={cn(
                'flex w-full items-center rounded-lg px-4 py-3 text-sm font-medium transition-colors',
                activeTab === tab.id
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              )}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              <tab.icon className="mr-3 h-5 w-5" />
              {tab.name}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}

function ProfileSettingsSection({
  user,
  profile,
  isSaving,
  getFieldError,
  onProfileFieldChange,
  onSubmit,
}: {
  user: AuthUser
  profile: Profile | null
  isSaving: boolean
  getFieldError: (field: string) => string | undefined
  onProfileFieldChange: (field: EditableProfileField, value: string) => void
  onSubmit: (event: React.FormEvent) => Promise<void>
}) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-6 text-lg font-semibold text-gray-900">Profile Information</h2>

      <form
        onSubmit={(event) => {
          void onSubmit(event)
        }}
        className="space-y-6"
      >
        <div className="flex items-center space-x-4 border-b pb-6">
          <div className="rounded-full bg-primary-100 p-4">
            <User className="h-8 w-8 text-primary-600" />
          </div>
          <div>
            <p className="font-medium text-gray-900">{user.username}</p>
            <p className="text-sm text-gray-500">{user.email}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Full Name <span className="text-red-500">*</span>
            </label>
            <input
              id="name"
              type="text"
              required
              value={profile?.name || ''}
              onChange={(event) => onProfileFieldChange('name', event.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              value={profile?.email || ''}
              onChange={(event) => onProfileFieldChange('email', event.target.value)}
              className={cn(
                'mt-1 block w-full rounded-md border px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500',
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
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
              Phone Number
            </label>
            <input
              id="phone"
              type="tel"
              value={profile?.phone || ''}
              onChange={(event) => onProfileFieldChange('phone', event.target.value)}
              className={cn(
                'mt-1 block w-full rounded-md border px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500',
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
            <label htmlFor="linkedin" className="block text-sm font-medium text-gray-700">
              LinkedIn
            </label>
            <input
              id="linkedin"
              type="url"
              value={profile?.linkedin || ''}
              onChange={(event) => onProfileFieldChange('linkedin', event.target.value)}
              className={cn(
                'mt-1 block w-full rounded-md border px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500',
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
            <label htmlFor="github" className="block text-sm font-medium text-gray-700">
              GitHub
            </label>
            <input
              id="github"
              type="url"
              value={profile?.github || ''}
              onChange={(event) => onProfileFieldChange('github', event.target.value)}
              className={cn(
                'mt-1 block w-full rounded-md border px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500',
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
            <label htmlFor="portfolio" className="block text-sm font-medium text-gray-700">
              Portfolio Website
            </label>
            <input
              id="portfolio"
              type="url"
              value={profile?.portfolio || ''}
              onChange={(event) => onProfileFieldChange('portfolio', event.target.value)}
              className={cn(
                'mt-1 block w-full rounded-md border px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500',
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

        <div className="flex justify-end pt-4">
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Save className="mr-2 h-4 w-4" />
            {isSaving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </form>
    </div>
  )
}

function StatisticsSettingsSection({
  resumesCount,
  totalApplications,
  coverLettersCount,
  offerCount,
  successRate,
  responseRate,
  statusBreakdown,
}: {
  resumesCount: number
  totalApplications: number
  coverLettersCount: number
  offerCount: number
  successRate: string
  responseRate: number
  statusBreakdown: Record<string, number>
}) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-lg bg-white p-4 shadow">
          <div className="flex items-center space-x-3">
            <div className="rounded-full bg-blue-100 p-2">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{resumesCount}</p>
              <p className="text-sm text-gray-500">Resumes</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg bg-white p-4 shadow">
          <div className="flex items-center space-x-3">
            <div className="rounded-full bg-green-100 p-2">
              <Briefcase className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalApplications}</p>
              <p className="text-sm text-gray-500">Applications</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg bg-white p-4 shadow">
          <div className="flex items-center space-x-3">
            <div className="rounded-full bg-purple-100 p-2">
              <Mail className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{coverLettersCount}</p>
              <p className="text-sm text-gray-500">Cover Letters</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg bg-white p-4 shadow">
          <div className="flex items-center space-x-3">
            <div className="rounded-full bg-yellow-100 p-2">
              <BookOpen className="h-5 w-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">0</p>
              <p className="text-sm text-gray-500">Journal Entries</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">
          Application Success Rate
        </h3>
        <div className="flex items-center space-x-6">
          <div className="flex-shrink-0">
            <div className="relative h-32 w-32">
              <svg className="h-32 w-32 -rotate-90 transform">
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
                <span className="text-2xl font-bold text-gray-900">{successRate}%</span>
              </div>
            </div>
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-600">
              {offerCount} offers out of {totalApplications} applications
            </p>
            <p className="mt-1 text-sm text-gray-500">
              Response rate: {responseRate.toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">
          Applications by Status
        </h3>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {Object.entries(statusBreakdown).map(([status, count]) => (
            <StatusBadge key={status} status={status} count={count} />
          ))}
          {Object.keys(statusBreakdown).length === 0 && (
            <p className="col-span-full py-4 text-center text-gray-500">
              No applications yet
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function SecuritySettingsSection({
  user,
  passwords,
  isSaving,
  onPasswordFieldChange,
  onSubmit,
  onSignOutAllDevices,
}: {
  user: AuthUser
  passwords: SettingsPasswordState
  isSaving: boolean
  onPasswordFieldChange: (
    field: keyof Omit<SettingsPasswordState, 'errors'>,
    value: string
  ) => void
  onSubmit: (event: React.FormEvent) => Promise<void>
  onSignOutAllDevices: () => void
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-6 text-lg font-semibold text-gray-900">Change Password</h3>
        <form
          onSubmit={(event) => {
            void onSubmit(event)
          }}
          className="max-w-md space-y-4"
        >
          <PasswordInput
            id="currentPassword"
            label="Current Password"
            value={passwords.currentPassword}
            onChange={(value) => onPasswordFieldChange('currentPassword', value)}
            error={passwords.errors.currentPassword}
          />
          <PasswordInput
            id="newPassword"
            label="New Password"
            value={passwords.newPassword}
            onChange={(value) => onPasswordFieldChange('newPassword', value)}
            error={passwords.errors.newPassword}
            showStrength
          />
          <PasswordInput
            id="confirmPassword"
            label="Confirm New Password"
            value={passwords.confirmPassword}
            onChange={(value) => onPasswordFieldChange('confirmPassword', value)}
            error={passwords.errors.confirmPassword}
          />
          <div className="pt-2">
            <button
              type="submit"
              disabled={isSaving}
              className="inline-flex items-center rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Lock className="mr-2 h-4 w-4" />
              {isSaving ? 'Updating...' : 'Update Password'}
            </button>
          </div>
        </form>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Session Information</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b py-3">
            <div>
              <p className="font-medium text-gray-900">Last Login</p>
              <p className="text-sm text-gray-500">
                {user.last_login ? new Date(user.last_login).toLocaleString() : 'Not available'}
              </p>
            </div>
          </div>
          <div className="flex items-center justify-between border-b py-3">
            <div>
              <p className="font-medium text-gray-900">Account Created</p>
              <p className="text-sm text-gray-500">
                {user.created_at ? new Date(user.created_at).toLocaleString() : 'Not available'}
              </p>
            </div>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-medium text-gray-900">Active Sessions</p>
              <p className="text-sm text-gray-500">1 active session (current)</p>
            </div>
            <button
              onClick={onSignOutAllDevices}
              className="text-sm font-medium text-red-600 hover:text-red-700"
            >
              Sign out all devices
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function DataManagementSection({
  data,
  onExportApplications,
  onExportJournal,
  onExportAll,
  onOpenDeleteAppsDialog,
  onOpenDeleteAllDialog,
  onOpenDeleteAccountDialog,
}: {
  data: SettingsDataState
  onExportApplications: () => void
  onExportJournal: () => void
  onExportAll: () => void
  onOpenDeleteAppsDialog: () => void
  onOpenDeleteAllDialog: () => void
  onOpenDeleteAccountDialog: () => void
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Export Your Data</h3>
        <p className="mb-4 text-sm text-gray-600">
          Download your data in various formats for backup or migration.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={onExportApplications}
            className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            <Download className="mr-2 h-4 w-4" />
            Export Applications (CSV)
          </button>
          <button
            onClick={onExportJournal}
            className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            <Download className="mr-2 h-4 w-4" />
            Export Journal (TXT)
          </button>
          <button
            onClick={onExportAll}
            className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            <Download className="mr-2 h-4 w-4" />
            Export All Data (JSON)
          </button>
        </div>
      </div>

      <div className="rounded-lg border-2 border-red-200 bg-white p-6 shadow">
        <div className="mb-4 flex items-center space-x-2">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <h3 className="text-lg font-semibold text-red-600">Danger Zone</h3>
        </div>
        <p className="mb-6 text-sm text-gray-600">
          These actions are irreversible. Please be certain before proceeding.
        </p>

        <div className="space-y-4">
          <div className="flex items-center justify-between border-b py-4">
            <div>
              <p className="font-medium text-gray-900">Delete All Applications</p>
              <p className="text-sm text-gray-500">
                Remove all {data.jobs.length} job applications
              </p>
            </div>
            <button
              onClick={onOpenDeleteAppsDialog}
              disabled={data.jobs.length === 0}
              className="inline-flex items-center rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Applications
            </button>
          </div>

          <div className="flex items-center justify-between border-b py-4">
            <div>
              <p className="font-medium text-gray-900">Delete All Data</p>
              <p className="text-sm text-gray-500">
                Remove all resumes, applications, and cover letters
              </p>
            </div>
            <button
              onClick={onOpenDeleteAllDialog}
              disabled={
                data.jobs.length === 0 &&
                data.resumes.length === 0 &&
                data.coverLetters.length === 0
              }
              className="inline-flex items-center rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete All Data
            </button>
          </div>

          <div className="flex items-center justify-between py-4">
            <div>
              <p className="font-medium text-gray-900">Delete Account</p>
              <p className="text-sm text-gray-500">
                Permanently delete your account and all associated data
              </p>
            </div>
            <button
              onClick={onOpenDeleteAccountDialog}
              className="inline-flex items-center rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Account
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function SystemSettingsSection({
  systemHealth,
  isCheckingHealth,
  apiBaseUrl,
  isAdmin,
  onRefresh,
}: {
  systemHealth: SystemHealth
  isCheckingHealth: boolean
  apiBaseUrl: string
  isAdmin: boolean
  onRefresh: () => void
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-white p-6 shadow">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">System Health</h3>
          <button
            onClick={onRefresh}
            disabled={isCheckingHealth}
            className="inline-flex items-center rounded-md bg-primary-50 px-3 py-1.5 text-sm font-medium text-primary-600 hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
          >
            <RefreshCw
              className={cn('mr-2 h-4 w-4', isCheckingHealth && 'animate-spin')}
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

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">API Information</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-gray-600">API Version</span>
            <span className="text-sm font-mono text-gray-900">v1.0.0</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-gray-600">API Base URL</span>
            <span className="text-sm font-mono text-gray-900">{apiBaseUrl}</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-gray-600">Frontend Version</span>
            <span className="text-sm font-mono text-gray-900">1.0.0</span>
          </div>
        </div>
      </div>

      {isAdmin && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-600" />
            <div>
              <p className="font-medium text-yellow-800">Administrator Account</p>
              <p className="mt-1 text-sm text-yellow-700">
                You have administrator privileges. Additional admin features are
                available in the admin panel.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function useSettingsPageController() {
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth()
  const [pageState, setPageState] = useState<SettingsPageState>(
    INITIAL_SETTINGS_PAGE_STATE
  )
  const {
    activeTab,
    data,
    isLoading,
    isSaving,
    message,
    validationErrors,
    passwords,
    dialogs,
    systemHealth,
    isCheckingHealth,
  } = pageState

  useEffect(() => {
    let isMounted = true

    async function hydrateSettingsPage() {
      if (authLoading) {
        return
      }

      let nextState: Partial<SettingsPageState> = { isLoading: false }

      try {
        if (isAuthenticated) {
          const [
            profileData,
            jobStatsData,
            resumesData,
            coverLettersData,
            jobsData,
          ] = await Promise.all([
            profileApi.get(),
            jobsApi.getStats(),
            resumesApi.list(),
            coverLettersApi.list(),
            jobsApi.list(),
          ])

          nextState = {
            data: {
              profile: profileData,
              jobStats: jobStatsData,
              resumes: resumesData,
              coverLetters: coverLettersData,
              jobs: jobsData,
            },
            isLoading: false,
          }
        }
      } catch (error) {
        console.error('Failed to load settings data:', error)
        nextState = {
          isLoading: false,
          message: { type: 'error', text: 'Failed to load settings data' },
        }
      }

      if (isMounted) {
        setPageState((prev) => ({ ...prev, ...nextState }))
      }
    }

    void hydrateSettingsPage()

    return () => {
      isMounted = false
    }
  }, [authLoading, isAuthenticated])

  useEffect(() => {
    if (!message) {
      return undefined
    }

    const timer = setTimeout(() => {
      setPageState((prev) => ({ ...prev, message: null }))
    }, 5000)

    return () => clearTimeout(timer)
  }, [message])

  const setActiveTab = useCallback((tab: SettingsTabId) => {
    setPageState((prev) => ({ ...prev, activeTab: tab }))
  }, [])

  const onProfileFieldChange = useCallback(
    (field: EditableProfileField, value: string) => {
      setPageState((prev) => {
        if (!prev.data.profile) {
          return prev
        }

        return {
          ...prev,
          data: {
            ...prev.data,
            profile: {
              ...prev.data.profile,
              [field]: value,
            },
          },
        }
      })
    },
    []
  )

  const onPasswordFieldChange = useCallback(
    (field: keyof Omit<SettingsPasswordState, 'errors'>, value: string) => {
      setPageState((prev) => ({
        ...prev,
        passwords: {
          ...prev.passwords,
          [field]: value,
        },
      }))
    },
    []
  )

  const setDialogOpen = useCallback(
    (dialog: keyof SettingsDialogState, isOpen: boolean) => {
      setPageState((prev) => ({
        ...prev,
        dialogs: {
          ...prev.dialogs,
          [dialog]: isOpen,
        },
      }))
    },
    []
  )

  const getFieldError = useCallback(
    (field: string) => validationErrors.find((error) => error.field === field)?.message,
    [validationErrors]
  )

  const validateProfile = useCallback(() => {
    if (!data.profile) {
      return false
    }

    const errors: ValidationError[] = []
    const emailError = validateEmail(data.profile.email || '')
    const phoneError = validatePhone(data.profile.phone || '')
    const linkedinError = validateUrl(data.profile.linkedin || '', 'linkedin')
    const githubError = validateUrl(data.profile.github || '', 'github')
    const portfolioError = validateUrl(data.profile.portfolio || '', 'portfolio')

    if (emailError) errors.push(emailError)
    if (phoneError) errors.push(phoneError)
    if (linkedinError) errors.push(linkedinError)
    if (githubError) errors.push(githubError)
    if (portfolioError) errors.push(portfolioError)

    setPageState((prev) => ({ ...prev, validationErrors: errors }))
    return errors.length === 0
  }, [data.profile])

  const handleSaveProfile = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault()

      if (!isAuthenticated || !data.profile) {
        return
      }

      if (!validateProfile()) {
        setPageState((prev) => ({
          ...prev,
          message: {
            type: 'error',
            text: 'Please fix validation errors before saving',
          },
        }))
        return
      }

      setPageState((prev) => ({
        ...prev,
        isSaving: true,
        message: null,
      }))

      try {
        const updatedProfile = await profileApi.update({
          name: data.profile.name,
          email: data.profile.email || undefined,
          phone: data.profile.phone || undefined,
          linkedin: data.profile.linkedin || undefined,
          github: data.profile.github || undefined,
          portfolio: data.profile.portfolio || undefined,
        })

        setPageState((prev) => ({
          ...prev,
          data: {
            ...prev.data,
            profile: updatedProfile,
          },
          isSaving: false,
          message: { type: 'success', text: 'Profile saved successfully!' },
        }))
      } catch (error) {
        console.error('Failed to save profile:', error)
        setPageState((prev) => ({
          ...prev,
          isSaving: false,
          message: {
            type: 'error',
            text: 'Failed to save profile. Please try again.',
          },
        }))
      }
    },
    [data.profile, isAuthenticated, validateProfile]
  )

  const handleChangePassword = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault()

      const nextErrors: Record<string, string> = {}

      if (!passwords.currentPassword) {
        nextErrors.currentPassword = 'Current password is required'
      }

      if (!passwords.newPassword) {
        nextErrors.newPassword = 'New password is required'
      } else if (passwords.newPassword.length < 8) {
        nextErrors.newPassword = 'Password must be at least 8 characters'
      }

      if (passwords.newPassword !== passwords.confirmPassword) {
        nextErrors.confirmPassword = 'Passwords do not match'
      }

      if (Object.keys(nextErrors).length > 0) {
        setPageState((prev) => ({
          ...prev,
          passwords: {
            ...prev.passwords,
            errors: nextErrors,
          },
        }))
        return
      }

      setPageState((prev) => ({
        ...prev,
        isSaving: true,
        passwords: {
          ...prev.passwords,
          errors: {},
        },
      }))

      try {
        await new Promise((resolve) => setTimeout(resolve, 1000))
        setPageState((prev) => ({
          ...prev,
          isSaving: false,
          message: { type: 'success', text: 'Password changed successfully!' },
          passwords: {
            currentPassword: '',
            newPassword: '',
            confirmPassword: '',
            errors: {},
          },
        }))
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          setPageState((prev) => ({
            ...prev,
            isSaving: false,
            passwords: {
              ...prev.passwords,
              errors: { currentPassword: 'Current password is incorrect' },
            },
          }))
          return
        }

        setPageState((prev) => ({
          ...prev,
          isSaving: false,
          message: {
            type: 'error',
            text: 'Failed to change password. Please try again.',
          },
        }))
      }
    },
    [passwords.confirmPassword, passwords.currentPassword, passwords.newPassword]
  )

  const handleDeleteAllApplications = useCallback(async () => {
    if (!isAuthenticated) {
      return
    }

    try {
      await Promise.all(data.jobs.map((job) => jobsApi.delete(job.id)))
      setPageState((prev) => ({
        ...prev,
        data: {
          ...prev.data,
          jobs: [],
          jobStats: prev.data.jobStats
            ? { ...prev.data.jobStats, total: 0, status_breakdown: {} }
            : null,
        },
        dialogs: {
          ...prev.dialogs,
          deleteApps: false,
        },
        message: {
          type: 'success',
          text: 'All applications deleted successfully',
        },
      }))
    } catch (error) {
      console.error('Failed to delete applications:', error)
      setPageState((prev) => ({
        ...prev,
        dialogs: {
          ...prev.dialogs,
          deleteApps: false,
        },
        message: {
          type: 'error',
          text: 'Failed to delete some applications',
        },
      }))
    }
  }, [data.jobs, isAuthenticated])

  const handleDeleteAllData = useCallback(async () => {
    if (!isAuthenticated) {
      return
    }

    try {
      await Promise.all([
        ...data.jobs.map((job) => jobsApi.delete(job.id)),
        ...data.resumes.map((resume) => resumesApi.delete(resume.id)),
        ...data.coverLetters.map((coverLetter) => coverLettersApi.delete(coverLetter.id)),
      ])

      setPageState((prev) => ({
        ...prev,
        data: {
          ...prev.data,
          jobs: [],
          resumes: [],
          coverLetters: [],
          jobStats: null,
        },
        dialogs: {
          ...prev.dialogs,
          deleteAll: false,
        },
        message: {
          type: 'success',
          text: 'All data deleted successfully',
        },
      }))
    } catch (error) {
      console.error('Failed to delete data:', error)
      setPageState((prev) => ({
        ...prev,
        dialogs: {
          ...prev.dialogs,
          deleteAll: false,
        },
        message: {
          type: 'error',
          text: 'Failed to delete some data',
        },
      }))
    }
  }, [data.coverLetters, data.jobs, data.resumes, isAuthenticated])

  const handleDeleteAccount = useCallback(() => {
    setPageState((prev) => ({
      ...prev,
      dialogs: {
        ...prev.dialogs,
        deleteAccount: false,
      },
      message: {
        type: 'error',
        text: 'Account deletion is not yet implemented',
      },
    }))
  }, [])

  const handleCheckSystemHealth = useCallback(async () => {
    setPageState((prev) => ({ ...prev, isCheckingHealth: true }))

    try {
      await new Promise((resolve) => setTimeout(resolve, 1500))
      setPageState((prev) => ({
        ...prev,
        isCheckingHealth: false,
        systemHealth: INITIAL_SYSTEM_HEALTH,
        message: {
          type: 'success',
          text: 'System health check completed',
        },
      }))
    } catch (error) {
      console.error('Health check failed:', error)
      setPageState((prev) => ({
        ...prev,
        isCheckingHealth: false,
        systemHealth: {
          database: 'degraded',
          llm: 'down',
          api: 'healthy',
        },
      }))
    }
  }, [])

  const handleSignOutAllDevices = useCallback(() => {
    void logout()
  }, [logout])

  const totalApplications = data.jobStats?.total || 0
  const offerCount = data.jobStats?.status_breakdown?.Offer || 0
  const successRate =
    totalApplications > 0 ? ((offerCount / totalApplications) * 100).toFixed(1) : '0'
  const responseRate = data.jobStats?.response_rate || 0
  const statusBreakdown = data.jobStats?.status_breakdown || {}

  return {
    user,
    isAuthenticated,
    authLoading,
    activeTab,
    data,
    isLoading,
    isSaving,
    message,
    passwords,
    dialogs,
    systemHealth,
    isCheckingHealth,
    totalApplications,
    offerCount,
    successRate,
    responseRate,
    statusBreakdown,
    setActiveTab,
    getFieldError,
    onProfileFieldChange,
    onPasswordFieldChange,
    handleSaveProfile,
    handleChangePassword,
    handleDeleteAllApplications,
    handleDeleteAllData,
    handleDeleteAccount,
    handleCheckSystemHealth,
    handleSignOutAllDevices,
    openDeleteAppsDialog: () => setDialogOpen('deleteApps', true),
    closeDeleteAppsDialog: () => setDialogOpen('deleteApps', false),
    openDeleteAllDialog: () => setDialogOpen('deleteAll', true),
    closeDeleteAllDialog: () => setDialogOpen('deleteAll', false),
    openDeleteAccountDialog: () => setDialogOpen('deleteAccount', true),
    closeDeleteAccountDialog: () => setDialogOpen('deleteAccount', false),
  }
}

export default function SettingsPage() {
  const controller = useSettingsPageController()
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  if (controller.authLoading || controller.isLoading) {
    return <PageLoadingState />
  }

  if (!controller.user || !controller.isAuthenticated) {
    return null
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Account & Settings</h1>
        <p className="text-gray-500">
          Manage your profile, security settings, and account data
        </p>
      </div>

      <SettingsMessageBanner message={controller.message} />

      <div className="flex flex-col gap-6 lg:flex-row">
        <SettingsNavigation
          activeTab={controller.activeTab}
          onTabChange={controller.setActiveTab}
        />

        <div className="flex-1">
          {controller.activeTab === 'profile' && (
            <ProfileSettingsSection
              user={controller.user}
              profile={controller.data.profile}
              isSaving={controller.isSaving}
              getFieldError={controller.getFieldError}
              onProfileFieldChange={controller.onProfileFieldChange}
              onSubmit={controller.handleSaveProfile}
            />
          )}

          {controller.activeTab === 'statistics' && (
            <StatisticsSettingsSection
              resumesCount={controller.data.resumes.length}
              totalApplications={controller.totalApplications}
              coverLettersCount={controller.data.coverLetters.length}
              offerCount={controller.offerCount}
              successRate={controller.successRate}
              responseRate={controller.responseRate}
              statusBreakdown={controller.statusBreakdown}
            />
          )}

          {controller.activeTab === 'security' && (
            <SecuritySettingsSection
              user={controller.user}
              passwords={controller.passwords}
              isSaving={controller.isSaving}
              onPasswordFieldChange={controller.onPasswordFieldChange}
              onSubmit={controller.handleChangePassword}
              onSignOutAllDevices={controller.handleSignOutAllDevices}
            />
          )}

          {controller.activeTab === 'data' && (
            <DataManagementSection
              data={controller.data}
              onExportApplications={() => exportApplicationsAsCsv(controller.data.jobs)}
              onExportJournal={exportCareerJournalAsTxt}
              onExportAll={() => exportAllDataAsJson(controller.data)}
              onOpenDeleteAppsDialog={controller.openDeleteAppsDialog}
              onOpenDeleteAllDialog={controller.openDeleteAllDialog}
              onOpenDeleteAccountDialog={controller.openDeleteAccountDialog}
            />
          )}

          {controller.activeTab === 'system' && (
            <SystemSettingsSection
              systemHealth={controller.systemHealth}
              isCheckingHealth={controller.isCheckingHealth}
              apiBaseUrl={apiBaseUrl}
              isAdmin={controller.user.is_admin}
              onRefresh={() => {
                void controller.handleCheckSystemHealth()
              }}
            />
          )}
        </div>
      </div>

      <ConfirmDialog
        isOpen={controller.dialogs.deleteApps}
        title="Delete All Applications"
        message={`This will permanently delete all ${controller.data.jobs.length} job applications. This action cannot be undone.`}
        confirmText="Delete Applications"
        confirmVariant="danger"
        onConfirm={() => {
          void controller.handleDeleteAllApplications()
        }}
        onCancel={controller.closeDeleteAppsDialog}
      />

      <ConfirmDialog
        isOpen={controller.dialogs.deleteAll}
        title="Delete All Data"
        message="This will permanently delete all your resumes, job applications, and cover letters. This action cannot be undone."
        confirmText="Delete All Data"
        confirmVariant="danger"
        requireTyping
        typingText="DELETE ALL DATA"
        onConfirm={() => {
          void controller.handleDeleteAllData()
        }}
        onCancel={controller.closeDeleteAllDialog}
      />

      <ConfirmDialog
        isOpen={controller.dialogs.deleteAccount}
        title="Delete Account"
        message="This will permanently delete your account and all associated data. You will be logged out immediately. This action cannot be undone."
        confirmText="Delete My Account"
        confirmVariant="danger"
        requireTyping
        typingText="DELETE MY ACCOUNT"
        onConfirm={controller.handleDeleteAccount}
        onCancel={controller.closeDeleteAccountDialog}
      />
    </div>
  )
}
