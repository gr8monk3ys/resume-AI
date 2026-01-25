'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * Network status information returned by the hook
 */
export interface NetworkStatus {
  /** Whether the browser is currently online */
  isOnline: boolean
  /** Whether the connection was recently restored (was offline, now online) */
  wasOffline: boolean
  /** Timestamp of the last connection change */
  lastChanged: Date | null
  /** Duration of the last offline period in milliseconds */
  lastOfflineDuration: number | null
}

/**
 * Options for the useNetworkStatus hook
 */
export interface UseNetworkStatusOptions {
  /**
   * Duration in milliseconds to show "back online" status
   * Default: 3000 (3 seconds)
   */
  reconnectedDuration?: number
  /**
   * Callback invoked when connection is lost
   */
  onOffline?: () => void
  /**
   * Callback invoked when connection is restored
   */
  onOnline?: () => void
}

/**
 * Check if we're in a browser environment
 */
function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof navigator !== 'undefined'
}

/**
 * Get initial online status
 */
function getInitialOnlineStatus(): boolean {
  if (!isBrowser()) {
    // Assume online during SSR
    return true
  }
  return navigator.onLine
}

/**
 * Custom hook to detect online/offline network status
 *
 * Uses navigator.onLine API and online/offline events to track
 * the browser's network connection state in real-time.
 *
 * @param options - Configuration options for the hook
 * @returns NetworkStatus object with current connection state
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { isOnline, wasOffline } = useNetworkStatus({
 *     onOffline: () => console.log('Connection lost'),
 *     onOnline: () => console.log('Connection restored'),
 *   })
 *
 *   if (!isOnline) {
 *     return <div>You are offline</div>
 *   }
 *
 *   if (wasOffline) {
 *     return <div>Back online!</div>
 *   }
 *
 *   return <div>Connected</div>
 * }
 * ```
 */
export function useNetworkStatus(
  options: UseNetworkStatusOptions = {}
): NetworkStatus {
  const {
    reconnectedDuration = 3000,
    onOffline,
    onOnline,
  } = options

  const [isOnline, setIsOnline] = useState<boolean>(getInitialOnlineStatus)
  const [wasOffline, setWasOffline] = useState<boolean>(false)
  const [lastChanged, setLastChanged] = useState<Date | null>(null)
  const [lastOfflineDuration, setLastOfflineDuration] = useState<number | null>(null)

  // Track when we went offline
  const offlineStartRef = useRef<Date | null>(null)
  // Timer for clearing wasOffline state
  const wasOfflineTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /**
   * Handle going offline
   */
  const handleOffline = useCallback(() => {
    offlineStartRef.current = new Date()
    setIsOnline(false)
    setLastChanged(new Date())

    // Clear any existing wasOffline timer
    if (wasOfflineTimerRef.current) {
      clearTimeout(wasOfflineTimerRef.current)
      wasOfflineTimerRef.current = null
    }
    setWasOffline(false)

    onOffline?.()
  }, [onOffline])

  /**
   * Handle coming back online
   */
  const handleOnline = useCallback(() => {
    const now = new Date()

    // Calculate offline duration
    if (offlineStartRef.current) {
      const duration = now.getTime() - offlineStartRef.current.getTime()
      setLastOfflineDuration(duration)
      offlineStartRef.current = null
    }

    setIsOnline(true)
    setLastChanged(now)
    setWasOffline(true)

    // Clear wasOffline state after duration
    wasOfflineTimerRef.current = setTimeout(() => {
      setWasOffline(false)
      wasOfflineTimerRef.current = null
    }, reconnectedDuration)

    onOnline?.()
  }, [reconnectedDuration, onOnline])

  /**
   * Set up event listeners
   */
  useEffect(() => {
    if (!isBrowser()) {
      return
    }

    // Sync initial state in case it changed between render and effect
    const currentOnline = navigator.onLine
    if (currentOnline !== isOnline) {
      if (currentOnline) {
        handleOnline()
      } else {
        handleOffline()
      }
    }

    // Add event listeners
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Cleanup
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)

      // Clear any pending timers
      if (wasOfflineTimerRef.current) {
        clearTimeout(wasOfflineTimerRef.current)
      }
    }
  }, [handleOnline, handleOffline, isOnline])

  return {
    isOnline,
    wasOffline,
    lastChanged,
    lastOfflineDuration,
  }
}

/**
 * Simple hook variant that just returns online status boolean
 *
 * @returns boolean indicating if browser is online
 *
 * @example
 * ```tsx
 * const isOnline = useIsOnline()
 * ```
 */
export function useIsOnline(): boolean {
  const { isOnline } = useNetworkStatus()
  return isOnline
}
