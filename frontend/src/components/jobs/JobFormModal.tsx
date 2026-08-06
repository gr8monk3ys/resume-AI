'use client'

import { X } from 'lucide-react'
import { useState } from 'react'

import { JOB_STATUSES } from '@/lib/jobs'

import type { JobApplication, JobStatus } from '@/types'

interface JobFormModalProps {
  job?: JobApplication | null
  initialStatus?: JobStatus
  onClose: () => void
  onSave: (data: Partial<JobApplication>) => void
  onDelete?: (id: number) => void
}

export function JobFormModal({
  job,
  initialStatus,
  onClose,
  onSave,
  onDelete,
}: JobFormModalProps) {
  const [formData, setFormData] = useState({
    company: job?.company || '',
    position: job?.position || '',
    job_description: job?.job_description || '',
    status: job?.status || initialStatus || ('Bookmarked'),
    application_date: job?.application_date || '',
    deadline: job?.deadline || '',
    location: job?.location || '',
    job_url: job?.job_url || '',
    notes: job?.notes || '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      onSave(formData)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-[var(--surface-strong)] rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-[var(--line)]">
          <h2 className="text-xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">
            {job ? 'Edit Job Application' : 'Add Job Application'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={(e) => { void handleSubmit(e) }} className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="company" className="glass-label mb-1">
                Company <span className="text-red-500">*</span>
              </label>
              <input
                id="company"
                type="text"
                required
                value={formData.company}
                onChange={(e) =>
                  setFormData({ ...formData, company: e.target.value })
                }
                className="w-full glass-input"
              />
            </div>

            <div>
              <label htmlFor="position" className="glass-label mb-1">
                Position <span className="text-red-500">*</span>
              </label>
              <input
                id="position"
                type="text"
                required
                value={formData.position}
                onChange={(e) =>
                  setFormData({ ...formData, position: e.target.value })
                }
                className="w-full glass-input"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="status" className="glass-label mb-1">
                Status
              </label>
              <select
                id="status"
                value={formData.status}
                onChange={(e) =>
                  setFormData({ ...formData, status: e.target.value as JobStatus })
                }
                className="w-full glass-select"
              >
                {JOB_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="location" className="glass-label mb-1">
                Location
              </label>
              <input
                id="location"
                type="text"
                value={formData.location}
                onChange={(e) =>
                  setFormData({ ...formData, location: e.target.value })
                }
                className="w-full glass-input"
                placeholder="Remote, New York, etc."
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="application_date" className="glass-label mb-1">
                Application Date
              </label>
              <input
                id="application_date"
                type="date"
                value={formData.application_date}
                onChange={(e) =>
                  setFormData({ ...formData, application_date: e.target.value })
                }
                className="w-full glass-input"
              />
            </div>

            <div>
              <label htmlFor="deadline" className="glass-label mb-1">
                Deadline
              </label>
              <input
                id="deadline"
                type="date"
                value={formData.deadline}
                onChange={(e) =>
                  setFormData({ ...formData, deadline: e.target.value })
                }
                className="w-full glass-input"
              />
            </div>
          </div>

          <div>
            <label htmlFor="job_url" className="glass-label mb-1">
              Job URL
            </label>
            <input
              id="job_url"
              type="url"
              value={formData.job_url}
              onChange={(e) =>
                setFormData({ ...formData, job_url: e.target.value })
              }
              className="w-full glass-input"
              placeholder="https://..."
            />
          </div>

          <div>
            <label htmlFor="job_description" className="glass-label mb-1">
              Job Description
            </label>
            <textarea
              id="job_description"
              rows={4}
              value={formData.job_description}
              onChange={(e) =>
                setFormData({ ...formData, job_description: e.target.value })
              }
              className="w-full glass-textarea"
              placeholder="Paste the job description here for better match scoring..."
            />
          </div>

          <div>
            <label htmlFor="notes" className="glass-label mb-1">
              Notes
            </label>
            <textarea
              id="notes"
              rows={3}
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              className="w-full glass-textarea"
              placeholder="Any additional notes..."
            />
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-[var(--line)]">
            {job && onDelete ? (
              <button
                type="button"
                onClick={() => {
                  if (confirm('Are you sure you want to delete this job application?')) {
                    onDelete(job.id)
                  }
                }}
                className="glass-button-danger"
              >
                Delete
              </button>
            ) : (
              <div />
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="glass-button-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="glass-button-primary disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : job ? 'Save Changes' : 'Add Job'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
