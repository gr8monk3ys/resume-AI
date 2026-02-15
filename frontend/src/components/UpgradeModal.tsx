'use client'

import { Sparkles, X } from 'lucide-react'
import { useState } from 'react'

import { billingApi } from '@/lib/api'

interface UpgradeModalProps {
  feature: string
  limit: number
  used: number
  resetAt: string | null
  onClose: () => void
}

function formatResetDate(resetAt: string): string {
  const date = new Date(resetAt)
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

const PRO_MONTHLY_PRICE_ID = 'price_pro_monthly'

export function UpgradeModal({
  feature,
  limit,
  used,
  resetAt,
  onClose,
}: UpgradeModalProps): React.ReactElement {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleUpgrade = async (): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      const { url } = await billingApi.createCheckout(PRO_MONTHLY_PRICE_ID)
      window.location.href = url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start checkout')
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-[var(--surface-strong)] rounded-lg shadow-xl max-w-md w-full">
        <div className="flex items-center justify-between p-4 border-b border-[var(--line)]">
          <h2 className="text-xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
            You&apos;ve reached your limit
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6">
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 rounded-full bg-[var(--accent)] bg-opacity-10 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-[var(--accent)]" />
            </div>
          </div>

          <p className="text-center text-[var(--ink)] mb-2">
            You&apos;ve used{' '}
            <span className="font-bold">
              {used}/{limit}
            </span>{' '}
            {feature} for this period.
          </p>

          {resetAt && (
            <p className="text-center text-sm text-[var(--muted)] mb-4">
              Resets {formatResetDate(resetAt)}
            </p>
          )}

          {/* Usage bar */}
          <div className="w-full bg-[var(--line)] rounded-full h-2 mb-6">
            <div
              className="bg-[var(--accent)] h-2 rounded-full transition-all"
              style={{ width: `${Math.min((used / limit) * 100, 100)}%` }}
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 text-center mb-4">{error}</p>
          )}
        </div>

        <div className="flex flex-col gap-3 p-4 border-t border-[var(--line)]">
          <button
            type="button"
            onClick={() => void handleUpgrade()}
            disabled={isLoading}
            className="glass-button-primary w-full disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            {isLoading ? 'Redirecting...' : 'Upgrade to Pro \u2014 $15/mo'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="glass-button-secondary w-full"
          >
            Maybe later
          </button>
        </div>
      </div>
    </div>
  )
}
