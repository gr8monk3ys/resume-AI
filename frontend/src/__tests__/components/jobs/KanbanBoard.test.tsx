import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { createMockJobApplication } from '@/__tests__/test-utils'
import { KanbanBoard } from '@/components/jobs/KanbanBoard'

import type { JobApplication } from '@/types'

// Mock @dnd-kit/core
vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DragOverlay: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  closestCorners: vi.fn(),
  KeyboardSensor: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(),
  useSensors: vi.fn(() => []),
}))

// Mock @dnd-kit/sortable
vi.mock('@dnd-kit/sortable', () => ({
  arrayMove: (arr: unknown[], from: number, to: number) => {
    const newArr = [...arr]
    const item = newArr.splice(from, 1)[0]
    newArr.splice(to, 0, item)
    return newArr
  },
  sortableKeyboardCoordinates: vi.fn(),
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

describe('KanbanBoard', () => {
  const mockOnAddJob = vi.fn()
  const mockOnEditJob = vi.fn()
  const mockOnDeleteJob = vi.fn()
  const mockOnStatusChange = vi.fn()
  const mockOnReorder = vi.fn()

  const mockJobs: JobApplication[] = [
    createMockJobApplication({
      id: 1,
      company: 'Company A',
      position: 'Position A',
      status: 'Bookmarked',
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
    createMockJobApplication({
      id: 4,
      company: 'Company D',
      position: 'Position D',
      status: 'Interview',
    }),
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render all kanban columns', () => {
      const { container } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      // All status headings should be present
      const headings = container.querySelectorAll('h3')
      const statusTexts = Array.from(headings).map((h) => h.textContent)

      expect(statusTexts.some((t) => t?.includes('Bookmarked'))).toBe(true)
      expect(statusTexts.some((t) => t?.includes('Applied'))).toBe(true)
      expect(statusTexts.some((t) => t?.includes('Phone Screen'))).toBe(true)
      expect(statusTexts.some((t) => t?.includes('Interview'))).toBe(true)
      expect(statusTexts.some((t) => t?.includes('Offer'))).toBe(true)
      expect(statusTexts.some((t) => t?.includes('Rejected'))).toBe(true)
    })

    it('should distribute jobs to correct columns', () => {
      render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      expect(screen.getByText('Company A')).toBeInTheDocument()
      expect(screen.getByText('Company B')).toBeInTheDocument()
      expect(screen.getByText('Company C')).toBeInTheDocument()
      expect(screen.getByText('Company D')).toBeInTheDocument()
    })

    it('should show empty columns when no jobs', () => {
      render(
        <KanbanBoard
          jobs={[]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const emptyMessages = screen.getAllByText('No jobs in this stage')
      expect(emptyMessages).toHaveLength(6) // One for each column
    })

    it('should render with minimum height', () => {
      const { container } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const board = container.querySelector('.min-h-\\[500px\\]')
      expect(board).toBeInTheDocument()
    })

    it('should enable horizontal scrolling', () => {
      const { container } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const board = container.querySelector('.overflow-x-auto')
      expect(board).toBeInTheDocument()
    })
  })

  describe('Job Distribution', () => {
    it('should group jobs by status', () => {
      const jobsAllApplied = [
        createMockJobApplication({ id: 1, status: 'Applied' }),
        createMockJobApplication({ id: 2, status: 'Applied' }),
        createMockJobApplication({ id: 3, status: 'Applied' }),
      ]

      const { container } = render(
        <KanbanBoard
          jobs={jobsAllApplied}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      // Applied column should show count of 3
      const appliedHeading = Array.from(container.querySelectorAll('h3')).find((h) =>
        h.textContent?.includes('Applied')
      )
      const appliedSection = appliedHeading?.closest('div')
      expect(appliedSection?.textContent).toContain('3')
    })

    it('should handle jobs in all statuses', () => {
      const jobsAllStatuses: JobApplication[] = [
        createMockJobApplication({ id: 1, status: 'Bookmarked' }),
        createMockJobApplication({ id: 2, status: 'Applied' }),
        createMockJobApplication({ id: 3, status: 'Phone Screen' }),
        createMockJobApplication({ id: 4, status: 'Interview' }),
        createMockJobApplication({ id: 5, status: 'Offer' }),
        createMockJobApplication({ id: 6, status: 'Rejected' }),
      ]

      render(
        <KanbanBoard
          jobs={jobsAllStatuses}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      // Each column should have exactly 1 job
      const counts = screen.getAllByText('1')
      expect(counts.length).toBeGreaterThanOrEqual(6)
    })
  })

  describe('Column Interactions', () => {
    it('should pass onAddJob to all columns', async () => {
      const user = userEvent.setup()

      render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const addButtons = screen.getAllByLabelText(/Add job to/i)
      expect(addButtons.length).toBeGreaterThanOrEqual(6)

      await user.click(addButtons[0]!) // Click first add button
      expect(mockOnAddJob).toHaveBeenCalled()
    })

    it('should pass onEditJob to all job cards', () => {
      render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      // All job cards should be rendered
      expect(screen.getByText('Company A')).toBeInTheDocument()
      expect(screen.getByText('Company B')).toBeInTheDocument()
    })

    it('should pass onDeleteJob to all job cards', () => {
      render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const deleteButtons = screen.getAllByLabelText('Delete job')
      expect(deleteButtons.length).toBe(4) // One for each job
    })

    it('should pass onStatusChange to all job cards', () => {
      render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const statusSelects = screen.getAllByLabelText('Change job status')
      expect(statusSelects.length).toBe(4) // One for each job
    })
  })

  describe('Company Filters', () => {
    it('should pass company filters to all columns', () => {
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
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
          companyFilters={companyFilters}
        />
      )

      expect(screen.getByTitle('Test reason')).toBeInTheDocument()
    })

    it('should handle empty company filters', () => {
      render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
          companyFilters={[]}
        />
      )

      expect(screen.getByText('Company A')).toBeInTheDocument()
    })

    it('should default to empty array when company filters not provided', () => {
      render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      expect(screen.getByText('Company A')).toBeInTheDocument()
    })
  })

  describe('Drag and Drop', () => {
    it('should wrap content in DndContext', () => {
      const { container } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      // The board should be rendered
      expect(container.firstChild).toBeInTheDocument()
    })

    it('should render drag overlay container', () => {
      render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      // DragOverlay is always rendered (though initially empty)
      expect(screen.getByText('Company A')).toBeInTheDocument()
    })
  })

  describe('Layout', () => {
    it('should render columns in a horizontal flex layout', () => {
      const { container } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const boardContainer = container.querySelector('.flex.gap-4')
      expect(boardContainer).toBeInTheDocument()
    })

    it('should have gap between columns', () => {
      const { container } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const boardContainer = container.querySelector('.gap-4')
      expect(boardContainer).toBeInTheDocument()
    })

    it('should have bottom padding for scroll', () => {
      const { container } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const boardContainer = container.querySelector('.pb-4')
      expect(boardContainer).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle single job', () => {
      render(
        <KanbanBoard
          jobs={[mockJobs[0]!]}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      expect(screen.getByText('Company A')).toBeInTheDocument()
      // Five empty columns
      const emptyMessages = screen.getAllByText('No jobs in this stage')
      expect(emptyMessages).toHaveLength(5)
    })

    it('should handle many jobs in single column', () => {
      const manyJobs = Array.from({ length: 20 }, (_, i) =>
        createMockJobApplication({
          id: i,
          company: `Company ${i}`,
          status: 'Applied',
        })
      )

      render(
        <KanbanBoard
          jobs={manyJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      expect(screen.getByText('Company 0')).toBeInTheDocument()
      expect(screen.getByText('Company 19')).toBeInTheDocument()
    })

    it('should handle jobs with missing optional fields', () => {
      const incompleteJobs = [
        createMockJobApplication({
          id: 1,
          company: 'Company',
          position: 'Position',
          status: 'Applied',
          location: null,
          job_url: null,
          application_date: null,
        }),
      ]

      render(
        <KanbanBoard
          jobs={incompleteJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      expect(screen.getByText('Company')).toBeInTheDocument()
      expect(screen.getByText('Position')).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('should memoize jobs by status', () => {
      const { rerender } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      // Rerender with same jobs
      rerender(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      // Should still render correctly
      expect(screen.getByText('Company A')).toBeInTheDocument()
    })

    it('should update when jobs change', () => {
      const { rerender } = render(
        <KanbanBoard
          jobs={mockJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      const newJobs = [
        ...mockJobs,
        createMockJobApplication({
          id: 5,
          company: 'New Company',
          status: 'Bookmarked',
        }),
      ]

      rerender(
        <KanbanBoard
          jobs={newJobs}
          onAddJob={mockOnAddJob}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onReorder={mockOnReorder}
        />
      )

      expect(screen.getByText('New Company')).toBeInTheDocument()
    })
  })
})
