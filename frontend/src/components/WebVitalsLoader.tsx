'use client'

import dynamic from 'next/dynamic'

// Dynamically import Web Vitals components for non-blocking loading
const WebVitalsProvider = dynamic(
  () => import('@/components/WebVitalsProvider').then((mod) => mod.WebVitalsProvider),
  { ssr: false }
)

const WebVitalsDebug = dynamic(
  () => import('@/components/WebVitalsDebug').then((mod) => mod.WebVitalsDebug),
  { ssr: false }
)

interface WebVitalsLoaderProps {
  /**
   * Whether to enable Web Vitals tracking
   * @default false
   */
  enabled?: boolean

  /**
   * Whether to show the debug panel
   * @default false
   */
  showDebugPanel?: boolean

  /**
   * Analytics endpoint to send metrics to
   */
  analyticsEndpoint?: string
}

/**
 * Client component that loads Web Vitals tracking and optional debug panel
 *
 * This component should be rendered in the root layout to enable Web Vitals
 * monitoring. It uses dynamic imports with ssr: false to ensure the components
 * only load on the client.
 *
 * @example
 * ```tsx
 * // In your layout.tsx (Server Component)
 * import { WebVitalsLoader } from '@/components/WebVitalsLoader'
 *
 * export default function RootLayout({ children }) {
 *   return (
 *     <html>
 *       <body>
 *         {children}
 *         <WebVitalsLoader
 *           enabled={process.env.NODE_ENV === 'production'}
 *           showDebugPanel={process.env.NODE_ENV === 'development'}
 *         />
 *       </body>
 *     </html>
 *   )
 * }
 * ```
 */
export function WebVitalsLoader({
  enabled = false,
  showDebugPanel = false,
  analyticsEndpoint,
}: WebVitalsLoaderProps) {
  return (
    <>
      {enabled && (
        <WebVitalsProvider analyticsEndpoint={analyticsEndpoint} />
      )}
      {showDebugPanel && <WebVitalsDebug position="bottom-right" />}
    </>
  )
}

export default WebVitalsLoader
