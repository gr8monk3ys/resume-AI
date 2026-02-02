/**
 * Web Vitals reporter for tracking Core Web Vitals performance metrics
 *
 * Tracks the following metrics:
 * - CLS (Cumulative Layout Shift): Visual stability
 * - INP (Interaction to Next Paint): Interactivity (replaced FID)
 * - LCP (Largest Contentful Paint): Loading performance
 * - FCP (First Contentful Paint): Initial render time
 * - TTFB (Time to First Byte): Server response time
 */

import type { Metric, CLSMetric, INPMetric, LCPMetric, FCPMetric, TTFBMetric } from 'web-vitals'

/**
 * Thresholds for Web Vitals metrics based on Google's recommendations
 * https://web.dev/vitals/
 */
export const WEB_VITALS_THRESHOLDS = {
  CLS: { good: 0.1, needsImprovement: 0.25 },
  INP: { good: 200, needsImprovement: 500 },
  LCP: { good: 2500, needsImprovement: 4000 },
  FCP: { good: 1800, needsImprovement: 3000 },
  TTFB: { good: 800, needsImprovement: 1800 },
} as const

export type MetricName = keyof typeof WEB_VITALS_THRESHOLDS

export type MetricRating = 'good' | 'needs-improvement' | 'poor'

export interface WebVitalsMetric {
  name: MetricName
  value: number
  rating: MetricRating
  delta: number
  id: string
  navigationType: string
}

export interface WebVitalsReport {
  metrics: Partial<Record<MetricName, WebVitalsMetric>>
  timestamp: number
  url: string
  userAgent: string
}

/**
 * Get the rating for a metric based on its value
 */
export function getMetricRating(name: MetricName, value: number): MetricRating {
  const threshold = WEB_VITALS_THRESHOLDS[name]
  if (value <= threshold.good) return 'good'
  if (value <= threshold.needsImprovement) return 'needs-improvement'
  return 'poor'
}

/**
 * Format a metric value for display
 */
export function formatMetricValue(name: MetricName, value: number): string {
  switch (name) {
    case 'CLS':
      return value.toFixed(3)
    case 'INP':
    case 'LCP':
    case 'FCP':
    case 'TTFB':
      return `${Math.round(value)}ms`
    default:
      return String(value)
  }
}

/**
 * Convert web-vitals Metric to our structured format
 */
function convertMetric(metric: Metric): WebVitalsMetric {
  return {
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    delta: metric.delta,
    id: metric.id,
    navigationType: metric.navigationType,
  }
}

/**
 * Storage for collected metrics
 */
const collectedMetrics: Partial<Record<MetricName, WebVitalsMetric>> = {}
const metricCallbacks: Set<(metrics: Partial<Record<MetricName, WebVitalsMetric>>) => void> = new Set()

/**
 * Subscribe to metric updates
 */
export function subscribeToMetrics(
  callback: (metrics: Partial<Record<MetricName, WebVitalsMetric>>) => void
): () => void {
  metricCallbacks.add(callback)
  // Immediately call with current metrics
  callback({ ...collectedMetrics })
  return () => {
    metricCallbacks.delete(callback)
  }
}

/**
 * Get current collected metrics
 */
export function getCollectedMetrics(): Partial<Record<MetricName, WebVitalsMetric>> {
  return { ...collectedMetrics }
}

/**
 * Notify all subscribers of metric updates
 */
function notifySubscribers(): void {
  const metrics = { ...collectedMetrics }
  metricCallbacks.forEach((callback) => callback(metrics))
}

/**
 * Configuration options for the Web Vitals reporter
 */
export interface WebVitalsReporterOptions {
  /**
   * Whether to log metrics to the console
   * @default true in development
   */
  logToConsole?: boolean

  /**
   * Analytics endpoint to send metrics to
   */
  analyticsEndpoint?: string

  /**
   * Custom callback for handling metrics
   */
  onMetric?: (metric: WebVitalsMetric) => void

  /**
   * Whether to report all changes or only final values
   * @default false
   */
  reportAllChanges?: boolean
}

/**
 * Default handler for metrics - logs to console with color coding
 */
function defaultMetricHandler(metric: WebVitalsMetric, logToConsole: boolean): void {
  collectedMetrics[metric.name] = metric
  notifySubscribers()

  if (!logToConsole) return

  const colors = {
    good: 'color: #0cce6b; font-weight: bold',
    'needs-improvement': 'color: #ffa400; font-weight: bold',
    poor: 'color: #ff4e42; font-weight: bold',
  }

  const formattedValue = formatMetricValue(metric.name, metric.value)
  const style = colors[metric.rating]

  console.log(
    `%c[Web Vitals] ${metric.name}: ${formattedValue} (${metric.rating})`,
    style
  )
}

/**
 * Send metrics to an analytics endpoint
 */
async function sendToAnalytics(
  endpoint: string,
  metric: WebVitalsMetric
): Promise<void> {
  const body: WebVitalsReport = {
    metrics: { [metric.name]: metric },
    timestamp: Date.now(),
    url: typeof window !== 'undefined' ? window.location.href : '',
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
  }

  try {
    // Use sendBeacon if available for reliable delivery
    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(body)], { type: 'application/json' })
      navigator.sendBeacon(endpoint, blob)
    } else {
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        keepalive: true,
      })
    }
  } catch (error) {
    console.warn('[Web Vitals] Failed to send metrics:', error)
  }
}

/**
 * Create a metric handler with the given options
 */
function createMetricHandler(options: WebVitalsReporterOptions) {
  return (metric: CLSMetric | INPMetric | LCPMetric | FCPMetric | TTFBMetric): void => {
    const convertedMetric = convertMetric(metric)

    // Default console logging
    const shouldLog = options.logToConsole ?? process.env.NODE_ENV === 'development'
    defaultMetricHandler(convertedMetric, shouldLog)

    // Custom callback
    if (options.onMetric) {
      options.onMetric(convertedMetric)
    }

    // Send to analytics endpoint
    if (options.analyticsEndpoint) {
      void sendToAnalytics(options.analyticsEndpoint, convertedMetric)
    }
  }
}

/**
 * Initialize Web Vitals reporting
 *
 * @example
 * ```ts
 * // Basic usage - logs to console in development
 * initWebVitals()
 *
 * // With analytics endpoint
 * initWebVitals({
 *   analyticsEndpoint: '/api/analytics/web-vitals',
 *   logToConsole: false,
 * })
 *
 * // With custom callback
 * initWebVitals({
 *   onMetric: (metric) => {
 *     sendToGoogleAnalytics(metric)
 *   }
 * })
 * ```
 */
export async function initWebVitals(
  options: WebVitalsReporterOptions = {}
): Promise<void> {
  // Only run in browser environment
  if (typeof window === 'undefined') return

  const { onCLS, onINP, onLCP, onFCP, onTTFB } = await import('web-vitals')

  const handler = createMetricHandler(options)
  const reportAllChanges = options.reportAllChanges ?? false

  // Initialize all metric observers
  onCLS(handler, { reportAllChanges })
  onINP(handler, { reportAllChanges })
  onLCP(handler, { reportAllChanges })
  onFCP(handler, { reportAllChanges })
  onTTFB(handler, { reportAllChanges })
}

/**
 * Create a report of all collected metrics
 */
export function createWebVitalsReport(): WebVitalsReport {
  return {
    metrics: { ...collectedMetrics },
    timestamp: Date.now(),
    url: typeof window !== 'undefined' ? window.location.href : '',
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
  }
}
