/**
 * Sentry Edge Runtime Configuration
 *
 * This file configures the initialization of Sentry for edge runtime.
 * The config you add here will be used whenever the edge runtime handles a request.
 *
 * @see https://docs.sentry.io/platforms/javascript/guides/nextjs/
 */

import * as Sentry from '@sentry/nextjs'

// App version for release tracking (works with both npm and bun)
const APP_VERSION = '2.0.0'

Sentry.init({
  // DSN is required - set via environment variable
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Environment configuration
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',

  // Release version for tracking deployments
  release: process.env.SENTRY_RELEASE || APP_VERSION,

  // Performance Monitoring
  // Lower sample rate for edge functions to reduce costs
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.05 : 1.0,

  // Only enable in non-development environments
  enabled: process.env.NODE_ENV !== 'development' || process.env.SENTRY_ENABLED === 'true',

  // Filter events before sending
  beforeSend(event, hint) {
    const error = hint.originalException

    // Filter out expected errors
    if (error instanceof Error) {
      // Skip authentication errors (handled by the app)
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        return null
      }
    }

    return event
  },

  // Add custom tags
  initialScope: {
    tags: {
      app: 'resuboost-ai-frontend',
      runtime: 'edge',
    },
  },
})
