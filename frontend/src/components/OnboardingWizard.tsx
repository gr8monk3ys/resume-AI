'use client'

import {
  ArrowRight,
  Briefcase,
  CheckCircle2,
  FileUp,
  Loader2,
  MapPin,
  Sparkles,
  Upload,
  X,
} from 'lucide-react'
import { useCallback, useRef, useState } from 'react'

import { aiApi, jobImportApi, onboardingApi, resumesApi } from '@/lib/api'

import type { JobImportData, Resume, TailorResumeResponse } from '@/types'

interface OnboardingWizardProps {
  onComplete: () => void
  onDismiss: () => void
}

interface ImportedJob {
  id: number
  data: JobImportData
}

export function OnboardingWizard({
  onComplete,
  onDismiss,
}: OnboardingWizardProps): React.ReactElement {
  const [step, setStep] = useState(1)

  // Step 1 state
  const [jobUrl, setJobUrl] = useState('')
  const [jobPreview, setJobPreview] = useState<JobImportData | null>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [isSavingJob, setIsSavingJob] = useState(false)
  const [importedJob, setImportedJob] = useState<ImportedJob | null>(null)
  const [jobError, setJobError] = useState<string | null>(null)

  // Step 2 state
  const [uploadedResume, setUploadedResume] = useState<Resume | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Step 3 state
  const [tailorResult, setTailorResult] = useState<TailorResumeResponse | null>(null)
  const [isTailoring, setIsTailoring] = useState(false)
  const [tailorError, setTailorError] = useState<string | null>(null)

  // ---------- Step 1 handlers ----------
  const handlePreviewJob = async (): Promise<void> => {
    if (!jobUrl.trim()) return

    setIsPreviewLoading(true)
    setJobError(null)
    setJobPreview(null)

    try {
      const result = await jobImportApi.preview(jobUrl.trim())
      if (!result.success || !result.job_data) {
        setJobError(result.errors[0] ?? 'Could not extract job data')
        return
      }
      setJobPreview(result.job_data)
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setIsPreviewLoading(false)
    }
  }

  const handleSaveJob = async (): Promise<void> => {
    if (!jobUrl.trim()) return

    setIsSavingJob(true)
    setJobError(null)

    try {
      const result = await jobImportApi.importUrl(jobUrl.trim(), true)
      if (!result.success || !result.job_data) {
        setJobError(result.errors[0] ?? 'Failed to import job')
        return
      }
      setImportedJob({
        id: result.job_id ?? 0,
        data: result.job_data,
      })
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setIsSavingJob(false)
    }
  }

  const goToStep = useCallback(
    async (nextStep: number) => {
      setStep(nextStep)
      try {
        await onboardingApi.update({ onboarding_step: nextStep })
      } catch {
        // Non-critical, continue
      }
    },
    []
  )

  // ---------- Step 2 handlers ----------
  const handleFileUpload = async (file: File): Promise<void> => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]
    if (!validTypes.includes(file.type)) {
      setUploadError('Please upload a PDF or DOCX file')
      return
    }

    setIsUploading(true)
    setUploadError(null)

    try {
      const resume = await resumesApi.upload(file)
      setUploadedResume(resume)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault()
    setIsDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      void handleFileUpload(file)
    }
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (): void => {
    setIsDragOver(false)
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const file = e.target.files?.[0]
    if (file) {
      void handleFileUpload(file)
    }
  }

  // ---------- Step 3 handlers ----------
  const handleTailor = useCallback(async (): Promise<void> => {
    if (!uploadedResume || !importedJob) return

    setIsTailoring(true)
    setTailorError(null)

    try {
      const result = await aiApi.tailorResume(
        uploadedResume.content,
        importedJob.data.description ?? ''
      )
      setTailorResult(result)
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : 'Optimization failed')
    } finally {
      setIsTailoring(false)
    }
  }, [uploadedResume, importedJob])

  const handleComplete = async (): Promise<void> => {
    try {
      await onboardingApi.update({ onboarding_completed: true })
    } catch {
      // Non-critical
    }
    onComplete()
  }

  const handleDismiss = async (): Promise<void> => {
    try {
      await onboardingApi.update({ onboarding_dismissed: true })
    } catch {
      // Non-critical
    }
    onDismiss()
  }

  const canShowMagic = importedJob !== null && uploadedResume !== null

  return (
    <div className="fixed inset-0 z-50 bg-[var(--surface)] overflow-y-auto">
      {/* Top bar with dismiss */}
      <div className="flex items-center justify-between p-4 max-w-3xl mx-auto">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-[var(--accent)]" />
          <span className="text-sm font-medium text-[var(--muted)]">
            Welcome to ResuBoost
          </span>
        </div>
        <button
          type="button"
          onClick={() => void handleDismiss()}
          className="p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
          aria-label="Dismiss onboarding"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Progress indicator */}
      <div className="flex items-center justify-center gap-2 mb-8">
        {[1, 2, 3].map((s) => (
          <div
            key={s}
            className={`w-3 h-3 rounded-full transition-colors ${
              s === step
                ? 'bg-[var(--accent)]'
                : s < step
                  ? 'bg-[var(--accent)] opacity-50'
                  : 'bg-[var(--line)]'
            }`}
          />
        ))}
      </div>

      <div className="max-w-3xl mx-auto px-4 pb-12">
        {/* =========== STEP 1 =========== */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-[var(--accent)] bg-opacity-10 flex items-center justify-center mx-auto mb-4">
                <Briefcase className="w-8 h-8 text-[var(--accent)]" />
              </div>
              <h1 className="text-2xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
                Import your first job
              </h1>
              <p className="mt-2 text-[var(--muted)] max-w-md mx-auto">
                Paste a job posting URL and we&apos;ll extract the details automatically.
              </p>
            </div>

            <div className="max-w-lg mx-auto space-y-4">
              <div className="flex gap-2">
                <input
                  type="url"
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                  placeholder="https://linkedin.com/jobs/view/..."
                  className="glass-input flex-1"
                />
                <button
                  type="button"
                  onClick={() => void handlePreviewJob()}
                  disabled={!jobUrl.trim() || isPreviewLoading}
                  className="glass-button-secondary shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isPreviewLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    'Preview'
                  )}
                </button>
              </div>

              {jobError && (
                <p className="text-sm text-red-400">{jobError}</p>
              )}

              {jobPreview && !importedJob && (
                <div className="surface-card rounded-lg p-4">
                  <h3 className="font-semibold text-[var(--ink)]">
                    {jobPreview.title}
                  </h3>
                  <p className="text-sm text-[var(--muted)] mt-1">
                    {jobPreview.company}
                  </p>
                  {jobPreview.location && (
                    <p className="text-sm text-[var(--muted)] mt-1 flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {jobPreview.location}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={() => void handleSaveJob()}
                    disabled={isSavingJob}
                    className="mt-3 glass-button-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isSavingJob && <Loader2 className="w-4 h-4 animate-spin" />}
                    {isSavingJob ? 'Adding...' : 'Add to Pipeline'}
                  </button>
                </div>
              )}

              {importedJob && (
                <div className="surface-card rounded-lg p-4">
                  <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-medium">
                      {importedJob.data.company} &mdash; {importedJob.data.title}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--muted)] mt-1">
                    Added to your pipeline
                  </p>
                </div>
              )}

              <div className="flex items-center justify-between pt-4">
                <button
                  type="button"
                  onClick={() => void goToStep(2)}
                  className="text-sm text-[var(--muted)] hover:text-[var(--ink)]"
                >
                  Skip
                </button>
                {importedJob && (
                  <button
                    type="button"
                    onClick={() => void goToStep(2)}
                    className="glass-button-primary flex items-center gap-2"
                  >
                    Next
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* =========== STEP 2 =========== */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-[var(--accent)] bg-opacity-10 flex items-center justify-center mx-auto mb-4">
                <FileUp className="w-8 h-8 text-[var(--accent)]" />
              </div>
              <h1 className="text-2xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
                Upload your resume
              </h1>
              <p className="mt-2 text-[var(--muted)] max-w-md mx-auto">
                Upload your resume so we can optimize it for each job you apply to.
              </p>
            </div>

            <div className="max-w-lg mx-auto space-y-4">
              {!uploadedResume ? (
                <>
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => fileInputRef.current?.click()}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        fileInputRef.current?.click()
                      }
                    }}
                    className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                      isDragOver
                        ? 'border-[var(--accent)] bg-[var(--accent)] bg-opacity-5'
                        : 'border-[var(--line)] hover:border-[var(--muted-soft)]'
                    }`}
                  >
                    {isUploading ? (
                      <div className="flex flex-col items-center gap-3">
                        <Loader2 className="w-8 h-8 text-[var(--accent)] animate-spin" />
                        <p className="text-sm text-[var(--muted)]">Uploading...</p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-3">
                        <Upload className="w-8 h-8 text-[var(--muted)]" />
                        <p className="text-sm text-[var(--ink)]">
                          Drag and drop your resume here
                        </p>
                        <p className="text-xs text-[var(--muted)]">
                          PDF or DOCX, up to 10MB
                        </p>
                      </div>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx"
                    onChange={handleFileInputChange}
                    className="hidden"
                  />
                </>
              ) : (
                <div className="surface-card rounded-lg p-4">
                  <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-medium">
                      {uploadedResume.version_name}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--muted)] mt-1">
                    Resume uploaded successfully
                  </p>
                  {uploadedResume.content && (
                    <div className="mt-3 max-h-32 overflow-y-auto rounded border border-[var(--line)] p-3">
                      <p className="text-xs text-[var(--muted)] whitespace-pre-wrap line-clamp-6">
                        {uploadedResume.content.slice(0, 500)}
                        {uploadedResume.content.length > 500 ? '...' : ''}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {uploadError && (
                <p className="text-sm text-red-400">{uploadError}</p>
              )}

              <div className="flex items-center justify-between pt-4">
                <button
                  type="button"
                  onClick={() => void goToStep(3)}
                  className="text-sm text-[var(--muted)] hover:text-[var(--ink)]"
                >
                  Skip
                </button>
                {uploadedResume && (
                  <button
                    type="button"
                    onClick={() => void goToStep(3)}
                    className="glass-button-primary flex items-center gap-2"
                  >
                    Next
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* =========== STEP 3 =========== */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-[var(--accent)] bg-opacity-10 flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-8 h-8 text-[var(--accent)]" />
              </div>
              <h1 className="text-2xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
                See the magic
              </h1>
              <p className="mt-2 text-[var(--muted)] max-w-md mx-auto">
                {canShowMagic
                  ? `Watch AI optimize your resume for ${importedJob?.data.company ?? 'the role'}.`
                  : 'Complete both previous steps to see AI optimization in action.'}
              </p>
            </div>

            {canShowMagic ? (
              <div className="max-w-3xl mx-auto space-y-4">
                {!tailorResult && !isTailoring && !tailorError && (
                  <div className="text-center">
                    <button
                      type="button"
                      onClick={() => void handleTailor()}
                      className="glass-button-primary flex items-center gap-2 mx-auto"
                    >
                      <Sparkles className="w-4 h-4" />
                      Optimize Resume
                    </button>
                  </div>
                )}

                {isTailoring && (
                  <div className="flex flex-col items-center justify-center py-12 gap-3">
                    <Loader2 className="w-8 h-8 text-[var(--accent)] animate-spin" />
                    <p className="text-sm text-[var(--muted)]">
                      Optimizing your resume for {importedJob?.data.company}...
                    </p>
                  </div>
                )}

                {tailorError && (
                  <div className="text-center">
                    <p className="text-sm text-red-400 mb-3">{tailorError}</p>
                    <button
                      type="button"
                      onClick={() => void handleTailor()}
                      className="glass-button-secondary text-sm"
                    >
                      Try again
                    </button>
                  </div>
                )}

                {tailorResult && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="surface-card rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-[var(--muted)] mb-2">
                        Your Resume
                      </h3>
                      <div className="max-h-64 overflow-y-auto">
                        <p className="text-xs text-[var(--ink)] whitespace-pre-wrap">
                          {uploadedResume?.content?.slice(0, 1000) ?? ''}
                          {(uploadedResume?.content?.length ?? 0) > 1000
                            ? '...'
                            : ''}
                        </p>
                      </div>
                    </div>
                    <div className="surface-card rounded-lg p-4 ring-2 ring-[var(--accent)]">
                      <h3 className="text-sm font-semibold text-[var(--accent)] mb-2">
                        Optimized for {importedJob?.data.company}{' '}
                        {importedJob?.data.title}
                      </h3>
                      <div className="max-h-64 overflow-y-auto">
                        <p className="text-xs text-[var(--ink)] whitespace-pre-wrap">
                          {tailorResult.tailored_resume.slice(0, 1000)}
                          {tailorResult.tailored_resume.length > 1000
                            ? '...'
                            : ''}
                        </p>
                      </div>
                      {tailorResult.changes_made.length > 0 && (
                        <div className="mt-3 border-t border-[var(--line)] pt-3">
                          <p className="text-xs font-medium text-[var(--muted)] mb-1">
                            Changes made:
                          </p>
                          <ul className="space-y-1">
                            {tailorResult.changes_made.slice(0, 5).map((change, i) => (
                              <li
                                key={i}
                                className="text-xs text-[var(--muted)] flex gap-1"
                              >
                                <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0 mt-0.5" />
                                {change}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="max-w-md mx-auto surface-card rounded-lg p-6 text-center">
                <p className="text-sm text-[var(--muted)]">
                  Complete both steps to see AI optimization:
                </p>
                <ul className="mt-3 space-y-2 text-sm">
                  <li className="flex items-center gap-2 justify-center">
                    {importedJob ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-[var(--line)]" />
                    )}
                    <span
                      className={
                        importedJob ? 'text-[var(--ink)]' : 'text-[var(--muted)]'
                      }
                    >
                      Import a job
                    </span>
                  </li>
                  <li className="flex items-center gap-2 justify-center">
                    {uploadedResume ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-[var(--line)]" />
                    )}
                    <span
                      className={
                        uploadedResume
                          ? 'text-[var(--ink)]'
                          : 'text-[var(--muted)]'
                      }
                    >
                      Upload a resume
                    </span>
                  </li>
                </ul>
              </div>
            )}

            <div className="flex justify-center pt-4">
              <button
                type="button"
                onClick={() => void handleComplete()}
                className="glass-button-primary flex items-center gap-2"
              >
                Go to Dashboard
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
