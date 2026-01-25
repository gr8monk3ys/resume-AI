import {
  FileText,
  Briefcase,
  Search,
  Inbox,
  FolderOpen,
  Users,
  Calendar,
  AlertCircle,
  type LucideIcon,
} from 'lucide-react'
import Link from 'next/link'

import { cn } from '@/lib/utils'

/**
 * Props for the EmptyState component
 */
interface EmptyStateProps {
  /** Title text displayed prominently */
  title: string
  /** Description text explaining the empty state */
  description?: string
  /** Icon to display (Lucide icon component) */
  icon?: LucideIcon
  /** Primary action button */
  action?: {
    label: string
    onClick?: () => void
    href?: string
  }
  /** Secondary action link */
  secondaryAction?: {
    label: string
    onClick?: () => void
    href?: string
  }
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
  /** Additional CSS classes */
  className?: string
  /** Children to render below the default content */
  children?: React.ReactNode
}

/**
 * Empty state component for lists with no data
 * Provides visual feedback and optional actions when content is empty
 *
 * @example
 * // Basic usage
 * <EmptyState
 *   title="No resumes yet"
 *   description="Create your first resume to get started"
 * />
 *
 * @example
 * // With action button
 * <EmptyState
 *   title="No job applications"
 *   description="Start tracking your job search"
 *   icon={Briefcase}
 *   action={{ label: "Add Application", onClick: handleAdd }}
 * />
 *
 * @example
 * // With link action
 * <EmptyState
 *   title="No results found"
 *   description="Try adjusting your search criteria"
 *   icon={Search}
 *   action={{ label: "Clear Filters", href: "/jobs" }}
 * />
 */
export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  secondaryAction,
  size = 'md',
  className,
  children,
}: EmptyStateProps) {
  const sizeStyles = {
    sm: {
      container: 'py-8',
      icon: 'w-10 h-10',
      title: 'text-base',
      description: 'text-sm',
      button: 'px-3 py-1.5 text-sm',
    },
    md: {
      container: 'py-12',
      icon: 'w-12 h-12',
      title: 'text-lg',
      description: 'text-sm',
      button: 'px-4 py-2 text-sm',
    },
    lg: {
      container: 'py-16',
      icon: 'w-16 h-16',
      title: 'text-xl',
      description: 'text-base',
      button: 'px-6 py-3 text-base',
    },
  }

  const styles = sizeStyles[size]

  const ActionButton = () => {
    if (!action) return null

    const buttonClasses = cn(
      'inline-flex items-center justify-center font-medium rounded-md',
      'text-white bg-primary-600 hover:bg-primary-700',
      'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500',
      'transition-colors',
      styles.button
    )

    if (action.href) {
      return (
        <Link href={action.href} className={buttonClasses}>
          {action.label}
        </Link>
      )
    }

    return (
      <button type="button" onClick={action.onClick} className={buttonClasses}>
        {action.label}
      </button>
    )
  }

  const SecondaryActionLink = () => {
    if (!secondaryAction) return null

    const linkClasses = cn(
      'text-primary-600 hover:text-primary-700 font-medium',
      'transition-colors',
      size === 'sm' ? 'text-xs' : 'text-sm'
    )

    if (secondaryAction.href) {
      return (
        <Link href={secondaryAction.href} className={linkClasses}>
          {secondaryAction.label}
        </Link>
      )
    }

    return (
      <button type="button" onClick={secondaryAction.onClick} className={linkClasses}>
        {secondaryAction.label}
      </button>
    )
  }

  return (
    <div
      className={cn('text-center', styles.container, className)}
      role="status"
      aria-label={title}
    >
      <Icon
        className={cn('mx-auto text-gray-300', styles.icon)}
        aria-hidden="true"
      />

      <h3 className={cn('mt-4 font-medium text-gray-900', styles.title)}>
        {title}
      </h3>

      {description && (
        <p className={cn('mt-2 text-gray-500', styles.description)}>
          {description}
        </p>
      )}

      {(action || secondaryAction) && (
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
          <ActionButton />
          <SecondaryActionLink />
        </div>
      )}

      {children && <div className="mt-6">{children}</div>}
    </div>
  )
}

