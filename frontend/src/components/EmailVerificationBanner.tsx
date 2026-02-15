'use client'

import { Loader2, Mail, X } from 'lucide-react'
import { useState } from 'react'

import { onboardingApi } from '@/lib/api'

interface EmailVerificationBannerProps {
  onDismiss?: () => void
}

export function EmailVerificationBanner({
  onDismiss,
}: EmailVerificationBannerProps): React.ReactElement {
  const [isDismissed, setIsDismissed] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [resendMessage, setResendMessage] = useState<string | null>(null)

  const handleResend = async (): Promise<void> => {
    setIsResending(true)
    setResendMessage(null)

    try {
      await onboardingApi.resendVerification()
      setResendMessage('Verification email sent. Check your inbox.')
    } catch {
      setResendMessage('Failed to send verification email. Try again later.')
    } finally {
      setIsResending(false)
    }
  }

  const handleDismiss = (): void => {
    setIsDismissed(true)
    onDismiss?.()
  }

  if (isDismissed) {
    return <></>
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border border-[var(--status-warning-border)] bg-[var(--status-warning-bg)] px-4 py-3">
      <Mail className="h-5 w-5 shrink-0 text-[var(--status-warning-text)]" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--status-warning-text)]">
          Please verify your email address.
        </p>
        {resendMessage && (
          <p className="mt-1 text-xs text-[var(--status-warning-text)] opacity-80">
            {resendMessage}
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={() => void handleResend()}
        disabled={isResending}
        className="shrink-0 text-sm font-medium text-[var(--status-warning-text)] underline hover:no-underline disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isResending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          'Resend'
        )}
      </button>
      <button
        type="button"
        onClick={handleDismiss}
        className="shrink-0 p-1 text-[var(--status-warning-text)] opacity-60 hover:opacity-100"
        aria-label="Dismiss verification banner"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
