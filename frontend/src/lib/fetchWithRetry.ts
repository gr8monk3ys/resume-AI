/**
 * Fetch wrapper with exponential backoff retry logic
 * Retries on network errors and 5xx server errors
 * Does not retry on 4xx client errors
 */

/**
 * Configuration options for fetchWithRetry
 */
export interface FetchRetryOptions extends RequestInit {
  /** Maximum number of retry attempts (default: 3) */
  maxRetries?: number
  /** Initial delay in milliseconds before first retry (default: 1000) */
  initialDelay?: number
  /** Maximum delay in milliseconds between retries (default: 10000) */
  maxDelay?: number
  /** Multiplier for exponential backoff (default: 2) */
  backoffMultiplier?: number
  /** Custom function to determine if an error is retryable */
  isRetryable?: (error: unknown, response?: Response) => boolean
  /** Callback invoked before each retry attempt */
  onRetry?: (attempt: number, delay: number, error: unknown) => void
}

/**
 * Default configuration values
 */
const DEFAULT_MAX_RETRIES = 3
const DEFAULT_INITIAL_DELAY = 1000
const DEFAULT_MAX_DELAY = 10000
const DEFAULT_BACKOFF_MULTIPLIER = 2

/**
 * HTTP status codes that indicate server errors (retryable)
 */
const RETRYABLE_STATUS_CODES = new Set([
  408, // Request Timeout
  429, // Too Many Requests
  500, // Internal Server Error
  502, // Bad Gateway
  503, // Service Unavailable
  504, // Gateway Timeout
])

/**
 * Error class for retry exhaustion
 */
export class RetryExhaustedError extends Error {
  readonly attempts: number
  readonly lastError: unknown

  constructor(message: string, attempts: number, lastError: unknown) {
    super(message)
    this.name = 'RetryExhaustedError'
    this.attempts = attempts
    this.lastError = lastError
  }
}

/**
 * Error class for network failures
 */
export class NetworkError extends Error {
  readonly originalError: unknown

  constructor(message: string, originalError: unknown) {
    super(message)
    this.name = 'NetworkError'
    this.originalError = originalError
  }
}

/**
 * Check if an error is a network-related error
 */
function isNetworkError(error: unknown): boolean {
  if (error instanceof TypeError) {
    // Common network error messages
    const message = error.message.toLowerCase()
    return (
      message.includes('failed to fetch') ||
      message.includes('network request failed') ||
      message.includes('networkerror') ||
      message.includes('load failed') ||
      message.includes('network error')
    )
  }
  return false
}

/**
 * Default retryable check function
 * Returns true for network errors and retryable HTTP status codes
 */
function defaultIsRetryable(error: unknown, response?: Response): boolean {
  // Network errors are always retryable
  if (isNetworkError(error)) {
    return true
  }

  // Check HTTP status code
  if (response) {
    return RETRYABLE_STATUS_CODES.has(response.status)
  }

  return false
}

/**
 * Calculate delay with exponential backoff and jitter
 */
function calculateDelay(
  attempt: number,
  initialDelay: number,
  maxDelay: number,
  multiplier: number
): number {
  // Calculate base delay with exponential backoff
  const baseDelay = initialDelay * Math.pow(multiplier, attempt - 1)

  // Add jitter (random value between 0 and 25% of base delay)
  const jitter = Math.random() * baseDelay * 0.25

  // Cap at maximum delay
  return Math.min(baseDelay + jitter, maxDelay)
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Fetch with automatic retry using exponential backoff
 *
 * @param url - The URL to fetch
 * @param options - Fetch options with retry configuration
 * @returns Promise resolving to the Response
 * @throws RetryExhaustedError if all retry attempts fail
 * @throws Error for non-retryable errors (4xx responses)
 *
 * @example
 * ```ts
 * const response = await fetchWithRetry('/api/data', {
 *   method: 'POST',
 *   body: JSON.stringify({ key: 'value' }),
 *   maxRetries: 3,
 *   initialDelay: 1000,
 * })
 * ```
 */
export async function fetchWithRetry(
  url: string | URL,
  options: FetchRetryOptions = {}
): Promise<Response> {
  const {
    maxRetries = DEFAULT_MAX_RETRIES,
    initialDelay = DEFAULT_INITIAL_DELAY,
    maxDelay = DEFAULT_MAX_DELAY,
    backoffMultiplier = DEFAULT_BACKOFF_MULTIPLIER,
    isRetryable = defaultIsRetryable,
    onRetry,
    ...fetchOptions
  } = options

  let lastError: unknown = null
  let attempt = 0

  while (attempt <= maxRetries) {
    try {
      const response = await fetch(url, fetchOptions)

      // Check if the response indicates a retryable error
      if (!response.ok && isRetryable(null, response)) {
        // Clone response for potential retry error context
        const errorMessage = `HTTP ${response.status}: ${response.statusText}`

        if (attempt < maxRetries) {
          const delay = calculateDelay(
            attempt + 1,
            initialDelay,
            maxDelay,
            backoffMultiplier
          )
          onRetry?.(attempt + 1, delay, new Error(errorMessage))
          await sleep(delay)
          attempt++
          lastError = new Error(errorMessage)
          continue
        }

        // All retries exhausted
        throw new RetryExhaustedError(
          `Failed after ${maxRetries} retries: ${errorMessage}`,
          attempt,
          new Error(errorMessage)
        )
      }

      // Success or non-retryable error (4xx)
      return response
    } catch (error) {
      lastError = error

      // Don't retry RetryExhaustedError
      if (error instanceof RetryExhaustedError) {
        throw error
      }

      // Check if error is retryable
      if (isRetryable(error)) {
        if (attempt < maxRetries) {
          const delay = calculateDelay(
            attempt + 1,
            initialDelay,
            maxDelay,
            backoffMultiplier
          )
          onRetry?.(attempt + 1, delay, error)
          await sleep(delay)
          attempt++
          continue
        }

        // All retries exhausted
        throw new RetryExhaustedError(
          `Failed after ${maxRetries} retries`,
          attempt,
          error
        )
      }

      // Non-retryable error, throw immediately
      if (isNetworkError(error)) {
        throw new NetworkError(
          'Network error occurred',
          error
        )
      }

      throw error
    }
  }

  // Should not reach here, but handle edge case
  throw new RetryExhaustedError(
    `Failed after ${maxRetries} retries`,
    attempt,
    lastError
  )
}

/**
 * Create a pre-configured fetchWithRetry function
 *
 * @param defaultOptions - Default options to apply to all requests
 * @returns A configured fetchWithRetry function
 *
 * @example
 * ```ts
 * const apiFetch = createFetchWithRetry({
 *   maxRetries: 3,
 *   initialDelay: 500,
 *   onRetry: (attempt, delay) => {
 *     console.log(`Retry attempt ${attempt} after ${delay}ms`)
 *   },
 * })
 *
 * const response = await apiFetch('/api/data')
 * ```
 */
export function createFetchWithRetry(
  defaultOptions: FetchRetryOptions = {}
): (url: string | URL, options?: FetchRetryOptions) => Promise<Response> {
  return (url: string | URL, options: FetchRetryOptions = {}) => {
    return fetchWithRetry(url, { ...defaultOptions, ...options })
  }
}
