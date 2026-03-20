'use client'

import {
  Plus,
  Calendar,
  Clock,
  MapPin,
  Link as LinkIcon,
  Users,
  CheckCircle,
  Bell,
  Trash2,
} from 'lucide-react'
import { useState, useMemo, useCallback, memo } from 'react'

import { EVENT_TYPES, getEventTypeColor, getUrgencyColor, calculateUrgency } from '@/lib/jobs'
import { cn, formatDate, truncate } from '@/lib/utils'

import { AddEventModal } from './AddEventModal'

import type { JobApplication, InterviewEvent, InterviewEventType } from '@/types'

interface TimelineTabProps {
  jobs: JobApplication[]
  events: InterviewEvent[]
  onAddEvent: (event: Omit<InterviewEvent, 'id' | 'created_at'>) => void
  onUpdateEvent: (id: number, updates: Partial<InterviewEvent>) => void
  onDeleteEvent: (id: number) => void
}

export const TimelineTab = memo(function TimelineTab({
  jobs,
  events,
  onAddEvent,
  onUpdateEvent,
  onDeleteEvent,
}: TimelineTabProps) {
  const [showAddForm, setShowAddForm] = useState(false)
  const [filterType, setFilterType] = useState<InterviewEventType | ''>('')

  // Group events by date
  const groupedEvents = useMemo(() => {
    const filtered = filterType
      ? events.filter((e) => e.event_type === filterType)
      : events

    const groups: Record<string, InterviewEvent[]> = {}

    filtered.forEach((event) => {
      const dateKey = new Date(event.scheduled_date).toISOString().slice(0, 10)
      if (!groups[dateKey]) {
        groups[dateKey] = []
      }
      groups[dateKey].push(event)
    })

    // Sort events within each group by time
    Object.keys(groups).forEach((key) => {
      const group = groups[key]
      if (group) {
        group.sort((a, b) => {
          const timeA = a.scheduled_time || '00:00'
          const timeB = b.scheduled_time || '00:00'
          return timeA.localeCompare(timeB)
        })
      }
    })

    // Sort dates
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  }, [events, filterType])

  // Get pending follow-ups
  const pendingFollowUps = useMemo(() => {
    return events
      .filter((e) => e.follow_up_date && !e.follow_up_done)
      .sort((a, b) => a.follow_up_date!.localeCompare(b.follow_up_date!))
  }, [events])

  // Memoized callbacks for modal handlers
  const handleCloseAddForm = useCallback(() => {
    setShowAddForm(false)
  }, [])

  const handleAddEvent = useCallback(
    (event: Omit<InterviewEvent, 'id' | 'created_at'>) => {
      onAddEvent(event)
      setShowAddForm(false)
    },
    [onAddEvent]
  )

  const handleShowAddForm = useCallback(() => {
    setShowAddForm(true)
  }, [])

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex items-center gap-4">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as InterviewEventType | '')}
            className="glass-select"
            aria-label="Filter by event type"
          >
            <option value="">All Event Types</option>
            {EVENT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleShowAddForm}
          className="glass-button-primary inline-flex items-center"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Event
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="lg:col-span-2 space-y-6">
          {groupedEvents.length === 0 ? (
            <div className="bg-[var(--surface-strong)] rounded-lg shadow p-8 text-center text-[var(--muted)]">
              <Calendar className="w-12 h-12 mx-auto mb-4 text-[var(--muted-soft)]" />
              <p>No events scheduled</p>
              <button
                onClick={handleShowAddForm}
                className="mt-4 text-primary-600 hover:text-primary-700 font-medium"
              >
                Add your first event
              </button>
            </div>
          ) : (
            groupedEvents.map(([date, dateEvents]) => {
              const dateObj = new Date(date)
              const isToday =
                dateObj.toDateString() === new Date().toDateString()
              const isPast = dateObj < new Date() && !isToday

              return (
                <div key={date}>
                  <div
                    className={cn(
                      'sticky top-0 z-10 py-2 px-4 rounded-lg mb-3',
                      isToday
                        ? 'bg-primary-100 text-primary-800'
                        : isPast
                        ? 'bg-[var(--surface)] text-[var(--muted)]'
                        : 'bg-blue-50 text-blue-800'
                    )}
                  >
                    <span className="font-semibold">
                      {isToday ? 'Today - ' : ''}
                      {formatDate(date, 'long')}
                    </span>
                  </div>

                  <div className="space-y-3 ml-4 border-l-2 border-[var(--line)] pl-4">
                    {dateEvents.map((event) => (
                      <div
                        key={event.id}
                        className={cn(
                          'bg-[var(--surface-strong)] rounded-lg shadow p-4 relative',
                          event.is_completed && 'opacity-60'
                        )}
                      >
                        <div className="absolute -left-6 top-4 w-3 h-3 rounded-full bg-[var(--surface-strong)] border-2 border-primary-500" />

                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span
                                className={cn(
                                  'text-xs font-medium px-2 py-1 rounded-full',
                                  getEventTypeColor(event.event_type)
                                )}
                              >
                                {EVENT_TYPES.find((t) => t.value === event.event_type)?.label}
                              </span>
                              {event.is_completed && (
                                <span className="text-xs text-green-600 flex items-center gap-1">
                                  <CheckCircle className="w-3 h-3" />
                                  Completed
                                </span>
                              )}
                            </div>

                            <h4 className="font-medium text-[var(--ink)] mt-2">
                              {event.position}
                            </h4>
                            <p className="text-sm text-[var(--muted)]">{event.company}</p>

                            <div className="mt-3 space-y-1 text-sm text-[var(--muted)]">
                              {event.scheduled_time && (
                                <div className="flex items-center gap-2">
                                  <Clock className="w-4 h-4 text-[var(--muted-soft)]" />
                                  {event.scheduled_time}
                                  {event.duration_minutes && ` (${event.duration_minutes} min)`}
                                </div>
                              )}
                              {event.location && (
                                <div className="flex items-center gap-2">
                                  <MapPin className="w-4 h-4 text-[var(--muted-soft)]" />
                                  {event.location}
                                </div>
                              )}
                              {event.meeting_link && (
                                <div className="flex items-center gap-2">
                                  <LinkIcon className="w-4 h-4 text-[var(--muted-soft)]" />
                                  <a
                                    href={event.meeting_link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary-600 hover:underline"
                                  >
                                    Join Meeting
                                  </a>
                                </div>
                              )}
                              {event.interviewer_names && event.interviewer_names.length > 0 && (
                                <div className="flex items-center gap-2">
                                  <Users className="w-4 h-4 text-[var(--muted-soft)]" />
                                  {event.interviewer_names.join(', ')}
                                </div>
                              )}
                            </div>

                            {event.notes && (
                              <p className="mt-2 text-sm text-[var(--muted)] italic">
                                {truncate(event.notes, 150)}
                              </p>
                            )}
                          </div>

                          <div className="flex items-center gap-2 ml-4">
                            {!event.is_completed && (
                              <button
                                onClick={() =>
                                  onUpdateEvent(event.id, { is_completed: true })
                                }
                                className="p-2 text-[var(--muted-soft)] hover:text-green-600 hover:bg-green-50 rounded"
                                aria-label="Mark as completed"
                                title="Mark as completed"
                              >
                                <CheckCircle className="w-5 h-5" />
                              </button>
                            )}
                            <button
                              onClick={() => onDeleteEvent(event.id)}
                              className="p-2 text-[var(--muted-soft)] hover:text-red-600 hover:bg-red-50 rounded"
                              aria-label="Delete event"
                            >
                              <Trash2 className="w-5 h-5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Follow-up Reminders Sidebar */}
        <div className="space-y-4">
          <div className="bg-[var(--surface-strong)] rounded-lg shadow p-4">
            <h3 className="font-semibold text-[var(--ink)] mb-4 flex items-center gap-2">
              <Bell className="w-5 h-5 text-amber-500" />
              Follow-up Reminders
            </h3>

            {pendingFollowUps.length === 0 ? (
              <p className="text-sm text-[var(--muted)] text-center py-4">
                No pending follow-ups
              </p>
            ) : (
              <div className="space-y-3">
                {pendingFollowUps.map((event) => {
                  const urgency = calculateUrgency(event.follow_up_date!)

                  return (
                    <div
                      key={event.id}
                      className={cn(
                        'p-3 rounded-lg border',
                        getUrgencyColor(urgency)
                      )}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-sm">{event.company}</p>
                          <p className="text-xs opacity-75">{event.position}</p>
                          <p className="text-xs mt-1 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(event.follow_up_date)}
                          </p>
                        </div>
                        <button
                          onClick={() =>
                            onUpdateEvent(event.id, { follow_up_done: true })
                          }
                          className="p-1 hover:bg-white/50 rounded"
                          aria-label="Mark follow-up done"
                          title="Mark done"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="bg-[var(--surface-strong)] rounded-lg shadow p-4">
            <h3 className="font-semibold text-[var(--ink)] mb-4">Quick Stats</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Total Events</span>
                <span className="font-medium">{events.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Upcoming</span>
                <span className="font-medium">
                  {events.filter((e) => !e.is_completed && new Date(e.scheduled_date) >= new Date()).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Completed</span>
                <span className="font-medium">
                  {events.filter((e) => e.is_completed).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Pending Follow-ups</span>
                <span className="font-medium">{pendingFollowUps.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add Event Modal */}
      {showAddForm && (
        <AddEventModal
          jobs={jobs}
          onClose={handleCloseAddForm}
          onAdd={handleAddEvent}
        />
      )}
    </div>
  )
})
