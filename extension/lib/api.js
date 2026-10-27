/**
 * ResuBoost AI Extension API Client
 * Talks to the FastAPI backend (backend/app/routers) on behalf of the popup
 * and the background service worker.
 *
 * Endpoints used:
 *   POST /api/auth/login    OAuth2 form login, returns { access_token }
 *   GET  /api/auth/me       current user
 *   POST /api/auth/refresh  new access token (refresh token from cookie or body)
 *   GET  /api/profile       profile used for autofill
 *   POST /api/jobs          create a job application (JobCreate schema)
 */

export const DEFAULT_API_URL = 'http://localhost:8000/api'

// Values accepted by ApplicationSource in backend/app/schemas/job.py
const APPLICATION_SOURCES = ['LinkedIn', 'Indeed', 'Glassdoor', 'Company Site', 'Referral', 'Recruiter', 'Job Fair', 'Networking', 'Other']

export class ApiError extends Error {
  /**
   * @param {string} message Error message (backend `detail` when available)
   * @param {number} status HTTP status code
   */
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export class ApiClient {
  /**
   * @param {string} [baseUrl] API base URL including the /api prefix
   * @param {Function} [fetchImpl] fetch implementation (injectable for tests)
   */
  constructor(baseUrl = DEFAULT_API_URL, fetchImpl) {
    this.baseUrl = baseUrl.replace(/\/+$/, '')
    this.fetch = fetchImpl || globalThis.fetch.bind(globalThis)
  }

  /**
   * Perform a request and decode the JSON response.
   * @param {string} path Path below the base URL, e.g. '/jobs'
   * @param {Object} [options] fetch options
   * @returns {Promise<any>} Parsed JSON body (null for empty bodies)
   */
  async request(path, options = {}) {
    let response
    try {
      response = await this.fetch(`${this.baseUrl}${path}`, {
        credentials: 'include',
        ...options,
      })
    } catch (error) {
      throw new ApiError(`Cannot reach ResuBoost API at ${this.baseUrl}: ${error.message}`, 0)
    }

    const text = await response.text()
    let body = null
    if (text) {
      try {
        body = JSON.parse(text)
      } catch {
        body = text
      }
    }

    if (!response.ok) {
      throw new ApiError(errorMessage(body, response.status), response.status)
    }
    return body
  }

  /**
   * Log in with username and password.
   * The backend returns only the access token in the body; the refresh token
   * is set as an HTTP-only cookie, so refresh_token is null unless a future
   * backend version includes it.
   * @param {string} username Username
   * @param {string} password Password
   * @returns {Promise<{access_token: string, refresh_token: string|null, user: Object}>}
   */
  async login(username, password) {
    const form = new URLSearchParams({ username, password })
    const token = await this.request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    })

    const user = await this.getCurrentUser(token.access_token)

    return {
      access_token: token.access_token,
      refresh_token: token.refresh_token || null,
      user,
    }
  }

  /**
   * Fetch the logged-in user. Adds `name` (from full_name) for the popup.
   * @param {string} accessToken Bearer token
   * @returns {Promise<Object>} User
   */
  async getCurrentUser(accessToken) {
    const user = await this.request('/auth/me', { headers: authHeaders(accessToken) })
    return { ...user, name: user.full_name || user.username }
  }

  /**
   * Exchange a refresh token for a new access token.
   * @param {string|null} refreshToken Refresh token (the cookie is also sent)
   * @returns {Promise<{access_token: string, refresh_token: string|null}>}
   */
  async refreshToken(refreshToken) {
    const options = { method: 'POST' }
    if (refreshToken) {
      options.headers = { 'Content-Type': 'application/json' }
      options.body = JSON.stringify({ refresh_token: refreshToken })
    }
    const token = await this.request('/auth/refresh', options)
    return {
      access_token: token.access_token,
      refresh_token: token.refresh_token || refreshToken || null,
    }
  }

  /**
   * Fetch the profile and shape it for the autofill fillers
   * (content/fillers/*.js read firstName, lastName, linkedIn, website, ...).
   * The backend fields are kept alongside.
   * @param {string} accessToken Bearer token
   * @returns {Promise<Object>} Autofill profile data
   */
  async getProfile(accessToken) {
    const profile = await this.request('/profile', { headers: authHeaders(accessToken) })
    return toAutofillProfile(profile)
  }

  /**
   * Create a job application in the tracker.
   * Accepts the extension's job shape ({ title, company, location, url,
   * description, status, source }) and maps it to the backend JobCreate schema.
   * @param {string} accessToken Bearer token
   * @param {Object} job Job details
   * @returns {Promise<Object>} Created job (JobResponse)
   */
  async createJobApplication(accessToken, job) {
    return this.request('/jobs', {
      method: 'POST',
      headers: { ...authHeaders(accessToken), 'Content-Type': 'application/json' },
      body: JSON.stringify(toJobCreate(job)),
    })
  }
}

function authHeaders(accessToken) {
  if (!accessToken) {
    throw new ApiError('Not authenticated. Please log in.', 401)
  }
  return { Authorization: `Bearer ${accessToken}` }
}

function errorMessage(body, status) {
  if (body && typeof body === 'object') {
    const { detail } = body
    if (typeof detail === 'string') return detail
    // FastAPI validation errors: [{ loc, msg, type }, ...]
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
    }
    if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
      return detail.message
    }
  }
  if (typeof body === 'string' && body) return body
  return `Request failed with status ${status}`
}

/**
 * Map a backend ProfileResponse to the field names the fillers read.
 * @param {Object} profile ProfileResponse
 * @returns {Object} Autofill profile data
 */
export function toAutofillProfile(profile) {
  const fullName = (profile.name || '').trim()
  const parts = fullName.split(/\s+/).filter(Boolean)
  const firstName = parts[0] || ''
  const lastName = parts.slice(1).join(' ')

  return {
    ...profile,
    fullName,
    firstName,
    lastName,
    email: profile.email || '',
    phone: profile.phone || '',
    linkedIn: profile.linkedin || '',
    github: profile.github || '',
    website: profile.portfolio || '',
    portfolio: profile.portfolio || '',
  }
}

/**
 * Map the extension's job shape to the backend JobCreate schema.
 * @param {Object} job Job details from a content script
 * @returns {Object} JobCreate payload
 */
export function toJobCreate(job) {
  const payload = {
    company: job.company || 'Unknown company',
    position: job.title || job.position || 'Unknown position',
    status: job.status || 'Bookmarked',
  }
  if (job.location) payload.location = job.location
  if (job.url) payload.job_url = job.url
  if (job.description) payload.job_description = job.description

  const source = normalizeSource(job.source)
  if (source) payload.application_source = source

  return payload
}

function normalizeSource(source) {
  if (!source) return null
  const match = APPLICATION_SOURCES.find((s) => s.toLowerCase() === String(source).toLowerCase())
  return match || 'Other'
}
