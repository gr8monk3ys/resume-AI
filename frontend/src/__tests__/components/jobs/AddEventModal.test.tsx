import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { createMockJobApplication } from '@/__tests__/test-utils'
import { AddEventModal } from '@/components/jobs/AddEventModal'

import type { JobApplication } from '@/types'

describe('AddEventModal', () => {
  const mockOnClose = vi.fn()
  const mockOnAdd = vi.fn()

  const mockJobs: JobApplication[] = [
    createMockJobApplication({
      id: 1,
      company: 'TechCorp',
      position: 'Software Engineer',
      status: 'Interview',
    }),
    createMockJobApplication({
      id: 2,
      company: 'DataCo',
      position: 'Data Scientist',
      status: 'Phone Screen',
    }),
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render modal title', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByText('Add Interview Event')).toBeInTheDocument()
    })

    it('should render all form fields', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByLabelText(/job application/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/event type/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^date$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/time/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/duration/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/location/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/meeting link/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/interviewer names/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/follow-up date/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/notes/i)).toBeInTheDocument()
    })

    it('should render close button', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByLabelText(/close modal/i)).toBeInTheDocument()
    })

    it('should render submit and cancel buttons', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByRole('button', { name: /add event/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })
  })

  describe('Job Selection', () => {
    it('should render job options in select', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByText('TechCorp - Software Engineer')).toBeInTheDocument()
      expect(screen.getByText('DataCo - Data Scientist')).toBeInTheDocument()
    })

    it('should default to "Select a job..." option', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const jobSelect = screen.getByLabelText(/job application/i) as HTMLSelectElement
      expect(jobSelect.value).toBe('0')
      expect(screen.getByText('Select a job...')).toBeInTheDocument()
    })

    it('should handle empty jobs list', () => {
      render(<AddEventModal jobs={[]} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByText('Select a job...')).toBeInTheDocument()
    })
  })

  describe('Event Type Selection', () => {
    it('should render all event type options', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByText('Phone Screen')).toBeInTheDocument()
      expect(screen.getByText('Technical Interview')).toBeInTheDocument()
      expect(screen.getByText('Behavioral Interview')).toBeInTheDocument()
      expect(screen.getByText('Onsite Interview')).toBeInTheDocument()
      expect(screen.getByText('Panel Interview')).toBeInTheDocument()
      expect(screen.getByText('HR Interview')).toBeInTheDocument()
      expect(screen.getByText('Final Round')).toBeInTheDocument()
      expect(screen.getByText('Follow Up')).toBeInTheDocument()
      expect(screen.getByText('Other')).toBeInTheDocument()
    })

    it('should default to phone_screen', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const eventTypeSelect = screen.getByLabelText(/event type/i) as HTMLSelectElement
      expect(eventTypeSelect.value).toBe('phone_screen')
    })
  })

  describe('Form Defaults', () => {
    it('should default duration to 60 minutes', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const durationInput = screen.getByLabelText(/duration/i) as HTMLInputElement
      expect(durationInput.value).toBe('60')
    })

    it('should have empty string defaults for optional text fields', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByLabelText(/location/i)).toHaveValue('')
      expect(screen.getByLabelText(/meeting link/i)).toHaveValue('')
      expect(screen.getByLabelText(/interviewer names/i)).toHaveValue('')
      expect(screen.getByLabelText(/notes/i)).toHaveValue('')
    })
  })

  describe('Form Validation', () => {
    it('should require job selection', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      const submitButton = screen.getByRole('button', { name: /add event/i })
      expect(submitButton).toBeDisabled()

      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')

      // Button should still be disabled without job selection
      expect(submitButton).toBeDisabled()
    })

    it('should require date field', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      expect(submitButton).toBeDisabled()
    })

    it('should enable submit when required fields are filled', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      expect(submitButton).not.toBeDisabled()
    })
  })

  describe('Form Submission', () => {
    it('should call onAdd with correct data when submitted', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')
      await user.type(screen.getByLabelText(/time/i), '14:00')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnAdd).toHaveBeenCalledWith(
          expect.objectContaining({
            job_id: 1,
            company: 'TechCorp',
            position: 'Software Engineer',
            event_type: 'phone_screen',
            scheduled_date: '2024-02-15',
            scheduled_time: '14:00',
            duration_minutes: 60,
            is_completed: false,
            follow_up_done: false,
          })
        )
      })
    })

    it('should include optional fields when provided', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')
      await user.type(screen.getByLabelText(/location/i), 'Office Building A')
      await user.type(screen.getByLabelText(/meeting link/i), 'https://zoom.us/meeting')
      await user.type(screen.getByLabelText(/interviewer names/i), 'John Doe, Jane Smith')
      await user.type(screen.getByLabelText(/notes/i), 'Prepare questions')
      await user.type(screen.getByLabelText(/follow-up date/i), '2024-02-20')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnAdd).toHaveBeenCalledWith(
          expect.objectContaining({
            location: 'Office Building A',
            meeting_link: 'https://zoom.us/meeting',
            interviewer_names: ['John Doe', 'Jane Smith'],
            notes: 'Prepare questions',
            follow_up_date: '2024-02-20',
          })
        )
      })
    })

    it('should parse comma-separated interviewer names', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')
      await user.type(screen.getByLabelText(/interviewer names/i), '  John Doe  ,  Jane Smith  ')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnAdd).toHaveBeenCalledWith(
          expect.objectContaining({
            interviewer_names: ['John Doe', 'Jane Smith'],
          })
        )
      })
    })

    it('should omit optional fields when not provided', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnAdd).toHaveBeenCalledWith(
          expect.objectContaining({
            scheduled_time: undefined,
            location: undefined,
            meeting_link: undefined,
            interviewer_names: undefined,
            notes: undefined,
            follow_up_date: undefined,
          })
        )
      })
    })

    it('should update duration when changed', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')

      const durationInput = screen.getByLabelText(/duration/i)
      await user.clear(durationInput)
      await user.type(durationInput, '90')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnAdd).toHaveBeenCalledWith(
          expect.objectContaining({
            duration_minutes: 90,
          })
        )
      })
    })
  })

  describe('Event Type Changes', () => {
    it('should update event type when changed', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')
      await user.selectOptions(screen.getByLabelText(/event type/i), 'technical')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnAdd).toHaveBeenCalledWith(
          expect.objectContaining({
            event_type: 'technical',
          })
        )
      })
    })
  })

  describe('Close Actions', () => {
    it('should call onClose when close button is clicked', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      const closeButton = screen.getByLabelText(/close modal/i)
      await user.click(closeButton)

      expect(mockOnClose).toHaveBeenCalled()
    })

    it('should call onClose when cancel button is clicked', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have accessible modal title', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByText('Add Interview Event')).toBeInTheDocument()
    })

    it('should have accessible form labels', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(screen.getByLabelText(/job application/i)).toHaveAccessibleName()
      expect(screen.getByLabelText(/event type/i)).toHaveAccessibleName()
      expect(screen.getByLabelText(/^date$/i)).toHaveAccessibleName()
    })

    it('should have accessible close button', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      const closeButton = screen.getByLabelText(/close modal/i)
      expect(closeButton).toHaveAccessibleName()
    })

    it('should mark required fields', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      const jobSelect = screen.getByLabelText(/job application/i)
      const dateInput = screen.getByLabelText(/^date$/i)

      expect(jobSelect).toBeRequired()
      expect(dateInput).toBeRequired()
    })
  })

  describe('Duration Input', () => {
    it('should have minimum value of 15 minutes', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const durationInput = screen.getByLabelText(/duration/i) as HTMLInputElement
      expect(durationInput.min).toBe('15')
    })

    it('should have step of 15 minutes', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const durationInput = screen.getByLabelText(/duration/i) as HTMLInputElement
      expect(durationInput.step).toBe('15')
    })
  })

  describe('URL Validation', () => {
    it('should validate meeting link as URL', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const meetingLinkInput = screen.getByLabelText(/meeting link/i) as HTMLInputElement
      expect(meetingLinkInput.type).toBe('url')
    })

    it('should have placeholder for meeting link', () => {
      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      const meetingLinkInput = screen.getByLabelText(/meeting link/i)
      expect(meetingLinkInput).toHaveAttribute('placeholder', 'https://zoom.us/...')
    })
  })

  describe('Edge Cases', () => {
    it('should handle single job in list', () => {
      render(
        <AddEventModal jobs={[mockJobs[0]!]} onClose={mockOnClose} onAdd={mockOnAdd} />
      )

      expect(screen.getByText('TechCorp - Software Engineer')).toBeInTheDocument()
      expect(screen.queryByText('DataCo - Data Scientist')).not.toBeInTheDocument()
    })

    it('should handle job with long company/position names', () => {
      const longNameJob = createMockJobApplication({
        id: 1,
        company: 'Very Long Company Name That Should Display Properly',
        position: 'Senior Principal Staff Software Engineering Architect',
      })

      render(<AddEventModal jobs={[longNameJob]} onClose={mockOnClose} onAdd={mockOnAdd} />)

      expect(
        screen.getByText(
          'Very Long Company Name That Should Display Properly - Senior Principal Staff Software Engineering Architect'
        )
      ).toBeInTheDocument()
    })

    it('should handle empty interviewer names field', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnAdd).toHaveBeenCalledWith(
          expect.objectContaining({
            interviewer_names: undefined,
          })
        )
      })
    })

    it('should handle special characters in text inputs', async () => {
      const user = userEvent.setup()

      render(<AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />)

      await user.selectOptions(screen.getByLabelText(/job application/i), '1')
      await user.type(screen.getByLabelText(/^date$/i), '2024-02-15')
      await user.type(screen.getByLabelText(/location/i), 'Building A & B')
      await user.type(screen.getByLabelText(/notes/i), 'Ask about <tech stack>')

      const submitButton = screen.getByRole('button', { name: /add event/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnAdd).toHaveBeenCalledWith(
          expect.objectContaining({
            location: 'Building A & B',
            notes: 'Ask about <tech stack>',
          })
        )
      })
    })
  })

  describe('Modal Layout', () => {
    it('should render as fixed overlay', () => {
      const { container } = render(
        <AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />
      )

      const overlay = container.querySelector('.fixed.inset-0')
      expect(overlay).toBeInTheDocument()
    })

    it('should have scrollable content', () => {
      const { container } = render(
        <AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />
      )

      const scrollContainer = container.querySelector('.overflow-y-auto')
      expect(scrollContainer).toBeInTheDocument()
    })

    it('should have maximum width constraint', () => {
      const { container } = render(
        <AddEventModal jobs={mockJobs} onClose={mockOnClose} onAdd={mockOnAdd} />
      )

      const modal = container.querySelector('.max-w-lg')
      expect(modal).toBeInTheDocument()
    })
  })
})
