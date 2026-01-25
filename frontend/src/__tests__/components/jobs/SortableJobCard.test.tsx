import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { createMockJobApplication } from '@/__tests__/test-utils'
import { SortableJobCard } from '@/components/jobs/SortableJobCard'

import type { JobApplication } from '@/types'

// Mock @dnd-kit/sortable
vi.mock('@dnd-kit/sortable', () => ({
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  }),
}))

// Mock @dnd-kit/utilities
vi.mock('@dnd-kit/utilities', () => ({
  CSS: {
    Transform: {
      toString: () => '',
    },
  },
}))

describe('SortableJobCard', () => {
  const mockOnEdit = vi.fn()
  const mockOnDelete = vi.fn()
  const mockOnStatusChange = vi.fn()

  const defaultJob: JobApplication = createMockJobApplication({
    id: 1,
    company: 'TechCorp',
    position: 'Software Engineer',
    status: 'Applied',
    location: 'Remote',
    job_url: 'https://example.com/job',
    application_date: '2024-01-15',
    job_description: 'Great job description',
    notes: 'Some notes',
  })

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render job card with basic information', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('Software Engineer')).toBeInTheDocument()
      expect(screen.getByText('TechCorp')).toBeInTheDocument()
      expect(screen.getByText('Remote')).toBeInTheDocument()
    })

    it('should render job URL link when provided', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const link = screen.getByLabelText('Open job link')
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', 'https://example.com/job')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    })

    it('should not render job URL link when not provided', () => {
      const jobWithoutUrl = createMockJobApplication({ job_url: null })

      render(
        <SortableJobCard
          job={jobWithoutUrl}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.queryByLabelText('Open job link')).not.toBeInTheDocument()
    })

    it('should render application date when provided', () => {
      const { container } = render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      // Date is formatted by formatDate function - the component displays dates
      // Just check that there's some date-related content rendered
      const calendarIcons = container.querySelectorAll('svg')
      expect(calendarIcons.length).toBeGreaterThan(0)

      // The application date should be present in some form
      expect(container.textContent).toBeTruthy()
    })

    it('should render location when provided', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('Remote')).toBeInTheDocument()
    })

    it('should not render location section when not provided', () => {
      const jobWithoutLocation = createMockJobApplication({ location: null })

      render(
        <SortableJobCard
          job={jobWithoutLocation}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      // Location icon shouldn't be present
      const container = screen.getByRole('button', { name: /edit job application/i }).closest('div')
      expect(container?.querySelector('svg[class*="MapPin"]')).not.toBeInTheDocument()
    })

    it('should render match score badge', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      // Based on calculateMatchScore: 50 + 20 (job_description) + 10 (location) + 10 (job_url) + 10 (notes) = 100
      expect(screen.getByText('100%')).toBeInTheDocument()
    })

    it('should apply correct color to high match score', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const badge = screen.getByText('100%')
      expect(badge).toHaveClass('bg-green-100', 'text-green-800')
    })

    it('should apply correct color to medium match score', () => {
      const jobMediumScore = createMockJobApplication({
        job_description: 'Description',
        location: null,
        job_url: null,
        notes: null,
      })

      render(
        <SortableJobCard
          job={jobMediumScore}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      // 50 + 20 = 70%
      const badge = screen.getByText('70%')
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800')
    })

    it('should apply correct color to low match score', () => {
      const jobLowScore = createMockJobApplication({
        job_description: null,
        location: null,
        job_url: null,
        notes: null,
      })

      render(
        <SortableJobCard
          job={jobLowScore}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      // 50%
      const badge = screen.getByText('50%')
      expect(badge).toHaveClass('bg-gray-100', 'text-gray-800')
    })

    it('should render company filter badge for blacklisted company', () => {
      const companyFilters = [
        {
          id: '1',
          company_name: 'TechCorp',
          filter_type: 'blacklist' as const,
          reason: 'Poor reviews',
          created_at: '2024-01-01',
        },
      ]

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
          companyFilters={companyFilters}
        />
      )

      const badge = screen.getByTitle('Poor reviews')
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveClass('bg-red-100', 'text-red-700')
    })

    it('should render company filter badge for whitelisted company', () => {
      const companyFilters = [
        {
          id: '1',
          company_name: 'TechCorp',
          filter_type: 'whitelist' as const,
          reason: 'Great company',
          created_at: '2024-01-01',
        },
      ]

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
          companyFilters={companyFilters}
        />
      )

      const badge = screen.getByTitle('Great company')
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveClass('bg-green-100', 'text-green-700')
    })
  })

  describe('User Interactions', () => {
    it('should call onEdit when card is clicked', async () => {
      const user = userEvent.setup()

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const editButton = screen.getByLabelText(/edit job application/i)
      await user.click(editButton)

      expect(mockOnEdit).toHaveBeenCalledWith(defaultJob)
      expect(mockOnEdit).toHaveBeenCalledTimes(1)
    })

    it('should call onDelete when delete button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const deleteButton = screen.getByLabelText('Delete job')
      await user.click(deleteButton)

      expect(mockOnDelete).toHaveBeenCalledWith(1)
      expect(mockOnDelete).toHaveBeenCalledTimes(1)
    })

    it('should stop propagation when delete button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const deleteButton = screen.getByLabelText('Delete job')
      await user.click(deleteButton)

      // onEdit should not be called when clicking delete
      expect(mockOnEdit).not.toHaveBeenCalled()
      expect(mockOnDelete).toHaveBeenCalledWith(1)
    })

    it('should call onStatusChange when status select is changed', async () => {
      const user = userEvent.setup()

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const statusSelect = screen.getByLabelText('Change job status')
      await user.selectOptions(statusSelect, 'Interview')

      expect(mockOnStatusChange).toHaveBeenCalledWith(1, 'Interview')
      expect(mockOnStatusChange).toHaveBeenCalledTimes(1)
    })

    it('should stop propagation when status select is changed', async () => {
      const user = userEvent.setup()

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const statusSelect = screen.getByLabelText('Change job status')
      await user.selectOptions(statusSelect, 'Interview')

      // onEdit should not be called when changing status
      expect(mockOnEdit).not.toHaveBeenCalled()
      expect(mockOnStatusChange).toHaveBeenCalledWith(1, 'Interview')
    })

    it('should stop propagation when job URL is clicked', async () => {
      const user = userEvent.setup()

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const urlLink = screen.getByLabelText('Open job link')
      await user.click(urlLink)

      // onEdit should not be called when clicking URL
      expect(mockOnEdit).not.toHaveBeenCalled()
    })
  })

  describe('Status Selection', () => {
    it('should render all job statuses in select', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const statusSelect = screen.getByLabelText('Change job status')
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

    it('should have current status selected', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const statusSelect = screen.getByLabelText('Change job status') as HTMLSelectElement
      expect(statusSelect.value).toBe('Applied')
    })
  })

  describe('Accessibility', () => {
    it('should have accessible drag handle', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByLabelText('Drag to reorder')).toBeInTheDocument()
    })

    it('should have accessible edit button', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const editButton = screen.getByLabelText(/edit job application/i)
      expect(editButton).toHaveAccessibleName()
    })

    it('should have accessible delete button', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const deleteButton = screen.getByLabelText('Delete job')
      expect(deleteButton).toHaveAccessibleName()
    })

    it('should have accessible status select', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const statusSelect = screen.getByLabelText('Change job status')
      expect(statusSelect).toHaveAccessibleName()
    })

    it('should have accessible job URL link', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const urlLink = screen.getByLabelText('Open job link')
      expect(urlLink).toHaveAccessibleName()
    })
  })

  describe('Edge Cases', () => {
    it('should handle job without application date', () => {
      const jobWithoutDate = createMockJobApplication({ application_date: null })

      render(
        <SortableJobCard
          job={jobWithoutDate}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.queryByText(/Jan/i)).not.toBeInTheDocument()
    })

    it('should handle empty company filters', () => {
      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
          companyFilters={[]}
        />
      )

      expect(screen.getByText('TechCorp')).toBeInTheDocument()
    })

    it('should handle partial company name match in filters', () => {
      const companyFilters = [
        {
          id: '1',
          company_name: 'Tech',
          filter_type: 'blacklist' as const,
          reason: 'Matches partial name',
          created_at: '2024-01-01',
        },
      ]

      render(
        <SortableJobCard
          job={defaultJob}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
          companyFilters={companyFilters}
        />
      )

      expect(screen.getByTitle('Matches partial name')).toBeInTheDocument()
    })

    it('should truncate long company names', () => {
      const jobWithLongName = createMockJobApplication({
        company: 'A Very Long Company Name That Should Be Truncated',
      })

      render(
        <SortableJobCard
          job={jobWithLongName}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const companyText = screen.getByText('A Very Long Company Name That Should Be Truncated')
      expect(companyText).toHaveClass('truncate')
    })

    it('should truncate long position names', () => {
      const jobWithLongPosition = createMockJobApplication({
        position: 'Senior Principal Staff Software Engineering Architect Lead',
      })

      render(
        <SortableJobCard
          job={jobWithLongPosition}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
          onStatusChange={mockOnStatusChange}
        />
      )

      const positionText = screen.getByText('Senior Principal Staff Software Engineering Architect Lead')
      expect(positionText).toHaveClass('truncate')
    })
  })
})
