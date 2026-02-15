'use client'

import {
  AlertTriangle,
  CheckCircle2,
  Link as LinkIcon,
  List,
  Loader2,
  MapPin,
  X,
  XCircle,
} from 'lucide-react'
import { useState } from 'react'

import { jobImportApi } from '@/lib/api'

import type { JobImportData } from '@/types'

interface JobImportModalProps {
  onClose: () => void
  onImported: () => void
}

type Tab = 'single' | 'bulk'

interface PreviewState {
  isLoading: boolean
  error: string | null
  data: JobImportData | null
  isDuplicate: boolean
}

interface BulkProgress {
  total: number
  completed: number
  imported: number
  duplicates: number
  failed: number
  isRunning: boolean
  error: string | null
}

export function JobImportModal({
  onClose,
  onImported,
}: JobImportModalProps): React.ReactElement {
  const [activeTab, setActiveTab] = useState<Tab>('single')
  const [url, setUrl] = useState('')
  const [bulkUrls, setBulkUrls] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [preview, setPreview] = useState<PreviewState>({
    isLoading: false,
    error: null,
    data: null,
    isDuplicate: false,
  })

  const [bulkProgress, setBulkProgress] = useState<BulkProgress>({
    total: 0,
    completed: 0,
    imported: 0,
    duplicates: 0,
    failed: 0,
    isRunning: false,
    error: null,
  })

  const handlePreview = async (): Promise<void> => {
    if (!url.trim()) return

    setPreview({ isLoading: true, error: null, data: null, isDuplicate: false })
    setSaveSuccess(false)

    try {
      const result = await jobImportApi.preview(url.trim())
      if (!result.success || !result.job_data) {
        setPreview({
          isLoading: false,
          error: result.errors[0] ?? 'Failed to extract job data from this URL',
          data: null,
          isDuplicate: false,
        })
        return
      }

      setPreview({
        isLoading: false,
        error: null,
        data: result.job_data,
        isDuplicate: false,
      })
    } catch (err) {
      setPreview({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to preview job',
        data: null,
        isDuplicate: false,
      })
    }
  }

  const handleSave = async (): Promise<void> => {
    if (!url.trim()) return

    setIsSaving(true)
    setSaveSuccess(false)

    try {
      const result = await jobImportApi.importUrl(url.trim(), true)

      if (!result.success) {
        setPreview((prev) => ({
          ...prev,
          error: result.errors[0] ?? 'Failed to import job',
        }))
        setIsSaving(false)
        return
      }

      if (result.job_id !== null) {
        // Check if it was a duplicate by looking at the original preview data
        // If the import succeeded with an existing job_id, it may have been a duplicate
        setSaveSuccess(true)
        onImported()
      }
    } catch (err) {
      setPreview((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to save job',
      }))
    } finally {
      setIsSaving(false)
    }
  }

  const handleBulkImport = async (): Promise<void> => {
    const urls = bulkUrls
      .split('\n')
      .map((u) => u.trim())
      .filter((u) => u.length > 0)

    if (urls.length === 0) return

    setBulkProgress({
      total: urls.length,
      completed: 0,
      imported: 0,
      duplicates: 0,
      failed: 0,
      isRunning: true,
      error: null,
    })

    try {
      const result = await jobImportApi.importBulk(urls, true)

      const duplicates = result.results.filter(
        (r) => r.success && r.job_id === null
      ).length

      setBulkProgress({
        total: result.total_requested,
        completed: result.total_requested,
        imported: result.success_count,
        duplicates,
        failed: result.error_count,
        isRunning: false,
        error: null,
      })

      if (result.success_count > 0) {
        onImported()
      }
    } catch (err) {
      setBulkProgress((prev) => ({
        ...prev,
        isRunning: false,
        error: err instanceof Error ? err.message : 'Bulk import failed',
      }))
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-[var(--surface-strong)] rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-[var(--line)]">
          <h2 className="text-xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
            Import Jobs
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[var(--line)]">
          <button
            type="button"
            onClick={() => setActiveTab('single')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'single'
                ? 'text-[var(--accent)] border-b-2 border-[var(--accent)]'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <LinkIcon className="w-4 h-4" />
            Single URL
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('bulk')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'bulk'
                ? 'text-[var(--accent)] border-b-2 border-[var(--accent)]'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <List className="w-4 h-4" />
            Bulk Import
          </button>
        </div>

        <div className="p-4">
          {activeTab === 'single' && (
            <div>
              {/* URL input */}
              <div className="flex gap-2">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://linkedin.com/jobs/view/..."
                  className="glass-input flex-1"
                />
                <button
                  type="button"
                  onClick={() => void handlePreview()}
                  disabled={!url.trim() || preview.isLoading}
                  className="glass-button-secondary shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {preview.isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    'Preview'
                  )}
                </button>
              </div>

              {/* Error */}
              {preview.error && (
                <div className="mt-4 flex items-start gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <XCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700 dark:text-red-400">
                    {preview.error}
                  </p>
                </div>
              )}

              {/* Preview card */}
              {preview.data && !preview.error && (
                <div className="mt-4 surface-card rounded-lg p-4">
                  <h3 className="font-semibold text-[var(--ink)]">
                    {preview.data.title}
                  </h3>
                  <p className="text-sm text-[var(--muted)] mt-1">
                    {preview.data.company}
                  </p>
                  {preview.data.location && (
                    <p className="text-sm text-[var(--muted)] mt-1 flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {preview.data.location}
                    </p>
                  )}

                  {preview.isDuplicate && (
                    <div className="mt-3 flex items-center gap-2 p-2 rounded bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
                      <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                      <span className="text-sm text-yellow-700 dark:text-yellow-400">
                        Already in your pipeline
                      </span>
                    </div>
                  )}

                  {saveSuccess ? (
                    <div className="mt-3 flex items-center gap-2 text-green-600 dark:text-green-400">
                      <CheckCircle2 className="w-4 h-4" />
                      <span className="text-sm font-medium">Added to pipeline</span>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => void handleSave()}
                      disabled={isSaving || preview.isDuplicate}
                      className="mt-3 glass-button-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                      {isSaving ? 'Adding...' : 'Add to Pipeline'}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'bulk' && (
            <div>
              <textarea
                value={bulkUrls}
                onChange={(e) => setBulkUrls(e.target.value)}
                placeholder={
                  'Paste job URLs, one per line:\nhttps://linkedin.com/jobs/view/...\nhttps://indeed.com/viewjob?jk=...'
                }
                rows={6}
                className="glass-input w-full resize-none"
              />

              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-[var(--muted)]">
                  {bulkUrls
                    .split('\n')
                    .filter((u) => u.trim().length > 0).length}{' '}
                  URL(s)
                </span>
                <button
                  type="button"
                  onClick={() => void handleBulkImport()}
                  disabled={
                    bulkProgress.isRunning ||
                    bulkUrls
                      .split('\n')
                      .filter((u) => u.trim().length > 0).length === 0
                  }
                  className="glass-button-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {bulkProgress.isRunning && (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  )}
                  {bulkProgress.isRunning ? 'Importing...' : 'Import All'}
                </button>
              </div>

              {/* Progress */}
              {bulkProgress.isRunning && bulkProgress.total > 0 && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm text-[var(--muted)] mb-1">
                    <span>
                      Importing {bulkProgress.completed}/{bulkProgress.total}...
                    </span>
                  </div>
                  <div className="w-full bg-[var(--line)] rounded-full h-2">
                    <div
                      className="bg-[var(--accent)] h-2 rounded-full transition-all"
                      style={{
                        width: `${(bulkProgress.completed / bulkProgress.total) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Results summary */}
              {!bulkProgress.isRunning && bulkProgress.total > 0 && (
                <div className="mt-4 surface-card rounded-lg p-4 space-y-2">
                  <h4 className="text-sm font-semibold text-[var(--ink)]">
                    Import Results
                  </h4>
                  <div className="flex flex-wrap gap-4 text-sm">
                    {bulkProgress.imported > 0 && (
                      <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                        <CheckCircle2 className="w-4 h-4" />
                        {bulkProgress.imported} imported
                      </span>
                    )}
                    {bulkProgress.duplicates > 0 && (
                      <span className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
                        <AlertTriangle className="w-4 h-4" />
                        {bulkProgress.duplicates} duplicates
                      </span>
                    )}
                    {bulkProgress.failed > 0 && (
                      <span className="flex items-center gap-1 text-red-500">
                        <XCircle className="w-4 h-4" />
                        {bulkProgress.failed} failed
                      </span>
                    )}
                  </div>
                  {bulkProgress.error && (
                    <p className="text-sm text-red-400 mt-2">
                      {bulkProgress.error}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
