'use client'

import { Sparkles, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { NudgeDraftModal } from '@/components/NudgeDraftModal'
import { nudgesApi } from '@/lib/api'

import type { NudgeItem } from '@/lib/api'

function getDismissKey(nudge: NudgeItem): string {
  if (nudge.nudge_type === 'application_velocity') {
    const now = new Date()
    const jan1 = new Date(now.getFullYear(), 0, 1)
    const weekNum = Math.ceil(((now.getTime() - jan1.getTime()) / 86400000 + jan1.getDay() + 1) / 7)
    return `nudge_dismissed_application_velocity_${now.getFullYear()}-W${String(weekNum).padStart(2, '0')}`
  }
  return `nudge_dismissed_${nudge.nudge_type}_${nudge.entity_id ?? 'none'}`
}

function isDismissed(nudge: NudgeItem): boolean {
  if (typeof window === 'undefined') return false
  return localStorage.getItem(getDismissKey(nudge)) === '1'
}

export function ActionItemsGrid() {
  const [nudges, setNudges] = useState<NudgeItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [draftNudge, setDraftNudge] = useState<NudgeItem | null>(null)

  const fetchNudges = useCallback(async () => {
    try {
      const response = await nudgesApi.list()
      setNudges(response.nudges.filter((n) => !isDismissed(n)))
    } catch {
      // Silently fail — nudges are non-critical
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchNudges()
  }, [fetchNudges])

  const handleDismiss = (nudge: NudgeItem) => {
    localStorage.setItem(getDismissKey(nudge), '1')
    setNudges((prev) => prev.filter((n) => n !== nudge))
  }

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-32 rounded-lg bg-[var(--surface-strong)] animate-pulse"
          />
        ))}
      </div>
    )
  }

  if (nudges.length === 0) return null

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {nudges.map((nudge, i) => (
          <div
            key={`${nudge.nudge_type}-${nudge.entity_id ?? i}`}
            className="relative rounded-lg border border-[var(--line)] bg-[var(--surface-strong)] p-4 flex flex-col gap-2"
            style={{ borderLeftWidth: '4px', borderLeftColor: nudge.color }}
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-[var(--ink)] font-display tracking-[-0.02em] leading-tight">
                {nudge.title}
              </h3>
              <button
                onClick={() => handleDismiss(nudge)}
                className="shrink-0 p-0.5 text-[var(--muted-soft)] hover:text-[var(--muted)] transition-colors"
                aria-label="Dismiss nudge"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-[var(--ink-secondary)] leading-relaxed flex-1">
              {nudge.description}
            </p>

            <button
              onClick={() => setDraftNudge(nudge)}
              className="mt-1 self-start inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors"
              style={{
                backgroundColor: `${nudge.color}18`,
                color: nudge.color,
              }}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Draft for me
            </button>
          </div>
        ))}
      </div>

      {draftNudge && (
        <NudgeDraftModal
          nudge={draftNudge}
          onClose={() => setDraftNudge(null)}
        />
      )}
    </>
  )
}
