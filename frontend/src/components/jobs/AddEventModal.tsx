'use client'

import { X } from 'lucide-react'
import { useState } from 'react'

import { EVENT_TYPES } from '@/lib/jobs'

import type { JobApplication, InterviewEvent, InterviewEventType } from '@/types'

interface AddEventModalProps {
  jobs: JobApplication[]
  onClose: () => void
  onAdd: (event: Omit<InterviewEvent, 'id' | 'created_at'>) => void
}

export function AddEventModal({ jobs, onClose, onAdd }: AddEventModalProps) {
  const [formData, setFormData] = useState({
    job_application_id: 0,
    event_type: 'phone_screen' as InterviewEventType,
    scheduled_date: '',
    scheduled_time: '',
    duration_minutes: 60,
    location: '',
    meeting_link: '',
    interviewer_names: '',
    notes: '',
    follow_up_date: '',
  })

  const selectedJob = jobs.find((j) => j.id === formData.job_application_id)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const event: Omit<InterviewEvent, 'id' | 'created_at'> = {
      job_application_id: formData.job_application_id || null,
      company: selectedJob?.company || '',
      position: selectedJob?.position || '',
      event_type: formData.event_type,
      scheduled_date: formData.scheduled_date,
      scheduled_time: formData.scheduled_time || undefined,
      duration_minutes: formData.duration_minutes || undefined,
      location: formData.location || undefined,
      meeting_link: formData.meeting_link || undefined,
      interviewer_names: formData.interviewer_names
        ? formData.interviewer_names.split(',').map((n) => n.trim())
        : undefined,
      notes: formData.notes || undefined,
      is_completed: false,
      follow_up_date: formData.follow_up_date || undefined,
      follow_up_done: false,
    }

    onAdd(event)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-[var(--surface-strong)] rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-[var(--line)]">
          <h2 className="text-xl font-bold font-display tracking-[-0.02em] text-[var(--ink)]">Add Interview Event</h2>
          <button
            onClick={onClose}
            className="p-1 text-[var(--muted-soft)] hover:text-[var(--muted)]"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label htmlFor="job_application_id" className="glass-label mb-1">
              Job Application
            </label>
            <select
              id="job_application_id"
              required
              value={formData.job_application_id}
              onChange={(e) =>
                setFormData({ ...formData, job_application_id: parseInt(e.target.value) })
              }
              className="w-full glass-select"
            >
              <option value={0}>Select a job...</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.company} - {job.position}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="event_type" className="glass-label mb-1">
              Event Type
            </label>
            <select
              id="event_type"
              value={formData.event_type}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  event_type: e.target.value as InterviewEventType,
                })
              }
              className="w-full glass-select"
            >
              {EVENT_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="scheduled_date" className="glass-label mb-1">
                Date
              </label>
              <input
                id="scheduled_date"
                type="date"
                required
                value={formData.scheduled_date}
                onChange={(e) =>
                  setFormData({ ...formData, scheduled_date: e.target.value })
                }
                className="w-full glass-input"
              />
            </div>
            <div>
              <label htmlFor="scheduled_time" className="glass-label mb-1">
                Time
              </label>
              <input
                id="scheduled_time"
                type="time"
                value={formData.scheduled_time}
                onChange={(e) =>
                  setFormData({ ...formData, scheduled_time: e.target.value })
                }
                className="w-full glass-input"
              />
            </div>
          </div>

          <div>
            <label htmlFor="duration_minutes" className="glass-label mb-1">
              Duration (minutes)
            </label>
            <input
              id="duration_minutes"
              type="number"
              min={15}
              step={15}
              value={formData.duration_minutes}
              onChange={(e) => {
                const nextDuration = Number.parseInt(e.target.value, 10)
                setFormData({
                  ...formData,
                  duration_minutes: Number.isNaN(nextDuration)
                    ? 0
                    : nextDuration,
                })
              }}
              className="w-full glass-input"
            />
          </div>

          <div>
            <label htmlFor="event_location" className="glass-label mb-1">
              Location
            </label>
            <input
              id="event_location"
              type="text"
              placeholder="Office address or 'Remote'"
              value={formData.location}
              onChange={(e) =>
                setFormData({ ...formData, location: e.target.value })
              }
              className="w-full glass-input"
            />
          </div>

          <div>
            <label htmlFor="meeting_link" className="glass-label mb-1">
              Meeting Link
            </label>
            <input
              id="meeting_link"
              type="url"
              placeholder="https://zoom.us/..."
              value={formData.meeting_link}
              onChange={(e) =>
                setFormData({ ...formData, meeting_link: e.target.value })
              }
              className="w-full glass-input"
            />
          </div>

          <div>
            <label htmlFor="interviewer_names" className="glass-label mb-1">
              Interviewer Names
            </label>
            <input
              id="interviewer_names"
              type="text"
              placeholder="John Doe, Jane Smith (comma separated)"
              value={formData.interviewer_names}
              onChange={(e) =>
                setFormData({ ...formData, interviewer_names: e.target.value })
              }
              className="w-full glass-input"
            />
          </div>

          <div>
            <label htmlFor="follow_up_date" className="glass-label mb-1">
              Follow-up Date
            </label>
            <input
              id="follow_up_date"
              type="date"
              value={formData.follow_up_date}
              onChange={(e) =>
                setFormData({ ...formData, follow_up_date: e.target.value })
              }
              className="w-full glass-input"
            />
          </div>

          <div>
            <label htmlFor="event_notes" className="glass-label mb-1">
              Notes
            </label>
            <textarea
              id="event_notes"
              rows={3}
              placeholder="Preparation notes, questions to ask, etc."
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              className="w-full glass-textarea"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-[var(--line)]">
            <button
              type="button"
              onClick={onClose}
              className="glass-button-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!formData.job_application_id || !formData.scheduled_date}
              className="glass-button-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add Event
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
