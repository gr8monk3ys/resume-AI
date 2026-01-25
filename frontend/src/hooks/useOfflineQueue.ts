'use client'

import { useState, useEffect, useCallback } from 'react'

import { offlineUtils } from '@/lib/api'

/**
 * Offline queue status information
 */
export interface OfflineQueueStatus {
  /** Number of pending requests in the queue */
  pendingCount: number
  /** Whether there are any pending requests */
  hasPending: boolean
  /** Manually trigger queue processing */
  processQueue: () => Promise<void>
  /** Clear all pending requests */
  clearQueue: () => void
}

/**
 * Custom hook to monitor and manage the offline request queue
 *
 * This hook provides reactive access to the offline queue state,
 * allowing components to display sync status and manage pending requests.
 *
 * @returns OfflineQueueStatus object with queue state and controls
 *
 * @example
 * ```tsx
 * function SyncStatus() {
 *   const { pendingCount, hasPending, processQueue } = useOfflineQueue()
 *
 *   if (!hasPending) {
 *     return null
 *   }
 *
 *   return (
 *     <div>
 *       <span>{pendingCount} pending changes</span>
 *       <button onClick={processQueue}>Sync now</button>
 *     </div>
 *   )
 * }
 * ```
 */
export function useOfflineQueue(): OfflineQueueStatus {
  const [pendingCount, setPendingCount] = useState<number>(() => {
    // Initialize with current queue count
    return offlineUtils.getPendingCount()
  })

  // Subscribe to queue changes
  useEffect(() => {
    const unsubscribe = offlineUtils.onQueueChange((count) => {
      setPendingCount(count)
    })

    // Sync initial state
    setPendingCount(offlineUtils.getPendingCount())

    return unsubscribe
  }, [])

  const processQueue = useCallback(async () => {
    await offlineUtils.processQueue()
  }, [])

  const clearQueue = useCallback(() => {
    offlineUtils.clearQueue()
  }, [])

  return {
    pendingCount,
    hasPending: pendingCount > 0,
    processQueue,
    clearQueue,
  }
}
