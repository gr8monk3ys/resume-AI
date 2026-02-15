'use client'

import { Copy, RefreshCw, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { AIMarkdown } from '@/components/AIMarkdown'
import { nudgesApi } from '@/lib/api'

import type { DraftResponse, NudgeItem } from '@/lib/api'

interface NudgeDraftModalProps {
  nudge: NudgeItem
  onClose: () => void
}

export function NudgeDraftModal({ nudge, onClose }: NudgeDraftModalProps) {
  const [draft, setDraft] = useState<DraftResponse | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const generateDraft = useCallback(async () => {
    setIsGenerating(true)
    setError(null)
    try {
      const result = await nudgesApi.draft({
        nudge_type: nudge.nudge_type,
        entity_id: nudge.entity_id,
        entity_type: nudge.entity_type,
        company: nudge.company,
        position: nudge.position,
        recruiter_name: nudge.recruiter_name,
      })
      setDraft(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate draft')
    } finally {
      setIsGenerating(false)
    }
  }, [nudge])

  useEffect(() => {
    void generateDraft()
  }, [generateDraft])

  const handleCopy = async () => {
    if (!draft) return
    const text = draft.subject
      ? `Subject: ${draft.subject}\n\n${draft.content}`
      : draft.content
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-[var(--surface-strong)] rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-[var(--line)]">
          <h2 className="text-xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
            {nudge.title}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-4">
          {isGenerating && (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <RefreshCw className="w-6 h-6 text-[var(--accent)] animate-spin" />
              <p className="text-sm text-[var(--muted)]">Generating draft...</p>
            </div>
          )}

          {error && !isGenerating && (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <p className="text-sm text-red-400">{error}</p>
              <button
                onClick={() => void generateDraft()}
                className="glass-button-secondary text-sm"
              >
                Try again
              </button>
            </div>
          )}

          {draft && !isGenerating && (
            <>
              {draft.subject && (
                <div className="mb-4">
                  <span className="glass-label">Subject</span>
                  <p className="mt-1 text-[var(--ink)] font-medium">{draft.subject}</p>
                </div>
              )}

              <div className="rounded-lg border border-[var(--line)] p-4 mb-4">
                <AIMarkdown content={draft.content} />
              </div>

              {draft.tips.length > 0 && (
                <div className="mb-4">
                  <span className="glass-label">Tips</span>
                  <ul className="mt-1 space-y-1">
                    {draft.tips.map((tip, i) => (
                      <li key={i} className="text-sm text-[var(--muted)] flex gap-2">
                        <span className="shrink-0">•</span>
                        <span>{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>

        <div className="flex justify-end gap-3 p-4 border-t border-[var(--line)]">
          <button
            onClick={() => void generateDraft()}
            disabled={isGenerating}
            className="glass-button-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isGenerating ? 'animate-spin' : ''}`} />
            Regenerate
          </button>
          <button
            onClick={() => void handleCopy()}
            disabled={!draft || isGenerating}
            className="glass-button-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Copy className="w-4 h-4" />
            {copied ? 'Copied!' : 'Copy to clipboard'}
          </button>
        </div>
      </div>
    </div>
  )
}
