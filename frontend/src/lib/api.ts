import {
  fetchWithRetry,
  NetworkError,
  RetryExhaustedError,
  type FetchRetryOptions,
} from './fetchWithRetry'

import type {
  AuthTokens,
  User,
  Resume,
  ATSAnalysis,
  JobApplication,
  JobStats,
  CoverLetter,
  Profile,
  TailorResumeResponse,
  AnswerQuestionResponse,
  InterviewPrepResponse,
  CompanyFilter,
  KeywordFilter,
  QuestionTemplate,
  JobCheckResult,
} from '@/types'

/**
 * API base URL from environment variable
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Default fetch options for cookie-based authentication
 *
 * credentials: 'include' ensures HTTP-only cookies are sent with requests
 * This is essential for the cookie-based authentication to work across origins
 */
const DEFAULT_FETCH_OPTIONS: RequestInit = {
  credentials: 'include',
}

/**
 * Type for API error response
 */
interface ApiErrorResponse {
  detail?: string
  message?: string
}

/**
 * Custom API error class with status code
 */
export class ApiError extends Error {
  status: number
  details?: unknown
  isOffline: boolean
  isRetryExhausted: boolean

  constructor(
    message: string,
    status: number,
    details?: unknown,
    options?: { isOffline?: boolean; isRetryExhausted?: boolean }
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
    this.isOffline = options?.isOffline ?? false
    this.isRetryExhausted = options?.isRetryExhausted ?? false
  }
}

/**
 * Request queue item for offline mode
 */
interface QueuedRequest {
  id: string
  endpoint: string
  options: RequestInit
  timestamp: number
  resolve: (value: unknown) => void
  reject: (reason: unknown) => void
}

/**
 * Request queue manager for offline mode
 * Queues requests when offline and processes them when back online
 */
class RequestQueueManager {
  private queue: QueuedRequest[] = []
  private isProcessing = false
  private isOnline = true
  private listeners: Set<(queue: QueuedRequest[]) => void> = new Set()
  private storageKey = 'resuboost_request_queue'

  constructor() {
    // Initialize online status and event listeners
    if (typeof window !== 'undefined') {
      this.isOnline = navigator.onLine
      window.addEventListener('online', this.handleOnline)
      window.addEventListener('offline', this.handleOffline)
      // Load persisted queue
      this.loadQueue()
    }
  }

  /**
   * Handle coming back online
   */
  private handleOnline = (): void => {
    this.isOnline = true
    void this.processQueue()
  }

  /**
   * Handle going offline
   */
  private handleOffline = (): void => {
    this.isOnline = false
  }

  /**
   * Generate unique request ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Load persisted queue from localStorage
   */
  private loadQueue(): void {
    try {
      const stored = localStorage.getItem(this.storageKey)
      if (stored) {
        const parsed = JSON.parse(stored) as Array<Omit<QueuedRequest, 'resolve' | 'reject'>>
        // Restore queue items without callbacks (they'll be new promises)
        this.queue = parsed.map((item) => ({
          ...item,
          resolve: () => {},
          reject: () => {},
        }))
      }
    } catch (error) {
      // Log queue loading errors for debugging but don't throw
      console.warn('Failed to load request queue from localStorage:', error)
    }
  }

  /**
   * Persist queue to localStorage
   */
  private saveQueue(): void {
    try {
      const toSave = this.queue.map(({ id, endpoint, options, timestamp }) => ({
        id,
        endpoint,
        options,
        timestamp,
      }))
      localStorage.setItem(this.storageKey, JSON.stringify(toSave))
    } catch (error) {
      // Log storage errors for debugging but don't throw (localStorage may be full or disabled)
      console.warn('Failed to save request queue to localStorage:', error)
    }
  }

