import { ApiError } from '@/lib/api'

/**
 * User-friendly error messages mapped to HTTP status codes.
 *
 * These messages are designed to be helpful and actionable for end users
 * without exposing sensitive technical details.
 */
const HTTP_STATUS_MESSAGES: Record<number, string> = {
  400: 'The request was invalid. Please check your input and try again.',
  401: 'Your session has expired. Please log in again.',
  403: 'You don\'t have permission to perform this action.',
  404: 'The requested resource was not found.',
  409: 'This conflicts with existing data. Please refresh and try again.',
  422: 'The submitted data is invalid. Please check your input.',
  429: 'Too many requests. Please wait a moment and try again.',
  500: 'Something went wrong on our end. Please try again later.',
  502: 'The server is temporarily unavailable. Please try again later.',
  503: 'The service is temporarily unavailable. Please try again later.',
  504: 'The request timed out. Please try again later.',
}

/**
 * Default error message when no specific mapping is found
 */
const DEFAULT_ERROR_MESSAGE = 'An unexpected error occurred. Please try again.'

/**
 * Error message for network connectivity failures
 */
const NETWORK_ERROR_MESSAGE =
  'Unable to connect to the server. Please check your internet connection.'

/**
 * Error message when all retry attempts are exhausted
 */
const RETRY_EXHAUSTED_MESSAGE =
  'The server is not responding. Please try again later.'

/**
 * Extract a user-friendly error message from various error shapes.
 *
 * Handles:
 * - ApiError instances (from the app's API layer)
 * - Standard Error instances
 * - String errors
 * - Unknown error shapes with message/detail properties
 * - Network and offline errors
 *
 * @param error - The error to extract a message from
 * @returns A user-friendly error message string
 *
 * @example
 * ```ts
 * try {
 *   await someApiCall()
 * } catch (error) {
 *   const message = getErrorMessage(error)
 *   toast.error(message)
 * }
 * ```
 */
export function getErrorMessage(error: unknown): string {
  // Handle ApiError from the app's API layer
  if (error instanceof ApiError) {
    // Network / offline errors
    if (error.isOffline) {
      return NETWORK_ERROR_MESSAGE
    }

    // Retry exhausted
    if (error.isRetryExhausted) {
      return RETRY_EXHAUSTED_MESSAGE
    }

    // Check for a mapped message based on HTTP status code
    const mappedMessage = HTTP_STATUS_MESSAGES[error.status]
    if (mappedMessage) {
      return mappedMessage
    }

    // Fall back to the error's own message if it exists and is not a
    // generic HTTP status line (e.g. "HTTP error! status: 500")
    if (error.message && !error.message.startsWith('HTTP error!')) {
      return error.message
    }

    return DEFAULT_ERROR_MESSAGE
  }

  // Handle standard Error instances
  if (error instanceof Error) {
    // Check for common network error patterns
    const msg = error.message.toLowerCase()
    if (
      msg.includes('failed to fetch') ||
      msg.includes('network request failed') ||
      msg.includes('networkerror') ||
      msg.includes('load failed') ||
      msg.includes('network error')
    ) {
      return NETWORK_ERROR_MESSAGE
    }

    // Return the error message if it looks user-friendly (not a stack trace or technical dump)
    if (error.message && error.message.length < 200) {
      return error.message
    }

    return DEFAULT_ERROR_MESSAGE
  }

  // Handle string errors
  if (typeof error === 'string') {
    return error
  }

  // Handle objects with detail or message properties (e.g. API response bodies)
  if (error !== null && typeof error === 'object') {
    const errorObj = error as Record<string, unknown>

    if (typeof errorObj.detail === 'string') {
      return errorObj.detail
    }

    if (typeof errorObj.message === 'string') {
      return errorObj.message
    }
  }

  return DEFAULT_ERROR_MESSAGE
}

/**
 * Get the user-friendly message for a specific HTTP status code.
 *
 * @param status - HTTP status code
 * @returns The mapped message or the default error message
 */
export function getHttpStatusMessage(status: number): string {
  return HTTP_STATUS_MESSAGES[status] ?? DEFAULT_ERROR_MESSAGE
}

/**
 * Determine whether an error represents an authentication failure
 * that should redirect the user to the login page.
 *
 * @param error - The error to check
 * @returns True if the error is a 401 Unauthorized
 */
export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

/**
 * Determine whether an error represents a rate limit response.
 *
 * @param error - The error to check
 * @returns True if the error is a 429 Too Many Requests
 */
export function isRateLimitError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 429
}

/**
 * Determine whether an error represents a server-side failure.
 *
 * @param error - The error to check
 * @returns True if the error status is in the 5xx range
 */
export function isServerError(error: unknown): boolean {
  return error instanceof ApiError && error.status >= 500 && error.status < 600
}

/**
 * Determine whether an error represents a network connectivity issue.
 *
 * @param error - The error to check
 * @returns True if the error is a network/offline error
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.isOffline
  }
  if (error instanceof Error) {
    const msg = error.message.toLowerCase()
    return (
      msg.includes('failed to fetch') ||
      msg.includes('network request failed') ||
      msg.includes('networkerror') ||
      msg.includes('load failed') ||
      msg.includes('network error')
    )
  }
  return false
}
