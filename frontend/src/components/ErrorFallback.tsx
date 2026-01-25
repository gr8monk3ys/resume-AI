'use client'

import { AlertTriangle, RefreshCw, Home, ChevronDown, ChevronUp } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'

import { cn } from '@/lib/utils'

/**
 * Props for the ErrorFallback component
 */
export interface ErrorFallbackProps {
  /** The error that was caught */
  error: Error
  /** Callback to reset the error boundary and retry */
  resetErrorBoundary: () => void
  /** Optional custom title for the error message */
  title?: string
  /** Optional custom description for the error message */
  description?: string
}

/**
 * Check if we're in development mode
 */
function isDevelopment(): boolean {
  return process.env.NODE_ENV === 'development'
}

/**
 * ErrorFallback component
 *
 * A user-friendly fallback UI displayed when an error is caught by an ErrorBoundary.
 * Shows error details in development mode only for debugging purposes.
 *
 * Features:
 * - Clean, accessible error message
 * - "Try Again" button to reset the error state
 * - Link to return home
 * - Collapsible error details in development mode
 * - Consistent styling with the rest of the application
 */
export function ErrorFallback({
  error,
  resetErrorBoundary,
  title = 'Something went wrong',
  description = 'We encountered an unexpected error. Please try again or return to the home page.',
}: ErrorFallbackProps): React.ReactElement {
  const [showDetails, setShowDetails] = useState(false)
  const showDevDetails = isDevelopment()

  return (
    <div
      className="min-h-[400px] flex items-center justify-center p-4"
      role="alert"
      aria-live="assertive"
    >
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg border border-gray-200 p-8">
        {/* Error Icon */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
            <AlertTriangle
              className="w-8 h-8 text-red-600"
              aria-hidden="true"
            />
          </div>
        </div>

        {/* Error Message */}
        <div className="text-center mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {title}
          </h2>
          <p className="text-gray-500 text-sm">
            {description}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <button
            type="button"
            onClick={resetErrorBoundary}
            className={cn(
              'flex-1 inline-flex items-center justify-center px-4 py-2.5',
              'text-sm font-medium text-white bg-primary-600',
              'rounded-lg hover:bg-primary-700 transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500'
            )}
          >
            <RefreshCw className="w-4 h-4 mr-2" aria-hidden="true" />
            Try Again
          </button>
          <Link
            href="/"
            className={cn(
              'flex-1 inline-flex items-center justify-center px-4 py-2.5',
              'text-sm font-medium text-gray-700 bg-gray-100',
              'rounded-lg hover:bg-gray-200 transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500'
            )}
          >
            <Home className="w-4 h-4 mr-2" aria-hidden="true" />
            Go Home
          </Link>
        </div>

        {/* Development-only Error Details */}
        {showDevDetails && (
          <div className="border-t border-gray-200 pt-4">
            <button
              type="button"
              onClick={() => setShowDetails(!showDetails)}
              className={cn(
                'w-full flex items-center justify-between px-3 py-2',
                'text-sm text-gray-600 hover:text-gray-900',
                'bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-primary-500'
              )}
              aria-expanded={showDetails}
              aria-controls="error-details"
            >
              <span className="font-medium">Error Details (Development Only)</span>
              {showDetails ? (
                <ChevronUp className="w-4 h-4" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-4 h-4" aria-hidden="true" />
              )}
            </button>

            {showDetails && (
              <div
                id="error-details"
                className="mt-3 p-4 bg-gray-900 rounded-lg overflow-auto max-h-64"
              >
                <div className="mb-3">
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                    Error Name
                  </p>
                  <p className="text-sm text-red-400 font-mono">
                    {error.name}
                  </p>
                </div>
                <div className="mb-3">
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                    Error Message
                  </p>
                  <p className="text-sm text-red-400 font-mono break-words">
                    {error.message}
                  </p>
                </div>
                {error.stack && (
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                      Stack Trace
                    </p>
                    <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap break-words">
                      {error.stack}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