  /**
   * Add a request to the queue
   */
  enqueue<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    return new Promise((resolve, reject) => {
      const request: QueuedRequest = {
        id: this.generateId(),
        endpoint,
        options,
        timestamp: Date.now(),
        resolve: resolve as (value: unknown) => void,
        reject,
      }

      this.queue.push(request)
      this.saveQueue()
      this.notifyListeners()

      // If we're online, try to process immediately
      if (this.isOnline) {
        void this.processQueue()
      }
    })
  }

  /**
   * Process queued requests
   */
  async processQueue(): Promise<void> {
    if (this.isProcessing || !this.isOnline || this.queue.length === 0) {
      return
    }

    this.isProcessing = true

    while (this.queue.length > 0 && this.isOnline) {
      const request = this.queue[0]
      if (!request) {
        break
      }

      try {
        const response = await fetchWithRetry(`${API_BASE_URL}${request.endpoint}`, {
          ...request.options,
          maxRetries: 2,
          initialDelay: 500,
        })

        if (!response.ok) {
          throw new ApiError(
            `HTTP error! status: ${response.status}`,
            response.status
          )
        }

        const data: unknown = await response.json()
        request.resolve(data)

        // Remove from queue on success
        this.queue.shift()
        this.saveQueue()
        this.notifyListeners()
      } catch (error) {
        if (error instanceof NetworkError) {
          // Network error, stop processing and wait for online
          this.isOnline = false
          break
        }

        // Other errors, reject and remove from queue
        request.reject(error)
        this.queue.shift()
        this.saveQueue()
        this.notifyListeners()
      }
    }

    this.isProcessing = false
  }

  /**
   * Get current queue
   */
  getQueue(): QueuedRequest[] {
    return [...this.queue]
  }

  /**
   * Get queue length
   */
  get length(): number {
    return this.queue.length
  }

  /**
   * Check if queue has pending requests
   */
  get hasPending(): boolean {
    return this.queue.length > 0
  }

  /**
   * Clear the queue
   */
  clear(): void {
    this.queue.forEach((request) => {
      request.reject(new Error('Queue cleared'))
    })
    this.queue = []
    this.saveQueue()
    this.notifyListeners()
  }

  /**
   * Remove a specific request from the queue
   */
  remove(id: string): void {
    const index = this.queue.findIndex((r) => r.id === id)
    if (index !== -1) {
      const removed = this.queue.splice(index, 1)
      if (removed[0]) {
        removed[0].reject(new Error('Request cancelled'))
      }
      this.saveQueue()
      this.notifyListeners()
    }
  }

  /**
   * Subscribe to queue changes
   */
  subscribe(listener: (queue: QueuedRequest[]) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /**
   * Notify listeners of queue changes
   */
  private notifyListeners(): void {
    const queue = this.getQueue()
    this.listeners.forEach((listener) => listener(queue))
  }

  /**
   * Cleanup
   */
  destroy(): void {
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this.handleOnline)
      window.removeEventListener('offline', this.handleOffline)
    }
  }
}

/**
 * Singleton request queue manager instance
 */
export const requestQueue = new RequestQueueManager()

/**
 * Default retry options for API requests
 */
const defaultRetryOptions: FetchRetryOptions = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  onRetry: (attempt, delay, error) => {
    console.warn(`API request retry attempt ${attempt} after ${delay}ms`, error)
  },
}

/**
 * Make an API request with proper error handling and retry logic
 *
 * All requests include credentials: 'include' to send HTTP-only cookies
 * for cookie-based authentication.
 *
 * @param endpoint - API endpoint (without base URL)
 * @param options - Fetch options including retry configuration
 * @returns Response data
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit & FetchRetryOptions = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  const { maxRetries, initialDelay, maxDelay, onRetry, ...fetchOptions } = {
    ...defaultRetryOptions,
    ...options,
  }

  try {
    const response = await fetchWithRetry(url, {
      ...DEFAULT_FETCH_OPTIONS,
      ...fetchOptions,
      headers,
      maxRetries,
      initialDelay,
      maxDelay,
      onRetry,
    })

    if (!response.ok) {
      let errorMessage = `HTTP error! status: ${response.status}`
      let errorDetails: unknown

      try {
        const errorData = (await response.json()) as ApiErrorResponse
        errorMessage = errorData.detail ?? errorData.message ?? errorMessage
        errorDetails = errorData
      } catch (parseError) {
        // Log parsing failure but use default error message
        console.debug('Failed to parse error response body:', parseError)
      }

      throw new ApiError(errorMessage, response.status, errorDetails)
    }

    // Handle empty responses
    const text = await response.text()
    if (!text) {
      return {} as T
    }

    return JSON.parse(text) as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }

    if (error instanceof NetworkError) {
      throw new ApiError(
        'Unable to connect to server. Please check your internet connection.',
        0,
        undefined,
        { isOffline: true }
      )
    }

    if (error instanceof RetryExhaustedError) {
      throw new ApiError(
        'Server is temporarily unavailable. Please try again later.',
        503,
        { attempts: error.attempts },
        { isRetryExhausted: true }
      )
    }

    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0
    )
  }
}

/**
 * Make an authenticated API request with retry logic
 *
 * With HTTP-only cookie authentication, the token parameter is optional
 * and kept for backward compatibility. Cookies are automatically sent
 * with credentials: 'include'.
 *
 * @param endpoint - API endpoint
 * @param token - Access token (optional, deprecated - use cookies instead)
 * @param options - Fetch options
 * @returns Response data
 */
