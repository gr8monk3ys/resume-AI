'use client'

import { ErrorBoundary } from '@/components/ErrorBoundary'

import type { ReactNode } from 'react'

/**
 * Props for the RootErrorBoundary component
 */
interface RootErrorBoundaryProps {
  children: ReactNode
}

/**
 * RootErrorBoundary Component
 *
 * A wrapper component that provides error boundary protection at the root level
 * of the application. This catches any unhandled errors in the React component
 * tree and displays a user-friendly error message.
 *
 * This component is designed to be used in the root layout to catch errors
 * that occur in any child component. It reports errors to Sentry for
 * production monitoring.
 *
 * Usage in layout.tsx:
 * ```tsx
 * <RootErrorBoundary>
 *   {children}
 * </RootErrorBoundary>
 * ```
 */
export function RootErrorBoundary({ children }: RootErrorBoundaryProps): React.ReactElement {
  return (
    <ErrorBoundary
      fallbackTitle="Application Error"
      fallbackDescription="We encountered an unexpected error. Please try refreshing the page or return to the home page."
      onError={(error, errorInfo) => {
        // Additional logging or analytics can be added here
        console.error('[RootErrorBoundary] Caught error:', error.message)
        console.error('[RootErrorBoundary] Component stack:', errorInfo.componentStack)
      }}
      onReset={() => {
        // Clear any cached state that might be causing issues
        console.log('[RootErrorBoundary] Error boundary reset')
      }}
    >
      {children}
    </ErrorBoundary>
  )
}
