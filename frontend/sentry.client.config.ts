/**
 * Sentry Client-side Configuration
 *
 * This file configures the initialization of Sentry on the client.
 * The config you add here will be used whenever a users loads a page in their browser.
 *
 * @see https://docs.sentry.io/platforms/javascript/guides/nextjs/
 */

import * as Sentry from '@sentry/nextjs'

Sentry.init({
  // DSN is required - set via environment variable
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Environment configuration
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',

  // Release version for tracking deployments
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE || process.env.npm_package_version,

  // Performance Monitoring
  // Adjust this value in production, or use tracesSampler for greater control
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  // Session Replay
  // This sets the sample rate at 10%. You may want to change it to 100%
  // while in development and then sample at a lower rate in production.
  replaysSessionSampleRate: 0.1,

  // If you're not already sampling the entire session, change the sample rate
  // to 100% when sampling sessions where errors occur.
  replaysOnErrorSampleRate: 1.0,

  // Only enable in non-development environments
  enabled: process.env.NODE_ENV !== 'development' || process.env.NEXT_PUBLIC_SENTRY_ENABLED === 'true',

  // Integrations
  integrations: [
    // Capture console.error as breadcrumbs
    Sentry.breadcrumbsIntegration({
      console: true,
      dom: true,
      fetch: true,
      history: true,
      xhr: true,
    }),

    // Session Replay integration
    Sentry.replayIntegration({
      // Mask all text content for privacy
      maskAllText: true,
      // Block all media (images, videos) for privacy
      blockAllMedia: true,
    }),
  ],

  // Filter events before sending
  beforeSend(event, hint) {
    // Filter out specific errors if needed
    const error = hint.originalException

    // Skip certain expected errors
    if (error instanceof Error) {
      // Skip network errors that are expected (e.g., user offline)
      if (error.message.includes('Failed to fetch') && !navigator.onLine) {
        return null
      }

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
    },
  },

  // Ignore specific errors
  ignoreErrors: [
    // Browser extensions
    'top.GLOBALS',
    'originalCreateNotification',
    'canvas.contentDocument',
    'MyApp_RemoveAllHighlights',
    'atomicFindClose',
    // Chrome extensions
    /^chrome:\/\//,
    /^chrome-extension:\/\//,
    // Firefox extensions
    /^moz-extension:\/\//,
    // Safari extensions
    /^safari-extension:\/\//,
    // Network errors
    'NetworkError',
    'Network request failed',
    // AbortController errors
    'AbortError',
    // ResizeObserver errors (common in UI libraries)
    'ResizeObserver loop limit exceeded',
    'ResizeObserver loop completed with undelivered notifications',
  ],

  // URLs to ignore
  denyUrls: [
    // Browser extensions
    /extensions\//i,
    /^chrome:\/\//i,
    /^chrome-extension:\/\//i,
    /^moz-extension:\/\//i,
    /^safari-extension:\/\//i,
  ],
})