async function authenticatedRequest<T>(
  endpoint: string,
  token?: string,
  options: RequestInit & FetchRetryOptions = {}
): Promise<T> {
  // If token is provided (for backward compatibility), include it in header
  // The server will prefer cookies but fall back to Authorization header
  const headers: HeadersInit = token
    ? {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      }
    : options.headers ?? {}

  return apiRequest<T>(endpoint, {
    ...options,
    headers,
  })
}

/**
 * Make an authenticated API request using cookie-based auth only
 *
 * This is the preferred method for browser-based requests.
 * Cookies are automatically sent with credentials: 'include'.
 *
 * @param endpoint - API endpoint
 * @param options - Fetch options
 * @returns Response data
 */
async function cookieAuthRequest<T>(
  endpoint: string,
  options: RequestInit & FetchRetryOptions = {}
): Promise<T> {
  return apiRequest<T>(endpoint, options)
}

/**
 * Make an authenticated request that can be queued when offline
 * Use for non-critical requests that can be retried later
 *
 * @param endpoint - API endpoint
 * @param token - Access token (optional, deprecated - use cookies instead)
 * @param options - Fetch options
 */
function queueableRequest<T>(
  endpoint: string,
  token?: string,
  options: RequestInit = {}
): Promise<T> {
  // Check if we're offline
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    // Add Authorization header if token provided (backward compatibility)
    if (token) {
      ;(headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }

    return requestQueue.enqueue<T>(endpoint, {
      ...DEFAULT_FETCH_OPTIONS,
      ...options,
      headers,
    })
  }

  // Online, make request normally
  return authenticatedRequest<T>(endpoint, token, options)
}

/**
 * Authentication API
 *
 * Uses HTTP-only cookies for secure token storage.
 * Cookies are automatically set by the server on login/refresh
 * and sent with all requests via credentials: 'include'.
 */
export const authApi = {
  /**
   * Login with username and password
   *
   * On success, the server sets HTTP-only cookies containing the tokens.
   * The response body also contains tokens for backward compatibility.
   */
  login: async (username: string, password: string): Promise<AuthTokens> => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    try {
      const response = await fetchWithRetry(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
        credentials: 'include', // Essential for receiving cookies
        ...defaultRetryOptions,
      })

      if (!response.ok) {
        let errorMessage = 'Login failed'
        try {
          const errorData = (await response.json()) as ApiErrorResponse
          errorMessage = errorData.detail ?? errorMessage
        } catch (parseError) {
          // Log parsing failure but use default error message
          console.debug('Failed to parse login error response:', parseError)
        }
        throw new ApiError(errorMessage, response.status)
      }

      return response.json() as Promise<AuthTokens>
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      if (error instanceof NetworkError) {
        throw new ApiError(
          'Unable to connect to server. Please check your internet connection.',
          0,
          undefined,
          { isOffline: true }
        )
      }
      throw new ApiError('Login failed', 0)
    }
  },

  /**
   * Register a new user
   */
  register: async (data: {
    username: string
    email: string
    password: string
    full_name?: string
  }): Promise<User> => {
    return apiRequest<User>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  /**
   * Refresh access token using HTTP-only cookie
   *
   * The refresh token is read from the HTTP-only cookie automatically.
   * A refreshToken parameter is accepted for backward compatibility.
   */
  refresh: async (refreshToken?: string): Promise<AuthTokens> => {
    return apiRequest<AuthTokens>('/api/auth/refresh', {
      method: 'POST',
      // Include refresh_token in body for backward compatibility with API clients
      body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : '{}',
    })
  },

  /**
   * Logout and clear authentication cookies
   *
   * This endpoint clears the HTTP-only cookies on the server side.
   */
  logout: async (): Promise<void> => {
    try {
      await apiRequest<{ message: string }>('/api/auth/logout', {
        method: 'POST',
      })
    } catch (error) {
      // Logout should succeed even if request fails (e.g., already logged out)
      console.warn('Logout request failed:', error)
    }
  },

  /**
   * Get current user info using cookie-based auth
   *
   * @param token - Optional access token (deprecated, use cookies instead)
   */
  me: async (token?: string): Promise<User> => {
    return authenticatedRequest<User>('/api/auth/me', token)
  },

  /**
   * Check if user is authenticated by attempting to get user info
   *
   * This is useful for checking auth status on page load when
   * using HTTP-only cookies (since JS cannot read them).
   */
  checkAuth: async (): Promise<User | null> => {
    try {
      return await cookieAuthRequest<User>('/api/auth/me')
    } catch (error) {
      // Not authenticated or error - return null (expected behavior for auth check)
      if (error instanceof ApiError && error.status !== 401) {
        // Log unexpected errors (not 401 which is expected for unauthenticated)
        console.debug('Auth check failed with unexpected error:', error)
      }
      return null
    }
  },

  /**
   * Change password
   *
   * @param token - Optional access token (deprecated, use cookies instead)
   */
  changePassword: async (
    currentPassword: string,
    newPassword: string,
    token?: string
  ): Promise<void> => {
    await authenticatedRequest('/api/auth/change-password', token, {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    })
  },
}

