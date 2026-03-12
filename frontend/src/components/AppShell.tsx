'use client'

import { AuthProvider } from '@/components/AuthProvider'
import { Navbar } from '@/components/Navbar'
import { OfflineIndicator } from '@/components/OfflineIndicator'
import { RootErrorBoundary } from '@/components/RootErrorBoundary'
import { WebVitalsLoader } from '@/components/WebVitalsLoader'

export function AppShell({ children }: { children: React.ReactNode }) {
  const enableWebVitals = process.env.NEXT_PUBLIC_ENABLE_WEB_VITALS === 'true' ||
    process.env.NODE_ENV === 'production'
  const showDebugPanel = process.env.NODE_ENV === 'development'

  return (
    <RootErrorBoundary>
      <AuthProvider>
        <OfflineIndicator position="top" />
        <div className="min-h-screen flex flex-col">
          <Navbar />
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-white focus:px-4 focus:py-2 focus:text-primary-700 focus:shadow-lg"
          >
            Skip to content
          </a>
          <main id="main-content" className="flex-1">
            {children}
          </main>
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
