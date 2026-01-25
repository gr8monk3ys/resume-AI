import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { createMockJobApplication } from '@/__tests__/test-utils'
import { JobFormModal } from '@/components/jobs/JobFormModal'

import type { JobApplication } from '@/types'

describe('JobFormModal', () => {
  const mockOnClose = vi.fn()
  const mockOnSave = vi.fn()
  const mockOnDelete = vi.fn()

  const defaultJob: JobApplication = createMockJobApplication({
    id: 1,
    company: 'TechCorp',
    position: 'Software Engineer',
    status: 'Applied',
    location: 'Remote',
    job_url: 'https://example.com/job',
    application_date: '2024-01-15',
    deadline: '2024-02-01',
    job_description: 'Great job description',
    notes: 'Some notes',
  })

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering - Add Mode', () => {
    it('should render add job modal title when no job provided', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByText('Add Job Application')).toBeInTheDocument()
    })

    it('should render all form fields', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByLabelText(/company/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/position/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/status/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/location/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/application date/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/deadline/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/job url/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/job description/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/notes/i)).toBeInTheDocument()
    })

    it('should render submit button with correct text', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByRole('button', { name: /add job/i })).toBeInTheDocument()
    })

    it('should not render delete button in add mode', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
    })

    it('should use initial status when provided', () => {
      render(
        <JobFormModal onClose={mockOnClose} onSave={mockOnSave} initialStatus="Interview" />
      )

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const statusSelect = screen.getByLabelText(/status/i) as HTMLSelectElement
      expect(statusSelect.value).toBe('Interview')
    })

    it('should default to Bookmarked status when no initial status provided', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const statusSelect = screen.getByLabelText(/status/i) as HTMLSelectElement
      expect(statusSelect.value).toBe('Bookmarked')
    })
  })

  describe('Rendering - Edit Mode', () => {
    it('should render edit job modal title when job provided', () => {
      render(<JobFormModal job={defaultJob} onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByText('Edit Job Application')).toBeInTheDocument()
    })

    it('should pre-fill form with job data', () => {
      render(<JobFormModal job={defaultJob} onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByDisplayValue('TechCorp')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Software Engineer')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Remote')).toBeInTheDocument()
      expect(screen.getByDisplayValue('https://example.com/job')).toBeInTheDocument()
      expect(screen.getByDisplayValue('2024-01-15')).toBeInTheDocument()
      expect(screen.getByDisplayValue('2024-02-01')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Great job description')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Some notes')).toBeInTheDocument()
    })

    it('should render submit button with correct text', () => {
      render(<JobFormModal job={defaultJob} onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument()
    })

    it('should render delete button in edit mode', () => {
      render(
        <JobFormModal
          job={defaultJob}
          onClose={mockOnClose}
          onSave={mockOnSave}
          onDelete={mockOnDelete}
        />
      )

      expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
    })

    it('should not render delete button when onDelete not provided', () => {
      render(<JobFormModal job={defaultJob} onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('should require company field', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const submitButton = screen.getByRole('button', { name: /add job/i })
      await user.click(submitButton)

      // HTML5 validation should prevent submission
      const companyInput = screen.getByLabelText(/company/i)
      expect((companyInput as HTMLInputElement).validity.valid).toBe(false)
      expect(mockOnSave).not.toHaveBeenCalled()
    })

    it('should require position field', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      await user.type(screen.getByLabelText(/company/i), 'TechCorp')

      const submitButton = screen.getByRole('button', { name: /add job/i })
      await user.click(submitButton)

      const positionInput = screen.getByLabelText(/position/i)
      expect((positionInput as HTMLInputElement).validity.valid).toBe(false)
      expect(mockOnSave).not.toHaveBeenCalled()
    })

    it('should accept valid form data', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      await user.type(screen.getByLabelText(/company/i), 'TechCorp')
      await user.type(screen.getByLabelText(/position/i), 'Software Engineer')

      const submitButton = screen.getByRole('button', { name: /add job/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalled()
      })
    })
  })

  describe('Form Submission', () => {
    it('should call onSave with form data when submitted', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      await user.type(screen.getByLabelText(/company/i), 'TechCorp')
      await user.type(screen.getByLabelText(/position/i), 'Software Engineer')
      await user.type(screen.getByLabelText(/location/i), 'Remote')
      await user.type(screen.getByLabelText(/job url/i), 'https://example.com')

      const submitButton = screen.getByRole('button', { name: /add job/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            company: 'TechCorp',
            position: 'Software Engineer',
            location: 'Remote',
            job_url: 'https://example.com',
          })
        )
      })
    })

    it('should include all optional fields when provided', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      await user.type(screen.getByLabelText(/company/i), 'TechCorp')
      await user.type(screen.getByLabelText(/position/i), 'Software Engineer')
      await user.type(screen.getByLabelText(/application date/i), '2024-01-15')
      await user.type(screen.getByLabelText(/deadline/i), '2024-02-01')
      await user.type(screen.getByLabelText(/job description/i), 'Great job')
      await user.type(screen.getByLabelText(/notes/i), 'Some notes')

      const submitButton = screen.getByRole('button', { name: /add job/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            application_date: '2024-01-15',
            deadline: '2024-02-01',
            job_description: 'Great job',
            notes: 'Some notes',
          })
        )
      })
    })

    // Note: Async submission state tests are skipped because the component
    // handles submission synchronously in tests due to how React batching works
  })

  describe('Status Selection', () => {
    it('should render all job statuses in select', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const statusSelect = screen.getByLabelText(/status/i)
      const options = Array.from((statusSelect as HTMLSelectElement).options).map((opt) => opt.value)

      expect(options).toEqual([
        'Bookmarked',
        'Applied',
        'Phone Screen',
        'Interview',
        'Offer',
        'Rejected',
      ])
    })

    it('should update status when changed', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      await user.selectOptions(screen.getByLabelText(/status/i), 'Interview')
      await user.type(screen.getByLabelText(/company/i), 'TechCorp')
      await user.type(screen.getByLabelText(/position/i), 'Software Engineer')

      const submitButton = screen.getByRole('button', { name: /add job/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 'Interview',
          })
        )
      })
    })
  })

  describe('Close Actions', () => {
    it('should call onClose when close button is clicked', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const closeButton = screen.getByLabelText(/close modal/i)
      await user.click(closeButton)

      expect(mockOnClose).toHaveBeenCalled()
    })

    it('should call onClose when cancel button is clicked', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  describe('Delete Actions', () => {
    it('should show confirmation dialog when delete is clicked', async () => {
      const user = userEvent.setup()
      window.confirm = vi.fn(() => false)

      render(
        <JobFormModal
          job={defaultJob}
          onClose={mockOnClose}
          onSave={mockOnSave}
          onDelete={mockOnDelete}
        />
      )

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)

      expect(window.confirm).toHaveBeenCalledWith(
        'Are you sure you want to delete this job application?'
      )
    })

    it('should call onDelete when confirmed', async () => {
      const user = userEvent.setup()
      window.confirm = vi.fn(() => true)

      render(
        <JobFormModal
          job={defaultJob}
          onClose={mockOnClose}
          onSave={mockOnSave}
          onDelete={mockOnDelete}
        />
      )

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)

      expect(mockOnDelete).toHaveBeenCalledWith(1)
    })

    it('should not call onDelete when cancelled', async () => {
      const user = userEvent.setup()
      window.confirm = vi.fn(() => false)

      render(
        <JobFormModal
          job={defaultJob}
          onClose={mockOnClose}
          onSave={mockOnSave}
          onDelete={mockOnDelete}
        />
      )

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)

      expect(mockOnDelete).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have accessible modal title', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByText('Add Job Application')).toBeInTheDocument()
    })

    it('should have accessible form labels', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByLabelText(/company/i)).toHaveAccessibleName()
      expect(screen.getByLabelText(/position/i)).toHaveAccessibleName()
    })

    it('should have accessible close button', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const closeButton = screen.getByLabelText(/close modal/i)
      expect(closeButton).toHaveAccessibleName()
    })

    it('should mark required fields', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const companyInput = screen.getByLabelText(/company/i)
      const positionInput = screen.getByLabelText(/position/i)

      expect(companyInput).toBeRequired()
      expect(positionInput).toBeRequired()
    })

    it('should show required indicators in labels', () => {
      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const requiredMarkers = screen.getAllByText('*')
      expect(requiredMarkers.length).toBeGreaterThanOrEqual(2) // Company and Position
    })
  })

  describe('Edge Cases', () => {
    it('should handle null job gracefully', () => {
      render(<JobFormModal job={null} onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByText('Add Job Application')).toBeInTheDocument()
    })

    it('should handle job with null optional fields', () => {
      const incompleteJob = createMockJobApplication({
        location: null,
        job_url: null,
        application_date: null,
        deadline: null,
        job_description: null,
        notes: null,
      })

      render(<JobFormModal job={incompleteJob} onClose={mockOnClose} onSave={mockOnSave} />)

      expect(screen.getByLabelText(/company/i)).toHaveValue(incompleteJob.company)
      expect(screen.getByLabelText(/location/i)).toHaveValue('')
    })

    it('should handle very long text inputs', async () => {
      const user = userEvent.setup()
      const longText = 'A'.repeat(1000)

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      await user.type(screen.getByLabelText(/company/i), 'TechCorp')
      await user.type(screen.getByLabelText(/position/i), 'Software Engineer')
      await user.type(screen.getByLabelText(/notes/i), longText)

      const submitButton = screen.getByRole('button', { name: /add job/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            notes: longText,
          })
        )
      })
    })

    it('should handle special characters in input', async () => {
      const user = userEvent.setup()

      render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      await user.type(screen.getByLabelText(/company/i), 'Tech & Co.')
      await user.type(screen.getByLabelText(/position/i), 'Software Engineer <Senior>')

      const submitButton = screen.getByRole('button', { name: /add job/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            company: 'Tech & Co.',
            position: 'Software Engineer <Senior>',
          })
        )
      })
    })
  })

  describe('Modal Layout', () => {
    it('should render as fixed overlay', () => {
      const { container } = render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const overlay = container.querySelector('.fixed.inset-0')
      expect(overlay).toBeInTheDocument()
    })

    it('should have scrollable content', () => {
      const { container } = render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const scrollContainer = container.querySelector('.overflow-y-auto')
      expect(scrollContainer).toBeInTheDocument()
    })

    it('should have maximum width constraint', () => {
      const { container } = render(<JobFormModal onClose={mockOnClose} onSave={mockOnSave} />)

      const modal = container.querySelector('.max-w-2xl')
      expect(modal).toBeInTheDocument()
    })
  })
})
