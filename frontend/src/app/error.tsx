'use client'

import { ErrorFallback } from '@/components/ErrorFallback'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}): React.ReactElement {
  return (
    <ErrorFallback
      error={error}
      resetErrorBoundary={reset}
      title="Something went wrong"
      description="An unexpected error occurred. Please try again or return to the home page."
    />
  )
}
