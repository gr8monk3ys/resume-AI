import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { createMockJobApplication } from '@/__tests__/test-utils'
import { ListView } from '@/components/jobs/ListView'

import type { JobApplication } from '@/types'

describe('ListView', () => {
  const mockOnEditJob = vi.fn()
  const mockOnDeleteJob = vi.fn()
  const mockOnStatusChange = vi.fn()
  const mockOnBulkDelete = vi.fn()
  const mockOnBulkStatusChange = vi.fn()

  const mockJobs: JobApplication[] = [
    createMockJobApplication({
      id: 1,
      company: 'Alpha Corp',
      position: 'Software Engineer',
      status: 'Applied',
      location: 'Remote',
      application_date: '2024-01-10',
      job_url: 'https://example.com/job1',
    }),
    createMockJobApplication({
      id: 2,
      company: 'Beta Inc',
      position: 'Frontend Developer',
      status: 'Interview',
      location: 'New York',
      application_date: '2024-01-15',
      job_url: null,
    }),
    createMockJobApplication({
      id: 3,
      company: 'Gamma LLC',
      position: 'Backend Engineer',
      status: 'Applied',
      location: 'San Francisco',
      application_date: '2024-01-20',
      job_url: 'https://example.com/job3',
    }),
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render search input', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      expect(screen.getByPlaceholderText(/search by company or position/i)).toBeInTheDocument()
    })

    it('should render status filter dropdown', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      expect(screen.getByLabelText(/filter by status/i)).toBeInTheDocument()
    })

    it('should render table with all jobs', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      expect(screen.getByText('Alpha Corp')).toBeInTheDocument()
      expect(screen.getByText('Beta Inc')).toBeInTheDocument()
      expect(screen.getByText('Gamma LLC')).toBeInTheDocument()
    })

    it('should render table headers', () => {
      const { container } = render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      // Check for all table headers in the thead
      const thead = container.querySelector('thead')
      expect(thead).toBeInTheDocument()
      expect(thead?.textContent).toContain('Company')
      expect(thead?.textContent).toContain('Position')
      expect(thead?.textContent).toContain('Status')
      expect(thead?.textContent).toContain('Match')
      expect(thead?.textContent).toContain('Applied')
      expect(thead?.textContent).toContain('Location')
      expect(thead?.textContent).toContain('Actions')
    })

    it('should show empty state when no jobs', () => {
      render(
        <ListView
          jobs={[]}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      expect(screen.getByText(/no jobs found matching your criteria/i)).toBeInTheDocument()
    })
  })

  describe('Search Functionality', () => {
    it('should filter jobs by company name', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const searchInput = screen.getByPlaceholderText(/search by company or position/i)
      await user.type(searchInput, 'Alpha')

      expect(screen.getByText('Alpha Corp')).toBeInTheDocument()
      expect(screen.queryByText('Beta Inc')).not.toBeInTheDocument()
      expect(screen.queryByText('Gamma LLC')).not.toBeInTheDocument()
    })

    it('should filter jobs by position', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const searchInput = screen.getByPlaceholderText(/search by company or position/i)
      await user.type(searchInput, 'Frontend')

      expect(screen.getByText('Beta Inc')).toBeInTheDocument()
      expect(screen.queryByText('Alpha Corp')).not.toBeInTheDocument()
      expect(screen.queryByText('Gamma LLC')).not.toBeInTheDocument()
    })

    it('should be case insensitive', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const searchInput = screen.getByPlaceholderText(/search by company or position/i)
      await user.type(searchInput, 'alpha')

      expect(screen.getByText('Alpha Corp')).toBeInTheDocument()
    })

    it('should show empty state when no matches', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const searchInput = screen.getByPlaceholderText(/search by company or position/i)
      await user.type(searchInput, 'NonexistentCompany')

      expect(screen.getByText(/no jobs found matching your criteria/i)).toBeInTheDocument()
    })
  })

  describe('Status Filter', () => {
    it('should filter jobs by status', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const statusFilter = screen.getByLabelText(/filter by status/i)
      await user.selectOptions(statusFilter, 'Interview')

      expect(screen.getByText('Beta Inc')).toBeInTheDocument()
      expect(screen.queryByText('Alpha Corp')).not.toBeInTheDocument()
      expect(screen.queryByText('Gamma LLC')).not.toBeInTheDocument()
    })

    it('should show all jobs when filter is cleared', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const statusFilter = screen.getByLabelText(/filter by status/i)
      await user.selectOptions(statusFilter, 'Interview')
      await user.selectOptions(statusFilter, '')

      expect(screen.getByText('Alpha Corp')).toBeInTheDocument()
      expect(screen.getByText('Beta Inc')).toBeInTheDocument()
      expect(screen.getByText('Gamma LLC')).toBeInTheDocument()
    })

    it('should render all status options', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const statusFilter = screen.getByLabelText(/filter by status/i)
      const options = Array.from((statusFilter as HTMLSelectElement).options).map((opt) => opt.value)

      expect(options).toContain('')
      expect(options).toContain('Bookmarked')
      expect(options).toContain('Applied')
      expect(options).toContain('Phone Screen')
      expect(options).toContain('Interview')
      expect(options).toContain('Offer')
      expect(options).toContain('Rejected')
    })
  })

  describe('Sorting', () => {
    it('should sort by company name ascending', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const companyHeader = screen.getByText('Company').closest('th')!
      await user.click(companyHeader)

      const rows = screen.getAllByRole('row').slice(1) // Skip header row
      const companies = rows.map((row) => within(row).queryByText(/Alpha|Beta|Gamma/))

      expect(companies[0]?.textContent).toContain('Alpha')
    })

    it('should sort by company name descending', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const companyHeader = screen.getByText('Company').closest('th')!
      await user.click(companyHeader)
      await user.click(companyHeader)

      const rows = screen.getAllByRole('row').slice(1)
      const companies = rows.map((row) => within(row).queryByText(/Alpha|Beta|Gamma/))

      expect(companies[0]?.textContent).toContain('Gamma')
    })

    it('should display sort icon on active column', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const companyHeader = screen.getByText('Company').closest('th')!
      await user.click(companyHeader)

      // Should show sort direction icon
      expect(companyHeader.querySelector('svg')).toBeInTheDocument()
    })
  })

  describe('Selection', () => {
    it('should select individual row', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const checkboxes = screen.getAllByLabelText(/select alpha/i)
      await user.click(checkboxes[0]!)

      expect(screen.getByText(/1 selected/i)).toBeInTheDocument()
    })

    it('should select all rows', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const selectAllCheckbox = screen.getByLabelText(/select all/i)
      await user.click(selectAllCheckbox)

      expect(screen.getByText(/3 selected/i)).toBeInTheDocument()
    })

    it('should deselect all rows when clicking select all again', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const selectAllCheckbox = screen.getByLabelText(/select all/i)
      await user.click(selectAllCheckbox)
      await user.click(selectAllCheckbox)

      expect(screen.queryByText(/selected/i)).not.toBeInTheDocument()
    })

    it('should show bulk actions when rows are selected', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[1]!) // Select first job

      expect(screen.getByText(/delete selected/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/bulk change status/i)).toBeInTheDocument()
    })
  })

  describe('Bulk Actions', () => {
    it('should call onBulkDelete when delete selected is clicked', async () => {
      const user = userEvent.setup()
      window.confirm = vi.fn(() => true)

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[1]!)
      await user.click(checkboxes[2]!)

      const deleteButton = screen.getByText(/delete selected/i)
      await user.click(deleteButton)

      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining('2 job applications')
      )
      expect(mockOnBulkDelete).toHaveBeenCalledWith([1, 2])
    })

    it('should not delete when confirmation is cancelled', async () => {
      const user = userEvent.setup()
      window.confirm = vi.fn(() => false)

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[1]!)

      const deleteButton = screen.getByText(/delete selected/i)
      await user.click(deleteButton)

      expect(mockOnBulkDelete).not.toHaveBeenCalled()
    })

    it('should call onBulkStatusChange when bulk status is changed', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[1]!)

      const bulkStatusSelect = screen.getByLabelText(/bulk change status/i)
      await user.selectOptions(bulkStatusSelect, 'Interview')

      expect(mockOnBulkStatusChange).toHaveBeenCalledWith([1], 'Interview')
    })

    it('should clear selection after bulk status change', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[1]!)

      const bulkStatusSelect = screen.getByLabelText(/bulk change status/i)
      await user.selectOptions(bulkStatusSelect, 'Interview')

      expect(screen.queryByText(/selected/i)).not.toBeInTheDocument()
    })

    it('should clear selection when clear button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[1]!)

      const clearButton = screen.getByText(/clear selection/i)
      await user.click(clearButton)

      expect(screen.queryByText(/selected/i)).not.toBeInTheDocument()
    })
  })

  describe('Row Actions', () => {
    it('should call onEditJob when row is clicked', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      // Click on a non-interactive part of the row (company name cell)
      const companyCell = screen.getByText('Alpha Corp').closest('td')!
      await user.click(companyCell)

      expect(mockOnEditJob).toHaveBeenCalledWith(mockJobs[0])
    })

    it('should call onEditJob when edit button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const editButtons = screen.getAllByLabelText(/edit job/i)
      await user.click(editButtons[0]!)

      expect(mockOnEditJob).toHaveBeenCalledWith(mockJobs[0])
    })

    it('should call onDeleteJob when delete button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const deleteButtons = screen.getAllByLabelText(/delete job/i)
      await user.click(deleteButtons[0]!)

      expect(mockOnDeleteJob).toHaveBeenCalledWith(1)
    })

    it('should call onStatusChange when status select is changed', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const statusSelects = screen.getAllByLabelText(/change status/i)
      await user.selectOptions(statusSelects[0]!, 'Interview')

      expect(mockOnStatusChange).toHaveBeenCalledWith(1, 'Interview')
    })

    it('should not trigger row click when clicking action buttons', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const deleteButtons = screen.getAllByLabelText(/delete job/i)
      await user.click(deleteButtons[0]!)

      expect(mockOnDeleteJob).toHaveBeenCalledTimes(1)
      expect(mockOnEditJob).not.toHaveBeenCalled()
    })
  })

  describe('Job URL Links', () => {
    it('should render job URL link when available', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const links = screen.getAllByLabelText(/open job link/i)
      expect(links.length).toBe(2) // Two jobs have URLs
    })

    it('should not render link when job URL is null', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const betaRow = screen.getByText('Beta Inc').closest('tr')!
      const linkInRow = within(betaRow).queryByLabelText(/open job link/i)
      expect(linkInRow).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have accessible filter controls', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      expect(screen.getByLabelText(/filter by status/i)).toHaveAccessibleName()
    })

    it('should have accessible selection checkboxes', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      expect(screen.getByLabelText(/select all/i)).toHaveAccessibleName()
      expect(screen.getByLabelText(/select alpha/i)).toHaveAccessibleName()
    })

    it('should have accessible action buttons', () => {
      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const editButtons = screen.getAllByLabelText(/edit job/i)
      const deleteButtons = screen.getAllByLabelText(/delete job/i)

      editButtons.forEach((button) => expect(button).toHaveAccessibleName())
      deleteButtons.forEach((button) => expect(button).toHaveAccessibleName())
    })
  })

  describe('Edge Cases', () => {
    it('should handle jobs with missing application dates', () => {
      const jobsWithoutDates = [
        createMockJobApplication({
          id: 1,
          company: 'Company',
          application_date: null,
        }),
      ]

      render(
        <ListView
          jobs={jobsWithoutDates}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      expect(screen.getByText('-')).toBeInTheDocument()
    })

    it('should handle jobs with missing locations', () => {
      const jobsWithoutLocations = [
        createMockJobApplication({
          id: 1,
          company: 'Company',
          location: null,
        }),
      ]

      render(
        <ListView
          jobs={jobsWithoutLocations}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      // Check that the location column shows a dash for missing location
      const allDashes = screen.getAllByText('-')
      expect(allDashes.length).toBeGreaterThanOrEqual(1)
    })

    it('should handle combined search and filter', async () => {
      const user = userEvent.setup()

      render(
        <ListView
          jobs={mockJobs}
          onEditJob={mockOnEditJob}
          onDeleteJob={mockOnDeleteJob}
          onStatusChange={mockOnStatusChange}
          onBulkDelete={mockOnBulkDelete}
          onBulkStatusChange={mockOnBulkStatusChange}
        />
      )

      const searchInput = screen.getByPlaceholderText(/search by company or position/i)
      await user.type(searchInput, 'corp')

      const statusFilter = screen.getByLabelText(/filter by status/i)
      await user.selectOptions(statusFilter, 'Applied')

      expect(screen.getByText('Alpha Corp')).toBeInTheDocument()
      expect(screen.queryByText('Beta Inc')).not.toBeInTheDocument()
    })
  })
})
