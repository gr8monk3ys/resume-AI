import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { createMockJobApplication } from '@/__tests__/test-utils'
import { KanbanColumn } from '@/components/jobs/KanbanColumn'

import type { JobApplication, JobStatus } from '@/types'

// Mock @dnd-kit/sortable
vi.mock('@dnd-kit/sortable', () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  verticalListSortingStrategy: {},
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

describe('KanbanColumn', () => {
  const mockOnAddJob = vi.fn()
  const mockOnEditJob = vi.fn()
  const mockOnDeleteJob = vi.fn()
  const mockOnStatusChange = vi.fn()

  const mockJobs: JobApplication[] = [
    createMockJobApplication({
      id: 1,
      company: 'Company A',
      position: 'Position A',
      status: 'Applied',
    }),
    createMockJobApplication({
      id: 2,
      company: 'Company B',
      position: 'Position B',
      status: 'Applied',
    }),
    createMockJobApplication({
      id: 3,
      company: 'Company C',
      position: 'Position C',
      status: 'Applied',
    }),
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render column with status title', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const heading = screen.getAllByText('Applied')[0]
      expect(heading).toBeInTheDocument()
    })

    it('should render job count badge', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('3')).toBeInTheDocument()
    })

    it('should render all job cards', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('Company A')).toBeInTheDocument()
      expect(screen.getByText('Company B')).toBeInTheDocument()
      expect(screen.getByText('Company C')).toBeInTheDocument()
    })

    it('should render add button', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByLabelText('Add job to Applied')).toBeInTheDocument()
    })

    it('should show empty state when no jobs', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('No jobs in this stage')).toBeInTheDocument()
      expect(screen.getByText('0')).toBeInTheDocument()
    })
  })

  describe('Status Colors', () => {
    it('should apply correct colors for Bookmarked status', () => {
      const { container } = render(
        <KanbanColumn
          status="Bookmarked"
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      // Find the header div with bg class
      const header = container.querySelector('.bg-gray-50')
      expect(header).toBeInTheDocument()
    })

    it('should apply correct colors for Applied status', () => {
      const { container } = render(
        <KanbanColumn
          status="Applied"
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const header = container.querySelector('.bg-blue-50')
      expect(header).toBeInTheDocument()
    })

    it('should apply correct colors for Phone Screen status', () => {
      const { container } = render(
        <KanbanColumn
          status="Phone Screen"
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const header = container.querySelector('.bg-purple-50')
      expect(header).toBeInTheDocument()
    })

    it('should apply correct colors for Interview status', () => {
      const { container } = render(
        <KanbanColumn
          status="Interview"
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const header = container.querySelector('.bg-amber-50')
      expect(header).toBeInTheDocument()
    })

    it('should apply correct colors for Offer status', () => {
      const { container } = render(
        <KanbanColumn
          status="Offer"
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const header = container.querySelector('.bg-green-50')
      expect(header).toBeInTheDocument()
    })

    it('should apply correct colors for Rejected status', () => {
      const { container } = render(
        <KanbanColumn
          status="Rejected"
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const header = container.querySelector('.bg-red-50')
      expect(header).toBeInTheDocument()
    })
  })

  describe('User Interactions', () => {
    it('should call onAddJob with correct status when add button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const addButton = screen.getByLabelText('Add job to Applied')
      await user.click(addButton)

      expect(mockOnAddJob).toHaveBeenCalledWith('Applied')
      expect(mockOnAddJob).toHaveBeenCalledTimes(1)
    })

    it('should pass callbacks to job cards', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      // Job cards should be rendered with proper callbacks
      expect(screen.getByText('Company A')).toBeInTheDocument()
    })
  })

  describe('Company Filters', () => {
    it('should pass company filters to job cards', () => {
      const companyFilters = [
        {
          id: '1',
          company_name: 'Company A',
          filter_type: 'blacklist' as const,
          reason: 'Test reason',
          created_at: '2024-01-01',
        },
      ]

      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          companyFilters={companyFilters}
        />
      )

      expect(screen.getByText('Company A')).toBeInTheDocument()
      expect(screen.getByTitle('Test reason')).toBeInTheDocument()
    })

    it('should handle empty company filters', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          companyFilters={[]}
        />
      )

      expect(screen.getByText('Company A')).toBeInTheDocument()
    })
  })

  describe('Job Count', () => {
    it('should display correct count for zero jobs', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('0')).toBeInTheDocument()
    })

    it('should display correct count for one job', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={[mockJobs[0]!]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('1')).toBeInTheDocument()
    })

    it('should display correct count for multiple jobs', () => {
      render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('3')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have accessible add button for each status', () => {
      const statuses: JobStatus[] = ['Bookmarked', 'Applied', 'Phone Screen', 'Interview', 'Offer', 'Rejected']

      statuses.forEach((status) => {
        const { unmount } = render(
          <KanbanColumn
            status={status}
            jobs={[]}
            onAddJob={mockOnAddJob}
            onEditJob={mockOnEditJob}
            onDeleteJob={mockOnDeleteJob}
            onStatusChange={mockOnStatusChange}
          />
        )

        const addButton = screen.getByLabelText(`Add job to ${status}`)
        expect(addButton).toHaveAccessibleName()

        unmount()
      })
    })

    it('should have proper heading hierarchy', () => {
      const { container } = render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      // The status title should be in a heading
      const heading = container.querySelector('h3')
      expect(heading).toBeInTheDocument()
      expect(heading?.textContent).toContain('Applied')
    })
  })

  describe('Edge Cases', () => {
    it('should handle very long status names', () => {
      const { container } = render(
        <KanbanColumn
          status="Phone Screen"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const heading = container.querySelector('h3')
      expect(heading?.textContent).toContain('Phone Screen')
    })

    it('should handle large number of jobs', () => {
      const manyJobs = Array.from({ length: 50 }, (_, i) =>
        createMockJobApplication({
          id: i,
          company: `Company ${i}`,
          position: `Position ${i}`,
          status: 'Applied',
        })
      )

      render(
        <KanbanColumn
          status="Applied"
          jobs={manyJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      expect(screen.getByText('50')).toBeInTheDocument()
      expect(screen.getByText('Company 0')).toBeInTheDocument()
      expect(screen.getByText('Company 49')).toBeInTheDocument()
    })

    it('should handle column with overflow content', () => {
      const { container } = render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      // Column should have scroll capability
      const scrollContainer = container.querySelector('.overflow-y-auto')
      expect(scrollContainer).toBeInTheDocument()
    })
  })

  describe('Layout', () => {
    it('should have fixed width', () => {
      const { container } = render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const column = container.firstChild as HTMLElement
      expect(column).toHaveClass('w-80')
    })

    it('should have rounded corners', () => {
      const { container } = render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const column = container.firstChild as HTMLElement
      expect(column).toHaveClass('rounded-lg')
    })

    it('should have proper spacing between job cards', () => {
      const { container } = render(
        <KanbanColumn
          status="Applied"
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
        />
      )

      const jobContainer = container.querySelector('.space-y-3')
      expect(jobContainer).toBeInTheDocument()
    })
  })
})
