'use client'

import { useEffect } from 'react'

interface WebVitalsProviderProps {
  /**
   * Analytics endpoint to send metrics to
   */
  analyticsEndpoint?: string

  /**
   * Whether to log metrics to the console
   * @default true in development, false in production
   */
  logToConsole?: boolean

  /**
   * Custom callback for handling metrics
   */
  onMetric?: (metric: {
    name: string
    value: number
    rating: string
    id: string
  }) => void

  /**
   * Whether to enable Web Vitals tracking
   * @default true
   */
  enabled?: boolean
}

/**
 * Client component that initializes Web Vitals tracking
 *
 * This component should be rendered once at the application root.
 * It initializes web-vitals tracking in a non-blocking way.
 *
 * @example
 * ```tsx
 * // In your layout.tsx
 * import dynamic from 'next/dynamic'
 *
 * const WebVitalsProvider = dynamic(
 *   () => import('@/components/WebVitalsProvider').then(mod => mod.WebVitalsProvider),
 *   { ssr: false }
 * )
 *
 * export default function RootLayout({ children }) {
 *   return (
 *     <html>
 *       <body>
 *         {children}
 *         <WebVitalsProvider
 *           analyticsEndpoint="/api/analytics/web-vitals"
 *         />
 *       </body>
 *     </html>
 *   )
 * }
 * ```
 */
export function WebVitalsProvider({
  analyticsEndpoint,
  logToConsole,
  onMetric,
  enabled = true,
}: WebVitalsProviderProps) {
  useEffect(() => {
    if (!enabled) return

    const initWebVitals = async () => {
      try {
        const { initWebVitals: init } = await import('@/lib/webVitals')

        await init({
          analyticsEndpoint,
          logToConsole: logToConsole ?? process.env.NODE_ENV === 'development',
          onMetric: onMetric
            ? (metric) =>
                onMetric({
                  name: metric.name,
                  value: metric.value,
                  rating: metric.rating,
                  id: metric.id,
                })
            : undefined,
        })
      } catch (error) {
        console.warn('[WebVitalsProvider] Failed to initialize:', error)
      }
    }

    // Use requestIdleCallback for non-blocking initialization
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => {
        void initWebVitals()
      })
    } else {
      // Fallback for Safari
      setTimeout(() => {
        void initWebVitals()
      }, 0)
    }
  }, [enabled, analyticsEndpoint, logToConsole, onMetric])

  // This component doesn't render anything
  return null
}

export default WebVitalsProvider
