'use client'

import { useEffect, useState, useCallback, useRef } from 'react'

import type {
  MetricName,
  WebVitalsMetric,
  WebVitalsReporterOptions,
} from '@/lib/webVitals'

export interface UseWebVitalsOptions extends WebVitalsReporterOptions {
  /**
   * Whether to enable Web Vitals tracking
   * @default true
   */
  enabled?: boolean
}

export interface UseWebVitalsReturn {
  /**
   * Current collected metrics
   */
  metrics: Partial<Record<MetricName, WebVitalsMetric>>

  /**
   * Whether all core metrics have been collected
   */
  isComplete: boolean

  /**
   * Get a specific metric by name
   */
  getMetric: (name: MetricName) => WebVitalsMetric | undefined

  /**
   * Check if a metric meets the "good" threshold
   */
  isGood: (name: MetricName) => boolean

  /**
   * Get overall score based on collected metrics
   * Returns percentage of metrics rated as "good"
   */
  overallScore: number
}

/**
 * Hook to initialize and track Web Vitals metrics
 *
 * @example
 * ```tsx
 * function PerformanceMonitor() {
 *   const { metrics, isComplete, overallScore } = useWebVitals({
 *     logToConsole: true,
 *   })
 *
 *   return (
 *     <div>
 *       <p>Score: {overallScore}%</p>
 *       {Object.entries(metrics).map(([name, metric]) => (
 *         <p key={name}>
 *           {name}: {metric.value} ({metric.rating})
 *         </p>
 *       ))}
 *     </div>
 *   )
 * }
 * ```
 */
export function useWebVitals(
  options: UseWebVitalsOptions = {}
): UseWebVitalsReturn {
  const { enabled = true, ...reporterOptions } = options
  const [metrics, setMetrics] = useState<Partial<Record<MetricName, WebVitalsMetric>>>({})

  // Store options in a ref to avoid dependency issues
  const optionsRef = useRef(reporterOptions)
  optionsRef.current = reporterOptions

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return

    let unsubscribe: (() => void) | undefined

    const init = async (): Promise<void> => {
      const { initWebVitals, subscribeToMetrics } = await import('@/lib/webVitals')

      // Subscribe to metric updates
      unsubscribe = subscribeToMetrics((updatedMetrics) => {
        setMetrics(updatedMetrics)
      })

      // Initialize web vitals tracking
      await initWebVitals(optionsRef.current)
    }

    void init()

    return () => {
      if (unsubscribe) {
        unsubscribe()
      }
    }
  }, [enabled]) // Only re-run if enabled changes

  const getMetric = useCallback(
    (name: MetricName): WebVitalsMetric | undefined => {
      return metrics[name]
    },
    [metrics]
  )

  const isGood = useCallback(
    (name: MetricName): boolean => {
      const metric = metrics[name]
      return metric?.rating === 'good'
    },
    [metrics]
  )

  const isComplete = Object.keys(metrics).length >= 5

  const overallScore = (() => {
    const metricList = Object.values(metrics)
    if (metricList.length === 0) return 0
    const goodCount = metricList.filter((m) => m.rating === 'good').length
    return Math.round((goodCount / metricList.length) * 100)
  })()

  return {
    metrics,
    isComplete,
    getMetric,
    isGood,
    overallScore,
  }
}

export type { MetricName, WebVitalsMetric }
