'use client'

import { Check, X } from 'lucide-react'
import { useState } from 'react'

interface PricingComparisonProps {
  onUpgrade: (priceId: string) => void
  currentPlan?: string
  isLoading?: boolean
}

interface FeatureRow {
  label: string
  free: string
  pro: string
  freeHas: boolean
  proHas: boolean
}

const FEATURES: FeatureRow[] = [
  { label: 'Job imports', free: '5', pro: 'Unlimited', freeHas: true, proHas: true },
  { label: 'AI generations', free: '3/day', pro: 'Unlimited', freeHas: true, proHas: true },
  { label: 'Job tracking', free: '20', pro: 'Unlimited', freeHas: true, proHas: true },
  { label: 'Resume versions', free: '2', pro: 'Unlimited', freeHas: true, proHas: true },
  { label: 'Analytics', free: 'Basic', pro: 'Full', freeHas: true, proHas: true },
  { label: 'Interview prep', free: '1/week', pro: 'Unlimited', freeHas: true, proHas: true },
  { label: 'Company research', free: '3', pro: 'Unlimited', freeHas: true, proHas: true },
  { label: 'Scheduled imports', free: '', pro: 'Yes', freeHas: false, proHas: true },
  { label: 'Email notifications', free: '', pro: 'Yes', freeHas: false, proHas: true },
]

const MONTHLY_PRICE_ID = 'price_pro_monthly'
const ANNUAL_PRICE_ID = 'price_pro_annual'

export function PricingComparison({
  onUpgrade,
  currentPlan,
  isLoading = false,
}: PricingComparisonProps): React.ReactElement {
  const [isAnnual, setIsAnnual] = useState(false)

  const isPro = currentPlan === 'pro_monthly' || currentPlan === 'pro_annual'
  const monthlyPrice = isAnnual ? 12 : 15
  const priceId = isAnnual ? ANNUAL_PRICE_ID : MONTHLY_PRICE_ID

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Billing toggle */}
      <div className="flex items-center justify-center gap-3 mb-8">
        <span
          className={`text-sm font-medium ${
            !isAnnual ? 'text-[var(--ink)]' : 'text-[var(--muted)]'
          }`}
        >
          Monthly
        </span>
        <button
          type="button"
          role="switch"
          aria-checked={isAnnual}
          onClick={() => setIsAnnual((prev) => !prev)}
          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${
            isAnnual ? 'bg-[var(--accent)]' : 'bg-[var(--muted-soft)]'
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform duration-200 ${
              isAnnual ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </button>
        <span
          className={`text-sm font-medium ${
            isAnnual ? 'text-[var(--ink)]' : 'text-[var(--muted)]'
          }`}
        >
          Annual
        </span>
        {isAnnual && (
          <span className="ml-1 inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
            Save 20%
          </span>
        )}
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Free plan */}
        <div className="surface-card rounded-lg p-6 flex flex-col">
          <h3 className="text-lg font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
            Free
          </h3>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-[var(--ink)]">$0</span>
            <span className="text-sm text-[var(--muted)]">/mo</span>
          </div>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Get started with essential tools
          </p>

          <ul className="mt-6 space-y-3 flex-1">
            {FEATURES.map((feature) => (
              <li key={feature.label} className="flex items-center gap-2 text-sm">
                {feature.freeHas ? (
                  <Check className="w-4 h-4 text-green-500 shrink-0" />
                ) : (
                  <X className="w-4 h-4 text-[var(--muted-soft)] shrink-0" />
                )}
                <span className={feature.freeHas ? 'text-[var(--ink)]' : 'text-[var(--muted-soft)]'}>
                  {feature.label}
                  {feature.free && (
                    <span className="text-[var(--muted)] ml-1">({feature.free})</span>
                  )}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-6">
            {!isPro && !currentPlan ? (
              <button
                type="button"
                className="glass-button-secondary w-full"
              >
                Start Free
              </button>
            ) : !isPro ? (
              <button
                type="button"
                disabled
                className="glass-button-secondary w-full opacity-60 cursor-not-allowed"
              >
                Current Plan
              </button>
            ) : (
              <button
                type="button"
                className="glass-button-secondary w-full opacity-60 cursor-not-allowed"
                disabled
              >
                Free Tier
              </button>
            )}
          </div>
        </div>

        {/* Pro plan */}
        <div className="surface-card rounded-lg p-6 flex flex-col ring-2 ring-[var(--accent)]">
          <h3 className="text-lg font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
            Pro
          </h3>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-[var(--ink)]">${monthlyPrice}</span>
            <span className="text-sm text-[var(--muted)]">/mo</span>
          </div>
          {isAnnual && (
            <p className="mt-1 text-xs text-[var(--muted)]">
              Billed as ${monthlyPrice * 12}/year
            </p>
          )}
          <p className="mt-2 text-sm text-[var(--muted)]">
            Unlock your full job search potential
          </p>

          <ul className="mt-6 space-y-3 flex-1">
            {FEATURES.map((feature) => (
              <li key={feature.label} className="flex items-center gap-2 text-sm">
                {feature.proHas ? (
                  <Check className="w-4 h-4 text-green-500 shrink-0" />
                ) : (
                  <X className="w-4 h-4 text-[var(--muted-soft)] shrink-0" />
                )}
                <span className="text-[var(--ink)]">
                  {feature.label}
                  {feature.pro && (
                    <span className="text-[var(--muted)] ml-1">({feature.pro})</span>
                  )}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-6">
            {isPro ? (
              <button
                type="button"
                disabled
                className="glass-button-primary w-full opacity-60 cursor-not-allowed"
              >
                Current Plan
              </button>
            ) : (
              <button
                type="button"
                disabled={isLoading}
                onClick={() => onUpgrade(priceId)}
                className="glass-button-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Processing...' : 'Upgrade to Pro'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
