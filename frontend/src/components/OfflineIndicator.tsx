'use client'

import { useEffect, useState } from 'react'

import { useNetworkStatus } from '@/hooks/useNetworkStatus'
import { cn } from '@/lib/utils'

/**
 * Props for the OfflineIndicator component
 */
export interface OfflineIndicatorProps {
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

  // Track visibility for animation
  const [isVisible, setIsVisible] = useState(false)
  const [isAnimatingOut, setIsAnimatingOut] = useState(false)

  // Handle visibility changes
  useEffect(() => {
    if (!isOnline) {
      // Going offline - show immediately
      setIsAnimatingOut(false)
      setIsVisible(true)
      return
    }

    if (wasOffline) {
      // Just came back online - show "back online" message
      setIsAnimatingOut(false)
      setIsVisible(true)
      return
    }

    if (isVisible) {
      // Was showing something, now should hide
      setIsAnimatingOut(true)
      const timer = setTimeout(() => {
        setIsVisible(false)
        setIsAnimatingOut(false)
      }, 300) // Match animation duration
      return () => clearTimeout(timer)
    }

    return
  }, [isOnline, wasOffline, isVisible])

  // Don't render anything if we shouldn't be visible
  if (!isVisible) {
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

/**
 * Compact offline indicator that shows just an icon with tooltip
 * Useful for nav bars or smaller UI areas
 */
export function OfflineIndicatorCompact({
  className,
}: {
  className?: string
}): React.ReactNode {
  const { isOnline, wasOffline } = useNetworkStatus()

  // Only show when offline
  if (isOnline && !wasOffline) {
    return null
  }

  const isOfflineState = !isOnline

  return (
    <div
      role="status"
      aria-label={isOfflineState ? 'Offline' : 'Back online'}
      className={cn(
        'relative flex items-center justify-center',
        'rounded-full p-2 transition-colors duration-200',
        isOfflineState
          ? 'bg-amber-100 text-amber-600'
          : 'bg-green-100 text-green-600',
        className
      )}
    >
      {isOfflineState ? (
        <OfflineIcon className="h-4 w-4" />
      ) : (
        <OnlineIcon className="h-4 w-4" />
      )}

      {/* Tooltip */}
      <span
        className={cn(
          'absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap',
          'rounded bg-gray-900 px-2 py-1 text-xs text-white',
          'pointer-events-none opacity-0 transition-opacity',
          'group-hover:opacity-100'
        )}
      >
        {isOfflineState ? "You're offline" : 'Back online'}
      </span>
    </div>
  )
}
