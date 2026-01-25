'use client'

import * as Sentry from '@sentry/nextjs'
import { Component } from 'react'

import { ErrorFallback } from '@/components/ErrorFallback'

import type { ErrorInfo, ReactNode } from 'react'

/**
 * Error information logged when an error is caught
 */
interface ErrorLogData {
  error: Error
  errorInfo: ErrorInfo
  timestamp: string
  componentStack: string | null
  userAgent: string
  url: string
}

/**
 * Props for the ErrorBoundary component
 */
export interface ErrorBoundaryProps {
  /** Child components to render */
  children: ReactNode
  /** Optional custom fallback component */
  fallback?: ReactNode
  /** Optional callback when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  /** Optional callback when error boundary resets */
  onReset?: () => void
  /** Optional custom title for error fallback */
  fallbackTitle?: string
  /** Optional custom description for error fallback */
  fallbackDescription?: string
}

/**
 * State for the ErrorBoundary component
 */
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

/**
 * Log error to console and report to Sentry
 *
 * This function logs errors to the console in development and
 * reports them to Sentry for production error tracking.
 */
function logError(data: ErrorLogData): void {
  // Console logging for development
  console.group('ErrorBoundary caught an error')
  console.error('Error:', data.error)
  console.error('Error Info:', data.errorInfo)
  console.log('Timestamp:', data.timestamp)
  console.log('URL:', data.url)
  console.log('User Agent:', data.userAgent)
  if (data.componentStack) {
    console.log('Component Stack:', data.componentStack)
  }
  console.groupEnd()

  // Report error to Sentry with additional context
  Sentry.withScope((scope) => {
    // Add component stack as extra context
    if (data.componentStack) {
      scope.setExtra('componentStack', data.componentStack)
    }
    scope.setExtra('timestamp', data.timestamp)
    scope.setExtra('url', data.url)
    scope.setExtra('userAgent', data.userAgent)

    // Tag as React error boundary error
    scope.setTag('error.boundary', 'true')
    scope.setTag('error.type', 'react_error_boundary')

    // Set the level to error
    scope.setLevel('error')

    // Capture the exception
    Sentry.captureException(data.error)
  })
}

/**
 * ErrorBoundary Component
 *
 * A React error boundary that catches JavaScript errors in child components,
 * logs them, and displays a fallback UI instead of crashing the entire app.
 *
 * Features:
 * - Catches errors in child component tree
 * - Logs errors with full context (component stack, timestamp, URL)
 * - Displays user-friendly fallback UI
 * - Provides reset functionality to retry
 * - Ready for Sentry integration
 * - Customizable fallback and callbacks
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary
 *   onError={(error, info) => console.log('Error logged:', error)}
 *   fallbackTitle="Page Error"
 *   fallbackDescription="This page encountered an error."
 * >
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 *
 * @see https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
    }
  }

  /**
   * Static method called when an error is thrown in a descendant component
   * Updates state to trigger fallback UI rendering
   */
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    }
  }

  /**
   * Lifecycle method called after an error is caught
   * Used for logging and side effects
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const { onError } = this.props

    // Prepare error data for logging
    const errorData: ErrorLogData = {
      error,
      errorInfo,
      timestamp: new Date().toISOString(),
      componentStack: errorInfo.componentStack ?? null,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
      url: typeof window !== 'undefined' ? window.location.href : 'unknown',
    }

    // Log the error
    logError(errorData)

    // Call optional error callback
    if (onError) {
      onError(error, errorInfo)
    }
  }

  /**
   * Reset the error boundary state
   * Called when user clicks "Try Again"
   */
  resetErrorBoundary = (): void => {
    const { onReset } = this.props

    // Call optional reset callback
    if (onReset) {
      onReset()
    }

    // Reset state
    this.setState({
      hasError: false,
      error: null,
    })
  }

  render(): ReactNode {
    const { hasError, error } = this.state
    const { children, fallback, fallbackTitle, fallbackDescription } = this.props

    // If there's an error, show fallback UI
    if (hasError && error) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback
      }

      // Use default ErrorFallback component
      return (
        <ErrorFallback
          error={error}
          resetErrorBoundary={this.resetErrorBoundary}
          title={fallbackTitle}
          description={fallbackDescription}
        />
      )
    }

    // No error, render children normally
    return children
  }
}

/**
 * Higher-order component to wrap a component with an ErrorBoundary
 *
 * Usage:
 * ```tsx
 * const SafeComponent = withErrorBoundary(MyComponent, {
 *   fallbackTitle: 'Component Error',
 * })
 * ```
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
): React.FC<P> {
  const displayName = WrappedComponent.displayName || WrappedComponent.name || 'Component'

  const ComponentWithErrorBoundary: React.FC<P> = (props) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  )

  ComponentWithErrorBoundary.displayName = `withErrorBoundary(${displayName})`

  return ComponentWithErrorBoundary
}
