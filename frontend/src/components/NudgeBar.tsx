'use client'

import {
  ArrowRight,
  Bell,
  BookOpen,
  Clock,
  FileText,
  Mail,
  X,
} from 'lucide-react'
import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'

import { NudgeDraftModal } from '@/components/NudgeDraftModal'
import { nudgesApi } from '@/lib/api'

import type { NudgeItem } from '@/lib/api'

const STORAGE_KEY = 'resuboost_dismissed_nudges'
const DISMISS_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000 // 7 days

interface DismissedMap {
  [id: string]: number // nudge key -> expiry timestamp
}

function getNudgeKey(nudge: NudgeItem): string {
  return `${nudge.nudge_type}:${nudge.entity_type}:${nudge.entity_id ?? 'none'}`
}

function getDismissedMap(): DismissedMap {
  if (typeof window === 'undefined') return {}
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return {}
    const parsed = JSON.parse(stored) as DismissedMap
    const now = Date.now()
    // Prune expired entries
    const cleaned: DismissedMap = {}
    for (const [key, expiry] of Object.entries(parsed)) {
      if (expiry > now) {
        cleaned[key] = expiry
      }
    }
    return cleaned
  } catch {
    return {}
  }
}

function dismissNudge(nudge: NudgeItem): void {
  const map = getDismissedMap()
  map[getNudgeKey(nudge)] = Date.now() + DISMISS_EXPIRY_MS
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
  } catch {
    // localStorage may be full or disabled
  }
}

function isNudgeDismissed(nudge: NudgeItem): boolean {
  const map = getDismissedMap()
  const expiry = map[getNudgeKey(nudge)]
  if (!expiry) return false
  return expiry > Date.now()
}

type NudgeType = 'follow_up' | 'interview_prep' | 'stale_application' | 'resume_freshness'

function getNudgeIcon(nudgeType: string): React.ReactElement {
  switch (nudgeType as NudgeType) {
    case 'follow_up':
      return <Mail className="w-5 h-5" />
    case 'interview_prep':
      return <BookOpen className="w-5 h-5" />
    case 'stale_application':
      return <Clock className="w-5 h-5" />
    case 'resume_freshness':
      return <FileText className="w-5 h-5" />
    default:
      return <Bell className="w-5 h-5" />
  }
}

function getNudgeAction(nudgeType: string): { label: string; type: 'draft' | 'link'; href?: string } {
  switch (nudgeType as NudgeType) {
    case 'follow_up':
      return { label: 'Draft Email', type: 'draft' }
    case 'interview_prep':
      return { label: 'Start Prep', type: 'link', href: '/interview' }
    case 'stale_application':
      return { label: 'Follow Up', type: 'draft' }
    case 'resume_freshness':
      return { label: 'Review', type: 'link', href: '/resumes' }
    default:
      return { label: 'View', type: 'link', href: '/jobs' }
  }
}

export function NudgeBar(): React.ReactElement | null {
  const [nudges, setNudges] = useState<NudgeItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [draftNudge, setDraftNudge] = useState<NudgeItem | null>(null)
  const [dismissedKeys, setDismissedKeys] = useState<Set<string>>(new Set())

  const fetchNudges = useCallback(async () => {
    try {
      const response = await nudgesApi.list()
      setNudges(response.nudges)
    } catch {
      // Silently fail - nudges are non-critical
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchNudges()
  }, [fetchNudges])

  // Initialize dismissed keys from localStorage
  useEffect(() => {
    const map = getDismissedMap()
    setDismissedKeys(new Set(Object.keys(map)))
  }, [])

  const handleDismiss = (nudge: NudgeItem): void => {
    dismissNudge(nudge)
    setDismissedKeys((prev) => new Set([...prev, getNudgeKey(nudge)]))
  }

  const visibleNudges = nudges.filter(
    (nudge) => !isNudgeDismissed(nudge) && !dismissedKeys.has(getNudgeKey(nudge))
  )

  if (isLoading || visibleNudges.length === 0) {
    return null
  }

  const displayNudges = visibleNudges.slice(0, 3)
  const hasMore = visibleNudges.length > 3

  return (
    <>
      <div className="flex flex-col sm:flex-row gap-3">
        {displayNudges.map((nudge) => {
          const action = getNudgeAction(nudge.nudge_type)
          const key = getNudgeKey(nudge)

          return (
            <div
              key={key}
              className="surface-card rounded-lg p-3 flex-1 flex items-start gap-3 min-w-0"
            >
              <div
                className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
                style={{
                  backgroundColor: nudge.color
                    ? `${nudge.color}20`
                    : 'var(--accent-muted, rgba(99, 102, 241, 0.1))',
                  color: nudge.color || 'var(--accent)',
                }}
              >
                {getNudgeIcon(nudge.nudge_type)}
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm text-[var(--ink)] font-medium truncate">
                  {nudge.title}
                </p>
                <p className="text-xs text-[var(--muted)] mt-0.5 line-clamp-2">
                  {nudge.description}
                </p>

                <div className="mt-2 flex items-center gap-2">
                  {action.type === 'draft' ? (
                    <button
                      type="button"
                      onClick={() => setDraftNudge(nudge)}
                      className="text-xs font-medium text-[var(--accent)] hover:underline flex items-center gap-1"
                    >
                      {action.label}
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  ) : (
                    <Link
                      href={action.href ?? '/jobs'}
                      className="text-xs font-medium text-[var(--accent)] hover:underline flex items-center gap-1"
                    >
                      {action.label}
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleDismiss(nudge)}
                className="shrink-0 p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
                aria-label={`Dismiss ${nudge.title}`}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )
        })}

        {hasMore && (
          <div className="flex items-center">
            <Link
              href="/jobs"
              className="text-xs font-medium text-[var(--accent)] hover:underline whitespace-nowrap"
            >
              See all ({visibleNudges.length})
            </Link>
          </div>
        )}
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
