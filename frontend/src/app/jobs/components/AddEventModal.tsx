'use client'

/**
 * Modal component for adding new interview events to the timeline.
 * Allows selection of job, event type, scheduling details, and follow-up dates.
 * @module jobs/components/AddEventModal
 */

import { useState } from 'react'
import type { JobApplication, InterviewEvent, InterviewEventType } from '@/types'
import { X } from 'lucide-react'
import { EVENT_TYPES } from './types'

// ============================================================================
// Props Interface
// ============================================================================

export interface AddEventModalProps {
  jobs: JobApplication[]
  onClose: () => void
  onAdd: (event: Omit<InterviewEvent, 'id' | 'created_at'>) => void
}

// ============================================================================
// AddEventModal Component
// ============================================================================

/**
 * Modal form for creating new interview events.
 * Links events to existing job applications and captures scheduling details.
 */
export function AddEventModal({ jobs, onClose, onAdd }: AddEventModalProps) {
  const [formData, setFormData] = useState({
    job_id: 0,
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

  const selectedJob = jobs.find((j) => j.id === formData.job_id)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const event: Omit<InterviewEvent, 'id' | 'created_at'> = {
      job_id: formData.job_id,
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
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Add Interview Event</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Job Application
            </label>
            <select
              required
              value={formData.job_id}
              onChange={(e) =>
                setFormData({ ...formData, job_id: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
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
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Event Type
            </label>
            <select
              value={formData.event_type}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  event_type: e.target.value as InterviewEventType,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date
              </label>
              <input
                type="date"
                required
                value={formData.scheduled_date}
                onChange={(e) =>
                  setFormData({ ...formData, scheduled_date: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Time
              </label>
              <input
                type="time"
                value={formData.scheduled_time}
                onChange={(e) =>
                  setFormData({ ...formData, scheduled_time: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Duration (minutes)
            </label>
            <input
              type="number"
              min={15}
              step={15}
              value={formData.duration_minutes}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  duration_minutes: parseInt(e.target.value),
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Location
            </label>
            <input
              type="text"
              placeholder="Office address or 'Remote'"
              value={formData.location}
              onChange={(e) =>
                setFormData({ ...formData, location: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Meeting Link
            </label>
            <input
              type="url"
              placeholder="https://zoom.us/..."
              value={formData.meeting_link}
              onChange={(e) =>
                setFormData({ ...formData, meeting_link: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Interviewer Names
            </label>
            <input
              type="text"
              placeholder="John Doe, Jane Smith (comma separated)"
              value={formData.interviewer_names}
              onChange={(e) =>
                setFormData({ ...formData, interviewer_names: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Follow-up Date
            </label>
            <input
              type="date"
              value={formData.follow_up_date}
              onChange={(e) =>
                setFormData({ ...formData, follow_up_date: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              rows={3}
              placeholder="Preparation notes, questions to ask, etc."
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!formData.job_id || !formData.scheduled_date}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add Event
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
