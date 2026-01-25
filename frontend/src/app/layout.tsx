import { AuthProvider } from '@/components/AuthProvider'
import { Navbar } from '@/components/Navbar'
import { OfflineIndicator } from '@/components/OfflineIndicator'
import { RootErrorBoundary } from '@/components/RootErrorBoundary'
import { WebVitalsLoader } from '@/components/WebVitalsLoader'

import type { Metadata } from 'next'

import './globals.css'

export const metadata: Metadata = {
  title: 'ResuBoost AI',
  description: 'AI-powered job search toolkit',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Enable Web Vitals in production or when explicitly enabled
  const enableWebVitals = process.env.NEXT_PUBLIC_ENABLE_WEB_VITALS === 'true' ||
    process.env.NODE_ENV === 'production'

  // Show debug panel only in development
  const showDebugPanel = process.env.NODE_ENV === 'development'

  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <RootErrorBoundary>
          <AuthProvider>
            <OfflineIndicator position="top" />
            <div className="min-h-screen flex flex-col">
              <Navbar />
              <main className="flex-1">{children}</main>
            </div>
          </AuthProvider>
        </RootErrorBoundary>

        {/* Web Vitals Monitoring - non-blocking */}
        <WebVitalsLoader
          enabled={enableWebVitals}
          showDebugPanel={showDebugPanel}
          analyticsEndpoint={process.env.NEXT_PUBLIC_WEB_VITALS_ENDPOINT}
        />
      </body>
    </html>
  );
}
