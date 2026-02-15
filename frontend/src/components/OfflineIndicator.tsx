'use client'

import { useEffect, useReducer } from 'react'

import { useNetworkStatus } from '@/hooks/useNetworkStatus'
import { cn } from '@/lib/utils'

/**
 * Props for the OfflineIndicator component
 */
interface OfflineIndicatorProps {
  /** Additional CSS classes */
  className?: string
  /** Position of the indicator */
  position?: 'top' | 'bottom'
  /** Duration to show "back online" message in milliseconds */
  reconnectedMessageDuration?: number
  /** Custom offline message */
  offlineMessage?: string
  /** Custom back online message */
  onlineMessage?: string
}

interface OfflineIndicatorState {
  isAnimatingOut: boolean
  wasShowing: boolean
}

type OfflineIndicatorAction =
  | { type: 'show' }
  | { type: 'hide-start' }
  | { type: 'hide-complete' }

function offlineIndicatorReducer(
  state: OfflineIndicatorState,
  action: OfflineIndicatorAction
): OfflineIndicatorState {
  switch (action.type) {
    case 'show':
      return {
        isAnimatingOut: false,
        wasShowing: true,
      }
    case 'hide-start':
      return {
        ...state,
        isAnimatingOut: true,
      }
    case 'hide-complete':
      return {
        isAnimatingOut: false,
        wasShowing: false,
      }
    default:
      return state
  }
}

/**
 * Component that displays network connectivity status
 *
 * Shows a banner when the user goes offline and briefly shows
 * a "back online" message when connectivity is restored.
 *
 * Uses Tailwind CSS for styling that matches the app design.
 *
 * @example
 * ```tsx
 * // In your layout or app component
 * <OfflineIndicator />
 *
 * // With custom positioning
 * <OfflineIndicator position="bottom" />
 *
 * // With custom messages
 * <OfflineIndicator
 *   offlineMessage="No internet connection"
 *   onlineMessage="Connection restored"
 * />
 * ```
 */
export function OfflineIndicator({
  className,
  position = 'top',
  reconnectedMessageDuration = 3000,
  offlineMessage = "You're offline. Some features may be unavailable.",
  onlineMessage = 'Back online!',
}: OfflineIndicatorProps): React.ReactNode {
  const { isOnline, wasOffline } = useNetworkStatus({
    reconnectedDuration: reconnectedMessageDuration,
  })

  const [{ isAnimatingOut, wasShowing }, dispatch] = useReducer(offlineIndicatorReducer, {
    isAnimatingOut: false,
    wasShowing: false,
  })
  const shouldShow = !isOnline || wasOffline

  useEffect(() => {
    if (shouldShow) {
      dispatch({ type: 'show' })
      return
    }

    if (!wasShowing) {
      return
    }

    dispatch({ type: 'hide-start' })
    const timer = setTimeout(() => {
      dispatch({ type: 'hide-complete' })
    }, 300)
    return () => clearTimeout(timer)
  }, [shouldShow, wasShowing])

  // Don't render anything if we shouldn't be visible
  if (!shouldShow && !isAnimatingOut) {
    return null
  }

  const isOfflineState = !isOnline
  const showBackOnline = isOnline && wasOffline

  return (
    <div
      role="alert"
      aria-live="polite"
      aria-atomic="true"
      className={cn(
        // Base styles
        'fixed left-0 right-0 z-50 flex items-center justify-center px-4 py-3',
        'transition-all duration-300 ease-in-out',
        // Position
        position === 'top' ? 'top-0' : 'bottom-0',
        // Animation states
        isAnimatingOut
          ? 'translate-y-full opacity-0'
          : position === 'top'
            ? 'translate-y-0 opacity-100'
            : 'translate-y-0 opacity-100',
        // Background colors based on state
        isOfflineState
          ? 'bg-amber-500 text-white'
          : 'bg-green-500 text-white',
        className
      )}
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        {isOfflineState ? (
          <OfflineIcon className="h-5 w-5 flex-shrink-0" />
        ) : (
          <OnlineIcon className="h-5 w-5 flex-shrink-0" />
        )}

        {/* Message */}
        <span className="text-sm font-medium">
          {isOfflineState ? offlineMessage : showBackOnline ? onlineMessage : ''}
        </span>
      </div>
    </div>
  )
}

/**
 * Offline icon (wifi with slash)
 */
function OfflineIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M18.364 5.636a9 9 0 010 12.728M15.536 8.464a5 5 0 010 7.072M12 12v.01"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 4l16 16"
      />
    </svg>
  )
}

/**
 * Online icon (wifi connected)
 */
function OnlineIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.142 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"
      />
    </svg>
  )
}