/**
 * Preset empty states for common use cases
 */

/**
 * Empty state for no resumes
 */
export function EmptyResumes({
  onCreateClick,
  className,
}: {
  onCreateClick?: () => void
  className?: string
}) {
  return (
    <EmptyState
      icon={FileText}
      title="No resumes yet"
      description="Create your first resume to get started with ATS optimization and job matching"
      action={
        onCreateClick
          ? { label: 'Create Resume', onClick: onCreateClick }
          : { label: 'Create Resume', href: '/resumes' }
      }
      className={className}
    />
  )
}

/**
 * Empty state for no job applications
 */
export function EmptyJobs({
  onAddClick,
  className,
}: {
  onAddClick?: () => void
  className?: string
}) {
  return (
    <EmptyState
      icon={Briefcase}
      title="No job applications"
      description="Start tracking your job search by adding your first application"
      action={
        onAddClick
          ? { label: 'Add Application', onClick: onAddClick }
          : { label: 'Add Application', href: '/jobs' }
      }
      className={className}
    />
  )
}

/**
 * Empty state for search with no results
 */
export function EmptySearchResults({
  query,
  onClearClick,
  className,
}: {
  query?: string
  onClearClick?: () => void
  className?: string
}) {
  return (
    <EmptyState
      icon={Search}
      title="No results found"
      description={
        query
          ? `No matches found for "${query}". Try different keywords or filters.`
          : 'No matches found. Try adjusting your search criteria.'
      }
      action={onClearClick ? { label: 'Clear Search', onClick: onClearClick } : undefined}
      className={className}
    />
  )
}

/**
 * Empty state for no documents
 */
export function EmptyDocuments({
  onCreateClick,
  className,
}: {
  onCreateClick?: () => void
  className?: string
}) {
  return (
    <EmptyState
      icon={FolderOpen}
      title="No documents yet"
      description="Generate cover letters, thank you notes, and other professional documents"
      action={
        onCreateClick
          ? { label: 'Create Document', onClick: onCreateClick }
          : { label: 'Create Document', href: '/documents' }
      }
      className={className}
    />
  )
}

/**
 * Empty state for no interviews scheduled
 */
export function EmptyInterviews({
  className,
}: {
  className?: string
}) {
  return (
    <EmptyState
      icon={Calendar}
      title="No interviews scheduled"
      description="When you schedule interviews, they will appear here for preparation"
      action={{ label: 'View Job Pipeline', href: '/jobs' }}
      className={className}
    />
  )
}

/**
 * Empty state for no team members (if applicable)
 */
export function EmptyTeam({
  onInviteClick,
  className,
}: {
  onInviteClick?: () => void
  className?: string
}) {
  return (
    <EmptyState
      icon={Users}
      title="No team members"
      description="Invite colleagues to collaborate on your job search"
      action={onInviteClick ? { label: 'Invite Member', onClick: onInviteClick } : undefined}
      className={className}
    />
  )
}

/**
 * Empty state for error/failed load
 */
export function ErrorState({
  title = 'Something went wrong',
  description = 'We encountered an error loading this content. Please try again.',
  onRetryClick,
  className,
}: {
  title?: string
  description?: string
  onRetryClick?: () => void
  className?: string
}) {
  return (
    <EmptyState
      icon={AlertCircle}
      title={title}
      description={description}
      action={onRetryClick ? { label: 'Try Again', onClick: onRetryClick } : undefined}
      className={className}
    />
  )
}

/**
 * Empty state wrapper for conditional rendering
 * Shows children when data exists, empty state when it doesn't
 */
export function EmptyStateWrapper<T>({
  data,
  emptyState,
  children,
  className,
}: {
  /** Data to check - if empty/null/undefined, shows empty state */
  data: T[] | null | undefined
  /** Empty state component to show when no data */
  emptyState: React.ReactNode
  /** Children to show when data exists */
  children: React.ReactNode
  /** Additional CSS classes */
  className?: string
}) {
  const isEmpty = !data || data.length === 0

  return (
    <div className={className}>
      {isEmpty ? emptyState : children}
    </div>
  )
}

export default EmptyState