/**
 * Profile API
 */
export const profileApi = {
  get: async (token?: string): Promise<Profile> => {
    return authenticatedRequest<Profile>('/api/profile', token)
  },

  update: async (data: Partial<Profile>, token?: string): Promise<Profile> => {
    return authenticatedRequest<Profile>('/api/profile', token, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },
}

/**
 * Resumes API
 */
export const resumesApi = {
  list: async (token?: string): Promise<Resume[]> => {
    return authenticatedRequest<Resume[]>('/api/resumes', token)
  },

  get: async (id: number, token?: string): Promise<Resume> => {
    return authenticatedRequest<Resume>(`/api/resumes/${id}`, token)
  },

  create: async (data: Partial<Resume>, token?: string): Promise<Resume> => {
    return authenticatedRequest<Resume>('/api/resumes', token, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  update: async (
    id: number,
    data: Partial<Resume>,
    token?: string
  ): Promise<Resume> => {
    return authenticatedRequest<Resume>(`/api/resumes/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  delete: async (id: number, token?: string): Promise<void> => {
    await authenticatedRequest(`/api/resumes/${id}`, token, {
      method: 'DELETE',
    })
  },

  analyze: async (id: number, token?: string): Promise<ATSAnalysis> => {
    return authenticatedRequest<ATSAnalysis>(
      `/api/resumes/${id}/analyze`,
      token,
      { method: 'POST' }
    )
  },

  analyzeContent: async (
    resumeContent: string,
    jobDescription?: string,
    token?: string
  ): Promise<ATSAnalysis> => {
    return authenticatedRequest<ATSAnalysis>('/api/resumes/analyze', token, {
      method: 'POST',
      body: JSON.stringify({
        resume_content: resumeContent,
        job_description: jobDescription,
      }),
    })
  },

  upload: async (file: File, token?: string): Promise<Resume> => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const headers: HeadersInit = token
        ? { Authorization: `Bearer ${token}` }
        : {}

      const response = await fetchWithRetry(`${API_BASE_URL}/api/resumes/upload`, {
        method: 'POST',
        headers,
        body: formData,
        credentials: 'include',
        ...defaultRetryOptions,
      })

      if (!response.ok) {
        let errorMessage = 'Upload failed'
        try {
          const errorData = (await response.json()) as ApiErrorResponse
          errorMessage = errorData.detail ?? errorMessage
        } catch (parseError) {
          // Log parsing failure but use default error message
          console.debug('Failed to parse upload error response:', parseError)
        }
        throw new ApiError(errorMessage, response.status)
      }

      return response.json() as Promise<Resume>
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      if (error instanceof NetworkError) {
        throw new ApiError(
          'Unable to upload file. Please check your internet connection.',
          0,
          undefined,
          { isOffline: true }
        )
      }
      throw new ApiError('Upload failed', 0)
    }
  },
}

/**
 * Jobs API
 */
export const jobsApi = {
  list: async (token?: string): Promise<JobApplication[]> => {
    return authenticatedRequest<JobApplication[]>('/api/jobs', token)
  },

  get: async (id: number, token?: string): Promise<JobApplication> => {
    return authenticatedRequest<JobApplication>(`/api/jobs/${id}`, token)
  },

  create: async (
    data: Partial<JobApplication>,
    token?: string
  ): Promise<JobApplication> => {
    return authenticatedRequest<JobApplication>('/api/jobs', token, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  update: async (
    id: number,
    data: Partial<JobApplication>,
    token?: string
  ): Promise<JobApplication> => {
    return authenticatedRequest<JobApplication>(`/api/jobs/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  /**
   * Update job with offline queue support
   * Changes will be queued if offline and synced when back online
   */
  updateQueued: async (
    id: number,
    data: Partial<JobApplication>,
    token?: string
  ): Promise<JobApplication> => {
    return queueableRequest<JobApplication>(`/api/jobs/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  delete: async (id: number, token?: string): Promise<void> => {
    await authenticatedRequest(`/api/jobs/${id}`, token, {
      method: 'DELETE',
    })
  },

  getStats: async (token?: string): Promise<JobStats> => {
    return authenticatedRequest<JobStats>('/api/jobs/stats', token)
  },

  updateStatus: async (
    id: number,
    status: string,
    token?: string
  ): Promise<JobApplication> => {
    return authenticatedRequest<JobApplication>(`/api/jobs/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    })
  },

  /**
   * Update job status with offline queue support
   */
  updateStatusQueued: async (
    id: number,
    status: string,
    token?: string
  ): Promise<JobApplication> => {
    return queueableRequest<JobApplication>(`/api/jobs/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    })
  },
}

/**
 * Cover Letters API
 */
export const coverLettersApi = {
  list: async (token?: string): Promise<CoverLetter[]> => {
    return authenticatedRequest<CoverLetter[]>('/api/cover-letters', token)
  },

  get: async (id: number, token?: string): Promise<CoverLetter> => {
    return authenticatedRequest<CoverLetter>(`/api/cover-letters/${id}`, token)
  },

  create: async (
    data: Partial<CoverLetter>,
    token?: string
  ): Promise<CoverLetter> => {
    return authenticatedRequest<CoverLetter>('/api/cover-letters', token, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  update: async (
    id: number,
    data: Partial<CoverLetter>,
    token?: string
  ): Promise<CoverLetter> => {
    return authenticatedRequest<CoverLetter>(`/api/cover-letters/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  delete: async (id: number, token?: string): Promise<void> => {
    await authenticatedRequest(`/api/cover-letters/${id}`, token, {
      method: 'DELETE',
    })
  },
}

/**
 * AI API
 */
export const aiApi = {
  tailorResume: async (
    resumeContent: string,
    jobDescription: string,
    token?: string
  ): Promise<TailorResumeResponse> => {
    return authenticatedRequest<TailorResumeResponse>('/api/ai/tailor-resume', token, {
      method: 'POST',
      body: JSON.stringify({
        resume_content: resumeContent,
        job_description: jobDescription,
      }),
    })
  },

  answerQuestion: async (
    question: string,
    context?: string,
    token?: string
  ): Promise<AnswerQuestionResponse> => {
    return authenticatedRequest<AnswerQuestionResponse>('/api/ai/answer', token, {
      method: 'POST',
      body: JSON.stringify({ question, context }),
    })
  },

  interviewPrep: async (
    question: string,
    resumeContent?: string,
    jobDescription?: string,
    token?: string
  ): Promise<InterviewPrepResponse> => {
    return authenticatedRequest<InterviewPrepResponse>('/api/ai/interview-prep', token, {
      method: 'POST',
      body: JSON.stringify({
        question,
        resume_content: resumeContent,
        job_description: jobDescription,
      }),
    })
  },

  generateCoverLetter: async (
    resumeContent: string,
    jobDescription: string,
    companyName: string,
    token?: string
  ): Promise<{ cover_letter: string }> => {
    return authenticatedRequest<{ cover_letter: string }>(
      '/api/ai/generate-cover-letter',
      token,
      {
        method: 'POST',
        body: JSON.stringify({
          resume_content: resumeContent,
          job_description: jobDescription,
          company_name: companyName,
        }),
      }
    )
  },

  optimizeResume: async (
    resumeContent: string,
    jobDescription: string,
    token?: string
  ): Promise<{ optimized_resume: string; suggestions: string[] }> => {
    return authenticatedRequest<{ optimized_resume: string; suggestions: string[] }>(
      '/api/ai/optimize-resume',
      token,
      {
        method: 'POST',
        body: JSON.stringify({
          resume_content: resumeContent,
          job_description: jobDescription,
        }),
      }
    )
  },
}

/**
 * Filters API
 */
export const filtersApi = {
  // Company filters
  listCompanyFilters: async (token?: string): Promise<CompanyFilter[]> => {
    return authenticatedRequest<CompanyFilter[]>('/api/filters/companies', token)
  },

  // Alias for backwards compatibility
  getCompanyFilters: async (token?: string): Promise<CompanyFilter[]> => {
    return authenticatedRequest<CompanyFilter[]>('/api/filters/companies', token)
  },

  createCompanyFilter: async (
    data: Omit<CompanyFilter, 'id' | 'created_at'>,
    token?: string
  ): Promise<CompanyFilter> => {
    return authenticatedRequest<CompanyFilter>('/api/filters/companies', token, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteCompanyFilter: async (id: string, token?: string): Promise<void> => {
    await authenticatedRequest(`/api/filters/companies/${id}`, token, {
      method: 'DELETE',
    })
  },

  // Keyword filters
  listKeywordFilters: async (token?: string): Promise<KeywordFilter[]> => {
    return authenticatedRequest<KeywordFilter[]>('/api/filters/keywords', token)
  },

  // Alias for backwards compatibility
  getKeywordFilters: async (token?: string): Promise<KeywordFilter[]> => {
    return authenticatedRequest<KeywordFilter[]>('/api/filters/keywords', token)
  },

  createKeywordFilter: async (
    data: Omit<KeywordFilter, 'id' | 'created_at'>,
    token?: string
  ): Promise<KeywordFilter> => {
    return authenticatedRequest<KeywordFilter>('/api/filters/keywords', token, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteKeywordFilter: async (id: string, token?: string): Promise<void> => {
    await authenticatedRequest(`/api/filters/keywords/${id}`, token, {
      method: 'DELETE',
    })
  },

  // Question templates
  listQuestionTemplates: async (token?: string): Promise<QuestionTemplate[]> => {
    return authenticatedRequest<QuestionTemplate[]>('/api/filters/questions', token)
  },

  createQuestionTemplate: async (
    data: Omit<QuestionTemplate, 'id' | 'created_at' | 'updated_at'>,
    token?: string
  ): Promise<QuestionTemplate> => {
    return authenticatedRequest<QuestionTemplate>('/api/filters/questions', token, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  updateQuestionTemplate: async (
    id: string,
    data: Partial<QuestionTemplate>,
    token?: string
  ): Promise<QuestionTemplate> => {
    return authenticatedRequest<QuestionTemplate>(`/api/filters/questions/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  deleteQuestionTemplate: async (id: string, token?: string): Promise<void> => {
    await authenticatedRequest(`/api/filters/questions/${id}`, token, {
      method: 'DELETE',
    })
  },

  // Job check
  checkJob: async (
    title: string,
    company: string,
    description?: string,
    token?: string
  ): Promise<JobCheckResult> => {
    return authenticatedRequest<JobCheckResult>('/api/filters/check-job', token, {
      method: 'POST',
      body: JSON.stringify({ title, company, description }),
    })
  },
}

/**
 * Account/Settings API
 */
export const accountApi = {
  deleteAccount: async (password: string, token?: string): Promise<void> => {
    await authenticatedRequest('/api/auth/delete-account', token, {
      method: 'DELETE',
      body: JSON.stringify({ password }),
    })
  },

  exportData: async (token?: string): Promise<Blob> => {
    try {
      const headers: HeadersInit = token
        ? { Authorization: `Bearer ${token}` }
        : {}

      const response = await fetchWithRetry(`${API_BASE_URL}/api/auth/export-data`, {
        method: 'GET',
        headers,
        credentials: 'include',
        ...defaultRetryOptions,
      })

      if (!response.ok) {
        throw new ApiError('Failed to export data', response.status)
      }

      return response.blob()
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      if (error instanceof NetworkError) {
        throw new ApiError(
          'Unable to export data. Please check your internet connection.',
          0,
          undefined,
          { isOffline: true }
        )
      }
      throw new ApiError('Failed to export data', 0)
    }
  },
}

/**
 * Utility functions for working with the request queue
 */
export const offlineUtils = {
  /**
   * Get the request queue manager instance
   */
  getQueue: () => requestQueue,

  /**
   * Check if there are pending offline requests
   */
  hasPendingRequests: () => requestQueue.hasPending,

  /**
   * Get count of pending requests
   */
  getPendingCount: () => requestQueue.length,

  /**
   * Subscribe to queue changes
   */
  onQueueChange: (callback: (count: number) => void) => {
    return requestQueue.subscribe((queue) => callback(queue.length))
  },

  /**
   * Manually trigger queue processing
   */
  processQueue: () => requestQueue.processQueue(),

  /**
   * Clear all pending requests
   */
  clearQueue: () => requestQueue.clear(),
}
