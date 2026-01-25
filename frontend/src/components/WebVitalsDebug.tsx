'use client'

import { useState, useCallback, useEffect } from 'react'

import { useWebVitals } from '@/hooks/useWebVitals'
import { formatMetricValue, type MetricName, type WebVitalsMetric } from '@/lib/webVitals'

interface WebVitalsDebugProps {
  /**
   * Position of the debug badge
   * @default 'bottom-right'
   */
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'

  /**
   * Whether to start expanded
   * @default false
   */
  defaultExpanded?: boolean

  /**
   * Only show in development mode
   * @default true
   */
  devOnly?: boolean
}

const POSITION_CLASSES = {
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
} as const

const RATING_COLORS = {
  good: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    border: 'border-green-300',
    dot: 'bg-green-500',
  },
  'needs-improvement': {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    border: 'border-yellow-300',
    dot: 'bg-yellow-500',
  },
  poor: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    border: 'border-red-300',
    dot: 'bg-red-500',
  },
} as const

const METRIC_DESCRIPTIONS: Record<MetricName, string> = {
  CLS: 'Cumulative Layout Shift',
  INP: 'Interaction to Next Paint',
  LCP: 'Largest Contentful Paint',
  FCP: 'First Contentful Paint',
  TTFB: 'Time to First Byte',
}

interface MetricRowProps {
  metric: WebVitalsMetric
}

function MetricRow({ metric }: MetricRowProps) {
  const colors = RATING_COLORS[metric.rating]
  const formattedValue = formatMetricValue(metric.name, metric.value)

  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${colors.dot}`} />
        <div>
          <span className="font-medium text-gray-900">{metric.name}</span>
          <p className="text-xs text-gray-500">{METRIC_DESCRIPTIONS[metric.name]}</p>
        </div>
      </div>
      <div className="text-right">
        <span className={`font-mono text-sm ${colors.text}`}>{formattedValue}</span>
        <p className={`text-xs capitalize ${colors.text}`}>{metric.rating.replace('-', ' ')}</p>
      </div>
    </div>
  )
}

/**
 * Debug component that displays Web Vitals metrics in a floating badge
 *
 * Shows a small badge with overall score that can be expanded to show
 * all individual metrics with color-coded ratings.
 *
 * @example
 * ```tsx
 * // Add to your layout or page for development debugging
 * export default function RootLayout({ children }) {
 *   return (
 *     <html>
 *       <body>
 *         {children}
 *         <WebVitalsDebug />
 *       </body>
 *     </html>
 *   )
 * }
 * ```
 */
export function WebVitalsDebug({
  position = 'bottom-right',
  defaultExpanded = false,
  devOnly = true,
}: WebVitalsDebugProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [isVisible, setIsVisible] = useState(true)
  const [isMounted, setIsMounted] = useState(false)

  const { metrics, overallScore, isComplete } = useWebVitals({
    enabled: true,
    logToConsole: false,
  })

  useEffect(() => {
    setIsMounted(true)
  }, [])

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev)
  }, [])

  const handleClose = useCallback(() => {
    setIsVisible(false)
  }, [])

  // Don't render in production if devOnly is true
  if (devOnly && process.env.NODE_ENV !== 'development') {
    return null
  }

  // Don't render on server or if hidden
  if (!isMounted || !isVisible) {
    return null
  }

  const metricList = Object.values(metrics)
  const hasMetrics = metricList.length > 0

  // Determine overall color based on score
  const getOverallColor = () => {
    if (!hasMetrics) return RATING_COLORS.good
    if (overallScore >= 80) return RATING_COLORS.good
    if (overallScore >= 50) return RATING_COLORS['needs-improvement']
    return RATING_COLORS.poor
  }

  const overallColor = getOverallColor()

  return (
    <div
      className={`fixed ${POSITION_CLASSES[position]} z-50 font-sans`}
      role="region"
      aria-label="Web Vitals Debug Panel"
    >
      {isExpanded ? (
        <div className="bg-white rounded-lg shadow-lg border border-gray-200 w-72 overflow-hidden">
          {/* Header */}
          <div className={`${overallColor.bg} ${overallColor.text} px-4 py-3 flex items-center justify-between`}>
            <div className="flex items-center gap-2">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              <span className="font-semibold">Web Vitals</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{overallScore}%</span>
              <button
                onClick={toggleExpanded}
                className="p-1 hover:bg-black/10 rounded transition-colors"
                aria-label="Collapse panel"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <button
                onClick={handleClose}
                className="p-1 hover:bg-black/10 rounded transition-colors"
                aria-label="Close panel"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="px-4 py-3">
            {hasMetrics ? (
              <div className="space-y-1">
                {metricList.map((metric) => (
                  <MetricRow key={metric.name} metric={metric} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">
                Collecting metrics...
              </p>
            )}

            {/* Status indicator */}
            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
              <span>
                {isComplete ? 'All metrics collected' : `${metricList.length}/5 metrics`}
              </span>
              <span className="flex items-center gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${isComplete ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'}`} />
                {isComplete ? 'Complete' : 'Collecting...'}
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Collapsed badge */
        <button
          onClick={toggleExpanded}
          className={`${overallColor.bg} ${overallColor.text} ${overallColor.border} border rounded-full px-3 py-1.5 flex items-center gap-2 shadow-lg hover:shadow-xl transition-shadow`}
          aria-label={`Web Vitals score: ${overallScore}%. Click to expand`}
        >
          <span className={`w-2 h-2 rounded-full ${overallColor.dot}`} />
          <span className="font-medium text-sm">
            {hasMetrics ? `${overallScore}%` : '...'}
          </span>
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </button>
      )}
    </div>
  )
}

export default WebVitalsDebug
