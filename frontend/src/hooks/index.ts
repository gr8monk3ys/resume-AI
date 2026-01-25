/**
 * Custom React hooks for the ResuBoost AI application
 */

export {
  useNetworkStatus,
  useIsOnline,
  type NetworkStatus,
  type UseNetworkStatusOptions,
} from './useNetworkStatus'

export {
  useOfflineQueue,
  type OfflineQueueStatus,
} from './useOfflineQueue'

export {
  useVirtualList,
  useVirtualTable,
  type UseVirtualListOptions,
  type UseVirtualListReturn,
  type UseVirtualTableOptions,
  type UseVirtualTableReturn,
  type VirtualItem,
  type VirtualItemInfo,
} from './useVirtualList'

export {
  useWebVitals,
  type UseWebVitalsOptions,
  type UseWebVitalsReturn,
  type MetricName,
  type WebVitalsMetric,
} from './useWebVitals'
