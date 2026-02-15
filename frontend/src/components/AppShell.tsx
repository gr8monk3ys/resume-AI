'use client'

import { AuthProvider } from '@/components/AuthProvider'
import { Navbar } from '@/components/Navbar'
import { OfflineIndicator } from '@/components/OfflineIndicator'
import { RootErrorBoundary } from '@/components/RootErrorBoundary'
import { WebVitalsLoader } from '@/components/WebVitalsLoader'

export function AppShell({ children }: { children: React.ReactNode }) {
  const enableWebVitals =
    process.env.NEXT_PUBLIC_ENABLE_WEB_VITALS === 'true' ||
    process.env.NODE_ENV === 'production'
  const showDebugPanel = process.env.NODE_ENV === 'development'

  return (
    <RootErrorBoundary>
      <AuthProvider>
        <OfflineIndicator position="top" />
        <div className="app-shell-background min-h-screen overflow-x-clip">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.75),transparent_62%)]"
          />
          <div className="relative z-10 flex min-h-screen flex-col">
          <Navbar />
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-white focus:px-4 focus:py-2 focus:text-primary-700 focus:shadow-lg"
          >
            Skip to content
          </a>
          <main id="main-content" className="flex-1 pb-12">
            {children}
          </main>
          </div>
        </div>
      </AuthProvider>

      <WebVitalsLoader
        enabled={enableWebVitals}
        showDebugPanel={showDebugPanel}
        analyticsEndpoint={process.env.NEXT_PUBLIC_WEB_VITALS_ENDPOINT}
      />
    </RootErrorBoundary>
  )
}
