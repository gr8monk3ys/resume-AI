'use client'

import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
}

/**
 * React Error Boundary component to catch and handle rendering errors.
 *
 * Prevents the entire app from crashing when a component throws an error.
 * Displays a user-friendly error message with retry option.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error details for debugging
    console.error('React Error Boundary caught an error:', error)
    console.error('Component stack:', errorInfo.componentStack)

    // Store error info in state for display
    this.setState({ errorInfo })

    // Call optional error handler (for error tracking services)
    this.props.onError?.(error, errorInfo)
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <div className="min-h-[200px] flex items-center justify-center p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md w-full">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-800">
                  Something went wrong
                </h3>
                <p className="mt-2 text-sm text-red-700">
                  An error occurred while rendering this section. This has been
                  logged for investigation.
                </p>
                {process.env.NODE_ENV === 'development' && this.state.error && (
                  <details className="mt-3">
                    <summary className="text-sm text-red-600 cursor-pointer hover:underline">
                      Technical details
                    </summary>
                    <pre className="mt-2 p-2 bg-red-100 rounded text-xs overflow-auto max-h-32">
                      {this.state.error.message}
                      {this.state.errorInfo?.componentStack}
                    </pre>
                  </details>
                )}
                <button
                  onClick={this.handleRetry}
                  className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm font-medium"
                >
                  <RefreshCw className="h-4 w-4" />
                  Try again
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * Higher-order component to wrap any component with an error boundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
): React.FC<P> {
  const displayName = WrappedComponent.displayName || WrappedComponent.name || 'Component'

  const ComponentWithErrorBoundary: React.FC<P> = (props) => (
    <ErrorBoundary fallback={fallback}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  )

  ComponentWithErrorBoundary.displayName = `withErrorBoundary(${displayName})`

  return ComponentWithErrorBoundary
}

/**
 * Compact error boundary for smaller UI sections
 */
export function CompactErrorBoundary({ children }: { children: ReactNode }): JSX.Element {
  return (
    <ErrorBoundary
      fallback={
        <div className="p-4 text-center text-red-600 text-sm">
          <AlertTriangle className="h-5 w-5 mx-auto mb-2" />
          <p>Failed to load this section</p>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  )
}
