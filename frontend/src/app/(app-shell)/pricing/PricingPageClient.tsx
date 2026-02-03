'use client'

import { useEffect, useState } from 'react'

import { PricingComparison } from '@/components/PricingComparison'
import { billingApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

import type { BillingStatus } from '@/types'

export default function PricingPageClient(): React.ReactElement {
  const { isAuthenticated } = useAuth()
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isUpgrading, setIsUpgrading] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) return

    let isMounted = true

    async function fetchStatus(): Promise<void> {
      try {
        const status = await billingApi.getStatus()
        if (isMounted) {
          setBillingStatus(status)
        }
      } catch {
        // Non-critical, continue with no plan info
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    setIsLoading(true)
    void fetchStatus()

    return () => {
      isMounted = false
    }
  }, [isAuthenticated])

  const handleUpgrade = async (priceId: string): Promise<void> => {
    if (!isAuthenticated) {
      window.location.href = '/register'
      return
    }

    setIsUpgrading(true)
    try {
      const { url } = await billingApi.createCheckout(priceId)
      window.location.href = url
    } catch {
      setIsUpgrading(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 text-center">
        <h1 className="font-display text-3xl font-bold tracking-[-0.03em] text-[var(--ink)] sm:text-4xl">
          Choose your plan
        </h1>
        <p className="mt-2 text-[var(--muted)]">
          Start free and upgrade when you need more power.
        </p>
      </div>

      {isLoading ? (
        <div className="flex min-h-[300px] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-[var(--accent)]" />
        </div>
      ) : (
        <PricingComparison
          onUpgrade={(priceId) => void handleUpgrade(priceId)}
          currentPlan={billingStatus?.plan}
          isLoading={isUpgrading}
        />
      )}
    </div>
  )
}
